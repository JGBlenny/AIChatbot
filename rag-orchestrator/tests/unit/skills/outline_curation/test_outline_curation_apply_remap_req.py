"""unit：`apply_proposal.py --canon`（從既有正本重切套用，knowledge-outline-and-intent-architecture 任務 9.3⑤；
9.6 S4：輸出改依粗目切九架寫到 `--out <目錄>`）。

驗五種情況（keep／move／merge／split／see_also 改寫與丟棄）各一案、policy 衝突 exit 2、
同一講法掛兩細目 exit 2、target_user 缺必填 exit 2、決定性（同輸入兩次逐位元相等）、
`parse_canon_dir` 回讀成功。輸入正本沿用單檔封存格式（`--canon` 讀單檔仍要能讀封存檔）；
輸出固定九架，未被提議提及的架落內建預設標題／scope（`schemas/coarses-jgb.json`／
`schemas/scopes-jgb.json`）、零細目。
"""
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:9.3.5")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
_SCRIPTS = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts")


def _run(args, cwd=None):
    return subprocess.run([sys.executable, os.path.join(_SCRIPTS, args[0])] + args[1:],
                           capture_output=True, text=True, cwd=cwd or _REPO)


# ⚠️ 輸入正本刻意用**舊制單檔封存格式**（`audience: prospect` 前綴、非九架目錄）——這是
# `--canon` 讀單檔（封存檔）能力本身的測試對象，⛔ 不是殘留：canon_parser.AUDIENCES 仍固定
# 收 prospect／property_manager／tenant 三值，單檔正本的細目 id 沿用這三值當第一段，與
# 圖書館正本（本 skill 唯一正本，id 首段固定 jgb）是兩套並存、各自有效的形態。
_CANON = """---
audience: prospect
version: 2026-09-01.0
reviewers: [owner]
language: zh-TW
budget_tokens: 8000
target_user: [prospect]
business_types: [system_provider]
---
## A 產品定位 {#A}
### 系統定位 {#prospect/A/positioning}
- phrasings:
  - {text: "系統簡介", source: "helpcenter:intro-slug", status: approved}
- sources: [kb:1]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-01}
金箍棒把物件、合約、收租集中管理。

### 舊系統資料能否匯入 {#prospect/A/data-migration}
- see_also: [prospect/A/migration-limits]
- sources: [kb:2]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-01}
可以匯入既有物件與合約資料。

### 資料搬遷限制 {#prospect/A/migration-limits}
- see_also: [prospect/A/data-migration]
- sources: [kb:3]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-01}
歷史帳單不支援搬遷。

### 收租對帳自動化 {#prospect/A/rent-collection}
- sources: [kb:4]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-01}
帳單自動產生，收租可線上對帳。

### 收租對帳費用說明 {#prospect/A/rent-collection-fee}
- sources: [kb:5]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-01}
費用依方案而定。

### 電子發票與載具 {#prospect/A/einvoice}
- phrasings:
  - {text: "電子發票怎麼開", source: "koyu:x#1", status: approved}
  - {text: "載具怎麼用", source: "koyu:x#2", status: approved}
- sources: [kb:6]
- instance_applicability: general
- reviewed: {by: owner, at: 2026-09-01}
系統可自動開立電子發票並支援載具設定。
帳務總覽也顯示發票狀態。
"""


@pytest.fixture
def canon_file(tmp_path):
    p = tmp_path / "canon.md"
    p.write_text(_CANON, encoding="utf-8")
    return str(p)


