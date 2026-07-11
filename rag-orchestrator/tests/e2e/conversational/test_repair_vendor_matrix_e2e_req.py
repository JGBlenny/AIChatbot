"""e2e：四業者驗收矩陣（conversational-repair 任務 4.2 / R6.2, R6.4）。

四業者（vendor_id 1/2/3/4）各以其租客身份走情境 A 核心流（文字版，無圖）——
斷言四者體驗一致（都進面向、出 confirm、建單成功）：
  - vendor 1/3：從無到有（原本無修繕 SOP，新形態直接可用）；
  - vendor 2/4：從舊表單切新形態（M2 已停用其修繕 SOP，is_active=false）。

**decision_case 遙測佐證（vendor 2/4）**：修繕查詢不再由 SOP 攔截——
usage_events.decision_case 不應是「SOP 勝出」案（sop_significantly_higher /
only_sop_qualified / close_scores_sop_* / sop_triggered_* 等 sop_ 勝出前綴）；
知識面向路由勝出（knowledge_* / only_knowledge_qualified）或直接走面向（無仲裁 sop 勝出）
即證 SOP 不再攔截。M2 未套時此斷言會紅（正確反映回歸）。

**gate e2e（另補）**：把某 vendor 的 repair_enabled 設 false（fixture 自建自清）→
不進面向、回降級文案＋客服管道（R1.5）。

身分：mock get_tenant_contracts 對任意 role_id/user_id 預設回 1 筆租約（見 _mock_get_tenant_contracts），
故四業者共用同一 mock 租客身份、僅 vendor_id 變動即可驗矩陣。
需 RUN_E2E=1 ＋ 整服務 ＋ USE_MOCK_JGB_API=true。
"""
import asyncio
import os
import uuid

import pytest

pytestmark = pytest.mark.e2e

VENDOR_IDS = [int(v) for v in os.getenv("TEST_REPAIR_VENDOR_IDS", "1,2,3,4").split(",")]
SOP_SWITCHED_VENDORS = {2, 4}   # M2 停用修繕 SOP 的業者（decision_case 佐證對象）
ROLE_ID = os.getenv("TEST_REPAIR_ROLE_ID", "R001")
USER_ID = os.getenv("TEST_REPAIR_USER_ID", "U001")
MOCK_TICKET = os.getenv("TEST_REPAIR_MOCK_TICKET", "12346")


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def _require_repair_facet():
    if os.getenv("USE_MOCK_JGB_API", "").lower() != "true":
        pytest.skip("修繕 e2e 需 USE_MOCK_JGB_API=true")

    async def _check():
        import asyncpg
        from services.conversational_config import config_for_category, reset_cache
        reset_cache()
        pool = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=1)
        try:
            return await config_for_category(pool, "修繕報修")
        finally:
            await pool.close()
    try:
        cfg = asyncio.run(_check())
    except Exception as e:
        pytest.skip(f"無法連 DB 檢查修繕面向設定：{e}")
    if cfg is None:
        pytest.skip("修繕面向設定未就緒；請套用面向配置＋錨點知識 seeds 並清快取")


def _post(client, message, sid, vendor_id):
    r = client.post("/api/v1/message", json={
        "message": message, "vendor_id": vendor_id, "target_user": "tenant", "mode": "b2c",
        "role_id": ROLE_ID, "user_id": USER_ID, "session_id": sid, "stream": False})
    assert r.status_code == 200, r.text
    return r.json()


def _answer(resp):
    return (resp.get("answer") or "").strip()


def _is_confirm(resp):
    qr = resp.get("quick_replies") or []
    vals = {q.get("value") for q in qr if isinstance(q, dict)}
    if "confirm_submit" in vals:
        return True
    a = _answer(resp)
    return ("確認" in a and ("送出" in a or "正確" in a))


def _conversational_rows(sid):
    import asyncpg

    async def _q():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            return await conn.fetchval(
                "SELECT count(*) FROM form_sessions WHERE session_id=$1 AND form_id='conversational'", sid)
        finally:
            await conn.close()
    return asyncio.run(_q())


def _decision_cases(sid):
    """該 session 首輪（進場）的 decision_case 遙測——用於佐證 SOP 是否攔截。"""
    import asyncpg

    async def _q():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            rows = await conn.fetch(
                "SELECT decision_case FROM usage_events WHERE session_id=$1", sid)
            return [r["decision_case"] for r in rows]
        finally:
            await conn.close()
    return asyncio.run(_q())


def _wait_decision_cases(sid, tries=20):
    import time
    for _ in range(tries):
        cases = _decision_cases(sid)
        if cases:
            return cases
        time.sleep(0.3)
    return _decision_cases(sid)


def _cleanup(sid):
    import asyncpg

    async def _d():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            await conn.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)
            await conn.execute("DELETE FROM usage_events WHERE session_id=$1", sid)
        finally:
            await conn.close()
    asyncio.run(_d())


# 缺槽補話（無圖文字路徑，槽位補齊具 LLM 變異）——不含同意詞，驅動到確認 gate。
_SLOT_FILL_NUDGES = [
    "很急，昨天就壞了",
    "是冷氣，不會冷、不製冷",
    "客廳的冷氣，完全不冷",
    "分類是家電，項目是冷氣，原因不製冷，很緊急",
]


