#!/usr/bin/env python3
"""步 0b 分批與合併（頁面樹基準，DSP-065；每格×兩身分，D5）。

worklist：把 0a `in_baseline` 的格按架分成固定批（每批一個唯讀判定子代理），寫 `<out-dir>/worklist-<批>.json`
         （只含 unit_id／label／path／component／shelf／kind；⛔ 不含判定欄）。
merge   ：把各批 `<out-dir>/coverage-<批>.json`（`{"cells":[{unit_id, by_identity}]}`）合成一份 `feature-coverage.json`；
         非基準格（住都專屬／無頁面元件／非功能／租客側）機械填：租客側 ⇒ tenant_not_open，其餘 ⇒ out_of_scope（兩身分同值，note 寫原因）；
         每個基準格必須恰在一批出現，缺／重／0a 沒有的格 ⇒ exit 2；判定後被歸架表移出基準的格 ⇒ 判定作廢、機械填並印數。決定性。
用法：
  python3 page_coverage_batches.py worklist --surface <page-surface.json> --out-dir <run>
  python3 page_coverage_batches.py merge --surface <page-surface.json> --out-dir <run> --out <run>/feature-coverage.json
  python3 page_coverage_batches.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

BATCHES = {"1": ("A", "B", "G", "H", "I"), "2": ("C", "F"), "3": ("D", "E")}  # 固定分批：架不重疊、每批 ≤ 80 格
IDENTITIES = ("prospect", "property_manager")
KEEP = ("unit_id", "kind", "label", "path", "component", "shelf")


def _batch_of(shelf: str) -> str:
    for b, shelves in BATCHES.items():
        if shelf in shelves:
            return b
    raise SystemExit(f"❌ 架 {shelf!r} 不在任何批——BATCHES 沒覆蓋九架，⛔ 不得靜默漏格")


def worklist(surface: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {b: [] for b in BATCHES}
    for u in sorted(surface["payload"]["units"], key=lambda u: u["unit_id"]):
        if u["in_baseline"]:
            out[_batch_of(u["shelf"])].append({k: u[k] for k in KEEP})
    if any(not v for v in out.values()):
        raise SystemExit(f"❌ 有批是空的：{ {b: len(v) for b, v in out.items()} }")
    return out


def _mechanical(u: dict) -> dict:
    if u["side"] == "租客側":
        v, why = "tenant_not_open", "租客側（DSP-054 未開）"
    elif u.get("vendor_specific"):
        v, why = "out_of_scope", "住都特定業者專屬（DSP-065）"
    elif u.get("no_page"):
        v, why = "out_of_scope", "無頁面元件（父路由轉址／catch-all，DSP-065a）"
    else:
        v, why = "out_of_scope", "非功能頁（D4：結果頁／匯入匯出／404／行銷頁）"
    return {"unit_id": u["unit_id"], "by_identity": {i: {"verdict": v, "fine_ids": [], "note": why} for i in IDENTITIES}}


def merge(surface: dict, batches: dict[str, dict], surface_path: str) -> dict:
    units = {u["unit_id"]: u for u in surface["payload"]["units"]}
    base_ids = {uid for uid, u in units.items() if u["in_baseline"]}
    judged: dict[str, dict] = {}
    seen = Counter()
    dropped: list[str] = []
    for b, cov in batches.items():
        for c in cov["cells"]:
            if c["unit_id"] not in units:
                raise SystemExit(f"❌ 批 {b} 有 0a 沒有的格：{c['unit_id']}")
            if c["unit_id"] not in base_ids:
                dropped.append(c["unit_id"])  # 判定後基準收窄（歸架表改 ⇒ 不計）：判定作廢、機械填
                continue
            seen[c["unit_id"]] += 1
            if set(c.get("by_identity", {})) != set(IDENTITIES):
                raise SystemExit(f"❌ 批 {b} 格 {c['unit_id']} 身分不齊：{sorted(c.get('by_identity', {}))}")
            judged[c["unit_id"]] = {"unit_id": c["unit_id"], "by_identity": c["by_identity"]}
    dup = [k for k, n in seen.items() if n > 1]
    if dup:
        raise SystemExit(f"❌ 格在多批重複：{dup[:5]}")
    missing = sorted(base_ids - set(judged))
    if missing:
        raise SystemExit(f"❌ 基準格未判：{missing[:5]}… 共 {len(missing)}")
    if dropped:
        print(f"ℹ️ 判定後移出基準、改機械填：{len(dropped)} 格 {sorted(dropped)[:6]}…")
    cells = [judged[uid] if uid in judged else _mechanical(units[uid]) for uid in sorted(units)]
    return {"surface_json": surface_path, "surface_jgb2_sha": surface["payload"]["sources"]["jgb2_sha"], "cells": cells}


def self_test() -> int:
    fails = []
    U = lambda uid, shelf, base=True, **kw: {"unit_id": uid, "kind": "spa", "label": uid, "path": "/x", "component": "x.vue", "shelf": shelf,
                                             "side": kw.get("side", "房東側"), "vendor_specific": kw.get("vendor", False), "no_page": kw.get("no_page", False), "in_baseline": base}
    surf = {"payload": {"sources": {"jgb2_sha": "sha"}, "units": [U("page:a1", "A"), U("page:c1", "C"), U("page:d1", "D"),
            U("page:n1", "", False, vendor=True), U("page:p1", "A", False, no_page=True), U("page:t1", "A", False, side="租客側"), U("page:r1", "-", False)]}}
    wl = worklist(surf)
    if {b: [u["unit_id"] for u in v] for b, v in wl.items()} != {"1": ["page:a1"], "2": ["page:c1"], "3": ["page:d1"]} or "in_baseline" in wl["1"][0]:
        fails.append(f"① worklist 分批錯：{wl}")
    J = lambda v, f=(): {"verdict": v, "fine_ids": list(f), "note": ""}
    B = {b: {"cells": [{"unit_id": u["unit_id"], "by_identity": {"prospect": J("missing"), "property_manager": J("covered", ["jgb/A/x"])}} for u in v]} for b, v in wl.items()}
    m1, m2 = merge(surf, B, "s.json"), merge(surf, B, "s.json")
    by = {c["unit_id"]: c for c in m1["cells"]}
    if m1 != m2 or len(m1["cells"]) != 7 or by["page:n1"]["by_identity"]["prospect"]["verdict"] != "out_of_scope" \
            or by["page:t1"]["by_identity"]["property_manager"]["verdict"] != "tenant_not_open" or by["page:a1"]["by_identity"]["property_manager"]["fine_ids"] != ["jgb/A/x"] \
            or "無頁面元件" not in by["page:p1"]["by_identity"]["prospect"]["note"] or m1["surface_jgb2_sha"] != "sha":
        fails.append("② merge 機械填／決定性錯")
    B2 = {**B, "1": {"cells": B["1"]["cells"] + [{"unit_id": "page:r1", "by_identity": {"prospect": J("covered", ["jgb/A/x"]), "property_manager": J("covered", ["jgb/A/x"])}}]}}
    m3 = merge(surf, B2, "s.json")
    if {c["unit_id"]: c for c in m3["cells"]}["page:r1"]["by_identity"]["prospect"]["verdict"] != "out_of_scope":
        fails.append("⑥ 移出基準的格沒被機械填覆蓋")
    for label, bad in (("③ 缺批格", {**B, "1": {"cells": []}}), ("④ 0a 沒有的格", {**B, "1": {"cells": B["1"]["cells"] + [{"unit_id": "page:zz", "by_identity": {}}]}}),
                       ("⑤ 身分不齊", {**B, "2": {"cells": [{"unit_id": "page:c1", "by_identity": {"prospect": J("missing")}}]}})):
        try:
            merge(surf, bad, "s.json"); fails.append(f"{label} 沒大聲失敗")
        except SystemExit as e:
            if not str(e).startswith("❌"):
                fails.append(f"{label} 失敗訊息不對：{e}")
    for f in fails:
        print("❌ self-test:", f)
    if not fails:
        print("✅ self-test 通過（正對照 3、負對照 3、決定性 1）")
    return 1 if fails else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("worklist", "merge"))
    ap.add_argument("--surface", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    surface = json.load(open(a.surface, encoding="utf-8"))
    if surface.get("step") != "page_surface":
        print("❌ surface 不是 page_surface"); return 2
    os.makedirs(a.out_dir, exist_ok=True)
    if a.cmd == "worklist":
        wl = worklist(surface)
        for b, v in wl.items():
            json.dump({"batch": b, "shelves": BATCHES[b], "units": v}, open(os.path.join(a.out_dir, f"worklist-{b}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("✅ worklist：" + "、".join(f"批 {b}（{'/'.join(BATCHES[b])}）{len(v)} 格" for b, v in wl.items()) + f" → {a.out_dir}")
        return 0
    try:
        batches = {b: json.load(open(os.path.join(a.out_dir, f"coverage-{b}.json"), encoding="utf-8")) for b in BATCHES}
    except FileNotFoundError as e:
        print(f"❌ 缺批判定檔：{e.filename}"); return 2
    try:
        cov = merge(surface, batches, a.surface)
    except SystemExit as e:
        print(e); return 2
    out = a.out or os.path.join(a.out_dir, "feature-coverage.json")
    json.dump(cov, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = Counter(j["verdict"] for c in cov["cells"] for j in c["by_identity"].values())
    print(f"✅ 合併 {len(cov['cells'])} 格 → {out}；判定分布 " + "、".join(f"{k} {v}" for k, v in sorted(n.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
