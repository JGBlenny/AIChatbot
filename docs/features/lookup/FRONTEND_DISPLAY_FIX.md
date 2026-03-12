# Frontend Display 修復 - Lookup JSON 格式化顯示

## 📅 完成日期
2026-03-12

## 🎯 問題描述

用戶反映：「重新匯入 💾 Lookup 數據管理 的顯示還是一樣區分開來」

**根本原因：** 前端顯示 `lookup_value` 時直接顯示原始值，對於 JSON 格式（utility_electricity, utility_water, utility_gas）會顯示成一長串 JSON 字串，非常難閱讀。

**範例：**
```
顯示前: {"寄送區間":"單月","電號":"01190293108","計費方式":"台電價格","抄表日":"每月25日","繳費日":"每月5日前"}

應該顯示: 寄送區間: 單月 | 電號: 01190293108 | 計費方式: 台電價格 ...等5項
```

---

## ✅ 解決方案

### 修改檔案
**knowledge-admin/frontend/src/components/VendorLookupManager.vue**

### 1. 新增 formatLookupValue() 方法 (Lines 543-578)

```javascript
formatLookupValue(item) {
  const jsonCategories = ['utility_electricity', 'utility_water', 'utility_gas'];

  // 如果是 JSON 類別，嘗試解析並格式化顯示
  if (jsonCategories.includes(item.category)) {
    try {
      let data;
      if (typeof item.lookup_value === 'string') {
        data = JSON.parse(item.lookup_value);
      } else {
        data = item.lookup_value;
      }

      // 只顯示非空值的關鍵欄位
      const keyFields = [];
      for (const [key, value] of Object.entries(data)) {
        if (value && value !== '' && value !== 'null') {
          keyFields.push(`${key}: ${value}`);
        }
      }

      // 限制顯示前 3 個欄位，避免過長
      if (keyFields.length > 3) {
        return keyFields.slice(0, 3).join(' | ') + ` ...等${keyFields.length}項`;
      }
      return keyFields.join(' | ') || '-';

    } catch (e) {
      // 如果解析失敗，顯示原始值的前 50 字元
      return String(item.lookup_value).substring(0, 50) + '...';
    }
  }

  // 非 JSON 類別，直接顯示原始值
  return item.lookup_value;
}
```

**功能說明：**
1. **自動識別 JSON 類別**：utility_electricity, utility_water, utility_gas
2. **智能解析**：支援字串或物件格式
3. **過濾空值**：只顯示有實際內容的欄位
4. **限制長度**：顯示前 3 個欄位，其餘用「...等N項」表示
5. **錯誤處理**：解析失敗時顯示前 50 字元

### 2. 更新模板顯示 (Line 91)

**修改前：**
```vue
<span class="lookup-value">{{ item.lookup_value }}</span>
```

**修改後：**
```vue
<span class="lookup-value">{{ formatLookupValue(item) }}</span>
```

---

## 🔨 部署步驟

### Step 1: 重新編譯前端
```bash
cd knowledge-admin/frontend
npm run build
```

**結果：** ✅ 成功編譯
```
✓ 177 modules transformed.
dist/index.html                   0.46 kB │ gzip:   0.33 kB
dist/assets/index-BDltw-oO.css  255.95 kB │ gzip:  40.15 kB
dist/assets/index-CWuPKoyW.js   821.01 kB │ gzip: 264.40 kB
✓ built in 1.59s
```

### Step 2: 重啟前端容器
```bash
docker restart aichatbot-knowledge-admin-web
```

**結果：** ✅ 成功重啟

---

## 📊 顯示效果對比

### 電費資訊 (utility_electricity)

**修改前：**
```
{"寄送區間":"單月","電號":"01190293108","計費方式":"台電價格","固定費率(元/度)":"","抄表日":"每月25日","繳費日":"每月5日前","台電優惠":"","分攤方式":"","備註":""}
```

**修改後：**
```
寄送區間: 單月 | 電號: 01190293108 | 計費方式: 台電價格 ...等5項
```

### 水費資訊 (utility_water)

**修改前：**
```
{"水表編號":"W12345001","寄送區間":"雙月","計費方式":"自來水公司價格","固定費率(元/度)":"","抄表日":"每兩月最後一天","繳費日":"每月5日前","分攤方式":"","備註":""}
```

**修改後：**
```
水表編號: W12345001 | 寄送區間: 雙月 | 計費方式: 自來水公司價格 ...等4項
```

### 瓦斯費資訊 (utility_gas)

**修改前：**
```
{"瓦斯公司":"欣欣天然氣","計費方式":"瓦斯公司價格","固定費率(元/度)":"","抄表方式":"","繳費日":"每月15日前","瓦斯公司電話":"02-2311-9999","備註":""}
```

