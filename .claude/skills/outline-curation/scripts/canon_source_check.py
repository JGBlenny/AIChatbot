#!/usr/bin/env python3
"""canon_source_check：正本一致性檢查——講法有 `helpcenter:<slug>` 來源，`sources` 卻沒有對應 `helpcenter:` 項目（F1）。

⛔ 唯讀：只解析、不改任何檔（不套用到真正的正本）。

判準：細目任一 `phrasings[].source` 為 `helpcenter:<slug>`（前綴比對），而該細目 `sources[]`
內沒有任何 `helpcenter:` 開頭的項目 ⇒ 該細目列入問題清單。有問題 ⇒ 印清單、exit 2；否則 exit 0。
"""
from __future__ import annotations

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "..", "rag-orchestrator"))
for cand in (_RAG, "/app"):
    if os.path.isdir(os.path.join(cand, "services")) and cand not in sys.path:
        sys.path.insert(0, cand)

try:
    from services.agent.canon.canon_parser import parse_canon  # noqa: E402
except ImportError as exc:  # pragma: no cover
    print(f"[canon_source_check] 無法匯入 rag-orchestrator services（{type(exc).__name__}）：請在 repo 根或容器內執行", file=sys.stderr)
    raise SystemExit(2)


def find_missing_helpcenter_sources(canon_path: str) -> list[dict]:
    """回傳有問題的細目清單：[{fine_id, phrasing_sources}]（有 helpcenter: 講法但 sources 缺對應項目）。"""
    doc = parse_canon(canon_path)
    problems = []
    for f in doc.fines():
        hc_phrasing_sources = sorted({p.source for p in f.phrasings if p.source.startswith("helpcenter:")})
        if not hc_phrasing_sources:
            continue
        has_hc_source = any(s.startswith("helpcenter:") for s in f.sources)
        if not has_hc_source:
            problems.append({"fine_id": f.id, "phrasing_sources": hc_phrasing_sources})
    return problems


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--canon", required=True, help="要檢查的正本（或草稿）Markdown")
    a = p.parse_args()

    problems = find_missing_helpcenter_sources(a.canon)
    if problems:
        print(f"[canon_source_check] {len(problems)} 個細目有 helpcenter: 講法但 sources 缺對應項目：", file=sys.stderr)
        for pr in problems:
            print(f"  {pr['fine_id']}: {pr['phrasing_sources']}", file=sys.stderr)
        return 2
    print("[canon_source_check] ok：所有 helpcenter: 講法都有對應 sources 項目")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
