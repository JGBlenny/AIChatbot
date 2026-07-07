"""回歸測試（先紅後綠）：欄位缺 `prompt` 的表單逐欄位推進不應崩潰。

Bug：部分 active 表單（temporary_parking_registration、complaint_form）的欄位資料
缺 `prompt` 鍵，而 collect_field_data 以硬存取 `next_field['prompt']` 取用 →
逐欄位推進時 `KeyError: 'prompt'`。因這些表單無知識觸發、/message 打不到，屬 latent。

根本修法：在 schema 載入邊界（get_form_schema）正規化欄位，保證每欄位有 prompt。
此測試在修正前應紅（KeyError），修正後綠。integration（需 DB schema）。
對應 testing-traceability R5.4 / R5.6（缺陷回歸）。
"""
import os

import asyncpg
import pytest

from services.form_manager import FormManager

pytestmark = pytest.mark.integration

BROKEN_FORM = "temporary_parking_registration"


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.mark.req("testing-traceability:5.4")
async def test_schema_load_normalizes_missing_prompt():
    """get_form_schema 載入後，每欄位都應有 prompt（即使 DB 資料缺）。"""
    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    try:
        fm = FormManager(db_pool=pool)
        schema = await fm.get_form_schema(BROKEN_FORM)
        assert schema, f"{BROKEN_FORM} 應存在"
        missing = [f.get("field_name") for f in schema["fields"] if not f.get("prompt")]
        assert not missing, f"以下欄位仍缺 prompt（正規化失敗）：{missing}"
    finally:
        await pool.close()


@pytest.mark.req("testing-traceability:5.4")
async def test_advance_field_does_not_crash_when_prompt_missing():
    """驅動缺 prompt 的表單推進欄位，不應 KeyError（修正前此步崩潰）。"""
    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    sid = "reg-missing-prompt"
    try:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)
        fm = FormManager(db_pool=pool)
        await fm.create_form_session(session_id=sid, user_id="u-reg",
                                     vendor_id=2, form_id=BROKEN_FORM)
        # 推進第一欄位 → 進入下一欄位；修正前此處 KeyError: 'prompt'
        r = await fm.collect_field_data("王小明", sid, vendor_id=2)
        assert isinstance(r, dict) and "answer" in r, "應正常回應、不拋例外"
        assert r.get("current_field"), "應推進到下一個欄位"
    finally:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)
        await pool.close()
