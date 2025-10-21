# Scripts 目錄

此目錄包含項目的各種實用腳本和工具。

## 目錄結構

### `/scripts/` (根目錄)
生產環境使用的主要腳本：

- `import_sop_from_excel.py` - 從 Excel 導入 SOP 到資料庫
- `migrate_sop_to_templates.py` - 遷移 SOP 到新的範本架構
- `process_line_chats.py` - 處理 LINE 聊天記錄

### `/scripts/knowledge_extraction/`
知識提取相關的腳本：

- 知識庫提取工具
- 回測框架

### `/scripts/tools/`
開發和維護工具（預留目錄）

## 相關目錄

- `/database/seeds/` - SQL 種子數據文件
- `/tests/` - 測試腳本
- `/tests/deduplication/` - 去重檢測測試

## 使用說明

```bash
# 導入 SOP
python scripts/import_sop_from_excel.py

# 遷移 SOP 架構
python scripts/migrate_sop_to_templates.py

# 處理 LINE 聊天記錄
python scripts/process_line_chats.py
```
