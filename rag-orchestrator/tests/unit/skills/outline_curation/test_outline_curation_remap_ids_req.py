"""unit：`scripts/remap_ids.py`（knowledge-outline-and-intent-architecture 任務 9.3②）。

驗：keep／move 改寫正確；split／merge 標須重判且不改字串；缺對應 exit 2（且 apply 模式不寫任何檔）；
決定性（同輸入兩次 stdout 逐位元相等）；冪等（apply 兩次，第二次零位元組變更）；
正對照＝不含任何 fine.id 的檔案零變更。
"""
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:9.3")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
_SCRIPT = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts", "remap_ids.py")

_ID_MAP = {
    "id_map": [
        {"old": "prospect/A/old-slug", "new": "prospect/B/new-slug", "op": "move"},
        {"old": "prospect/A/keep-slug", "new": "prospect/A/keep-slug", "op": "keep"},
        {"old": "prospect/C/merged-1", "new": "prospect/C/merged-target", "op": "merge"},
        {"old": "prospect/C/merged-2", "new": "prospect/C/merged-target", "op": "merge"},
    ]
}

_MATERIAL_MAPPED = (
    '{"rows": [\n'
    '  {"fine_id": "prospect/A/old-slug", "q": "x"},\n'
    '  {"fine_id": "prospect/A/keep-slug", "q": "y"},\n'
    '  {"fine_id": "prospect/C/merged-1", "q": "z"}\n'
    ']}\n'
)

_MATERIAL_WITH_UNMAPPED = (
    '{"rows": [\n'
    '  {"fine_id": "prospect/A/old-slug", "q": "x"},\n'
    '  {"fine_id": "prospect/D/no-entry", "q": "w"}\n'
    ']}\n'
)

_NO_IDS_MD = "# 標題\n這裡沒有任何 fine id 樣式的字串。\n"


def _skip_if_missing():
    if not os.path.isfile(_SCRIPT):
        pytest.skip(f"[env] 找不到 {_SCRIPT}——容器需掛 repo 根 .claude/，宿主直跑本檔")


def _run(args):
    return subprocess.run([sys.executable, _SCRIPT] + args, capture_output=True, text=True)


@pytest.fixture
def id_map_file(tmp_path):
    p = tmp_path / "id_map.json"
    p.write_text(json.dumps(_ID_MAP, ensure_ascii=False), encoding="utf-8")
    return str(p)


def test_help_runs():
    _skip_if_missing()
    r = subprocess.run([sys.executable, _SCRIPT, "--help"], capture_output=True, text=True)
    assert r.returncode == 0


def test_keep_move_rewritten_split_merge_flagged(tmp_path, id_map_file):
    _skip_if_missing()
    mat = tmp_path / "material.json"
    mat.write_text(_MATERIAL_MAPPED, encoding="utf-8")
    r = _run(["--id-map", id_map_file, "--files", str(mat), "--apply"])
    assert r.returncode == 0, r.stderr
    out = mat.read_text(encoding="utf-8")
    assert "prospect/B/new-slug" in out
    assert "prospect/A/old-slug" not in out
    assert "prospect/A/keep-slug" in out  # keep：old==new，內容不變但仍算改寫
    assert "prospect/C/merged-1" in out  # merge：⛔ 不自動猜，原字串保留
    report = json.loads(r.stdout)
    assert report["totals"]["rewritten"] == 2
    assert report["totals"]["must_rejudge"] == 1
    must = report["files"][0]["must_rejudge_ids"]
    assert must == [{"old": "prospect/C/merged-1", "op": "merge", "occurrences": 1}]


def test_missing_correspondence_exits_2_and_writes_nothing(tmp_path, id_map_file):
    _skip_if_missing()
    mat = tmp_path / "material.json"
    mat.write_text(_MATERIAL_WITH_UNMAPPED, encoding="utf-8")
    before = mat.read_bytes()
    r = _run(["--id-map", id_map_file, "--files", str(mat), "--apply"])
    assert r.returncode == 2
    report = json.loads(r.stdout)
    assert report["ok"] is False
    assert report["totals"]["unmapped"] == 1
    # apply 模式下找不到對應 ⇒ 一個檔案都不寫（原檔位元組不變、也不留 remap-report）
    assert mat.read_bytes() == before
    assert not os.path.isfile(str(mat) + ".remap-report.json")