def _synthesis(extra_fines=(), extra_id_map=()):
    fines = [
        {"id": "jgb/A/positioning", "coarse_id": "A", "title": "系統定位", "slug": "positioning",
         "merge_of": ["tmp:kb:prospect/A/positioning"], "split_from": [], "moved_from": [], "reason": "keep",
         "target_user": ["prospect"]},
        {"id": "jgb/B/data-migration", "coarse_id": "B", "title": "舊系統資料能否匯入", "slug": "data-migration",
         "merge_of": ["tmp:kb:prospect/A/data-migration"], "split_from": [], "moved_from": [], "reason": "move",
         "target_user": ["prospect"]},
        {"id": "jgb/B/migration-limits", "coarse_id": "B", "title": "資料搬遷限制", "slug": "migration-limits",
         "merge_of": ["tmp:kb:prospect/A/migration-limits"], "split_from": [], "moved_from": [], "reason": "move",
         "target_user": ["prospect"]},
        {"id": "jgb/C/rent-collection-overview", "coarse_id": "C", "title": "收租對帳總覽", "slug": "rent-collection-overview",
         "merge_of": ["tmp:kb:prospect/A/rent-collection", "tmp:kb:prospect/A/rent-collection-fee"],
         "split_from": [], "moved_from": [], "reason": "merge", "target_user": ["prospect"]},
        {"id": "jgb/C/einvoice-issuing", "coarse_id": "C", "title": "電子發票開立", "slug": "einvoice-issuing",
         "merge_of": ["tmp:kb:prospect/A/einvoice"], "split_from": ["tmp:kb:prospect/A/einvoice"],
         "moved_from": [], "reason": "split", "target_user": ["prospect"]},
        {"id": "jgb/C/einvoice-invoice-status", "coarse_id": "C", "title": "發票狀態顯示", "slug": "einvoice-invoice-status",
         "merge_of": ["tmp:kb:prospect/A/einvoice"], "split_from": ["tmp:kb:prospect/A/einvoice"],
         "moved_from": [], "reason": "split", "target_user": ["prospect"]},
        *extra_fines,
    ]
    id_map = [
        {"old": "tmp:kb:prospect/A/positioning", "new": "jgb/A/positioning", "op": "keep"},
        {"old": "tmp:kb:prospect/A/data-migration", "new": "jgb/B/data-migration", "op": "move"},
        {"old": "tmp:kb:prospect/A/migration-limits", "new": "jgb/B/migration-limits", "op": "move"},
        {"old": "tmp:kb:prospect/A/rent-collection", "new": "jgb/C/rent-collection-overview", "op": "merge"},
        {"old": "tmp:kb:prospect/A/rent-collection-fee", "new": "jgb/C/rent-collection-overview", "op": "merge"},
        {"old": "tmp:kb:prospect/A/einvoice", "new": "jgb/C/einvoice-issuing", "op": "split"},
        {"old": "tmp:kb:prospect/A/einvoice", "new": "jgb/C/einvoice-invoice-status", "op": "split"},
        *extra_id_map,
    ]
    return {
        "angle": "synthesis",
        "coarses": [{"id": "A", "title": "產品定位"}, {"id": "B", "title": "資料搬遷"}, {"id": "C", "title": "帳務模組"}],
        "fines": fines, "id_map": id_map, "rejected_alternatives": [],
    }


