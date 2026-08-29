#!/usr/bin/env python3
"""不變量 20：**R10-P4 registry 投影完整性**（業主裁定 2026-08-29）。

源起：P4 最容易犯的錯，是為了讓資料模型「每列剛好一個 responsibility」而**製造 authority**——
把 SPLIT 的來源列硬塞成第五個責任、或替 10 個 INSUFFICIENT_EVIDENCE 群捏一個 responsibility_id。
⚠️ 業主凍結的規則是：**P4 必須做到 row disposition 完整，⛔ 不是強迫 responsibility assignment 完整。**

## 不變量陳述

> ① registry.json／p4-projection.json 的 bytes == 凍結 REGISTRY_DIGEST／PROJECTION_DIGEST。
> ② row disposition 是 54-row 母體的**窮盡分割**：每列剛好一類，四類計數合計 54。
> ③ SPLIT_REQUIRED 的來源列：⛔ 不得有自己的 responsibility record；必須**恰好**映到凍結的
>    split_across targets；每個 target 必須 reviewed_active；來源列必須出現在**每一個** target 的
>    members；且貢獻 **0** 個新 responsibility identity。
> ④ MERGE_WITH_OTHER 的群：⛔ 不得有自己的 record；其列必須出現在 target 的 members。
> ⑤ INSUFFICIENT_EVIDENCE 的列：⛔ 不得出現在任何 responsibility 的 members，且必須落 D 類。
> ⑥ HISTORICAL_ONLY → status=reviewed_historical，⛔ 不計入 active census。
> ⑦ canonical_responsibility 與 PENDING_OWNER_STATEMENT 必須一致
>    ——⛔ 機器不得代填（schema：canonical ⛔ 不得由機器自動產生後直接生效）。

用法：python3 scripts/audit/checks/p4_projection_integrity.py [--self-test]
"""
import copy
import hashlib
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
R10P = os.path.join(REPO, ".kiro", "specs", "conversational-routing-execution", "r10p")
CLASSES = {"A_MEMBER_OF_ONE_REVIEWED_RESPONSIBILITY",
           "B_MEMBER_OF_MULTIPLE_REVIEWED_RESPONSIBILITIES",
           "C_HISTORICAL_ONLY_MEMBER",
           "D_UNRESOLVED_NO_AUTHORITATIVE_MEMBERSHIP"}
EXPECTED_ROWS = 54


def load():
    with open(os.path.join(R10P, "digests.txt"), encoding="utf-8") as f:
        txt = f.read()
    def g(k):
        m = re.search(rf"^{k}=(\S+)$", txt, re.M)
        return m.group(1) if m else None
    with open(os.path.join(R10P, "registry.json"), "rb") as f:
        rraw = f.read()
    with open(os.path.join(R10P, "p4-projection.json"), "rb") as f:
        praw = f.read()
    with open(os.path.join(R10P, "p3-verdicts.json"), encoding="utf-8") as f:
        v = json.load(f)
    ids = [int(l.split("|", 1)[0]) for l in
           open(os.path.join(R10P, "population.txt"), encoding="utf-8").read().splitlines() if l.strip()]
    cur = {}
    for r in v["records"]:
        cid = r["candidate_group_id"]
        if cid not in cur or r.get("epoch", 1) > cur[cid].get("epoch", 1):
            cur[cid] = r
    return {"reg": json.loads(rraw), "proj": json.loads(praw), "rraw": rraw, "praw": praw,
            "cur": cur, "frozen_ids": ids,
            "reg_digest": g("REGISTRY_DIGEST"), "proj_digest": g("PROJECTION_DIGEST")}


