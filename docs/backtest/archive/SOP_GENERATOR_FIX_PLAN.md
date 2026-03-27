# SOP Generator 修正計劃

## 問題總結

經過完整盤查，發現生成的 SOP 無法被檢索到的兩個根本原因：

###  1. `category_id = NULL`
- **現況**：53 筆 SOP 的 category_id 為 NULL
- **影響**：`vendor_sop_retriever_v2.py` 使用 `INNER JOIN vendor_sop_categories`，會排除所有 category_id = NULL 的記錄
- **檢索條件**：`WHERE sc.is_active = TRUE` → NULL category_id 被排除

### 2. 缺少 Embedding
- **現況**：最近生成的 10 筆 SOP 全部沒有 embedding
- **影響**：檢索器要求 `(primary_embedding IS NOT NULL OR fallback_embedding IS NOT NULL)`
- **結果**：沒有 embedding 的 SOP 完全無法被檢索

## 修正方案

### Phase 1: 添加 category_id 支援

1. **新增方法 `_get_or_create_default_category()`**
   ```python
   async def _get_or_create_default_category(self, vendor_id: int) -> int:
       """獲取或創建默認的 AI 生成知識分類"""
       conn = self.db_pool.getconn()
       try:
           cur = conn.cursor()

           # 嘗試獲取現有的「AI 生成知識」分類
           cur.execute("""
               SELECT id FROM vendor_sop_categories
               WHERE vendor_id = %s
               AND category_name = 'AI 生成知識'
               AND is_active = TRUE
           """, (vendor_id,))

           result = cur.fetchone()
           if result:
               return result[0]

           # 創建新分類
           cur.execute("""
               INSERT INTO vendor_sop_categories (
                   vendor_id,
                   category_name,
                   is_active,
                   created_at,
                   updated_at
               ) VALUES (%s, 'AI 生成知識', TRUE, NOW(), NOW())
               RETURNING id
           """, (vendor_id,))

           category_id = cur.fetchone()[0]
           conn.commit()
           return category_id
       finally:
           self.db_pool.putconn(conn)
   ```

2. **修改 `_persist_sop()` 包含 category_id**
   ```python
   # 獲取默認分類
   category_id = await self._get_or_create_default_category(vendor_id)

   # INSERT 時加入 category_id
   cur.execute("""
       INSERT INTO vendor_sop_items (
           vendor_id,
           category_id,  -- ✅ 加入這個
           item_name,
           content,
           trigger_mode,
           ...
       ) VALUES (%s, %s, %s, %s, %s, ...)
   """, (
       vendor_id,
       category_id,  -- ✅ 傳入 category_id
       sop_data['item_name'],
       ...
   ))
   ```

### Phase 2: 添加 Embedding 生成

1. **新增方法 `_generate_embedding()`**
   ```python
   async def _generate_embedding(self, text: str) -> Optional[List[float]]:
       """使用 Embedding API 生成向量"""
       embedding_api_url = os.getenv('EMBEDDING_API_URL', 'http://localhost:5001/api/v1/embeddings')

       try:
           async with httpx.AsyncClient(timeout=30.0) as client:
               response = await client.post(
                   embedding_api_url,
                   json={"input": text}
               )

               if response.status_code == 200:
                   data = response.json()
                   return data.get('data', [{}])[0].get('embedding')
               else:
                   print(f"   ⚠️  Embedding API 錯誤: {response.status_code}")
                   return None
       except Exception as e:
           print(f"   ⚠️  生成 embedding 失敗: {e}")
           return None
   ```

2. **在 `_persist_sop()` 中生成並存儲 embedding**
   ```python
   # 生成 embedding
   combined_text = f"{sop_data['item_name']}\n\n{sop_data['content']}"
   primary_embedding = await self._generate_embedding(combined_text)

   # INSERT 時加入 embedding
   cur.execute("""
       INSERT INTO vendor_sop_items (
           vendor_id,
           category_id,
           item_name,
           content,
           ...,
           primary_embedding  -- ✅ 加入這個
       ) VALUES (%s, %s, %s, %s, ..., %s)
   """, (
       vendor_id,
       category_id,
       sop_data['item_name'],
       sop_data['content'],
       ...,
       primary_embedding  -- ✅ 傳入 embedding
   ))
   ```

### Phase 3: 測試驗證

1. **單元測試**
   - 驗證 category_id 正確設置
   - 驗證 embedding 成功生成
   - 驗證 SOP 可以被檢索到

2. **集成測試**
   - 運行完整的知識完善迴圈
   - 檢查生成的 SOP 的 category_id
   - 檢查生成的 SOP 的 embedding
   - 測試 SOP 檢索功能

3. **回測驗證**
   - 重新運行回測
   - 驗證通過率提升（預期從 10% 提升到 30%+）

## 預期效果

修復後，新生成的 SOP 將：
1. ✅ 擁有有效的 category_id（指向「AI 生成知識」分類）
2. ✅ 擁有 primary_embedding 向量
3. ✅ 可以被 `vendor_sop_retriever_v2.py` 檢索到
4. ✅ 顯著提升回測通過率

## 實施順序

1. 先實作 category_id 支援（較簡單，立即見效）
2. 再實作 embedding 生成（需要調用外部 API）
3. 最後進行完整測試驗證
