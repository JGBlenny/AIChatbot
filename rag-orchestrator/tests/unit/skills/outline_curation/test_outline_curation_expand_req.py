"""outline-curation 擴充模式（brief-9.7，2026-09-16）：`--shelf X`＋`--canon <九架目錄>`＋`--kb-rows`（＋`--drafts`）。

受測物：`structure_propose.py prepare`／`intake.py`／`apply_proposal.py` 三支的 `--shelf` 分支。
材料：`tests/fixtures/canon_jgb/shelves/`（S1 合成九架：A 2 條、B／C 各 2 條、其餘空架）＋本檔內嵌的 kb 列／草稿。
每條否定結論都附正對照（同輸入不動時成功）。
"""
from __future__ import annotations

import filecmp
import json
import os
import shutil
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:9.7")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
_SCRIPTS = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts")
_SCHEMAS = os.path.join(_REPO, ".claude", "skills", "outline-curation", "schemas")
# ⚠️ 容器內 rag 根是 `/app`（不是 `<repo>/rag-orchestrator`），fixture 與 services 一律從本檔相對定位。
_TESTS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_RAG = os.path.dirname(_TESTS)
_FIXTURE = os.path.join(_TESTS, "fixtures", "canon_jgb", "shelves")
if _RAG not in sys.path:
    sys.path.insert(0, _RAG)

from services.agent.canon.canon_parser import parse_canon_dir  # noqa: E402


def _run(args, cwd=None):
    return subprocess.run([sys.executable, os.path.join(_SCRIPTS, args[0])] + args[1:],
                           capture_output=True, text=True, cwd=cwd or _REPO)


_KB_ROWS = {"rows": [
    {"kb_id": "9001", "question_summary": "忘記信箱 查帳號", "answer": "先用手機號碼登入。登入後到帳號設定看信箱。"},
    {"kb_id": "9002", "question_summary": "驗證碼一直失敗", "answer": "請用最新一封信的驗證碼；舊碼會失效。"},
    {"kb_id": "9003", "question_summary": "改信箱", "answer": "帳號設定可以改信箱，改完要重新驗證。"},
]}
_DRAFTS = [
    {"id": "help:onboarding9", "summary": "公司團隊怎麼註冊", "text": "公司帳號要先建立團隊再邀請成員。"},
]


def _ids(shelf_dir: str) -> set:
    return {f.id for f in parse_canon_dir(shelf_dir).fines()}


def _proposal(fixture_ids: list, *, extra_fines=(), extra_idmap=()) -> dict:
    """A 架：既有細目全部 keep ＋ 兩條 new（kb）＋ 一條 new（draft）。"""
    fines, id_map = [], []
    for fid in fixture_ids:
        slug = fid.split("/")[-1]
        fines.append({"id": fid, "slug": slug, "title": f"既有 {slug}", "coarse_id": "A", "op": "keep",
                      "merge_of": [f"tmp:canon:{fid}"], "split_from": [], "moved_from": [], "reason": "既有",
                      "target_user": ["prospect"]})
        id_map.append({"old": f"tmp:canon:{fid}", "new": fid, "op": "keep"})
    fines.append({"id": "jgb/A/find-account", "slug": "find-account", "title": "忘記信箱怎麼找帳號", "coarse_id": "A",
                  "op": "new", "merge_of": ["tmp:kb:9001", "tmp:kb:9002"], "split_from": [], "moved_from": [],
                  "reason": "登入排障", "target_user": ["prospect", "property_manager"]})
    id_map += [{"old": "tmp:kb:9001", "new": "jgb/A/find-account", "op": "new"},
               {"old": "tmp:kb:9002", "new": "jgb/A/find-account", "op": "new"}]
    fines.append({"id": "jgb/A/company-registration", "slug": "company-registration", "title": "公司團隊怎麼註冊",
                  "coarse_id": "A", "op": "new", "merge_of": ["tmp:draft:1"], "split_from": [], "moved_from": [],
                  "reason": "幫助中心", "target_user": ["prospect"]})
    id_map.append({"old": "tmp:draft:1", "new": "jgb/A/company-registration", "op": "new"})
    fines += list(extra_fines)
    id_map += list(extra_idmap)
    return {"coarses": [{"id": "A", "title": "帳號與身分"}], "fines": fines, "id_map": id_map, "out_of_shelf": []}


