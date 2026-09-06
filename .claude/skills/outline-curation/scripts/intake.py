#!/usr/bin/env python3
"""步 1 intake（knowledge-outline-and-intent-architecture 任務 1.3｜design 元件 1）。

讀 kb 列／草稿／缺口地圖／既有正本 → `intake.json`。純決定性：不讀 DB、不讀網路、
不讀 `.env`；kb 列由呼叫端先匯出成 JSON 檔傳入。

輸出：inputs_sha（各輸入 sha256）、kb 列摘要（id／question_summary 前 40 字）、
drafts 摘要、gapmap 格數、object_under_test 骨架（materials／frozen_at／approved_by=""）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _envelope import make_envelope, sha256_file, write_json  # noqa: E402

SKILL_VERSION = "0.1.0"


def _load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _truncate(s: str, n: int = 40) -> str:
    return s[:n]


def build_payload(kb_path: str, drafts_path: str | None, gapmap_path: str | None,
                   canon_path: str | None, frozen_at: str) -> tuple[dict, dict]:
    kb_rows_raw = _load_json(kb_path)
    if not isinstance(kb_rows_raw, list):
        raise ValueError("--kb-json 內容必須是列表")
    kb_rows = [
        {"id": str(r.get("id", "")), "question_summary": _truncate(str(r.get("question_summary", "")))}
        for r in kb_rows_raw
    ]

    drafts_raw = _load_json(drafts_path) if drafts_path else []
    if not isinstance(drafts_raw, list):
        raise ValueError("--drafts 內容必須是列表")
    drafts = [
        {"id": str(d.get("id", "")), "summary": _truncate(str(d.get("summary", d.get("question_summary", ""))))}
        for d in drafts_raw
    ]

    gapmap_raw = _load_json(gapmap_path) if gapmap_path else []
    if isinstance(gapmap_raw, list):
        gapmap_cells = len(gapmap_raw)
    elif isinstance(gapmap_raw, dict):
        cells = gapmap_raw.get("cells")
        gapmap_cells = len(cells) if isinstance(cells, list) else len(gapmap_raw)
    else:
        gapmap_cells = 0

    materials = [os.path.relpath(p) if os.path.isabs(p) else p for p in [kb_path, drafts_path, gapmap_path, canon_path] if p]

    inputs_sha = {"kb": sha256_file(kb_path)}
    if drafts_path:
        inputs_sha["drafts"] = sha256_file(drafts_path)
    if gapmap_path:
        inputs_sha["gapmap"] = sha256_file(gapmap_path)
    if canon_path:
        inputs_sha["canon"] = sha256_file(canon_path)
    else:
        inputs_sha["canon"] = None

    payload = {
        "frozen_at": frozen_at,
        "kb_rows": kb_rows,
        "drafts": drafts,
        "gapmap_cells": gapmap_cells,
        "object_under_test": {
            "materials": materials,
            "frozen_at": frozen_at,
            "approved_by": "",
        },
    }
    return payload, inputs_sha


def main() -> int:
    p = argparse.ArgumentParser(description="步 1 intake：讀 kb 列／草稿／缺口地圖／既有正本 → intake.json")
    p.add_argument("--kb-json", required=True, help="kb 列 JSON 檔（呼叫端先匯出，⛔ 本腳本不讀 DB）")
    p.add_argument("--drafts", required=False, default=None, help="草稿 JSON 檔")
    p.add_argument("--gapmap", required=False, default=None, help="缺口地圖 JSON 檔")
    p.add_argument("--canon", required=False, default=None, help="既有正本 Markdown（選填）")
    p.add_argument("--out", required=True, help="輸出 intake.json 路徑")
    p.add_argument("--frozen-at", required=True, help="ISO 時間戳，⛔ 不用 datetime.now()")
    args = p.parse_args()

    payload, inputs_sha = build_payload(args.kb_json, args.drafts, args.gapmap, args.canon, args.frozen_at)
    envelope = make_envelope(
        step="intake",
        skill_version=SKILL_VERSION,
        inputs_sha=inputs_sha,
        deterministic=True,
        payload=payload,
    )
    write_json(args.out, envelope)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
