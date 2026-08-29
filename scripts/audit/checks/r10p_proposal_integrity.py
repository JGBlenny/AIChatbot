#!/usr/bin/env python3
"""不變量 18：**R10-P2 proposal 的分割身分與 authority 邊界**（業主裁定 2026-08-29）。

源起：不變量 17 擋的是「母體少列而不報錯」；proposal 有**第二種**同形失效——
54 列被分群後，某列**被漏掉**或**同時出現在兩群**，總數看起來仍然合理。
⚠️ 只比 `sum(len(members)) == 54` 不夠：「漏一列、另一列重複」會假綠。

## 不變量陳述

> ① proposed_members 是凍結 54-row 母體的**嚴格分割**（聯集相符、兩兩不相交、無重複）。
> ② proposal.json bytes 的 sha256 == 凍結 PROPOSAL_DIGEST。
> ③ proposal ⛔ 不得帶任何 authority 欄位（schema `proposal_record._forbidden`）。
> ④ 每個 grouping reason ∈ 凍結允許規則 ∪ {SINGLETON_NO_ALLOWED_RULE_APPLIES}。
> ⑤ 每個 **多列** group 必須來自 entry-alias registry，且成員與 registry **逐一相符**
>    ——這是唯一在本母體上產生合併的允許規則；⛔ 任何其他來源的合併都是偷渡 authority。

用法：python3 scripts/audit/checks/r10p_proposal_integrity.py [--self-test]
"""
import copy
import hashlib
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SPEC = os.path.join(REPO, ".kiro", "specs", "conversational-routing-execution")
R10P = os.path.join(SPEC, "r10p")
PROPOSAL = os.path.join(R10P, "proposal.json")
REGISTRY = os.path.join(SPEC, "entry-alias-registry.json")
EXPECTED_ROWS = 54

ALLOWED_RULES = {
    "same explicit entry-alias registry responsibility",
    "same existing reviewed owner contract",
    "same deterministic mapping（同一 capability 函式）",
    "SINGLETON_NO_ALLOWED_RULE_APPLIES",
}
ALIAS_RULE = "same explicit entry-alias registry responsibility"
#: schema proposal_record._forbidden 的欄位名（authority 一律不得出現在 proposal 的 candidate 內）
FORBIDDEN_KEYS = {"responsibility_id", "applicability", "review_status", "review",
                  "canonical_responsibility", "declaration_status", "status"}


def load():
    with open(os.path.join(R10P, "digests.txt"), encoding="utf-8") as f:
        txt = f.read()
    def g(k):
        m = re.search(rf"^{k}=(\S+)$", txt, re.M)
        return m.group(1) if m else None
    with open(os.path.join(R10P, "population.txt"), encoding="utf-8") as f:
        ids = [int(l.split("|", 1)[0]) for l in f.read().splitlines() if l.strip()]
    with open(PROPOSAL, "rb") as f:
        raw = f.read()
    with open(REGISTRY, encoding="utf-8") as f:
        reg = json.load(f)
    return {"frozen_ids": ids, "raw": raw, "doc": json.loads(raw.decode("utf-8")),
            "reg": reg, "proposal_digest": g("PROPOSAL_DIGEST"),
            "schema_digest": g("SCHEMA_DIGEST"), "population_digest": g("POPULATION_DIGEST")}


def _forbidden_hits(node, path="candidates"):
    hits = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k in FORBIDDEN_KEYS:
                hits.append(f"{path}.{k}")
            hits += _forbidden_hits(v, f"{path}.{k}")
    elif isinstance(node, list):
        for n, v in enumerate(node):
            hits += _forbidden_hits(v, f"{path}[{n}]")
    return hits


def violations(st=None, raw_override=None):
    st = load() if st is None else st
    doc, frozen = st["doc"], st["frozen_ids"]
    bad = []

    # ② bytes 身分
    raw = st["raw"] if raw_override is None else raw_override
    got = hashlib.sha256(raw).hexdigest()
    frozen_dg = st["proposal_digest"]
    # ⚠️ 大聲失敗：proposal.json 已存在卻沒有凍結 digest ⇒ ⛔ 不得靜默跳過 bytes 檢查
    if not frozen_dg or frozen_dg.startswith("（"):
        bad.append("proposal.json 已存在，但 digests.txt 的 PROPOSAL_DIGEST 仍是佔位字串"
                   "——⛔ 未凍結的 proposal 不得被當成已凍結")
    elif got != frozen_dg:
        bad.append(f"proposal.json bytes 已變（{got[:12]}… ≠ 凍結 {frozen_dg[:12]}…）")
    # 判準／母體同一版
    if doc.get("schema_digest") != st["schema_digest"]:
        bad.append("proposal 引用的 SCHEMA_DIGEST 與凍結值不符 ⇒ 判準不同版")
    if doc.get("population_digest") != st["population_digest"]:
        bad.append("proposal 引用的 POPULATION_DIGEST 與凍結值不符 ⇒ 母體不同批")

    # ① 嚴格分割
    members = [i for c in doc.get("candidates", []) for i in c.get("proposed_members", [])]
    dup = sorted({i for i in members if members.count(i) > 1})
    if dup:
        bad.append(f"同一 id 出現在多個 candidate group：{dup}——⚠️ 分割不成立")
    missing = sorted(set(frozen) - set(members))
    extra = sorted(set(members) - set(frozen))
    if missing:
        bad.append(f"母體中的 id 未被任何 candidate group 涵蓋：{missing}——⚠️ 這正是漏列的形狀")
    if extra:
        bad.append(f"proposal 出現母體外的 id：{extra}")
    if len(members) != EXPECTED_ROWS or len(set(members)) != EXPECTED_ROWS:
        bad.append(f"members 總數 {len(members)}／distinct {len(set(members))}（皆應為 {EXPECTED_ROWS}）")
    if not doc.get("candidates"):
        bad.append("proposal 沒有任何 candidate group")

    # ③ authority 邊界
    hits = _forbidden_hits(doc.get("candidates", []))
    if hits:
        bad.append(f"proposal 帶了 authority 欄位（schema _forbidden）：{sorted(set(hits))}")

    # ④／⑤ 規則合法性
    reg_groups = {tuple(sorted(m["id"] for m in v)) for v in st["reg"]["facets"].values()}
    for c in doc.get("candidates", []):
        cid, ms = c.get("candidate_group_id"), sorted(c.get("proposed_members", []))
        rule = c.get("mechanical_grouping_reason")
        if rule not in ALLOWED_RULES:
            bad.append(f"{cid}：grouping reason ⛔ 不在凍結允許集合：{rule!r}")
        if len(ms) > 1:
            if rule != ALIAS_RULE:
                bad.append(f"{cid}：多列合併卻非 entry-alias registry 規則（{rule!r}）⇒ 偷渡 authority")
            elif tuple(ms) not in reg_groups:
                bad.append(f"{cid}：宣稱依 registry 合併，但成員 {ms} 與 registry 任一 facet 皆不相符")
    return bad


