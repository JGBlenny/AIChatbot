"""
CoverageAnalyzer 單元測試

覆蓋需求：3.1, 3.2, 3.3, 3.4, 3.5
- 3.1: embedding similarity 比對 → 覆蓋狀態標記
- 3.2: 模組×角色雙維度覆蓋率統計
- 3.3: 結構化 JSON 報告產出
- 3.4: 品質不佳項目標記「需改善」
- 3.5: 缺口建議區分 add_kb / add_sop / improve_existing
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional
from unittest.mock import AsyncMock, patch

import pytest

from scripts.kb_system_coverage.models import (
    CoverageReport,
    GapItem,
    ModuleCoverage,
    RoleCoverage,
    SimilarItem,
    SystemQuestion,
)
from scripts.kb_system_coverage.coverage_analyzer import CoverageAnalyzer


# ---------------------------------------------------------------------------
# Helpers: mock embeddings
# ---------------------------------------------------------------------------

def _make_embedding(seed: float, dim: int = 8) -> List[float]:
    """Generate a deterministic mock embedding vector."""
    import math
    return [math.sin(seed * (i + 1)) for i in range(dim)]


def _make_similar_embedding(base: List[float], noise: float = 0.05) -> List[float]:
    """Create an embedding very similar to base (high cosine similarity)."""
    return [v + noise for v in base]


def _make_orthogonal_embedding(base: List[float]) -> List[float]:
    """Create an embedding dissimilar to base (low cosine similarity)."""
    return [-v + 0.5 for v in base]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _question(topic_id: str, module_id: str, question: str,
              roles: List[str], priority: str = "p0",
              query_type: str = "static",
              question_category: str = "basic_operation") -> SystemQuestion:
    return SystemQuestion(
        topic_id=topic_id,
        module_id=module_id,
        question=question,
        roles=roles,
        entry_point="app",
        priority=priority,
        query_type=query_type,
        question_category=question_category,
        keywords=[],
    )


def _kb_item(item_id: str, title: str, content: str,
             embedding: Optional[List[float]] = None) -> dict:
    return {
        "id": item_id,
        "question_summary": title,
        "answer": content,
        "embedding": embedding,
    }


def _sop_item(item_id: str, title: str, content: str,
              embedding: Optional[List[float]] = None) -> dict:
    return {
        "id": item_id,
        "title": title,
        "content": content,
        "embedding": embedding,
    }


# ---------------------------------------------------------------------------
# Test: cosine similarity
# ---------------------------------------------------------------------------

class TestCosineSimilarity:
    def test_identical_vectors(self):
        analyzer = CoverageAnalyzer()
        v = [1.0, 2.0, 3.0]
        assert analyzer._cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors(self):
        analyzer = CoverageAnalyzer()
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        assert analyzer._cosine_similarity(v1, v2) == pytest.approx(0.0, abs=1e-6)

    def test_zero_vector(self):
        analyzer = CoverageAnalyzer()
        v1 = [0.0, 0.0]
        v2 = [1.0, 2.0]
        assert analyzer._cosine_similarity(v1, v2) == 0.0


# ---------------------------------------------------------------------------
# Test: quality check (Req 3.4)
# ---------------------------------------------------------------------------

class TestQualityCheck:
    def test_good_content(self):
        analyzer = CoverageAnalyzer()
        content = "這是一段足夠長的內容，包含了操作步驟和具體說明，確保使用者能夠正確完成操作。" * 2
        assert analyzer._check_quality(content) is True

    def test_short_content(self):
        """Content < 50 chars should be poor quality."""
        analyzer = CoverageAnalyzer()
        assert analyzer._check_quality("簡短回答") is False

    def test_just_contact_manager(self):
        """Content that is just '請洽管理師' is poor quality."""
        analyzer = CoverageAnalyzer()
        assert analyzer._check_quality("請洽管理師") is False

    def test_contains_contact_manager_with_other_content(self):
        """Content that mentions '請洽管理師' but has substantial other text is OK."""
        analyzer = CoverageAnalyzer()
        content = "這個功能需要管理師協助設定。若需要進一步了解，請洽管理師。操作步驟如下：首先登入系統，然後選擇功能選單。"
        assert analyzer._check_quality(content) is True

    def test_empty_content(self):
        analyzer = CoverageAnalyzer()
        assert analyzer._check_quality("") is False

    def test_exactly_50_chars(self):
        """Boundary: exactly 50 chars should pass."""
        analyzer = CoverageAnalyzer()
        content = "a" * 50
        assert analyzer._check_quality(content) is True


# ---------------------------------------------------------------------------
# Test: recommendation logic (Req 3.5)
# ---------------------------------------------------------------------------

class TestRecommendation:
    def test_improve_existing_for_needs_improvement(self):
        analyzer = CoverageAnalyzer()
        q = _question("帳務_001", "billing", "怎麼查帳單", ["tenant"])
        assert analyzer._recommend("needs_improvement", q) == "improve_existing"

    def test_add_sop_for_step_operation(self):
        """Questions with SOP signals (流程/步驟/操作/怎麼做) -> add_sop."""
        analyzer = CoverageAnalyzer()
        q = _question("帳務_002", "billing", "怎麼操作線上繳費流程", ["tenant"])
        assert analyzer._recommend("uncovered", q) == "add_sop"

    def test_add_kb_for_explanatory(self):
        """Questions with KB signals (是什麼/為什麼/定義) -> add_kb."""
        analyzer = CoverageAnalyzer()
        q = _question("帳務_003", "billing", "帳單金額是什麼意思", ["tenant"])
        assert analyzer._recommend("uncovered", q) == "add_kb"

    def test_add_sop_for_how_to_apply(self):
        analyzer = CoverageAnalyzer()
        q = _question("修繕_001", "repair", "如何申請報修", ["tenant"])
        assert analyzer._recommend("uncovered", q) == "add_sop"

    def test_default_to_add_kb(self):
        """When no SOP signal, default to add_kb."""
        analyzer = CoverageAnalyzer()
        q = _question("帳務_004", "billing", "帳單明細", ["tenant"])
        assert analyzer._recommend("uncovered", q) == "add_kb"


# ---------------------------------------------------------------------------
# Test: analyze — coverage status (Req 3.1)
# ---------------------------------------------------------------------------

class TestAnalyzeCoverage:
    @pytest.mark.asyncio
    async def test_covered_by_kb(self):
        """Question with high-similarity KB item -> covered_by_kb."""
        analyzer = CoverageAnalyzer(similarity_threshold=0.6, partial_threshold=0.4)
        q_emb = _make_embedding(1.0)
        kb_emb = _make_similar_embedding(q_emb, noise=0.01)

        questions = [_question("帳務_001", "billing", "怎麼查帳單", ["tenant"])]
        kb_items = [_kb_item("kb1", "帳單查詢", "詳細的帳單查詢操作說明，包含完整步驟和注意事項，確保使用者能夠順利完成操作。請先點選首頁的帳務功能，進入帳單列表後可查看各期帳單狀態。", kb_emb)]

        mock_client = AsyncMock()
        mock_client.get_embeddings_batch = AsyncMock(return_value=[q_emb])

        with patch.object(analyzer, '_get_embedding_client', return_value=mock_client):
            report = await analyzer.analyze(questions, kb_items, [])

        assert report.covered_by_kb == 1
        assert report.uncovered == 0
        assert len(report.gaps) == 0

    @pytest.mark.asyncio
    async def test_covered_by_sop(self):
        """Question with high-similarity SOP item -> covered_by_sop."""
        analyzer = CoverageAnalyzer(similarity_threshold=0.6, partial_threshold=0.4)
        q_emb = _make_embedding(2.0)
        sop_emb = _make_similar_embedding(q_emb, noise=0.01)

        questions = [_question("修繕_001", "repair", "如何申請報修", ["tenant"])]
        sop_items = [_sop_item("sop1", "報修申請流程", "完整的報修申請流程說明，包含步驟一到步驟五的詳細操作指引，確保租客可以順利提交報修。第一步登入 APP，第二步點選報修，第三步填寫問題描述。", sop_emb)]

        mock_client = AsyncMock()
        mock_client.get_embeddings_batch = AsyncMock(return_value=[q_emb])

        with patch.object(analyzer, '_get_embedding_client', return_value=mock_client):
            report = await analyzer.analyze(questions, [], sop_items)

        assert report.covered_by_sop == 1
        assert report.uncovered == 0

    @pytest.mark.asyncio
    async def test_uncovered(self):
        """Question with no similar items -> uncovered."""
        analyzer = CoverageAnalyzer(similarity_threshold=0.6, partial_threshold=0.4)
        q_emb = _make_embedding(3.0)
        kb_emb = _make_orthogonal_embedding(q_emb)

        questions = [_question("IoT_001", "iot", "怎麼綁定智慧門鎖", ["tenant"])]
        kb_items = [_kb_item("kb1", "帳單查詢", "帳單查詢的操作說明，與 IoT 完全無關的內容，確保測試覆蓋率。您可以在管理後台的帳務模組中查看帳單列表與明細資訊和繳費紀錄。", kb_emb)]

        mock_client = AsyncMock()
        mock_client.get_embeddings_batch = AsyncMock(return_value=[q_emb])

        with patch.object(analyzer, '_get_embedding_client', return_value=mock_client):
            report = await analyzer.analyze(questions, kb_items, [])

        assert report.uncovered == 1
        assert len(report.gaps) == 1
        assert report.gaps[0].gap_type == "uncovered"

    @pytest.mark.asyncio
    async def test_partial_covered(self):
        """Question with mid-range similarity -> partial_covered."""
        analyzer = CoverageAnalyzer(similarity_threshold=0.6, partial_threshold=0.4)
        q_emb = _make_embedding(4.0)
        # Create embedding with moderate similarity (between 0.4 and 0.6)
        partial_emb = [v + 1.2 for v in q_emb]

        questions = [_question("帳務_005", "billing", "帳單怎麼列印", ["tenant"])]
        kb_items = [_kb_item("kb1", "帳單查詢", "帳單查詢的完整操作說明，但不包含列印功能的具體步驟和操作指引。您可以在管理後台的帳務模組中查看帳單列表與明細資訊。", partial_emb)]

        mock_client = AsyncMock()
        mock_client.get_embeddings_batch = AsyncMock(return_value=[q_emb])

        with patch.object(analyzer, '_get_embedding_client', return_value=mock_client):
            report = await analyzer.analyze(questions, kb_items, [])

        assert report.partial_covered == 1
        assert len(report.gaps) == 1
        assert report.gaps[0].gap_type == "partial"


# ---------------------------------------------------------------------------
# Test: needs_improvement quality check (Req 3.4)
# ---------------------------------------------------------------------------

class TestNeedsImprovement:
    @pytest.mark.asyncio
    async def test_covered_but_poor_quality(self):
        """High similarity but poor content -> needs_improvement."""
        analyzer = CoverageAnalyzer(similarity_threshold=0.6, partial_threshold=0.4)
        q_emb = _make_embedding(5.0)
        kb_emb = _make_similar_embedding(q_emb, noise=0.01)

        questions = [_question("帳務_006", "billing", "怎麼查帳單明細", ["tenant"])]
        # Content is too short (< 50 chars)
        kb_items = [_kb_item("kb1", "帳單明細", "請洽管理師", kb_emb)]

        mock_client = AsyncMock()
        mock_client.get_embeddings_batch = AsyncMock(return_value=[q_emb])

        with patch.object(analyzer, '_get_embedding_client', return_value=mock_client):
            report = await analyzer.analyze(questions, kb_items, [])

        assert report.needs_improvement == 1
        assert len(report.gaps) == 1
        assert report.gaps[0].gap_type == "needs_improvement"
        assert report.gaps[0].recommendation == "improve_existing"


# ---------------------------------------------------------------------------
# Test: module and role coverage stats (Req 3.2)
# ---------------------------------------------------------------------------

class TestCoverageStats:
    @pytest.mark.asyncio
    async def test_module_coverage_stats(self):
        """Verify per-module coverage aggregation."""
        analyzer = CoverageAnalyzer(similarity_threshold=0.6, partial_threshold=0.4)
        q_emb1 = _make_embedding(10.0)
        q_emb2 = _make_embedding(11.0)
        kb_emb = _make_similar_embedding(q_emb1, noise=0.01)

        questions = [
            _question("帳務_001", "billing", "怎麼查帳單", ["tenant"]),
            _question("帳務_002", "billing", "帳單怎麼列印", ["tenant"]),
        ]
        kb_items = [_kb_item("kb1", "帳單查詢", "詳細的帳單查詢操作說明，包含完整步驟和注意事項，確保使用者順利操作。請先進入首頁帳務模組，即可查看各期帳單明細。", kb_emb)]

        mock_client = AsyncMock()
        mock_client.get_embeddings_batch = AsyncMock(return_value=[q_emb1, q_emb2])

        with patch.object(analyzer, '_get_embedding_client', return_value=mock_client):
            report = await analyzer.analyze(questions, kb_items, [])

        assert "billing" in report.coverage_by_module
        mod = report.coverage_by_module["billing"]
        assert mod.total == 2
        assert mod.covered_by_kb + mod.uncovered + mod.partial_covered + mod.needs_improvement == 2

    @pytest.mark.asyncio
    async def test_role_coverage_stats(self):
        """Verify per-role coverage aggregation (a question with multiple roles counts for each)."""
        analyzer = CoverageAnalyzer(similarity_threshold=0.6, partial_threshold=0.4)
        q_emb = _make_embedding(12.0)
        kb_emb = _make_similar_embedding(q_emb, noise=0.01)

        questions = [
            _question("帳務_001", "billing", "怎麼查帳單", ["tenant", "landlord"]),
        ]
        kb_items = [_kb_item("kb1", "帳單查詢", "詳細的帳單查詢操作說明，確保各角色使用者都能順利完成帳單查詢的操作流程。請先登入系統後進入帳務模組即可查看各期帳單。", kb_emb)]

        mock_client = AsyncMock()
        mock_client.get_embeddings_batch = AsyncMock(return_value=[q_emb])

        with patch.object(analyzer, '_get_embedding_client', return_value=mock_client):
            report = await analyzer.analyze(questions, kb_items, [])

        assert "tenant" in report.coverage_by_role
        assert "landlord" in report.coverage_by_role
        assert report.coverage_by_role["tenant"].total == 1
        assert report.coverage_by_role["landlord"].total == 1

    @pytest.mark.asyncio
    async def test_total_counts(self):
        """Verify total_questions matches input length."""
        analyzer = CoverageAnalyzer()
        q_embs = [_make_embedding(float(i)) for i in range(3)]

        questions = [
            _question("帳務_001", "billing", "Q1", ["tenant"]),
            _question("修繕_001", "repair", "Q2", ["tenant"]),
            _question("合約_001", "contract", "Q3", ["landlord"]),
        ]

        mock_client = AsyncMock()
        mock_client.get_embeddings_batch = AsyncMock(return_value=q_embs)

        with patch.object(analyzer, '_get_embedding_client', return_value=mock_client):
            report = await analyzer.analyze(questions, [], [])

        assert report.total_questions == 3


# ---------------------------------------------------------------------------
# Test: gap item details (Req 3.3, 3.5)
# ---------------------------------------------------------------------------

class TestGapItems:
    @pytest.mark.asyncio
    async def test_gap_has_similar_existing(self):
        """Gap items should list most similar existing items."""
        analyzer = CoverageAnalyzer(similarity_threshold=0.6, partial_threshold=0.4)
        q_emb = _make_embedding(20.0)
        # Partially similar (noise 2.0 yields ~0.56 cosine similarity for seed 20)
        partial_emb = [v + 2.0 for v in q_emb]

        questions = [_question("帳務_010", "billing", "帳單怎麼列印", ["tenant"])]
        kb_items = [_kb_item("kb1", "帳單查詢", "帳單查詢的完整操作說明，不包含列印功能具體步驟。您可以在管理後台的帳務模組中查看帳單列表與明細資訊和狀態。", partial_emb)]

        mock_client = AsyncMock()
        mock_client.get_embeddings_batch = AsyncMock(return_value=[q_emb])

        with patch.object(analyzer, '_get_embedding_client', return_value=mock_client):
            report = await analyzer.analyze(questions, kb_items, [])

        assert len(report.gaps) >= 1
        gap = report.gaps[0]
        assert gap.topic_id == "帳務_010"
        assert gap.priority == "p0"
        assert gap.query_type == "static"
        # Should have similar_existing if any item had > 0 similarity
        if gap.similar_existing:
            assert gap.similar_existing[0].source_type == "kb"

    @pytest.mark.asyncio
    async def test_gap_recommendation_sop(self):
        """Uncovered question with SOP signals -> add_sop."""
        analyzer = CoverageAnalyzer(similarity_threshold=0.6, partial_threshold=0.4)
        q_emb = _make_embedding(21.0)

        questions = [_question("修繕_002", "repair", "如何操作報修申請流程", ["tenant"])]

        mock_client = AsyncMock()
        mock_client.get_embeddings_batch = AsyncMock(return_value=[q_emb])

        with patch.object(analyzer, '_get_embedding_client', return_value=mock_client):
            report = await analyzer.analyze(questions, [], [])

        assert len(report.gaps) == 1
        assert report.gaps[0].recommendation == "add_sop"

    @pytest.mark.asyncio
    async def test_gap_recommendation_kb(self):
        """Uncovered question with KB signals -> add_kb."""
        analyzer = CoverageAnalyzer(similarity_threshold=0.6, partial_threshold=0.4)
        q_emb = _make_embedding(22.0)

        questions = [_question("帳務_011", "billing", "帳單金額是什麼", ["tenant"])]

        mock_client = AsyncMock()
        mock_client.get_embeddings_batch = AsyncMock(return_value=[q_emb])

        with patch.object(analyzer, '_get_embedding_client', return_value=mock_client):
            report = await analyzer.analyze(questions, [], [])

        assert len(report.gaps) == 1
        assert report.gaps[0].recommendation == "add_kb"


# ---------------------------------------------------------------------------
# Test: export report (Req 3.3)
# ---------------------------------------------------------------------------

class TestExportReport:
    def test_export_creates_json(self):
        """export_report should write valid JSON with expected keys."""
        analyzer = CoverageAnalyzer()
        report = CoverageReport(
            total_questions=5,
            covered_by_kb=2,
            covered_by_sop=1,
            uncovered=1,
            partial_covered=1,
            needs_improvement=0,
            coverage_by_module={
                "billing": ModuleCoverage(module_id="billing", module_name="帳務管理", total=5, covered_by_kb=2),
            },
            coverage_by_role={
                "tenant": RoleCoverage(role="tenant", total=5, covered_by_kb=2),
            },
            gaps=[
                GapItem(
                    topic_id="帳務_003",
                    question="帳單怎麼列印",
                    gap_type="uncovered",
                    recommendation="add_kb",
                    query_type="static",
                    priority="p0",
                    similar_existing=[],
                ),
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "coverage_report.json"
            analyzer.export_report(report, out_path)

            assert out_path.exists()
            data = json.loads(out_path.read_text(encoding="utf-8"))
            assert data["total_questions"] == 5
            assert data["covered_by_kb"] == 2
            assert data["covered_by_sop"] == 1
            assert data["uncovered"] == 1
            assert "coverage_by_module" in data
            assert "coverage_by_role" in data
            assert "gaps" in data
            assert len(data["gaps"]) == 1
            assert data["gaps"][0]["topic_id"] == "帳務_003"


# ---------------------------------------------------------------------------
# Test: empty inputs
# ---------------------------------------------------------------------------

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_questions(self):
        """No questions -> empty report."""
        analyzer = CoverageAnalyzer()
        mock_client = AsyncMock()
        mock_client.get_embeddings_batch = AsyncMock(return_value=[])

        with patch.object(analyzer, '_get_embedding_client', return_value=mock_client):
            report = await analyzer.analyze([], [], [])

        assert report.total_questions == 0
        assert report.covered_by_kb == 0
        assert len(report.gaps) == 0

    @pytest.mark.asyncio
    async def test_no_kb_no_sop(self):
        """All questions uncovered when no KB/SOP items."""
        analyzer = CoverageAnalyzer()
        q_embs = [_make_embedding(float(i)) for i in range(2)]
        questions = [
            _question("帳務_001", "billing", "Q1", ["tenant"]),
            _question("修繕_001", "repair", "Q2", ["tenant"]),
        ]

        mock_client = AsyncMock()
        mock_client.get_embeddings_batch = AsyncMock(return_value=q_embs)

        with patch.object(analyzer, '_get_embedding_client', return_value=mock_client):
            report = await analyzer.analyze(questions, [], [])

        assert report.total_questions == 2
        assert report.uncovered == 2
        assert len(report.gaps) == 2

    @pytest.mark.asyncio
    async def test_items_without_embeddings(self):
        """KB/SOP items without pre-computed embeddings should get embeddings via client."""
        analyzer = CoverageAnalyzer(similarity_threshold=0.6, partial_threshold=0.4)
        q_emb = _make_embedding(30.0)
        kb_emb = _make_similar_embedding(q_emb, noise=0.01)

        questions = [_question("帳務_001", "billing", "怎麼查帳單", ["tenant"])]
        # KB item WITHOUT embedding
        kb_items = [_kb_item("kb1", "帳單查詢", "詳細的帳單查詢操作說明，確保使用者能順利操作系統完成帳單查詢。請先登入後進入帳務模組，即可查看各期帳單明細與狀態。", None)]

        mock_client = AsyncMock()
        # First call: question embeddings, second call: KB item embeddings
        mock_client.get_embeddings_batch = AsyncMock(side_effect=[[q_emb], [kb_emb]])

        with patch.object(analyzer, '_get_embedding_client', return_value=mock_client):
            report = await analyzer.analyze(questions, kb_items, [])

        assert report.covered_by_kb == 1
        # Verify get_embeddings_batch was called for KB items too
        assert mock_client.get_embeddings_batch.call_count == 2
