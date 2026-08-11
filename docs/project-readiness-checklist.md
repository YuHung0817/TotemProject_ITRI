# 專案完成度與上線準備清單

最後盤點：2026-08-10

這份文件用來回答三個問題：這件事需不需要做、現在做到哪裡、如何證明真的完成。每次完成工作後，應同步更新「狀態」與「完成證據」，不要只修改程式而不更新清單。

## 狀態標記

- `[x]`：已完成，且已有可重複的驗證或正式環境證據。
- `[~]`：部分完成；已有實作，但仍缺自動化或正式環境驗收。
- `[ ]`：尚未完成。
- `[N/A]`：經確認目前不需要；必須在備註寫明原因與重新評估條件。

## 目前結論

核心功能、本機後端測試、靜態檢查與前端 production build 均可通過。現階段應優先完成正式環境驗收、監控告警與資料風險決策，再繼續擴充產品功能。目前採單人開發與人工部署前檢查，因此 CI 不列為上線必要條件。

### 2026-08-10 本機基準

- [x] 後端測試：`85 passed`。
- [x] 後端 Ruff：`All checks passed!`。
- [x] 前端 TypeScript 與 Vite production build：成功。
- [x] `.env` 已由 `.gitignore` 排除，且未被 Git 追蹤。
- [x] 上述檢查目前由開發者在每次 push 或部署前手動執行；現階段不導入 CI。

## P0：正式交付前必須完成

### 1. 完成正式環境安全與部署驗收

- 是否需要：需要。本機測試不能取代 DNS、TLS、Security Group、systemd 與 IAM 實機驗證。
- 目前狀態：[x] 已於 2026-08-11 完成正式 EC2 的網路、HTTPS、Cookie、服務重啟、Parameter Store／IAM、log、前端 bundle、generation job 恢復及手機實機驗收。
- 要做的事：
  - [x] 確認公網只能存取 80／443；22、8000、5173 與 SQLite 不可由公網連線。
  - [x] 確認 HTTP 一律轉向 HTTPS。
  - [x] 確認正式 Cookie 包含 `Secure`、`HttpOnly`、`SameSite=Strict`。
  - [x] 執行並記錄 `certbot renew --dry-run` 成功結果。
  - [x] EC2 重新啟動後，Nginx、FastAPI 與 cleanup timer 均會自動恢復。
  - [x] 確認 production 使用 SSM Parameter Store 與 instance role，環境檔沒有明文 OpenAI API key。
  - [x] 確認 IAM role 無法讀取未授權的 Parameter Store parameters。
  - [x] 搜尋 production journal 與 Nginx log，確認沒有 Token、Cookie、密碼、完整 Prompt、圖片內容或完整 request body。
  - [x] 確認正式前端 bundle 不含 API Token 或疑似秘密字串。
  - [x] 在實際 production 流程送出圖片生成後切換至其他頁面，再返回原聊天室；完成或失敗結果必須從既有 generation job 正確恢復，不顯示錯誤的 `Load failed`，也不得建立第二個付費請求。
  - [x] 使用實際手機驗收登入頁、聊天室、文化元素、我的圖片與圖片詳情頁；不需手動縮小、沒有水平溢出，且輸入框聚焦與返回頁面後縮放比例正常。
- 完成判定：逐項在正式 EC2 執行，記錄日期、執行者與結果。
- 完成證據：已記錄於本文件「正式環境驗收紀錄」。

### 2. 驗收資料到期、清理與磁碟保護

