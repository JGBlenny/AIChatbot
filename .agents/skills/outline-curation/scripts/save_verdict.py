#!/usr/bin/env python3
"""步 4 判者回收：從 Claude Code 子代理 transcript（JSONL）取最後一則 assistant 文字，
解析成 JSON 陣列，存 `<out-dir>/verdicts/<key>.json`（供 `answerability_agents.py collect` 讀）。

用法：save_verdict.py <key> <task-output.jsonl> --out-dir <answerability_agents prepare 的 --out-dir>

容忍：```json 圍欄、陣列前的散文（取第一個 `[` 起 raw_decode）、陣列後的散文。
找不到 assistant 文字或不是陣列 ⇒ exit 2（大聲失敗，不寫檔）。
2026-09-07 前此腳本只存在 gitignore 的 raw/ 目錄（verifier 抓到），現固化於 scripts/。
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def last_assistant_text(path: str) -> str | None:
    last = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            m = rec.get("message") if isinstance(rec, dict) else None
            if isinstance(m, dict) and m.get("role") == "assistant":
                for b in m.get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "text" and (b.get("text") or "").strip():
                        last = b["text"]
    return last


def extract_array(text: str) -> list:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        t = t.rsplit("```", 1)[0]
    i = t.find("[")
    if i < 0:
        raise ValueError("no JSON array start")
    arr, _ = json.JSONDecoder().raw_decode(t[i:])
    if not isinstance(arr, list):
        raise ValueError("decoded value is not a list")
    return arr


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="步 4 判者回收：transcript → verdicts/<key>.json")
    p.add_argument("key")
    p.add_argument("task_output")
    p.add_argument("--out-dir", required=True, help="answerability_agents.py prepare 的 --out-dir")
    a = p.parse_args(argv)

    text = last_assistant_text(a.task_output)
    if not text:
        print(f"[save_verdict] {a.key}: transcript 無 assistant 文字（{a.task_output}）", file=sys.stderr)
        return 2
    try:
        arr = extract_array(text)
    except ValueError as e:
        print(f"[save_verdict] {a.key}: 解析失敗：{e}", file=sys.stderr)
        return 2

    vdir = os.path.join(a.out_dir, "verdicts")
    os.makedirs(vdir, exist_ok=True)
    out = os.path.join(vdir, f"{a.key}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(arr, f, ensure_ascii=False, indent=1)
    print(f"[save_verdict] {a.key}: {len(arr)} 筆 → {out}")
    for x in arr:
        if isinstance(x, dict):
            print(f"  {x.get('cell_id')} {x.get('label')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
