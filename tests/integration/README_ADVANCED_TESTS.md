# 進階功能自動化測試套件

## 📚 概述

本測試套件涵蓋兩個重要的系統功能：

1. **回退機制測試** (`test_fallback_mechanism.py`)
2. **參數動態注入測試** (`test_parameter_injection.py`)

---

## 🔄 回退機制測試

### 測試目標

驗證系統的 4 層回退路徑是否正常運作：

```plaintext
用戶問題
  ↓
第 1 層：SOP 檢索
  ├─ 有 SOP → 使用 SOP ✅
  └─ 無 SOP → 降級到第 2 層
  ↓
第 2 層：知識庫檢索
  ├─ 有知識 → 使用知識庫 ✅
  └─ 無知識 → 降級到第 3 層
  ↓
第 3 層：RAG 向量搜尋
  ├─ RAG 找到 → 使用 RAG 結果 ✅
  └─ RAG 無結果 → 降級到第 4 層
  ↓
第 4 層：兜底回應
  └─ 返回友善的「無法回答」訊息 ✅
```

### 測試類別

| 測試類別 | 測試數量 | 測試內容 |
|---------|---------|---------|
| `TestLayer1_SOPPriority` | 2 | SOP 優先級 |
| `TestLayer2_KnowledgeBaseFallback` | 2 | 知識庫回退 |
| `TestLayer3_RAGFallback` | 2 | RAG 回退 |
| `TestLayer4_FallbackResponse` | 3 | 兜底回應 |
| `TestFallbackSequence` | 1 | 回退序列完整性 |
| `TestSourcePriority` | 1 | 來源優先級 |

**總計**: 11 個測試案例

### 測試案例範例

#### 第 1 層：SOP 優先

```python
def test_has_sop_uses_sop():
    """測試：有 SOP 時應該使用 SOP"""
    question = "租金怎麼繳？"
    response = call_api(question)

    # 驗證使用 SOP
    sop_sources = [s for s in response["sources"]
                   if s.get("scope") == "vendor_sop"]
    assert len(sop_sources) > 0
```

#### 第 4 層：兜底回應

```python
def test_completely_unrelated_question_gets_fallback():
    """測試：完全無關的問題應返回兜底回應"""
    question = "今天天氣如何？"
    response = call_api(question)

    # 驗證兜底回應
    fallback_keywords = ["不太確定", "客服", "協助"]
    assert any(kw in response["answer"] for kw in fallback_keywords)
```

### 執行方式

```bash
# 完整測試
pytest tests/integration/test_fallback_mechanism.py -v -s

# 只測試 SOP 優先層
pytest tests/integration/test_fallback_mechanism.py::TestLayer1_SOPPriority -v -s

# 使用腳本
./scripts/run_advanced_tests.sh
# 選擇選項 1
```

---

## 💉 參數動態注入測試

### 測試目標

驗證業者參數是否正確注入到 AI 回答中。

### 測試的參數

| 參數名稱 | Vendor 1 | Vendor 2 | 測試問題範例 |
|---------|----------|----------|------------|
| `payment_day` | 1 號 | 5 號 | "每月幾號要繳租金？" |
| `late_fee` | 200 元 | 300 元 | "遲繳租金會被罰多少錢？" |
| `grace_period` | 5 天 | 3 天 | "繳費日當天沒繳會怎樣？" |
| `service_hotline` | 02-2345-6789 | 02-8765-4321 | "客服電話是多少？" |
| `deposit_months` | 2 個月 | 2 個月 | "押金要付幾個月？" |

### 測試類別

| 測試類別 | 測試數量 | 測試內容 |
|---------|---------|---------|
| `TestPaymentDayInjection` | 3 | 繳費日期注入 |
| `TestLateFeeInjection` | 2 | 逾期手續費注入 |
| `TestGracePeriodInjection` | 2 | 繳費寬限期注入 |
| `TestServiceHotlineInjection` | 2 | 客服專線注入 |
| `TestDepositMonthsInjection` | 2 | 押金月數注入 |
| `TestParameterInjectionIntegrity` | 2 | 參數注入完整性 |
| `TestParameterInjectionEdgeCases` | 2 | 邊界情況 |

**總計**: 15 個測試案例（參數化測試展開後約 25 個）

### 測試案例範例

#### 繳費日期注入

```python
@pytest.mark.parametrize("vendor_id", [1, 2])
def test_payment_day_appears_in_answer(vendor_id):
    """測試：繳費日期應出現在回答中"""
    question = "每月幾號要繳租金？"
    expected_day = VENDOR_PARAMS[vendor_id]["payment_day"]

    response = call_api(question, vendor_id)
    answer = response.get("answer", "")

    # 驗證繳費日期出現在回答中
    numbers_in_answer = extract_numbers_from_text(answer)
    assert expected_day in numbers_in_answer
```

#### 不同業者差異驗證

```python
def test_different_vendors_have_different_payment_days():
    """測試：不同業者的繳費日期應該不同"""
    question = "每月幾號要繳租金？"

    response_v1 = call_api(question, 1)
    response_v2 = call_api(question, 2)

    # 業者 1 應該包含 "1"，業者 2 應該包含 "5"
    assert "1" in extract_numbers_from_text(response_v1["answer"])
    assert "5" in extract_numbers_from_text(response_v2["answer"])
```

### 執行方式

```bash
# 完整測試
pytest tests/integration/test_parameter_injection.py -v -s

# 只測試繳費日期注入
pytest tests/integration/test_parameter_injection.py::TestPaymentDayInjection -v -s

# 使用腳本
./scripts/run_advanced_tests.sh
# 選擇選項 2
```