def violations(st=None, check_bytes=True):
    st = load() if st is None else st
    reg, proj, cur = st["reg"], st["proj"], st["cur"]
    bad = []
    if check_bytes:
        for name, raw, frozen in (("registry.json", st["rraw"], st["reg_digest"]),
                                  ("p4-projection.json", st["praw"], st["proj_digest"])):
            if not frozen or frozen.startswith("（"):
                bad.append(f"{name} 已存在但 digests.txt 未凍結其 digest——⛔ 不得靜默跳過")
            elif hashlib.sha256(raw).hexdigest() != frozen:
                bad.append(f"{name} bytes 已變（≠ 凍結 {frozen[:12]}…）")

    recs = reg["responsibilities"]
    by_group = {r["sealed_from_candidate_group"]: r for r in recs}
    members = {}
    for r in recs:
        for m in r["members"]:
            members.setdefault(m["row_id"], []).append(r["responsibility_id"])

    # ⑦ canonical 一致性
    for r in recs:
        pend = r["canonical_responsibility_status"] == "PENDING_OWNER_STATEMENT"
        if pend and r["canonical_responsibility"]:
            bad.append(f"{r['responsibility_id']}：標 PENDING 卻已有 canonical_responsibility"
                       f"——⛔ 機器不得代填")
        if not pend and not r["canonical_responsibility"]:
            bad.append(f"{r['responsibility_id']}：標 OWNER_STATED 卻沒有 canonical_responsibility")

    # ③④⑤⑥ 逐 verdict 檢查
    for cid, v in cur.items():
        verdict = v["verdict"]
        if verdict in ("CONFIRMED_RESPONSIBILITY", "HISTORICAL_ONLY"):
            r = by_group.get(cid)
            if r is None:
                bad.append(f"{cid}（{verdict}）沒有對應的 responsibility record")
                continue
            want = "reviewed_active" if verdict == "CONFIRMED_RESPONSIBILITY" else "reviewed_historical"
            if r["status"] != want:
                bad.append(f"{r['responsibility_id']}（{cid}）status={r['status']}，應為 {want}")
        elif cid in by_group:
            bad.append(f"{cid}（{verdict}）⛔ 不得擁有自己的 responsibility record"
                       f"（{by_group[cid]['responsibility_id']}）——那是**製造 authority**")

        if verdict == "SPLIT_REQUIRED":
            src = v["members"][0]
            got = set(members.get(src, []))
            want_ids = set()
            for t in v["split_across"]:
                tr = by_group.get(t)
                if tr is None:
                    bad.append(f"{cid}：split target {t} 沒有 responsibility record")
                    continue
                if tr["status"] != "reviewed_active":
                    bad.append(f"{cid}：split target {t} 不是 reviewed_active")
                want_ids.add(tr["responsibility_id"])
                if src not in [m["row_id"] for m in tr["members"]]:
                    bad.append(f"{cid}：來源列 {src} **未出現**在 target {t} 的 members——⛔ 漏掛")
            extra = got - want_ids
            if extra:
                bad.append(f"{cid}：來源列 {src} 掛到 split_across 之外的責任 {sorted(extra)}")
            for m in [m for r in recs for m in r["members"] if m["row_id"] == src]:
                if m.get("_membership_origin") != "SPLIT_REQUIRED":
                    bad.append(f"{cid}：來源列 {src} 的 membership_origin 未標 SPLIT_REQUIRED")

        if verdict == "MERGE_WITH_OTHER":
            tgt = by_group.get(v["merge_target"])
            if tgt is None:
                bad.append(f"{cid}：merge target {v['merge_target']} 沒有 responsibility record")
            else:
                for i in v["members"]:
                    if i not in [m["row_id"] for m in tgt["members"]]:
                        bad.append(f"{cid}：merge 來源列 {i} 未出現在 target 的 members")

        if verdict == "INSUFFICIENT_EVIDENCE":
            for i in v["members"]:
                if i in members:
                    bad.append(f"{cid}：未解列 {i} 竟出現在 responsibility {members[i]} 的 members"
                               f"——⛔ 為了湊滿 54/54 而製造 authority")

    # ② 窮盡分割
    part = proj["_row_disposition_partition"]
    by_row = {int(k): v for k, v in part["by_row"].items()}
    if set(by_row) != set(st["frozen_ids"]):
        bad.append("row disposition 未涵蓋 frozen 母體（或多出母體外的列）")
    bad_cls = {k: v for k, v in by_row.items() if v not in CLASSES}
    if bad_cls:
        bad.append(f"disposition 類別非法：{bad_cls}")
    if sum(part["tally"].values()) != EXPECTED_ROWS:
        bad.append(f"disposition tally 合計 {sum(part['tally'].values())} ≠ {EXPECTED_ROWS}")
    recount = {}
    for v in by_row.values():
        recount[v] = recount.get(v, 0) + 1
    if recount != part["tally"]:
        bad.append(f"disposition tally 與逐列結果不符：{part['tally']} vs {recount}")
    # 交叉核對：分類必須與 members 實況一致
    for i in st["frozen_ids"]:
        rs = members.get(i, [])
        st_list = [r["status"] for r in recs if r["responsibility_id"] in rs]
        if not rs:
            want = "D_UNRESOLVED_NO_AUTHORITATIVE_MEMBERSHIP"
        elif len(rs) > 1:
            want = "B_MEMBER_OF_MULTIPLE_REVIEWED_RESPONSIBILITIES"
        elif st_list == ["reviewed_historical"]:
            want = "C_HISTORICAL_ONLY_MEMBER"
        else:
            want = "A_MEMBER_OF_ONE_REVIEWED_RESPONSIBILITY"
        if by_row.get(i) != want:
            bad.append(f"row {i}：disposition {by_row.get(i)} 與 registry 實況（{rs or '無'}）不符，應為 {want}")

    # ⑥ active census ⛔ 不含 historical
    active = [r for r in recs if r["status"] == "reviewed_active"]
    if reg["counts"]["reviewed_active"] != len(active):
        bad.append("counts.reviewed_active 與實際不符")
    if any(r["status"] == "reviewed_historical" for r in active):
        bad.append("historical 被算進 active census")
    return bad


