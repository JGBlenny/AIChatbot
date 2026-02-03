# 📋 SOP 觸發模式全面測試計畫

**測試日期**: 2026-02-03
**測試目的**: 驗證所有表單組合場景正常運作
**測試範圍**: KnowledgeView, PlatformSOPEditView, PlatformSOPView, VendorSOPManager

---

## 🎯 測試策略

### 測試維度

1. **後續動作 (next_action)**
   - `none` - 無後續動作
   - `form_fill` - 觸發表單
   - `api_call` - 調用 API
   - `form_then_api` - 表單後調用 API

2. **觸發模式 (trigger_mode)**
   - `NULL` - 無觸發模式 (when next_action='none')
   - `manual` - 排查型
   - `immediate` - 行動型
   - ~~`none`~~ - 已移除

3. **操作類型**
   - 新增
   - 編輯 (現有資料)
   - 編輯 (舊資料 trigger_mode=NULL)
   - 編輯 (舊資料 trigger_mode='none')

4. **測試頁面**
   - KnowledgeView (知識庫管理)
   - PlatformSOPEditView (平台 SOP 編輯)
   - PlatformSOPView (平台 SOP 列表)
   - VendorSOPManager (業者 SOP 管理)

---

## 📊 測試矩陣

### 組合 1: 無後續動作

| next_action | trigger_mode | 應顯示欄位 | 預期結果 |
|-------------|--------------|-----------|---------|
| `none` | `NULL` | 僅後續動作 | ✅ trigger_mode 不顯示 |

**測試步驟**:
1. 選擇「後續動作」= 「無」
2. 確認表單選擇、觸發模式等欄位都不顯示
3. 儲存
4. 重新編輯，確認 trigger_mode = NULL

---

### 組合 2: 觸發表單 - 排查型

| next_action | trigger_mode | trigger_keywords | 應顯示欄位 |
|-------------|--------------|------------------|-----------|
| `form_fill` | `manual` | `["還是不冷", "還是不行"]` | 後續動作、選擇表單、觸發模式、觸發關鍵詞 |

**測試步驟**:
1. 選擇「後續動作」= 「觸發表單」
2. 確認顯示「選擇表單 *」欄位
3. 選擇「報修申請表」
4. 確認顯示「觸發模式 *」欄位，預設為「排查型」✅
5. 確認顯示「觸發關鍵詞 *」欄位
6. 填寫關鍵詞: "還是不冷", "還是不行"
7. 確認「確認提示詞」欄位不顯示
8. 儲存
9. 重新編輯，確認所有欄位值正確

**驗證點**:
- [ ] 欄位顯示順序正確: 後續動作 → 選擇表單 → 觸發模式 → 觸發關鍵詞
- [ ] 觸發模式預設為「排查型」
- [ ] 關鍵詞可以新增多個
- [ ] 控制台顯示 log: `📋 表單選擇後 trigger_mode: manual`
- [ ] 提示文字清晰顯示

---

### 組合 3: 觸發表單 - 行動型

| next_action | trigger_mode | immediate_prompt | 應顯示欄位 |
|-------------|--------------|------------------|-----------|
| `form_fill` | `immediate` | `是否要登記繳租記錄？` | 後續動作、選擇表單、觸發模式、確認提示詞 |

**測試步驟**:
1. 選擇「後續動作」= 「觸發表單」
2. 選擇「繳租登記表」
3. 確認「觸發模式」預設為「排查型」
4. 切換為「行動型」
5. 確認「觸發關鍵詞」欄位消失
6. 確認顯示「確認提示詞（選填）」欄位
7. 填寫提示詞: "是否要登記繳租記錄？"
8. 儲存
9. 重新編輯，確認所有欄位值正確

**驗證點**:
- [ ] 切換觸發模式時，欄位正確切換顯示
- [ ] 關鍵詞欄位消失，提示詞欄位出現
- [ ] 提示詞為選填，可以留空
- [ ] immediate_prompt 正確儲存

---

### 組合 4: 調用 API

