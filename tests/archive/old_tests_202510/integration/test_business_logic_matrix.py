"""
業種類型 × 金流模式自動化測試套件

測試四種業務情境：
1. 包租型（full_service + through_company）
2. 純代管型-金流不過公司（property_management + direct_to_landlord）
3. 純代管型-金流過公司（property_management + through_company）
4. 純代管型-混合型（property_management + hybrid）

測試問題涵蓋：
- 租金繳納
- 押金退還
- 收據申請
- 遲繳處理
- 繳費方式
- 租金查詢
"""

import pytest
import requests
import time
from typing import Dict, List

# 測試配置
BASE_URL = "http://localhost:8100"
API_ENDPOINT = f"{BASE_URL}/api/v1/message"

# 業者配置
VENDORS = {
    "full_service": {
        "vendor_id": 1,
        "name": "甲山林（包租型）",
        "business_type": "full_service",
        "cashflow_model": "through_company"
    },
    "pm_direct": {
        "vendor_id": 2,
        "name": "信義（純代管-不過公司）",
        "business_type": "property_management",
        "cashflow_model": "direct_to_landlord"
    },
    "pm_company": {
        "vendor_id": 4,
        "name": "永慶（純代管-過公司）",
        "business_type": "property_management",
        "cashflow_model": "through_company"
    },
    "pm_hybrid": {
        "vendor_id": 5,
        "name": "台灣房屋（純代管-混合型）",
        "business_type": "property_management",
        "cashflow_model": "hybrid"
    }
}

# 測試問題集
TEST_QUESTIONS = {
    "rent_payment": "租金怎麼繳？",
    "deposit_refund": "押金什麼時候退還？",
    "receipt_request": "如何申請收據？",
    "late_payment": "遲繳租金會怎樣？",
    "payment_methods": "繳費方式有哪些？",
    "rent_inquiry": "如何查詢當月租金？"
}


class ToneValidator:
    """語氣驗證器"""

    # 包租型特徵（主動服務）
    FULL_SERVICE_PATTERNS = [
        "我們會", "我們將", "公司會", "公司將",
        "系統會", "系統將", "自動", "主動"
    ]

    # 代管型特徵（協助引導）
    PROPERTY_MANAGEMENT_PATTERNS = [
        "請您", "建議您", "您可以", "建議",
        "可協助", "協助您", "請向", "請聯繫"
    ]

    @staticmethod
    def validate_tone(answer: str, expected_type: str) -> Dict:
        """
        驗證語氣

        Args:
            answer: AI 回答
            expected_type: 預期業種類型（full_service 或 property_management）

        Returns:
            {
                'is_valid': bool,
                'matched_patterns': List[str],
                'score': float,
                'details': str
            }
        """
        if expected_type == "full_service":
            patterns = ToneValidator.FULL_SERVICE_PATTERNS
            pattern_type = "主動服務型"
        else:
            patterns = ToneValidator.PROPERTY_MANAGEMENT_PATTERNS
            pattern_type = "協助引導型"

        matched = [p for p in patterns if p in answer]
        score = len(matched) / len(patterns) if patterns else 0

        return {
            'is_valid': len(matched) > 0,
            'matched_patterns': matched,
            'score': score,
            'pattern_type': pattern_type,
            'details': f"找到 {len(matched)} 個{pattern_type}關鍵詞"
        }


