# Totem — AI 布農族圖騰生成網站

以 React、TypeScript 與 FastAPI 開發的前後端分離網站。使用者可輸入設計概念、選擇布農文化相關元素，透過 OpenAI Image API 生成圖騰，並取得不同配色、水平重複圖與十字繡輔助圖。

本專案不需要 Docker Desktop。本機直接使用 Python virtual environment、Node.js、SQLite 與本機圖片目錄；部署至 AWS EC2 時使用 Nginx 與 systemd。圖片、聊天室、訊息、收藏及生成工作均已由 SQLAlchemy/SQLite 儲存，不再使用 JSON catalog 或瀏覽器 localStorage 作為正式資料來源。

## 目前實作狀態（2026-07-22）

已完成：

- SQLite 資料模型與 Alembic migrations。
- 圖片紀錄、圖片資產、收藏資料夾與多對多收藏關係。
- 聊天室與訊息 API；前端聊天資料直接讀寫 SQLite。
- 圖片生成結果與聊天室／訊息關聯。
- `generation_jobs` 工作狀態、全域生成鎖與過期工作處理。
- 生成 job 保存聊天室 context；即使切換聊天室或關閉頁面，後端仍會完成訊息狀態與圖片關聯。
- `Idempotency-Key` 防止網路重試重複呼叫付費 API。
- 每小時／每日生成額度，涵蓋圖片生成、商品預覽與重新生成。
- SQLite foreign keys、WAL、`synchronous=FULL` 與 busy timeout。
- 集中式 storage service；圖片使用 UUID 檔名，寫入前驗證格式、MIME、大小、尺寸及路徑安全。
- `IMAGE_STORAGE_ROOT` 控制圖片根目錄；相對路徑固定以專案根目錄解析。本機使用 `backend/data/images`，EC2 使用 `/srv/safu-data/images`。
- `expires_at` 與可重跑 cleanup job；預設 dry-run，確認後才可用 `--execute` 實際清除到期資料與圖片。
- 舊 JSON catalog、JSON 匯入程式及聊天 localStorage 匯入程式均已移除。
- 單一商家帳號初始化、Argon2id 密碼 hash、伺服器端 Session，以及登入／狀態／登出 API。
- 圖片、收藏、聊天室、生成工作與實際圖片檔案均加入 Session 和 ownership 驗證。
- Session Cookie 使用 HttpOnly、SameSite=Strict；正式環境啟用 Secure，並驗證修改請求的 Origin。
- 登入失敗限流；Session 原始 Token 只存在 Cookie，SQLite 僅保存 SHA-256 hash。
- 前端登入頁、啟動時登入狀態檢查與登出操作。

部署前尚待完成：

- 正式網域完成後設定 `SESSION_COOKIE_SECURE=true`，並進行完整 HTTPS／Cookie 驗收。
- 將 SQLite 與圖片移至 EC2 持久資料目錄。
- AWS Parameter Store、IAM role、HTTPS、正式網域與 Nginx/systemd 驗證。

完整項目請參考 [EC2 單一商家部署檢查表](docs/ec2-single-store-deployment-checklist.md)。

## 主要功能

- 中文圖騰需求輸入
- 布農元素快速選擇
- Prompt compiler：使用 `gpt-5-mini` 將需求整理為圖片生成指令
- AI 圖片生成
- 初始生成一次圖騰幾何，再輸出四組隨機配色
- 對話式修改：更換元素、更換配色、原組合重新生成、更換商品圖
- 更換元素先由 Revision Resolver 產生結構化 Design Spec，再編譯新 Prompt
- GAI 解析自然語言顏色，Pillow 執行指定區域換色
- 5 種商品與其合法位置的商品預覽
- 水平三連 repeat 預覽
- 我的圖片瀑布流、收藏資料夾與預設「我的最愛」
- 圖騰詳情畫廊：圖騰原圖、商品展示、輔助圖
- 全螢幕圖片檢視、雙指縮放、拖曳與左右切換
- 手機聊天室介面，聊天室與訊息儲存於 SQLite
- 橫式十字繡格線輔助圖
- 每張圖騰使用 self-contained catalog record
- React 前端與版本化 FastAPI API

## 技術架構

