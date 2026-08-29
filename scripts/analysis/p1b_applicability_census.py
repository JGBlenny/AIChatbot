#!/usr/bin/env python3
"""P1b：instance applicability 的全量 deterministic census（**只產提案，⛔ 不寫 DB**）。

判準（業主定案 2026-08-29）：
```text
① 只允許 machine-supported disposition：instance／general／UNKNOWN
   instance/general **必須附可追溯 evidence**；證據不足一律 UNKNOWN，
   ⛔ 不為了提高 coverage 引入「看起來像」。
② execution capability **只能當 evidence，不得當決定規則**
   no form ≠ general（3509 反證）；has form ≠ 一定 instance
③ 先產 census、凍結、再決定是否寫回 DB
   ⛔ 不得一邊掃一邊 UPDATE generation_metadata——規則若有問題，資料已被污染
```

verdict：`DETERMINISTIC_INSTANCE` / `DETERMINISTIC_GENERAL` / `CONFLICT` / `UNKNOWN`
⚠️ CONFLICT 不自動裁決——不同證據互斥時直接停在 CONFLICT，不做優先序。
"""
import json
import os
import re
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
JGB_DIR = os.path.join(REPO, "rag-orchestrator/services/jgb")
#: 使用者範圍的讀取端點（參數含 role_id／bill_id／estate_id 等個體識別）
USER_SCOPED_ENDPOINTS = {
    "jgb_bills", "jgb_bill_detail", "jgb_payments", "jgb_payment_logs",
    "jgb_invoices", "jgb_invoice_logs", "jgb_contracts", "jgb_contract_checkin",
    "jgb_subscription", "jgb_estates", "jgb_estate_status", "jgb_estate_detail",
    "jgb_meters", "jgb_repairs", "jgb_tenant_summary", "jgb_tenant_registration",
    "jgb_team_members", "jgb_member_permissions", "jgb_bill_visibility",
    "jgb_iot_manufacturers",
}
#: 純分流／非取值端點 —— ⛔ 不得作為 instance 證據
NON_DATA_ENDPOINTS = {"branch_answer", "lookup"}

_DOC_RE = re.compile(r'def (_?diagnose_[a-z_]+|build_[a-z_]+_facts)\([^)]*\)[^:]*:\s*\n\s*"""([A-Z]\d{2})：([^\n"]+)')


def engine_titles():
    """E1 來源：診斷引擎 docstring 的「代碼：標題」。**可追溯到 file:function**。"""
    out = {}
    for fn in sorted(os.listdir(JGB_DIR)):
        if not fn.endswith(".py"):
            continue
        path = os.path.join(JGB_DIR, fn)
        src = open(path, encoding="utf-8").read()
        for m in _DOC_RE.finditer(src):
            func, code, title = m.group(1), m.group(2), m.group(3).strip()
            title = re.split(r"[——(（]", title)[0].strip()
            if title:
                out.setdefault(_norm(title), []).append(f"services/jgb/{fn}::{func}（{code}）")
    return out


def _norm(s):
    return re.sub(r"[\s　,，、。？?！!/／]", "", str(s or ""))


SQL = r"""
SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json)::text FROM (
  WITH face AS (
    SELECT generation_metadata->'conversational_config'->'topic_scope'->>'category' AS cat,
           generation_metadata->'conversational_config'->>'key'  AS fkey,
           generation_metadata->'conversational_config'->'grounding_scope' AS gs
    FROM knowledge_base WHERE category='對話規則' AND is_active
      AND COALESCE((generation_metadata->'conversational_config'->>'enabled')::boolean, TRUE)
  )
  SELECT k.id, k.question_summary, k.categories, k.action_type, k.form_id,
         k.api_config->>'endpoint'  AS row_endpoint,
         fs.api_config->>'endpoint' AS form_endpoint,
         COALESCE(fs.is_active, FALSE) AS form_active,
         (SELECT count(*) FROM jsonb_array_elements(COALESCE(fs.fields,'[]'::jsonb)) fd
           WHERE fd->>'field_name' IS NOT NULL) AS form_field_count,
         (SELECT json_agg(json_build_object('key', f.fkey, 'select', f.gs->>'select',
                  'req_inst', f.gs->>'requires_instance_reference'))
            FROM face f WHERE f.cat = ANY(k.categories)) AS candidates,
         k.generation_metadata->>'instance_applicability' AS existing_declaration
  FROM knowledge_base k
  LEFT JOIN form_schemas fs ON fs.form_id = k.form_id
  WHERE k.is_active AND COALESCE(k.category,'') NOT IN ('對話規則','系統脈絡')
) t;
"""


