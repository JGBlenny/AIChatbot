#!/usr/bin/env python3
"""不變量 9：Face preemption 的能力保全（Capability preservation across Face preemption）。

**源起**（2026-08-29 盤查）：`chat.py` 的面向分支在表單分支**之前**（同一個
`form_trigger_threshold` 門檻），且 responsibility resolver 的 allowlist 未涵蓋的面向
一律回 `FACE_UNEVALUATED` → `face_precedence()` 判 `"face"` → **無條件 commit**。
於是「知識掛著 active 表單」與「知識的某個 category 命中面向」同時成立時，
**表單永遠不會開**——而這在 2026-07 的面向化遷移期沒有任何盤查或守衛。

實例：3505/3506（為什麼不能新增物件／物件為什麼突然全部下架）掛
`jgb_subscription_diagnosis`（收識別碼→打 `jgb_subscription` 查**該使用者**訂閱狀態），
卻被 `estate_guide` 攔截——而 estate_guide 是 `grounding_scope.select=category`
的引導型面向，只讀知識庫，**沒有任何實值查詢能力**。
答案因此從「查你這一筆」降級成「通用說明」，且靜默無訊號。

── 不變量陳述（產品層，與實作解耦）────────────────────────────────────
  若一筆**仍具 active execution capability** 的知識會被 Face nomination 攔截，
  該 Face 必須能證明保留**等價的 execution capability**；否則 FAIL。

── ⚠️ 可證代理條件（**這是目前的實作代理，不是產品公理**）──────────────
  本檢查器用來機器判定「Face 保有 execution capability」的述詞是：
      grounding_scope.select == 'api'   （面向自己打 API 取實值）
   或 grounding_scope 具 'execute_endpoint'（交易面向，可寫入執行）
  這是**現行專案裡唯一可機器證明**的等價能力形式。
  ⛔ 不得把 `select=api` 讀成「能力等價的定義」——它只是當前唯一的可證形式。
  若日後出現別種等價能力（例如面向掛工具、或委派給具能力的面向），
  **必須改的是這裡的述詞**，而不是把違規列進豁免清單。

── FAIL vs WARN 的分界（有實據，非主觀）─────────────────────────────
  FAIL：被攔截的表單會**取外部實值**（on_complete_action=call_api 且
        endpoint 不是純分流 handler）——遺失的是「查你這一筆」的能力。
  WARN：被攔截的表單是**選項分流**（endpoint ∈ BRANCHING_ENDPOINTS，
        如 `branch_answer`＝選項分歧知識回覆，implementation_type=custom，
        不取任何外部資料）——面向以知識作答在種類上等價，
        但 `next_form_id` 的後續鏈結仍會遺失 ⇒ 列為待辦雷達，不擋部署。
        （同族既有處置：不變量 1 對 3508／3522 分流表單的 by-design 豁免。）

用法：python3 scripts/audit/checks/face_preemption_capability.py [--self-test]
退出碼：0＝PASS（WARN 不影響），1＝FAIL。
"""
import json
import subprocess
import sys

# 純分流 handler：不取外部實值，僅依選項回不同知識（api_endpoints.implementation_type=custom）
BRANCHING_ENDPOINTS = {"branch_answer"}
# 知識層自帶執行語義（不經 form_schemas）
DIRECT_EXECUTION_ACTIONS = {"api_call", "form_then_api"}


# ════════════════════════════════════════════════════════════════════
# 純函式核心（可離線測；DB 只負責餵資料）
# ════════════════════════════════════════════════════════════════════

def knowledge_has_execution_capability(row) -> bool:
    """這筆知識目前是否仍具**可執行**能力（表單或 API）。

    ⚠️ 停用的表單不算——指向 inactive form 的知識早已無能力可失去。
    """
    if row.get("action_type") in DIRECT_EXECUTION_ACTIONS:
        return True
    if row.get("form_id"):
        return bool(row.get("form_active"))
    return False


def face_preserves_capability(row) -> bool:
    """Face 是否**可證**保有等價 execution capability（見檔頭「可證代理條件」）。"""
    if (row.get("face_select") or "").lower() == "api":
        return True
    return bool(row.get("face_has_execute_endpoint"))


def preempted_capability_is_data_fetching(row) -> bool:
    """被攔截的能力是否為「取外部實值」（決定 FAIL／WARN）。"""
    if row.get("action_type") in DIRECT_EXECUTION_ACTIONS:
        return True
    if (row.get("form_on_complete") or "") != "call_api":
        return False
    return (row.get("form_endpoint") or "") not in BRANCHING_ENDPOINTS


def evaluate(rows):
    """rows = 每個 (知識, 被提名面向) 配對。回傳 (fails, warns)。"""
    fails, warns = [], []
    for r in rows:
        if not knowledge_has_execution_capability(r):
            continue                      # shape C：資訊型知識，本不變量不管
        if face_preserves_capability(r):
            continue                      # shape A：能力保全
        item = (f"知識 {r.get('kid')}「{r.get('summary')}」"
                f" 表單/動作={r.get('form_id') or r.get('action_type')}"
                f" → 被面向 {r.get('face_key')}"
                f"（select={r.get('face_select') or '無'}）攔截")
        (fails if preempted_capability_is_data_fetching(r) else warns).append(item)
    return fails, warns


# ════════════════════════════════════════════════════════════════════
# 自我測試：先證明 guard 抓得到已知病灶，再去掃 repo（同不變量 8 的紀律）
# ════════════════════════════════════════════════════════════════════

