#!/usr/bin/env python3
"""步 6 diff（knowledge-outline-and-intent-architecture 任務 1.3｜design 元件 1）。

輸出結構差異（粗目／細目新增／刪除／改名）、id_map 原樣、取代對應表 replacements[]，
並把狀態檔 `.claude/hooks/state/outline-gate/session.json` 的 `diff_report` 鍵寫成
{"path": <相對 repo 根>, "inputs_sha": {"canon": <new-canon sha256>}}（合併寫入，不清掉其他鍵）。

id_map 格式（本任務定義）：JSON 陣列，每筆 {"old_kb_id": str, "fine_id": str,
"op": "keep"|"move"|"merge"|"new", "source": "phrasing"|...(選填)}。
op → how 對映：keep/move → "content"；merge → "merged_into"；
new 且 source=="phrasing" → "phrasing_only"。

缺 --id-map ⇒ exit 2。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _envelope import find_repo_root, make_envelope, sha256_file, update_state, write_json  # noqa: E402

SKILL_VERSION = "0.1.0"

_H2_RE = re.compile(r'^##\s+(.*?)\s*\{#([^}]+)\}\s*$', re.MULTILINE)
_H3_RE = re.compile(r'^###\s+(.*?)\s*\{#([^}]+)\}\s*$', re.MULTILINE)

_OP_TO_HOW = {
    "keep": "content",
    "move": "content",
    "merge": "merged_into",
}


def _headings(text: str, pattern: re.Pattern) -> dict:
    """回 {id: title}。"""
    return {m.group(2): m.group(1) for m in pattern.finditer(text)}


def _read_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def structure_diff(old_text: str | None, new_text: str) -> dict:
    new_h2 = _headings(new_text, _H2_RE)
    new_h3 = _headings(new_text, _H3_RE)
    old_h2 = _headings(old_text, _H2_RE) if old_text is not None else {}
    old_h3 = _headings(old_text, _H3_RE) if old_text is not None else {}

    added = []
    removed = []
    renamed = []

    for level, old_h, new_h in (("h2", old_h2, new_h2), ("h3", old_h3, new_h3)):
        for hid, title in new_h.items():
            if hid not in old_h:
                added.append({"level": level, "id": hid, "title": title})
        for hid, title in old_h.items():
            if hid not in new_h:
                removed.append({"level": level, "id": hid, "title": title})
        for hid in set(old_h) & set(new_h):
            if old_h[hid] != new_h[hid]:
                renamed.append({"level": level, "id": hid, "from": old_h[hid], "to": new_h[hid]})

    return {
        "headings_added": sorted(added, key=lambda x: (x["level"], x["id"])),
        "headings_removed": sorted(removed, key=lambda x: (x["level"], x["id"])),
        "headings_renamed": sorted(renamed, key=lambda x: (x["level"], x["id"])),
    }


def build_replacements(id_map: list) -> list:
    out = []
    for entry in id_map:
        old_kb_id = str(entry.get("old_kb_id", ""))
        fine_id = str(entry.get("fine_id", ""))
        op = entry.get("op", "")
        source = entry.get("source", "")
        if op == "new" and source == "phrasing":
            how = "phrasing_only"
        elif op in _OP_TO_HOW:
            how = _OP_TO_HOW[op]
        else:
            # 未知 op 一律視為 content（保守：不遺漏取代紀錄）
            how = "content"
        out.append({"old_kb_id": old_kb_id, "fine_id": fine_id, "how": how})
    return sorted(out, key=lambda r: (r["old_kb_id"], r["fine_id"]))


def main() -> int:
    p = argparse.ArgumentParser(description="步 6 diff：結構差異＋id 對應表＋取代對應表")
    p.add_argument("--new-canon", required=True)
    p.add_argument("--old-canon", required=False, default=None)
    p.add_argument("--id-map", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--frozen-at", required=True)
    args = p.parse_args()

    if not args.id_map or not os.path.isfile(args.id_map):
        print(f"[diff_report] 缺 --id-map（{args.id_map}）", file=sys.stderr)
        return 2

    with open(args.id_map, encoding="utf-8") as f:
        id_map = json.load(f)
    if not isinstance(id_map, list):
        print("[diff_report] --id-map 內容必須是列表", file=sys.stderr)
        return 2

    new_text = _read_text(args.new_canon)
    old_text = _read_text(args.old_canon) if args.old_canon and os.path.isfile(args.old_canon) else None

    diff = structure_diff(old_text, new_text)
    replacements = build_replacements(id_map)

    inputs_sha = {"new_canon": sha256_file(args.new_canon)}
    if args.old_canon and os.path.isfile(args.old_canon):
        inputs_sha["old_canon"] = sha256_file(args.old_canon)
    else:
        inputs_sha["old_canon"] = None

    payload = {
        "structure_diff": diff,
        "id_map": id_map,
        "replacements": replacements,
    }
    envelope = make_envelope(
        step="diff",
        skill_version=SKILL_VERSION,
        inputs_sha=inputs_sha,
        deterministic=True,
        payload=payload,
    )
    write_json(args.out, envelope)

    try:
        repo_root = find_repo_root()
        out_rel = os.path.relpath(os.path.abspath(args.out), repo_root)
        update_state(repo_root, {
            "diff_report": {
                "path": out_rel,
                "inputs_sha": {"canon": inputs_sha["new_canon"]},
            }
        })
    except RuntimeError as e:
        print(f"[diff_report] 警告：找不到 repo 根，跳過狀態檔寫入（{e}）", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