- 是否需要：需要。系統承諾 14 天保存政策，且圖片生成會產生成本及占用本機磁碟。
- 目前狀態：[x] cleanup service／timer、dry-run、到期下載、收藏期限、實體檔案刪除與磁碟容量保護均已驗收；另有 2 個無 DB 引用的舊 orphan PNG，專案負責人決定暫不處理並保留紀錄。
- 2026-08-11 production 唯讀盤點：177 個 DB asset key 均有對應檔案，但發現 2 個未列於 `image_assets` 的 PNG orphan files。全 DB 文字／JSON 欄位引用數均為 0，兩檔內容完全相同；已確認為磁碟殘留，安全隔離前不得直接永久刪除。
- 要做的事：
  - [x] 將測試資料設為已到期並執行 cleanup service，確認刪除聊天室、訊息、image records、assets、generation job、API usage 與所有對應圖片檔。
  - [x] 確認收藏關聯不會延長圖片保存期限：收藏頁顯示證明關聯已建立，`collection_assets.image_asset_id` 使用 `ON DELETE CASCADE`，且 production cleanup 已實測會刪除到期 asset 與實體檔案。
  - [x] 確認 cleanup timer 會自動觸發到期資料清理；2026-08-11 03:34 由 `safu-cleanup.timer` 觸發 service，成功清除到期 DB 資料與 3 個圖片檔。
  - [N/A] 目前不額外製造清理中途故障；現有自動測試已驗證 dry-run、重複執行、缺檔可重試及共用檔案保護，production 實測亦已成功。若未來改用多節點／外部儲存、清理曾實際中斷，或資料不可復原，再補故障注入測試。
  - [x] 確認收藏中的圖片仍依 14 天政策到期；收藏只建立分類關聯，不改變 image record／asset 的到期時間。
  - [x] 確認到期前可下載正確原圖，到期後無法再取得。
  - [x] 以獨立 production process 將磁碟保留比例暫時模擬為 101%，確認在建立 generation job 與呼叫付費 API 前回傳 `507 storage_capacity_reached`，且正式前端 bundle 包含安全中文提示。
  - [N/A] cleanup 失敗會由 systemd 留下 failed 狀態與 journal；目前決定不建立主動告警，改由人工檢查。若正式對外營運、使用者增加或停機不可接受，需改為告警並完成通知測試。
- 完成判定：測試環境與正式環境至少各完成一次；保存不含敏感資料的執行摘要。
- 完成證據：已記錄於本文件「正式環境驗收紀錄」。

### 3. 建立基本監控與告警

- 是否需要：主動告警目前不需要；log retention 仍需要。專案負責人接受以人工健康檢查處理故障，也接受故障可能不會立即被發現。
- 目前狀態：[x] CloudWatch／SNS 主動告警已決定暫不導入；systemd journal 使用內建動態容量限制，Nginx log 每日輪替、保留 14 份並壓縮，logrotate timer 已啟用。
- 要做的事：
  - [N/A] API health check 失敗告警。
  - [N/A] `safu-api` 停止或頻繁重啟告警。
  - [N/A] EC2 CPU 與記憶體告警。
  - [N/A] EBS 剩餘容量／使用率告警。
  - [N/A] HTTP 5xx 異常增加告警。
  - [N/A] cleanup timer 執行失敗告警。
  - [N/A] TLS 憑證即將到期告警。
  - [x] 確認 systemd journal 與 Nginx log retention：journal 目前 57.9 MB，root volume 15 GB／使用率 27%，採 systemd 內建動態容量限制；Nginx 每日輪替、保留 14 份、壓縮，logrotate timer 為 enabled／active。
- 完成判定：確認 systemd journal 與 Nginx log 均有容量或輪替上限。若未來啟用告警，每種告警至少觸發一次測試通知，確認負責人實際收得到。
- 重新評估條件：正式對外營運、使用者增加、需要即時得知故障，或停機時間不再可接受。
- 完成證據：主動告警決策與 2026-08-11 log retention 驗收結果已記錄。

### 4. 正式決定資料備份與復原政策

- 是否需要：需要做「決策」；是否實作長期備份則由產品風險決定。
- 目前狀態：[x] 專案負責人決定不保留正式 DB 或圖片備份，並接受 EC2／EBS 故障或誤刪後永久失去既有資料，改以重新部署、migration 與重建帳號恢復服務。
- 要做的事：
  - [N/A] 不保留每次部署前的短期 SQLite backup。
  - [x] 圖片完全不備份。
  - [N/A] 不設定備份保存位置、保存期限或定期刪除流程。
  - [N/A] 因不採用備份，不執行 restore 演練。
  - [x] 專案負責人接受 EC2／EBS 故障或誤刪時，14 天內資料、正式帳號與同機資料均可能永久遺失；`git pull` 只能恢復程式碼，恢復服務時仍需重建環境、migration 與帳號。
