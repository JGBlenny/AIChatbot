# 方案 A 實作摘要

## 📋 變更概覽

**實作日期**: 2025-10-22
**實作目標**: 整合參數注入 + 業種語氣調整為單一 API 調用
**修改文件**: `services/llm_answer_optimizer.py`
**修改行數**: 9 處修改位置

---

## 🎯 實作目標

### 問題背景
1. **引用標記問題**: 答案中出現「根據【參考資料 1】」、「參考資料2」等引用
2. **語氣不一致**: Fast Path 和 Template Path 沒有業種語氣調整
3. **API 成本考量**: 需要優化 API 調用次數

### 解決方案
**方案 A (已採用)**: 合併參數注入 + 語氣調整為單一 API 調用

**優點**:
- ✅ 只需 1 次 API 調用（相比方案 B 的 2 次）
- ✅ 所有優化路徑統一處理
- ✅ 降低 API 成本和延遲

**缺點**:
- ⚠️  Temperature 需提升至 0.3（原 0.1）以兼顧參數準確度和語氣自然度
- ⚠️  需監控參數替換準確度

---

## 🔧 核心修改

### 1. inject_vendor_params 函數增強

**位置**: Line 368-471

#### 1.1 函數簽名修改
```python
def inject_vendor_params(
    self,
    content: str,
    vendor_params: Dict,
    vendor_name: str,
    vendor_info: Optional[Dict] = None  # ← 新增參數
) -> str:
```

#### 1.2 業種檢測邏輯
```python
# Line 397-400
business_type = vendor_info.get('business_type', 'property_management') if vendor_info else 'property_management'
```

#### 1.3 System Prompt 重構
```python
system_prompt = f"""你是一個專業的內容調整助理。你的任務是：
1. 根據業者的具體參數，調整知識庫內容中的數值和資訊
2. 根據業種類型，調整回答的語氣和表達方式

業者名稱：{vendor_name}
業種類型：{business_type}
業者參數：
{params_description}

【任務 1 - 參數調整】
1. 仔細識別內容中提到的參數相關資訊（如日期、金額、時間等）
2. 將這些資訊替換為業者的實際參數值
3. 確保替換後的內容自然流暢
4. 保持原有的語氣和結構，只調整數值和具體資訊

【任務 2 - 語氣調整】"""

# 根據 business_type 添加不同的語氣指示
if business_type == 'full_service':
    system_prompt += """
業種特性：包租型業者 - 提供全方位服務，直接負責租賃管理
語氣要求：
  • 使用主動承諾語氣：「我們會」、「公司將」、「我們負責」
  • 表達直接負責：「我們處理」、「我們安排」
  • 避免被動引導：不要用「請您聯繫」、「建議」等
  • 展現服務能力：強調公司會主動處理問題

範例：
  ❌ 避免：「建議您聯繫我們的客服」
  ✅ 推薦：「我們會立即為您處理」

  ❌ 避免：「您可以透過系統查看」
  ✅ 推薦：「我們會主動通知您最新進度」
"""

elif business_type == 'property_management':
    system_prompt += """
業種特性：代管型業者 - 協助租客與房東溝通，居中協調
語氣要求：
  • 使用協助引導語氣：「請您」、「建議」、「可協助」
  • 表達居中協調：「我們可以協助您聯繫」、「我們居中協調」
  • 避免直接承諾：不要用「我們會處理」、「公司負責」等
  • 引導租客行動：提供建議和協助選項

範例：
  ❌ 避免：「我們會直接為您維修」
  ✅ 推薦：「建議您聯繫房東，我們可協助居中協調」

  ❌ 避免：「公司負責處理所有維修」
  ✅ 推薦：「如需協助，我們可以幫您聯繫相關人員」
"""
```

#### 1.4 Temperature 調整
```python
# Line 482
param_injection_temp = float(os.getenv("LLM_PARAM_INJECTION_TEMP", "0.3"))

# 調整理由：
# 0.1: 參數準確但語氣僵硬
# 0.3: 兼顧參數準確度和語氣自然度 ✅
# 0.5: 語氣自然但可能影響參數準確度
```

