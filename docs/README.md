# 文件目錄與維護規則

這個目錄提供開發、部署、維運、驗收與問題歷史文件。第一次接觸專案時，先讀 repository 根目錄的 `README.md`，再依工作類型進入對應文件。

## 現行文件

| 文件 | 唯一責任 | 主要讀者 |
| --- | --- | --- |
| [本機開發環境](local-development.md) | Windows 安裝、環境變數、migration、本機帳號、啟動與測試 | 開發者 |
| [EC2 部署](deployment.md) | 第一次建立正式環境，以及從本機版本發布至 EC2 | 部署人員 |
| [管理者維運手冊](operations-runbook.md) | 已上線 EC2 的服務、log、cleanup、密碼、DB 與故障處理 | 維運人員 |
| [專案完成度清單](project-readiness-checklist.md) | 唯一的現行未完成事項、必要性、優先級與完成證據 | 專案負責人 |

## 歷史封存

`archive/` 保存已被現行文件取代、但仍有決策背景價值的內容。封存文件不得再作為目前完成狀態或操作命令的主要依據。

| 文件 | 用途 |
| --- | --- |
| [早期 EC2 架構與實作規劃](archive/ec2-single-store-deployment-plan.md) | 保存單一商家 EC2 架構、安全設計、早期實作順序與驗收構想 |

## 應該修改哪份文件

| 變更類型 | 更新位置 |
| --- | --- |
| 更改本機安裝、啟動、migration 或測試方法 | `local-development.md` |
| 更改第一次 EC2 建置、正式環境設定或發布流程 | `deployment.md` |
| 更改 EC2 日常命令、資料風險決策、log、cleanup 或故障排除 | `operations-runbook.md` |
| 更改架構選擇或擴充條件 | 根目錄 `README.md` 的「系統架構」與「已知限制與未完成事項」 |
| 完成或新增待辦、驗收與風險決策 | `project-readiness-checklist.md` |
| 修正一個曾在實際使用中發生的問題 | 程式、對應自動測試與 Git commit；若仍待驗收，另更新 `project-readiness-checklist.md` |

## 避免重複的規則

1. 根目錄 `README.md` 放總覽、最短快速開始，以及本機與 EC2 共用的 API、安全、資料生命週期與環境變數規則；不複製完整操作手冊或逐項 UI 行為。
2. 本機 PowerShell 命令只以 `local-development.md` 為完整來源。
3. 第一次部署與版本發布以 `deployment.md` 為準。
4. 正式環境的日常維護命令以 `operations-runbook.md` 為準。
5. 只有 `project-readiness-checklist.md` 維護目前的 `[x]`、`[~]`、`[ ]` 與 `[N/A]` 狀態。
6. 歷史文件只保存背景，不同步維護現行狀態。
7. 若另一份文件需要相同內容，保留一至三句摘要並連到主要來源，不複製整段命令。
