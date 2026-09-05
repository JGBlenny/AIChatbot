#!/usr/bin/env python3
"""離線輔助工具：讀 `tools/agent_eval.py --dump-texts` 的 texts 旁路 jsonl，
彙總「被 Verifier 拒掉的中間嘗試」（spec agentic-mcp-orchestration・
tasks 4.3c，量測第六輪回歸發現的缺口——見同目錄
`.kiro/specs/agentic-mcp-orchestration/eval/perf-agent-regression-20260905/README.md`
第六輪）。

⛔ **純離線分析**：不呼叫任何模型、不連任何 DB、不觸網。輸入只有本機一個
jsonl 檔（每列一筆 `{..., "attempts": [...]}` 記錄，見
`services/agent/runtime.py::AgentRuntime._emit_attempt` 的 record 形狀、
`tools/agent_eval.py::_build_agent_record` 怎麼把它塞進 texts 旁路）。

輸出四項統計（stdout，或 `--out` 寫成 markdown）：
1. 每種拒因的嘗試數（`SCHEMA_PARSE`／`SCHEMA:<schema_cause>`／其餘 `reason` 原樣）。
2. 被拒過至少一次的回合，最終走哪個 `kind`（`answer`／`ask`／`recommend`／`handoff`）
   的分佈——量「牆擋下去之後使用者最後拿到什麼」。
3. `ref_invalid`（標記格式本身不合）的字串樣態統計：去掉 nonce 段後以規則分類
   （缺段／多段／含中文／含空白／其他），⛔ 不印任何原始標記字串，只印樣態
   名稱與計數。
4. `QUOTE_NOT_COVERING` 嘗試的句數（`sentences` 長度）與 refs 數（逐句 `refs`
   加總）分佈——量「牆擋下去的是短小輕薄的引用問題，還是整段話都在硬凹」。

⚠️ **只讀 texts 旁路本身的封閉形狀**：不讀 `answer`／`q` 等原文欄位，
本工具的輸出完全不含任何一句原文或標記字面值。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Optional

# ---------------------------------------------------------------------------
# 1) 讀檔
# ---------------------------------------------------------------------------


def load_texts_jsonl(path: Path) -> list[dict]:
    """讀 `--dump-texts` 旁路 jsonl；第一行是 `_warning` 表頭，略過。

    格式壞掉的行直接 raise（⛔ 靜默跳過壞資料等於假裝分析完整；這支工具
    本來就只給人工在確定檔案存在之後手動跑，壞檔早點炸比較好）。
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    records: list[dict] = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if i == 0 and "_warning" in row:
            continue
        records.append(row)
    return records


# ---------------------------------------------------------------------------
# 2) 拒因分佈
# ---------------------------------------------------------------------------


def _attempt_reject_label(attempt: dict) -> Optional[str]:
    """一筆 attempt 記錄的拒因標籤；`ok=True`（沒被拒）回 `None`。

    形狀對齊 `services/agent/runtime.py`：
    - JSON 解析／schema 驗證失敗 ⇒ `{"verdict": {"reason": "SCHEMA_PARSE"}}`。
    - 驗證過的輸出 ⇒ `{"verdict": VerifierVerdict.model_dump()}`，`reason=SCHEMA`
      時額外看 `schema_cause`（同 `tools/agent_eval.py::_verdict_reason_label`
      的慣例，⛔ 不重造另一套標籤規則）。
    """
    verdict = attempt.get("verdict") or {}
    if verdict.get("ok"):
        return None
    reason = verdict.get("reason") or ""
    if reason == "SCHEMA_PARSE":
        return "SCHEMA_PARSE"
    cause = verdict.get("schema_cause")
    if reason == "SCHEMA" and cause:
        return f"SCHEMA:{cause}"
    return reason or "UNKNOWN"


def reject_reason_counts(records: Iterable[dict]) -> Counter:
    counts: Counter = Counter()
    for record in records:
        for attempt in record.get("attempts") or []:
            label = _attempt_reject_label(attempt)
            if label is not None:
                counts[label] += 1
    return counts


# ---------------------------------------------------------------------------
# 3) 被拒後最終走哪個 kind
# ---------------------------------------------------------------------------