@pytest.fixture
def lib(tmp_path):
    """材料落到 tmp：九架複本、kb 列、草稿；回 (canon_dir, kb_path, drafts_path, A 架既有 id 升冪)。"""
    canon = tmp_path / "jgb"
    shutil.copytree(_FIXTURE, canon)
    kb = tmp_path / "kb.json"
    kb.write_text(json.dumps(_KB_ROWS, ensure_ascii=False), encoding="utf-8")
    drafts = tmp_path / "drafts.json"
    drafts.write_text(json.dumps(_DRAFTS, ensure_ascii=False), encoding="utf-8")
    a_ids = sorted(
        f.id for f in parse_canon_dir(str(canon)).fines()
        if f.id.split("/")[1] == "A"  # 計畫 9.10 S5 第二輪：架字母＝細目 id 中段，⛔ 不用 coarse_id（見 canon_items.fine_shelf_letter）
    )
    assert a_ids, "fixture A 架必須有既有細目（正對照）"
    return str(canon), str(kb), str(drafts), a_ids


def _apply(lib, proposal: dict, out: str, *, with_drafts=True):
    canon, kb, drafts, _ = lib
    p = os.path.join(os.path.dirname(out), os.path.basename(out) + "-proposal.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(proposal, fh, ensure_ascii=False)
    args = ["apply_proposal.py", "--shelf", "A", "--canon", canon, "--kb-rows", kb, "--proposal", p, "--out", out]
    if with_drafts:
        args += ["--drafts", drafts]
    return _run(args)


# ---------------------------------------------------------------------------
# prepare / intake
# ---------------------------------------------------------------------------

def test_prepare_expand_candidates_are_shelf_plus_rows_plus_drafts_and_other_shelves_absent(lib, tmp_path):
    canon, kb, drafts, a_ids = lib
    out = tmp_path / "prep"
    r = _run(["structure_propose.py", "prepare", "--canon", canon, "--kb-rows", kb, "--drafts", drafts,
              "--shelf", "A", "--coarses", os.path.join(_SCHEMAS, "coarses-jgb.json"), "--out-dir", str(out)])
    assert r.returncode == 0, r.stderr
    items = json.load(open(out / "items.json", encoding="utf-8"))
    ids = {it["id"] for it in items}
    assert ids == {f"tmp:canon:{i}" for i in a_ids} | {"tmp:kb:9001", "tmp:kb:9002", "tmp:kb:9003", "tmp:draft:1"}
    prompt = "".join(open(p, encoding="utf-8").read() for p in out.glob("angle-*.prompt.md"))
    assert prompt, "prompt 檔必須存在（正對照）"
    other = _ids(canon) - set(a_ids)
    assert other, "fixture 其他架必須有細目（正對照）"
    assert not any(o in prompt for o in other), "他架細目不得進 prompt"
    assert all(i in prompt for i in a_ids)
    assert "jgb/<粗目碼>/<slug>" in prompt
    manifest = json.load(open(out / "manifest.json", encoding="utf-8"))
    assert manifest["mode"] == "expand" and manifest["shelf"] == "A"


def test_prepare_expand_rejects_missing_kb_rows_and_bad_shelf(lib, tmp_path):
    canon, kb, drafts, _ = lib
    coarses = os.path.join(_SCHEMAS, "coarses-jgb.json")
    r = _run(["structure_propose.py", "prepare", "--canon", canon, "--shelf", "A", "--coarses", coarses,
              "--out-dir", str(tmp_path / "p1")])
    assert r.returncode == 2 and "--kb-rows" in r.stderr
    r = _run(["structure_propose.py", "prepare", "--canon", canon, "--kb-rows", kb, "--shelf", "Z",
              "--coarses", coarses, "--out-dir", str(tmp_path / "p2")])
    assert r.returncode == 2 and "--shelf" in r.stderr


def test_intake_expand_records_mode_shelf_and_both_material_sets(lib, tmp_path):
    canon, kb, drafts, a_ids = lib
    out = tmp_path / "intake.json"
    r = _run(["intake.py", "--canon", canon, "--kb-json", kb, "--drafts", drafts, "--shelf", "A",
              "--out", str(out), "--frozen-at", "2026-09-16T00:00:00Z"])
    assert r.returncode == 0, r.stderr
    payload = json.load(open(out, encoding="utf-8"))["payload"]
    assert payload["mode"] == "expand" and payload["shelf"] == "A"
    ids = {row["id"] for row in payload["kb_rows"]}
    assert ids == set(a_ids) | {"9001", "9002", "9003"}
    assert len(payload["drafts"]) == 1
    # 正對照：非擴充模式同給 --canon＋--kb-json 仍是二擇一錯
    r2 = _run(["intake.py", "--canon", canon, "--kb-json", kb, "--out", str(tmp_path / "i2.json"),
               "--frozen-at", "2026-09-16T00:00:00Z"])
    assert r2.returncode == 2


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------

def test_apply_expand_other_shelves_byte_identical_and_new_fines_rendered(lib, tmp_path):
    canon, _, _, a_ids = lib
    out = str(tmp_path / "x")
    r = _apply(lib, _proposal(a_ids), out)
    assert r.returncode == 0, r.stderr + r.stdout
    for code in "BCDEFGHI":
        assert filecmp.cmp(os.path.join(canon, f"{code}.md"), os.path.join(out, f"{code}.md"), shallow=False), code
    doc = parse_canon_dir(out)
    assert set(_ids(out)) == _ids(canon) | {"jgb/A/find-account", "jgb/A/company-registration"}
    kb_fine = next(f for f in doc.fines() if f.id == "jgb/A/find-account")
    assert kb_fine.content_units == ("先用手機號碼登入。", "登入後到帳號設定看信箱。", "請用最新一封信的驗證碼；舊碼會失效。")
    assert kb_fine.sources == ("kb:9001", "kb:9002")
    assert kb_fine.target_user == ("property_manager", "prospect")
    assert kb_fine.business_types == ("system_provider",)
    assert kb_fine.reviewed_by is None
    draft_fine = next(f for f in doc.fines() if f.id == "jgb/A/company-registration")
    assert draft_fine.content_units == () and draft_fine.sources == ("helpcenter:onboarding9",)
    pending = json.load(open(os.path.join(out, "pending", "pending-content.json"), encoding="utf-8"))
    assert [p["id"] for p in pending] == ["jgb/A/company-registration"]
    assert pending[0]["source_pages"][0]["text"] == _DRAFTS[0]["text"]
    for derived in ("CATALOG.md", "jgb.json", "id_map.json"):
        assert os.path.isfile(os.path.join(out, derived)), derived
    # 既有細目原樣（content_sha 不變）
    before = {
        f.id: f.content_sha256 for f in parse_canon_dir(canon).fines()
        if f.id.split("/")[1] == "A"
    }
    after = {f.id: f.content_sha256 for f in doc.fines() if f.id in before}
    assert before == after


def test_apply_expand_existing_fine_absorbing_new_material_appends_and_drops_reviewed(lib, tmp_path):
    """既有細目 merge 進 kb 列＋草稿：內容＝既有句＋kb 句、sources 追加、講法保留、reviewed 丟棄、進 pending-content。"""
    canon, _, _, a_ids = lib
    target = a_ids[0]
    prop = _proposal(a_ids)
    fine = next(f for f in prop["fines"] if f["id"] == target)
    fine["op"] = "merge"
    fine["merge_of"] = [f"tmp:canon:{target}", "tmp:kb:9003", "tmp:draft:1"]
    # 改派：kb:9003 與 draft:1 從原本的新細目移到既有細目
    prop["fines"] = [f for f in prop["fines"] if f["id"] != "jgb/A/company-registration"]
    prop["id_map"] = [r for r in prop["id_map"] if r["old"] not in ("tmp:draft:1",)]
    prop["id_map"] += [{"old": "tmp:kb:9003", "new": target, "op": "merge"},
                       {"old": "tmp:draft:1", "new": target, "op": "merge"}]
    before = next(f for f in parse_canon_dir(canon).fines() if f.id == target)
    r = _apply(lib, prop, str(tmp_path / "m"))
    assert r.returncode == 0, r.stderr + r.stdout
    after = next(f for f in parse_canon_dir(str(tmp_path / "m")).fines() if f.id == target)
    assert after.content_units == before.content_units + ("帳號設定可以改信箱，改完要重新驗證。",)
    assert set(before.sources) <= set(after.sources) and {"kb:9003", "helpcenter:onboarding9"} <= set(after.sources)
    assert [p.text for p in after.phrasings] == [p.text for p in before.phrasings]
    assert after.reviewed_by is None
    pending = json.load(open(tmp_path / "m" / "pending" / "pending-content.json", encoding="utf-8"))
    assert [p["id"] for p in pending] == [target]
    # 正對照：沒吸收新材料的既有細目 reviewed 原樣
    other = [i for i in a_ids if i != target]
    if other:
        b = next(f for f in parse_canon_dir(canon).fines() if f.id == other[0])
        a = next(f for f in parse_canon_dir(str(tmp_path / "m")).fines() if f.id == other[0])
        assert (a.reviewed_by, a.content_units) == (b.reviewed_by, b.content_units)


def test_apply_expand_new_fine_with_kb_and_draft_keeps_kb_sentences(lib, tmp_path):
    """新細目同時來自 kb 列與草稿：kb 句必須渲染、sources 兩種都有、且進 pending-content（草稿段落待補）。"""
    _, _, _, a_ids = lib
    prop = _proposal(a_ids)
    fine = next(f for f in prop["fines"] if f["id"] == "jgb/A/find-account")
    fine["merge_of"] = ["tmp:kb:9001", "tmp:kb:9002", "tmp:draft:1"]
    prop["fines"] = [f for f in prop["fines"] if f["id"] != "jgb/A/company-registration"]
    prop["id_map"] = [r for r in prop["id_map"] if r["old"] != "tmp:draft:1"]
    prop["id_map"].append({"old": "tmp:draft:1", "new": "jgb/A/find-account", "op": "new"})
    out = str(tmp_path / "kd")
    r = _apply(lib, prop, out)
    assert r.returncode == 0, r.stderr + r.stdout
    fine_out = next(f for f in parse_canon_dir(out).fines() if f.id == "jgb/A/find-account")
    assert len(fine_out.content_units) == 3, fine_out.content_units
    assert fine_out.sources == ("kb:9001", "kb:9002", "helpcenter:onboarding9")
    pending = json.load(open(os.path.join(out, "pending", "pending-content.json"), encoding="utf-8"))
    assert [p["id"] for p in pending] == ["jgb/A/find-account"] and pending[0].get("note")


def test_sentences_of_strips_list_markers():
    sys.path.insert(0, _SCRIPTS)
    import importlib
    ap = importlib.import_module("apply_proposal")
    assert ap.sentences_of("- 第一句。\n* 第二句。\n• 第三句") == ["第一句。", "第二句。", "第三句"]
    assert ap.sentences_of("普通一句。") == ["普通一句。"]  # 正對照：無符號不動


def test_apply_expand_is_byte_deterministic(lib, tmp_path):
    _, _, _, a_ids = lib
    r1 = _apply(lib, _proposal(a_ids), str(tmp_path / "x1"))
    r2 = _apply(lib, _proposal(a_ids), str(tmp_path / "x2"))
    assert r1.returncode == 0 and r2.returncode == 0, r1.stderr + r2.stderr
    cmp = filecmp.dircmp(str(tmp_path / "x1"), str(tmp_path / "x2"))
    assert not cmp.diff_files and not cmp.left_only and not cmp.right_only
    sub = cmp.subdirs["pending"]
    assert not sub.diff_files


@pytest.mark.parametrize("mutate,needle", [
    (lambda p: p["fines"][-2].update({"id": "jgb/B/team-invite"}) or p["id_map"].__setitem__(
        -3, {**p["id_map"][-3], "new": "jgb/B/team-invite"}) or p["id_map"].__setitem__(
        -2, {**p["id_map"][-2], "new": "jgb/B/team-invite"}), "撞"),
    (lambda p: p["fines"][-2].pop("target_user"), "target_user"),
    (lambda p: p["fines"][-1].update({"coarse_id": "B"}), "--shelf"),
    (lambda p: p["fines"][-2].update({"merge_of": ["tmp:kb:9999"]}) or p["id_map"].append(
        {"old": "tmp:kb:9999", "new": "jgb/A/find-account", "op": "new"}), "不在 --kb-rows"),
])
def test_apply_expand_rejects_and_writes_nothing(lib, tmp_path, mutate, needle):
    canon, _, _, a_ids = lib
    prop = _proposal(a_ids)
    mutate(prop)
    out = str(tmp_path / "y")
    r = _apply(lib, prop, out)
    assert r.returncode == 2, r.stdout + r.stderr
    assert needle in r.stderr
    assert not os.path.exists(out), "拒套不得落任何輸出檔"
    # 正對照：同材料未動的提議成功
    ok = _apply(lib, _proposal(a_ids), str(tmp_path / "ok"))
    assert ok.returncode == 0, ok.stderr


def test_apply_expand_refuses_non_empty_out_dir(lib, tmp_path):
    _, _, _, a_ids = lib
    out = tmp_path / "busy"
    out.mkdir()
    (out / "junk").write_text("x", encoding="utf-8")
    r = _apply(lib, _proposal(a_ids), str(out))
    assert r.returncode == 2 and "不覆蓋" in r.stderr
    assert (out / "junk").exists() and sorted(p.name for p in out.iterdir()) == ["junk"]


# ---------------------------------------------------------------------------
# 計畫 9.10 S5 第三輪（DSP-070 殘留稽核 F1／F2）：粗目結構與架標題不得被靜默改掉
# ---------------------------------------------------------------------------

def _edit_a(canon: str, old: str, new: str) -> None:
    path = os.path.join(canon, "A.md")
    text = open(path, encoding="utf-8").read()
    assert text.count(old) == 1, f"fixture A.md 須恰含一次 {old!r}（正對照）"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.replace(old, new))


