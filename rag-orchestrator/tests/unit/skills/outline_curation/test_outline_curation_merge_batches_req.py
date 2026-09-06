"""merge_answerability_batches.py：分批合併的決定性與門檻一致性。"""
import importlib.util, os, pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:1.5")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))  # 容器內＝/（.claude 掛在 /.claude）
_SCRIPT = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts", "merge_answerability_batches.py")


def _mod():
    if not os.path.exists(_SCRIPT):
        pytest.skip("merge script 不在掛載路徑")
    spec = importlib.util.spec_from_file_location("merge_ab", _SCRIPT)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def _v(label, fine="tmp:kb:1"):
    return {"label": label, "fine_id": fine, "evidence_unit": 1, "confidence": "high", "provisional": True}


def _batch(entries, agree, agents, **head):
    base = {"step": "answerability", "frozenAt": "2026-09-06T00:00:00Z", "rubricSha": "r", "inputsSha": {"a": "1"}}
    base.update(head)
    return {**base, "labels": entries, "total": len(entries), "agree": agree, "agentsUsed": agents}


def test_merge_sums_and_threshold_matches_workflow():
    m = _mod()
    b1 = _batch([{"cell_id": "C02", "label": "answerable", "verdicts": [_v("answerable"), _v("answerable")]},
                 {"cell_id": "C01", "label": "partial", "verdicts": [_v("partial", "tmp:kb:1"), _v("partial", "tmp:kb:2")]}], 2, 4)
    b2 = _batch([{"cell_id": "C03", "label": "no_source", "unresolved": True,
                  "verdicts": [_v("partial"), _v("answerable"), _v("no_source")]}], 0, 3)
    r = m.merge([b1, b2])
    assert [e["cell_id"] for e in r["labels"]] == ["C01", "C02", "C03"]
    assert (r["total"], r["agree"], r["agentsUsed"]) == (3, 2, 7)
    assert r["agreementRate"] == pytest.approx(2 / 3) and r["needs_rubric_revision"] is True
    assert r["fineIdAgreement"] == {"pairs": 2, "agree": 1, "rate": 0.5}
    assert r["unresolved"] == ["C03"] and r["labelCounts"]["no_source"] == 1


def test_merge_rejects_mismatched_freeze():
    m = _mod()
    with pytest.raises(SystemExit):
        m.merge([_batch([], 0, 0), _batch([], 0, 0, rubricSha="other")])


def test_merge_rejects_duplicate_cells():
    m = _mod()
    e = {"cell_id": "C01", "label": "partial", "verdicts": [_v("partial"), _v("partial")]}
    with pytest.raises(SystemExit):
        m.merge([_batch([e], 1, 2), _batch([e], 1, 2)])
