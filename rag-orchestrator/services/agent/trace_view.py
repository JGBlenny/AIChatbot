"""回合軌跡的**渲染層**（spec agentic-mcp-orchestration・任務 2.7）。

輸入是 `usage_events` 的一列（`decision_snapshot.agent` 為 2.5 落地的封閉
白名單快照），輸出是一份**只含形狀、不含原文**的敘事視圖。端點
（`routers/agent.py`）與 CLI（`tools/agent_trace.py`）共用本檔，⛔ 不各寫
一份渲染邏輯——否則兩條路徑的遮罩紀律會漂。

## 為什麼渲染層還要再遮一次
`decision_snapshot.agent` 本身已受不變量 30（`scripts/audit/checks/
agent_boundary.py:check_30_decision_snapshot_no_verbatim`）保護，鍵集合是
封閉白名單。但那條不變量守的是**寫入端**；本檔是**讀出端**，而讀出端會把
內容送到人的螢幕、CLI 檔案與 HTTP 回應上。兩件寫入端管不到的事在這裡處理：

1. **`session_id` 遮罩**（前置 security review P3）——`usage_events.session_id`
   是欄位不是快照，寫入端的白名單管不到它。輸出一律 `前 4 碼＋…＋sha256 前 8`，
   ⛔ 不輸出原值：足以在多回合時間軸上辨識「是不是同一段對話」，但不足以
   拿去猜／重放別人的 session。
2. **`term_id` 只印規則索引**（前置 security review P2）——2.6 會把 verdict 的
   `term_id` 改成 `rule#n`；在那之前 `services/agent/verifier.py` 寫進去的是
   **字面詞或 regex pattern**（`SENSITIVE_TOPIC` 存 `pattern.pattern`、
   `FORBIDDEN_TERM`／`POLARITY_MISMATCH` 存詞本身）。字面詞會反向洩漏規則集
   內容，所以本檔只放行 `^rule#\\d+$`，其餘一律 `redacted`。⚠️ 這是
   **fail-closed 白名單**：不是「認得的壞值才擋」，是「不是規則索引就擋」，
   2.6 上線前後都成立。

## 與 2.6 的相容性
2.6 會刪 `ToolCallRecord.args_hash`（前置 security review P2：低熵參數可字典
反解）。本檔**從頭到尾不讀 `args_hash`**——`_render_step` 只取
`args_summary` 的四個形狀欄位，所以那個鍵在不在都不影響輸出。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Mapping, Optional

# 查詢時間窗與筆數上限：`decision_snapshot->'agent'->>'trace_id'` **沒有索引**
# （`database/migrations/add_usage_events.sql` 只建 `idx_usage_date_vendor`／
# `idx_usage_session`），全表掃是 DoS 面（前置 security review P3）。端點與 CLI
# 共用這兩個常數，⛔ 不各自寫一份預設值——不然兩條路徑的窗會漂。
TRACE_WINDOW_ENV = "AGENT_TRACE_WINDOW_DAYS"
DEFAULT_WINDOW_DAYS = 7
SESSION_TIMELINE_LIMIT = 50


def window_days() -> int:
    """`AGENT_TRACE_WINDOW_DAYS`（預設 7）。非法／非正數 ⇒ 退回預設，⛔ 不放大窗。"""
    try:
        days = int(os.getenv(TRACE_WINDOW_ENV, str(DEFAULT_WINDOW_DAYS)))
    except (TypeError, ValueError):
        return DEFAULT_WINDOW_DAYS
    return days if days > 0 else DEFAULT_WINDOW_DAYS

# ⛔ 這些鍵一旦出現在輸出裡就是原文外洩（前四個與 `scripts/audit/checks/
# agent_boundary.py:DECISION_BANNED_KEYS` 同一組，`session_id` 是本層自己
# 多守的一條：輸出只准有遮罩後的 `session`）。`_assert_no_verbatim` 在
# `render_trace` 回傳前遞迴掃一次——縱深防禦第二層：白名單建構已經保證
# 不會有，這一層是為了「日後有人加欄位時當場炸」而不是靜默通過。
FORBIDDEN_OUTPUT_KEYS = frozenset({"answer", "quote", "text", "user_message", "session_id"})

# 只有規則索引可以原樣輸出（見模組 docstring 第 2 點）。
_RULE_INDEX_RE = re.compile(r"^rule#\d+$")

SESSION_PREFIX_LEN = 4
SESSION_HASH_LEN = 8


# ════════════════════════════════════════════════════════════════════
# 取值小工具：row 可能是 dict／asyncpg.Record／psycopg2 RealDictRow
# ════════════════════════════════════════════════════════════════════
def _field(row: Any, name: str, default: Any = None) -> Any:
    try:
        value = row[name]
    except (KeyError, IndexError, TypeError):
        return default
    return default if value is None else value


def _as_dict(value: Any) -> dict:
    """`decision_snapshot` 可能是 dict（psycopg2 jsonb）或 str（asyncpg 預設不解碼）。"""
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, (str, bytes)):
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def agent_snapshot(row: Any) -> dict:
    """取出 `decision_snapshot.agent`（沒有就回空 dict，⛔ 不猜、不補值）。"""
    snapshot = _as_dict(_field(row, "decision_snapshot"))
    agent = snapshot.get("agent")
    return agent if isinstance(agent, dict) else {}


# ════════════════════════════════════════════════════════════════════
# 遮罩
# ════════════════════════════════════════════════════════════════════
def mask_session(session_id: Any) -> str:
    """`前 4 碼…sha256 前 8`（前置 security review P3）。空值回空字串。"""
    if session_id is None:
        return ""
    raw = str(session_id)
    if not raw:
        return ""
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:SESSION_HASH_LEN]
    return f"{raw[:SESSION_PREFIX_LEN]}…{digest}"


def rule_index(term_id: Any) -> Optional[str]:
    """只放行 `rule#n`；其他非空值一律 `redacted`；本來就沒有 ⇒ None。

    ⚠️ 取捨：派工契約寫「否則 `redacted`」。這裡對 **`term_id` 不存在／為 None**
    的情形回 `None` 而不是 `redacted`——通過的 verdict（`ok=True`）本來就沒有
    term，印 `redacted` 會謊報「有東西被遮掉」。安全性質不變：任何**存在但
    不是規則索引**的值一律變 `redacted`，⛔ 字面詞永遠不會被印出來。
    """
    if term_id is None:
        return None
    value = str(term_id)
    if not value:
        return None
    return value if _RULE_INDEX_RE.match(value) else "redacted"


# ════════════════════════════════════════════════════════════════════
# 渲染
# ════════════════════════════════════════════════════════════════════
def _render_step(call: Any) -> dict:
    """工具序列一格。⛔ 不讀 `args_hash`（2.6 會刪，讀了就會綁死在它身上）。"""
    call = call if isinstance(call, Mapping) else {}
    summary = call.get("args_summary")
    summary = summary if isinstance(summary, Mapping) else {}

    step: dict = {"name": call.get("name")}
    if "face" in summary:
        step["face"] = summary.get("face")
    step["has_ref"] = bool(summary.get("has_ref", False))
    step["has_keyword"] = bool(summary.get("has_keyword", False))
    if "k" in summary:
        step["k"] = summary.get("k")
    step["n_items"] = call.get("n_items")
    step["status"] = call.get("status")
    step["ms"] = call.get("ms")
    return step


def _render_verdict(verdict: Any) -> dict:
    verdict = verdict if isinstance(verdict, Mapping) else {}
    return {
        "reason": verdict.get("reason"),
        # DSP-029 r13 #7／DSP-029a：`SCHEMA` 的子成因（封閉列舉值，⛔ 無原文）——只回
        # reason 時八種結構性失敗全擠成同一格，稽核看不出「標記不是本回合的」
        # （`ref_invalid`）與「句子空白」的差別。值域見
        # `services/agent/output_schema.py:VerifierVerdict.schema_cause`，本檔**原樣透傳**，
        # ⛔ 不自己維護第二份名單（維護第二份就會有新值印不出來的那一天）。
        "schema_cause": verdict.get("schema_cause"),
        "sent": verdict.get("sent"),
        "rule": rule_index(verdict.get("term_id")),
        # DSP-033：`NOT_ENTAILED` 的定位靠它——`term_id` 對這個拒因固定為 None
        # （r18 F-15），沒有 rule 可以印。0–1 的分數，⛔ 非原文。
        "entail_score": verdict.get("entail_score"),
    }


def _assert_no_verbatim(view: Any, path: str = "$") -> None:
    if isinstance(view, Mapping):
        hit = FORBIDDEN_OUTPUT_KEYS & set(map(str, view.keys()))
        if hit:
            raise ValueError(f"trace_view 輸出含原文鍵 {sorted(hit)}（{path}）——⛔ 不得外洩")
        for k, v in view.items():
            _assert_no_verbatim(v, f"{path}.{k}")
    elif isinstance(view, (list, tuple)):
        for i, v in enumerate(view):
            _assert_no_verbatim(v, f"{path}[{i}]")


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    return isoformat() if callable(isoformat) else str(value)


def render_trace(row: Any) -> dict:
    """一列 `usage_events` ⇒ 一份回合敘事視圖（封閉鍵集合，⛔ 無原文）。"""
    agent = agent_snapshot(row)

    tool_calls = agent.get("tool_calls")
    verdicts = agent.get("verifier")

    view = {
        "trace_id": agent.get("trace_id"),
        "at": _iso(_field(row, "ts")),
        "kind": agent.get("final_kind"),
        "handoff_reason": agent.get("handoff_reason"),
        "replayed_from": agent.get("replayed_from"),
        "steps": [_render_step(c) for c in (tool_calls if isinstance(tool_calls, list) else [])],
        "verifier": [_render_verdict(v) for v in (verdicts if isinstance(verdicts, list) else [])],
        "counts": {
            "llm_calls": agent.get("llm_calls"),
            "prompt_tokens": agent.get("prompt_tokens"),
            "completion_tokens": agent.get("completion_tokens"),
            "latency_ms": agent.get("latency_ms"),
        },
        "session": mask_session(_field(row, "session_id")),
        "rules_sha": agent.get("rules_sha"),
        "outline_sha": agent.get("outline_sha"),
        "nli_model_sha": agent.get("nli_model_sha"),
    }
    _assert_no_verbatim(view)
    return view


# ════════════════════════════════════════════════════════════════════
# CLI 文字輸出
# ════════════════════════════════════════════════════════════════════
def _fmt(value: Any, dash: str = "-") -> str:
    return dash if value is None or value == "" else str(value)


def render_text(view: Mapping) -> str:
    """`render_trace` 的結果 ⇒ 人可讀敘事（`tools/agent_trace.py` 用）。"""
    lines = [
        f"trace_id : {_fmt(view.get('trace_id'))}",
        f"時間     : {_fmt(view.get('at'))}",
        f"session  : {_fmt(view.get('session'))}   （遮罩：前 4 碼＋sha256 前 8）",
        f"最終 kind: {_fmt(view.get('kind'))}"
        + (f"   轉人原因: {view.get('handoff_reason')}" if view.get("handoff_reason") else ""),
    ]
    if view.get("replayed_from"):
        lines.append(f"重播自   : {view['replayed_from']}")

    steps = list(view.get("steps") or [])
    lines.append(f"工具序列 : {len(steps)} 次")
    for i, step in enumerate(steps, 1):
        bits = [f"face={step['face']}"] if "face" in step else []
        bits.append(f"ref={'有' if step.get('has_ref') else '無'}")
        bits.append(f"keyword={'有' if step.get('has_keyword') else '無'}")
        if "k" in step:
            bits.append(f"k={step['k']}")
        bits.append(f"筆數={_fmt(step.get('n_items'))}")
        bits.append(f"狀態={_fmt(step.get('status'))}")
        bits.append(f"{_fmt(step.get('ms'))}ms")
        lines.append(f"  {i}. {_fmt(step.get('name'))}  " + "  ".join(bits))

    verdicts = list(view.get("verifier") or [])
    lines.append(f"Verifier : {len(verdicts)} 次判定")
    for i, v in enumerate(verdicts, 1):
        if v.get("reason") is None:
            lines.append(f"  {i}. 通過")
        else:
            tail = f"  規則={v['rule']}" if v.get("rule") else ""
            # DSP-033：NOT_ENTAILED 印分數（⛔ 無原文）——不印的話稽核只看得到
            # 「被 NLI 拒了」，卻看不出是差一點還是差很遠。
            if v.get("entail_score") is not None:
                tail += f"  蘊涵={v['entail_score']}"
            # DSP-029／DSP-029a：`SCHEMA` 不印子成因等於什麼都沒說（八種結構性失敗同一格）。
            cause = f"／{v['schema_cause']}" if v.get("schema_cause") else ""
            lines.append(
                f"  {i}. 拒 {v['reason']}{cause}  筆次={_fmt(v.get('sent'))}{tail}")

    counts = view.get("counts") or {}
    lines.append(
        "計數     : "
        f"llm={_fmt(counts.get('llm_calls'))}  "
        f"prompt_tokens={_fmt(counts.get('prompt_tokens'))}  "
        f"completion_tokens={_fmt(counts.get('completion_tokens'))}  "
        f"latency={_fmt(counts.get('latency_ms'))}ms"
    )
    lines.append(
        f"指紋     : rules_sha={_fmt(view.get('rules_sha'))}  "
        f"outline_sha={_fmt(view.get('outline_sha'))}  "
        f"nli_model_sha={_fmt(view.get('nli_model_sha'))}"
    )
    return "\n".join(lines)


__all__ = [
    "DEFAULT_WINDOW_DAYS",
    "FORBIDDEN_OUTPUT_KEYS",
    "SESSION_TIMELINE_LIMIT",
    "TRACE_WINDOW_ENV",
    "agent_snapshot",
    "mask_session",
    "render_text",
    "render_trace",
    "rule_index",
    "window_days",
]
