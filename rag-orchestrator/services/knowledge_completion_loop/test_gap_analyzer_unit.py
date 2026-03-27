"""
測試 GapAnalyzer - 單元測試（不需要資料庫）

測試分類、優先級判斷、去重等核心邏輯
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from gap_analyzer import GapAnalyzer
from models import FailureReason, GapPriority, KnowledgeGap


def test_classify_and_prioritize():
    """測試失敗原因分類與優先級判斷"""
    print("=" * 60)
    print("測試失敗原因分類與優先級判斷")
    print("=" * 60)

    analyzer = GapAnalyzer(db_pool=None)  # 單元測試不需要 db_pool

    # Test Case 1: NO_MATCH (similarity < 0.6) → P0
    print("\n[Test 1] similarity < 0.6 → NO_MATCH & P0")
    scenario1 = {
        'scenario_id': 1,
        'question': '可以養大型犬嗎？',
        'similarity_score': 0.45,
        'confidence_score': 0.3,
        'semantic_overlap_score': 0.2,
        'error_type': None,
        'intent_id': None,
        'intent_name': None
    }
    gap1 = analyzer._classify_and_prioritize(scenario1)
    print(f"✅ 失敗原因: {gap1.failure_reason.value}")
    print(f"✅ 優先級: {gap1.priority.value}")
    assert gap1.failure_reason == FailureReason.NO_MATCH
    assert gap1.priority == GapPriority.P0

    # Test Case 2: LOW_CONFIDENCE (similarity >= 0.6, confidence < 0.7) → P1
    print("\n[Test 2] similarity >= 0.6, confidence < 0.7 → LOW_CONFIDENCE & P1")
    scenario2 = {
        'scenario_id': 2,
        'question': '租金可以用信用卡支付嗎？',
        'similarity_score': 0.75,
        'confidence_score': 0.55,
        'semantic_overlap_score': 0.6,
        'error_type': None,
        'intent_id': 1,
        'intent_name': '繳費查詢'
    }
    gap2 = analyzer._classify_and_prioritize(scenario2)
    print(f"✅ 失敗原因: {gap2.failure_reason.value}")
    print(f"✅ 優先級: {gap2.priority.value}")
    assert gap2.failure_reason == FailureReason.LOW_CONFIDENCE
    assert gap2.priority == GapPriority.P1

    # Test Case 3: SEMANTIC_MISMATCH (semantic_overlap < 0.4) → P2
    print("\n[Test 3] semantic_overlap < 0.4 → SEMANTIC_MISMATCH & P2")
    scenario3 = {
        'scenario_id': 3,
        'question': '如何申請停車位？',
        'similarity_score': 0.8,
        'confidence_score': 0.75,
        'semantic_overlap_score': 0.35,
        'error_type': None,
        'intent_id': 2,
        'intent_name': '停車申請'
    }
    gap3 = analyzer._classify_and_prioritize(scenario3)
    print(f"✅ 失敗原因: {gap3.failure_reason.value}")
    print(f"✅ 優先級: {gap3.priority.value}")
    assert gap3.failure_reason == FailureReason.SEMANTIC_MISMATCH
    assert gap3.priority == GapPriority.P2

    # Test Case 4: SYSTEM_ERROR → P2
    print("\n[Test 4] error_type != None → SYSTEM_ERROR & P2")
    scenario4 = {
        'scenario_id': 4,
        'question': '管理費包含哪些項目？',
        'similarity_score': 0.0,
        'confidence_score': 0.0,
        'semantic_overlap_score': 0.0,
        'error_type': 'timeout',
        'intent_id': 3,
        'intent_name': '費用查詢'
    }
    gap4 = analyzer._classify_and_prioritize(scenario4)
    print(f"✅ 失敗原因: {gap4.failure_reason.value}")
    print(f"✅ 優先級: {gap4.priority.value}")
    assert gap4.failure_reason == FailureReason.SYSTEM_ERROR
    assert gap4.priority == GapPriority.P2

    print("\n✅ 所有分類測試通過！")


def test_suggest_action_type():
    """測試回應類型建議"""
    print("\n" + "=" * 60)
    print("測試回應類型建議")
    print("=" * 60)

    analyzer = GapAnalyzer(db_pool=None)

    # Test Case 1: 意圖包含「申請」→ form_fill
    print("\n[Test 1] 意圖包含「申請」→ form_fill")
    action_type1 = analyzer._suggest_action_type('維修申請', FailureReason.NO_MATCH)
    print(f"✅ 建議回應類型: {action_type1}")
    assert action_type1 == 'form_fill'

    # Test Case 2: 意圖包含「電費」→ api_call
    print("\n[Test 2] 意圖包含「電費」→ api_call")
    action_type2 = analyzer._suggest_action_type('查詢電費', FailureReason.LOW_CONFIDENCE)
    print(f"✅ 建議回應類型: {action_type2}")
    assert action_type2 == 'api_call'

    # Test Case 3: 意圖包含「繳費」→ api_call
    print("\n[Test 3] 意圖包含「繳費」→ api_call")
    action_type3 = analyzer._suggest_action_type('繳費查詢', FailureReason.LOW_CONFIDENCE)
    print(f"✅ 建議回應類型: {action_type3}")
    assert action_type3 == 'api_call'

    # Test Case 4: 一般查詢 → direct_answer
    print("\n[Test 4] 一般查詢 → direct_answer")
    action_type4 = analyzer._suggest_action_type('設施查詢', FailureReason.NO_MATCH)
    print(f"✅ 建議回應類型: {action_type4}")
    assert action_type4 == 'direct_answer'

    # Test Case 5: 無意圖 → direct_answer
    print("\n[Test 5] 無意圖 → direct_answer")
    action_type5 = analyzer._suggest_action_type(None, FailureReason.NO_MATCH)
    print(f"✅ 建議回應類型: {action_type5}")
    assert action_type5 == 'direct_answer'

    print("\n✅ 所有回應類型建議測試通過！")


def test_deduplicate_gaps():
    """測試缺口去重邏輯"""
    print("\n" + "=" * 60)
    print("測試缺口去重邏輯")
    print("=" * 60)

    analyzer = GapAnalyzer(db_pool=None)

    # 建立測試缺口（包含重複的 scenario_id）
    gaps = [
        KnowledgeGap(
            scenario_id=1,
            question='可以養寵物嗎？',
            failure_reason=FailureReason.NO_MATCH,
            priority=GapPriority.P0,
            suggested_action_type='direct_answer',
            confidence_score=0.3,
            max_similarity=0.45,
            frequency=1
        ),
        KnowledgeGap(
            scenario_id=2,
            question='租金如何支付？',
            failure_reason=FailureReason.LOW_CONFIDENCE,
            priority=GapPriority.P1,
            suggested_action_type='direct_answer',
            confidence_score=0.55,
            max_similarity=0.75,
            frequency=1
        ),
        KnowledgeGap(
            scenario_id=1,  # 重複的 scenario_id
            question='可以養寵物嗎？',
            failure_reason=FailureReason.NO_MATCH,
            priority=GapPriority.P0,
            suggested_action_type='direct_answer',
            confidence_score=0.35,
            max_similarity=0.48,
            frequency=1
        ),
        KnowledgeGap(
            scenario_id=3,
            question='如何申請停車位？',
            failure_reason=FailureReason.SEMANTIC_MISMATCH,
            priority=GapPriority.P2,
            suggested_action_type='form_fill',
            confidence_score=0.75,
            max_similarity=0.8,
            frequency=1
        ),
        KnowledgeGap(
            scenario_id=2,  # 重複的 scenario_id，但優先級更高
            question='租金如何支付？',
            failure_reason=FailureReason.NO_MATCH,
            priority=GapPriority.P0,
            suggested_action_type='direct_answer',
            confidence_score=0.4,
            max_similarity=0.5,
            frequency=1
        ),
    ]

    print(f"\n原始缺口數量: {len(gaps)}")

    # 執行去重
    unique_gaps = analyzer._deduplicate_gaps(gaps)

    print(f"去重後缺口數量: {len(unique_gaps)}")

    # 驗證結果
    assert len(unique_gaps) == 3, f"應該剩下 3 個唯一缺口，實際為 {len(unique_gaps)}"

    # 驗證 scenario_id = 1 的缺口（應該合併，frequency = 2）
    gap_1 = next((g for g in unique_gaps if g.scenario_id == 1), None)
    assert gap_1 is not None, "應該存在 scenario_id = 1 的缺口"
    assert gap_1.frequency == 2, f"scenario_id = 1 的頻率應為 2，實際為 {gap_1.frequency}"
    print(f"✅ scenario_id = 1: frequency = {gap_1.frequency}")

    # 驗證 scenario_id = 2 的缺口（應該升級為 P0）
    gap_2 = next((g for g in unique_gaps if g.scenario_id == 2), None)
    assert gap_2 is not None, "應該存在 scenario_id = 2 的缺口"
    assert gap_2.priority == GapPriority.P0, f"scenario_id = 2 的優先級應為 P0，實際為 {gap_2.priority.value}"
    assert gap_2.frequency == 2, f"scenario_id = 2 的頻率應為 2，實際為 {gap_2.frequency}"
    print(f"✅ scenario_id = 2: priority = {gap_2.priority.value}, frequency = {gap_2.frequency}")

    # 驗證 scenario_id = 3 的缺口
    gap_3 = next((g for g in unique_gaps if g.scenario_id == 3), None)
    assert gap_3 is not None, "應該存在 scenario_id = 3 的缺口"
    assert gap_3.frequency == 1, f"scenario_id = 3 的頻率應為 1，實際為 {gap_3.frequency}"
    print(f"✅ scenario_id = 3: frequency = {gap_3.frequency}")

    print("\n✅ 所有去重測試通過！")


def test_priority_value():
    """測試優先級數值化"""
    print("\n" + "=" * 60)
    print("測試優先級數值化")
    print("=" * 60)

    analyzer = GapAnalyzer(db_pool=None)

    p0_value = analyzer._priority_value(GapPriority.P0)
    p1_value = analyzer._priority_value(GapPriority.P1)
    p2_value = analyzer._priority_value(GapPriority.P2)

    print(f"P0 數值: {p0_value}")
    print(f"P1 數值: {p1_value}")
    print(f"P2 數值: {p2_value}")

    assert p0_value > p1_value > p2_value, "優先級數值應該是 P0 > P1 > P2"

    print("✅ 優先級數值化測試通過！")


if __name__ == "__main__":
    try:
        test_classify_and_prioritize()
        test_suggest_action_type()
        test_deduplicate_gaps()
        test_priority_value()

        print("\n" + "=" * 60)
        print("✅ 所有單元測試通過！")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