---

### 2. 四個調用點更新

#### 2.1 Fast Path (Line 157)
```python
# 修改前
answer = self.inject_vendor_params(answer, vendor_params, vendor_name)

# 修改後
answer = self.inject_vendor_params(answer, vendor_params, vendor_name, vendor_info)
```

**影響**: Fast Path 現在也有業種語氣調整

---

#### 2.2 Template Path (Line 191)
```python
# 修改前
answer = self.inject_vendor_params(answer, vendor_params, vendor_name)

# 修改後
answer = self.inject_vendor_params(answer, vendor_params, vendor_name, vendor_info)
```

**影響**: Template Path 現在也有業種語氣調整

---

#### 2.3 Synthesis Path (Line 544)
```python
# 修改前
content = self.inject_vendor_params(content, vendor_params, vendor_name)

# 修改後
content = self.inject_vendor_params(content, vendor_params, vendor_name, vendor_info)
```

**影響**: Synthesis 語氣調整從舊版升級為增強版

---

#### 2.4 Full LLM Optimization Path (Line 715)
```python
# 修改前
content = self.inject_vendor_params(content, vendor_params, vendor_name)

# 修改後
content = self.inject_vendor_params(content, vendor_params, vendor_name, vendor_info)
```

**影響**: Full optimization 語氣調整從舊版升級為增強版

---

### 3. Citation 移除實作

#### 3.1 單一答案優化 Prompt (Line 779, 787)

**Process Questions**:
```python
prompt += """
5. **請直接回答，不要在答案中提及「參考資料1」、「參考資料2」等來源編號**

【參考資料】
"""
```

**General Questions**:
```python
prompt += """
5. **請直接回答，不要在答案中提及「參考資料1」、「參考資料2」等來源編號**

【參考資料】
"""
```

---

#### 3.2 答案合成 Prompt (Line 625, 636)

**Process Questions**:
```python
prompt += """
- **請直接回答，不要在答案中提及「答案1」、「答案2」等來源編號**

以下是從知識庫檢索到的多個相關答案：
"""
```

**General Questions**:
```python
prompt += """
- **請直接回答，不要在答案中提及「答案1」、「答案2」等來源編號**

以下是從知識庫檢索到的多個相關答案：
"""
```

---

## 📊 決策樹：優化路徑分析

```
用戶問題
    │
    ├─ 意圖分類
    │
    ├─ [Unclear] ──→ RAG Fallback ──→ 構建答案 ──→ inject_vendor_params() ✅
    │
    ├─ [有 SOP] ──→ 檢索 SOP ──→ LLM 優化 ──→ inject_vendor_params() ✅
    │
    └─ [知識庫]
        │
        ├─ [單一高信心] ──→ Fast Path ──→ inject_vendor_params() ✅
        │
        ├─ [模板匹配] ──→ Template Path ──→ inject_vendor_params() ✅
        │
        ├─ [多結果 + 需合成] ──→ Synthesis ──→ inject_vendor_params() ✅
        │
        └─ [其他] ──→ Full LLM Optimization ──→ inject_vendor_params() ✅
```

**結論**: 所有路徑都會經過 `inject_vendor_params()`，確保語氣調整的一致性

---

## ✅ 驗證結果

### 測試覆蓋

| 優化路徑 | 測試案例 | 語氣驗證 | 引用移除 | 狀態 |
|---------|---------|---------|---------|------|
| Fast Path | 租金何時繳？ | ✅ | ✅ | 通過 |
| Synthesis | 申請流程？ | ✅ | ✅ | 通過 |
| Knowledge | 冷氣壞了？ | ✅ | ✅ | 通過 |

### 語氣指標分析

#### 代管型 (property_management) 語氣特徵
```
✅ 出現頻率高：
  - "建議您" (出現在所有測試中)
  - "可以" (出現在所有測試中)
  - "如需協助" / "如有疑問" (出現在 2/3 測試中)
  - "我們可協助" (出現在測試 2)
  - "我們將協助居中協調" (出現在測試 3) ⭐

❌ 未出現：
  - "我們會處理"
  - "公司負責"
  - "我們安排"
```

