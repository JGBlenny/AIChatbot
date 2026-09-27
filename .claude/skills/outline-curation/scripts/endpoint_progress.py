#!/usr/bin/env python3
"""終點指標（Plan 9.15 S1）：HANDOFF §1 終點＝頁面樹每件事 × 開放身分，各有一條 `reviewed` 的細目。
每份計畫與每次回報先看這支的第一行（記憶 `feedback_endpoint_metric_first`）。

- M1（主指標）：`reviewed_by` 非空、且 `target_user` 含該身分的細目數／該身分細目數；逐架列。
- M2（覆蓋，代理指標）：page-surface `in_baseline` 的頁，有幾頁被「已審且含該身分」的細目 `sources` 指到：
  SPA 頁 ⇔ `code:src/pages/<component>` 逐字相等；blade 頁（`Controller@method`）⇔
  `code:app/Http/Controllers/(<子目錄>/)*<Controller>.php`（控制器檔層級）。⚠️ 近似，只看趨勢。
- `--ignore-review`：關掉已審過濾，只供正對照（Plan 9.15 §1：現樹不分身分須為 132／183）。

前置拿不到（正本／page-surface 不存在、細目 0、細目數與標題數不符）⇒ 非 0 並印原因（⛔ 不靜默）。
解析一律走 `canon_items.parse_canon_auto`（需容器依賴：`docker compose -f docker-compose.dev.yml run --rm -T
--no-deps rag-orchestrator python3 /.claude/skills/outline-curation/scripts/endpoint_progress.py …`）。
用法：endpoint_progress.py --canon <正本目錄> --surface <page-surface.json> [--json] [--ignore-review]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canon_items import fine_shelf_letter, parse_canon_auto  # noqa: E402

IDENTITIES = ("property_manager", "prospect")  # 開放身分（D3；租客未開）
_HEADING_RE = re.compile(r"^### .*\{#jgb/", re.M)


def is_reviewed(fine) -> bool:
    return bool((fine.reviewed_by or "").strip())


def code_paths(fine) -> set:
    return {s[len("code:"):] for s in (fine.sources or ()) if s.startswith("code:")}


def page_hit(unit: dict, paths: set) -> bool:
    comp = unit.get("component") or ""
    if not comp:
        return False
    if unit.get("kind") == "spa":
        return f"src/pages/{comp}" in paths
    ctrl = re.escape(comp.split("@")[0])
    rx = re.compile(rf"app/Http/Controllers/(?:.+/)?{ctrl}\.php")
    return any(rx.fullmatch(p) for p in paths)


def pages_covered(units: list, fines: list) -> int:
    paths = set().union(*(code_paths(f) for f in fines)) if fines else set()
    return sum(1 for u in units if page_hit(u, paths))


def measure(canon: str, surface: str, ignore_review: bool = False) -> dict:
    if not os.path.exists(canon):
        raise SystemExit(f"❌ 正本不存在：{canon}")
    if not os.path.isfile(surface):
        raise SystemExit(f"❌ page-surface 不存在：{surface}")
    fines = parse_canon_auto(canon).fines()
    if not fines:
        raise SystemExit("❌ 正本解析出 0 條細目（工具或路徑壞了，不是「沒有細目」）")
    if os.path.isdir(canon):  # 正對照：解析數＝標題數
        heads = sum(len(_HEADING_RE.findall(open(p, encoding="utf-8").read()))
                    for p in glob.glob(os.path.join(canon, "*.md")))
        if heads != len(fines):
            raise SystemExit(f"❌ 解析細目 {len(fines)} ≠ 標題 {heads}")
    units = [u for u in json.load(open(surface, encoding="utf-8"))["payload"]["units"] if u.get("in_baseline")]
    if not units:
        raise SystemExit("❌ page-surface 的 in_baseline 頁數為 0")
    out = {"fines": len(fines), "pages": len(units), "by_identity": {}, "by_shelf": {}}
    for ident in IDENTITIES:
        mine = [f for f in fines if ident in (f.target_user or ())]
        rev = [f for f in mine if ignore_review or is_reviewed(f)]
        out["by_identity"][ident] = {"reviewed": sum(1 for f in mine if is_reviewed(f)), "total": len(mine),
                                     "pages": pages_covered(units, rev)}
        for f in mine:
            s = out["by_shelf"].setdefault(fine_shelf_letter(f.id), {i: [0, 0] for i in IDENTITIES})
            s[ident][1] += 1
            s[ident][0] += is_reviewed(f)
    if ignore_review:
        out["pages_any_identity_ignore_review"] = pages_covered(units, fines)
    return out


def headline(m: dict) -> str:
    pm, pr = m["by_identity"]["property_manager"], m["by_identity"]["prospect"]
    return (f"已審細目 pm {pm['reviewed']}／{pm['total']}、prospect {pr['reviewed']}／{pr['total']}；"
            f"頁面 pm {pm['pages']}／{m['pages']}、prospect {pr['pages']}／{m['pages']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--canon", required=True)
    ap.add_argument("--surface", required=True)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ignore-review", action="store_true", help="關掉已審過濾（只供正對照）")
    a = ap.parse_args(argv)
    m = measure(a.canon, a.surface, a.ignore_review)
    if a.json:
        print(json.dumps(m, ensure_ascii=False, indent=1))
        return 0
    if a.ignore_review:
        pm, pr = m["by_identity"]["property_manager"], m["by_identity"]["prospect"]
        print(f"正對照（不過濾已審）：頁面 不分身分 {m['pages_any_identity_ignore_review']}／{m['pages']}；"
              f"pm {pm['pages']}、prospect {pr['pages']}")
        return 0
    print(headline(m))
    for shelf in sorted(m["by_shelf"]):
        s = m["by_shelf"][shelf]
        print(f"  {shelf}：pm {s['property_manager'][0]}／{s['property_manager'][1]}、"
              f"prospect {s['prospect'][0]}／{s['prospect'][1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
