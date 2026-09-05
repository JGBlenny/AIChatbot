"""unit：`tools/agent_outline_dump.py`（spec agentic-mcp-orchestration 任務 3.5）。

假 `OutlineDoc`／`RowMeta`，離線、不接觸真 DB——與 `test_outline_unit_req.py`
同一原則：不呼叫 `build_prospect_outline`，只測本檔的純渲染／判準函式。
"""
from __future__ import annotations

import pytest

from services.agent.outline import OutlineDoc, OutlineSection
from tools.agent_outline_dump import RowMeta, classify_alias, render_markdown

pytestmark = pytest.mark.unit

_SPEC = "agentic-mcp-orchestration:3.5"


def _make_doc(sections: list[OutlineSection]) -> OutlineDoc:
    text = "\n".join(s.text for s in sections)
    return OutlineDoc(
        audience="prospect",
        version="2026-09-05T00:00:00+00:00",
        sha256="deadbeef" * 8,
        token_count=42,
        sections=sections,
        text=text,
        token_count_approx=False,
    )


def _row(
    id_: int,
    answer: str = "答案內容",
    categories=("售前模組",),
    generation_metadata=None,
    question_summary: str = "問題摘要",
) -> RowMeta:
    return RowMeta(
        id=id_,
        question_summary=question_summary,
        answer=answer,
        categories=list(categories) if categories else None,
        target_user=["prospect"],
        business_types=["system_provider"],
        outline_approved_by="owner-20260905",
        generation_metadata=generation_metadata or {},
    )


class TestRenderHeader:
    def test_header_has_version_sha_token_count(self):
        doc = _make_doc(
            [OutlineSection(id="outline:listing", title="房源", text="body", source_ids=[1], citable=True)]
        )
        row_meta = {1: _row(1)}
        md = render_markdown(
            doc,
            row_meta,
            git_head="abc123",
            generated_at="2026-09-05T00:00:00+00:00",
            batch_question_summaries=set(),
        )
        assert "version: 2026-09-05T00:00:00+00:00" in md
        assert f"sha256: {doc.sha256}" in md
        assert "token_count: 42" in md
        assert "git_head: abc123" in md

    def test_source_row_fields_rendered(self):
        doc = _make_doc(
            [OutlineSection(id="outline:listing", title="房源", text="body", source_ids=[1], citable=True)]
        )
        row_meta = {1: _row(1, answer="完整答案全文")}
        md = render_markdown(
            doc, row_meta, git_head="x", generated_at="t", batch_question_summaries=set()
        )
        assert "### kb 1" in md
        assert "question_summary: 問題摘要" in md
        assert "outline_approved_by: owner-20260905" in md
        assert "完整答案全文" in md


class TestAliasClassificationMarker:
    def test_marker_key_present_true_value_is_alias(self):
        row = _row(1, generation_metadata={"entry_alias": True})
        kind, reason = classify_alias(row, {1: row}, set())
        assert kind == "alias"
        assert reason.startswith("marker:")


class TestAliasClassificationBatchFile:
    def test_question_summary_in_batch_file_is_alias(self):
        row = _row(2, question_summary="費用怎麼算 一年多少錢 收費方式 月費 年費 要花多少")
        kind, reason = classify_alias(row, {2: row}, {row.question_summary})
        assert kind == "alias"
        assert reason == "batch_file"


class TestAliasClassificationDuplicateAnswer:
    def test_exact_duplicate_answer_is_alias(self):
        a = _row(3, answer="一模一樣的答案內容", question_summary="問法一")
        b = _row(4, answer="一模一樣的答案內容", question_summary="問法二")
        kind, reason = classify_alias(a, {3: a, 4: b}, set())
        assert kind == "alias"
        assert "duplicate_answer:4" in reason

    def test_prefix_similarity_duplicate_is_alias(self):
        long_answer = "這是一段很長的來源答案內容用來測試前綴相似度判準是否正確運作" * 2
        a = RowMeta(
            id=5,
            question_summary="問法甲",
            answer=long_answer,
            categories=["售前模組"],
            target_user=["prospect"],
            business_types=["system_provider"],
            outline_approved_by="owner-20260905",
            generation_metadata={},
        )
        b = RowMeta(
            id=6,
            question_summary="問法乙",
            answer=long_answer[:-2] + "XX",  # 幾乎相同，尾端兩字不同
            categories=["售前模組"],
            target_user=["prospect"],
            business_types=["system_provider"],
            outline_approved_by="owner-20260905",
            generation_metadata={},
        )
        kind, reason = classify_alias(a, {5: a, 6: b}, set())
        assert kind == "alias"
        assert "duplicate_answer:6" in reason

    def test_no_signal_and_has_categories_is_topic(self):
        row = _row(7, answer="獨立不重複的答案", categories=["售前模組"])
        kind, reason = classify_alias(row, {7: row}, set())
        assert kind == "topic"

    def test_no_signal_and_no_categories_is_unknown(self):
        row = _row(8, answer="沒有分類的舊列答案", categories=None)
        kind, reason = classify_alias(row, {8: row}, set())
        assert kind == "unknown"
        assert reason == "no_categories"


class TestSuggestedSqlOnlyWhenAliasExists:
    def test_sql_present_when_alias_found(self):
        doc = _make_doc(
            [OutlineSection(id="outline:listing", title="房源", text="body", source_ids=[9], citable=True)]
        )
        row_meta = {9: _row(9, generation_metadata={"entry_alias": True})}
        md = render_markdown(
            doc, row_meta, git_head="x", generated_at="t", batch_question_summaries=set()
        )
        assert "UPDATE knowledge_base SET outline_approved_by=NULL" in md
        assert "WHERE id IN (9)" in md

    def test_sql_absent_when_no_alias(self):
        doc = _make_doc(
            [OutlineSection(id="outline:listing", title="房源", text="body", source_ids=[10], citable=True)]
        )
        row_meta = {10: _row(10, categories=["售前模組"])}
        md = render_markdown(
            doc, row_meta, git_head="x", generated_at="t", batch_question_summaries=set()
        )
        assert "UPDATE knowledge_base" not in md
        assert "無建議取消標記 SQL" in md


class TestNoMeteringOrNonceLeakage:
    def test_output_excludes_nonce_and_metering_terms(self):
        doc = _make_doc(
            [OutlineSection(id="outline:listing", title="房源", text="body", source_ids=[11], citable=True)]
        )
        row_meta = {11: _row(11)}
        md = render_markdown(
            doc, row_meta, git_head="x", generated_at="t", batch_question_summaries=set()
        )
        lowered = md.lower()
        assert "nonce" not in lowered
        assert "metering" not in lowered