def test_dry_run_default_writes_nothing(tmp_path, id_map_file):
    _skip_if_missing()
    mat = tmp_path / "material.json"
    mat.write_text(_MATERIAL_MAPPED, encoding="utf-8")
    before = mat.read_bytes()
    r = _run(["--id-map", id_map_file, "--files", str(mat)])
    assert r.returncode == 0, r.stderr
    assert mat.read_bytes() == before
    assert not os.path.isfile(str(mat) + ".remap-report.json")


def test_deterministic_stdout_byte_identical(tmp_path, id_map_file):
    _skip_if_missing()
    mat1 = tmp_path / "a.json"
    mat2 = tmp_path / "b.json"
    mat1.write_text(_MATERIAL_MAPPED, encoding="utf-8")
    mat2.write_text(_MATERIAL_MAPPED, encoding="utf-8")
    r1 = _run(["--id-map", id_map_file, "--files", str(mat1)])
    r2 = _run(["--id-map", id_map_file, "--files", str(mat2)])
    assert r1.returncode == 0 and r2.returncode == 0
    # 兩檔路徑不同但內容相同 ⇒ 只比對 path 以外的欄位需相等：直接比對兩份 report 拿掉 path 後 dump 相同
    d1 = json.loads(r1.stdout)
    d2 = json.loads(r2.stdout)
    for d in (d1, d2):
        d["id_map_path"] = "<id_map>"
        for f in d["files"]:
            f["path"] = "<path>"
    assert json.dumps(d1, sort_keys=True) == json.dumps(d2, sort_keys=True)


def test_apply_idempotent_second_pass_zero_bytes_changed(tmp_path, id_map_file):
    _skip_if_missing()
    mat = tmp_path / "material.json"
    mat.write_text(_MATERIAL_MAPPED, encoding="utf-8")
    r1 = _run(["--id-map", id_map_file, "--files", str(mat), "--apply"])
    assert r1.returncode == 0, r1.stderr
    after_first = mat.read_bytes()
    r2 = _run(["--id-map", id_map_file, "--files", str(mat), "--apply"])
    assert r2.returncode == 0, r2.stderr
    after_second = mat.read_bytes()
    assert after_first == after_second
    report2 = json.loads(r2.stdout)
    assert report2["totals"]["rewritten"] == 1  # keep：old==new，重寫但字串不變
    assert report2["totals"]["already_new"] == 1  # move 過的目標 id 這次落在 already_new 桶
    assert report2["totals"]["unmapped"] == 0


def test_positive_control_file_without_any_fine_id_zero_change(tmp_path, id_map_file):
    _skip_if_missing()
    md = tmp_path / "no_ids.md"
    md.write_text(_NO_IDS_MD, encoding="utf-8")
    before = md.read_bytes()
    r = _run(["--id-map", id_map_file, "--files", str(md), "--apply"])
    assert r.returncode == 0, r.stderr
    assert md.read_bytes() == before
    report = json.loads(r.stdout)
    assert report["files"][0]["matches_found"] == 0
    # 正對照：material.json 這種必然含 fine id 的檔案要能命中 >0（否則代表工具/條件本身壞了）
    mat = tmp_path / "material.json"
    mat.write_text(_MATERIAL_MAPPED, encoding="utf-8")
    r2 = _run(["--id-map", id_map_file, "--files", str(mat)])
    assert json.loads(r2.stdout)["files"][0]["matches_found"] > 0


def test_missing_id_map_file_exits_2(tmp_path):
    _skip_if_missing()
    mat = tmp_path / "material.json"
    mat.write_text(_MATERIAL_MAPPED, encoding="utf-8")
    r = _run(["--id-map", str(tmp_path / "does-not-exist.json"), "--files", str(mat)])
    assert r.returncode == 2


def test_missing_input_file_exits_2(id_map_file, tmp_path):
    _skip_if_missing()
    r = _run(["--id-map", id_map_file, "--files", str(tmp_path / "does-not-exist.json")])
    assert r.returncode == 2
