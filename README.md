# Totem — AI 布農族圖騰設計與商品預覽系統

本文件是專案的交接入口，主要讀者為開發者、維運人員、專案管理者與未來接手者。目標是讓第一次取得 repository 的人，能快速理解系統用途、在本機啟動、找到修改位置，並安全地部署與維護正式環境。

正式網站：<https://safu-studio.com>

## 專案概覽

Totem 是為單一商家打造的手機優先網站。使用者登入後，可以用中文描述設計概念、選擇布農文化相關元素與配色，透過 OpenAI 產生圖騰，再修改元素、顏色或商品載體，並保存至聊天室、圖片庫與收藏圖版。

目前系統包含：

- 中文對話式圖騰生成與四種初始提案
- 布農元素、配色與商品載體選擇
- 元素修改、指定／隨機換色與原組合重新生成
- 九種內建商品參考圖及自由文字商品預覽
- 水平重複圖與十字繡格線輔助圖
- 聊天室、圖片庫、收藏圖版與圖片下載
- 單一商家登入、Session、ownership 與用量限制
- 14 天資料保存、到期清理與磁碟容量保護
- AWS EC2、Nginx、systemd、SQLite 與加密 EBS 部署

本專案不是公開註冊的多租戶 SaaS。現行架構的前提是單一商家、單一後端 worker、低至中度流量、資料預設只保留 14 天。

## 核心使用流程

```text
登入
  ↓
輸入需求／選擇元素、配色、載體
  ↓
Prompt Compiler 整理設計要求
  ↓
Image API 產生四種圖騰提案
  ↓
Pillow 統一色票並建立輔助圖
  ↓
選擇圖片進行元素、配色或商品修改
  ↓
保存於聊天室、圖片庫與收藏圖版
  ↓
到期前下載；預設 14 天後清理
```

生成與修改是同一套資料流程。不要只修改前端顯示而忽略 `generation_jobs`、聊天室 exchange、圖片 record、asset ownership、到期時間與冪等規則。

## 系統架構

```text
Browser
  │
  ├─ Development: React/Vite :5173
  │                  │ /api/v1 proxy
  │                  ▼
  │               FastAPI :8000
  │
  └─ Production: HTTPS / Nginx
                     ├─ React production static files
                     └─ /api/*、/generated/*
                              ▼
                     Gunicorn + Uvicorn worker
                              │
                  ┌───────────┼───────────┐
                  ▼           ▼           ▼
               SQLite     Image files   OpenAI API
               on EBS      on EBS       ├─ Responses API
                                         └─ Image API
```

| 區域 | 技術與責任 |
| --- | --- |
| Frontend | React、TypeScript、Vite；手機介面、狀態管理與 API 呼叫 |
| Backend | Python 3.12、FastAPI、Pydantic；驗證、商業規則、生成流程與檔案授權 |
| AI | `gpt-5-mini` Prompt Compiler、OpenAI Image API |
| 圖片處理 | Pillow；色票統一、換色、repeat 與十字繡輔助圖 |
| Database | SQLAlchemy、Alembic、SQLite；正式 DB 位於加密 EBS |
| Storage | 本機／EBS 圖片目錄；圖片透過需登入與 ownership 驗證的 route 提供 |
| Production | AWS EC2、Nginx、systemd、Gunicorn/Uvicorn、SSM Parameter Store |

目前不需要 RDS、S3、Load Balancer 或多台 EC2。只有在多商家、多 worker、長期保存、不可停機或資料不可遺失時，才應重新評估架構。

## Repository 結構

```text
TotemProject/
├─ backend/
│  ├─ app/
│  │  ├─ api/v1/routes/       HTTP routes
│  │  ├─ core/                設定、secret 與安全輸出
│  │  ├─ db/                  SQLAlchemy models 與 session
│  │  ├─ prompts/             圖騰與商品生成規則
│  │  ├─ schemas/             API 輸入／輸出型別
│  │  ├─ services/            生成、儲存、聊天與商業規則
│  │  └─ assets/              內建商品參考圖
│  ├─ alembic/                DB migrations
│  └─ tests/                  後端自動測試
├─ frontend/
│  └─ src/
│     ├─ api/                 API client
│     ├─ features/auth/       登入功能
│     ├─ features/image-generator/  主要產品介面與流程
│     └─ styles/              全域與動畫樣式
├─ public/                    前端公開圖像與商品卡片資產
├─ deploy/                    EC2、Nginx、systemd 設定
├─ docs/                      架構、部署、維運與檢查表
├─ scripts/                   Windows 本機初始化與啟動腳本
├─ .env.example               環境變數範本，不含秘密
└─ README-backup-waitfordelete.md  舊版文件暫存備份，確認搬移後刪除
```

