#!/usr/bin/env python3
"""真實問句進場（Plan 9.14 S1-1）：遮蔽後題目 `[{id, q, audience}]` → 每受眾一份步 4／步 5 輸入。

輸出（全部落在 `--out-dir`，並在該目錄建立圍欄標記 `.text-external`）：
  cells-<audience>.json  `{_meta:{text_policy:"external", source_sha256, audience, n},
                           cells:[{id, questions:[q], policy:"", module:"", topic:"", g0:{authority:"none"}}]}`
                         ——`answerability_args.py --cells`／`reweigh.py --demand` 直接吃（`project_cell` 只取
                         id／questions[0]／policy；`g0.authority="none"` ⇒ `no_source` 落 `not_available` 進 5b）。
  map-<audience>.json    `{_meta:{同上}, cells:[{id, cause_state:"NOT_MEASURED", entry_state:"", coverage:""}]}`
                         ——量測層 stub：`coverage_map` 不判任何 gap class（檢索缺口另由 ruler 量）。

⛔ `--out-dir` 的 realpath 位於 rag root 下、或任一祖先有 `.git` ⇒ 非 0 退出、⛔ 不建任何檔
（`rag-orchestrator/tools/text_containment.py::create_marker`，與各呼叫點 `require_contained` 同一個排除函式）。
⛔ `topic` 留空：不寫任何題目衍生字。⛔ stdout／stderr 只印筆數、sha 與路徑，⛔ 不印題目文字。
在主機執行即可（只讀寫 JSON、只用標準庫＋唯一守門模組）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _envelope import sha256_file, text_containment, write_json  # noqa: E402

#: 受眾會進檔名（`cells-<audience>.json`）⇒ 只收小寫英數底線，⛔ 路徑字元。
AUDIENCE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class InputError(ValueError):
    pass


def load_questions(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    if not isinstance(doc, list):
        raise InputError("輸入須為 JSON 陣列 [{id, q, audience}]")
    seen: set[str] = set()
    out = []
    for i, it in enumerate(doc):
        if not isinstance(it, dict):
            raise InputError(f"第 {i} 筆不是物件")
        for k in ("id", "q", "audience"):
            if not isinstance(it.get(k), str) or not it[k].strip():
                raise InputError(f"第 {i} 筆缺 {k} 或非字串")
        if not AUDIENCE_RE.match(it["audience"]):
            raise InputError(f"第 {i} 筆 audience 形狀不合（須 {AUDIENCE_RE.pattern}）")
        if it["id"] in seen:
            raise InputError(f"第 {i} 筆 id 重複")
        seen.add(it["id"])
        out.append({"id": it["id"], "q": it["q"], "audience": it["audience"]})
    return out


def build(questions: list[dict], source_sha256: str) -> dict:
    """回 {audience: (cells_doc, map_doc)}；受眾內保留輸入原序。"""
    by_aud: dict[str, list[dict]] = {}
    for it in questions:
        by_aud.setdefault(it["audience"], []).append(it)
    out = {}
    for aud in sorted(by_aud):
        items = by_aud[aud]
        meta = {"text_policy": "external", "source_sha256": source_sha256, "audience": aud, "n": len(items)}
        cells = [{"id": it["id"], "questions": [it["q"]], "policy": "", "module": "", "topic": "",
                  "g0": {"authority": "none"}} for it in items]
        mcells = [{"id": it["id"], "cause_state": "NOT_MEASURED", "entry_state": "", "coverage": ""} for it in items]
        out[aud] = ({"_meta": dict(meta), "cells": cells}, {"_meta": dict(meta), "cells": mcells})
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="真實問句 [{id,q,audience}] → cells-<aud>.json＋map-<aud>.json（Plan 9.14 S1-1）")
    p.add_argument("--in", dest="inp", required=True, help="遮蔽後題目 JSON（repo 外）")
    p.add_argument("--out-dir", required=True, help="repo 外的 run 目錄；會在此建 .text-external 圍欄標記")
    a = p.parse_args(argv)

    tc = text_containment()
    try:
        questions = load_questions(a.inp)
    except (InputError, ValueError, OSError) as e:
        print(f"[real_questions_to_cells] ⛔ 輸入不合：{type(e).__name__}: {e if isinstance(e, InputError) else '無法讀取或解析'}",
              file=sys.stderr)
        return 2
    try:
        tc.create_marker(a.out_dir)
        tc.require_contained(a.out_dir)
    except tc.TextContainmentError as e:
        print(f"[real_questions_to_cells] ⛔ {e}", file=sys.stderr)
        return 2

    sha = sha256_file(a.inp)
    built = build(questions, sha)
    for aud, (cells_doc, map_doc) in built.items():
        write_json(os.path.join(a.out_dir, f"cells-{aud}.json"), cells_doc)
        write_json(os.path.join(a.out_dir, f"map-{aud}.json"), map_doc)
    counts = " ".join(f"{aud}={len(cd['cells'])}" for aud, (cd, _m) in built.items())
    print(f"[real_questions_to_cells] source_sha256={sha} total={len(questions)} {counts} → {a.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