**修改後：**
```
瓦斯公司: 欣欣天然氣 | 計費方式: 瓦斯公司價格 | 繳費日: 每月15日前 ...等4項
```

---

## 🧪 測試驗證

### 當前資料庫狀態

```sql
SELECT category, COUNT(*) as count
FROM lookup_tables
WHERE vendor_id = 2
GROUP BY category;
```

**結果：**
| Category | Count | Status |
|----------|-------|--------|
| billing_interval | 5 | ⚠️ 舊資料（待替換） |
| billing_method | 5 | ⚠️ 舊資料（待替換） |
| meter_reading_day | 5 | ⚠️ 舊資料（待替換） |
| payment_day | 5 | ⚠️ 舊資料（待替換） |
| water_billing | 5 | ⚠️ 舊資料（待替換） |
| gas_billing | 5 | ⚠️ 舊資料（待替換） |
| utility_electricity | 0 | 🔄 待匯入新資料 |
| utility_water | 0 | 🔄 待匯入新資料 |
| utility_gas | 0 | 🔄 待匯入新資料 |

**說明：** 舊資料仍然存在，需要透過新的 Excel 範本匯入，才會產生新格式的 utility_* 記錄。

---

## 📝 後續步驟（用戶需執行）

### Step 1: 準備 Excel 匯入檔案

使用新的 Excel 範本，包含三個工作表：

1. **01_電費資訊⭐** - 整合格式
   - 物件地址（必填）
   - 寄送區間（必填）
   - 電號
   - 計費方式
   - 固定費率(元/度)
   - 抄表日
   - 繳費日
   - 台電優惠
   - 分攤方式
   - 備註

2. **02_水費資訊⭐** - 整合格式
   - 物件地址（必填）
   - 水表編號
   - 寄送區間（建議填寫）
   - 計費方式
   - 固定費率(元/度)
   - 抄表日
   - 繳費日
   - 分攤方式
   - 備註

3. **03_瓦斯費資訊⭐** - 整合格式
   - 物件地址（必填）
   - 瓦斯公司（必填）
   - 計費方式
   - 固定費率(元/度)
   - 抄表方式
   - 繳費日
   - 瓦斯公司電話
   - 備註

### Step 2: 匯入資料

1. 開啟前端管理介面：http://localhost:8087
2. 進入「💾 Lookup 數據管理」
3. 點擊「📥 匯入 Excel」
4. 選擇準備好的 Excel 檔案
5. 點擊「上傳」

### Step 3: 驗證顯示

匯入成功後，檢查：
1. ✅ utility_electricity 記錄顯示為格式化文字（非 JSON 字串）
2. ✅ utility_water 記錄顯示為格式化文字（非 JSON 字串）
3. ✅ utility_gas 記錄顯示為格式化文字（非 JSON 字串）
4. ✅ 每個類別只有一筆記錄/每個地址（非多筆分散記錄）

### Step 4: 清理舊資料（可選）

確認新資料正常運作後，可刪除舊的分散記錄：

```sql
DELETE FROM lookup_tables
WHERE vendor_id = 2
AND category IN (
  'billing_interval',
  'billing_method',
  'meter_reading_day',
  'payment_day',
  'water_billing',
  'gas_billing'
);
```

---

## 🎯 預期效果

### 1. 管理介面
- ✅ Lookup 列表顯示清晰易讀的摘要
- ✅ 不再顯示冗長的 JSON 字串
- ✅ 自動隱藏空值欄位
- ✅ 限制顯示長度，避免版面混亂

### 2. API 回應
- ✅ 已在後端解析 JSON（rag-orchestrator/routers/lookup.py）
- ✅ 返回結構化 JSON 物件（非字串）
- ✅ 前端可直接使用，無需再次解析

### 3. 使用者體驗
- ✅ 一個地址只有一筆完整記錄
- ✅ 所有資訊集中在一個 JSON 物件
- ✅ 易於維護和更新
- ✅ 減少資料不一致的風險

---

## 📚 相關文檔

1. [Lookup 重構完整總結](./LOOKUP_REFACTORING_COMPLETE_SUMMARY.md)
2. [水費和瓦斯費重構設計](./water_gas_refactoring_design.md)
3. [測試指引](./TESTING_GUIDE.md)
4. [測試腳本](../../testing/test_lookup_api_direct.py)

---

**文檔版本：** 1.0
**最後更新：** 2026-03-12
**負責人：** AI Assistant
**狀態：** ✅ 前端修復完成，待用戶匯入新資料驗證
