# Lookup Table 系統測試指南

**更新日期**: 2026-02-04
**測試業者**: Vendor 1
**數據量**: 220 筆電錶記錄

---

## 📋 測試概覽

本系統用於查詢電費寄送區間（單月/雙月），支持：
- ✅ 精確地址匹配
- ✅ 模糊地址匹配（相似度 0.6 以上）
- ✅ 自動返回電號等元數據

---

## 🎯 測試方式 1: 直接 API 測試（推薦）

### 基本測試

```bash
# 使用 curl 測試
curl "http://localhost:8100/api/lookup?category=billing_interval&key=台北市士林區中山北路六段768號二樓&vendor_id=1"
```

### Python 測試腳本

```python
import requests

response = requests.get(
    "http://localhost:8100/api/lookup",
    params={
        "category": "billing_interval",
        "key": "台北市士林區中山北路六段768號二樓",
        "vendor_id": 1,
        "fuzzy": True,
        "threshold": 0.6
    }
)

result = response.json()
print(f"寄送區間: {result['value']}")
print(f"匹配類型: {result['match_type']}")
print(f"相似度: {result.get('match_score', 1.0)}")
```

### 預期結果

```json
{
  "success": true,
  "match_type": "exact" 或 "fuzzy",
  "match_score": 0.6 - 1.0,
  "category": "billing_interval",
  "key": "輸入的地址",
  "matched_key": "匹配到的地址",
  "value": "單月" 或 "雙月",
  "metadata": {
    "electric_number": "電號"
  }
}
```

---

## 🧪 測試數據

### 推薦測試地址

| 地址 | 預期結果 | 電號 |
|------|---------|------|
| 台北市士林區中山北路六段768號二樓 | 雙月 | 16030591200 |
| 新北市三重區集勇街96號B1 | 雙月 | 05297923087 |
| 台北市萬華區西園路二段283號二樓 | 雙月 | 00694600211 |
| 新北市三重區長元西街1號二樓 | 單月 | 05040835202 |
| 台北市大安區泰順街54巷25號三樓 | 雙月 | 00817543305 |
| 新北市板橋區忠孝路48巷4弄8號二樓 | 雙月 | 01190293108 (模糊匹配) |

### 模糊匹配測試

```bash
# 測試 1: 部分地址
curl "http://localhost:8100/api/lookup?category=billing_interval&key=台北市士林區&vendor_id=1"

# 測試 2: 錯別字
curl "http://localhost:8100/api/lookup?category=billing_interval&key=台北市大安區泰順街54巷25號&vendor_id=1"

# 測試 3: 樓層不同
curl "http://localhost:8100/api/lookup?category=billing_interval&key=新北市板橋區忠孝路48巷4弄8號二樓&vendor_id=1"
# 應匹配: 新北市板橋區忠孝路48巷4弄8號一樓 (相似度 0.94)
```

---

## 🔧 測試方式 2: 通過知識庫對話

### 當前狀態
⚠️ **知識匹配待優化** - RAG 檢索可能被其他知識覆蓋

### 測試步驟（通過知識管理後台）

1. **直接測試知識 ID 1296**
   ```bash
   # 查詢知識詳情
   curl "http://localhost:8100/api/v1/knowledge/1296"
   ```

2. **手動調整優先級**（如需要）
   ```sql
   -- 提高優先級
   UPDATE knowledge_base
   SET priority = 20
   WHERE id = 1296;
   ```

3. **測試對話流程**
   ```bash
   # 發送查詢
   curl -X POST "http://localhost:8100/api/v1/message" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "查詢電費寄送區間",
       "vendor_id": 1,
       "user_role": "customer",
       "user_id": "test_user",
       "session_id": "test_001"
     }'
   ```

### 預期對話流程

```
用戶: 查詢電費寄送區間
系統: [觸發表單 billing_address_form]
      好的！我來協助您查詢電費寄送區間。請提供以下資訊：
      請提供完整的物件地址（例如：新北市板橋區忠孝路48巷4弄8號二樓）

用戶: 台北市士林區中山北路六段768號二樓
系統: [調用 Lookup API 並格式化結果]
      ✅ 查詢成功

      📬 **寄送區間**: 雙月
      💡 您的電費帳單將於每【雙月】寄送。
```

---

## 📊 測試方式 3: API 端點測試

### 1. 查詢類別列表

```bash
curl "http://localhost:8100/api/lookup/categories?vendor_id=1"
```

**預期結果**:
```json
{
  "success": true,
  "vendor_id": 1,
  "categories": [
    {
      "category": "billing_interval",
      "category_name": "電費寄送區間",
      "record_count": 220
    }
  ],
  "total": 1
}
```

### 2. 查詢統計資料

```bash
curl "http://localhost:8100/api/lookup/stats?vendor_id=1&category=billing_interval"
```

**預期結果**:
```json
{
  "success": true,
  "vendor_id": 1,
  "category": "billing_interval",
  "total_records": 220,
  "value_distribution": [
    {"value": "雙月", "count": 191},
    {"value": "單月", "count": 29}
  ]
}
```

---

## 🧪 完整測試腳本

### 自動化測試腳本

