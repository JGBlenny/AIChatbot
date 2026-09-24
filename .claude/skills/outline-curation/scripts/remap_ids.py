#!/usr/bin/env python3
"""remap_ids：把驗收材料裡的舊 `fine.id` 依 `id_map` 改成新 id（任務 9.3②）。

只做 `op=keep`／`move`（1→1）的直接改寫；`split`／`merge`（以及任何其他非
keep/move 的 op）的格 ⛔ 不自動猜，一律標成「須重判」並保留原字串不動。

輸入：
- `--id-map <json>`：接受三種殼——`{"id_map": [...]}`、
  structure-proposal.json 的 StepEnvelope（取 `payload.synthesis.id_map`）、
  或裸陣列 `[...]`。每筆 `{"old": str, "new": str, "op": "keep"|"move"|"split"|"merge"|"new"}`。
- `--files <path>...`：純文字掃描（JSON／TSV／MD 皆同法，⛔ 不做格式感知解析——
  這樣才能保證「不含任何 fine.id 的檔案零變更」，格式感知重寫一定會動到無關的排版）。
  掃描式樣＝`canon_parser.FINE_ID_RE` 拿掉頭尾錨點後的同一個內層樣式（⛔ 不另寫新樣式），
  外加左右邊界防呆（前後不得接 `[A-Za-z0-9_-]`），避免誤吃到更長 token 的一截。

比對規則（決定性、可重跑兩次）：
- 掃到的 id ∈ id_map 的 `old` 集合 ⇒ 依 op：keep/move 改寫成 `new`；其餘（split/merge/
  未知 op）標「須重判」、原字串不動。
- 掃到的 id ∈ id_map 的 `new` 集合（但不在 `old` 集合）⇒ 視為「已經是新 id」，0 變更、
  不算失敗（這條是冪等性的關鍵：apply 過一次之後，檔案裡的 id 已經是 new，
  再 apply 一次不能因為「in new not in old」被誤判成找不到對應）。
- 兩者都不是 ⇒「找不到對應的舊 id」，計入 unmapped ⇒ 整支工具 FAIL（exit 2，
  ⛔ 不靜默略過、⛔ 部分寫檔——apply 模式下只要有任何 unmapped，一個檔案都不寫）。

輸出：
- `--dry-run`（預設）：只印報表到 stdout，不寫任何檔案。
- `--apply`：把改寫後的內容寫回原檔（保留其餘位元組不變：用 `newline=""` 讀寫，
  不做行尾轉換），並在旁邊留 `<file>.remap-report.json`（該檔的報表）；exit 前
  也把彙總報表印到 stdout。

決定性：同輸入兩次逐位元相等（報表不含時間戳；所有清單依 id 排序）。
冪等：apply 兩次，第二次每檔 matches 全落在 already_new 桶、零位元組變更。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "rag-orchestrator"))
for _cand in (_RAG, "/app"):
    if os.path.isdir(os.path.join(_cand, "services")) and _cand not in sys.path:
        sys.path.insert(0, _cand)

try:
    from services.agent.canon.canon_parser import FINE_ID_RE  # noqa: E402
except ImportError as exc:  # pragma: no cover
    print(f"[remap_ids] 無法匯入 rag-orchestrator services（{type(exc).__name__}）：請在 repo 根或容器內執行", file=sys.stderr)
    raise SystemExit(2)

assert FINE_ID_RE.pattern.startswith("^") and FINE_ID_RE.pattern.endswith("$"), \
    "canon_parser.FINE_ID_RE 樣式已變，remap_ids 的掃描式樣需要重新確認"
_INNER = FINE_ID_RE.pattern[1:-1]
# 同一個內層樣式，只加左右邊界防呆（⛔ 不改字元類本身）：避免把更長 token 的一截誤判成 id。
SCAN_RE = re.compile(r"(?<![A-Za-z0-9_-])" + _INNER + r"(?![A-Za-z0-9_-])")

_REWRITE_OPS = frozenset({"keep", "move"})


def _fail(msg: str) -> None:
    print(f"[remap_ids] {msg}", file=sys.stderr)
    raise SystemExit(2)


def load_id_map(path: str) -> list:
    if not os.path.isfile(path):
        _fail(f"--id-map 檔案不存在：{path}")
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)

    id_map = None
    if isinstance(doc, list):
        id_map = doc
    elif isinstance(doc, dict):
        if "id_map" in doc:
            id_map = doc["id_map"]
        elif "payload" in doc and isinstance(doc["payload"], dict):
            synth = doc["payload"].get("synthesis")
            if isinstance(synth, dict) and "id_map" in synth:
                id_map = synth["id_map"]
    if not isinstance(id_map, list):
        _fail(f"--id-map（{path}）裡找不到 id_map 陣列（接受 {{'id_map':[...]}}／StepEnvelope／裸陣列三種殼）")
    for entry in id_map:
        if not isinstance(entry, dict) or "new" not in entry or "op" not in entry:
            _fail(f"id_map 有一筆缺 new／op：{entry!r}")
    return id_map


def build_indexes(id_map: list) -> tuple[dict, set]:
    """回 (old_index, new_ids)。`old_index`：old id → 該筆 entry（後者覆蓋前者，同 old 只取最後一筆）。"""
    old_index: dict = {}
    new_ids: set = set()
    for entry in id_map:
        old = entry.get("old")
        if isinstance(old, str) and old:
            old_index[old] = entry
        new = entry.get("new")
        if isinstance(new, str) and new:
            new_ids.add(new)
    return old_index, new_ids


def scan_ids(text: str) -> list:
    """回文字裡所有 id 樣式子字串（含重複、依出現順序），皆已通過 `FINE_ID_RE.match` 全比對確認。"""
    out = []
    for m in SCAN_RE.finditer(text):
        s = m.group(0)
        assert FINE_ID_RE.match(s), f"掃描式樣與 FINE_ID_RE 全比對不一致：{s!r}"
        out.append(s)
    return out


def classify(ids: list, old_index: dict, new_ids: set) -> dict:
    """回每檔分類結果：{'rewritten': {old: {'new':.., 'occurrences':n}}, 'must_rejudge': {old: {'op':.., 'occurrences':n}},
    'already_new': {id: n}, 'unmapped': {id: n}}（皆依 id 內容累加次數，⛔ 不含時間戳）。"""
    rewritten: dict = {}
    must_rejudge: dict = {}
    already_new: dict = {}
    unmapped: dict = {}
    for sid in ids:
        entry = old_index.get(sid)
        if entry is not None:
            op = entry.get("op")
            if op in _REWRITE_OPS:
                bucket = rewritten.setdefault(sid, {"new": entry["new"], "occurrences": 0})
                bucket["occurrences"] += 1
            else:
                bucket = must_rejudge.setdefault(sid, {"op": op, "occurrences": 0})
                bucket["occurrences"] += 1
        elif sid in new_ids:
            already_new[sid] = already_new.get(sid, 0) + 1
        else:
            unmapped[sid] = unmapped.get(sid, 0) + 1
    return {"rewritten": rewritten, "must_rejudge": must_rejudge, "already_new": already_new, "unmapped": unmapped}


def rewrite_text(text: str, rewritten: dict) -> str:
    """依 `rewritten`（{old: {'new':..}}）把 text 內每個 old 子字串換成 new；其餘（must_rejudge／already_new/
    unmapped）原樣保留。用 SCAN_RE 逐一比對，只替換落在 rewritten 裡的那些 id，其他子字串不動。"""
    def _sub(m: re.Match) -> str:
        s = m.group(0)
        hit = rewritten.get(s)
        return hit["new"] if hit is not None else s

    return SCAN_RE.sub(_sub, text)


def file_report(path: str, cls: dict) -> dict:
    matches_found = sum(v["occurrences"] for v in cls["rewritten"].values()) \
        + sum(v["occurrences"] for v in cls["must_rejudge"].values()) \
        + sum(cls["already_new"].values()) + sum(cls["unmapped"].values())
    return {
        "path": path,
        "matches_found": matches_found,
        "counts": {
            "rewritten": sum(v["occurrences"] for v in cls["rewritten"].values()),
            "must_rejudge": sum(v["occurrences"] for v in cls["must_rejudge"].values()),
            "already_new": sum(cls["already_new"].values()),
            "unmapped": sum(cls["unmapped"].values()),
        },
        "rewritten_ids": [
            {"old": k, "new": v["new"], "occurrences": v["occurrences"]}
            for k, v in sorted(cls["rewritten"].items())
        ],
        "must_rejudge_ids": [
            {"old": k, "op": v["op"], "occurrences": v["occurrences"]}
            for k, v in sorted(cls["must_rejudge"].items())
        ],
        "already_new_ids": [
            {"id": k, "occurrences": v} for k, v in sorted(cls["already_new"].items())
        ],
        "unmapped_ids": [
            {"id": k, "occurrences": v} for k, v in sorted(cls["unmapped"].items())
        ],
    }


def build_overall_report(mode: str, id_map_path: str, file_reports: list) -> dict:
    totals = {"files": len(file_reports), "matches_found": 0, "rewritten": 0, "must_rejudge": 0,
              "already_new": 0, "unmapped": 0}
    for fr in file_reports:
        totals["matches_found"] += fr["matches_found"]
        for k in ("rewritten", "must_rejudge", "already_new", "unmapped"):
            totals[k] += fr["counts"][k]
    return {
        "mode": mode,
        "id_map_path": id_map_path,
        "files": file_reports,
        "totals": totals,
        "ok": totals["unmapped"] == 0,
    }


def _write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--id-map", required=True)
    p.add_argument("--files", required=True, nargs="+")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="只印報表，不寫檔（預設）")
    mode.add_argument("--apply", action="store_true", help="寫回檔案＋留 <file>.remap-report.json")
    args = p.parse_args()

    for fp in args.files:
        if not os.path.isfile(fp):
            _fail(f"--files 指到不存在的檔案：{fp}")

    id_map = load_id_map(args.id_map)
    old_index, new_ids = build_indexes(id_map)

    texts: dict = {}
    file_reports = []
    for fp in args.files:
        with open(fp, "r", encoding="utf-8", newline="") as f:
            text = f.read()
        texts[fp] = text
        ids = scan_ids(text)
        cls = classify(ids, old_index, new_ids)
        file_reports.append((fp, cls, file_report(fp, cls)))

    apply_mode = bool(args.apply)
    overall = build_overall_report(
        "apply" if apply_mode else "dry_run", args.id_map, [fr for _, _, fr in file_reports],
    )
    print(json.dumps(overall, ensure_ascii=False, indent=2, sort_keys=True))

    if not overall["ok"]:
        return 2

    if apply_mode:
        for fp, cls, fr in file_reports:
            new_text = rewrite_text(texts[fp], cls["rewritten"])
            with open(fp, "w", encoding="utf-8", newline="") as f:
                f.write(new_text)
            _write_json(fp + ".remap-report.json", fr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
