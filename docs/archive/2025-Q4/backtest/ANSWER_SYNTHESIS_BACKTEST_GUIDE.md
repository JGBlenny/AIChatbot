# 答案合成與回測框架 - 使用指南

**更新日期：** 2025-10-11
**狀態：** ✅ 已實施動態控制功能

---

## 📋 核心原則

### 回測框架「不應該」使用答案合成

**原因：**
- ✅ 回測的目的是測試**知識庫本身**的品質
- ✅ 需要真實評估檢索結果，而非 LLM 合成的答案
- ✅ 避免混淆改善來源（知識庫優化 vs LLM 補充）

**解決方案：**
- 即使 `.env` 中 `ENABLE_ANSWER_SYNTHESIS=true`
- 回測時仍然可以**動態禁用**答案合成

---

## 🔧 技術實現

### 新增參數：`enable_synthesis_override`

在 `LLMAnswerOptimizer.optimize_answer()` 方法中新增參數：

```python
def optimize_answer(
    self,
    question: str,
    search_results: List[Dict],
    confidence_level: str,
    intent_info: Dict,
    vendor_params: Optional[Dict] = None,
    vendor_name: Optional[str] = None,
    enable_synthesis_override: Optional[bool] = None  # 新增參數
) -> Dict:
```

**參數說明：**
- `None` (預設)：使用配置檔案的設定
- `True`：強制啟用答案合成（無視配置）
- `False`：強制禁用答案合成（無視配置）

---

## 🧪 使用方式

### 1. 回測框架（禁用答案合成）

即使 `.env` 中 `ENABLE_ANSWER_SYNTHESIS=true`，回測時仍然禁用：

```python
# 回測框架中呼叫 LLM 優化器
optimization_result = llm_optimizer.optimize_answer(
    question=question,
    search_results=search_results,
    confidence_level='high',
    intent_info=intent_result,
    enable_synthesis_override=False  # ⭐ 強制禁用答案合成
)
```

**效果：**
- ✅ 答案合成不會觸發
- ✅ 只使用傳統優化模式
- ✅ 真實評估知識庫品質

---

### 2. 生產環境（使用配置）

生產環境不傳入 `enable_synthesis_override`，使用配置檔案的設定：

```python
# Chat API 中呼叫 LLM 優化器
optimization_result = llm_optimizer.optimize_answer(
    question=request.message,
    search_results=search_results,
    confidence_level='high',
    intent_info=intent_result,
    vendor_params=vendor_params,
    vendor_name=vendor_name
    # 不傳 enable_synthesis_override，使用配置
)
```

**效果：**
- ✅ 依照 `.env` 中 `ENABLE_ANSWER_SYNTHESIS` 的設定
- ✅ 啟用時可提升答案完整性
- ✅ 停用時使用傳統優化

---

### 3. 灰度測試（強制啟用）

即使 `.env` 中 `ENABLE_ANSWER_SYNTHESIS=false`，也可以強制啟用：

```python
# 灰度測試：特定問題強制啟用答案合成
optimization_result = llm_optimizer.optimize_answer(
    question=question,
    search_results=search_results,
    confidence_level='high',
    intent_info=intent_result,
    enable_synthesis_override=True  # ⭐ 強制啟用答案合成
)
```

---

## 📊 決策矩陣

| 情境 | `.env` 配置 | `enable_synthesis_override` | 實際行為 | 用途 |
|------|------------|----------------------------|---------|------|
| **回測框架** | `true` | `False` | ❌ 不合成 | 測試知識庫 |
| **回測框架** | `false` | `False` | ❌ 不合成 | 測試知識庫 |
| **生產環境** | `true` | `None` | ✅ 合成 | 提升體驗 |
| **生產環境** | `false` | `None` | ❌ 不合成 | 傳統模式 |
| **灰度測試** | `false` | `True` | ✅ 合成 | 測試功能 |
| **特殊測試** | `true` | `True` | ✅ 合成 | 強制啟用 |

---

## 🔬 測試驗證

執行測試腳本驗證功能：

```bash
python3 rag-orchestrator/tests/test_synthesis_override.py
```

**預期結果：**
```
【測試 1】配置啟用 + 沒有覆蓋
預期：應該觸發合成 (True)
實際：True
結果：✅ PASS

【測試 2】配置啟用 + 覆蓋為 False（回測模式）
預期：不應該觸發合成 (False)
實際：False
結果：✅ PASS

【測試 3】配置停用 + 覆蓋為 True（強制啟用）
預期：應該觸發合成 (True)
實際：True
結果：✅ PASS

【測試 4】配置停用 + 沒有覆蓋
預期：不應該觸發合成 (False)
實際：False
結果：✅ PASS
```

---

## 📝 實施清單

### 已完成 ✅

- [x] 新增 `enable_synthesis_override` 參數
- [x] 修改 `_should_synthesize()` 方法支援覆蓋
- [x] 創建測試腳本 `test_synthesis_override.py`
- [x] 測試通過（4/4 PASS）
- [x] 文檔撰寫

### 待完成 ⏸️

- [ ] 修改回測框架，傳入 `enable_synthesis_override=False`
- [ ] 修改 Chat API，確保生產環境不傳 `enable_synthesis_override`
- [ ] 執行回測驗證功能
- [ ] 更新 `ANSWER_SYNTHESIS_SUMMARY.md`

---

## 🚀 下一步行動

### 步驟 1：修改回測框架

**檔案：** `scripts/knowledge_extraction/backtest_framework.py`

在 `query_rag_system()` 方法中，確保回測時禁用答案合成：

```python
# 方式 1：在回測 API payload 中添加參數（推薦）
payload = {
    "message": question,
    "vendor_id": self.vendor_id,
    "mode": "tenant",
    "include_sources": True,
    "disable_answer_synthesis": True  # ⭐ 回測時禁用
}
```

或者：

```python
# 方式 2：在 Chat API 中檢查請求來源
# 如果檢測到 disable_answer_synthesis=True，傳入 enable_synthesis_override=False
```

---

### 步驟 2：驗證回測

```bash
# 1. 啟用答案合成（在配置中）
sed -i '' 's/ENABLE_ANSWER_SYNTHESIS=false/ENABLE_ANSWER_SYNTHESIS=true/' .env
docker-compose restart rag-orchestrator

# 2. 執行回測（應該仍然禁用答案合成）
BACKTEST_QUALITY_MODE=basic \
BACKTEST_TYPE=smoke \
BACKTEST_SAMPLE_SIZE=3 \
BACKTEST_NON_INTERACTIVE=true \
PROJECT_ROOT=/Users/lenny/jgb/AIChatbot \
python3 scripts/knowledge_extraction/backtest_framework.py

# 3. 檢查日誌，應該沒有「答案合成觸發」的訊息
docker-compose logs rag-orchestrator | grep -E "合成|synthesis"
```

---

## 💡 總結

### 核心價值

這個動態控制機制解決了一個關鍵問題：

**問題：**
- ❌ 如果全局啟用答案合成，回測結果會失真
- ❌ 如果全局禁用答案合成，無法測試生產功能

**解決：**
- ✅ 生產環境：依照配置啟用/禁用
- ✅ 回測框架：強制禁用（測試真實知識庫）
- ✅ 灰度測試：選擇性啟用（測試特定案例）

### 設計原則

1. **配置優先**：預設使用 `.env` 配置
2. **動態覆蓋**：特殊情況可以覆蓋配置
3. **向後相容**：不傳參數時行為不變
4. **清晰意圖**：參數名稱明確表達用途

---

**最後更新：** 2025-10-11
**版本：** v1.1 (新增動態控制功能)
