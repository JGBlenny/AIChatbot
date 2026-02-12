#!/bin/bash

# 進階測試執行腳本
# 包含：回退機制測試、參數動態注入測試

set -e  # 遇到錯誤立即退出

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=================================================="
echo "進階功能自動化測試"
echo "=================================================="
echo ""

# 檢查是否在專案根目錄
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ 錯誤：請在專案根目錄執行此腳本${NC}"
    exit 1
fi

# 檢查 RAG API 是否運行
echo -e "${YELLOW}🔍 檢查 RAG API 狀態...${NC}"
if ! curl -s http://localhost:8100/api/v1/message > /dev/null 2>&1; then
    echo -e "${RED}❌ 錯誤：RAG API 未運行（http://localhost:8100）${NC}"
    echo "請先啟動服務："
    echo "  docker-compose up -d"
    exit 1
fi
echo -e "${GREEN}✅ RAG API 運行中${NC}"
echo ""

# 檢查測試環境
echo -e "${YELLOW}🔍 檢查測試環境...${NC}"
if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  pytest 未安裝，正在安裝...${NC}"
    pip3 install pytest requests
fi
echo -e "${GREEN}✅ 測試環境就緒${NC}"
echo ""

# 測試選單
echo "請選擇測試類型："
echo "  1) 回退機制測試"
echo "  2) 參數動態注入測試"
echo "  3) 全部測試"
echo "  4) 快速測試（每種測試 1 個案例）"
echo ""
read -p "請輸入選擇 [1-4]（預設: 3）: " choice
choice=${choice:-3}

PYTEST_ARGS="-v -s --tb=short"

case $choice in
    1)
        echo -e "${BLUE}📝 執行回退機制測試...${NC}"
        echo ""
        python3 -m pytest tests/integration/test_fallback_mechanism.py $PYTEST_ARGS
        ;;
    2)
        echo -e "${BLUE}📝 執行參數動態注入測試...${NC}"
        echo ""
        python3 -m pytest tests/integration/test_parameter_injection.py $PYTEST_ARGS
        ;;
    3)
        echo -e "${BLUE}📝 執行全部進階測試...${NC}"
        echo ""
        python3 -m pytest tests/integration/test_fallback_mechanism.py tests/integration/test_parameter_injection.py $PYTEST_ARGS
        ;;
    4)
        echo -e "${BLUE}📝 執行快速測試...${NC}"
        echo ""
        # 回退機制：只測試第一層
        echo -e "${YELLOW}▶ 回退機制快速測試${NC}"
        python3 -m pytest tests/integration/test_fallback_mechanism.py::TestLayer1_SOPPriority::test_has_sop_uses_sop $PYTEST_ARGS

        # 參數注入：只測試一個參數
        echo ""
        echo -e "${YELLOW}▶ 參數注入快速測試${NC}"
        python3 -m pytest tests/integration/test_parameter_injection.py::TestPaymentDayInjection::test_payment_day_appears_in_answer $PYTEST_ARGS -k "vendor_id1"
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

    case $choice in
        1)
            echo "回退機制測試涵蓋："
            echo "  ✓ SOP 優先級"
            echo "  ✓ 知識庫 Fallback"
            echo "  ✓ RAG 向量搜尋 Fallback"
            echo "  ✓ 兜底回應"
            echo "  ✓ 來源優先級"
            ;;
        2)
            echo "參數注入測試涵蓋："
            echo "  ✓ 繳費日期注入"
            echo "  ✓ 逾期手續費注入"
            echo "  ✓ 繳費寬限期注入"
            echo "  ✓ 客服專線注入"
            echo "  ✓ 押金月數注入"
            echo "  ✓ 參數一致性"
            ;;
        3)
            echo "全部進階測試涵蓋："
            echo "  ✓ 4 層回退機制"
            echo "  ✓ 5 種參數注入"
            echo "  ✓ 邊界情況處理"
            ;;
    esac

    echo ""
    echo "下一步建議："
    echo "  1. 定期執行回歸測試"
    echo "  2. 新增業者參數後執行參數注入測試"
    echo "  3. 整合到 CI/CD 流程"
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
    echo "  4. 業者參數是否已配置"
    echo ""
    exit 1
fi
