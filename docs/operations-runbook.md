# Safu 管理者維運手冊

內容以目前 repository內的設定為準：單一 AWS EC2、Ubuntu、Nginx、systemd、FastAPI、React、SQLite，
圖片與資料庫位於獨立資料目錄。若正式主機的路徑或網域已變更，請先同步更新本手冊。

本手冊負責「EC2 已上線後」的日常操作與故障處理。第一次建立 EC2、正式環境變數、DNS／HTTPS，以及本機版本發布至 EC2 的完整順序，以 [EC2 部署文件](deployment.md) 為準。本手冊第 2 節保留部署時需要的維運檢查，作為主機端操作 runbook。

## 1. 先知道這些位置

| 項目 | 正式環境位置或名稱 |
|---|---|
| 程式碼 | `/opt/safu` |
| Python 虛擬環境 | `/opt/safu/.venv` |
| 正式環境設定 | `/etc/safu/safu.env` |
| SQLite DB | `/srv/safu-data/app.db` |
| 圖片 | `/srv/safu-data/images` |
| 暫存資料 | `/srv/safu-data/temp` |
| API service | `safu-api.service` |
| 定期清理 | `safu-cleanup.timer` / `safu-cleanup.service` |
| Web server | `nginx.service` |
| 健康檢查 | `https://safu-studio.com/api/v1/health` |

日常管理建議透過 AWS Systems Manager Session Manager 進入 EC2。Security Group
只公開 80、443，不公開 8000。

## 2. 更新 code 後部署到 EC2

### 2.1 部署前

先確認程式已在本機測試、commit 並 push。進入 EC2 後：

```bash
cd /opt/safu
sudo git status --short
sudo git branch --show-current
sudo git log -1 --oneline
```

### 2.2 執行部署

```bash
sudo git -C /opt/safu pull --ff-only
sudo bash /opt/safu/deploy/setup-ec2.sh
```

部署腳本會安裝／更新套件、執行 `npm ci`、重建前端、更新 systemd 與 Nginx
設定並重啟 API。`safu-api` 啟動前會自動執行 `alembic upgrade head`。

### 2.3 部署後檢查

```bash
sudo systemctl is-active safu-api nginx safu-cleanup.timer
sudo systemctl --no-pager --full status safu-api
sudo nginx -t
curl -fsS https://safu-studio.com/api/v1/health
sudo journalctl -u safu-api --since "10 minutes ago" --no-pager
```

三個服務應顯示 `active`，health request 應成功。再用瀏覽器實際測試：

1. 首頁可載入且 HTTPS 正常。
2. 可以登入。
3. 聊天室切換正常。
4. 圖片可顯示與下載。
5. 若本次更動生成流程，再做一次完整生成。

## 2. 檢查與清理日誌

### 2.1 API 與 cleanup 日誌

systemd journal 是主要的 backend log：

```bash
# 即時查看 API
sudo journalctl -u safu-api -f

# 最近 200 行
sudo journalctl -u safu-api -n 200 --no-pager

# 指定時間範圍
sudo journalctl -u safu-api --since "2026-08-03 09:00" --until "2026-08-03 12:00"

# 最近一次資料清理
sudo journalctl -u safu-cleanup.service -n 100 --no-pager
```

### 2.2 Nginx 日誌

```bash
sudo tail -n 200 /var/log/nginx/access.log
sudo tail -n 200 /var/log/nginx/error.log
sudo du -sh /var/log/nginx /var/log/journal 2>/dev/null
```

Nginx 通常由 Ubuntu 的 logrotate 管理；先檢查設定，不要直接刪除正在寫入的檔案：

```bash
sudo logrotate --debug /etc/logrotate.d/nginx
sudo journalctl --disk-usage
sudo journalctl --vacuum-time=30d
```

`--vacuum-time=30d` 會刪除超過 30 天的 archived journal。

### 2.3 檢查磁碟

```bash
df -h
sudo du -sh /srv/safu-data/*
sudo journalctl --disk-usage
```

圖片生成會保留至少 2 GiB 且至少 20% volume 空間（取較高者）；低於門檻時 API
會在呼叫付費圖片服務前回傳 HTTP 507。

### 3.4 圖片 timeout 與卡住的 generation job

圖片 API 單次 timeout 為 300 秒，OpenAI SDK 的圖片請求不自動重試。瀏覽器或
Nginx 若先回傳 `5xx`／`504`，前端會沿用同一個 `Idempotency-Key` 查回原
generation job 並輪詢；不要用新 key 手動重送同一個動作，否則會被單帳號唯一
active-job 限制擋下。

只有後端 job 進入 `failed` 後，前端才應顯示正式失敗並允許重新送出。聊天室的失敗
exchange 不應顯示圖片 placeholder 或「儲存期限已過」。若畫面長時間停在生成中，
先檢查 API journal，再查 `generation_jobs.status`、`updated_at`、`error_message`
與 `finished_at`；輪詢 job 時會將超過 `GENERATION_STALE_MINUTES` 的孤立 active
job 標記為失敗。

