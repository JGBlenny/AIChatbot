# 知識庫動作系統 - 實作指南

> 完整的分步實作指南，從資料庫遷移到測試驗證

**日期**: 2026-01-16
**相關文檔**:
- [系統設計](./KNOWLEDGE_ACTION_SYSTEM_DESIGN.md)
- [快速參考](./KNOWLEDGE_ACTION_QUICK_REFERENCE.md)
- [實作範例](./KNOWLEDGE_ACTION_IMPLEMENTATION_EXAMPLE.md)

---

## 📋 實作檢查清單

### ✅ 階段 1: 資料庫遷移

- [x] 創建遷移腳本 `add_action_type_and_api_config.sql`
- [ ] 執行資料庫遷移
- [ ] 驗證欄位添加成功
- [ ] 更新現有數據（將 form_id 存在的知識設置為 form_fill）

### ✅ 階段 2: 核心服務層

- [x] 創建 `api_call_handler.py` - API 調用處理器
- [x] 創建 `billing_api.py` - 帳單 API 服務
- [ ] 配置環境變數
- [ ] 測試 API 服務（使用模擬模式）

### ✅ 階段 3: 業務邏輯擴充

- [x] 修改 `form_manager.py` - 添加 `_execute_form_api` 和 `_format_completion_message`
- [x] 修改 `chat.py` - 添加 action_type 路由邏輯和 `_handle_api_call`
- [ ] 重啟服務

### ✅ 階段 4: 配置與測試

- [x] 創建配置腳本 `configure_billing_inquiry_examples.sql`
- [ ] 執行配置腳本
- [ ] 單元測試
- [ ] 集成測試
- [ ] 手動測試所有場景

---

## 🚀 部署步驟

### 步驟 1: 執行資料庫遷移

```bash
cd /Users/lenny/jgb/AIChatbot

# 1. 執行遷移腳本
psql -U your_username -d your_database \
  -f database/migrations/add_action_type_and_api_config.sql

# 2. 驗證結果
psql -U your_username -d your_database -c "
  SELECT column_name, data_type
  FROM information_schema.columns
  WHERE table_name = 'knowledge_base'
    AND column_name IN ('action_type', 'api_config');
"

# 3. 檢查統計
psql -U your_username -d your_database -c "
  SELECT action_type, COUNT(*)
  FROM knowledge_base
  WHERE is_active = true
  GROUP BY action_type;
"
```

### 步驟 2: 配置環境變數

在 `.env` 文件中添加：

```bash
# 帳單 API 配置
BILLING_API_BASE_URL=http://your-billing-api.com
BILLING_API_KEY=your_secret_api_key
BILLING_API_TIMEOUT=10.0

# 開發/測試模式（使用模擬數據）
USE_MOCK_BILLING_API=true

# 生產環境設置為 false
# USE_MOCK_BILLING_API=false
```

### 步驟 3: 安裝依賴

```bash
cd /Users/lenny/jgb/AIChatbot/rag-orchestrator

# 安裝 httpx（如果尚未安裝）
pip install httpx

# 驗證安裝
python -c "import httpx; print(f'httpx version: {httpx.__version__}')"
```

### 步驟 4: 執行配置腳本

```bash
# 插入示例配置
psql -U your_username -d your_database \
  -f database/migrations/configure_billing_inquiry_examples.sql

# 驗證配置
psql -U your_username -d your_database -c "
  SELECT
    id,
    question_summary,
    action_type,
    form_id,
    CASE
      WHEN api_config IS NOT NULL THEN 'Yes'
      ELSE 'No'
    END as has_api_config
  FROM knowledge_base
  WHERE question_summary LIKE '%帳單%' OR question_summary LIKE '%租金%'
  ORDER BY id;
"
```

### 步驟 5: 重啟服務

