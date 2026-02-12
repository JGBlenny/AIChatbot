#!/bin/bash

# 完整對話流程測試腳本 - 2026-01-24
# 測試所有主要流程路徑

API_URL="http://localhost:8100/api/v1/message"
VENDOR_ID=1
LOG_FILE="/tmp/chat_flow_test_$(date +%Y%m%d_%H%M%S).log"

echo "========================================"
echo "對話流程完整測試"
echo "開始時間: $(date)"
echo "========================================"
echo "" | tee -a "$LOG_FILE"

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 測試計數器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 測試函數
run_test() {
    local test_name="$1"
    local test_data="$2"
    local expected_keyword="$3"

    ((TOTAL_TESTS++))

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}測試 $TOTAL_TESTS: $test_name${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    echo "請求數據:" | tee -a "$LOG_FILE"
    echo "$test_data" | jq '.' 2>/dev/null || echo "$test_data" | tee -a "$LOG_FILE"

    echo "" | tee -a "$LOG_FILE"
    echo "發送請求..." | tee -a "$LOG_FILE"

    response=$(curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "$test_data")

    echo "回應:" | tee -a "$LOG_FILE"
    echo "$response" | jq '.' 2>/dev/null || echo "$response" | tee -a "$LOG_FILE"

    # 驗證結果
    if echo "$response" | grep -q "$expected_keyword"; then
        echo -e "${GREEN}✅ 測試通過${NC}" | tee -a "$LOG_FILE"
        ((PASSED_TESTS++))
    else
        echo -e "${RED}❌ 測試失敗 - 未找到關鍵字: $expected_keyword${NC}" | tee -a "$LOG_FILE"
        ((FAILED_TESTS++))
    fi

    echo "" | tee -a "$LOG_FILE"
    sleep 1
}

echo ""
echo "========================================" | tee -a "$LOG_FILE"
echo "測試 A: 表單會話流程" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo ""

# A1: 觸發表單（知識庫 action_type=form_fill）
SESSION_A="test_form_flow_$(date +%s)"
run_test "A1: 觸發表單（我想租房子）" \
'{
  "message": "我想租房子",
  "vendor_id": '"$VENDOR_ID"',
  "session_id": "'"$SESSION_A"'",
  "user_id": "test_user_a",
  "target_user": "tenant"
}' \
"姓名"

# A2: COLLECTING 狀態 - 輸入姓名
run_test "A2: COLLECTING - 輸入姓名" \
'{
  "message": "王小明",
  "vendor_id": '"$VENDOR_ID"',
  "session_id": "'"$SESSION_A"'",
  "user_id": "test_user_a",
  "target_user": "tenant"
}' \
"電話"

# A3: COLLECTING 狀態 - 輸入電話
run_test "A3: COLLECTING - 輸入電話" \
'{
  "message": "0912345678",
  "vendor_id": '"$VENDOR_ID"',
  "session_id": "'"$SESSION_A"'",
  "user_id": "test_user_a",
  "target_user": "tenant"
}' \
"email"

# A4: COLLECTING 狀態 - 輸入 email
run_test "A4: COLLECTING - 輸入 email" \
'{
  "message": "test@example.com",
  "vendor_id": '"$VENDOR_ID"',
  "session_id": "'"$SESSION_A"'",
  "user_id": "test_user_a",
  "target_user": "tenant"
}' \
"預算"

# A5: COLLECTING 狀態 - 輸入預算
run_test "A5: COLLECTING - 輸入預算" \
'{
  "message": "15000-20000",
  "vendor_id": '"$VENDOR_ID"',
  "session_id": "'"$SESSION_A"'",
  "user_id": "test_user_a",
  "target_user": "tenant"
}' \
"地區"

# A6: COLLECTING 狀態 - 輸入地區
run_test "A6: COLLECTING - 輸入地區" \
'{
  "message": "台北市信義區",
  "vendor_id": '"$VENDOR_ID"',
  "session_id": "'"$SESSION_A"'",
  "user_id": "test_user_a",
  "target_user": "tenant"
}' \
"確認"

