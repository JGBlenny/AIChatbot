#!/bin/bash
# 快速驗證意圖閾值改進功能
# 使用方法: ./scripts/verify_intent_threshold.sh

echo "🧪 意圖閾值改進 - 快速驗證"
echo "================================"
echo ""

# 測試問題
QUESTION="租約條款 租金、押金、租期"

echo "📝 測試問題: $QUESTION"
echo ""

# 發送請求
echo "🔄 發送請求..."
RESPONSE=$(curl -s -X POST http://localhost:8100/api/v1/message \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"$QUESTION\",
    \"vendor_id\": 1,
    \"user_role\": \"customer\",
    \"user_id\": \"quick_verify\"
  }")

# 解析結果
echo "📊 結果:"
echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    intent = data.get('intent_name', 'N/A')
    confidence = data.get('confidence', 0)
    secondary = data.get('secondary_intents', [])

    print(f'  主意圖: {intent}')
    print(f'  信心度: {confidence:.3f}')
    print(f'  次要意圖: {secondary}')

    if intent == '合約規定' and confidence >= 0.8:
        print('\n✅ 驗證通過: 主意圖正確且信心度達標')
    elif intent == 'unclear':
        print('\n⚠️ 注意: 問題被分類為 unclear')
    else:
        print('\n⚠️ 結果可能異常，請檢查')
except Exception as e:
    print(f'❌ 解析失敗: {e}')
    print(sys.stdin.read())
"

echo ""
echo "🔍 檢查過濾日誌..."
echo ""

# 檢查日誌
docker-compose logs rag-orchestrator --tail=10 | grep -E "(Filtered|Promoting|threshold)" | tail -3

echo ""
echo "✅ 驗證完成"
echo ""
echo "💡 提示:"
echo "  - 查看完整測試: python3 test_intent_improvements.py"
echo "  - 查看詳細日誌: docker-compose logs rag-orchestrator -f"
echo "  - 查看改進報告: docs/INTENT_THRESHOLD_IMPROVEMENT_REPORT.md"
