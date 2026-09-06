"""任務 2.2：similar_items.py（細目相似**待審清單**，⛔ 永不合併）。"""
import importlib.util
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:2.2")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))  # 容器內＝/（.claude 掛在 /.claude）
_SCRIPTS = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts")
_SCHEMAS = os.path.join(_REPO, ".claude", "skills", "outline-curation", "schemas")


def _load(name):
    path = os.path.join(_SCRIPTS, f"{name}.py")
    if not os.path.exists(path):
        pytest.skip(f"{name}.py 不在掛載路徑")
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


FINES = [
    {"id": "prospect/C/contract-esign", "coarse_id": "C", "title": "線上電子簽約流程",
     "merge_of": [], "split_from": [], "moved_from": [], "reason": "r", "slug": "contract-esign"},
    {"id": "prospect/C/contract-esign-flow", "coarse_id": "C", "title": "線上電子簽約流程說明",
     "merge_of": [], "split_from": [], "moved_from": [], "reason": "r", "slug": "contract-esign-flow"},
    {"id": "prospect/D/pricing", "coarse_id": "D", "title": "怎麼收費與報價",
     "merge_of": [], "split_from": [], "moved_from": [], "reason": "r", "slug": "pricing"},
]


def _structure(tmp_path):
    p = tmp_path / "structure-proposal.json"
    p.write_text(json.dumps({
        "step": "structure", "skill_version": "0.1.0", "inputs_sha": {}, "deterministic": False,
        "raw_outputs_path": None, "cost": {},
        "payload": {"proposals": [], "synthesis": {"angle": "synthesis", "coarses": [], "fines": FINES,
                                                   "id_map": [], "rejected_alternatives": []}},
    }, ensure_ascii=False), encoding="utf-8")
    return str(p)


def _phrasing_map(tmp_path):
    p = tmp_path / "phrasing-map.json"
    p.write_text(json.dumps({
        "step": "phrasing", "skill_version": "0.1.0", "inputs_sha": {}, "deterministic": True,
        "raw_outputs_path": None, "cost": {},
        "payload": {"phrasings": [
            {"fine_id": "prospect/C/contract-esign", "text": "電子簽約", "source": "koyu:a#1",
             "status": "proposed", "score": 0.5},
            {"fine_id": "prospect/D/pricing", "text": "多少錢", "source": "koyu:b#1",
             "status": "proposed", "score": 0.5},
        ], "similar_pairs": []},
    }, ensure_ascii=False), encoding="utf-8")
    return str(p)


def test_pairs_above_threshold_only(tmp_path):
    si = _load("similar_items")
    payload = si.build(_structure(tmp_path), None, threshold=0.30)
    pairs = payload["similar_pairs"]
    assert {(p["a"], p["b"]) for p in pairs} == {("prospect/C/contract-esign", "prospect/C/contract-esign-flow")}
    assert all(p["score"] >= 0.30 for p in pairs)

    # 正對照：門檻降到 0 時，3 個細目的 3 組配對全都要出現（否則上面的「只有一組」是掃描器壞了）
    all_pairs = si.build(_structure(tmp_path), None, threshold=0.0)["similar_pairs"]
    assert len(all_pairs) == 3
    # 負對照：門檻拉到 1.01 一組都不該有
    assert si.build(_structure(tmp_path), None, threshold=1.01)["similar_pairs"] == []


def test_pairs_are_sorted_and_unique(tmp_path):
    si = _load("similar_items")
    pairs = si.build(_structure(tmp_path), None, threshold=0.0)["similar_pairs"]
    assert pairs == sorted(pairs, key=lambda p: (-p["score"], p["a"], p["b"]))
    assert all(p["a"] < p["b"] for p in pairs), "a<b、⛔ 不自比、⛔ 不重複"
    assert len({(p["a"], p["b"]) for p in pairs}) == len(pairs)


def test_never_merges_anything(tmp_path):
    """只出清單：輸入的 structure 不得被改，輸出也不得帶任何合併語義的欄位。"""
    si = _load("similar_items")
    struct = _structure(tmp_path)
    before = open(struct, "rb").read()
    payload = si.build(struct, None, threshold=0.0)
    assert open(struct, "rb").read() == before
    for p in payload["similar_pairs"]:
        assert set(p) == {"a", "b", "score", "method"}
    assert "id_map" not in payload and "fines" not in payload and "merge_of" not in json.dumps(payload)


def test_lexical_fallback_when_no_env_var(tmp_path, monkeypatch):
    monkeypatch.delenv("EMBEDDING_API_URL", raising=False)
    si = _load("similar_items")
    out = tmp_path / "similar-items.json"
    r = subprocess.run([sys.executable, os.path.join(_SCRIPTS, "similar_items.py"),
                        "--structure", _structure(tmp_path), "--out", str(out)],
                       capture_output=True, text=True, env={k: v for k, v in os.environ.items()
                                                            if k != "EMBEDDING_API_URL"})
    assert r.returncode == 0, r.stderr
    env = json.loads(out.read_text(encoding="utf-8"))
    assert env["payload"]["params"]["method"] == si.LEXICAL_METHOD
    assert env["deterministic"] is True
    for p in env["payload"]["similar_pairs"]:
        assert p["method"] == si.LEXICAL_METHOD
    assert "EMBEDDING_API_URL" not in r.stdout and "http" not in r.stdout, "⛔ 不得印出 URL 或環境變數"


def test_merges_phrasing_map_into_payload(tmp_path):
    si = _load("similar_items")
    pm_path = _phrasing_map(tmp_path)
    merged = si.build(_structure(tmp_path), pm_path, threshold=0.0, merge_phrasings=True)
    assert len(merged["phrasings"]) == 2 and merged["params"]["merged_phrasing_map"] is True
    plain = si.build(_structure(tmp_path), pm_path, threshold=0.0, merge_phrasings=False)
    assert plain["phrasings"] == []
    # profile 含講法 ⇒ 分數會變（講法確實有被讀進去，不是掛著好看）
    without = si.build(_structure(tmp_path), None, threshold=0.0)["similar_pairs"]
    assert [p["score"] for p in merged["similar_pairs"]] != [p["score"] for p in without]


def test_envelope_schema_and_determinism(tmp_path):
    si = _load("similar_items")
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    env_no_url = {k: v for k, v in os.environ.items() if k != "EMBEDDING_API_URL"}
    struct = _structure(tmp_path)
    for out in (a, b):
        r = subprocess.run([sys.executable, os.path.join(_SCRIPTS, "similar_items.py"),
                            "--structure", struct, "--phrasing-map", _phrasing_map(tmp_path),
                            "--threshold", "0.0", "--out", str(out)],
                           capture_output=True, text=True, env=env_no_url)
        assert r.returncode == 0, r.stderr
    assert a.read_bytes() == b.read_bytes()
    doc = json.loads(a.read_text(encoding="utf-8"))
    assert doc["step"] == "phrasing"
    si._env.validate(doc, si._env.load_schema(os.path.join(_SCHEMAS, "phrasing-map.json")))
