"""unit：retrieval semantic contract（D1）與 scoring surface 單一實作（D2/D3）。

⚠️ **本檔刻意不手寫 `{"generation_metadata": {...}}` 作為主要證據**。
   P1f 的 23 條單元測試全過卻在 production 全數失效，正因為它們餵的是
   production **從不產生**的形狀（A03 抓到）。這裡的 row 一律先過
   `VendorKnowledgeRetrieverV2._format_result`，也就是 production 真正的 producer。

涵蓋：
  1. transport：DB 列 → producer → 契約欄位確實存在（⛔ 不是 fixture 自帶）
  2. 授權：proposal provenance ⛔ 不得被當成 declared surface
  3. 降級：未 migrate 的 row 必須落 legacy summary 且**被標記**（可計數）
  4. payload：reranker 送出的候選必帶 surface 與 source
"""
import pytest

from services.retrieval_representation import (
    SURFACE_FIELD,
    SURFACE_SOURCE_DECLARED,
    SURFACE_SOURCE_EMPTY,
    SURFACE_SOURCE_FIELD,
    SURFACE_SOURCE_LEGACY_SUMMARY,
    PROPOSAL_SOURCE,
    is_authoritative,
    retrieval_representation,
    scoring_surface,
)
from services.semantic_reranker import SemanticReranker
from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2

pytestmark = pytest.mark.unit

REVIEWED = "reviewed_product_declaration"


def _db_row(**over):
    """**SQL projection 的形狀**——欄位名與 retriever 的 SELECT 別名一致。

    ⚠️ 這是 producer 的**輸入**；測試斷言的是 producer 的**輸出**。
    """
    row = {
        "id": 4656,
        "question_summary": "查帳單 帳單編號查詢",
        "answer": "",
        "content": "",
        "retrieval_representation": None,
        "retrieval_representation_source": None,
    }
    row.update(over)
    return row


def _produced(**over):
    return VendorKnowledgeRetrieverV2._format_result(
        VendorKnowledgeRetrieverV2.__new__(VendorKnowledgeRetrieverV2), _db_row(**over)
    )


# ───────────────────────── 1. transport 真的存在 ─────────────────────────

@pytest.mark.req("D1:transport")
def test_producer_actually_emits_contract_fields():
    """⚠️ 這條就是 A03 逼出來的：契約存在、consumer 接好，但 producer 不吐欄位。"""
    out = _produced()
    assert "retrieval_representation" in out
    assert "retrieval_representation_source" in out


@pytest.mark.req("D1:transport")
def test_declared_row_survives_producer():
    out = _produced(retrieval_representation="找出並查詢某一筆帳單目前的狀態",
                    retrieval_representation_source=REVIEWED)
    assert retrieval_representation(out) == "找出並查詢某一筆帳單目前的狀態"
    assert is_authoritative(out) is True


# ───────────────────────── 2. 授權：proposal 不算 ─────────────────────────

@pytest.mark.req("D3:reviewed-only")
def test_proposal_is_not_consumable():
    """⛔ machine-generated proposal 不得進 scoring——D3 的核心。"""
    out = _produced(retrieval_representation="機器產生的提案文字",
                    retrieval_representation_source=PROPOSAL_SOURCE)
    assert is_authoritative(out) is False
    text, src = scoring_surface(out)
    assert src == SURFACE_SOURCE_LEGACY_SUMMARY
    assert text == "查帳單 帳單編號查詢"


@pytest.mark.req("D3:reviewed-only")
def test_declared_text_without_provenance_is_not_consumable():
    """有文字、沒 provenance ⇒ ⛔ 不得採用（來源不明等同未審）。"""
    out = _produced(retrieval_representation="來源不明的文字")
    assert is_authoritative(out) is False
    assert scoring_surface(out)[1] == SURFACE_SOURCE_LEGACY_SUMMARY


# ───────────────────────── 3. 降級必須被標記 ─────────────────────────

@pytest.mark.req("D2:single-surface")
def test_unmigrated_row_falls_back_and_is_counted():
    text, src = scoring_surface(_produced())
    assert (text, src) == ("查帳單 帳單編號查詢", SURFACE_SOURCE_LEGACY_SUMMARY)


@pytest.mark.req("D2:single-surface")
def test_reviewed_row_uses_declared_surface():
    out = _produced(retrieval_representation="查詢某一筆帳單是否已繳費、已寄出或仍為草稿",
                    retrieval_representation_source=REVIEWED)
    text, src = scoring_surface(out)
    assert src == SURFACE_SOURCE_DECLARED
    assert text == "查詢某一筆帳單是否已繳費、已寄出或仍為草稿"


@pytest.mark.req("D2:single-surface")
def test_empty_row_is_loud_not_silent():
    """⚠️ 連 summary 都沒有時回 `empty`，⛔ 不得偽裝成正常降級。"""
    assert scoring_surface(_produced(question_summary=""))[1] == SURFACE_SOURCE_EMPTY


@pytest.mark.req("D1:no-fallback")
def test_reader_never_guesses():
    """⛔ 讀取器不得把 summary 當成宣告——這是契約與降級的分界。"""
    assert retrieval_representation(_produced()) is None


# ───────────────────────── 4. payload 帶得出去 ─────────────────────────

@pytest.mark.req("D2:single-surface")
def test_reranker_payload_carries_surface_and_source(monkeypatch):
    captured = {}

    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {"results": []}

    def _fake_post(url, json=None, timeout=None):
        captured["body"] = json
        return _Resp()

    r = SemanticReranker.__new__(SemanticReranker)
    r.semantic_api_url = "http://stub"
    r.is_available = True
    monkeypatch.setattr("services.semantic_reranker.use_httpx", False, raising=False)
    monkeypatch.setattr("services.semantic_reranker.requests",
                        type("M", (), {"post": staticmethod(_fake_post)}), raising=False)

    reviewed = _produced(retrieval_representation="宣告文字",
                         retrieval_representation_source=REVIEWED)
    r.rerank("那筆帳單繳了沒", [reviewed, _produced(id=3406)], top_k=5)

    cands = captured["body"]["candidates"]
    assert [c[SURFACE_FIELD] for c in cands] == ["宣告文字", "查帳單 帳單編號查詢"]
    assert [c[SURFACE_SOURCE_FIELD] for c in cands] == [
        SURFACE_SOURCE_DECLARED, SURFACE_SOURCE_LEGACY_SUMMARY,
    ]
    # ⚠️ 舊欄位必須照舊送——api_server 對沒有 surface 的舊 client 仍需維持原優先序
    assert all("question_summary" in c and "answer" in c for c in cands)
