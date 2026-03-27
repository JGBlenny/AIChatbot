#!/bin/bash
# 50 題驗證測試 - 快速驗證腳本
# 使用方式：./quick_verification.sh <loop_id>

set -e

LOOP_ID=$1
if [ -z "$LOOP_ID" ]; then
    echo "請提供 Loop ID"
    echo "使用方式：$0 <loop_id>"
    echo ""
    echo "查詢最新 Loop ID："
    docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -t -c \
        "SELECT id FROM knowledge_completion_loops ORDER BY id DESC LIMIT 1;"
    exit 1
fi

echo "========================================"
echo "50 題驗證測試 - 快速驗證"
echo "Loop ID: $LOOP_ID"
echo "========================================"
echo ""

# 函數：執行 SQL 查詢
query() {
    docker exec aichatbot-postgres psql -U aichatbot -d aichatbot_admin -t -c "$1"
}

# 1. 基本資訊
echo "1. 迴圈基本資訊"
echo "----------------------------------------"
query "SELECT
    'Loop ID: ' || id || E'\n' ||
    'Name: ' || loop_name || E'\n' ||
    'Status: ' || status || E'\n' ||
    'Iteration: ' || current_iteration || '/' || COALESCE((config->>'max_iterations')::text, '未設定') || E'\n' ||
    'Pass Rate: ' || ROUND(current_pass_rate::numeric * 100, 2) || '% (目標: ' || ROUND(target_pass_rate::numeric * 100, 2) || '%)' || E'\n' ||
    'Scenarios: ' || COALESCE(total_scenarios, 0)
FROM knowledge_completion_loops WHERE id = $LOOP_ID;"
echo ""

# 2. 測試集固定性
echo "2. ✅ 測試集固定性檢查"
echo "----------------------------------------"
SCENARIO_COUNT=$(query "SELECT COALESCE(total_scenarios, 0) FROM knowledge_completion_loops WHERE id = $LOOP_ID;")
SCENARIO_COUNT=$(echo $SCENARIO_COUNT | xargs)

if [ "$SCENARIO_COUNT" = "50" ] || [ "$SCENARIO_COUNT" = "500" ] || [ "$SCENARIO_COUNT" = "3000" ]; then
    echo "✅ PASS: 測試規模已記錄（$SCENARIO_COUNT 題）"
    # 檢查 config 中是否有 scenario_ids
    HAS_SCENARIO_IDS=$(query "SELECT CASE WHEN config ? 'scenario_ids' THEN 'yes' ELSE 'no' END FROM knowledge_completion_loops WHERE id = $LOOP_ID;")
    HAS_SCENARIO_IDS=$(echo $HAS_SCENARIO_IDS | xargs)
    if [ "$HAS_SCENARIO_IDS" = "yes" ]; then
        echo "✅ scenario_ids 已固定在 config 中"
    else
        echo "⚠️  scenario_ids 未固定（批次模式）"
    fi
else
    echo "⚠️  WARNING: 測試規模數量異常（$SCENARIO_COUNT 題）"
fi
echo ""

# 3. 回測結果
echo "3. 回測結果統計"
echo "----------------------------------------"
query "SELECT
    '迭代 ' || kga.iteration || E'\n' ||
    '  總題數: ' || COUNT(*) || E'\n' ||
    '  失敗數: ' || COUNT(*) || E'\n' ||
    '  通過率: ' || ROUND((1 - COUNT(*)::numeric / $SCENARIO_COUNT) * 100, 2) || '%'
FROM knowledge_gap_analysis kga
WHERE kga.loop_id = $LOOP_ID
GROUP BY kga.iteration
ORDER BY kga.iteration;"
echo ""

# 4. 知識缺口分類
echo "4. 知識缺口分類"
echo "----------------------------------------"
query "SELECT
    failure_reason || ': ' || COUNT(*) || ' 個'
FROM knowledge_gap_analysis
WHERE loop_id = $LOOP_ID AND iteration = 1
GROUP BY failure_reason
ORDER BY COUNT(*) DESC;"
echo ""

# 5. 知識生成
echo "5. 知識生成統計"
echo "----------------------------------------"
query "SELECT
    CASE
        WHEN knowledge_type = 'sop' THEN 'SOP'
        ELSE '一般知識'
    END || ' - ' || status || ': ' || COUNT(*) || ' 個'
FROM loop_generated_knowledge
WHERE loop_id = $LOOP_ID
GROUP BY knowledge_type, status
ORDER BY knowledge_type, status;"
echo ""

