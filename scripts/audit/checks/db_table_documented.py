#!/usr/bin/env python3
"""不變量 37：**`public` schema 的每一張表都要有文件，或明示登記為例外**。

源起（2026-09-12）：業主問「這 19 張零引用的表要不要處置」，而**沒有任何地方
記得住答案**——`DECISIONS.md`／`MAP.md`／`DATABASE_SCHEMA.md` 三者對
`digression_config`／`knowledge_gap_analysis`／`loop_rollback_history` 都是 0 次提及。
逐一盤查後才發現更大的洞：`DATABASE_SCHEMA.md` 只寫了 **38/63** 張，
漏掉的 25 張裡有 **12 張是執行期程式正在讀寫的**——其中 `usage_events`
（每次 `/mcp` 呼叫落一列、14,422 列）與 `vendor_quotas`（額度）都在內。

⇒ 這不是「某幾張表沒寫」，是**沒有機制保證資料表會被寫進文件**。

## 不變量陳述

> 每一張 `public` schema 的表，要嘛出現在 `docs/architecture/DATABASE_SCHEMA.md`，
> 要嘛列在 `scripts/audit/data/db_tables_undocumented.txt`（明示例外，要說得出理由）。

⚠️ **例外清單是凍結債，⛔ 不是垃圾桶**：加一行等於宣告「這張表不需要文件」。
新表一律該寫文件，⛔ 不得靠加例外過關。

⚠️ **本檢查器需要 DB 連線**；連不上一律 **FAIL 並印明原因**，
⛔ 不得因為「拿不到表清單」就靜默通過（大聲失敗原則）。

用法：python3 scripts/audit/checks/db_table_documented.py [--self-test]
"""
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DOC = os.path.join(REPO, "docs", "architecture", "DATABASE_SCHEMA.md")
EXCL = os.path.join(REPO, "scripts", "audit", "data", "db_tables_undocumented.txt")
PG = ("docker", "exec", "aichatbot-postgres", "psql", "-U", "aichatbot",
      "-d", "aichatbot_admin", "-t", "-A", "-c")
SQL = "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1;"


def live_tables():
    r = subprocess.run(PG + (SQL,), capture_output=True, text=True)
    if r.returncode != 0:
        return None, (r.stderr or "").strip()[:200]
    return [x.strip() for x in r.stdout.splitlines() if x.strip()], None


def excluded():
    if not os.path.exists(EXCL):
        return set()
    out = set()
    with open(EXCL, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#"):
                out.add(line)
    return out


def documented(table, doc_text):
    return re.search(r"(?<![\w])" + re.escape(table) + r"(?![\w])", doc_text) is not None


def self_test():
    fails = []
    if not os.path.exists(DOC):
        fails.append("① DATABASE_SCHEMA.md 不存在")
    else:
        doc = open(DOC, encoding="utf-8").read()
        # 正對照：一張一定寫過的表
        if not documented("knowledge_base", doc):
            fails.append("② 正對照 knowledge_base 在文件裡找不到（比對法壞了）")
        # 負對照：一個不可能存在的表名不得被判成已記錄
        if documented("this_table_does_not_exist_xyz", doc):
            fails.append("③ 不存在的表名被判成已記錄（比對法太寬）")
    ex = excluded()
    if not ex:
        fails.append("④ 例外清單讀不到或為空（⛔ 空清單不得當通過）")
    tbls, err = live_tables()
    if tbls is None:
        fails.append(f"⑤ 取不到表清單（{err}）——⛔ 不得靜默通過")
    elif len(tbls) < 10:
        fails.append(f"⑥ 只取到 {len(tbls)} 張表，查詢可能壞了")
    if fails:
        for f in fails:
            print(f"❌ self-test: {f}")
        return 1
    print(f"✅ self-test 通過（6 個正對照；DB {len(tbls)} 張表、例外清單 {len(ex)} 行）")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    tbls, err = live_tables()
    if tbls is None:
        print(f"❌ FAIL：取不到 public 表清單（{err}）——⛔ 不得因此判通過")
        return 1
    if not tbls:
        print("❌ FAIL：表清單為空，查詢壞了")
        return 1
    doc = open(DOC, encoding="utf-8").read()
    ex = excluded()
    missing = [t for t in tbls if not documented(t, doc) and t not in ex]
    stale_ex = [t for t in ex if t not in tbls]
    if missing:
        print(f"❌ FAIL：{len(tbls)} 張表中 {len(missing)} 張既無文件也未登記例外")
        for t in missing:
            print(f"   {t}")
        print("   ⇒ 寫進 docs/architecture/DATABASE_SCHEMA.md，"
              "或在 scripts/audit/data/db_tables_undocumented.txt 說明為何不需要")
        return 1
    if stale_ex:
        print(f"❌ FAIL：例外清單有 {len(stale_ex)} 張表已不存在於 DB（清單腐爛）")
        for t in stale_ex:
            print(f"   {t}")
        return 1
    print(f"✅ PASS（{len(tbls)} 張表：{len(tbls) - len(ex)} 張有文件、{len(ex)} 張登記例外）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
