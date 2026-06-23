"""回歸測試（先紅後綠）：select 欄位收到非選項輸入應退回重問，不存入無效值。

Bug 2：collect_field_data 的 select 處理（form_manager.py 5b 段）以編號/label/value
比對選項；但**比對不到時沒有 else 分支**，會把原始輸入（如「亂填身分」）原樣存入 →
select 形同不驗證。

修法：5b 段比對後若 resolved_value 仍為 None（非編號、非 label/value）→ 回 validation_failed
退回重問，不推進。僅影響「完全不符任何選項」的輸入；既有編號/精確 label/value 選擇不變。

修正前此測試應紅（非選項被接受、推進），修正後綠。integration（需 DB schema）。
對應 testing-traceability R5.4 / R5.6。
"""
import os

import asyncpg
import pytest

from services.form_manager import FormManager

pytestmark = pytest.mark.integration

# demo_form 第一欄 identity 為 select，選項：個人房東/二房東/包租代管業/物管
SELECT_FORM = "demo_form"


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.mark.req("testing-traceability:5.4")
async def test_select_rejects_non_option_and_accepts_valid():
    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    sid = "reg-select-invalid"
    try:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)
        fm = FormManager(db_pool=pool)

        await fm.create_form_session(session_id=sid, user_id="u-sel",
                                     vendor_id=2, form_id=SELECT_FORM)

        # 非選項輸入 → 應退回重問、不推進
        bad = await fm.collect_field_data("亂填身分", sid, vendor_id=2)
        assert bad.get("validation_failed") is True, \
            f"非選項輸入應 validation_failed，實得 {bad.get('validation_failed')}"
        st = await fm.get_session_state(sid)
        assert st["current_field_index"] == 0, "非選項輸入不應推進到下一欄位"

        # 合法選項 → 應被接受並推進
        ok = await fm.collect_field_data("個人房東", sid, vendor_id=2)
        assert not ok.get("validation_failed"), "合法選項應被接受"
        st2 = await fm.get_session_state(sid)
        assert st2["current_field_index"] == 1, "合法選項應推進到下一欄位"
    finally:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)
        await pool.close()
