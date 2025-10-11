# 回測框架答案合成禁用 - 實施完成

**實施日期：** 2025-10-11
**狀態：** ✅ 已完成
**版本：** v1.0

---

## 🎯 問題與解決方案

### 問題

當 `.env` 中 `ENABLE_ANSWER_SYNTHESIS=true` 時，回測框架也會使用答案合成功能，導致：
- ❌ 無法真實評估知識庫品質
- ❌ LLM 自動補充掩蓋知識庫缺陷
- ❌ 混淆改善來源（知識庫 vs LLM 合成）

### 解決方案

創建專用參數 `BACKTEST_DISABLE_ANSWER_SYNTHESIS`，使回測與生產配置分離：
- ✅ 回測框架：專用參數控制（禁用答案合成）
- ✅ 生產環境：使用 `ENABLE_ANSWER_SYNTHESIS` 配置
- ✅ 配置獨立：互不影響

---

## 📋 實施內容

### Phase 1: 回測框架修改 ✅

**文件：** `scripts/knowledge_extraction/backtest_framework.py`

**修改內容：** 在 `query_rag_system()` 方法中讀取環境變數並傳遞給 API

```python
def query_rag_system(self, question: str) -> Dict:
    """查詢 RAG 系統"""
    url = f"{self.base_url}/api/v1/message"

    payload = {
        "message": question,
        "vendor_id": self.vendor_id,
        "mode": "tenant",
        "include_sources": True
    }

    # ⭐ 回測專用：檢查是否禁用答案合成
    disable_synthesis = os.getenv("BACKTEST_DISABLE_ANSWER_SYNTHESIS", "false").lower() == "true"
    if disable_synthesis:
        payload["disable_answer_synthesis"] = True
        # 只在第一次請求時顯示提示
        if not hasattr(self, '_synthesis_disabled_logged'):
            print("   ⚙️  回測模式：答案合成已禁用（BACKTEST_DISABLE_ANSWER_SYNTHESIS=true）")
            self._synthesis_disabled_logged = True

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"   ❌ API 請求失敗: {e}")
        return None
```

**關鍵點：**
- 讀取 `BACKTEST_DISABLE_ANSWER_SYNTHESIS` 環境變數
- 如果為 `true`，在 API payload 中添加 `disable_answer_synthesis: True`
- 首次請求時顯示日誌提示

---

### Phase 2: Chat API 修改 ✅

**文件：** `rag-orchestrator/routers/chat.py`

#### 2.1 請求模型新增欄位

**位置：** Line 389

```python
class VendorChatRequest(BaseModel):
    """多業者聊天請求"""
    message: str = Field(..., description="使用者訊息", min_length=1, max_length=2000)
    vendor_id: int = Field(..., description="業者 ID", ge=1)
    mode: str = Field("tenant", description="模式：tenant (B2C) 或 customer_service (B2B)")
    session_id: Optional[str] = Field(None, description="會話 ID（用於追蹤）")
    user_id: Optional[str] = Field(None, description="使用者 ID（租客 ID 或客服 ID）")
    top_k: int = Field(3, description="返回知識數量", ge=1, le=10)
    include_sources: bool = Field(True, description="是否包含知識來源")
    disable_answer_synthesis: bool = Field(False, description="禁用答案合成（回測模式專用）")  # ⭐ NEW
```

#### 2.2 修改所有 `optimize_answer()` 呼叫

**三個呼叫位置：**

1. **Unclear 意圖 RAG fallback**（Line 477-485）
2. **已知意圖 RAG fallback**（Line 596-603）
3. **主要知識檢索**（Line 675-683）

**統一修改模式：**

```python
optimization_result = llm_optimizer.optimize_answer(
    question=request.message,
    search_results=search_results,
    confidence_level='high',
    intent_info=intent_result,
    vendor_params=vendor_params,
    vendor_name=vendor_info['name'],
    enable_synthesis_override=False if request.disable_answer_synthesis else None  # ⭐ ADD
)
```