| 區域 | 技術 |
|---|---|
| 前端 | React、TypeScript、Vite |
| 後端 | Python 3.12、FastAPI、Pydantic |
| AI | OpenAI Responses API、Image API |
| 圖片處理 | Pillow |
| 本機與第一版 EC2 資料 | SQLAlchemy、SQLite、本機／EC2 圖片目錄 |
| 未來擴充選項 | PostgreSQL/RDS、S3（目前不需要） |
| Web server | Nginx |
| Process manager | systemd + Gunicorn/Uvicorn |

開發環境資料流：

```text
React :5173
    │ HTTP /api/v1
    ▼
FastAPI :8000
    ├─ OpenAI API
    ├─ IMAGE_STORAGE_ROOT（透過 /generated/images URL 提供）
    └─ SQLite database
```

正式環境由 Nginx 提供 React 靜態檔，並將 `/api/` 反向代理至只監聽 `127.0.0.1:8000` 的 FastAPI。

## 使用者流程

1. 新聊天室顯示「元素、風格、工藝技術」與文字輸入框。
2. 初次送出只生成一個圖騰幾何，再以 Pillow 產生四張不同配色；此階段不生成商品圖。
3. 使用者點擊圖騰後進入詳情畫廊，可切換圖騰原圖、商品展示與十字繡輔助圖，並將目前圖片加入一個或多個收藏資料夾。
4. 商品預覽按需生成：只有第一次點開該圖騰詳情頁時，才在背景隨機選擇合法的商品、位置與商品／背景樣式並呼叫圖片 API；從未點開的圖騰不生成商品照。
5. 若要指定其他商品設定，從聊天室圖片左下方的「類似」選擇「更換商品圖」，再選載體、合法位置與商品／背景。此操作建立獨立 record，保留舊商品照。
6. 修改圖騰分為四種模式：
   - `更換元素`：第一層 `gpt-5-mini` 將最新要求解析為結構化 Design Spec，第二層 Prompt Compiler 編譯新 Prompt，再呼叫 Image API。明確排除的元素會保存於 `excluded_elements`；例如「移除菱形」會覆蓋預設菱形偏好。
   - `更換配色`：有文字時由文字 GAI 解析來源/目標 RGB，再由 Pillow 換色；留空時從預設布農色盤隨機換色。此模式不呼叫 Image API。
   - `原組合重新生成`：直接重用該 record 保存的完整 Prompt 與實際 RGB 色票，不重新執行 Prompt Compiler。
   - `更換商品圖`：保持圖騰不變，只生成指定的新商品照。
7. 一般輸入框在生成後仍可繼續從頭設計；同一聊天室會保留多組 Generation Exchange。每張圖片也可隨時使用「類似」。

前端是最大寬度 480px 的手機版聊天室，會依裝置 viewport 自動適配；窄螢幕不會因固定卡片寬度產生水平溢出，並支援手機安全區域。第一則訊息送出時會立即建立 pending 聊天紀錄；即使先離開聊天室，完成或失敗結果仍會更新原 chat ID。返回聊天室時會重新向後端取得 generation job 最終狀態，避免圖片已完成但畫面仍顯示 `Load failed`。聊天室、訊息、圖片與收藏皆由後端 SQLite 提供，因此重新整理或更換瀏覽器後仍可讀取相同資料。

## 專案目錄

```text
TotemProject/
├─ backend/
│  ├─ app/
│  │  ├─ api/v1/routes/       FastAPI endpoints
│  │  ├─ core/                環境設定
│  │  ├─ db/                  SQLAlchemy 基礎設定
│  │  ├─ generated/           本機產生的圖片與 catalog
│  │  ├─ prompts/             布農 prompt 與選項資料
│  │  ├─ schemas/             Request/response models
│  │  ├─ services/            圖片生成、處理與資料存取
│  │  └─ main.py              FastAPI application
│  ├─ tests/
│  └─ pyproject.toml
├─ frontend/
│  ├─ src/
│  │  ├─ api/
│  │  ├─ features/image-generator/
│  │  ├─ styles/
│  │  ├─ App.tsx
│  │  └─ main.tsx
│  └─ package.json
├─ deploy/
│  ├─ nginx/
│  └─ systemd/
├─ docs/
├─ scripts/
├─ .env.example
└─ README.md
```

## 本機需求

請先安裝：

