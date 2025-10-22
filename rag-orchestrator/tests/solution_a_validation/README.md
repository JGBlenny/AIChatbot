# 方案 A 驗證測試文檔

**測試日期**: 2025-10-22
**測試目的**: 驗證參數注入 + 業種語氣調整的整合方案
**測試業者**: vendor_id=1 (甲山林包租代管, property_management)

---

## 📁 文件結構

```
solution_a_validation/
├── README.md                        # 本文件：測試說明
├── TEST_REPORT.md                   # 完整測試報告（8.6KB）
├── test_1_payment_query.json        # 測試 1: 帳務查詢（Fast Path）
├── test_2_application_process.json  # 測試 2: 申請流程（Synthesis）
├── test_3_repair_request.json       # 測試 3: 維修請求（協調場景）
└── IMPLEMENTATION_SUMMARY.md        # 實作摘要（本次建立）
```

---

## 🎯 測試目標

### 1. 引用移除驗證
- ❌ 修改前: 答案中出現「根據【參考資料 1】」、「參考資料2」
- ✅ 修改後: 完全移除所有引用標記

### 2. 語氣調整統一
- ❌ 修改前: Fast Path 和 Template Path 沒有語氣調整
- ✅ 修改後: 所有路徑（Fast/Template/Synthesis/Full LLM）都有業種語氣

### 3. API 成本優化
- ❌ 原方案 B: 參數注入 + 語氣調整需要 2 次 API 調用
- ✅ 方案 A: 合併為 1 次 API 調用，Temperature 從 0.1 提升至 0.3

---

## 📊 測試案例說明

### Test 1: 帳務查詢問題
**文件**: `test_1_payment_query.json`

- **問題**: "租金什麼時候要繳納？"
- **意圖**: 帳務查詢 (data_query)
- **優化路徑**: Fast Path（高信心單一答案）
- **驗證重點**:
  - ✅ 引用移除
  - ✅ 代管型協助引導語氣（"建議您"、"可以"、"如需協助"）
  - ✅ 參數準確注入（"每個月的1日"、"5天寬限期"）

**關鍵語氣指標**:
```
"建議您留意繳費日期"
"您可以登入我們的系統查看"
"如果您需要任何協助或有疑問，我們都可以幫助您處理"
```

---

### Test 2: 申請流程問題
**文件**: `test_2_application_process.json`

- **問題**: "如何申請租賃並簽約？"
- **意圖**: 服務說明 (knowledge)
- **優化路徑**: Synthesis（多答案合成）
- **驗證重點**:
  - ✅ 引用移除（無"答案1"、"參考資料"標記）
  - ✅ 合成答案語氣一致
  - ✅ Markdown 格式正確

**關鍵語氣指標**:
```
"建議您儘快完成申請程序，我們可協助您完成文件提交"
"我們可協助您確認所需文件"
"如有疑問可協助您了解審查進度"
```

---

### Test 3: 維修請求問題
**文件**: `test_3_repair_request.json`

- **問題**: "冷氣壞了怎麼辦？"
- **意圖**: 設備報修 (service_request)
- **優化路徑**: Knowledge-based optimization
- **驗證重點**:
  - ✅ **完美展現代管型居中協調角色**
  - ✅ 引導租客主動聯繫房東
  - ✅ 明確表達"協助協調"而非"直接負責"

**關鍵語氣指標** (⭐ 代管型核心特徵):
```
"建議立即聯繫房東通報冷氣故障情況"         ← 引導租客行動
"請向我們提交維修請求"                       ← 提供協助管道
"我們將協助居中協調維修事宜"                 ← 明確協調定位（非直接負責）
```

---

## 🔧 實作修改清單

### 修改文件
`/Users/lenny/jgb/AIChatbot/rag-orchestrator/services/llm_answer_optimizer.py`

### 修改位置（共 9 處）

1. **inject_vendor_params 函數簽名** (Line 368-374)
   - 新增 `vendor_info: Optional[Dict] = None` 參數

2. **System Prompt 增強** (Line 407-468)
   ```python
   # 新增業種檢測
   business_type = vendor_info.get('business_type', 'property_management') if vendor_info else 'property_management'

   # 新增任務 2：語氣調整
   if business_type == 'full_service':
       # 包租型：主動承諾語氣
   elif business_type == 'property_management':
       # 代管型：協助引導語氣
   ```

