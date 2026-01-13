#!/bin/bash
# 根目錄整理腳本
# 將文檔、腳本、SQL 文件整理到對應目錄

set -e  # 遇到錯誤立即停止

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         📁 根目錄整理腳本                                  ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 創建目錄結構
echo -e "${BLUE}📁 創建目錄結構...${NC}"
mkdir -p docs/{implementation,analysis,verification,deployment,maintenance}
mkdir -p scripts
mkdir -p sql/hotfixes
echo -e "${GREEN}✅ 目錄結構創建完成${NC}"
echo ""

# 2. 移動文檔到 docs/
echo -e "${BLUE}📚 移動文檔文件...${NC}"

# 主導航文檔
if [ -f "DOCUMENTATION_INDEX.md" ]; then
    mv DOCUMENTATION_INDEX.md docs/README.md
    echo "  ✓ DOCUMENTATION_INDEX.md → docs/README.md"
fi

# 實施文檔
if [ -f "FINAL_IMPLEMENTATION_2026-01-13.md" ]; then
    mv FINAL_IMPLEMENTATION_2026-01-13.md docs/implementation/FINAL_2026-01-13.md
    echo "  ✓ FINAL_IMPLEMENTATION_2026-01-13.md → docs/implementation/"
fi

if [ -f "IMPLEMENTATION_SUMMARY.md" ]; then
    mv IMPLEMENTATION_SUMMARY.md docs/implementation/SUMMARY.md
    echo "  ✓ IMPLEMENTATION_SUMMARY.md → docs/implementation/"
fi

# 分析文檔
if [ -f "RETRIEVAL_LOGIC_COMPLETE_ANALYSIS.md" ]; then
    mv RETRIEVAL_LOGIC_COMPLETE_ANALYSIS.md docs/analysis/retrieval_logic_complete.md
    echo "  ✓ RETRIEVAL_LOGIC_COMPLETE_ANALYSIS.md → docs/analysis/"
fi

if [ -f "RETRIEVAL_PHILOSOPHY_ANALYSIS.md" ]; then
    mv RETRIEVAL_PHILOSOPHY_ANALYSIS.md docs/analysis/retrieval_philosophy.md
    echo "  ✓ RETRIEVAL_PHILOSOPHY_ANALYSIS.md → docs/analysis/"
fi

# 驗證文檔
if [ -f "VERIFICATION_REPORT_2026-01-13.md" ]; then
    mv VERIFICATION_REPORT_2026-01-13.md docs/verification/report_2026-01-13.md
    echo "  ✓ VERIFICATION_REPORT_2026-01-13.md → docs/verification/"
fi

# 部署文檔
if [ -f "DEPLOY_STEPS_2026-01-13.md" ]; then
    mv DEPLOY_STEPS_2026-01-13.md docs/deployment/steps_2026-01-13.md
    echo "  ✓ DEPLOY_STEPS_2026-01-13.md → docs/deployment/"
fi

if [ -f "HOTFIX_STEPS_2026-01-13.md" ]; then
    mv HOTFIX_STEPS_2026-01-13.md docs/deployment/hotfix_2026-01-13.md
    echo "  ✓ HOTFIX_STEPS_2026-01-13.md → docs/deployment/"
fi

# 維護文檔
if [ -f "CLEANUP_REPORT_2026-01-13.md" ]; then
    mv CLEANUP_REPORT_2026-01-13.md docs/maintenance/cleanup_2026-01-13.md
    echo "  ✓ CLEANUP_REPORT_2026-01-13.md → docs/maintenance/"
fi

echo -e "${GREEN}✅ 文檔移動完成${NC}"
echo ""

# 3. 移動腳本到 scripts/
echo -e "${BLUE}🔧 移動腳本文件...${NC}"

if [ -f "test_retrieval_logic_validation.sh" ]; then
    mv test_retrieval_logic_validation.sh scripts/test_retrieval_validation.sh
    chmod +x scripts/test_retrieval_validation.sh
    echo "  ✓ test_retrieval_logic_validation.sh → scripts/"
fi

