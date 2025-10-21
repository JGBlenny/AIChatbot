# 業種類型 × 金流模式自動化測試套件

## 概述

這是一套完整的自動化測試套件，用於驗證 AI 客服系統的核心業務邏輯：**業種類型（business_type）** 和 **金流模式（cashflow_model）** 的所有組合。

## 測試覆蓋

### 四種業務情境

| 編號 | 業者 | business_type | cashflow_model | 說明 |
|-----|------|---------------|----------------|------|
| 1 | 甲山林 (V1) | `full_service` | `through_company` | 包租型 |
| 2 | 信義 (V2) | `property_management` | `direct_to_landlord` | 純代管-不過公司 |
| 3 | 永慶 (V4) | `property_management` | `through_company` | 純代管-過公司 |
| 4 | 台灣房屋 (V5) | `property_management` | `hybrid` | 純代管-混合型 |

### 六個測試問題

每種情境測試以下 6 個問題：

1. 租金怎麼繳？
2. 押金什麼時候退還？
3. 如何申請收據？
4. 遲繳租金會怎樣？
5. 繳費方式有哪些？
6. 如何查詢當月租金？

**總測試數量**: 4 種情境 × 6 個問題 = **24 個測試案例**

### 驗證項目

#### 1. 語氣驗證（ToneValidator）

**包租型（full_service）** - 主動服務語氣：
- ✅ 我們會、我們將
- ✅ 公司會、公司將
- ✅ 系統會、自動

**代管型（property_management）** - 協助引導語氣：
- ✅ 請您、建議您
- ✅ 您可以、建議
- ✅ 可協助、協助您

#### 2. 內容驗證（ContentValidator）

**金流過公司（through_company）**：
- ✅ 提及：公司、系統、JGB、自動生成
- ❌ 避免：房東、向房東索取

**金流不過公司（direct_to_landlord）**：
- ✅ 提及：房東、向房東索取、自行保管
- ❌ 避免：公司收款、系統自動

**混合型（hybrid）**：
- ✅ 提及：依房源、部分房源、而異
- ✅ 同時提及公司和房東

#### 3. 交叉驗證

- ✅ 包租型 vs 代管型語氣差異
- ✅ 金流過公司 vs 不過公司內容差異
- ✅ 混合型包含兩種金流說明

## 快速開始

### 前置要求

1. **服務運行中**
   ```bash
   docker-compose up -d
   ```

2. **Python 套件**
   ```bash
   pip install pytest requests
   ```

### 執行測試

#### 方法 1：使用執行腳本（推薦）

```bash
# 在專案根目錄執行
./scripts/run_business_logic_tests.sh
```

腳本會引導您選擇測試模式：
- 快速測試（1 個問題/情境）
- 完整測試（6 個問題/情境）
- 單一情境測試
- 交叉驗證測試

#### 方法 2：直接使用 pytest

```bash
# 完整測試
pytest tests/integration/test_business_logic_matrix.py -v -s

# 快速測試（只測試租金繳納）
pytest tests/integration/test_business_logic_matrix.py -v -s -k "rent_payment"

# 測試單一情境
pytest tests/integration/test_business_logic_matrix.py::TestScenario1_FullService -v -s

# 交叉驗證
pytest tests/integration/test_business_logic_matrix.py::TestCrossValidation -v -s
```

## 測試輸出範例

### 成功案例

```
✅ 測試通過：租金怎麼繳？
   語氣：主動服務型 (匹配 3 個關鍵詞)
   內容：金流過公司 (匹配 4 個關鍵詞)
```

### 失敗案例

```
❌ 語氣驗證失敗：找到 0 個主動服務型關鍵詞
回答：租金一般是按月支付的，請您在每月...
```

## 測試架構

### 檔案結構

```
tests/integration/
├── test_business_logic_matrix.py   # 主測試檔案
└── README_BUSINESS_LOGIC_TESTS.md  # 本文檔

scripts/
└── run_business_logic_tests.sh     # 執行腳本
```

### 核心類別

```python
# 語氣驗證器
class ToneValidator:
    def validate_tone(answer, expected_type) -> Dict
    # 驗證回答語氣是否符合業種類型

# 內容驗證器
class ContentValidator:
    def validate_content(answer, expected_cashflow) -> Dict
    # 驗證回答內容是否符合金流模式

# API 呼叫
def call_vendor_api(vendor_id, question) -> Dict
    # 呼叫業者 API 並返回結果
```

### 測試類別

