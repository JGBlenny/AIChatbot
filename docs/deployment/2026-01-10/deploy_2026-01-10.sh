#!/bin/bash

# ==========================================
# 生產環境部署腳本
# 版本: 2026-01-10
# 說明: 從 commit b03d649 開始的完整部署流程
# ==========================================

set -e  # 遇到錯誤立即停止

# 顏色設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日誌函數
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 進度顯示
show_step() {
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo -e "${BLUE}📍 步驟 $1: $2${NC}"
    echo "═══════════════════════════════════════════════════════════"
}

# 確認繼續
confirm() {
    read -p "$(echo -e ${YELLOW}⚠️  $1 '(y/n): '${NC})" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "部署已取消"
        exit 1
    fi
}

# ==========================================
# 開始部署
# ==========================================

echo "═══════════════════════════════════════════════════════════"
echo "🚀 AIChatbot 生產環境部署"
echo "   版本: 2026-01-10"
echo "   範圍: commit b03d649 ~ HEAD"
echo "═══════════════════════════════════════════════════════════"
echo ""

# 檢查是否在正確的目錄
if [ ! -f "docker-compose.prod.yml" ]; then
    log_error "請在 AIChatbot 專案根目錄執行此腳本"
    exit 1
fi

# ==========================================
# 步驟 0: 前置檢查
# ==========================================

show_step 0 "前置檢查"

log_info "檢查 Git 狀態..."
CURRENT_BRANCH=$(git branch --show-current)
log_info "當前分支: $CURRENT_BRANCH"

if [ "$CURRENT_BRANCH" != "main" ]; then
    log_warning "當前不在 main 分支"
    confirm "是否繼續部署？"
fi

log_info "最近的提交記錄："
git log --oneline -5

confirm "確認要部署以上版本嗎？"

# 備份提示
log_warning "強烈建議在部署前備份資料庫"
read -p "$(echo -e ${YELLOW}'是否需要立即備份資料庫？ (y/n): '${NC})" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    BACKUP_FILE="/tmp/backup_aichatbot_$(date +%Y%m%d_%H%M%S).sql"
    log_info "正在備份資料庫到 $BACKUP_FILE ..."
    docker-compose -f docker-compose.prod.yml exec postgres \
        pg_dump -U aichatbot aichatbot_admin > "$BACKUP_FILE"
    log_success "資料庫已備份到 $BACKUP_FILE"
fi

# ==========================================
# 步驟 1: 拉取最新代碼
# ==========================================

show_step 1 "拉取最新代碼"

log_info "執行 git pull..."
git pull origin main

log_success "代碼已更新"

# ==========================================
# 步驟 2: 執行資料庫遷移
# ==========================================

show_step 2 "執行資料庫遷移"

# 檢查資料表是否已存在
log_info "檢查現有資料表..."
EXISTING_TABLES=$(docker-compose -f docker-compose.prod.yml exec postgres \
    psql -U aichatbot -d aichatbot_admin -t -c "\dt" | grep -c "form_" || true)

if [ "$EXISTING_TABLES" -eq 0 ]; then
    log_info "執行表單資料表遷移..."
    docker-compose -f docker-compose.prod.yml exec -T postgres \
        psql -U aichatbot -d aichatbot_admin < database/migrations/create_form_tables.sql
    log_success "表單資料表建立完成"

    log_info "執行離題檢測配置遷移..."
    docker-compose -f docker-compose.prod.yml exec -T postgres \
        psql -U aichatbot -d aichatbot_admin < database/migrations/create_digression_config.sql
    log_success "離題檢測配置建立完成"
else
    log_info "表單資料表已存在，跳過基礎遷移"
fi

# 檢查 status 欄位是否存在
log_info "檢查狀態管理欄位..."
HAS_STATUS=$(docker-compose -f docker-compose.prod.yml exec postgres \
    psql -U aichatbot -d aichatbot_admin -t -c "\d form_submissions" | grep -c "status" || true)

if [ "$HAS_STATUS" -eq 0 ]; then
    log_info "執行狀態管理欄位遷移..."
    docker-compose -f docker-compose.prod.yml exec -T postgres \
        psql -U aichatbot -d aichatbot_admin < database/migrations/add_form_submission_status.sql
    log_success "狀態管理欄位建立完成"
else
    log_info "狀態管理欄位已存在，跳過遷移"
fi

# 驗證遷移結果
log_info "驗證資料表結構..."
docker-compose -f docker-compose.prod.yml exec postgres \
    psql -U aichatbot -d aichatbot_admin -c "\dt" | grep form

log_success "資料庫遷移完成"

