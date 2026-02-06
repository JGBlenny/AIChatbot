#!/bin/bash
# Docker 部署測試腳本

echo "======================================"
echo "語義模型 Docker 部署測試"
echo "======================================"
echo ""

# 1. 建立 Docker 映像檔
echo "1. 建立 Docker 映像檔..."
docker build -t semantic-model:test . || {
    echo "❌ 建立映像檔失敗"
    exit 1
}
echo "✅ 映像檔建立成功"
echo ""

# 2. 啟動容器
echo "2. 啟動測試容器..."
docker run -d \
    --name semantic_model_test \
    -p 8001:8000 \
    -v $(pwd)/data:/app/data \
    -v $(pwd)/config:/app/config \
    semantic-model:test || {
    echo "❌ 容器啟動失敗"
    exit 1
}
echo "✅ 容器啟動成功"
echo ""

# 3. 等待服務啟動
echo "3. 等待服務啟動（最多 30 秒）..."
for i in {1..30}; do
    if curl -s http://localhost:8001/ > /dev/null 2>&1; then
        echo "✅ 服務已啟動"
        break
    fi
    echo -n "."
    sleep 1
done
echo ""

# 4. 健康檢查
echo "4. 執行健康檢查..."
curl -s http://localhost:8001/ | python3 -m json.tool || {
    echo "❌ 健康檢查失敗"
    docker logs semantic_model_test
    exit 1
}
echo ""

# 5. 測試搜索功能
echo "5. 測試搜索功能..."
echo "   查詢：電費帳單寄送區間"

curl -s -X POST http://localhost:8001/search \
    -H "Content-Type: application/json" \
    -d '{
        "query": "電費帳單寄送區間",
        "top_k": 3,
        "min_score": 0.1
    }' | python3 -m json.tool || {
    echo "❌ 搜索測試失敗"
    exit 1
}

echo ""
echo "   查詢：我要報修"

curl -s -X POST http://localhost:8001/search \
    -H "Content-Type: application/json" \
    -d '{
        "query": "我要報修",
        "top_k": 3,
        "min_score": 0.1
    }' | python3 -m json.tool

echo ""
echo "======================================"
echo "✅ Docker 測試完成"
echo "======================================"

# 6. 清理測試容器
echo ""
read -p "是否清理測試容器？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "清理測試容器..."
    docker stop semantic_model_test
    docker rm semantic_model_test
    echo "✅ 清理完成"
fi

echo ""
echo "部署指令："
echo "  生產部署：docker-compose up -d"
echo "  查看日誌：docker logs semantic_model_service"
echo "  API 端點：http://localhost:8001/"