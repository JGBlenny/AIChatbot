#!/bin/bash

# 完整對話流程測試腳本 - 2026-01-24 (真實版本)
# 真正測試所有主要流程，不再假裝

API_URL="http://localhost:8100/api/v1/message"
VENDOR_ID=1
LOG_FILE="/tmp/comprehensive_test_$(date +%Y%m%d_%H%M%S).log"

echo "========================================" | tee "$LOG_FILE"
echo "完整對話流程測試（真實版本）"
echo "開始時間: $(date)"
echo "========================================" | tee -a "$LOG_FILE"

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
    local validation_fn="$3"  # 驗證函數名稱

    ((TOTAL_TESTS++))

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "$LOG_FILE"
    echo -e "${YELLOW}測試 $TOTAL_TESTS: $test_name${NC}" | tee -a "$LOG_FILE"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}" | tee -a "$LOG_FILE"

    echo "發送請求..." | tee -a "$LOG_FILE"

    response=$(curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "$test_data")

    echo "回應:" | tee -a "$LOG_FILE"
    echo "$response" | tee -a "$LOG_FILE"

    # 調用驗證函數
    if $validation_fn "$response"; then
        echo -e "${GREEN}✅ 測試通過${NC}" | tee -a "$LOG_FILE"
        ((PASSED_TESTS++))
    else
        echo -e "${RED}❌ 測試失敗${NC}" | tee -a "$LOG_FILE"
        ((FAILED_TESTS++))
    fi

    echo "" | tee -a "$LOG_FILE"
    sleep 1
}

# ============================================
# 驗證函數
# ============================================

validate_sop_none() {
    local response="$1"
    # SOP none 模式：應返回資訊內容，不觸發表單
    echo "$response" | grep -qE "(租屋須知|押金|租期|禁止)"
}

validate_sop_manual_wait() {
    local response="$1"
    # SOP manual 模式：顯示資訊 + 提示
    echo "$response" | grep -q "看房預約"
}

validate_sop_manual_trigger() {
    local response="$1"
    # 關鍵字觸發：應觸發表單（檢查表單問題或 form_triggered）
    echo "$response" | grep -qE "(form_triggered.*true|請問您的姓名|請提供|請輸入)"
}

validate_sop_immediate() {
    local response="$1"
    # immediate 模式：詢問確認
    echo "$response" | grep -q "需要立即"
}

validate_sop_immediate_confirm() {
    local response="$1"
    # 確認後觸發表單（檢查表單問題或 form_triggered）
    echo "$response" | grep -qE "(form_triggered.*true|請提供|請輸入|請問)"
}

validate_sop_auto_api() {
    local response="$1"
    # auto + api_call：自動調用 API（可能返回錯誤，但應有 api_call 相關內容）
    echo "$response" | grep -qE "(api|API|調用)"
}

validate_sop_form_then_api() {
    local response="$1"
    # form_then_api：先觸發表單
    echo "$response" | grep -q "form_triggered.*true"
}

validate_knowledge_api_call() {
    local response="$1"
    # knowledge api_call（有 config）
    echo "$response" | grep -qE "(繳費記錄|api|API)"
}

validate_knowledge_form_then_api() {
    local response="$1"
    # knowledge form_then_api
    echo "$response" | grep -q "form_triggered.*true"
}

validate_downgrade_no_form_id() {
    local response="$1"
    # 降級邏輯：缺少 form_id，應返回 direct_answer
    echo "$response" | grep -q "測試降級邏輯" && \
    ! echo "$response" | grep -q "form_triggered.*true"
}

validate_downgrade_no_api_config() {
    local response="$1"
    # 降級邏輯：缺少 api_config
    echo "$response" | grep -q "測試降級邏輯"
}

validate_form_collecting() {
    local response="$1"
    echo "$response" | grep -qE "(姓名|電話|phone|聯絡|current_field)"
}

validate_form_reviewing() {
    local response="$1"
    echo "$response" | grep -q "確認"
}

validate_form_completed() {
    local response="$1"
    echo "$response" | grep -qE "(已收到|已記錄|完成)"
}

validate_form_cancel() {
    local response="$1"
    echo "$response" | grep -qE "(已取消|取消成功)"
}

