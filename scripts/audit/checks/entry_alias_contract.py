#!/usr/bin/env python3
"""不變量 16：**entry alias ⛔ 不得各自擁有 semantic contract**（業主裁定 2026-08-29）。

⚠️ **狀態：TRANSITIONAL_GUARD，⛔ 不是終局契約**（業主明示）。
「允許同 facet 共用**逐字相同**的 canonical contract」只是避免 migration 卡死，
⛔ **不代表終局允許兩份相同 semantic document 各自進 ranking**。
R10 已裁 target architecture＝C＋C2（explicit `responsibility_id`＋
threshold／truncation／reranker **之前** collapse），終局應升級為：

```text
ENTRY_ALIAS MUST reference exactly one active responsibility_id
ENTRY_ALIAS MUST NOT own authoritative retrieval_representation
ENTRY_ALIAS MUST NOT own authoritative applicability
canonical retrieval_representation MUST belong to responsibility
applicability MUST belong to responsibility
multiple aliases of same responsibility
  MUST collapse before threshold／truncation／reranking
```

源起（T3 provenance audit）：`billing-knowledge-review.md` 明文「錨點（12 筆，
answer 空、**一種講法一筆**）」，且批次 schema 每筆只有 facet／question／keywords
⇒ 錨點的單位是**講法**，責任單位是 **facet**。

## 不變量陳述

> **同一 facet 底下的 entry alias，⛔ 不得擁有**彼此不同**的 authoritative
> `retrieval_representation`——那等於發明一個不存在的 responsibility distinction。**

⚠️ 允許的兩種狀態：① 全部未宣告（現況，`NOT_POPULATED_PENDING_ALIAS_GOVERNANCE`）；
② 同 facet 全部共用**逐字相同**的 canonical contract。
⚠️ ⛔ 本不變量**不要求**退役任何 alias——`KEEP_BOTH_AS_ENTRY_VARIANTS` 是業主定案。

用法：python3 scripts/audit/checks/entry_alias_contract.py [--self-test]
"""
import json
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
REGISTRY = os.path.join(REPO, ".kiro", "specs", "conversational-routing-execution",
                        "entry-alias-registry.json")
APPROVED_SOURCE = "reviewed_product_declaration"


def facets():
    with open(REGISTRY, encoding="utf-8") as f:
        return json.load(f)["facets"]


def fetch(ids):
    sql = ("SELECT COALESCE(json_agg(json_build_object('id',id,"
           "'repr',NULLIF(TRIM(COALESCE(generation_metadata->>'retrieval_representation','')),''),"
           "'src',generation_metadata->'retrieval_representation_provenance'->>'source')),'[]')::text "
           "FROM knowledge_base WHERE id IN (%s);" % ",".join(str(i) for i in ids))
    out = subprocess.run(["docker", "exec", "aichatbot-postgres", "psql", "-U", "aichatbot",
                          "-d", "aichatbot_admin", "-t", "-A", "-c", sql],
                         capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"psql 失敗：{out.stderr.strip()}")
    return {r["id"]: r for r in json.loads(out.stdout.strip() or "[]")}


def violations(groups, data):
    bad = []
    for facet, rows in groups.items():
        declared = {}
        for r in rows:
            rec = data.get(r["id"], {})
            if rec.get("repr") and rec.get("src") == APPROVED_SOURCE:
                declared[r["id"]] = rec["repr"]
        if len(set(declared.values())) > 1:
            bad.append(f"facet「{facet}」的 entry alias 擁有**不同**的 representation："
                       f"{ {k: v[:24] + '…' for k, v in declared.items()} }"
                       f" ⇒ 發明了不存在的 responsibility distinction")
    return bad


def self_test() -> int:
    g = facets()
    ids = [r["id"] for rows in g.values() for r in rows]
    cases = [("登記簿涵蓋 12 個錨點", len(ids) == 12),
             ("現況乾淨", violations(g, fetch(ids)) == [])]
    # 正對照：同 facet 兩個 alias 各寫不同 representation 必須紅
    fake = {3939: {"id": 3939, "repr": "查滯納金為何這麼多", "src": APPROVED_SOURCE},
            3940: {"id": 3940, "repr": "拆解滯納金計算過程", "src": APPROVED_SOURCE}}
    cases.append(("同 facet 不同 representation 必須紅", violations(g, fake) != []))
    same = {3939: {"id": 3939, "repr": "同一份 canonical", "src": APPROVED_SOURCE},
            3940: {"id": 3940, "repr": "同一份 canonical", "src": APPROVED_SOURCE}}
    cases.append(("同 facet 共用逐字相同 contract 不得誤報", violations(g, same) == []))
    only_one = {3939: {"id": 3939, "repr": "只有一列宣告", "src": APPROVED_SOURCE}}
    cases.append(("只有一列宣告不得誤報", violations(g, only_one) == []))
    for n, ok in cases:
        print(f"{'✅' if ok else '❌'} {n}")
    return 1 if any(not ok for _n, ok in cases) else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    try:
        g = facets()
        ids = [r["id"] for rows in g.values() for r in rows]
        if not ids:
            print("❌ FAIL：entry-alias 登記簿為空——大聲失敗，⛔ 不當成沒有違規")
            return 1
        bad = violations(g, fetch(ids))
    except Exception as e:                                    # noqa: BLE001
        print(f"❌ FAIL：檢查無法執行（{e}）——大聲失敗")
        return 1
    if bad:
        print("❌ FAIL：entry alias 契約違規：")
        for b in bad:
            print(f"   {b}")
        return 1
    print(f"（entry alias {len(ids)} 筆／{len(g)} 個 facet；同 facet 內未出現分歧的 "
          f"semantic contract；⚠️ 現況為 NOT_POPULATED_PENDING_ALIAS_GOVERNANCE）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
