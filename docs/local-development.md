# 本機開發環境安裝與操作

本文件只說明 Windows 本機開發環境。正式 AWS EC2 的安裝、設定與更新方式請見 [EC2 部署文件](deployment.md)。本機與 EC2 是兩套獨立環境，各自擁有自己的 `.env`、SQLite database、圖片目錄與登入帳號；本機資料不會自動同步至 EC2。

## 1. 安裝前提

### 最簡單的方式

一般情況不需要先自行安裝 Python 或 Node.js。只要電腦具備：

- Windows 10／11
- PowerShell
- `winget`（Microsoft App Installer 提供）
- 可下載 Python 與 npm packages 的網路

就可以直接在專案根目錄執行：

```powershell
.\scripts\bootstrap.ps1
```

`bootstrap.ps1` 會檢查 Python 與 Node.js：缺少時透過 `winget` 安裝；已存在時則沿用。它也會建立 `.env`、Python virtual environment 並安裝前後端 dependencies。

專案要求 Python 3.12 以上。`bootstrap.ps1` 目前只判斷 `python` 指令是否存在，不會自動替換已安裝但版本過舊的 Python；若電腦已有舊版，請先執行 `python --version`，並自行安裝 Python 3.12 後再執行腳本。Node.js 建議使用目前的 LTS 版本。

若腳本剛安裝完 Python 或 Node.js，但目前 PowerShell 尚未取得新 PATH，請關閉 PowerShell、重新開啟後再執行一次 `bootstrap.ps1`。

### 已自行準備工具的方式

若已安裝 Python 3.12、Node.js LTS 與 npm，可以執行：

```powershell
Copy-Item .env.example .env
.\scripts\setup.ps1
```

若 `.env` 已存在，不要覆蓋；先確認其中是否有仍需保留的本機設定。

本機不需要 Docker Desktop、PostgreSQL、RDS、S3、Nginx 或 systemd。

## 2. 設定本機環境變數

開啟專案根目錄的 `.env`，至少確認：

```env
APP_ENV=development
SECRET_KEY=請更換為本機使用的隨機字串
DATABASE_URL=sqlite:///./data/app.db
CORS_ORIGINS=http://localhost:5173
OPENAI_API_KEY=需要實際生成時填入
IMAGE_STORAGE_ROOT=backend/data/images
SESSION_COOKIE_SECURE=false
```

注意：

- `.env` 已被 Git 忽略，不得強制加入版本控制。
- OpenAI key 不得放入 `VITE_*` 變數，否則會被編譯到瀏覽器 bundle。
- 沒有 OpenAI key 仍可啟動網站與執行不呼叫真實生成服務的自動測試，但無法完成實際 AI 圖片生成。
- 本機與 EC2 不共用 `.env`；正式環境設定位於 EC2 的 `/etc/safu/safu.env`。

## 3. 第一次建立本機資料庫

`bootstrap.ps1` 只負責工具、virtual environment 與 dependencies，不會執行 database migration。

第一次啟動前，在專案根目錄執行：

```powershell
Push-Location backend
& ..\.venv\Scripts\python.exe -m alembic upgrade head
Pop-Location
```

這個指令會依 `DATABASE_URL`：

1. 自動建立 SQLite database file（預設為 `backend/data/app.db`）。
2. 執行所有 Alembic migrations。
3. 建立系統需要的資料表與索引。

不需要使用 SQLite 工具手動建立 database 或 table，也不要直接修改 schema。

日後 pull 到包含新 migration 的程式碼時，也要再次執行 `alembic upgrade head`。已套用的 migration 不會重複執行。

## 4. 第一次建立本機登入帳號

確認 migration 已成功後執行：

```powershell
Push-Location backend
& ..\.venv\Scripts\python.exe -m app.manage_user create
Pop-Location
```

依提示輸入 username、至少 12 個字元的 password，並再次確認 password。