- Python 3.12 或以上
- Node.js 22 LTS
- npm
- Git

不需要安裝 Docker Desktop、PostgreSQL 或 Nginx 才能進行本機開發。

確認工具版本：

```powershell
python --version
node --version
npm --version
```

## 一鍵初始化（類似 Docker build）

在專案根目錄開啟 PowerShell。腳本會檢查並透過 `winget` 安裝 Python 3.12、Node.js LTS，接著建立 `.venv`、安裝 Python/npm 套件並建立 `.env`：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\bootstrap.ps1
```

接著編輯 `.env`，至少填入：

```env
OPENAI_API_KEY=你的金鑰
```

`.env` 已被 Git 忽略，不要將 API key 寫入前端程式、README 或提交到版本控制。

第一次使用登入功能時，在專案根目錄建立本機單一商家帳號：

```powershell
Set-Location C:\TotemProject\backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m app.manage_user create
```

指令會互動要求輸入帳號、密碼及密碼確認；密碼至少 12 個字元，畫面不會顯示輸入內容。它會更新既有 `single-store` 使用者，因此原本的圖片、聊天室與收藏不會失去所有權。同一個資料庫只能初始化一次；EC2 使用自己的 `/srv/totem-data/app.db`，部署時須在 EC2 另建正式帳號。

若 PowerShell 阻擋本機腳本，可只針對目前終端調整：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

## 一鍵啟動開發環境（類似 docker compose up）

初始化完成後只需要：

```powershell
.\scripts\dev.ps1
```

這會同時啟動 FastAPI 與 Vite，並將兩邊的 log 顯示在目前終端。按 `Ctrl+C` 會一起停止。

如果想分開啟動或除錯，也可以使用下面兩個腳本。

第一個 PowerShell 終端啟動後端：

```powershell
.\scripts\dev-backend.ps1
```

第二個 PowerShell 終端啟動前端：

```powershell
.\scripts\dev-frontend.ps1
```

服務位置：

| 服務 | URL |
|---|---|
| React 網站 | http://localhost:5173 |
| FastAPI | http://localhost:8000 |
| Swagger API 文件 | http://localhost:8000/docs |
| 健康檢查 | http://localhost:8000/api/v1/health |

## 環境變數

以 [.env.example](.env.example) 建立本機 `.env`。

| 變數 | 說明 | 開發預設值 |
|---|---|---|
| `APP_ENV` | 執行環境 | `development` |
| `APP_NAME` | API 名稱 | `Totem API` |
| `API_V1_PREFIX` | API prefix | `/api/v1` |
| `SECRET_KEY` | 應用程式密鑰 | 必須自行更換 |
| `DATABASE_URL` | SQLAlchemy 連線字串 | SQLite |
| `CORS_ORIGINS` | 允許的前端來源，逗號分隔 | `http://localhost:5173` |
| `VITE_API_BASE_URL` | 前端呼叫的 API URL；開發由 Vite proxy 轉送 | `/api/v1` |
| `OPENAI_API_KEY` | OpenAI API key | 無，必填 |
| `OPENAI_IMAGE_MODEL` | 圖片生成模型 | `gpt-image-1` |
| `OPENAI_PROMPT_COMPILER_MODEL` | Prompt compiler 模型 | `gpt-5-mini` |
| `USE_PROMPT_COMPILER` | 是否啟用 prompt compiler | `1` |
| `GENERATION_HOURLY_LIMIT` | 每小時最多建立的生成工作數 | `100` |
| `GENERATION_DAILY_LIMIT` | 每 24 小時最多建立的生成工作數 | `300` |
| `GENERATION_STALE_MINUTES` | 執行中工作超過多久視為中斷 | `10` |
| `IMAGE_STORAGE_ROOT` | 圖片儲存根目錄；相對路徑以專案根目錄解析 | `backend/data/images` |
| `IMAGE_MAX_BYTES` | 單張圖片最大位元組數 | `20000000` |
| `IMAGE_MAX_DIMENSION` | 圖片單邊最大像素 | `8192` |
| `IMAGE_MAX_PIXELS` | 圖片最大總像素數 | `40000000` |
| `DATA_RETENTION_MINUTES` | 新資料保留時間；正式環境 14 天 | `20160` |
| `SESSION_COOKIE_NAME` | Session Cookie 名稱 | `totem_session` |
| `SESSION_TTL_MINUTES` | 登入 Session 絕對期限（分鐘） | `480` |
| `SESSION_COOKIE_SECURE` | Cookie 是否只允許 HTTPS；正式環境必須為 `true` | `false` |
| `LOGIN_FAILURE_LIMIT` | 同一來源與帳號在時間窗內最多失敗次數 | `5` |
| `LOGIN_FAILURE_WINDOW_MINUTES` | 登入失敗計數時間窗 | `15` |