# A7: REVIEWING 狀態 - 確認提交
run_test "A7: REVIEWING - 確認提交" \
'{
  "message": "確認",
  "vendor_id": '"$VENDOR_ID"',
  "session_id": "'"$SESSION_A"'",
  "user_id": "test_user_a",
  "target_user": "tenant"
}' \
"已收到"

echo ""
echo "========================================" | tee -a "$LOG_FILE"
echo "測試 B: 知識庫 action_type（高質量過濾）" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo ""

# B1: 普通知識（direct_answer）
SESSION_B="test_knowledge_$(date +%s)"
run_test "B1: 普通知識回答" \
'{
  "message": "租金怎麼繳？",
  "vendor_id": '"$VENDOR_ID"',
  "session_id": "'"$SESSION_B"'",
  "user_id": "test_user_b",
  "target_user": "tenant"
}' \
"繳"

echo ""
echo "========================================" | tee -a "$LOG_FILE"
echo "測試 C: 無知識處理" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo ""

# C1: 參數型問題
SESSION_C="test_param_$(date +%s)"
run_test "C1: 參數型問題 - 繳費日" \
'{
  "message": "繳費日是幾號？",
  "vendor_id": '"$VENDOR_ID"',
  "session_id": "'"$SESSION_C"'",
  "user_id": "test_user_c",
  "target_user": "tenant"
}' \
"號"

# C2: 兜底回應
SESSION_C2="test_fallback_$(date +%s)"
run_test "C2: 兜底回應 - 完全無關問題" \
'{
  "message": "火星旅遊多少錢？",
  "vendor_id": '"$VENDOR_ID"',
  "session_id": "'"$SESSION_C2"'",
  "user_id": "test_user_c2",
  "target_user": "tenant"
}' \
"沒有找到"

echo ""
echo "========================================" | tee -a "$LOG_FILE"
echo "測試 D: unclear 意圖處理" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo ""

# D1: unclear 意圖
SESSION_D="test_unclear_$(date +%s)"
run_test "D1: unclear 意圖" \
'{
  "message": "嗯嗯",
  "vendor_id": '"$VENDOR_ID"',
  "session_id": "'"$SESSION_D"'",
  "user_id": "test_user_d",
  "target_user": "tenant"
}' \
"unclear"

echo ""
echo "========================================" | tee -a "$LOG_FILE"
echo "測試 E: 離題偵測" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo ""

# E1: 觸發表單
SESSION_E="test_digression_$(date +%s)"
run_test "E1: 觸發表單" \
'{
  "message": "我想租房子",
  "vendor_id": '"$VENDOR_ID"',
  "session_id": "'"$SESSION_E"'",
  "user_id": "test_user_e",
  "target_user": "tenant"
}' \
"姓名"

# E2: 填寫中突然問問題（離題）
run_test "E2: 填寫中突然問問題（離題）" \
'{
  "message": "租金怎麼繳？",
  "vendor_id": '"$VENDOR_ID"',
  "session_id": "'"$SESSION_E"'",
  "user_id": "test_user_e",
  "target_user": "tenant"
}' \
"繼續填寫"

echo ""
echo "========================================" | tee -a "$LOG_FILE"
echo "測試總結" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo ""

echo "總測試數: $TOTAL_TESTS" | tee -a "$LOG_FILE"
echo -e "${GREEN}通過: $PASSED_TESTS${NC}" | tee -a "$LOG_FILE"
echo -e "${RED}失敗: $FAILED_TESTS${NC}" | tee -a "$LOG_FILE"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有測試通過！${NC}" | tee -a "$LOG_FILE"
    exit 0
else
    echo -e "${RED}❌ 部分測試失敗${NC}" | tee -a "$LOG_FILE"
    exit 1
fi
