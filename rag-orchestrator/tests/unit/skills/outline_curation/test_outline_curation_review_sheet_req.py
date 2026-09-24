"""unit：`structure_review_sheet.py`（knowledge-outline-and-intent-architecture 任務 9.3⑤／9.5 前置）。

驗：讀 `structure-proposal.json`＋`structure/items.json` 產出各段（A 舊→新／B split／C merge／
D rejected_alternatives／E 粗目分佈／F 待審清單）；三角度分歧標 ⚠️；決定性（同輸入兩次逐位元相同）。
"""
import importlib.util
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:9.3.5")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
_SCRIPTS = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts")


def _run(args):
    return subprocess.run([sys.executable, os.path.join(_SCRIPTS, args[0])] + args[1:],
                           capture_output=True, text=True, cwd=_REPO)


def _angle_proposal(angle, fines, id_map):
    return {"angle": angle, "coarses": [{"id": "A", "title": "產品定位"}, {"id": "B", "title": "資料搬遷"}],
            "fines": fines, "id_map": id_map}


ITEMS = [
    {"id": "tmp:kb:prospect/A/positioning", "title": "系統定位", "content": "x"},
    {"id": "tmp:kb:prospect/A/data-migration", "title": "舊資料匯入", "content": "y"},
    {"id": "tmp:kb:prospect/A/migration-limits", "title": "搬遷限制", "content": "z"},
]


def _fine(fid, coarse, title, merge_of, split_from=()):
    return {"id": fid, "coarse_id": coarse, "title": title, "slug": fid.split("/")[-1],
            "merge_of": list(merge_of), "split_from": list(split_from), "moved_from": [], "reason": "r"}


@pytest.fixture
def run_dir(tmp_path):
    d = tmp_path / "prospect-20260915"
    (d / "structure").mkdir(parents=True)
    (d / "structure" / "items.json").write_text(json.dumps(ITEMS, ensure_ascii=False), encoding="utf-8")

    fines_agree = [
        _fine("prospect/A/positioning", "A", "系統定位", ["tmp:kb:prospect/A/positioning"]),
        _fine("prospect/B/data-migration", "B", "舊資料匯入", ["tmp:kb:prospect/A/data-migration"]),
        _fine("prospect/B/migration-limits", "B", "搬遷限制", ["tmp:kb:prospect/A/migration-limits"]),
    ]
    id_map_agree = [
        {"old": "tmp:kb:prospect/A/positioning", "new": "prospect/A/positioning", "op": "keep"},
        {"old": "tmp:kb:prospect/A/data-migration", "new": "prospect/B/data-migration", "op": "move"},
        {"old": "tmp:kb:prospect/A/migration-limits", "new": "prospect/B/migration-limits", "op": "move"},
    ]
    # 一個角度對 positioning 的判定分歧（歸到 B 而非 A）製造 ⚠️
    fines_divergent = [
        _fine("prospect/A/positioning", "B", "系統定位", ["tmp:kb:prospect/A/positioning"]),
        _fine("prospect/B/data-migration", "B", "舊資料匯入", ["tmp:kb:prospect/A/data-migration"]),
        _fine("prospect/B/migration-limits", "B", "搬遷限制", ["tmp:kb:prospect/A/migration-limits"]),
    ]

    proposals = [
        _angle_proposal("product_feature", fines_agree, id_map_agree),
        _angle_proposal("content_boundary", fines_agree, id_map_agree),
        _angle_proposal("audience_level", fines_divergent, id_map_agree),
    ]
    synthesis = {
        "angle": "synthesis",
        "coarses": [{"id": "A", "title": "產品定位"}, {"id": "B", "title": "資料搬遷"}],
        "fines": fines_agree, "id_map": id_map_agree,
        "rejected_alternatives": [{"alternative": "把三條併一條", "reason": "各自獨立可答"}],
    }
    envelope = {
        "step": "structure", "skill_version": "0.1.0", "inputs_sha": {}, "deterministic": False,
        "raw_outputs_path": None, "cost": {}, "payload": {"proposals": proposals, "synthesis": synthesis},
    }
    (d / "structure-proposal.json").write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")
    return str(d)