if [ -f "cleanup_outdated_docs.sh" ]; then
    mv cleanup_outdated_docs.sh scripts/cleanup_docs.sh
    chmod +x scripts/cleanup_docs.sh
    echo "  ✓ cleanup_outdated_docs.sh → scripts/"
fi

echo -e "${GREEN}✅ 腳本移動完成${NC}"
echo ""

# 4. 移動 SQL 文件
echo -e "${BLUE}💾 移動 SQL 文件...${NC}"

if [ -f "HOTFIX_knowledge_1262_classification.sql" ]; then
    mv HOTFIX_knowledge_1262_classification.sql sql/hotfixes/2026-01-13_knowledge_1262.sql
    echo "  ✓ HOTFIX_knowledge_1262_classification.sql → sql/hotfixes/"
fi

echo -e "${GREEN}✅ SQL 文件移動完成${NC}"
echo ""

# 5. 創建 docs/README.md 中的導航索引
echo -e "${BLUE}📝 更新 docs/README.md 路徑...${NC}"

# 更新 docs/README.md 中的路徑
if [ -f "docs/README.md" ]; then
    # 使用 sed 更新路徑（從 ./ 改為相對路徑）
    sed -i.bak 's|(\./FINAL_IMPLEMENTATION|(./implementation/FINAL|g' docs/README.md
    sed -i.bak 's|(\./IMPLEMENTATION_SUMMARY|(./implementation/SUMMARY|g' docs/README.md
    sed -i.bak 's|(\./RETRIEVAL_LOGIC_COMPLETE_ANALYSIS|(./analysis/retrieval_logic_complete|g' docs/README.md
    sed -i.bak 's|(\./RETRIEVAL_PHILOSOPHY_ANALYSIS|(./analysis/retrieval_philosophy|g' docs/README.md
    sed -i.bak 's|(\./VERIFICATION_REPORT|(./verification/report|g' docs/README.md
    sed -i.bak 's|(\./DEPLOY_STEPS|(./deployment/steps|g' docs/README.md
    sed -i.bak 's|(\./HOTFIX_STEPS|(./deployment/hotfix|g' docs/README.md
    sed -i.bak 's|(\./CLEANUP_REPORT|(./maintenance/cleanup|g' docs/README.md
    sed -i.bak 's|(\./test_retrieval_logic_validation|(../scripts/test_retrieval_validation|g' docs/README.md

    # 刪除備份文件
    rm -f docs/README.md.bak

    echo "  ✓ docs/README.md 路徑已更新"
fi

echo -e "${GREEN}✅ 路徑更新完成${NC}"
echo ""

# 6. 顯示整理結果
echo "───────────────────────────────────────────────────────────"
echo ""
echo -e "${BLUE}📊 整理結果${NC}"
echo ""
echo "根目錄文件數："
ROOT_FILES=$(ls -1 | grep -v "^docs$" | grep -v "^scripts$" | grep -v "^sql$" | grep -v "^rag-orchestrator$" | grep -v "^embedding-api$" | grep -v "^knowledge-admin-api$" | grep -v "^knowledge-admin-web$" | wc -l | xargs)
echo "  配置文件: ${ROOT_FILES} 個"
echo ""

echo "docs/ 結構："
tree -L 2 docs/ 2>/dev/null || find docs/ -type f | sed 's|^docs/|  |' | sort

echo ""
echo "scripts/ 內容："
ls -1 scripts/ 2>/dev/null | sed 's/^/  /' || echo "  (無)"

echo ""
echo "sql/ 結構："
tree -L 2 sql/ 2>/dev/null || find sql/ -type f | sed 's|^sql/|  |' | sort

echo ""
echo "───────────────────────────────────────────────────────────"
echo ""
echo -e "${GREEN}✅ 根目錄整理完成！${NC}"
echo ""
echo -e "${YELLOW}📝 後續步驟：${NC}"
echo "  1. 檢查整理結果"
echo "  2. 測試腳本是否正常運行"
echo "  3. Git 提交變更："
echo "     git add -A"
echo "     git commit -m 'refactor: 整理根目錄，建立清晰的項目結構'"
echo ""