```python
# 4 個情境測試類別
TestScenario1_FullService                          # 包租型
TestScenario2_PropertyManagement_DirectToLandlord  # 純代管-不過公司
TestScenario3_PropertyManagement_ThroughCompany    # 純代管-過公司
TestScenario4_PropertyManagement_Hybrid            # 純代管-混合型

# 1 個交叉驗證類別
TestCrossValidation                                # 交叉驗證
```

## 擴展測試

### 添加新的測試問題

編輯 `test_business_logic_matrix.py`：

```python
TEST_QUESTIONS = {
    "rent_payment": "租金怎麼繳？",
    "deposit_refund": "押金什麼時候退還？",
    # 添加新問題
    "your_new_question": "您的新問題？",
}
```

### 調整驗證規則

修改驗證器的關鍵詞列表：

```python
class ToneValidator:
    FULL_SERVICE_PATTERNS = [
        "我們會", "我們將",
        # 添加新的關鍵詞
        "您的新關鍵詞",
    ]
```

### 添加新的情境

複製現有的測試類別並修改業者配置：

```python
class TestScenario5_YourNewScenario:
    vendor_config = VENDORS["your_vendor"]

    @pytest.mark.parametrize("question_key", TEST_QUESTIONS.keys())
    def test_your_scenario_questions(self, question_key):
        # 測試邏輯
        pass
```

## CI/CD 整合

### GitHub Actions 範例

```yaml
name: Business Logic Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start services
        run: docker-compose up -d
      - name: Wait for services
        run: sleep 30
      - name: Run tests
        run: pytest tests/integration/test_business_logic_matrix.py -v
```

### 本地 Git Hook

在 `.git/hooks/pre-push` 添加：

```bash
#!/bin/bash
echo "執行業務邏輯測試..."
pytest tests/integration/test_business_logic_matrix.py -v -s -k "rent_payment"
```

## 故障排除

### 問題 1：API 連接失敗

**症狀**：
```
requests.exceptions.ConnectionError: Connection refused
```

**解決方案**：
```bash
# 檢查服務狀態
docker-compose ps

# 重啟服務
docker-compose restart rag-orchestrator
```

### 問題 2：語氣驗證失敗

**症狀**：
```
語氣驗證失敗：找到 0 個協助引導型關鍵詞
```

**可能原因**：
1. SOP 內容未正確設定 `business_type_*` 欄位
2. LLM 系統提示詞未正確注入

**檢查步驟**：
```sql
-- 檢查 SOP 設定
SELECT item_name, requires_business_type_check,
       business_type_full_service, business_type_management
FROM vendor_sop_items
WHERE vendor_id = 1 AND item_name LIKE '%租金%';
```

### 問題 3：內容驗證失敗

**症狀**：
```
內容驗證失敗：找到 0 個金流過公司關鍵詞
```

**可能原因**：
1. `cashflow_*` 欄位未設定
2. 金流模式判斷邏輯有誤

**檢查步驟**：
```sql
-- 檢查金流模式設定
SELECT id, name, business_type, cashflow_model
FROM vendors
WHERE id IN (1,2,4,5);

-- 檢查 SOP 金流版本
SELECT item_name, requires_cashflow_check,
       cashflow_through_company, cashflow_direct_to_landlord
FROM vendor_sop_items
WHERE vendor_id = 1 AND requires_cashflow_check = TRUE;
```

## 最佳實踐

### 1. 定期執行

```bash
# 每天執行一次完整測試
0 2 * * * cd /path/to/project && ./scripts/run_business_logic_tests.sh
```

### 2. 代碼變更後執行

```bash
# 修改 SOP 相關代碼後
pytest tests/integration/test_business_logic_matrix.py -v -s

# 只快速驗證核心功能
pytest tests/integration/test_business_logic_matrix.py -v -s -k "rent_payment or TestCrossValidation"
```

### 3. 測試結果記錄

```bash
# 生成 HTML 報告
pytest tests/integration/test_business_logic_matrix.py --html=report.html --self-contained-html

# 生成 JUnit XML（CI/CD 用）
pytest tests/integration/test_business_logic_matrix.py --junitxml=results.xml
```

## 參考文檔

- [四種情境手動測試報告](../../docs/features/FOUR_SCENARIOS_TEST_REPORT.md)
- [測試與驗證狀況總覽](../../docs/TESTING_AND_VALIDATION_STATUS.md)
- [AI 客服邏輯實作狀況](../../docs/AI_CHATBOT_LOGIC_IMPLEMENTATION_STATUS.md)

## 維護者

- **建立日期**: 2025-10-18
- **維護者**: 開發團隊
- **最後更新**: 2025-10-18

## 版本歷史

- **v1.0.0** (2025-10-18): 初始版本
  - 4 種情境測試
  - 6 個測試問題
  - 語氣和內容雙重驗證
  - 交叉驗證測試
