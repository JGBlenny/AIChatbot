"""H 留出題守護的 unit 收編（目標驗收規格 2026-10-04 §2.4、Plan 9.27）。

`scripts/audit/checks/goal_eval_holdout_guard.py` 對真題的掃描只在主機跑（題目原文在 repo 外）；
本檔 ⛔ 讀 `~/jgb-archive`，只用合成題與合成正本，驗比對規則、基準扣除與大聲失敗。
"""
import importlib.util
import json
import os

import pytest

pytestmark = pytest.mark.unit

_SPEC = "knowledge-outline-and-intent-architecture:plan-9.27"

_REPO_ROOT = os.path.dirname(  # repo/
    os.path.dirname(  # rag-orchestrator/
        os.path.dirname(  # tests/
            os.path.dirname(  # tests/unit/
                os.path.dirname(os.path.abspath(__file__))  # tests/unit/audit/
            )
        )
    )
)
_GUARD_PY = os.path.join(_REPO_ROOT, "scripts", "audit", "checks", "goal_eval_holdout_guard.py")


@pytest.fixture(scope="module")
def g():
    assert os.path.exists(_GUARD_PY), f"{_GUARD_PY} 不存在——守護檔案位置變了"
    spec = importlib.util.spec_from_file_location("goal_eval_holdout_guard", _GUARD_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


Q = {"qa": "請問合約到期之後押金多久會退還給租客呢", "qb": "帳單逾期未繳的滯納金要怎麼設定比較好"}


def _env(g, tmp_path, fines, baseline=None):
    os.makedirs(tmp_path, exist_ok=True)
    return g._mk_env(str(tmp_path), Q, fines, baseline)


@pytest.mark.req(_SPEC)
def test_self_test_passes(g):
    """⛔ 這條紅了代表守護本身壞了，其餘結果不可信。"""
    assert g.self_test() == 0


@pytest.mark.req(_SPEC)
def test_fragment_in_title_and_body_fail(g, tmp_path):
    frag_a = g.norm(Q["qa"])[4:4 + g.MINLEN]
    frag_b = g.norm(Q["qb"])[1:1 + g.MINLEN]
    fines = [g._fine("t1", title="說" + frag_a + "明"), g._fine("b1", body=("內文" + frag_b + "。",))]
    rc, out = g.run(*_env(g, tmp_path, fines))
    assert rc == 1
    assert any(x.startswith("HIT qa × t1 × title × 8") for x in out)
    assert any(x.startswith("HIT qb × b1 × body × 8") for x in out)


@pytest.mark.req(_SPEC)
def test_whole_sentence_in_phrasing_fails_via_hash(g, tmp_path):
    rc, out = g.run(*_env(g, tmp_path, [g._fine("p1", phr=("帳單逾期未繳的滯納金要怎麼設定比較好？",))]))
    assert rc == 1
    assert any("qb × p1 × phrasing × hash" in x for x in out)


@pytest.mark.req(_SPEC)
def test_baseline_allows_only_exact_triple(g, tmp_path):
    frag_a = g.norm(Q["qa"])[4:4 + g.MINLEN]
    fines = [g._fine("t1", title="說" + frag_a + "明")]
    allow = [{"qid": "qa", "fine_id": "t1", "field": "title"}]
    rc, _ = g.run(*_env(g, tmp_path / "ok", fines, allow))
    assert rc == 0
    fines2 = [g._fine("t1", title="說" + frag_a + "明", body=("又" + frag_a + "。",))]
    rc2, out2 = g.run(*_env(g, tmp_path / "body", fines2, allow))
    assert rc2 == 1 and any("qa × t1 × body" in x for x in out2)


@pytest.mark.req(_SPEC)
def test_missing_or_mismatched_questions_fail_loudly(g, tmp_path):
    fz, qp, cg, bp = _env(g, tmp_path, [g._fine("f0")])
    assert g.run(fz, qp + ".missing", cg, bp)[0] == 2
    with open(qp, "a", encoding="utf-8") as f:
        f.write(" ")
    rc, out = g.run(fz, qp, cg, bp)
    assert rc == 2 and "sha256 不符" in out[0]
    fz2, qp2, _, bp2 = _env(g, tmp_path / "x", [g._fine("f0")])
    assert g.run(fz2, qp2, str(tmp_path / "none" / "*.json"), bp2)[0] == 2


@pytest.mark.req(_SPEC)
def test_output_never_contains_question_text(g, tmp_path):
    frag_a = g.norm(Q["qa"])[4:4 + g.MINLEN]
    rc, out = g.run(*_env(g, tmp_path, [g._fine("t1", title="說" + frag_a + "明")]))
    assert rc == 1
    joined = g.norm("".join(out))
    for q in Q.values():
        t = g.norm(q)
        assert not any(t[i:i + g.MINLEN] in joined for i in range(len(t) - g.MINLEN + 1))


@pytest.mark.req(_SPEC)
def test_freeze_file_has_196_ids_and_no_text(g):
    """凍結檔（repo 內）只有 id／雜湊／計數：196 題、holdout 99、material 97、業者 193、售前 3。"""
    with open(g.DEFAULT_FREEZE, encoding="utf-8") as f:
        fz = json.load(f)
    items = fz["items"]
    assert len(items) == 196
    assert sum(i["split"] == "holdout" for i in items) == 99
    assert sum(i["audience"] == "property_manager" for i in items) == 193
    assert "ce2ce3372c6e" not in {i["id"] for i in items}
    assert all(set(i) == {"id", "split", "audience", "form", "q_sha256"} for i in items)