常見修改位置：

| 想修改的內容 | 主要位置 |
| --- | --- |
| 手機 UI、聊天室、詳情頁、收藏 | `frontend/src/features/image-generator/` |
| API 呼叫與錯誤對應 | `frontend/src/api/client.ts` |
| 圖騰文化元素與 Prompt 規則 | `backend/app/prompts/bunun.py`、`options.py` |
| 商品位置與生成規則 | `backend/app/prompts/product_preview.py` |
| 商品參考圖與路由 | `backend/app/assets/product_references/`、`product_reference_service.py` |
| 生成／重新生成流程 | `backend/app/api/v1/routes/images.py`、`services/image_generation.py` |
| 圖片後處理 | `backend/app/services/image_processing.py` |
| DB schema | `backend/app/db/models.py` 與 `backend/alembic/versions/` |
| 登入與 Session | `backend/app/api/v1/routes/auth.py`、`services/auth_service.py` |
| 正式服務設定 | `deploy/nginx/`、`deploy/systemd/`、`deploy/setup-ec2.sh` |

## 本機環境需求

- Windows 10／11 與 PowerShell
- `winget`（Microsoft App Installer）
- 可安裝 Python 與 npm packages 的網路
- OpenAI API key，只有實際生成圖片時需要

本機不需要 Docker Desktop、PostgreSQL、RDS 或 S3。

## 第一次安裝

在專案根目錄執行：

```powershell
.\scripts\bootstrap.ps1
```

一般情況只需先執行這個命令，不必自行安裝 Python 或 Node.js。若電腦已存在 `python`，請先以 `python --version` 確認為 3.12 以上；腳本不會自動替換已存在的舊版本。腳本會：

1. 檢查並透過 `winget` 安裝 Python 3.12 與 Node.js LTS。
2. 將 `.env.example` 複製為 `.env`（僅在 `.env` 不存在時）。
3. 建立根目錄 `.venv`。
4. 安裝 backend 及開發依賴。
5. 安裝 frontend npm dependencies。

但 `bootstrap.ps1` 不會建立 database table 或登入帳號。工具與 dependencies 完成後，第一次還必須依序執行 migration 與帳號初始化：

```powershell
Push-Location backend
& ..\.venv\Scripts\python.exe -m alembic upgrade head
& ..\.venv\Scripts\python.exe -m app.manage_user create
Pop-Location
```

`alembic upgrade head` 會自動建立 SQLite file、tables 與 indexes，不需要手動建立 database。帳號則只在該本機 database 第一次初始化時建立一次。

若 Python 與 Node.js 已安裝，也可以只執行：

```powershell
Copy-Item .env.example .env
.\scripts\setup.ps1
```

接著編輯 `.env`。不要把 `.env` 或真正的 API key commit 到 Git。完整步驟、更新 dependencies、重設密碼與本機資料位置請見 [本機開發環境安裝與操作](docs/local-development.md)。

## 啟動開發環境

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

本機資料、帳號與 `.env` 都不會同步至 EC2。正式環境有獨立 database、正式設定及商家帳號。

## 環境變數

可設定項目的程式來源是 `backend/app/core/config.py`，可複製的範本是 [.env.example](.env.example)。新增、刪除或改名設定時，必須同步更新這兩處及下表。