def self_test() -> int:
    st = load()
    cases = [("現況乾淨", violations(st) == [])]

    def mutate(fn):
        m = copy.deepcopy(st); fn(m); return m

    # 正對照：漏一列
    m = mutate(lambda d: d["doc"]["candidates"].pop())
    cases.append(("漏一列必須紅", any("未被任何 candidate group 涵蓋" in x for x in violations(m, m["raw"]))))
    # 正對照：漏一列＋另一列重複（總數仍 54 ⇒ 只比總數會假綠）
    def swap(d):
        cands = d["doc"]["candidates"]
        victim = next(c for c in cands if len(c["proposed_members"]) == 1)
        keep = next(c for c in cands if c is not victim and len(c["proposed_members"]) == 1)
        victim["proposed_members"] = list(keep["proposed_members"])
    m = mutate(swap)
    mem = [i for c in m["doc"]["candidates"] for i in c["proposed_members"]]
    cases.append(("漏一列＋重複一列（總數仍 54）必須紅",
                  len(mem) == EXPECTED_ROWS and violations(m, m["raw"]) != []))
    # 正對照：偷渡 authority 欄位
    m = mutate(lambda d: d["doc"]["candidates"][0].update({"responsibility_id": "late_fee_instance"}))
    cases.append(("proposal 帶 authority 欄位必須紅",
                  any("authority 欄位" in x for x in violations(m, m["raw"]))))
    # 正對照：用禁用規則合併（同 facet／相似 summary）
    def merge(d):
        cands = d["doc"]["candidates"]
        a = next(c for c in cands if len(c["proposed_members"]) == 1)
        b = next(c for c in cands if c is not a and len(c["proposed_members"]) == 1)
        a["proposed_members"] = sorted(a["proposed_members"] + b["proposed_members"])
        a["mechanical_grouping_reason"] = "summary 看起來很像"
        cands.remove(b)
    m = mutate(merge)
    v = violations(m, m["raw"])
    cases.append(("用禁用規則合併必須紅",
                  any("不在凍結允許集合" in x for x in v) and any("偷渡 authority" in x for x in v)))
    # 正對照：宣稱 registry 合併但成員對不上
    def fake(d):
        c = next(x for x in d["doc"]["candidates"] if len(x["proposed_members"]) > 1)
        c["proposed_members"] = sorted(c["proposed_members"][:-1] + [3361])
    m = mutate(fake)
    cases.append(("假冒 registry 合併必須紅",
                  any("與 registry 任一 facet 皆不相符" in x for x in violations(m, m["raw"]))))
    # 正對照：bytes 被改
    cases.append(("bytes 被改必須紅",
                  any("bytes 已變" in x for x in violations(st, st["raw"] + b" "))))
    # 正對照：判準換版
    m = mutate(lambda d: d["doc"].update({"schema_digest": "deadbeef"}))
    cases.append(("判準換版必須紅", any("判準不同版" in x for x in violations(m, m["raw"]))))

    for n, ok in cases:
        print(f"{'✅' if ok else '❌'} {n}")
    return 1 if any(not ok for _n, ok in cases) else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    try:
        bad = violations()
    except FileNotFoundError as e:
        print(f"❌ FAIL：R10-P2 proposal 前置檔缺失（{e}）")
        return 1
    if bad:
        print("❌ FAIL：R10-P2 proposal 完整性")
        for b in bad:
            print(f"   · {b}")
        return 1
    doc = load()["doc"]
    s = doc["summary"]
    print(f"（R10-P2 proposal：{s['candidate_groups']} 個 candidate group ＝ "
          f"{s['multi_row_groups']} 多列群 ＋ {s['singletons']} singleton；"
          f"54 列嚴格分割、無 authority 欄位、合併僅來自 entry-alias registry）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
