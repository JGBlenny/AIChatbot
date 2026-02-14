# Markdown 知識庫使用指南

## 📚 概述

Markdown 知識庫生成器會將已批准的 LINE 對話轉換為結構化的 Markdown 檔案，用於：
1. 人類閱讀和分享
2. Git 版本控制
3. RAG 系統的資料來源

---

## 🔄 完整工作流程

```
1. LINE 對話匯入 → PostgreSQL
   ↓
2. AI 處理（品質評估、分類、清理）
   ↓
3. 人工審核批准
   ↓
4. 生成 Markdown 知識庫 ← 你現在在這裡
   ↓
5. 向量化並儲存（下一步）
   ↓
6. RAG 查詢系統使用
```

---

## 🚀 快速開始

### 1. 準備工作

確保你有已批准的對話：

```bash
# 檢查已批准對話數
curl http://localhost:8000/api/conversations/stats/summary
```

如果沒有，先執行：
```bash
python test_example.py  # 匯入並處理測試對話
```

### 2. 生成知識庫

```bash
# 方式 1: 使用測試腳本（推薦）
python test_knowledge.py

# 方式 2: 使用 API
curl -X POST "http://localhost:8000/api/knowledge/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "min_quality_score": 7,
    "only_approved": true
  }'
```

### 3. 查看生成的檔案

```bash
cd ../knowledge-base
ls -la

# 應該會看到：
# README.md           - 索引檔案
# 產品功能.md         - 產品功能分類
# 技術支援.md         - 技術支援分類
# 使用教學.md         - 使用教學分類
```

---

## 📖 API 使用

### 1. 生成完整知識庫

**端點**: `POST /api/knowledge/generate`

```bash
curl -X POST "http://localhost:8000/api/knowledge/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "categories": null,          // null = 所有分類
    "min_quality_score": 7,      // 最低品質分數
    "only_approved": true         // 僅已批准的對話
  }'
```

**回應**:
```json
{
  "success": true,
  "files_generated": ["產品功能.md", "技術支援.md"],
  "total_conversations": 15,
  "message": "成功生成 2 個知識庫檔案"
}
```

---

### 2. 生成特定分類

**端點**: `POST /api/knowledge/generate/{category}`

```bash
curl -X POST "http://localhost:8000/api/knowledge/generate/產品功能?min_quality_score=8"
```

---

### 3. 列出知識庫檔案

**端點**: `GET /api/knowledge/files`

```bash
curl http://localhost:8000/api/knowledge/files
```

**回應**:
```json
{
  "files": [
    {
      "filename": "產品功能.md",
      "category": "產品功能",
      "file_path": "/path/to/產品功能.md",
      "size_bytes": 5120,
      "conversations_count": 8,
      "last_updated": "2024-01-15T10:30:00"
    }
  ],
  "total": 3
}
```

---

### 4. 讀取檔案內容

**端點**: `GET /api/knowledge/files/{category}`

```bash
curl http://localhost:8000/api/knowledge/files/產品功能
```

**回應**:
```json
{
  "category": "產品功能",
  "filename": "產品功能.md",
  "content": "# 產品功能\n\n> **元數據**\n..."
}
```

---

### 5. 匯出單一對話

**端點**: `POST /api/knowledge/export/{conversation_id}`

```bash
curl -X POST "http://localhost:8000/api/knowledge/export/abc-123-def"
```

---

### 6. 知識庫統計

**端點**: `GET /api/knowledge/stats`

```bash
curl http://localhost:8000/api/knowledge/stats
```

**回應**:
```json
{
  "total_files": 3,
  "total_size_bytes": 15360,
  "total_size_mb": 0.015,
  "conversations_exported": 15,
  "conversations_approved": 15,
  "export_coverage": 100.0
}
```

---

### 7. 刪除知識庫檔案

**端點**: `DELETE /api/knowledge/files/{category}`

```bash
curl -X DELETE "http://localhost:8000/api/knowledge/files/產品功能"
```

---

## 📝 生成的 Markdown 格式

### 檔案結構

```markdown
# 產品功能

> **元數據**
> - 更新日期：2024-01-15 14:30:00
> - 資料筆數：8
> - 來源：LINE 對話整理
> - 標籤：登入, 功能, 設定

---

## 1. 如何重設密碼？

重設密碼的步驟如下：
1. 點選右上角『設定』
2. 選擇『帳戶安全』
3. 點擊『變更密碼』
4. 輸入新密碼並確認

> **上下文**：對話時間：2024-01-15 14:30

**標籤**：登入, 密碼, 帳戶
**來源**：對話 ID `abc-123-def`
**品質分數**：8/10
**信心度**：0.92

---

## 2. 如何上傳檔案？

上傳檔案很簡單：
1. 點選『上傳』按鈕
2. 選擇檔案（支援 PDF, JPG, PNG）
3. 點擊『確認上傳』即可

**標籤**：功能, 上傳
**來源**：對話 ID `def-456-ghi`
**品質分數**：9/10
**信心度**：0.95

---
```

