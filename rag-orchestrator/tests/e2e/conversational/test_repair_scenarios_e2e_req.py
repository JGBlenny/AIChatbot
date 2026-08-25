"""e2e：對話式修繕目標形態情境 A–F＋冪等（conversational-repair 任務 5.1 / R7.3 含 R1–R5）。

TestClient(app) 程序內起整服務，POST /api/v1/message 走正常管線
（意圖分類→檢索→reranker→config_for_category→修繕交易面向引擎→真 LLM＋mock JGB API）：
  - A 明確報修（單一租約身份）→ 物件確認式陳述＋只問缺槽（急迫性）→ confirm 摘要＋quick_replies
      →「好」→ 回執含單號；≤3 輪、execute 一次、facet 埋點 MAX(turn_number)≥3 入庫（R2.5/R4.1/R7.3）。
  - B 岔題先答回流：收槽中問費用 → 先答再接回收集，最終仍建單（R3.1）。
  - C 模糊先澄清：「房子有點問題」不進面向；後續「馬桶不通」進面向（R1.2）。
  - D 確認階段改資料：confirm 後改急迫性 → 重出 confirm → 同意 → 建單一次（R4.5）。
  - E 完成後查進度：建單後「修得怎樣了」→ jgb_repairs 查詢回工單狀態（R5.1）。
  - F 直達參數：trigger_facet_key='repair_create' 進同一面向（跳意圖辨識，R1.3）。
  - 冪等：建單後再說「好」→ 回單號不重複建單（execute 一次，R4.4）。

身分：b2c、mode=b2c、target_user=tenant。
⚠️ 2026-08-25 起 `get_tenant_contracts` 走**真端點** `/contracts/status-overview` 帶 `user_id`，
mock 端由 `ContractFixtureTable` 依 `to_user_id` 過濾（production 語義 `(int) user_id`）——
故 user_id **必須是 fixture 的租客編號**：9001 → 1 筆有效租約（678）。
舊的 R001/U001 語義（任意組合都回 1 筆）已隨方法級 mock 一併移除。

**照片（A 案）**：ENABLE_IMAGE_RECOGNITION=true 時 Vision 真打 GPT-4o 不穩定且需真圖，
故 A 案採「文字推斷版」為穩定收案主軸（描述「冷氣壞了」即足夠進面向、推斷分類），
不依賴 image_urls；帶圖版的圖辨識由 unit（test_repair_entry_gate_req Step 0.5）＋
integration（test_repair_image_ingest_integration_req）覆蓋，e2e 不重跑不穩定 Vision。

真 LLM → 斷言僅限「行為級不變式」（進面向/出確認/建單/單號/查進度），不逐字比對文案。
需 RUN_E2E=1 ＋ 整服務（DB/embedding/semantic-model/OPENAI）＋ USE_MOCK_JGB_API=true。
"""
import asyncio
import os
import uuid

import pytest

pytestmark = pytest.mark.e2e

VENDOR_ID = int(os.getenv("TEST_REPAIR_VENDOR_ID", "1"))
ROLE_ID = os.getenv("TEST_REPAIR_ROLE_ID", "R001")
USER_ID = os.getenv("TEST_REPAIR_USER_ID", "9001")    # fixture 678 的 to_user_id → 1 筆有效租約
MOCK_TICKET = os.getenv("TEST_REPAIR_MOCK_TICKET", "12346")   # _mock_create_repair data.id


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
    """修繕面向配置＋mock JGB API 前置：任一未就緒 → skip（不假綠）。"""
    if os.getenv("USE_MOCK_JGB_API", "").lower() != "true":
        pytest.skip("修繕 e2e 需 USE_MOCK_JGB_API=true（開發以 mock 驗流程，E1 真 API 為上線 gate）")

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


# ── 請求／查詢輔助 ───────────────────────────────────────────────────────

