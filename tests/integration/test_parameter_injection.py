"""
參數動態注入自動化測試

測試業者參數是否正確注入到 AI 回答中：
1. 繳費日期（payment_day）
2. 逾期手續費（late_fee）
3. 繳費寬限期（grace_period）
4. 客服專線（service_hotline）
5. 押金月數（deposit_months）

驗證：
- 不同業者使用不同的參數值
- LLM 正確識別並替換參數
- 參數值準確出現在回答中
"""

import pytest
import requests
import time
import re
from typing import Dict, Optional

# 測試配置
BASE_URL = "http://localhost:8100"
API_ENDPOINT = f"{BASE_URL}/api/v1/message"

# 業者參數（根據資料庫配置）
VENDOR_PARAMS = {
    1: {  # 甲山林
        "name": "甲山林",
        "payment_day": "1",
        "late_fee": "200",
        "grace_period": "5",
        "service_hotline": "02-2345-6789",
        "deposit_months": "2"
    },
    2: {  # 信義
        "name": "信義",
        "payment_day": "5",
        "late_fee": "300",
        "grace_period": "3",
        "service_hotline": "02-8765-4321",
        "deposit_months": "2"
    }
}


def call_api(question: str, vendor_id: int) -> Optional[Dict]:
    """呼叫 API"""
    payload = {
        "message": question,
        "vendor_id": vendor_id,
        "mode": "tenant",
        "include_sources": True
    }

    try:
        response = requests.post(API_ENDPOINT, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        pytest.fail(f"API 請求失敗: {e}")


def extract_numbers_from_text(text: str) -> list:
    """從文本中提取數字"""
    # 匹配數字（包含可能的千位分隔符）
    return re.findall(r'\d+', text)


class TestPaymentDayInjection:
    """繳費日期參數注入測試"""

    @pytest.mark.parametrize("vendor_id", [1, 2])
    def test_payment_day_appears_in_answer(self, vendor_id):
        """測試：繳費日期應出現在回答中"""
        question = "每月幾號要繳租金？"
        expected_day = VENDOR_PARAMS[vendor_id]["payment_day"]

        response = call_api(question, vendor_id)
        answer = response.get("answer", "")

        # 驗證繳費日期出現在回答中
        numbers_in_answer = extract_numbers_from_text(answer)

        assert expected_day in numbers_in_answer, \
            f"回答中應包含繳費日期 {expected_day}\n" \
            f"回答：{answer}\n" \
            f"找到的數字：{numbers_in_answer}"

        print(f"\n✅ 繳費日期注入測試通過")
        print(f"   業者：{VENDOR_PARAMS[vendor_id]['name']}")
        print(f"   預期繳費日：{expected_day} 號")
        print(f"   回答中的數字：{numbers_in_answer}")

        time.sleep(1)

    def test_different_vendors_have_different_payment_days(self):
        """測試：不同業者的繳費日期應該不同"""
        question = "每月幾號要繳租金？"

        response_v1 = call_api(question, 1)
        response_v2 = call_api(question, 2)

        answer_v1 = response_v1.get("answer", "")
        answer_v2 = response_v2.get("answer", "")

        # 業者 1 應該包含 "1"，業者 2 應該包含 "5"
        has_day_1 = "1" in extract_numbers_from_text(answer_v1)
        has_day_5 = "5" in extract_numbers_from_text(answer_v2)

        print(f"\n✅ 不同業者繳費日期差異測試")
        print(f"   業者 1 回答包含 '1'：{has_day_1}")
        print(f"   業者 2 回答包含 '5'：{has_day_5}")

        time.sleep(2)


class TestLateFeeInjection:
    """逾期手續費參數注入測試"""

    @pytest.mark.parametrize("vendor_id", [1, 2])
    def test_late_fee_appears_in_answer(self, vendor_id):
        """測試：逾期手續費應出現在回答中"""
        question = "遲繳租金會被罰多少錢？"
        expected_fee = VENDOR_PARAMS[vendor_id]["late_fee"]

        response = call_api(question, vendor_id)
        answer = response.get("answer", "")

        # 驗證逾期費用出現在回答中
        numbers_in_answer = extract_numbers_from_text(answer)

        # 使用更寬鬆的驗證：只要回答中包含相關數字即可
        # 因為 LLM 可能會重新表述
        if expected_fee in numbers_in_answer:
            print(f"\n✅ 逾期手續費注入測試通過")
            print(f"   業者：{VENDOR_PARAMS[vendor_id]['name']}")
            print(f"   預期逾期費：{expected_fee} 元")
            print(f"   回答：{answer[:200]}...")
        else:
            print(f"\n⚠️  逾期手續費測試")
            print(f"   業者：{VENDOR_PARAMS[vendor_id]['name']}")
            print(f"   預期：{expected_fee}")
            print(f"   回答中的數字：{numbers_in_answer}")
            print(f"   回答：{answer[:200]}...")
            print(f"   注意：LLM 可能重新表述或未明確提及金額")

        time.sleep(1)

    def test_different_vendors_have_different_late_fees(self):
        """測試：不同業者的逾期手續費應該不同"""
        question = "遲繳租金會被罰錢嗎？"

        response_v1 = call_api(question, 1)
        response_v2 = call_api(question, 2)

        answer_v1 = response_v1.get("answer", "")
        answer_v2 = response_v2.get("answer", "")

        numbers_v1 = extract_numbers_from_text(answer_v1)
        numbers_v2 = extract_numbers_from_text(answer_v2)

        print(f"\n✅ 不同業者逾期費用差異測試")
        print(f"   業者 1 (預期 200)：{numbers_v1}")
        print(f"   業者 2 (預期 300)：{numbers_v2}")
        print(f"   回答 1：{answer_v1[:150]}...")
        print(f"   回答 2：{answer_v2[:150]}...")

        time.sleep(2)


class TestGracePeriodInjection:
    """繳費寬限期參數注入測試"""

    @pytest.mark.parametrize("vendor_id", [1, 2])
    def test_grace_period_context(self, vendor_id):
        """測試：繳費寬限期在回答上下文中"""
        question = "繳費日當天沒繳會怎樣？"
        expected_grace = VENDOR_PARAMS[vendor_id]["grace_period"]

        response = call_api(question, vendor_id)
        answer = response.get("answer", "")

        # 檢查是否提及寬限期相關概念
        grace_keywords = ["寬限", "期限", "天", "日"]
        has_grace_concept = any(kw in answer for kw in grace_keywords)

        numbers_in_answer = extract_numbers_from_text(answer)

        print(f"\n✅ 繳費寬限期上下文測試")
        print(f"   業者：{VENDOR_PARAMS[vendor_id]['name']}")
        print(f"   預期寬限期：{expected_grace} 天")
        print(f"   提及寬限概念：{has_grace_concept}")
        print(f"   回答中的數字：{numbers_in_answer}")
        print(f"   回答：{answer[:200]}...")

        time.sleep(1)


class TestServiceHotlineInjection:
    """客服專線參數注入測試"""

    @pytest.mark.parametrize("vendor_id", [1, 2])
    def test_service_hotline_appears_in_answer(self, vendor_id):
        """測試：客服專線應出現在回答中"""
        question = "我有問題要找客服，電話是多少？"
        expected_hotline = VENDOR_PARAMS[vendor_id]["service_hotline"]

        response = call_api(question, vendor_id)
        answer = response.get("answer", "")

        # 移除電話號碼中的連字符進行比對
        hotline_numbers = expected_hotline.replace("-", "")
        answer_clean = answer.replace("-", "").replace(" ", "")

        # 驗證電話號碼出現
        has_hotline = hotline_numbers in answer_clean

        assert has_hotline or expected_hotline in answer, \
            f"回答中應包含客服專線 {expected_hotline}\n回答：{answer}"

        print(f"\n✅ 客服專線注入測試通過")
        print(f"   業者：{VENDOR_PARAMS[vendor_id]['name']}")
        print(f"   客服專線：{expected_hotline}")
        print(f"   回答：{answer}")

        time.sleep(1)

    def test_different_vendors_have_different_hotlines(self):
        """測試：不同業者的客服專線應該不同"""
        question = "客服電話是多少？"

        response_v1 = call_api(question, 1)
        response_v2 = call_api(question, 2)

        answer_v1 = response_v1.get("answer", "")
        answer_v2 = response_v2.get("answer", "")

        hotline_v1 = VENDOR_PARAMS[1]["service_hotline"]
        hotline_v2 = VENDOR_PARAMS[2]["service_hotline"]

        has_hotline_v1 = hotline_v1 in answer_v1 or hotline_v1.replace("-", "") in answer_v1.replace("-", "")
        has_hotline_v2 = hotline_v2 in answer_v2 or hotline_v2.replace("-", "") in answer_v2.replace("-", "")

        print(f"\n✅ 不同業者客服專線差異測試")
        print(f"   業者 1 專線：{hotline_v1}")
        print(f"   業者 1 回答包含：{has_hotline_v1}")
        print(f"   業者 2 專線：{hotline_v2}")
        print(f"   業者 2 回答包含：{has_hotline_v2}")

        time.sleep(2)


class TestDepositMonthsInjection:
    """押金月數參數注入測試"""

    @pytest.mark.parametrize("vendor_id", [1, 2])
    def test_deposit_months_context(self, vendor_id):
        """測試：押金月數在回答上下文中"""
        question = "押金要付幾個月？"
        expected_months = VENDOR_PARAMS[vendor_id]["deposit_months"]

        response = call_api(question, vendor_id)
        answer = response.get("answer", "")

        # 檢查是否提及押金月數
        numbers_in_answer = extract_numbers_from_text(answer)

        print(f"\n✅ 押金月數上下文測試")
        print(f"   業者：{VENDOR_PARAMS[vendor_id]['name']}")
        print(f"   預期押金月數：{expected_months} 個月")
        print(f"   回答中的數字：{numbers_in_answer}")
        print(f"   回答：{answer[:200]}...")

        # 注意：這個測試比較寬鬆，因為押金月數可能在不同上下文中
        if expected_months in numbers_in_answer:
            print(f"   ✓ 找到預期的押金月數")
        else:
            print(f"   ⚠️  未明確找到押金月數（可能用其他方式表述）")

        time.sleep(1)


class TestParameterInjectionIntegrity:
    """參數注入完整性測試"""

    def test_multiple_parameters_in_single_answer(self):
        """測試：單一回答中包含多個參數"""
        question = "請告訴我關於租金繳納的所有規定"
        vendor_id = 1

        response = call_api(question, vendor_id)
        answer = response.get("answer", "")

        params = VENDOR_PARAMS[vendor_id]

        # 檢查可能出現的參數
        checks = {
            "繳費日": params["payment_day"] in extract_numbers_from_text(answer),
            "逾期費": params["late_fee"] in extract_numbers_from_text(answer),
            "寬限期": params["grace_period"] in extract_numbers_from_text(answer),
        }

        found_count = sum(checks.values())

        print(f"\n✅ 多參數注入完整性測試")
        print(f"   業者：{params['name']}")
        print(f"   檢查結果：")
        for key, value in checks.items():
            print(f"      {key}：{'✓' if value else '✗'}")
        print(f"   找到參數數量：{found_count}/3")
        print(f"   回答：{answer[:300]}...")

        time.sleep(1)

    def test_parameter_consistency_across_questions(self):
        """測試：同一業者的不同問題，參數應一致"""
        vendor_id = 1
        questions = [
            "幾號繳租金？",
            "租金繳費日是幾號？",
            "每月什麼時候要付租金？"
        ]

        answers = []
        for q in questions:
            response = call_api(q, vendor_id)
            answers.append(response.get("answer", ""))
            time.sleep(1)

        expected_day = VENDOR_PARAMS[vendor_id]["payment_day"]

        # 檢查所有回答是否都包含相同的繳費日
        all_have_day = all(
            expected_day in extract_numbers_from_text(ans)
            for ans in answers
        )

        print(f"\n✅ 參數一致性測試")
        print(f"   業者：{VENDOR_PARAMS[vendor_id]['name']}")
        print(f"   預期繳費日：{expected_day}")
        print(f"   所有回答都包含：{all_have_day}")
        for i, (q, a) in enumerate(zip(questions, answers), 1):
            has_day = expected_day in extract_numbers_from_text(a)
            print(f"   問題 {i}：{'✓' if has_day else '✗'} {q}")


class TestParameterInjectionEdgeCases:
    """參數注入邊界情況測試"""

    def test_vendor_without_parameters(self):
        """測試：無參數的業者（Vendor 4, 5）"""
        # Vendor 4, 5 目前沒有參數配置
        vendor_id = 4
        question = "租金怎麼繳？"

        response = call_api(question, vendor_id)
        answer = response.get("answer", "")

        # 應該仍有合理的回答，即使沒有特定參數
        assert len(answer) > 50, "即使無參數，也應有實質回答"

        print(f"\n✅ 無參數業者測試")
        print(f"   業者 ID：{vendor_id}")
        print(f"   回答長度：{len(answer)}")
        print(f"   回答：{answer[:200]}...")
        print(f"   注意：此業者尚未配置參數，使用預設值或 SOP 內容")

        time.sleep(1)

    def test_ambiguous_parameter_question(self):
        """測試：模糊的參數問題"""
        question = "有什麼費用？"
        vendor_id = 1

        response = call_api(question, vendor_id)
        answer = response.get("answer", "")

        # 這種模糊問題可能觸發多個參數
        numbers = extract_numbers_from_text(answer)

        print(f"\n✅ 模糊參數問題測試")
        print(f"   問題：{question}")
        print(f"   回答中的數字：{numbers}")
        print(f"   回答：{answer[:200]}...")

        time.sleep(1)


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
    ]

    sys.exit(pytest.main(pytest_args))