---

## 🚀 快速開始

### 前置要求

```bash
# 1. 啟動服務
docker-compose up -d

# 2. 安裝依賴
pip3 install pytest requests
```

### 執行測試

#### 使用腳本（推薦）

```bash
./scripts/run_advanced_tests.sh
```

選單選項：
1. 回退機制測試
2. 參數動態注入測試
3. 全部測試
4. 快速測試

#### 直接使用 pytest

```bash
# 全部進階測試
pytest tests/integration/test_fallback_mechanism.py tests/integration/test_parameter_injection.py -v -s

# 快速測試（各選 1 個）
pytest tests/integration/test_fallback_mechanism.py::TestLayer1_SOPPriority::test_has_sop_uses_sop -v -s
pytest tests/integration/test_parameter_injection.py::TestPaymentDayInjection::test_payment_day_appears_in_answer -v -s -k "vendor_id1"
```

---

## 📊 測試覆蓋範圍

### 回退機制測試

| 回退層級 | 測試覆蓋 | 關鍵驗證點 |
|---------|---------|-----------|
| SOP 優先 | ✅ 100% | 使用 SOP、內容正確 |
| 知識庫 Fallback | ✅ 100% | 降級邏輯、答案品質 |
| RAG Fallback | ✅ 100% | 向量搜尋、相關性 |
| 兜底回應 | ✅ 100% | 友善性、聯繫資訊 |
| 完整性 | ✅ 100% | 序列一致性、優先級 |

### 參數注入測試

| 參數類型 | 測試覆蓋 | 關鍵驗證點 |
|---------|---------|-----------|
| 繳費日期 | ✅ 100% | 值正確、業者差異 |
| 逾期費用 | ✅ 100% | 值正確、業者差異 |
| 寬限期 | ✅ 100% | 上下文正確 |
| 客服專線 | ✅ 100% | 格式正確、業者差異 |
| 押金月數 | ✅ 100% | 上下文正確 |
| 完整性 | ✅ 100% | 多參數、一致性 |

---

## 🎯 測試結果解讀

### 成功案例

```
✅ SOP 優先測試通過
   問題：租金怎麼繳？
   來源數量：3
   SOP 來源數量：2
```

### 警告案例（可能是正常的）

```
⚠️  知識庫測試：無來源但有回答（可能是 RAG）
   問題：租約期間可以提前解約嗎？
   回答長度：150
```

**解讀**: 這可能是正常的，表示問題沒有對應的知識庫，但 RAG 找到了相關內容。

### 失敗案例

```
❌ 參數注入失敗
   業者：甲山林
   預期繳費日：1
   回答中的數字：['5', '3']
```

**解讀**: 參數注入有問題，需要檢查：
1. 業者參數配置
2. LLM 參數注入邏輯
3. SOP 內容

---

## 🔍 故障排除

### 問題 1：API 連接失敗

```bash
# 檢查服務
docker-compose ps

# 重啟
docker-compose restart rag-orchestrator
```

### 問題 2：參數未注入

**可能原因**:
1. 業者參數未配置
2. LLM 未正確識別參數需求

**檢查步驟**:
```sql
-- 檢查業者參數
SELECT * FROM vendor_configs WHERE vendor_id = 1;

-- 應該看到：payment_day, late_fee, grace_period 等
```

### 問題 3：回退機制不正確

**可能原因**:
1. SOP 資料不完整
2. 知識庫資料缺失

**檢查步驟**:
```sql
-- 檢查 SOP 數量
SELECT COUNT(*) FROM vendor_sop_items WHERE vendor_id = 1;

-- 應該有 28 個項目

-- 檢查知識庫
SELECT COUNT(*) FROM knowledge_base WHERE is_active = TRUE;
```

---

## 📈 測試擴展

### 添加新的回退測試

```python
class TestLayer5_NewFallback:
    """第 5 層：新的回退機制"""

    def test_new_fallback_logic(self):
        """測試新的回退邏輯"""
        question = "你的測試問題"
        response = call_api(question)
        # 你的驗證邏輯
        assert condition
```

### 添加新的參數測試

```python
class TestNewParameterInjection:
    """新參數注入測試"""

    @pytest.mark.parametrize("vendor_id", [1, 2])
    def test_new_parameter(self, vendor_id):
        """測試新參數注入"""
        question = "關於新參數的問題"
        expected_value = VENDOR_PARAMS[vendor_id]["new_param"]

        response = call_api(question, vendor_id)
        # 驗證參數出現
        assert expected_value in response["answer"]
```

---

## 🎓 最佳實踐

### 1. 定期執行

```bash
# 每週執行一次完整測試
0 0 * * 0 cd /path/to/project && ./scripts/run_advanced_tests.sh
```

### 2. 代碼變更後執行

```bash
# 修改回退邏輯後
pytest tests/integration/test_fallback_mechanism.py -v

# 修改參數注入邏輯後
pytest tests/integration/test_parameter_injection.py -v
```

### 3. 新增業者參數後執行

```bash
# 為新業者添加參數後
pytest tests/integration/test_parameter_injection.py -v -s
```

---

## 📚 相關文檔

- [業務邏輯測試](./README_BUSINESS_LOGIC_TESTS.md)
- [測試狀況總覽](../../docs/TESTING_AND_VALIDATION_STATUS.md)
- [測試完成報告](../../docs/AUTOMATED_TESTING_SETUP_COMPLETE.md)

---

**建立日期**: 2025-10-18
**維護者**: 開發團隊
**版本**: 1.0.0
