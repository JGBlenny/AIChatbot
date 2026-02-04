#!/bin/bash
# 電費寄送區間查詢系統 - 快速部署腳本
# 日期: 2026-02-04
# 版本: v1.3
# 使用: ./deploy_billing_interval.sh [local|prod]

set -e  # 遇到錯誤立即退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日誌函數
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 環境設定（預設為生產環境）
ENV=${1:-prod}
if [ "$ENV" = "local" ]; then
    COMPOSE_FILE="docker-compose.yml"
else
    COMPOSE_FILE="docker-compose.prod.yml"
fi

# 檢查函數
check_prerequisites() {
    log_info "檢查前置條件..."

    # 檢查 Docker
    if ! docker --version &> /dev/null; then
        log_error "Docker 未安裝或未啟動"
        exit 1
    fi

    # 檢查 Docker Compose
    if ! docker-compose --version &> /dev/null; then
        log_error "Docker Compose 未安裝"
        exit 1
    fi

    # 檢查 PostgreSQL 容器
    if ! docker ps | grep aichatbot-postgres &> /dev/null; then
        log_error "PostgreSQL 容器未運行"
        exit 1
    fi

    log_success "前置條件檢查通過"
}

# 備份函數
backup_database() {
    log_info "備份資料庫..."

    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"

    docker exec aichatbot-postgres pg_dump -U aichatbot aichatbot_admin > "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        log_success "資料庫備份完成: $BACKUP_FILE"
    else
        log_error "資料庫備份失敗"
        exit 1
    fi
}

# 執行 Migrations
run_migrations() {
    log_info "執行資料庫 Migrations..."

    MIGRATIONS=(
        "add_skip_review_to_form_schemas"
        "add_followup_prompt_to_knowledge_base"
        "create_lookup_tables"
        "add_lookup_api_endpoint"
        "create_billing_address_form"
        "create_billing_knowledge"
    )

    for migration in "${MIGRATIONS[@]}"; do
        log_info "執行 Migration: $migration"
        docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
            database/migrations/${migration}.sql 2>&1 | grep -v "ERROR.*already exists" | grep -v "ERROR.*duplicate"

        if [ ${PIPESTATUS[0]} -eq 0 ]; then
            log_success "Migration $migration 完成"
        else
            log_warning "Migration $migration 可能已執行過，繼續..."
        fi
    done

    log_success "所有 Migrations 執行完成"
}