這個命令只在該 database 尚未初始化商家帳號時執行一次。若再次執行，程式會拒絕覆蓋既有帳號。

需要重設本機密碼時使用：

```powershell
Push-Location backend
& ..\.venv\Scripts\python.exe -m app.manage_user reset-password
Pop-Location
```

重設密碼會撤銷該 database 內既有 Session。本機帳號不會自動建立或更新 EC2 正式帳號。

## 5. 啟動開發環境

```powershell
.\scripts\dev.ps1
```

啟動後：

| 服務 | URL |
| --- | --- |
| Frontend | <http://localhost:5173> |
| Backend | <http://localhost:8000> |
| API docs | <http://localhost:8000/docs> |
| Health check | <http://localhost:8000/api/v1/health> |

同一 Wi-Fi 的手機可使用腳本顯示的區域網路 URL 測試。按 `Ctrl+C` 會停止前後端服務。

若只想個別啟動服務，可以使用：

```powershell
.\scripts\dev-backend.ps1
.\scripts\dev-frontend.ps1
```

## 6. 每次取得新程式碼後

在沒有未保存修改的前提下取得團隊最新版本：

```powershell
git status --short
git pull --ff-only
```

接著更新 dependencies、migration 並驗證：

```powershell
.\scripts\setup.ps1

Push-Location backend
& ..\.venv\Scripts\python.exe -m alembic upgrade head
& ..\.venv\Scripts\python.exe -m pytest
& ..\.venv\Scripts\python.exe -m ruff check .
Pop-Location

Push-Location frontend
npm.cmd run build
Pop-Location
```

`git status --short` 若顯示不明修改，應先確認來源，不要直接 reset 或覆蓋。

## 7. 修改完成後的本機驗證

最低驗證：

```powershell
Push-Location backend
& ..\.venv\Scripts\python.exe -m pytest
& ..\.venv\Scripts\python.exe -m ruff check .
Pop-Location

Push-Location frontend
npm.cmd run build
Pop-Location
```

若修改生成、聊天室、登入或商品流程，還應在瀏覽器完成對應操作。實際 AI 生成會產生成本，不應只為無關 UI 修改重複呼叫。

## 8. 本機資料與重建方式

預設位置：

| 項目 | 位置 |
| --- | --- |
| SQLite | `backend/data/app.db` |
| 圖片 | `backend/data/images/` |
| Python environment | `.venv/` |
| Frontend dependencies | `frontend/node_modules/` |

這些內容都不應 commit。若需要清空或重建本機資料，先停止開發服務並確認目標確實是本機 `backend/data`；不要把相同操作直接套用到 EC2。資料刪除不可復原時，應先建立備份。

## 9. 到期資料清理

先執行 dry-run：

```powershell
Push-Location backend
& ..\.venv\Scripts\python.exe -m app.cleanup
Pop-Location
```

確認數量與路徑合理後，才執行：

```powershell
Push-Location backend
& ..\.venv\Scripts\python.exe -m app.cleanup --execute
Pop-Location
```

不要用手動刪除圖片取代 cleanup，否則 database 與檔案狀態可能不一致。

## 10. 本機與 EC2 的界線

| 本機開發 | EC2 正式環境 |
| --- | --- |
| Windows PowerShell | Ubuntu shell／SSM Session Manager |
| `.env` | `/etc/safu/safu.env` |
| `backend/data/app.db` | `/srv/safu-data/app.db` |
| `backend/data/images` | `/srv/safu-data/images` |
| Vite :5173 + FastAPI :8000 | Nginx :443 + localhost FastAPI :8000 |
| 手動執行 migration | systemd 啟動 API 前自動 migration |
| 本機測試帳號 | 獨立的正式商家帳號 |

完成本機修改與驗證後，請依 [從本機更新至 EC2](deployment.md#從本機更新至-ec2) 的流程部署；不要複製本機 database、圖片或 `.env` 到正式環境。
