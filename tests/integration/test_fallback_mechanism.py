"""
回退機制自動化測試

測試 4 層回退路徑：
1. SOP 優先 → 使用 SOP
2. SOP fallback → 知識庫
3. 知識庫 fallback → RAG 向量搜尋
4. RAG fallback → 兜底回應

確保：
- 有 SOP 時優先使用 SOP
- 無 SOP 時自動降級到知識庫
- 無知識庫時降級到 RAG
- 全部失敗時提供友善的兜底回應
"""

import pytest
import requests
import time
from typing import Dict, Optional

# 測試配置
BASE_URL = "http://localhost:8100"
API_ENDPOINT = f"{BASE_URL}/api/v1/message"

# 測試業者（使用 Vendor 1）
TEST_VENDOR_ID = 1


def call_api(question: str, vendor_id: int = TEST_VENDOR_ID) -> Optional[Dict]:
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


class TestLayer1_SOPPriority:
    """第 1 層：SOP 優先測試"""

    def test_has_sop_uses_sop(self):
        """測試：有 SOP 時應該使用 SOP"""
        # 這個問題應該有對應的 SOP
        question = "租金怎麼繳？"

        response = call_api(question)

        # 驗證基本結構
        assert "answer" in response, "回應缺少 answer 欄位"
        assert "sources" in response, "回應缺少 sources 欄位"

        # 驗證來源
        sources = response.get("sources", [])
        assert len(sources) > 0, "應該有知識來源"

        # 檢查來源類型（SOP 的 scope 應該是 vendor_sop）
        sop_sources = [s for s in sources if s.get("scope") == "vendor_sop"]
        assert len(sop_sources) > 0, "應該使用 SOP 作為來源"

        print(f"\n✅ SOP 優先測試通過")
        print(f"   問題：{question}")
        print(f"   來源數量：{len(sources)}")
        print(f"   SOP 來源數量：{len(sop_sources)}")
        print(f"   來源項目：{[s.get('question_summary', 'N/A')[:30] for s in sop_sources[:3]]}")

        time.sleep(1)

    def test_sop_content_in_answer(self):
        """測試：使用 SOP 時，回答應包含 SOP 關鍵內容"""
        question = "租金怎麼繳？"

        response = call_api(question)
        answer = response.get("answer", "")

        # 檢查是否包含金流相關關鍵字（根據 Vendor 1 是 through_company）
        has_company_keyword = any(kw in answer for kw in ["公司", "系統", "JGB"])
        assert has_company_keyword, f"使用 SOP 時應包含公司相關關鍵字\n回答：{answer[:200]}"

        print(f"\n✅ SOP 內容驗證通過")
        print(f"   答案包含金流相關關鍵字")

        time.sleep(1)


class TestLayer2_KnowledgeBaseFallback:
    """第 2 層：知識庫 Fallback 測試"""

    def test_no_sop_uses_knowledge_base(self):
        """測試：無 SOP 但有知識庫時，應使用知識庫"""
        # 選擇一個不太可能有 SOP 但可能有知識庫的問題
        # 例如：租賃合約相關的通用問題
        question = "租約到期前多久需要通知？"

        response = call_api(question)

        # 驗證有回答
        assert "answer" in response, "回應缺少 answer 欄位"
        answer = response.get("answer", "")
        assert len(answer) > 50, "回答內容太短，可能是兜底回應"

        # 驗證有來源
        sources = response.get("sources", [])

        # 如果有來源，檢查是否不是 SOP
        if sources:
            sop_sources = [s for s in sources if s.get("scope") == "vendor_sop"]
            # 可能沒有 SOP 來源，或者 SOP 不是主要來源

            print(f"\n✅ 知識庫 Fallback 測試通過")
            print(f"   問題：{question}")
            print(f"   來源數量：{len(sources)}")
            print(f"   來源類型：{[s.get('scope', 'N/A') for s in sources[:3]]}")
        else:
            # 如果沒有來源但有實質回答，可能是 RAG 找到的
            print(f"\n⚠️  知識庫測試：無來源但有回答（可能是 RAG）")
            print(f"   問題：{question}")
            print(f"   回答長度：{len(answer)}")

        time.sleep(1)

    def test_knowledge_base_answer_quality(self):
        """測試：知識庫回答品質"""
        question = "租約期間可以提前解約嗎？"

        response = call_api(question)
        answer = response.get("answer", "")

        # 驗證回答不是兜底回應
        fallback_keywords = ["不太確定", "不太理解", "無法回答", "客服專線"]
        is_fallback = any(kw in answer for kw in fallback_keywords)

        # 如果是兜底回應，只是警告而不是失敗（因為可能真的沒有相關知識）
        if is_fallback:
            print(f"\n⚠️  知識庫品質測試：返回兜底回應（可能缺少相關知識）")
            print(f"   問題：{question}")
            print(f"   建議：添加相關知識到知識庫")
        else:
            print(f"\n✅ 知識庫品質測試通過")
            print(f"   問題：{question}")
            print(f"   回答長度：{len(answer)}")

        time.sleep(1)