| 變數 | 用途 | 本機預設／注意事項 |
| --- | --- | --- |
| `APP_ENV` | 執行環境 | 本機 `development`；正式必須為 `production` |
| `APP_NAME` | FastAPI 應用程式名稱 | 預設 `Totem API` |
| `API_V1_PREFIX` | API version prefix | 預設 `/api/v1`；前後端與 proxy 須一致 |
| `SECRET_KEY` | Session 與安全功能密鑰 | 正式環境必須換成足夠長的隨機值 |
| `DATABASE_URL` | SQLAlchemy DB URL | 本機 SQLite；正式為 `/srv/safu-data/app.db` |
| `CORS_ORIGINS` | 可使用 credentials 的前端來源 | 逗號分隔；正式只允許正式 HTTPS 網域 |
| `VITE_API_BASE_URL` | 瀏覽器呼叫的 API base URL | 預設 `/api/v1`；修改後須重啟或重建 frontend |
| `OPENAI_API_KEY` | 本機 OpenAI key | 不可放入任何 `VITE_` 變數或 commit |
| `OPENAI_API_KEY_PARAMETER_NAME` | 正式 SSM SecureString 名稱 | production 使用此項，不使用明文 key |
| `AWS_REGION` | SSM parameter 所在區域 | 必須與正式設定一致 |
| `OPENAI_IMAGE_MODEL` | 圖騰圖片模型 | 預設 `gpt-image-1` |
| `OPENAI_PRODUCT_IMAGE_MODEL` | 商品預覽模型 | 預設 `gpt-image-1` |
| `OPENAI_PROMPT_COMPILER_MODEL` | 需求整理模型 | 預設 `gpt-5-mini` |
| `USE_PROMPT_COMPILER` | 是否啟用 Prompt Compiler | 預設 `1`／`true` |
| `GENERATION_HOURLY_LIMIT` | 每帳號每小時生成上限 | 預設 100 |
| `GENERATION_DAILY_LIMIT` | 每帳號每日生成上限 | 預設 300 |
| `GENERATION_STALE_MINUTES` | active job 多久未更新視為中斷 | 預設 10 分鐘 |
| `IMAGE_STORAGE_ROOT` | 圖片根目錄 | 本機 `backend/data/images` |
| `IMAGE_MAX_BYTES` | 單張圖片最大檔案大小 | 預設 20,000,000 bytes |
| `IMAGE_MAX_DIMENSION` | 圖片單邊最大尺寸 | 預設 8192 px |
| `IMAGE_MAX_PIXELS` | 圖片最大總像素數 | 預設 40,000,000 |
| `IMAGE_MIN_FREE_BYTES` | 必須保留的磁碟空間 | 預設 2 GiB |
| `IMAGE_MIN_FREE_PERCENT` | 必須保留的磁碟百分比 | 預設 20% |
| `DATA_RETENTION_MINUTES` | 資料保存時間 | 預設 `20160`，即 14 天 |
| `SESSION_COOKIE_NAME` | Session Cookie 名稱 | 預設 `totem_session` |
| `SESSION_TTL_MINUTES` | Session 絕對有效期限 | 預設 480 分鐘 |
| `SESSION_REPLACEMENT_CHALLENGE_MINUTES` | 取代既有登入的一次性 challenge 期限 | 程式預設 5 分鐘 |
| `SESSION_COOKIE_SECURE` | Cookie 是否只經 HTTPS 傳送 | 本機 `false`；正式必須 `true` |
| `LOGIN_FAILURE_LIMIT` | 同一來源與帳號在時間窗內可失敗次數 | 預設 5 |
| `LOGIN_FAILURE_WINDOW_MINUTES` | 登入失敗計數時間窗 | 預設 15 分鐘 |

`VITE_*` 變數會進入瀏覽器 bundle，絕對不可包含 OpenAI key、AWS secret、Session secret 或其他機密。正式主機的實際值不應寫回 repository。

## AI 生成流程

### 圖騰生成

```text
使用者文字、元素、配色與載體
  ↓
Prompt Compiler 建立結構化設計要求
  ↓
布農圖騰規則組合最終 generation prompt
  ↓
Image API 產生四種構圖
  ↓
Pillow 將結果統一至同一目標色票
  ↓
儲存 motif、實際 RGB、request、compiled prompt 與關聯資料
```

### 修改模式

- 更換元素：Revision Resolver 先更新結構化 Design Spec，再將上一版圖騰與元素修改要求交給 Image API 編輯；新元素可帶入新顏色，成品完成後重新擷取實際 RGB 色盤。
- 更換配色：解析信心達門檻時使用 Pillow 換色，否則改用 Image API。
- 原組合重新生成：沿用 record 內保存的完整 Prompt 與實際色票。
- 更換商品圖：保留圖騰，以內建商品參考圖或自然語言要求生成商品預覽。

### 商品參考圖

內建參考圖位於 `backend/app/assets/product_references/`。新增或更換商品時，不應只替換圖片；還要同步檢查：

1. `product_reference_service.py` 的商品映射。
2. `prompts/product_preview.py` 的位置與構圖規則。
3. 前端 `public/carrier-cards/` 的選擇卡片。
4. 商品 reference routing 與 prompt tests。
5. 前端 production build 與一次實際商品生成。

AI 輸出不是完全確定性的。文化元素辨識、色彩、商品位置與完整商品構圖仍可能需要人工驗收。

