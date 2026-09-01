"""F-C28：被 validate_session() 視為 authority contract 的欄位，必須能跨 persistence 存活。

⚠️ 逼出本條的實例（2026-09-01，S2 真 DB round-trip）：
   `build_responsibility_session()` 在記憶體裡設 on_complete_action=resume_fulfillment，
   `validate_session()` 把它當契約驗，但 form_sessions 沒有該欄位
   ⇒ restore 後必為 None ⇒ turn 2 直接 SessionAuthorityError。
   unit 測試餵**記憶體 dict**，所以一直是綠的——只有真 round-trip 會炸。

⚠️ 本檔守的是「validator knows field / writer forgot field」這個失效模式：
   欄位清單必須有**單一來源**，⛔ 不得兩處各抄一份。
"""
import inspect
import re

import pytest

from services import responsibility_session as rsess

pytestmark = pytest.mark.unit

#: validate_session 允許讀、且**確實有對應 form_sessions 欄位**的其他鍵
OTHER_PERSISTED_KEYS = {"knowledge_id"}


def _keys_read_by(func):
    src = inspect.getsource(func)
    keys = set(re.findall(r'session\.get\(\s*["\'](\w+)["\']', src))
    keys |= set(re.findall(r'session\[\s*["\'](\w+)["\']\s*\]', src))
    # 透過常數迭代讀取的欄位
    if "AUTHORITY_FIELDS" in src:
        keys |= set(rsess.AUTHORITY_FIELDS)
    return keys


def test_positive_control_validator_reads_something():
    """沒有它，下面的子集合斷言可能只是在比對空集合。"""
    keys = _keys_read_by(rsess.validate_session)
    assert keys, "解析不到 validate_session 讀取的欄位——⛔ 守門失效"
    assert "session_authority_mode" in keys
    assert "on_complete_action" in keys, "解析漏了 on_complete_action ⇒ 本檔無法守住該欄"


def test_every_validated_field_is_declared_persistable():
    """**F-C28 本體**：validator 讀的每個欄位都必須在單一持久化宣告內。"""
    keys = _keys_read_by(rsess.validate_session)
    declared = set(rsess.PERSISTED_AUTHORITY_FIELDS) | OTHER_PERSISTED_KEYS
    missing = sorted(keys - declared)
    assert not missing, (
        f"validate_session 驗了 {missing}，但它們不在 PERSISTED_AUTHORITY_FIELDS 內"
        f"——⛔ restore 後必為 None，validation 會在跨 turn 時才炸")


def test_builder_output_covers_every_persisted_field():
    """writer 端：builder 產出的 session 必須含全部宣告欄位。"""
    session = rsess.build_responsibility_session(
        responsibility_id="R-29", fulfillment_binding_id="receipt.actual_amount.v1",
        fulfillment_strategy="CAPABILITY", input_contract_id="bill.by_ref.v1")
    missing = [f for f in rsess.PERSISTED_AUTHORITY_FIELDS if f not in session]
    assert not missing, f"builder 未產出 {missing}"


def test_persisted_declaration_is_single_source_in_writer():
    """⛔ writer ⛔ 不得手抄第二份欄位清單。"""
    from services import form_manager
    src = inspect.getsource(form_manager.FormManager.trigger_responsibility_form)
    src += inspect.getsource(form_manager.FormManager._create_form_session_sync)
    assert "PERSISTED_AUTHORITY_FIELDS" in src, "writer 未引用單一來源常數"
    # 手抄跡象：同時出現三個以上 authority 欄位字面值
    literals = sum(1 for f in rsess.AUTHORITY_FIELDS if f'"{f}"' in src)
    assert literals < 3, "writer 內出現多個 authority 欄位字面值——疑似又手抄了一份清單"


def test_restore_must_not_derive_on_complete_action():
    """⚠️ restore 階段補值會讓 validate_session 對還原路徑恆真（normalization 非 validation）。
    ⇒ 以缺欄的 restored session 呼叫 validate_session **必須 RED**。"""
    restored = {"session_authority_mode": "responsibility",
                "responsibility_id": "R-29",
                "fulfillment_binding_id": "receipt.actual_amount.v1",
                "fulfillment_strategy": "CAPABILITY",
                "input_contract_id": "bill.by_ref.v1",
                "on_complete_action": None,          # ← DB 未持久化時的樣子
                "knowledge_id": None}
    with pytest.raises(rsess.SessionAuthorityError):
        rsess.validate_session(restored)


def test_show_knowledge_in_responsibility_mode_is_red():
    """F-C4：responsibility mode ⛔ 不得以 row authority 作 completion authority。"""
    tampered = {"session_authority_mode": "responsibility",
                "responsibility_id": "R-29",
                "fulfillment_binding_id": "receipt.actual_amount.v1",
                "fulfillment_strategy": "CAPABILITY",
                "input_contract_id": "bill.by_ref.v1",
                "on_complete_action": rsess.ACTION_SHOW_KNOWLEDGE,
                "knowledge_id": None}
    with pytest.raises(rsess.SessionAuthorityError):
        rsess.validate_session(tampered)


def test_fully_persisted_session_validates():
    """正對照：欄位齊全時必須 GREEN，否則上面的 RED 沒有意義。"""
    good = {"session_authority_mode": "responsibility",
            "responsibility_id": "R-29",
            "fulfillment_binding_id": "receipt.actual_amount.v1",
            "fulfillment_strategy": "CAPABILITY",
            "input_contract_id": "bill.by_ref.v1",
            "on_complete_action": rsess.ACTION_RESUME_FULFILLMENT,
            "knowledge_id": None}
    assert rsess.validate_session(good) == rsess.MODE_RESPONSIBILITY
