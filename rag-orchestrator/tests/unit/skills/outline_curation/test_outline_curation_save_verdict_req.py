"""unit：`scripts/save_verdict.py`（knowledge-outline-and-intent-architecture 步 4 判者回收）。

驗：取 transcript 最後一則 assistant 文字；容忍 ```json 圍欄與前後散文；寫 `<out-dir>/verdicts/<key>.json`；
無 assistant 文字 ⇒ exit 2 不寫檔（正對照：同格式但有文字者必成功）。
"""
import json
import os
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:2.4")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
_SCRIPT = os.path.join(_REPO, ".claude", "skills", "outline-curation", "scripts", "save_verdict.py")


def _skip_if_missing():
    if not os.path.isfile(_SCRIPT):
        pytest.skip(f"[env] 找不到 {_SCRIPT}——容器需掛 repo 根 .claude/")


def _transcript(path, texts, trailing_user=True):
    lines = [json.dumps({"message": {"role": "user", "content": [{"type": "text", "text": "prompt"}]}})]
    for t in texts:
        lines.append(json.dumps({"message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Read"}, {"type": "text", "text": t}]}}))
    if trailing_user:
        lines.append(json.dumps({"type": "result", "message": {"role": "user", "content": "x"}}))
    lines.append("not json at all")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _run(key, transcript, out_dir):
    return subprocess.run([sys.executable, _SCRIPT, key, transcript, "--out-dir", out_dir],
                          capture_output=True, text=True)


_ARR = [{"cell_id": "C01", "label": "answerable", "fine_id": "prospect/A/x", "confidence": 0.9}]


def test_takes_last_assistant_text_and_tolerates_fence_and_prose(tmp_path):
    _skip_if_missing()
    tr = tmp_path / "t.jsonl"
    _transcript(tr, ["讀完了。", "結果如下：\n```json\n" + json.dumps(_ARR, ensure_ascii=False) + "\n```\n以上。"])
    r = _run("g1-s1", str(tr), str(tmp_path / "out"))
    assert r.returncode == 0, r.stderr
    got = json.load(open(tmp_path / "out" / "verdicts" / "g1-s1.json", encoding="utf-8"))
    assert got == _ARR


def test_no_assistant_text_exits_2_without_writing(tmp_path):
    _skip_if_missing()
    tr = tmp_path / "empty.jsonl"
    _transcript(tr, [])
    r = _run("g1-s2", str(tr), str(tmp_path / "out"))
    assert r.returncode == 2
    assert "無 assistant 文字" in r.stderr
    assert not os.path.exists(tmp_path / "out" / "verdicts" / "g1-s2.json")
    # 正對照：同一寫法但有文字者必成功
    tr2 = tmp_path / "ok.jsonl"
    _transcript(tr2, [json.dumps(_ARR)])
    assert _run("g1-s3", str(tr2), str(tmp_path / "out")).returncode == 0


def test_non_array_json_exits_2(tmp_path):
    _skip_if_missing()
    tr = tmp_path / "obj.jsonl"
    _transcript(tr, ['{"cell_id": "C01"}'])
    r = _run("g1-s4", str(tr), str(tmp_path / "out"))
    assert r.returncode == 2
    assert "解析失敗" in r.stderr
