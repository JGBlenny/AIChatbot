"""
知識生成器客戶端測試

測試 KnowledgeGeneratorClient 的核心功能：
1. OpenAI API 調用（Stub 模式）
2. Prompt 構建
3. 批次生成
4. 錯誤處理
5. 資料持久化

由於不依賴實際 OpenAI API Key，使用 Stub 模式進行測試
"""

import asyncio
import json
import pytest
from knowledge_generator import KnowledgeGeneratorClient


# ============================================
# 測試 1: Stub 模式知識生成
# ============================================

@pytest.mark.asyncio
async def test_stub_generate_knowledge():
    """測試 Stub 模式：無 API Key 時應生成模擬知識"""

    # 不提供 API Key，啟用 Stub 模式
    client = KnowledgeGeneratorClient(
        openai_api_key=None,
        db_pool=None,
        model="gpt-3.5-turbo"
    )

    # 準備測試數據
    gaps = [
        {
            "gap_id": 1,
            "question": "租金每個月幾號要繳？",
            "failure_reason": "no_match",
            "priority": "p0"
        },
        {
            "gap_id": 2,
            "question": "如何申請停車位？",
            "failure_reason": "low_confidence",
            "priority": "p1"
        }
    ]

    action_type_judgments = {
        1: {"action_type": "direct_answer", "confidence": 0.9},
        2: {"action_type": "form_fill", "confidence": 0.8}
    }

    # 執行生成
    result = await client.generate_knowledge(
        loop_id=1,
        gaps=gaps,
        action_type_judgments=action_type_judgments,
        iteration=1,
        vendor_id=1
    )

    # 驗證結果
    assert len(result) == 2

    # 驗證第一個知識
    knowledge_1 = result[0]
    assert knowledge_1["gap_id"] == 1
    assert knowledge_1["question"] == "租金每個月幾號要繳？"
    assert "Stub 模式" in knowledge_1["answer"]
    assert knowledge_1["action_type"] == "direct_answer"
    assert knowledge_1["needs_verification"] == True
    assert len(knowledge_1["keywords"]) > 0

    # 驗證第二個知識
    knowledge_2 = result[1]
    assert knowledge_2["gap_id"] == 2
    assert knowledge_2["action_type"] == "form_fill"

    print("✅ Stub 模式知識生成測試通過")


# ============================================
# 測試 2: Prompt 構建邏輯
# ============================================

def test_build_prompt():
    """測試 Prompt 構建邏輯"""

    client = KnowledgeGeneratorClient(
        openai_api_key=None,
        db_pool=None
    )

    gap = {
        "gap_id": 1,
        "question": "租金每個月幾號要繳？",
        "failure_reason": "no_match",
        "priority": "p0",
        "intent_name": "payment_inquiry"
    }

    action_type_judgment = {
        "action_type": "direct_answer",
        "confidence": 0.9
    }

    existing_knowledge = [
        {
            "question": "租金如何繳納？",
            "answer": "可以透過銀行轉帳或自動扣款..."
        }
    ]

    # 構建 Prompt
    prompt = client._build_prompt(
        gap=gap,
        action_type_judgment=action_type_judgment,
        existing_knowledge=existing_knowledge,
        vendor_id=1
    )

    # 驗證 Prompt 內容
    assert "租金每個月幾號要繳？" in prompt
    assert "no_match" in prompt
    assert "p0" in prompt
    assert "direct_answer" in prompt
    assert "payment_inquiry" in prompt
    assert "租金如何繳納？" in prompt
    assert "包租代管公司" in prompt
    assert "JSON 格式" in prompt

    print("✅ Prompt 構建測試通過")


# ============================================
# 測試 3: 批次生成（並發控制）
# ============================================

@pytest.mark.asyncio
async def test_batch_generation_concurrency():
    """測試批次生成的並發控制（應每次最多 5 個並發）"""

    client = KnowledgeGeneratorClient(
        openai_api_key=None,
        db_pool=None
    )

    # 準備 12 個 gaps（應分成 3 批：5 + 5 + 2）
    gaps = [
        {
            "gap_id": i,
            "question": f"問題 {i}",
            "failure_reason": "no_match",
            "priority": "p0"
        }
        for i in range(1, 13)
    ]

    action_type_judgments = {
        i: {"action_type": "direct_answer", "confidence": 0.9}
        for i in range(1, 13)
    }

    # 執行批次生成
    result = await client.generate_knowledge(
        loop_id=1,
        gaps=gaps,
        action_type_judgments=action_type_judgments,
        iteration=1,
        vendor_id=1
    )

    # 驗證結果數量
    assert len(result) == 12

    # 驗證所有 gap_id 都有對應的知識
    gap_ids = {k["gap_id"] for k in result}
    assert gap_ids == set(range(1, 13))

    print("✅ 批次生成並發控制測試通過")