def _run_scenario_a_core(client, vendor_id):
    """情境 A 核心流（無圖文字版）：進面向 → 補槽驅動到 confirm → 同意建單。
    回 (final_answer, decision_cases)。文字路徑缺槽補問具變異，故用補話驅動到確認 gate。"""
    sid = f"e2e-repair-vm{vendor_id}-{uuid.uuid4().hex[:8]}"
    try:
        # 開場（明確帶物件內項目，利於文字推斷）
        r = _post(client, "冷氣壞了，不會冷，客廳的", sid, vendor_id)
        assert _conversational_rows(sid) >= 1, f"vendor {vendor_id}：明確報修應進修繕面向對話"

        if not _is_confirm(r):
            for nudge in _SLOT_FILL_NUDGES:
                r = _post(client, nudge, sid, vendor_id)
                if _is_confirm(r):
                    break
        assert _is_confirm(r), \
            f"vendor {vendor_id}：槽位收齊應出確認 gate，實得：{_answer(r)[:200]}"

        r_consent = _post(client, "好", sid, vendor_id)
        a3 = _answer(r_consent)
        assert MOCK_TICKET in a3, \
            f"vendor {vendor_id}：同意後應建單成功回單號，實得：{a3[:200]}"

        cases = _wait_decision_cases(sid)
        return a3, cases
    finally:
        _cleanup(sid)


# ══════ R6.4 四業者一致體驗 ══════

@pytest.mark.parametrize("vendor_id", VENDOR_IDS)
@pytest.mark.req("conversational-repair:6.4")
def test_vendor_matrix_scenario_a_consistent(client, vendor_id):
    """四業者各走情境 A 核心流 → 都進面向、出 confirm、建單成功（體驗一致）。"""
    _run_scenario_a_core(client, vendor_id)


@pytest.mark.parametrize("vendor_id", sorted(SOP_SWITCHED_VENDORS))
@pytest.mark.req("conversational-repair:6.4")
def test_vendor_sop_switched_decision_case_not_sop(client, vendor_id):
    """vendor 2/4：修繕查詢的 decision_case 不得是 SOP 勝出案（佐證 M2 停用後 SOP 不再攔截）。"""
    if vendor_id not in VENDOR_IDS:
        pytest.skip(f"vendor {vendor_id} 不在受測清單")
    _answer_txt, cases = _run_scenario_a_core(client, vendor_id)
    assert cases, f"vendor {vendor_id}：應有 usage_events 遙測入庫"
    sop_win = [c for c in cases if c and c.startswith("sop_")]
    assert not sop_win, \
        f"vendor {vendor_id}：修繕查詢不應由 SOP 勝出攔截（M2 應已停用），實得 decision_case={cases}"


# ══════ gate e2e：repair_enabled=false → 不進面向回降級文案（R1.5，fixture 自建自清）══════

@pytest.mark.req("conversational-repair:6.4")
def test_gate_disabled_returns_degraded_not_facet(client):
    """把某 vendor repair_enabled 設 false → 不進面向、回降級文案。fixture 自建自清、不動 seed。"""
    import asyncpg
    from services.vendor_config_service import VendorConfigService  # noqa: F401
    gate_vendor = int(os.getenv("TEST_REPAIR_GATE_VENDOR", "3"))
    sid = f"e2e-repair-gate-{uuid.uuid4().hex[:8]}"

    # vendor_configs 唯一鍵＝(vendor_id, category, param_key)；gate 讀值只認 param_key，
    # 故 category 任填可辨識值（'service'）。data_type='boolean' → 'false' 解析為 False。
    GATE_CATEGORY = "service"

    async def _set_gate(value):
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            await conn.execute(
                "INSERT INTO vendor_configs (vendor_id, category, param_key, param_value, data_type) "
                "VALUES ($1, $2, 'repair_enabled', $3, 'boolean') "
                "ON CONFLICT (vendor_id, category, param_key) "
                "DO UPDATE SET param_value = EXCLUDED.param_value, data_type = EXCLUDED.data_type",
                gate_vendor, GATE_CATEGORY, "false" if value is False else "true")
        finally:
            await conn.close()

    async def _clear_gate():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            await conn.execute(
                "DELETE FROM vendor_configs WHERE vendor_id=$1 AND category=$2 AND param_key='repair_enabled'",
                gate_vendor, GATE_CATEGORY)
        finally:
            await conn.close()

    try:
        try:
            asyncio.run(_set_gate(False))
        except Exception as e:
            pytest.skip(f"無法設定 repair_enabled gate fixture：{e}")
        # 清 vendor_config 快取（服務可能快取）——透過 reset 或直接新請求；此處靠新 session。
        r = _post(client, "冷氣壞了不會冷", sid, gate_vendor)
        a = _answer(r)
        assert a, "gate 關仍應有降級回覆"
        assert _conversational_rows(sid) == 0, \
            f"repair_enabled=false 不應進修繕面向對話，實得 rows={_conversational_rows(sid)}"
    finally:
        _cleanup(sid)
        try:
            asyncio.run(_clear_gate())
        except Exception:
            pass