def final_kind_after_reject_counts(records: Iterable[dict]) -> Counter:
    """限定「本回合至少一次嘗試被拒」的記錄，數它們最終 `kind` 的分佈。

    `record["kind"]` 是這一輪**最終被採用**的結果（`_build_agent_record` 寫入的
    那份，來自 `TurnResult.kind`），⛔ 不是某一次嘗試的 kind——固定句收場
    （耗盡重寫預算）在 `TurnResult` 上一律是 `handoff`。
    """
    counts: Counter = Counter()
    for record in records:
        attempts = record.get("attempts") or []
        if any(_attempt_reject_label(a) is not None for a in attempts):
            counts[record.get("kind") or "UNKNOWN"] += 1
    return counts


# ---------------------------------------------------------------------------
# 4) ref_invalid 字串樣態分類（⛔ 不印原文，只印樣態名）
# ---------------------------------------------------------------------------

_CJK_RE = re.compile(r"[㐀-䶿一-鿿]")
_WS_RE = re.compile(r"\s")

#: 合法形狀（去掉頭尾方括號／空白後）：`nonce:tool_call_id:source§index`——
#: 與 `services/agent/provenance_units.py:_REF_RE` 對齊，但這裡不驗 nonce 的
#: 實際值（本工具沒有本回合的真 nonce 可比對，且無論值對不對，樣態統計只管
#: 「三段＋§數字」這個**結構**）。
_WELL_FORMED_RE = re.compile(r"^[^:\s]+:[^:\s]+:[^\s]+§\d+$")

#: 分類結果的封閉列舉——與 brief 指定的五類逐字對齊。
RefShape = str  # Literal["缺段", "多段", "含中文", "含空白", "其他"]


def classify_ref_shape(ref: str) -> RefShape:
    """把一個（格式錯誤的）`refs` 標記字串分類成樣態，⛔ 呼叫端不得印出 `ref` 本身。

    判斷順序（有交集時，較「顯眼」的病灶優先）：
    1. 含中文字元 ⇒ `含中文`（模型把中文說明抄進標記，而不是照抄行首標記）。
    2. 去掉頭尾方括號後仍含空白 ⇒ `含空白`（抄寫時夾帶了空白／換行）。
    3. 依 `:` 切段：少於 3 段 ⇒ `缺段`；多於 3 段 ⇒ `多段`。
    4. 其餘（含「三段＋§ 數字」但仍被判 `ref_invalid`，通常是 nonce 對不上
       本回合）⇒ `其他`——**正對照**：一筆結構正確的三段式 ref 必須落在這裡，
       ⛔ 不得被誤判進上面任何一個「格式缺陷」桶。

    ⚠️ **已知限制**：判段數是單純用 `:` 切割計數，而合法的 `source` 段本身
    可以含冒號（`provenance_units.py` 註解舉例 `kb:3600`／`jgb2:bills#ref`）。
    這支工具沒有本回合的真 nonce／來源清單可比對，無法像 `resolve_refs` 那樣
    精準驗證，遇到 `source` 含冒號的合法 ref 會被誤算成段數偏多——這是離線
    分析工具刻意接受的簡化 heuristic，⛔ 不當成權威判定，抽審時仍要回原始
    `resolve_errors`／`schema_cause` 對照。
    """
    raw = ref.strip()
    if _CJK_RE.search(raw):
        return "含中文"
    inner = raw.strip("[]").strip()
    if _WS_RE.search(inner):
        return "含空白"
    colon_parts = inner.split(":")
    if len(colon_parts) < 3:
        return "缺段"
    if len(colon_parts) > 3:
        return "多段"
    return "其他"


def _ref_for_error_key(attempt: dict, error_key: str) -> Optional[str]:
    """`error_key` 形如 `"<sent_idx>:<ref_idx>"`（見 `runtime.py::run_turn` 的
    `resolve_errors` 記法）；回該筆句子在該索引的原始 `refs` 字串，取不到回 `None`
    （形狀跟預期不符——資料本身壞了，⛔ 不猜、直接跳過這筆統計）。"""
    try:
        sent_idx_s, ref_idx_s = error_key.split(":", 1)
        sent_idx, ref_idx = int(sent_idx_s), int(ref_idx_s)
    except ValueError:
        return None
    sentences = attempt.get("sentences") or []
    if not (0 <= sent_idx < len(sentences)):
        return None
    refs = sentences[sent_idx].get("refs") or []
    if not (0 <= ref_idx < len(refs)):
        return None
    return str(refs[ref_idx])


