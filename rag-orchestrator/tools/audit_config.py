#!/usr/bin/env python3
"""設定契約稽核（knowledge-config-governance R2）——唯讀，不依賴應用程式啟動。

契約來源：`rag-orchestrator/database/config_contracts.yaml`（單一來源）。
本腳本只做三件事：讀 DB → 逐條比對 → 依 L1／L2／L3 分段輸出。

⚠️ **L3 一律標為「提案，待人裁」，不進 FAIL**（R2.2）——
   L3 是在回答「這個 query 應該由誰擁有」，那是產品語義，不是資料清理。
⚠️ **誤報視為缺陷**（R5.1）：規則對合法變體報錯時修規則，不是叫人忽略。
   已知合法變體：role-routed 面向（如 presales）無 topic_scope／無 endpoint。

用法：
  make audit-config                       # 人可讀報告
  python3 rag-orchestrator/tools/audit_config.py --json   # 機器可讀
退出碼：L1／L2 有違規 → 1；只有 L3 提案 → 0（提案不擋部署）
"""
import json
import os
import re
import subprocess
import sys

PG = os.getenv("PG_CONTAINER", "aichatbot-postgres")
DB_USER = os.getenv("DB_USER", "aichatbot")
DB_NAME = os.getenv("DB_NAME", "aichatbot_admin")
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
JSON_OUT = "--json" in sys.argv


def q(sql: str) -> str:
    """唯讀查詢（走既有 docker exec psql 慣例，與 check_invariants.sh 同款）。"""
    return subprocess.run(
        ["docker", "exec", PG, "psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", sql],
        capture_output=True, text=True, check=True).stdout.strip()


def known_endpoints() -> "set[str]":
    """合法 endpoint ＝ **兩個來源的聯集**，缺一即誤報。

    ```text
    ① Python registry   api_call_handler.api_registry（自訂程式實作）
    ② DB api_endpoints  endpoint_id（implementation_type='dynamic'，由 universal handler 分派）
    ```

    ⚠️ 初版只讀 ①，於是把 `lookup_generic`／`demo_form`／`trial_form` 等
    **8 筆合法設定**判成違規（10 筆裡 8 筆誤報）。
    依 R5.1「誤報視為缺陷」——修規則，不是叫人忽略。
    ⚠️ 刻意**不 import** registry：稽核不得依賴應用程式可啟動（R2.3）。
    """
    src = open(os.path.join(REPO, "rag-orchestrator", "services", "api_call_handler.py"),
               encoding="utf-8").read()
    block = re.search(r"self\.api_registry\s*=\s*\{(.*?)\n        \}", src, re.S)
    keys = set(re.findall(r"'([a-z_0-9]+)':", block.group(1))) if block else set()
    dynamic = q("SELECT endpoint_id FROM api_endpoints;")
    return keys | {r.strip() for r in dynamic.splitlines() if r.strip()}


def load_configs() -> "list[dict]":
    rows = q("""
        SELECT id, coalesce(generation_metadata->'conversational_config', 'null'::jsonb)::text,
               coalesce(array_to_string(target_user, ','), '')
        FROM knowledge_base WHERE category = '對話規則' ORDER BY id;
    """)
    out = []
    for line in filter(None, rows.splitlines()):
        kid, payload, tu = line.split("|", 2)
        md = json.loads(payload)
        out.append({"id": int(kid), "md": md if isinstance(md, dict) else None, "target_user": tu})
    return out


def check(findings, level, rule_id, subject, detail):
    findings.append({"level": level, "rule": rule_id, "subject": subject, "detail": detail})