修改 `VITE_` 開頭的環境變數後，需要重新啟動 Vite。

## API

所有圖騰 API 都位於 `/api/v1/images`。

登入 API：

| Method | Endpoint | 用途 |
|---|---|---|
| `POST` | `/api/v1/auth/login` | 驗證帳密並建立 HttpOnly Session Cookie |
| `GET` | `/api/v1/auth/me` | 取得目前登入帳號；未登入回傳 `401` |
| `POST` | `/api/v1/auth/logout` | 撤銷伺服器 Session 並清除 Cookie |

| Method | Endpoint | 用途 |
|---|---|---|
| `POST` | `/api/v1/images/generate` | 生成圖騰與配色版本 |
| `GET` | `/api/v1/images` | 取得圖片列表 |
| `GET` | `/api/v1/images/assets` | 取得全部圖片資產，可用 `saved`／`favorite` 篩選 |
| `PATCH` | `/api/v1/images/{id}/assets/{type}` | 更新 motif／preview／chart 的狀態 |
| `GET/POST` | `/api/v1/images/collections` | 取得或新增收藏資料夾 |
| `GET` | `/api/v1/images/collections/{collection_id}/assets` | 取得資料夾內圖片 |
| `PATCH` | `/api/v1/images/{id}/assets/{type}/collections` | 設定圖片所屬收藏資料夾 |
| `POST` | `/api/v1/images/{id}/preview` | 為指定圖騰生成或更新商品預覽 |
| `POST` | `/api/v1/images/{id}/preview/random` | 隨機選擇合法設定並生成商品預覽 |
| `POST` | `/api/v1/images/{id}/preview/variant` | 保留圖騰並建立指定商品照的新 record |
| `POST` | `/api/v1/images/{id}/regenerate` | 更換元素、程式換色或依完整 record 重新生成 |
| `GET` | `/api/v1/images/{id}/cross-stitch-chart` | 產生十字繡輔助圖 |

生成範例：

```powershell
$body = @{
  prompt = "月亮、山脈與守護的意象"
  elements = @("月亮", "山脈")
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/api/v1/images/generate `
  -Headers @{ "Idempotency-Key" = [guid]::NewGuid().ToString() } `
  -ContentType application/json `
  -Body $body
```

所有會呼叫 GAI 的 `POST` endpoint 都必須帶 16–100 字元的 `Idempotency-Key`。同一個動作因網路問題重試時必須沿用原 key；使用新 key 代表建立新的生成工作。工作狀態可由 `GET /api/v1/generation-jobs/{job_id}` 查詢。

聊天室內的生成請求另外傳送 `X-Chatroom-Id` 與 `X-Client-Exchange-Id`。後端會把這兩個值存入 generation job，完成或失敗後直接更新對應 assistant message 並連結結果圖片；即使使用者切換聊天室、重新整理或關閉頁面，也不依賴原頁面繼續存在。若 pending 訊息比 job 結果晚寫入，聊天室同步時會再次 reconciliation，避免訊息永久停在生成中。

`palette` 與 `count` 不屬於前端初始生成請求。後端固定生成四組隨機、不重複的配色。每張圖騰是獨立且完整的 record；除了相容舊 UI 的 `palette_name`，也會保存從輸出圖片重新擷取的實際 RGB 色票。

修改 endpoint 的 request body：

```json
{
  "mode": "elements | palette | same",
  "instruction": "把紅色換成奶茶色"
}
```

商品預覽 endpoint 的 request body：

```json
{
  "product": "托特包",
  "placement": "袋子中央",
  "display_style": "白色商品＋白底"
}
```

目前啟用商品：托特包、束口袋、午餐袋、飲料提袋、環形鑰匙圈。位置必須屬於該商品的合法選項。

十字繡 endpoint 接受以下 query parameters：

- `width`：10–300，預設 100
- `height`：10–300，預設 50
- `colors`：2–20，預設 5

## 測試與檢查

安裝腳本會安裝 backend development dependencies。執行：

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m ruff check .
Pop-Location

Push-Location frontend
npm run build
Pop-Location
```

