#!/bin/bash
# 背景執行知識庫 Embedding 重新生成
# 用途：將所有知識庫的 embedding 從 question+answer 改為只使用 question
# 根據實測：只使用 question 可提升 9.2% 的檢索匹配度

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
LOG_FILE="/tmp/regenerate_embeddings_$(date +%Y%m%d_%H%M%S).log"

echo "=========================================="
echo "知識庫 Embedding 重新生成（背景執行）"
echo "=========================================="
echo ""
echo "日誌檔案: $LOG_FILE"
echo "專案目錄: $PROJECT_ROOT"
echo ""

cd "$PROJECT_ROOT"

# 檢查 Docker 服務是否運行
if ! docker-compose ps | grep -q "rag-orchestrator.*Up"; then
    echo "❌ rag-orchestrator 服務未運行，請先啟動服務："
    echo "   docker-compose up -d rag-orchestrator"
    exit 1
fi

echo "✅ Docker 服務檢查通過"
echo ""

# 提示用戶確認
echo "⚠️  警告：此操作將重新生成所有知識庫的 embedding"
echo ""
echo "變更說明："
echo "  • 舊策略：question_summary + answer[:200]"
echo "  • 新策略：只使用 question_summary"
echo "  • 預期效果：檢索匹配度提升 9.2%"
echo ""
echo "預估時間：約 10-15 分鐘（依知識庫數量而定）"
echo ""
read -p "確定要繼續嗎？(y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

echo ""
echo "開始重新生成 embedding（背景執行）..."
echo "您可以使用以下指令監控進度："
echo "  tail -f $LOG_FILE"
echo ""

# 使用 nohup 背景執行
nohup docker-compose exec -T rag-orchestrator \
    python3 scripts/regenerate_all_embeddings.py \
    > "$LOG_FILE" 2>&1 &

PID=$!
echo "✅ 背景程序已啟動 (PID: $PID)"
echo ""
echo "監控指令："
echo "  # 即時查看日誌"
echo "  tail -f $LOG_FILE"
echo ""
echo "  # 檢查程序狀態"
echo "  ps aux | grep $PID"
echo ""
echo "  # 結束程序（如需要）"
echo "  kill $PID"
echo ""

# 等待幾秒確認程序啟動
sleep 3

if ps -p $PID > /dev/null; then
    echo "✅ 程序運行中"
    echo ""
    echo "初始日誌輸出："
    head -n 20 "$LOG_FILE" || echo "(日誌尚未產生)"
else
    echo "❌ 程序啟動失敗，請查看日誌："
    echo "  cat $LOG_FILE"
    exit 1
fi
