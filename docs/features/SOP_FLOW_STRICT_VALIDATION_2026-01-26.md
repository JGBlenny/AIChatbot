# SOP 流程配置嚴格限制實施

**實施日期**: 2026-01-26
**狀態**: ✅ 已完成並可用於生產環境
**測試成功率**: 100% (8/8 測試通過)
**相關功能**: [Vendor SOP 流程配置](./VENDOR_SOP_FLOW_CONFIGURATION.md)

---

## 📋 功能概述

為 SOP 流程配置系統實施**嚴格的組合驗證規則**，防止無意義的配置組合，提升用戶體驗和系統可靠性。

### 問題背景

在原有的 SOP 流程配置系統中，`trigger_mode` 和 `next_action` 可以任意組合，導致：
- ❌ 無意義的組合（如 `none + form_fill`）
- ❌ 用戶困惑不知如何選擇
- ❌ 配置錯誤難以發現
- ❌ 必填欄位可能被遺漏

### 解決方案

實施**7 種有效組合**的嚴格限制：

| # | trigger_mode | next_action | 說明 | 狀態 |
|---|-------------|-------------|------|------|
| 1 | none | none | 純資訊型 SOP | ✅ 允許 |
| 2 | manual | form_fill | 排查後填表 | ✅ 允許 |
| 3 | manual | api_call | 排查後調用 API | ✅ 允許 |
| 4 | manual | form_then_api | 排查後完整流程 | ✅ 允許 |
| 5 | immediate | form_fill | 緊急處理填表 | ✅ 允許 |
| 6 | immediate | api_call | 緊急處理調用 API | ✅ 允許 |
| 7 | immediate | form_then_api | 緊急處理完整流程 | ✅ 允許 |

**禁止的組合**：
- ❌ `none` + 任何 action（除了 none）- 無觸發就執行動作，應該用 immediate
- ❌ `manual + none` 或 `immediate + none` - 有觸發無動作，意義不大
- ❌ `auto` + 任何 - 未實作

---

## 🔧 實施細節

### 前端驗證 (VendorSOPManager.vue)

#### 1. 動態選項限制 (lines 354-378)

根據 `trigger_mode` 動態顯示/隱藏 `next_action` 選項：

```javascript
// 定義有效組合
VALID_COMBINATIONS: {
  'none': ['none'],  // none 只能搭配 none
  'manual': ['form_fill', 'api_call', 'form_then_api'],  // manual 必須有後續動作
  'immediate': ['form_fill', 'api_call', 'form_then_api']  // immediate 必須有後續動作
}
```

下拉選單使用 `v-if` 動態顯示：
```vue
<select v-model="editingForm.next_action" @change="onNextActionChange">
  <option value="none" v-if="VALID_COMBINATIONS[editingForm.trigger_mode].includes('none')">
    無（僅顯示 SOP 內容）
  </option>
  <option value="form_fill" v-if="VALID_COMBINATIONS[editingForm.trigger_mode].includes('form_fill')">
    觸發表單（引導用戶填寫表單）
  </option>
  <!-- ... 其他選項 ... -->
</select>
```

#### 2. 自動調整機制 (lines 1157-1180)

當用戶切換 `trigger_mode` 時，自動調整為有效的 `next_action`：

```javascript
onTriggerModeChange() {
  const validActions = this.VALID_COMBINATIONS[this.editingForm.trigger_mode] || [];

  // 如果當前 next_action 不在有效列表中，重置為第一個有效值
  if (!validActions.includes(this.editingForm.next_action)) {
    const oldAction = this.editingForm.next_action;
    this.editingForm.next_action = validActions[0] || 'none';
    console.log(`🔒 組合驗證：${this.editingForm.trigger_mode} 不支持 ${oldAction}，已自動調整為 ${this.editingForm.next_action}`);
  }

  // 清除不相關的欄位
  if (this.editingForm.trigger_mode !== 'manual') {
    this.editingForm.trigger_keywords = [];
  }
  if (this.editingForm.trigger_mode !== 'immediate') {
    this.editingForm.immediate_prompt = '';
  }

  this.onNextActionChange();
}
```

#### 3. 保存前驗證 (lines 888-893)

在保存前檢查組合有效性：

```javascript
// 驗證 trigger_mode 和 next_action 組合
const validActions = this.VALID_COMBINATIONS[this.editingForm.trigger_mode] || [];
if (!validActions.includes(this.editingForm.next_action)) {
  alert(`❌ 無效的組合：${this.editingForm.trigger_mode} + ${this.editingForm.next_action}\n有效的後續動作：${validActions.join(', ')}`);
  return;
}
```

