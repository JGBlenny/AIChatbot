#!/usr/bin/env python3
"""不變量 19：**R10-P3 裁定紀錄的合法性**（業主裁定 2026-08-29）。

源起：R10P-SCHEMA-2 把 applicability 拆成兩軸，正是因為單軸會讓
「還沒 review」被序列化成 `unknown`，把「我們不知道」偷換成「我們知道正確值就是 UNKNOWN」。
⚠️ 業主在 Batch A 又點名第二種偷換：`INSUFFICIENT_EVIDENCE` 不得抹掉已 CONFIRMED 的
IDENTITY／MEMBERSHIP，也不得順手把 applicability 填成 unknown。

## 不變量陳述

> ① 每筆裁定的 candidate_group_id ∈ **frozen proposal**，且不重複。
> ② verdict ∈ schema 凍結的六值集合。
> ③ applicability 落在**四格合法 state space** 之一（兩種 illegal 明文擋掉）。
> ④ `verdict=INSUFFICIENT_EVIDENCE` ⛔ 不得伴隨 `applicability.value=unknown`。
> ⑤ `CONFIRMED_RESPONSIBILITY` 必須**每一項命題各自**有 evidence 支持
>    （identity／membership／applicability／ownership 四類 supports 全到齊）——
>    ⛔ IDENTITY CONFIRMED 不自動推出 applicability／ownership。
> ⑥ 每筆 evidence 的 `supports[]` ⛔ 不得為空（schema「evidence 不得萬用」）。
> ⑦ review_basis_digest 可由紀錄內容**重算**且相符（⛔ 不得謊報看過哪些證據）。

用法：python3 scripts/audit/checks/p3_verdict_legality.py [--self-test]
"""
import copy
import hashlib
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
R10P = os.path.join(REPO, ".kiro", "specs", "conversational-routing-execution", "r10p")
VERDICTS = os.path.join(R10P, "p3-verdicts.json")
PROPOSAL = os.path.join(R10P, "proposal.json")

VERDICTS_ALLOWED = {"CONFIRMED_RESPONSIBILITY", "SPLIT_REQUIRED", "MERGE_WITH_OTHER",
                    "MEMBERSHIP_REJECTED", "INSUFFICIENT_EVIDENCE", "HISTORICAL_ONLY"}
LEGAL_APPL = {("undeclared", None), ("reviewed", "instance"),
              ("reviewed", "general"), ("reviewed", "unknown")}
REQUIRED_SUPPORTS = {"identity", "membership", "applicability", "ownership"}


def load():
    with open(VERDICTS, encoding="utf-8") as f:
        v = json.load(f)
    with open(PROPOSAL, encoding="utf-8") as f:
        p = json.load(f)
    return {"v": v, "group_ids": {c["candidate_group_id"] for c in p["candidates"]}}


def basis_digest(rec):
    payload = {"candidate_group_id": rec["candidate_group_id"],
               "review_input_scope": rec["review_input_scope"],
               "evidence": rec["review_basis_evidence"],
               "absence_observations": rec["absence_observations"]}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def violations(st=None):
    st = load() if st is None else st
    recs = st["v"]["records"]
    bad = []
    seen = set()
    for r in recs:
        cid = r.get("candidate_group_id")
        if cid not in st["group_ids"]:
            bad.append(f"{cid}：⛔ 不在 frozen proposal 的 candidate 集合內")
        if cid in seen:
            bad.append(f"{cid}：同一群被裁定兩次")
        seen.add(cid)

        if r.get("verdict") not in VERDICTS_ALLOWED:
            bad.append(f"{cid}：verdict {r.get('verdict')!r} ⛔ 不在 schema 凍結集合")

        ap = r["propositions"]["III_APPLICABILITY"]
        pair = (ap.get("declaration_status"), ap.get("value"))
        if pair not in LEGAL_APPL:
            bad.append(f"{cid}：applicability {pair} 落在**非法** state space"
                       f"（undeclared 必須 value=null；reviewed 必須 ∈ instance/general/unknown）")
        if r.get("verdict") == "INSUFFICIENT_EVIDENCE" and ap.get("value") == "unknown":
            bad.append(f"{cid}：⛔ INSUFFICIENT_EVIDENCE 伴隨 value=unknown"
                       f"——把「我們不知道」偷換成「已知正確值就是 UNKNOWN」")

        sup = set()
        for e in r.get("review_basis_evidence", []):
            s = e.get("supports") or []
            if not s:
                bad.append(f"{cid}：evidence {e.get('source')!r} 的 supports[] 為空（evidence ⛔ 不得萬用）")
            sup |= set(s)
        if r.get("verdict") == "CONFIRMED_RESPONSIBILITY":
            miss = REQUIRED_SUPPORTS - sup
            # alias_relation 可替 identity 作證（同一 authoring rule）
            if "identity" in miss and "alias_relation" in sup:
                miss.discard("identity")
            if miss:
                bad.append(f"{cid}：CONFIRMED_RESPONSIBILITY 但缺 {sorted(miss)} 的支持證據"
                           f"——⛔ IDENTITY CONFIRMED 不自動推出 applicability／ownership")
            if not (r["propositions"]["IV_OWNERSHIP"].get("owner") or "").strip():
                bad.append(f"{cid}：CONFIRMED_RESPONSIBILITY 卻未寫 owner")

        got = basis_digest(r)
        if got != r.get("review_basis_digest"):
            bad.append(f"{cid}：review_basis_digest 重算不符（{got[:12]}… ≠ "
                       f"{str(r.get('review_basis_digest'))[:12]}…）⇒ 引用的證據集合已變")
    if not recs:
        bad.append("p3-verdicts.json 沒有任何裁定紀錄")
    return bad


