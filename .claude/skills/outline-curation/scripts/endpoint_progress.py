#!/usr/bin/env python3
"""終點指標（Plan 9.15 S1）：HANDOFF §1 終點＝頁面樹每件事 × 開放身分，各有一條 `reviewed` 的細目。
每份計畫與每次回報先看這支的第一行（記憶 `feedback_endpoint_metric_first`）。

- M1（主指標）：`reviewed_by` 非空、且 `target_user` 含該身分的細目數／該身分細目數；逐架列。
- M2（覆蓋，代理指標）：page-surface `in_baseline` 的頁，有幾頁被「已審且含該身分」的細目 `sources` 指到：
  SPA 頁 ⇔ 給了 `--closure` 時：該頁閉包（入口檔＋其 `src/pages/` 內 import 與子路由，`page_import_closure.py` 產出）
  任一檔被 `code:src/pages/<檔>` 引用；不給時只比入口檔（Plan 9.26 前的舊量尺）。blade 頁（`Controller@method`）⇔
  `code:app/Http/Controllers/(<子目錄>/)*<Controller>.php`（控制器檔層級；來源的 `#方法` 後綴先去掉）。
  ⚠️ 代理指標：跨功能共用子元件、外框父路由被子孫引用點亮都會算入；只看趨勢。
- `--ignore-review`：關掉已審過濾，只供正對照（Plan 9.15 §1：現樹不分身分須為 132／183）。

前置拿不到（正本／page-surface 不存在、細目 0、細目數與標題數不符）⇒ 非 0 並印原因（⛔ 不靜默）。
解析一律走 `canon_items.parse_canon_auto`（需容器依賴：`docker compose -f docker-compose.dev.yml run --rm -T
--no-deps rag-orchestrator python3 /.claude/skills/outline-curation/scripts/endpoint_progress.py …`）。
用法：endpoint_progress.py --canon <正本目錄> --surface <page-surface.json> [--closure <page-import-closure.json>] [--json] [--ignore-review]
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
    """`code:` 來源路徑；去掉 `#方法` 後綴（Plan 9.26：`NotificationController.php#index` 比不到 blade 頁）。"""
    return {s[len("code:"):].split("#", 1)[0] for s in (fine.sources or ()) if s.startswith("code:")}


def page_hit(unit: dict, paths: set, closure: dict | None = None) -> bool:
    comp = unit.get("component") or ""
    if not comp:
        return False
    if unit.get("kind") == "spa":
        if closure is None:
            files = [comp]  # 舊量尺：只比入口檔
        elif comp in closure:
            files = closure[comp]  # Plan 9.26：入口檔＋其 src/pages 內 import／子路由閉包
        else:
            raise SystemExit(f"❌ closure 沒有這頁：src/pages/{comp}（閉包與 page-surface 不同版？⛔ 靜默退回只比入口檔）")
        return any(f"src/pages/{f}" in paths for f in files)
    ctrl = re.escape(comp.split("@")[0])
    rx = re.compile(rf"app/Http/Controllers/(?:.+/)?{ctrl}\.php")
    return any(rx.fullmatch(p) for p in paths)


def pages_covered(units: list, fines: list, closure: dict | None = None) -> int:
    paths = set().union(*(code_paths(f) for f in fines)) if fines else set()
    return sum(1 for u in units if page_hit(u, paths, closure))


def load_closure(path: str | None) -> dict | None:
    if not path:
        return None
    if not os.path.isfile(path):
        raise SystemExit(f"❌ closure 不存在：{path}")
    pages = json.load(open(path, encoding="utf-8")).get("pages") or {}
    if not pages:
        raise SystemExit("❌ closure 的 pages 為空（工具或路徑壞了）")
    return pages


def measure(canon: str, surface: str, ignore_review: bool = False, closure: dict | None = None) -> dict:
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
                                     "pages": pages_covered(units, rev, closure)}
        for f in mine:
            s = out["by_shelf"].setdefault(fine_shelf_letter(f.id), {i: [0, 0] for i in IDENTITIES})
            s[ident][1] += 1
            s[ident][0] += is_reviewed(f)
    if ignore_review:
        out["pages_any_identity_ignore_review"] = pages_covered(units, fines, closure)
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
    ap.add_argument("--closure", help="頁面閉包 JSON（page_import_closure.py 產出）；不給＝只比入口檔（舊量尺）")
    a = ap.parse_args(argv)
    m = measure(a.canon, a.surface, a.ignore_review, load_closure(a.closure))
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
