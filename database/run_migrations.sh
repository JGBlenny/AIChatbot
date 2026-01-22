#!/bin/bash
# Migration 自動執行腳本（安全加強版）
# 用途: 自動執行所有未執行的 migration，解決推版漏掉欄位的問題
# 使用: ./run_migrations.sh [docker-compose-file] [options]
#
# 安全特性:
# - Dry-run 模式預覽即將執行的 migration
# - 自動備份資料庫
# - 交互式確認（可選）
# - 語法驗證
# - 詳細錯誤日誌

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 參數解析
COMPOSE_FILE="${1:-docker-compose.prod.yml}"
DRY_RUN=false
AUTO_BACKUP=true
INTERACTIVE=false
BACKUP_DIR="database/backups"

# 解析選項
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-backup)
            AUTO_BACKUP=false
            shift
            ;;
        --interactive|-i)
            INTERACTIVE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [docker-compose-file] [options]"
            echo ""
            echo "Options:"
            echo "  --dry-run        預覽即將執行的 migration，不實際執行"
            echo "  --no-backup      不自動備份資料庫（不推薦）"
            echo "  --interactive    執行前需要確認"
            echo "  --help           顯示此幫助訊息"
            echo ""
            echo "Examples:"
            echo "  $0 docker-compose.prod.yml                    # 正常執行"
            echo "  $0 docker-compose.prod.yml --dry-run          # 預覽模式"
            echo "  $0 docker-compose.prod.yml --interactive      # 交互式執行"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

DB_CONTAINER="postgres"
DB_USER="aichatbot"
DB_NAME="aichatbot_admin"
MIGRATIONS_DIR="database/migrations"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Migration 自動執行腳本（安全加強版）${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}⚠️  DRY-RUN 模式：僅預覽，不實際執行${NC}"
    echo ""
fi

# 檢查 Docker 服務是否運行
echo -e "${CYAN}[1/6] 檢查資料庫服務...${NC}"
if ! docker-compose -f "$COMPOSE_FILE" ps | grep -q "$DB_CONTAINER.*Up"; then
    echo -e "${RED}❌ 資料庫服務未運行，請先啟動：${NC}"
    echo "   docker-compose -f $COMPOSE_FILE up -d postgres"
    exit 1
fi
echo -e "${GREEN}✓${NC} 資料庫服務運行中"
echo ""

# 確保 schema_migrations 表存在
echo -e "${CYAN}[2/6] 檢查 schema_migrations 表...${NC}"
docker-compose -f "$COMPOSE_FILE" exec -T "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
    CREATE TABLE IF NOT EXISTS schema_migrations (
        id SERIAL PRIMARY KEY,
        migration_name VARCHAR(255) UNIQUE NOT NULL,
        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        execution_time_ms INTEGER,
        success BOOLEAN DEFAULT TRUE,
        error_message TEXT,
        created_by VARCHAR(100) DEFAULT 'system'
    );
" > /dev/null 2>&1

echo -e "${GREEN}✓${NC} schema_migrations 表已就緒"
echo ""

