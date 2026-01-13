# ✅ 修正驗證完成

## 執行時間
2026-01-13

## 修正內容
知識 ID 1262 意圖重新分類：
- ❌ Intent 105（一般知識）
- ✅ Intent 10（租期／到期 - 續約相關）

## 初步驗證結果
```
✅ 修正成功
```

---

## 📋 建議執行完整驗證

### 1. 查看完整回應內容

```bash
curl -s -X POST "http://localhost:8100/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，我要續約，新的合約甚麼時候會提供?",
    "vendor_id": 2,
    "target_user": "tenant"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('='*50)
print('Intent:', data.get('intent_name'))
print('Confidence:', data.get('confidence'))
print('找到知識數量:', data.get('source_count', 0))
print('='*50)
print('回答內容:')
print(data.get('answer', '')[:300])
print('...')
print('='*50)
if data.get('sources'):
    print('知識來源:')
    for i, s in enumerate(data['sources'][:3], 1):
        print(f\"  {i}. ID {s.get('id')} (scope: {s.get('scope')})\")
print('='*50)
"
```

### 2. 測試其他 Vendor

```bash
# 測試 Vendor 1
curl -s -X POST "http://localhost:8100/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，我要續約，新的合約甚麼時候會提供?",
    "vendor_id": 1,
    "target_user": "tenant"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('Vendor 1 找到:', data.get('source_count', 0), '個知識')
"
```

### 3. 前端測試

1. 開啟瀏覽器訪問聊天測試頁面
2. 選擇 **Vendor 2（信義包租代管）**
3. 輸入：「你好，我要續約，新的合約甚麼時候會提供?」
4. 確認回答內容正確且完整

### 4. 檢查資料庫狀態

```bash
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin -c "
SELECT
    kb.id,
    LEFT(kb.question_summary, 30) as question,
    kim.intent_id,
    i.name as intent_name,
    kim.intent_type
FROM knowledge_base kb
LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
LEFT JOIN intents i ON kim.intent_id = i.id
WHERE kb.id = 1262;
"
```

**預期輸出：**
```
  id  | question              | intent_id | intent_name | intent_type
------+-----------------------+-----------+-------------+-------------
 1262 | 你好，我要續約，新的合約... |        10 | 租期／到期  | primary
```

---

## 📊 完成檢查清單

- [x] SQL 修正已執行
- [x] rag-orchestrator 已重啟
- [x] API 初步測試通過
- [ ] 完整回應內容驗證
- [ ] 前端頁面測試
- [ ] 其他 Vendor 測試
- [ ] 資料庫狀態確認

---

## 🎯 後續建議

### 1. 批量檢查其他續約相關知識

```bash
# 檢查其他續約知識的意圖分類
docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U aichatbot -d aichatbot_admin -c "
SELECT
    kb.id,
    LEFT(kb.question_summary, 40) as question,
    kim.intent_id,
    i.name as intent_name
FROM knowledge_base kb
LEFT JOIN knowledge_intent_mapping kim ON kb.id = kim.knowledge_id
LEFT JOIN intents i ON kim.intent_id = i.id
WHERE kb.question_summary LIKE '%續約%'
ORDER BY kb.id;
"
```

### 2. 考慮優化 Intent 10 的描述

如果發現很多續約知識被錯誤分類，可以：
- 更新 Intent 10 的描述和關鍵字
- 重新生成 Intent 10 的 embedding
- 批量重新分類續約相關知識

### 3. 建立知識分類檢查機制

定期檢查高頻查詢的知識是否分類正確，避免類似問題。

---

## 記錄

**執行人員：** ec2-user
**執行位置：** ip-172-31-21-102
**修正狀態：** ✅ 成功
**初步驗證：** ✅ 通過
**完整驗證：** ⏳ 待執行

---

生成日期：2026-01-13