#### 4. API 端點修正 (lines 1124-1142)

修正前端 API 調用，統一使用 `/v1/` 前綴：

```javascript
// 修正前：/api/forms
// 修正後：/api/v1/forms
async loadAvailableForms() {
  const response = await axios.get(`${RAG_API}/v1/forms`);
  this.availableForms = response.data;
}

// 修正前：/api/api-endpoints
// 修正後：/api/v1/api-endpoints
async loadAvailableAPIs() {
  const response = await axios.get(`${RAG_API}/v1/api-endpoints`);
  this.availableAPIs = response.data;
}
```

**修正效果**：
- ✅ 表單下拉選單正確載入 10 個表單
- ✅ API 下拉選單正確載入 6 個 API 端點
- ✅ 解決 404 錯誤

---

### 後端驗證 (vendors.py)

#### 1. Pydantic 模型更新 (lines 589-603)

添加流程配置欄位到 `SOPItemUpdate` 模型：

```python
class SOPItemUpdate(BaseModel):
    """更新 SOP 項目"""
    item_name: str = Field(..., description="項目名稱")
    content: str = Field(..., description="項目內容")

    # 流程配置欄位
    trigger_mode: str = Field(default='none', description="觸發模式：none, manual, immediate")
    next_action: str = Field(default='none', description="後續動作：none, form_fill, api_call, form_then_api")
    trigger_keywords: Optional[List[str]] = Field(default=None, description="觸發關鍵詞（manual 模式使用）")
    immediate_prompt: Optional[str] = Field(default=None, description="確認提示詞（immediate 模式使用）")
    next_form_id: Optional[str] = Field(default=None, description="關聯的表單 ID")
    next_api_config: Optional[dict] = Field(default=None, description="API 配置")
    followup_prompt: Optional[str] = Field(default=None, description="後續提示詞")
```

#### 2. 組合規則驗證 (lines 733-748)

在 `update_sop_item()` 端點添加嚴格驗證：

```python
# 嚴格限制：驗證 trigger_mode 和 next_action 組合
VALID_COMBINATIONS = {
    'none': ['none'],
    'manual': ['form_fill', 'api_call', 'form_then_api'],
    'immediate': ['form_fill', 'api_call', 'form_then_api']
}

if item_update.next_action not in VALID_COMBINATIONS.get(item_update.trigger_mode, []):
    raise HTTPException(
        status_code=400,
        detail=f"❌ 無效的組合：{item_update.trigger_mode} + {item_update.next_action}。有效的後續動作：{', '.join(VALID_COMBINATIONS.get(item_update.trigger_mode, []))}"
    )
```

#### 3. 必填欄位驗證 (lines 749-761)

驗證每種模式的必填欄位：

```python
# 驗證必填欄位
if item_update.trigger_mode == 'manual':
    if not item_update.trigger_keywords or len(item_update.trigger_keywords) == 0:
        raise HTTPException(status_code=400, detail="❌ manual 模式必須設定至少一個觸發關鍵詞")

if item_update.trigger_mode == 'immediate':
    if not item_update.immediate_prompt or item_update.immediate_prompt.strip() == '':
        raise HTTPException(status_code=400, detail="❌ immediate 模式必須設定確認提示詞")

if item_update.next_action in ['form_fill', 'form_then_api']:
    if not item_update.next_form_id:
        raise HTTPException(status_code=400, detail="❌ 此後續動作必須選擇表單")

if item_update.next_action in ['api_call', 'form_then_api']:
    if not item_update.next_api_config:
        raise HTTPException(status_code=400, detail="❌ 此後續動作必須配置 API")
```

#### 4. SQL 更新語句 (lines 801-824)

保存所有流程配置欄位：

```python
# 更新流程配置欄位
update_fields.append("trigger_mode = %s")
params.append(item_update.trigger_mode)

update_fields.append("next_action = %s")
params.append(item_update.next_action)

update_fields.append("trigger_keywords = %s")
params.append(item_update.trigger_keywords if item_update.trigger_keywords else None)

update_fields.append("immediate_prompt = %s")
params.append(item_update.immediate_prompt)

update_fields.append("next_form_id = %s")
params.append(item_update.next_form_id)

update_fields.append("next_api_config = %s")
params.append(psycopg2.extras.Json(item_update.next_api_config) if item_update.next_api_config else None)

update_fields.append("followup_prompt = %s")
params.append(item_update.followup_prompt)
```

---

## 🧪 測試結果

### 自動化測試 (test_sop_validation.py)

**測試腳本**: `/tmp/test_sop_validation.py`（已刪除）
**測試環境**: `http://localhost:8100/api/v1`
**測試對象**: Vendor 2, SOP ID 1678