def self_test() -> int:
    st = load()
    cases = [("現況乾淨", violations(st) == [])]

    def mut(fn):
        m = copy.deepcopy(st); fn(m["v"]["records"]); return m

    def redigest(r):
        r["review_basis_digest"] = basis_digest(r)

    m = mut(lambda rs: rs[0]["propositions"]["III_APPLICABILITY"].update(
        {"declaration_status": "reviewed", "value": None}))
    cases.append(("reviewed＋null 必須紅", any("非法" in x for x in violations(m))))

    m = mut(lambda rs: rs[0]["propositions"]["III_APPLICABILITY"].update(
        {"declaration_status": "undeclared", "value": "unknown"}))
    cases.append(("undeclared＋unknown 必須紅", any("非法" in x for x in violations(m))))

    def insuf_unknown(rs):
        r = next(x for x in rs if x["verdict"] == "INSUFFICIENT_EVIDENCE")
        r["propositions"]["III_APPLICABILITY"] = {"declaration_status": "reviewed", "value": "unknown"}
    m = mut(insuf_unknown)
    cases.append(("INSUFFICIENT_EVIDENCE＋unknown 必須紅", any("偷換" in x for x in violations(m))))

    def strip_owner_ev(rs):
        r = next(x for x in rs if x["verdict"] == "CONFIRMED_RESPONSIBILITY")
        r["review_basis_evidence"] = [e for e in r["review_basis_evidence"]
                                      if "ownership" not in (e.get("supports") or [])]
        redigest(r)
    m = mut(strip_owner_ev)
    cases.append(("CONFIRMED 但無 ownership 證據必須紅",
                  any("缺 ['ownership']" in x for x in violations(m))))

    def empty_supports(rs):
        rs[0]["review_basis_evidence"][0]["supports"] = []
        redigest(rs[0])
    m = mut(empty_supports)
    cases.append(("空 supports 必須紅", any("supports[] 為空" in x for x in violations(m))))

    m = mut(lambda rs: rs[0]["review_basis_evidence"].append(
        {"evidence_type": "AUTHORING_SPEC", "source": "偷加的證據",
         "claim_supported": "x", "supports": ["identity"], "digest": None}))
    cases.append(("事後偷加證據必須紅（digest 重算不符）",
                  any("重算不符" in x for x in violations(m))))

    m = mut(lambda rs: rs[0].update({"candidate_group_id": "CG-ROW-999999"}))
    cases.append(("裁定不存在的群必須紅",
                  any("不在 frozen proposal" in x for x in violations(m))))

    m = mut(lambda rs: rs[0].update({"verdict": "LOOKS_FINE"}))
    cases.append(("verdict 不在凍結集合必須紅",
                  any("不在 schema 凍結集合" in x for x in violations(m))))

    for n, ok in cases:
        print(f"{'✅' if ok else '❌'} {n}")
    return 1 if any(not ok for _n, ok in cases) else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if not os.path.exists(VERDICTS):
        print("（R10-P3 尚未有裁定紀錄——p3-verdicts.json 不存在；本條不適用）")
        return 0
    bad = violations()
    if bad:
        print("❌ FAIL：R10-P3 裁定紀錄合法性")
        for b in bad:
            print(f"   · {b}")
        return 1
    st = load()
    recs = st["v"]["records"]
    tally = {}
    for r in recs:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    order = ", ".join(f"{k} {v}" for k, v in sorted(tally.items()))
    print(f"（R10-P3 已裁 {len(recs)} 群／批次 {st['v']['batches_reviewed']}：{order}；"
          f"applicability 全數落在四格合法 state space，review_basis_digest 逐筆重算相符）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