---

## 🎯 業種語氣對比表

| 場景 | 包租型 (full_service) | 代管型 (property_management) |
|------|---------------------|---------------------------|
| **租金繳納** | "我們會在每月1日收取租金" | "建議您在每月1日前繳納租金" |
| **維修處理** | "我們會立即派人維修" | "建議您先聯繫房東，我們可協助協調" |
| **問題諮詢** | "我們的客服會主動聯繫您" | "如有疑問，歡迎隨時聯繫我們" |
| **文件處理** | "我們會準備所有必要文件" | "建議您準備相關文件，我們可協助確認" |

---

## 🚀 後續優化方向

### 1. 包租型測試 (優先級: 🔴 高)
**目標**: 驗證 `business_type='full_service'` 的語氣調整

**測試步驟**:
```sql
-- 1. 找到包租型業者
SELECT id, name, business_type
FROM vendors
WHERE business_type = 'full_service'
  AND is_active = true;

-- 2. 執行測試
curl -s -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "冷氣壞了怎麼辦？",
    "vendor_id": <包租型業者ID>,
    "user_role": "customer"
  }'

-- 3. 預期語氣
-- ✅ "我們會派人維修"
-- ✅ "公司負責處理"
-- ❌ 不應出現 "建議您聯繫房東"
```

---

### 2. Temperature 微調 (優先級: 🟡 中)
**目標**: 找到最佳 Temperature 平衡點

**實驗方案**:
| Temperature | 預期效果 | 測試重點 |
|------------|---------|---------|
| 0.2 | 參數極準確，語氣稍僵硬 | 參數替換準確度 |
| 0.3 | **當前值** | 綜合平衡 |
| 0.4 | 語氣自然，參數可能偏差 | 語氣流暢度 |

**監控指標**:
- 參數替換準確率 (目標: >99%)
- 語氣自然度評分 (目標: >4/5)
- Token 使用量 (目標: 不超過原來的 110%)

---

### 3. 特定意圖語氣定制 (優先級: 🟢 低)
**目標**: 針對特定意圖類型定制語氣策略

**候選意圖**:
```python
INTENT_TONE_OVERRIDE = {
    'legal_inquiry': {
        'property_management': '建議您諮詢專業法律顧問',
        'full_service': '我們的法務團隊會協助處理'
    },
    'emergency_repair': {
        'property_management': '請立即聯繫房東，我們會協助緊急協調',
        'full_service': '我們會立即派遣緊急維修人員'
    }
}
```

---

## 📝 環境變數配置

### 新增環境變數
```bash
# Temperature 控制（預設 0.3）
LLM_PARAM_INJECTION_TEMP=0.3

# 可選：針對不同業種設置不同 Temperature
LLM_PARAM_INJECTION_TEMP_FULL_SERVICE=0.3
LLM_PARAM_INJECTION_TEMP_PROPERTY_MGMT=0.3
```

### Docker Compose 配置範例
```yaml
rag-orchestrator:
  environment:
    - LLM_PARAM_INJECTION_TEMP=0.3
```

---

## 🔍 除錯與監控

### 日誌關鍵點
```python
# Line 397: 業種檢測
print(f"🏢 業種類型: {business_type}")

# Line 471: 注入完成
print(f"✅ 參數注入完成 - 內容已調整")
print(f"   原始: {content[:100]}...")
print(f"   調整: {result[:100]}...")
```

### 監控指標
1. **API 調用統計**
   - inject_vendor_params 調用次數
   - 平均 token 使用量
   - 平均響應時間

2. **準確度監控**
   - 參數替換錯誤率
   - 語氣匹配度（人工抽檢）

3. **用戶反饋**
   - 答案滿意度
   - 語氣自然度評分

---

## 📚 相關文檔

- **測試報告**: `TEST_REPORT.md`
- **測試指南**: `README.md`
- **修改文件**: `rag-orchestrator/services/llm_answer_optimizer.py`

---

**文檔版本**: v1.0
**最後更新**: 2025-10-22
**維護者**: Claude Code
