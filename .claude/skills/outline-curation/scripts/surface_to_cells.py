#!/usr/bin/env python3
"""步 0 → 步 4／5 的橋：把頁面樹基準（`page_surface.py`）或功能全表（`feature_surface.py`）的分母單位轉成缺口地圖格（demand-v2 同形）。

為什麼：步 4（`answerability_args.py --cells`）與步 5（`tools/gapmap/coverage_map.py::reweigh`）只吃 demand-v2 形狀的
`cells[]`（`id／module／topic／questions／g0.authority`）＋量測層 map（`cause_state／entry_state／coverage`）；
原本只有售前 55 格手工檔。本橋讓分母＝產品功能面（DSP-064）也能走完七步、兩身分共用，⛔ 不另立需求面分母。

規則（決定性）：
- 只取分母種類（頁面樹預設 spa,blade 且 `in_baseline`；功能全表 action,help），⛔ 不取 route；兩個開放身分（D3）都判 `internal`／`tenant_not_open`／`out_of_scope` 的單位跳過（由 0b 判定檔決定，缺判定檔則只跳 internal）。
- 格 id＝`F` + 三位序號（依 unit_id 排序）；`questions`：help 格種入頁標題（問句形），action 格空（步 3 掛講法；空格在步 4 被擋是預期）；0b 判定與 unit_id 放 `_meta.trace`（系統判定欄位 ⛔ 不進格，步 4 白名單擋）；`topic`＝單位 label；`questions`＝[]（問法在步 3 從真實問句掛）；
  `g0.authority`＝`help:<file>` 或 `code:config/character.php:<action>`；`module`＝0b 判定的細目所在架（有 fine_ids 時）否則空字串。
- 量測層 map：每格 `cause_state="NOT_MEASURED"`、`entry_state=""`、`coverage=""`（尚未跑系統量測；`coverage_map` 對此不判任何 gap）。

用法：
  python3 surface_to_cells.py --surface <feature-surface.json> [--coverage <feature-coverage.json>] \\
      --out-cells <cells.json> --out-map <map.json>
  python3 surface_to_cells.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _envelope import sha256_file  # noqa: E402

SKIP_VERDICTS = ("internal", "tenant_not_open", "out_of_scope")
IDENTITIES = ("prospect", "property_manager")  # 與 feature_coverage_check.IDENTITIES 同源（D3）
PAGE_KINDS = ("spa", "blade")


def build(surface: dict, coverage: dict | None, kinds: set[str]) -> tuple[dict, dict]:
    units = surface["payload"]["units"]
    verdicts = {c["unit_id"]: c for c in (coverage or {}).get("cells", [])}
    cells, mcells, trace = [], [], []
    n = 0
    seen: set = set()
    for u in sorted(units, key=lambda u: u["unit_id"]):
        if u["kind"] not in kinds or u.get("internal") or u["unit_id"] in seen:
            continue
        if u["kind"] in PAGE_KINDS and not u.get("in_baseline"):
            continue
        seen.add(u["unit_id"])
        v = verdicts.get(u["unit_id"])
        by = (v or {}).get("by_identity", {})
        if v and all(by[i]["verdict"] in SKIP_VERDICTS for i in IDENTITIES):
            continue
        n += 1
        cid = f"F{n:03d}"
        if u["kind"] == "help":
            authority = f"help:{u['evidence']}"
            help_center = [u["evidence"].split("#")[0]]
            questions = [u["label"].split("／")[0]]  # 幫助中心頁標題本身是問句形（常見問題）或主題句；步 3 再掛真實問法
        elif u["kind"] in PAGE_KINDS:
            authority = f"code:{u['source']}:{u['label']}"  # 頁面樹格：路由檔＋路由名（jgb2 master）
            help_center = []
            questions = []  # 頁面無問句；步 3 掛講法前，步 4 對此格會擋（questions 空）＝預期閘
        else:
            authority = f"code:{u['evidence']}"
            help_center = []
            questions = []  # 權限 action 無問句；步 3 掛講法前，步 4 對此格會擋（questions 空）＝預期閘
        module = ""
        first_fine = next((by[i]["fine_ids"][0] for i in ("property_manager", "prospect") if by.get(i, {}).get("fine_ids")), "")
        if first_fine:
            module = first_fine.split("/")[1] if first_fine.count("/") >= 2 else ""
        cells.append({
            "id": cid, "module": module, "topic": u["label"], "questions": questions, "keywords": [],
            "sources": [u.get("evidence") or authority[len("code:"):]], "help_center": help_center, "intent": "", "policy": "",
            "note": "；".join(f"{i}：{by[i]['note']}" for i in IDENTITIES if by.get(i, {}).get("note")), "rubric": "", "g0": {"authority": authority},
        })
        # 0b 判定屬系統判定欄位，⛔ 不進格（步 4 白名單擋）；放 sidecar `trace`（每身分）
        trace.append({"id": cid, "unit_id": u["unit_id"], "by_identity_0b": {i: {"verdict": by[i]["verdict"], "fine_ids": by[i]["fine_ids"]} for i in IDENTITIES} if by else {}})
        mcells.append({"id": cid, "cause_state": "NOT_MEASURED", "entry_state": "", "coverage": ""})
    if not cells:
        sys.exit("❌ 轉出 0 格——分母種類或 0b 判定檔不對，⛔ 不得當作沒有缺口")
    meta = {"scope": "頁面樹基準（DSP-065）／功能全表（粒度對照），每格×兩身分判定（D5）", "source_surface_jgb2_sha": surface["payload"]["sources"]["jgb2_sha"],
            "kinds": sorted(kinds), "n_cells": len(cells)}
    return {"_meta": {**meta, "trace": trace}, "cells": cells}, {"_meta": {**meta, "states": {"NOT_MEASURED": "尚未跑系統量測"}}, "cells": mcells}


def self_test() -> int:
    fails = []
    surface = {"payload": {"sources": {"jgb2_sha": "x"}, "units": [
        {"unit_id": "action:a", "kind": "action", "label": "A", "evidence": "config/character.php:'a'", "internal": False},
        {"unit_id": "help:h.html#s", "kind": "help", "label": "H", "evidence": "h.html#s", "internal": False},
        {"unit_id": "route:X", "kind": "route", "label": "R", "evidence": "routes/web.php:x", "internal": False},
        {"unit_id": "route:Admin\\Y", "kind": "route", "label": "Y", "evidence": "routes/web.php:y", "internal": True},
    ]}}
    J = lambda v, f=(), n="": {"verdict": v, "fine_ids": list(f), "note": n}
    cov = {"cells": [{"unit_id": "help:h.html#s", "by_identity": {"prospect": J("missing"), "property_manager": J("partial", ["jgb/E/x"], "n")}},
                     {"unit_id": "action:a", "by_identity": {"prospect": J("missing"), "property_manager": J("missing")}}]}
    c1, m1 = build(surface, cov, {"action", "help"}); c2, _ = build(surface, cov, {"action", "help"})
    if c1 != c2 or [c["id"] for c in c1["cells"]] != ["F001", "F002"] or any(k in c1["cells"][0] for k in ("unit_id", "verdict_0b", "by_identity_0b")):
        fails.append("① 不決定性或 id 序錯（route 必須被排除）")
    by = {t["unit_id"]: c for t, c in zip(c1["_meta"]["trace"], c1["cells"])}
    if by["help:h.html#s"]["module"] != "E" or by["help:h.html#s"]["g0"]["authority"] != "help:h.html#s":
        fails.append("② help 格的 module／authority 錯")
    if by["action:a"]["g0"]["authority"] != "code:config/character.php:'a'" or by["action:a"]["module"] != "":
        fails.append("③ action 格的 authority／module 錯")
    if len(m1["cells"]) != 2 or m1["cells"][0]["cause_state"] != "NOT_MEASURED":
        fails.append("④ 量測層 map 形狀錯")
    cov2 = {"cells": [{"unit_id": "action:a", "by_identity": {"prospect": J("out_of_scope"), "property_manager": J("out_of_scope")}}]}
    c3, _ = build(surface, cov2, {"action", "help"})
    if [t["unit_id"] for t in c3["_meta"]["trace"]] != ["help:h.html#s"]:
        fails.append("⑤ 兩身分皆 out_of_scope 沒被跳過")
    cov3 = {"cells": [{"unit_id": "action:a", "by_identity": {"prospect": J("out_of_scope"), "property_manager": J("covered", ["jgb/B/y"])}}]}
    c4, _ = build(surface, cov3, {"action", "help"})
    if [t["unit_id"] for t in c4["_meta"]["trace"]] != ["action:a", "help:h.html#s"] or c4["cells"][0]["module"] != "B":
        fails.append("⑤b 單一身分 covered 的格被錯跳或 module 錯")
    page_surface = {"payload": {"sources": {"jgb2_sha": "x"}, "units": [
        {"unit_id": "page:bills.list", "kind": "spa", "label": "bills.list", "source": "bills.js", "in_baseline": True},
        {"unit_id": "page:nthurc.list", "kind": "spa", "label": "nthurc.list", "source": "index.js", "in_baseline": False},
        {"unit_id": "page:web:contracts.sign", "kind": "blade", "label": "contracts.sign", "source": "routes/web.php", "in_baseline": True}]}}
    c5, _ = build(page_surface, None, {"spa", "blade"})
    if [t["unit_id"] for t in c5["_meta"]["trace"]] != ["page:bills.list", "page:web:contracts.sign"] or c5["cells"][0]["g0"]["authority"] != "code:bills.js:bills.list":
        fails.append(f"⑦ 頁面樹格：非基準未跳或 authority 錯：{[t['unit_id'] for t in c5['_meta']['trace']]}")
    try:
        build(surface, cov, {"nothing"}); fails.append("⑥ 0 格沒大聲失敗")
    except SystemExit:
        pass
    for f in fails:
        print("❌ self-test:", f)
    if not fails:
        print("✅ self-test 通過（正對照 6、負對照 2、決定性 1）")
    return 1 if fails else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    ap = argparse.ArgumentParser()
    ap.add_argument("--surface", required=True)
    ap.add_argument("--coverage", default=None)
    ap.add_argument("--kinds", default=None, help="分母種類；預設依 surface step：page_surface ⇒ spa,blade、feature_surface ⇒ action,help")
    ap.add_argument("--out-cells", required=True)
    ap.add_argument("--out-map", required=True)
    a = ap.parse_args()
    surface = json.load(open(a.surface, encoding="utf-8"))
    coverage = json.load(open(a.coverage, encoding="utf-8")) if a.coverage else None
    kinds = a.kinds or ("spa,blade" if surface.get("step") == "page_surface" else "action,help")
    cells, mmap = build(surface, coverage, set(kinds.split(",")))
    cells["_meta"]["inputs_sha"] = {"surface": sha256_file(a.surface), **({"coverage": sha256_file(a.coverage)} if a.coverage else {})}
    for path, obj in ((a.out_cells, cells), (a.out_map, mmap)):
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"✅ 缺口地圖格：{len(cells['cells'])} 格（種類 {kinds}）→ {a.out_cells}；量測層 stub → {a.out_map}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
