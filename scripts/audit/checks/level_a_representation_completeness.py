#!/usr/bin/env python3
"""不變量 13：**Level-A representation population 完整性**（業主定案 2026-08-29）。

## 為什麼這條**現在就該是紅的**

Level-A 的 10 筆是本專案唯一「applicability truth 已閉合」的 authority scope。
D1 之後，它們的 `retrieval_representation` 也必須閉合——否則會出現
「一部分 row 走 reviewed surface、一部分走 legacy summary」的半遷移狀態。

⚠️ 目前 4657 卡在 **capability blocker**（`FACET_TYPE_SELECTION_MISSING`：
全流程從未讀 `type` ⇒「該合約的**點退**帳單」無法被辨識／選出）。業主裁示：**就讓它紅**。

```text
⛔ 不得為了讓 invariant 變綠而寫一個不忠於 row intent 的 representation
⛔ 不得把 4657 改寫成 4656 的 duplicate responsibility 來湊 10/10
⛔ 不得給 legacy exemption——那會把這輪剛找到的真 defect 藏掉
```

> 紅燈的語義**不是**「invariant 太嚴」，而是：
> **一個 Level-A authority row 宣稱能承接的 intent，其 execution responsibility
> 本身尚未成立。**

## 機器判定

```text
母體    LEVEL_A_ROWS（10 筆，凍結）
已宣告  generation_metadata.retrieval_representation 非空
       **且** provenance.source ∈ APPROVED_SOURCES
狀態    COMPLETE   10/10 → PASS
       BLOCKED    缺漏集合 ⊆ KNOWN_BLOCKERS → FAIL（訊息指名 blocker 與 cause）
       PARTIAL    出現 KNOWN_BLOCKERS 以外的缺漏 → FAIL（更嚴重：無名缺漏）
       NOT_STARTED 0/10 → FAIL（population 尚未開始）
⚠️ 四種狀態**都會印出來**，⛔ 不得只印 FAIL 讓人分不出是哪一種。
```

用法：python3 scripts/audit/checks/level_a_representation_completeness.py [--self-test]
"""
import json
import os
import subprocess
import sys

#: 凍結的 Level-A scope（與 instance applicability 的 Level-A 同一組 row）
LEVEL_A_ROWS = [3402, 3406, 3495, 3496, 3498, 3499, 3519, 4640, 4656, 4657]

#: 唯一被承認的 provenance（與 services/retrieval_representation.APPROVED_SOURCES 同值）
APPROVED_SOURCE = "reviewed_product_declaration"

#: 具名 blocker：**不是豁免**——它仍然讓本不變量 FAIL，
#: 只是讓訊息能指出「紅在哪、為什麼紅」，避免與無名缺漏混為一談。
KNOWN_BLOCKERS = {
    4657: "FACET_TYPE_SELECTION_MISSING（點退帳單身分從未以 type 判定）"
           "——見 .kiro/specs/conversational-routing-execution/r9-review-status.md",
}

SQL = """
SELECT COALESCE(json_agg(row_to_json(t)), '[]')::text FROM (
  SELECT id,
         NULLIF(TRIM(COALESCE(generation_metadata->>'retrieval_representation','')), '') AS repr,
         generation_metadata->'retrieval_representation_provenance'->>'source' AS src
  FROM knowledge_base
  WHERE id IN (%s)
) t;
""" % ",".join(str(i) for i in LEVEL_A_ROWS)


def fetch_rows():
    out = subprocess.run(
        ["docker", "exec", "aichatbot-postgres", "psql", "-U", "aichatbot",
         "-d", "aichatbot_admin", "-t", "-A", "-c", SQL],
        capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"psql 失敗：{out.stderr.strip()}")
    return json.loads(out.stdout.strip() or "[]")


def declared_ids(rows):
    """已宣告**且**經審查的 row id 集合。⛔ 只有文字沒有 provenance 不算。"""
    # ⚠️ 空白判定在 Python 端**再做一次**：SQL 的 NULLIF(TRIM(...)) 只保護 DB 這條路，
    #    self-test 餵的是 dict ⇒ 兩邊都要擋，否則測不到的那一半就是漏洞。
    return {r["id"] for r in rows
            if isinstance(r.get("repr"), str) and r["repr"].strip()
            and r.get("src") == APPROVED_SOURCE}