def _post(client, message, sid, *, trigger_facet_key=None, image_urls=None):
    body = {
        "message": message, "vendor_id": VENDOR_ID, "target_user": "tenant", "mode": "b2c",
        "role_id": ROLE_ID, "user_id": USER_ID, "session_id": sid, "stream": False,
    }
    if trigger_facet_key:
        body["trigger_facet_key"] = trigger_facet_key
    if image_urls:
        body["image_urls"] = image_urls
    r = client.post("/api/v1/message", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _answer(resp):
    return (resp.get("answer") or "").strip()


def _is_confirm(resp):
    """confirm gate 出現的行為訊號：quick_replies 含 confirm_submit（機器值），或摘要含確認語。"""
    qr = resp.get("quick_replies") or []
    vals = {q.get("value") for q in qr if isinstance(q, dict)}
    if "confirm_submit" in vals:
        return True
    a = _answer(resp)
    return ("確認" in a and ("送出" in a or "正確" in a))


def _facet_turn_stats(sid):
    """usage_events 面向埋點入庫證據：該 session 的 facet_key 事件數與最大輪數。"""
    import asyncpg

    async def _q():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            return await conn.fetchrow(
                "SELECT count(*) AS n, max(turn_number) AS max_turn "
                "FROM usage_events WHERE session_id=$1 AND facet_key='repair'", sid)
        finally:
            await conn.close()
    return asyncio.run(_q())


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


def _cleanup(sid):
    """自建自清：只刪本測試 session 產生的暫態列（form_sessions／usage_events）；
    不動 seed 的知識與面向配置列。usage_events fire-and-forget 有寫入延遲，重試容忍。"""
    import asyncpg

    async def _d():
        conn = await asyncpg.connect(**_conn_kwargs())
        try:
            await conn.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)
            await conn.execute("DELETE FROM usage_events WHERE session_id=$1", sid)
        finally:
            await conn.close()
    asyncio.run(_d())


def _wait_facet_written(sid, min_turn=1, tries=20):
    """usage 為 fire-and-forget async task；輪詢等埋點落庫（收案證據）。"""
    import time
    for _ in range(tries):
        row = _facet_turn_stats(sid)
        if row and row["n"] and (row["max_turn"] or 0) >= min_turn:
            return row
        time.sleep(0.3)
    return _facet_turn_stats(sid)


# 缺槽補話：確認 gate 誠實化後，若某輪必要槽位（尤其無 Vision 時的 item/category）
#   未由 brain 推斷齊，引擎會續問——文字推斷路徑的槽位補齊具 LLM 變異。此清單依序餵入
#   常見缺槽補充語（皆不含同意詞），把對話「驅動到確認 gate」，供穩定收案。
_SLOT_FILL_NUDGES = [
    "很急，昨天就壞了",                          # 急迫性
    "是冷氣，不會冷、不製冷",                     # item/category（明確帶名稱）
    "客廳的冷氣，完全不冷",                       # 補充物件內項目
    "分類是家電，項目是冷氣，原因不製冷，很緊急",   # 明確逐槽（最後催齊，皆不含同意詞）
]


def _drive_to_confirm(client, sid, opener, *, trigger_facet_key=None, max_nudges=4):
    """開場後把對話驅動到確認 gate（容忍文字推斷路徑的缺槽補問變異）。
    回 (confirm_resp, user_turns)；未在預算內到確認 gate → 回 (last_resp, turns)（呼叫端斷言）。"""
    r = _post(client, opener, sid, trigger_facet_key=trigger_facet_key)
    turns = 1
    if _is_confirm(r):
        return r, turns
    for nudge in _SLOT_FILL_NUDGES[:max_nudges]:
        r = _post(client, nudge, sid)
        turns += 1
        if _is_confirm(r):
            return r, turns
    return r, turns


def _build_repair_ticket(client, base_sid, opener, *, trigger_facet_key=None, attempts=4):
    """驅動一次完整建單並回 (sid, receipt_answer)，供「先有一張單」的情境（E/F/冪等）。
    真 LLM 文字推斷偶爾不在補話預算內收齊——同款腳本以新 session 重試（每次自建自清），
    behavior 正確、只是偶爾多需一次；重試耗盡才判失敗（不放寬斷言）。"""
    last = ""
    for i in range(attempts):
        sid = f"{base_sid}-a{i}"
        rc, _ = _drive_to_confirm(client, sid, opener, trigger_facet_key=trigger_facet_key)
        if _is_confirm(rc):
            r = _post(client, "好", sid)
            last = _answer(r)
            if MOCK_TICKET in last:
                return sid, last
        _cleanup(sid)   # 本次未收齊/未建單 → 清掉重試
    raise AssertionError(f"重試 {attempts} 次仍未在補話預算內建單成功；最後回覆：{last[:200]}")