| next_action | trigger_mode | 應顯示欄位 |
|-------------|--------------|-----------|
| `api_call` | `NULL` | 後續動作、選擇 API |

**測試步驟**:
1. 選擇「後續動作」= 「調用 API」
2. 確認顯示「選擇 API」欄位
3. 確認「觸發模式」欄位不顯示
4. 選擇一個 API 端點
5. 儲存
6. 重新編輯，確認 trigger_mode = NULL

**驗證點**:
- [ ] API 選擇正常顯示
- [ ] 觸發模式不顯示
- [ ] trigger_mode 儲存為 NULL

---

### 組合 5: 表單後調用 API

| next_action | trigger_mode | 應顯示欄位 |
|-------------|--------------|-----------|
| `form_then_api` | `manual` 或 `immediate` | 後續動作、選擇表單、觸發模式、選擇 API、關鍵詞/提示詞 |

**測試步驟**:
1. 選擇「後續動作」= 「表單後調用 API」(如果有此選項)
2. 選擇表單
3. 確認觸發模式顯示並有預設值
4. 選擇 API
5. 填寫關鍵詞或提示詞
6. 儲存
7. 驗證

**驗證點**:
- [ ] 表單和 API 選擇都顯示
- [ ] 觸發模式邏輯正常

---

## 🔄 編輯舊資料測試

### 場景 1: 編輯 trigger_mode = NULL 的資料

**準備資料**:
```sql
-- 創建測試資料
INSERT INTO knowledge (
    vendor_id, category_id, title, content,
    action_type, form_id, trigger_mode,
    trigger_keywords, immediate_prompt
) VALUES (
    1, 1, '測試-舊資料-NULL',
    '這是舊資料，trigger_mode 為 NULL',
    'form_fill', 1, NULL,
    '[]', NULL
);
```

**測試步驟**:
1. 編輯這筆資料
2. 確認「觸發模式」顯示為「排查型」(fallback 值)✅
3. 不修改直接儲存
4. 檢查資料庫: trigger_mode 應該還是 NULL (因為沒有改變)
5. 修改觸發模式為「行動型」
6. 儲存
7. 檢查資料庫: trigger_mode 應該更新為 'immediate'

**驗證點**:
- [ ] NULL 值正確 fallback 為 'manual'
- [ ] 下拉選單顯示「排查型」
- [ ] 可以正常修改並儲存

---

### 場景 2: 編輯 trigger_mode = 'none' 的資料

**準備資料**:
```sql
-- 創建測試資料 (模擬舊資料)
INSERT INTO knowledge (
    vendor_id, category_id, title, content,
    action_type, form_id, trigger_mode,
    trigger_keywords, immediate_prompt
) VALUES (
    1, 1, '測試-舊資料-none',
    '這是舊資料，trigger_mode 為 none',
    'form_fill', 1, 'none',
    '[]', NULL
);
```

**測試步驟**:
1. 編輯這筆資料
2. 確認「觸發模式」顯示為「排查型」(fallback 值)✅
3. 修改為「行動型」
4. 儲存
5. 檢查資料庫: trigger_mode 應該更新為 'immediate'

**驗證點**:
- [ ] 'none' 值正確 fallback 為 'manual'
- [ ] 下拉選單顯示「排查型」
- [ ] 可以正常修改並儲存

---

### 場景 3: 編輯 trigger_mode = 'manual' 的資料

**準備資料**:
```sql
INSERT INTO knowledge (
    vendor_id, category_id, title, content,
    action_type, form_id, trigger_mode,
    trigger_keywords, immediate_prompt
) VALUES (
    1, 1, '測試-排查型',
    '這是排查型資料',
    'form_fill', 1, 'manual',
    '["還是不冷", "還是不行"]', NULL
);
```

**測試步驟**:
1. 編輯這筆資料
2. 確認「觸發模式」顯示為「排查型」✅
3. 確認「觸發關鍵詞」顯示現有值
4. 不修改直接儲存
5. 重新編輯，確認值沒有變化