# 獲取所有 migration 文件（排序）
echo -e "${CYAN}[3/6] 掃描 migration 文件...${NC}"
MIGRATION_FILES=$(ls -1 "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort)

if [ -z "$MIGRATION_FILES" ]; then
    echo -e "${RED}❌ 未找到任何 migration 文件${NC}"
    exit 1
fi

TOTAL_COUNT=$(echo "$MIGRATION_FILES" | wc -l | tr -d ' ')
echo -e "${GREEN}✓${NC} 找到 $TOTAL_COUNT 個 migration 文件"
echo ""

# 找出未執行的 migration
echo -e "${CYAN}[4/6] 分析待執行的 migration...${NC}"
PENDING_MIGRATIONS=()

for MIGRATION_FILE in $MIGRATION_FILES; do
    MIGRATION_NAME=$(basename "$MIGRATION_FILE" .sql)

    ALREADY_EXECUTED=$(docker-compose -f "$COMPOSE_FILE" exec -T "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -tAc "
        SELECT COUNT(*) FROM schema_migrations WHERE migration_name = '$MIGRATION_NAME';
    " 2>/dev/null)

    if [ "$ALREADY_EXECUTED" -eq 0 ]; then
        PENDING_MIGRATIONS+=("$MIGRATION_FILE")
    fi
done

PENDING_COUNT=${#PENDING_MIGRATIONS[@]}
SKIPPED_COUNT=$((TOTAL_COUNT - PENDING_COUNT))

if [ $PENDING_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓${NC} 所有 migration 都已執行，無需執行"
    echo -e "   已執行: $TOTAL_COUNT 個"
    exit 0
fi

echo -e "${YELLOW}⚠️  發現 $PENDING_COUNT 個待執行的 migration:${NC}"
for MIGRATION_FILE in "${PENDING_MIGRATIONS[@]}"; do
    MIGRATION_NAME=$(basename "$MIGRATION_FILE" .sql)
    echo -e "   - $MIGRATION_NAME"
done
echo ""

# Dry-run 模式：顯示預覽後退出
if [ "$DRY_RUN" = true ]; then
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Dry-Run 預覽完成${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "待執行: $PENDING_COUNT 個 migration"
    echo -e "已跳過: $SKIPPED_COUNT 個 migration"
    echo ""
    echo -e "${YELLOW}提示: 移除 --dry-run 參數以實際執行${NC}"
    exit 0
fi

# 自動備份
if [ "$AUTO_BACKUP" = true ]; then
    echo -e "${CYAN}[5/6] 備份資料庫...${NC}"

    # 創建備份目錄
    mkdir -p "$BACKUP_DIR"

    BACKUP_FILE="$BACKUP_DIR/backup_before_migration_$(date +%Y%m%d_%H%M%S).sql"

    echo -e "   備份到: $BACKUP_FILE"

    if docker-compose -f "$COMPOSE_FILE" exec -T "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" > "$BACKUP_FILE" 2>/dev/null; then
        BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
        echo -e "${GREEN}✓${NC} 備份完成（大小: $BACKUP_SIZE）"
        echo -e "   ${YELLOW}如需回滾，執行: docker exec -i aichatbot-postgres psql -U $DB_USER $DB_NAME < $BACKUP_FILE${NC}"
    else
        echo -e "${RED}❌ 備份失敗${NC}"
        echo -e "${YELLOW}是否繼續執行？(y/N) ${NC}"
        read -r CONTINUE
        if [ "$CONTINUE" != "y" ] && [ "$CONTINUE" != "Y" ]; then
            echo "已取消"
            exit 1
        fi
    fi
    echo ""
else
    echo -e "${CYAN}[5/6] 跳過備份（使用 --no-backup）${NC}"
    echo -e "${YELLOW}⚠️  警告: 未備份資料庫，如有錯誤將難以回滾${NC}"
    echo ""
fi

# 交互式確認
if [ "$INTERACTIVE" = true ]; then
    echo -e "${YELLOW}即將執行 $PENDING_COUNT 個 migration，是否繼續？(y/N) ${NC}"
    read -r CONFIRM
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        echo "已取消"
        exit 0
    fi
    echo ""
fi

# 執行 migration
echo -e "${CYAN}[6/6] 執行 migration...${NC}"
echo ""

EXECUTED_COUNT=0
FAILED_COUNT=0
FAILED_MIGRATIONS=()

for MIGRATION_FILE in "${PENDING_MIGRATIONS[@]}"; do
    MIGRATION_NAME=$(basename "$MIGRATION_FILE" .sql)

    echo -e "  ${BLUE}▶${NC} 執行: $MIGRATION_NAME"

    # 語法驗證（簡單檢查）
    if ! grep -q ";" "$MIGRATION_FILE"; then
        echo -e "  ${YELLOW}⚠${NC} 警告: migration 可能不包含有效的 SQL 語句"
    fi

    # 記錄開始時間（秒級，macOS 不支援毫秒）
    START_TIME=$(date +%s)

    # 創建臨時日誌文件
    TMP_LOG="/tmp/migration_${MIGRATION_NAME}_$(date +%s).log"

    # 執行 migration
    if cat "$MIGRATION_FILE" | docker-compose -f "$COMPOSE_FILE" exec -T "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" > "$TMP_LOG" 2>&1; then
        # 計算執行時間（秒 -> 毫秒）
        END_TIME=$(date +%s)
        EXECUTION_TIME=$(( (END_TIME - START_TIME) * 1000 ))

        # 記錄到 schema_migrations
        docker-compose -f "$COMPOSE_FILE" exec -T "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
            INSERT INTO schema_migrations (migration_name, execution_time_ms, success, created_by)
            VALUES ('$MIGRATION_NAME', $EXECUTION_TIME, true, 'run_migrations.sh')
            ON CONFLICT (migration_name) DO NOTHING;
        " > /dev/null 2>&1

        echo -e "  ${GREEN}✓${NC} $MIGRATION_NAME ${GREEN}(成功，耗時 ${EXECUTION_TIME}ms)${NC}"
        EXECUTED_COUNT=$((EXECUTED_COUNT + 1))

        # 清理臨時日誌
        rm -f "$TMP_LOG"
    else
        # 讀取錯誤訊息
        ERROR_MSG=$(cat "$TMP_LOG" | head -n 10 | tr '\n' ' ' | sed "s/'/''/g")

        # 記錄失敗
        docker-compose -f "$COMPOSE_FILE" exec -T "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
            INSERT INTO schema_migrations (migration_name, success, error_message, created_by)
            VALUES ('$MIGRATION_NAME', false, '$ERROR_MSG', 'run_migrations.sh')
            ON CONFLICT (migration_name) DO NOTHING;
        " > /dev/null 2>&1

        echo -e "  ${RED}✗${NC} $MIGRATION_NAME ${RED}(失敗)${NC}"
        echo -e "     ${RED}錯誤: $(cat "$TMP_LOG" | head -n 3)${NC}"
        echo -e "     ${RED}完整錯誤日誌: $TMP_LOG${NC}"

        FAILED_COUNT=$((FAILED_COUNT + 1))
        FAILED_MIGRATIONS+=("$MIGRATION_NAME")

        # 失敗後停止執行
        echo ""
        echo -e "${RED}⚠️  Migration 執行失敗，已停止後續執行${NC}"
        break
    fi
done

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Migration 執行完成${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "總計: $TOTAL_COUNT 個 migration"
echo -e "${GREEN}✓ 成功執行: $EXECUTED_COUNT${NC}"
echo -e "${YELLOW}⊘ 已跳過: $SKIPPED_COUNT${NC}"
if [ $FAILED_COUNT -gt 0 ]; then
    echo -e "${RED}✗ 執行失敗: $FAILED_COUNT${NC}"
    echo ""
    echo -e "${RED}失敗的 migration:${NC}"
    for FAILED in "${FAILED_MIGRATIONS[@]}"; do
        echo -e "  - $FAILED"
    done
fi
echo ""

# 顯示執行歷史
echo -e "${YELLOW}最近 10 次 migration 記錄:${NC}"
docker-compose -f "$COMPOSE_FILE" exec -T "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
    SELECT
        migration_name,
        TO_CHAR(executed_at, 'YYYY-MM-DD HH24:MI:SS') as executed_at,
        CASE WHEN success THEN '✓' ELSE '✗' END as status,
        COALESCE(execution_time_ms::text || 'ms', '-') as time
    FROM schema_migrations
    ORDER BY executed_at DESC
    LIMIT 10;
"

# 回滾提示
if [ $FAILED_COUNT -gt 0 ] && [ "$AUTO_BACKUP" = true ]; then
    echo ""
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}回滾指南${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo ""
    echo -e "如需回滾到執行前的狀態，執行以下命令："
    echo ""
    echo -e "${CYAN}docker exec -i aichatbot-postgres psql -U $DB_USER $DB_NAME < $BACKUP_FILE${NC}"
    echo ""
fi

# 退出碼
if [ $FAILED_COUNT -gt 0 ]; then
    echo -e "${RED}⚠️  有 migration 執行失敗，請檢查上方錯誤訊息${NC}"
    exit 1
else
    echo -e "${GREEN}✓ 所有 migration 已成功執行${NC}"
    exit 0
fi
