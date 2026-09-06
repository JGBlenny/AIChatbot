"""unit：`.claude/workflows/outline-curation.js`（knowledge-outline-and-intent-architecture 任務 1.4｜design 元件 2）。

JS 沒有測試跑道：用 `node --check`（若 host 有 node）驗語法；再以純文字／正則斷言
`export const meta` 為純字面（無 `${`、無函式呼叫）、含 `pipeline(`、`effort: 'low'`、
⛔ 無 `Date.now`／`Math.random`。
"""
import os
import re
import shutil
import subprocess

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:1.5")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
_JS = os.path.join(_REPO, ".claude", "workflows", "outline-curation.js")


def _skip_if_missing():
    if not os.path.isfile(_JS):
        pytest.skip(f"[env] 找不到 {_JS}——容器需掛 repo 根 .claude/，宿主直跑本檔")


def _text():
    with open(_JS, encoding="utf-8") as f:
        return f.read()


def test_file_exists():
    _skip_if_missing()


def test_node_check_syntax_ok_if_node_available():
    _skip_if_missing()
    node = shutil.which("node")
    if not node:
        pytest.skip("[env] host 無 node，跳過語法檢查（answerability_args.py 等 Python 部分不受影響）")
    r = subprocess.run([node, "--check", _JS], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def _meta_block(text: str) -> str:
    m = re.search(r"export const meta\s*=\s*\{", text)
    assert m, "找不到 export const meta = {...}"
    start = m.end() - 1  # 指到那個 '{'
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise AssertionError("meta 物件括號不平衡")


def test_meta_is_pure_literal():
    _skip_if_missing()
    text = _text()
    meta_src = _meta_block(text)
    assert "${" not in meta_src, "meta 內不得有樣板字串插值"
    # 不得呼叫函式（如 Date.now()、require(...)）——找「識別字(」的模式，
    # 但允許物件屬性語法本身（沒有函式呼叫時不會出現這個模式）
    call_like = re.findall(r"[A-Za-z_$][A-Za-z0-9_$.]*\s*\(", meta_src)
    assert not call_like, f"meta 內偵測到疑似函式呼叫：{call_like}"
    assert "name:" in meta_src and "description:" in meta_src
    assert "phases:" in meta_src


def test_contains_pipeline_and_low_effort_and_no_forbidden_apis():
    _skip_if_missing()
    text = _text()
    assert "pipeline(" in text
    assert "effort: 'low'" in text
    assert "Date.now" not in text
    assert "Math.random" not in text
    assert "new Date(" not in text


def test_structure_step_throws_placeholder():
    _skip_if_missing()
    text = _text()
    assert "args.step === 'structure'" in text
    assert "throw new Error" in text


def test_verdict_schema_uses_fine_id_enum_from_args():
    _skip_if_missing()
    text = _text()
    assert "args.fineIdEnum" in text
    assert "provisional" in text
    assert "needs_rubric_revision" in text


def test_judges_do_not_see_each_others_verdicts():
    """判者互不可見：三個 agent() 呼叫的 prompt 只能是 `promptOf(c)`／`promptOf(r.c)`，
    ⛔ 不把 v1（或 v2）字面塞進 prompt 字串。promptOf 本身只拼 judgePrompt 或四段
    （promptHead／cellBlock／candidatesBlock／cellTail），⛔ 不讀其他欄位。"""
    _skip_if_missing()
    text = _text()
    calls = re.findall(r"agent\((promptOf\([\w.]+\)|[\w.]+),", text)
    assert len(calls) == 3, f"預期 3 個 agent() 呼叫，找到 {len(calls)}：{calls}"
    for c in calls:
        assert c.strip() in ("promptOf(c)", "promptOf(r.c)")
    m = re.search(r"const promptOf = c => (.+)", text)
    assert m, "找不到 promptOf 定義"
    body = m.group(1)
    allowed = {"c.judgePrompt", "args.promptHead", "c.cellBlock", "args.candidatesBlock", "c.cellTail"}
    refs = set(re.findall(r"\b(?:c|args)\.[\w]+", body))
    assert refs == allowed, f"promptOf 只能拼白名單欄位：{refs}"
