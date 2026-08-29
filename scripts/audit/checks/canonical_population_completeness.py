#!/usr/bin/env python3
"""不變量 21：**active responsibility 的 canonical contract 閉合**（業主裁定 2026-08-29）。

⚠️ 這條紅燈是**刻意保留的產品閘**，與不變量 13 同性質：
R10 已選 C2，而 C2 拿 **responsibility-level canonical semantic contract** 做 semantic scoring。
只要還有 `reviewed_active` 的責任 canonical 為 null，實際跑出來的就**不是**已裁定的 target
architecture——會被迫臨時決定 fallback（row scoring／不進 reranker／用 summary／alias max），
每一種都改變 A05 的競爭環境。

## 不變量陳述

> status = reviewed_active  → canonical_responsibility MUST be non-null **且** 已 reviewed
> status = reviewed_historical → ⛔ **不要求** active scoring canonical（3498 不受此閘拘束）

用法：python3 scripts/audit/checks/canonical_population_completeness.py [--self-test]
"""
import copy
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
R10P = os.path.join(REPO, ".kiro", "specs", "conversational-routing-execution", "r10p")
V1 = os.path.join(R10P, "registry.json")
V2C = os.path.join(R10P, "registry-v2-candidate.json")
#: ⚠️ 這條閘看的是**當前工作 registry**：canonical migration 期間 ＝ V2 candidate，
#   否則 ＝ V1。⛔ 不看 V1（V1 是 immutable historical seal，永遠不會轉綠）。
REG = V2C if os.path.exists(V2C) else V1


def load():
    with open(REG, encoding="utf-8") as f:
        return json.load(f)


def violations(reg=None):
    reg = load() if reg is None else reg
    bad = []
    active = [r for r in reg["responsibilities"] if r["status"] == "reviewed_active"]
    if not active:
        bad.append("registry 沒有任何 reviewed_active responsibility")
    for r in active:
        if not r.get("canonical_responsibility"):
            bad.append(f"{r['responsibility_id']}（{r['sealed_from_candidate_group']}）："
                       f"reviewed_active 但 canonical_responsibility 為 null")
        elif r.get("canonical_responsibility_status") != "OWNER_STATED":
            bad.append(f"{r['responsibility_id']}：canonical 有值但狀態為 "
                       f"{r.get('canonical_responsibility_status')!r}——⛔ 未經 review 不算閉合")
    return bad


def self_test() -> int:
    reg = load()
    cases = []
    # 正對照：historical **不得**被這條閘拘束
    hist = [r for r in reg["responsibilities"] if r["status"] == "reviewed_historical"]
    cases.append(("historical 不受此閘拘束（即使 canonical=null）",
                  all(not any(r["responsibility_id"] in v for v in violations(reg)) for r in hist)))
    # 正對照：active 缺 canonical 必須紅
    m = copy.deepcopy(reg)
    tgt = next(r for r in m["responsibilities"] if r["status"] == "reviewed_active")
    tgt["canonical_responsibility"] = None
    tgt["canonical_responsibility_status"] = "PENDING_OWNER_STATEMENT"
    cases.append(("active 缺 canonical 必須紅",
                  any(tgt["responsibility_id"] in v for v in violations(m))))
    # 正對照：canonical 有值但未 review 必須紅
    m2 = copy.deepcopy(reg)
    t2 = next(r for r in m2["responsibilities"] if r["status"] == "reviewed_active")
    t2["canonical_responsibility"] = "某段文字"
    t2["canonical_responsibility_status"] = "PENDING_OWNER_STATEMENT"
    cases.append(("canonical 未經 review 必須紅",
                  any("未經 review 不算閉合" in v for v in violations(m2))))
    # 正對照：全部補齊必須綠
    m3 = copy.deepcopy(reg)
    for r in m3["responsibilities"]:
        if r["status"] == "reviewed_active":
            r["canonical_responsibility"] = "x"
            r["canonical_responsibility_status"] = "OWNER_STATED"
    cases.append(("全部補齊必須綠", violations(m3) == []))
    for n, ok in cases:
        print(f"{'✅' if ok else '❌'} {n}")
    return 1 if any(not ok for _n, ok in cases) else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if not os.path.exists(REG):
        print("（registry 尚未 seal——本條不適用）")
        return 0
    reg = load()
    active = [r for r in reg["responsibilities"] if r["status"] == "reviewed_active"]
    done = [r for r in active if r.get("canonical_responsibility")
            and r.get("canonical_responsibility_status") == "OWNER_STATED"]
    bad = violations(reg)
    if bad:
        print(f"❌ FAIL：active canonical 未閉合（{len(done)}/{len(active)}）")
        print(f"   · 尚缺 {len(bad)} 筆——⚠️ 這是**產品閘**：C2 的 semantic scoring 要吃 "
              f"responsibility-level canonical contract，缺一筆就代表跑出來的不是 target architecture")
        for b in bad[:6]:
            print(f"   · {b}")
        if len(bad) > 6:
            print(f"   · …另有 {len(bad) - 6} 筆")
        return 1
    print(f"（active canonical 閉合 {len(done)}/{len(active)}；"
          f"reviewed_historical ⛔ 不受此閘拘束）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