**邏輯說明：**
- 如果 `request.disable_answer_synthesis == True`（回測模式）
  - 傳入 `enable_synthesis_override=False`
  - 強制禁用答案合成
- 如果 `request.disable_answer_synthesis == False`（生產模式）
  - 傳入 `enable_synthesis_override=None`
  - 使用 `.env` 配置

---

## 🧪 使用方式

### 1. 回測模式（禁用答案合成）

```bash
# 設定環境變數
export BACKTEST_DISABLE_ANSWER_SYNTHESIS=true

# 執行回測
BACKTEST_QUALITY_MODE=basic \
BACKTEST_TYPE=smoke \
BACKTEST_SAMPLE_SIZE=3 \
BACKTEST_NON_INTERACTIVE=true \
PROJECT_ROOT=/Users/lenny/jgb/AIChatbot \
python3 scripts/knowledge_extraction/backtest_framework.py
```

**預期日誌：**
```
⚙️  回測模式：答案合成已禁用（BACKTEST_DISABLE_ANSWER_SYNTHESIS=true）
```

**驗證：**
```bash
# 檢查 RAG Orchestrator 日誌，應該沒有「答案合成觸發」的訊息
docker-compose logs rag-orchestrator | grep -E "合成|synthesis"
```

---

### 2. 生產模式（使用配置）

**方式 1：啟用答案合成**
```bash
# .env
ENABLE_ANSWER_SYNTHESIS=true

# 重啟服務
docker-compose restart rag-orchestrator
```

**方式 2：禁用答案合成**
```bash
# .env
ENABLE_ANSWER_SYNTHESIS=false

# 重啟服務
docker-compose restart rag-orchestrator
```

---

## 📊 決策矩陣

| 模式 | `ENABLE_ANSWER_SYNTHESIS` | `BACKTEST_DISABLE_ANSWER_SYNTHESIS` | API `disable_answer_synthesis` | 實際行為 |
|------|--------------------------|-----------------------------------|-------------------------------|---------|
| **生產** | `true` | - | `False` (預設) | ✅ 合成 |
| **生產** | `false` | - | `False` (預設) | ❌ 不合成 |
| **回測** | `true` | `true` | `True` | ❌ 不合成 |
| **回測** | `false` | `true` | `True` | ❌ 不合成 |
| **回測** | `true` | `false` | `False` | ✅ 合成（不建議）|

---

## ✅ 驗證清單

### 已完成

- [x] 修改 `backtest_framework.py` 讀取環境變數
- [x] 修改 `VendorChatRequest` 模型新增 `disable_answer_synthesis` 欄位
- [x] 修改第一個 `optimize_answer()` 呼叫（Line 477-485）
- [x] 修改第二個 `optimize_answer()` 呼叫（Line 596-603）
- [x] 修改第三個 `optimize_answer()` 呼叫（Line 675-683）
- [x] 撰寫實施文檔

### 待測試

- [ ] 執行回測驗證答案合成已禁用
- [ ] 驗證生產環境仍然正常使用配置
- [ ] 測試兩種模式可以獨立運行

---

## 🚀 測試步驟

### 測試 1：回測禁用答案合成

```bash
# 1. 啟用生產環境的答案合成
sed -i '' 's/ENABLE_ANSWER_SYNTHESIS=false/ENABLE_ANSWER_SYNTHESIS=true/' .env
docker-compose restart rag-orchestrator

# 2. 驗證生產環境啟用成功
docker-compose logs rag-orchestrator | grep "答案合成功能已啟用"

# 3. 設定回測禁用
export BACKTEST_DISABLE_ANSWER_SYNTHESIS=true

# 4. 執行回測
BACKTEST_QUALITY_MODE=basic \
BACKTEST_TYPE=smoke \
BACKTEST_SAMPLE_SIZE=3 \
BACKTEST_NON_INTERACTIVE=true \
PROJECT_ROOT=/Users/lenny/jgb/AIChatbot \
python3 scripts/knowledge_extraction/backtest_framework.py

# 5. 檢查日誌：應該看到「回測模式：答案合成已禁用」
# 6. 檢查日誌：不應該看到「答案合成觸發」
docker-compose logs rag-orchestrator | grep -E "合成觸發|synthesis triggered"
```

