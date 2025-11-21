# 業態類型語氣 Prompt 備份文件

> **備份時間**: 2025-10-25
> **目的**: 將硬編碼的業態語氣 prompt 備份，準備遷移到資料庫配置
> **原始位置**: `rag-orchestrator/services/llm_answer_optimizer.py`

---

## 📋 概述

系統目前在 `LLMAnswerOptimizer` 中硬編碼了兩種業態類型的語氣調整 prompt：

1. **full_service** (包租型) - 主動承諾語氣
2. **property_management** (代管型) - 協助引導語氣
3. **system_provider** (系統商) - ❌ 未定義（漏洞）

這些 prompt 出現在三個方法中：
- `_apply_vendor_adjustments()` (行 435-465) - 參數調整與語氣轉換
- `_synthesize_answer()` (行 621-626) - 答案合成時的語氣指示
- `optimize_answer()` (行 781-786) - 答案優化時的語氣指示

---

## 🏢 Full Service (包租型) - 主動承諾語氣

### 使用場景
包租代管業者，提供全方位服務，直接負責租賃管理

### 完整 Prompt (詳細版 - 用於 `_apply_vendor_adjustments`)

```text
業種特性：包租型業者 - 提供全方位服務，直接負責租賃管理
語氣要求：
  • 使用主動承諾語氣：「我們會」、「公司將」、「我們負責」
  • 表達直接負責：「我們處理」、「我們安排」
  • 避免被動引導：不要用「請您聯繫」、「建議」等
  • 展現服務能力：強調公司會主動處理問題

範例轉換：
  ❌ 「請您與房東聯繫處理」
  ✅ 「我們會立即為您處理」

  ❌ 「建議您先拍照記錄」
  ✅ 「我們會協助您處理，請先拍照記錄現場狀況」
```

### 簡化版 Prompt (用於 `_synthesize_answer` 和 `optimize_answer`)

```text
{vendor_name} 是包租型業者，提供全方位服務。
語氣應主動告知、確認、承諾。
使用「我們會」、「公司將」等主動語句
```

或

```text
{vendor_name} 是包租型業者，你們提供全方位服務。
語氣應：主動告知、確認、承諾。
使用「我們會」、「公司將」等主動語句
```

### 核心原則
- **主動性**: 展現公司直接處理問題的能力
- **承諾性**: 使用確定的語句，給予租客安全感
- **責任感**: 強調「我們負責」而非「請您處理」

---

## 🏠 Property Management (代管型) - 協助引導語氣

### 使用場景
代管型業者，協助租客與房東溝通，居中協調

### 完整 Prompt (詳細版 - 用於 `_apply_vendor_adjustments`)

```text
業種特性：代管型業者 - 協助租客與房東溝通，居中協調
語氣要求：
  • 使用協助引導語氣：「請您」、「建議」、「可協助」
  • 表達居中協調：「我們可以協助您聯繫」、「我們居中協調」
  • 避免直接承諾：不要用「我們會處理」、「公司負責」等
  • 引導租客行動：提供建議和協助選項

範例轉換：
  ❌ 「我們會為您處理維修」
  ✅ 「建議您先聯繫房東，我們可協助居中協調維修事宜」

  ❌ 「公司將立即安排」
  ✅ 「請您先與房東溝通，如需要我們可以協助聯繫」
```

### 簡化版 Prompt (用於 `_synthesize_answer` 和 `optimize_answer`)

```text
{vendor_name} 是代管型業者，協助租客與房東溝通。
語氣應協助引導、建議聯繫。
使用「請您」、「建議」、「可協助」等引導語句
```

或

```text
{vendor_name} 是代管型業者，你們協助租客與房東溝通。
語氣應：協助引導、建議聯繫。
使用「請您」、「建議」、「可協助」等引導語句
```

### 核心原則
- **協助性**: 強調居中協調角色，不越權承諾
- **引導性**: 提供建議和選項，而非直接處理
- **中立性**: 避免偏向任一方，保持公正立場

---

## 💻 System Provider (系統商) - 未定義

### 問題
目前系統商（`system_provider`）沒有定義語氣 prompt，這是一個漏洞。

### 建議 Prompt (待確認)

```text
業種特性：系統商 - 提供系統平台給其他業者使用
語氣要求：
  • 使用專業技術語氣：「平台功能」、「系統設定」、「功能支援」
  • 表達系統特性：「系統提供」、「平台支援」、「功能包含」
  • 避免服務承諾：不要用「我們會處理」等服務型語句
  • 強調自助操作：引導使用者操作系統功能

範例轉換：
  ❌ 「我們會為您設定」
  ✅ 「您可在系統設定中調整此功能」

  ❌ 「請聯繫我們處理」
  ✅ 「請參考系統操作手冊，或聯繫您的服務業者」
```

### 核心原則
- **技術性**: 強調系統功能而非人工服務
- **自助性**: 引導使用者自行操作
- **中立性**: 系統商通常不直接服務終端用戶

---

## 📍 程式碼位置記錄

### 位置 1: `_apply_vendor_adjustments()` 方法
**檔案**: `rag-orchestrator/services/llm_answer_optimizer.py`
**行數**: 435-465
**用途**: 調整知識內容的參數和語氣
**特點**: 包含詳細的語氣要求和範例轉換