## API 概覽

所有主要 API 使用 `/api/v1` prefix。開發者需要 API 資訊；管理者一般只需要 health check。為避免手寫 endpoint 清單與程式碼不同步，完整 method、path、request 與 response schema 以本機 FastAPI `/docs`、`backend/app/api/v1/routes/` 與 `backend/app/schemas/` 為準。本節只記錄 OpenAPI schema 無法完整表達、修改時必須保留的共通契約。

| 分類 | 主要用途 |
| --- | --- |
| `/health` | 服務存活檢查 |
| `/auth/*` | 登入、Session 狀態、取代既有 Session、登出 |
| `/chatrooms/*` | 聊天室與訊息管理 |
| `/images/*` | 生成、修改、圖片、商品預覽、收藏與下載 |
| `/generation-jobs/*` | 生成工作狀態與網路中斷後對帳 |
| `/generated/images/{storage_key}` | 經登入、ownership、刪除及到期驗證後傳送圖片 |

### 必須保留的 API 契約

- 所有呼叫付費 GAI 的生成操作都使用 16–100 字元的 `Idempotency-Key`。同一動作因網路錯誤、`5xx` 或 `504` 重試時必須沿用原 key；新 key 代表新工作。
- 每個帳號同時只允許一個 `pending`／`running` generation job，並受每小時與每日用量上限保護。
- generation job 狀態持久化於 database。瀏覽器切換聊天室、重新整理或暫時斷線後，必須查詢既有 job，不可直接建立第二個付費請求。
- 聊天室生成請求使用 `X-Chatroom-Id` 與 `X-Client-Exchange-Id` 關聯原聊天室 exchange。完成或失敗結果必須回寫原訊息，不可依賴原頁面持續開啟。
- API 錯誤使用穩定的 `detail.code` 與安全中文 `detail.message`。第三方 SDK 訊息、traceback、檔案路徑或 database 細節不得直接回傳前端。
- `/generated/images/{storage_key}` 不是公開靜態目錄，必須驗證 Session、ownership、刪除狀態與 record 到期時間。
- 修改生成、聊天室或圖片 route 時，必須同步驗證 idempotency、ownership、額度、active-job lock、錯誤安全與 pending-message reconciliation。

以上契約對本機與 EC2 完全相同；差別只有設定值、資料位置與執行環境。

## 資料與儲存

SQLite 是唯一的結構化資料來源；瀏覽器 localStorage 與 JSON catalog 不是正式資料來源。

```text
users
├─ sessions
├─ chatrooms ── messages
├─ image_records ── image_assets ── collection_assets ── collections
├─ api_usage
└─ generation_jobs

image_records ── parent_image_id ──> image_records
```

主要資料表：

| Table | 用途 |
| --- | --- |
| `users` | 商家帳號與 Argon2id password hash |
| `sessions` | Session token hash、有效期限與撤銷狀態 |
| `chatrooms`、`messages` | 聊天室及結構化 exchange |
| `image_records` | 每次生成或修改的 self-contained 紀錄 |
| `image_assets` | motif、preview、chart 等圖片 metadata |
| `collections`、`collection_assets` | 收藏圖版及圖片關聯 |
| `api_usage` | 用量計算與生成結果摘要 |
| `generation_jobs` | 冪等、active lock、工作與結果狀態 |

修改 schema 時必須新增 Alembic migration，不可直接修改 production SQLite table。正式資料與圖片位置請參考 [維運手冊](docs/operations-runbook.md)。

### 圖片 record、asset 與到期生命週期

以下是本機與 EC2 共用的核心資料規則，不能只從單一 table 結構判斷：

- `ImageRecord` 代表一次完整的生成或修改版本；每個新圖騰保存自己的 request、Prompt、實際色票、設計狀態與 assets。
- `ImageAsset` 代表實體圖片 metadata；主要類型包括 `motif`、`preview`、`chart` 與 `original`。同一 record 內每種 asset 最多一筆。
- 後續商品預覽通常建立衍生 record，以 `parent_image_id` 指向來源；不可為了新的聊天室回覆改綁原 record 的單值 `message_id`。
- 多個衍生 record 可以引用同一個 motif `storage_key`。清除舊 record 時，只要仍有有效引用，就必須保留共用實體檔案。
- 圖片、聊天室與訊息預設保存 14 天，時間一律以 UTC 儲存，前端顯示時才轉換成本地時間。
- 成功新增商品預覽或十字繡輔助圖時，依目前規則刷新所屬版本期限；單純讀取、收藏或更改 saved 狀態不延長期限。
- cleanup 依 record 與引用關係刪除 database 資料、收藏關聯及圖片；`pending`／`running` generation job 不會被一般到期清理刪除。
- SQLite 是結構化資料的唯一來源，圖片 binary 位於 `IMAGE_STORAGE_ROOT`；不可用手動刪檔取代 cleanup。