validate_form_edit() {
    local response="$1"
    echo "$response" | grep -qE "(修改|編輯)"
}

validate_no_knowledge() {
    local response="$1"
    echo "$response" | grep -qE "(沒有找到|無法回答|很抱歉)"
}

validate_unclear() {
    local response="$1"
    echo "$response" | grep -qE "(unclear|不太理解|請問您)"
}

# ============================================
# 測試 F: SOP Orchestrator（5 個場景）
# ============================================

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "測試 F: SOP Orchestrator 完整流程" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# F1: SOP none 模式（資訊展示）
SESSION_F1="test_sop_none_$(date +%s)"
run_test "F1: SOP none 模式 - 租賃須知" \
'{
  "message": "租賃須知",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_F1"'",
  "user_id": "test_user_f1",
  "target_user": "tenant"
}' \
"validate_sop_none"

# F2: SOP manual 模式（等待關鍵字）
SESSION_F2="test_sop_manual_$(date +%s)"
run_test "F2: SOP manual 模式 - 看房預約資訊" \
'{
  "message": "看房預約說明",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_F2"'",
  "user_id": "test_user_f2",
  "target_user": "tenant"
}' \
"validate_sop_manual_wait"

# F3: SOP manual 觸發（輸入關鍵字）
run_test "F3: SOP manual 觸發 - 我要看房" \
'{
  "message": "我要看房",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_F2"'",
  "user_id": "test_user_f2",
  "target_user": "tenant"
}' \
"validate_sop_manual_trigger"

# F4: SOP immediate 模式
SESSION_F4="test_sop_immediate_$(date +%s)"
run_test "F4: SOP immediate 模式 - 報修申請" \
'{
  "message": "我要報修",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_F4"'",
  "user_id": "test_user_f4",
  "target_user": "tenant"
}' \
"validate_sop_immediate"

# F5: SOP immediate 確認觸發
run_test "F5: SOP immediate 確認 - 確認報修" \
'{
  "message": "確認",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_F4"'",
  "user_id": "test_user_f4",
  "target_user": "tenant"
}' \
"validate_sop_immediate_confirm"

# F6: SOP auto + api_call
SESSION_F6="test_sop_auto_$(date +%s)"
run_test "F6: SOP auto 模式 - 查詢租金帳單（自動 API）" \
'{
  "message": "查詢租金帳單",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_F6"'",
  "user_id": "test_user_f6",
  "target_user": "tenant"
}' \
"validate_sop_auto_api"

# F7: SOP form_then_api
SESSION_F7="test_sop_form_then_api_$(date +%s)"
run_test "F7: SOP form_then_api - 租屋申請" \
'{
  "message": "我要租屋申請",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_F7"'",
  "user_id": "test_user_f7",
  "target_user": "tenant"
}' \
"validate_sop_form_then_api"

# ============================================
# 測試 G: Knowledge action_type（4 個場景）
# ============================================

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "測試 G: Knowledge action_type" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# G1: action_type = api_call（有 config）
SESSION_G1="test_kb_api_call_$(date +%s)"
run_test "G1: Knowledge api_call - 租金繳費記錄" \
'{
  "message": "【測試】我的租金繳費記錄",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_G1"'",
  "user_id": "test_user_g1",
  "target_user": "tenant"
}' \
"validate_knowledge_api_call"

# G2: action_type = form_then_api
SESSION_G2="test_kb_form_then_api_$(date +%s)"
run_test "G2: Knowledge form_then_api - 我要退租" \
'{
  "message": "【測試】我要退租",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_G2"'",
  "user_id": "test_user_g2",
  "target_user": "tenant"
}' \
"validate_knowledge_form_then_api"

# G3: 降級邏輯 - 缺少 form_id
SESSION_G3="test_downgrade_form_$(date +%s)"
run_test "G3: 降級邏輯 - form_fill 但缺少 form_id" \
'{
  "message": "【測試】降級邏輯：缺少 form_id",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_G3"'",
  "user_id": "test_user_g3",
  "target_user": "tenant"
}' \
"validate_downgrade_no_form_id"