def self_test() -> int:
    st = load()
    cases = [("現況乾淨", violations(st) == [])]

    def mut(fn):
        m = copy.deepcopy(st); fn(m); return m

    def split_src(m):
        v = next(x for x in m["cur"].values() if x["verdict"] == "SPLIT_REQUIRED")
        return v, v["members"][0]

    # 正對照：漏掛四個 target 之一
    def drop_one(m):
        v, src = split_src(m)
        tgt = v["split_across"][0]
        r = next(x for x in m["reg"]["responsibilities"] if x["sealed_from_candidate_group"] == tgt)
        r["members"] = [x for x in r["members"] if x["row_id"] != src]
        m["proj"]["_row_disposition_partition"]["by_row"][str(src)] = \
            "B_MEMBER_OF_MULTIPLE_REVIEWED_RESPONSIBILITIES"
    m = mut(drop_one)
    cases.append(("漏掛 split target 必須紅",
                  any("未出現**在 target" in x or "漏掛" in x for x in violations(m, False))))

    # 正對照：偷偷替 SPLIT 來源建第五個 responsibility
    def fake_fifth(m):
        v, src = split_src(m)
        clone = copy.deepcopy(m["reg"]["responsibilities"][0])
        clone["responsibility_id"] = "R-99"
        clone["sealed_from_candidate_group"] = v["candidate_group_id"]
        clone["members"] = [{"row_id": src, "member_role": "ANSWER_KNOWLEDGE",
                             "operational_status": "active", "_membership_origin": "DIRECT"}]
        m["reg"]["responsibilities"].append(clone)
    m = mut(fake_fifth)
    cases.append(("替 SPLIT 來源建第五個責任必須紅",
                  any("不得擁有自己的 responsibility record" in x for x in violations(m, False))))

    # 正對照：掛到 split_across 之外
    def wrong_target(m):
        v, src = split_src(m)
        outside = next(r for r in m["reg"]["responsibilities"]
                       if r["sealed_from_candidate_group"] not in v["split_across"]
                       and src not in [x["row_id"] for x in r["members"]])
        outside["members"].append({"row_id": src, "member_role": "ANSWER_KNOWLEDGE",
                                   "operational_status": "active",
                                   "_membership_origin": "SPLIT_REQUIRED"})
    m = mut(wrong_target)
    cases.append(("掛到 split_across 之外必須紅",
                  any("之外的責任" in x for x in violations(m, False))))

    # 正對照：把未解列塞進某個責任
    def fabricate(m):
        v = next(x for x in m["cur"].values() if x["verdict"] == "INSUFFICIENT_EVIDENCE")
        i = v["members"][0]
        m["reg"]["responsibilities"][0]["members"].append(
            {"row_id": i, "member_role": "ANSWER_KNOWLEDGE", "operational_status": "active",
             "_membership_origin": "DIRECT"})
    m = mut(fabricate)
    cases.append(("未解列被塞進責任必須紅",
                  any("製造 authority" in x for x in violations(m, False))))

    # 正對照：disposition 少一列
    m = mut(lambda d: d["proj"]["_row_disposition_partition"]["by_row"].popitem())
    cases.append(("disposition 少一列必須紅",
                  any("未涵蓋 frozen 母體" in x for x in violations(m, False))))

    # 正對照：historical 被當 active
    def hist_active(m):
        r = next(x for x in m["reg"]["responsibilities"] if x["status"] == "reviewed_historical")
        r["status"] = "reviewed_active"
    m = mut(hist_active)
    cases.append(("historical 被標成 active 必須紅",
                  any("應為 reviewed_historical" in x for x in violations(m, False))))

    # 正對照：機器代填 canonical
    def autofill(m):
        r = next(x for x in m["reg"]["responsibilities"]
                 if x["canonical_responsibility_status"] == "PENDING_OWNER_STATEMENT")
        r["canonical_responsibility"] = "機器自己寫的責任陳述"
    m = mut(autofill)
    cases.append(("機器代填 canonical 必須紅",
                  any("機器不得代填" in x for x in violations(m, False))))

    # 正對照：bytes 被改
    m = mut(lambda d: d.update({"rraw": d["rraw"] + b" "}))
    cases.append(("registry bytes 被改必須紅",
                  any("bytes 已變" in x for x in violations(m))))

    for n, ok in cases:
        print(f"{'✅' if ok else '❌'} {n}")
    return 1 if any(not ok for _n, ok in cases) else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if not os.path.exists(os.path.join(R10P, "registry.json")):
        print("（R10-P4 尚未 seal registry——本條不適用）")
        return 0
    bad = violations()
    if bad:
        print("❌ FAIL：R10-P4 registry 投影完整性")
        for b in bad:
            print(f"   · {b}")
        return 1
    st = load()
    t = st["proj"]["_row_disposition_partition"]["tally"]
    c = st["reg"]["counts"]
    print(f"（R10-P4 registry：reviewed_active {c['reviewed_active']}／"
          f"reviewed_historical {c['reviewed_historical']}；"
          f"row disposition 窮盡分割 54＝A{t.get('A_MEMBER_OF_ONE_REVIEWED_RESPONSIBILITY',0)}／"
          f"B{t.get('B_MEMBER_OF_MULTIPLE_REVIEWED_RESPONSIBILITIES',0)}／"
          f"C{t.get('C_HISTORICAL_ONLY_MEMBER',0)}／"
          f"D{t.get('D_UNRESOLVED_NO_AUTHORITATIVE_MEMBERSHIP',0)}；"
          f"⛔ 未解列未被塞進任何責任）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
