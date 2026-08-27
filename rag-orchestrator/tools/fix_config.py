#!/usr/bin/env python3
"""L1 設定違規的**決定性修正**（knowledge-config-governance 任務 3）。

```text
make fix-config            # dry-run：只印將要執行的 SQL，**不寫入**
make fix-config APPLY=1    # 真跑：執行並產生對應的 rollback SQL
```

## 兩條鐵則

1. **只修 L1**。L2 需先寫得出明確規則才可自動化；**L3 一律不修**
   （那是在回答「這個 query 應該由誰擁有」，屬產品語義）。
2. **只修有唯一正解的那幾條**。以下逐條列出「可修」與「不可修」的理由——
   說不出唯一正解的，寧可留給人，也不猜。

## 逐條處置

```text
C10 active 表單指向不存在的 endpoint → **可修**：is_active = false
    唯一正解的理由：該表單完成後必然回「不支援的 API endpoint」，
    停用是唯一不需要猜的補救。⚠️ **不得**自動映射到名稱相近的端點、
    不得重建 legacy 端點——那已跨入產品語義（業主 2026-08-26 裁定）。
C9  知識掛不存在的 endpoint  → **不可修**：停用整筆知識會連帶移除它的答案內容，
    影響面大於缺陷本身；交人工。
C1  列既無 config 也無 target_user → **不可修**：要補哪一邊是語義決定。
C2  key 重複 → **不可修**：留哪一筆是語義決定。
C3  category 模式卻無 category → **不可修**：該填什麼 category 是語義決定。
C4  category 重複 → **不可修**：同上。
C5  delegate target 不存在 → **不可修**：該指向誰是責任歸屬（L3 的題）。
C6  delegate 缺 when → **不可修**：when 是語義條件，不能自動生成。
C8  面向的 grounding endpoint 不存在 → **不可修**：該接哪支 API 是產品決定。
```
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.audit_config import (DB_NAME, DB_USER, PG, known_endpoints,  # noqa: E402
                                load_configs, q, scan)

APPLY = os.getenv("APPLY", "0") == "1" or "--apply" in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__))
ROLLBACK_DIR = os.path.join(os.path.dirname(HERE), "database", "migrations", "rollback")

#: 有唯一正解、可決定性自動修的規則（其餘一律交人工，理由見 docstring）
AUTOFIXABLE = {"C10"}


def _forms_with_unknown_endpoint(endpoints):
    rows = q("""SELECT form_id, coalesce(api_config->>'endpoint','') FROM form_schemas
                WHERE is_active AND api_config ? 'endpoint' ORDER BY form_id;""")
    out = []
    for line in filter(None, rows.splitlines()):
        form_id, endpoint = line.split("|", 1)
        if endpoint and endpoint not in endpoints:
            out.append((form_id, endpoint))
    return out


def main() -> int:
    endpoints = known_endpoints()
    configs = load_configs()
    for c in configs:
        c["answer"] = q(f"SELECT coalesce(answer,'') FROM knowledge_base WHERE id={c['id']};")
    kb = [tuple(l.split("|", 1)) for l in q(
        """SELECT id, coalesce(api_config->>'endpoint','') FROM knowledge_base
           WHERE api_config ? 'endpoint' AND is_active ORDER BY id;""").splitlines() if l]
    forms = _forms_with_unknown_endpoint(endpoints)
    findings = scan(configs, endpoints, kb, [(f, e) for f, e in forms])

    fixable = [f for f in findings if f["rule"] in AUTOFIXABLE]
    manual = [f for f in findings if f["rule"] not in AUTOFIXABLE]

    print(f"═══ fix-config（{'**APPLY**' if APPLY else 'dry-run'}）═══")
    print(f"可決定性修：{len(fixable)} 筆｜交人工：{len(manual)} 筆\n")

    if not fixable:
        print("沒有可自動修的 L1 違規。")
    else:
        ids = [f for f, _ in forms]
        forward = ("UPDATE form_schemas SET is_active = false, updated_at = now()\n"
                   f"WHERE form_id IN ({', '.join(repr(i) for i in ids)});")
        backward = ("-- rollback：還原這次停用的表單（僅還原本次動到的 form_id）\n"
                    "UPDATE form_schemas SET is_active = true, updated_at = now()\n"
                    f"WHERE form_id IN ({', '.join(repr(i) for i in ids)});")
        for f in fixable:
            print(f"  [{f['rule']}] {f['subject']}\n        → 停用（endpoint 不存在，完成後必然失敗）")
        print("\n── 將執行的 SQL ──\n" + forward)
        if APPLY:
            path = os.path.join(ROLLBACK_DIR, "fix_config_disable_broken_forms_rollback.sql")
            os.makedirs(ROLLBACK_DIR, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(backward + "\n")
            subprocess.run(["docker", "exec", PG, "psql", "-U", DB_USER, "-d", DB_NAME,
                            "-v", "ON_ERROR_STOP=1", "-c", forward], check=True)
            print(f"\n✅ 已執行｜rollback 已寫入 {path}")
        else:
            print("\n（dry-run；`make fix-config APPLY=1` 才真跑，屆時同步產生 rollback SQL）")

    if manual:
        print("\n── 交人工（無唯一正解，不猜）──")
        for f in manual:
            print(f"  [{f['rule']}] {f['level']} {f['subject']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