def test_expand_refuses_shelf_with_multiple_coarses(lib, tmp_path):
    """F2：提議只能表達一架一粗目；目標架已有多粗目時照跑會把粗目結構攤平 ⇒ 必須拒套、⛔ 不落檔。"""
    canon, _, _, a_ids = lib
    _edit_a(canon, "### 忘記密碼怎麼辦 {#jgb/A/password-reset}",
            "## 另一個功能 {#A-other}\n### 忘記密碼怎麼辦 {#jgb/A/password-reset}")
    assert sorted(c.id for c in parse_canon_dir(canon).coarses if c.id.startswith("A-")) == ["A-account", "A-other"]
    out = str(tmp_path / "multi")
    r = _apply(lib, _proposal(a_ids), out)
    assert r.returncode == 2, r.stdout
    assert "攤平" in r.stderr and "A-other" in r.stderr
    assert not os.path.exists(os.path.join(out, "A.md"))


def test_expand_keeps_single_coarse_id_and_title(lib, tmp_path):
    """F2：單粗目架保留原粗目 id 與標題（⛔ 不改名成 `A-shelf`）。"""
    canon, _, _, a_ids = lib
    _edit_a(canon, "## 帳號與身分 {#A-account}", "## 帳號功能 {#A-account}")
    out = str(tmp_path / "keep")
    r = _apply(lib, _proposal(a_ids), out)
    assert r.returncode == 0, r.stderr + r.stdout
    assert [(c.id, c.title) for c in parse_canon_dir(out).coarses if c.id.startswith("A-")] == [("A-account", "帳號功能")]


def test_expand_keeps_canon_shelf_title(lib, tmp_path):
    """F1：架標題取正本 front matter（`shelf_titles`），⛔ 不被提議或內建預設蓋回。"""
    canon, _, _, a_ids = lib
    _edit_a(canon, "title: 帳號與身分\n", "title: 帳號與身分（業主改名）\n")
    out = str(tmp_path / "title")
    r = _apply(lib, _proposal(a_ids), out)
    assert r.returncode == 0, r.stderr + r.stdout
    assert dict(parse_canon_dir(out).shelf_titles)["A"] == "帳號與身分（業主改名）"
