#!/bin/bash

# 業種類型 × 金流模式自動化測試執行腳本
# 用途：執行完整的業務邏輯矩陣測試

set -e  # 遇到錯誤立即退出

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=================================================="
echo "業種類型 × 金流模式自動化測試"
echo "=================================================="
echo ""

# 檢查是否在專案根目錄
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ 錯誤：請在專案根目錄執行此腳本${NC}"
    exit 1
fi

# 檢查 RAG API 是否運行
echo -e "${YELLOW}🔍 檢查 RAG API 狀態...${NC}"
if ! curl -s http://localhost:8100/health > /dev/null 2>&1; then
    echo -e "${RED}❌ 錯誤：RAG API 未運行（http://localhost:8100）${NC}"
    echo "請先啟動服務："
    echo "  docker-compose up -d"
    exit 1
fi
echo -e "${GREEN}✅ RAG API 運行中${NC}"
echo ""

# 檢查測試所需的 Python 套件
echo -e "${YELLOW}🔍 檢查測試環境...${NC}"
if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  pytest 未安裝，正在安裝...${NC}"
    pip3 install pytest requests
fi
echo -e "${GREEN}✅ 測試環境就緒${NC}"
echo ""

# 測試模式選擇
echo "請選擇測試模式："
echo "  1) 快速測試（每種情境測試 1 個問題）"
echo "  2) 完整測試（每種情境測試 6 個問題）"
echo "  3) 僅測試單一情境"
echo "  4) 交叉驗證測試"
echo ""
read -p "請輸入選擇 [1-4]（預設: 2）: " choice
choice=${choice:-2}

# 設置測試參數
TEST_FILE="tests/integration/test_business_logic_matrix.py"
PYTEST_ARGS="-v -s --tb=short"

case $choice in
    1)
        echo -e "${YELLOW}📝 執行快速測試...${NC}"
        # 使用 pytest 的 -k 參數只執行租金繳納相關的測試
        python3 -m pytest $TEST_FILE $PYTEST_ARGS -k "rent_payment"
        ;;
    2)
        echo -e "${YELLOW}📝 執行完整測試（4 種情境 × 6 個問題 = 24 個測試）...${NC}"
        python3 -m pytest $TEST_FILE $PYTEST_ARGS
        ;;
    3)
        echo ""
        echo "請選擇情境："
        echo "  1) 包租型"
        echo "  2) 純代管型-金流不過公司"
        echo "  3) 純代管型-金流過公司"
        echo "  4) 純代管型-混合型"
        echo ""
        read -p "請輸入選擇 [1-4]: " scenario

        case $scenario in
            1) CLASS="TestScenario1_FullService" ;;
            2) CLASS="TestScenario2_PropertyManagement_DirectToLandlord" ;;
            3) CLASS="TestScenario3_PropertyManagement_ThroughCompany" ;;
            4) CLASS="TestScenario4_PropertyManagement_Hybrid" ;;
            *) echo -e "${RED}無效的選擇${NC}"; exit 1 ;;
        esac

        echo -e "${YELLOW}📝 執行情境測試：$CLASS...${NC}"
        python3 -m pytest $TEST_FILE::$CLASS $PYTEST_ARGS
        ;;
    4)
        echo -e "${YELLOW}📝 執行交叉驗證測試...${NC}"
        python3 -m pytest $TEST_FILE::TestCrossValidation $PYTEST_ARGS
        ;;
    *)
        echo -e "${RED}無效的選擇${NC}"
        exit 1
        ;;
esac

# 測試結果總結
if [ $? -eq 0 ]; then
    echo ""
    echo "=================================================="
    echo -e "${GREEN}✅ 測試通過！${NC}"
    echo "=================================================="
    echo ""
    echo "測試涵蓋："
    echo "  ✓ 4 種業務情境"
    echo "  ✓ 語氣驗證（包租型 vs 代管型）"
    echo "  ✓ 內容驗證（金流模式差異）"
    echo "  ✓ 交叉驗證（確保差異正確）"
    echo ""
    echo "下一步建議："
    echo "  1. 定期執行回歸測試（每次修改代碼後）"
    echo "  2. 整合到 CI/CD 流程"
    echo "  3. 添加更多測試問題"
    echo ""
else
    echo ""
    echo "=================================================="
    echo -e "${RED}❌ 測試失敗${NC}"
    echo "=================================================="
    echo ""
    echo "請檢查："
    echo "  1. RAG API 是否正常運行"
    echo "  2. 資料庫連接是否正常"
    echo "  3. SOP 資料是否已匯入"
    echo "  4. 業者配置是否正確"
    echo ""
    echo "查看詳細錯誤訊息請往上捲動"
    exit 1
fi
