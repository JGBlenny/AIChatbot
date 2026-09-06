"""F1（completeness audit）：apply_proposal.py --cells（helpcenter 來源衍生）＋ canon_source_check.py（正本一致性檢查）。"""
import copy
import importlib.util
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:audit-f1")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))  # 容器內＝/（.claude 掛在 /.claude）
_SCRIPTS = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts")


def _load(name):
    path = os.path.join(_SCRIPTS, f"{name}.py")
    if not os.path.exists(path):
        pytest.skip(f"{name}.py 不在掛載路徑")
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _run(args, cwd=None):
    return subprocess.run([sys.executable, os.path.join(_SCRIPTS, args[0])] + args[1:], capture_output=True, text=True, cwd=cwd or _REPO)


KB = {"rows": [
    {"kb_id": 2, "question_summary": "收租對帳 自動", "answer": "帳單自動產生。收租可線上對帳。", "business_types": ["system_provider"], "categories": ["售前顧問"], "target_user": ["prospect"], "outline_approved_by": "owner"},
    {"kb_id": 1, "question_summary": "系統介紹", "answer": "金箍棒把物件、合約、收租集中管理。", "business_types": ["system_provider"], "categories": ["售前顧問"], "target_user": ["prospect"], "outline_approved_by": "owner"},
]}
DRAFTS = {"knowledge": [{"question": "可以試用嗎", "answer": "可先免費試用一個月。", "instance_applicability": "general"}]}

CELLS = {"cells": [
    {"id": "draft:batch#1", "sources": [], "help_center": ["trial-guide"]},
    {"id": "C01", "sources": ["kb:1"], "help_center": ["intro-slug"]},
    {"id": "C02", "sources": ["kb:1"], "help_center": ["intro-slug-2"]},  # 同一 kb:1 第二個 cell ⇒ 聯集
]}


