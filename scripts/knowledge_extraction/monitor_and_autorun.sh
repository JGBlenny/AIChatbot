#!/bin/bash

# 知識提取監控與自動執行腳本
# 監控提取進度，完成後自動導入並回測

OUTPUT_DIR="/Users/lenny/jgb/AIChatbot/output"
KNOWLEDGE_FILE="$OUTPUT_DIR/knowledge_base_extracted.xlsx"
TEST_FILE="$OUTPUT_DIR/test_scenarios.xlsx"

echo "============================================================"
echo "知識提取監控與自動執行"
echo "============================================================"
echo

# 等待提取完成
while true; do
    if [ -f "$KNOWLEDGE_FILE" ] && [ -f "$TEST_FILE" ]; then
        echo "✅ 提取完成！檢測到輸出文件"
        echo "   - $KNOWLEDGE_FILE"
        echo "   - $TEST_FILE"
        echo
        break
    fi

    echo "⏳ 等待提取完成..."
    sleep 30
done

# 檢查文件大小
kb_size=$(ls -lh "$KNOWLEDGE_FILE" | awk '{print $5}')
test_size=$(ls -lh "$TEST_FILE" | awk '{print $5}')

echo "文件大小:"
echo "   知識庫: $kb_size"
echo "   測試情境: $test_size"
echo

# 詢問是否繼續
echo "是否要繼續執行以下步驟？"
echo "1. 導入知識到資料庫"
echo "2. 執行回測驗證"
echo
read -p "繼續? (y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 已取消後續步驟"
    exit 0
fi

# Step 1: 導入知識庫
echo
echo "============================================================"
echo "步驟 1: 導入知識庫到資料庫"
echo "============================================================"
echo

# OPENAI_API_KEY should be set in environment before running this script
# export OPENAI_API_KEY=your-key-here

# TODO: 這裡需要一個腳本將 Excel 導入資料庫
# python3 scripts/knowledge_extraction/import_extracted_to_db.py

echo "⚠️  注意：目前需要手動導入知識庫"
echo "   選項 1: 使用前端頁面 http://localhost:8200/knowledge"
echo "   選項 2: 使用 import_excel_to_kb.py (需要調整)"
echo

read -p "知識庫已導入？繼續回測？(y/N): " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 已取消回測"
    exit 0
fi

# Step 2: 執行回測
echo
echo "============================================================"
echo "步驟 2: 執行回測驗證"
echo "============================================================"
echo

python3 scripts/knowledge_extraction/backtest_framework.py

echo
echo "============================================================"
echo "✅ 全部完成！"
echo "============================================================"
echo
echo "檢查結果："
echo "   知識庫: $KNOWLEDGE_FILE"
echo "   測試情境: $TEST_FILE"
echo "   回測結果: $OUTPUT_DIR/backtest/backtest_results.xlsx"
echo "   回測摘要: $OUTPUT_DIR/backtest/backtest_results_summary.txt"
