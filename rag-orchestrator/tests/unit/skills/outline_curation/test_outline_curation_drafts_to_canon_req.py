"""unit：`scripts/drafts_to_canon.py`（計畫 9.10 S3；DSP-067／DSP-068）。

驗：九架合成 drafts → `generate` 子命令跑完整流程（`parse_canon_dir`／`export_json`／
`export_catalog`／`load_canon_or_die` 三源比對）；DSP-068 標點例外只刪成對括號內、緊接右括號的
終止符，標題與 phrasings 一字不動；粗目標題查表落空／講法含 `"`／跨架重複細目 id／跨架重複講法
／引號不平衡皆大聲失敗（exit≠0）且不留半套產出；引號不平衡守門一次點名**所有**違規細目 id；
兩次生成逐位元相同；`--self-test` 通過。

已審保留（Plan 9.16 S1）：舊正本內容不變的已審細目重生成後保留 `reviewed`、內容改過的丟棄並列入
`reviewed-dropped-<日期>.json`、未審者不會變已審；`--expect-reviewed-kept` 不符 ⇒ 非 0 且不留任何輸出。

材料一律合成的最小九架 fixture（⛔ 不讀版控正本——那是整合驗收，不是 unit 的事）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:9.6")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
_SCRIPT = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts", "drafts_to_canon.py")

_SHELVES = tuple("ABCDEFGHI")


def _skip_if_missing():
    if not os.path.isfile(_SCRIPT):
        pytest.skip(f"[env] 找不到 {_SCRIPT}——容器需掛 repo 根 .claude/，宿主直跑本檔")


def _fine(fid, title, sentences, phrasings=None, open_questions=None):
    return {
        "proposed_id": fid, "title": title, "sentences": sentences,
        "phrasings": phrasings or [], "sources": ["code:x.vue"],
        "target_user": ["property_manager"], "business_types": ["system_provider"],
        "instance_applicability": "general", "open_questions": open_questions or [],
    }


def _minimal_drafts():
    """九架、每架恰一粗目一細目（唯一例外：A 架兩粗目，覆蓋一架多粗目路徑）。"""
    drafts = {}
    for shelf in _SHELVES:
        if shelf == "A":
            drafts[shelf] = {
                "shelf": "A", "jgb2_sha": "sha-a",
                "coarses": [
                    {"coarse": f"測試粗目{shelf}一", "fines": [
                        _fine(f"jgb/{shelf}/probe-one", f"標題{shelf}1？",
                              ["第一句。第二句。", "有「引號句子」的內容。"],
                              phrasings=[f"講法{shelf}1"],
                              open_questions=[f"待裁{shelf}1"]),
                    ]},
                    {"coarse": f"測試粗目{shelf}二 ⇄ 由 B 移入", "fines": [
                        _fine(f"jgb/{shelf}/probe-two", f"標題{shelf}2",
                              ["內容句。"], phrasings=[f"講法{shelf}2"]),
                    ]},
                ],
            }
        else:
            drafts[shelf] = {
                "shelf": shelf, "jgb2_sha": f"sha-{shelf}",
                "coarses": [
                    {"coarse": f"測試粗目{shelf}", "fines": [
                        _fine(f"jgb/{shelf}/probe", f"標題{shelf}",
                              ["內容句。"], phrasings=[f"講法{shelf}"]),
                    ]},
                ],
            }
    return drafts


def _coarse_ids_table(drafts):
    rows = ["| # | 架 | 粗目標題 | 粗目 id | 細目數 |", "|---|---|---|---|---|"]
    n = 1
    for shelf in _SHELVES:
        for coarse in drafts[shelf]["coarses"]:
            title = coarse["coarse"].split("⇄")[0].rstrip()
            slug = coarse["fines"][0]["proposed_id"].split("/")[-1]
            cid = f"{shelf}-{slug}-coarse"
            rows.append(f"| {n} | {shelf} | {title} | `{cid}` | {len(coarse['fines'])} |")
            n += 1
    return "\n".join(rows) + "\n"


def _front_matter_dir(tmp_path):
    d = tmp_path / "fm"
    d.mkdir()
    for shelf in _SHELVES:
        (d / f"{shelf}.md").write_text(
            "---\n"
            f"coarse: {shelf}\n"
            f"title: 架{shelf}標題\n"
            f"scope: 架{shelf}範圍\n"
            "version: 2026-09-15.0\n"
            "reviewers: [owner]\n"
            "language: zh-TW\n"
            "---\n"
            f"## 架{shelf}標題 {{#{shelf}}}\n",
            encoding="utf-8",
        )
    return str(d)


@pytest.fixture
def workspace(tmp_path):
    drafts = _minimal_drafts()
    drafts_dir = tmp_path / "drafts"
    drafts_dir.mkdir()
    for shelf in _SHELVES:
        (drafts_dir / f"drafts-{shelf}.json").write_text(
            json.dumps(drafts[shelf], ensure_ascii=False), encoding="utf-8",
        )
    coarse_ids = tmp_path / "coarse-ids.md"
    coarse_ids.write_text(_coarse_ids_table(drafts), encoding="utf-8")
    fm_dir = _front_matter_dir(tmp_path)
    return {"drafts": drafts, "drafts_dir": str(drafts_dir), "coarse_ids": str(coarse_ids), "fm_dir": fm_dir}


def _run_generate(tmp_path, drafts_dir, coarse_ids, fm_dir, canon_root, runs_out, date="20260923", extra=()):
    cmd = [
        sys.executable, _SCRIPT, "generate",
        "--drafts-dir", drafts_dir, "--coarse-ids", coarse_ids,
        "--front-matter-from", fm_dir, "--canon-root", str(canon_root),
        "--runs-out", str(runs_out), "--date", date, *extra,
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_self_test_passes():
    _skip_if_missing()
    r = subprocess.run([sys.executable, _SCRIPT, "--self-test"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_generate_happy_path_passes_load_canon_or_die(tmp_path, workspace):
    _skip_if_missing()
    canon_root = tmp_path / "canon"
    runs_out = tmp_path / "runs"
    r = _run_generate(tmp_path, workspace["drafts_dir"], workspace["coarse_ids"], workspace["fm_dir"],
                       canon_root, runs_out)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (canon_root / "jgb.json").is_file()
    assert (canon_root / "jgb" / "CATALOG.md").is_file()
    for shelf in _SHELVES:
        assert (canon_root / "jgb" / f"{shelf}.md").is_file()

    a_text = (canon_root / "jgb" / "A.md").read_text(encoding="utf-8")
    assert "version: 2026-09-21.0" in a_text
    assert "{#A-probe-one-coarse}" in a_text or "測試粗目A一" in a_text  # 粗目 id 來自凍結表
    # DSP-068：句中「引號句子」不含終止符緊鄰右括號，不受影響；多句切成多行
    assert "第一句。" in a_text and "第二句。" in a_text
    assert "有「引號句子」的內容。" in a_text


def test_dsp068_deletes_only_bracket_final_terminator(tmp_path, workspace):
    _skip_if_missing()
    drafts = workspace["drafts"]
    drafts["A"]["coarses"][0]["fines"][0]["sentences"] = ["登入頁「還沒有帳號嗎？」旁的連結。"]
    drafts_dir = tmp_path / "drafts2"
    drafts_dir.mkdir()
    for shelf in _SHELVES:
        (drafts_dir / f"drafts-{shelf}.json").write_text(
            json.dumps(drafts[shelf], ensure_ascii=False), encoding="utf-8",
        )
    canon_root = tmp_path / "canon2"
    runs_out = tmp_path / "runs2"
    r = _run_generate(tmp_path, str(drafts_dir), workspace["coarse_ids"], workspace["fm_dir"],
                       canon_root, runs_out)
    assert r.returncode == 0, r.stdout + r.stderr
    a_text = (canon_root / "jgb" / "A.md").read_text(encoding="utf-8")
    assert "登入頁「還沒有帳號嗎」旁的連結。" in a_text
    assert "還沒有帳號嗎？」" not in a_text
    # 標題／phrasings 一字不動（此 fixture 標題含 ？，斷言仍在）
    assert "標題A1？" in a_text

    manifest = json.loads((runs_out / "dsp-068-deletions-20260923.json").read_text(encoding="utf-8"))
    assert manifest == [{
        "fine_id": "jgb/A/probe-one", "sentence_index": 0, "offset": 10, "char": "？",
    }]


def test_coarse_title_lookup_miss_fails_loudly_with_title(tmp_path, workspace):
    _skip_if_missing()
    bad_table = tmp_path / "bad-coarse-ids.md"
    bad_table.write_text("| # | 架 | 粗目標題 | 粗目 id | 細目數 |\n|---|---|---|---|---|\n", encoding="utf-8")
    canon_root = tmp_path / "canon3"
    runs_out = tmp_path / "runs3"
    r = _run_generate(tmp_path, workspace["drafts_dir"], str(bad_table), workspace["fm_dir"],
                       canon_root, runs_out)
    assert r.returncode != 0
    assert "測試粗目A一" in (r.stdout + r.stderr)
    assert not (canon_root / "jgb").exists()


def test_phrasing_with_quote_fails_loudly(tmp_path, workspace):
    _skip_if_missing()
    drafts = workspace["drafts"]
    drafts["B"]["coarses"][0]["fines"][0]["phrasings"] = ['含 " 引號的講法']
    drafts_dir = tmp_path / "drafts4"
    drafts_dir.mkdir()
    for shelf in _SHELVES:
        (drafts_dir / f"drafts-{shelf}.json").write_text(
            json.dumps(drafts[shelf], ensure_ascii=False), encoding="utf-8",
        )
    canon_root = tmp_path / "canon4"
    runs_out = tmp_path / "runs4"
    r = _run_generate(tmp_path, str(drafts_dir), workspace["coarse_ids"], workspace["fm_dir"],
                       canon_root, runs_out)
    assert r.returncode != 0
    assert "jgb/B/probe" in (r.stdout + r.stderr)
    assert not (canon_root / "jgb").exists()


def test_duplicate_fine_id_across_shelves_fails_loudly(tmp_path, workspace):
    _skip_if_missing()
    drafts = workspace["drafts"]
    drafts["C"]["coarses"][0]["fines"][0]["proposed_id"] = "jgb/A/probe-one"  # 撞 A 架的第一條
    drafts_dir = tmp_path / "drafts5"
    drafts_dir.mkdir()
    for shelf in _SHELVES:
        (drafts_dir / f"drafts-{shelf}.json").write_text(
            json.dumps(drafts[shelf], ensure_ascii=False), encoding="utf-8",
        )
    canon_root = tmp_path / "canon5"
    runs_out = tmp_path / "runs5"
    r = _run_generate(tmp_path, str(drafts_dir), workspace["coarse_ids"], workspace["fm_dir"],
                       canon_root, runs_out)
    assert r.returncode != 0
    out = r.stdout + r.stderr
    assert "跨架重複細目 id：1" in out
    assert not (canon_root / "jgb").exists()


def test_duplicate_phrasing_across_shelves_fails_loudly(tmp_path, workspace):
    _skip_if_missing()
    drafts = workspace["drafts"]
    drafts["D"]["coarses"][0]["fines"][0]["phrasings"] = ["講法A1"]  # 撞 A 架第一條細目的講法
    drafts_dir = tmp_path / "drafts6"
    drafts_dir.mkdir()
    for shelf in _SHELVES:
        (drafts_dir / f"drafts-{shelf}.json").write_text(
            json.dumps(drafts[shelf], ensure_ascii=False), encoding="utf-8",
        )
    canon_root = tmp_path / "canon6"
    runs_out = tmp_path / "runs6"
    r = _run_generate(tmp_path, str(drafts_dir), workspace["coarse_ids"], workspace["fm_dir"],
                       canon_root, runs_out)
    assert r.returncode != 0
    out = r.stdout + r.stderr
    assert "跨架重複講法（NFKC）：1" in out
    assert not (canon_root / "jgb").exists()


def test_unbalanced_brackets_names_every_violating_fine(tmp_path, workspace):
    """步驟 0 未做的負對照場景：⛔ 只 fail-fast 報第一條不合格——兩條都不平衡時兩個 id 都要點名。"""
    _skip_if_missing()
    drafts = workspace["drafts"]
    drafts["A"]["coarses"][0]["fines"][0]["sentences"] = ["尚未註冊「還沒有帳號嗎？立即註冊」連結。"]
    drafts["B"]["coarses"][0]["fines"][0]["sentences"] = ["顯示「恭喜！你已經成功綁定所有物件」按鈕。"]
    drafts_dir = tmp_path / "drafts7"
    drafts_dir.mkdir()
    for shelf in _SHELVES:
        (drafts_dir / f"drafts-{shelf}.json").write_text(
            json.dumps(drafts[shelf], ensure_ascii=False), encoding="utf-8",
        )
    canon_root = tmp_path / "canon7"
    runs_out = tmp_path / "runs7"
    r = _run_generate(tmp_path, str(drafts_dir), workspace["coarse_ids"], workspace["fm_dir"],
                       canon_root, runs_out)
    assert r.returncode != 0
    out = r.stdout + r.stderr
    assert "jgb/A/probe-one" in out
    assert "jgb/B/probe" in out
    assert not (canon_root / "jgb").exists()


def test_two_runs_byte_identical(tmp_path, workspace):
    _skip_if_missing()
    canon_root1 = tmp_path / "canon_r1"
    runs_out1 = tmp_path / "runs_r1"
    canon_root2 = tmp_path / "canon_r2"
    runs_out2 = tmp_path / "runs_r2"
    r1 = _run_generate(tmp_path, workspace["drafts_dir"], workspace["coarse_ids"], workspace["fm_dir"],
                        canon_root1, runs_out1)
    r2 = _run_generate(tmp_path, workspace["drafts_dir"], workspace["coarse_ids"], workspace["fm_dir"],
                        canon_root2, runs_out2)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    assert r2.returncode == 0, r2.stdout + r2.stderr
    for shelf in _SHELVES:
        assert (canon_root1 / "jgb" / f"{shelf}.md").read_bytes() == \
               (canon_root2 / "jgb" / f"{shelf}.md").read_bytes()
    assert (canon_root1 / "jgb.json").read_bytes() == (canon_root2 / "jgb.json").read_bytes()
    assert (canon_root1 / "jgb" / "CATALOG.md").read_bytes() == (canon_root2 / "jgb" / "CATALOG.md").read_bytes()
    assert (runs_out1 / "dsp-068-deletions-20260923.json").read_bytes() == \
           (runs_out2 / "dsp-068-deletions-20260923.json").read_bytes()
    assert (runs_out1 / "open-questions-20260923.md").read_bytes() == \
           (runs_out2 / "open-questions-20260923.md").read_bytes()


# ---------------------------------------------------------------------------
# 已審保留（Plan 9.16 S1）
# ---------------------------------------------------------------------------

_REVIEWED_LINE = "- reviewed: {by: owner, at: 2026-09-27}"


def _mark_reviewed(shelf_md, fine_id):
    """在舊正本某細目的 `- sources:` 之後插入已審行（模擬 9.15 S4 的寫入方式）。"""
    lines = shelf_md.read_text(encoding="utf-8").split("\n")
    out, in_fine = [], False
    for line in lines:
        if line.startswith("### "):
            in_fine = line.endswith(f"{{#{fine_id}}}")
        out.append(line)
        if in_fine and line.startswith("- sources:"):
            out.append(_REVIEWED_LINE)
    shelf_md.write_text("\n".join(out), encoding="utf-8")


def _reviewed_ids(shelf_md):
    ids, cur = [], None
    for line in shelf_md.read_text(encoding="utf-8").split("\n"):
        if line.startswith("### "):
            cur = line.rsplit("{#", 1)[1].rstrip("}")
        elif line == _REVIEWED_LINE:
            ids.append(cur)
    return ids


@pytest.fixture
def reviewed_canon(tmp_path, workspace):
    """先生成一份舊正本，再標 B、C 兩條已審（D 維持未審）；回傳舊正本根目錄。"""
    old_root = tmp_path / "old_canon"
    r = _run_generate(tmp_path, workspace["drafts_dir"], workspace["coarse_ids"], workspace["fm_dir"],
                      old_root, tmp_path / "old_runs")
    assert r.returncode == 0, r.stdout + r.stderr
    _mark_reviewed(old_root / "jgb" / "B.md", "jgb/B/probe")
    _mark_reviewed(old_root / "jgb" / "C.md", "jgb/C/probe")
    assert _reviewed_ids(old_root / "jgb" / "B.md") == ["jgb/B/probe"]
    assert _reviewed_ids(old_root / "jgb" / "C.md") == ["jgb/C/probe"]
    # C 改一句 ⇒ 內容指紋不同
    drafts_c = dict(workspace["drafts"]["C"])
    drafts_c["coarses"][0]["fines"][0]["sentences"] = ["改過的內容句。"]
    (tmp_path / "drafts" / "drafts-C.json").write_text(json.dumps(drafts_c, ensure_ascii=False), encoding="utf-8")
    return old_root


def test_reviewed_kept_when_unchanged_and_dropped_when_changed(tmp_path, workspace, reviewed_canon):
    _skip_if_missing()
    canon_root = tmp_path / "canon"
    runs_out = tmp_path / "runs"
    r = _run_generate(tmp_path, workspace["drafts_dir"], workspace["coarse_ids"], str(reviewed_canon / "jgb"),
                      canon_root, runs_out, extra=("--expect-reviewed-kept", "1"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "已審保留：1 條／丟棄：1 條" in r.stdout
    assert _reviewed_ids(canon_root / "jgb" / "B.md") == ["jgb/B/probe"]
    assert _reviewed_ids(canon_root / "jgb" / "C.md") == []
    assert _reviewed_ids(canon_root / "jgb" / "D.md") == []
    # 內容不變的已審細目：整架逐位元組等於舊正本（已審行寫在 `- sources:` 之後的原位置）
    assert (canon_root / "jgb" / "B.md").read_bytes() == (reviewed_canon / "jgb" / "B.md").read_bytes()
    dropped = json.loads((runs_out / "reviewed-dropped-20260923.json").read_text(encoding="utf-8"))
    assert [(d["fine_id"], d["reason"]) for d in dropped] == [("jgb/C/probe", "content_changed")]
    # 三源一致且已審進了 jgb.json（load_canon_or_die 在 generate 內已跑過）
    by_id = {f["id"]: f for c in json.loads((canon_root / "jgb.json").read_text(encoding="utf-8"))["coarses"]
             for f in c["fines"]}
    assert by_id["jgb/B/probe"]["reviewed_by"] == "owner"
    assert by_id["jgb/C/probe"]["reviewed_by"] is None
    assert by_id["jgb/D/probe"]["reviewed_by"] is None


def test_expect_reviewed_kept_mismatch_fails_before_any_write(tmp_path, workspace, reviewed_canon):
    _skip_if_missing()
    canon_root = tmp_path / "canon"
    runs_out = tmp_path / "runs"
    r = _run_generate(tmp_path, workspace["drafts_dir"], workspace["coarse_ids"], str(reviewed_canon / "jgb"),
                      canon_root, runs_out, extra=("--expect-reviewed-kept", "2"))
    assert r.returncode != 0
    assert "已審保留 1 條，與預期 2 條不符" in r.stdout + r.stderr
    assert not (canon_root / "jgb").exists()
    assert not runs_out.exists()


def test_expect_reviewed_kept_mismatch_leaves_existing_canon_byte_identical(tmp_path, workspace, reviewed_canon):
    """輸出根＝舊正本本身（S1 驗收的實跑形狀）：比對失敗時舊正本一個位元組都不動。"""
    _skip_if_missing()
    before = {p: p.read_bytes() for p in reviewed_canon.rglob("*") if p.is_file()}
    r = _run_generate(tmp_path, workspace["drafts_dir"], workspace["coarse_ids"], str(reviewed_canon / "jgb"),
                      reviewed_canon, tmp_path / "runs", extra=("--expect-reviewed-kept", "2"))
    assert r.returncode != 0
    after = {p: p.read_bytes() for p in reviewed_canon.rglob("*") if p.is_file()}
    assert after == before
    assert _reviewed_ids(reviewed_canon / "jgb" / "B.md") == ["jgb/B/probe"]
