"""任務 2.3：structure_propose.py（prepare／validate／synth-prompt／package，子代理執行、⛔ 不打 API）＋ apply_proposal.py（決定性套用）。"""
import copy
import importlib.util
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:2.3")]

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


KB = {"rows": [  # 欄位形狀同 inputs/prospect-kb-rows-20260906.json（白名單投影會擋未知欄位）
    {"kb_id": 2, "question_summary": "收租對帳 自動", "answer": "帳單自動產生。收租可線上對帳。", "business_types": ["system_provider"], "categories": ["售前顧問"], "target_user": ["prospect"], "outline_approved_by": "owner"},
    {"kb_id": 1, "question_summary": "系統介紹", "answer": "金箍棒把物件、合約、收租集中管理。", "business_types": ["system_provider"], "categories": ["售前顧問"], "target_user": ["prospect"], "outline_approved_by": "owner"},
]}
DRAFTS = {"knowledge": [{"question": "可以試用嗎", "answer": "可先免費試用一個月。", "instance_applicability": "general"}]}
COARSES = {"audience": "prospect", "coarses": [{"id": "A", "title": "產品基本盤"}, {"id": "C", "title": "六大模組"}, {"id": "D", "title": "方案試用"}]}


def _inputs(tmp_path):
    kb, dr, co = tmp_path / "kb.json", tmp_path / "drafts.json", tmp_path / "coarses.json"
    kb.write_text(json.dumps(KB, ensure_ascii=False), encoding="utf-8")
    dr.write_text(json.dumps(DRAFTS, ensure_ascii=False), encoding="utf-8")
    co.write_text(json.dumps(COARSES, ensure_ascii=False), encoding="utf-8")
    return str(kb), str(dr), str(co)


def _proposal(angle="user_question_path"):
    return {
        "angle": angle,
        "coarses": copy.deepcopy(COARSES["coarses"]),
        "fines": [
            {"id": "prospect/A/positioning", "coarse_id": "A", "title": "系統定位", "slug": "positioning",
             "merge_of": ["tmp:kb:1"], "split_from": [], "moved_from": [], "reason": "定位問題獨立成題"},
            {"id": "prospect/C/rent-collection", "coarse_id": "C", "title": "收租對帳", "slug": "rent-collection",
             "merge_of": ["tmp:kb:2"], "split_from": [], "moved_from": [], "reason": "帳務模組"},
            {"id": "prospect/D/trial", "coarse_id": "D", "title": "免費試用", "slug": "trial",
             "merge_of": ["tmp:draft:1"], "split_from": [], "moved_from": [], "reason": "試用獨立"},
        ],
        "id_map": [{"old": "tmp:kb:1", "new": "prospect/A/positioning", "op": "keep"},
                   {"old": "tmp:kb:2", "new": "prospect/C/rent-collection", "op": "keep"},
                   {"old": "tmp:draft:1", "new": "prospect/D/trial", "op": "keep"}],
    }


def _synthesis():
    return {**_proposal("synthesis"), "rejected_alternatives": [{"alternative": "把試用併進定位", "reason": "問法不同"}]}


def _run(args, cwd=None):
    return subprocess.run([sys.executable, os.path.join(_SCRIPTS, args[0])] + args[1:], capture_output=True, text=True, cwd=cwd or _REPO)


# ---------------------------------------------------------------------------
# structure_propose
# ---------------------------------------------------------------------------

def test_prepare_writes_three_byte_stable_prompts_without_examples(tmp_path):
    kb, dr, co = _inputs(tmp_path)
    out = tmp_path / "raw"
    r1 = _run(["structure_propose.py", "prepare", "--kb-rows", kb, "--drafts", dr, "--coarses", co, "--out-dir", str(out)])
    assert r1.returncode == 0, r1.stderr
    m1 = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert set(m1["prompts"]) == {"user_question_path", "content_boundary", "audience_level"} and m1["items"] == 3
    texts = {k: open(v["path"], encoding="utf-8").read() for k, v in m1["prompts"].items()}
    for k, t in texts.items():
        assert "tmp:kb:1" in t and "tmp:draft:1" in t and "⛔ 不得增刪改" in t and k in t
        assert "例如" not in t and "例：" not in t  # 只寫定義不寫例子
        assert "score" not in t and "similarity" not in t  # 白名單投影：無分數
    # 逐位元穩定：再跑一次 sha 相同
    r2 = _run(["structure_propose.py", "prepare", "--kb-rows", kb, "--drafts", dr, "--coarses", co, "--out-dir", str(tmp_path / "raw2")])
    m2 = json.loads((tmp_path / "raw2" / "manifest.json").read_text(encoding="utf-8"))
    assert {k: v["sha256"] for k, v in m1["prompts"].items()} == {k: v["sha256"] for k, v in m2["prompts"].items()}
    # 三個角度的 prompt 互不相同（角度定義不同）
    assert len({v["sha256"] for v in m1["prompts"].values()}) == 3


