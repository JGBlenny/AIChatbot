# Ground-truth Research（jgb2 原始碼盤查結論）

各 spec 開發時對 jgb2 原始碼逐行盤查的定案結論（含 file:line 出處）——**系統斷言的真相依據**。
jgb2 持續演進；本目錄為「當時盤查」的證據快照，重大版更後如行為不符，先重盤再改斷言。

| 檔案 | 核心真相 |
|---|---|
| contract-…-research.md | 合約 12 狀態位元/4 階段、違約金 type、G1–G4 |
| billing-…-research.md | 滯納金兩機制、超商逢 5 撥付、發票開立時點、金流狀態機 |
| account-…-research.md | 帳號/團隊/權限、邀請機制 |
| iot-…-research.md | 台科電=DAE、電表機制、G 趨近零 |
| estate-…-research.md | 兩軸狀態模型（status×is_open）、刊登條件 |
| conversational-diagnosis-research.md | 合約診斷 v1 盤查（12 狀態首盤） |
| domain-…-research.md | 面向化架構定案（三層脈絡/候選辨識/中途切換） |
| sop-audience-isolation-research.md | 撤案 spec 的 jgb2 真相三題（金流支付枚舉/電費六模式/統編） |
| usage-metering / quota-management | 計量與額度的裁決紀錄 |

原開發位置 `.kiro/specs/<spec>/research.md`（開發史）；此處為定稿副本。
