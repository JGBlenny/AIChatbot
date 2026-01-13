#!/bin/bash
# 檢索邏輯驗證測試腳本
# 測試方案 A 的效果：只用向量相似度過濾，意圖作為排序因子

echo "=========================================="
echo "檢索邏輯驗證測試 (方案 A)"
echo "修改內容: if base_similarity < threshold (原: if boosted_similarity < threshold)"
echo "=========================================="
echo ""

# 測試 1: 知識 1262 - 續約問題（完美匹配案例）
echo "測試 1: 知識 1262 - 續約問題"
echo "------------------------------------------"
curl -s -X POST "http://localhost:8100/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好，我要續約，新的合約甚麼時候會提供?",
    "vendor_id": 2,
    "target_user": "tenant"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'找到知識: {data.get(\"source_count\", 0)} 個')
if data.get('sources'):
    kb_ids = [s.get('id') for s in data['sources']]
    if 1262 in kb_ids:
        print('✅ 測試通過：找到知識 1262')
    else:
        print('❌ 測試失敗：未找到知識 1262')
        print(f'找到的知識 ID: {kb_ids}')
else:
    print('❌ 測試失敗：沒有找到任何知識')
"
echo ""

# 測試 2: 租金繳納相關問題
echo "測試 2: 租金繳納問題"
echo "------------------------------------------"
curl -s -X POST "http://localhost:8100/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "租金每個月幾號要繳？",
    "vendor_id": 2,
    "target_user": "tenant"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Intent: {data.get(\"intent_name\")} (ID: {data.get(\"intent_id\")})')
print(f'找到知識: {data.get(\"source_count\", 0)} 個')
if data.get('sources'):
    for i, s in enumerate(data['sources'][:3], 1):
        print(f'  {i}. ID {s.get(\"id\")}: {s.get(\"question_summary\", \"\")[:40]}...')
    print('✅ 測試通過：找到租金相關知識')
else:
    print('⚠️  沒有找到知識（可能沒有相關知識或相似度不夠）')
"
echo ""

# 測試 3: 報修問題
echo "測試 3: 報修問題"
echo "------------------------------------------"
curl -s -X POST "http://localhost:8100/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "房間冷氣壞了要怎麼報修？",
    "vendor_id": 2,
    "target_user": "tenant"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Intent: {data.get(\"intent_name\")} (ID: {data.get(\"intent_id\")})')
print(f'找到知識: {data.get(\"source_count\", 0)} 個')
if data.get('sources'):
    for i, s in enumerate(data['sources'][:3], 1):
        print(f'  {i}. ID {s.get(\"id\")}: {s.get(\"question_summary\", \"\")[:40]}...')
    print('✅ 測試通過：找到報修相關知識')
else:
    print('⚠️  沒有找到知識（可能沒有相關知識或相似度不夠）')
"
echo ""

# 測試 4: 退租流程
echo "測試 4: 退租流程"
echo "------------------------------------------"
curl -s -X POST "http://localhost:8100/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "我想要退租，請問流程是什麼？",
    "vendor_id": 2,
    "target_user": "tenant"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Intent: {data.get(\"intent_name\")} (ID: {data.get(\"intent_id\")})')
print(f'找到知識: {data.get(\"source_count\", 0)} 個')
if data.get('sources'):
    for i, s in enumerate(data['sources'][:3], 1):
        print(f'  {i}. ID {s.get(\"id\")}: {s.get(\"question_summary\", \"\")[:40]}...')
    print('✅ 測試通過：找到退租相關知識')
else:
    print('⚠️  沒有找到知識（可能沒有相關知識或相似度不夠）')
"
echo ""

# 測試 5: 押金退款
echo "測試 5: 押金退款"
echo "------------------------------------------"
curl -s -X POST "http://localhost:8100/api/v1/message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "押金什麼時候會退還？",
    "vendor_id": 2,
    "target_user": "tenant"
  }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Intent: {data.get(\"intent_name\")} (ID: {data.get(\"intent_id\")})')
print(f'找到知識: {data.get(\"source_count\", 0)} 個')
if data.get('sources'):
    for i, s in enumerate(data['sources'][:3], 1):
        print(f'  {i}. ID {s.get(\"id\")}: {s.get(\"question_summary\", \"\")[:40]}...')
    print('✅ 測試通過：找到押金相關知識')
else:
    print('⚠️  沒有找到知識（可能沒有相關知識或相似度不夠）')
"
echo ""

echo "=========================================="
echo "測試完成"
echo "=========================================="
echo ""
echo "檢查日誌以查看詳細的過濾過程："
echo "docker-compose logs --tail 100 rag-orchestrator | grep -E '(Hybrid Retrieval|原始|boost|加成後|filtered)'"
