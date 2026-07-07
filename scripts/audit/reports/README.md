# 盤查報告與可重放批次索引

## 報告（證據鏈，含 file:line 可追溯）
| 檔案 | 內容 |
|---|---|
| `jgb-knowledge-audit-20260706.md` | JGB 知識盤查：17 斷言對 jgb2 原始碼、行為基準 38.3%→68.3% 軌跡、掛帳清單、範疇外裁定 |
| `vendor-sop-audit-20260706.md` | 業者設定與 SOP 邏輯盤查：參數雙軌真相、分工定案與反轉全紀錄、vendor 資料疑慮（污染/假值） |

## 可重放批次（prod 部署依賴，runbook §1 引用）
| 檔案 | 用途 |
|---|---|
| `knowledge-corrections-20260706.json` | 錯誤知識修正 5 筆（已固化於 audit_20260706_knowledge_fixes.sql，此檔為審核紀錄） |
| `knowledge-additions-20260706.json` | 檢索補強 2 筆的審核紀錄 |
| `audit-additions-import.json` | 檢索補強 import 批次（工具可直接重放） |
| `gap-batch-import.json` | 缺口 3 主題 import 批次 |
| `lookup-anchors-import.py` | lookup 案場級錨點重放腳本（需 embedding-api） |
