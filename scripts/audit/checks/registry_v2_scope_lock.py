#!/usr/bin/env python3
"""不變量 22：**registry V1→V2 只准改 canonical 面**（業主裁定 2026-08-29）。

⚠️ 本輪 scope ＝ canonical population，**⛔ 不是第二次 responsibility review**。
若在填 canonical 時順手改了 members／owner／applicability／status，
registry topology 就會**無聲漂移**，而 P4/P5 的普查數字（30 active／54 disposition）
會在沒有任何裁定紀錄的情況下失真。

## 不變量陳述

> V2 candidate 相對於 **immutable V1**：
> ① responsibility 集合完全相同（⛔ 不得新增／刪除）
> ② 每筆的 responsibility_id／status／facet／applicability／owner／owner_contract／
>    sealed_from_candidate_group **逐欄相同**
> ③ members 逐列相同（row_id／member_role／operational_status／_membership_origin）
> ④ **只有** canonical_responsibility／canonical_responsibility_status／canonical_review 可變
> ⑤ V1 bytes 必須仍等於凍結的 REGISTRY_DIGEST（V1 是 immutable historical seal）

⛔ 若 canonical review 期間發現證據足以推翻 identity／membership／owner，
   必須**另立** responsibility review epoch——⛔ 不得趁填 canonical 改 topology。

用法：python3 scripts/audit/checks/registry_v2_scope_lock.py [--self-test]
"""
import copy
import hashlib
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
R10P = os.path.join(REPO, ".kiro", "specs", "conversational-routing-execution", "r10p")
V1 = os.path.join(R10P, "registry.json")
V2C = os.path.join(R10P, "registry-v2-candidate.json")
#: ⚠️ 只有這三個欄位可變；其餘一律鎖死
MUTABLE = {"canonical_responsibility", "canonical_responsibility_status", "canonical_review"}
LOCKED_SCALARS = ["responsibility_id", "status", "facet", "owner", "owner_contract",
                  "sealed_from_candidate_group"]


def load():
    with open(V1, "rb") as f:
        raw1 = f.read()
    with open(os.path.join(R10P, "digests.txt"), encoding="utf-8") as f:
        m = re.search(r"^REGISTRY_DIGEST=(\S+)$", f.read(), re.M)
    return {"v1": json.loads(raw1), "raw1": raw1, "frozen": m.group(1) if m else None,
            "v2": json.load(open(V2C, encoding="utf-8"))}


def violations(st=None):
    st = load() if st is None else st
    bad = []
    if st["frozen"] and hashlib.sha256(st["raw1"]).hexdigest() != st["frozen"]:
        bad.append("registry.json（V1）bytes 已變——⛔ V1 是 immutable historical seal")
    a = {r["responsibility_id"]: r for r in st["v1"]["responsibilities"]}
    b = {r["responsibility_id"]: r for r in st["v2"]["responsibilities"]}
    added, removed = sorted(set(b) - set(a)), sorted(set(a) - set(b))
    if added:
        bad.append(f"V2 **新增**了 responsibility：{added}——⛔ canonical review 不得新增責任")
    if removed:
        bad.append(f"V2 **刪除**了 responsibility：{removed}——⛔ canonical review 不得刪除責任")
    for rid in sorted(set(a) & set(b)):
        ra, rb = a[rid], b[rid]
        for k in LOCKED_SCALARS:
            if ra.get(k) != rb.get(k):
                bad.append(f"{rid}：鎖定欄位 {k} 被改（{ra.get(k)!r} → {rb.get(k)!r}）"
                           f"——⛔ 這是 topology 變更，需另立 responsibility review epoch")
        if ra.get("applicability") != rb.get("applicability"):
            bad.append(f"{rid}：applicability 被改——⛔ 需另立 responsibility review epoch")
        ma = [(m["row_id"], m["member_role"], m["operational_status"], m.get("_membership_origin"))
              for m in ra["members"]]
        mb = [(m["row_id"], m["member_role"], m["operational_status"], m.get("_membership_origin"))
              for m in rb["members"]]
        if sorted(ma) != sorted(mb):
            bad.append(f"{rid}：members 被改（{sorted(ma)} → {sorted(mb)}）"
                       f"——⛔ membership 變更必須走 responsibility review，⛔ 不得夾帶在 canonical migration")
        extra = (set(rb) - set(ra)) - MUTABLE
        if extra:
            bad.append(f"{rid}：V2 出現非 canonical 面的新欄位 {sorted(extra)}")
    if st["v2"].get("seal_status") not in ("unsealed", "sealed"):
        bad.append("V2 candidate 的 seal_status 非法")
    return bad