## 3. 檢查與執行資料清理

資料預設保留 14 天（`DATA_RETENTION_MINUTES=20160`）。timer 每天 03:30 執行，
並加入最多 10 分鐘的隨機延遲；若當時關機，`Persistent=true` 會在下次開機補跑。

```bash
sudo systemctl status safu-cleanup.timer
sudo systemctl list-timers safu-cleanup.timer
sudo journalctl -u safu-cleanup.service -n 100 --no-pager
```

先用 dry run 查看「將會刪除」的數量：

```bash
sudo -u safu bash -c 'set -a; source /etc/safu/safu.env; set +a; cd /opt/safu/backend; ../.venv/bin/python -m app.cleanup'
```

確認 JSON 數量合理後才真正執行：

```bash
sudo systemctl start safu-cleanup.service
sudo journalctl -u safu-cleanup.service -n 100 --no-pager
```

清理範圍包含過期圖片 DB records／assets 與檔案、聊天室、已完成的 generation jobs、
API usage 和 sessions。`pending`、`running` 的 generation job 不會被定期清理。

## 4. 忘記密碼

系統不提供 email 忘記密碼功能，所以管理者需透過 Session Manager 進入 EC2，在終端執行：

```bash
sudo -u safu bash -c 'set -a; source /etc/safu/safu.env; set +a; cd /opt/safu/backend; ../.venv/bin/python -m app.manage_user reset-password'
```

輸入既有 username，再輸入兩次新密碼。密碼至少 12 個字元，終端不會顯示密碼。
成功後所有既有登入 session 會被撤銷，需以新密碼重新登入。

若不知道 username，可只查 username，不要輸出 password hash：

```bash
sudo -u safu sqlite3 /srv/safu-data/app.db "SELECT username FROM users;"
```

第一次部署、尚未建立帳號時才使用：

```bash
sudo -u safu bash -c 'set -a; source /etc/safu/safu.env; set +a; cd /opt/safu/backend; ../.venv/bin/python -m app.manage_user create'
```

## 5. DB 結構

正式資料庫為 `/srv/safu-data/app.db`。schema 由 SQLAlchemy models 與 Alembic
migrations 管理；更新結構應新增 migration，不應手動改 production table。

主要關係：

```text
users
├── sessions
├── chatrooms ── messages
├── image_records ── image_assets ── collection_assets ── collections
├── collections
├── api_usage
└── generation_jobs

image_records ── parent_image_id ──> image_records
image_records ── chatroom_id ──> chatrooms
image_records ── message_id ──> messages
```

| Table | 用途 | 重要欄位 |
|---|---|---|
| `users` | 單一商家帳號 | `username`, `password_hash`, `created_at` |
| `sessions` | 登入 session；DB 只存 token 的 SHA-256 hash | `user_id`, `expires_at`, `revoked_at` |
| `chatrooms` | 聊天室 | `user_id`, `title`, `updated_at`, `expires_at`, `deleted_at` |
| `messages` | 結構化對話訊息 | `chatroom_id`, `role`, `message_type`, `content`, `content_data`, `expires_at` |
| `image_records` | 一次生成／修改的圖片紀錄 | `prompt`, `compiled_prompt`, `generation_data`, parent/chat/message IDs, `expires_at` |
| `image_assets` | motif、preview、chart 等實體圖片 metadata | `asset_type`, `storage_key`, MIME、尺寸、`is_saved`, `deletion_status`, `expires_at` |
| `collections` | 使用者圖片收藏夾 | `name`, `is_system`, `expires_at` |
| `collection_assets` | collections 與 image assets 多對多關聯 | `collection_id`, `image_asset_id` |
| `api_usage` | API 使用紀錄與 rate-limit 計算資料 | `operation`, `status`, provider/usage data, `created_at` |
| `generation_jobs` | 生成工作、冪等與結果／錯誤狀態 | `idempotency_key`, `status`, request/result data, `expires_at`, `finished_at` |

查看目前 migration 版本與 tables：

```bash
sudo -u safu bash -c 'set -a; source /etc/safu/safu.env; set +a; cd /opt/safu/backend; ../.venv/bin/alembic current'
sudo -u safu sqlite3 /srv/safu-data/app.db ".tables"
sudo -u safu sqlite3 /srv/safu-data/app.db ".schema users"
```

請勿把整份 DB、prompt、password hash、session ID 或使用者資料貼到公開位置。

## 6. 例行檢查

```bash
sudo systemctl is-active safu-api nginx safu-cleanup.timer
curl -fsS https://safu-studio.com/api/v1/health
sudo systemctl list-timers safu-cleanup.timer
sudo journalctl -u safu-cleanup.service -n 30 --no-pager
df -h
sudo journalctl --disk-usage
sudo certbot renew --dry-run
```

另確認 EC2/EBS 狀態、HTTPS 到期日、SSM 可登入、Parameter Store 金鑰可讀。