```bash
# 如果使用 docker-compose
cd /Users/lenny/jgb/AIChatbot
docker-compose restart rag-orchestrator

# 如果直接運行
pkill -f "uvicorn.*rag-orchestrator"
cd rag-orchestrator
uvicorn main:app --host 0.0.0.0 --port 8100 --reload

# 驗證服務啟動
curl http://localhost:8100/health
```

---

## 🧪 測試指南

### 測試環境準備

1. **確保使用模擬 API**：
   ```bash
   export USE_MOCK_BILLING_API=true
   ```

2. **準備測試用戶**：
   - `test_user`: 正常測試用戶（身分證後4碼: 1234）
   - `test_no_data`: 無帳單資料
   - `test_not_sent`: 尚未到發送時間

### 場景測試

#### 場景 A: 純知識問答

```bash
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "租金怎麼繳",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "test_user"
  }'
```

**預期結果**：返回租金繳納方式的知識答案

#### 場景 B: 表單填寫

```bash
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我想租房子",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "test_user",
    "session_id": "test_session_001"
  }'
```

**預期結果**：觸發租屋詢問表單，開始收集資料

#### 場景 C: API 查詢（已登入）

```bash
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我的帳單",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "test_user",
    "session_id": "test_session_002"
  }'
```

**預期結果**：直接調用 API 查詢帳單，返回 API 結果 + 知識答案

#### 場景 D: 表單 + API（未登入）

```bash
# 第1步：觸發表單
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查詢帳單",
    "vendor_id": 1,
    "user_role": "guest",
    "session_id": "test_session_003"
  }'

# 第2步：填寫租客編號
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "test_user",
    "vendor_id": 1,
    "user_role": "guest",
    "session_id": "test_session_003"
  }'

# 第3步：填寫身分證後4碼
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "1234",
    "vendor_id": 1,
    "user_role": "guest",
    "session_id": "test_session_003"
  }'

# 第4步：填寫查詢月份（可選）
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "2026-01",
    "vendor_id": 1,
    "user_role": "guest",
    "session_id": "test_session_003"
  }'
```

**預期結果**：表單完成後自動調用 API，返回帳單資訊

#### 場景 E: 表單 + API（只返回 API 結果）

```bash
# 觸發報修表單
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我要報修",
    "vendor_id": 1,
    "user_role": "customer",
    "user_id": "test_user",
    "session_id": "test_session_004"
  }'

# 後續填寫表單...
```

**預期結果**：表單完成後調用 API，只返回報修單號（不含知識答案）

### 錯誤場景測試

1. **測試 API 失敗降級**：
   ```bash
   # 設置錯誤的 API endpoint
   export BILLING_API_BASE_URL=http://invalid-url
   # 執行查詢，應該返回 fallback_message
   ```

2. **測試缺少參數**：
   ```bash
   # 場景 C 但不提供 user_id
   # 應該返回錯誤提示
   ```

3. **測試身份驗證失敗**：
   ```bash
   # 場景 D 但提供錯誤的身分證後4碼
   # 應該返回身份驗證失敗訊息
   ```

---

## 📊 驗證檢查

### 資料庫檢查

```sql
-- 1. 檢查 action_type 分布
SELECT action_type, COUNT(*)
FROM knowledge_base
WHERE is_active = true
GROUP BY action_type;

-- 2. 檢查 API 配置
SELECT
  id,
  question_summary,
  action_type,
  api_config->>'endpoint' as endpoint,
  api_config->>'combine_with_knowledge' as combine_kb
FROM knowledge_base
WHERE api_config IS NOT NULL;

-- 3. 檢查表單配置
SELECT
  form_id,
  form_name,
  on_complete_action,
  api_config->>'endpoint' as endpoint
FROM form_schemas
WHERE on_complete_action != 'show_knowledge';

-- 4. 檢查表單關聯
SELECT
  kb.id,
  kb.question_summary,
  kb.action_type,
  kb.form_id,
  fs.form_name,
  fs.on_complete_action
FROM knowledge_base kb
LEFT JOIN form_schemas fs ON kb.form_id = fs.form_id
WHERE kb.action_type IN ('form_fill', 'form_then_api');
```