def fetch_rows():
    out = subprocess.run(
        ["docker", "exec", "aichatbot-postgres", "psql", "-U", "aichatbot",
         "-d", "aichatbot_admin", "-t", "-A", "-c", SQL],
        capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(f"psql 失敗：{out.stderr.strip()}")
    return json.loads(out.stdout.strip() or "[]")


def classify(row, titles):
    """回 (verdict, proposed, [(evidence_source, evidence_detail), ...])。

    ⚠️ 目前**只有 instance 側**存在 deterministic evidence source。
       `general` 需要「這一題不依賴使用者資料」的正面證據，
       而 repository 內**不存在**這樣的機器事實——「沒有 instance 跡象」
       不是 general 的證據（同否定結論紀律）。⇒ 大量 UNKNOWN 是預期結果。
    """
    ev = []
    key = _norm(row.get("question_summary"))
    if key in titles:
        ev.append(("E1_ENGINE_TITLE", "；".join(titles[key])))
    fep = row.get("form_endpoint")
    if (row.get("form_active") and fep in USER_SCOPED_ENDPOINTS
            and (row.get("form_field_count") or 0) >= 1):
        ev.append(("E2_IDENTIFIER_FORM",
                   f"form={row.get('form_id')} → {fep}（收 {row['form_field_count']} 個識別欄位）"))
    rep = row.get("row_endpoint")
    if row.get("action_type") in ("api_call", "form_then_api") and rep in USER_SCOPED_ENDPOINTS:
        ev.append(("E3_ACTION_API", f"action={row['action_type']} → {rep}"))
    if ev:
        return "DETERMINISTIC_INSTANCE", "instance", ev
    return "UNKNOWN", "unknown", []


def main():
    titles = engine_titles()
    rows = fetch_rows()
    if not rows:
        print("❌ 母體為 0——大聲失敗，不當成「沒有資料」")
        return 1
    out = []
    for r in rows:
        verdict, proposed, ev = classify(r, titles)
        cands = r.get("candidates") or []
        out.append({
            "knowledge_id": r["id"],
            "question_summary": r.get("question_summary"),
            "categories": r.get("categories") or [],
            "current_candidate_facet_keys": [c["key"] for c in cands],
            "execution_capability": bool(r.get("form_id")) or r.get("action_type") in (
                "form_fill", "api_call", "form_then_api"),
            "face_requirement_if_any": [c.get("req_inst") for c in cands],
            "proposed_applicability": proposed,
            "evidence_source": [e[0] for e in ev],
            "evidence_detail": [e[1] for e in ev],
            "verdict": verdict,
            "existing_declaration": r.get("existing_declaration"),
        })
    dest = os.path.join(REPO, "scripts/analysis/p1b_census.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    from collections import Counter
    c = Counter(o["verdict"] for o in out)
    print(f"引擎標題證據源：{len(titles)} 條")
    print(f"母體：{len(out)} 筆")
    for k in ("DETERMINISTIC_INSTANCE", "DETERMINISTIC_GENERAL", "CONFLICT", "UNKNOWN"):
        print(f"  {k:24s} {c.get(k,0):4d}  {100.0*c.get(k,0)/len(out):5.1f}%")
    print(f"census → {os.path.relpath(dest, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
