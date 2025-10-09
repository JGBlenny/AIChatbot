#!/bin/bash

echo "=================================="
echo "AIChatbot 後台系統 - 快速設定"
echo "=================================="

# 檢查 Python 版本
echo ""
echo "1️⃣  檢查 Python 版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python 版本: $python_version"

# 檢查 PostgreSQL
echo ""
echo "2️⃣  檢查 PostgreSQL..."
if command -v psql &> /dev/null; then
    echo "✅ PostgreSQL 已安裝"
else
    echo "❌ PostgreSQL 未安裝"
    echo "   安裝指令: brew install postgresql@16"
    exit 1
fi

# 建立資料庫
echo ""
echo "3️⃣  建立資料庫..."
read -p "是否建立資料庫 aichatbot_admin？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    createdb aichatbot_admin 2>/dev/null && echo "✅ 資料庫建立成功" || echo "ℹ️  資料庫已存在"
fi

# 進入後端目錄
cd backend || exit

# 建立虛擬環境
echo ""
echo "4️⃣  建立 Python 虛擬環境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ 虛擬環境建立成功"
else
    echo "ℹ️  虛擬環境已存在"
fi

# 啟動虛擬環境
echo ""
echo "5️⃣  啟動虛擬環境..."
source venv/bin/activate
echo "✅ 虛擬環境已啟動"

# 安裝依賴
echo ""
echo "6️⃣  安裝 Python 依賴..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "✅ 依賴安裝完成"

# 設定環境變數
echo ""
echo "7️⃣  設定環境變數..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ .env 檔案已建立"
    echo ""
    echo "⚠️  請編輯 backend/.env 並填入："
    echo "   - OPENAI_API_KEY (必填)"
    echo "   - DATABASE_URL (如需修改)"
    echo ""
    read -p "是否現在編輯 .env？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env
    fi
else
    echo "ℹ️  .env 檔案已存在"
fi

# 初始化資料庫
echo ""
echo "8️⃣  初始化資料庫..."
read -p "是否初始化資料庫表？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 -c "from app.core.database import Base, sync_engine; Base.metadata.create_all(sync_engine)"
    echo "✅ 資料庫初始化完成"
fi

# 完成
echo ""
echo "=================================="
echo "✅ 設定完成！"
echo "=================================="
echo ""
echo "啟動後端："
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo ""
echo "測試 API："
echo "  python test_example.py"
echo ""
echo "API 文件："
echo "  http://localhost:8000/docs"
echo ""
