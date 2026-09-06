# hook 接線實跑證據（任務 1.1，2026-09-06）

> 目的：證明 repo 層 `.claude/settings.json` 的 hook 真的接得上線、拿得到 `CLAUDE_PROJECT_DIR`，並實測事件 `file_path` 的形狀（絕對／相對）——design 元件 3 明令 **⛔ 不憑文件**。
> 探測骨架 `.claude/hooks/outline_gate.py` 只印不擋（exit 0），log 落 `.claude/hooks/state/outline-gate/probe.log`（已 gitignore）。

## 1. 結論（給 1.2 用）

| 項目 | 實測值 | 對 1.2 的意義 |
|---|---|---|
| `CLAUDE_PROJECT_DIR` | `/Users/lenny/jgb/AIChatbot`（repo 根，絕對路徑） | 相對化基準用它，⛔ 不用 cwd |
| hook 執行時 cwd | `/Users/lenny/jgb/AIChatbot/rag-orchestrator`（**跟著 Bash 工具的 cwd 走，不是 repo 根**） | 任何以 cwd 為基準的路徑比對都會靜默失準；正對照＝本次 cwd 就已經不是根 |
| 事件 `file_path` 形狀 | **絕對路徑**（`/Users/lenny/jgb/AIChatbot/rag-orchestrator/canon/README.md`） | 腳本先 `os.path.relpath(file_path, CLAUDE_PROJECT_DIR)` 再比對白名單 `rag-orchestrator/canon/<audience>.md`；假事件測試須含絕對路徑案（N2） |
| 觸發的事件 | `PreToolUse`＋`PostToolUse`（同一次 Edit 各一筆，`tool_name=Edit`） | 兩道閘門都接得上 |
| 事件多帶的鍵 | `cwd`／`permission_mode`／`scratchpad_dir`／`transcript_path`／`tool_use_id`／`prompt_id`；PostToolUse 另有 `tool_response`／`duration_ms` | 1.2 的 `<session>.json` 狀態檔以 `session_id` 分檔；⛔ 不讀 `transcript_path` 內容（那是對話原文） |
| `Stop` 事件 | settings 已掛；本回合結束時才觸發，log 第三筆待下回合查證 | 1.2 的 Stop 判定不會拿到 `file_path`（形狀＝`missing`），要靠狀態檔判斷本 session 跑過什麼 |
| 生效時機 | settings.json 建立後、**同一批工具呼叫內**的 Write（README 占位檔）未觸發；下一則訊息的 Edit 才觸發 | hook 變更在同 session 生效，但不回溯到同批已排程的呼叫；接線 meta 測試（見 §3）補這個缺口 |

**done ①（附錄 C M-a）達成**：hook 接線實跑印出 `CLAUDE_PROJECT_DIR` 與解析到的腳本路徑 `/Users/lenny/jgb/AIChatbot/.claude/hooks/outline_gate.py`。

## 2. log 原文（`.claude/hooks/state/outline-gate/probe.log`，逐字）

```json
{"ts": "2026-09-06T06:05:12+00:00", "CLAUDE_PROJECT_DIR": "/Users/lenny/jgb/AIChatbot", "script": "/Users/lenny/jgb/AIChatbot/.claude/hooks/outline_gate.py", "cwd": "/Users/lenny/jgb/AIChatbot/rag-orchestrator", "hook_event_name": "PreToolUse", "tool_name": "Edit", "file_path": "/Users/lenny/jgb/AIChatbot/rag-orchestrator/canon/README.md", "file_path_shape": "absolute", "session_id": "158ab224-5fb1-4cb1-8d8a-8a4a3d250f04", "event_keys": ["cwd", "effort", "hook_event_name", "permission_mode", "prompt_id", "scratchpad_dir", "session_id", "tool_input", "tool_name", "tool_use_id", "transcript_path"]}
{"ts": "2026-09-06T06:05:12+00:00", "CLAUDE_PROJECT_DIR": "/Users/lenny/jgb/AIChatbot", "script": "/Users/lenny/jgb/AIChatbot/.claude/hooks/outline_gate.py", "cwd": "/Users/lenny/jgb/AIChatbot/rag-orchestrator", "hook_event_name": "PostToolUse", "tool_name": "Edit", "file_path": "/Users/lenny/jgb/AIChatbot/rag-orchestrator/canon/README.md", "file_path_shape": "absolute", "session_id": "158ab224-5fb1-4cb1-8d8a-8a4a3d250f04", "event_keys": ["cwd", "duration_ms", "effort", "hook_event_name", "permission_mode", "prompt_id", "scratchpad_dir", "session_id", "tool_input", "tool_name", "tool_response", "tool_use_id", "transcript_path"]}
```