**驗證點**:
- [ ] 'manual' 正確顯示
- [ ] 關鍵詞陣列正確顯示
- [ ] 儲存後不會改變

---

### 場景 4: 編輯 trigger_mode = 'immediate' 的資料

**準備資料**:
```sql
INSERT INTO knowledge (
    vendor_id, category_id, title, content,
    action_type, form_id, trigger_mode,
    trigger_keywords, immediate_prompt
) VALUES (
    1, 1, '測試-行動型',
    '這是行動型資料',
    'form_fill', 1, 'immediate',
    '[]', '是否要登記繳租記錄？'
);
```

**測試步驟**:
1. 編輯這筆資料
2. 確認「觸發模式」顯示為「行動型」✅
3. 確認「確認提示詞」顯示現有值
4. 不修改直接儲存
5. 重新編輯，確認值沒有變化

**驗證點**:
- [ ] 'immediate' 正確顯示
- [ ] 提示詞正確顯示
- [ ] 儲存後不會改變

---

## 🎨 UI/UX 測試

### 欄位顯示順序測試

**測試目的**: 確認使用 Flexbox order 後，視覺順序正確

**測試步驟**:
1. 選擇「後續動作」= 「觸發表單」
2. 選擇表單
3. 觀察欄位出現的順序

**預期順序**:
```
1️⃣ 後續動作 * (order: 1)
   ↓
2️⃣ 選擇表單 * (order: 2)
   ↓
3️⃣ 觸發模式 * (order: 3)
   ↓
4️⃣ 觸發關鍵詞 * (order: 4) [僅 manual 模式]
   或
   確認提示詞 (選填) (order: 5) [僅 immediate 模式]
```

**驗證點**:
- [ ] 視覺順序與預期一致
- [ ] 沒有欄位跳動或閃爍
- [ ] 在不同瀏覽器尺寸下順序正確

---

### 提示文字測試

**測試目的**: 確認提示文字清晰易懂

**驗證點**:
- [ ] 排查型提示文字清楚說明排查步驟應該寫在「知識庫內容」
- [ ] 行動型提示文字清楚說明會自動詢問用戶
- [ ] 範例具體且容易理解
- [ ] 格式正確，沒有排版錯誤

---

### 響應式設計測試

**測試目的**: 確認在不同螢幕尺寸下正常顯示

**測試步驟**:
1. 在桌面瀏覽器測試 (1920x1080)
2. 縮小視窗到平板尺寸 (768x1024)
3. 縮小視窗到手機尺寸 (375x667)

**驗證點**:
- [ ] 欄位寬度自適應
- [ ] 文字不會溢出
- [ ] 按鈕可點擊
- [ ] 提示文字完整顯示

---

## 🧪 資料庫驗證測試

### 測試 1: 儲存後資料庫值正確

**測試步驟**:
1. 新增知識庫，選擇「排查型」
2. 儲存後查詢資料庫

**SQL 查詢**:
```sql
SELECT
    id, title,
    action_type,
    form_id,
    trigger_mode,
    trigger_keywords,
    immediate_prompt
FROM knowledge
WHERE title LIKE '測試%'
ORDER BY created_at DESC
LIMIT 5;
```

**驗證點**:
- [ ] trigger_mode = 'manual'
- [ ] trigger_keywords 為 JSON 陣列
- [ ] immediate_prompt 為 NULL

---

### 測試 2: 更新現有資料

**測試步驟**:
1. 編輯現有知識庫，從「排查型」改為「行動型」
2. 儲存後查詢資料庫

**驗證點**:
- [ ] trigger_mode 更新為 'immediate'
- [ ] trigger_keywords 被清空為 `[]`
- [ ] immediate_prompt 正確儲存

---

### 測試 3: 舊資料遷移測試

**準備工作**:
```sql
-- 創建各種舊資料
INSERT INTO knowledge (vendor_id, category_id, title, content, action_type, form_id, trigger_mode)
VALUES
    (1, 1, '測試-NULL', '內容', 'form_fill', 1, NULL),
    (1, 1, '測試-none', '內容', 'form_fill', 1, 'none'),
    (1, 1, '測試-manual', '內容', 'form_fill', 1, 'manual'),
    (1, 1, '測試-immediate', '內容', 'form_fill', 1, 'immediate');
```

