#!/usr/bin/env python3
"""大綱缺口圖（人讀）：按九架列「已有細目／缺的主題（要新寫）／相近未答（要補一段）」。決定性。
- 已有：正本各架細目標題（`canon/jgb/CATALOG.md`）。
- 缺／相近：步 0b 判定（`feature-coverage.json`，取業者 property_manager 的判定當主題判定；身分是細目屬性不是缺口）。
- 頁面路由名不當標題：主題名取 0b note 的白話描述；同一 note 前綴相同的頁面合併成一個主題並列出對應頁。
用法：python3 outline_gap_map.py --surface <page-surface.json> --coverage <feature-coverage.json> --catalog <CATALOG.md> --out <md>
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict

SHELF_NAMES = {"A": "帳號與身分", "B": "團隊、人員與大房東", "C": "社區與物件", "D": "租約", "E": "帳務", "F": "修繕", "G": "裝置", "H": "幫助中心", "I": "方案與導入"}
TOPIC_ID = "property_manager"  # 主題判定取業者身分（產品的主要使用者）；售前只作細目屬性


def catalog_titles(path: str) -> dict[str, list[tuple[str, str, str]]]:
    out: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^(jgb/([A-I])/[a-z0-9-]+)｜([^｜]+)｜target_user=([^｜]+)", line)
        if m:
            out[m.group(2)].append((m.group(1), m.group(3), m.group(4)))
    if not out:
        raise SystemExit("❌ CATALOG.md 解析到 0 條細目——格式變了")
    return out


def topic_name(note: str) -> str:
    """把 0b note 轉成主題名：去掉「缺／需要一條細目說明／的說明」等外殼，保留白話主體。"""
    t = note.strip()
    t = re.sub(r"^(缺：?|需要一條細目說明|沒有描述|無對應細目[:：]?)", "", t)
    t = re.sub(r"(的說明|的填寫方式|的填寫規則|無對應細目|，無對應說明|功能的說明|對應的內容|的對應內容)$", "", t)
    return t.strip("，。 ") or note


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--surface", required=True)
    ap.add_argument("--coverage", required=True)
    ap.add_argument("--catalog", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    units = {u["unit_id"]: u for u in json.load(open(a.surface, encoding="utf-8"))["payload"]["units"]}
    cov = json.load(open(a.coverage, encoding="utf-8"))
    cat = catalog_titles(a.catalog)
    by_shelf: dict[str, dict[str, list]] = {s: {"missing": [], "partial": [], "covered": []} for s in SHELF_NAMES}
    for c in cov["cells"]:
        u = units[c["unit_id"]]
        if not u["in_baseline"]:
            continue
        j = c["by_identity"][TOPIC_ID]
        p = c["by_identity"]["prospect"]
        by_shelf[u["shelf"]][j["verdict"]].append((u, j, p))
    md = ["# 大綱缺口圖（九架；主題判定取業者身分；售前＝細目屬性；⚠️ 「有細目」≠「答對」——既有細目來自舊 kb 改寫，尚未逐句對源，對源盤查另出）", "",
          "讀法：每架先列**已有細目**（標題＋目前標給誰），再列**缺的主題**（沒有任何細目，要新寫）與**相近未答**（有細目但沒碰到這頁，要補一段）。「已有細目」只表示存在，內容是否符合 JGB 現況要看對源盤查（`canon-source-audit-*.md`）。主題名是白話，對應頁在括號裡。", ""]
    tot = {"have": 0, "missing": 0, "partial": 0}
    for s, name in SHELF_NAMES.items():
        have = cat.get(s, [])
        miss = by_shelf[s]["missing"]; part = by_shelf[s]["partial"]; cov_ok = by_shelf[s]["covered"]
        # 同主題合併（note 主體相同）
        groups: dict[str, list] = defaultdict(list)
        for u, j, p in miss:
            groups[topic_name(j["note"])].append(u)
        tot["have"] += len(have); tot["missing"] += len(groups); tot["partial"] += len(part)
        md += [f"## {s} {name}（已有 {len(have)} 條｜缺 {len(groups)} 個主題｜相近未答 {len(part)} 頁｜有細目未對源 {len(cov_ok)} 頁）", ""]
        md += ["**已有細目**", ""]
        for fid, title, tu in have:
            md.append(f"- {title}（`{fid.split('/', 1)[1]}`；{tu}）")
        md.append("")
        if groups:
            md += ["**缺的主題（要新寫細目）**", "", "| 主題 | 對應頁 | 細目要說什麼 |", "|---|---|---|"]
            for tname, us in groups.items():
                pages = "、".join(f"`{u['label']}`" for u in us)
                note = next(j["note"] for u2, j, _ in miss if u2["unit_id"] == us[0]["unit_id"])
                md.append(f"| {tname} | {pages} | {note} |")
            md.append("")
        if part:
            md += ["**相近未答（要在既有細目補一段）**", "", "| 頁 | 既有細目 | 缺什麼 |", "|---|---|---|"]
            for u, j, p in part:
                md.append(f"| `{u['label']}` | " + "、".join(f"`{f.split('/', 1)[1]}`" for f in j["fine_ids"]) + f" | {j['note']} |")
            md.append("")
        # 屬性缺：主題已有細目但沒標售前
        attr = [(u, j, p) for u, j, p in cov_ok if p["verdict"] != "covered"]
        if attr:
            md += [f"**細目屬性：有細目但未標給售前（{len(attr)} 頁，審核時決定要不要標）**", ""]
            md.append("、".join(f"`{u['label']}`" for u, _, _ in attr))
            md.append("")
    md.insert(2, f"合計：已有細目 {tot['have']} 條；缺 {tot['missing']} 個主題要新寫；相近未答 {tot['partial']} 頁要補段。")
    open(a.out, "w", encoding="utf-8").write("\n".join(md))
    print(f"✅ 大綱缺口圖 → {a.out}；已有 {tot['have']}、缺主題 {tot['missing']}、相近未答 {tot['partial']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