class ContentValidator:
    """內容驗證器"""

    # 金流過公司特徵
    THROUGH_COMPANY_PATTERNS = [
        "公司", "系統", "JGB", "管理系統",
        "公司收款", "公司帳號", "自動生成",
        "郵件發送", "電子發票"
    ]

    # 金流不過公司特徵
    DIRECT_TO_LANDLORD_PATTERNS = [
        "房東", "向房東", "房東索取", "房東確認",
        "保留記錄", "自行保管", "交易記錄"
    ]

    # 混合型特徵
    HYBRID_PATTERNS = [
        "依房源", "部分房源", "另一些房源",
        "查看租約", "具體方式", "而異"
    ]

    @staticmethod
    def validate_content(answer: str, expected_cashflow: str) -> Dict:
        """
        驗證內容

        Args:
            answer: AI 回答
            expected_cashflow: 預期金流模式

        Returns:
            {
                'is_valid': bool,
                'matched_patterns': List[str],
                'avoided_patterns': List[str],
                'score': float,
                'details': str
            }
        """
        if expected_cashflow == "through_company":
            required = ContentValidator.THROUGH_COMPANY_PATTERNS
            avoid = ContentValidator.DIRECT_TO_LANDLORD_PATTERNS
            cashflow_type = "金流過公司"
        elif expected_cashflow == "direct_to_landlord":
            required = ContentValidator.DIRECT_TO_LANDLORD_PATTERNS
            avoid = ContentValidator.THROUGH_COMPANY_PATTERNS
            cashflow_type = "金流不過公司"
        else:  # hybrid
            required = ContentValidator.HYBRID_PATTERNS
            avoid = []
            cashflow_type = "混合型"

        matched_required = [p for p in required if p in answer]
        matched_avoid = [p for p in avoid if p in answer]

        # 計算分數
        required_score = len(matched_required) / len(required) if required else 0
        avoid_penalty = len(matched_avoid) * 0.2
        score = max(0, required_score - avoid_penalty)

        is_valid = len(matched_required) > 0 and len(matched_avoid) == 0

        return {
            'is_valid': is_valid,
            'matched_patterns': matched_required,
            'avoided_patterns': matched_avoid,
            'score': score,
            'cashflow_type': cashflow_type,
            'details': f"找到 {len(matched_required)} 個{cashflow_type}關鍵詞，避免了 {len(matched_avoid)} 個衝突詞"
        }


