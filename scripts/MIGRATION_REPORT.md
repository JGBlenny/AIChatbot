# 業者參數遷移報告

**日期**: 2025-10-31
**執行人**: Claude Code
**目標**: 將所有業者的 `emergency_repair_hours` 遷移到 `repair_response_time`

---

## 📊 遷移前狀態

### 業者清單
- **業者 1**: emergency_repair_hours = "24小時" → repair_response_time = 24
- **業者 2**: emergency_repair_hours = "2小時內回應" → repair_response_time = 2

### 系統參數定義
- ✅ `repair_response_time` 已在 `system_param_definitions` 中定義
  - 顯示名稱: 報修回應時間
  - 資料類型: number
  - 單位: 小時
  - 預設值: 24

### 知識庫狀態
- ✅ 資料庫中沒有使用 `emergency_repair_hours` 模板變數的知識條目
- ⚠️  初始化 SQL 中有 2 個全域知識使用 `emergency_repair_hours`（已更新）

### 程式碼依賴
- ✅ 沒有找到程式碼中直接引用 `emergency_repair_hours`
- ✅ 僅在初始化 SQL 中有引用（已更新）

---

## 🔧 遷移執行

### 步驟 1: 數值轉換規則
```
"24小時" → 24 (業者 1)
"2小時內回應" → 2 (業者 2)
```

### 步驟 2: 資料庫遷移

#### 2.1 備份
```bash
docker exec aichatbot-postgres pg_dump -U aichatbot -t vendor_configs aichatbot_admin > scripts/vendor_configs_backup.sql
```
- ✅ 備份完成: 186 行

#### 2.2 插入新參數
```sql
INSERT INTO vendor_configs (vendor_id, category, param_key, param_value, data_type, created_at, updated_at)
VALUES
  (1, 'service', 'repair_response_time', '24', 'integer', NOW(), NOW()),
  (2, 'service', 'repair_response_time', '2', 'integer', NOW(), NOW());
```
- ✅ 成功插入 2 筆記錄

#### 2.3 更新顯示資訊
```sql
UPDATE vendor_configs
SET
    display_name = '報修回應時間',
    description = '報修後的預期回應時間',
    unit = '小時'
WHERE param_key = 'repair_response_time';
```
- ✅ 更新 2 筆記錄

#### 2.4 刪除舊參數
```sql
DELETE FROM vendor_configs WHERE param_key = 'emergency_repair_hours';
```
- ✅ 刪除 2 筆記錄

### 步驟 3: 更新初始化 SQL

#### 3.1 更新 `06-vendors-and-configs.sql`
```diff
- (1, 'service', 'emergency_repair_hours', '24小時', 'string', '緊急報修時效', '緊急報修處理時效', NULL)
+ (1, 'service', 'repair_response_time', '24', 'number', '報修回應時間', '報修後的預期回應時間', '小時')

- (2, 'service', 'emergency_repair_hours', '2小時內回應', 'string', '緊急報修時效', '緊急報修處理時效', NULL)
+ (2, 'service', 'repair_response_time', '2', 'number', '報修回應時間', '報修後的預期回應時間', '小時')
```

#### 3.2 更新 `07-extend-knowledge-base.sql`
```diff
- {{emergency_repair_hours}} 內回應
+ {{repair_response_time}} 小時內回應

- '["service_hotline", "service_hours", "emergency_repair_hours"]'
+ '["service_hotline", "service_hours", "repair_response_time"]'
```

### 步驟 4: 清除快取
- ✅ 重啟 RAG Orchestrator 服務清除記憶體快取

---

## ✅ 遷移後驗證

### API 端點測試

#### 業者 1
```bash
curl "http://localhost:8100/api/v1/vendors/1/test"
```
結果:
```json
{
  "repair_response_time": {
    "value": "24",
    "data_type": "integer",
    "unit": "小時",
    "display_name": "報修回應時間",
    "description": "報修後的預期回應時間"
  }
}
```
- ✅ 新參數正確
- ✅ 舊參數已移除

