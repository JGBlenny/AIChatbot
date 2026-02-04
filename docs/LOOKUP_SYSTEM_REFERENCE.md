# Lookup Table 系統快速參考

## 系統架構

```
用戶輸入
    ↓
Form Manager（表單管理）
    ↓
Universal API Handler（API 調用）
    ↓
Lookup API（查詢服務）
    ↓
PostgreSQL（lookup_tables 表）
```

## 關鍵配置

### 模糊匹配參數

| 參數 | 位置 | 值 | 說明 |
|------|------|-----|------|
| `fuzzy` | Query Parameter | true/false | 是否啟用模糊匹配 |
| `threshold` | Query Parameter | 0.75 | 模糊匹配最低相似度 |
| `ambiguous_threshold` | lookup.py:160 | 0.02 | 多選項檢測閾值 |

### 錯誤類型

| 錯誤類型 | 觸發條件 | 表單行為 |
|----------|----------|----------|
| `ambiguous_match` | 多個相似度接近的匹配 | 保持 COLLECTING 狀態 |
| `no_match` | 無法找到匹配 | 保持 COLLECTING 狀態 |
| `invalid_input` | 輸入格式無效 | 保持 COLLECTING 狀態 |
| 其他錯誤 | 系統錯誤 | 標記為 COMPLETED（失敗）|

## API 端點

### 查詢 Lookup
```http
GET /api/lookup?category=billing_interval&key={地址}&vendor_id=1&fuzzy=true&threshold=0.75
```

**成功回應（精確匹配）：**
```json
{
  "success": true,
  "match_type": "exact",
  "value": "單月",
  "note": "您的電費帳單將於每【單月】寄送。",
  "fuzzy_warning": ""
}
```

**成功回應（模糊匹配）：**
```json
{
  "success": true,
  "match_type": "fuzzy",
  "matched_key": "新北市三重區重陽路3段158號一樓",
  "value": "單月",
  "fuzzy_warning": "⚠️ 注意：您輸入的地址與資料庫記錄不完全相同..."
}
```

**失敗回應（多選項）：**
```json
{
  "success": false,
  "error": "ambiguous_match",
  "suggestions": [
    {"key": "新北市三重區重陽路3段158號四樓", "value": "雙月", "score": 0.97},
    {"key": "新北市三重區重陽路3段158號一樓", "value": "單月", "score": 0.97}
  ],
  "message": "您輸入的地址不夠完整..."
}
```

## 資料庫結構

### lookup_tables 表

```sql
CREATE TABLE lookup_tables (
    id SERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    category VARCHAR(50) NOT NULL,           -- 'billing_interval'
    category_name VARCHAR(100),              -- '電費寄送區間'
    lookup_key TEXT NOT NULL,                -- 地址（已清理）
    lookup_value TEXT NOT NULL,              -- '單月', '雙月', '自繳'
    metadata JSONB,                          -- {"note": "...", ...}
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 資料統計

```sql
-- 查看各類別統計
SELECT lookup_value, COUNT(*)
FROM lookup_tables
WHERE category = 'billing_interval' AND vendor_id = 1
GROUP BY lookup_value;

-- 結果：
-- 單月: 29 筆
-- 雙月: 191 筆
-- 自繳: 27 筆
```

## 故障排除

### 問題：地址無法精確匹配

**檢查步驟：**
1. 查詢資料庫確認地址格式
   ```sql
   SELECT lookup_key FROM lookup_tables
   WHERE lookup_key LIKE '%關鍵字%' AND vendor_id = 1;
   ```

2. 檢查是否有多餘空格或特殊字符
   ```sql
   SELECT LENGTH(lookup_key), lookup_key
   FROM lookup_tables
   WHERE category = 'billing_interval';
   ```

### 問題：模糊匹配返回錯誤結果

**解決方案：**
1. 調高閾值（0.75 → 0.80）
2. 檢查 ambiguous_threshold 設定
3. 清理資料庫地址格式

### 問題：表單無法重試

**檢查日誌：**
```bash
docker-compose logs rag-orchestrator | grep "API 返回.*保持表單狀態"
```

**確認 API 返回：**
- `success`: false
- `error`: "ambiguous_match" | "no_match" | "invalid_input"

## 維護命令

### 清理地址格式

```sql
-- 移除括號內容
UPDATE lookup_tables
SET lookup_key = REGEXP_REPLACE(lookup_key, '\([^)]*\)', '', 'g')
WHERE category = 'billing_interval' AND vendor_id = 1 AND lookup_key ~ '\(';

-- 移除後綴
UPDATE lookup_tables
SET lookup_key = REGEXP_REPLACE(lookup_key, '-租客自繳', '')
WHERE category = 'billing_interval' AND vendor_id = 1 AND lookup_key LIKE '%-租客自繳';
```

### 重新載入資料

```bash
cd /Users/lenny/jgb/AIChatbot
python3 scripts/data_import/import_billing_intervals.py \
  --file data/billing_intervals.xlsx \
  --vendor-id 1
```

## 相關文件

- [完整更新日誌](./CHANGELOG_2026-02-04_lookup_improvements.md)
- [更新摘要](./UPDATES_SUMMARY.md)
- 資料導入腳本：`scripts/data_import/import_billing_intervals.py`

## 聯絡

- 技術問題：參考日誌檔案或聯繫開發團隊
- 資料問題：聯繫資料維護人員
