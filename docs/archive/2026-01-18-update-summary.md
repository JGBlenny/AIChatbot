# 更新摘要 - 方式 2：API 自動格式化

**日期**: 2026-01-18
**版本**: v1.1.0
**核心變更**: 將 API 回應處理從「方式 1（手動格式化）」調整為「方式 2（系統自動格式化）」

---

## 🎯 核心改動（3 分鐘速覽）

### 變更目的
讓 API 只需返回原始數據，由系統統一格式化，提升維護性和一致性。

### 主要修改

#### 1️⃣ `billing_api.py` - API 只返回原始數據

**修改前**：
```python
return {
    'success': True,
    'invoice_id': 'INV-123',
    'message': '✅ **帳單查詢成功**\n\n📅 月份: ...'  # ❌ 自己格式化
}
```

**修改後**：
```python
return {
    'success': True,
    'invoice_id': 'INV-123',
    'month': '2026-01',
    'amount': 15000,
    # ✅ 只返回原始數據，沒有 message
}
```

---

#### 2️⃣ `api_call_handler.py` - 新增自動格式化

**新增函數**：
- `_format_success_data()`: 格式化成功數據
- `_format_error_data()`: 格式化錯誤數據

**核心功能**：
- ✅ 中文欄位映射（`invoice_id` → `帳單編號`）
- ✅ 特殊格式化（金額加千分位：`15000` → `NT$ 15,000`）
- ✅ 自動添加圖示和標題

---

## 📂 文件清單

### 修改的文件（5 個）
1. ✏️ `rag-orchestrator/routers/chat.py` (+191/-30)
2. ✏️ `rag-orchestrator/services/form_manager.py` (+113/-10)
3. ✏️ `rag-orchestrator/services/vendor_knowledge_retriever.py` (+4)
4. ✏️ `rag-orchestrator/services/api_call_handler.py` (+85) ⭐
5. ✏️ `rag-orchestrator/services/billing_api.py` (~50 行修改) ⭐

### 新增的文件（2 個核心 + 2 個 SQL + 8 個文檔）
**核心服務**：
1. ➕ `rag-orchestrator/services/api_call_handler.py` (322 行)
2. ➕ `rag-orchestrator/services/billing_api.py` (328 行)

**資料庫**：
3. ➕ `database/migrations/add_action_type_and_api_config.sql` (164 行)
4. ➕ `database/migrations/configure_billing_inquiry_examples.sql` (381 行)

**文檔**：
5. ➕ `docs/design/API_CONFIGURATION_GUIDE.md`
6. ➕ `docs/design/KNOWLEDGE_ACTION_SYSTEM_DESIGN.md`
7. ➕ 其他 6 份設計文檔...

---

## 🎨 效果對比

### 輸入（API 原始數據）

```python
{
    'success': True,
    'invoice_id': 'INV-test_user-2026-01',
    'month': '2026-01',
    'amount': 15000,
    'sent_date': '2026-01-01',
    'due_date': '2026-01-15',
    'email': 'test_user@example.com'
}
```

### 輸出（系統自動格式化）

```
✅ **查詢成功**

📌 **帳單編號**: INV-test_user-2026-01
📌 **帳單月份**: 2026-01
📌 **金額**: NT$ 15,000
📌 **狀態**: sent
📌 **發送日期**: 2026-01-01
📌 **到期日**: 2026-01-15
📌 **發送郵箱**: test_user@example.com

---

📌 溫馨提醒
如未收到帳單郵件，請檢查垃圾郵件夾。
```

---

## 🔧 如何自訂格式化

### 添加欄位映射

編輯 `rag-orchestrator/services/api_call_handler.py:292`

```python
field_mapping = {
    'invoice_id': '帳單編號',
    'month': '帳單月份',
    'amount': '金額',
    # ✅ 添加你的自訂映射
    'custom_field': '自訂欄位',
}
```

### 添加特殊格式化

編輯 `rag-orchestrator/services/api_call_handler.py:313`

```python
if key == 'amount':
    formatted_value = f'NT$ {value:,}'  # 金額千分位
elif key == 'phone':
    formatted_value = f'{value[:4]}-{value[4:]}'  # 電話格式
# ✅ 添加你的自訂格式化
```

---

## 🚀 快速部署（5 步驟）

### 1. 執行資料庫遷移

```bash
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  -f /docker-entrypoint-initdb.d/migrations/add_action_type_and_api_config.sql
```

### 2. 執行範例配置

```bash
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  -f /docker-entrypoint-initdb.d/migrations/configure_billing_inquiry_examples.sql
```

### 3. 驗證資料庫

```bash
docker exec -it aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  -c "SELECT action_type, COUNT(*) FROM knowledge_base GROUP BY action_type;"
```

### 4. 重啟服務

```bash
docker-compose restart rag-orchestrator
```

### 5. 測試

```bash
curl -X POST http://localhost:8100/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我的帳單",
    "vendor_id": 1,
    "user_id": "test_user",
    "session_id": "test_001"
  }'
```

**預期輸出**：包含「✅ **查詢成功**」、中文欄位標籤、千分位金額

---

## ⚠️ 注意事項

### 重要提醒
1. ✅ 確保 `USE_MOCK_BILLING_API=true`（測試環境）
2. ✅ 新增 API 時，記得更新 `field_mapping`
3. ✅ 錯誤數據需包含 `error_type` 和 `suggestion` 欄位

### 向後兼容
- ✅ 現有知識無需修改
- ✅ 現有表單功能不受影響
- ✅ 資料庫自動遷移

---

## 📊 測試場景

| 場景 | 測試問題 | action_type | 預期行為 |
|------|---------|------------|---------|
| A | 「租金怎麼繳」 | `direct_answer` | 返回知識答案 |
| B | 「我想租房子」 | `form_fill` | 觸發表單 |
| C | 「我的帳單」（已登入） | `api_call` | 調用 API + 自動格式化 |
| D | 「查詢帳單」（訪客） | `form_then_api` | 表單 → API |
| E | 「我要報修」 | `form_then_api` | 表單 → API |

---

## 📚 詳細文檔

- **完整變更規格**: `docs/CHANGELOG_2026-01-18.md` (本文檔的詳細版)
- **API 配置指南**: `docs/design/API_CONFIGURATION_GUIDE.md`
- **系統設計**: `docs/design/KNOWLEDGE_ACTION_SYSTEM_DESIGN.md`

---

## ✅ 檢查清單

**部署前**：
- [ ] 確認 Docker 服務運行
- [ ] 確認資料庫連接正常
- [ ] 確認環境變數已配置（`.env` 包含 `USE_MOCK_BILLING_API=true`）

**部署後**：
- [ ] 資料庫遷移成功
- [ ] 服務重啟無錯誤
- [ ] 場景 A-E 測試通過
- [ ] API 回應包含中文標籤和千分位

---

**最後更新**: 2026-01-18
**版本**: v1.1.0