**測試步驟**:
1. 逐一編輯每筆資料
2. 確認前端顯示正確
3. 儲存後驗證資料庫

**驗證點**:
- [ ] NULL → 顯示「排查型」(不修改仍為 NULL)
- [ ] 'none' → 顯示「排查型」(不修改仍為 'none')
- [ ] 'manual' → 顯示「排查型」
- [ ] 'immediate' → 顯示「行動型」

---

## 🌐 跨頁面測試

### 頁面 1: KnowledgeView (知識庫管理)

**路徑**: `/knowledge`

**測試場景**:
- [ ] 新增知識庫 - 排查型
- [ ] 新增知識庫 - 行動型
- [ ] 編輯現有知識庫
- [ ] 切換觸發模式
- [ ] 儲存並重新編輯

---

### 頁面 2: PlatformSOPEditView (平台 SOP 編輯)

**路徑**: `/platform-sop/:id/edit`

**測試場景**:
- [ ] 編輯平台 SOP 範本
- [ ] 設定觸發模式為排查型
- [ ] 設定觸發模式為行動型
- [ ] 儲存並驗證

---

### 頁面 3: PlatformSOPView (平台 SOP 列表)

**路徑**: `/platform-sop`

**測試場景**:
- [ ] 新增平台 SOP
- [ ] 內聯編輯 SOP
- [ ] 設定觸發模式
- [ ] 儲存並驗證

---

### 頁面 4: VendorSOPManager (業者 SOP 管理)

**路徑**: `/vendors/:id/configs` → SOP 管理標籤

**測試場景**:
- [ ] 新增業者 SOP
- [ ] 編輯業者 SOP
- [ ] 設定觸發模式
- [ ] 儲存並驗證

---

## 🚨 錯誤處理測試

### 測試 1: 必填欄位驗證

**測試步驟**:
1. 選擇「觸發表單」但不選擇表單
2. 嘗試儲存
3. 確認顯示錯誤訊息

**驗證點**:
- [ ] 表單驗證正確觸發
- [ ] 錯誤訊息清晰

---

### 測試 2: 關鍵詞必填驗證 (排查型)

**測試步驟**:
1. 選擇「排查型」
2. 不填寫關鍵詞
3. 嘗試儲存

**驗證點**:
- [ ] 顯示錯誤: 「排查型模式必須填寫觸發關鍵詞」
- [ ] 無法儲存

---

### 測試 3: 控制台錯誤檢查

**測試步驟**:
1. 開啟開發者工具
2. 執行所有操作
3. 觀察控制台

**驗證點**:
- [ ] 無 Vue 警告
- [ ] 無 JavaScript 錯誤
- [ ] 無 404 錯誤
- [ ] 只有預期的 log 訊息

---

## 📊 測試執行記錄

### 測試環境

- **測試日期**: ___________
- **測試人員**: ___________
- **瀏覽器**: Chrome / Firefox / Safari
- **瀏覽器版本**: ___________
- **測試環境**: http://localhost:8080

---

### 測試結果統計

| 測試類別 | 通過 | 失敗 | 阻塞 | 跳過 |
|---------|------|------|------|------|
| 基本組合測試 (5) | | | | |
| 編輯舊資料測試 (4) | | | | |
| UI/UX 測試 (3) | | | | |
| 資料庫驗證 (3) | | | | |
| 跨頁面測試 (4) | | | | |
| 錯誤處理測試 (3) | | | | |
| **總計 (22)** | | | | |

---

### 發現的問題

| # | 嚴重程度 | 問題描述 | 重現步驟 | 狀態 |
|---|---------|---------|---------|------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

---

## 🔧 自動化測試腳本

為加快測試速度，我們可以準備一些自動化腳本:

### 腳本 1: 準備測試資料

