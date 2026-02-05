#!/bin/bash

# =====================================================
# 專案清理腳本
# 日期: 2025-02-05
# 功能: 清理臨時檔案、備份檔案、舊測試檔案
# =====================================================

echo "========================================"
echo "   AIChatbot 專案清理腳本"
echo "========================================"
echo ""

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 統計變數
TOTAL_DELETED=0
SPACE_FREED=0

# 確認執行
echo -e "${YELLOW}此腳本將清理以下類型的檔案：${NC}"
echo "1. 備份檔案 (*.bak, *.backup, *.old)"
echo "2. 系統檔案 (.DS_Store)"
echo "3. 舊測試檔案 (scripts/testing/archive/2026-01-26)"
echo ""
read -p "確定要執行清理嗎？(y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${RED}已取消清理${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}開始清理...${NC}"
echo ""

# 1. 清理備份檔案
echo "1. 清理備份檔案..."
BACKUP_FILES=$(find . -name "*.bak" -o -name "*.backup" -o -name "*.old" -o -name "*.swp" 2>/dev/null)
if [ ! -z "$BACKUP_FILES" ]; then
    echo "$BACKUP_FILES" | while read file; do
        if [ -f "$file" ]; then
            SIZE=$(du -h "$file" | cut -f1)
            echo "   刪除: $file ($SIZE)"
            rm -f "$file"
            ((TOTAL_DELETED++))
        fi
    done
else
    echo "   沒有找到備份檔案"
fi

# 2. 清理 .DS_Store
echo ""
echo "2. 清理 Mac 系統檔案..."
DS_STORE_FILES=$(find . -name ".DS_Store" 2>/dev/null)
if [ ! -z "$DS_STORE_FILES" ]; then
    COUNT=$(echo "$DS_STORE_FILES" | wc -l)
    echo "$DS_STORE_FILES" | xargs rm -f
    echo "   已刪除 $COUNT 個 .DS_Store 檔案"
    ((TOTAL_DELETED+=COUNT))
else
    echo "   沒有找到 .DS_Store 檔案"
fi

# 3. 清理 .backup 目錄
echo ""
echo "3. 清理 .backup 目錄..."
if [ -d "rag-orchestrator/routers/.backup" ]; then
    SIZE=$(du -sh "rag-orchestrator/routers/.backup" | cut -f1)
    echo "   刪除: rag-orchestrator/routers/.backup ($SIZE)"
    rm -rf "rag-orchestrator/routers/.backup"
    ((TOTAL_DELETED++))
fi

if [ -d "knowledge-admin/frontend/src/views/.backup" ]; then
    SIZE=$(du -sh "knowledge-admin/frontend/src/views/.backup" | cut -f1)
    echo "   刪除: knowledge-admin/frontend/src/views/.backup ($SIZE)"
    rm -rf "knowledge-admin/frontend/src/views/.backup"
    ((TOTAL_DELETED++))
fi

# 4. 清理舊測試檔案
echo ""
echo "4. 清理舊測試檔案..."
if [ -d "scripts/testing/archive/2026-01-26" ]; then
    COUNT=$(find "scripts/testing/archive/2026-01-26" -type f | wc -l)
    SIZE=$(du -sh "scripts/testing/archive/2026-01-26" | cut -f1)
    echo "   刪除: scripts/testing/archive/2026-01-26 ($COUNT 個檔案, $SIZE)"
    rm -rf "scripts/testing/archive/2026-01-26"
    ((TOTAL_DELETED+=COUNT))
else
    echo "   沒有找到舊測試檔案"
fi

# 5. 詢問是否清理舊的 archive 文件
echo ""
echo -e "${YELLOW}5. 發現 docs/archive 中有 2025 年 10 月的舊文件${NC}"
echo "   - CLEANUP_EXECUTION_REPORT_2025-10-28.md"
echo "   - CLEANUP_SUMMARY_2025-10-28.md"
echo "   - COMPLETE_CLEANUP_PLAN.md"
echo "   - LEGACY_FILES_CLEANUP_2025-10-28.md"
read -p "是否要刪除這些舊文件？(y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "   清理舊文件..."
    rm -f docs/archive/CLEANUP_EXECUTION_REPORT_2025-10-28.md
    rm -f docs/archive/CLEANUP_SUMMARY_2025-10-28.md
    rm -f docs/archive/COMPLETE_CLEANUP_PLAN.md
    rm -f docs/archive/LEGACY_FILES_CLEANUP_2025-10-28.md
    ((TOTAL_DELETED+=4))
    echo -e "   ${GREEN}已刪除 4 個舊文件${NC}"
else
    echo "   跳過舊文件清理"
fi

# 統計結果
echo ""
echo "========================================"
echo -e "${GREEN}清理完成！${NC}"
echo "========================================"
echo ""

# 顯示 Git 狀態
echo "Git 狀態："
git status --short

echo ""
echo -e "${YELLOW}提示：${NC}"
echo "1. 執行 'git status' 查看變更"
echo "2. 執行 'git add -A && git commit -m \"chore: 清理臨時檔案\"' 提交變更"
echo "3. 考慮更新 .gitignore 以防止這些檔案再次出現"