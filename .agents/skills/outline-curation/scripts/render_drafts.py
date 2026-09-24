#!/usr/bin/env python3
"""把 drafts-<架>.json（DSP-067 主題出發起草）轉成人讀 Markdown：粗目 → 細目（標題、講法、句子、來源、待查）。決定性。
用法：python3 render_drafts.py --drafts <drafts-A.json> --out <md>
"""
from __future__ import annotations

import argparse
import json


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drafts", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = json.load(open(a.drafts, encoding="utf-8"))
    n_f = sum(len(c["fines"]) for c in d["coarses"]); n_s = sum(len(f["sentences"]) for c in d["coarses"] for f in c["fines"])
    md = [f"# {d['shelf']} 架草稿（jgb2 master @ {d.get('jgb2_sha', '')[:12]}；粗目 {len(d['coarses'])}、細目 {n_f}、句 {n_s}）", "",
          "讀法：每個粗目底下一條細目答一件事；句子後的〔〕是來源檔（程式或幫助中心頁）；「待查」是文件與程式衝突或程式裡查不到的，未選邊。", ""]
    for c in d["coarses"]:
        md += [f"## {c['coarse']}（{len(c['fines'])} 條；頁：{'、'.join(u.replace('page:', '') for u in c['unit_ids'])}）", ""]
        for f in c["fines"]:
            md += [f"### {f['title']}", f"- 講法：{'／'.join(f.get('phrasings', []))}", f"- 給誰看：{'、'.join(f['target_user'])}"]
            src_of = {}
            for e in f.get("evidence", []):
                src_of.setdefault(e["sentence_index"], e["source"])
            for i, s_ in enumerate(f["sentences"]):
                src = src_of.get(i, "")
                short = src.split("#")[0].replace("code:", "").replace("help:", "幫助中心:")
                md.append(f"- {s_}〔{short}〕")
            for g in f.get("not_supported_greps", []):
                md.append(f"- 否定查證：`{g}`")
            for q in f.get("open_questions", []):
                md.append(f"- ⚠️ 待查：{q}")
            md.append("")
    open(a.out, "w", encoding="utf-8").write("\n".join(md))
    print(f"✅ {a.out}：粗目 {len(d['coarses'])}、細目 {n_f}、句 {n_s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