def test_validate_accepts_good_and_rejects_each_rule(tmp_path):
    m = _load("structure_propose")
    kb, dr, co = _inputs(tmp_path)
    out = tmp_path / "raw"
    assert _run(["structure_propose.py", "prepare", "--kb-rows", kb, "--drafts", dr, "--coarses", co, "--out-dir", str(out)]).returncode == 0
    good = tmp_path / "good.json"
    good.write_text("```json\n" + json.dumps(_proposal(), ensure_ascii=False) + "\n```", encoding="utf-8")  # 圍欄也接受
    r = _run(["structure_propose.py", "validate", "--kb-rows", kb, "--drafts", dr, "--coarses", co, "--out-dir", str(out), "--proposal", str(good)])
    assert r.returncode == 0, r.stderr
    ids, cids = {"tmp:kb:1", "tmp:kb:2", "tmp:draft:1"}, {"A", "C", "D"}
    titles = {c["id"]: c["title"] for c in COARSES["coarses"]}

    def errs(mut):
        p = _proposal(); mut(p)
        return m.validate_proposal(p, "prospect", cids, ids, titles)

    assert errs(lambda p: p["id_map"].pop()) and any("未覆蓋" in e for e in errs(lambda p: p["id_map"].pop()))
    assert any("不合規" in e for e in errs(lambda p: p["fines"][0].update(id="prospect/A/Bad_Slug", slug="Bad_Slug")))
    assert any("coarse_id" in e for e in errs(lambda p: p["fines"][0].update(coarse_id="Z", id="prospect/Z/positioning")))
    assert any("未知項目" in e for e in errs(lambda p: p["fines"][0]["merge_of"].append("tmp:kb:99")))
    assert any("不存在的細目" in e for e in errs(lambda p: p["id_map"][0].update(new="prospect/A/nope")))
    assert any("title 被改" in e for e in errs(lambda p: p["coarses"][0].update(title="改名")))
    assert any("重複" in e for e in errs(lambda p: p["fines"].append(dict(p["fines"][0]))))
    assert any("old 須為 null" in e for e in errs(lambda p: p["id_map"][0].update(op="new")))
    assert m.validate_proposal(_proposal(), "prospect", cids, ids, titles) == []


def test_package_rejects_synthesis_with_new_fine_and_accepts_valid(tmp_path):
    kb, dr, co = _inputs(tmp_path)
    raw = tmp_path / "raw"; raw.mkdir()
    ps = []
    for i, ang in enumerate(("user_question_path", "content_boundary", "audience_level")):
        p = raw / f"angle-{ang}.json"; p.write_text(json.dumps(_proposal(ang), ensure_ascii=False), encoding="utf-8"); ps.append(str(p))
    bad = _synthesis(); bad["fines"].append({"id": "prospect/A/extra", "coarse_id": "A", "title": "多出來", "slug": "extra",
                                            "merge_of": ["tmp:kb:1"], "split_from": [], "moved_from": [], "reason": "x"})
    bad["id_map"].append({"old": "tmp:kb:1", "new": "prospect/A/extra", "op": "split"})
    sb = raw / "synthesis-bad.json"; sb.write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    base = ["structure_propose.py", "package", "--kb-rows", kb, "--drafts", dr, "--coarses", co, "--proposals", *ps,
            "--raw-dir", str(raw), "--journal", str(tmp_path / "j.json"), "--run-id", "t", "--out", str(tmp_path / "env.json")]
    r = _run(base + ["--synthesis", str(sb)])
    assert r.returncode == 2 and "三份提議都沒有的細目" in r.stderr
    sg = raw / "synthesis.json"; sg.write_text(json.dumps(_synthesis(), ensure_ascii=False), encoding="utf-8")
    r = _run(base + ["--synthesis", str(sg)])
    assert r.returncode == 0, r.stderr
    env = json.loads((tmp_path / "env.json").read_text(encoding="utf-8"))
    assert env["step"] == "structure" and env["deterministic"] is False and len(env["payload"]["proposals"]) == 3
    assert env["payload"]["synthesis"]["rejected_alternatives"] and env["cost"]["agents"] == 4
    assert json.loads((tmp_path / "j.json").read_text(encoding="utf-8"))["step"] == "structure"


