# SOP 與意圖快速參考表

## 1. 核心概念速查

### 意圖欄位出現的地方

| 位置 | 表/檢視 | 欄位名 | 類型 | 說明 |
|------|--------|--------|------|------|
| 平台範本 | `platform_sop_templates` | `related_intent_id` | INTEGER (FK) | 平台管理員設定的預設意圖 |
| 業者 SOP | `vendor_sop_items` | `related_intent_id` | INTEGER (FK) | 業者複製後可修改的意圖 |
| 意圖定義 | `intents` | `id` | SERIAL PK | 意圖 ID |
| 意圖定義 | `intents` | `name` | VARCHAR | 意圖名稱（如「租金問詢」） |

### 關鍵 SQL 查詢

**按意圖檢索 SOP**
```sql
SELECT 
  si.id, si.item_name, si.content, si.priority
FROM vendor_sop_items si
WHERE si.vendor_id = :vendor_id
  AND si.related_intent_id = :intent_id
  AND si.is_active = TRUE
ORDER BY si.priority DESC, si.item_number ASC;
```

**查看已設定意圖的所有 SOP**
```sql
SELECT 
  si.id, si.item_name, 
  i.name as intent_name,
  si.priority
FROM vendor_sop_items si
LEFT JOIN intents i ON si.related_intent_id = i.id
WHERE si.vendor_id = :vendor_id
  AND si.related_intent_id IS NOT NULL;
```

**檢查某個意圖有多少個關聯 SOP**
```sql
SELECT 
  i.id, i.name,
  COUNT(si.id) as sop_count
FROM intents i
LEFT JOIN vendor_sop_items si 
  ON i.id = si.related_intent_id 
  AND si.is_active = TRUE
  AND si.vendor_id = :vendor_id
GROUP BY i.id, i.name
ORDER BY sop_count DESC;
```

---

## 2. API 端點快速查詢

### 獲取可用範本
```bash
GET /api/v1/vendors/{vendor_id}/sop/available-templates

Response 包含：
{
  "template_id": 42,
  "item_name": "租金如何繳納",
  "content": "...",
  "related_intent_id": 5,           # ◄── 意圖
  "related_intent_name": "租金問詢"  # ◄── 意圖名稱
  "already_copied": false,
  ...
}
```

### 更新 SOP 項目（含意圖）
```bash
PUT /api/v1/vendors/{vendor_id}/sop/items/{item_id}

Request:
{
  "item_name": "我們的租金規定",
  "content": "租金應於...",
  "related_intent_id": 5,           # ◄── 設定或修改意圖
  "priority": 90
}

Response: 更新後的 SOP 項目
```

### 建立平台範本（含意圖）
```bash
POST /api/v1/platform/sop/templates

Request:
{
  "category_id": 1,
  "item_name": "租金如何繳納",
  "content": "...",
  "related_intent_id": 5,           # ◄── 預設意圖
  "priority": 80,
  "business_type": null             # null = 通用
}
```

### 複製單個範本（自動複製意圖）
```bash
POST /api/v1/vendors/{vendor_id}/sop/copy-template

Request:
{
  "template_id": 42,
  "category_id": 5
}

Response:
{
  "id": 100,
  "item_name": "...",
  "related_intent_id": 5,           # ◄── 自動複製
  "template_id": 42,                # ◄── 記錄來源
  ...
}
```

---

## 3. 前端表單範例

### Vue 中的意圖選擇
```vue
<template>
  <div class="form-group">
    <label>關聯意圖</label>
    <select v-model.number="form.related_intent_id" class="form-control">
      <option :value="null">無</option>
      <option v-for="intent in intents" :key="intent.id" :value="intent.id">
        {{ intent.name }}
      </option>
    </select>
  </div>
</template>

<script>
data() {
  return {
    form: {
      item_name: '',
      content: '',
      related_intent_id: null,      // ◄── 核心欄位
      priority: 50
    },
    intents: []  // 從 API 加載
  }
},
mounted() {
  this.loadIntents();
},
methods: {
  async loadIntents() {
    const response = await axios.get('/api/v1/intents');
    this.intents = response.data;
  }
}
</script>
```