def test_review_sheet_sections_and_divergence_mark(tmp_path, run_dir):
    out = tmp_path / "sheet.md"
    r = _run(["structure_review_sheet.py", "--run-dir", run_dir, "--out", str(out)])
    assert r.returncode == 0, r.stderr
    text = out.read_text(encoding="utf-8")
    assert "## A. 舊細目 → 新細目" in text
    assert "## B. 拆分" in text and "（本次無拆分）" in text
    assert "## C. 合併" in text and "（本次無合併）" in text
    assert "## D. 合成否決的替代方案" in text
    assert "把三條併一條" in text
    assert "## E. 粗目分佈" in text
    # positioning 一行應標 ⚠️（audience_level 判 B，其餘判 A，且與合成 A 不一致）
    positioning_line = next(line for line in text.splitlines() if "prospect/A/positioning" in line and "|" in line and "舊細目" not in line)
    assert "⚠️" in positioning_line
    # data-migration 三角度一致、與合成一致 ⇒ 無 ⚠️
    dm_line = next(line for line in text.splitlines() if "data-migration" in line and "舊細目" not in line and line.startswith("|"))
    assert "⚠️" not in dm_line


def test_review_sheet_split_and_merge_sections(tmp_path):
    d = tmp_path / "prospect-20260915b"
    (d / "structure").mkdir(parents=True)
    items = [
        {"id": "tmp:kb:prospect/A/one", "title": "主題一", "content": "x"},
        {"id": "tmp:kb:prospect/A/two", "title": "主題二", "content": "y"},
    ]
    (d / "structure" / "items.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    fines = [
        _fine("prospect/A/one-a", "A", "主題一之一", ["tmp:kb:prospect/A/one"], ["tmp:kb:prospect/A/one"]),
        _fine("prospect/A/one-b", "A", "主題一之二", ["tmp:kb:prospect/A/one"], ["tmp:kb:prospect/A/one"]),
        _fine("prospect/A/merged", "A", "合併後主題", ["tmp:kb:prospect/A/one", "tmp:kb:prospect/A/two"]),
    ]
    id_map = [
        {"old": "tmp:kb:prospect/A/one", "new": "prospect/A/one-a", "op": "split"},
        {"old": "tmp:kb:prospect/A/one", "new": "prospect/A/one-b", "op": "split"},
        {"old": "tmp:kb:prospect/A/one", "new": "prospect/A/merged", "op": "merge"},
        {"old": "tmp:kb:prospect/A/two", "new": "prospect/A/merged", "op": "merge"},
    ]
    proposal = {"angle": "synthesis", "coarses": [{"id": "A", "title": "產品定位"}],
                "fines": fines, "id_map": id_map, "rejected_alternatives": []}
    envelope = {"step": "structure", "skill_version": "0.1.0", "inputs_sha": {}, "deterministic": False,
                "raw_outputs_path": None, "cost": {},
                "payload": {"proposals": [dict(proposal, angle=k) for k in
                                           ("product_feature", "content_boundary", "audience_level")],
                            "synthesis": proposal}}
    (d / "structure-proposal.json").write_text(json.dumps(envelope, ensure_ascii=False), encoding="utf-8")

    out = tmp_path / "sheet2.md"
    r = _run(["structure_review_sheet.py", "--run-dir", str(d), "--out", str(out)])
    assert r.returncode == 0, r.stderr
    text = out.read_text(encoding="utf-8")
    assert "prospect/A/one-a" in text and "prospect/A/one-b" in text  # B 段列出子細目
    assert "（本次無拆分）" not in text
    assert "prospect/A/merged" in text  # C 段：one 被拆但也算進 merged 的來源之一
    assert "（本次無合併）" not in text
    assert "F1." in text


def test_review_sheet_deterministic(tmp_path, run_dir):
    out1, out2 = tmp_path / "s1.md", tmp_path / "s2.md"
    for out in (out1, out2):
        r = _run(["structure_review_sheet.py", "--run-dir", run_dir, "--out", str(out)])
        assert r.returncode == 0, r.stderr
    assert out1.read_bytes() == out2.read_bytes()