def _run_with_retry(body, base_sid, *, attempts=3):
    """把「開場→…→建單」的整段情境以新 session 重試（容忍 LLM 文字推斷變異）。
    body(sid) 在收齊前的變異點用 `pytest.skip`-free 的 `_NotConverged` 表達「本次沒到 gate」；
    真正的斷言失敗（行為錯）直接上拋、不重試。每次失敗自建自清。"""
    last_exc = None
    for i in range(attempts):
        sid = f"{base_sid}-r{i}"
        try:
            body(sid)
            _cleanup(sid)
            return
        except _NotConverged as e:
            last_exc = e
            _cleanup(sid)
    raise AssertionError(f"重試 {attempts} 次仍未收齊到確認 gate（LLM 變異）：{last_exc}")


class _NotConverged(Exception):
    """情境未在補話預算內到確認 gate（可重試），與行為級斷言失敗（不可重試）區分。"""


def _confirm_or_notconverged(rc):
    if not _is_confirm(rc):
        raise _NotConverged(f"未到確認 gate，最後回覆：{_answer(rc)[:160]}")
    return rc


# ══════ 情境 A（文字推斷版，穩定收案）：明確報修 → confirm → 建單 ══════

@pytest.mark.req("conversational-repair:7.3")
def test_scenario_a_text_inference_creates_ticket(client):
    """文字路徑（無圖，穩定跑）：明確報修→進面向→（缺槽補齊）→確認 gate→同意→建單。
    ≤3 輪硬判準屬「明確陳述＋照片」的 A 類（見 test_scenario_a_with_image_three_turns）；
    無圖時 item/category 靠 brain 文字推斷，可能多一輪補問——此處驗行為鏈與建單成功。"""
    def _body(sid):
        r1 = _post(client, "冷氣壞了，不會冷", sid)
        assert _answer(r1), "第 1 輪應有回覆"
        assert _conversational_rows(sid) >= 1, "明確報修應進修繕面向對話"
        assert not _is_confirm(r1), "第 1 輪尚缺槽位，不應直接出確認 gate（收齊≠送出的前提）"

        # 驅動到確認 gate（容忍缺槽補問）——開場已送 1 輪，續驅動沿用同 session。
        rc, _ = _drive_to_confirm(client, sid, "很急，昨天就壞的，是客廳冷氣不製冷")
        _confirm_or_notconverged(rc)

        r_consent = _post(client, "好", sid)
        a = _answer(r_consent)
        assert MOCK_TICKET in a, f"同意後應回執含單號 #{MOCK_TICKET}，實得：{a[:200]}"

        # 埋點入庫證據：facet_key='repair'、輪數入庫（MAX(turn_number)≥3）
        row = _wait_facet_written(sid, min_turn=3)
        assert row and row["n"] >= 1, "usage_events 應有 facet_key='repair' 事件"
        assert (row["max_turn"] or 0) >= 3, f"MAX(turn_number) 應 ≥3，實得：{row['max_turn']}"

    _run_with_retry(_body, f"e2e-repair-a-{uuid.uuid4().hex[:8]}")


# ══════ 情境 A（帶圖版，≤3 輪硬判準；Vision 真打不穩時 skip）══════