#### 業者 2
```bash
curl "http://localhost:8100/api/v1/vendors/2/test"
```
結果:
```json
{
  "repair_response_time": {
    "value": "2",
    "data_type": "integer",
    "unit": "小時",
    "display_name": "報修回應時間",
    "description": "報修後的預期回應時間"
  }
}
```
- ✅ 新參數正確
- ✅ 舊參數已移除

### 資料庫驗證
```sql
SELECT vendor_id, param_key, param_value, display_name, unit
FROM vendor_configs
WHERE category = 'service'
ORDER BY vendor_id, param_key;
```

結果:
```
vendor_id | param_key            | param_value            | display_name | unit
----------|----------------------|------------------------|--------------|------
1         | repair_response_time | 24                     | 報修回應時間 | 小時
1         | service_hotline      | 02-2345-6789           | 客服專線     |
1         | service_hours        | 週一至週日 09:00-21:00 | 服務時間     |
2         | repair_response_time | 2                      | 報修回應時間 | 小時
2         | service_hotline      | 02-8765-4321           | 客服專線     |
2         | service_hours        | 週一至週五 09:00-18:00 | 服務時間     |
```
- ✅ 舊參數完全移除
- ✅ 新參數正確設定

---

## 📝 後續建議

### 1. 知識庫更新（如需要）
如果有業者特定的知識條目硬編碼了維修時效，建議更新為模板變數：

```sql
-- 範例：將硬編碼的「24小時」改為模板變數
UPDATE knowledge_base
SET
    answer = REPLACE(answer, '24小時內處理', '{{repair_response_time}} 小時內處理'),
    is_template = true,
    template_vars = template_vars || '["repair_response_time"]'::jsonb
WHERE id = 3;
```

### 2. 前端顯示
- ✅ Chat Test 頁面應該自動顯示新參數
- ✅ 業者配置頁面會顯示「報修回應時間」

### 3. 測試清單
- [x] API 端點正確返回新參數
- [x] 舊參數已完全移除
- [x] 資料庫資料一致
- [x] 初始化 SQL 已更新
- [ ] 前端 UI 顯示測試（需手動驗證）
- [ ] AI 回答測試（需手動驗證）

---

## 🔄 回滾方案

如需回滾，執行以下步驟：

### 1. 還原資料
```bash
# 從備份還原
docker exec -i aichatbot-postgres psql -U aichatbot -d aichatbot_admin < scripts/vendor_configs_backup.sql
```

### 2. 還原初始化 SQL
```bash
git checkout database/init/06-vendors-and-configs.sql
git checkout database/init/07-extend-knowledge-base.sql
```

### 3. 重啟服務
```bash
docker restart aichatbot-rag-orchestrator
```

---

## 📂 相關檔案

### 遷移腳本
- `/Users/lenny/jgb/AIChatbot/scripts/migrate_vendor_params.py` - 遷移調查腳本
- `/Users/lenny/jgb/AIChatbot/scripts/migration_output.sql` - 生成的遷移 SQL
- `/Users/lenny/jgb/AIChatbot/scripts/clear_vendor_cache.py` - 快取清除腳本

### 備份檔案
- `/Users/lenny/jgb/AIChatbot/scripts/vendor_configs_backup.sql` - 資料備份

### 更新的檔案
- `/Users/lenny/jgb/AIChatbot/database/init/06-vendors-and-configs.sql` - 業者配置初始化
- `/Users/lenny/jgb/AIChatbot/database/init/07-extend-knowledge-base.sql` - 知識庫初始化

---

## ✅ 遷移結論

**狀態**: 成功完成
**影響範圍**: 2 個業者
**資料損失**: 無
**停機時間**: 約 3 秒（重啟服務）

所有業者參數已成功從 `emergency_repair_hours` 遷移到 `repair_response_time`。新參數使用標準化的數值格式（整數 + 小時單位），便於系統處理和顯示。

---

## 📞 聯絡資訊

如有任何問題或需要協助，請聯繫開發團隊。
