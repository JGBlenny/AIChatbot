# 知識範圍簡化

## 概述
日期：2026-02-09
狀態：已實施

本文件描述知識範圍邏輯的簡化，從使用獨立的 `scope` 欄位改為基於 vendor_id 的方法，使系統更簡單且更易維護。

## 背景

### 原有實作
系統原本使用複雜的雙欄位方法：
- `scope` 欄位包含值：'global'、'vendor'、'customized'
- `vendor_id` 欄位用於識別業者
- 複雜的 SQL 查詢需檢查兩個欄位
- 不必要的 `scope_weight` 計算用於排序

### 原有方法的問題
1. **冗餘**：scope 欄位是多餘的，因為 vendor_id 本身就能決定範圍
2. **複雜性**：SQL 查詢有不必要的複雜 WHERE 子句
3. **不一致**：設定了 vendor_id 的全域知識無法正確檢索
4. **維護性**：變更範圍邏輯時需要更新多處

## 新實作

### 核心原則
**簡化為僅使用 vendor_id：**
- `vendor_id = NULL`：全域知識（所有業者可見）
- `vendor_id = <id>`：業者專屬知識（僅該業者可見）

### 優點
1. **簡單性**：單一欄位決定知識可見性
2. **清晰度**：清楚直觀的邏輯
3. **效能**：更簡單的 SQL 查詢
4. **可維護性**：進行變更時需要更新的地方更少

## 技術變更

### 1. 資料庫架構
雖然 `scope` 欄位為了向後相容仍保留在資料庫中，但不再用於查詢。

```sql
-- 知識可見性現在僅由 vendor_id 決定
-- NULL vendor_id = 全域知識
-- 非 NULL vendor_id = 業者專屬知識
```

### 2. SQL 查詢簡化

#### 修改前（複雜）
```sql
WHERE (
    (kb.vendor_id = %s AND kb.scope IN ('customized', 'vendor'))
    OR
    (kb.vendor_id IS NULL AND kb.scope = 'global')
)
```

#### 修改後（簡單）
```sql
WHERE (kb.vendor_id = %s OR kb.vendor_id IS NULL)
```

### 3. API 變更

#### 新端點：`/api/vendors`
```python
@app.get("/api/vendors")
async def list_vendors(user: dict = Depends(get_current_user)):
    """取得所有業者列表"""
    # Returns list of vendors with id and name
    # Used for vendor selection in knowledge management UI
```

回應格式：
```json
{
    "vendors": [
        {"id": 1, "name": "業者A"},
        {"id": 2, "name": "業者B"}
    ]
}
```

### 4. 前端變更

#### 知識管理 UI 更新
- 在知識創建/編輯表單中新增業者選擇下拉選單
- 從 UI 中移除 scope 欄位
- 清楚的視覺區別：
  - 🌐 全域知識（所有業者）
  - 🏢 業者專屬知識

#### Vue 元件變更 (KnowledgeView.vue)
```javascript
// 新的資料屬性
availableVendors: [], // 來自 API 的業者列表

// 新方法
async loadVendors() {
    const response = await axios.get('/api/vendors');
    this.availableVendors = response.data.vendors;
}

// 表單欄位
<select v-model="formData.vendor_id">
    <option :value="null">🌐 全域知識（所有業者可見）</option>
    <option v-for="vendor in availableVendors" :key="vendor.id" :value="vendor.id">
        🏢 {{ vendor.name }}（專屬知識）
    </option>
</select>
```

### 5. 後端服務變更

#### vendor_knowledge_retriever.py
- 移除所有 `scope_weight` 計算
- 簡化 WHERE 子句僅使用 vendor_id
- 移除基於 scope 的排序邏輯

#### rag_engine.py
- 更新 8 個不同的 SQL 查詢分支（由於巢狀條件）
- 每個分支現在使用簡單的 vendor_id 檢查
- 移除複雜的 scope 過濾邏輯

