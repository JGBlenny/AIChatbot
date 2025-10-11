# 答案合成功能 - 快速總結

**狀態：** ✅ 已整合到 RAG Orchestrator，等待啟用

---

## 📍 如何啟用？

### 方式 1：修改 .env 檔案（推薦）

```bash
# 1. 編輯 .env 檔案
nano .env

# 2. 找到這一行並修改：
ENABLE_ANSWER_SYNTHESIS=false  →  ENABLE_ANSWER_SYNTHESIS=true

# 3. 儲存並重啟 RAG Orchestrator
docker-compose restart rag-orchestrator

# 4. 驗證配置已載入
docker-compose logs -f rag-orchestrator | grep "答案合成"
```

### 預期看到：
```
✅ LLM 答案優化器已初始化 (Phase 3 + 答案合成功能已啟用)
   合成閾值: 0.7
   合成來源數: 2-3
```

---

## 🧪 如何測試？

### 測試案例（應該觸發合成）

```bash
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "退租時押金要怎麼退還？需要什麼流程？",
    "vendor_id": 1,
    "mode": "tenant"
  }'
```

### 預期結果：

**日誌中看到：**
```
🔄 答案合成觸發：問題類型=True, 最高相似度=0.65 < 0.7
✨ 答案合成完成：使用了 3 個來源，tokens: 1138
```

**返回的答案：**
- ✅ 結構清晰（標題、步驟、注意事項）
- ✅ 完整性高（涵蓋多個來源的資訊）
- ✅ 無重複
- ✅ 易讀性好（Markdown 格式）

---

## 📊 配置位置

| 項目 | 位置 | 說明 |
|------|------|------|
| **環境變數** | `.env` 第 19-24 行 | 啟用/停用、閾值設定 |
| **初始化配置** | `rag-orchestrator/app.py` 第 66-81 行 | 載入環境變數 |
| **核心邏輯** | `rag-orchestrator/services/llm_answer_optimizer.py` | 合成功能實施 |
| **測試腳本** | `rag-orchestrator/tests/test_answer_synthesis.py` | 單元測試 |

---

## ⚙️ 可調整參數

| 參數 | 預設值 | 說明 | 調整建議 |
|------|--------|------|---------|
| `ENABLE_ANSWER_SYNTHESIS` | `false` | 是否啟用 | 測試時改為 `true` |
| `SYNTHESIS_THRESHOLD` | `0.7` | 觸發閾值 | 觸發太多？提高到 0.75<br>觸發太少？降低到 0.65 |
| `SYNTHESIS_MIN_RESULTS` | `2` | 最少結果數 | 通常不需調整 |
| `SYNTHESIS_MAX_RESULTS` | `3` | 最多合成來源 | 答案太長？減少到 2<br>不夠完整？增加到 4 |

---

## 🎯 觸發條件

答案合成會在以下**全部條件滿足**時觸發：

1. ✅ 功能已啟用（`ENABLE_ANSWER_SYNTHESIS=true`）
2. ✅ 問題包含複合需求關鍵字：
   - 「如何」、「怎麼」、「流程」、「步驟」
   - 「需要」、「什麼時候」、「注意」、「準備」、「辦理」
3. ✅ 至少有 2 個檢索結果
4. ✅ 最高相似度 < 0.7（沒有單一高分答案）

---

## ⚠️ 回測框架注意事項

### 回測時「不應該」使用答案合成

**原因：**
- 回測的目的是測試**知識庫本身**的品質
- 答案合成會掩蓋知識庫的問題
- 無法區分改善來自「知識庫優化」還是「LLM 補充」

**解決方案：**
即使 `.env` 中 `ENABLE_ANSWER_SYNTHESIS=true`，回測框架仍會**自動禁用**答案合成。

詳細說明請參考：`docs/ANSWER_SYNTHESIS_BACKTEST_GUIDE.md`

---

## 💰 成本估算

| 情境 | Tokens | 成本 |
|------|--------|------|
| 合成 2 個來源 | ~750 | ~$0.0003 |
| 合成 3 個來源 | ~1100 | ~$0.0005 |
| **每月（假設 10% 觸發）** | - | **~$1.2** |

---

## 📈 預期效果

| 指標 | 當前 | 預期 | 改善 |
|------|------|------|------|
| **完整性** | 2.92/5 | 3.5-4.0/5 | **+20-37%** |
| 綜合評分 | 3.42/5 | 3.8-4.0/5 | +11-17% |
| NDCG | 0.958 | 0.95+ | 維持 |

---

## ⏸️ 何時停用？

如果出現以下情況，建議停用：

- ❌ 答案品質反而變差
- ❌ 成本超出預算 2 倍以上
- ❌ 收到用戶負面反饋
- ❌ 頻繁出錯或超時

**停用方式：**
```bash
# 修改 .env
ENABLE_ANSWER_SYNTHESIS=true  →  ENABLE_ANSWER_SYNTHESIS=false

# 重啟服務
docker-compose restart rag-orchestrator
```

---

## 📚 完整文檔

1. **實施報告：** `docs/ANSWER_SYNTHESIS_IMPLEMENTATION.md`
2. **測試指南：** `docs/ANSWER_SYNTHESIS_TESTING_GUIDE.md`
3. **單元測試：** `rag-orchestrator/tests/test_answer_synthesis.py`

---

## 🚀 快速開始（3 步驟）

```bash
# 1. 啟用功能
sed -i '' 's/ENABLE_ANSWER_SYNTHESIS=false/ENABLE_ANSWER_SYNTHESIS=true/' .env

# 2. 重啟服務
docker-compose restart rag-orchestrator

# 3. 測試
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{"message": "退租時押金要怎麼退還？需要什麼流程？", "vendor_id": 1, "mode": "tenant"}'
```

---

**最後更新：** 2025-10-11
**狀態：** 等待啟用測試
**預計測試時長：** 1-2 週
