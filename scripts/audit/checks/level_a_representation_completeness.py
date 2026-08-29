#!/usr/bin/env python3
"""不變量 13：**Level-A representation population 完整性**（業主定案 2026-08-29）。

## 為什麼這條**現在就該是紅的**

Level-A 的 10 筆是本專案唯一「applicability truth 已閉合」的 authority scope。
D1 之後，它們的 `retrieval_representation` 也必須閉合——否則會出現
「一部分 row 走 reviewed surface、一部分走 legacy summary」的半遷移狀態。

⚠️ 沿革：4657 一度卡在 `FACET_TYPE_SELECTION_MISSING`（全流程從未讀 `type`
⇒「該合約的**點退**帳單」無法被辨識／選出）。`POINT_REFUND_BILL_SELECTION` 實作並經
6 道 guard ＋ 3 個 mutation 後，該 blocker 已 **RESOLVED_LOCALLY**，4657 representation
亦已 APPROVED ⇒ `KNOWN_BLOCKERS` 現為空。業主當時的裁示仍有效且應保留：

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
import hashlib
import json
import os
import subprocess
import sys

#: ⚠️ **Level-A scope 已版本化**（業主裁定 2026-08-29）：
#:   `LEVEL_A_V1` = 原始 10 rows，**immutable**——A04／P1f／R-series 的證據永遠
#:   對 V1 解讀，⛔ 不得回寫成 9；`LEVEL_A_V2` = V1 − {3498}（3498 已停用）。
#:   ⛔ **不得**就地把 10 改成 9——否則回看時無法分辨某份證據講的是哪一版。
REGISTRY = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
    ".kiro", "specs", "conversational-routing-execution", "level-a-scope-registry.json")


def _registry():
    with open(os.path.abspath(REGISTRY), encoding="utf-8") as f:
        return json.load(f)


_REG = _registry()
ACTIVE_VERSION = _REG["active_version"]
LEVEL_A_ROWS = _REG["versions"][ACTIVE_VERSION]["rows"]
V1_ROWS = _REG["versions"]["V1"]["rows"]
V1_DIGEST = _REG["versions"]["V1"]["population_digest"]

#: 唯一被承認的 provenance（與 services/retrieval_representation.APPROVED_SOURCES 同值）
APPROVED_SOURCE = "reviewed_product_declaration"

#: 具名 blocker：**不是豁免**——它仍然讓本不變量 FAIL，
#: 只是讓訊息能指出「紅在哪、為什麼紅」，避免與無名缺漏混為一談。
#: ⚠️ 目前**為空**：4657 的 capability blocker 已解（見上）。
#: 未來若再出現具名 blocker，加在這裡——它仍讓本不變量 FAIL，只是讓訊息分得出
#: 「紅在哪、為什麼紅」，⛔ 不是豁免。
KNOWN_BLOCKERS = {}

def _sql(rows):
    return """
SELECT COALESCE(json_agg(row_to_json(t)), '[]')::text FROM (
  SELECT id,
         NULLIF(TRIM(COALESCE(generation_metadata->>'retrieval_representation','')), '') AS repr,
         generation_metadata->'retrieval_representation_provenance'->>'source' AS src
  FROM knowledge_base
  WHERE id IN (%s)
) t;
""" % ",".join(str(i) for i in rows)


SQL = _sql(LEVEL_A_ROWS)


def fetch_rows(sql=None):
    out = subprocess.run(
        ["docker", "exec", "aichatbot-postgres", "psql", "-U", "aichatbot",
         "-d", "aichatbot_admin", "-t", "-A", "-c", sql or SQL],
        capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"psql 失敗：{out.stderr.strip()}")
    return json.loads(out.stdout.strip() or "[]")


def v1_population_digest():
    """重算 V1 的 population digest。

    ⚠️ **失效不失憶**：3498 停用時宣告與 provenance 全部保留 ⇒ V1 的 digest
    **必須仍然算得出原值**。算不出＝有人刪了歷史宣告，那會讓 A04 的證據無法解讀。
    """
    sql = """