- 完成判定：已留下決策日期、負責角色、可接受損失範圍與重新評估條件。
- 目前決策：不建立正式 DB、圖片或跨主機備份；2026-08-11 cleanup 驗收期間建立的臨時 SQLite backup 已於驗收後移除。

## P1：建議在正式公開使用前完成

### 5. 補前端關鍵流程自動測試

- 是否需要：目前不需要。現階段為單人開發、單一商家，且部署前會人工驗收主要前端流程。
- 目前狀態：[N/A] 不導入前端測試框架或 `test` script。
- 目前替代流程：部署前人工驗收登入、Session、圖片生成狀態、聊天室恢復、商品預覽、常見錯誤中文提示、圖片下載與到期狀態。
- 重新評估條件：多人共同開發、前端修改頻率提高、開始公開給更多客戶使用，或曾發生人工驗收未發現的前端回歸。
- 屆時建議：使用 Vitest + Testing Library，並以 Playwright 建立至少一條登入到生成結果的 smoke test。

### 6. 固定並管理前端相依版本

- 是否需要：需要，但不是目前最優先事項。
- 目前狀態：[x] `package.json` 的所有直接 dependencies／devDependencies 已固定為目前 lockfile 的實際版本，乾淨執行 `npm ci` 與 production build 成功。
- 要做的事：
  - [x] React、React DOM、Vite、TypeScript、Vite React plugin 與型別套件均使用明確版本。
  - [x] 未來更新相依套件時使用獨立 commit 或 PR，並執行完整人工檢查。
  - [N/A] 現階段不建立定期自動更新；遇到安全公告或實際升級需求時個別評估，避免未驗證的大版本一次升級。
- 完成判定：刪除 `node_modules` 後執行 `npm ci` 與 build，結果一致且人工檢查通過。
- 完成證據：2026-08-11 執行乾淨 `npm ci` 成功，Vite 8.1.4 production build 成功。

### 7. 統一文件中的完成狀態

- 是否需要：需要。現行文件必須以 2026-08-11 正式環境驗收與營運決策為準。
- 目前狀態：[x] README、部署文件、維運手冊與 readiness checklist 已同步正式環境驗收、監控／備份決策、網域與 14 天期限。
- 要做的事：
  - [x] 以實際 EC2 驗收結果更新 `README.md`。
  - [x] `docs/archive/ec2-single-store-deployment-plan.md` 已明確標示為歷史封存，不維護現行完成狀態。
  - [x] 功能實作、正式驗收與 N/A 決策已明確區分。
  - [x] 文件中的日期、網域、保留期限與實際設定保持一致。
- 完成判定：同一事項在不同文件不再出現互相矛盾的狀態。
- 完成證據：2026-08-11 完成現行 Markdown 關鍵字、狀態、網域、期限、監控與備份決策交叉檢查。

## P2：符合條件時才需要

### 8. 建立持續整合（CI）

- 是否需要：目前不需要。
- 目前狀態：[N/A] 現階段為單人開發、單一商家，且每次 push 或部署前由開發者手動執行後端 `pytest`、`ruff check`、前端 `npm ci` 與 `npm run build`。
- 重新評估條件：多人共同開發、更新或部署頻率提高、需要 Pull Request 合併保護，或曾因漏跑檢查而造成回歸或部署問題。
- 屆時要做：建立 GitHub Actions，在 Push 與 Pull Request 自動執行後端測試、Ruff 與前端 production build，任一步驟失敗時阻止合併或部署。

### 9. 將同步圖片生成改成背景工作佇列

