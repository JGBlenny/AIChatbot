"""unit：站內幫手 S3-live 修正輪（主 session 2026-10-15 裁示 R2～R5；R1 在 `test_image_entry_req.py`）。

每條都把 S3-live 實際失敗的情境留成回歸檢查，並附正對照（目標存在時看得到）：

  R2  縣市寫法：JGB 資料一律「台」，送「臺北市」建物件會被替身（以名稱解析）回 422
      （S3-live A11_deed_pdf）。謄本輸出與使用者自己打的縣市都在寫入端改成「台」。
  R3  謄本回合程式驅動：放行的謄本回合 ⛔ 叫模型，程式自己發一次 `confirm.request`
      （S3-live A11_deed_photo：模型沒出卡、改去搜知識庫後轉人，暫存也沒建立）。
  R4  (1) 封閉鍵錯誤回允許鍵清單；(2) 文件回合的 `confirm.request` 說明附欄位定義
      （S3-live A14_receipt-inject：模型猜鍵名兩度被擋後轉人）。
  R5  文件線預算 `document_budget_s()`；擷取逾時歸 `timeout`
      （S3-live A14_receipt-2：「文件擷取逾時（14s）」）。
"""
from __future__ import annotations

import json

import pytest

from services import documind_client as dm
from services.agent import document_extract as dx
from services.agent import mcp_facade as F
from services.agent.agent_session import DOCUMENT_CARRY_KEY
from services.agent.tools import action as action_tools
from services.agent.tools.confirm import (
    DOCUMENT_CONFIRM_FIELDS_PREFIX,
    MISSING_FIELDS_ASK_TEMPLATE,
    closed_keys_text,
    confirm_request,
)
from services.agent.tools.registry import openai_tool_name

from tests.unit.agent.test_assistant_documents_photos_req import (  # noqa: F401 — fixtures
    DOOR,
    FIXTURE,
    _CaptureRegistry,
    _confirm_call,
    _Extractor,
    _FileFetcher,
    _pm,
    _RealConfirmRegistry,
    _receipt_doc,
    _receipt_result,
    _rt,
    _synth_pdf,
    _clean_counts,
    _freeze_today,
    api,
)
from tests.unit.agent.test_documind_client_req import electronic_response
from tests.unit.agent.test_runtime_req import FakeProvider, _final_response

pytestmark = [pytest.mark.unit, pytest.mark.req("agentic-mcp-orchestration:R10")]

_URL = "https://relay.jgbsmart.com/d.pdf"
_SCAN_TYPED = (("address", DOOR), ("use_for", "residential"), ("size", 68.47))
_FULL_TYPED = (("city", "台北市"), ("district", "大安區"), ("address", DOOR),
               ("use_for", "residential"), ("size", 68.47), ("floor", "5樓"))


def _deed(typed) -> dx.DocumentTurnInput:
    return dx.DocumentTurnInput(status="ok", kind="building_deed",
                                facts=dx.build_deed_facts(typed), pages_seen=1,
                                pages_total=1, typed_fields=typed)


async def _confirm(payload: dict):
    return await confirm_request(
        _pm(), {"summary": "確認", "payload": json.dumps(payload, ensure_ascii=False)},
        db_pool=_RealConfirmRegistry().pool,
    )


# ════════════════════════════════════════════════════════════════════
# R2：縣市一律以 JGB 資料的寫法（「台」）上卡與送出
# ════════════════════════════════════════════════════════════════════
def test_r2_documind_city_output_uses_jgb_spelling():
    typed = dict(dm.extract_deed_fields(electronic_response()).typed_fields)
    assert typed["city"] == "台北市" and typed["district"] == "大安區"
    taipei = electronic_response()
    taipei["document_fields"]["transcript_records"][0]["謄本"]["資料管轄機關"] = "台北市大安地政事務所"
    assert dict(dm.extract_deed_fields(taipei).typed_fields)["city"] == "台北市"   # 台／臺視同
    # 比對仍兩寫法視同：門牌前綴以「臺」或「台」寫都去得掉
    assert dm.clean_address("臺北市大安區" + DOOR, "台北市", "大安區") == DOOR
    assert dm.clean_address("台北市大安區" + DOOR, "臺北市", "大安區") == DOOR
    # 正對照：JGB 錄製資料確實用「台」寫這一組（⇒ 輸出值對得到替身的物件列）
    rows = json.loads(FIXTURE.read_text(encoding="utf-8"))["estates"]
    assert any(r.get("city") == "台北市" and r.get("district") == "大安區" for r in rows)
    assert not any(r.get("city") == "臺北市" for r in rows)