修改 `database_catalog_service.py`、`cleanup_service.py`、圖片 route 或 asset 查詢時，必須特別驗證共用 `storage_key`、衍生 record、到期時間與聊天室圖片關聯。

### 聊天室排序與滑動到期

- 聊天室依 `updated_at` 由新到舊排列；`updated_at` 代表最後一次內容更新，不是最後查看時間。
- 單純開啟聊天室或取得列表，不會將聊天室置頂，也不會延長保存期限。
- 傳送或同步新內容時，聊天室與相關訊息期限更新為操作時間加上 `DATA_RETENTION_MINUTES`。
- generation job 已完成、但 pending 訊息尚未取得結果時，第一次 reconciliation 會補回結果並同步必要的排序與期限；完成後重複讀取不應持續刷新期限。
- 已到期聊天室即使 cleanup 尚未實際刪除，也不應出現在最近對話。

這些規則同樣適用本機與 EC2，因為它們是應用程式商業邏輯，不是部署設定。

## 測試與品質檢查

在專案根目錄執行：

```powershell
Push-Location backend
& ..\.venv\Scripts\python.exe -m pytest
& ..\.venv\Scripts\python.exe -m ruff check .
Pop-Location

Push-Location frontend
npm.cmd run build
Pop-Location
```

2026-08-10 本機基準：

- 後端：85 tests passed
- Ruff：通過
- TypeScript 與 Vite production build：通過

2026-08-11 已完成正式 EC2 的網路、HTTPS、Cookie、服務重啟、Parameter Store／IAM、log、前端 bundle、generation job 恢復、手機版面、到期清理、cleanup timer 與磁碟容量保護驗收。CI 與前端自動測試依目前單人、單一商家模式決定暫不導入；完整證據與重新評估條件見 [專案完成度與上線準備清單](docs/project-readiness-checklist.md)。

## 正式部署

正式環境目前採：

| 項目 | 設定 |
| --- | --- |
| 網域 | `https://safu-studio.com` |
| 主機 | 單一 AWS EC2／Ubuntu |
| 程式碼 | `/opt/safu` |
| 正式設定 | `/etc/safu/safu.env` |
| SQLite | `/srv/safu-data/app.db` |
| 圖片 | `/srv/safu-data/images` |
| API service | `safu-api.service` |
| Cleanup | `safu-cleanup.timer`／`safu-cleanup.service` |
| 管理連線 | AWS Systems Manager Session Manager |

第一次部署、正式 database／帳號、DNS／Certbot，以及「本機修改 → Git push → EC2 pull → migration → 驗收」的完整流程，請依照 [EC2 部署文件](docs/deployment.md)。日後更新的核心命令是：

```bash
sudo git -C /opt/safu status --short
sudo git -C /opt/safu pull --ff-only
sudo bash /opt/safu/deploy/setup-ec2.sh
```

部署後至少檢查：

```bash
sudo systemctl is-active safu-api nginx safu-cleanup.timer
sudo nginx -t
curl -fsS https://safu-studio.com/api/v1/health
sudo journalctl -u safu-api --since "10 minutes ago" --no-pager
```

部署失敗處理、migration、日誌與 rollback 注意事項請依照 [維運手冊](docs/operations-runbook.md)，不要自行用 `git reset --hard`、直接覆蓋運作中的 SQLite，或任意執行 `alembic downgrade`。目前營運決策是不保留正式 DB／圖片備份；`git pull` 只能恢復程式碼，無法恢復既有帳號或資料。

## 日常維護

### 建立帳號與重設密碼

- 第一次部署才執行 `python -m app.manage_user create`。
- 忘記密碼使用 `python -m app.manage_user reset-password`。
- 重設密碼後，既有 Session 會被撤銷。
- 不提供公開註冊或 email 自助重設流程。

正式環境的完整命令請見 [維運手冊](docs/operations-runbook.md)。

### 到期資料清理

資料預設保留 14 天，但本機與 EC2 的執行方式不同：

