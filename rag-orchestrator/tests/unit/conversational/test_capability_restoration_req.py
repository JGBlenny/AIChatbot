"""unit：不變量 9 逼出的能力回補——**驗收單位是「能力可以被使用」，不是設定裡出現端點名稱**。

業主定案（2026-08-29）：只恢復已存在、已被 KB／execution contract 證明的能力，
⛔ 不擴大 Face 的產品責任；且「改完 audit 變綠」不算 PASS，必須證明

    Configuration → capability declared
    Runtime reachability → 對應 execution consumer 真能走到
    Responsibility → 沒有把 unrelated general knowledge 一併搶進 Face
    Preemption → 不再由無能力 Face 搶走原有 execution path

⚠️ 這一輪要防的是「形式綠」：secondary 端點宣告了、資料卻到不了 consumer，
   或 consumer 走到了、卻只是複製了一份判斷邏輯。
"""
import json
from pathlib import Path

import pytest

from services.jgb.bills import build_invoice_facts, build_payment_flow_facts

# 容器內 rootdir＝/app＝rag-orchestrator/（run-tests.sh 掛載），故從 tests/ 往上三層
APP = Path(__file__).resolve().parents[3]
MIGRATION = APP / "database/migrations/restore_preempted_diagnostic_capabilities.sql"
ENGINE = APP / "services/conversational_engine.py"

pytestmark = pytest.mark.unit


# ════════════════════════════════════════════════════════════════════
# Runtime reachability：兩個既有診斷引擎必須真的被走到
# ════════════════════════════════════════════════════════════════════

def test_invoice_logs_attach_reaches_issue_failure_engine():
    """3503「發票為什麼沒有開出來」→ `_diagnose_issue_failure` 必須可達。

    ⚠️ 病灶：該引擎只在 `jgb_invoice_logs` **作為主查詢 endpoint** 時才被分派到，
       而面向路徑主查詢是 `jgb_bills` ⇒ 引擎存在卻永遠到不了。
    """
    bill = {"id": 9001, "title": "測試帳單", "bit_status": 16, "invoice_status": 0,
            "invoice_logs": [{
                "action": "觸發開立",
                "created_at": "2026-08-01 10:00:00",
                "response_parsed": {"status": "FAIL", "message": "買受人統編格式錯誤"},
            }]}
    out = build_invoice_facts(bill, "發票為什麼沒有開出來")
    # 引擎輸出的專屬字樣＋**這張帳單實際的**失敗訊息，兩者都要在
    assert "發票開立紀錄" in out, "未走到 diagnose_invoice_logs"
    assert "買受人統編格式錯誤" in out, "走到了但沒帶出這張帳單的實際失敗訊息"


def test_invoice_facts_without_attach_does_not_fabricate():
    """負控制：沒有 attach 時不得憑空生出開立紀錄（缺 → 不虛構）。"""
    out = build_invoice_facts({"id": 9002, "title": "T", "bit_status": 16,
                               "invoice_status": 0}, "發票為什麼沒有開出來")
    assert "發票開立紀錄" not in out
    assert "買受人統編" not in out


def test_bill_detail_attach_reaches_atm_engine():
    """3502「虛擬帳號過期或轉帳失敗」→ `_diagnose_atm_expired` 必須可達。

    ⚠️ attach 一律是 list（引擎把單物件包成單元素 list）——本測試同時鎖住那個形狀。
    """
    bill = {"id": 9003, "title": "測試帳單", "bit_status": 2,
            "bill_detail": [{"id": 9003, "title": "測試帳單",
                             "pay_info": {"online_payment_action": "atm",
                                          "atm_info": {"expire": "2026/07/31",
                                                       "bank_code": "013",
                                                       "v_account": "9990001234"}}}]}
    out = build_payment_flow_facts(bill, "虛擬帳號過期了嗎 轉帳失敗")
    assert "9990001234" in out or "2026/07/31" in out, \
        "bill_detail 已 attach 但 _diagnose_atm_expired 未被走到"