- 是否需要：目前不一定需要。
- 目前狀態：[N/A] 現況採同步生成、單一 worker 與 300 秒 proxy timeout，對單一商家低流量模式可接受。
- 重新評估條件：生成經常超時、同時使用者增加、需要取消／重試工作、部署期間不能中斷生成，或等待中的請求開始占滿服務能力。
- 屆時要做：採用持久化 queue／worker，讓 API 快速回傳 job ID，並維持既有 idempotency、額度與 ownership 規則。

### 10. 將登入限流移出 process memory

- 是否需要：目前不一定需要。
- 目前狀態：[N/A] 登入失敗紀錄儲存在單一 backend process 記憶體；服務重啟會歸零。現行單 worker、單商家模式可暫時接受。
- 重新評估條件：改成多 worker／多台主機、對外公開登入、遭遇持續暴力嘗試，或需要跨重啟保留封鎖狀態。
- 屆時要做：改用資料庫、Redis 或邊界層 rate limiting，並正確處理可信 proxy 與來源 IP。

### 11. 遷移 PostgreSQL、S3 或多節點架構

- 是否需要：目前不需要。
- 目前狀態：[N/A] 單一商家、單 worker、14 天保存及可接受停機的前提下，SQLite 與加密 EBS 足夠。
- 重新評估條件：多商家、多 worker、多 EC2、長期保存、不可停機、資料不可遺失或圖片量明顯增加。

### 12. 圖形化管理後台與自助密碼重設

- 是否需要：目前不是上線阻擋項。
- 目前狀態：[N/A] 已有 CLI 帳號初始化與維運流程，適用單一商家模式。
- 重新評估條件：帳號數量增加、非技術管理者需要自行管理，或密碼重設頻率提高。

## 建議執行順序

1. [x] 在正式 EC2 完成安全、HTTPS、IAM、重啟與 log 驗收。
2. [x] 完成清理、到期下載與磁碟不足情境驗收。
3. [x] 確認 systemd journal 與 Nginx log retention；目前不導入主動告警。
4. [x] 確認備份／不備份決策及負責人。
5. [N/A] 目前不補前端自動測試，部署前採人工驗收。
6. [x] 固定前端依賴版本。
7. [x] 依實測結果同步所有文件狀態。

## 正式環境驗收紀錄

每次驗收新增一列。不要在這裡貼 Token、Cookie、完整環境檔或其他秘密。