def test_synth_prompt_contains_three_proposals_and_no_examples(tmp_path):
    kb, dr, co = _inputs(tmp_path)
    ps = []
    for ang in ("user_question_path", "content_boundary", "audience_level"):
        p = tmp_path / f"{ang}.json"; p.write_text(json.dumps(_proposal(ang), ensure_ascii=False), encoding="utf-8"); ps.append(str(p))
    r = _run(["structure_propose.py", "synth-prompt", "--kb-rows", kb, "--drafts", dr, "--coarses", co, "--proposals", *ps, "--out", str(tmp_path / "s.md")])
    assert r.returncode == 0, r.stderr
    t = (tmp_path / "s.md").read_text(encoding="utf-8")
    assert t.count('"angle": "') >= 3 and "rejected_alternatives" in t and "例如" not in t


# ---------------------------------------------------------------------------
# apply_proposal（決定性；缺對應表必擋；產出過 canon_parser）
# ---------------------------------------------------------------------------

def test_apply_is_byte_deterministic_and_parses(tmp_path):
    kb, dr, _ = _inputs(tmp_path)
    prop = tmp_path / "syn.json"; prop.write_text(json.dumps(_synthesis(), ensure_ascii=False), encoding="utf-8")
    outs = []
    for i in (1, 2):
        md, im = tmp_path / f"c{i}.md", tmp_path / f"i{i}.json"
        r = _run(["apply_proposal.py", "--proposal", str(prop), "--kb-rows", kb, "--drafts", dr, "--version", "2026-09-06.1",
                  "--out-md", str(md), "--out-idmap", str(im)])
        assert r.returncode == 0, r.stderr
        outs.append((md.read_bytes(), im.read_bytes()))
    assert outs[0] == outs[1]
    md = outs[0][0].decode("utf-8")
    assert "## A 產品基本盤 {#A}" in md and "### 收租對帳 {#prospect/C/rent-collection}" in md
    assert "- sources: [kb:2]" in md and "- sources: [draft:batch#1]" in md and "- instance_applicability: general" in md
    assert "帳單自動產生。\n收租可線上對帳。" in md  # 一行一句
    idmap = json.loads(outs[0][1])
    assert len(idmap["id_map"]) == 3 and idmap["fines"][0]["from"] and len(idmap["canon_sha256"]) == 64
    from services.agent.canon.canon_parser import parse_canon_text
    doc = parse_canon_text(md)
    assert [f.id for f in doc.fines()] == ["prospect/A/positioning", "prospect/C/rent-collection", "prospect/D/trial"]


def test_apply_requires_id_map_and_known_sources(tmp_path):
    kb, dr, _ = _inputs(tmp_path)
    no_map = _synthesis(); no_map["id_map"] = []
    p1 = tmp_path / "p1.json"; p1.write_text(json.dumps(no_map, ensure_ascii=False), encoding="utf-8")
    r = _run(["apply_proposal.py", "--proposal", str(p1), "--kb-rows", kb, "--drafts", dr, "--version", "v", "--out-md", str(tmp_path / "a.md"), "--out-idmap", str(tmp_path / "a.json")])
    assert r.returncode == 2 and "id_map" in r.stderr
    unmapped = _synthesis(); unmapped["id_map"] = unmapped["id_map"][:2]  # draft:1 不在對應表
    p2 = tmp_path / "p2.json"; p2.write_text(json.dumps(unmapped, ensure_ascii=False), encoding="utf-8")
    r = _run(["apply_proposal.py", "--proposal", str(p2), "--kb-rows", kb, "--drafts", dr, "--version", "v", "--out-md", str(tmp_path / "b.md"), "--out-idmap", str(tmp_path / "b.json")])
    assert r.returncode == 2 and "不在 id_map" in r.stderr
    assert not (tmp_path / "b.md").exists()


def test_apply_merge_concatenates_sources_in_order(tmp_path):
    kb, dr, _ = _inputs(tmp_path)
    merged = _synthesis()
    merged["fines"] = [{"id": "prospect/A/all", "coarse_id": "A", "title": "全部", "slug": "all",
                        "merge_of": ["tmp:draft:1", "tmp:kb:1", "tmp:kb:2"], "split_from": [], "moved_from": [], "reason": "併"}]
    merged["id_map"] = [{"old": o, "new": "prospect/A/all", "op": "merge"} for o in ("tmp:kb:1", "tmp:kb:2", "tmp:draft:1")]
    p = tmp_path / "m.json"; p.write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
    md = tmp_path / "m.md"
    r = _run(["apply_proposal.py", "--proposal", str(p), "--kb-rows", kb, "--drafts", dr, "--version", "v", "--out-md", str(md), "--out-idmap", str(tmp_path / "m.idmap.json")])
    assert r.returncode == 0, r.stderr
    body = md.read_text(encoding="utf-8").split("{#prospect/A/all}\n", 1)[1]
    assert body.index("可先免費試用一個月。") < body.index("金箍棒把物件") < body.index("帳單自動產生。")
    assert "- sources: [draft:batch#1, kb:1, kb:2]" in md.read_text(encoding="utf-8")