def main() -> int:
    findings: "list[dict]" = []
    configs = load_configs()
    registry = known_endpoints()

    by_key, by_cat = {}, {}
    for c in configs:
        md, kid = c["md"], c["id"]
        if not md and not c["target_user"]:
            check(findings, "L1", "C1", f"kb{kid}",
                  "『對話規則』列既無 conversational_config 也無 target_user → loader 回 None，該列等於不存在")
            continue
        md = md or {}
        key = md.get("key") or md.get("persona_role") or (c["target_user"].split(",")[0] or "default")
        if key in by_key:
            check(findings, "L1", "C2", f"kb{kid}",
                  f"config.key 重複：{key!r} 也出現在 kb{by_key[key]} → 後載入者靜默覆蓋")
        by_key[key] = kid

        scope = md.get("topic_scope") or {}
        if scope.get("mode") == "category":
            cat = (scope.get("category") or "").strip()
            if not cat:
                check(findings, "L1", "C3", f"{key}(kb{kid})",
                      "topic_scope.mode='category' 但 category 為空 → 永遠不會被 config_for_category 命中")
            elif cat in by_cat:
                check(findings, "L1", "C4", f"{key}(kb{kid})",
                      f"topic_scope.category 重複：{cat!r} 也屬 {by_cat[cat]} → by_category 靜默覆蓋")
            else:
                by_cat[cat] = key

        endpoint = ((md.get("grounding_scope") or {}).get("endpoint") or "").strip()
        if endpoint and endpoint not in registry:
            check(findings, "L1", "C8", f"{key}(kb{kid})",
                  f"grounding_scope.endpoint={endpoint!r} 不在 api_registry ∪ api_endpoints → 執行期回「不支援的 API endpoint」")

    # delegates 需在 by_key 建好後才驗
    for c in configs:
        md = c["md"] or {}
        key = md.get("key") or md.get("persona_role")
        for d in ((md.get("responsibility") or {}).get("delegates") or []):
            target = (d or {}).get("target")
            if not target or target not in by_key:
                check(findings, "L1", "C5", f"{key}(kb{c['id']})",
                      f"delegate target={target!r} 不存在於 config registry → resolver fail closed（不進場）")
            if not (d or {}).get("when"):
                check(findings, "L1", "C6", f"{key}(kb{c['id']})",
                      f"delegate {target!r} 缺 when（語義條件）→ 規則生成與斷言會落空")
        if (md.get("responsibility") or {}).get("delegates"):
            rules = (md.get("answer_rules") or "")
            answer = q(f"SELECT coalesce(answer,'') FROM knowledge_base WHERE id={c['id']};")
            if "delegate_facet_key" not in rules and "delegate_facet_key" not in answer:
                check(findings, "L2", "C7", f"{key}(kb{c['id']})",
                      "宣告了 delegates，但 persona 規則未宣告 delegate_facet_key → 模型不會產出該欄位，委派永不發生")

    # C9 knowledge_base.api_config.endpoint
    #  ⚠️ 本條初版立在 `trigger_facet_key` 上——那是 **request 參數**不是欄位，規則本身是錯的。
    ke = q("""SELECT id, coalesce(api_config->>'endpoint','') FROM knowledge_base
              WHERE api_config ? 'endpoint' AND is_active ORDER BY id;""")
    for line in filter(None, ke.splitlines()):
        kid, endpoint = line.split("|", 1)
        if endpoint and endpoint not in registry:
            check(findings, "L1", "C9", f"kb{kid}",
                  f"api_config.endpoint={endpoint!r} 不在 api_registry ∪ api_endpoints → 問到該題才會炸")

    # C10 form_schemas.api_config.endpoint
    fs = q("""SELECT form_id, coalesce(api_config->>'endpoint','') FROM form_schemas
              WHERE is_active AND api_config ? 'endpoint' ORDER BY form_id;""")
    for line in filter(None, fs.splitlines()):
        form_id, endpoint = line.split("|", 1)
        if endpoint and endpoint not in registry:
            check(findings, "L1", "C10", f"form:{form_id}",
                  f"api_config.endpoint={endpoint!r} 不在 api_registry ∪ api_endpoints → 表單完成後必然失敗")

    if JSON_OUT:
        print(json.dumps({"findings": findings, "configs": len(configs),
                          "registry_size": len(registry)}, ensure_ascii=False, indent=2))
    else:
        print(f"═══ 設定契約稽核（{len(configs)} 個對話設定／{len(registry)} 個合法 endpoint）═══\n")
        for lvl, title in (("L1", "L1 Structural（可決定性修）"),
                           ("L2", "L2 Consistency（需明確規則）"),
                           ("L3", "L3 Semantic ownership（**提案，待人裁**）")):
            items = [f for f in findings if f["level"] == lvl]
            print(f"── {title}：{len(items)} 筆")
            for f in items:
                print(f"   [{f['rule']}] {f['subject']}\n        {f['detail']}")
            print()
        print("⚠️ L3 由 skill 產生提案，本掃描器不判定語義歸屬（R2.2／R3.3）。")
    return 1 if any(f["level"] in ("L1", "L2") for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