| 日期 | 環境／版本 | 執行者 | 驗收範圍 | 結果 | 證據或備註 |
| --- | --- | --- | --- | --- | --- |
| 2026-08-11 | production／版本待補 | 專案負責人 | Security Group、公網 TCP 連線、HTTP 轉址 | 通過 | Security Group 僅允許 inbound 80／443；外部測試 80／443 可連線，22／8000／5173 不可連線；HTTP 回傳 301 並轉向 `https://safu-studio.com/`。 |
| 2026-08-11 | production／版本待補 | 專案負責人 | Session Cookie 安全屬性 | 通過 | `safu_session` 的 Path 為 `/`，並已啟用 `HttpOnly`、`Secure`、`SameSite=Strict`；驗收截圖不作為 repository 附件。 |
| 2026-08-11 | production／版本待補 | 專案負責人 | TLS 憑證模擬續期 | 通過 | `sudo certbot renew --dry-run` 成功；`safu-studio.com` 的模擬續期完成。 |
| 2026-08-11 | production／版本待補 | 專案負責人 | EC2 重啟與服務自動恢復 | 通過 | 重啟後 `safu-api`、`nginx`、`safu-cleanup.timer` 均為 active；cleanup timer 已重新排程；正式 health check 回傳 `{"status":"ok"}`。 |
| 2026-08-11 | production／版本待補 | 專案負責人 | Parameter Store 與 IAM 最小權限 | 通過 | Production 使用 instance role 與 Parameter Store，環境檔未保存明文 OpenAI API key；自訂政策只允許 `ssm:GetParameter`，Resource 精確限制為 `/safu/production/openai-api-key`，未使用 wildcard。 |
| 2026-08-11 | production／版本待補 | 專案負責人 | Production journal 與 Nginx log 敏感資料檢查 | 通過 | Nginx 未出現敏感關鍵字；journal 的 `prompt` 紀錄僅包含字數／狀態，未記錄完整 Prompt；query string 未包含 Token、Cookie、密碼、API key、Prompt 或 session。 |
| 2026-08-11 | production／版本待補 | 專案負責人 | 正式前端 bundle 秘密掃描 | 通過 | 疑似 OpenAI／AWS／Bearer 金鑰格式、敏感環境變數名稱及誤打包環境檔的搜尋結果均為 0。 |
| 2026-08-11 | production／版本待補 | 專案負責人 | 生成期間切頁與既有 job 恢復 | 通過 | 切頁返回後畫面正確恢復，未出現 `Load failed` 或重複結果；重試收到 `409 generation_in_progress` 後接手既有 job，未建立第二個付費請求。 |
| 2026-08-11 | production／版本待補 | 專案負責人 | 手機實機主要頁面與響應式版面 | 通過 | 登入頁、聊天室、文化元素、我的圖片及圖片詳情頁均正常；鍵盤聚焦、縮放比例、直橫向切換及水平溢出檢查通過。 |
| 2026-08-11 | production／版本待補 | 專案負責人 | Production 到期資料與實體圖片清理 | 通過 | 唯一測試聊天室含 2 則訊息、4 筆 image records、8 筆 assets／檔案、1 個 generation job、1 筆 API usage；dry-run 與 execute 數量一致。清理後 dry-run 全為 0，DB asset keys 與磁碟檔案均減少 8，`missing_active_files=0`；前端確認聊天室與圖片均消失，到期前下載成功、到期後不可再取得。收藏頁實測可建立收藏關聯，schema 以 `ON DELETE CASCADE` 維持關聯清理，收藏不延長 14 天期限；另有 2 個既知舊 orphan files 暫不處理。 |
| 2026-08-11 | production／版本待補 | 專案負責人 | cleanup timer 自動執行 | 通過 | `TriggeredBy=safu-cleanup.timer`；timer 於 03:34 自動啟動 service，清除 1 筆 image record、3 筆 assets／檔案、1 個 generation job 與 1 筆 API usage，systemd 回報成功完成。 |
| 2026-08-11 | production／版本待補 | 專案負責人 | 磁碟容量不足保護 | 通過 | 獨立 production process 將 `IMAGE_MIN_FREE_PERCENT` 暫時設為 101%，容量檢查回傳 `507 storage_capacity_reached` 與安全中文訊息；正式 bundle 搜尋命中 1 個提示字串。測試未修改正式環境檔、未建立 generation job，亦未呼叫付費 API。 |
| 2026-08-11 | production／版本待補 | 專案負責人 | Log retention | 通過 | systemd journal 使用量 57.9 MB，root volume 15 GB／使用率 27%，採內建動態容量限制；Nginx log 設為 daily、rotate 14、compress／delaycompress，`logrotate.timer` 為 enabled／active。 |

## 決策紀錄

| 日期 | 決策 | 結果 | 負責角色 | 重新評估條件 |
| --- | --- | --- | --- | --- |
| 2026-08-11 | 是否建立正式備份 | 不建立；接受資料永久遺失後重新部署、migration 與重建帳號 | 專案負責人 | 多商家、長期保存、資料不可遺失，或風險承受度改變 |
| 2026-08-10 | 是否立即導入背景 queue | 暫不導入 | 專案負責人 | 超時、並行量或可靠性需求增加 |
| 2026-08-10 | 是否立即遷移 PostgreSQL／S3 | 暫不遷移 | 專案負責人 | 多節點、長期保存或不可接受資料遺失 |
| 2026-08-11 | 是否建立 CloudWatch／SNS 主動告警 | 暫不建立，接受人工檢查與延遲發現故障 | 專案負責人 | 正式對外營運、使用者增加、需要即時得知故障，或停機不可接受 |
| 2026-08-11 | 是否建立前端自動測試 | 暫不建立，部署前採人工驗收 | 專案負責人 | 多人開發、修改頻率提高、公開使用者增加，或曾發生前端回歸 |
