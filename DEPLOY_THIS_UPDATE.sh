#!/bin/bash
# 此次更新的部署腳本
# 執行方式：bash DEPLOY_THIS_UPDATE.sh

set -e  # 遇到錯誤立即停止

echo "========================================="
echo "開始部署此次更新"
echo "========================================="

# 步驟 1：拉取最新代碼
echo ""
echo "步驟 1：拉取最新代碼..."
git pull origin main

# 步驟 2：執行資料庫遷移
echo ""
echo "步驟 2：執行資料庫遷移..."
echo "2.1 建立 admins 表..."
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U aichatbot -d aichatbot_admin < database/migrations/add_admins_table.sql

echo "2.2 建立權限系統表..."
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U aichatbot -d aichatbot_admin < database/migrations/add_permission_system.sql

echo "2.3 驗證遷移..."
docker-compose -f docker-compose.prod.yml exec postgres psql -U aichatbot -d aichatbot_admin -c "\dt" | grep -E "admins|permissions|roles"

# 步驟 3：重新構建並啟動
echo ""
echo "步驟 3：重新構建並啟動服務..."
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache knowledge-admin-api
docker-compose -f docker-compose.prod.yml up -d

# 步驟 4：等待服務啟動
echo ""
echo "步驟 4：等待服務啟動..."
sleep 10

# 步驟 5：檢查服務狀態
echo ""
echo "步驟 5：檢查服務狀態..."
docker-compose -f docker-compose.prod.yml ps

# 步驟 6：驗證
echo ""
echo "步驟 6：驗證 API..."
docker-compose -f docker-compose.prod.yml logs --tail=20 knowledge-admin-api

echo ""
echo "========================================="
echo "部署完成！"
echo "========================================="
echo ""
echo "接下來："
echo "1. 訪問前端測試功能"
echo "2. 如需創建管理員，執行："
echo "   docker-compose -f docker-compose.prod.yml exec knowledge-admin-api python create_admin.py"