- 本機開發：由開發者視需要手動執行 dry-run，再確認是否實際清理。完整命令見 [本機到期資料清理](docs/local-development.md#9-到期資料清理)。
- EC2 正式環境：由 `safu-cleanup.timer` 定期啟動 `safu-cleanup.service`，不需要管理者每天手動執行。檢查、dry-run 與手動觸發方式見 [維運手冊的資料清理章節](docs/operations-runbook.md#4-檢查與執行資料清理)。

兩個環境都不可用手動刪除圖片檔案取代 cleanup 程式，否則 database 與檔案狀態可能不一致。本機 cleanup 只處理本機資料；不會清除或影響 EC2。

### 每月檢查

- API、Nginx 與 cleanup timer 是否 active
- HTTPS 與憑證續期
- EC2／EBS 狀態與剩餘容量
- cleanup 最近一次執行結果
- journal 與 Nginx log 使用量
- SSM 是否可登入、Parameter Store 是否可讀
- 是否仍接受目前「不備份、故障後重建」的營運決策

操作命令與故障排除步驟見 [維運手冊](docs/operations-runbook.md)。

## 安全界線

- `.env`、API key、Cookie、Session token、密碼與 AWS credentials 不得進 Git。
- OpenAI key 不得放入 `VITE_*` 變數，否則會進入瀏覽器 bundle。
- Production 不直接保存明文 `OPENAI_API_KEY`；使用 SSM SecureString 與最小權限 instance role。
- Security Group 只公開 80／443；8000、5173、SQLite 不得對公網開放。
- Production 必須使用 HTTPS、`SESSION_COOKIE_SECURE=true` 與正式 Origin allowlist。
- 圖片 route 必須維持登入、ownership、刪除狀態與到期驗證。
- Log 不得輸出完整 Prompt、request body、圖片內容、Token、Cookie 或 traceback 給前端。

## 已知限制與未完成事項

- 圖片生成目前是同步請求；單一 worker 與 300 秒 timeout 適用目前低流量模式。
- 登入失敗限流存在 backend process memory，服務重啟後紀錄會歸零。
- SQLite 與本機圖片儲存不適合多台應用伺服器同時寫入。
- 系統沒有圖形化管理後台、公開註冊或 email 密碼重設。
- AI 圖片可能偶爾出現錯誤色彩、商品位置或文化元素表現，需要人工檢查。
- 目前未導入 CI、前端自動測試或主動監控告警；是否需要依使用規模與停機容忍度重新評估。
- 正式環境不保留 DB／圖片備份；專案負責人接受 EC2／EBS 故障後永久失去既有資料，改以重新部署、migration 與重建帳號恢復服務。

未完成項目、必要性、完成標準與證據請以 [專案完成度與上線準備清單](docs/project-readiness-checklist.md) 為準。已修正問題由 Git 歷史與自動測試保存，不另外維護容易過期的修正紀錄文件。

## 文件索引

完整文件責任與維護規則亦可從 [docs 文件目錄](docs/README.md) 查詢。

| 文件 | 適合何時閱讀 |
| --- | --- |
| [本機開發環境](docs/local-development.md) | Windows 安裝、migration、帳號、啟動、測試與取得新程式碼 |
| [部署文件](docs/deployment.md) | 第一次部署、更新 EC2、設定 DNS 與 HTTPS |
| [管理者維運手冊](docs/operations-runbook.md) | 日常維護、日誌、清理、密碼與故障處理 |
| [專案完成度清單](docs/project-readiness-checklist.md) | 判斷還需做什麼、是否完成及完成證據 |
| [歷史 EC2 規劃](docs/archive/ec2-single-store-deployment-plan.md) | 查詢早期架構、實作順序與風險決策；不作為目前狀態依據 |
| [舊版 README 備份](README-backup-waitfordelete.md) | 暫時查詢尚未確認搬移的舊內容；確認完成後刪除 |

## 接手者第一天建議順序

1. 閱讀本文件的專案概覽、架構與安全界線。
2. 依本機開發文件執行 bootstrap、migration、帳號初始化與 `dev.ps1`，確認可登入並載入網站。
3. 跑完後端測試、Ruff 與前端 build。
4. 閱讀 `backend/app/db/models.py` 與主要 `services/`，理解資料生命週期。
5. 閱讀部署與維運手冊，但在取得正式權限前不要修改 EC2。
6. 查看專案完成度清單，先處理 P0，再新增產品功能。

若這六步都能完成，接手者就應能安全地開始修改與維護本專案。
