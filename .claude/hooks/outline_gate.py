#!/usr/bin/env python3
"""outline_gate.py — repo 層 hook 探測骨架（knowledge-outline-and-intent-architecture 任務 1.1）。

現階段**只印不擋**：把 hook 執行時拿到的三個事實寫進 probe.log，供 1.2 決定 file_path 相對化寫法。
  ① CLAUDE_PROJECT_DIR 環境變數（有沒有、值是什麼）
  ② 事件名（hook_event_name）與工具名（tool_name）
  ③ 事件原始 file_path 的形狀（絕對／相對／缺）

約束（design 元件 3）：零第三方依賴、⛔ 不讀網路、⛔ 不讀 .env、只讀 stdin 事件與 repo 內檔案。
任何例外一律吞掉並 exit 0——探測骨架不得阻斷任何工具呼叫。
"""
import json
import os
import sys
from datetime import datetime, timezone


def _log_dir(project_dir: str) -> str:
    base = project_dir or os.getcwd()
    return os.path.join(base, ".claude", "hooks", "state", "outline-gate")


def main() -> int:
    try:
        raw = sys.stdin.read()
        try:
            ev = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            ev = {"_unparsable_stdin_len": len(raw)}
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
        tool_input = ev.get("tool_input") or {}
        file_path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
        if file_path is None:
            shape = "missing"
        elif os.path.isabs(file_path):
            shape = "absolute"
        else:
            shape = "relative"
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "CLAUDE_PROJECT_DIR": project_dir,
            "script": os.path.abspath(__file__),
            "cwd": os.getcwd(),
            "hook_event_name": ev.get("hook_event_name"),
            "tool_name": ev.get("tool_name"),
            "file_path": file_path,
            "file_path_shape": shape,
            "session_id": ev.get("session_id"),
            "event_keys": sorted(ev.keys()),
        }
        d = _log_dir(project_dir or "")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "probe.log"), "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 — 探測骨架絕不阻斷
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
