# AWS EC2 部署

目前使用 Ubuntu 24.04 LTS。Security Group 只公開 80、443；不對外開放 22、8000。管理 EC2 使用 AWS Systems Manager Session Manager。

本文件只說明正式 AWS EC2 環境。Windows 本機工具安裝、database migration、測試帳號與開發啟動方式請見 [本機開發環境](local-development.md)。本機與 EC2 的設定、database、圖片及帳號彼此獨立，不會自動同步。

## 部署

將 repository 放到 `/opt/safu`：

```bash
sudo mkdir -p /opt/safu
sudo chown "$USER:$USER" /opt/safu
git clone YOUR_REPOSITORY_URL /opt/safu
cd /opt/safu
sudo bash deploy/setup-ec2.sh
```

腳本會自動：

- 安裝 Python、Node.js、Nginx、Certbot
- 建立 `safu` 系統使用者
- 建立 `/opt/safu/.venv`
- 安裝 backend 與 PostgreSQL driver
- 執行 `npm ci` 和前端 production build
- 安裝 systemd service
- 安裝 Nginx 設定
- 啟用開機自動啟動

第一次執行如果尚未有正式環境設定，腳本會建立：

```text
/etc/safu/safu.env
```

編輯它並至少設定：

```env
APP_ENV=production
SECRET_KEY=足夠長的隨機字串
DATABASE_URL=sqlite:////srv/safu-data/app.db
IMAGE_STORAGE_ROOT=/srv/safu-data/images
CORS_ORIGINS=https://safu-studio.com
SESSION_COOKIE_SECURE=true
SESSION_TTL_MINUTES=480
OPENAI_API_KEY=
OPENAI_API_KEY_PARAMETER_NAME=/safu/production/openai-api-key
AWS_REGION=EC2 所在區域，例如 ap-northeast-1
GENERATION_HOURLY_LIMIT=100
GENERATION_DAILY_LIMIT=300
GENERATION_STALE_MINUTES=10
IMAGE_MIN_FREE_BYTES=2147483648
IMAGE_MIN_FREE_PERCENT=20
```

目前是在同一 AWS Region 的 Systems Manager
Parameter Store 建立 `/safu/production/openai-api-key` `SecureString`，並將只允許
`ssm:GetParameter` 讀取該 parameter 的 IAM instance role 掛載至 EC2。後端會使用
instance role 取得並解密金鑰。

圖片生成前會檢查 `/srv/safu-data/images` 所在 volume 的剩餘空間。預設至少保留
2 GiB，且至少保留 volume 的 20%，兩者取較大；低於門檻時 API 會在呼叫付費圖片
服務前回傳 `507`。可依 EBS 容量調整上述兩個環境變數，但不建議關閉保留空間。

設定完成後再次執行：

```bash
cd /opt/safu
sudo bash deploy/setup-ec2.sh
```

systemd 啟動 FastAPI 前會自動執行 `alembic upgrade head`。第一次部署還必須在 EC2 終端建立正式單一商家帳號；這是互動指令，不會由部署腳本產生或保存明文密碼：

```bash
sudo -u safu bash -c 'set -a; source /etc/safu/safu.env; set +a; cd /opt/safu/backend; ../.venv/bin/python -m app.manage_user create'
```

帳號只需在該 EC2 的 SQLite 初始化一次。日後更新程式不要重跑 `manage_user create`；本機測試帳號也不會自動複製到 EC2。

## 從本機更新至 EC2

完整流程是「本機修改與驗證 → Git commit／push → EC2 pull／部署 → 正式環境驗收」。

### 1. 在本機驗證修改

```powershell
Push-Location backend
& ..\.venv\Scripts\python.exe -m pytest
& ..\.venv\Scripts\python.exe -m ruff check .
Pop-Location

Push-Location frontend
npm.cmd run build
Pop-Location

git status --short
git diff --check
```

建立 commit 並 push 到團隊使用的 branch：

```powershell
git add <本次修改的檔案>
git commit -m "描述本次修改"
git push
```

### 2. 進入 EC2 並確認狀態

使用 AWS Systems Manager Session Manager 進入 EC2：

```bash
sudo git -C /opt/safu status --short
sudo git -C /opt/safu branch --show-current
sudo git -C /opt/safu log -1 --oneline
```

正式主機的 Git worktree 應為乾淨。若 `status --short` 有輸出，先停止部署並確認修改來源，不要用 reset 或 checkout 強制清除。

### 3. Pull 並執行部署腳本

```bash
sudo git -C /opt/safu pull --ff-only
sudo git -C /opt/safu log -1 --oneline
sudo bash /opt/safu/deploy/setup-ec2.sh
```

`setup-ec2.sh` 會更新 Python／npm dependencies、執行 frontend production build、安裝 systemd／Nginx 設定並重啟服務。`safu-api.service` 啟動前會自動執行 `alembic upgrade head`，因此 EC2 不需另外手動建立 database table。

一般程式更新不要再次執行 `app.manage_user create`。正式帳號只在該 EC2 database 第一次初始化時建立一次。

### 4. 部署後技術驗收

```bash
sudo systemctl is-active safu-api nginx safu-cleanup.timer
sudo systemctl --no-pager --full status safu-api
sudo nginx -t
curl -fsS https://safu-studio.com/api/v1/health
sudo journalctl -u safu-api --since "10 minutes ago" --no-pager
```

接著用瀏覽器驗收：

1. HTTPS 首頁可載入。
2. 可以登入與登出。
3. 聊天室與既有圖片可載入。
4. 本次修改的功能正常。
5. 若修改生成流程，再執行一次完整 AI 生成與結果下載。
6. journal 與瀏覽器 response 沒有洩漏 Token、Cookie、Prompt 或內部錯誤。

## 服務管理

部署後的服務管理、日誌、磁碟、cleanup、密碼重設、database 查詢與每月檢查，統一以 [管理者維運手冊](operations-runbook.md) 為準。

## EC2 到期資料清理

正式資料預設保留 14 天，由 `safu-cleanup.timer` 定期啟動 `safu-cleanup.service`。部署腳本負責安裝與啟用 timer；部署後的檢查、dry-run、手動觸發與 log 查詢統一見 [維運手冊的資料清理章節](operations-runbook.md#4-檢查與執行資料清理)。Windows 本機的手動清理方式則見 [本機到期資料清理](local-development.md#9-到期資料清理)。兩個環境的 database 與圖片彼此獨立。

網域註冊完成後，在 Route 53 將 `safu-studio.com` 的 A 記錄指向 Safu EC2 的 Elastic IP。確認 DNS 已生效後執行：

```bash
sudo certbot --nginx -d safu-studio.com --redirect
sudo certbot renew --dry-run
```

依目前單一商家、低流量的條件，因此暫不建立 CloudWatch／SNS 主動告警。本專案採單一 EC2、SQLite 與本機圖片，不要求 RDS、S3 或資料備份。
