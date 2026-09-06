"""unit：repo 層 hook 接線必須真的接得上（knowledge-outline-and-intent-architecture 任務 1.1｜R1.4）。

**為什麼需要這條**：design 元件 3 把四道紀律交給 `.claude/settings.json` 的 hook；
hook 的 command 是字串，寫錯一個路徑就是「靜默失效」——事件照跑、腳本找不到、`|| exit 0` 放行，
沒有任何紅燈。本檔驗的是**接線**而非腳本邏輯（腳本邏輯由 1.2 的 `test_outline_gate_req.py` 驗）：

  ① `.claude/settings.json` 三個事件（PreToolUse／PostToolUse／Stop）都掛了 `outline_gate.py`；
  ② Edit／Write 事件的 matcher 為 `Edit|Write`；
  ③ 每條 command 把 `$CLAUDE_PROJECT_DIR` 代入 repo 根後，腳本檔**必須存在**；
  ④ 正對照：故意把路徑改壞 ⇒ 同一判定必紅（證明③不是恆真）。

⚠️ 測試容器只掛 `rag-orchestrator`／`docs`／`.kiro`（docker-compose.dev.yml），看不到 repo 根的 `.claude/`。
容器內跑到本檔會 **skip 並印明原因**（`[env]` 前綴），⛔ 不得靜默綠；宿主直跑（`python3 -m pytest`）才是真驗。
"""
import json
import os
import re

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:1.4")]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
_SETTINGS = os.path.join(_REPO, ".claude", "settings.json")
_SCRIPT_REL = ".claude/hooks/outline_gate.py"
_EVENTS = ("PreToolUse", "PostToolUse", "Stop")
_CMD_RE = re.compile(r'\$CLAUDE_PROJECT_DIR/([^"\' ]+)')


def _load_settings() -> dict:
    if not os.path.isdir(os.path.join(_REPO, ".claude")):
        pytest.skip("[env] 容器內看不到 repo 根 .claude/（compose 只掛 rag-orchestrator）；請於宿主直跑本檔")
    assert os.path.isfile(_SETTINGS), f"缺 {_SETTINGS}（任務 1.1 應建立）"
    with open(_SETTINGS, encoding="utf-8") as f:
        return json.load(f)


def _outline_commands(settings: dict, event: str) -> list:
    """回 (matcher, command) 清單——只取掛 outline_gate.py 的條目。"""
    out = []
    for entry in (settings.get("hooks") or {}).get(event) or []:
        for h in entry.get("hooks") or []:
            cmd = h.get("command") or ""
            if "outline_gate.py" in cmd:
                out.append((entry.get("matcher"), cmd))
    return out


def _resolved_paths(cmd: str, project_dir: str) -> list:
    """把 command 裡每個 `$CLAUDE_PROJECT_DIR/<path>` 代入 project_dir。"""
    return [os.path.join(project_dir, rel) for rel in _CMD_RE.findall(cmd)]


def test_three_events_wired():
    s = _load_settings()
    for ev in _EVENTS:
        assert _outline_commands(s, ev), f"{ev} 未掛 outline_gate.py"


def test_edit_write_matcher_exact():
    s = _load_settings()
    for ev in ("PreToolUse", "PostToolUse"):
        matchers = {m for m, _ in _outline_commands(s, ev)}
        assert matchers == {"Edit|Write"}, f"{ev} matcher 應為 Edit|Write，實得 {matchers}"


def test_command_shape_uses_project_dir_and_fail_open():
    s = _load_settings()
    for ev in _EVENTS:
        for _, cmd in _outline_commands(s, ev):
            assert "$CLAUDE_PROJECT_DIR/" in cmd, f"{ev} command 未用 $CLAUDE_PROJECT_DIR：{cmd}"
            assert "$REPO" not in cmd, "⛔ $REPO 只是 check_invariants.sh 內部變數（design F11）"
            assert cmd.rstrip().endswith("|| exit 0'"), f"{ev} command 缺檔未放行：{cmd}"


def test_script_exists_after_substitution():
    s = _load_settings()
    seen = 0
    for ev in _EVENTS:
        for _, cmd in _outline_commands(s, ev):
            for p in _resolved_paths(cmd, _REPO):
                seen += 1
                assert os.path.isfile(p), f"{ev} 代入 repo 根後腳本不存在：{p}"
    assert seen >= 3, "正對照失敗：command 內解析不到任何 $CLAUDE_PROJECT_DIR 路徑（regex 或形狀變了）"


def test_positive_control_broken_path_is_red():
    """正對照：把 project_dir 指到不存在的目錄，同一判定必紅——證明上一條不是恆真。"""
    s = _load_settings()
    bogus = os.path.join(_REPO, "__no_such_dir__")
    missing = [p for ev in _EVENTS for _, cmd in _outline_commands(s, ev)
               for p in _resolved_paths(cmd, bogus) if not os.path.isfile(p)]
    assert missing, "正對照失敗：改壞路徑後仍全部存在，判定無效"
