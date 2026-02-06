#!/bin/bash

# 語義模型快速開始腳本
# 自動執行完整的訓練流程

echo "======================================"
echo "語義模型訓練 - 快速開始"
echo "======================================"

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 檢查 Python
echo -e "\n${YELLOW}檢查環境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 找不到 Python3${NC}"
    exit 1
fi

# 檢查依賴
echo "檢查依賴套件..."
pip list | grep sentence-transformers > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}安裝 sentence-transformers...${NC}"
    pip install sentence-transformers
fi

pip list | grep psycopg2 > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}安裝 psycopg2...${NC}"
    pip install psycopg2-binary
fi

# 建立資料夾
echo -e "\n${GREEN}建立專案結構...${NC}"
mkdir -p data models

# 檢查 Docker 資料庫
echo -e "\n${YELLOW}檢查資料庫連接...${NC}"
docker ps | grep postgres > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "${RED}⚠️  PostgreSQL Docker 容器未運行${NC}"
    echo "請先啟動資料庫："
    echo "  cd .. && docker-compose up -d postgres"
    echo ""
    read -p "資料庫已啟動？(y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: 提取知識庫
echo -e "\n${GREEN}Step 1: 提取知識庫${NC}"
echo "======================================"
python3 scripts/extract_knowledge.py
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 知識庫提取失敗${NC}"
    echo "請確認資料庫連接設定："
    echo "  export DB_HOST=localhost"
    echo "  export DB_NAME=aichatbot"
    echo "  export DB_USER=aichatbot_user"
    echo "  export DB_PASSWORD=aichatbot_password"
    exit 1
fi

# Step 2: 生成訓練數據
echo -e "\n${GREEN}Step 2: 生成訓練數據${NC}"
echo "======================================"
python3 scripts/generate_training_data.py
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ 訓練數據生成失敗${NC}"
    exit 1
fi

# 詢問是否開始訓練
echo -e "\n${YELLOW}準備開始訓練${NC}"
echo "訓練時間預估："
echo "  - GPU: 30-60 分鐘"
echo "  - CPU: 2-3 小時"
echo ""
read -p "是否開始訓練？(y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Step 3: 訓練模型
    echo -e "\n${GREEN}Step 3: 訓練模型${NC}"
    echo "======================================"
    python3 scripts/train.py

    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}✅ 訓練完成！${NC}"
        echo ""
        echo "模型已保存到: models/semantic_v1/"
        echo ""
        echo "後續步驟："
        echo "1. 測試模型: python scripts/evaluate.py"
        echo "2. 部署模型: python scripts/deploy.py"
        echo "3. 查看文檔: cat docs/implementation.md"
    else
        echo -e "${RED}❌ 訓練失敗${NC}"
        echo "請檢查錯誤訊息並重試"
    fi
else
    echo -e "\n${YELLOW}已跳過訓練${NC}"
    echo "訓練數據已準備好："
    echo "  - data/training_data.json"
    echo "  - data/test_data.json"
    echo ""
    echo "稍後執行訓練："
    echo "  python3 scripts/train.py"
fi

echo ""
echo "======================================"
echo "完成！"
echo "======================================"