def _apply(tmp_path, canon_file, synthesis, suffix="", extra_args=()):
    prop = tmp_path / f"syn{suffix}.json"
    prop.write_text(json.dumps(synthesis, ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / f"out{suffix}"
    r = _run(["apply_proposal.py", "--proposal", str(prop), "--canon", canon_file, "--version", "2026-09-15.0",
              "--out", str(out_dir), *extra_args])
    idmap = out_dir / "id_map.json"
    pending_dir = out_dir / "pending"
    return r, out_dir, idmap, pending_dir


def _shelf(out_dir, code):
    return (out_dir / f"{code}.md").read_text(encoding="utf-8")


def test_keep_carries_phrasings_verbatim_and_drops_reviewed_per_target_user_contract(tmp_path, canon_file):
    """9.6 S4：target_user 改由提議必填驅動（⛔ 不再沿用來源），reviewed 沿用來源既有值（keep 分支不變）。"""
    r, out_dir, idmap, pending_dir = _apply(tmp_path, canon_file, _synthesis())
    assert r.returncode == 0, r.stderr
    text = _shelf(out_dir, "A")
    assert "### 系統定位 {#jgb/A/positioning}" in text
    assert '{text: "系統簡介", source: "helpcenter:intro-slug", status: approved}' in text
    assert "- reviewed: {by: owner, at: 2026-09-01}" in text
    assert "- target_user: [prospect]" in text
    assert "- business_types: [system_provider]" in text


def test_move_changes_id_and_carries_attrs_and_rewrites_see_also(tmp_path, canon_file):
    r, out_dir, idmap, pending_dir = _apply(tmp_path, canon_file, _synthesis())
    assert r.returncode == 0, r.stderr
    text = _shelf(out_dir, "B")
    assert "### 舊系統資料能否匯入 {#jgb/B/data-migration}" in text
    assert "- see_also: [jgb/B/migration-limits]" in text  # 目標同為 1:1 move ⇒ 改寫成功
    assert "- reviewed: {by: owner, at: 2026-09-01}" in text
    pending_see_also = json.loads((pending_dir / "pending-see_also.json").read_text(encoding="utf-8"))
    assert pending_see_also == []  # 兩者都是 1:1 move，改寫成功、無待審


def test_merge_unions_and_dedupes_and_drops_reviewed(tmp_path, canon_file):
    r, out_dir, idmap, pending_dir = _apply(tmp_path, canon_file, _synthesis())
    assert r.returncode == 0, r.stderr
    text = _shelf(out_dir, "C")
    assert "### 收租對帳總覽 {#jgb/C/rent-collection-overview}" in text
    assert "- sources: [kb:4, kb:5]" in text
    assert "帳單自動產生，收租可線上對帳。" in text
    assert "費用依方案而定。" in text
    # merge 命中內容改變 ⇒ reviewed 丟棄
    block = text.split("### 收租對帳總覽")[1].split("### 電子發票開立")[0]
    assert "reviewed" not in block


def test_split_copies_full_content_to_each_child_and_drops_phrasings_to_pending(tmp_path, canon_file):
    r, out_dir, idmap, pending_dir = _apply(tmp_path, canon_file, _synthesis())
    assert r.returncode == 0, r.stderr
    text = _shelf(out_dir, "C")
    for heading in ("### 電子發票開立 {#jgb/C/einvoice-issuing}", "### 發票狀態顯示 {#jgb/C/einvoice-invoice-status}"):
        block = text.split(heading)[1]
        assert "系統可自動開立電子發票並支援載具設定。" in block
        assert "帳務總覽也顯示發票狀態。" in block
        assert "phrasings" not in block.split("###")[0]  # 講法全丟到 pending，不掛任一子細目
    pending_splits = json.loads((pending_dir / "pending-splits.json").read_text(encoding="utf-8"))
    assert len(pending_splits) == 1
    assert pending_splits[0]["old"] == "tmp:kb:prospect/A/einvoice"
    assert sorted(pending_splits[0]["children"]) == ["jgb/C/einvoice-invoice-status", "jgb/C/einvoice-issuing"]
    pending_phrasings = json.loads((pending_dir / "pending-phrasings.json").read_text(encoding="utf-8"))
    assert {p["text"] for p in pending_phrasings} == {"電子發票怎麼開", "載具怎麼用"}
    for p in pending_phrasings:
        assert p["from_old"] == "tmp:kb:prospect/A/einvoice"
        assert sorted(p["candidates"]) == ["jgb/C/einvoice-invoice-status", "jgb/C/einvoice-issuing"]


def test_see_also_target_dropped_when_target_is_split(tmp_path, canon_file):
    """data-migration 的 see_also 目標若改指向被拆分的 einvoice ⇒ 丟棄並記 pending-see_also。"""
    canon_with_dangling_see_also = _CANON.replace(
        "### 舊系統資料能否匯入 {#prospect/A/data-migration}\n- see_also: [prospect/A/migration-limits]",
        "### 舊系統資料能否匯入 {#prospect/A/data-migration}\n- see_also: [prospect/A/migration-limits, prospect/A/einvoice]",
    )
    p = tmp_path / "canon2.md"
    p.write_text(canon_with_dangling_see_also, encoding="utf-8")
    r, out_dir, idmap, pending_dir = _apply(tmp_path, str(p), _synthesis(), suffix="2")
    assert r.returncode == 0, r.stderr
    text = _shelf(out_dir, "B")
    assert "- see_also: [jgb/B/migration-limits]" in text  # einvoice 目標被丟棄，只留改寫成功的一個
    pending_see_also = json.loads((pending_dir / "pending-see_also.json").read_text(encoding="utf-8"))
    assert {(x["target_old"], x["reason"]) for x in pending_see_also} == {("prospect/A/einvoice", "target_split")}


def test_policy_conflict_on_merge_exits_2(tmp_path, canon_file):
    canon_with_policy = _CANON.replace(
        "### 收租對帳費用說明 {#prospect/A/rent-collection-fee}\n- sources: [kb:5]",
        "### 收租對帳費用說明 {#prospect/A/rent-collection-fee}\n- policy: deliberate_no\n- sources: [kb:5]",
    )
    p = tmp_path / "canon3.md"
    p.write_text(canon_with_policy, encoding="utf-8")
    r, out_dir, idmap, pending_dir = _apply(tmp_path, str(p), _synthesis(), suffix="3")
    assert r.returncode == 2
    assert "policy" in r.stderr
    assert "jgb/C/rent-collection-overview" in r.stderr
    assert not out_dir.exists() or not (out_dir / "A.md").exists()  # fail-closed：拒套不落任何架


def test_duplicate_phrasing_across_two_fines_exits_2(tmp_path, canon_file):
    """守門（a）：兩個 keep 細目若掛同一句講法 ⇒ 拒套。"""
    canon_dup = _CANON.replace(
        '### 舊系統資料能否匯入 {#prospect/A/data-migration}\n- see_also: [prospect/A/migration-limits]',
        '### 舊系統資料能否匯入 {#prospect/A/data-migration}\n- see_also: [prospect/A/migration-limits]\n'
        '- phrasings:\n  - {text: "系統簡介", source: "helpcenter:dup", status: approved}',
    )
    p = tmp_path / "canon4.md"
    p.write_text(canon_dup, encoding="utf-8")
    r, out_dir, idmap, pending_dir = _apply(tmp_path, str(p), _synthesis(), suffix="4")
    assert r.returncode == 2
    assert "系統簡介" in r.stderr


def test_target_user_missing_on_one_fine_exits_2(tmp_path, canon_file):
    """9.6 S4：target_user 現由提議必填驅動；缺一筆 ⇒ 拒套，且不落任何架（正對照見上一測試的成功案例）。"""
    bad = _synthesis()
    del bad["fines"][0]["target_user"]
    r, out_dir, idmap, pending_dir = _apply(tmp_path, canon_file, bad, suffix="_notu")
    assert r.returncode == 2
    assert "target_user" in r.stderr
    assert "jgb/A/positioning" in r.stderr
    assert not (out_dir / "A.md").exists()


def test_deterministic_byte_identical(tmp_path, canon_file):
    syn = _synthesis()
    r1, out1, idmap1, _ = _apply(tmp_path, canon_file, syn, suffix="_a")
    r2, out2, idmap2, _ = _apply(tmp_path, canon_file, syn, suffix="_b")
    assert r1.returncode == 0 and r2.returncode == 0
    for code in ("A", "B", "C", "D", "E", "F", "G", "H", "I"):
        assert (out1 / f"{code}.md").read_bytes() == (out2 / f"{code}.md").read_bytes()
    assert idmap1.read_bytes() == idmap2.read_bytes()


def test_output_reparses_via_parse_canon_dir_and_produces_catalog(tmp_path, canon_file):
    r, out_dir, idmap, pending_dir = _apply(tmp_path, canon_file, _synthesis())
    assert r.returncode == 0, r.stderr
    idmap_data = json.loads(idmap.read_text(encoding="utf-8"))
    assert "canon_sha256" in idmap_data
    assert len(idmap_data["canon_sha256"]) == 64
    assert (out_dir / "CATALOG.md").is_file()
    assert (out_dir / "jgb.json").is_file()
    # 未被提議提及的架（D…I）仍要備齊、零細目、標題落內建預設
    empty_text = _shelf(out_dir, "H")
    assert "coarse: H" in empty_text and "{#H-shelf}" in empty_text
    assert "###" not in empty_text


def test_kb_rows_and_canon_mutually_exclusive(tmp_path, canon_file):
    prop = tmp_path / "syn.json"
    prop.write_text(json.dumps(_synthesis(), ensure_ascii=False), encoding="utf-8")
    kb = tmp_path / "kb.json"
    kb.write_text(json.dumps({"rows": []}, ensure_ascii=False), encoding="utf-8")
    r = _run(["apply_proposal.py", "--proposal", str(prop), "--kb-rows", str(kb), "--canon", canon_file,
              "--version", "v", "--out", str(tmp_path / "out")])
    assert r.returncode == 2
    assert "二擇一" in r.stderr


def test_canon_mode_requires_out(tmp_path, canon_file):
    """9.6 S4：`--out-pending-dir` 已有預設（`<out>/pending`），改為必給 `--out`（九架輸出目錄）。"""
    prop = tmp_path / "syn.json"
    prop.write_text(json.dumps(_synthesis(), ensure_ascii=False), encoding="utf-8")
    r = _run(["apply_proposal.py", "--proposal", str(prop), "--canon", canon_file, "--version", "v"])
    assert r.returncode == 2
    assert "--out" in r.stderr


def test_canon_mode_scopes_and_version_default_from_bundled_and_source(tmp_path, canon_file):
    """最小可只給 --canon／--proposal／--out（version 沿用來源正本、scope 落 schemas/scopes-jgb.json 內建預設）。"""
    prop = tmp_path / "syn.json"
    prop.write_text(json.dumps(_synthesis(), ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "outmin"
    r = _run(["apply_proposal.py", "--proposal", str(prop), "--canon", canon_file, "--out", str(out_dir)])
    assert r.returncode == 0, r.stderr
    text = _shelf(out_dir, "A")
    assert "version: 2026-09-01.0" in text  # 沿用來源正本 version（未給 --version）
    assert "scope: " in text and "scope: \n" not in text  # 內建預設非空
