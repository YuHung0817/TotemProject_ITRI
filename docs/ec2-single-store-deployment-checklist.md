# EC2 單一商家部署決策與執行清單

本文件記錄 Totem AI 圖像網站目前確定的營運條件、技術決策、實作順序與上線驗收項目。

## 1. 已確定的前提

- 只有一個商家帳號使用。
- 商家透過自己的網域，由外縣市連線使用網站。
- 網站的實際主機是 AWS EC2；公司電腦只用於開發、管理與部署，不需要保持開機，也不應直接對外提供網站。
- 聊天室、聊天訊息、生成紀錄、收藏關聯及圖片只保留 14 天。
- 資料屬於可重新生成的靈感資料，接受 EC2/EBS 故障時提前遺失，因此不建置備份或 snapshot。
- 使用者必須在到期前自行下載想保留的圖片；刪除後不可復原。
- 必須保護付費 GAI API Token，並限制被盜用或失控消耗的風險。

## 2. 最終架構決策

```text
商家瀏覽器
    │
    │ HTTPS + 自有網域
    ▼
EC2 Security Group（只開放 80/443）
    │
    ▼
Nginx
    ├── React 靜態檔案
    ├── /api/* → FastAPI 127.0.0.1:8000
    └── 受保護圖片 → 通過 FastAPI session 驗證後由 Nginx 傳送
                         │
                         ├── SQLite：帳號、session、聊天室、訊息、圖片 metadata、收藏、用量
                         ├── EBS 本機目錄：實際圖片檔案
                         └── SSM Parameter Store：GAI API Token
```

本案不需要 RDS，也不需要 S3。未來需求改變時仍可遷移，但目前不要為尚未存在的多使用者或高流量需求增加成本與複雜度。

## 3. 為什麼選 SQLite，不選 JSON

本案選擇 **SQLite**。

JSON 適合只讀設定或測試資料，但本網站需要同時處理：

- 新增、重新命名及刪除聊天室；
- 新增訊息；
- 新增及刪除圖片；
- 一張圖片加入多個收藏資料夾；
- session 登入狀態；
- 14 天到期查詢與跨表刪除；
- API 用量與生成工作狀態；
- 多個請求可能在相近時間寫入。

SQLite 能提供 transaction、foreign key、索引與唯一約束，會比反覆讀寫整份 JSON 安全且容易維護。單一商家、單台 EC2、單一 FastAPI worker 的負載足以使用 SQLite。