## 本機資料位置

開發期間的檔案位於：

```text
data/app.db（實際位置依 DATABASE_URL 與啟動目錄設定）
backend/data/images/（由 IMAGE_STORAGE_ROOT 設定，與啟動目錄無關）
```

## 到期資料清理

本機與正式環境目前都使用 `DATA_RETENTION_MINUTES=20160`（14 天）。若要測試短生命週期，可暫時調低此值；它只影響設定後新建立資料的 `expires_at`，測試結束必須改回 `20160`。

圖片、聊天室、訊息與清理判斷一律使用 UTC；前端顯示時才轉換成本地時間。請勿使用作業系統本機時間字串寫入資料庫，避免台灣時區造成到期時間延後 8 小時。

清理指令預設只預覽，不會刪除：

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m app.cleanup
Pop-Location
```

確認輸出的筆數與檔案數正確後，才可實際執行：

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m app.cleanup --execute
Pop-Location
```

清理工作可重跑；圖片檔案不存在時不會失敗，共用中的圖片檔案不會因其中一筆 asset 到期而被刪除，仍在 `pending`／`running` 的 generation job 也不會被清理。收藏資料夾本身永久保留；圖片 asset 到期後，資料夾與該圖片的關聯會自動刪除，最後可能留下空資料夾。

每張新圖騰使用一筆不依賴其他圖片的 self-contained record，核心資料包括：

```json
{
  "id": "獨立圖片 ID",
  "files": {
    "original": "單張配色圖騰",
    "repeat": "水平三連圖騰"
  },
  "generation": {
    "user_prompt": "使用者需求",
    "elements": ["月亮", "山脈"],
    "compiled_prompt": "實際使用的完整圖片 Prompt"
  },
  "palette": {
    "colors": [{"rgb": [244, 239, 226]}]
  },
  "design_spec": {
    "final_elements": ["山脈"],
    "added_elements": [],
    "removed_elements": ["月亮"],
    "excluded_elements": ["月亮"],
    "changes_palette": false,
    "palette_instruction": "",
    "revision_summary": "移除月亮並保留山脈"
  },
  "assets": {
    "motif": {
      "url": "/generated/images/example.png",
      "favorite": false,
      "collection_ids": []
    },
    "preview": {
      "type": "preview",
      "filename": "商品預覽檔名",
      "url": "/generated/images/example_mockup.png",
      "favorite": false,
      "collection_ids": [],
      "parameters": {
        "product": "托特包",
        "placement": "袋子中央",
        "display_style": "白色商品＋白底"
      }
    }
  }
}
```

每個新圖騰 record 都保存自己的 Prompt、元素、實際 RGB 色票與 assets。重新配色完成後會重新擷取 RGB；更換元素時直接讀取上一張 `palette.colors`，將精確色集合寫入 Prompt，並在 Image API 完成後由 Pillow 強制套用。顏色可以交換圖騰中的位置，但不會跳出指定集合。`palette_name` 只作顯示；缺少實際色票時才退回預設名稱或從原圖擷取。

`design_spec` 目前主要出現在更換元素產生的新 record。它由 Mini Revision Resolver 產生並經 Pydantic 驗證，只包含設計狀態；ID、檔案、URL、收藏與 assets 一律由 Python 管理。`excluded_elements` 是持續性的明確排除，優先級高於預設 Prompt 偏好。

商品圖只保存於 `assets.preview`，不再重複保存 `preview`、`preview_filename`、`preview_url` 或 `preview_request`。商品 variant 目前採「一個 record 對應一張商品照」：更換商品圖會建立新 record、沿用相同圖騰並保存新的 preview asset，避免覆蓋舊聊天室結果。

SQLite 是目前唯一的結構化資料來源。舊 JSON catalog 與 localStorage 聊天匯入邏輯已移除。圖片二進位仍放在檔案系統，SQLite 保存圖片路徑、metadata、收藏關係及聊天關聯。第一版 EC2 必須維持單一 FastAPI worker；若未來要多台主機或多 worker 寫入，應再遷移至 PostgreSQL。