def self_test() -> int:
    st = load()
    cases = [("現況乾淨（V2 candidate 與 V1 topology 逐欄相同）", violations(st) == [])]

    def mut(fn):
        m = copy.deepcopy(st); fn(m["v2"]["responsibilities"]); return m

    m = mut(lambda rs: rs[0]["members"].append(
        {"row_id": 999999, "member_role": "ANSWER_KNOWLEDGE",
         "operational_status": "active", "_membership_origin": "DIRECT"}))
    cases.append(("偷改 members 必須紅", any("members 被改" in x for x in violations(m))))

    m = mut(lambda rs: rs[0]["applicability"].update({"value": "general"}))
    cases.append(("偷改 applicability 必須紅", any("applicability 被改" in x for x in violations(m))))

    m = mut(lambda rs: rs[0].update({"owner_contract": "另一個 owner"}))
    cases.append(("偷改 owner 必須紅", any("owner_contract 被改" in x for x in violations(m))))

    m = mut(lambda rs: rs[0].update({"status": "reviewed_historical"}))
    cases.append(("偷改 status 必須紅", any("status 被改" in x for x in violations(m))))

    def add_resp(rs):
        c = copy.deepcopy(rs[0]); c["responsibility_id"] = "R-99"; rs.append(c)
    m = mut(add_resp)
    cases.append(("新增 responsibility 必須紅", any("新增" in x for x in violations(m))))

    m = mut(lambda rs: rs.pop())
    cases.append(("刪除 responsibility 必須紅", any("刪除" in x for x in violations(m))))

    # 正對照：只改 canonical 面必須綠
    def canon_only(rs):
        for r in rs:
            if r["status"] == "reviewed_active":
                r["canonical_responsibility"] = "某段已 review 的責任陳述"
                r["canonical_responsibility_status"] = "OWNER_STATED"
                r["canonical_review"] = {"verdict": "APPROVED", "reviewer": "業主",
                                         "reviewed_at": "2026-08-29", "review_basis": "…"}
    m = mut(canon_only)
    cases.append(("只改 canonical 面必須綠", violations(m) == []))

    # 正對照：V1 bytes 被改必須紅
    m = copy.deepcopy(st); m["raw1"] = m["raw1"] + b" "
    cases.append(("V1 bytes 被改必須紅", any("immutable historical seal" in x for x in violations(m))))

    for n, ok in cases:
        print(f"{'✅' if ok else '❌'} {n}")
    return 1 if any(not ok for _n, ok in cases) else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if not os.path.exists(V2C):
        print("（無 registry V2 candidate——canonical migration 未進行中，本條不適用）")
        return 0
    bad = violations()
    if bad:
        print("❌ FAIL：registry V1→V2 scope lock")
        for b in bad:
            print(f"   · {b}")
        return 1
    st = load()
    done = sum(1 for r in st["v2"]["responsibilities"]
               if r["status"] == "reviewed_active" and r.get("canonical_responsibility"))
    act = sum(1 for r in st["v2"]["responsibilities"] if r["status"] == "reviewed_active")
    print(f"（registry V2 candidate：topology 與 V1 逐欄相同（{len(st['v1']['responsibilities'])} 筆）；"
          f"僅 canonical 面在動（{done}/{act}）；seal_status={st['v2']['seal_status']}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
