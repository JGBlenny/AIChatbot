#!/bin/bash
# 線上環境修復腳本
# 用途：更新代碼並重啟服務

set -e

echo "========================================================================"
echo "線上環境修復腳本"
echo "========================================================================"
echo ""

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 步驟 1：檢查當前位置
echo "📍 步驟 1：檢查當前目錄"
if [ ! -f "docker-compose.prod.yml" ]; then
    echo -e "${RED}❌ 錯誤：找不到 docker-compose.prod.yml${NC}"
    echo "請確認你在 AIChatbot 專案根目錄"
    exit 1
fi
echo -e "${GREEN}✅ 當前目錄正確${NC}"
echo ""

# 步驟 2：拉取最新代碼
echo "📥 步驟 2：拉取最新代碼"
git pull
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Git pull 成功${NC}"
else
    echo -e "${RED}❌ Git pull 失敗${NC}"
    exit 1
fi
echo ""

# 步驟 3：檢查 commit 版本
echo "📋 步驟 3：檢查 commit 版本"
LATEST_COMMIT=$(git log --oneline -1)
echo "最新 commit: $LATEST_COMMIT"
echo ""

# 步驟 4：驗證文件內容
echo "🔍 步驟 4：驗證文件內容"
if grep -q "按來源類型統計" knowledge-admin/backend/app.py; then
    echo -e "${GREEN}✅ app.py 文件已更新（找到 '按來源類型統計'）${NC}"
else
    echo -e "${RED}❌ app.py 文件可能未正確更新${NC}"
    echo "請檢查 git pull 是否有衝突"
    exit 1
fi

if grep -q "@app.post.*regenerate-embeddings" knowledge-admin/backend/app.py; then
    echo -e "${GREEN}✅ regenerate-embeddings endpoint 存在${NC}"
else
    echo -e "${YELLOW}⚠️  找不到 regenerate-embeddings endpoint${NC}"
fi
echo ""

# 步驟 5：停止舊容器
echo "🛑 步驟 5：停止 knowledge-admin-api 容器"
docker-compose -f docker-compose.prod.yml stop knowledge-admin-api
echo -e "${GREEN}✅ 容器已停止${NC}"
echo ""

# 步驟 6：重建鏡像（不使用緩存）
echo "🔨 步驟 6：重建 knowledge-admin-api 鏡像（可能需要 1-2 分鐘）"
docker-compose -f docker-compose.prod.yml build knowledge-admin-api --no-cache
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 鏡像重建成功${NC}"
else
    echo -e "${RED}❌ 鏡像重建失敗${NC}"
    exit 1
fi
echo ""

# 步驟 7：啟動容器
echo "🚀 步驟 7：啟動 knowledge-admin-api 容器"
docker-compose -f docker-compose.prod.yml up -d knowledge-admin-api
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 容器啟動成功${NC}"
else
    echo -e "${RED}❌ 容器啟動失敗${NC}"
    exit 1
fi
echo ""

# 步驟 8：等待服務啟動
echo "⏳ 步驟 8：等待服務啟動（5 秒）"
sleep 5
echo -e "${GREEN}✅ 等待完成${NC}"
echo ""

# 步驟 9：驗證容器內的文件
echo "🔍 步驟 9：驗證容器內的文件"
echo "檢查 get_stats 函數："
docker exec aichatbot-knowledge-admin-api grep -A5 "按來源類型統計" /app/app.py 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 容器內文件已更新${NC}"
else
    echo -e "${YELLOW}⚠️  無法確認容器內文件${NC}"
fi
echo ""

# 步驟 10：測試 API
echo "🧪 步驟 10：測試 API"
echo ""
echo "測試 /api/stats："
STATS_RESULT=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/stats)
if [ "$STATS_RESULT" == "200" ]; then
    echo -e "${GREEN}✅ /api/stats 返回 200${NC}"
    curl -s http://localhost:8000/api/stats | python3 -m json.tool | head -20
else
    echo -e "${RED}❌ /api/stats 返回 $STATS_RESULT${NC}"
fi
echo ""

echo "測試 /api/knowledge/regenerate-embeddings："
REGEN_RESULT=$(curl -s -X POST http://localhost:8000/api/knowledge/regenerate-embeddings)
echo "$REGEN_RESULT" | python3 -m json.tool 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ /api/knowledge/regenerate-embeddings 可以訪問${NC}"
else
    echo -e "${YELLOW}⚠️  /api/knowledge/regenerate-embeddings 可能有問題${NC}"
fi
echo ""

# 步驟 11：檢查最新日誌
echo "📋 步驟 11：檢查最新日誌（最後 20 行）"
docker logs --tail=20 aichatbot-knowledge-admin-api 2>&1 | tail -20
echo ""

# 總結
echo "========================================================================"
echo "✅ 修復腳本執行完成"
echo "========================================================================"
echo ""
echo "下一步："
echo "1. 如果 API 測試都正常，請在瀏覽器測試："
echo "   https://chatai.jgbsmart.com/knowledge"
echo ""
echo "2. 點擊「批量生成向量」按鈕測試"
echo ""
echo "3. 如果還有問題，請檢查上方的日誌輸出"
echo ""