async def test_r2_user_typed_city_is_written_in_jgb_spelling_and_the_double_accepts_it(api):
    payload = {"action": "estate_create", "title": DOOR, "city": "臺北市", "district": "大安區",
               "address": DOOR, "use_for": "residential"}
    res = await _confirm(payload)
    assert res.ok, res
    sent = res.data["payload"]
    assert sent["city"] == "台北市" and "・縣市：台北市" in res.data["card"]
    done = await action_tools.estate_create(_pm(), {"payload": dict(sent)})
    assert done.ok, done
    # 正對照：不經正規化、照原話送「臺北市」⇒ 替身確實拒（證明上面那筆不是空測）
    raw = dict(sent, city="臺北市")
    assert not (await action_tools.estate_create(_pm(), {"payload": raw})).ok


# ════════════════════════════════════════════════════════════════════
# R3：放行的謄本回合由程式發 `confirm.request`（⛔ 叫模型）
# ════════════════════════════════════════════════════════════════════
async def test_r3_scanned_deed_asks_city_district_without_the_model_then_follow_up_issues_card(api):
    state = {"agent": {}}
    provider = FakeProvider([])                       # 被叫到就斷言失敗
    r1 = await _rt(provider, _RealConfirmRegistry()).run_turn(
        _pm(), "幫我用這份建物謄本建立一筆物件。", state, document=_deed(_SCAN_TYPED))
    assert r1.kind == "ask", r1.answer
    assert r1.answer == MISSING_FIELDS_ASK_TEMPLATE.format(labels="縣市、行政區")
    assert provider.calls == [] and r1.trace.llm_calls == 0
    assert not r1.quick_replies                        # 程式追問：沒有確認鍵
    assert "document_program_confirm" in r1.trace.violations
    carry = state["agent"][DOCUMENT_CARRY_KEY]
    assert carry["action"] == "estate_create"
    assert [tuple(p) for p in carry["typed_fields"]] == list(_SCAN_TYPED)
    # 下一回合：使用者補一句，模型只帶縣市行政區 ⇒ 暫存補上其餘 ⇒ 出卡
    reg2 = _RealConfirmRegistry()
    p2 = {"action": "estate_create", "city": "臺北市", "district": "大安區"}
    r2 = await _rt(FakeProvider([_confirm_call(p2), _final_response()]), reg2).run_turn(
        _pm(), "臺北市大安區", state)
    assert r2.outcome["state"] == "confirm_pending", r2.answer
    payload = reg2.results[0].data["payload"]
    assert {k: payload.get(k) for k in ("title", "city", "district", "address", "use_for", "size")} == {
        "title": DOOR, "city": "台北市", "district": "大安區", "address": DOOR,
        "use_for": "residential", "size": 68.47}
    assert "floor" not in payload                      # 掃描件不取樓層（D7）
    assert DOCUMENT_CARRY_KEY not in state["agent"]


async def test_r3_electronic_deed_issues_the_card_without_the_model(api):
    provider = FakeProvider([])
    reg = _RealConfirmRegistry()
    res = await _rt(provider, reg).run_turn(
        _pm(), "幫我用這份建物謄本建立一筆物件。", {"agent": {}}, document=_deed(_FULL_TYPED))
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert provider.calls == [] and res.trace.llm_calls == 0
    payload = reg.results[0].data["payload"]
    assert payload["title"] == DOOR and payload["floor"] == "5樓" and payload["city"] == "台北市"
    assert "・物件名稱：" + DOOR in res.answer
    # 程式送出的 payload 只有 action，其餘全由暫存／覆寫段寫入（D4）
    sent = json.loads(reg.call_args[0]["args"]["payload"])
    assert set(sent) == {"action", "title"} | {k for k, _ in _FULL_TYPED}


async def test_r3_receipt_turn_still_goes_to_the_model():
    """收據 ⛔ 程式驅動（合約／項目／期限在使用者原話裡，只有模型讀得出）。正對照。"""
    provider = FakeProvider([_final_response()])
    res = await _rt(provider, _CaptureRegistry()).run_turn(
        _pm(), "幫我用這張收據建一張手動帳單。", {"agent": {}}, document=_receipt_doc())
    assert len(provider.calls) == 1
    assert "document_program_confirm" not in res.trace.violations


