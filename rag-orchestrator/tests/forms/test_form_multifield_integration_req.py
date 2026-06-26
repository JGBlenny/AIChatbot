"""FormManager 元件層：多欄位表單填寫推進（integration，碰真實 DB schema）。

驗證表單引擎逐欄位推進——以 demo_form（5 欄位，含 select identity）為例，
經 create_form_session → 逐欄位 collect_field_data，推進至全欄位收集完（REVIEWING）。

說明（誠實標註現況行為，非臆測）：
- demo_form 的 select 欄位 identity 目前「不驗證選項」（送非選項文字也被接受）→ 故本測試
  不斷言 select 選項驗證；該行為記於 spec 發現清單，待產品端決定是否強制。
- demo_form on_complete=call_api，完成前先進 REVIEWING（送出審閱）；本測試停在 REVIEWING，
  不觸發外部 API。
對應 testing-traceability R5.4（表單填寫流程）。需 RUN_INTEGRATION=1 與可連 DB。
"""
import os

import asyncpg
import pytest

from services.form_manager import FormManager

pytestmark = pytest.mark.integration


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.mark.req("testing-traceability:5.4")
async def test_demo_form_multifield_progression_to_review():
    pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    sid = "e2e-demo-multifield"
    try:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)

        fm = FormManager(db_pool=pool)
        await fm.create_form_session(session_id=sid, user_id="u-mf",
                                     vendor_id=2, form_id="demo_form")
        start = await fm.get_session_state(sid)
        assert start["form_id"] == "demo_form"
        assert start["state"] == "COLLECTING"

        # 依序送 5 欄位值，記錄每步推進到的下一欄位
        seen_fields = []
        for value in ["個人房東", "30", "3", "自動催繳", "0912345678"]:
            r = await fm.collect_field_data(value, sid, vendor_id=2)
            seen_fields.append(r.get("current_field"))

        # 逐欄位推進：至少推進過數個不同欄位，最後一步收集完畢（不再停在某欄位）
        assert seen_fields[-1] is None, f"全欄位填完後不應再停在收集，實得 {seen_fields}"
        distinct_fields = [f for f in seen_fields if f]
        assert len(distinct_fields) >= 3, f"應逐欄位推進多個欄位，實得 {seen_fields}"

        # 全欄位收集完 → 進入審閱（送出前）或完成；證明 5 欄位表單推進到流程尾端
        final = await fm.get_session_state(sid)
        assert final["state"] in ("REVIEWING", "COMPLETED"), \
            f"全欄位後應進入 REVIEWING/COMPLETED，實得 {final['state']}"
    finally:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)
        await pool.close()
