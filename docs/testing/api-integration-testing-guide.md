# ✅ API 整合修正完成 - 測試指南

**修正完成時間**: 2026-01-21
**修正內容**: Knowledge Admin 後端 API 現在完整支援 `action_type` 和 `api_config`

---

## 🎉 已完成的修正

### 1. ✅ Pydantic 模型更新
**檔案**: `/knowledge-admin/backend/app.py` (Line 95-96)

新增欄位：
```python
action_type: Optional[str] = 'direct_answer'
api_config: Optional[dict] = None
```

### 2. ✅ INSERT 語句更新
**檔案**: `/knowledge-admin/backend/app.py` (Line 513, 525-526)

新增插入：
```python
(... action_type, api_config)
VALUES (... %s, %s)
...
data.action_type,
Json(data.api_config) if data.api_config else None
```

### 3. ✅ UPDATE 語句更新
**檔案**: `/knowledge-admin/backend/app.py` (Line 374-375, 388-389)

新增更新：
```python
SET
  ...
  action_type = %s,
  api_config = %s,
  ...
```

### 4. ✅ Import 更新
**檔案**: `/knowledge-admin/backend/app.py` (Line 10)

加入：
```python
from psycopg2.extras import RealDictCursor, Json
```

### 5. ✅ 服務重啟
- aichatbot-knowledge-admin-api 已重啟 ✅
- aichatbot-knowledge-admin-web 已重啟 ✅

---

## 🧪 測試步驟

### 測試 1: 新增知識 + API 關聯 🔴 **必做**

#### 操作步驟

1. **開啟前端**
   ```
   http://localhost:8087/
   ```

2. **進入知識管理**
   - 點擊左側選單「知識管理」

3. **點擊新增**
   - 點擊右上角「新增知識」按鈕

4. **填寫基本資訊**
   - **問題摘要**: `測試 API 整合功能`
   - **知識內容**: `這是一個測試，用來驗證 API 關聯是否能正確保存。`
   - **關鍵字**: `測試, API`

5. **設定 API 關聯** 🎯 **關鍵步驟**
   - **關聯功能**: 從下拉選單選擇 `API（調用 API 查詢即時資訊）`
   - **選擇 API Endpoint**: 選擇 `test_timeout - 測試超時 ⏱️`

6. **儲存**
   - 點擊「儲存」按鈕
   - 應該看到 ✅ 成功訊息

#### 驗證結果

執行以下命令檢查資料庫：

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT id, question_summary, action_type,
   jsonb_pretty(api_config) as api_config
   FROM knowledge_base
   WHERE question_summary = '測試 API 整合功能';"
```

#### ✅ 預期結果

```
action_type: 'api_call'
api_config: {
  "endpoint": "test_timeout",
  "params": {},
  "combine_with_knowledge": true
}
```

#### ❌ 如果失敗

如果看到：
```
action_type: 'direct_answer'
api_config: NULL
```

表示修正未生效，需要檢查：
1. 服務是否正確重啟
2. 修改的程式碼是否正確
3. 查看後端日誌：`docker logs aichatbot-knowledge-admin-api`

---

### 測試 2: 編輯現有知識 + 修改 API 關聯 🟡 **建議執行**

#### 操作步驟

1. **編輯剛建立的知識**
   - 在知識列表中找到「測試 API 整合功能」
   - 點擊「編輯」

2. **確認 API 關聯顯示正確**
   - 關聯功能應該顯示「API」
   - API Endpoint 應該顯示「test_timeout」

3. **修改 API 端點**
   - 將 API Endpoint 改為 `example_user_info - 用戶資訊查詢（示例）👤`

4. **儲存並驗證**

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT id, question_summary, action_type,
   jsonb_pretty(api_config) as api_config
   FROM knowledge_base
   WHERE question_summary = '測試 API 整合功能';"
```

#### ✅ 預期結果

```
api_config: {
  "endpoint": "example_user_info",
  "params": {},
  "combine_with_knowledge": true
}
```

---

### 測試 3: 取消 API 關聯 🟢 **可選**

#### 操作步驟

1. **編輯知識**
2. **關聯功能改為「無（僅回答知識庫內容）」**
3. **儲存**

#### ✅ 預期結果

```
action_type: 'direct_answer'
api_config: NULL
```

---

### 測試 4: 編輯現有 API 關聯知識 🟡 **建議執行**

#### 操作步驟

1. **編輯現有記錄**
   - 編輯 ID 1265「我的帳單在哪裡」

2. **確認載入正確**
   - 關聯功能應該顯示「API」
   - API Endpoint 應該顯示「billing_inquiry」