# ==========================================
# 步驟 3: 構建前端
# ==========================================

show_step 3 "構建前端"

log_info "安裝前端依賴..."
cd knowledge-admin/frontend
npm install

log_info "構建前端..."
npm run build

if [ ! -d "dist" ]; then
    log_error "前端構建失敗：dist 目錄不存在"
    exit 1
fi

cd ../..
log_success "前端構建完成"

# ==========================================
# 步驟 4: 重新構建服務
# ==========================================

show_step 4 "重新構建服務"

log_warning "即將停止所有服務進行重新構建"
confirm "確認繼續？"

log_info "停止舊服務..."
docker-compose -f docker-compose.prod.yml down

log_info "重新構建 rag-orchestrator..."
docker-compose -f docker-compose.prod.yml build --no-cache rag-orchestrator

log_info "重新構建 knowledge-admin-api..."
docker-compose -f docker-compose.prod.yml build --no-cache knowledge-admin-api

log_info "重新構建 knowledge-admin-web..."
docker-compose -f docker-compose.prod.yml build --no-cache knowledge-admin-web

log_success "服務構建完成"

log_info "啟動所有服務..."
docker-compose -f docker-compose.prod.yml up -d

log_success "服務已啟動"

# 等待服務啟動
log_info "等待服務啟動... (10秒)"
sleep 10

# ==========================================
# 步驟 5: 驗證部署
# ==========================================

show_step 5 "驗證部署"

log_info "檢查服務狀態..."
docker-compose -f docker-compose.prod.yml ps

# 檢查關鍵服務
SERVICES=("postgres" "rag-orchestrator" "knowledge-admin-api" "knowledge-admin-web")
ALL_UP=true

for SERVICE in "${SERVICES[@]}"; do
    STATUS=$(docker-compose -f docker-compose.prod.yml ps -q $SERVICE | xargs docker inspect -f '{{.State.Status}}' 2>/dev/null || echo "not found")
    if [ "$STATUS" = "running" ]; then
        log_success "$SERVICE: 運行中"
    else
        log_error "$SERVICE: 狀態異常 ($STATUS)"
        ALL_UP=false
    fi
done

if [ "$ALL_UP" = false ]; then
    log_error "部分服務未正常運行，請檢查日誌"
    echo ""
    log_info "查看日誌命令："
    echo "  docker-compose -f docker-compose.prod.yml logs --tail=50 [service_name]"
    exit 1
fi

# 測試 API
log_info "測試 API 端點..."
sleep 5  # 再等待 5 秒確保 API 完全啟動

API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8100/api/v1/forms || echo "000")
if [ "$API_RESPONSE" = "200" ] || [ "$API_RESPONSE" = "404" ]; then
    log_success "API 端點可訪問 (HTTP $API_RESPONSE)"
else
    log_warning "API 端點回應異常 (HTTP $API_RESPONSE)"
fi

# ==========================================
# 部署完成
# ==========================================

echo ""
echo "═══════════════════════════════════════════════════════════"
echo -e "${GREEN}🎉 部署完成！${NC}"
echo "═══════════════════════════════════════════════════════════"
echo ""

log_info "部署摘要："
echo "  - 資料庫遷移: ✅ 完成"
echo "  - 前端構建: ✅ 完成"
echo "  - 服務構建: ✅ 完成"
echo "  - 服務驗證: ✅ 通過"
echo ""

log_info "下一步驗證："
echo "  1. 訪問管理後台進行功能測試"
echo "  2. 檢查「表單管理」功能"
echo "  3. 檢查「業者管理」的「📋 表單」按鈕"
echo "  4. 測試業者表單頁面的狀態管理功能"
echo ""

log_info "監控命令："
echo "  # 查看所有服務日誌"
echo "  docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "  # 查看特定服務日誌"
echo "  docker-compose -f docker-compose.prod.yml logs -f rag-orchestrator"
echo ""

log_info "如遇問題，請參考："
echo "  - PRODUCTION_DEPLOY_2026-01-10.md（完整部署文檔）"
echo "  - QUICK_DEPLOY_2026-01-10.md（快速參考指南）"
echo ""

# 記錄部署資訊
DEPLOY_LOG="/tmp/deploy_record_$(date +%Y%m%d_%H%M%S).txt"
cat > "$DEPLOY_LOG" <<EOF
==========================================
部署記錄
==========================================
部署時間: $(date)
部署版本: $(git log --oneline -1)
部署人員: $(whoami)
部署主機: $(hostname)

服務狀態:
$(docker-compose -f docker-compose.prod.yml ps)

==========================================
EOF

log_success "部署記錄已保存到 $DEPLOY_LOG"