觸發動作：先 Write `rag-orchestrator/canon/README.md`（占位，內容＝路徑約定一句），再對它做一次 Edit（補一句 R2.9）。Claude Code 版本 2.1.263。

## 3. 接線自證（宿主直跑）

`rag-orchestrator/tests/unit/_meta/test_outline_gate_wiring_req.py`（5 案，TDD 先紅後綠）：三事件皆掛 `outline_gate.py`、Edit／Write matcher 逐字 `Edit|Write`、command 用 `$CLAUDE_PROJECT_DIR` 且 `|| exit 0` 缺檔放行、代入 repo 根後腳本存在、正對照（改壞根目錄必紅）。

```
# 紅（settings.json 尚未建立）
/usr/bin/python3 -m pytest tests/unit/_meta/test_outline_gate_wiring_req.py -q   → 5 failed
# 綠（接線完成）
/usr/bin/python3 -m pytest tests/unit/_meta/test_outline_gate_wiring_req.py -q   → 5 passed
```

⚠️ 測試容器（`docker-compose.dev.yml`）只掛 `rag-orchestrator`／`docs`／`.kiro`／`scripts`／`.github`，看不到 repo 根 `.claude/`，容器內跑本檔會 `[env]` skip 並印明原因（不靜默綠）。要讓 `make test` 也驗接線，需在 compose 補掛 `./.claude:/.claude:ro`——列為 1.2 的處置選項，本任務不動 compose。

## 4. 對照組（非實跑，僅證明 command 字串與腳本本身可用）

把 settings.json 的 command 原字串以假 `CLAUDE_PROJECT_DIR`（scratchpad 下的 `simroot/`）與手工 stdin 事件跑一次：exit 0、log 落在 `$CLAUDE_PROJECT_DIR/.claude/hooks/state/outline-gate/probe.log`。這一步只證明「給對 env 就會動」，**不能取代 §2 的線上實跑**。

## 5. 本任務落地清單

- `.claude/settings.json`（新，repo 層 hooks 首例：PreToolUse／PostToolUse `Edit|Write`、Stop）
- `.claude/hooks/outline_gate.py`（探測骨架，只印不擋；1.2 在此之上實作五道判定）
- `rag-orchestrator/canon/README.md`（占位；⛔ 不入 1.2 白名單）
- `.gitignore` 三條：`.claude/hooks/state/`、`.claude/skills/outline-curation/raw/`、`.claude/skills/outline-curation/journal/`（Workflow journal 複本落點；`runs/` 已去識別者才版控）
- `rag-orchestrator/tests/unit/_meta/test_outline_gate_wiring_req.py`（接線 meta 測試）

## 6. 已知取捨

- Workflow journal 的 repo 內落點（`journal/`）是本任務定的約定，design 只寫「gitignored」未指名目錄；1.3 的 `cost_ledger.py` 讀取路徑須對齊此處。
- 探測骨架目前對**所有** Edit／Write 都寫 log（含非目標路徑）——1.1 要的就是觀察形狀；1.2 上線判定時須改為只在目標路徑命中時動作（design：噪音會訓練人略過）。
- Stop 事件的第一筆 log 在本回合結束後才產生，未寫進本檔；1.2 開工時先 `cat probe.log` 確認第三筆存在（正對照：`hook_event_name=Stop`、`file_path_shape=missing`）。