3. **Temperature 調整** (Line 482)
   ```python
   # 從 0.1 提升至 0.3
   param_injection_temp = float(os.getenv("LLM_PARAM_INJECTION_TEMP", "0.3"))
   ```

4-7. **四個調用點更新** (Line 157, 191, 544, 715)
   ```python
   # Fast Path
   inject_vendor_params(answer, vendor_params, vendor_name, vendor_info)

   # Template Path
   inject_vendor_params(answer, vendor_params, vendor_name, vendor_info)

   # Synthesis Path
   inject_vendor_params(content, vendor_params, vendor_name, vendor_info)

   # Full LLM Path
   inject_vendor_params(content, vendor_params, vendor_name, vendor_info)
   ```

8-9. **Citation 移除指示** (Line 779, 787, 625, 636)
   ```python
   # 單一優化
   prompt += """
   5. **請直接回答，不要在答案中提及「參考資料1」、「參考資料2」等來源編號**"""

   # 合成優化
   prompt += """
   - **請直接回答，不要在答案中提及「答案1」、「答案2」等來源編號**"""
   ```

---

## 📈 測試結果摘要

| 驗證項目 | 測試 1 | 測試 2 | 測試 3 | 狀態 |
|---------|--------|--------|--------|------|
| 引用移除 | ✅ | ✅ | ✅ | 通過 |
| 語氣調整 | ✅ | ✅ | ✅ | 通過 |
| 參數注入 | ✅ | ✅ | ✅ | 通過 |
| Markdown格式 | N/A | ✅ | ✅ | 通過 |
| 協調語氣 | N/A | N/A | ✅⭐ | 優秀 |

**總體評估**: ✅ **全部通過**

---

## 🚀 下一步建議

### 1. 包租型業者測試 (優先級: 高)
找到 `business_type='full_service'` 的業者進行測試，驗證主動承諾語氣：
- 預期語氣: "我們會處理"、"公司負責"、"我們安排"
- 避免語氣: "建議您"、"請聯繫"、"可協助"

### 2. Temperature 長期監控 (優先級: 中)
- 監控 Temperature=0.3 對參數替換準確度的影響
- 收集異常案例（如果參數替換錯誤）
- 必要時微調至 0.2 或 0.25

### 3. Token 成本分析 (優先級: 中)
- 記錄 Temperature 提升後的 token 使用量
- 對比修改前後的 API 調用成本
- 評估是否需要針對特定場景優化

### 4. 用戶反饋收集 (優先級: 低)
- 收集終端用戶對新語氣的反饋
- 分析用戶滿意度變化
- 根據反饋微調語氣策略

---

## 📝 相關文檔

- **完整測試報告**: `TEST_REPORT.md`
- **實作摘要**: `IMPLEMENTATION_SUMMARY.md`
- **修改文件**: `rag-orchestrator/services/llm_answer_optimizer.py`

---

## 🔍 如何使用這些測試文件

### 重現測試結果
```bash
# 1. 清除緩存
docker exec aichatbot-redis redis-cli FLUSHDB

# 2. 執行測試 1: 帳務查詢
curl -s -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "租金什麼時候要繳納？",
    "vendor_id": 1,
    "user_role": "customer"
  }' | python3 -m json.tool

# 3. 執行測試 2: 申請流程
curl -s -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "如何申請租賃並簽約？",
    "vendor_id": 1,
    "user_role": "customer"
  }' | python3 -m json.tool

# 4. 執行測試 3: 維修請求
curl -s -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "冷氣壞了怎麼辦？",
    "vendor_id": 1,
    "user_role": "customer"
  }' | python3 -m json.tool
```

### 驗證語氣特徵
```python
import json

# 讀取測試結果
with open('test_1_payment_query.json') as f:
    data = json.load(f)
    answer = data['answer']

# 檢查代管型語氣指標
property_mgmt_indicators = ['建議', '請您', '可以', '協助', '如需']
for indicator in property_mgmt_indicators:
    if indicator in answer:
        print(f"✅ 找到代管型指標: {indicator}")

# 檢查不應出現的包租型語氣
full_service_indicators = ['我們會', '公司負責', '我們處理']
for indicator in full_service_indicators:
    if indicator in answer:
        print(f"⚠️  發現包租型指標: {indicator}")
```

---

**文檔維護者**: Claude Code
**最後更新**: 2025-10-22
**版本**: v1.0
