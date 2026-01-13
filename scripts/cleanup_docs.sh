#!/bin/bash
# 清理過時文檔腳本
# 將過時文檔移動到 docs/archive/ 目錄

echo "🗂️  清理過時文檔..."
echo ""

# 創建 archive 目錄
mkdir -p docs/archive/2026-01-13

# 過時文檔列表
OUTDATED_DOCS=(
    "RETRIEVAL_LOGIC_EVALUATION.md"
    "VERIFICATION_COMPLETE.md"
    "PROPOSED_FIX_high_similarity_bypass.py"
)

echo "以下文檔將被移到 docs/archive/2026-01-13/："
echo ""

for doc in "${OUTDATED_DOCS[@]}"; do
    if [ -f "$doc" ]; then
        echo "  ⚠️  $doc"
    fi
done

echo ""
read -p "確定要移動這些文檔嗎？(y/N) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    for doc in "${OUTDATED_DOCS[@]}"; do
        if [ -f "$doc" ]; then
            mv "$doc" "docs/archive/2026-01-13/"
            echo "  ✅ 已移動：$doc"
        fi
    done

    echo ""
    echo "✅ 清理完成！"
    echo ""
    echo "過時文檔已移至：docs/archive/2026-01-13/"
    echo "如需復原，請使用：mv docs/archive/2026-01-13/* ."
else
    echo ""
    echo "❌ 取消清理"
fi
