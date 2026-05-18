# 知識庫 Embedding 優化方案

## 📊 背景

根據實際測試（30 個查詢、1269 筆知識庫數據），發現在 embedding 中加入 answer 會**降低檢索匹配度**。

### 測試結果

```
總測試數: 30 個查詢

平均 Top 1 相似度:
  只用 Question:      0.5990
  Question + Answer:  0.5441
  差異: -0.0549 (-9.2%)  ❌

效果分布:
  Answer 有正面影響: 4 個  (13.3%)
  Answer 有負面影響: 26 個 (86.7%)  ← 大多數受負面影響
```

### 負面影響原因

1. **格式化內容稀釋語意**：answer 包含 markdown、emoji、步驟編號等格式
2. **操作步驟干擾**：「請到...」、「點選...」等行動指引與查詢語意不匹配
3. **無關資訊混入**：系統說明、注意事項等內容降低精準度

### 最嚴重的案例

| 查詢 | 只用 Question | Question + Answer | 降幅 |
|------|---------------|-------------------|------|
| 押金怎麼退還 | 0.9494 | 0.7114 | **-25.1%** |
| 押金要多少 | 0.7212 | 0.5409 | **-25.0%** |
| 押金什麼時候退 | 0.8476 | 0.6493 | **-23.4%** |

---

## ✅ 優化方案

### 策略調整

**舊策略（V2 初版）**：
```python
text = f"{question_summary} {answer[:200]}"
embedding = generate_embedding(text)
```

**新策略（V2 優化版）**：
```python
# 只使用 question_summary
text = question_summary
embedding = generate_embedding(text)

# keywords 獨立處理（透過 jieba 分詞匹配，不混入 embedding）
```

### 預期效果

- ✅ 檢索匹配度平均提升 **9.2%**
- ✅ 86.7% 的查詢效果改善
- ✅ 降低 embedding 成本（減少 ~70 字/筆的處理）
- ✅ 避免 answer 中無關內容的語意稀釋

---

## 🔧 已修改的檔案

### 1. 批次重新生成 Embedding

**檔案**: `scripts/regenerate_all_embeddings.py`

```python
# 修改前
answer = row['answer'][:200] if row['answer'] else ''
text = f"{question} {answer}"

# 修改後
text = question  # 只使用 question_summary
```

### 2. 知識庫匯入服務

**檔案**: `rag-orchestrator/services/knowledge_import_service.py`

```python
# 修改前
text = f"{knowledge['question_summary']} {knowledge['answer'][:200]}"

# 修改後
text = knowledge['question_summary']
```

### 3. Excel 匯入腳本

**檔案**: `scripts/knowledge_extraction/import_excel_to_kb.py`

```python
# 修改前（還包含 keywords）
keywords_str = ", ".join(knowledge['keywords']) if knowledge.get('keywords') else ""
text_for_embedding = f"{question_summary} {knowledge['answer'][:200]}"
if keywords_str:
    text_for_embedding = f"{text_for_embedding}. 關鍵字: {keywords_str}"

# 修改後（V2 架構：keywords 獨立處理）
text_for_embedding = question_summary
```

### 4. 提取資料匯入腳本

**檔案**: `scripts/knowledge_extraction/import_extracted_to_db.py`

```python
# 修改前（還包含 title 和 keywords）
keywords_str = ", ".join(keywords) if keywords else ""
embedding_text = f"{title} {question_summary} {answer[:200]}"
if keywords_str:
    embedding_text = f"{embedding_text}. 關鍵字: {keywords_str}"

# 修改後
embedding_text = question_summary
```

---

## 🚀 執行方式

### 方式 1: 背景執行（推薦）

```bash
# 使用提供的腳本（包含進度監控和日誌）
./scripts/regenerate_kb_embeddings_background.sh
```

腳本功能：
- ✅ 自動檢查 Docker 服務狀態
- ✅ 使用者確認提示
- ✅ 背景執行並產生日誌檔
- ✅ 提供即時監控指令

監控進度：
```bash
# 即時查看日誌
tail -f /tmp/regenerate_embeddings_*.log

# 檢查程序狀態
ps aux | grep regenerate_all_embeddings
```

### 方式 2: Docker 直接執行

```bash
# 進入 Docker 容器
docker-compose exec rag-orchestrator bash

# 執行腳本
python3 scripts/regenerate_all_embeddings.py
```

### 方式 3: nohup 手動背景執行

```bash
# 方法 A: 使用 docker-compose exec
nohup docker-compose exec -T rag-orchestrator \
  python3 scripts/regenerate_all_embeddings.py \
  > /tmp/regenerate_embeddings.log 2>&1 &

# 方法 B: 生產環境（使用 docker-compose.prod.yml）
nohup docker-compose -f docker-compose.prod.yml exec -T rag-orchestrator \
  python3 scripts/regenerate_all_embeddings.py \
  > /tmp/regenerate_embeddings.log 2>&1 &
```

監控日誌：
```bash
# 即時查看
tail -f /tmp/regenerate_embeddings.log

# 查看最後 100 行
tail -n 100 /tmp/regenerate_embeddings.log
```

---

## 📝 未來新增/編輯知識庫

所有知識庫的新增和編輯操作會自動使用新策略：

1. **Web UI 匯入** → 使用 `knowledge_import_service.py` ✅ 已更新
2. **Excel 匯入** → 使用 `import_excel_to_kb.py` ✅ 已更新
3. **提取數據匯入** → 使用 `import_extracted_to_db.py` ✅ 已更新
4. **批次重新生成** → 使用 `regenerate_all_embeddings.py` ✅ 已更新

---

## ⚠️ 注意事項

1. **SOP 不受影響**：SOP 的 embedding 策略不變（只使用 `item_name`）
2. **Keywords 仍然有效**：keywords 透過獨立機制（jieba 分詞）處理，提供 10-30% 的匹配度加成
3. **執行時間**：重新生成約需 10-15 分鐘（依知識庫數量而定）
4. **API 成本降低**：每筆減少 ~70 字的 embedding 處理

---

## 📈 效果驗證

重新生成完成後，可以執行測試驗證：

```bash
# 在 Docker 容器內執行
docker-compose exec rag-orchestrator python3 /tmp/test_answer_30_queries_fast.py
```

預期看到檢索相似度提升約 9.2%。

---

## 📚 相關文件

- [SOP Keywords 實作說明](features/sop/optimization/SOP_KEYWORDS_IMPLEMENTATION_2026-02-11.md)
- [SOP Keywords 對比分析](features/sop/optimization/SOP_KEYWORDS_COMPARISON.md)
- [測試腳本](../tests/test_sop_keywords_api.py)

---

**更新日期**: 2026-02-13
**測試數據**: 30 個查詢 × 1269 筆知識庫
**改善幅度**: 平均 +9.2% 檢索匹配度