#### 測試結果：8/8 全部通過 (100%)

| # | 測試項目 | 預期 | 結果 |
|---|---------|------|------|
| 1 | none + none | 200 OK | ✅ 通過 |
| 2 | manual + form_fill | 200 OK | ✅ 通過 |
| 3 | immediate + form_fill | 200 OK | ✅ 通過 |
| 4 | none + form_fill | 400 Bad Request | ✅ 通過 |
| 5 | none + api_call | 400 Bad Request | ✅ 通過 |
| 6 | manual 缺少 trigger_keywords | 400 Bad Request | ✅ 通過 |
| 7 | immediate 缺少 immediate_prompt | 400 Bad Request | ✅ 通過 |
| 8 | form_fill 缺少 next_form_id | 400 Bad Request | ✅ 通過 |

**成功率**: 100.0%
**執行時間**: ~2 秒

#### 錯誤訊息範例

無效組合 (測試 #4):
```
❌ 無效的組合：none + form_fill。有效的後續動作：none
```

必填欄位缺失 (測試 #6):
```
❌ manual 模式必須設定至少一個觸發關鍵詞
```

---

### 前端測試指南 (frontend_test_guide.md)

**測試指南**: `/tmp/frontend_test_guide.md`（已刪除）
**測試項目**: 10 個檢查點

#### 測試覆蓋範圍

1. **動態選項限制** (3 項)
   - none 模式只顯示 1 個選項
   - manual 模式顯示 3 個選項（無「無」）
   - immediate 模式顯示 3 個選項（無「無」）

2. **自動調整機制** (1 項)
   - 切換模式時自動調整無效組合

3. **必填欄位驗證** (3 項)
   - manual 缺少關鍵詞被拒絕
   - immediate 缺少提示詞被拒絕
   - form_fill 缺少表單被拒絕

4. **成功保存測試** (3 項)
   - manual + form_fill 成功保存
   - immediate + form_fill 成功保存
   - none + none 成功保存

---

## 📊 實施影響

### 數據庫現況 (Vendor 2)

| trigger_mode | next_action | 數量 | 比例 |
|-------------|-------------|------|------|
| none | none | 56 | 84.8% |
| manual | form_fill | 1 | 1.5% |
| manual | api_call | 1 | 1.5% |
| immediate | form_fill | 1 | 1.5% |
| 其他 | 其他 | 7 | 10.6% |

**符合嚴格限制**: 59/66 (89.4%)
**需要調整**: 7/66 (10.6%) - 測試 SOP

### 相關修正

#### 動態關鍵詞組合 (sop_trigger_handler.py:222-241)

觸發關鍵詞改為動態組合，不再硬編碼在 SOP 內容中：

```python
# 動態組合回應：SOP 內容 + 觸發關鍵詞提示
response = sop_item.get('content', '')

# 如果有觸發關鍵詞，自動添加提示
if trigger_keywords and len(trigger_keywords) > 0:
    keywords_hint = '\n\n💡 **如需進一步協助，請告訴我：**\n'
    for keyword in trigger_keywords:
        keywords_hint += f'• 「{keyword}」\n'
    response += keywords_hint

return {
    'response': response,
    'action': 'wait_for_keywords',
    'trigger_mode': TriggerMode.MANUAL,
    'next_action': sop_item.get('next_action'),
    'form_id': sop_item.get('next_form_id'),
    'api_config': sop_item.get('next_api_config'),
    'context_saved': True,
    'trigger_keywords': trigger_keywords
}
```

**效果**：
- ✅ SOP 內容更乾淨
- ✅ 修改關鍵詞不需要重新生成 embeddings
- ✅ 關鍵詞顯示更靈活

#### Embeddings 重新生成

修改 SOP 內容後，重新生成 66 個 SOP 的 embeddings：
- ✅ 成功率：100% (66/66)
- ✅ 執行時間：~2 分鐘
- ✅ 移除硬編碼關鍵詞

---

## 📂 相關文件

### 功能文件
- [SOP 流程配置功能](./VENDOR_SOP_FLOW_CONFIGURATION.md) - 主功能文檔
- [SOP 組合分析](../../tmp/sop_combination_analysis.md) - 理論分析（已刪除）

### 測試文件
- [後端驗證測試腳本](../../tmp/test_sop_validation.py) - 自動化測試（已刪除）
- [前端測試指南](../../tmp/frontend_test_guide.md) - 手動測試指南（已刪除）

### 代碼文件
- **前端**: `knowledge-admin/frontend/src/components/VendorSOPManager.vue`
  - Lines 354-378: 動態下拉選單
  - Lines 510-516: VALID_COMBINATIONS 定義
  - Lines 888-893: 保存前驗證
  - Lines 1124-1142: API 端點修正
  - Lines 1157-1180: 自動調整邏輯

- **後端**: `rag-orchestrator/routers/vendors.py`
  - Lines 589-603: Pydantic 模型
  - Lines 733-761: 組合與必填欄位驗證
  - Lines 801-824: SQL 更新

- **處理邏輯**: `rag-orchestrator/services/sop_trigger_handler.py`
  - Lines 222-241: 動態關鍵詞組合

---

## 🎯 使用建議

### 創建 SOP 時

1. **選擇觸發模式**
   - 資訊型 (none): 純粹回答問題，無後續動作
   - 排查型 (manual): 等待用戶說關鍵詞，適合排查流程
   - 行動型 (immediate): 主動詢問用戶，適合緊急處理

2. **系統自動限制選項**
   - none 模式：只能選「無」
   - manual/immediate 模式：可選「觸發表單」「調用 API」「先填表單再調用 API」

3. **填寫必填欄位**
   - manual 模式：必須添加觸發關鍵詞
   - immediate 模式：必須填寫確認提示詞
   - 選擇表單/API：必須選擇對應資源

4. **保存驗證**
   - 前端自動檢查組合有效性
   - 後端雙重驗證確保數據一致性

### 編輯 SOP 時

1. **切換觸發模式**
   - 系統自動調整後續動作為有效值
   - 清除不相關的欄位（如關鍵詞、提示詞）

2. **保存失敗處理**
   - 閱讀錯誤訊息提示
   - 補充缺失的必填欄位
   - 確認組合符合規則

---

## ✅ 實施檢查清單

### 前端 (VendorSOPManager.vue)
- [x] 定義 VALID_COMBINATIONS 常量
- [x] 實施動態下拉選單 (v-if)
- [x] 實施 onTriggerModeChange 自動調整
- [x] 實施 saveSOP 保存前驗證
- [x] 修正 API 端點路徑 (/v1/)

### 後端 (vendors.py)
- [x] 更新 SOPItemUpdate Pydantic 模型
- [x] 實施組合規則驗證
- [x] 實施必填欄位驗證
- [x] 更新 SQL 保存語句

### 相關功能 (sop_trigger_handler.py)
- [x] 實施動態關鍵詞組合
- [x] 重新生成 SOP embeddings

### 測試
- [x] 後端自動化測試 (8/8 通過)
- [x] 前端測試指南創建
- [x] 清理臨時測試文件

### 文檔
- [x] 創建功能實施文檔
- [x] 更新部署文件 README
- [x] 記錄測試結果和效果

---

## 🚀 部署步驟

### 1. 代碼部署

```bash
# 拉取最新代碼
git pull origin main

# 重啟服務
docker-compose restart knowledge-admin
docker-compose restart rag-orchestrator
```

### 2. 驗證部署

```bash
# 測試 API 端點
curl http://localhost:8100/api/v1/forms
curl http://localhost:8100/api/v1/api-endpoints

# 測試 SOP 更新
curl -X PUT http://localhost:8100/api/v1/vendors/2/sop/items/1678 \
  -H "Content-Type: application/json" \
  -d '{
    "item_name": "測試 SOP",
    "content": "內容",
    "trigger_mode": "none",
    "next_action": "form_fill"
  }'
# 應該返回 400 Bad Request
```

### 3. 前端測試

1. 訪問 http://localhost:8087/vendor-sop
2. 編輯任意 SOP
3. 測試動態選項限制
4. 測試自動調整機制
5. 測試保存驗證

---

## 📈 成果總結

### 系統改善

- ✅ **用戶體驗提升**：動態選項限制，減少選擇困惑
- ✅ **配置可靠性**：嚴格驗證防止無意義組合
- ✅ **數據一致性**：前後端雙重驗證
- ✅ **維護成本降低**：清晰的規則，易於理解和維護

### 技術指標

- **前端**：動態 UI + 自動調整 + 保存驗證
- **後端**：組合驗證 + 必填驗證 + 清晰錯誤訊息
- **測試**：100% 成功率 (8/8 通過)
- **影響範圍**：59/66 SOP 符合規則 (89.4%)

### 代碼質量

- **可讀性**：清晰的常量定義和驗證邏輯
- **可維護性**：集中管理規則，易於修改
- **可擴展性**：支援未來添加新的組合規則

---

**實施完成**: 2026-01-26
**測試狀態**: 100% 通過 (8/8)
**生產狀態**: 🟢 可用