SQLite 設定至少包含：

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;
PRAGMA busy_timeout = 5000;
```

正式服務先使用一個 Uvicorn worker。若未來要增加 worker 或多台 EC2，應先評估改用 PostgreSQL，不要直接共用 SQLite 檔案。

## 4. 資料模型

建議資料表：

- `users`：唯一商家帳號與 Argon2id password hash。
- `sessions`：伺服器端 session、到期時間及撤銷時間。
- `chatrooms`：聊天室標題與到期時間。
- `messages`：使用者及 AI 訊息。
- `image_records`：prompt、生成參數、來源圖片及生成狀態。
- `image_assets`：motif、original、preview、chart 等實際檔案 metadata。
- `collections`：收藏資料夾，包含系統「我的收藏」。
- `collection_assets`：收藏資料夾與圖片 asset 的多對多關聯。
- `api_usage`：生成次數、時間及結果，用於額度控制與稽核。
- `generation_jobs`：避免重複送出與追蹤 pending/running/succeeded/failed。

`collection_assets` 必須有：

```text
UNIQUE(collection_id, image_asset_id)
```

這能讓同一張圖片同時存在多個資料夾，但不會重複加入同一資料夾。

資料庫只保存圖片的相對 `storage_key`、類型、大小與 MIME type，不保存圖片二進位。例如：

```text
2026/07/uuid/motif.webp
```

## 5. 14 天保留與刪除規則

所有需要保留 14 天的主資料在建立時寫入：

```text
expires_at = created_at（UTC）+ 14 天
```

規則如下：

- 聊天室到期時，刪除其訊息與相關生成紀錄。
- 每個圖片 asset 依自己的建立時間到期；收藏不會延長圖片期限。
- 收藏資料夾永久保留；裡面的圖片到期後只清除圖片與收藏關聯，空資料夾不刪除。
- 使用者手動刪除圖片時，立即從 UI 消失並進入相同的實體清理流程。
- session 不使用 14 天資料規則，另設較短的閒置與絕對期限。
- 所有時間在後端與資料庫使用 UTC，前端轉換為台灣時間顯示。

每日由 systemd timer 執行清理工作。清理程序必須可重複執行：

1. 找出 `expires_at <= now` 的資料。
2. 將圖片狀態改為 `deleting` 並提交 transaction。
3. 只允許刪除設定之圖片根目錄內的檔案，拒絕 `..`、絕對路徑及 symlink 越界。
4. 刪除圖片及衍生檔案。
5. transaction 內刪除資料庫紀錄，利用 foreign key cascade 清除關聯。
6. 檔案已不存在視為成功，確保工作中斷後可以重跑。
7. 記錄刪除筆數、失敗筆數與剩餘磁碟空間，但不可記錄 Token、cookie 或完整 prompt。

清理工作每天至少執行一次，並使用 `Persistent=true`，讓 EC2 關機錯過排程後在下次啟動補跑。

## 6. 使用者到期提醒

目前介面依已確認的需求呈現：

- App bar 說明圖片只保留 14 天，提醒使用者下載想保留的圖片；
- 「我的圖片」與「我的收藏」中的每張圖片，在圖片外側左下方以小字顯示明確到期日期與時間；
- 聊天室圖片不重複顯示到期文字；
- 圖片詳情及圖片檢視器提供下載操作。

「加入收藏」不代表永久保存，不能讓使用者產生錯誤期待。

## 7. EC2 與檔案配置

建議路徑：

```text
/opt/totem/                     程式碼與前端 build
/srv/totem-data/app.db          SQLite
/srv/totem-data/images/         圖片
/srv/totem-data/temp/           暫存檔
```

- 程式碼與持久資料必須分開，部署不得覆蓋 `/srv/totem-data`。
- 服務使用無登入 shell 的專用 `totem` OS 帳號。
- `/srv/totem-data` 僅允許 `totem` 服務帳號存取，建議權限 `750`，檔案依需要使用更嚴格權限。
- EBS 啟用靜態加密。
- 即使決定不備份，仍建議將 data volume 的 `DeleteOnTermination` 設為 `false`，避免誤終止 instance 就立即刪除磁碟；這是降低誤操作，不是備份。
- 設定容量上限及警報，磁碟接近滿載時停止接受新生成，不能等寫入失敗才處理。

## 8. 登入與 API Token 安全

### 登入

- 只建立一個商家帳號，不提供公開註冊。
- 密碼使用 Argon2id hash，不保存明文或可逆密碼。
- 登入成功後使用隨機、高熵、伺服器端 session。
- Cookie 使用 `Secure`、`HttpOnly`、`SameSite=Strict`、`Path=/`；正式網域可使用 `__Host-` 前綴。
- 登入後重新產生 session ID；登出、改密碼及到期時撤銷 session。
- 除健康檢查及登入外，所有 API 都在後端驗證 session，包括圖片讀取與下載。
- 所有會改變資料的請求使用 CSRF 防護，並驗證 `Origin`。
- 登入失敗訊息不透露帳號是否存在。

### GAI API Token

- Token 永遠不得出現在 React、`VITE_*` 環境變數、Git、URL、API response 或 log。
- Token 存入 AWS Systems Manager Parameter Store `SecureString`。
- EC2 掛載 IAM instance role，只允許讀取該一個 parameter；不要在 EC2 儲存長期 AWS access key。
- EC2 要求 IMDSv2。
- FastAPI 只在後端呼叫 GAI provider。
- 若懷疑外洩，立即撤銷並輪替 Token。

### 防止惡意消耗

登入本身不等於用量保護，還需要：

- Nginx 對登入與生成 endpoint 分別限流。
- 後端限制同時只能有少量生成工作。
- 設定每小時、每日生成上限；超額回傳 `429`。
- 限制 prompt 長度、一次生成張數、圖片尺寸與衍生操作次數。
- 支援 idempotency key，避免重送或重整頁面造成重複計費。
- 記錄生成請求的時間、結果與計費用量，不記錄 Token。
- 在 GAI provider 帳戶設定可用的預算或用量警報；應理解警報不一定等同即時硬性停用，因此應用程式仍需自己的硬上限。

## 9. 網路、網域與 HTTPS

- 網域的 DNS A/AAAA record 指向 EC2 的固定公網位址；若使用 Elastic IP，要納入 IPv4 成本評估。
- Security Group 公開入站只允許 TCP 80、443。
- FastAPI 僅監聽 `127.0.0.1:8000`，不得直接公開 8000。
- Vite 開發 port、SQLite、內部圖片目錄均不得公開。
- 管理 EC2 優先使用 AWS Systems Manager Session Manager；若必須開 SSH 22，只允許固定管理 IP，不對全網開放。
- Nginx 終止 TLS，HTTP 全部轉向 HTTPS。
- 使用有效憑證並確認自動續期；正式上線前執行續期 dry run。
- CORS 只允許正式網域，不使用 `*` 搭配 credentials。

圖片不再由公開靜態目錄直接提供。現在 `/generated/images/{storage_key}` 會先由 FastAPI 驗證 Session、ownership、圖片狀態與到期時間，再以 `FileResponse` 傳送；過期、刪除、未登入或非擁有者均回傳 `404/401`。EC2 上線後可再改用 Nginx internal location／`X-Accel-Redirect` 傳送檔案，以保留相同驗證流程並降低 FastAPI 傳輸負擔。

## 10. 實作順序

### A. 資料層

- [x] 建立 SQLAlchemy ORM models。
- [x] 加入 Alembic migrations。
- [x] 建立 collections 與 image assets 多對多關聯。
- [x] 啟用 SQLite foreign keys、WAL、FULL synchronous 與 busy timeout。
- [x] 舊 JSON 已完成一次性匯入，匯入工具與舊 JSON 檔均已移除。
- [x] 聊天室與訊息改用 API，並直接捨棄舊 `localStorage` 聊天紀錄。
- [x] 圖片與收藏資料完全改用 SQLite，不再保留 JSON 資料來源。
- [x] generation job 保存 chatroom/exchange context，完成或失敗時由後端更新訊息與圖片關聯，並可處理訊息晚於 job 寫入的競態。

### B. 圖片儲存與生命週期

- [x] 建立 storage service，集中處理路徑、儲存、metadata 讀取及刪除。
- [ ] 將 storage root 設為 `/srv/totem-data/images`，不得硬編碼在 route。
- [x] 使用 UUID 檔名並驗證輸出 MIME、大小與尺寸。
- [x] 圖片 API 與 `/generated/images/{storage_key}` 加入 Session 驗證、ownership、刪除狀態及到期檢查。
- [x] 實作 `expires_at`、到期查詢及可重跑、預設 dry-run 的清理 job。
- [x] 建立 systemd cleanup service/timer，並由 EC2 部署腳本安裝及啟用 timer。
- [ ] 實作磁碟容量硬上限與剩餘空間檢查。
- [x] UI 顯示 14 天政策、個別圖片到期時間與下載提醒，並提供下載操作。

### C. 驗證與用量保護

- [x] 建立單一帳號 CLI 初始化方式，不提供公開註冊 endpoint。
- [ ] EC2 第一次部署時，以 `totem` 服務帳號執行 `python -m app.manage_user create` 建立正式商家帳號；後續更新不得重複初始化。
- [x] 加入 Argon2id 密碼 hash 與伺服器端 session；資料庫只保存 Session Token hash。
- [x] 加入 HttpOnly／SameSite Cookie、Origin-based CSRF 防護與登入失敗限流；正式環境須設定 Secure Cookie。
- [x] 除健康檢查、登入與開發文件外，所有非公開 API 及圖片檔案預設拒絕未登入請求，並驗證 ownership。
- [x] 建立生成工作狀態、idempotency、單帳號唯一 active job 與每小時／每日硬上限。
- [x] 盤點 `safe_print`、`print`、traceback 與 HTTP 錯誤回應，Log 僅允許 operation、job/image ID、狀態、錯誤類型、字數及數量等安全摘要。
- [x] 移除完整 Prompt、修改指令、完整 request body、圖片 URL 與 traceback Log。
- [x] 一般化對外 `500` 錯誤訊息，不回傳第三方 SDK 原始例外、內部檔案路徑或資料庫細節。
- [x] 確認程式不記錄 API Token、Session Token、Cookie、密碼或完整 request headers。
- [x] 新增 Log 安全自動測試，以敏感標記確認 stdout/stderr 與錯誤回應不洩漏內容。
- [x] 建置並掃描前端 production bundle、前端原始碼與公開資源，確認不存在 `OPENAI_API_KEY` 或疑似 API Token。
- [x] 掃描版本控制內檔案，確認 API Token 不存在 repository；`.env` 維持忽略且未被版本控制追蹤。

### D. AWS 與部署

- [ ] 建立 EC2、加密 EBS、固定公網位址及最小權限 Security Group。
- [ ] 設定 IMDSv2 required。
- [ ] 建立只允許讀取指定 Parameter Store secret 的 IAM instance role。
- [ ] 將 GAI Token 寫入 Parameter Store `SecureString`。
- [x] 後端支援使用 EC2 instance role 從指定 Region 的 Parameter Store 解密讀取 GAI Token；production 拒絕直接使用明文環境變數金鑰。
- [x] 部署腳本建立 `/srv/totem-data`、圖片及暫存目錄，並設定 `totem` 專用帳號與 `0750` 權限；`/opt/totem` 由第一次部署步驟建立。
- [ ] 安裝並設定 Nginx、FastAPI systemd service 與單一 worker。
- [ ] 設定正式 DNS、HTTPS 與憑證自動續期。
- [ ] 設定 systemd journal／Nginx log retention，避免無限增長。
- [ ] 建立 CPU、記憶體、磁碟和服務存活警報。
- [ ] 記錄「不備份」為正式接受的營運風險與負責人決策。

## 11. 上線前驗收

- [x] 本機驗收：未登入存取聊天室、圖片、收藏、生成與下載 API 均回傳 `401/403`。
- [x] 本機驗收：未登入直接輸入圖片 URL 無法取得圖片。
- [ ] 前端 production bundle 搜尋不到 API Token。
- [ ] EC2 對外掃描只有預期的 80/443；8000、5173、SQLite 不可連線。
- [ ] HTTP 強制轉 HTTPS，cookie 只在 HTTPS 傳送。
- [x] 本機驗收：登入暴力嘗試會回傳 `429`；生成 endpoint 的單一 active job 與每小時上限已有自動測試。
- [x] 自動測試確認相同 idempotency key 與同帳號並行請求不會建立第二個 active job。
- [ ] 測試資料設為已過期後，timer 能刪除聊天室、訊息、收藏關聯、metadata 與所有圖片檔案。
- [ ] 清理中途故意失敗後重跑，能完成且不誤刪其他路徑。
- [ ] 收藏中的圖片仍會在 14 天後刪除。
- [ ] 到期前下載功能可取得正確原圖。
- [ ] 磁碟達到安全門檻時，新生成被拒絕並顯示可理解訊息。
- [ ] 重新啟動 EC2 後，Nginx、FastAPI 與 cleanup timer 自動恢復。
- [ ] EC2 無法取得未授權的 Parameter Store parameters。
- [ ] log 中不存在 Token、session cookie 或完整敏感 request body。

## 12. 明確接受的限制

此方案合理且可執行，但選擇「不備份」代表正式接受：

- EC2/EBS 損壞、帳號誤操作或刪除 volume 時，最多 14 天內的所有資料可能立即永久遺失；
- `DeleteOnTermination=false` 只能降低誤終止風險，不是備份；
- 14 天清理程式若有錯誤也可能造成提前刪除，因此仍必須有路徑安全檢查與自動測試；
- 未來改為多商家、多台應用伺服器、不可停機或資料不可遺失時，需要重新評估 PostgreSQL/RDS、S3 與備份。

在上述限制確實可接受的前提下，這是目前需求最精簡且安全界線合理的部署方案。