def classify(rows):
    """回傳 (state, missing_ids, unnamed_missing)。"""
    present = declared_ids(rows)
    missing = sorted(set(LEVEL_A_ROWS) - present)
    unnamed = [i for i in missing if i not in KNOWN_BLOCKERS]
    if not missing:
        return "COMPLETE", missing, unnamed
    if len(present) == 0:
        return "NOT_STARTED", missing, unnamed
    if unnamed:
        return "PARTIAL", missing, unnamed
    return "BLOCKED", missing, unnamed


def self_test() -> int:
    def row(i, repr_="x", src=APPROVED_SOURCE):
        return {"id": i, "repr": repr_, "src": src}

    all_ok = [row(i) for i in LEVEL_A_ROWS]
    cases = [
        ("10/10 → COMPLETE", classify(all_ok)[0] == "COMPLETE"),
        ("0/10 → NOT_STARTED", classify([row(i, None, None) for i in LEVEL_A_ROWS])[0]
         == "NOT_STARTED"),
        ("只缺具名 blocker → BLOCKED（**仍非 PASS**）",
         classify([row(i) for i in LEVEL_A_ROWS if i != 4657]
                  + [row(4657, None, None)])[0] == "BLOCKED"),
        ("缺無名 row → PARTIAL（比 BLOCKED 更嚴重）",
         classify([row(i) for i in LEVEL_A_ROWS if i != 3406]
                  + [row(3406, None, None)])[0] == "PARTIAL"),
        # ⚠️ 授權正控制：有文字但 provenance 是 proposal ⇒ ⛔ 不算已宣告
        ("proposal provenance 不得充數",
         4640 not in declared_ids([row(4640, "提案文字", "retrieval_representation_proposal")])),
        ("空白字串不得充數", 4640 not in declared_ids([row(4640, "   ")])),
        ("缺 provenance 不得充數", 4640 not in declared_ids([row(4640, "文字", None)])),
        # ⚠️ 具名 blocker ⛔ 不得被當成豁免：BLOCKED 必須讓 main() 回非 0
        ("BLOCKED 必須 FAIL", _exit_for("BLOCKED") != 0),
        ("COMPLETE 才 PASS", _exit_for("COMPLETE") == 0),
    ]
    for n, ok in cases:
        print(f"{'✅' if ok else '❌'} {n}")
    return 1 if any(not ok for _n, ok in cases) else 0


def _exit_for(state):
    return 0 if state == "COMPLETE" else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    try:
        rows = fetch_rows()
    except Exception as e:                      # noqa: BLE001
        print(f"❌ FAIL：無法取得 Level-A 現況（{e}）——大聲失敗，⛔ 不當成「沒有違規」")
        return 1
    if len(rows) != len(LEVEL_A_ROWS):
        print(f"❌ FAIL：Level-A 母體應為 {len(LEVEL_A_ROWS)} 筆，實得 {len(rows)} 筆"
              f"——凍結的 scope 與 DB 不一致")
        return 1
    state, missing, unnamed = classify(rows)
    present = len(LEVEL_A_ROWS) - len(missing)
    print(f"（Level-A representation population：{present}/{len(LEVEL_A_ROWS)}，狀態 {state}）")
    if state == "COMPLETE":
        return 0
    if state == "NOT_STARTED":
        print("❌ FAIL：population 尚未開始。依定案順序，DB write 需等 10/10 review 閉合"
              "（目前卡 4657 capability blocker）。")
    elif state == "BLOCKED":
        print(f"❌ FAIL：BLOCKED {present}/{len(LEVEL_A_ROWS)}——缺漏全部為**具名 blocker**：")
        for i in missing:
            print(f"   {i}：{KNOWN_BLOCKERS[i]}")
        print("   ⚠️ 具名 ⛔ 不等於豁免；紅燈語義＝該 row 的 execution responsibility 尚未成立。")
    else:
        print(f"❌ FAIL：PARTIAL——出現**無名缺漏** {unnamed}（比 BLOCKED 更嚴重："
              f"半遷移且無人認領）。具名 blocker：{[i for i in missing if i in KNOWN_BLOCKERS]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
