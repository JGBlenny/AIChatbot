"""unit:錯位直答相關性把關（51 題全面抽驗逼出）。

根因：分數＝0.1×向量＋0.9×rerank，reranker 對表面詞彙重疊的無關知識打 0.9+
（實例：「電表度數登記錯誤怎麼改」top1=「租客看即時電表」0.956）——任何分數
閾值都切不開。修法：直答前對 top1 做一次輕量 LLM 相關性判定，不相關讓次筆
晉位（最多查 2 筆），全不相關回空列走誠實 fallback。
豁免：表單/API 觸發列不判（不擋表單）；raw 向量 ≥0.85 視為近精確命中跳過
（省延遲）；LLM 失敗放行（不阻斷服務）。
"""
import pytest
from unittest.mock import patch

pytestmark = pytest.mark.unit


def _row(id, summary="知識", answer="內容", vec=0.6, **over):
    r = {"id": id, "question_summary": summary, "answer": answer,
         "vector_similarity": vec, "similarity": 0.9, "action_type": "direct_answer"}
    r.update(over)
    return r


async def _gate(rows, verdicts, q="問題"):
    """verdicts: 依呼叫順序回覆的 LLM 判定串（'YES'/'NO'/Exception）。"""
    from routers import chat as chat_mod
    calls = {"n": 0}

    def fake_completion(**kwargs):
        v = verdicts[min(calls["n"], len(verdicts) - 1)]
        calls["n"] += 1
        if isinstance(v, Exception):
            raise v
        return {"content": v}
    with patch.object(chat_mod, "chat_completion", side_effect=lambda **kw: fake_completion(**kw)):
        out = await chat_mod._top1_relevance_gate(q, rows)
    return out, calls["n"]


async def test_relevant_top1_passes_through():
    rows = [_row(1), _row(2)]
    out, n = await _gate(rows, ["YES"])
    assert [k["id"] for k in out] == [1, 2] and n == 1


async def test_irrelevant_top1_promotes_next():
    rows = [_row(1, summary="租客看即時電表"), _row(2, summary="帳單編輯 修改度數")]
    out, n = await _gate(rows, ["NO", "YES"])
    assert [k["id"] for k in out] == [2] and n == 2


async def test_all_irrelevant_returns_empty_for_honest_fallback():
    rows = [_row(1), _row(2), _row(3)]
    out, _ = await _gate(rows, ["NO", "NO"])
    assert out == []                      # 最多查 2 筆，全 NO → 空列走 fallback


async def test_high_vector_similarity_skips_gate():
    rows = [_row(1, vec=0.9)]
    out, n = await _gate(rows, ["NO"])    # 即使 LLM 會說 NO 也不該被呼叫
    assert [k["id"] for k in out] == [1] and n == 0


async def test_form_trigger_rows_not_gated():
    rows = [_row(1, answer="", action_type="form_fill", form_id="f1")]
    out, n = await _gate(rows, ["NO"])
    assert [k["id"] for k in out] == [1] and n == 0


async def test_llm_failure_fails_open():
    rows = [_row(1)]
    out, _ = await _gate(rows, [RuntimeError("llm down")])
    assert [k["id"] for k in out] == [1]  # 失敗放行不阻斷


async def test_disabled_by_env(monkeypatch):
    from routers import chat as chat_mod
    monkeypatch.setenv("RELEVANCE_GATE_ENABLED", "false")
    rows = [_row(1)]
    with patch.object(chat_mod, "chat_completion") as mock_cc:
        out = await chat_mod._top1_relevance_gate("q", rows)
    assert [k["id"] for k in out] == [1] and not mock_cc.called