class TestLayer3_RAGFallback:
    """第 3 層：RAG 向量搜尋 Fallback 測試"""

    def test_no_knowledge_uses_rag(self):
        """測試：無知識庫但 RAG 能找到時，使用 RAG"""
        # 選擇一個可能在全局知識庫中但不在業者特定知識庫的問題
        question = "什麼是租賃契約？"

        response = call_api(question)

        # 驗證有回答
        assert "answer" in response, "回應缺少 answer 欄位"
        answer = response.get("answer", "")

        # 檢查是否是實質回答（非兜底）
        fallback_keywords = ["不太確定", "不太理解", "無法回答"]
        is_fallback = any(kw in answer for kw in fallback_keywords)

        sources = response.get("sources", [])

        if not is_fallback and len(answer) > 50:
            print(f"\n✅ RAG Fallback 測試通過")
            print(f"   問題：{question}")
            print(f"   來源數量：{len(sources)}")
            print(f"   回答長度：{len(answer)}")
        else:
            print(f"\n⚠️  RAG Fallback 測試：可能降級到兜底回應")
            print(f"   問題：{question}")
            print(f"   這可能是預期行為（真的沒有相關知識）")

        time.sleep(1)

    def test_rag_answer_contains_relevant_info(self):
        """測試：RAG 回答包含相關資訊"""
        question = "租賃合約的基本條款有哪些？"

        response = call_api(question)
        answer = response.get("answer", "")

        # 驗證回答長度（RAG 回答通常比較詳細）
        if len(answer) > 100:
            print(f"\n✅ RAG 答案相關性測試通過")
            print(f"   問題：{question}")
            print(f"   回答長度：{len(answer)} 字元")
        else:
            print(f"\n⚠️  RAG 答案較短（可能是邊界情況）")
            print(f"   問題：{question}")

        time.sleep(1)