# ════════════════════════════════════════════════════════════════════
# R4：封閉鍵錯誤回允許鍵；文件回合 `confirm.request` 說明附欄位定義
# ════════════════════════════════════════════════════════════════════
async def test_r4_closed_key_error_lists_allowed_keys_only(api):
    bad = {"action": "manual_bill_create", "contract_ref": "79994", "title": "雜支",
           "amount": 588, "receipt_date": "2026-10-12", "date_expire": "20261130"}
    res = await _confirm(bad)
    assert not res.ok and res.error == "INVALID_INPUT"
    text = res.text_for_model or ""
    for key in ("contract_ref", "title", "total", "date_expire", "sub_title", "estate_name"):
        assert key in text
    for leak in ("contract_id", "amount", "receipt_date", "79994", "雜支"):
        assert leak not in text                          # ⛔ sys_id、⛔ 回顯模型的鍵或值
    assert text == closed_keys_text("manual_bill_create")
    assert "city" in closed_keys_text("estate_create")   # 正對照：依動作取表


def _tool_desc(tools: list, name: str):
    for t in tools:
        fn = t.get("function") or {}
        if fn.get("name") == openai_tool_name(name):
            return fn.get("description") or ""
    return None


async def test_r4_document_turn_confirm_description_carries_the_field_definition():
    seen: list = []

    def _capture(kwargs):
        seen.append(kwargs["tools"])
        return _final_response()

    reg = _CaptureRegistry(tools=("confirm.request", "jgb2.action.manual_bill_create"))
    await _rt(FakeProvider([_capture]), reg).run_turn(
        _pm(), "幫我用這張收據建一張手動帳單。", {"agent": {}}, document=_receipt_doc())
    desc = _tool_desc(seen[0], "confirm.request")
    assert desc is not None and DOCUMENT_CONFIRM_FIELDS_PREFIX in desc
    assert "total＝金額" in desc and "date_expire＝繳費期限" in desc
    assert _tool_desc(seen[0], "jgb2.action.manual_bill_create") is None   # 寫入工具仍不可見
    # 正對照：非文件回合同一個 registry ⇒ 說明不附、寫入工具可見
    seen.clear()
    await _rt(FakeProvider([_capture]), reg).run_turn(_pm(), "幫我建一張手動帳單", {"agent": {}})
    assert DOCUMENT_CONFIRM_FIELDS_PREFIX not in (_tool_desc(seen[0], "confirm.request") or "")
    assert _tool_desc(seen[0], "jgb2.action.manual_bill_create") is not None


# ════════════════════════════════════════════════════════════════════
# R5：文件線預算；擷取逾時歸 `timeout`
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("turn_s,want", [("120", 45.0), ("30", 15.0), ("200", 45.0)])
def test_r5_document_budget(monkeypatch, turn_s, want):
    monkeypatch.setenv("AGENT_TURN_TIMEOUT_S", turn_s)
    assert F.document_budget_s() == pytest.approx(want)
    monkeypatch.setenv("AGENT_TURN_TIMEOUT_S", "120")
    assert F.image_budget_s() == pytest.approx(15.0)      # 正對照：照片線不變


class _TimedExtractor(_Extractor):
    def __init__(self, result=None, *, raises=None):
        super().__init__(result)
        self.raises = raises
        self.timeouts: list = []

    async def __call__(self, data_urls, **kw):
        self.timeouts.append(kw.get("timeout_s"))
        if self.raises is not None:
            raise self.raises
        return await super().__call__(data_urls, **kw)


async def test_r5_prepare_document_turn_uses_the_document_budget(monkeypatch):
    monkeypatch.setenv("AGENT_TURN_TIMEOUT_S", "120")
    spy = _TimedExtractor(_receipt_result())
    monkeypatch.setattr(F, "_document_fetch_one", _FileFetcher(_synth_pdf()))
    monkeypatch.setattr(F, "_document_extract_pages", spy)
    await F.prepare_document_turn([], [_URL])
    assert spy.timeouts[0] > 30.0                         # 舊行為：≤ 15 秒


async def test_r5_extraction_timeout_is_timeout_not_failed(monkeypatch):
    monkeypatch.setattr(F, "_document_fetch_one", _FileFetcher(_synth_pdf()))
    monkeypatch.setattr(F, "_document_extract_pages", _TimedExtractor(
        raises=dx.DocumentExtractionError("DOCUMENT_EXTRACTION_TIMEOUT")))
    turn, _ = await F.prepare_document_turn([], [_URL])
    assert turn.status == "timeout" and turn.facts == ""
    # 正對照：其他擷取錯誤仍是 `failed`
    monkeypatch.setattr(F, "_document_extract_pages", _TimedExtractor(
        raises=dx.DocumentExtractionError("DOCUMENT_OUTPUT_NOT_JSON")))
    turn2, _ = await F.prepare_document_turn([], [_URL])
    assert turn2.status == "failed"