### 服務日誌檢查

啟動服務後，關注以下日誌：

```bash
# 關鍵日誌標記：
# 🔧 - 服務初始化
# 🎯 - action_type 判斷
# 📝 - 表單觸發
# 🔌 - API 調用
# 📞 - 表單完成後 API 調用
# 🧪 - 模擬 API 調用

# 查看實時日誌
docker-compose logs -f rag-orchestrator | grep -E "🔧|🎯|📝|🔌|📞|🧪"
```

---

## 🐛 常見問題排查

### 問題 1: ImportError: No module named 'httpx'

**原因**：缺少 httpx 依賴
**解決**：`pip install httpx`

### 問題 2: action_type 總是 'direct_answer'

**原因**：資料庫遷移未執行或數據未更新
**解決**：
1. 檢查欄位是否存在：`\d knowledge_base`
2. 手動更新：`UPDATE knowledge_base SET action_type='form_fill' WHERE form_id IS NOT NULL;`

### 問題 3: API 調用失敗但沒有降級訊息

**原因**：api_config 中缺少 fallback_message
**解決**：添加 fallback_message 配置

### 問題 4: 表單完成後沒有調用 API

**原因**：form_schemas.on_complete_action 未設置
**解決**：檢查並更新 form_schemas 配置

### 問題 5: 身份驗證總是失敗

**原因**：驗證參數映射錯誤
**解決**：檢查 verification_params 是否正確映射表單欄位

---

## 📝 維護指南

### 添加新的 API Endpoint

1. 在 `billing_api.py` 中添加新方法
2. 在 `api_call_handler.py` 的 `api_registry` 中註冊
3. 配置 knowledge_base 或 form_schemas 的 api_config
4. 測試驗證

### 修改現有場景

1. 更新資料庫配置（knowledge_base 或 form_schemas）
2. 如果修改 api_config 結構，更新處理邏輯
3. 重新測試受影響的場景

### 性能優化

1. **API 調用緩存**：對於高頻查詢，考慮添加快取層
2. **批量查詢**：如果需要多次 API 調用，考慮批量介面
3. **異步優化**：確保所有 I/O 操作都是異步的

---

## 🔄 回滾計劃

如果部署後發現問題，可以按以下步驟回滾：

### 方案 1: 禁用新功能

```sql
-- 暫時禁用所有 API 調用相關的知識
UPDATE knowledge_base
SET is_active = false
WHERE action_type IN ('api_call', 'form_then_api');

-- 暫時禁用所有 API 相關的表單
UPDATE form_schemas
SET is_active = false
WHERE on_complete_action IN ('call_api', 'both');
```

### 方案 2: 完全回滾

```sql
BEGIN;

-- 1. 刪除新增的欄位
ALTER TABLE knowledge_base
DROP COLUMN IF EXISTS action_type,
DROP COLUMN IF EXISTS api_config;

ALTER TABLE form_schemas
DROP COLUMN IF EXISTS on_complete_action,
DROP COLUMN IF EXISTS api_config;

-- 2. 刪除約束
ALTER TABLE knowledge_base
DROP CONSTRAINT IF EXISTS check_action_type;

ALTER TABLE form_schemas
DROP CONSTRAINT IF EXISTS check_on_complete_action;

COMMIT;
```

### 方案 3: 程式碼回滾

```bash
# 回滾到遷移前的版本
git revert <commit_hash>

# 重啟服務
docker-compose restart rag-orchestrator
```

---

## 📚 相關資源

- [系統設計文檔](./KNOWLEDGE_ACTION_SYSTEM_DESIGN.md)
- [快速參考指南](./KNOWLEDGE_ACTION_QUICK_REFERENCE.md)
- [實作範例程式碼](./KNOWLEDGE_ACTION_IMPLEMENTATION_EXAMPLE.md)
- [表單管理系統文檔](../features/FORM_MANAGEMENT_SYSTEM.md)

---

**最後更新**: 2026-01-16
