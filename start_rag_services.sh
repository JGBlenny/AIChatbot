#!/bin/bash

# 啟動 RAG Orchestrator 及相依服務
# 這個腳本會啟動：
# 1. PostgreSQL (資料庫)
# 2. Redis (快取)
# 3. Embedding API (向量生成服務)
# 4. RAG Orchestrator (RAG 協調服務)

set -e

echo "🚀 啟動 RAG Orchestrator 服務..."
echo ""

# 檢查 Docker 是否運行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker daemon 未運行！"
    echo "請先啟動 Docker Desktop，然後重新執行此腳本。"
    exit 1
fi

echo "✅ Docker daemon 正在運行"
echo ""

# 檢查 .env 文件
if [ ! -f .env ]; then
    echo "❌ .env 文件不存在！"
    echo "請確認 .env 文件存在並包含 OPENAI_API_KEY"
    exit 1
fi

echo "✅ .env 文件存在"
echo ""

# 啟動服務
echo "📦 啟動服務容器..."
echo ""

# 啟動 PostgreSQL
echo "🗄️  啟動 PostgreSQL..."
docker-compose up -d postgres
sleep 5

# 啟動 Redis
echo "🔴 啟動 Redis..."
docker-compose up -d redis
sleep 2

# 啟動 Embedding API
echo "🤖 啟動 Embedding API..."
docker-compose up -d embedding-api
sleep 5

# 啟動 RAG Orchestrator
echo "🎯 啟動 RAG Orchestrator..."
docker-compose up -d rag-orchestrator
sleep 5

echo ""
echo "✅ 所有服務已啟動！"
echo ""

# 檢查服務狀態
echo "📊 服務狀態："
echo "============================================"
docker-compose ps

echo ""
echo "🔗 服務端點："
echo "============================================"
echo "RAG Orchestrator API: http://localhost:8100"
echo "Embedding API:        http://localhost:5001"
echo "PostgreSQL:           localhost:5432"
echo "Redis:                localhost:6379"
echo ""

# 檢查 RAG Orchestrator 是否就緒
echo "⏳ 等待 RAG Orchestrator 就緒..."
for i in {1..30}; do
    if curl -s http://localhost:8100/health > /dev/null 2>&1; then
        echo "✅ RAG Orchestrator 已就緒！"
        break
    fi
    echo "   等待中... ($i/30)"
    sleep 2
done

# 檢查健康狀態
echo ""
echo "🏥 健康檢查："
echo "============================================"
if curl -s http://localhost:8100/health > /dev/null 2>&1; then
    echo "✅ RAG Orchestrator: 健康"
else
    echo "⚠️  RAG Orchestrator: 未就緒（可能仍在啟動中）"
fi

if curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo "✅ Embedding API: 健康"
else
    echo "⚠️  Embedding API: 未就緒（可能仍在啟動中）"
fi

echo ""
echo "🎉 完成！現在可以執行回測了。"
echo ""
echo "💡 提示："
echo "  - 查看日誌: docker-compose logs -f rag-orchestrator"
echo "  - 停止服務: docker-compose down"
echo "  - 重啟服務: docker-compose restart rag-orchestrator"