### 索引檔案 (README.md)

```markdown
# AIChatbot 知識庫

> 更新時間：2024-01-15 14:30:00

## 📚 分類目錄

- [產品功能](./產品功能.md)
- [技術支援](./技術支援.md)
- [使用教學](./使用教學.md)

---

## 📖 使用說明

本知識庫由 AIChatbot 後台管理系統自動生成。
內容來源於 LINE 對話記錄，經過 AI 處理和人工審核。

### 資料格式

每個分類檔案包含：
- 問題和答案（Q&A 格式）
- 相關標籤
- 品質分數和信心度
- 來源追溯資訊

### 更新頻率

- 建議：每週更新一次
- 或當有新的已批准對話時手動觸發
```

---

## ⚙️ 配置選項

### 環境變數

在 `backend/.env` 中設定：

```env
# 知識庫輸出目錄
KNOWLEDGE_BASE_PATH=../knowledge-base
```

### 生成參數

```python
{
  "categories": ["產品功能", "技術支援"],  # 指定分類，null = 全部
  "min_quality_score": 7,                  # 最低品質分數（1-10）
  "only_approved": true                    # 僅已批准的對話
}
```

---

## 🔄 自動化生成

### 方式 1: 定時任務（Cron）

```bash
# 每天凌晨 2 點自動生成
0 2 * * * cd /path/to/backend && python -c "
import requests
requests.post('http://localhost:8000/api/knowledge/generate', json={
    'min_quality_score': 7,
    'only_approved': True
})
"
```

### 方式 2: Python 腳本

```python
# auto_generate.py
import requests
import schedule
import time

def generate_knowledge_base():
    response = requests.post(
        "http://localhost:8000/api/knowledge/generate",
        json={"min_quality_score": 7, "only_approved": True}
    )
    print(f"生成結果: {response.json()}")

# 每天凌晨 2 點執行
schedule.every().day.at("02:00").do(generate_knowledge_base)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 📊 使用場景

### 場景 1: 客服團隊分享

```bash
# 生成知識庫
python test_knowledge.py

# 壓縮並分享
cd ../knowledge-base
zip -r knowledge-base.zip *.md
# 發送給客服團隊
```

### 場景 2: Git 版本控制

```bash
cd ../knowledge-base
git init
git add *.md
git commit -m "初始知識庫"

# 每次更新後
git add *.md
git commit -m "更新：新增 5 筆 FAQ"
git push
```

### 場景 3: 靜態網站部署

```bash
# 使用 VitePress 或 Docusaurus
npm create vitepress@latest
# 將 knowledge-base/ 複製到 docs/
npm run docs:build
```

### 場景 4: RAG 系統使用

```python
# 讀取知識庫
from pathlib import Path

kb_path = Path("knowledge-base")
documents = []

for md_file in kb_path.glob("*.md"):
    with open(md_file, "r", encoding="utf-8") as f:
        content = f.read()
        documents.append({
            "category": md_file.stem,
            "content": content
        })

# 向量化並儲存（下一步）
```

---

## 🔍 品質控制

### 建議的品質分數門檻

| 用途 | 建議門檻 |
|------|---------|
| 內部參考 | ≥ 5 |
| 客服使用 | ≥ 7 |
| 公開文檔 | ≥ 8 |
| RAG 系統 | ≥ 7 |

### 檢查清單

生成前確認：
- ✅ 對話已經過 AI 處理
- ✅ 對話已經過人工審核
- ✅ 對話狀態為「已批准」
- ✅ 品質分數達到門檻
- ✅ 分類正確

---

## ❓ 常見問題

### Q1: 生成的檔案在哪裡？

**A**: `knowledge-base/` 目錄（專案根目錄下）

### Q2: 如何修改已生成的 Markdown？

**A**: 有兩種方式：
1. 直接編輯 MD 檔案（手動）
2. 修改資料庫中的對話 → 重新生成（推薦）

### Q3: 重新生成會覆蓋舊檔案嗎？

**A**: 是的，每次生成都會覆蓋同名檔案

### Q4: 如何只更新特定分類？

**A**: 使用分類生成 API：
```bash
curl -X POST "http://localhost:8000/api/knowledge/generate/產品功能"
```

### Q5: 可以自定義 MD 格式嗎？

**A**: 可以，編輯 `backend/app/services/markdown_generator.py` 的 `_format_markdown()` 方法

---

## 🚀 下一步

完成 Markdown 生成後：

1. ✅ Markdown 知識庫已建立
2. 📝 實作向量化服務（將 MD 轉為向量）
3. 🤖 建立 RAG 查詢 API
4. 🌐 整合到前台 AIChatbot

查看：[NEXT_STEPS.md](../NEXT_STEPS.md)

---

## 📞 技術支援

如有問題，請檢查：
- API 文件：http://localhost:8000/docs
- 專案文件：[PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md)