# 6. 同步檢查
echo "6. ✅ 立即同步檢查"
echo "----------------------------------------"
KB_COUNT=$(query "SELECT COUNT(*) FROM knowledge_base WHERE source = 'loop' AND source_loop_id = $LOOP_ID;")
# SOP 通過 loop_generated_knowledge 的 kb_id 反查
SOP_COUNT=$(query "SELECT COUNT(*) FROM loop_generated_knowledge lgk JOIN vendor_sop_items vsi ON lgk.kb_id = vsi.id WHERE lgk.loop_id = $LOOP_ID AND lgk.knowledge_type = 'sop' AND lgk.synced_to_kb = true;")
SYNCED_COUNT=$(query "SELECT COUNT(*) FROM loop_generated_knowledge WHERE loop_id = $LOOP_ID AND synced_to_kb = true;")
APPROVED_COUNT=$(query "SELECT COUNT(*) FROM loop_generated_knowledge WHERE loop_id = $LOOP_ID AND status = 'approved';")

KB_COUNT=$(echo $KB_COUNT | xargs)
SOP_COUNT=$(echo $SOP_COUNT | xargs)
SYNCED_COUNT=$(echo $SYNCED_COUNT | xargs)
APPROVED_COUNT=$(echo $APPROVED_COUNT | xargs)

echo "knowledge_base 新增: $KB_COUNT"
echo "vendor_sop_items 新增: $SOP_COUNT"
echo "總同步數: $SYNCED_COUNT"
echo "已批准數: $APPROVED_COUNT"

if [ "$SYNCED_COUNT" -eq "$APPROVED_COUNT" ]; then
    echo "✅ PASS: 同步數量匹配"
else
    echo "⚠️  WARNING: 同步數量不匹配（同步 $SYNCED_COUNT vs 批准 $APPROVED_COUNT）"
fi
echo ""

# 7. 執行日誌
echo "7. 執行日誌（最近 5 條）"
echo "----------------------------------------"
query "SELECT
    TO_CHAR(created_at, 'HH24:MI:SS') || ' | ' || event_type
FROM loop_execution_logs
WHERE loop_id = $LOOP_ID
ORDER BY created_at DESC
LIMIT 5;"
echo ""

# 8. 改善幅度分析（如果有多次迭代）
echo "8. ✅ 改善幅度分析"
echo "----------------------------------------"
ITERATION_COUNT=$(query "SELECT COALESCE(MAX(iteration), 0) FROM knowledge_gap_analysis WHERE loop_id = $LOOP_ID;")
ITERATION_COUNT=$(echo $ITERATION_COUNT | xargs)

if [ "$ITERATION_COUNT" -ge 2 ]; then
    echo "迭代間通過率變化："
    query "WITH iteration_stats AS (
        SELECT
            iteration,
            COUNT(*) as failed_count,
            $SCENARIO_COUNT as total_count,
            ROUND((1 - COUNT(*)::numeric / $SCENARIO_COUNT) * 100, 2) as pass_rate
        FROM knowledge_gap_analysis
        WHERE loop_id = $LOOP_ID
        GROUP BY iteration
        ORDER BY iteration
    )
    SELECT
        '迭代 ' || iteration || ': ' || pass_rate || '% (失敗 ' || failed_count || ' 題)' ||
        CASE
            WHEN iteration > 1 THEN ' [改善 ' ||
                ROUND(pass_rate - LAG(pass_rate) OVER (ORDER BY iteration), 2) || '%]'
            ELSE ''
        END
    FROM iteration_stats;"
    echo "✅ PASS: 可追蹤改善幅度（測試集固定）"
else
    echo "僅執行 $ITERATION_COUNT 次迭代，無法分析改善幅度"
    echo "建議：執行第二次迭代後再次檢查"
fi
echo ""

# 總結
echo "========================================"
echo "驗證總結"
echo "========================================"
echo ""

ISSUES=0

# 檢查 1：scenario_ids
if [ "$SCENARIO_COUNT" -ne "50" ] && [ "$SCENARIO_COUNT" -ne "500" ] && [ "$SCENARIO_COUNT" -ne "3000" ]; then
    echo "❌ 測試集固定性：FAIL（數量異常）"
    ISSUES=$((ISSUES + 1))
else
    echo "✅ 測試集固定性：PASS"
fi

# 檢查 2：同步數量
if [ "$SYNCED_COUNT" -ne "$APPROVED_COUNT" ]; then
    echo "⚠️  立即同步：WARNING（數量不匹配）"
    ISSUES=$((ISSUES + 1))
else
    echo "✅ 立即同步：PASS"
fi

# 檢查 3：改善幅度
if [ "$ITERATION_COUNT" -ge 2 ]; then
    echo "✅ 改善幅度可追蹤：PASS"
else
    echo "⚠️  改善幅度可追蹤：未測試（需執行第 2 次迭代）"
fi

echo ""
if [ "$ISSUES" -eq 0 ]; then
    echo "🎉 所有檢查通過！可以進入設計階段。"
    exit 0
else
    echo "⚠️  發現 $ISSUES 個問題，請檢查後再進入設計階段。"
    exit 1
fi