SELECT string_agg(id || '|' || (generation_metadata->>'retrieval_representation') || '|' ||
       (generation_metadata->'retrieval_representation_provenance'->>'source'), E'\n' ORDER BY id)
FROM knowledge_base WHERE id IN (%s);""" % ",".join(str(i) for i in V1_ROWS)
    out = subprocess.run(
        ["docker", "exec", "aichatbot-postgres", "psql", "-U", "aichatbot",
         "-d", "aichatbot_admin", "-t", "-A", "-c", sql],
        capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"psql 失敗：{out.stderr.strip()}")
    return hashlib.sha256(out.stdout.encode()).hexdigest()


def declared_ids(rows):
    """已宣告**且**經審查的 row id 集合。⛔ 只有文字沒有 provenance 不算。"""
    # ⚠️ 空白判定在 Python 端**再做一次**：SQL 的 NULLIF(TRIM(...)) 只保護 DB 這條路，
    #    self-test 餵的是 dict ⇒ 兩邊都要擋，否則測不到的那一半就是漏洞。
    return {r["id"] for r in rows
            if isinstance(r.get("repr"), str) and r["repr"].strip()
            and r.get("src") == APPROVED_SOURCE}


def classify(rows, blockers=None):
    """回傳 (state, missing_ids, unnamed_missing)。

    ⚠️ `blockers` 可注入：否則登記簿一旦清空（blocker 解掉），BLOCKED 這條路徑就
    **再也測不到**——那正是「guard exists ≠ guard can fail」的另一種死法。
    """
    blockers = KNOWN_BLOCKERS if blockers is None else blockers
    present = declared_ids(rows)
    missing = sorted(set(LEVEL_A_ROWS) - present)
    unnamed = [i for i in missing if i not in blockers]
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
        (f"{len(LEVEL_A_ROWS)}/{len(LEVEL_A_ROWS)} → COMPLETE", classify(all_ok)[0] == "COMPLETE"),
        (f"0/{len(LEVEL_A_ROWS)} → NOT_STARTED", classify([row(i, None, None) for i in LEVEL_A_ROWS])[0]
         == "NOT_STARTED"),
        # ⚠️ 注入合成 blocker：登記簿現為空，但這條路徑必須永遠可被測到
        ("只缺具名 blocker → BLOCKED（**仍非 PASS**）",
         classify([row(i) for i in LEVEL_A_ROWS if i != 4657]
                  + [row(4657, None, None)], blockers={4657: "synthetic"})[0] == "BLOCKED"),
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
    print(f"（LEVEL_A_VERSION: {ACTIVE_VERSION}｜ACTIVE_ROWS: {len(LEVEL_A_ROWS)}｜"
          f"REPRESENTATION_POPULATION: {present}/{len(LEVEL_A_ROWS)} {state}）")
    # ⚠️ V1 immutability：歷史宣告必須仍在，否則 A04 的證據無法解讀
    try:
        got = v1_population_digest()
    except Exception as e:                      # noqa: BLE001
        print(f"❌ FAIL：無法重算 V1 population digest（{e}）——大聲失敗")
        return 1
    if got != V1_DIGEST:
        print(f"❌ FAIL：**V1 population digest 已改變**（期望 {V1_DIGEST[:12]}…、"
              f"實得 {got[:12]}…）⇒ 有人刪改了歷史宣告；A04 證據將無法解讀。"
              f"⚠️ 停用 row 必須「失效不失憶」。")
        return 1
    print(f"（V1 immutable：10 rows 的歷史宣告完整，digest {V1_DIGEST[:12]}… 未變 ✅）")
    if state == "COMPLETE":
        return 0
    if state == "NOT_STARTED":
        print("❌ FAIL：population 尚未開始（Level-A 10/10 review 已閉合，"
              "待執行 migrations/r9_level_a_retrieval_representation.sql）。")
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