# ════════════════════════════════════════════════════════════════════
# S3-live 第二輪（主 session 2026-10-15）：推理強度、民國日期、辨識封閉選項
# ════════════════════════════════════════════════════════════════════
from types import SimpleNamespace  # noqa: E402

from services import image_recognition_service as irs  # noqa: E402


class _FakeOpenAI:
    """`chat.completions.create` 的替身：記下 kwargs，回固定 JSON 內容（⛔ 不連網）。"""

    def __init__(self, content: dict):
        self.kwargs: list = []
        self._content = json.dumps(content, ensure_ascii=False)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kw):
        self.kwargs.append(kw)
        usage = SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2)
        msg = SimpleNamespace(content=self._content)
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=usage)


def _fixture_tree() -> list:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["repair_categories"]


_RECOG = {"is_damage": True, "damage_type": "other", "severity": "medium", "description": "",
          "confidence": 0.9, "suggested_category": "家具", "suggested_item": "沙發",
          "suggested_reason": "", "suggested_emergency": 1, "secondary_damages": []}


# ── 1) 推理強度：gpt-6 系列 none、gpt-5 系列 low ──────────────────────────
@pytest.mark.parametrize("model,want", [("gpt-6-luna", "none"), ("gpt-6", "none"),
                                        ("gpt-5.6-luna", "low"), ("gpt-5-mini", "low")])
def test_reasoning_effort_by_model_family(model, want):
    assert dx._completion_params(model, 999)["extra_body"] == {"reasoning_effort": want}
    assert irs._completion_params(model)["extra_body"] == {"reasoning_effort": want}
    assert "extra_body" not in dx._completion_params("gpt-4o", 1)        # 正對照：舊分支不帶
    assert dx.REASONING_EFFORT_BY_PREFIX == irs.REASONING_EFFORT_BY_PREFIX


