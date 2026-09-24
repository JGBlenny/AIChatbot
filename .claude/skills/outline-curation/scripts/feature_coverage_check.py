#!/usr/bin/env python3
"""步 0b 驗收：分母＝頁面樹基準（`page_surface`，DSP-065；`in_baseline` 為真的格）或功能全表（`feature_surface`，粒度對照）。
`feature-coverage.json` 的每個 unit_id 必須 ⊆ 0a `units[]`，且每個單位恰有一格；每格對每個開放身分（D3：`prospect`／`property_manager`，
租客 DSP-054 未開）各一個判定，verdict 在封閉值域；`fine_ids` 指向存在的細目；sha 與 0a 一致。違反 ⇒ exit 2（⛔ 不靜默）。
也印每身分統計給審核單。

用法：python3 feature_coverage_check.py --surface <feature-surface.json> --coverage <feature-coverage.json>
"""
import argparse, json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _envelope import SchemaError, validate_file  # noqa: E402

VERDICTS = ("covered", "partial", "missing", "tenant_not_open", "internal", "out_of_scope")
IDENTITIES = ("prospect", "property_manager")  # 開放中的身分（D3；租客 DSP-054 未開、system_admin 折成業者 DSP-053a）
SKIP = ("tenant_not_open", "out_of_scope", "internal")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--surface", required=True)
    ap.add_argument("--coverage", required=True)
    ap.add_argument("--denominator", default=None,
                    help="計入缺口的單位種類（預設 action,help；route 只當證據／候選，⛔ 不自動算缺口）")
    a = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    surf0 = json.load(open(a.surface, encoding="utf-8"))
    step = surf0.get("step")
    if step not in ("page_surface", "feature_surface"):
        print("❌ surface 的 step 不是 page_surface／feature_surface"); return 2
    try:
        validate_file(a.surface, os.path.join(here, "..", "schemas", f"{step.replace('_', '-')}.json"))
        validate_file(a.coverage, os.path.join(here, "..", "schemas", "feature-coverage.json"))
    except SchemaError as e:
        print(f"❌ schema 不符：{e}"); return 2
    surf = json.load(open(a.surface, encoding="utf-8"))
    cov = json.load(open(a.coverage, encoding="utf-8"))
    units = {u["unit_id"]: u for u in surf["payload"]["units"]}
    fails = []
    if surf.get("deterministic") is not True:
        fails.append("0a 產物 deterministic 不對（schema 驗證器不支援 const，這裡手動釘）")
    if cov["surface_jgb2_sha"] != surf["payload"]["sources"]["jgb2_sha"]:
        fails.append("0b 的 surface_jgb2_sha 與 0a 不同——判定算在別的產品版本上")
    ids = [c["unit_id"] for c in cov["cells"]]
    extra = sorted(set(ids) - set(units))
    missing = sorted(set(units) - set(ids))
    dup = sorted(k for k, n in Counter(ids).items() if n > 1)
    if extra: fails.append(f"0b 新增了 0a 沒有的單位（⛔ 不得增刪合併）：{extra[:5]}… 共 {len(extra)}")
    if missing: fails.append(f"0b 漏判 {len(missing)} 個單位：{missing[:5]}…")
    if dup: fails.append(f"單位重複判定：{dup[:5]}")
    noid = [c["unit_id"] for c in cov["cells"] if set(c.get("by_identity", {})) != set(IDENTITIES)]
    if noid: fails.append(f"格缺身分判定（每格須恰有 {IDENTITIES}）：{noid[:5]}… 共 {len(noid)}")
    bad = [f"{c['unit_id']}[{i}]" for c in cov["cells"] for i, j in c.get("by_identity", {}).items() if j.get("verdict") not in VERDICTS]
    if bad: fails.append(f"verdict 不在值域：{bad[:5]}")
    fine_ids = {c["id"] for c in surf["payload"]["canon_titles"]}
    unknown = sorted({f for c in cov["cells"] for j in c.get("by_identity", {}).values() for f in j.get("fine_ids", []) if f not in fine_ids})
    if unknown: fails.append(f"fine_ids 指向不存在的細目：{unknown[:5]}")
    nofine = [f"{c['unit_id']}[{i}]" for c in cov["cells"] for i, j in c.get("by_identity", {}).items() if j.get("verdict") in ("covered", "partial") and not j.get("fine_ids")]
    if nofine: fails.append(f"covered／partial 必須列 fine_ids：{nofine[:5]}… 共 {len(nofine)}")
    for f in fails:
        print("❌", f)
    if fails:
        return 2
    denominator = a.denominator or ("spa,blade" if step == "page_surface" else "action,help")
    denom_kinds = set(denominator.split(","))
    base = [c for c in cov["cells"] if units[c["unit_id"]]["kind"] in denom_kinds and units[c["unit_id"]].get("in_baseline", True)]
    print(f"✅ 0b 驗收通過（共 {len(ids)} 單位＝0a units；每格 {len(IDENTITIES)} 身分）")
    for ident in IDENTITIES:
        denom = [c for c in base if c["by_identity"][ident]["verdict"] not in SKIP]
        n = Counter(c["by_identity"][ident]["verdict"] for c in denom)
        print(f"{ident} 分母（{denominator}，扣 tenant／out_of_scope／internal）：{len(denom)}＝"
              + "、".join(f"{k} {n.get(k, 0)}" for k in ("covered", "partial", "missing")))
    other = Counter(j["verdict"] for c in cov["cells"] if c not in base for j in c["by_identity"].values())
    print("不入分母的判定（證據／候選，不計缺口）：" + ("、".join(f"{k} {v}" for k, v in sorted(other.items())) or "無"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
