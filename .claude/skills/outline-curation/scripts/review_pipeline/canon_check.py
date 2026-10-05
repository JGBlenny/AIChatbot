#!/usr/bin/env python3
"""Plan 9.18 S1: canon block diff (base vs new) restricted to allowed ids + customer-name scan.
  python3 p918_s1_canon_check.py <base canon dir> <new canon dir> <allowed.json> [--remove <removed-ids.json>]"""
import json, re, sys, filecmp, os
argv = sys.argv[1:]
remove = set()
if "--remove" in argv:  # Plan 9.30: fines absent from the new canon are allowed only if listed here
    i = argv.index("--remove"); remove = set(json.load(open(argv[i + 1]))); del argv[i:i + 2]
base, new, allowed = argv[0], argv[1], set(json.load(open(argv[2])))
PAT = re.compile(r"(?<!系)統上|新北住都|樓宇|資育|資聯|泰萬通|Beyond360|beyond360|安歌|喬立|joeRich|nthurc|tongSang|21228|愛租屋")
def blocks(p):
    out, pre = {}, []
    t = open(p, encoding="utf-8").read()
    for b in re.split(r"\n(?=## |### )", t):
        m = re.match(r"### .*\{#(jgb/[^}]+)\}", b)
        if m: out[m.group(1)] = b
        else: pre.append(b)
    return out, pre
errs = []; changed = set()
for s in "ABCDEFGHI":
    (bb, bp), (nb, np_) = blocks(f"{base}/jgb/{s}.md"), blocks(f"{new}/jgb/{s}.md")
    if [k for k in bb if not (k in remove and k not in nb)] != list(nb): errs.append(f"{s}: fine order/membership differs")
    if bp != np_: errs.append(f"{s}: non-fine text differs")
    for k in bb:
        if k in nb and bb[k] != nb[k]: changed.add(k)
out_of_set = sorted(changed - allowed)
if out_of_set: errs.append(f"blocks changed outside allowed set: {out_of_set}")
for rel in ("README.md",):
    if not filecmp.cmp(f"{base}/{rel}", f"{new}/{rel}", shallow=False): errs.append(f"{rel} differs")
ja, jb = json.load(open(f"{base}/jgb.json")), json.load(open(f"{new}/jgb.json"))
fa = {f["id"]: f for c in ja["coarses"] for f in c["fines"]}; fb = {f["id"]: f for c in jb["coarses"] for f in c["fines"]}
jch = sorted(k for k in fa if fa[k] != fb.get(k))
if set(jch) - allowed: errs.append(f"jgb.json fines changed outside allowed: {sorted(set(jch) - allowed)}")
cat_a = open(f"{base}/jgb/CATALOG.md", encoding="utf-8").read().split("\n"); cat_b = open(f"{new}/jgb/CATALOG.md", encoding="utf-8").read().split("\n")
cat_ch = [l for l in set(cat_a) ^ set(cat_b)]
bad_cat = [l for l in cat_ch if not any(l.startswith(i + "｜") for i in allowed)]
if bad_cat: errs.append(f"CATALOG lines changed outside allowed: {bad_cat[:3]}")
hits = []; sysn = 0
for s in "ABCDEFGHI":
    t = open(f"{new}/jgb/{s}.md", encoding="utf-8").read(); sysn += t.count("系統上")
    hits += [(s, m.group(0)) for m in PAT.finditer(t)]
cat_hits = PAT.findall(open(f"{new}/jgb/CATALOG.md", encoding="utf-8").read()) + PAT.findall(json.dumps(jb, ensure_ascii=False))
print(f"[check] blocks changed {len(changed)} (in allowed {len(changed & allowed)}); jgb.json fines changed {len(jch)}; CATALOG lines changed {len(cat_ch)}")
print(f"[check] customer-name hits in .md {len(hits)}, in CATALOG+jgb.json {len(cat_hits)}; 系統上 occurrences {sysn}")
if hits or cat_hits: errs.append(f"customer names remain: {hits[:5]} {cat_hits[:5]}")
print(f"[check] mismatches: {len(errs)}")
for e in errs: print("[check]  ", e)
sys.exit(1 if errs else 0)
