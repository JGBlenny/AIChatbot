#!/bin/bash

echo "🔧 快速修復腳本 - 批量審核功能顯示問題"
echo "============================================"
echo ""

# 1. 檢查檔案大小
echo "📊 1. 檢查 LoopKnowledgeReviewTab.vue 檔案..."
FILE_SIZE=$(wc -c < src/components/review/LoopKnowledgeReviewTab.vue)
echo "   檔案大小: $FILE_SIZE bytes"

if [ "$FILE_SIZE" -lt 30000 ]; then
    echo "   ❌ 檔案太小！應該約 35KB"
    echo "   可能修改沒有儲存成功"
    exit 1
else
    echo "   ✅ 檔案大小正常"
fi

# 2. 檢查關鍵代碼是否存在
echo ""
echo "📝 2. 檢查批量審核程式碼..."

if grep -q "selectedIds: \[\]" src/components/review/LoopKnowledgeReviewTab.vue; then
    echo "   ✅ selectedIds 狀態存在"
else
    echo "   ❌ selectedIds 狀態不存在"
    exit 1
fi

if grep -q "toggleSelectAll()" src/components/review/LoopKnowledgeReviewTab.vue; then
    echo "   ✅ toggleSelectAll 方法存在"
else
    echo "   ❌ toggleSelectAll 方法不存在"
    exit 1
fi

if grep -q "showBatchApproveDialog()" src/components/review/LoopKnowledgeReviewTab.vue; then
    echo "   ✅ showBatchApproveDialog 方法存在"
else
    echo "   ❌ showBatchApproveDialog 方法不存在"
    exit 1
fi

if grep -q "batch-action-toolbar" src/components/review/LoopKnowledgeReviewTab.vue; then
    echo "   ✅ 批量操作工具列存在"
else
    echo "   ❌ 批量操作工具列不存在"
    exit 1
fi

if grep -q "select-all-section" src/components/review/LoopKnowledgeReviewTab.vue; then
    echo "   ✅ 全選區域存在"
else
    echo "   ❌ 全選區域不存在"
    exit 1
fi

# 3. 清除 dist 目錄
echo ""
echo "🗑️  3. 清除舊的編譯檔案..."
rm -rf dist/
echo "   ✅ dist 目錄已清除"

# 4. 重新編譯
echo ""
echo "🔨 4. 重新編譯前端..."
npm run build

if [ $? -eq 0 ]; then
    echo "   ✅ 編譯成功"
else
    echo "   ❌ 編譯失敗"
    exit 1
fi

# 5. 檢查 API 是否正常
echo ""
echo "🌐 5. 檢查後端 API..."
STATS=$(curl -s http://localhost:8100/api/v1/loop-knowledge/stats)

if [ $? -eq 0 ]; then
    echo "   ✅ API 連線正常"
    echo "   統計: $STATS"
else
    echo "   ❌ API 連線失敗"
    exit 1
fi

# 完成
echo ""
echo "============================================"
echo "✅ 所有檢查通過！"
echo ""
echo "📋 接下來請執行："
echo "   1. 關閉所有瀏覽器視窗"
echo "   2. 重新啟動開發伺服器: npm run dev"
echo "   3. 開啟無痕模式瀏覽器"
echo "   4. 訪問: http://localhost:8087/review-center"
echo "   5. 切換到「🔄 迴圈知識審核」Tab"
echo ""
echo "如果仍然看不到批量審核功能，請："
echo "   - 按 F12 打開開發者工具"
echo "   - 查看 Console 是否有錯誤訊息"
echo "   - 查看 Network 是否有 API 請求"
echo ""