def _row(**kw):
    base = dict(kid=0, summary="", action_type="form_fill", form_id=None, form_active=True,
                form_on_complete="call_api", form_endpoint="jgb_x",
                face_key="f", face_select="api", face_has_execute_endpoint=False)
    base.update(kw)
    return base


def self_test() -> int:
    cases = []

    # ── shape A：有執行能力 ＋ 面向具等價能力 → 不得報 ──
    a = _row(kid=1, summary="A", form_id="jgb_contract_query", face_key="contract_diag",
             face_select="api")
    cases.append(("A 能力保全不得誤報", evaluate([a]) == ([], [])))

    # ── shape A'：交易面向以 execute_endpoint 證明能力 → 不得報 ──
    a2 = _row(kid=2, summary="A'", form_id="jgb_repair_create", face_key="repair_create",
              face_select=None, face_has_execute_endpoint=True)
    cases.append(("A' execute_endpoint 亦屬等價能力", evaluate([a2]) == ([], [])))

    # ── shape B：有執行能力（取實值）＋ 面向無能力 → 必須 FAIL ──
    b = _row(kid=3505, summary="B", form_id="jgb_subscription_diagnosis",
             face_key="estate_guide", face_select="category")
    b_f, b_w = evaluate([b])
    cases.append(("B 能力遺失必須 FAIL", len(b_f) == 1 and b_w == []))

    # ── shape C：資訊型知識（無表單、非動作型）→ 不得因本不變量誤報 ──
    c = _row(kid=4, summary="C", action_type="direct_answer", form_id=None,
             face_key="estate_guide", face_select="category")
    cases.append(("C 資訊型知識不得誤報", evaluate([c]) == ([], [])))

    # ── shape C'：指向 inactive 表單 → 早已無能力可失去，不得報 ──
    c2 = _row(kid=5, summary="C'", form_id="dead_form", form_active=False,
              face_key="estate_guide", face_select="category")
    cases.append(("C' 停用表單不得誤報", evaluate([c2]) == ([], [])))

    # ── 分流表單被攔截 → WARN 而非 FAIL ──
    d = _row(kid=3548, summary="D", form_id="payment_gateway_select",
             form_endpoint="branch_answer", face_key="billing_setup_guide",
             face_select="category")
    d_f, d_w = evaluate([d])
    cases.append(("分流表單降為 WARN", d_f == [] and len(d_w) == 1))

    # ── 突變控制：把已 PASS 的 A 拔掉能力，scanner 必須轉紅 ──
    mutated = dict(a, face_select="category")
    m_f, _ = evaluate([mutated])
    cases.append(("突變控制：拔掉能力後必須轉紅", len(m_f) == 1))

    # ── 突變控制 2：把 B 的面向補上能力，scanner 必須轉綠（證明它讀的是能力而非知識 id）──
    healed = dict(b, face_select="api")
    cases.append(("突變控制：補上能力後必須轉綠", evaluate([healed]) == ([], [])))

    bad = [name for name, ok in cases if not ok]
    for name, ok in cases:
        print(f"{'✅' if ok else '❌'} {name}")
    if bad:
        print(f"❌ 自我測試未過：{bad}")
        return 1
    return 0


# ════════════════════════════════════════════════════════════════════
# DB 取值
# ════════════════════════════════════════════════════════════════════

SQL = r"""
WITH face AS (
  SELECT generation_metadata->'conversational_config'->'topic_scope'->>'category' AS cat,
         generation_metadata->'conversational_config'->>'key'                     AS fkey,
         generation_metadata->'conversational_config'->'grounding_scope'          AS gs
  FROM knowledge_base
  WHERE category='對話規則' AND is_active
    AND COALESCE((generation_metadata->'conversational_config'->>'enabled')::boolean, TRUE)
)
SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json)::text FROM (
  SELECT k.id AS kid, k.question_summary AS summary, k.action_type, k.form_id,
         COALESCE(fs.is_active, FALSE)          AS form_active,
         fs.on_complete_action                  AS form_on_complete,
         fs.api_config->>'endpoint'             AS form_endpoint,
         f.fkey                                 AS face_key,
         f.gs->>'select'                        AS face_select,
         (f.gs ? 'execute_endpoint')            AS face_has_execute_endpoint
  FROM knowledge_base k
  JOIN face f ON f.cat = ANY(k.categories)
  LEFT JOIN form_schemas fs ON fs.form_id = k.form_id
  WHERE k.is_active
    AND (k.form_id IS NOT NULL OR k.action_type IN ('form_fill','api_call','form_then_api'))
) t;
"""


def fetch_rows():
    out = subprocess.run(
        ["docker", "exec", "aichatbot-postgres", "psql", "-U", "aichatbot",
         "-d", "aichatbot_admin", "-t", "-A", "-c", SQL],
        capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"psql 失敗：{out.stderr.strip()}")
    return json.loads(out.stdout.strip() or "[]")


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    rows = fetch_rows()
    if not rows:
        # ⚠️ 大聲失敗：母體為空代表查詢或環境壞了，不是「沒有違規」
        print("❌ FAIL：母體為 0——被面向提名的動作知識不可能一筆都沒有，"
              "請檢查 DB 連線或 schema（否定結論需正對照組）")
        return 1
    fails, warns = evaluate(rows)
    print(f"（母體：{len(rows)} 組 (知識, 被提名面向) 配對）")
    for w in warns:
        print(f"⚠️  WARN（分流表單，不擋部署）：{w}")
    if fails:
        print("❌ FAIL：以下知識的 execution capability 會被無等價能力的面向靜默攔截：")
        for f in fails:
            print(f"   {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