# 匯入 CSV 資料
import_csv_data() {
    log_info "匯入 247 筆地址資料..."

    # 將 CSV 複製到容器中
    docker cp database/exports/lookup_tables_vendor1.csv aichatbot-postgres:/tmp/

    # 使用 COPY 命令匯入
    docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
        COPY lookup_tables (vendor_id, category, category_name, lookup_key, lookup_value, metadata, is_active)
        FROM '/tmp/lookup_tables_vendor1.csv'
        WITH (FORMAT CSV, HEADER true);
    " > /dev/null

    if [ $? -eq 0 ]; then
        log_success "CSV 資料匯入完成"
        # 驗證數量
        COUNT=$(docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -t -c "
            SELECT COUNT(*) FROM lookup_tables WHERE vendor_id = 1 AND category = 'billing_interval';
        " | xargs)
        log_info "業者 1 地址資料: $COUNT 筆"
    else
        log_error "CSV 資料匯入失敗"
        exit 1
    fi
}

# 匯入業務資料
import_business_data() {
    log_info "匯入業務配置..."

    # 匯入業者 1 的配置
    docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
        database/seeds/billing_interval_system_data.sql

    if [ $? -eq 0 ]; then
        log_success "業者 1 配置匯入完成"
    else
        log_error "業者 1 配置匯入失敗"
        exit 1
    fi

    # 匯入 CSV 資料
    import_csv_data

    # 匯入業者 2 的配置
    docker exec -i aichatbot-postgres psql -U aichatbot aichatbot_admin < \
        database/seeds/import_vendor2_only.sql

    if [ $? -eq 0 ]; then
        log_success "業者 2 配置匯入完成"
    else
        log_error "業者 2 配置匯入失敗"
        exit 1
    fi
}

# 重啟服務
restart_services() {
    log_info "重啟 rag-orchestrator 服務..."

    docker-compose -f "$COMPOSE_FILE" restart rag-orchestrator

    log_info "等待服務啟動（10 秒）..."
    sleep 10

    # 檢查服務狀態
    if docker-compose -f "$COMPOSE_FILE" ps rag-orchestrator | grep "Up" &> /dev/null; then
        log_success "服務重啟成功"
    else
        log_error "服務重啟失敗"
        exit 1
    fi
}

# 驗證部署
verify_deployment() {
    log_info "驗證部署結果..."

    echo ""
    log_info "=== 資料庫驗證 ==="
    docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
        SELECT
            vendor_id,
            COUNT(*) as 總筆數,
            COUNT(CASE WHEN lookup_value = '單月' THEN 1 END) as 單月,
            COUNT(CASE WHEN lookup_value = '雙月' THEN 1 END) as 雙月,
            COUNT(CASE WHEN lookup_value = '自繳' THEN 1 END) as 自繳
        FROM lookup_tables
        WHERE category = 'billing_interval'
        GROUP BY vendor_id
        ORDER BY vendor_id;
    "

    echo ""
    docker exec aichatbot-postgres psql -U aichatbot aichatbot_admin -c "
        SELECT
            id,
            vendor_id,
            scope,
            embedding IS NULL as no_embedding
        FROM knowledge_base
        WHERE id IN (1296, 1297);
    "
}

# 功能測試
test_functionality() {
    log_info "執行功能測試..."

    echo ""
    log_info "測試 1: 業者 1 表單觸發"
    curl -s -X POST http://localhost:8100/api/v1/message \
        -H "Content-Type: application/json" \
        -d '{
            "message": "我想查詢電費寄送區間",
            "vendor_id": 1,
            "user_role": "customer",
            "user_id": "deploy_test",
            "session_id": "deploy_test_v1"
        }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('form_triggered'):
    print('✅ 業者 1 表單觸發成功')
    exit(0)
else:
    print('❌ 業者 1 表單觸發失敗')
    exit(1)
" || exit 1

    echo ""
    log_info "測試 2: 業者 2 表單觸發"
    curl -s -X POST http://localhost:8100/api/v1/message \
        -H "Content-Type: application/json" \
        -d '{
            "message": "我想查詢電費寄送區間",
            "vendor_id": 2,
            "user_role": "customer",
            "user_id": "deploy_test",
            "session_id": "deploy_test_v2"
        }' | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('form_triggered'):
    print('✅ 業者 2 表單觸發成功')
    exit(0)
else:
    print('❌ 業者 2 表單觸發失敗')
    exit(1)
" || exit 1

    log_success "所有功能測試通過"
}

# 主函數
main() {
    echo ""
    echo "=========================================="
    echo "  電費寄送區間查詢系統 - 部署腳本"
    echo "  版本: v1.3"
    echo "  日期: 2026-02-04"
    echo "  環境: $ENV (使用 $COMPOSE_FILE)"
    echo "=========================================="
    echo ""

    # 確認執行
    read -p "是否繼續部署? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warning "部署已取消"
        exit 0
    fi

    # 執行部署步驟
    check_prerequisites
    backup_database
    run_migrations
    import_business_data
    restart_services
    verify_deployment
    test_functionality

    echo ""
    log_success "=========================================="
    log_success "  部署完成！"
    log_success "=========================================="
    echo ""
    log_info "詳細部署文檔: docs/deployment/DEPLOYMENT_2026-02-04_BILLING_INTERVAL.md"
}

# 執行主函數
main