```sql
-- /tmp/prepare_test_data.sql
-- 清理舊測試資料
DELETE FROM knowledge WHERE title LIKE '測試-%';

-- 插入各種測試資料
INSERT INTO knowledge (vendor_id, category_id, title, content, action_type, form_id, trigger_mode, trigger_keywords, immediate_prompt)
VALUES
    -- NULL 觸發模式
    (1, 1, '測試-舊資料-NULL', '排查步驟...', 'form_fill', 1, NULL, '[]', NULL),

    -- none 觸發模式 (舊資料)
    (1, 1, '測試-舊資料-none', '排查步驟...', 'form_fill', 1, 'none', '[]', NULL),

    -- manual 觸發模式
    (1, 1, '測試-排查型-完整', '1. 檢查溫度\n2. 檢查濾網', 'form_fill', 1, 'manual', '["還是不冷", "還是不行"]', NULL),

    -- immediate 觸發模式
    (1, 1, '測試-行動型-完整', '租金繳納方式...', 'form_fill', 1, 'immediate', '[]', '是否要登記繳租記錄？'),

    -- 無後續動作
    (1, 1, '測試-無後續動作', '一般資訊...', 'none', NULL, NULL, '[]', NULL);

-- 顯示結果
SELECT id, title, action_type, trigger_mode, trigger_keywords, immediate_prompt
FROM knowledge
WHERE title LIKE '測試-%'
ORDER BY id DESC;
```

### 腳本 2: 驗證資料庫狀態

```sql
-- /tmp/verify_test_data.sql
SELECT
    id,
    title,
    action_type,
    COALESCE(trigger_mode, 'NULL') AS trigger_mode,
    form_id,
    trigger_keywords,
    immediate_prompt,
    created_at
FROM knowledge
WHERE title LIKE '測試-%'
ORDER BY id DESC;
```

### 腳本 3: 清理測試資料

```sql
-- /tmp/cleanup_test_data.sql
DELETE FROM knowledge WHERE title LIKE '測試-%';
SELECT '已清理測試資料' AS message;
```

---

## 📝 測試執行指令

### 準備測試環境

```bash
# 1. 準備測試資料
psql -h localhost -U aichatbot -d aichatbot_admin -f /tmp/prepare_test_data.sql

# 2. 啟動前端 (如果未啟動)
cd /Users/lenny/jgb/AIChatbot/knowledge-admin/frontend
npm run dev

# 3. 開啟瀏覽器
open http://localhost:8080
```

### 測試過程中驗證

```bash
# 查看測試資料狀態
psql -h localhost -U aichatbot -d aichatbot_admin -f /tmp/verify_test_data.sql

# 查看最近的資料變更
psql -h localhost -U aichatbot -d aichatbot_admin -c "
SELECT id, title, trigger_mode, updated_at
FROM knowledge
WHERE title LIKE '測試-%'
ORDER BY updated_at DESC
LIMIT 5;
"
```

### 測試結束後清理

```bash
# 清理測試資料
psql -h localhost -U aichatbot -d aichatbot_admin -f /tmp/cleanup_test_data.sql
```

---

## ✅ 測試完成檢查清單

### 功能完整性
- [ ] 所有表單組合場景測試完成
- [ ] 舊資料編輯測試完成
- [ ] 新增資料測試完成
- [ ] 資料庫驗證完成

### UI/UX 完整性
- [ ] 欄位顯示順序正確
- [ ] 提示文字清晰
- [ ] 響應式設計正常
- [ ] 無視覺錯誤

### 跨瀏覽器測試
- [ ] Chrome 測試完成
- [ ] Firefox 測試完成
- [ ] Safari 測試完成

### 錯誤處理
- [ ] 表單驗證正常
- [ ] 錯誤訊息清晰
- [ ] 無控制台錯誤

### 文檔
- [ ] 測試結果已記錄
- [ ] 問題已記錄到 Issue
- [ ] 測試報告已完成

---

**測試報告製作者**: ___________
**審查者**: ___________
**批准日期**: ___________
