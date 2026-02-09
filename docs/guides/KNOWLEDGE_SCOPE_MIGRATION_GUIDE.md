# 知識範圍遷移指南

## 執行摘要

本指南提供從舊的基於 scope 的知識可見性系統遷移到新的簡化 vendor_id 方法的逐步說明。

**遷移日期：** 2026-02-09
**影響等級：** 中等
**需要停機時間：** 否

---

## 快速參考

### 修改前（複雜）
```
知識可見性由以下決定：
- scope 欄位（'global', 'vendor', 'customized'）
- vendor_id 欄位
- 複雜的 SQL 查詢檢查兩個欄位
```

### 修改後（簡單）
```
知識可見性由以下決定：
- 僅 vendor_id
  - NULL = 全域（所有業者）
  - 非 NULL = 業者專屬
```

---

## 遷移前檢查清單

- [ ] 備份資料庫
- [ ] 檢視目前知識條目分佈
- [ ] 在測試環境中測試遷移
- [ ] 通知開發團隊
- [ ] 準備回滾計畫

---

## 遷移步驟

### 步驟 1：程式碼更新

#### 1.1 更新前端元件

**檔案：** `/knowledge-admin/frontend/src/views/KnowledgeView.vue`

需要的變更：
1. 新增業者選擇下拉選單
2. 移除 scope 欄位參考
3. 修正 trigger_mode 約束

```javascript
// 新增到 data()
availableVendors: [],

// 新增方法
async loadVendors() {
  try {
    const response = await axios.get('/api/vendors');
    this.availableVendors = response.data.vendors;
  } catch (error) {
    console.error('載入業者失敗：', error);
  }
},

// 更新 formData 初始化
resetFormData() {
  this.formData = {
    question: '',
    answer: '',
    vendor_id: null,  // 取代 scope
    intent_id: null,
    trigger_mode: null  // 不是 'none'
  };
}
```

#### 1.2 更新後端服務

**檔案：** `/rag-orchestrator/services/vendor_knowledge_retriever.py`

替換複雜的 WHERE 子句：
```python
# 舊
WHERE (
    (kb.vendor_id = %s AND kb.scope IN ('customized', 'vendor'))
    OR
    (kb.vendor_id IS NULL AND kb.scope = 'global')
)

# 新
WHERE (kb.vendor_id = %s OR kb.vendor_id IS NULL)
```

**檔案：** `/rag-orchestrator/services/rag_engine.py`

更新所有 8 個 SQL 查詢分支以使用簡化的邏輯：
```python
# 移除 scope_weight 計算
# 在所有條件分支中簡化業者過濾
```

#### 1.3 新增業者 API 端點

**檔案：** `/knowledge-admin/backend/app.py`

```python
@app.get("/api/vendors")
async def list_vendors(user: dict = Depends(get_current_user)):
    """獲取所有業者以供選擇"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT id, name
            FROM vendors
            ORDER BY id
        """)
        vendors = cur.fetchall()

        return {"vendors": vendors}
    finally:
        cur.close()
        conn.close()
```

### 步驟 2：資料庫更新（選擇性）

雖然功能不需要，但您可能想要更新 scope 欄位以保持一致性：

```sql
-- 根據 vendor_id 更新 scope（僅供參考）
UPDATE knowledge_base
SET scope = CASE
    WHEN vendor_id IS NULL THEN 'global'
    ELSE 'vendor'
END
WHERE scope IS NULL OR scope NOT IN ('global', 'vendor');

-- 新增索引以獲得更好的效能
CREATE INDEX IF NOT EXISTS idx_knowledge_vendor
ON knowledge_base(vendor_id);
```

### 步驟 3：服務部署

按此順序部署服務：

1. **資料庫變更**（如有）
   ```bash
   psql -U user -d database -f migration.sql
   ```

2. **後端服務**
   ```bash
   docker-compose down
   docker-compose build rag-orchestrator
   docker-compose build knowledge-admin-api
   docker-compose up -d
   ```