圖片檔案統一由 `storage_service.py` 管理。它負責安全解析 storage key、產生存取 URL、UUID 命名、圖片內容驗證、原子寫入、metadata 讀取與刪除。`/generated/images/{storage_key}` 已不再直接掛載公開靜態目錄，而是由 FastAPI 驗證 Session、ownership、刪除狀態與到期時間後回傳檔案；未登入、非擁有者、已刪除或已到期均不會取得圖片。

## AWS EC2 部署

部署設定已放在：

- [EC2 部署步驟](docs/deployment.md)
- [EC2 自動安裝腳本](deploy/setup-ec2.sh)
- [Nginx 設定](deploy/nginx/safu.conf)
- [FastAPI systemd service](deploy/systemd/safu-api.service)
- [14 天清理 systemd service](deploy/systemd/safu-cleanup.service)
- [每日清理 systemd timer](deploy/systemd/safu-cleanup.timer)
- [架構決策](docs/architecture.md)

正式環境建議：

1. Ubuntu 24.04 LTS EC2。
2. Nginx 對外提供 80/443，正式網域為 `safu-studio.com`。
3. FastAPI 只監聽 `127.0.0.1:8000`。
4. Security Group 不開放 8000。
5. 使用 HTTPS；主機管理使用 AWS Systems Manager Session Manager，不公開 SSH。
6. 本機開發金鑰放在 Git 忽略的 `.env`；正式環境只在 `/etc/safu/safu.env` 設定 Parameter Store 名稱與 AWS Region，實際金鑰存放於 AWS Systems Manager Parameter Store `SecureString`，並由 EC2 IAM instance role 讀取。
7. SQLite 與圖片放在 `/srv/safu-data`，程式碼放在 `/opt/safu`。
8. FastAPI 維持單一 worker；目前不需要 S3 或 RDS。

### 部署階段建議

- 可先部署只有開發者使用、資料可清除的私人 staging，以驗證 HTTPS、CORS、Nginx、環境變數、手機 UI 與 OpenAI API。
- SQLite 部署維持單一 backend worker，資料與圖片依產品規則只保留 14 天。
- 單一商家登入、Session Cookie、私有 API ownership、HTTPS、Secure Cookie 與清理 CLI 已完成；EC2 已啟用並實測 systemd cleanup timer。
- 未來只有在需要多 worker、多台 EC2、長期保存或備份時，才遷移至 PostgreSQL/RDS 與 S3。

## 目前限制與後續工作

- 原型程式的完整文化元素、Prompt 規則與圖片處理演算法已拆入對應模組；後續修改應保留重構前後行為測試。
- SQLite 適用於目前的單一商家與單一 worker；不支援未來直接水平擴充成多台寫入。
- 登入與 Session 驗證已完成；正式部署仍須使用 HTTPS、`SESSION_COOKIE_SECURE=true` 並驗證正式網域 Origin。
- 圖片在 EC2 儲存於獨立的 `/srv/safu-data/images` 加密 EBS volume。
- 圖片生成目前是同步請求；生成時間變長後應加入背景工作佇列。
- 生成鎖、額度、圖片、收藏、聊天室與生成工作均使用 Session 對應的實際登入者 ID。
- 已提供單一帳號 CLI 初始化方式，但尚未建立圖形化管理後台或密碼重設流程。
- 14 天資料與圖片清理服務及 CLI 已完成；本機可使用 `python -m app.cleanup` 預覽，確認後以 `python -m app.cleanup --execute` 刪除。EC2 的 systemd cleanup service/timer 已建立、啟用並通過手動執行測試。
- 上線前應加入 HTTPS、CloudWatch logs 與基本監控告警；依本專案決策不做資料備份。

## 安全注意事項

- 不要提交 `.env`。
- 不要將 `OPENAI_API_KEY` 放入任何 `VITE_` 變數。
- 不要讓 EC2 的 port 8000 對公網開放。
- 正式環境務必更換 `SECRET_KEY`。
- 生成 endpoint 已有登入、ownership、quota、單帳號 active job 鎖與冪等保護；敏感 Log、一般化 `500`、production bundle 與 repository 機密掃描已完成，正式 EC2 上線後仍須驗收實際 journal／Nginx log。