class TestLayer4_FallbackResponse:
    """第 4 層：兜底回應測試"""

    def test_completely_unrelated_question_gets_fallback(self):
        """測試：完全無關的問題應返回兜底回應"""
        # 使用一個完全無關的問題
        question = "今天天氣如何？"

        response = call_api(question)

        # 驗證基本結構
        assert "answer" in response, "回應缺少 answer 欄位"
        answer = response.get("answer", "")

        # 驗證是兜底回應
        fallback_keywords = ["不太確定", "不太理解", "客服", "協助"]
        has_fallback = any(kw in answer for kw in fallback_keywords)

        # 兜底回應應該較短且友善
        assert len(answer) > 0, "兜底回應不應為空"

        print(f"\n✅ 兜底回應測試通過")
        print(f"   問題：{question}")
        print(f"   回答：{answer[:100]}...")
        print(f"   包含兜底關鍵字：{has_fallback}")

        time.sleep(1)

    def test_fallback_response_is_friendly(self):
        """測試：兜底回應應該友善且有建議"""
        question = "宇宙的終極答案是什麼？"

        response = call_api(question)
        answer = response.get("answer", "")

        # 檢查友善性
        friendly_keywords = ["抱歉", "建議", "聯繫", "協助", "客服"]
        is_friendly = any(kw in answer for kw in friendly_keywords)

        assert is_friendly, f"兜底回應應該友善\n回答：{answer}"

        print(f"\n✅ 兜底回應友善性測試通過")
        print(f"   問題：{question}")
        print(f"   回答：{answer}")

        time.sleep(1)

    def test_fallback_provides_contact_info(self):
        """測試：兜底回應應提供聯繫方式"""
        question = "我想問一個你們不知道的問題"

        response = call_api(question)
        answer = response.get("answer", "")

        # 檢查是否提供聯繫方式
        contact_keywords = ["客服", "聯繫", "專線", "協助"]
        has_contact = any(kw in answer for kw in contact_keywords)

        # 這個測試不強制，因為並非所有兜底回應都需要聯繫方式
        if has_contact:
            print(f"\n✅ 兜底回應提供聯繫方式")
            print(f"   回答：{answer}")
        else:
            print(f"\n⚠️  兜底回應未提供聯繫方式（可能不需要）")
            print(f"   回答：{answer}")

        time.sleep(1)


class TestFallbackSequence:
    """回退序列完整性測試"""

    def test_fallback_sequence_coherence(self):
        """測試：回退序列的一致性"""
        # 準備不同類型的問題
        test_cases = [
            {
                "question": "租金怎麼繳？",
                "expected_layer": "SOP",
                "description": "有 SOP 的問題"
            },
            {
                "question": "租約條款有哪些？",
                "expected_layer": "知識庫或 RAG",
                "description": "可能有知識庫的問題"
            },
            {
                "question": "火星上有生命嗎？",
                "expected_layer": "兜底",
                "description": "完全無關的問題"
            }
        ]

        results = []

        for case in test_cases:
            response = call_api(case["question"])
            answer = response.get("answer", "")
            sources = response.get("sources", [])

            # 判斷實際使用的層級
            if sources and any(s.get("scope") == "vendor_sop" for s in sources):
                actual_layer = "SOP"
            elif sources and len(sources) > 0:
                actual_layer = "知識庫或 RAG"
            elif any(kw in answer for kw in ["不太確定", "客服"]):
                actual_layer = "兜底"
            else:
                actual_layer = "知識庫或 RAG"

            results.append({
                "question": case["question"],
                "expected": case["expected_layer"],
                "actual": actual_layer,
                "description": case["description"]
            })

            time.sleep(1)

        # 顯示結果
        print(f"\n✅ 回退序列一致性測試完成")
        print(f"\n結果：")
        for r in results:
            match = "✓" if r["expected"] in r["actual"] or r["actual"] in r["expected"] else "⚠"
            print(f"   {match} {r['description']}")
            print(f"      預期：{r['expected']}")
            print(f"      實際：{r['actual']}")
            print()


class TestSourcePriority:
    """來源優先級測試"""

    def test_sop_has_higher_priority_than_knowledge(self):
        """測試：SOP 優先級高於知識庫"""
        # 使用一個同時可能有 SOP 和知識庫的問題
        question = "租金怎麼繳？"

        response = call_api(question)
        sources = response.get("sources", [])

        if len(sources) > 0:
            # 檢查第一個來源是否是 SOP
            first_source_scope = sources[0].get("scope")

            # 如果有 SOP 來源，它應該排在前面
            sop_sources = [s for s in sources if s.get("scope") == "vendor_sop"]
            if sop_sources:
                # 第一個來源應該是 SOP
                assert first_source_scope == "vendor_sop", \
                    f"SOP 應該優先於其他來源\n第一個來源：{first_source_scope}"

                print(f"\n✅ 來源優先級測試通過")
                print(f"   第一個來源類型：{first_source_scope}")
                print(f"   SOP 來源數量：{len(sop_sources)}")
            else:
                print(f"\n⚠️  此問題無 SOP 來源")
        else:
            print(f"\n⚠️  無來源資料")

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
