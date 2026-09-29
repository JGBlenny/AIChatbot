#!/usr/bin/env python3
"""grep-check (path, literal) pairs in the pinned jgb2 export; prints count per pair. Usage: p919_grepcheck.py < pairs.tsv"""
import os, sys
X = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jgb2-b2ee2ac")
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line or line.startswith("#"): continue
    path, pat = line.split("\t", 1)
    p = os.path.join(X, path); n = 0
    if os.path.isdir(p):
        for r, _, fs in os.walk(p):
            for f in fs:
                try: n += open(os.path.join(r, f), encoding="utf-8", errors="ignore").read().count(pat)
                except Exception: pass
    elif os.path.exists(p): n = open(p, encoding="utf-8", errors="ignore").read().count(pat)
    else: n = -1
    print(f"{n:>3} | {path} | {pat}")
