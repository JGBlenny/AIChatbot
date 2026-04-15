#!/bin/bash
# 3000 題驗證測試 - 執行腳本
# 使用方式：./run_3000_verification.sh

set -e

echo "========================================="
echo "3000 題驗證測試 - 執行腳本"
echo "========================================="
echo ""
echo "⚠️  警告：3000 題測試規模較大"
echo "   預計耗時：90-120 分鐘"
echo "   建議先完成 50 題和 500 題測試"
echo ""

read -p "確認要執行 3000 題測試？(y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消執行"
    exit 0
fi

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

# 進入 Docker 容器執行
echo "📦 進入 rag-orchestrator 容器..."
echo ""

docker exec -i \
    -e OPENAI_API_KEY="$OPENAI_API_KEY" \
    -e DB_HOST=postgres \
    -e DB_PORT=5432 \
    -e DB_NAME=aichatbot_admin \
    -e DB_USER=aichatbot \
    -e DB_PASSWORD=aichatbot_password \
    -e RAG_API_URL=http://rag-orchestrator:8100 \
    -e VENDOR_ID=2 \
    -e BATCH_SIZE=3000 \
    -e LOOP_NAME="知識完善迴圈（3000題）" \
    aichatbot-rag-orchestrator \
    python3 <<'EOF'
import asyncio
import os
import sys
from datetime import datetime
import psycopg2.pool

sys.path.insert(0, '/app/services/knowledge_completion_loop')

from coordinator import LoopCoordinator
from models import LoopConfig

async def main():
    print("\n" + "="*70)
    print("知識庫完善迴圈 - 3000 題全面評估")
    print("="*70)
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")

    # 資料庫連接參數
    db_params = {
        'host': os.getenv('DB_HOST', 'postgres'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'aichatbot_admin'),
        'user': os.getenv('DB_USER', 'aichatbot'),
        'password': os.getenv('DB_PASSWORD', 'aichatbot_password'),
    }

    openai_api_key = os.getenv('OPENAI_API_KEY')
    backtest_url = os.getenv('RAG_API_URL', 'http://localhost:8100')
    vendor_id = int(os.getenv('VENDOR_ID', '2'))
    batch_size = int(os.getenv('BATCH_SIZE', '3000'))
    loop_name = os.getenv('LOOP_NAME', '知識完善迴圈（3000題）')

    print(f"📋 配置資訊:")
    print(f"   測試規模: {batch_size} 題")
    print(f"   業者 ID: {vendor_id}")
    print(f"   迴圈名稱: {loop_name}")
    print()

    # 建立資料庫連接池
    print("🔌 建立資料庫連接池...")
    try:
        db_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            **db_params
        )
        print("   ✅ 連接池建立成功")
    except Exception as e:
        print(f"   ❌ 連接失敗: {e}")
        sys.exit(1)

    # 迴圈配置
    config = LoopConfig(
        batch_size=batch_size,
        target_pass_rate=0.85,
        max_iterations=10,
        action_type_mode="ai_assisted",
    )

    print("\n⚙️  迴圈配置:")
    print(f"   批次大小: {config.batch_size} 題")
    print(f"   目標通過率: {config.target_pass_rate * 100}%")
    print(f"   最大迭代次數: {config.max_iterations}")
    print()

    # 初始化協調器
    print("🚀 初始化知識完善迴圈協調器...")
    coordinator = LoopCoordinator(
        db_pool=db_pool,
        vendor_id=vendor_id,
        loop_name=loop_name,
        backtest_base_url=backtest_url,
        openai_api_key=openai_api_key
    )
    print("   ✅ 協調器初始化完成")
    print()

    try:
        # 啟動迴圈
        print("="*70)
        print("開始執行迴圈")
        print("="*70)
        print()

        result = await coordinator.start_loop(config)

        print("\n" + "="*70)
        print("迴圈啟動成功")
        print("="*70)
        print(f"迴圈 ID: {result.get('loop_id', 'N/A')}")
        print(f"狀態: {result.get('status', 'N/A')}")
        print()

        # 執行第一次迭代
        print("="*70)
        print("開始第一次迭代")
        print("="*70)
        print()

        iteration_result = await coordinator.execute_iteration()

        print("\n" + "="*70)
        print("第一次迭代完成")
        print("="*70)
        print(f"迭代次數: {iteration_result.get('current_iteration', 'N/A')}")

        if 'backtest_result' in iteration_result:
            backtest = iteration_result['backtest_result']
            print(f"\n📊 回測結果:")
            print(f"   測試題數: {backtest.get('total_tested', 'N/A')}")
            print(f"   通過數: {backtest.get('passed', 'N/A')}")
            print(f"   失敗數: {backtest.get('failed', 'N/A')}")
            print(f"   通過率: {backtest.get('pass_rate', 0) * 100:.1f}%")

        if 'gaps_found' in iteration_result:
            print(f"\n🔍 知識缺口: {iteration_result.get('gaps_found', 'N/A')} 個")

        if 'knowledge_generated' in iteration_result:
            print(f"📝 知識生成: {iteration_result.get('knowledge_generated', 'N/A')} 個")

        if 'cost_summary' in iteration_result:
            cost = iteration_result['cost_summary']
            print(f"\n💰 成本統計:")
            print(f"   總成本: ${cost.get('total_cost_usd', 0):.4f} USD")
            print(f"   API 調用次數: {cost.get('total_calls', 'N/A')}")

        print()
        print("="*70)
        print("✅ 3000 題全面評估執行完成！")
        print("="*70)

    except Exception as e:
        print(f"\n❌ 執行失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        if db_pool:
            db_pool.closeall()
            print("🔌 資料庫連接池已關閉")

if __name__ == "__main__":
    asyncio.run(main())
EOF

echo ""
echo "========================================="
echo "執行完成！"
echo "========================================="
echo ""
echo "📌 下一步："
echo "1. 查詢 Loop ID："
echo "   docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -t -c \"SELECT id FROM knowledge_completion_loops ORDER BY id DESC LIMIT 1;\""
echo ""
echo "2. 使用快速驗證腳本："
echo "   ./quick_verification.sh <loop_id>"
echo ""
