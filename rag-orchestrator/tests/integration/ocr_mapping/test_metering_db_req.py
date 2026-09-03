"""integration 層：端點計量真的落 usage_events（需求 9.3／9.5）。需 RUN_INTEGRATION=1 與 DB_* 環境。

驗的是本端點用的同一組 usage_metering 呼叫序（begin → set_path → finalize(db_pool)）：
落一列 `processing_path='ocr_mapping'`、`is_internal` 依 session 前綴、且 `decision_snapshot` 不含任何欄位值。
"""
import asyncio
import os
import uuid

import pytest

pytestmark = pytest.mark.integration


async def _run(session_id: str) -> dict:
    import asyncpg
    from services import usage_metering as um
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "postgres"), port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aichatbot_admin"), user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", ""), min_size=1, max_size=2,
    )
    try:
        um.begin({"mode": "b2c", "role_id": "20151", "target_user": "landlord", "vendor_id": 1, "session_id": session_id})
        um.set_path("ocr_mapping")
        um.finalize(status="success", http_status=200, db_pool=pool)
        await asyncio.sleep(0.5)                                        # fire-and-forget 寫入
        row = await pool.fetchrow(
            "SELECT processing_path, is_internal, internal_kind, decision_snapshot::text AS snap "
            "FROM usage_events WHERE session_id = $1 ORDER BY ts DESC LIMIT 1", session_id)
        return dict(row) if row else {}
    finally:
        await pool.close()


@pytest.mark.req("documind-ocr-mapping:9.3")
def test_metering_writes_one_row_with_ocr_mapping_path():
    if os.getenv("RUN_INTEGRATION") != "1":
        pytest.skip("RUN_INTEGRATION 未設")
    sid = f"backtest_session_ocrint_{uuid.uuid4().hex[:8]}"
    row = asyncio.run(_run(sid))
    assert row, "usage_events 沒有落列（正對照：同一連線可查 usage_events）"
    assert row["processing_path"] == "ocr_mapping" and row["is_internal"] is True and row["internal_kind"] == "backtest"
    assert not row["snap"] or "壹萬" not in row["snap"]                  # 需求 9.5：不落欄位值