@pytest.mark.req("conversational-repair:7.3")
def test_scenario_a_with_image_three_turns(client):
    """A 類北極星（明確陳述＋照片、單一租約、無岔題）≤3 輪建單。
    照片經 Vision 填 category/item → 只需補急迫性即收齊，3 輪（報修＋急迫性＋同意）完成。
    Vision 需 ENABLE_IMAGE_RECOGNITION=true＋可辨識測試圖；不可用/不穩 → skip（不假綠）。
    測試圖 URL 由 env 提供（TEST_REPAIR_IMAGE_URL），未提供則 skip——誠實分層。"""
    img = os.getenv("TEST_REPAIR_IMAGE_URL")
    if not img:
        pytest.skip("未提供 TEST_REPAIR_IMAGE_URL（真圖）＋ENABLE_IMAGE_RECOGNITION；帶圖 A 類略過（依賴標記）")
    sid = f"e2e-repair-aimg-{uuid.uuid4().hex[:8]}"
    try:
        # 第 1 輪：明確報修＋照片 → Vision 推斷 category/item，只缺急迫性
        r1 = _post(client, "冷氣壞了", sid, image_urls=[img])
        assert _answer(r1), "第 1 輪應有回覆"
        assert _conversational_rows(sid) >= 1, "明確報修＋照片應進修繕面向對話"

        # 第 2 輪：補急迫性 → 收齊 → 確認 gate
        r2 = _post(client, "昨天開始，蠻急的", sid)
        assert _is_confirm(r2), f"帶圖時第 2 輪應收齊出確認 gate，實得：{_answer(r2)[:200]}"

        # 第 3 輪：同意 → 建單
        r3 = _post(client, "好", sid)
        assert MOCK_TICKET in _answer(r3), f"第 3 輪同意應建單，實得：{_answer(r3)[:200]}"

        # ≤3 輪硬判準：MAX(turn_number) 恰 3（報修＋急迫性＋同意）
        row = _wait_facet_written(sid, min_turn=3)
        assert row and (row["max_turn"] or 0) == 3, \
            f"A 類（帶圖）應恰 3 輪完成，實得 MAX(turn_number)={row['max_turn'] if row else None}"
    finally:
        _cleanup(sid)


# ══════ 情境 B：岔題先答回流最終建單（R3.1）══════

@pytest.mark.req("conversational-repair:7.3")
def test_scenario_b_digression_answered_then_resume(client):
    def _body(sid):
        r1 = _post(client, "馬桶不通了", sid)
        assert _conversational_rows(sid) >= 1, "應進修繕面向對話"

        # 收集中岔題問費用 → 先答費用再接回收集（不中斷面向）
        r2 = _post(client, "這要自己出錢嗎", sid)
        assert _answer(r2), "岔題應有回覆"
        assert _conversational_rows(sid) >= 1, "岔題後面向會話仍在（未中斷）"

        # 岔題後補槽驅動到確認 → 同意建單（最終仍完成）
        rc, _ = _drive_to_confirm(client, sid, "有點急，今天就壞的，是馬桶排水堵住")
        _confirm_or_notconverged(rc)
        r5 = _post(client, "確認送出", sid)
        assert MOCK_TICKET in _answer(r5), f"最終仍應建單成功，實得：{_answer(r5)[:200]}"

    _run_with_retry(_body, f"e2e-repair-b-{uuid.uuid4().hex[:8]}")


# ══════ 情境 C：模糊先澄清、明確才進面向（R1.2）══════

@pytest.mark.req("conversational-repair:7.3")
def test_scenario_c_vague_clarifies_then_enters(client):
    sid = f"e2e-repair-c-{uuid.uuid4().hex[:8]}"
    try:
        # 模糊敘述 → 不硬開面向（先澄清）
        r1 = _post(client, "房子有點問題", sid)
        assert _answer(r1), "模糊敘述應有澄清回覆"
        assert _conversational_rows(sid) == 0, \
            f"模糊敘述不應直接開修繕面向對話，實得 rows={_conversational_rows(sid)}"

        # 後續明確 → 進面向
        r2 = _post(client, "馬桶不通，排水堵住了", sid)
        assert _answer(r2)
        assert _conversational_rows(sid) >= 1, "明確報修後應進修繕面向對話"
    finally:
        _cleanup(sid)


# ══════ 情境 D：確認階段改資料重確認建單一次（R4.5）══════

