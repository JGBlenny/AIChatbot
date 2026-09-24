"""attach_phrasings 圖書館模式（`--shelf`）的架歸屬判定（計畫 9.10 S5 第二輪、DSP-070）。

⚠️ 為什麼有這一檔：`fines_without_phrasings` 曾用 `f.coarse_id == a.shelf` 判「屬於這一架」，
粗目 id 自 S1 起是 `A-registration` 這種形狀 ⇒ 對現行正本恆回空，而既有 attach 測試只跑單檔模式，
改回舊寫法也不會紅（S5 verifier F1）。這裡用新形態 fixture 九架走 `--shelf`，釘住「該架確實有
無講法細目時，報告不得是空的」。
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:9.10")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))  # 容器內＝/（.claude 掛在 /.claude）
_RAG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))  # rag-orchestrator 根（容器內＝/app）
_SCRIPT = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts", "attach_phrasings.py")
_SHELVES = os.path.join(_RAG, "tests", "fixtures", "canon_jgb", "shelves")
_TARGET = "jgb/A/password-reset"


def _strip_phrasings(md: str, fine_id: str) -> str:
    """拿掉某一細目的 `- phrasings:` 區塊（屬性行＋其下兩格縮排的講法行）。"""
    lines = md.split("\n")
    out, in_fine, skipping = [], False, False
    for line in lines:
        if line.startswith("### "):
            in_fine = line.rstrip().endswith("{#" + fine_id + "}")
            skipping = False
        if in_fine and line == "- phrasings:":
            skipping = True
            continue
        if skipping and line.startswith("  - "):
            continue
        skipping = False
        out.append(line)
    return "\n".join(out)


def test_shelf_mode_reports_fines_without_phrasings_on_multi_coarse_shelf(tmp_path):
    if not os.path.exists(_SCRIPT):
        pytest.skip("attach_phrasings.py 不在掛載路徑")
    canon = tmp_path / "canon"
    shutil.copytree(_SHELVES, canon)
    a_md = (canon / "A.md").read_text(encoding="utf-8")
    # 正對照：fixture 的 A 架粗目 id 不是裸字母（否則本測試量不到 S5 的病灶）
    assert re.search(r"^## .+\{#A-[a-z0-9-]+\}\s*$", a_md, re.M), "fixture A 架須為新形態粗目"
    stripped = _strip_phrasings(a_md, _TARGET)
    assert stripped != a_md, f"fixture 須含 {_TARGET} 的講法區塊（正對照）"
    (canon / "A.md").write_text(stripped, encoding="utf-8")

    pm = tmp_path / "pm.json"
    pm.write_text(json.dumps({"step": "phrasing", "payload": {"phrasings": [], "similar_pairs": []}}), encoding="utf-8")
    rep = tmp_path / "rep.json"
    r = subprocess.run(
        [sys.executable, _SCRIPT, "--canon", str(canon), "--phrasing-map", str(pm),
         "--out", str(tmp_path / "out"), "--report", str(rep), "--shelf", "A"],
        capture_output=True, text=True, cwd=_REPO,
    )
    assert r.returncode == 0, r.stderr
    report = json.loads(rep.read_text(encoding="utf-8"))
    assert _TARGET in report["fines_without_phrasings"]
    assert all(fid.split("/")[1] == "A" for fid in report["fines_without_phrasings"])
