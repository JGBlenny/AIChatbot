#!/bin/bash
# 執行指定 Loop 的下一次迭代
# 使用方式：./run_next_iteration.sh <loop_id>
#
# ⚠️  WARNING: 此功能目前無法使用
# 原因：LoopCoordinator 不支援載入現有 loop 後繼續執行迭代
# 狀態：待實作 (見 docs/backtest/IMPLEMENTATION_GAPS.md)
#
# 暫時替代方案：
#   1. 執行 ./run_50_verification.sh 建立新 loop
#   2. 前端審核知識
#   3. 再次執行 ./run_50_verification.sh 建立另一個 loop
#   4. 手動比較兩個 loop 的通過率差異

set -e

LOOP_ID=$1

if [ -z "$LOOP_ID" ]; then
    echo "請提供 Loop ID"
    echo "使用方式：$0 <loop_id>"
    echo ""
    echo "查詢最新 Loop ID："
    docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -t -c \
        "SELECT id FROM knowledge_completion_loops ORDER BY id DESC LIMIT 1;"
    exit 1
fi

echo "========================================="
echo "執行 Loop #$LOOP_ID 的下一次迭代"
echo "========================================="
echo ""

# 檢查 OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ 錯誤：OPENAI_API_KEY 未設定"
    echo ""
    echo "請執行以下命令設定 API Key："
    echo "  export OPENAI_API_KEY='your-api-key-here'"
    echo ""
    exit 1
fi

echo "✅ OpenAI API Key 已設定"
echo ""

# 查詢當前迭代狀態
echo "📊 查詢 Loop 狀態..."
docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -t -c "
SELECT
    'Loop #' || id || ' - ' || loop_name || E'\n' ||
    '  狀態: ' || status || E'\n' ||
    '  目前迭代: ' || current_iteration || '/' || COALESCE((config->>'max_iterations')::text, '未設定') || E'\n' ||
    '  通過率: ' || ROUND(current_pass_rate::numeric * 100, 2) || '% (目標: ' || ROUND(target_pass_rate::numeric * 100, 2) || '%)'
FROM knowledge_completion_loops
WHERE id = $LOOP_ID;
"
echo ""

# 檢查待審核知識數量
PENDING_COUNT=$(docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -t -c \
    "SELECT COUNT(*) FROM loop_generated_knowledge WHERE loop_id = $LOOP_ID AND status = 'pending';" | xargs)

if [ "$PENDING_COUNT" -gt 0 ]; then
    echo "⚠️  警告：尚有 $PENDING_COUNT 個待審核知識"
    echo "   建議先完成審核再執行下一次迭代"
    echo ""
    read -p "是否繼續執行下一次迭代？(y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消執行"
        exit 0
    fi
fi

# 進入 Docker 容器執行下一次迭代
echo "🚀 開始執行下一次迭代..."
echo ""

docker exec -i \
    -e OPENAI_API_KEY="$OPENAI_API_KEY" \
    -e DB_HOST=postgres \
    -e DB_PORT=5432 \
    -e DB_NAME=aichatbot_admin \
    -e DB_USER=aichatbot \
    -e DB_PASSWORD=aichatbot_password \
    -e RAG_API_URL=http://rag-orchestrator:8100 \
    aichatbot-rag-orchestrator \
    python3 <<EOF
import asyncio
import sys
import os
sys.path.insert(0, '/app/services/knowledge_completion_loop')

from coordinator import LoopCoordinator
from models import LoopStatus
import psycopg2.pool

async def main():
    loop_id = $LOOP_ID

    # 建立資料庫連接池
    db_pool = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=5,
        host='postgres',
        port=5432,
        database='aichatbot_admin',
        user='aichatbot',
        password='aichatbot_password'
    )

    print(f"📋 執行 Loop #{loop_id} 的下一次迭代...")
    print("")

    # 查詢 loop 資訊並更新狀態
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT loop_name, vendor_id, status FROM knowledge_completion_loops WHERE id = %s", (loop_id,))
            loop_name, vendor_id, status = cur.fetchone()

            # 如果是 reviewing 狀態，更新為 running
            if status == 'reviewing':
                cur.execute("UPDATE knowledge_completion_loops SET status = 'running' WHERE id = %s", (loop_id,))
                conn.commit()
                print("✅ 狀態已更新: reviewing → running")
    finally:
        db_pool.putconn(conn)

    # 初始化協調器
    coordinator = LoopCoordinator(
        db_pool=db_pool,
        vendor_id=vendor_id,
        loop_name=loop_name,
        backtest_base_url='http://rag-orchestrator:8100',
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )

    # 設定 loop_id 和狀態
    coordinator.loop_id = loop_id
    coordinator.current_status = LoopStatus.RUNNING

    try:
        # 執行下一次迭代
        result = await coordinator.execute_iteration()

        print("")
        print("="*70)
        print("✅ 迭代執行完成")
        print("="*70)

        if 'current_iteration' in result:
            print(f"迭代次數: {result['current_iteration']}")

        if 'backtest_result' in result:
            backtest = result['backtest_result']
            print(f"\n📊 回測結果:")
            print(f"   測試題數: {backtest.get('total_tested', 'N/A')}")
            print(f"   通過數: {backtest.get('passed', 'N/A')}")
            print(f"   失敗數: {backtest.get('failed', 'N/A')}")
            print(f"   通過率: {backtest.get('pass_rate', 0) * 100:.1f}%")

        if 'gaps_found' in result:
            print(f"\n🔍 知識缺口: {result['gaps_found']} 個")

        if 'knowledge_generated' in result:
            print(f"📝 知識生成: {result['knowledge_generated']} 個")

        if 'cost_summary' in result:
            cost = result['cost_summary']
            print(f"\n💰 成本統計:")
            print(f"   總成本: \${cost.get('total_cost_usd', 0):.4f} USD")
            print(f"   API 調用: {cost.get('total_calls', 'N/A')} 次")

        print("")

    except Exception as e:
        print(f"\n❌ 執行失敗: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_pool.closeall()

asyncio.run(main())
EOF

echo ""
echo "========================================="
echo "執行完成！"
echo "========================================="
echo ""
echo "📌 下一步："
echo "1. 執行驗證腳本："
echo "   ./quick_verification.sh $LOOP_ID"
echo ""
echo "2. 查看生成的知識："
echo "   docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \\"
echo "     \"SELECT id, knowledge_type, status FROM loop_generated_knowledge WHERE loop_id = $LOOP_ID ORDER BY id DESC LIMIT 10;\\\""
echo ""