## 商品預覽與近期行為說明（2026-07-23）

### 固定商品參考圖與雙圖生成

商品預覽會同時送出兩張輸入圖片給 Image API：

1. 系統內建的固定商品參考圖，用來保留商品外型、比例、接縫、翻蓋、肩帶、五金與視角。
2. 使用者目前的圖騰圖片，作為要合成到商品上的最終圖案。

Image API 最後只輸出一張商品預覽照，不會輸出拼貼圖。使用者只需選擇商品、圖騰位置及商品／背景顏色，不需自行上傳商品圖。

固定參考圖位於：

```text
backend/app/assets/product_references/
```

商品與安全檔名的正式對應定義在：

```text
backend/app/services/product_reference_service.py
```

目前支援的商品：

| 商品 | 固定參考圖 |
|---|---|
| 托特包 | `tote-bag.jpg` |
| 帆布袋 | `canvas-bag.jpg` |
| 束口袋 | `drawstring-bag.jpg` |
| 午餐袋 | `lunch-bag.jpg` |
| 飲料提袋 | `beverage-carrier.jpg` |
| 環形鑰匙圈 | `loop-key-fob.jpg` |
| 台灣高中生側背書包 | `taiwan-school-shoulder-bag.jpg` |
| 貝殼零錢包 | `shell-coin-purse.jpg` |
| 圖騰織帶手機掛繩 | `phone-lanyard.jpg` |

專案根目錄的 `商品參考圖/` 是原始圖片整理區，不是執行時讀取位置。新增或替換原圖後，必須：

1. 複製至 `backend/app/assets/product_references/`。
2. 改用不含空格與中文字的安全檔名。
3. 更新 `PRODUCT_REFERENCE_FILES`。
4. 確認 `PRODUCT_OPTIONS`、`PRODUCT_PLACEMENT_OPTIONS`、前端 `products` 與 `placementByProduct` 同步。

套件封裝已透過 `backend/pyproject.toml` 的 `tool.setuptools.package-data` 納入這些 JPG 資產。

### 商品位置規則

- 手動選擇商品時仍可使用「AI自動決定位置」。
- `POST /api/v1/images/{id}/preview/random` 的隨機位置會排除「AI自動決定位置」，只從該商品的具體位置中抽選。
- 「台灣高中生側背書包」使用台灣傳統高中學生布製側背書包造型，約寬 20 cm、高 15 cm、厚 6 cm，具有大面積正面翻蓋、側片、尼龍肩帶及塑膠調節扣。
- 該書包的指定正面位置名稱為「翻蓋偏下方」，不是「袋子中央」。
- 「翻蓋偏下方」會將完整圖騰水平置中、垂直放在翻蓋下方約三分之一處；圖騰外框寬度約為翻蓋寬度的 20%，左右各保留至少 40% 空白，且不得貼近底邊或縫線。
- 其他商品的「袋子中央」不受上述 20% 規則影響。

商品英文描述、位置提示與特殊尺寸鎖定位於：

```text
backend/app/prompts/product_preview.py
```

雙圖送出與最終覆寫規則位於：

```text
backend/app/services/product_preview.py
```

### 聊天室滑動到期時間

聊天室保存期限採滑動式 14 天，而不是建立後固定 14 天。以下操作會把聊天室及其訊息的 `expires_at` 更新為操作當下加上 `DATA_RETENTION_MINUTES`：

- 開啟單一聊天室。
- 傳送或同步聊天室內容。
- 重新命名聊天室。

單純取得聊天室列表不會延長全部聊天室。預設 `DATA_RETENTION_MINUTES=20160`，即 14 天。

### 收藏圖版

收藏面板的「＋」已連接建立圖版功能：

- 輸入名稱後可按「＋」或 Enter 建立。
- 名稱空白時會聚焦名稱輸入框。
- 建立期間會阻止重複送出。

### 驗證

修改商品、位置或參考圖後，至少執行：

```powershell
Push-Location backend
python -m py_compile app\prompts\product_preview.py app\services\product_preview.py app\services\product_reference_service.py app\api\v1\routes\images.py
Pop-Location

Push-Location frontend
npm.cmd run build
Pop-Location
```

若後端開發依賴已安裝，再執行：

```powershell
Push-Location backend
python -m pytest
Pop-Location
```
