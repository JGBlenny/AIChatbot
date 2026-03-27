"""
測試 ActionTypeClassifier - 回應類型判斷功能

測試 AI 輔助判斷、啟發式分類、配置生成等功能
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from action_type_classifier import ActionTypeClassifier
from models import ActionType, ActionTypeJudgment


async def test_manual_only_mode():
    """測試手動審核模式"""
    print("=" * 60)
    print("測試手動審核模式（manual_only）")
    print("=" * 60)

    classifier = ActionTypeClassifier()

    judgment = await classifier.classify_action_type(
        question="租金每月幾號要繳？",
        answer="每月 5 號前需繳納租金",
        vendor_id=1,
        mode="manual_only"
    )

    print(f"\n判斷結果:")
    print(f"  回應類型: {judgment.action_type.value}")
    print(f"  信心度: {judgment.confidence}")
    print(f"  理由: {judgment.reasoning}")
    print(f"  需人工審核: {judgment.needs_manual_review}")

    assert judgment.action_type == ActionType.DIRECT_ANSWER
    assert judgment.confidence == 0.0
    assert judgment.needs_manual_review == True

    print("\n✅ 手動審核模式測試通過！")


async def test_heuristic_direct_answer():
    """測試啟發式分類 - direct_answer"""
    print("\n" + "=" * 60)
    print("測試啟發式分類 - direct_answer")
    print("=" * 60)

    classifier = ActionTypeClassifier()

    # 固定資訊問題
    judgment = await classifier.classify_action_type(
        question="租金每月幾號要繳？",
        answer="每月 5 號前需繳納租金，可透過轉帳或現金支付",
        vendor_id=1,
        mode="ai_assisted"
    )

    print(f"\n判斷結果:")
    print(f"  回應類型: {judgment.action_type.value}")
    print(f"  信心度: {judgment.confidence}")
    print(f"  理由: {judgment.reasoning}")

    assert judgment.action_type == ActionType.DIRECT_ANSWER
    assert judgment.confidence == 0.8

    print("✅ direct_answer 測試通過！")


async def test_heuristic_form_fill():
    """測試啟發式分類 - form_fill"""
    print("\n" + "=" * 60)
    print("測試啟發式分類 - form_fill")
    print("=" * 60)

    classifier = ActionTypeClassifier()

    # 需要填寫表單
    judgment = await classifier.classify_action_type(
        question="如何申請維修？",
        answer="請填寫維修申請表單，我們會盡快安排人員處理",
        vendor_id=1,
        mode="ai_assisted"
    )

    print(f"\n判斷結果:")
    print(f"  回應類型: {judgment.action_type.value}")
    print(f"  信心度: {judgment.confidence}")
    print(f"  理由: {judgment.reasoning}")
    print(f"  建議表單: {judgment.suggested_form_id}")

    assert judgment.action_type == ActionType.FORM_FILL
    assert judgment.confidence == 0.7
    assert judgment.suggested_form_id == "repair_form"  # 應該匹配到維修表單

    print("✅ form_fill 測試通過！")


async def test_heuristic_api_call():
    """測試啟發式分類 - api_call"""
    print("\n" + "=" * 60)
    print("測試啟發式分類 - api_call")
    print("=" * 60)

    classifier = ActionTypeClassifier()

    # 測試 1: 電費查詢
    judgment1 = await classifier.classify_action_type(
        question="我本月電費多少？",
        answer="請提供您的房號，我們會為您查詢本月電費",
        vendor_id=1,
        mode="ai_assisted"
    )

    print(f"\n[測試 1] 電費查詢:")
    print(f"  回應類型: {judgment1.action_type.value}")
    print(f"  信心度: {judgment1.confidence}")
    print(f"  建議 API: {judgment1.suggested_api_id}")
    print(f"  API Endpoint: {judgment1.required_api_endpoint}")

    assert judgment1.action_type == ActionType.API_CALL
    assert judgment1.suggested_api_id == "electricity_bill"
    assert judgment1.required_api_endpoint == "/api/v1/electricity/bill"

    # 測試 2: 水費查詢
    judgment2 = await classifier.classify_action_type(
        question="查詢水費",
        answer="請提供您的房號，我們會為您查詢水費資訊",
        vendor_id=1,
        mode="ai_assisted"
    )

    print(f"\n[測試 2] 水費查詢:")
    print(f"  回應類型: {judgment2.action_type.value}")
    print(f"  建議 API: {judgment2.suggested_api_id}")

    assert judgment2.action_type == ActionType.API_CALL
    assert judgment2.suggested_api_id == "water_bill"

    print("\n✅ api_call 測試通過！")


async def test_heuristic_form_then_api():
    """測試啟發式分類 - form_then_api"""
    print("\n" + "=" * 60)
    print("測試啟發式分類 - form_then_api")
    print("=" * 60)

    classifier = ActionTypeClassifier()

    # 需要先填寫表單再繳費
    judgment = await classifier.classify_action_type(
        question="如何繳納管理費？",
        answer="請先填寫繳費資訊，系統會為您產生繳費連結",
        vendor_id=1,
        mode="ai_assisted"
    )

    print(f"\n判斷結果:")
    print(f"  回應類型: {judgment.action_type.value}")
    print(f"  信心度: {judgment.confidence}")
    print(f"  理由: {judgment.reasoning}")

    assert judgment.action_type == ActionType.FORM_THEN_API
    assert judgment.confidence == 0.6

    print("✅ form_then_api 測試通過！")


async def test_ai_assisted_mode():
    """測試 AI 輔助模式（所有判斷都需人工確認）"""
    print("\n" + "=" * 60)
    print("測試 AI 輔助模式（ai_assisted）")
    print("=" * 60)

    classifier = ActionTypeClassifier()

    # 即使信心度高，也應標記為需審核
    judgment = await classifier.classify_action_type(
        question="可以養寵物嗎？",
        answer="依據租約規定，本社區不允許飼養寵物",
        vendor_id=1,
        mode="ai_assisted"
    )

    print(f"\n判斷結果:")
    print(f"  回應類型: {judgment.action_type.value}")
    print(f"  信心度: {judgment.confidence}")
    print(f"  需人工審核: {judgment.needs_manual_review}")

    assert judgment.needs_manual_review == True, \
        "ai_assisted 模式應該標記所有判斷為需審核"

    print("✅ ai_assisted 模式測試通過！")


async def test_auto_mode():
    """測試自動模式（高信心度時自動應用）"""
    print("\n" + "=" * 60)
    print("測試自動模式（auto）")
    print("=" * 60)

    classifier = ActionTypeClassifier()

    # 信心度 >= 0.8 → 不需審核
    judgment1 = await classifier.classify_action_type(
        question="租約期限是多久？",
        answer="租約期限為一年，自簽約日起算",
        vendor_id=1,
        mode="auto"
    )

    print(f"\n[測試 1] 高信心度 (0.8):")
    print(f"  回應類型: {judgment1.action_type.value}")
    print(f"  信心度: {judgment1.confidence}")
    print(f"  需人工審核: {judgment1.needs_manual_review}")

    assert judgment1.confidence == 0.8
    assert judgment1.needs_manual_review == False

    # 信心度 < 0.8 → 需審核
    judgment2 = await classifier.classify_action_type(
        question="如何申請停車位？",
        answer="請填寫停車位申請表單",
        vendor_id=1,
        mode="auto"
    )

    print(f"\n[測試 2] 中信心度 (0.7):")
    print(f"  回應類型: {judgment2.action_type.value}")
    print(f"  信心度: {judgment2.confidence}")
    print(f"  需人工審核: {judgment2.needs_manual_review}")

    assert judgment2.confidence == 0.7
    assert judgment2.needs_manual_review == True

    print("\n✅ auto 模式測試通過！")


async def test_load_forms_and_apis():
    """測試載入表單與 API"""
    print("\n" + "=" * 60)
    print("測試載入表單與 API")
    print("=" * 60)

    classifier = ActionTypeClassifier()

    # 在無資料庫環境下，應使用預設清單
    await classifier._load_available_forms_and_apis(vendor_id=1)

    print(f"\n可用表單數量: {len(classifier.available_forms)}")
    for form in classifier.available_forms:
        print(f"  - {form['form_id']}: {form['name']}")

    print(f"\n可用 API 數量: {len(classifier.available_apis)}")
    for api in classifier.available_apis:
        print(f"  - {api['api_id']}: {api['name']} ({api['endpoint']})")

    assert len(classifier.available_forms) > 0, "應該有可用表單"
    assert len(classifier.available_apis) > 0, "應該有可用 API"

    # 驗證特定表單存在
    form_ids = [f['form_id'] for f in classifier.available_forms]
    assert 'repair_form' in form_ids, "應該有維修表單"
    assert 'parking_form' in form_ids, "應該有停車位表單"

    # 驗證特定 API 存在
    api_ids = [a['api_id'] for a in classifier.available_apis]
    assert 'electricity_bill' in api_ids, "應該有電費查詢 API"
    assert 'water_bill' in api_ids, "應該有水費查詢 API"

    print("\n✅ 表單與 API 載入測試通過！")


async def test_judgment_model():
    """測試 ActionTypeJudgment 模型"""
    print("\n" + "=" * 60)
    print("測試 ActionTypeJudgment 模型")
    print("=" * 60)

    # 測試模型建立
    judgment = ActionTypeJudgment(
        action_type=ActionType.FORM_FILL,
        confidence=0.85,
        reasoning="需要填寫申請表單",
        suggested_form_id="repair_form",
        required_form_fields=["room_number", "description", "contact"],
        needs_manual_review=False
    )

    print(f"\n判斷結果:")
    print(f"  回應類型: {judgment.action_type.value}")
    print(f"  信心度: {judgment.confidence}")
    print(f"  理由: {judgment.reasoning}")
    print(f"  建議表單: {judgment.suggested_form_id}")
    print(f"  必填欄位: {judgment.required_form_fields}")
    print(f"  需人工審核: {judgment.needs_manual_review}")

    # 驗證欄位
    assert judgment.action_type == ActionType.FORM_FILL
    assert 0.0 <= judgment.confidence <= 1.0
    assert len(judgment.reasoning) > 0
    assert judgment.suggested_form_id == "repair_form"
    assert len(judgment.required_form_fields) == 3

    # 測試 API 相關判斷
    api_judgment = ActionTypeJudgment(
        action_type=ActionType.API_CALL,
        confidence=0.9,
        reasoning="需要查詢即時資料",
        suggested_api_id="electricity_bill",
        required_api_endpoint="/api/v1/electricity/bill",
        needs_manual_review=False
    )

    print(f"\nAPI 判斷結果:")
    print(f"  回應類型: {api_judgment.action_type.value}")
    print(f"  建議 API: {api_judgment.suggested_api_id}")
    print(f"  API Endpoint: {api_judgment.required_api_endpoint}")

    assert api_judgment.suggested_api_id == "electricity_bill"
    assert api_judgment.required_api_endpoint == "/api/v1/electricity/bill"

    print("\n✅ 模型驗證測試通過！")


async def main():
    """執行所有測試"""
    try:
        await test_manual_only_mode()
        await test_heuristic_direct_answer()
        await test_heuristic_form_fill()
        await test_heuristic_api_call()
        await test_heuristic_form_then_api()
        await test_ai_assisted_mode()
        await test_auto_mode()
        await test_load_forms_and_apis()
        await test_judgment_model()

        print("\n" + "=" * 60)
        print("✅ 所有測試通過！")
        print("=" * 60)
        print("\n測試總結:")
        print("- ✅ 手動審核模式")
        print("- ✅ 啟發式分類（4 種回應類型）")
        print("- ✅ AI 輔助模式")
        print("- ✅ 自動模式")
        print("- ✅ 表單與 API 載入")
        print("- ✅ 模型驗證")

    except Exception as e:
        print(f"\n❌ 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