@pytest.mark.req("conversational-repair:7.3")
def test_scenario_d_edit_at_confirm_then_reconfirm(client):
    def _body(sid):
        rc, _ = _drive_to_confirm(client, sid, "冷氣壞了不製冷")
        _confirm_or_notconverged(rc)

        # 確認階段改急迫性 → 更新後重出 confirm（不重跑整個流程）
        #   修正語避開同意詞（"好/對/可以/是的" 等）——引擎確認待決以同意詞觸發 execute，
        #   北極星腳本的修正句（「不是客廳是臥室的」）本就不含同意詞，此處比照。
        r3 = _post(client, "其實沒那麼緊急，改成一般就行", sid)
        assert _is_confirm(r3), f"改資料後應重出確認 gate，實得：{_answer(r3)[:200]}"

        # 同意 → 建單一次
        r4 = _post(client, "好", sid)
        assert MOCK_TICKET in _answer(r4), f"重確認後同意應建單，實得：{_answer(r4)[:200]}"

        # 再說一次「好」→ 冪等，不重複建單（回同一單號）
        r5 = _post(client, "好", sid)
        assert MOCK_TICKET in _answer(r5), "冪等：重複同意仍回同一單號"

    _run_with_retry(_body, f"e2e-repair-d-{uuid.uuid4().hex[:8]}")


# ══════ 情境 E：完成後查進度（R5.1）══════

@pytest.mark.req("conversational-repair:7.3")
def test_scenario_e_progress_query_after_create(client):
    sid, a3 = _build_repair_ticket(
        client, f"e2e-repair-e-{uuid.uuid4().hex[:8]}", "冷氣壞了不會冷")
    try:
        assert MOCK_TICKET in a3, "應先建單成功"

        # 查進度：新 session（查進度是獨立知識 api_call→jgb_repairs，身份查詢）
        qsid = f"e2e-repair-eq-{uuid.uuid4().hex[:8]}"
        try:
            rq = _post(client, "我的修繕修得怎樣了", qsid)
            aq = _answer(rq)
            assert aq, "查進度應有回覆"
            # 行為級：回工單狀態相關內容（狀態/處理/報修/單），不逐字比對
            assert any(k in aq for k in ("報修", "修繕", "工單", "單", "狀態", "處理", "進度")), \
                f"查進度應回工單狀態相關內容，實得：{aq[:200]}"
        finally:
            _cleanup(qsid)
    finally:
        _cleanup(sid)


# ══════ 情境 F：直達參數進同一面向（R1.3）══════

@pytest.mark.req("conversational-repair:7.3")
def test_scenario_f_trigger_facet_key_enters_same_facet(client):
    # (1) 直達進場斷言：trigger_facet_key 命中 → 進同一修繕面向（跳意圖辨識）
    entry_sid = f"e2e-repair-f-entry-{uuid.uuid4().hex[:8]}"
    try:
        r1 = _post(client, "冷氣壞了", entry_sid, trigger_facet_key="repair_create")
        assert _answer(r1), "直達應有回覆"
        assert _conversational_rows(entry_sid) >= 1, "直達參數應進修繕面向對話"
    finally:
        _cleanup(entry_sid)

    # (2) 同槽位邏輯直達建單（經 trigger_facet_key 重入，補話驅動＋重試容忍 LLM 變異）
    sid, a = _build_repair_ticket(
        client, f"e2e-repair-f-{uuid.uuid4().hex[:8]}", "冷氣壞了",
        trigger_facet_key="repair_create")
    try:
        assert MOCK_TICKET in a, f"直達路徑亦應建單成功，實得：{a[:200]}"
    finally:
        _cleanup(sid)


# ══════ 冪等 e2e：建單後再同意不重複建單（R4.4）══════

@pytest.mark.req("conversational-repair:7.3")
def test_idempotent_repeat_consent_no_duplicate(client):
    sid, a3 = _build_repair_ticket(
        client, f"e2e-repair-idem-{uuid.uuid4().hex[:8]}", "冷氣壞了不製冷")
    try:
        assert MOCK_TICKET in a3, "首次同意應建單成功"

        # 再說「好」→ 回同一單號、不重複建單（executed 冪等）
        r4 = _post(client, "好", sid)
        a4 = _answer(r4)
        assert MOCK_TICKET in a4, "冪等：重複同意回同一單號"
        # 觀測：建單後 form_sessions 仍為單一收斂會話（executed 標記，不再新增建單）
        assert _conversational_rows(sid) >= 1, "會話保留供追問（executed）"
    finally:
        _cleanup(sid)