### 顯示意圖標籤
```vue
<template>
  <div class="sop-card">
    <h4>{{ sop.item_name }}</h4>
    
    <!-- 顯示相關意圖 -->
    <span v-if="sop.related_intent_name" class="badge badge-intent">
      🎯 {{ sop.related_intent_name }}
    </span>
  </div>
</template>
```

---

## 4. 常見操作流程

### 流程 A：新增帶意圖的 SOP 範本

1. 平台管理員進入 **PlatformSOPEditView**
2. 點擊「新增 SOP 項目」
3. 填寫表單：
   - item_name: "租金繳納方式"
   - content: "具體內容..."
   - related_intent_id: 5（選擇「租金問詢」）
   - priority: 80
4. 保存 → INSERT platform_sop_templates
5. 業者看到此範本時會看到意圖標籤

### 流程 B：業者複製並修改意圖

1. 業者進入 **VendorSOPManager**
2. 查看可用範本 → 看到帶意圖的範本
3. 複製整份範本或單個範本
4. 進入「我的 SOP」Tab
5. 編輯某個 SOP → 修改 related_intent_id
6. 保存 → UPDATE vendor_sop_items

### 流程 C：根據意圖檢索 SOP

1. 用戶提問：「怎麼繳租金？」
2. NLU 分類為意圖 ID = 5
3. RAG 調用 `retrieve_sop_by_intent(vendor_id=1, intent_id=5)`
4. 後端執行 SQL：
   ```sql
   SELECT * FROM vendor_sop_items
   WHERE vendor_id = 1 
   AND related_intent_id = 5 
   AND is_active = TRUE
   ORDER BY priority DESC
   ```
5. 返回相關 SOP 項目
6. LLM 使用這些 SOP 生成回答

---

## 5. 數據驗證檢查清單

檢查 SOP 與意圖的關聯是否正確：

```sql
-- 檢查 1：所有 vendor_sop_items 的 related_intent_id 是否指向存在的 intent
SELECT si.id, si.item_name, si.related_intent_id
FROM vendor_sop_items si
WHERE si.related_intent_id IS NOT NULL
  AND si.related_intent_id NOT IN (SELECT id FROM intents WHERE is_active = TRUE)
ORDER BY si.vendor_id;

-- 檢查 2：統計每個意圖有多少個 SOP
SELECT 
  i.id, i.name,
  COUNT(si.id) as sop_items,
  COUNT(DISTINCT si.vendor_id) as vendors_using
FROM intents i
LEFT JOIN vendor_sop_items si ON i.id = si.related_intent_id AND si.is_active = TRUE
WHERE i.is_active = TRUE
GROUP BY i.id, i.name
ORDER BY sop_items DESC;

-- 檢查 3：查找未設定意圖的 SOP 項目
SELECT 
  v.name as vendor_name,
  vsc.category_name,
  vsi.item_name,
  vsi.priority
FROM vendor_sop_items vsi
INNER JOIN vendor_sop_categories vsc ON vsi.category_id = vsc.id
INNER JOIN vendors v ON vsi.vendor_id = v.id
WHERE vsi.related_intent_id IS NULL 
  AND vsi.is_active = TRUE
ORDER BY v.name, vsc.category_name;

-- 檢查 4：檢查範本的意圖設定是否被複製
SELECT 
  pt.id as template_id,
  pt.item_name,
  pt.related_intent_id,
  COUNT(vsi.id) as copied_count,
  COUNT(CASE WHEN vsi.related_intent_id = pt.related_intent_id THEN 1 END) as intent_preserved
FROM platform_sop_templates pt
LEFT JOIN vendor_sop_items vsi ON vsi.template_id = pt.id AND vsi.is_active = TRUE
WHERE pt.is_active = TRUE
GROUP BY pt.id, pt.item_name, pt.related_intent_id
ORDER BY copied_count DESC;
```

---

## 6. 故障排除

### 問題：編輯 SOP 時看不到意圖選項

**檢查**：
1. 確認 `intents` 表有活躍的記錄
   ```sql
   SELECT * FROM intents WHERE is_active = TRUE;
   ```
2. 確認前端 `loadIntents()` 方法執行成功
3. 檢查 API 權限

### 問題：複製範本後意圖沒有被複製

