#!/usr/bin/env python3
"""步 0b 人讀報告：按架×身分列 covered／partial／missing 計數，並逐格列 partial／missing 的 note（審核單用）。決定性。
用法：python3 page_coverage_report.py --surface <page-surface.json> --coverage <feature-coverage.json> --out <coverage-report.md>
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict

IDENTITIES = ("prospect", "property_manager")
LABEL = {"prospect": "售前 prospect", "property_manager": "業者 property_manager"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--surface", required=True)
    ap.add_argument("--coverage", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    surf = json.load(open(a.surface, encoding="utf-8"))
    cov = json.load(open(a.coverage, encoding="utf-8"))
    units = {u["unit_id"]: u for u in surf["payload"]["units"]}
    base = [c for c in cov["cells"] if units[c["unit_id"]]["in_baseline"]]
    by_shelf: dict[str, list[dict]] = defaultdict(list)
    for c in base:
        by_shelf[units[c["unit_id"]]["shelf"]].append(c)
    md = [f"# 步 0b 覆蓋報告：頁面樹基準 {len(base)} 格 × 兩身分（jgb2 master @ {cov['surface_jgb2_sha'][:12]}）", "", "⚠️ covered＝有細目提到這頁，⛔ 不代表細目內容符合 JGB 現況；既有細目來自舊 kb 改寫，逐句對源另出。", ""]
    md += ["## 總表", "", "| 架 | 格 | " + " | ".join(f"{LABEL[i]} covered／partial／missing" for i in IDENTITIES) + " |", "|---|---|" + "---|" * len(IDENTITIES)]
    tot = {i: Counter() for i in IDENTITIES}
    for shelf in sorted(by_shelf):
        cells = by_shelf[shelf]
        row = [shelf, str(len(cells))]
        for i in IDENTITIES:
            n = Counter(c["by_identity"][i]["verdict"] for c in cells)
            tot[i].update(n)
            row.append(f"{n.get('covered', 0)}／{n.get('partial', 0)}／{n.get('missing', 0)}")
        md.append("| " + " | ".join(row) + " |")
    md.append("| **合計** | " + str(len(base)) + " | " + " | ".join(f"**{tot[i].get('covered', 0)}／{tot[i].get('partial', 0)}／{tot[i].get('missing', 0)}**" for i in IDENTITIES) + " |")
    md.append("")
    for shelf in sorted(by_shelf):
        md += [f"## {shelf}（{len(by_shelf[shelf])} 格）", "", "| 格 | 路徑 | " + " | ".join(LABEL[i] for i in IDENTITIES) + " |", "|---|---|" + "---|" * len(IDENTITIES)]
        for c in sorted(by_shelf[shelf], key=lambda c: c["unit_id"]):
            u = units[c["unit_id"]]
            cols = []
            for i in IDENTITIES:
                j = c["by_identity"][i]
                ids = "、".join(f"`{f.split('/', 1)[1]}`" for f in j["fine_ids"]) if j["fine_ids"] else ""
                cols.append(f"**{j['verdict']}** {ids}" + (f"｜{j['note']}" if j["note"] else ""))
            md.append(f"| `{u['label']}` | `{u['path']}` | " + " | ".join(cols) + " |")
        md.append("")
    open(a.out, "w", encoding="utf-8").write("\n".join(md))
    print(f"✅ 覆蓋報告 → {a.out}；" + "；".join(f"{LABEL[i]} covered {tot[i].get('covered', 0)}／partial {tot[i].get('partial', 0)}／missing {tot[i].get('missing', 0)}" for i in IDENTITIES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