async def test_reasoning_effort_reaches_both_services(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key-for-tests")
    fake = _FakeOpenAI({"kind": "other", "page_count": 1, "unreadable": False,
                        "uncertain": [], "fields": {}, "evidence": None})
    svc = dx.DocumentExtractionService(model="gpt-6-luna", timeout_s=5, max_retries=1)
    monkeypatch.setattr(svc, "_client", lambda: fake)
    await svc.extract(["data:image/png;base64,AAAA"], timeout_s=5)
    assert fake.kwargs[0]["extra_body"] == {"reasoning_effort": "none"}
    img = irs.ImageRecognitionService(model="gpt-6-luna", detail="low", max_retries=1)
    img.client = _FakeOpenAI(_RECOG)
    await img.analyze_images(["data:image/jpeg;base64,AAAA"], max_images=None)
    assert img.client.kwargs[0]["extra_body"] == {"reasoning_effort": "none"}


# ── 2) 民國日期 ─────────────────────────────────────────────────────────
def _receipt_raw(date, evidence_date, uncertain=()):
    return {"kind": "bill_receipt", "page_count": 1, "unreadable": False,
            "uncertain": list(uncertain), "fields": {"amount": 2350, "date": date},
            "evidence": {"amount": "合計 2,350 元", "date": evidence_date}}


def _gate(raw):
    return dx.apply_evidence_gate(dx.validate_extraction(raw))


def test_prompt_defines_roc_to_ad_conversion():
    p = dx.DOCUMENT_SYSTEM_PROMPT
    assert "民國" in p and "1911" in p and "YYYY-MM-DD" in p


def test_roc_evidence_keeps_the_converted_date():
    out = _gate(_receipt_raw("2026-10-08", "收據日期：民國115年10月8日"))
    assert out["fields"]["date"] == "2026-10-08" and "date" not in out["uncertain"]
    # 正對照：西元片段照舊規則
    assert _gate(_receipt_raw("2026-10-08", "2026/10/08"))["fields"]["date"] == "2026-10-08"


def test_null_date_with_full_roc_evidence_is_filled_by_the_program():
    out = _gate(_receipt_raw(None, "收據日期：民國115年10月8日", uncertain=["date"]))
    assert out["fields"]["date"] == "2026-10-08" and "date" not in out["uncertain"]
    typed, receipt_date = dx.receipt_typed_fields(out)
    assert receipt_date == "2026-10-08" and typed == (("total", 2350),)
    # 值與民國片段不符 ⇒ 以片段的決定性換算為準
    assert _gate(_receipt_raw("2025-10-08", "民國115年10月8日"))["fields"]["date"] == "2026-10-08"


@pytest.mark.parametrize("evidence", [
    "115年10月8日",                       # 缺「民國」⇒ ⛔ 猜
    "民國115年10月8日 至 民國115年11月8日",  # 兩個不同日期 ⇒ 不填
    "民國115年2月30日",                   # 不是合法日期
    "民國115年10月",                      # 不完整
    None,
])
def test_incomplete_or_ambiguous_roc_evidence_is_not_converted(evidence):
    out = _gate(_receipt_raw(None, evidence, uncertain=["date"]))
    assert out["fields"]["date"] is None and "date" in out["uncertain"]


# ── 3) 照片辨識：`suggested_item`／`suggested_category` 封閉選項 ───────────
def test_recognition_schema_enumerates_tree_leaves_exactly():
    tree = _fixture_tree()
    schema = irs.build_recognition_schema(None, tree)
    props = schema["properties"]
    assert schema["additionalProperties"] is False and set(schema["required"]) == set(props)
    leaves = props["suggested_item"]["enum"]
    assert "沙發" in leaves and "床" in leaves and "椅子" in leaves and "" in leaves
    assert "沙發坐墊" not in leaves                      # 非逐字名稱 ⛔ 可選
    assert len(leaves) == len(set(leaves))
    want = [str(i["name"]).strip() for n in tree for i in (n.get("items") or [])]
    assert set(leaves) == set(want) | {""}
    assert "家具" in props["suggested_category"]["enum"]
    assert irs.build_recognition_schema(None, None) is None   # 沒有樹 ⇒ 不產（退回 json_object）


async def test_closed_schema_is_sent_only_when_requested(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key-for-tests")
    tree = _fixture_tree()
    svc = irs.ImageRecognitionService(model="gpt-6-luna", detail="low", max_retries=1)
    svc.client = _FakeOpenAI(_RECOG)
    res = await svc.analyze_images(["data:image/jpeg;base64,AAAA"], None, None, tree,
                                   max_images=None, closed_schema=True)
    rf = svc.client.kwargs[0]["response_format"]
    assert rf["type"] == "json_schema" and rf["json_schema"]["strict"] is True
    assert "沙發" in rf["json_schema"]["schema"]["properties"]["suggested_item"]["enum"]
    assert res["suggested_item"] == "沙發"
    # 正對照：REST 路徑（不帶旗標）照舊 json_object
    svc.client = _FakeOpenAI(_RECOG)
    await svc.analyze_images(["data:image/jpeg;base64,AAAA"], None, None, tree, max_images=None)
    assert svc.client.kwargs[0]["response_format"] == {"type": "json_object"}


async def test_mcp_recognition_batch_requests_the_closed_schema(monkeypatch):
    seen: list = []

    async def _spy(self, *a, **kw):
        seen.append(kw)
        return dict(_RECOG)

    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key-for-tests")
    monkeypatch.setattr(irs.ImageRecognitionService, "analyze_images", _spy)
    await F._image_recognize_batch(["data:image/jpeg;base64,AAAA"], category_names=["家具"],
                                   categories_tree=_fixture_tree(), db_pool=None, timeout_s=5)
    assert seen[0].get("closed_schema") is True


# ════════════════════════════════════════════════════════════════════
# S3-live A7 第二輪：模型在建單參數自填**父分類**（家具）⇒ 換成照片葉節點（椅子）
# ════════════════════════════════════════════════════════════════════
from services.agent import runtime as rt  # noqa: E402

_A7_TREE = [
    {"id": 5, "name": "家具", "items": [{"id": 51, "name": "椅子", "broken_reasons": []},
                                       {"id": 52, "name": "沙發", "broken_reasons": []}]},
    {"id": 1, "name": "水電類", "items": [{"id": 11, "name": "漏水", "broken_reasons": []}]},
]


def test_a7_normalize_records_parent_when_leaf_is_chosen():
    got = F._normalize_recognition(
        {"is_damage": True, "suggested_category": "家具", "suggested_item": "椅子"}, _A7_TREE)
    assert (got["category"], got["parent"]) == ("椅子", "家具")
    # 正對照：品項不是同大類葉節點 ⇒ 維持大類、parent 為 None
    got = F._normalize_recognition(
        {"is_damage": True, "suggested_category": "家具", "suggested_item": "漏水"}, _A7_TREE)
    assert (got["category"], got["parent"]) == ("家具", None)


def _a7_args(category):
    payload = {"action": "repair_create", "description": "椅面破了"}
    if category is not None:
        payload["category_name"] = category
    return {"payload": json.dumps(payload, ensure_ascii=False)}


_A7_SUGGESTION = {"category_name": "椅子", "parent_category_name": "家具", "item": "椅子"}


def test_a7_model_parent_category_is_replaced_by_photo_leaf():
    args, applied = rt._apply_image_suggestion_to_confirm_args(_a7_args("家具"), _A7_SUGGESTION)
    assert json.loads(args["payload"])["category_name"] == "椅子"
    assert applied == ["category_name_leaf"]


@pytest.mark.parametrize("model_value", ["水電類", "漏水", "椅子"])
def test_a7_other_model_categories_are_left_alone(model_value):
    args, applied = rt._apply_image_suggestion_to_confirm_args(_a7_args(model_value), _A7_SUGGESTION)
    assert json.loads(args["payload"])["category_name"] == model_value
    assert applied == []


def test_a7_no_parent_in_suggestion_keeps_model_value():
    sug = {"category_name": "家具", "parent_category_name": None}
    args, applied = rt._apply_image_suggestion_to_confirm_args(_a7_args("家具"), sug)
    assert json.loads(args["payload"])["category_name"] == "家具" and applied == []


def test_a7_blank_model_category_still_filled_with_leaf():
    args, applied = rt._apply_image_suggestion_to_confirm_args(_a7_args(None), _A7_SUGGESTION)
    assert json.loads(args["payload"])["category_name"] == "椅子"
    assert applied == ["category_name"]


async def test_a7_photo_turn_stores_parent_only_when_leaf_was_chosen():
    from services.agent.runtime import IMAGE_SUGGESTION_KEY, ImageTurnInput
    from tests.unit.agent.test_image_suggestion_carry_req import FakeRegistry, _identity, _runtime
    state = {"agent": {}}
    r = _runtime(FakeProvider([_final_response(answer="請問急不急？")]), FakeRegistry())
    await r.run_turn(_identity(), "椅子壞了", state,
                     image=ImageTurnInput(status="ok", facts="照片辨識到的修繕分類是「椅子」。", processed=1,
                                          total=1, suggested_category="椅子", suggested_parent_category="家具"))
    assert state["agent"][IMAGE_SUGGESTION_KEY]["parent_category_name"] == "家具"
    # 正對照：沒有父分類 ⇒ 不加鍵
    state = {"agent": {}}
    r = _runtime(FakeProvider([_final_response(answer="請問急不急？")]), FakeRegistry())
    await r.run_turn(_identity(), "椅子壞了", state,
                     image=ImageTurnInput(status="ok", facts="照片辨識到的修繕分類是「家具」。", processed=1,
                                          total=1, suggested_category="家具"))
    assert "parent_category_name" not in state["agent"][IMAGE_SUGGESTION_KEY]


async def test_a7_prepare_image_turn_carries_parent_to_the_turn_input(monkeypatch):
    from tests.unit.agent.test_image_entry_req import (
        _OK_URL, _TREE, FakeFetcher, FakeRecognizer, _recognition,
    )
    from services.agent import image_fetch
    image_fetch.reset_image_count_cap()
    monkeypatch.setattr(F, "_image_fetch_one", FakeFetcher())
    monkeypatch.setattr(F, "_image_recognize_batch", FakeRecognizer(
        results=[_recognition(suggested_category="水電類", suggested_item="漏水")]))
    turn, _ = await F.prepare_image_turn([_OK_URL], category_tree=_TREE)
    assert (turn.suggested_category, turn.suggested_parent_category) == ("漏水", "水電類")
    # 正對照：沒有細項 ⇒ 父分類為 None
    monkeypatch.setattr(F, "_image_recognize_batch", FakeRecognizer(
        results=[_recognition(suggested_category="水電類")]))
    turn, _ = await F.prepare_image_turn([_OK_URL], category_tree=_TREE)
    assert (turn.suggested_category, turn.suggested_parent_category) == ("水電類", None)
    image_fetch.reset_image_count_cap()