def _synthesis():
    return {
        "angle": "synthesis",
        "coarses": [{"id": "A", "title": "產品基本盤"}, {"id": "C", "title": "六大模組"}, {"id": "D", "title": "方案試用"}],
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


def _inputs(tmp_path):
    kb, dr, cells = tmp_path / "kb.json", tmp_path / "drafts.json", tmp_path / "cells.json"
    kb.write_text(json.dumps(KB, ensure_ascii=False), encoding="utf-8")
    dr.write_text(json.dumps(DRAFTS, ensure_ascii=False), encoding="utf-8")
    cells.write_text(json.dumps(CELLS, ensure_ascii=False), encoding="utf-8")
    return str(kb), str(dr), str(cells)


def test_apply_proposal_without_cells_is_byte_identical_to_today(tmp_path):
    kb, dr, _ = _inputs(tmp_path)
    prop = tmp_path / "syn.json"; prop.write_text(json.dumps(_synthesis(), ensure_ascii=False), encoding="utf-8")
    md = tmp_path / "c.md"
    r = _run(["apply_proposal.py", "--proposal", str(prop), "--kb-rows", kb, "--drafts", dr, "--version", "v",
              "--out-md", str(md), "--out-idmap", str(tmp_path / "i.json")])
    assert r.returncode == 0, r.stderr
    text = md.read_text(encoding="utf-8")
    assert "- sources: [kb:1]" in text
    assert "- sources: [kb:2]" in text
    assert "- sources: [draft:batch#1]" in text
    assert "helpcenter:" not in text


def test_apply_proposal_with_cells_unions_helpcenter_sources(tmp_path):
    kb, dr, cells = _inputs(tmp_path)
    prop = tmp_path / "syn.json"; prop.write_text(json.dumps(_synthesis(), ensure_ascii=False), encoding="utf-8")
    outs = []
    for i in (1, 2):
        md, im = tmp_path / f"c{i}.md", tmp_path / f"i{i}.json"
        r = _run(["apply_proposal.py", "--proposal", str(prop), "--kb-rows", kb, "--drafts", dr, "--cells", cells,
                  "--version", "v", "--out-md", str(md), "--out-idmap", str(im)])
        assert r.returncode == 0, r.stderr
        outs.append(md.read_bytes())
    assert outs[0] == outs[1]  # 決定性
    text = outs[0].decode("utf-8")
    # tmp:kb:1 ⇒ kb:1，來自兩個 cell（C01/C02）的 help_center 聯集、排序去重
    assert "- sources: [kb:1, helpcenter:intro-slug, helpcenter:intro-slug-2]" in text
    # tmp:draft:1 ⇒ draft:batch#1，cell 自身 id 就是該參照
    assert "- sources: [draft:batch#1, helpcenter:trial-guide]" in text
    # tmp:kb:2 沒有任何 cell 的 sources 含 kb:2 ⇒ 不衍生
    assert "- sources: [kb:2]" in text


# ---------------------------------------------------------------------------
# canon_source_check：講法有 helpcenter: 來源、sources 卻沒有對應項目
# ---------------------------------------------------------------------------

def _pm(phrasings):
    return {"step": "phrasing", "payload": {"phrasings": phrasings, "similar_pairs": []}}


def test_canon_source_check_flags_missing_and_passes_when_present(tmp_path):
    kb, dr, cells = _inputs(tmp_path)
    prop = tmp_path / "syn.json"; prop.write_text(json.dumps(_synthesis(), ensure_ascii=False), encoding="utf-8")
    md = tmp_path / "c.md"
    r = _run(["apply_proposal.py", "--proposal", str(prop), "--kb-rows", kb, "--drafts", dr, "--cells", cells,
              "--version", "v", "--out-md", str(md), "--out-idmap", str(tmp_path / "i.json")])
    assert r.returncode == 0, r.stderr

    # 反例（negative）：prospect/A/positioning 的 sources 已含 helpcenter:intro-slug，講法來源同一個 slug ⇒ 不列
    pm_ok = tmp_path / "pm_ok.json"
    pm_ok.write_text(json.dumps(_pm([
        {"fine_id": "prospect/A/positioning", "text": "系統簡介", "source": "helpcenter:intro-slug", "status": "proposed", "score": 1.0},
    ]), ensure_ascii=False), encoding="utf-8")
    ok_md = tmp_path / "ok.md"
    r = _run(["attach_phrasings.py", "--canon", str(md), "--phrasing-map", str(pm_ok), "--out", str(ok_md)])
    assert r.returncode == 0, r.stderr
    r = _run(["canon_source_check.py", "--canon", str(ok_md)])
    assert r.returncode == 0, r.stdout + r.stderr

    # 正例（positive）：prospect/C/rent-collection 的 sources 只有 kb:2（無 helpcenter:），講法卻有 helpcenter: 來源 ⇒ 列出
    pm_bad = tmp_path / "pm_bad.json"
    pm_bad.write_text(json.dumps(_pm([
        {"fine_id": "prospect/C/rent-collection", "text": "收租怎麼對帳", "source": "helpcenter:rent-guide", "status": "proposed", "score": 1.0},
    ]), ensure_ascii=False), encoding="utf-8")
    bad_md = tmp_path / "bad.md"
    r = _run(["attach_phrasings.py", "--canon", str(md), "--phrasing-map", str(pm_bad), "--out", str(bad_md)])
    assert r.returncode == 0, r.stderr
    r = _run(["canon_source_check.py", "--canon", str(bad_md)])
    assert r.returncode == 2
    assert "prospect/C/rent-collection" in r.stderr
    assert "helpcenter:rent-guide" in r.stderr


def test_build_cells_lookups_maps_draft_via_batch_cell_field(tmp_path):
    """真資料鏈：草稿檔第 n 筆的 `cell` → map-v2 該格 help_center（verifier P4：cell id 不會以 draft:batch# 開頭）。
    正對照：沒給 drafts 時同一 key 查不到；cell 不在地圖的草稿不產。"""
    ap = _load("apply_proposal")
    cells = tmp_path / "map.json"
    cells.write_text(json.dumps({"cells": [
        {"id": "C05", "sources": [], "help_center": ["slugA", "slugB"]},
        {"id": "C06", "sources": ["kb:1"], "help_center": ["slugC"]},
    ]}), encoding="utf-8")
    drafts = tmp_path / "batch.json"
    drafts.write_text(json.dumps({"knowledge": [
        {"question": "q1", "answer": "a", "cell": "C05"},
        {"question": "q2", "answer": "b", "cell": "C99"},
    ]}), encoding="utf-8")
    draft_hc, kb_hc = ap.build_cells_lookups(str(cells), str(drafts))
    assert draft_hc == {"draft:batch#1": ["slugA", "slugB"]}
    assert kb_hc == {"kb:1": ["slugC"]}
    draft_hc2, _ = ap.build_cells_lookups(str(cells))
    assert "draft:batch#1" not in draft_hc2