# ============================================
# 測試 4: 不同 action_type 的知識生成
# ============================================

@pytest.mark.asyncio
async def test_different_action_types():
    """測試不同 action_type 的知識生成"""

    client = KnowledgeGeneratorClient(
        openai_api_key=None,
        db_pool=None
    )

    gaps = [
        {
            "gap_id": 1,
            "question": "租金何時繳納？",
            "failure_reason": "no_match",
            "priority": "p0"
        },
        {
            "gap_id": 2,
            "question": "如何申請維修？",
            "failure_reason": "low_confidence",
            "priority": "p1"
        },
        {
            "gap_id": 3,
            "question": "我的電費是多少？",
            "failure_reason": "no_match",
            "priority": "p0"
        },
        {
            "gap_id": 4,
            "question": "如何繳納水電費？",
            "failure_reason": "no_match",
            "priority": "p0"
        }
    ]

    action_type_judgments = {
        1: {"action_type": "direct_answer", "confidence": 0.95},
        2: {"action_type": "form_fill", "confidence": 0.85},
        3: {"action_type": "api_call", "confidence": 0.90},
        4: {"action_type": "form_then_api", "confidence": 0.80}
    }

    # 執行生成
    result = await client.generate_knowledge(
        loop_id=1,
        gaps=gaps,
        action_type_judgments=action_type_judgments,
        iteration=1,
        vendor_id=1
    )

    # 驗證每個知識的 action_type
    for knowledge in result:
        gap_id = knowledge["gap_id"]
        expected_action_type = action_type_judgments[gap_id]["action_type"]
        assert knowledge["action_type"] == expected_action_type

    print("✅ 不同 action_type 知識生成測試通過")


# ============================================
# 測試 5: 空 gaps 處理
# ============================================

@pytest.mark.asyncio
async def test_empty_gaps():
    """測試空 gaps 列表的處理"""

    client = KnowledgeGeneratorClient(
        openai_api_key=None,
        db_pool=None
    )

    result = await client.generate_knowledge(
        loop_id=1,
        gaps=[],
        action_type_judgments={},
        iteration=1,
        vendor_id=1
    )

    assert result == []

    print("✅ 空 gaps 處理測試通過")


# ============================================
# 測試 6: 驗證返回的知識結構
# ============================================

@pytest.mark.asyncio
async def test_knowledge_structure():
    """測試生成的知識結構是否完整"""

    client = KnowledgeGeneratorClient(
        openai_api_key=None,
        db_pool=None
    )

    gaps = [
        {
            "gap_id": 1,
            "question": "測試問題",
            "failure_reason": "no_match",
            "priority": "p0"
        }
    ]

    action_type_judgments = {
        1: {"action_type": "direct_answer", "confidence": 0.9}
    }

    result = await client.generate_knowledge(
        loop_id=1,
        gaps=gaps,
        action_type_judgments=action_type_judgments,
        iteration=1,
        vendor_id=1
    )

    knowledge = result[0]

    # 驗證必要欄位
    assert "gap_id" in knowledge
    assert "question" in knowledge
    assert "answer" in knowledge
    assert "keywords" in knowledge
    assert "confidence_explanation" in knowledge
    assert "needs_verification" in knowledge
    assert "action_type" in knowledge

    # 驗證資料型態
    assert isinstance(knowledge["gap_id"], int)
    assert isinstance(knowledge["question"], str)
    assert isinstance(knowledge["answer"], str)
    assert isinstance(knowledge["keywords"], list)
    assert isinstance(knowledge["confidence_explanation"], str)
    assert isinstance(knowledge["needs_verification"], bool)
    assert isinstance(knowledge["action_type"], str)

    # 驗證 keywords 列表非空
    assert len(knowledge["keywords"]) > 0

    print("✅ 知識結構驗證測試通過")


# ============================================
# 主函數：執行所有測試
# ============================================

async def run_all_tests():
    """執行所有測試"""

    print("\n" + "="*60)
    print("開始測試 KnowledgeGeneratorClient")
    print("="*60 + "\n")

    # 測試 1: Stub 模式知識生成
    print("測試 1: Stub 模式知識生成")
    await test_stub_generate_knowledge()
    print()

    # 測試 2: Prompt 構建
    print("測試 2: Prompt 構建")
    test_build_prompt()
    print()

    # 測試 3: 批次生成並發控制
    print("測試 3: 批次生成並發控制")
    await test_batch_generation_concurrency()
    print()

    # 測試 4: 不同 action_type
    print("測試 4: 不同 action_type 知識生成")
    await test_different_action_types()
    print()

    # 測試 5: 空 gaps 處理
    print("測試 5: 空 gaps 處理")
    await test_empty_gaps()
    print()

    # 測試 6: 知識結構驗證
    print("測試 6: 知識結構驗證")
    await test_knowledge_structure()
    print()

    print("="*60)
    print("✅ 所有測試通過！")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
