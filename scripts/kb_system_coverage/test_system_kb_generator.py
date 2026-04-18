"""
SystemKBGenerator 單元測試

測試覆蓋：
- 缺口過濾（只處理 recommendation=add_kb, query_type=static）
- LLM prompt 建構（含模組上下文）
- KB 品質驗證（長度、工程術語、入口路徑、語義去重）
- 批量生成流程
- 候選項匯出
- 冪等性（topic_id 去重）
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 確保 project root 在 sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.kb_system_coverage.models import (
    Feature,
    GapItem,
    Module,
    SimilarItem,
)
from scripts.kb_system_coverage.system_kb_generator import SystemKBGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def modules() -> List[Module]:
    """測試用模組清單"""
    return [
        Module(
            module_id="billing",
            module_name="帳務管理",
            description="租金帳單、費用項目、收款紀錄、催繳",
            features=[
                Feature(
                    feature_id="billing_001",
                    feature_name="租金帳單查詢",
                    roles=["tenant", "landlord"],
                    entry_point="both",
                ),
                Feature(
                    feature_id="billing_002",
                    feature_name="繳費操作",
                    roles=["tenant"],
                    entry_point="app",
                ),
            ],
        ),
        Module(
            module_id="repair",
            module_name="修繕系統",
            description="報修提交、修繕進度追蹤、維修派工",
            features=[
                Feature(
                    feature_id="repair_001",
                    feature_name="報修提交",
                    roles=["tenant"],
                    entry_point="app",
                ),
            ],
        ),
    ]


@pytest.fixture
def static_kb_gaps() -> List[GapItem]:
    """recommendation=add_kb 且 query_type=static 的缺口"""
    return [
        GapItem(
            topic_id="帳務_001",
            question="怎麼在 APP 查看帳單明細",
            gap_type="uncovered",
            recommendation="add_kb",
            query_type="static",
            priority="p0",
        ),
        GapItem(
            topic_id="修繕_001",
            question="怎麼在 APP 報修",
            gap_type="uncovered",
            recommendation="add_kb",
            query_type="static",
            priority="p0",
        ),
    ]


@pytest.fixture
def mixed_gaps() -> List[GapItem]:
    """包含各種類型的缺口，用來驗證過濾邏輯"""
    return [
        GapItem(
            topic_id="帳務_001",
            question="怎麼在 APP 查看帳單明細",
            gap_type="uncovered",
            recommendation="add_kb",
            query_type="static",
            priority="p0",
        ),
        GapItem(
            topic_id="帳務_002",
            question="帳單為什麼沒產生發票",
            gap_type="uncovered",
            recommendation="add_kb",
            query_type="dynamic",  # 應被排除
            priority="p0",
        ),
        GapItem(
            topic_id="帳務_003",
            question="催繳流程怎麼走",
            gap_type="uncovered",
            recommendation="add_sop",  # 應被排除
            query_type="static",
            priority="p1",
        ),
        GapItem(
            topic_id="修繕_001",
            question="怎麼在 APP 報修",
            gap_type="needs_improvement",
            recommendation="add_kb",
            query_type="static",
            priority="p0",
        ),
    ]


@pytest.fixture
def generator() -> SystemKBGenerator:
    return SystemKBGenerator(openai_api_key="test-key", batch_size=5)


def _mock_openai_response(content: dict) -> MagicMock:
    """建立模擬的 OpenAI API 回應"""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps(content, ensure_ascii=False)
    mock_resp.usage.prompt_tokens = 100
    mock_resp.usage.completion_tokens = 50
    return mock_resp


def _good_kb_response() -> dict:
    """一個品質合格的 KB 回應"""
    return {
        "question_summary": "APP 查看帳單",
        "answer": (
            "您可以在 APP 首頁 > 繳費 > 帳單明細中查看所有帳單資訊。"
            "系統會列出每筆帳單的金額、到期日和付款狀態。"
            "如果您有多個租約，可以在上方切換不同物件來查看對應的帳單。"
        ),
        "keywords": ["帳單", "查看帳單", "帳單明細", "APP 帳單"],
        "category": "帳務管理",
        "target_user": ["tenant"],
        "business_types": ["rental", "management"],
    }


# ---------------------------------------------------------------------------
# 1. 缺口過濾
# ---------------------------------------------------------------------------

class TestFilterStaticKBGaps:
    """測試 _filter_static_kb_gaps：只保留 add_kb + static"""

    def test_filters_only_add_kb_static(self, generator, mixed_gaps):
        result = generator._filter_static_kb_gaps(mixed_gaps)
        assert len(result) == 2
        for gap in result:
            assert gap.recommendation == "add_kb"
            assert gap.query_type == "static"

    def test_empty_input_returns_empty(self, generator):
        result = generator._filter_static_kb_gaps([])
        assert result == []

    def test_no_matching_gaps(self, generator):
        gaps = [
            GapItem(
                topic_id="x",
                question="q",
                gap_type="uncovered",
                recommendation="add_sop",
                query_type="dynamic",
                priority="p1",
            ),
        ]
        result = generator._filter_static_kb_gaps(gaps)
        assert result == []

    def test_includes_needs_improvement_gaps(self, generator, mixed_gaps):
        """needs_improvement + add_kb + static 也要包含"""
        result = generator._filter_static_kb_gaps(mixed_gaps)
        topic_ids = [g.topic_id for g in result]
        assert "修繕_001" in topic_ids  # needs_improvement gap


# ---------------------------------------------------------------------------
# 2. Prompt 建構
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    """測試 _build_prompt：確保 prompt 包含模組上下文"""

    def test_prompt_contains_module_info(self, generator, modules, static_kb_gaps):
        gap = static_kb_gaps[0]  # 帳務_001
        module = modules[0]  # billing
        prompt = generator._build_prompt(gap, module)
        assert "帳務管理" in prompt
        assert "租金帳單" in prompt
        assert gap.question in prompt

    def test_prompt_contains_feature_list(self, generator, modules, static_kb_gaps):
        gap = static_kb_gaps[0]
        module = modules[0]
        prompt = generator._build_prompt(gap, module)
        assert "租金帳單查詢" in prompt
        assert "繳費操作" in prompt

    def test_prompt_contains_output_format_instructions(self, generator, modules, static_kb_gaps):
        gap = static_kb_gaps[0]
        module = modules[0]
        prompt = generator._build_prompt(gap, module)
        assert "question_summary" in prompt
        assert "answer" in prompt
        assert "keywords" in prompt

    def test_prompt_mentions_entry_path(self, generator, modules, static_kb_gaps):
        """prompt 應指示 LLM 包含操作入口路徑"""
        gap = static_kb_gaps[0]
        module = modules[0]
        prompt = generator._build_prompt(gap, module)
        assert "入口" in prompt or "路徑" in prompt


# ---------------------------------------------------------------------------
# 3. 品質驗證
# ---------------------------------------------------------------------------

class TestValidateQuality:
    """測試 _validate_quality"""

    def test_good_kb_passes(self, generator):
        kb = _good_kb_response()
        is_valid, issues = generator._validate_quality(kb)
        assert is_valid is True
        assert issues == []

    def test_too_short_answer_fails(self, generator):
        kb = _good_kb_response()
        kb["answer"] = "請到 APP 查看。"  # < 50 字
        is_valid, issues = generator._validate_quality(kb)
        assert is_valid is False
        assert any("長度" in issue or "50" in issue for issue in issues)

    def test_only_contact_manager_fails(self, generator):
        kb = _good_kb_response()
        kb["answer"] = "請洽管理師" + "。" * 50  # 長度夠但只說請洽管理師
        is_valid, issues = generator._validate_quality(kb)
        assert is_valid is False
        assert any("管理師" in issue for issue in issues)

    def test_engineering_terms_fails(self, generator):
        kb = _good_kb_response()
        kb["answer"] = (
            "您可以呼叫 /api/v1/bills endpoint 來查看帳單，"
            "系統會透過 getBillList() function 回傳 JSON response。"
            "入口路徑：APP 首頁 > 帳務。"
        )
        is_valid, issues = generator._validate_quality(kb)
        assert is_valid is False
        assert any("工程" in issue or "術語" in issue for issue in issues)

    def test_missing_entry_path_fails(self, generator):
        kb = _good_kb_response()
        kb["answer"] = (
            "系統提供帳單查詢功能，您可以隨時查看所有帳單的金額、到期日和付款狀態，"
            "如果有多個租約也能分別查看對應帳單。"
        )
        is_valid, issues = generator._validate_quality(kb)
        assert is_valid is False
        assert any("入口" in issue or "路徑" in issue for issue in issues)

    def test_missing_question_summary_fails(self, generator):
        kb = _good_kb_response()
        kb["question_summary"] = ""
        is_valid, issues = generator._validate_quality(kb)
        assert is_valid is False

    def test_question_summary_too_long_fails(self, generator):
        kb = _good_kb_response()
        kb["question_summary"] = "這是一個超過二十個字元的問題摘要標題來測試長度限制功能"
        is_valid, issues = generator._validate_quality(kb)
        assert is_valid is False
        assert any("20" in issue or "摘要" in issue for issue in issues)


# ---------------------------------------------------------------------------
# 4. 工程術語檢查
# ---------------------------------------------------------------------------

class TestCheckEngineeringTerms:
    """測試 _check_engineering_terms"""

    def test_clean_text_returns_false(self, generator):
        text = "您可以在 APP 首頁點選「繳費」按鈕，查看所有待繳帳單。"
        assert generator._check_engineering_terms(text) is False

    def test_api_endpoint_returns_true(self, generator):
        text = "呼叫 /api/v1/bills 端點查詢帳單"
        assert generator._check_engineering_terms(text) is True

    def test_function_name_returns_true(self, generator):
        text = "使用 getBillList() 查詢帳單列表"
        assert generator._check_engineering_terms(text) is True

    def test_variable_name_returns_true(self, generator):
        text = "設定 bill_status 為 paid"
        assert generator._check_engineering_terms(text) is True

    def test_json_reference_returns_true(self, generator):
        text = "回傳 JSON response 包含 bill_id"
        assert generator._check_engineering_terms(text) is True

    def test_http_method_returns_true(self, generator):
        text = "發送 GET 請求到伺服器查詢資料"
        assert generator._check_engineering_terms(text) is True


# ---------------------------------------------------------------------------
# 5. 語義去重
# ---------------------------------------------------------------------------

class TestSemanticDedup:
    """測試 _check_semantic_dedup"""

    def test_no_existing_kb_returns_false(self, generator):
        """沒有既有 KB 時不是重複"""
        kb = _good_kb_response()
        result = asyncio.run(generator._check_semantic_dedup(kb, []))
        assert result is False

    def test_no_existing_kb_none_returns_false(self, generator):
        """existing_kb=None 時不是重複"""
        kb = _good_kb_response()
        result = asyncio.run(generator._check_semantic_dedup(kb, None))
        assert result is False

    def test_high_similarity_returns_true(self, generator):
        """相似度 >= 0.85 應判定為重複"""
        kb = _good_kb_response()
        existing = [
            {"question_summary": "APP 查看帳單", "answer": "在APP查看帳單", "similarity": 0.90},
        ]
        # Mock the similarity calculation
        with patch.object(generator, '_compute_similarity', return_value=0.90):
            result = asyncio.run(generator._check_semantic_dedup(kb, existing))
            assert result is True

    def test_low_similarity_returns_false(self, generator):
        """相似度 < 0.85 不算重複"""
        kb = _good_kb_response()
        existing = [
            {"question_summary": "修繕報修", "answer": "在APP報修", "similarity": 0.30},
        ]
        with patch.object(generator, '_compute_similarity', return_value=0.30):
            result = asyncio.run(generator._check_semantic_dedup(kb, existing))
            assert result is False


# ---------------------------------------------------------------------------
# 6. 批量生成
# ---------------------------------------------------------------------------

class TestGenerateBatch:
    """測試 generate_batch 完整流程"""

    def test_generate_batch_success(self, generator, static_kb_gaps, modules):
        """正常生成流程"""
        good_resp = _mock_openai_response(_good_kb_response())

        with patch.object(
            generator.client.chat.completions, "create",
            new_callable=AsyncMock, return_value=good_resp,
        ):
            with patch.object(generator, '_check_semantic_dedup',
                              new_callable=AsyncMock, return_value=False):
                results = asyncio.run(
                    generator.generate_batch(static_kb_gaps, modules)
                )

        assert len(results) == 2
        for item in results:
            assert "question_summary" in item
            assert "answer" in item
            assert "keywords" in item
            assert "category" in item
            assert "topic_id" in item
            assert item["status"] == "pending_review"

    def test_generate_batch_filters_gaps(self, generator, mixed_gaps, modules):
        """generate_batch 應自動過濾非 add_kb/static 缺口"""
        good_resp = _mock_openai_response(_good_kb_response())

        with patch.object(
            generator.client.chat.completions, "create",
            new_callable=AsyncMock, return_value=good_resp,
        ):
            with patch.object(generator, '_check_semantic_dedup',
                              new_callable=AsyncMock, return_value=False):
                results = asyncio.run(
                    generator.generate_batch(mixed_gaps, modules)
                )

        # mixed_gaps 中只有 2 筆符合 add_kb + static
        assert len(results) == 2

    def test_generate_batch_skips_quality_failures(self, generator, static_kb_gaps, modules):
        """品質驗證不通過的項目應被排除"""
        bad_resp = _mock_openai_response({
            "question_summary": "查帳",
            "answer": "請洽管理師。" * 10,  # 只說請洽管理師
            "keywords": ["帳單"],
            "category": "帳務管理",
            "target_user": ["tenant"],
            "business_types": ["rental"],
        })

        with patch.object(
            generator.client.chat.completions, "create",
            new_callable=AsyncMock, return_value=bad_resp,
        ):
            results = asyncio.run(
                generator.generate_batch(static_kb_gaps, modules)
            )

        # 全部因品質問題被排除
        assert len(results) == 0

    def test_generate_batch_skips_duplicates(self, generator, static_kb_gaps, modules):
        """語義重複的項目應被排除"""
        good_resp = _mock_openai_response(_good_kb_response())

        with patch.object(
            generator.client.chat.completions, "create",
            new_callable=AsyncMock, return_value=good_resp,
        ):
            with patch.object(generator, '_check_semantic_dedup',
                              new_callable=AsyncMock, return_value=True):
                results = asyncio.run(
                    generator.generate_batch(static_kb_gaps, modules)
                )

        assert len(results) == 0

    def test_generate_batch_empty_gaps(self, generator, modules):
        """空缺口清單應回傳空結果"""
        results = asyncio.run(generator.generate_batch([], modules))
        assert results == []

    def test_generate_batch_includes_topic_id(self, generator, static_kb_gaps, modules):
        """生成結果應保留原始 topic_id"""
        good_resp = _mock_openai_response(_good_kb_response())

        with patch.object(
            generator.client.chat.completions, "create",
            new_callable=AsyncMock, return_value=good_resp,
        ):
            with patch.object(generator, '_check_semantic_dedup',
                              new_callable=AsyncMock, return_value=False):
                results = asyncio.run(
                    generator.generate_batch(static_kb_gaps, modules)
                )

        topic_ids = {r["topic_id"] for r in results}
        assert "帳務_001" in topic_ids
        assert "修繕_001" in topic_ids

    def test_generate_batch_sets_scope_global(self, generator, static_kb_gaps, modules):
        """系統知識的 scope 應為 global"""
        good_resp = _mock_openai_response(_good_kb_response())

        with patch.object(
            generator.client.chat.completions, "create",
            new_callable=AsyncMock, return_value=good_resp,
        ):
            with patch.object(generator, '_check_semantic_dedup',
                              new_callable=AsyncMock, return_value=False):
                results = asyncio.run(
                    generator.generate_batch(static_kb_gaps, modules)
                )

        for item in results:
            assert item["scope"] == "global"


# ---------------------------------------------------------------------------
# 7. 候選項匯出
# ---------------------------------------------------------------------------

class TestExportCandidates:
    """測試 export_candidates"""

    def test_export_writes_json(self, generator, tmp_path):
        candidates = [
            {
                "topic_id": "帳務_001",
                "question_summary": "APP 查看帳單",
                "answer": "在 APP 首頁 > 繳費 > 帳單明細中查看。",
                "keywords": ["帳單"],
                "category": "帳務管理",
                "scope": "global",
                "status": "pending_review",
            },
        ]
        output_path = tmp_path / "candidates.json"
        generator.export_candidates(candidates, output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["topic_id"] == "帳務_001"

    def test_export_empty_candidates(self, generator, tmp_path):
        output_path = tmp_path / "empty.json"
        generator.export_candidates([], output_path)

        assert output_path.exists()
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data == []


# ---------------------------------------------------------------------------
# 8. 冪等性（topic_id 去重）
# ---------------------------------------------------------------------------

class TestIdempotency:
    """測試 topic_id 去重"""

    def test_dedup_by_topic_id(self, generator, static_kb_gaps, modules):
        """同一 topic_id 不應重複生成"""
        good_resp = _mock_openai_response(_good_kb_response())

        with patch.object(
            generator.client.chat.completions, "create",
            new_callable=AsyncMock, return_value=good_resp,
        ):
            with patch.object(generator, '_check_semantic_dedup',
                              new_callable=AsyncMock, return_value=False):
                # 第一次生成
                results1 = asyncio.run(
                    generator.generate_batch(static_kb_gaps, modules)
                )
                # 帶入已生成的結果作為 existing
                results2 = asyncio.run(
                    generator.generate_batch(
                        static_kb_gaps, modules,
                        existing_candidates=results1,
                    )
                )

        # 第二次應跳過已有 topic_id
        assert len(results2) == 0


# ---------------------------------------------------------------------------
# 9. 模組對照
# ---------------------------------------------------------------------------

class TestModuleLookup:
    """測試根據 gap.topic_id 對照模組"""

    def test_finds_module_by_topic_prefix(self, generator, modules):
        """從 topic_id 前綴找到對應模組"""
        # topic_id "帳務_001" 的前綴是 "帳務"，對應 module_id "billing"
        gap = GapItem(
            topic_id="帳務_001",
            question="test",
            gap_type="uncovered",
            recommendation="add_kb",
            query_type="static",
            priority="p0",
        )
        module = generator._find_module_for_gap(gap, modules)
        assert module is not None
        assert module.module_id == "billing"

    def test_returns_none_for_unknown_prefix(self, generator, modules):
        gap = GapItem(
            topic_id="未知_001",
            question="test",
            gap_type="uncovered",
            recommendation="add_kb",
            query_type="static",
            priority="p0",
        )
        module = generator._find_module_for_gap(gap, modules)
        assert module is None