**預期結果：**
- ✅ 回測提示：「回測模式：答案合成已禁用」
- ✅ 沒有「答案合成觸發」的日誌
- ✅ 回測結果反映真實知識庫品質

---

### 測試 2：生產環境正常使用配置

```bash
# 1. 確保回測變數未設定或為 false
unset BACKTEST_DISABLE_ANSWER_SYNTHESIS

# 2. 設定生產環境啟用答案合成
sed -i '' 's/ENABLE_ANSWER_SYNTHESIS=false/ENABLE_ANSWER_SYNTHESIS=true/' .env
docker-compose restart rag-orchestrator

# 3. 測試生產 API
curl -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "退租時押金要怎麼退還？需要什麼流程？",
    "vendor_id": 1,
    "mode": "tenant"
  }'

# 4. 檢查日誌：應該看到答案合成觸發
docker-compose logs rag-orchestrator | tail -50 | grep -E "合成觸發|答案合成完成"
```

**預期結果：**
- ✅ 看到「答案合成觸發」日誌
- ✅ 看到「答案合成完成」日誌
- ✅ 返回結構化的合成答案

---

## 💡 技術亮點

### 1. 配置分離

**問題：** 單一 `ENABLE_ANSWER_SYNTHESIS` 變數無法區分生產與回測
**解決：** 創建專用 `BACKTEST_DISABLE_ANSWER_SYNTHESIS` 變數

### 2. 動態覆蓋

**利用現有機制：** `enable_synthesis_override` 參數（已在 Phase 1 實施）
**實現：**
```python
enable_synthesis_override=False if request.disable_answer_synthesis else None
```

### 3. 向後相容

**預設行為不變：** `disable_answer_synthesis` 預設為 `False`
**無破壞性：** 現有 API 呼叫不受影響

### 4. 清晰語義

**參數命名明確：**
- `BACKTEST_DISABLE_ANSWER_SYNTHESIS` → 明確表示回測專用
- `disable_answer_synthesis` → 明確表示禁用意圖

---

## 📚 相關文檔

| 文檔 | 說明 |
|------|------|
| `ANSWER_SYNTHESIS_BACKTEST_SOLUTION.md` | 完整解決方案總結 |
| `ANSWER_SYNTHESIS_BACKTEST_GUIDE.md` | 使用指南與決策矩陣 |
| `ANSWER_SYNTHESIS_SUMMARY.md` | 快速啟用指南 |
| `ANSWER_SYNTHESIS_IMPLEMENTATION.md` | 完整實施報告 |
| `BACKTEST_ANSWER_SYNTHESIS_IMPLEMENTATION_COMPLETE.md` | 本文檔 |

---

## 🎉 總結

### 核心價值

**之前的問題：**
- ❌ 回測受答案合成影響，結果失真
- ❌ 無法區分知識庫品質 vs LLM 補充
- ❌ 需要反覆修改 `.env` 才能切換模式

**現在的解決：**
- ✅ 回測與生產配置完全分離
- ✅ 回測專用參數控制答案合成
- ✅ 真實評估知識庫品質
- ✅ 生產環境不受影響

### 設計原則

1. **配置獨立**：回測與生產互不干擾
2. **語義清晰**：參數名稱明確表達用途
3. **向後相容**：現有功能不受影響
4. **簡單實施**：利用現有機制，無需重構

---

**最後更新：** 2025-10-11
**實施者：** Lenny（提出需求）+ Claude（技術實現）
**版本：** v1.0（實施完成）