def ref_invalid_shape_counts(records: Iterable[dict]) -> Counter:
    """只統計 `schema_cause == "ref_invalid"` 的那些 ref（格式本身不合）；
    `ref_source_not_found`／`ref_ambiguous`／`unit_out_of_range` 是格式合法但
    指不到東西，不算「字串樣態」問題，不進這張表。"""
    counts: Counter = Counter()
    for record in records:
        for attempt in record.get("attempts") or []:
            resolve_errors = attempt.get("resolve_errors") or {}
            for key, cause in resolve_errors.items():
                if cause != "ref_invalid":
                    continue
                ref = _ref_for_error_key(attempt, key)
                if ref is None:
                    continue
                counts[classify_ref_shape(ref)] += 1
    return counts


# ---------------------------------------------------------------------------
# 5) QUOTE_NOT_COVERING 嘗試的句數／refs 數分佈
# ---------------------------------------------------------------------------


def quote_not_covering_shape_distribution(records: Iterable[dict]) -> dict:
    """回傳 `{"n_sentences": Counter, "n_refs": Counter}`——`QUOTE_NOT_COVERING`
    拒因的那些嘗試，句數與（逐句 refs 加總）數各自的分佈。"""
    n_sentences: Counter = Counter()
    n_refs: Counter = Counter()
    for record in records:
        for attempt in record.get("attempts") or []:
            verdict = attempt.get("verdict") or {}
            if verdict.get("reason") != "QUOTE_NOT_COVERING":
                continue
            sentences = attempt.get("sentences") or []
            n_sentences[len(sentences)] += 1
            total_refs = sum(len(s.get("refs") or []) for s in sentences)
            n_refs[total_refs] += 1
    return {"n_sentences": n_sentences, "n_refs": n_refs}


# ---------------------------------------------------------------------------
# report 組裝
# ---------------------------------------------------------------------------


def _render_counter_md(title: str, counter: Counter) -> list[str]:
    lines = [f"## {title}", ""]
    if not counter:
        lines.append("（無資料）")
        lines.append("")
        return lines
    lines.append("| 項目 | 次數 |")
    lines.append("|---|---|")
    for key, n in sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0]))):
        lines.append(f"| `{key}` | {n} |")
    lines.append("")
    return lines


def render_report_md(records: list[dict]) -> str:
    lines = ["# agent_attempts_report", "", f"- 總記錄數（回合數）：{len(records)}", ""]
    lines += _render_counter_md("每種拒因的嘗試數", reject_reason_counts(records))
    lines += _render_counter_md(
        "被拒過至少一次的回合，最終 kind 分佈", final_kind_after_reject_counts(records)
    )
    lines += _render_counter_md(
        "ref_invalid 字串樣態統計（⛔ 不含原文，只有樣態名與計數）",
        ref_invalid_shape_counts(records),
    )
    qnc = quote_not_covering_shape_distribution(records)
    lines += _render_counter_md("QUOTE_NOT_COVERING 嘗試的句數分佈", qnc["n_sentences"])
    lines += _render_counter_md("QUOTE_NOT_COVERING 嘗試的 refs 數分佈", qnc["n_refs"])
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "讀一個 `agent_eval.py --dump-texts` 的 texts 旁路 jsonl，彙總被拒"
            "中間嘗試的統計（純離線，不呼叫模型／DB）。"
        )
    )
    p.add_argument("jsonl_path", type=Path, help="texts 旁路 jsonl 路徑（如 out/texts/topics.jsonl）")
    p.add_argument("--out", type=Path, default=None, help="寫 markdown 報表到此路徑；不給則印 stdout")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if not args.jsonl_path.is_file():
        print(f"找不到檔案：{args.jsonl_path}", file=sys.stderr)
        return 1
    records = load_texts_jsonl(args.jsonl_path)
    report = render_report_md(records)
    if args.out is not None:
        args.out.write_text(report, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
