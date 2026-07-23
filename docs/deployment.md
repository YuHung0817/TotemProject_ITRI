# AWS EC2 部署（不使用 Docker）

建議使用 Ubuntu 24.04 LTS。Security Group 只開放 22（限制管理 IP）、80、443；不要對外開放 8000。

## 第一次部署

先將 repository 放到 `/opt/totem`：

```bash
sudo mkdir -p /opt/totem
sudo chown "$USER:$USER" /opt/totem
git clone YOUR_REPOSITORY_URL /opt/totem
cd /opt/totem
sudo bash deploy/setup-ec2.sh
```

腳本會自動：

- 安裝 Python、Node.js、Nginx
- 建立 `totem` 系統使用者
- 建立 `/opt/totem/.venv`
- 安裝 backend 與 PostgreSQL driver
- 執行 `npm ci` 和前端 production build
- 安裝 systemd service
- 安裝 Nginx 設定
- 啟用開機自動啟動

第一次執行如果尚未有正式環境設定，腳本會建立：

```text
/etc/totem/totem.env
```

編輯它並至少設定：

```env
APP_ENV=production
SECRET_KEY=足夠長的隨機字串
DATABASE_URL=sqlite:////srv/totem-data/app.db
IMAGE_STORAGE_ROOT=/srv/totem-data/images
CORS_ORIGINS=https://你的網域
SESSION_COOKIE_SECURE=true
SESSION_TTL_MINUTES=480
OPENAI_API_KEY=
OPENAI_API_KEY_PARAMETER_NAME=/totem/production/openai-api-key
AWS_REGION=EC2 所在區域，例如 ap-northeast-1
GENERATION_HOURLY_LIMIT=10
GENERATION_DAILY_LIMIT=30
GENERATION_STALE_MINUTES=10
IMAGE_MIN_FREE_BYTES=2147483648
IMAGE_MIN_FREE_PERCENT=20
```

正式環境禁止直接設定 `OPENAI_API_KEY`。請先在同一 AWS Region 的 Systems Manager
Parameter Store 建立 `/totem/production/openai-api-key` `SecureString`，並將只允許
`ssm:GetParameter` 讀取該 parameter 的 IAM instance role 掛載至 EC2。後端會使用
instance role 取得並解密金鑰，不需要在主機保存 AWS access key。

圖片生成前會檢查 `/srv/totem-data/images` 所在 volume 的剩餘空間。預設至少保留
2 GiB，且至少保留 volume 的 20%，兩者取較大；低於門檻時 API 會在呼叫付費圖片
服務前回傳 `507`。可依 EBS 容量調整上述兩個環境變數，但不建議關閉保留空間。

設定完成後再次執行：

```bash
cd /opt/totem
sudo bash deploy/setup-ec2.sh
```

systemd 啟動 FastAPI 前會自動執行 `alembic upgrade head`。第一次部署還必須在 EC2 終端建立正式單一商家帳號；這是互動指令，不會由部署腳本產生或保存明文密碼：

```bash
sudo -u totem bash -c 'set -a; source /etc/totem/totem.env; set +a; cd /opt/totem/backend; ../.venv/bin/python -m app.manage_user create'
```

帳號只需在該 EC2 的 SQLite 初始化一次。日後更新程式不要重跑 `manage_user create`；本機測試帳號也不會自動複製到 EC2。

## 日後更新

```bash
cd /opt/totem
sudo -u totem git pull --ff-only
sudo bash deploy/setup-ec2.sh
```

## 服務管理

```bash
sudo systemctl status totem-api
sudo systemctl restart totem-api
sudo journalctl -u totem-api -f
sudo nginx -t
```

綁定網域後，再使用 Certbot 設定 HTTPS。正式環境應加入 CloudWatch logs、健康監控與告警，並確認 14 天清理 timer 正常執行。本專案目前採單一 EC2、SQLite 與本機圖片，不要求 RDS、S3 或資料備份。