#### chat.py
- 從 DebugKnowledgeInfo 類別移除 `scope_weight`
- 清理除錯資訊生成

## 修改的檔案

### 前端
- `/knowledge-admin/frontend/src/views/KnowledgeView.vue`
  - 新增業者選擇 UI
  - 修正 trigger_mode 約束（null 而非 'none'）
  - 新增業者載入邏輯

### 後端 API
- `/knowledge-admin/backend/app.py`
  - 新增 `/api/vendors` 端點

### RAG 服務
- `/rag-orchestrator/services/vendor_knowledge_retriever.py`
  - 簡化 SQL 查詢
  - 移除 scope_weight 邏輯

- `/rag-orchestrator/services/rag_engine.py`
  - 更新 8 個 SQL 查詢分支
  - 簡化業者過濾

- `/rag-orchestrator/routers/chat.py`
  - 從除錯資訊移除 scope_weight
  - 清理回應格式

## 遷移指南

### 現有系統

#### 1. 資料庫遷移（選擇性）
雖然 scope 欄位為相容性而保留，您可以選擇性地更新現有記錄：

```sql
-- 根據 vendor_id 設定 scope（僅供參考，不用於查詢）
UPDATE knowledge_base
SET scope = CASE
    WHEN vendor_id IS NULL THEN 'global'
    ELSE 'vendor'
END;
```

#### 2. 程式碼更新
如果您有參考 scope 邏輯的自訂程式碼：

**要替換的舊模式：**
```python
# 複雜的 scope 檢查
if (vendor_id == target_vendor and scope in ['vendor', 'customized']) or \
   (vendor_id is None and scope == 'global'):
    # 處理知識
```

**新模式：**
```python
# 簡單的 vendor_id 檢查
if vendor_id == target_vendor or vendor_id is None:
    # 處理知識
```

#### 3. API 整合更新
如果使用知識管理 API：
- 更新以使用新的 `/api/vendors` 端點獲取業者列表
- 直接設定 `vendor_id` 而非 `scope` 欄位

### 測試檢查清單

✅ 全域知識（vendor_id = NULL）對所有業者可見
✅ 業者專屬知識僅對指定業者可見
✅ 知識創建與業者選擇功能正常
✅ 知識編輯保留業者指派
✅ 聊天檢索根據業者返回正確知識
✅ 表單觸發使用新範圍邏輯正常運作

## 效能改善

### 查詢複雜度降低
- **修改前**：複雜的巢狀 OR 條件與多欄位檢查
- **修改後**：單一欄位的簡單 OR 條件
- **結果**：更快的查詢執行，更容易的資料庫優化

### 索引優化
簡化的查詢使資料庫能更好地利用索引：
```sql
CREATE INDEX idx_knowledge_vendor ON knowledge_base(vendor_id);
```

## 回滾計畫

如果出現問題，系統可以回滾，因為：
1. scope 欄位保留在資料庫中
2. 舊的 scope 值保持不變
3. 僅修改了查詢邏輯

回滾步驟：
1. 還原受影響檔案的程式碼變更
2. 重啟服務
3. 不需要資料庫變更

## 未來考量

### 潛在增強功能
1. **多業者知識**：允許知識與特定業者群組共享
2. **業者繼承**：階層式業者結構
3. **基於時間的可見性**：知識根據時間變為可見/隱藏

### 棄用時間表
- **第一階段**（目前）：scope 欄位在查詢中被忽略但保留
- **第二階段**（未來）：新安裝中移除 scope 欄位
- **第三階段**（長期）：遷移現有資料並刪除 scope 欄位

## 相關文件
- [知識匯入匯出指南](../guides/KNOWLEDGE_IMPORT_EXPORT_GUIDE.md)
- [API 參考](../api/API_REFERENCE_PHASE1.md)
- [前端使用指南](../guides/FRONTEND_USAGE_GUIDE.md)

## 聯絡方式
關於此變更的問題或議題，請聯絡開發團隊或在專案儲存庫中建立議題。