#!/usr/bin/env python3
"""不變量 17：**R10-P governance population 的集合身分**（業主裁定 2026-08-29）。

源起：產 P0 population 時，SQL 的 NULL 傳遞讓 census **少列而不報錯** ——兩次：
① `replace(question_summary, …)` 對 NULL summary → 整列 NULL → `string_agg` 靜默略過
② `generation_metadata ? 'retirement'` 對 **NULL metadata** → 同樣靜默略過
   ⇒ 12 個 alias 中 10 個沒有 generation_metadata，**整批被吞掉**，
     母體只剩 44 列卻「看起來完全正常」。

## 不變量陳述

> **expected IDs == emitted IDs == distinct IDs == 54，且 ID-set digest 必須相符。**

⚠️ 只比 `COUNT(*)=54` **不夠**——「少一列、意外多另一列」會假綠，
故一併比對 **frozen ID-set digest**。

⚠️ **母體漂移一律 FAIL**：`APPLICABILITY_DECLARED` 是活查詢，任何新宣告都會讓母體變大。
R10-P review 進行中，母體變動必須是**明示的版本決策**（比照 LEVEL_A_V1→V2），
⛔ 不得在 review 中途靜默長大——否則已完成的 review 涵蓋範圍立刻失真。

用法：python3 scripts/audit/checks/r10p_population_integrity.py [--self-test]
"""
import hashlib
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
BASE = os.path.join(REPO, ".kiro", "specs", "conversational-routing-execution", "r10p")
POP = os.path.join(BASE, "population.txt")
DIG = os.path.join(BASE, "digests.txt")
EXPECTED_ROWS = 54

#: P0 的機械聯集規則（凍結）
SQL_UNION = """
WITH la AS (SELECT unnest(ARRAY[3402,3406,3495,3496,3498,3499,3519,4640,4656,4657]) AS id),
     alias AS (SELECT unnest(ARRAY[3931,3932,3933,3934,3935,3936,3937,3938,3939,3940,3941,3942]) AS id),
     declared AS (SELECT id FROM knowledge_base WHERE generation_metadata ? 'instance_applicability'),
     u AS (SELECT id FROM la UNION SELECT id FROM alias UNION SELECT id FROM declared)
SELECT string_agg(id::text, ',' ORDER BY id) FROM u;
"""


def frozen():
    with open(DIG, encoding="utf-8") as f:
        txt = f.read()
    def g(k):
        m = re.search(rf"^{k}=(\S+)$", txt, re.M)
        return m.group(1) if m else None
    with open(POP, encoding="utf-8") as f:
        lines = [l for l in f.read().splitlines() if l.strip()]
    ids = [l.split("|", 1)[0] for l in lines]
    return {"pop_digest": g("POPULATION_DIGEST"), "idset_digest": g("POPULATION_IDSET_DIGEST"),
            "lines": lines, "ids": ids}


def db_ids():
    out = subprocess.run(["docker", "exec", "aichatbot-postgres", "psql", "-U", "aichatbot",
                          "-d", "aichatbot_admin", "-t", "-A", "-c", SQL_UNION],
                         capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"psql 失敗：{out.stderr.strip()}")
    raw = out.stdout.strip()
    return raw.split(",") if raw else []


def idset_digest(ids):
    return hashlib.sha256(",".join(sorted(ids, key=int)).encode()).hexdigest()


def violations(fz=None, live=None):
    fz = frozen() if fz is None else fz
    bad = []
    n_lines, n_ids, n_uniq = len(fz["lines"]), len(fz["ids"]), len(set(fz["ids"]))
    if not (n_lines == n_ids == n_uniq == EXPECTED_ROWS):
        bad.append(f"凍結母體不自洽：lines={n_lines} ids={n_ids} distinct={n_uniq}"
                   f"（應皆為 {EXPECTED_ROWS}）——⚠️ 這正是 NULL 靜默丟列的形狀")
    got = hashlib.sha256(("\n".join(fz["lines"]) + "\n").encode()).hexdigest()
    if fz["pop_digest"] and got != fz["pop_digest"]:
        bad.append(f"population.txt bytes 已變（digest {got[:12]}… ≠ 凍結 {fz['pop_digest'][:12]}…）")
    if fz["idset_digest"] and idset_digest(fz["ids"]) != fz["idset_digest"]:
        bad.append("ID-set digest 與凍結值不符")
    live = db_ids() if live is None else live
    if live:
        extra = sorted(set(live) - set(fz["ids"]), key=int)
        missing = sorted(set(fz["ids"]) - set(live), key=int)
        if missing:
            bad.append(f"凍結母體中的 id 已不在聯集結果內：{missing}——⚠️ 真實破壞")
        if extra:
            bad.append(f"聯集結果**多出** id：{extra} ⇒ governance population 漂移。"
                       f"⚠️ review 中途母體不得靜默長大——需明示**版本決策**（比照 LEVEL_A_V1→V2）")
    return bad


def self_test() -> int:
    fz = frozen()
    cases = [("凍結母體自洽（54/54/54）",
              len(fz["lines"]) == len(fz["ids"]) == len(set(fz["ids"])) == EXPECTED_ROWS),
             ("現況乾淨", violations() == [])]
    # 正對照：少一列（模擬 NULL 靜默丟列）
    cut = dict(fz); cut["lines"] = fz["lines"][:-1]; cut["ids"] = fz["ids"][:-1]
    cases.append(("少一列必須紅", violations(cut, fz["ids"]) != []))
    # 正對照：少一列 + 多一列（COUNT 仍為 54 ⇒ 只比數量會假綠）
    swap = dict(fz)
    swap["lines"] = fz["lines"][:-1] + ["999999|true|-|false|假列"]
    swap["ids"] = fz["ids"][:-1] + ["999999"]
    v = violations(swap, fz["ids"])
    cases.append(("少一列＋多一列（COUNT 仍 54）必須紅", v != []))
    # 正對照：聯集多出 id ⇒ 漂移必紅
    cases.append(("母體漂移必須紅", any("漂移" in x for x in violations(fz, fz["ids"] + ["888888"]))))
    for n, ok in cases:
        print(f"{'✅' if ok else '❌'} {n}")
    return 1 if any(not ok for _n, ok in cases) else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    try:
        bad = violations()
    except Exception as e:                                    # noqa: BLE001
        print(f"❌ FAIL：檢查無法執行（{e}）——大聲失敗")
        return 1
    if bad:
        print("❌ FAIL：R10-P population 完整性違規：")
        for b in bad:
            print(f"   {b}")
        return 1
    print(f"（R10-P governance population：{EXPECTED_ROWS} 列，lines＝ids＝distinct 皆相符；"
          f"population 與 ID-set 兩個 digest 均未變；聯集無漂移）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
