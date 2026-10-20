"""unit：站內幫手 S3 照片／PDF（plan-assistant-11-items-20261014 §3h 第 1～9 點＋DocuMind D1～D10）。

被測物：`document_extract`（`building_deed` 分類、放行對照、有型別值）、`mcp_facade`
（照片中繼資料、謄本送 DocuMind）、`runtime`（文件回合放行／覆寫／暫存、照片附進修繕單）、
`confirm_card`（附照片一行、收據日期卡外提示）、`image_fetch`（`exp` fail-closed）。
全部離線：抓檔、擷取、DocuMind 一律替身（DocuMind 回應形狀以合成值重建，見
`test_documind_client_req.py`）。每條附正對照；變異清單見回報。
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from tests.unit.agent.confirm_pool_double import attach_token_tx  # 第 3 步 A7：token 寫入交易替身
from PIL import Image

from services import documind_client as dm
from services import jgb_system_api as api_mod
from services.agent import document_extract as dx
from services.agent import image_fetch
from services.agent import mcp_facade as F
from services.agent.agent_session import (
    DOCUMENT_CARRY_KEY,
    DOCUMENT_CARRY_MAX_TURNS,
    AgentSession,
)
from services.agent.budget import Budget
from services.agent.confirm_card import RECEIPT_DATE_HINT_TEMPLATE, render
from services.agent.identity import Identity
from services.agent.runtime import (
    DOC_NO_WRITE_TEXT,
    IMAGE_SUGGESTION_KEY,
    PENDING_CONFIRM_KEY,
    AgentRuntime,
    ImageTurnInput,
)
from services.agent.tools import action as action_tools
from services.agent.tools import jgb2 as jgb2_tools
from services.agent.tools.confirm import CONFIRM_SPEC, confirm_request, sha256_hex
from services.agent.tools.registry import ToolRegistry, ToolResult, openai_tool_name
from services.jgb import bills as _bills
from services.jgb import fixture_store
from services.jgb.transport import RecordingTransport

from tests.unit.agent.test_documind_client_req import (
    DOOR,
    MUST_NOT_APPEAR,
    electronic_response,
    scanned_response,
)
from tests.unit.agent.test_runtime_req import (
    FakeAssembler, FakeClock, FakeProvider, FakeVerifier, VerifierVerdict,
    _fake_message, _fake_response, _fake_tool_call, _final_response,
)

pytestmark = [pytest.mark.unit, pytest.mark.req("agentic-mcp-orchestration:R10")]

FIXTURE = (Path(__file__).resolve().parents[3]
           / "services" / "jgb" / "fixture_data" / "assistant_demo_vendor4.json")
ROLE, OWNER = "20151", "12291"
TODAY = date(2026, 10, 15)
CONTRACT_A = 89481                       # fixture：12291 可見的有效合約（S2 測試同一筆）
UPLOAD_HOST = "upload.jgb.example"       # 必帶 exp 的測試主機（非豁免）
FREE_ISSUER = "合成五金行"


@pytest.fixture(autouse=True)
def _freeze_today(monkeypatch):
    monkeypatch.setattr(_bills, "_today", lambda: TODAY)


@pytest.fixture(autouse=True)
def _clean_counts():
    image_fetch.reset_image_count_cap()
    image_fetch.reset_file_count_cap()
    image_fetch.reset_image_failures()
    yield


@pytest.fixture()
def api(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.delenv("MOCK_FAIL_NEXT_WRITE", raising=False)
    monkeypatch.delenv("JGB_MOCK_WRITE_LOG", raising=False)
    monkeypatch.setattr(fixture_store, "_DATA", fixture_store._DATA)
    fixture_store.load_from(FIXTURE)
    a = api_mod.JGBSystemAPI()
    a._mock_transport = RecordingTransport(a._mock_transport)
    monkeypatch.setattr(jgb2_tools, "_api_singleton", a)
    return a


@pytest.fixture()
def no_documind(monkeypatch):
    for k in (dm.DOCUMIND_BASE_URL_ENV, dm.DOCUMIND_TOKEN_ENV, dm.DOCUMIND_INSECURE_TEST_HOST_ENV):
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


@pytest.fixture()
def documind_on(no_documind):
    no_documind.setenv(dm.DOCUMIND_BASE_URL_ENV, "https://documind.example.test/api/v1")
    no_documind.setenv(dm.DOCUMIND_TOKEN_ENV, "tok123")
    return no_documind


def _pm(**over) -> Identity:
    base = dict(vendor_id=4, target_user="property_manager", mode="b2b", role_id=ROLE,
                user_id=OWNER, session_id="mcp:1:4:s3", api_key_id=1, entry="mcp")
    base.update(over)
    return Identity(**base)


def _jpeg(color=(120, 140, 160), *, exif=False) -> bytes:
    img = Image.new("RGB", (64, 48), color)
    buf = io.BytesIO()
    if exif:
        ex = Image.Exif()
        ex[0x010F] = "合成相機"
        img.save(buf, format="JPEG", exif=ex.tobytes())
    else:
        img.save(buf, format="JPEG")
    return buf.getvalue()


def _synth_pdf(pages: int = 1) -> bytes:
    from tests.unit.agent.test_document_turn_req import _synth_pdf as make
    return make(pages=pages)


# ════════════════════════════════════════════════════════════════════
# 第 7 點：抓圖 `exp` fail-closed（F9／S3-6）
# ════════════════════════════════════════════════════════════════════
@pytest.fixture()
def gate_env(monkeypatch):
    monkeypatch.setenv("IMAGE_URL_ALLOWLIST", f"relay.jgbsmart.com,{UPLOAD_HOST}")
    monkeypatch.setattr(image_fetch, "resolve_host", lambda host: ["8.8.8.8"])
    return monkeypatch


NOW = 1_800_000_000


@pytest.mark.parametrize("query,code", [
    ("", image_fetch.IMAGE_URL_NOT_ALLOWED),                                   # 缺
    ("exp=", image_fetch.IMAGE_URL_NOT_ALLOWED),                               # 空值
    (f"exp={NOW + 60}&exp={NOW + 60}", image_fetch.IMAGE_URL_NOT_ALLOWED),     # 多個
    (f"exp={NOW + 60}&exp=", image_fetch.IMAGE_URL_NOT_ALLOWED),               # 多個（含空）
    ("exp=abc", image_fetch.IMAGE_URL_EXPIRED),                                # 非整數
    (f"exp={NOW}", image_fetch.IMAGE_URL_EXPIRED),                             # 已到期
    (f"exp={NOW + image_fetch.EXP_MAX_AHEAD_S + 1}", image_fetch.IMAGE_URL_NOT_ALLOWED),  # 太遠
])
def test_exp_is_required_on_non_exempt_hosts(gate_env, query, code):
    url = f"https://{UPLOAD_HOST}/p/1.jpg" + (f"?{query}" if query else "")
    with pytest.raises(image_fetch.ImageFetchError) as err:
        image_fetch.validate_image_url(url, now=NOW)
    assert err.value.code == code


def test_exp_positive_controls(gate_env):
    ok = f"https://{UPLOAD_HOST}/p/1.jpg?exp={NOW + image_fetch.EXP_MAX_AHEAD_S}&sig=x"
    assert image_fetch.validate_image_url(ok, now=NOW) == UPLOAD_HOST
    # relay 豁免：行為不變——沒有 exp 照樣過、過期照樣擋
    assert image_fetch.validate_image_url("https://relay.jgbsmart.com/a/1.jpg", now=NOW) \
        == "relay.jgbsmart.com"
    assert image_fetch.validate_image_url(
        f"https://relay.jgbsmart.com/a/1.jpg?exp={NOW + 99999}", now=NOW) == "relay.jgbsmart.com"
    with pytest.raises(image_fetch.ImageFetchError):
        image_fetch.validate_image_url(f"https://relay.jgbsmart.com/a/1.jpg?exp={NOW - 1}", now=NOW)
    assert image_fetch.EXP_OPTIONAL_HOSTS == frozenset({"relay.jgbsmart.com"})


# ════════════════════════════════════════════════════════════════════
# 第 8 點：gpt-6 系列參數分支
# ════════════════════════════════════════════════════════════════════
def test_gpt6_models_use_the_new_param_branch():
    from services import image_recognition_service as irs

    for model in ("gpt-6-luna", "gpt-5.6-luna"):
        p = irs._completion_params(model)
        assert "max_completion_tokens" in p and "temperature" not in p
        q = dx._completion_params(model, 999)
        assert q["max_completion_tokens"] == 999 and "temperature" not in q
    assert "max_tokens" in irs._completion_params("gpt-4o")            # 正對照
    assert "max_tokens" in dx._completion_params("gpt-4o", 1)
    assert dx.NEW_PARAM_MODEL_PREFIXES == irs.NEW_PARAM_MODEL_PREFIXES


# ════════════════════════════════════════════════════════════════════
# 第 6 點：照片中繼資料（原檔 sha256）
# ════════════════════════════════════════════════════════════════════
class _PhotoFetcher:
    def __init__(self, blobs):
        self.blobs = list(blobs)

    async def __call__(self, url, *, timeout_s):
        return image_fetch.FetchedImage(data=self.blobs.pop(0), content_type="image/jpeg")


async def _recognize(*a, **k):
    return {"is_damage": True, "confidence": 0.9, "suggested_category": None}


async def test_photo_meta_is_sha256_of_original_bytes(monkeypatch):
    a, b = _jpeg((1, 2, 3)), _jpeg((200, 2, 3))
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([a, b]))
    monkeypatch.setattr(F, "_image_recognize_batch", _recognize)
    turn, _ = await F.prepare_image_turn(["u1", "u2"], category_tree=None)
    assert [p["sha256"] for p in turn.photos] == [hashlib.sha256(a).hexdigest(),
                                                  hashlib.sha256(b).hexdigest()]
    assert turn.photos[0] == {"filename": "photo-1.jpg", "content_type": "image/jpeg",
                              "size": len(a), "sha256": hashlib.sha256(a).hexdigest()}
    # 改一個位元組 ⇒ sha256 不同
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([a[:-3] + b"\x00" + a[-2:]]))
    turn2, _ = await F.prepare_image_turn(["u1"], category_tree=None)
    assert turn2.photos[0]["sha256"] != hashlib.sha256(a).hexdigest()


async def test_failed_recognition_attaches_no_photos(monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("x")
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([_jpeg()]))
    monkeypatch.setattr(F, "_image_recognize_batch", boom)
    turn, _ = await F.prepare_image_turn(["u1"], category_tree=None)
    assert turn.status == "failed" and turn.photos == ()


# ════════════════════════════════════════════════════════════════════
# 第 6 點：照片附進修繕單（runtime 刪鍵＋寫入、卡上張數、兌現帶中繼資料）
# ════════════════════════════════════════════════════════════════════
def _meta(i: int) -> dict:
    return {"filename": f"photo-{i}.jpg", "content_type": "image/jpeg", "size": 1000 + i,
            "sha256": hashlib.sha256(str(i).encode()).hexdigest()}


class _CaptureRegistry:
    """記下送進 registry 的參數；`confirm.request` 用真 `render()` 出卡（不碰 DB）。"""

    def __init__(self, *, confirm_error=None, tools=("confirm.request",)):
        self.call_args: list = []
        self.confirm_error = confirm_error
        self.tools = tools

    def to_openai_tools(self, identity, stage, *, readonly_view=False):
        return [{"type": "function", "function": {"name": openai_tool_name(n), "parameters": {}}}
                for n in self.tools]

    def specs_for(self, identity, stage, *, readonly_view=False, for_model=False):
        return [dict(CONFIRM_SPEC)] + [dict(s) for s, _ in action_tools.ACTION_SPECS]

    async def call(self, identity, name, args, timeout_s, *, stage, readonly_view=False,
                   for_model=False):
        self.call_args.append({"name": name, "args": dict(args)})
        if name != "confirm.request":
            return ToolResult(ok=False, error="NO_MATCH")
        if self.confirm_error:
            return ToolResult(ok=False, error=self.confirm_error)
        payload = json.loads(args["payload"])
        card = render(payload["action"], payload, today=TODAY)
        return ToolResult(ok=True, data={
            "pending_id": "0123456789abcdef", "card": card, "action": payload["action"],
            "payload": payload, "quick_replies": [], "hint": "", "estate_id": None,
        }, text_for_model="")


_LONG = "麻煩幫我把這筆修繕資料建立起來謝謝"


def _rt(provider, registry):
    return AgentRuntime(provider, registry, FakeVerifier([VerifierVerdict(ok=True)] * 6),
                        FakeAssembler(), Budget(), stage="M1", clock=FakeClock())


def _confirm_call(payload: dict, call_id="c1"):
    return _fake_response(_fake_message(tool_calls=[_fake_tool_call(
        "confirm.request", {"summary": "確認", "payload": json.dumps(payload, ensure_ascii=False)},
        call_id=call_id)]))


_REPAIR = {"action": "repair_create", "estate_name": "測試物件", "description": "椅面破了"}


@pytest.mark.usefixtures("_aplus_proposal_off")
async def test_server_photos_replace_model_photo_keys_and_show_on_card():
    state = {"agent": {IMAGE_SUGGESTION_KEY: {"category_name": None, "photos": [_meta(1)]}}}
    forged = dict(_REPAIR, broken_photos=[_meta(9)], image_ref="x", Photo_count=3)
    reg = _CaptureRegistry()
    res = await _rt(FakeProvider([_confirm_call(forged), _final_response()]), reg).run_turn(
        _pm(), _LONG, state)
    sent = json.loads(reg.call_args[0]["args"]["payload"])
    assert sent["broken_photos"] == [_meta(1)]
    assert "image_ref" not in sent and "Photo_count" not in sent
    assert res.outcome["state"] == "confirm_pending"
    assert "・附照片：1 張" in res.answer
    pending = state["agent"][PENDING_CONFIRM_KEY]["0123456789abcdef"]
    assert pending["payload"]["broken_photos"] == [_meta(1)]          # 進 payload ⇒ 進雜湊
    assert IMAGE_SUGGESTION_KEY not in state["agent"]                 # 出卡即消耗


async def test_no_photo_turn_still_drops_model_photo_keys():
    reg = _CaptureRegistry()
    forged = dict(_REPAIR, broken_photos=[_meta(1)], broken_photos_omitted=9)
    res = await _rt(FakeProvider([_confirm_call(forged), _final_response()]), reg).run_turn(
        _pm(), _LONG, {"agent": {}})
    sent = json.loads(reg.call_args[0]["args"]["payload"])
    assert "broken_photos" not in sent and "broken_photos_omitted" not in sent
    assert "附照片" not in res.answer
    # 正對照：同一份 payload 不經 runtime 直接 render，卡上真的會印照片那一行
    assert "附照片" in render("repair_create", dict(_REPAIR, broken_photos=[_meta(1)]))


@pytest.mark.usefixtures("_aplus_proposal_off")
async def test_more_than_five_photos_attach_none_and_card_says_so():
    state = {"agent": {IMAGE_SUGGESTION_KEY: {"category_name": None,
                                              "photos": [_meta(i) for i in range(1, 7)]}}}
    reg = _CaptureRegistry()
    res = await _rt(FakeProvider([_confirm_call(dict(_REPAIR)), _final_response()]), reg).run_turn(
        _pm(), _LONG, state)
    sent = json.loads(reg.call_args[0]["args"]["payload"])
    assert "broken_photos" not in sent and sent["broken_photos_omitted"] == 6
    assert "・附照片：未附（本次 6 張，超過 5 張上限）" in res.answer


@pytest.mark.usefixtures("_aplus_proposal_off")
async def test_invalid_input_does_not_consume_the_photo_suggestion():
    suggestion = {"category_name": None, "photos": [_meta(1)]}
    state = {"agent": {IMAGE_SUGGESTION_KEY: dict(suggestion)}}
    reg = _CaptureRegistry(confirm_error="INVALID_INPUT")
    await _rt(FakeProvider([_confirm_call(dict(_REPAIR)), _final_response()]), reg).run_turn(
        _pm(), _LONG, state)
    assert state["agent"][IMAGE_SUGGESTION_KEY] == suggestion
    # 正對照：其他失敗（NO_MATCH）照舊消耗
    reg2 = _CaptureRegistry(confirm_error="NO_MATCH")
    await _rt(FakeProvider([_confirm_call(dict(_REPAIR)), _final_response()]), reg2).run_turn(
        _pm(), _LONG, state)
    assert IMAGE_SUGGESTION_KEY not in state["agent"]


async def test_photo_turn_writes_photos_into_the_one_shot_suggestion():
    state = {"agent": {}}
    image = ImageTurnInput(status="ok", facts="照片看不出損壞。", processed=1, total=1,
                           photos=(_meta(1),))
    await _rt(FakeProvider([_final_response()]), _CaptureRegistry()).run_turn(
        _pm(), "這張照片", state, image=image)
    assert state["agent"][IMAGE_SUGGESTION_KEY]["photos"] == [_meta(1)]


def test_card_rejects_bad_photo_shapes():
    from services.agent.confirm_card import ConfirmCardError

    for bad in ([dict(_meta(1), extra=1)], [dict(_meta(1), sha256="x")],
                [_meta(i) for i in range(6)], [dict(_meta(1), content_type="image/gif")]):
        with pytest.raises(ConfirmCardError):
            render("repair_create", dict(_REPAIR, broken_photos=bad))
    with pytest.raises(ConfirmCardError):
        render("repair_create", dict(_REPAIR, broken_photos_omitted=3))


async def test_repair_execution_sends_photo_metadata(api):
    reg = ToolRegistry(write_tools_enabled=True,
                       redeem_checker=AsyncMock(return_value=True))
    for spec, fn in action_tools.ACTION_SPECS:
        reg.register(spec, fn)
    payload = {"action": "repair_create", "estate_name": "測試物件", "description": "椅面破了",
               "broken_photos": [_meta(1)]}
    res = await reg.call(_pm(), "jgb2.action.repair_create",
                         {"payload": payload, "confirmation_token": "tok-s3"},
                         timeout_s=5, stage="M1", for_model=True)
    assert res.ok, res
    body = api._mock_transport.bodies[-1]
    assert body["broken_photos"] == [_meta(1)]
    # 正對照：沒照片 ⇒ body 不帶這個鍵
    payload2 = dict(payload)
    payload2.pop("broken_photos")
    await reg.call(_pm(), "jgb2.action.repair_create",
                   {"payload": payload2, "confirmation_token": "tok-s3b"},
                   timeout_s=5, stage="M1", for_model=True)
    assert "broken_photos" not in api._mock_transport.bodies[-1]


# ════════════════════════════════════════════════════════════════════
# 第 4、5 點：門面——謄本送 DocuMind、收據有型別值
# ════════════════════════════════════════════════════════════════════
class _FileFetcher:
    def __init__(self, data):
        self.data = data

    async def __call__(self, url, *, timeout_s):
        return image_fetch.FetchedImage(data=self.data, content_type="application/pdf")


class _Extractor:
    def __init__(self, result):
        self.result = result

    async def __call__(self, data_urls, **kw):
        return self.result, {"prompt_tokens": 1, "completion_tokens": 1}, "gpt-6-luna"


def _deed_result() -> dict:
    return {"kind": "building_deed", "page_count": 1, "unreadable": False, "uncertain": [],
            "fields": {}, "evidence": None}


def _receipt_result(**fields_over) -> dict:
    fields = {"issuer": FREE_ISSUER, "payer": "合成乙", "amount": 588, "currency": "TWD",
              "date": "2026-10-12", "items": [{"name": "合成燈泡", "amount": 588}],
              "payment_method": "現金", "reference_no": "ZZ-00000001"}
    fields.update(fields_over)
    return {"kind": "bill_receipt", "page_count": 1, "unreadable": False, "uncertain": [],
            "fields": fields, "evidence": None}


class _DocuMindSpy:
    def __init__(self, result=None, *, advance=None):
        self.result = result or dm.DeedResult("ok", (("address", DOOR),))
        self.calls: list = []
        self.advance = advance

    async def __call__(self, data, *, timeout_s, pdf_pages, config):
        self.calls.append({"data": data, "timeout_s": timeout_s, "pdf_pages": pdf_pages,
                           "config": config})
        if self.advance:
            self.advance()
        return self.result


async def test_deed_without_documind_config_is_disabled_and_sends_nothing(monkeypatch, no_documind):
    spy = _DocuMindSpy()
    monkeypatch.setattr(F, "_documind_analyze", spy)
    monkeypatch.setattr(F, "_document_fetch_one", _FileFetcher(_synth_pdf()))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_deed_result()))
    turn, _ = await F.prepare_document_turn([], ["https://relay.jgbsmart.com/d.pdf"])
    assert turn.notice == "deed_unavailable" and turn.facts == "" and spy.calls == []
    assert dx.document_writable_action(turn) is None


async def test_deed_pdf_sends_original_bytes_and_builds_facts_from_typed_only(monkeypatch, documind_on):
    pdf = _synth_pdf()
    typed = (("city", "臺北市"), ("district", "大安區"), ("address", DOOR),
             ("use_for", "residential"), ("size", 68.47), ("floor", "5樓"))
    spy = _DocuMindSpy(dm.DeedResult("ok", typed))
    monkeypatch.setattr(F, "_documind_analyze", spy)
    monkeypatch.setattr(F, "_document_fetch_one", _FileFetcher(pdf))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_deed_result()))
    turn, _ = await F.prepare_document_turn([], ["https://relay.jgbsmart.com/d.pdf"])
    assert spy.calls[0]["data"] == pdf and spy.calls[0]["pdf_pages"] == 1
    assert turn.notice is None and turn.typed_fields == typed and turn.kind == "building_deed"
    assert turn.facts == dx.build_deed_facts(typed)
    assert "縣市：臺北市。" in turn.facts and "用途：住宅。" in turn.facts
    assert dx.document_writable_action(turn) == "estate_create"


async def test_deed_photo_is_reencoded_without_exif(monkeypatch, documind_on):
    original = _jpeg(exif=True)
    spy = _DocuMindSpy()
    monkeypatch.setattr(F, "_documind_analyze", spy)
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([original]))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_deed_result()))
    await F.prepare_document_turn(["https://relay.jgbsmart.com/a.jpg"], [])
    sent = spy.calls[0]["data"]
    assert sent != original and sent.startswith(b"\xff\xd8\xff") and b"Exif" not in sent
    assert spy.calls[0]["pdf_pages"] is None
    assert b"Exif" in original                                          # 正對照


async def test_deed_with_two_attachments_or_too_many_pages_is_not_sent(monkeypatch, documind_on):
    spy = _DocuMindSpy()
    monkeypatch.setattr(F, "_documind_analyze", spy)
    monkeypatch.setattr(F, "_image_fetch_one", _PhotoFetcher([_jpeg()]))
    monkeypatch.setattr(F, "_document_fetch_one", _FileFetcher(_synth_pdf()))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_deed_result()))
    turn, _ = await F.prepare_document_turn(["https://relay.jgbsmart.com/a.jpg"],
                                            ["https://relay.jgbsmart.com/d.pdf"])
    assert turn.notice == "deed_one_at_a_time" and spy.calls == []
    monkeypatch.setattr(F, "_document_fetch_one", _FileFetcher(_synth_pdf(pages=7)))
    turn2, _ = await F.prepare_document_turn([], ["https://relay.jgbsmart.com/d.pdf"])
    assert turn2.notice == "deed_one_at_a_time" and spy.calls == []


@pytest.mark.parametrize("status,notice", [
    ("timeout", "deed_failed"), ("failed", "deed_failed"),
    ("multiple", "deed_one_at_a_time"), ("not_deed", "deed_not_recognized"),
])
async def test_documind_errors_map_to_fixed_notices(monkeypatch, documind_on, status, notice):
    monkeypatch.setattr(F, "_documind_analyze", _DocuMindSpy(dm.DeedResult(status)))
    monkeypatch.setattr(F, "_document_fetch_one", _FileFetcher(_synth_pdf()))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_deed_result()))
    turn, _ = await F.prepare_document_turn([], ["https://relay.jgbsmart.com/d.pdf"])
    assert turn.notice == notice and turn.typed_fields == () and turn.facts == ""


async def test_documind_time_counts_into_elapsed_and_timeout_is_the_remaining_budget(
        monkeypatch, documind_on):
    documind_on.setenv("AGENT_TURN_TIMEOUT_S", "60")
    clock = FakeClock()
    spy = _DocuMindSpy(advance=lambda: clock.advance(7.0))
    monkeypatch.setattr(F, "_documind_analyze", spy)
    monkeypatch.setattr(F, "_document_fetch_one", _FileFetcher(_synth_pdf()))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_deed_result()))
    turn, elapsed = await F.prepare_document_turn(
        [], ["https://relay.jgbsmart.com/d.pdf"], clock=clock)
    assert elapsed >= 7.0
    assert spy.calls[0]["timeout_s"] == pytest.approx(60 - F.DOCUMIND_MODEL_LOOP_RESERVE_S, abs=1.0)
    # 剩餘預算不到下限 ⇒ 不送、沒查成
    documind_on.setenv("AGENT_TURN_TIMEOUT_S", "20")
    spy.calls.clear()
    turn2, _ = await F.prepare_document_turn([], ["https://relay.jgbsmart.com/d.pdf"], clock=clock)
    assert spy.calls == [] and turn2.notice == "deed_failed"


async def test_receipt_typed_fields_and_free_text(monkeypatch):
    monkeypatch.setattr(F, "_document_fetch_one", _FileFetcher(_synth_pdf()))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_receipt_result()))
    turn, _ = await F.prepare_document_turn([], ["https://relay.jgbsmart.com/d.pdf"])
    assert turn.typed_fields == (("total", 588),) and turn.receipt_date == "2026-10-12"
    assert FREE_ISSUER in turn.free_text and "合成燈泡" in turn.free_text
    assert "free_text" not in repr(turn)                                # repr 不印自由文字欄


@pytest.mark.parametrize("over,uncertain", [
    ({"currency": "USD"}, []), ({"amount": 588.5}, []), ({}, ["amount"]),
])
def test_receipt_amount_is_not_filled_when_unsure(over, uncertain):
    result = _receipt_result(**over)
    result["uncertain"] = uncertain
    typed, _ = dx.receipt_typed_fields(result)
    assert typed == ()
    assert dx.receipt_typed_fields(_receipt_result())[0] == (("total", 588),)   # 正對照
    assert dx.receipt_typed_fields(_receipt_result(currency=None))[0] == (("total", 588),)


def test_building_deed_model_fields_cannot_carry_values():
    """我方模型對 `building_deed` 的輸出經封閉表驗證後**一欄都不留**（欄位表為空）。"""
    raw = dict(_deed_result(), fields={"issuer": "x", "title": "y"},
               evidence={"title": "y"})
    checked = dx.apply_evidence_gate(dx.validate_extraction(raw))
    assert checked["fields"] == {}
    assert dx.build_document_facts(checked) == ""
    assert "building_deed" in dx.build_json_schema()["properties"]["kind"]["enum"]


# ════════════════════════════════════════════════════════════════════
# 第 1～3 點：runtime——放行、覆寫、原話限制、自由文字縱深、暫存生命週期
# ════════════════════════════════════════════════════════════════════
class _RealConfirmRegistry(_CaptureRegistry):
    """`confirm.request` 接真 `confirm_request`（真替身資料、假 pool）。"""

    def __init__(self):
        super().__init__()
        self.pool = AsyncMock()
        self.pool.execute = AsyncMock(return_value="INSERT 0 1")
        attach_token_tx(self.pool)
        self.results: list = []

    async def call(self, identity, name, args, timeout_s, *, stage, readonly_view=False,
                   for_model=False):
        self.call_args.append({"name": name, "args": dict(args)})
        if name != "confirm.request":
            return ToolResult(ok=False, error="NO_MATCH")
        res = await confirm_request(identity, args, db_pool=self.pool)
        self.results.append(res)
        return res


def _deed_doc(typed=None, **over) -> dx.DocumentTurnInput:
    typed = typed if typed is not None else (
        ("city", "臺北市"), ("district", "大安區"), ("address", DOOR),
        ("use_for", "residential"), ("size", 68.47), ("floor", "5樓"))
    base = dict(status="ok", kind="building_deed", facts=dx.build_deed_facts(typed),
                pages_seen=1, pages_total=1, typed_fields=typed)
    base.update(over)
    return dx.DocumentTurnInput(**base)


def _receipt_doc(**over) -> dx.DocumentTurnInput:
    base = dict(status="ok", kind="bill_receipt",
                facts=dx.build_document_facts(_receipt_result()), pages_seen=1, pages_total=1,
                typed_fields=(("total", 588),), receipt_date="2026-10-12",
                free_text=dx.free_text_values(_receipt_result()))
    base.update(over)
    return dx.DocumentTurnInput(**base)


async def test_deed_turn_issues_estate_card_with_typed_values_replacing_the_model(api):
    model_payload = {"action": "estate_create", "title": "模型自己取的名字", "city": "新北市",
                     "district": "板橋區", "address": "模型路1號", "use_for": "business"}
    reg = _RealConfirmRegistry()
    state = {"agent": {}}
    res = await _rt(FakeProvider([_confirm_call(model_payload), _final_response()]), reg).run_turn(
        _pm(), "幫我用這份謄本建物件", state, document=_deed_doc())
    assert res.outcome["state"] == "confirm_pending", res.answer
    payload = reg.results[0].data["payload"]
    assert {k: payload[k] for k in ("city", "district", "address", "use_for", "size", "floor")} == {
        "city": "台北市", "district": "大安區", "address": DOOR, "use_for": "residential",
        "size": 68.47, "floor": "5樓"}
    assert payload["title"] == DOOR                     # 模型的標題不在使用者原話 ⇒ 程式取地址
    assert "・物件名稱：" + DOOR in res.answer
    assert DOCUMENT_CARRY_KEY not in state["agent"]     # 出卡即清
    assert "document_typed_fields_applied" in res.trace.violations


async def test_other_action_in_a_writable_document_turn_is_not_called(api):
    reg = _RealConfirmRegistry()
    # S3-live 修正 R3：謄本回合改由程式發 confirm.request（不進模型）⇒ 「別的動作被擋」改在
    # 仍由模型驅動的收據回合驗。
    res = await _rt(FakeProvider([_confirm_call(dict(_REPAIR)), _final_response()]), reg).run_turn(
        _pm(), "幫我用這張收據開帳單", {"agent": {}}, document=_receipt_doc())
    reg.pool.execute.assert_not_awaited()   # 原斷言保留（A7 前 INSERT 走這裡）
    assert reg.call_args == [] and reg.pool.insert.await_count == 0 and reg.pool.burn.await_count == 0      # token 表零新增
    assert "document_turn_action_blocked" in res.trace.violations
    assert res.outcome["state"] != "confirm_pending"


async def test_deed_classified_as_other_is_not_released(api):
    reg = _RealConfirmRegistry()
    doc = _deed_doc(kind="other", typed_fields=(), facts=dx.build_deed_facts(()))
    provider = FakeProvider([_confirm_call({"action": "estate_create"}), _final_response()])
    res = await _rt(provider, reg).run_turn(_pm(), "幫我用這份謄本建物件", {"agent": {}}, document=doc)
    tools = {t["function"]["name"] for t in provider.calls[0]["tools"]}
    assert "confirm__request" not in tools
    assert reg.call_args == []
    assert any(v.startswith("DOCUMENT_TURN_WRITE_BLOCKED:") for v in res.trace.violations)


async def test_writable_doc_turn_still_blocks_confirm_submit():
    """④ `turn_segments` 不改：放行對照內的 kind 照樣不接受 `confirm_submit`。"""
    for doc in (_deed_doc(), _receipt_doc()):
        state = {"agent": {PENDING_CONFIRM_KEY: {"0123456789abcdef": {
            "action": "estate_create", "payload": {}}}}}
        res = await _rt(FakeProvider([]), _CaptureRegistry()).run_turn(
            _pm(), "confirm_submit:0123456789abcdef", state, document=doc)
        assert res.answer == DOC_NO_WRITE_TEXT and res.trace.llm_calls == 0
        assert "0123456789abcdef" in state["agent"][PENDING_CONFIRM_KEY]


async def test_receipt_turn_replaces_total_and_shows_the_receipt_date_off_card(api):
    model_payload = {"action": "manual_bill_create", "contract_ref": "89481", "title": "水電費",
                     "total": 99999, "date_expire": "20261130"}
    msg = "這張收據開到合約 89481，項目水電費，期限 20261130"
    reg = _RealConfirmRegistry()
    state = {"agent": {}}
    res = await _rt(FakeProvider([_confirm_call(model_payload), _final_response()]), reg).run_turn(
        _pm(), msg, state, document=_receipt_doc())
    assert res.outcome["state"] == "confirm_pending", res.answer
    payload = reg.results[0].data["payload"]
    assert payload["total"] == 588 and payload["contract_id"] == CONTRACT_A
    card = reg.results[0].data["card"]
    hint = RECEIPT_DATE_HINT_TEMPLATE.format(date="2026/10/12")
    assert res.answer == f"{card}\n{hint}"                # 卡外提示
    assert "2026/10/12" not in card and "receipt_date" not in payload and "date" not in payload
    pending = state["agent"][PENDING_CONFIRM_KEY][reg.results[0].data["pending_id"]]
    assert pending["card_sha256"] == sha256_hex(card)    # 雜湊只綁卡文字
    assert state["agent"]["dialog"][-1]["content"] == card


async def test_free_text_in_any_payload_field_issues_no_card(api):
    msg = f"項目寫{FREE_ISSUER}，開到合約 89481，期限 20261130"
    payload = {"action": "manual_bill_create", "contract_ref": "89481", "title": FREE_ISSUER,
               "date_expire": "20261130"}
    reg = _RealConfirmRegistry()
    res = await _rt(FakeProvider([_confirm_call(payload), _final_response()]), reg).run_turn(
        _pm(), msg, {"agent": {}}, document=_receipt_doc())
    assert reg.call_args == [] and "document_free_text_in_payload" in res.trace.violations
    # 正對照：同一句換一個不是文件自由文字的項目名 ⇒ 出卡
    msg2 = "項目寫水電費，開到合約 89481，期限 20261130"
    reg2 = _RealConfirmRegistry()
    res2 = await _rt(FakeProvider([_confirm_call(dict(payload, title="水電費")), _final_response()]),
                     reg2).run_turn(_pm(), msg2, {"agent": {}}, document=_receipt_doc())
    assert res2.outcome["state"] == "confirm_pending"


async def test_model_text_not_in_user_words_is_dropped_and_asked(api):
    """`title` 不在使用者原話 ⇒ 視為缺 ⇒ 程式追問（文件回合的程式追問出口）。"""
    payload = {"action": "manual_bill_create", "contract_ref": "89481", "title": "管理費",
               "date_expire": "20261130"}
    reg = _RealConfirmRegistry()
    provider = FakeProvider([_confirm_call(payload), _final_response()])
    res = await _rt(provider, reg).run_turn(
        _pm(), "開到合約 89481，期限 20261130", {"agent": {}}, document=_receipt_doc())
    assert reg.results[0].data == {"missing_fields": ["帳單項目"]}
    assert res.kind == "ask" and "帳單項目" in res.answer
    assert "confirm_missing_fields_ask" in res.trace.violations
    assert len(provider.calls) == 1                         # 模型 ⛔ 再被叫


async def test_guarded_total_from_the_document_is_dropped_when_not_typed(api):
    payload = {"action": "manual_bill_create", "contract_ref": "89481", "title": "水電費",
               "total": 588, "date_expire": "20261130"}
    reg = _RealConfirmRegistry()
    res = await _rt(FakeProvider([_confirm_call(payload), _final_response()]), reg).run_turn(
        _pm(), "項目水電費，開到合約 89481，期限 20261130", {"agent": {}},
        document=_receipt_doc(typed_fields=()))
    assert reg.results[0].data == {"missing_fields": ["金額"]}
    assert res.kind == "ask"


async def test_carry_is_not_created_without_a_confirm_request():
    state = {"agent": {}}
    await _rt(FakeProvider([_final_response()]), _CaptureRegistry()).run_turn(
        _pm(), "幫我看這張", state, document=_receipt_doc())
    assert DOCUMENT_CARRY_KEY not in state["agent"]


async def test_carry_follow_up_turn_keeps_earlier_words_and_closed_shape(api):
    # 掃描件：沒有縣市／行政區（DocuMind 掃描路徑不取）
    typed = (("address", DOOR), ("use_for", "residential"), ("size", 68.47))
    doc = _deed_doc(typed=typed)
    msg1 = "幫我用這份謄本建物件，縣市是臺北市"
    state = {"agent": {}}
    reg = _RealConfirmRegistry()
    p1 = {"action": "estate_create", "city": "臺北市"}
    r1 = await _rt(FakeProvider([_confirm_call(p1), _final_response()]), reg).run_turn(
        _pm(), msg1, state, document=doc)
    # S3-live 修正 R3：上傳回合由程式驅動（不讀使用者原話）⇒ 縣市、行政區都追問
    assert r1.kind == "ask" and "行政區" in r1.answer and "縣市" in r1.answer
    carry = state["agent"][DOCUMENT_CARRY_KEY]
    assert set(carry) == {"action", "typed_fields", "receipt_date", "turns"}
    assert carry["action"] == "estate_create" and carry["turns"] == 1
    for value in json.dumps(carry, ensure_ascii=False).split('"'):
        assert value not in (msg1,) and "臺北市" not in value      # ⛔ 使用者原話
    # 下一回合：使用者只給行政區；模型重送前一回合給過的縣市 ⇒ 不被重複追問
    reg2 = _RealConfirmRegistry()
    p2 = {"action": "estate_create", "city": "臺北市", "district": "大安區"}
    r2 = await _rt(FakeProvider([_confirm_call(p2), _final_response()]), reg2).run_turn(
        _pm(), "大安區", state)
    assert r2.outcome["state"] == "confirm_pending", r2.answer
    payload = reg2.results[0].data["payload"]
    assert payload["city"] == "台北市" and payload["address"] == DOOR and payload["size"] == 68.47
    assert "document_carry_applied" in r2.trace.violations
    assert DOCUMENT_CARRY_KEY not in state["agent"]


async def test_carry_contains_no_free_text_or_user_words(api):
    msg = "開到合約 89481"
    state = {"agent": {}}
    await _rt(FakeProvider([_confirm_call({"action": "manual_bill_create", "contract_ref": "89481"}),
                            _final_response()]), _RealConfirmRegistry()).run_turn(
        _pm(), msg, state, document=_receipt_doc())
    carry = state["agent"][DOCUMENT_CARRY_KEY]
    blob = json.dumps(carry, ensure_ascii=False)
    for needle in dx.free_text_values(_receipt_result()) + (msg, "89481"):
        assert needle not in blob
    assert carry["typed_fields"] == [["total", 588]] and carry["receipt_date"] == "2026-10-12"


async def test_other_action_clears_the_carry():
    state = {"agent": {}}
    AgentSession(state["agent"]).write_document_carry("estate_create", [("address", DOOR)], None)
    res = await _rt(FakeProvider([_confirm_call(dict(_REPAIR)), _final_response()]),
                    _CaptureRegistry()).run_turn(_pm(), _LONG, state)
    assert DOCUMENT_CARRY_KEY not in state["agent"]
    assert "document_carry_cleared" in res.trace.violations


def test_carry_expires_after_five_turns():
    agent: dict = {}
    session = AgentSession(agent)
    session.write_document_carry("estate_create", [("address", DOOR)], None)
    for i in range(DOCUMENT_CARRY_MAX_TURNS - 1):
        session.end_turn(user_message="x", dialog_text="y", ask_target=None)
        assert agent[DOCUMENT_CARRY_KEY]["turns"] == i + 1
    session.end_turn(user_message="x", dialog_text="y", ask_target=None)
    assert DOCUMENT_CARRY_KEY not in agent


async def test_notice_ends_the_turn_without_the_model():
    doc = _deed_doc(typed=(), facts="", notice="deed_unavailable")
    res = await _rt(FakeProvider([]), _CaptureRegistry()).run_turn(_pm(), "謄本", {"agent": {}},
                                                                   document=doc)
    assert res.answer == dx.DOCUMENT_NOTICE_TEXTS["deed_unavailable"]
    assert res.trace.llm_calls == 0


# ════════════════════════════════════════════════════════════════════
# 端到端（門面＋真 DocuMind 呼叫端＋runtime＋真 confirm_request）：所有權部不外洩
# ════════════════════════════════════════════════════════════════════
async def test_owner_data_never_reaches_model_state_card_or_log(monkeypatch, documind_on, api, caplog):
    def handler(request):
        return httpx.Response(200, json=electronic_response())

    monkeypatch.setattr(dm, "_new_client", lambda t: httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=False, trust_env=False))
    monkeypatch.setattr(F, "_document_fetch_one", _FileFetcher(_synth_pdf()))
    monkeypatch.setattr(F, "_document_extract_pages", _Extractor(_deed_result()))
    with caplog.at_level(logging.DEBUG):
        doc, _ = await F.prepare_document_turn([], ["https://relay.jgbsmart.com/d.pdf"])
        # 模型（對抗）把所有權人資料塞進 payload
        bad = {"action": "estate_create", "title": MUST_NOT_APPEAR[0], "address": MUST_NOT_APPEAR[2],
               "building": MUST_NOT_APPEAR[1], "city": "新北市", "district": "板橋區",
               "use_for": "residential"}
        reg = _RealConfirmRegistry()
        first_seen: list = []

        def _first(kwargs):
            # 送給模型的訊息在**這一刻**的快照（之後的串列會被追加模型自己的 tool call）
            first_seen.append(json.dumps(kwargs["messages"], ensure_ascii=False))
            return _confirm_call(bad)

        provider = FakeProvider([_first, _final_response()])
        state = {"agent": {}}
        res = await _rt(provider, reg).run_turn(_pm(), "幫我用這份謄本建物件", state, document=doc)
    assert res.outcome["state"] == "confirm_pending", res.answer
    payload = reg.results[0].data["payload"]
    assert payload["address"] == DOOR and payload["city"] == "台北市" and payload["floor"] == "5樓"
    # S3-live 修正 R3：謄本回合不進模型（對抗的 payload 根本送不出去）
    assert provider._completions.calls == [] and first_seen == []
    surfaces = {
        "card": res.answer, "payload": json.dumps(payload, ensure_ascii=False),
        "state": json.dumps(state, ensure_ascii=False, default=str),
        "log": "\n".join(r.getMessage() for r in caplog.records),
        "doc": repr(doc) + doc.facts,
    }
    assert DOOR in surfaces["card"]                                      # 正對照
    for name, text in surfaces.items():
        for secret in MUST_NOT_APPEAR:
            assert secret not in text, f"{secret} 出現在 {name}"


@pytest.fixture()
def _aplus_proposal_off(monkeypatch):
    """A+ 片（`AGENT_WRITE_PROPOSAL`）：本檔以「模型自呼 `confirm.request`、以模型參數執行」為載具的
    測試＝開關 off 的正對照（開關 on 時該路徑已收掉）。開關 on 的程式路徑由
    `test_aplus_card_program_only_req.py` 驗出卡、缺欄追問、查無固定句、帳單候選點選、照片與物件記憶前處理；
    本檔其餘行為在開關 on 時沒有另寫程式路徑版本。"""
    monkeypatch.setenv("AGENT_WRITE_PROPOSAL", "off")
