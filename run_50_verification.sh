#!/bin/bash
# 50 題驗證測試 - 執行腳本
# 使用方式：./run_50_verification.sh

set -e

echo "========================================="
echo "50 題驗證測試 - 執行腳本"
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
    aichatbot-rag-orchestrator \
    python3 /app/services/knowledge_completion_loop/run_first_loop.py

echo ""
echo "========================================="
echo "執行完成！"
echo "========================================="
echo ""
echo "📌 下一步："
echo "1. 查詢最新的 Loop ID："
echo "   docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -t -c \"SELECT id FROM knowledge_completion_loops ORDER BY id DESC LIMIT 1;\""
echo ""
echo "2. 查看迴圈執行結果："
echo "   docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -c \"SELECT * FROM knowledge_completion_loops ORDER BY id DESC LIMIT 1;\""
echo ""
echo "3. 執行更大規模的測試："
echo "   ./run_500_verification.sh   # 500 題標準驗證"
echo "   ./run_3000_verification.sh  # 3000 題完整驗證"
echo ""