def test_payment_flow_without_detail_does_not_fabricate():
    """負控制：沒有 bill_detail 時不得生出虛擬帳號資訊。"""
    out = build_payment_flow_facts({"id": 9004, "title": "T", "bit_status": 2},
                                   "虛擬帳號過期了嗎")
    assert "9990001234" not in out


def test_non_atm_question_does_not_trigger_atm_engine():
    """負控制：問題不是虛擬帳號類時，不得因為 attach 存在就硬塞 ATM 診斷。"""
    bill = {"id": 9005, "title": "T", "bit_status": 16, "complete_at": "2026-08-01",
            "bill_detail": [{"pay_info": {"online_payment_action": "atm",
                                          "atm_info": {"v_account": "9990005678"}}}]}
    out = build_payment_flow_facts(bill, "這筆到帳了嗎")
    assert "9990005678" not in out


# ════════════════════════════════════════════════════════════════════
# 假綠防線：單物件 secondary 結果不得被丟成 []
# ════════════════════════════════════════════════════════════════════

def test_single_object_secondary_is_wrapped_not_dropped():
    """`jgb_bill_detail` 回 dict——引擎必須包成單元素 list，⛔ 不得丟成 []。

    原碼 `sec_rows if isinstance(sec_rows, list) else []` 會把 dict 整個丟掉：
    端點宣告了、資料卻永遠不到 ⇒ 設定看起來對、能力仍失效。
    """
    src = ENGINE.read_text(encoding="utf-8")
    assert "elif sec_rows:\n                        attached = [sec_rows]" in src, \
        "單物件 secondary 的包裝已被改掉——會退回丟棄 dict 的假綠行為"


# ════════════════════════════════════════════════════════════════════
# Responsibility：窄責任，⛔ 不得把制度說明一併搶進 Face
# ════════════════════════════════════════════════════════════════════

def _migration_text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_subscription_face_scope_is_narrow():
    """訂閱面向只掛 `條件診斷：訂閱`，**不得**掛 `訂閱方案`（制度說明走知識單發）。"""
    sql = _migration_text()
    assert '"category": "條件診斷：訂閱"' in sql
    assert '"category": "訂閱方案"' not in sql, "把制度說明一併 Face 化＝擴大責任，違反裁定"


def test_subscription_face_declares_existing_capability_only():
    """面向宣告的是**既有**能力：jgb_subscription 端點，⛔ 不新造端點。"""
    sql = _migration_text()
    assert '"endpoint": "jgb_subscription"' in sql
    assert '"role_id": "{session.role_id}"' in sql


# ════════════════════════════════════════════════════════════════════
# Preemption：3505／3506 不得再被無能力的 estate_guide 先 commit
# ════════════════════════════════════════════════════════════════════

def test_subscription_category_is_prepended_not_appended():
    """first-commit-wins 之下候選**順序具語義**——必須 prepend。

    ⚠️ 業主明示：新增 Face 後若 estate_guide 仍先 commit，
       那是「配置新增成功、能力交接仍失敗」，不算 PASS。
       3505/3506 原 categories = [條件診斷：物件, 物件操作引導]，
       `物件操作引導` → estate_guide（select=category，無能力）會先被提名。
    """
    sql = _migration_text()
    assert "array_prepend('條件診斷：訂閱', categories)" in sql, \
        "用 append 會讓 estate_guide 仍然先 commit ⇒ 能力交接失敗"
    assert "array_append" not in sql


def test_migration_does_not_touch_3507():
    """⛔ 不得順手動 3507——它是合約建立受阻，不是訂閱問題（主題相似 ≠ 責任）。"""
    # ⚠️ 只看**可執行語句**：註解裡本來就寫著「⛔ 不動 3507」，
    #    連註解一起比對會把說明文字誤判成違規（第一版就是這樣紅的）。
    code = "\n".join(line for line in _migration_text().splitlines()
                     if not line.lstrip().startswith("--"))
    assert "3507" not in code, "3507 被納入 UPDATE ＝按主題相似度指派責任"
    assert "id IN (3505, 3506)" in code
