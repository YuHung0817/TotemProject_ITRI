# 架構決策

瀏覽器只連到 Nginx。Nginx 提供前端靜態檔，並把 `/api/*` 轉送到只監聽 localhost 的 FastAPI。目前是單一商家、資料只保留 14 天且不要求備份，因此第一版正式環境使用同一台 EC2 上的 SQLite 與本機圖片目錄，暫時不需要 RDS 或 S3。

- `api/v1`：保持 API 可演進。
- `services`：放商業規則，route 只處理 HTTP。
- `schemas`：放 API 輸入/輸出型別，不直接暴露 ORM model。
- `features`：前端依登入、商品、訂單等功能垂直切分。
- `.env`：本機設定；正式機密用 EC2 設定檔或 Parameter Store，不進 Git。

單一 EC2 足以支援目前需求。只有在需要多台後端、資料長期保存、備份或更高可用性時，才考慮加入 RDS、S3/CloudFront、Load Balancer；現有 service 與 ORM 分層可支援後續遷移。