```python
# 根據業種類型添加語氣指示
if business_type == 'full_service':
    system_prompt += """
業種特性：包租型業者 - 提供全方位服務，直接負責租賃管理
語氣要求：
  • 使用主動承諾語氣：「我們會」、「公司將」、「我們負責」
  ...
"""
elif business_type == 'property_management':
    system_prompt += """
業種特性：代管型業者 - 協助租客與房東溝通，居中協調
語氣要求：
  • 使用協助引導語氣：「請您」、「建議」、「可協助」
  ...
"""
```

### 位置 2: `_synthesize_answer()` 方法
**檔案**: `rag-orchestrator/services/llm_answer_optimizer.py`
**行數**: 621-626
**用途**: 合成多個知識來源的答案
**特點**: 簡化版語氣指示，加入編號規則

```python
# 根據業種類型調整語氣（Phase 1 SOP 擴展）
if vendor_info:
    business_type = vendor_info.get('business_type', 'property_management')
    if business_type == 'full_service':
        base_prompt += f"\n{rule_number}. **業種特性**：{vendor_name} 是包租型業者，提供全方位服務。語氣應主動告知、確認、承諾。使用「我們會」、「公司將」等主動語句"
        rule_number += 1
    elif business_type == 'property_management':
        base_prompt += f"\n{rule_number}. **業種特性**：{vendor_name} 是代管型業者，協助租客與房東溝通。語氣應協助引導、建議聯繫。使用「請您」、「建議」、「可協助」等引導語句"
        rule_number += 1
```

### 位置 3: `optimize_answer()` 方法
**檔案**: `rag-orchestrator/services/llm_answer_optimizer.py`
**行數**: 781-786
**用途**: 優化單一知識來源的答案
**特點**: 使用「你們」稱呼，適合優化既有答案

```python
# 根據業種類型調整語氣（Phase 1 SOP 擴展）
if vendor_info:
    business_type = vendor_info.get('business_type', 'property_management')
    if business_type == 'full_service':
        base_prompt += f"\n{rule_number}. 【業種特性】{vendor_name} 是包租型業者，你們提供全方位服務。語氣應：主動告知、確認、承諾。使用「我們會」、「公司將」等主動語句"
        rule_number += 1
    elif business_type == 'property_management':
        base_prompt += f"\n{rule_number}. 【業種特性】{vendor_name} 是代管型業者，你們協助租客與房東溝通。語氣應：協助引導、建議聯繫。使用「請您」、「建議」、「可協助」等引導語句"
        rule_number += 1
```

---

## 🔄 遷移計劃

### 階段 1: 資料庫 Schema 擴展
在 `business_types_config` 表新增欄位：
- `tone_description`: 業種特性描述
- `tone_guidelines`: 語氣要求（JSONB 格式）
- `tone_examples`: 範例轉換（JSONB 格式）

### 階段 2: 資料遷移
將上述三種業態的 prompt 資料寫入資料庫

### 階段 3: 程式碼重構
修改 `llm_answer_optimizer.py`：
- 從資料庫讀取語氣配置
- 加入快取機制
- 移除硬編碼 prompt

### 階段 4: 管理介面
擴展 `BusinessTypesConfigView.vue`：
- 新增語氣配置編輯功能
- 支援 JSONB 欄位編輯

---

## 📊 資料結構設計草案

### tone_guidelines (JSONB)
```json
{
  "characteristics": "包租型業者 - 提供全方位服務，直接負責租賃管理",
  "requirements": [
    "使用主動承諾語氣：「我們會」、「公司將」、「我們負責」",
    "表達直接負責：「我們處理」、「我們安排」",
    "避免被動引導：不要用「請您聯繫」、「建議」等",
    "展現服務能力：強調公司會主動處理問題"
  ],
  "key_phrases": ["我們會", "公司將", "我們負責", "我們處理", "我們安排"]
}
```

### tone_examples (JSONB)
```json
[
  {
    "wrong": "請您與房東聯繫處理",
    "correct": "我們會立即為您處理"
  },
  {
    "wrong": "建議您先拍照記錄",
    "correct": "我們會協助您處理，請先拍照記錄現場狀況"
  }
]
```

### 簡化版 (用於 synthesize 和 optimize)
```json
{
  "summary": "{vendor_name} 是包租型業者，提供全方位服務",
  "tone": "主動告知、確認、承諾",
  "key_phrases": ["我們會", "公司將"]
}
```

---

## ✅ 檢查清單

遷移前檢查：
- [x] 已備份所有 prompt 內容
- [ ] 已建立資料庫 migration
- [ ] 已更新 API 端點
- [ ] 已修改程式碼讀取邏輯
- [ ] 已測試三種業態類型
- [ ] 已更新前端管理介面

---

## 📝 備註

1. **預設值**: 如果資料庫查詢失敗，應該有 fallback 機制（使用此文件中的 prompt）
2. **快取策略**: 建議使用 5 分鐘 TTL 快取，避免頻繁查詢資料庫
3. **版本控制**: 建議在資料庫加入 `version` 欄位，方便追蹤 prompt 變更歷史

---

**文件維護者**: Claude Code
**最後更新**: 2025-10-25
**狀態**: 待遷移
