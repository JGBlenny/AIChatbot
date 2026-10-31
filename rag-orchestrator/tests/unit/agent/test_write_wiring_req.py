"""unit：寫入改接片（plan-write-wiring-20261031 §3、W1～W8；驗收清單 §5.1 A1～A6）。

離線：真 `JGBSystemAPI`＋替身（`assistant_demo_vendor4.json`）、`httpx.MockTransport` 包的
`RealHttpTransport`、假 registry／假 pool。⛔ 不接觸任何 jgbsmart.com 主機（A7 staging 實打由主會話跑）。

「接真 JGB」的模擬：API 以替身模式建構後改成 `use_mock=False`，`_real_transport` 換成
`RecordingTransport(替身)`——請求走真 JGB 分支（`_send` 的 real 路徑），出向參數被記錄，
回應由替身照 staging `544e8592eb` 的形狀產生。

期望值由測試自己寫死：staging 白名單照抄 jgb2 `origin/staging` `544e8592eb`
（`EstateController::STORE_FIELDS`、`ContractController::STORE_FIELDS`、`BillController::MANUAL_FIELDS`／
`DUE_FIELDS`、`RepairController::STORE_FIELDS`、`ExternalWriteGuard::ALWAYS_ALLOWED_FIELDS`），⛔ 引用被測物常數當期望。
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
import re
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from PIL import Image

from services import jgb_system_api as api_mod
from services.agent import confirm_card as CC
from services.agent import mcp_facade as F
from services.agent import runtime as runtime_mod
from services.agent.identity import Identity
from services.agent.runtime import PENDING_CONFIRM_KEY
from services.agent.tools import action as action_tools
from services.agent.tools import confirm as confirm_mod
from services.agent.tools import jgb2 as jgb2_tools
from services.agent.tools.confirm import confirm_request
from services.agent.tools.registry import ToolRegistry, ToolResult
from services.jgb import bills as _bills
from services.jgb import fixture_store
from services.jgb import transport as T
from services.jgb.transport import RealHttpTransport, RecordingTransport

from tests.unit.agent.confirm_pool_double import attach_token_tx
from tests.unit.agent.test_runtime_confirm_segment_req import (
    _PID,
    FakePool,
    _identity as _seg_identity,
    _redeem_row,
    _state_with_pending,
)
from tests.unit.agent.test_runtime_req import (
    FakeAssembler,
    FakeClock,
    FakeRegistry,
    FakeVerifier,
    _empty_provider,
)
from services.agent.budget import Budget
from services.agent.runtime import AgentRuntime

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("agentic-mcp-orchestration:R4.2"),
]

FIXTURE = (Path(__file__).resolve().parents[3]
           / "services" / "jgb" / "fixture_data" / "assistant_demo_vendor4.json")
ROLE, OWNER = "20151", "12291"
TODAY = date(2026, 10, 15)
#: fixture 人工查證：68926「測試物件」僅 12291 可見、唯一有效合約 89481。
ESTATE_A_TITLE, ESTATE_A, CONTRACT_A = "測試物件", 68926, 89481
#: fixture 人工查證：帳單 769258 status=1（待發送）、date_expire=20270614、僅 12291 可見；
#: 帳單 769246 status=16（非待發送）、date_expire=20260801、僅 12291 可見。
BILL_DRAFT, BILL_DRAFT_EXPIRE = "769258", "20270614"
BILL_NOT_DRAFT, BILL_NOT_DRAFT_EXPIRE = "769246", "20260801"

#: staging `544e8592eb` 白名單（逐字照抄，見檔頭）。
STAGING_ALWAYS = frozenset({"role_id", "viewer_user_id", "idempotency_key"})
STAGING_ESTATE = frozenset({"title", "city", "district", "address", "use_for", "space_type",
                            "building", "room_count", "size", "rent", "floor"})
STAGING_CONTRACT = frozenset({"estate_id", "date_start", "date_end", "rent", "to_user_email",
                              "to_user_phone", "deposit_amount", "title"})
STAGING_MANUAL_BILL = frozenset({"contract_id", "title", "total", "date_expire", "sub_title"})
STAGING_DUE = frozenset({"date_expire"})
STAGING_REPAIR = frozenset({"estate_id", "category_id", "item_id", "broken_reason", "broken_note",
                            "broken_photos", "emergency_status", "contract_id", "to_user_note"})

UNCONFIRMED_SENTENCE = "結果未確認，請到 JGB 畫面確認是否已建立，再決定要不要重送"


# ═══ 共用 fixture ════════════════════════════════════════════════════════════
@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(_bills, "_today", lambda: TODAY)
    monkeypatch.delenv(api_mod.JGB_WRITE_WIRING_ENV, raising=False)
    monkeypatch.delenv("MOCK_FAIL_NEXT_WRITE", raising=False)
    monkeypatch.delenv("JGB_MOCK_WRITE_LOG", raising=False)
    monkeypatch.setenv("AGENT_ASSISTANT_KEY_IDS", "1")


def _load_fixture(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.setattr(fixture_store, "_DATA", fixture_store._DATA)   # monkeypatch 負責還原
    fixture_store.load_from(FIXTURE)


@pytest.fixture()
def mock_api(monkeypatch):
    """替身模式的真 `JGBSystemAPI`（開關由各測試設 `write_wiring`）。"""
    _load_fixture(monkeypatch)
    a = api_mod.JGBSystemAPI()
    a._mock_transport = RecordingTransport(a._mock_transport)
    monkeypatch.setattr(jgb2_tools, "_api_singleton", a)
    return a


@pytest.fixture()
def real_api(monkeypatch):
    """「接真 JGB」：`use_mock=False`，real transport＝`RecordingTransport(替身)`；替身路徑拔掉（走錯就炸）。"""
    _load_fixture(monkeypatch)
    a = api_mod.JGBSystemAPI()
    inner = a._mock_transport
    a.use_mock = False
    a._mock_transport = None
    a._real_transport = RecordingTransport(inner)
    a.write_wiring = True
    monkeypatch.setattr(jgb2_tools, "_api_singleton", a)
    return a


def _pm(**over) -> Identity:
    base = dict(vendor_id=4, target_user="property_manager", mode="b2b", role_id=ROLE,
                user_id=OWNER, session_id="mcp:1:4:ww", api_key_id=1, entry="mcp")
    base.update(over)
    return Identity(**base)


def _pool():
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value="INSERT 0 1")
    return attach_token_tx(pool)


def _registry() -> ToolRegistry:
    reg = ToolRegistry(write_tools_enabled=True, redeem_checker=AsyncMock(return_value=True))
    for spec, fn in action_tools.ACTION_SPECS:
        reg.register(spec, fn)
    return reg


async def _execute(payload: dict, *, token: str = "tok-ww", identity: Identity = None) -> ToolResult:
    return await _registry().call(identity or _pm(), f"jgb2.action.{payload['action']}",
                                  {"payload": payload, "confirmation_token": token},
                                  timeout_s=5, stage="M1", for_model=True)


async def _card(payload: dict) -> ToolResult:
    return await confirm_request(
        _pm(), {"summary": "確認", "payload": json.dumps(payload, ensure_ascii=False)},
        db_pool=_pool())


def _writes(rec: RecordingTransport) -> list:
    return [(i, m, p) for i, (m, p, _q) in enumerate(rec.calls) if m in ("POST", "PATCH")]


def _estate_payload() -> dict:
    return {"action": "estate_create", "title": "幸福小窩", "city": "台北市", "district": "信義區",
            "address": "松仁路100號5樓", "use_for": "residential", "rent": 18000}


def _contract_payload() -> dict:
    return {"action": "contract_create", "estate_name": ESTATE_A_TITLE, "date_start": "20261101",
            "date_end": "20271031", "rent": 18000, "to_user_phone": "0912345678"}


def _bill_payload() -> dict:
    return {"action": "manual_bill_create", "contract_ref": str(CONTRACT_A), "title": "清潔費",
            "total": 1500, "date_expire": "20261031"}


def _due_payload(bill_id: str = BILL_DRAFT, before: str = BILL_DRAFT_EXPIRE,
                 after: str = "20270617") -> dict:
    return {"action": "bill_due_extend", "bill_id": bill_id, "date_expire_before": before,
            "days": 3, "date_expire_after": after}


def _jpeg(color=(120, 140, 160)) -> bytes:
    img = Image.new("RGB", (64, 48), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


async def _card_photos(ident: Identity) -> list:
    """把一張 JPEG 放進暫存並重新編碼成卡上照片中繼資料（同 UD-3 測試的做法）。"""
    from services.agent import upload_store as U
    from services.agent.runtime import _encode_card_photos

    binding = U.binding_from_identity(ident, "repair")
    handle = U.STORE.verify_ticket(U.STORE.issue_ticket(binding).upload_token)
    blob = _jpeg()
    up = U.STORE.add_upload(handle, content_type="image/jpeg", data=blob)
    U.STORE.end_turn([c.ref for c in U.STORE.claim([up.upload_id], binding)])
    return await _encode_card_photos(ident, [F._photo_meta(blob, "jpeg", 1)])


# ═══ A1：開關預設 off（既有測試全套跑在 off）══════════════════════════════════
def test_a1_default_env_is_off(monkeypatch):
    """A1：env 未設 ⇒ `write_wiring is False`——既有單元全套因此全部跑在 off；
    A1 的主證據是單元全套輸出檔（失敗集合＝改前 9 筆基準），本測試只證「預設就是 off」。"""
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    assert api_mod.JGBSystemAPI().write_wiring is False
    monkeypatch.setenv("USE_MOCK_JGB_API", "false")
    monkeypatch.setenv("JGB_API_KEY", "unit-test-placeholder")
    monkeypatch.setenv("JGB_API_BASE_URL", "https://staging.jgbsmart.com")
    real = api_mod.JGBSystemAPI()
    assert real.write_wiring is False and real._real_transport.write_wiring is False


# ═══ A2：開關讀值、host 限制、各閘門點 on/off ══════════════════════════════════
@pytest.mark.parametrize("raw", [None, "", "ON", "On", "1", "true", "yes", "off", "on1", "o n"])
def test_a2_switch_only_exact_on_counts(monkeypatch, raw):
    """A2：只收 `on`（去空白後逐字相等）；其他值、未設 ⇒ off（fail-closed）。"""
    if raw is None:
        monkeypatch.delenv(api_mod.JGB_WRITE_WIRING_ENV, raising=False)
    else:
        monkeypatch.setenv(api_mod.JGB_WRITE_WIRING_ENV, raw)
    assert api_mod._write_wiring_from_env("https://staging.jgbsmart.com", True) is False
    assert api_mod._write_wiring_from_env("https://staging.jgbsmart.com", False) is False


@pytest.mark.parametrize("raw", ["on", " on ", "on\n"])
def test_a2_switch_on_with_mock_or_staging(monkeypatch, raw):
    """A2 正對照：`on`（含前後空白）＋替身模式 ⇒ on；＋staging 主機 ⇒ on。"""
    monkeypatch.setenv(api_mod.JGB_WRITE_WIRING_ENV, raw)
    assert api_mod._write_wiring_from_env("https://www.jgbsmart.com", True) is True
    assert api_mod._write_wiring_from_env("https://staging.jgbsmart.com", False) is True
    assert api_mod._write_wiring_from_env("https://STAGING.jgbsmart.com/", False) is True


@pytest.mark.parametrize("url", [
    "https://www.jgbsmart.com",
    "https://preview.jgbsmart.com",
    "https://staging.jgbsmart.com.evil.example",
    "https://evil.example/staging.jgbsmart.com",
    "https://staging-jgbsmart.com",
    "",
    "not a url",
])
def test_a2_switch_on_but_not_staging_host_is_off_with_warning(monkeypatch, caplog, url):
    """A2：開關 on 但 base URL 主機不是 staging（例：www）⇒ off，記一行警告；警告 ⛔ 印 URL 全文。"""
    monkeypatch.setenv(api_mod.JGB_WRITE_WIRING_ENV, "on")
    with caplog.at_level(logging.WARNING, logger=api_mod.logger.name):
        assert api_mod._write_wiring_from_env(url, False) is False
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    if url:
        assert url not in caplog.text


def test_a2_constructor_stores_one_value_and_passes_it_to_real_transport(monkeypatch):
    """A2：建構時只讀一次，存成 `write_wiring`，同一個值傳給 `RealHttpTransport`；www ⇒ 兩者皆 off。"""
    monkeypatch.setenv(api_mod.JGB_WRITE_WIRING_ENV, "on")
    monkeypatch.setenv("USE_MOCK_JGB_API", "false")
    monkeypatch.setenv("JGB_API_KEY", "unit-test-placeholder")
    monkeypatch.setenv("JGB_API_BASE_URL", "https://www.jgbsmart.com")
    www = api_mod.JGBSystemAPI()
    assert www.write_wiring is False and www._real_transport.write_wiring is False
    monkeypatch.setenv("JGB_API_BASE_URL", "https://staging.jgbsmart.com")
    stg = api_mod.JGBSystemAPI()
    assert stg.write_wiring is True and stg._real_transport.write_wiring is True
    # 建構後改 env ⇒ 不影響已建好的物件（只讀一次）
    monkeypatch.setenv(api_mod.JGB_WRITE_WIRING_ENV, "")
    assert stg.write_wiring is True


@pytest.mark.parametrize("action", sorted(confirm_mod.WRITE_NOT_SUPPORTED_ACTIONS))
def test_a2_confirm_gate_on_off(monkeypatch, action):
    """A2（`confirm.py` 閘門）：接真 JGB＋off ⇒ 照舊「尚未開放」；on ⇒ 不攔；非布林真值 ⇒ 當 off；替身模式 ⇒ 不攔。"""
    def api(**kw):
        monkeypatch.setattr(jgb2_tools, "_api_singleton", SimpleNamespace(**kw))

    api(use_mock=False, write_wiring=False)
    assert confirm_mod._write_not_supported(action) is True
    api(use_mock=False)                                    # 缺屬性 ⇒ off
    assert confirm_mod._write_not_supported(action) is True
    api(use_mock=False, write_wiring="true")               # 非布林 ⇒ off（fail-closed）
    assert confirm_mod._write_not_supported(action) is True
    api(use_mock=False, write_wiring=True)
    assert confirm_mod._write_not_supported(action) is False
    api(use_mock=True, write_wiring=False)                 # 替身：與改動前相同，不攔
    assert confirm_mod._write_not_supported(action) is False


def test_a2_confirm_has_no_raw_use_mock_gate_left():
    """A2（靜態）：`confirm.py` 每一處「接真 JGB」判斷都同時看開關——原始碼裡的
    `use_mock ... is False` 判斷後面緊接 `not write_wiring_on()`。正對照：至少找得到一處。"""
    src = Path(confirm_mod.__file__).read_text(encoding="utf-8")
    needle = 'getattr(jgb2_tools._get_api(), "use_mock", True) is False'
    spots = [m.start() for m in re.finditer(re.escape(needle), src)]
    assert spots, "正對照：判斷式應該找得到"
    for pos in spots:
        assert "not write_wiring_on()" in src[pos: pos + len(needle) + 80], src[pos: pos + 200]
    assert "_write_not_supported(" in src


async def test_a2_assistant_write_off_sends_nothing_on_sends(real_api):
    """A2（`_assistant_write`）：接真 JGB＋off ⇒ 不發請求（降級回應）；on ⇒ 送出 `POST /estates`。"""
    rec = real_api._real_transport
    fields = {k: v for k, v in _estate_payload().items() if k != "action"}
    real_api.write_wiring = False
    off = await real_api.assistant_create_estate(ROLE, OWNER, dict(fields), idempotency_key="k1")
    assert off.get("success") is not True and not _writes(rec)
    real_api.write_wiring = True
    on = await real_api.assistant_create_estate(ROLE, OWNER, dict(fields), idempotency_key="k2")
    assert on.get("success") is True
    assert [(m, p) for _i, m, p in _writes(rec)] == [("POST", "/api/external/v1/estates")]


async def test_a2_create_repair_off_json_on_multipart(real_api):
    """A2（`create_repair`）：接真 JGB＋off ⇒ JSON、⛔ 送檔；on ⇒ multipart `broken_photos[]`。"""
    rec = real_api._real_transport
    photo = [("photo-1.jpg", _jpeg(), "image/jpeg")]

    async def send():
        return await real_api.create_repair(ROLE, ESTATE_A, 1, 1, "冷氣不冷", user_id=OWNER,
                                            photo_files=photo, idempotency_key="k-r")

    real_api.write_wiring = False
    await send()
    assert rec.files[-1] is None and rec.calls[-1][:2] == ("POST", "/api/external/v1/repairs")
    real_api.write_wiring = True
    await send()
    assert rec.calls[-1][:2] == ("POST", "/api/external/v1/repairs")
    assert [(f[0], f[1], f[2]) for f in rec.files[-1]] == [("broken_photos[]", "photo-1.jpg", "image/jpeg")]


async def test_a2_patch_due_off_no_send_on_new_path(real_api, mock_api):
    """A2（`agent_patch_bill_due_date`）：接真 JGB＋off ⇒ 不發請求；on ⇒ `PATCH /api/external/v1/bills/{id}`。
    替身模式＋off ⇒ 照舊打 `/agent/v1/bills/{id}`（off 等價）。"""
    rec = real_api._real_transport
    real_api.write_wiring = False
    off = await real_api.agent_patch_bill_due_date(BILL_DRAFT, "2027-06-17", idempotency_key="k",
                                                   role_id=ROLE, user_id=OWNER)
    assert off.get("success") is not True and not _writes(rec)
    real_api.write_wiring = True
    on = await real_api.agent_patch_bill_due_date(BILL_DRAFT, "2027-06-17", idempotency_key="k",
                                                  role_id=ROLE, user_id=OWNER)
    assert on.get("success") is True
    assert [(m, p) for _i, m, p in _writes(rec)] == [("PATCH", f"/api/external/v1/bills/{BILL_DRAFT}")]

    mock_api.write_wiring = False
    await mock_api.agent_patch_bill_due_date(BILL_DRAFT, "2027-06-17", idempotency_key="k",
                                             role_id=ROLE, user_id=OWNER)
    assert mock_api._mock_transport.calls[-1][:2] == ("PATCH", f"/agent/v1/bills/{BILL_DRAFT}")


async def test_a2_action_repair_photo_gate_on_off(real_api, monkeypatch):
    """A2（`action.repair_create` 閘門）：接真 JGB＋off ⇒ 照片不驗、不送（照舊文字單）；on ⇒ 驗暫存位元組。"""
    from services.agent import upload_store as U

    U.STORE.reset()
    try:
        ident = _pm()
        photos = await _card_photos(ident)
        payload = {"action": "repair_create", "estate_name": ESTATE_A_TITLE, "description": "椅面破了",
                   "broken_photos": photos}
        U.STORE.reset()                                       # 暫存清空：on 會擋、off 不看
        rec = real_api._real_transport
        real_api.write_wiring = False
        off = await _execute(payload, token="tok-off")
        assert off.ok, off
        assert rec.files[-1] is None
        n = len(_writes(rec))
        real_api.write_wiring = True
        on = await _execute(payload, token="tok-on")
        assert (on.ok, on.error) == (False, "INVALID_INPUT")
        assert on.data.get(CC.PHOTOS_UNAVAILABLE_KEY) is True
        assert len(_writes(rec)) == n, "暫存缺照片 ⇒ ⛔ 寫入"
    finally:
        U.STORE.reset()


# ═══ A3：on 時五項送出的 method／路徑／body 鍵 ════════════════════════════════
def test_a3_mock_body_whitelists_equal_staging():
    """A3（W3 替身同步）：替身各寫入端點收的鍵＝staging 白名單＋身分鍵＋冪等鍵（修繕替身比 staging 窄，⛔ 寬）。"""
    M = T.JGBMockTransport
    assert M._ESTATE_BODY_KEYS == STAGING_ESTATE | STAGING_ALWAYS
    assert M._CONTRACT_BODY_KEYS == STAGING_CONTRACT | STAGING_ALWAYS
    assert M._BILL_BODY_KEYS == STAGING_MANUAL_BILL | STAGING_ALWAYS
    assert M._ASSISTANT_DUE_BODY_KEYS == STAGING_DUE | STAGING_ALWAYS
    assert M._REPAIR_BODY_KEYS <= STAGING_REPAIR | STAGING_ALWAYS
    for keys in (M._ESTATE_BODY_KEYS, M._CONTRACT_BODY_KEYS, M._BILL_BODY_KEYS,
                 M._ASSISTANT_DUE_BODY_KEYS, M._REPAIR_BODY_KEYS):
        assert "confirmation_token" not in keys


def test_a3_photo_policy_matches_staging():
    """A3（W3）：替身照片政策＝staging（JPEG/PNG、≤ 5,000,000 bytes）。"""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    policy = json.dumps(data, ensure_ascii=False)
    assert '"max_bytes": 5000000' in policy
    found = []

    def walk(node):
        if isinstance(node, dict):
            if "photo_policy" in node:
                found.append(node["photo_policy"])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    assert found, "正對照：fixture 應該有 photo_policy"
    for p in found:
        assert p["max_bytes"] == 5_000_000
        assert sorted(p["content_types"]) == ["image/jpeg", "image/png"]


def _assert_body(body: dict, allowed: frozenset, token: str) -> None:
    assert set(body) <= allowed | STAGING_ALWAYS, set(body) - (allowed | STAGING_ALWAYS)
    assert body["role_id"] == ROLE and body["viewer_user_id"] == OWNER
    assert body["idempotency_key"] == token
    assert "confirmation_token" not in body


@pytest.mark.parametrize("factory,path,allowed", [
    (_estate_payload, "/api/external/v1/estates", STAGING_ESTATE),
    (_contract_payload, "/api/external/v1/contracts", STAGING_CONTRACT),
    (_bill_payload, "/api/external/v1/bills/manual", STAGING_MANUAL_BILL),
])
async def test_a3_closed_actions_send_staging_shape(real_api, factory, path, allowed):
    """A3：on＋接真 JGB——建物件／合約／手動帳單出卡成功、兌現送出 `POST <staging 路徑>`，
    body 鍵 ⊆ staging 白名單＋身分鍵＋冪等鍵（冪等鍵＝確認 token），⛔ `confirmation_token`。"""
    card = await _card(factory())
    assert card.ok and not (card.data or {}).get("not_supported"), card
    rec = real_api._real_transport
    res = await _execute(card.data["payload"], token="tok-a3")
    assert res.ok, res
    writes = _writes(rec)
    assert [(m, p) for _i, m, p in writes] == [("POST", path)]
    _assert_body(rec.bodies[writes[0][0]], allowed, "tok-a3")


async def test_a3_due_extend_sends_patch_with_only_date_expire(real_api):
    """A3：on＋接真 JGB——改到期日送 `PATCH /api/external/v1/bills/{id}`，body 鍵＝{date_expire}＋身分＋冪等鍵；
    回執 `after` 取 staging 回應的 `date_expire`（整數 YYYYMMDD），`before` 取卡上值。"""
    rec = real_api._real_transport
    res = await _execute(_due_payload(), token="tok-due")
    assert res.ok, res
    writes = _writes(rec)
    assert [(m, p) for _i, m, p in writes] == [("PATCH", f"/api/external/v1/bills/{BILL_DRAFT}")]
    body = rec.bodies[writes[0][0]]
    assert set(body) == STAGING_DUE | STAGING_ALWAYS
    assert body["date_expire"] == "2027-06-17"
    _assert_body(body, STAGING_DUE, "tok-due")
    assert res.data["receipt"] == {"bill_id": BILL_DRAFT, "before": "2027-06-14", "after": "2027-06-17"}


@pytest.mark.parametrize("bad", ["769258/1", "abc", "１２３", " ", "769258?x=1"])
async def test_a3_non_numeric_bill_id_is_never_sent(real_api, bad):
    """A3：`bill_id` 送出前必須是純 ASCII 數字，否則不發請求。"""
    rec = real_api._real_transport
    resp = await real_api.agent_patch_bill_due_date(bad, "2027-06-17", idempotency_key="k",
                                                    role_id=ROLE, user_id=OWNER)
    assert resp.get("success") is not True and not _writes(rec)


async def test_a3_repair_with_photo_sends_card_bytes_multipart(real_api):
    """A3：on＋接真 JGB——修繕附照片 ⇒ multipart `broken_photos[]`，位元組 sha256＝卡上值；
    表單欄位鍵 ⊆ staging 白名單＋身分鍵＋冪等鍵、⛔ 夾帶照片中繼資料。"""
    from services.agent import upload_store as U

    U.STORE.reset()
    try:
        ident = _pm()
        photos = await _card_photos(ident)
        payload = {"action": "repair_create", "estate_name": ESTATE_A_TITLE, "description": "椅面破了",
                   "broken_photos": photos}
        rec = real_api._real_transport
        res = await _execute(payload, token="tok-photo", identity=ident)
        assert res.ok, res
        writes = _writes(rec)
        assert [(m, p) for _i, m, p in writes] == [("POST", "/api/external/v1/repairs")]
        idx = writes[0][0]
        files = rec.files[idx]
        assert [(f[0], f[1], f[2]) for f in files] == [("broken_photos[]", "photo-1.jpg", "image/jpeg")]
        assert hashlib.sha256(files[0][3]).hexdigest() == photos[0]["sha256"]
        form = rec.bodies[idx]
        assert "broken_photos" not in form
        _assert_body(form, STAGING_REPAIR, "tok-photo")
    finally:
        U.STORE.reset()


async def test_a3_repair_photo_missing_from_cache_is_not_written(real_api):
    """A3：on＋接真 JGB——暫存裡沒有卡上照片 ⇒ `photos_unavailable`、⛔ 寫入、⛔ 改成不附照片照送。"""
    from services.agent import upload_store as U

    U.STORE.reset()
    try:
        ident = _pm()
        photos = await _card_photos(ident)
        U.STORE.reset()
        rec = real_api._real_transport
        res = await _execute({"action": "repair_create", "estate_name": ESTATE_A_TITLE,
                              "description": "椅面破了", "broken_photos": photos},
                             token="tok-gone", identity=ident)
        assert (res.ok, res.error) == (False, "INVALID_INPUT")
        assert res.data.get(CC.PHOTOS_UNAVAILABLE_KEY) is True
        assert not _writes(rec)
    finally:
        U.STORE.reset()


# ═══ A4：JGB 拒絕 ⇒ 程式固定句（封閉白名單）══════════════════════════════════
def _real_transport_with(handler, seen_timeouts: list = None) -> RealHttpTransport:
    t = RealHttpTransport("https://staging.jgbsmart.com", "unit-test-placeholder", 10.0,
                          write_wiring=True)

    def client(timeout):
        if seen_timeouts is not None:
            seen_timeouts.append(timeout)
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=timeout)

    t._client = client
    return t


def _our_log_text(caplog) -> str:
    """本系統 logger 的紀錄（排除 httpx 函式庫自己的 INFO 請求行——那是既有讀取路徑也有的函式庫行為，不在本片範圍）。"""
    return "\n".join(r.getMessage() for r in caplog.records if not r.name.startswith(("httpx", "httpcore")))


def _concrete(template: str) -> tuple:
    if "{bill_id}" in template:
        return "PATCH", template.replace("{bill_id}", BILL_DRAFT)
    return "POST", template


def _json_error(status: int, message: str):
    def handler(request):
        return httpx.Response(status, json={"success": False, "error": {"code": status, "message": message}})
    return handler


def test_a4_codes_and_texts_are_one_closed_set():
    """A4：transport 錯誤碼值域＝runtime 固定句表的鍵；白名單每句的固定句＝「這筆操作沒有完成：」＋staging 原句＋「。」；
    `unconfirmed`／`failed` 各自對到既定句子；固定句 ⛔ 有插值。"""
    assert set(T.WRITE_RESULT_CODES) == set(CC.WRITE_RESULT_TEXTS)
    for (_tpl, _status, message), code in T.WRITE_REJECTION_WHITELIST.items():
        assert CC.WRITE_RESULT_TEXTS[code] == f"這筆操作沒有完成：{message}。"
    assert CC.WRITE_RESULT_TEXTS[CC.WRITE_RESULT_UNCONFIRMED] == UNCONFIRMED_SENTENCE
    assert CC.WRITE_RESULT_TEXTS[CC.WRITE_RESULT_FAILED] == CC.ACTION_FAILED_TEXT
    for text in CC.WRITE_RESULT_TEXTS.values():
        assert "{" not in text and "%" not in text
    assert len(T.WRITE_REJECTION_WHITELIST) == 15        # 14 句（訂閱句兩個端點各一列）


@pytest.mark.parametrize("entry", sorted(T.WRITE_REJECTION_WHITELIST), ids=lambda e: f"{e[0]}-{e[1]}")
async def test_a4_whitelisted_rejection_maps_to_fixed_sentence(entry, caplog):
    """A4：白名單內每一句（端點、狀態碼、全文相符）⇒ 對應錯誤碼 ⇒ 固定句；回應訊息換成固定句；
    log 只有樣板與錯誤碼、⛔ JGB 訊息全文（正對照：樣板與錯誤碼有出現在 log）。"""
    template, status, message = entry
    code = T.WRITE_REJECTION_WHITELIST[entry]
    method, path = _concrete(template)
    t = _real_transport_with(_json_error(status, message))
    with caplog.at_level(logging.DEBUG):
        resp = await t.send(method, path, data={"role_id": ROLE, "viewer_user_id": OWNER})
        result = action_tools._write_failed(SimpleNamespace(write_wiring=True), resp, "unit")
    assert resp["success"] is False
    assert resp["error"]["reason"] == code
    assert resp["error"]["message"] == T.FALLBACK_MESSAGE
    assert (result.ok, result.error) == (False, "NO_MATCH")
    assert result.data == {CC.WRITE_RESULT_KEY: code}
    assert result.text_for_model in (None, "")
    assert CC.WRITE_RESULT_TEXTS[code] != CC.ACTION_FAILED_TEXT
    ours = _our_log_text(caplog)
    assert message not in caplog.text and message not in json.dumps(resp, ensure_ascii=False)
    assert template in ours and code in ours                          # 正對照


_OUTSIDE = [
    # 金鑰層／身分層（ExternalWriteGuard 類訊息）、404 折疊、欄位插值句、白名單句配錯端點或狀態碼、字面不全相符
    ("POST", "/api/external/v1/estates", 401, "API Key 無效"),
    ("POST", "/api/external/v1/estates", 403, "此金鑰不可使用查詢參數"),
    ("POST", "/api/external/v1/contracts", 400, "role_id 與 viewer_user_id 為必填"),
    ("POST", "/api/external/v1/contracts", 422, "不允許的欄位"),
    ("POST", "/api/external/v1/bills/manual", 422, "歸屬欄位由登入身分決定"),
    ("PATCH", f"/api/external/v1/bills/{BILL_DRAFT}", 404, "資源不存在或無權存取"),
    ("POST", "/api/external/v1/estates", 400, "title 格式不正確"),
    ("POST", "/api/external/v1/contracts", 422, "物件數量已達訂閱方案上限"),
    ("POST", "/api/external/v1/estates", 422, "此團隊目前沒有有效的訂閱方案"),
    ("POST", "/api/external/v1/bills/manual", 422, "此合約尚未綁定承租方，無法建立帳單 "),
    ("POST", "/api/external/v1/repairs", 409, "相同的冪等鍵正在處理中"),
]


@pytest.mark.parametrize("method,path,status,message", _OUTSIDE)
async def test_a4_outside_whitelist_or_key_layer_is_action_failed(method, path, status, message, caplog):
    """A4：白名單外、金鑰層、404 ⇒ `failed` ⇒ 現有 `ACTION_FAILED_TEXT`；log ⛔ JGB 訊息全文。"""
    t = _real_transport_with(_json_error(status, message))
    with caplog.at_level(logging.DEBUG):
        resp = await t.send(method, path, data={"role_id": ROLE})
        result = action_tools._write_failed(SimpleNamespace(write_wiring=True), resp, "unit")
    assert resp["error"]["reason"] == CC.WRITE_RESULT_FAILED
    assert result.data == {CC.WRITE_RESULT_KEY: CC.WRITE_RESULT_FAILED}
    assert CC.WRITE_RESULT_TEXTS[result.data[CC.WRITE_RESULT_KEY]] == CC.ACTION_FAILED_TEXT
    assert message.strip() not in caplog.text


def test_a4_write_failed_off_is_byte_identical_and_ignores_jgb_text():
    """A4：off ⇒ `_write_failed` 回改動前的 `NO_MATCH`（無 data）；on 只讀 transport 放的 `reason`，
    ⛔ 讀 `error.message`（JGB 原文就算剛好等於錯誤碼也不採用）。"""
    off = action_tools._write_failed(SimpleNamespace(write_wiring=False),
                                     {"success": False, "error": {"reason": "no_lessee"}}, "unit")
    assert (off.ok, off.error, off.data) == (False, "NO_MATCH", None) or \
        (off.ok, off.error, off.data) == (False, "NO_MATCH", {})
    sneaky = action_tools._write_failed(SimpleNamespace(write_wiring=True),
                                        {"success": False, "error": {"code": 422, "message": "no_lessee"}},
                                        "unit")
    assert sneaky.data == {CC.WRITE_RESULT_KEY: CC.WRITE_RESULT_FAILED}
    bogus = action_tools._write_failed(SimpleNamespace(write_wiring=True),
                                       {"success": False, "error": {"reason": "<script>"}}, "unit")
    assert bogus.data == {CC.WRITE_RESULT_KEY: CC.WRITE_RESULT_FAILED}


async def test_a4_mock_path_due_not_draft_reaches_fixed_sentence_code(mock_api):
    """A4（替身路徑同一套分類）：on＋替身——非待發送帳單改到期日 ⇒ 替身回 staging 422 原句 ⇒ `due_not_draft`。
    off 正對照：同一筆 ⇒ 改動前的 `NO_MATCH`（無錯誤碼）。"""
    mock_api.write_wiring = True
    res = await _execute(_due_payload(BILL_NOT_DRAFT, BILL_NOT_DRAFT_EXPIRE, "20261018"), token="tok-nd")
    assert (res.ok, res.error) == (False, "NO_MATCH"), res
    assert res.data == {CC.WRITE_RESULT_KEY: "due_not_draft"}
    assert mock_api._mock_transport.calls[-1][:2] == ("PATCH", f"/api/external/v1/bills/{BILL_NOT_DRAFT}")


# ── runtime：兌現段依錯誤碼出固定句、重按回同一句 ─────────────────────────────
class _WriteRegistry(FakeRegistry):
    """FakeRegistry＋`is_write_tool`＋記錄 `timeout_s`。"""

    def __init__(self, *, write_tool: bool = True, **kw):
        super().__init__(**kw)
        self._write_tool = write_tool
        self.timeouts: list = []

    def is_write_tool(self, name):
        return self._write_tool and name.startswith("jgb2.action.")

    async def call(self, identity, name, args, timeout_s, **kw):
        self.timeouts.append(timeout_s)
        return await super().call(identity, name, args, timeout_s, **kw)


def _seg_runtime(registry, pool, **kw):
    return AgentRuntime(_empty_provider(), registry, FakeVerifier(), FakeAssembler(), Budget(),
                        stage="M1", clock=FakeClock(), db_pool=pool, **kw)


@pytest.fixture()
def seg_today(monkeypatch):
    monkeypatch.setattr(_bills, "_today", lambda: date(2026, 8, 15))   # 段測試 payload 的日期


def _wiring(monkeypatch, on: bool):
    monkeypatch.setattr(jgb2_tools, "_api_singleton", SimpleNamespace(use_mock=False, write_wiring=on))


@pytest.mark.parametrize("code", ["due_not_draft", "no_lessee", "repair_item", "failed", "unconfirmed"])
async def test_a4_runtime_redeem_fixed_sentence_and_same_on_repress(monkeypatch, seg_today, code):
    """A4：on——寫入工具回封閉錯誤碼 ⇒ 兌現段回該碼的固定句、receipt 存錯誤碼；同一張卡重按回同一句、⛔ 再呼叫工具。"""
    _wiring(monkeypatch, True)
    registry = _WriteRegistry(call_results=[
        ToolResult(ok=False, error="NO_MATCH", data={CC.WRITE_RESULT_KEY: code})])
    rt = _seg_runtime(registry, FakePool([_redeem_row(), None]))
    state = _state_with_pending()
    first = await rt.run_turn(_seg_identity(), f"confirm_submit:{_PID}", state)
    assert first.answer == CC.WRITE_RESULT_TEXTS[code]
    assert first.trace.llm_calls == 0
    assert state["agent"][PENDING_CONFIRM_KEY][_PID]["receipt"] == {"error": code}
    second = await rt.run_turn(_seg_identity(), f"confirm_submit:{_PID}", state)
    assert second.answer == first.answer
    assert len(registry.call_args) == 1


async def test_a4_runtime_off_keeps_action_failed_text(monkeypatch, seg_today):
    """A4 off 等價：同樣的工具結果在 off ⇒ 改動前的 `ACTION_FAILED_TEXT`、receipt `{"error": "NO_MATCH"}`。"""
    _wiring(monkeypatch, False)
    registry = _WriteRegistry(call_results=[
        ToolResult(ok=False, error="NO_MATCH", data={CC.WRITE_RESULT_KEY: "due_not_draft"})])
    rt = _seg_runtime(registry, FakePool([_redeem_row()]))
    state = _state_with_pending()
    res = await rt.run_turn(_seg_identity(), f"confirm_submit:{_PID}", state)
    assert res.answer == CC.ACTION_FAILED_TEXT
    assert state["agent"][PENDING_CONFIRM_KEY][_PID]["receipt"] == {"error": "NO_MATCH"}


async def test_a4_runtime_rejects_code_outside_closed_set(monkeypatch, seg_today):
    """A4：工具 data 帶封閉值域外的碼 ⇒ 當 `failed`（⛔ 把任意字串當句子鍵）。"""
    _wiring(monkeypatch, True)
    registry = _WriteRegistry(call_results=[
        ToolResult(ok=False, error="NO_MATCH", data={CC.WRITE_RESULT_KEY: "這是 JGB 原文"})])
    rt = _seg_runtime(registry, FakePool([_redeem_row()]))
    res = await rt.run_turn(_seg_identity(), f"confirm_submit:{_PID}", _state_with_pending())
    assert res.answer == CC.ACTION_FAILED_TEXT


# ═══ A5：結果無法確定 ⇒「結果未確認」═════════════════════════════════════════
async def test_a5_write_tool_timeout_is_90s_only_when_on_and_write_tool(monkeypatch, seg_today):
    """A5（W7）：on＋寫入工具 ⇒ 兌現段工具逾時 90 秒；off 或非寫入工具 ⇒ 維持 3 秒。"""
    ok = ToolResult(ok=True, data={"receipt": {"id": "BILL-77"}})
    cases = [(True, True, 90.0), (False, True, 3.0), (True, False, 3.0)]
    for on, write_tool, expected in cases:
        _wiring(monkeypatch, on)
        registry = _WriteRegistry(write_tool=write_tool, call_results=[ok])
        rt = _seg_runtime(registry, FakePool([_redeem_row()]))
        await rt.run_turn(_seg_identity(), f"confirm_submit:{_PID}", _state_with_pending())
        assert registry.timeouts == [expected], (on, write_tool)
    assert runtime_mod.WRITE_TOOL_TIMEOUT_S == 90.0


async def test_a5_tool_timeout_is_unconfirmed_and_same_on_repress(monkeypatch, seg_today):
    """A5：on——寫入工具 `TOOL_TIMEOUT` ⇒「結果未確認」（⛔「無法執行」）；同一張卡重按回同一句、⛔ 再送。
    off 正對照：同一結果 ⇒ `ACTION_FAILED_TEXT`。"""
    _wiring(monkeypatch, True)
    registry = _WriteRegistry(call_results=[ToolResult(ok=False, error="TOOL_TIMEOUT")])
    rt = _seg_runtime(registry, FakePool([_redeem_row(), None]))
    state = _state_with_pending()
    first = await rt.run_turn(_seg_identity(), f"confirm_submit:{_PID}", state)
    assert first.answer == UNCONFIRMED_SENTENCE
    second = await rt.run_turn(_seg_identity(), f"confirm_submit:{_PID}", state)
    assert second.answer == UNCONFIRMED_SENTENCE and len(registry.call_args) == 1

    _wiring(monkeypatch, False)
    registry = _WriteRegistry(call_results=[ToolResult(ok=False, error="TOOL_TIMEOUT")])
    rt = _seg_runtime(registry, FakePool([_redeem_row()]))
    off = await rt.run_turn(_seg_identity(), f"confirm_submit:{_PID}", _state_with_pending())
    assert off.answer == CC.ACTION_FAILED_TEXT


def _slow_registry(sleep_s: float) -> ToolRegistry:
    """真 `ToolRegistry`（真的 `asyncio.wait_for` 逾時）＋真寫入工具 spec，handler 換成睡 `sleep_s` 的替身。"""
    reg = ToolRegistry(write_tools_enabled=True, redeem_checker=AsyncMock(return_value=True))

    async def slow(identity, args):
        await asyncio.sleep(sleep_s)
        return ToolResult(ok=True, data={"receipt": {"id": "BILL-77"}}, text_for_model="ok")

    for spec, _fn in action_tools.ACTION_SPECS:
        reg.register(spec, slow)
    return reg


async def test_a5_real_registry_slow_write_uses_long_timeout(monkeypatch, seg_today):
    """A5：寫入工具耗時超過一般工具逾時——on ⇒ 用寫入逾時、成功；off ⇒ 一般逾時切斷 ⇒ `ACTION_FAILED_TEXT`（同改動前）；
    on 但連寫入逾時也超過 ⇒「結果未確認」。（逾時秒數縮成毫秒級跑，比例同 3 秒／90 秒。）"""
    monkeypatch.setattr(runtime_mod, "WRITE_TOOL_TIMEOUT_S", 0.5)
    # 真 registry 的寫入 wrapper 要求業者身分帶 user_id（單一證明）⇒ 身分與待確認筆建立者一致帶上 role／user。
    ident = _seg_identity(role_id=ROLE, user_id=OWNER)
    creator = {"user_id": OWNER, "role_id": ROLE}

    def run(sleep_s):
        rt = _seg_runtime(_slow_registry(sleep_s), FakePool([_redeem_row()]), tool_timeout_s=0.02)
        return rt.run_turn(ident, f"confirm_submit:{_PID}", _state_with_pending(creator=creator))

    _wiring(monkeypatch, True)
    on = await run(0.1)
    assert on.answer not in (CC.ACTION_FAILED_TEXT, UNCONFIRMED_SENTENCE), on.answer
    assert on.outcome["state"] == "confirmed"

    _wiring(monkeypatch, False)
    off = await run(0.1)
    assert off.answer == CC.ACTION_FAILED_TEXT

    _wiring(monkeypatch, True)
    late = await run(2.0)
    assert late.answer == UNCONFIRMED_SENTENCE


def _raise(exc_type):
    def handler(request):
        raise exc_type("boom", request=request)
    return handler


def _status(status: int, **kw):
    def handler(request):
        return httpx.Response(status, **kw)
    return handler


@pytest.mark.parametrize("name,handler,expected", [
    ("http_read_timeout", _raise(httpx.ReadTimeout), "unconfirmed"),
    ("http_write_timeout", _raise(httpx.WriteTimeout), "unconfirmed"),
    ("http_connect_timeout", _raise(httpx.ConnectTimeout), "unconfirmed"),
    ("read_error_after_send", _raise(httpx.ReadError), "unconfirmed"),
    ("remote_protocol_error", _raise(httpx.RemoteProtocolError), "unconfirmed"),
    ("5xx_500", _status(500, json={"success": False, "error": {"code": 500, "message": "x"}}), "unconfirmed"),
    ("5xx_502_html", _status(502, text="<html>bad gateway</html>"), "unconfirmed"),
    ("2xx_not_json", _status(200, text="<html>ok</html>"), "unconfirmed"),
    ("2xx_json_list", _status(201, json=[1, 2]), "unconfirmed"),
    ("2xx_not_success_shell", _status(200, json={"success": False,
                                                 "error": {"reason": "no_lessee", "message": "x"}}), "unconfirmed"),
    ("3xx_redirect", _status(302, headers={"location": "https://evil.example/"}), "unconfirmed"),
    ("connect_error_before_send", _raise(httpx.ConnectError), "failed"),
])
async def test_a5_transport_uncertain_results_are_unconfirmed(name, handler, expected, caplog):
    """A5（W7）：HTTP 逾時、5xx、送出後連線／讀取錯誤、2xx 非 JSON、2xx 非成功外殼、3xx ⇒ `unconfirmed`；
    送出前就連不上 ⇒ `failed`（確定沒寫入）。log ⛔ 例外訊息與網址。"""
    t = _real_transport_with(handler)
    with caplog.at_level(logging.DEBUG):
        resp = await t.send("POST", "/api/external/v1/estates", data={"role_id": ROLE})
    assert resp["success"] is False and resp["error"]["reason"] == expected, name
    result = action_tools._write_failed(SimpleNamespace(write_wiring=True), resp, "unit")
    text = CC.WRITE_RESULT_TEXTS[result.data[CC.WRITE_RESULT_KEY]]
    assert text == (UNCONFIRMED_SENTENCE if expected == "unconfirmed" else CC.ACTION_FAILED_TEXT)
    ours = _our_log_text(caplog)
    assert "staging.jgbsmart.com" not in ours and "boom" not in ours
    assert "/api/external/v1/estates" in ours                         # 正對照：樣板有記


async def test_a5_write_http_timeouts_and_reads_unchanged():
    """A5（W7）：寫入 JSON 30 秒、multipart 60 秒；讀取維持建構時的 10 秒；off 時寫入也維持 10 秒。"""
    seen: list = []
    ok = _status(201, json={"success": True, "data": {"id": 1}})
    t = _real_transport_with(ok, seen)
    await t.send("POST", "/api/external/v1/estates", data={"role_id": ROLE})
    await t.send("POST", "/api/external/v1/repairs", data={"role_id": ROLE},
                 files=[("broken_photos[]", ("p.jpg", b"\xff\xd8\xff", "image/jpeg"))])
    await t.send("PATCH", f"/api/external/v1/bills/{BILL_DRAFT}", data={"role_id": ROLE})
    await t.send("GET", "/api/external/v1/bills", params={"role_id": ROLE})
    assert seen == [T.WRITE_TIMEOUT_S, T.WRITE_TIMEOUT_MULTIPART_S, T.WRITE_TIMEOUT_S, 10.0]
    assert (T.WRITE_TIMEOUT_S, T.WRITE_TIMEOUT_MULTIPART_S) == (30.0, 60.0)

    seen_off: list = []
    t_off = _real_transport_with(ok, seen_off)
    t_off.write_wiring = False
    await t_off.send("POST", "/api/external/v1/estates", data={"role_id": ROLE})
    assert seen_off == [10.0]


class _ScriptedWrites:
    """GET 轉給替身、POST／PATCH 回固定回應（模擬 staging 寫入回 2xx 但缺 `data.id` 之類）。"""

    def __init__(self, inner, write_resp):
        self.inner = inner
        self.write_resp = write_resp
        self.writes: list = []

    async def send(self, method, path, *, params=None, data=None, files=None):
        if method in ("POST", "PATCH"):
            self.writes.append((method, path))
            return self.write_resp
        return await self.inner.send(method, path, params=params, data=data)


@pytest.mark.parametrize("factory", [_estate_payload, _contract_payload, _bill_payload])
async def test_a5_success_without_id_is_unconfirmed(real_api, factory):
    """A5（W7）：2xx 成功外殼卻缺 `data.id` ⇒ 工具回 `unconfirmed`（JGB 可能已建立）；正對照：帶 id ⇒ 成功。"""
    card = await _card(factory())
    assert card.ok, card
    inner = real_api._real_transport.inner
    real_api._real_transport = _ScriptedWrites(inner, {"success": True, "data": {}})
    res = await _execute(card.data["payload"], token="tok-noid")
    assert (res.ok, res.error) == (False, "NO_MATCH")
    assert res.data == {CC.WRITE_RESULT_KEY: CC.WRITE_RESULT_UNCONFIRMED}
    real_api._real_transport = _ScriptedWrites(inner, {"success": True, "data": {"id": 4321}})
    ok = await _execute(card.data["payload"], token="tok-id")
    assert ok.ok, ok


async def test_a5_due_and_repair_success_without_id_is_unconfirmed(real_api):
    """A5（W7）：改到期日、修繕 2xx 缺 `data.id` ⇒ `unconfirmed`。"""
    inner = real_api._real_transport.inner
    real_api._real_transport = _ScriptedWrites(inner, {"success": True, "data": {"date_expire": 20270617}})
    due = await _execute(_due_payload(), token="tok-due-noid")
    assert due.data == {CC.WRITE_RESULT_KEY: CC.WRITE_RESULT_UNCONFIRMED}
    repair = await _execute({"action": "repair_create", "estate_name": ESTATE_A_TITLE,
                             "description": "冷氣不冷"}, token="tok-rep-noid")
    assert repair.data == {CC.WRITE_RESULT_KEY: CC.WRITE_RESULT_UNCONFIRMED}
    assert [m for m, _p in real_api._real_transport.writes] == ["PATCH", "POST"]


# ═══ A6：寫入工具只給站內幫手金鑰 ═══════════════════════════════════════════
def _spy_registry():
    reg = ToolRegistry(write_tools_enabled=True, redeem_checker=AsyncMock(return_value=True))
    calls: list = []

    def spy(name):
        async def handler(identity, args):
            calls.append(name)
            return ToolResult(ok=False, error="NO_MATCH")
        return handler

    names = []
    for spec, _fn in action_tools.ACTION_SPECS:
        reg.register(spec, spy(spec["name"]))
        names.append(spec["name"])
    return reg, calls, names


@pytest.mark.parametrize("env,key_id", [
    ("1", 5),           # 金鑰不在清單
    (None, 1),          # env 未設 ⇒ 空集合
    ("", 1),            # env 空 ⇒ 空集合
    ("5,x", 5),         # env 不合法 ⇒ 當空集合
    ("1", None),        # 沒有金鑰 id
    ("1", True),        # bool ⛔ 當 1
    ("1", "1"),         # 字串 ⛔ 當整數
])
async def test_a6_non_assistant_key_cannot_see_or_call_write_tools(monkeypatch, env, key_id):
    """A6（W8）：非站內幫手金鑰 ⇒ 寫入工具不在清單、`call` 回 `NO_MATCH` 且 handler ⛔ 被呼叫。"""
    if env is None:
        monkeypatch.delenv("AGENT_ASSISTANT_KEY_IDS", raising=False)
    else:
        monkeypatch.setenv("AGENT_ASSISTANT_KEY_IDS", env)
    reg, calls, names = _spy_registry()
    ident = _pm(api_key_id=key_id)
    visible = {s["name"] for s in reg.specs_for(ident, "M1", for_model=True)}
    assert not (visible & set(names))
    for name in names:
        res = await reg.call(ident, name, {"payload": {}, "confirmation_token": "t"},
                             timeout_s=1, stage="M1", for_model=True)
        assert (res.ok, res.error) == (False, "NO_MATCH")
    assert calls == []


async def test_a6_listed_assistant_key_can_see_and_call(monkeypatch):
    """A6 正對照：金鑰 id 在 `AGENT_ASSISTANT_KEY_IDS` ⇒ 看得到、呼叫得到 handler；`is_write_tool` 只認寫入 spec。"""
    monkeypatch.setenv("AGENT_ASSISTANT_KEY_IDS", "3, 1")
    reg, calls, names = _spy_registry()
    ident = _pm(api_key_id=1)
    visible = {s["name"] for s in reg.specs_for(ident, "M1", for_model=True)}
    assert set(names) <= visible
    await reg.call(ident, names[0], {"payload": {}, "confirmation_token": "t"},
                   timeout_s=1, stage="M1", for_model=True)
    assert calls == [names[0]]
    assert all(reg.is_write_tool(n) for n in names)
    assert reg.is_write_tool("jgb2.no_such_tool") is False


def test_a6_mcp_union_probe_has_no_key_so_write_tools_are_not_registered(monkeypatch):
    """A6（W8 副作用，交人審）：`union_specs` 探針身分沒有金鑰 id ⇒ `/mcp` server 不再註冊寫入工具。
    寫入仍由對話回合內 `registry.call`（帶真實身分）執行；本測試只把這個現況釘住。"""
    monkeypatch.setenv("AGENT_ASSISTANT_KEY_IDS", "1")
    reg, _calls, names = _spy_registry()
    union = {s["name"] for s in F.union_specs(reg, "M1")}
    assert not (union & set(names))
