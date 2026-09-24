#!/usr/bin/env python3
"""九架起草總表：各架 粗目／細目／句 數與所有 open_questions（業主待裁清單）。決定性。
用法：python3 outline_summary.py --run <runs/outline-YYYYMMDD> --out <md>
"""
from __future__ import annotations

import argparse
import glob
import json
import os

NAMES = {"A": "帳號與身分", "B": "團隊、人員與大房東", "C": "社區與物件", "D": "租約", "E": "帳務", "F": "修繕", "G": "裝置", "H": "幫助中心", "I": "方案與導入"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows, oqs, tot = [], [], [0, 0, 0, 0]
    for shelf in "ABCDEFGHI":
        p = os.path.join(a.run, f"drafts-{shelf}.json")
        if not os.path.exists(p):
            rows.append(f"| {shelf} {NAMES[shelf]} | — | — | — | — | 未完成 |"); continue
        d = json.load(open(p, encoding="utf-8"))
        nc = len(d["coarses"]); nf = sum(len(c["fines"]) for c in d["coarses"]); ns = sum(len(f["sentences"]) for c in d["coarses"] for f in c["fines"])
        qs = [(f["proposed_id"], q) for c in d["coarses"] for f in c["fines"] for q in f.get("open_questions", [])]
        rows.append(f"| {shelf} {NAMES[shelf]} | {nc} | {nf} | {ns} | {len(qs)} | {d.get('jgb2_sha', '')[:12]} |")
        oqs += [(shelf, fid, q) for fid, q in qs]
        for i, v in enumerate((nc, nf, ns, len(qs))): tot[i] += v
    md = ["# 九架起草總表（DSP-067，主題出發、每句對源）", "", "| 架 | 粗目 | 細目 | 句 | 待裁 | jgb2 |", "|---|---|---|---|---|---|", *rows,
          f"| **合計** | {tot[0]} | {tot[1]} | {tot[2]} | {tot[3]} | |", "",
          "## 待裁清單（open_questions：文件與程式衝突、程式缺陷、查不到來源，⛔ 未選邊）", ""]
    cur = None
    for shelf, fid, q in oqs:
        if shelf != cur:
            md.append(f"### {shelf} {NAMES[shelf]}"); cur = shelf
        md.append(f"- `{fid.split('/', 1)[1]}`：{q}")
    open(a.out, "w", encoding="utf-8").write("\n".join(md))
    print(f"✅ {a.out}：粗目 {tot[0]}、細目 {tot[1]}、句 {tot[2]}、待裁 {tot[3]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
