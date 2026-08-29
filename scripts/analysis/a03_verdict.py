#!/usr/bin/env python3
"""A03 第【5】–【7】關。判準逐字取自已凍結協議，⛔ 未調整。"""
import json, sys
from collections import Counter

ALLOWED = {"G1":3402,"G2":3406,"G3":3519,"I1":4640,"I2":4656,
           "I3":4657,"I4":3495,"I5":3496,"I6":3498,"I7":3499}
LEVEL_A = set(ALLOWED.values())
SEM_UNITS = ["G1","G2","G3"] + [f"I{i}-explicit" for i in range(1,8)]
ELL_UNITS = [f"I{i}-elliptical" for i in range(1,8)]

res = {r["i"]: r for r in json.load(open("scripts/analysis/a03_result.json",encoding="utf-8"))}
lab = json.load(open("scripts/analysis/a03_labels.json",encoding="utf-8"))
q = {int(k): v for k, v in lab["layer_q"].items()}

# 完整性
errs = [r for r in res.values() if r.get("error")]
print(f"執行完整性：{len(res)}/200｜例外 {len(errs)}")
if len(res)!=200 or errs:
    print("❌ PROCEDURAL_INVALID"); sys.exit(1)

semantic_fail, authority_incon = [], []
print("\n【5】Layer A —— 10 個 semantic evaluation units（>= 80%）")
for u in SEM_UNITS:
    base = ALLOWED[u.split("-")[0]]
    ids = [i for i,r in res.items() if r["unit"]==u and q[i]=="SEMANTICALLY_JUDGEABLE"]
    hit = [i for i in ids if res[i].get("top1_id")==base]
    rate = 100.0*len(hit)/max(len(ids),1)
    ok = rate>=80.0
    if not ok: semantic_fail.append(u)
    print(f"   {u:16s} {len(hit):2d}/{len(ids):2d} = {rate:5.1f}%  (allowed={base}) {'✅' if ok else '❌'}")

print("\n【6】ELLIPTICAL_AUTHORITY_EXERCISE_PRECONDITION —— top1 ∈ Level-A（>= 8/10）")
for u in ELL_UNITS:
    ids = [i for i,r in res.items() if r["unit"]==u]
    hit = [i for i in ids if res[i].get("top1_id") in LEVEL_A]
    ok = len(hit)>=8
    if not ok: authority_incon.append(u)
    print(f"   {u:16s} {len(hit):2d}/{len(ids):2d} {'✅' if ok else '❌'}")

print("\n【7】Layer B —— 所有 top1 ∈ Level-A 的案例（accuracy = 100%）")
cases = [r for r in res.values() if r.get("level_a") and "observed_suppressed" in r]
mism = [r for r in cases if r["observed_suppressed"] != r["expected_suppressed"]]
print(f"   母體 {len(cases)}（general {sum(1 for r in cases if r['expected_suppressed'])}"
      f"／instance {sum(1 for r in cases if not r['expected_suppressed'])}）")
print(f"   不一致 **{len(mism)}**")
for r in mism[:10]:
    print(f"     i={r['i']} unit={r['unit']} top1={r['top1_id']} "
          f"expected_suppress={r['expected_suppressed']} observed={r['observed_suppressed']}")

print("\n" + "="*62)
print(f"A03-LABELS    = PASS（L1 {lab['L1']*100:.1f}%／κ {lab['kappa']:.3f}）")
if semantic_fail:
    print(f"A03-SEMANTIC  = **FAIL ／ RETRIEVAL_SEMANTIC_MISALIGNMENT** {semantic_fail}")
else:
    print("A03-SEMANTIC  = **PASS**")
if authority_incon:
    print(f"A03-AUTHORITY = **INCONCLUSIVE ／ "
          f"ELLIPTICAL_AUTHORITY_NOT_SUFFICIENTLY_EXERCISED** {authority_incon}")
elif mism:
    print("A03-AUTHORITY = **FAIL ／ AUTHORITY_POLICY_FAIL**")
else:
    print("A03-AUTHORITY = **PASS**（conditional on the retrieval interpretation）")