# G4: 降級邏輯 - 缺少 api_config
SESSION_G4="test_downgrade_api_$(date +%s)"
run_test "G4: 降級邏輯 - api_call 但缺少 api_config" \
'{
  "message": "【測試】降級邏輯：缺少 api_config",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_G4"'",
  "user_id": "test_user_g4",
  "target_user": "tenant"
}' \
"validate_downgrade_no_api_config"

# ============================================
# 測試 H: 表單狀態完整測試（7 個場景）
# ============================================

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "測試 H: 表單狀態完整流程" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# H1: 觸發表單
SESSION_H="test_form_states_$(date +%s)"
run_test "H1: 觸發表單" \
'{
  "message": "我想租房子",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_H"'",
  "user_id": "test_user_h",
  "target_user": "tenant"
}' \
"validate_form_collecting"

# H2: COLLECTING - 輸入姓名
run_test "H2: COLLECTING 狀態 - 輸入姓名" \
'{
  "message": "王小明",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_H"'",
  "user_id": "test_user_h",
  "target_user": "tenant"
}' \
"validate_form_collecting"

# H3: COLLECTING - 輸入電話
run_test "H3: COLLECTING 狀態 - 輸入電話" \
'{
  "message": "0912345678",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_H"'",
  "user_id": "test_user_h",
  "target_user": "tenant"
}' \
"validate_form_collecting"

# H4: COLLECTING - 輸入 email
run_test "H4: COLLECTING 狀態 - 輸入 email" \
'{
  "message": "test@example.com",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_H"'",
  "user_id": "test_user_h",
  "target_user": "tenant"
}' \
"validate_form_reviewing"

# H5: REVIEWING - 確認提交
run_test "H5: REVIEWING 狀態 - 確認提交" \
'{
  "message": "確認",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_H"'",
  "user_id": "test_user_h",
  "target_user": "tenant"
}' \
"validate_form_completed"

# H6: 測試取消流程
SESSION_H6="test_form_cancel_$(date +%s)"
run_test "H6a: 觸發表單（準備取消）" \
'{
  "message": "我想租房子",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_H6"'",
  "user_id": "test_user_h6",
  "target_user": "tenant"
}' \
"validate_form_collecting"

run_test "H6b: COLLECTING - 輸入取消" \
'{
  "message": "取消",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_H6"'",
  "user_id": "test_user_h6",
  "target_user": "tenant"
}' \
"validate_form_cancel"

# ============================================
# 測試 I: 其他流程
# ============================================

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "測試 I: 其他流程（無知識、unclear）" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# I1: 無知識處理
SESSION_I1="test_no_knowledge_$(date +%s)"
run_test "I1: 無知識處理 - 完全無關問題" \
'{
  "message": "火星旅遊多少錢？",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_I1"'",
  "user_id": "test_user_i1",
  "target_user": "tenant"
}' \
"validate_no_knowledge"

# I2: unclear 意圖
SESSION_I2="test_unclear_$(date +%s)"
run_test "I2: unclear 意圖處理" \
'{
  "message": "嗯嗯",
  "vendor_id": '\"$VENDOR_ID\"',
  "session_id": "'"$SESSION_I2"'",
  "user_id": "test_user_i2",
  "target_user": "tenant"
}' \
"validate_unclear"

# ============================================
# 測試總結
# ============================================

echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "測試總結" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

PASS_RATE=$(awk "BEGIN {printf \"%.1f\", $PASSED_TESTS / $TOTAL_TESTS * 100}")

echo "總測試數: $TOTAL_TESTS" | tee -a "$LOG_FILE"
echo -e "${GREEN}通過: $PASSED_TESTS${NC}" | tee -a "$LOG_FILE"
echo -e "${RED}失敗: $FAILED_TESTS${NC}" | tee -a "$LOG_FILE"
echo "通過率: $PASS_RATE%" | tee -a "$LOG_FILE"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✅ 所有測試通過！${NC}" | tee -a "$LOG_FILE"
    exit 0
else
    echo -e "${YELLOW}⚠️  部分測試失敗（$FAILED_TESTS/$TOTAL_TESTS）${NC}" | tee -a "$LOG_FILE"
    exit 1
fi