def call_vendor_api(vendor_id: int, question: str) -> Dict:
    """
    呼叫業者 API

    Args:
        vendor_id: 業者 ID
        question: 問題

    Returns:
        API 回應
    """
    payload = {
        "message": question,
        "vendor_id": vendor_id,
        "mode": "tenant",
        "include_sources": True,
        "disable_answer_synthesis": False
    }

    try:
        response = requests.post(API_ENDPOINT, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        pytest.fail(f"API 請求失敗: {e}")


# ============================================
# 情境測試
# ============================================

class TestScenario1_FullService:
    """情境 1：包租型（full_service + through_company）"""

    vendor_config = VENDORS["full_service"]

    @pytest.mark.parametrize("question_key", TEST_QUESTIONS.keys())
    def test_full_service_questions(self, question_key):
        """測試包租型業者的各種問題"""
        question = TEST_QUESTIONS[question_key]

        # 呼叫 API
        response = call_vendor_api(self.vendor_config["vendor_id"], question)

        # 驗證回應結構
        assert "answer" in response, "回應中缺少 answer 欄位"
        answer = response["answer"]

        # 驗證語氣（包租型 = 主動服務）
        tone_result = ToneValidator.validate_tone(answer, "full_service")
        assert tone_result['is_valid'], \
            f"語氣驗證失敗：{tone_result['details']}\n回答：{answer[:200]}"

        # 驗證內容（金流過公司）
        content_result = ContentValidator.validate_content(answer, "through_company")
        assert content_result['is_valid'], \
            f"內容驗證失敗：{content_result['details']}\n回答：{answer[:200]}"

        # 記錄測試結果
        print(f"\n✅ 測試通過：{question}")
        print(f"   語氣：{tone_result['pattern_type']} (匹配 {len(tone_result['matched_patterns'])} 個關鍵詞)")
        print(f"   內容：{content_result['cashflow_type']} (匹配 {len(content_result['matched_patterns'])} 個關鍵詞)")

        # 延遲避免 rate limit
        time.sleep(1)


class TestScenario2_PropertyManagement_DirectToLandlord:
    """情境 2：純代管型-金流不過公司（property_management + direct_to_landlord）"""

    vendor_config = VENDORS["pm_direct"]

    @pytest.mark.parametrize("question_key", TEST_QUESTIONS.keys())
    def test_pm_direct_questions(self, question_key):
        """測試純代管型-金流不過公司的各種問題"""
        question = TEST_QUESTIONS[question_key]

        # 呼叫 API
        response = call_vendor_api(self.vendor_config["vendor_id"], question)

        # 驗證回應結構
        assert "answer" in response, "回應中缺少 answer 欄位"
        answer = response["answer"]

        # 驗證語氣（代管型 = 協助引導）
        tone_result = ToneValidator.validate_tone(answer, "property_management")
        assert tone_result['is_valid'], \
            f"語氣驗證失敗：{tone_result['details']}\n回答：{answer[:200]}"

        # 驗證內容（金流不過公司）
        content_result = ContentValidator.validate_content(answer, "direct_to_landlord")
        assert content_result['is_valid'], \
            f"內容驗證失敗：{content_result['details']}\n回答：{answer[:200]}"

        # 記錄測試結果
        print(f"\n✅ 測試通過：{question}")
        print(f"   語氣：{tone_result['pattern_type']} (匹配 {len(tone_result['matched_patterns'])} 個關鍵詞)")
        print(f"   內容：{content_result['cashflow_type']} (匹配 {len(content_result['matched_patterns'])} 個關鍵詞)")

        # 延遲避免 rate limit
        time.sleep(1)


class TestScenario3_PropertyManagement_ThroughCompany:
    """情境 3：純代管型-金流過公司（property_management + through_company）"""

    vendor_config = VENDORS["pm_company"]

    @pytest.mark.parametrize("question_key", TEST_QUESTIONS.keys())
    def test_pm_company_questions(self, question_key):
        """測試純代管型-金流過公司的各種問題"""
        question = TEST_QUESTIONS[question_key]

        # 呼叫 API
        response = call_vendor_api(self.vendor_config["vendor_id"], question)

        # 驗證回應結構
        assert "answer" in response, "回應中缺少 answer 欄位"
        answer = response["answer"]

        # 驗證語氣（代管型 = 協助引導）
        tone_result = ToneValidator.validate_tone(answer, "property_management")
        assert tone_result['is_valid'], \
            f"語氣驗證失敗：{tone_result['details']}\n回答：{answer[:200]}"

        # 驗證內容（金流過公司）
        content_result = ContentValidator.validate_content(answer, "through_company")
        assert content_result['is_valid'], \
            f"內容驗證失敗：{content_result['details']}\n回答：{answer[:200]}"

        # 特殊驗證：這是關鍵情境，需要同時具備代管語氣 + 公司金流
        print(f"\n✅ 測試通過（關鍵情境）：{question}")
        print(f"   語氣：{tone_result['pattern_type']} (匹配 {len(tone_result['matched_patterns'])} 個關鍵詞)")
        print(f"   內容：{content_result['cashflow_type']} (匹配 {len(content_result['matched_patterns'])} 個關鍵詞)")
        print(f"   ⭐ 此情境驗證了業種類型和金流模式的獨立運作")

        # 延遲避免 rate limit
        time.sleep(1)


class TestScenario4_PropertyManagement_Hybrid:
    """情境 4：純代管型-混合型（property_management + hybrid）"""

    vendor_config = VENDORS["pm_hybrid"]

    @pytest.mark.parametrize("question_key", TEST_QUESTIONS.keys())
    def test_pm_hybrid_questions(self, question_key):
        """測試純代管型-混合型的各種問題"""
        question = TEST_QUESTIONS[question_key]

        # 呼叫 API
        response = call_vendor_api(self.vendor_config["vendor_id"], question)

        # 驗證回應結構
        assert "answer" in response, "回應中缺少 answer 欄位"
        answer = response["answer"]

        # 驗證語氣（代管型 = 協助引導）
        tone_result = ToneValidator.validate_tone(answer, "property_management")
        assert tone_result['is_valid'], \
            f"語氣驗證失敗：{tone_result['details']}\n回答：{answer[:200]}"

        # 驗證內容（混合型）
        content_result = ContentValidator.validate_content(answer, "hybrid")
        assert content_result['is_valid'], \
            f"內容驗證失敗：{content_result['details']}\n回答：{answer[:200]}"

        # 記錄測試結果
        print(f"\n✅ 測試通過：{question}")
        print(f"   語氣：{tone_result['pattern_type']} (匹配 {len(tone_result['matched_patterns'])} 個關鍵詞)")
        print(f"   內容：{content_result['cashflow_type']} (匹配 {len(content_result['matched_patterns'])} 個關鍵詞)")

        # 延遲避免 rate limit
        time.sleep(1)


# ============================================
# 交叉驗證測試
# ============================================

class TestCrossValidation:
    """交叉驗證：確保不同情境之間的差異正確"""

    def test_tone_difference_between_full_service_and_pm(self):
        """測試包租型和代管型的語氣差異"""
        question = "租金怎麼繳？"

        # 包租型
        response_fs = call_vendor_api(VENDORS["full_service"]["vendor_id"], question)
        answer_fs = response_fs["answer"]

        # 代管型
        response_pm = call_vendor_api(VENDORS["pm_direct"]["vendor_id"], question)
        answer_pm = response_pm["answer"]

        # 包租型應該有主動語氣
        tone_fs = ToneValidator.validate_tone(answer_fs, "full_service")
        assert tone_fs['is_valid'], "包租型語氣驗證失敗"

        # 代管型應該有協助語氣
        tone_pm = ToneValidator.validate_tone(answer_pm, "property_management")
        assert tone_pm['is_valid'], "代管型語氣驗證失敗"

        print(f"\n✅ 語氣差異驗證通過")
        print(f"   包租型：{tone_fs['matched_patterns'][:3]}")
        print(f"   代管型：{tone_pm['matched_patterns'][:3]}")

        time.sleep(1)

    def test_content_difference_between_cashflow_models(self):
        """測試不同金流模式的內容差異"""
        question = "租金怎麼繳？"

        # 金流過公司
        response_company = call_vendor_api(VENDORS["pm_company"]["vendor_id"], question)
        answer_company = response_company["answer"]

        # 金流不過公司
        response_direct = call_vendor_api(VENDORS["pm_direct"]["vendor_id"], question)
        answer_direct = response_direct["answer"]

        # 金流過公司應該提及公司
        content_company = ContentValidator.validate_content(answer_company, "through_company")
        assert content_company['is_valid'], "金流過公司內容驗證失敗"

        # 金流不過公司應該提及房東
        content_direct = ContentValidator.validate_content(answer_direct, "direct_to_landlord")
        assert content_direct['is_valid'], "金流不過公司內容驗證失敗"

        print(f"\n✅ 金流模式內容差異驗證通過")
        print(f"   過公司：{content_company['matched_patterns'][:3]}")
        print(f"   不過公司：{content_direct['matched_patterns'][:3]}")

        time.sleep(1)

    def test_hybrid_contains_both_scenarios(self):
        """測試混合型是否同時提及兩種金流方式"""
        question = "租金怎麼繳？"

        response = call_vendor_api(VENDORS["pm_hybrid"]["vendor_id"], question)
        answer = response["answer"]

        # 應該同時提及公司和房東
        has_company = any(p in answer for p in ["公司", "系統"])
        has_landlord = any(p in answer for p in ["房東", "向房東"])
        has_hybrid_keywords = any(p in answer for p in ["依房源", "部分", "另一些"])

        assert has_company, f"混合型回答未提及公司\n回答：{answer}"
        assert has_landlord, f"混合型回答未提及房東\n回答：{answer}"
        assert has_hybrid_keywords, f"混合型回答未提及依房源而異\n回答：{answer}"

        print(f"\n✅ 混合型內容驗證通過")
        print(f"   ✓ 提及公司")
        print(f"   ✓ 提及房東")
        print(f"   ✓ 提及依房源而異")


# ============================================
# 測試執行配置
# ============================================

if __name__ == "__main__":
    import sys

    # 執行測試
    pytest_args = [
        __file__,
        "-v",  # 詳細輸出
        "-s",  # 顯示 print 輸出
        "--tb=short",  # 簡短的錯誤追蹤
        "-x",  # 第一個失敗就停止（可選）
    ]

    sys.exit(pytest.main(pytest_args))