3. **修改內容（不修改 API 關聯）**
   - 修改知識內容
   - 保持 API 關聯不變

4. **儲存並驗證**

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT action_type, jsonb_pretty(api_config)
   FROM knowledge_base
   WHERE id = 1265;"
```

#### ✅ 預期結果

API 關聯設定應該保持不變，不會被清空。

---

## 🎯 快速驗證命令

### 查看所有 API 關聯的知識

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT id, question_summary, action_type
   FROM knowledge_base
   WHERE action_type IN ('api_call', 'form_then_api')
   ORDER BY id DESC;"
```

### 查看特定知識的完整資訊

```bash
# 替換 <ID> 為實際的知識 ID
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT id, question_summary, action_type,
   jsonb_pretty(api_config) as api_config
   FROM knowledge_base
   WHERE id = <ID>;"
```

### 統計各種 action_type 的數量

```bash
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \
  "SELECT action_type, COUNT(*) as count
   FROM knowledge_base
   GROUP BY action_type
   ORDER BY count DESC;"
```

---

## 📊 測試檢查清單

請完成以下測試並打勾：

- [ ] 測試 1: 新增知識 + API 關聯
  - [ ] 前端操作成功
  - [ ] 資料庫驗證通過（action_type = 'api_call'）
  - [ ] api_config 包含正確的 endpoint

- [ ] 測試 2: 編輯知識 + 修改 API 關聯
  - [ ] 正確載入現有 API 設定
  - [ ] 修改後正確保存

- [ ] 測試 3: 取消 API 關聯
  - [ ] action_type 改回 'direct_answer'
  - [ ] api_config 變為 NULL

- [ ] 測試 4: 編輯現有 API 關聯知識
  - [ ] 載入正確
  - [ ] 保存後不會遺失 API 設定

---

## 🚀 對話流程測試（進階）

如果基本測試都通過，可以進行實際對話測試：

### 前置條件

確保測試知識的意圖映射正確設定。

### 測試步驟

1. 使用 API 測試工具（如 Postman）或前端聊天介面
2. 提問觸發剛建立的知識（例如：「測試 API」）
3. 觀察回應是否包含 API 調用結果

### 預期結果

- 系統應該觸發 API 調用
- 回應包含 API 結果或超時訊息（test_timeout 會模擬超時）

---

## ❓ 問題排查

### 問題 1: 保存後 api_config 仍然是 NULL

**可能原因**:
- 服務未正確重啟
- 前端發送的資料格式不正確

**排查步驟**:
1. 檢查後端日誌：`docker logs aichatbot-knowledge-admin-api`
2. 檢查前端 Console 是否有錯誤
3. 確認前端發送的資料包含 `action_type` 和 `api_config`

### 問題 2: 編輯時 API 端點顯示空白

**可能原因**:
- 前端載入邏輯問題
- 舊資料格式不一致

**解決方案**:
- 檢查前端 Console 的載入日誌
- 確認 `api_config.endpoint` 欄位存在

### 問題 3: 儲存時出現錯誤

**可能原因**:
- SQL 語法錯誤
- Json 轉換問題

**解決方案**:
- 查看後端日誌詳細錯誤訊息
- 確認 `from psycopg2.extras import Json` 已正確導入

---

## 📝 測試報告模板

測試完成後，請記錄結果：

```
測試日期: ____________________
測試人: ____________________

測試 1: 新增知識 + API 關聯
結果: □ 通過  □ 失敗
備註: ________________________________

測試 2: 編輯知識 + 修改 API 關聯
結果: □ 通過  □ 失敗
備註: ________________________________

測試 3: 取消 API 關聯
結果: □ 通過  □ 失敗
備註: ________________________________

測試 4: 編輯現有 API 關聯知識
結果: □ 通過  □ 失敗
備註: ________________________________

整體結論:
□ 所有測試通過，修正成功
□ 部分測試失敗，需要進一步調查

問題記錄:
________________________________
________________________________
________________________________
```

---

## 🎉 成功標準

當以下條件都滿足時，視為修正成功：

1. ✅ 可以透過前端 UI 新增帶有 API 關聯的知識
2. ✅ 資料庫中正確保存 `action_type = 'api_call'`
3. ✅ 資料庫中正確保存 `api_config` 包含 endpoint
4. ✅ 可以編輯並修改 API 關聯
5. ✅ 編輯現有知識時不會遺失 API 設定

---

**文件版本**: 1.0
**最後更新**: 2026-01-21
**狀態**: ✅ 修正完成，等待測試驗證