**檢查**：
1. 驗證來源範本是否有設定 `related_intent_id`
   ```sql
   SELECT id, item_name, related_intent_id FROM platform_sop_templates WHERE id = :id;
   ```
2. 檢查複製 API 是否保留了意圖
3. 查看業者 SOP 是否有 `related_intent_id`
   ```sql
   SELECT id, item_name, related_intent_id FROM vendor_sop_items WHERE template_id = :id;
   ```

### 問題：意圖檢索沒有返回預期的 SOP

**檢查**：
1. 確認 SOP 已設定意圖
   ```sql
   SELECT COUNT(*) FROM vendor_sop_items 
   WHERE vendor_id = :id AND related_intent_id = :intent_id;
   ```
2. 確認 SOP 是活躍的 (`is_active = TRUE`)
3. 確認優先級設定 (`priority > 0`)

---

## 7. 性能優化提示

### 必須的索引（已創建）
```sql
-- vendor_sop_items 表
CREATE INDEX idx_sop_items_intent ON vendor_sop_items(related_intent_id);
CREATE INDEX idx_sop_items_vendor_intent ON vendor_sop_items(vendor_id, related_intent_id);

-- platform_sop_templates 表
CREATE INDEX idx_platform_sop_templates_intent ON platform_sop_templates(related_intent_id);
```

### 查詢優化技巧
```sql
-- 使用 LIMIT 避免一次性加載過多數據
SELECT * FROM vendor_sop_items 
WHERE vendor_id = :id AND related_intent_id = :intent_id
ORDER BY priority DESC
LIMIT 10;  -- 只返回前 10 個

-- 使用 OFFSET 分頁
SELECT * FROM vendor_sop_items 
WHERE vendor_id = :id
OFFSET :offset LIMIT 20;
```

---

## 8. 實戰例子

### 例子 1：為某業者的「租金問詢」意圖查找最優先的 SOP

```python
# Python/SQLAlchemy 風格
from vendor_sop_retriever import VendorSOPRetriever

retriever = VendorSOPRetriever()
sops = retriever.retrieve_sop_by_intent(
    vendor_id=1,
    intent_id=5,  # 租金問詢
    top_k=5       # 返回前 5 個
)

for sop in sops:
    print(f"{sop['item_name']}: {sop['content'][:100]}...")
```

### 例子 2：統計業者有多少未設定意圖的 SOP

```sql
SELECT 
  v.name,
  COUNT(*) as total_sop,
  SUM(CASE WHEN related_intent_id IS NULL THEN 1 ELSE 0 END) as unlinked_sop
FROM vendor_sop_items vsi
INNER JOIN vendors v ON vsi.vendor_id = v.id
WHERE vsi.is_active = TRUE
GROUP BY v.id, v.name
HAVING SUM(CASE WHEN related_intent_id IS NULL THEN 1 ELSE 0 END) > 0;
```

### 例子 3：同步平台範本的意圖更新到已複製的業者 SOP

```sql
-- 找出範本意圖已改變但業者 SOP 還是舊意圖的記錄
SELECT 
  pt.id as template_id,
  pt.related_intent_id as new_intent,
  vsi.id as vendor_sop_id,
  vsi.related_intent_id as old_intent
FROM platform_sop_templates pt
INNER JOIN vendor_sop_items vsi ON vsi.template_id = pt.id
WHERE pt.related_intent_id != vsi.related_intent_id;

-- 同步更新（可選）
UPDATE vendor_sop_items vsi
SET related_intent_id = pt.related_intent_id
FROM platform_sop_templates pt
WHERE vsi.template_id = pt.id
  AND vsi.related_intent_id != pt.related_intent_id;
```

---

## 9. 開發檢查清單

- [ ] 建立新 SOP 時是否設定了 `related_intent_id`？
- [ ] 複製 SOP 時是否保留了意圖？
- [ ] 更新 SOP 時是否允許修改意圖？
- [ ] 檢索 SOP 時是否正確過濾意圖？
- [ ] 前端是否正確顯示意圖標籤？
- [ ] 是否有建立必要的索引？
- [ ] 是否驗證了意圖 ID 的有效性？
- [ ] 是否測試了 NULL 意圖的情況？