```python
#!/usr/bin/env python3
"""
Lookup Table 系統完整測試
"""
import requests
import json

BASE_URL = "http://localhost:8100"
VENDOR_ID = 1

# 測試數據
TEST_CASES = [
    {
        "name": "精確匹配 - 雙月",
        "address": "台北市士林區中山北路六段768號二樓",
        "expected_value": "雙月",
        "expected_match": "exact"
    },
    {
        "name": "精確匹配 - 單月",
        "address": "新北市三重區長元西街1號二樓",
        "expected_value": "單月",
        "expected_match": "exact"
    },
    {
        "name": "模糊匹配 - 樓層不同",
        "address": "新北市板橋區忠孝路48巷4弄8號二樓",
        "expected_value": "雙月",
        "expected_match": "fuzzy",
        "min_score": 0.9
    },
    {
        "name": "模糊匹配 - 部分地址",
        "address": "台北市大安區",
        "expected_match": "fuzzy"
    }
]

def test_lookup_api():
    """測試 Lookup API"""
    print("=" * 60)
    print("🧪 Lookup API 測試")
    print("=" * 60)

    passed = 0
    failed = 0

    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n測試 {i}: {test['name']}")
        print("-" * 60)
        print(f"地址: {test['address']}")

        response = requests.get(
            f"{BASE_URL}/api/lookup",
            params={
                "category": "billing_interval",
                "key": test['address'],
                "vendor_id": VENDOR_ID,
                "fuzzy": True,
                "threshold": 0.6
            }
        )

        if response.status_code != 200:
            print(f"❌ HTTP 錯誤: {response.status_code}")
            failed += 1
            continue

        data = response.json()

        # 驗證結果
        success = True

        if not data.get("success"):
            print(f"❌ 查詢失敗")
            success = False

        if "expected_value" in test and data.get("value") != test["expected_value"]:
            print(f"❌ 寄送區間不符: 預期 {test['expected_value']}, 實際 {data.get('value')}")
            success = False

        if "expected_match" in test and data.get("match_type") != test["expected_match"]:
            print(f"⚠️  匹配類型: 預期 {test['expected_match']}, 實際 {data.get('match_type')}")

        if "min_score" in test:
            score = data.get("match_score", 0)
            if score < test["min_score"]:
                print(f"❌ 相似度過低: {score} < {test['min_score']}")
                success = False

        if success:
            print(f"✅ 測試通過")
            print(f"   寄送區間: {data.get('value')}")
            print(f"   匹配類型: {data.get('match_type')}")
            if data.get('match_score'):
                print(f"   相似度: {data['match_score']:.2f}")
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"測試結果: {passed} 通過, {failed} 失敗")
    print("=" * 60)

    return failed == 0

def test_categories():
    """測試類別查詢"""
    print("\n📋 測試類別查詢")
    print("-" * 60)

    response = requests.get(
        f"{BASE_URL}/api/lookup/categories",
        params={"vendor_id": VENDOR_ID}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 找到 {data['total']} 個類別")
        for cat in data['categories']:
            print(f"   - {cat['category_name']}: {cat['record_count']} 筆")
        return True
    else:
        print(f"❌ 查詢失敗: {response.status_code}")
        return False

def test_stats():
    """測試統計查詢"""
    print("\n📊 測試統計查詢")
    print("-" * 60)

    response = requests.get(
        f"{BASE_URL}/api/lookup/stats",
        params={
            "vendor_id": VENDOR_ID,
            "category": "billing_interval"
        }
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 總記錄數: {data['total_records']}")
        print("   分布:")
        for dist in data['value_distribution']:
            print(f"   - {dist['value']}: {dist['count']} 筆")
        return True
    else:
        print(f"❌ 查詢失敗: {response.status_code}")
        return False

if __name__ == "__main__":
    all_passed = True

    all_passed &= test_lookup_api()
    all_passed &= test_categories()
    all_passed &= test_stats()

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有測試通過！")
    else:
        print("❌ 部分測試失敗")
    print("=" * 60)
```

保存為 `scripts/test_lookup_system.py` 並執行：

```bash
python3 scripts/test_lookup_system.py
```

---

## 📝 測試檢查清單

### API 功能測試
- [ ] 精確匹配查詢
- [ ] 模糊匹配查詢
- [ ] 部分地址查詢
- [ ] 不存在地址查詢（應返回建議）
- [ ] 類別列表查詢
- [ ] 統計資料查詢

### 數據驗證
- [ ] 單月記錄數: 29 筆
- [ ] 雙月記錄數: 191 筆
- [ ] 總記錄數: 220 筆
- [ ] 元數據包含電號

### 性能測試
- [ ] 查詢響應時間 < 500ms
- [ ] 模糊匹配響應時間 < 1s
- [ ] 並發 10 個請求無錯誤

---

## 🐛 故障排除

### 問題 1: API 返回 404
**解決方案**: 檢查服務是否運行
```bash
curl http://localhost:8100/api/v1/health
```

### 問題 2: 查詢無結果
**可能原因**:
1. vendor_id 不匹配（確認使用 vendor_id=1）
2. category 拼寫錯誤（應為 billing_interval）
3. 地址相似度過低（降低 threshold）

**調試方法**:
```bash
# 查看所有數據
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin \
  -c "SELECT * FROM lookup_tables WHERE vendor_id=1 LIMIT 5"
```

### 問題 3: 模糊匹配不准確
**調整相似度閾值**:
```bash
# 降低閾值至 0.4
curl "http://localhost:8100/api/lookup?category=billing_interval&key=地址&vendor_id=1&threshold=0.4"
```

---

## 📞 支援

如有問題，請查看：
- [系統設計文檔](../design/LOOKUP_TABLE_SYSTEM_DESIGN.md)
- [快速參考指南](../guides/reference/LOOKUP_TABLE_QUICK_REFERENCE.md)
- 實現總結

**測試業者**: Vendor 1
**知識 ID**: 1296
**表單 ID**: billing_address_form
**API Endpoint**: lookup_billing_interval
