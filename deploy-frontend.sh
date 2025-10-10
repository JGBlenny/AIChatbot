#!/bin/bash

# 前端快速部署腳本（生產環境）
# 使用方式: ./deploy-frontend.sh

set -e  # 遇到錯誤立即停止

echo "🚀 開始部署前端..."

# 1. 檢查是否在正確的目錄
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ 錯誤: 請在專案根目錄執行此腳本"
    exit 1
fi

# 2. 進入前端目錄
cd knowledge-admin/frontend

echo "📦 安裝依賴..."
npm install

echo "🔨 編譯前端..."
npm run build

# 3. 檢查編譯結果
if [ ! -d "dist" ]; then
    echo "❌ 錯誤: 編譯失敗，dist 目錄不存在"
    exit 1
fi

echo "✅ 編譯完成"

# 4. 返回專案根目錄
cd ../..

# 5. 重新載入 nginx（零停機）
echo "🔄 重新載入 nginx..."
docker exec aichatbot-knowledge-admin-web nginx -s reload

echo "✅ 部署完成！"
echo ""
echo "📍 前端地址: http://localhost:8080"
echo "💡 提示: 如果看不到變更，請清除瀏覽器快取（Ctrl+Shift+R）"