3. **前端**
   ```bash
   cd knowledge-admin/frontend
   npm run build
   docker-compose build knowledge-admin-frontend
   docker-compose up -d knowledge-admin-frontend
   ```

### 步驟 4：驗證

#### 4.1 測試全域知識
```bash
curl -X GET "http://localhost:8100/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "測試全域知識",
    "vendor_id": 1
  }'
```

#### 4.2 測試業者專屬知識
```bash
curl -X GET "http://localhost:8100/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "測試業者專屬知識",
    "vendor_id": 2
  }'
```

#### 4.3 驗證知識創建
1. 登入知識管理 UI
2. 創建新知識條目
3. 從下拉選單選擇業者
4. 驗證正確儲存

---

## 回滾計畫

如果發生問題，回滾很簡單，因為保留了 scope 欄位：

### 立即回滾（< 5 分鐘）

1. **還原程式碼變更**
   ```bash
   git revert <commit-hash>
   ```

2. **重建並重啟服務**
   ```bash
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

3. **不需要資料庫變更** - scope 欄位仍存在

### 遷移後監控

監控這些指標 24 小時：
- 知識檢索準確度
- API 回應時間
- 日誌中的錯誤率
- 使用者回饋

---

## 常見問題與解決方案

### 問題 1：KeyError 'scope_weight'
**原因：** 程式碼仍參考已移除的 scope_weight 欄位
**解決方案：** 確保從以下檔案移除所有 scope_weight 參考：
- chat.py
- rag_engine.py
- vendor_knowledge_retriever.py

### 問題 2：Trigger Mode 約束違反
**原因：** 前端傳送 'none' 而非 null
**解決方案：** 更新前端以傳送 null 值：
```javascript
trigger_mode: null  // 不是 'none'
```

### 問題 3：業者未載入
**原因：** 缺少 /api/vendors 端點或認證問題
**解決方案：**
1. 驗證端點已實作
2. 檢查認證標頭
3. 確保資料庫連線

### 問題 4：錯誤的知識檢索
**原因：** SQL 查詢未正確更新
**解決方案：** 檢視所有 SQL 查詢在：
- vendor_knowledge_retriever.py（1 個位置）
- rag_engine.py（8 個位置，由於巢狀條件）

---

## 遷移後任務

### 第 1 週
- [ ] 監控系統效能
- [ ] 收集使用者回饋
- [ ] 記錄任何問題

### 第 1 個月
- [ ] 效能分析
- [ ] 考慮移除查詢中的 scope 欄位參考
- [ ] 規劃第 2 階段增強功能

### 第 1 季
- [ ] 評估完全移除 scope 欄位
- [ ] 規劃資料庫架構優化
- [ ] 考慮多業者知識功能

---

## 支援與聯絡

遷移支援：
- 技術問題：建立 GitHub 議題
- 緊急問題：聯絡 DevOps 團隊
- 問題：參考[知識範圍簡化](../features/KNOWLEDGE_SCOPE_SIMPLIFICATION.md)

---

## 附錄：SQL 查詢變更

### 修改的查詢完整列表

1. **vendor_knowledge_retriever.py**
   - retrieve_similar_knowledge()
   - 1 個查詢簡化

2. **rag_engine.py**
   - get_relevant_knowledge()
   - 8 個條件分支更新
   - 每個處理不同組合：
     - intent_ids（存在/不存在）
     - target_users（匹配/不匹配）
     - vendor_business_types（匹配/不匹配）

3. **chat.py**
   - 從排序移除 scope_weight
   - 從 DebugKnowledgeInfo 類別移除

### 效能改善

遷移後的預期改善：
- 15-20% 更快的查詢執行
- 更簡單的查詢計畫
- 更好的索引利用
- 降低程式碼複雜度

---

## 版本歷史

- v1.0 (2026-02-09)：初始遷移指南
- 未來更新將在此記錄