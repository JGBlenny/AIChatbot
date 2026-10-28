"""unit：F12「名稱講不準時找得到」——寫入流程物件／合約名稱查無時的寬鬆比對（前篩＋AI 挑選＋程式補齊）。

計畫 `.kiro/specs/agentic-mcp-orchestration/plan-name-lenient-f12-20261022.md` §4.1～§4.5、§4.8；
凍結規則與清單 `acceptance-name-lenient-f12-20261022.md`（FR-1～FR-4、F1）。

F1 斷言 ↔ 本檔測試（逐條）：
  - 開關值域（S-10）                  → `test_f1_switch_*`
  - A-2a 關、寬鬆開 ⇒ 逐字相同、0 次模型 → `test_f1_a2a_off_lenient_on_is_identical_and_never_calls_the_model`
  - 身分負向 ⇒ API 與模型皆 0 次        → `test_f1_identity_negative_*`
  - 每回合模型呼叫 ≤1、畫面編號＝候選集 → `test_f1_typo_repair_lists_lenient_candidates_*`、`test_f1_run_once_*`
  - 送模型每列鍵＝{id,title}            → `test_f1_model_rows_keys_*`、`test_f1_ai_pick_sends_only_id_and_title_*`
  - `jgb2.query.estates`、`repair_create` 輸出不變 → `test_f1_estates_tool_and_repair_create_unchanged_*`
  - 九種壞模型輸出                      → `test_f1_bad_model_output_*`
  - log／trace 不含句子、名稱、編號     → `test_f1_log_and_trace_never_carry_sentence_name_or_id`
  - 性質測試 ≥200 組                    → `test_f1_property_*`
  - off-run 逐字相同                    → `test_f1_off_run_is_identical_to_f12_removed`
資料：真 `JGBSystemAPI`＋mock transport（`assistant_demo_vendor4.json`）或依 (role, viewer) 回列的假 API；
模型一律假（`_Provider` 的 `name_lenient_pick` 分流）。全部離線。
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from datetime import date

import pytest

from services import usage_metering
from services.agent import mcp_facade as F
from services.agent import name_match as NM
from services.agent import write_candidates as WC
from services.agent import write_forms as WF
from services.agent.agent_session import WRITE_CANDIDATES_KEY, WRITE_DRAFT_KEY
from services.agent.identity import Identity
from services.agent.tools import confirm as C
from services.agent.tools import jgb2 as jgb2_tools

from tests.unit.agent.test_runtime_req import _fake_message, _fake_response
from tests.unit.agent.test_step3_write_lifecycle_req import (  # noqa: F401 — autouse／fixture 匯入
    _env, _World, api,
)
from tests.unit.agent.test_write_draft_flow_req import (
    ASK_TEXT, OWNER, ROLE, STUDENT_ESTATE, _intent, _pm, _pool, _Provider, _Reg, _rt,
)

pytestmark = [pytest.mark.unit,
              pytest.mark.req("agentic-mcp-orchestration:plan-name-lenient-f12-20261022")]


@pytest.fixture(autouse=True)
def _fill_data_text_off(monkeypatch):
    """填欄只填答覆片（plan-fill-answer-only-20261027）：本檔的假寫入意圖不帶 `data_texts`，驗的是改前行為 ⇒ 釘住
    `AGENT_FILL_DATA_TEXT=off`（off 與改前逐字相同，FA8 (2)；on 的行為見 test_fill_data_text_req.py）。"""
    monkeypatch.setenv("AGENT_FILL_DATA_TEXT", "off")


TODAY = date(2026, 10, 17)
STUDENT_ID = "67338"                         # 「學生獨立套房可租補」，只有 12291 看得到
TYPO_STUDENT = "學生獨力套房"                 # 錯字（獨立→獨力）＋只講一半；現行關鍵字查無
TYPO_REPAIR_TEXT = f"{TYPO_STUDENT} 冷氣不冷"
NOWHERE = "火星基地"                          # fixture 沒有任何相近名稱
NOWHERE_REPAIR_TEXT = f"{NOWHERE} 冷氣不冷"
CONTRACT_TYPO = "捷士堂一廳一房"              # 合約 85516「捷仕堂大一廳一房」的錯字＋漏字


@pytest.fixture(autouse=True)
def _f12_env(monkeypatch):
    monkeypatch.delenv(NM.NAME_LENIENT_ENV, raising=False)      # 未設＝on
    monkeypatch.delenv(WF.WRITE_CANDIDATES_ENV, raising=False)  # A-2a 未設＝on
    monkeypatch.delenv(WF.PICK_RIGHT_ENV, raising=False)        # 選對紀錄未設＝on


# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------
def _ids_resp(ids) -> str:
    return json.dumps({"ids": list(ids)}, ensure_ascii=False)


_NO_RC = object()


def _intent_rc6(action: str, rechoice=_NO_RC, pick_id=None, **fields):
    """F12 r6 §11.14 第 2 點：意圖判斷呼叫的假回應另帶已選定回合的 `rechoice`（任意 JSON 值；`_NO_RC`＝不帶這個鍵）
    與 `pick_id`（`None`＝不帶）。"""
    obj = {"action": action, "fields": [{"key": k, "value": v} for k, v in fields.items()]}
    if rechoice is not _NO_RC:
        obj["rechoice"] = rechoice
    if pick_id is not None:
        obj[WF.PICK_ID_KEY] = pick_id
    return _intent(raw=json.dumps(obj, ensure_ascii=False))


class _Create:
    """假 `chat.completions.create`：記錄每次 kwargs；回固定內容、拋例外或延遲。"""

    def __init__(self, content=None, *, exc=None, delay: float = 0.0, fn=None):
        self.content, self.exc, self.delay, self.fn = content, exc, delay, fn
        self.calls: list = []

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.exc is not None:
            raise self.exc
        content = self.fn(kwargs) if self.fn is not None else self.content
        return _fake_response(_fake_message(content=content), prompt_tokens=11, completion_tokens=4)


def _sent_ids_of(kwargs) -> list:
    """模型呼叫訊息裡 nonce 資料段的編號（每列 `編號｜名稱`）。"""
    piece = kwargs["messages"][1]["content"]
    assert f":{NM.NAME_LENIENT_DATA_LABEL}>>" in piece
    return re.findall(r"^([A-Za-z0-9_-]{1,32})｜", piece, flags=re.M)


def _ctx(create=None, *, user_message="", touched=(), remaining=20.0, marks=None):
    create = create or _Create(_ids_resp(["none"]))
    return NM.NameLenientTurn(
        create_factory=lambda: create, model="fake-model", reasoning_effort=None,
        user_message=user_message, touched=touched, remaining_s=lambda: remaining,
        marks=[] if marks is None else marks)


def _tenant() -> Identity:
    return F.namespaced_identity(Identity(
        vendor_id=4, target_user="tenant", mode="b2c", role_id=ROLE, user_id=OWNER,
        session_id="f12t", api_key_id=1, entry="mcp"))


def _pm_missing(role=ROLE, user=OWNER) -> Identity:
    return F.namespaced_identity(Identity(
        vendor_id=4, target_user="property_manager", mode="b2b", role_id=role, user_id=user,
        session_id="f12m", api_key_id=1, entry="mcp"))


def _intent_cmd(action: str, target: list, **fields):
    """選定後回合的假意圖：自帶 `target` 指令清單（`[(op, value), ...]`；替身 `_adapt_intent_target` 原樣送）。"""
    obj = {"action": action, "fields": [{"key": k, "value": v} for k, v in fields.items()],
           WF.PICK_TARGET_KEY: [{"op": op, "value": value} for op, value in target]}
    return _intent(raw=json.dumps(obj, ensure_ascii=False))


async def _t(w: _World, message, script=(), *, intents=None, lenient=None):
    provider = _Provider(list(script), intents, lenient)
    rt = w.runtime(provider)
    res = await rt.run_turn(w.ident, message, w.state)
    assert rt._write_intent_calls == {}
    return res, provider


def _agent(w: _World) -> dict:
    return w.state.get("agent") or {}


def _pick_ids(res) -> list:
    return [r["value"].rsplit(":", 1)[1] for r in res.quick_replies
            if str(r.get("value", "")).startswith("pick:")]


def _transport_calls(api) -> list:
    return list(api._mock_transport.calls)


def _snap(res) -> tuple:
    """回合的使用者可見結果＋trace 標記；每回合隨機的 pending id 換成固定字（其餘逐字）。"""
    pid = res.trace.pending_id
    dumped = json.dumps([res.answer, res.outcome, res.quick_replies, list(res.trace.violations)],
                        ensure_ascii=False)
    if pid:
        dumped = dumped.replace(str(pid), "<pid>")
    return dumped, pid is None


# ════════════════════════════════════════════════════════════════════
# 開關（S-10）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("value, expected", [(None, True), ("", True), ("  ", True),
                                             ("on", True), ("off", False)])
def test_f1_switch_unset_and_empty_mean_on(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv(NM.NAME_LENIENT_ENV, raising=False)
    else:
        monkeypatch.setenv(NM.NAME_LENIENT_ENV, value)
    assert NM.name_lenient_enabled_from_env() is expected
    rt = _rt(_Provider([]), _Reg(_pool()))
    assert rt._name_lenient_on is expected


@pytest.mark.parametrize("value", ["OFF", "On", "false", "0", "1", "yes", "true"])
def test_f1_switch_other_values_fail_at_startup_with_reason(monkeypatch, caplog, value):
    monkeypatch.setenv(NM.NAME_LENIENT_ENV, value)
    with pytest.raises(ValueError) as exc:
        NM.name_lenient_enabled_from_env()
    assert NM.NAME_LENIENT_ENV in str(exc.value) and repr(value) in str(exc.value)
    with pytest.raises(ValueError):
        _rt(_Provider([]), _Reg(_pool()))
    assert NM.NAME_LENIENT_ENV in caplog.text


def test_f1_switch_effective_needs_a2a(monkeypatch):
    assert NM.name_lenient_effective_from_env() is True
    monkeypatch.setenv(WF.WRITE_CANDIDATES_ENV, "off")
    assert NM.name_lenient_effective_from_env() is False
    monkeypatch.delenv(WF.WRITE_CANDIDATES_ENV)
    monkeypatch.setenv(WF.WRITE_PROPOSAL_ENV, "off")          # A+ 關 ⇒ A-2a 不生效 ⇒ 寬鬆不生效
    assert NM.name_lenient_effective_from_env() is False
    monkeypatch.delenv(WF.WRITE_PROPOSAL_ENV)
    monkeypatch.setenv(NM.NAME_LENIENT_ENV, "off")
    assert NM.name_lenient_effective_from_env() is False


# ════════════════════════════════════════════════════════════════════
# 純函式：前篩、送模型列、補齊
# ════════════════════════════════════════════════════════════════════
ROWS = [
    {"id": 101, "title": "學生獨立套房可租補", "to_user_phone": "0912000111",
     "to_user_email": "tenant-a@example.com", "estate_id": 9001, "rent": 9000},
    {"id": "102", "title": "基隆溫馨一人宅套房", "to_user_phone": "0912000222",
     "to_user_email": "tenant-b@example.com", "estate_id": 9002},
    {"id": "103", "title": "台北文山-離塵一房(國泰)", "to_user_phone": "0912000333"},
    {"id": "104", "title": "台北文山-離塵一房(國泰)", "to_user_phone": "0912000444"},
    {"id": "105", "title": "【智慧電錶】海大質感獨立套房高級廚房可租補"},
    {"id": True, "title": "布林編號"},
    {"id": "106", "title": ""},
]
PII = ("0912000111", "0912000222", "0912000333", "0912000444", "tenant-a@example.com",
       "tenant-b@example.com", "to_user_phone", "to_user_email", "rent", "estate_id")


def test_f1_prefilter_ranks_typo_first_and_drops_bad_rows():
    ranked, scores = NM.prefilter(TYPO_REPAIR_TEXT, ROWS)
    assert ranked[0] == "101"                                     # 獨力＝獨立同音
    assert set(ranked) <= {"101", "102", "103", "104", "105"}     # 布林編號、空名稱略過
    assert all(scores[i] >= NM.NAME_LENIENT_MIN_SCORE for i in ranked)
    assert NM.prefilter(NOWHERE, ROWS) == ([], {})
    assert NM.core_units("【智慧電錶】海大(備註)套房") == NM.units("海大套房")
    many = [{"id": str(i), "title": f"套房{i}"} for i in range(80)]
    assert len(NM.prefilter("套房", many)[0]) == NM.NAME_LENIENT_PRE_K


def test_f1_model_rows_keys_are_exactly_id_and_title():
    ranked, _scores = NM.prefilter(TYPO_REPAIR_TEXT, ROWS)
    sent = NM.model_rows(ROWS, ranked)
    assert sent and all(tuple(r) == NM.MODEL_ROW_KEYS for r in sent)
    assert all(set(r) == {"id", "title"} and isinstance(r["id"], str) for r in sent)
    dumped = json.dumps(sent, ensure_ascii=False)
    for leaked in PII:
        assert leaked not in dumped


def test_f1_pick_messages_rejects_rows_with_extra_keys():
    with pytest.raises(ValueError):
        NM.pick_messages("x", [{"id": "1", "title": "a", "to_user_phone": "0912"}], "contract", "n0")
    with pytest.raises(ValueError):
        NM.pick_messages("x", [{"title": "a", "id": "1"}], "estate", "n0")    # 鍵順序也等值


def test_f1_augment_only_inside_sent_and_capped():
    sent = [{"id": str(i), "title": "同名" if i < 3 else f"別名{i}"} for i in range(10)]
    scores = {str(i): 9 - i for i in range(10)}
    assert NM.augment([], sent, scores) == []
    assert NM.augment(["999"], sent, scores) == []                # 清單外 ⇒ 空
    got = NM.augment(["1"], sent, scores)
    assert got[0] == "1" and set(got) <= {r["id"] for r in sent}
    assert len(got) <= NM.NAME_LENIENT_CAP and {"0", "2"} <= set(got)   # 同名補齊
    got = NM.augment([str(i) for i in range(10)], sent, scores)
    assert len(got) == NM.NAME_LENIENT_CAP


# ════════════════════════════════════════════════════════════════════
# AI 挑選：九種壞輸出、送出內容、呼叫次數、失敗
# ════════════════════════════════════════════════════════════════════
ALLOWED = ["101", "102", "103"]
BAD_OUTPUTS = {
    "off_list_id": (_ids_resp(["555"]), []),
    "other_viewer_id": (_ids_resp(["990002", "101"]), ["101"]),
    "free_text": ("我覺得是第一筆學生獨立套房", []),
    "json_only_in_reasoning": ('<reasoning>{"ids": ["101"]}</reasoning>我不確定', []),
    "reasoning_unterminated": ('<reasoning>{"ids": ["101"]}', []),
    "two_different_objects": ('{"ids": ["101"]} {"ids": ["102"]}', []),
    "integer_ids": ('{"ids": [101, 102]}', []),
    "more_than_50_ids": (_ids_resp([str(i) for i in range(60)] + ["101", "103"]), ["101", "103"]),
    "none_mixed_with_ids": (_ids_resp(["101", "none"]), []),
}


@pytest.mark.parametrize("case", list(BAD_OUTPUTS))
def test_f1_bad_model_output_parses_to_empty_or_in_list_only(case):
    content, expected = BAD_OUTPUTS[case]
    got = NM.parse_pick_content(content, ALLOWED)
    assert got == expected
    assert set(got) <= set(ALLOWED)


@pytest.mark.parametrize("case", list(BAD_OUTPUTS))
async def test_f1_bad_model_output_through_ai_pick_and_augment(case):
    content, expected = BAD_OUTPUTS[case]
    sent = [{"id": i, "title": f"名稱{i}"} for i in ALLOWED]
    create = _Create(content)
    picked = await NM.ai_pick(create, model="m", reasoning_effort=None, sentence="名稱",
                              sent=sent, cand_type="estate", timeout_s=5.0)
    assert list(picked.ids) == expected and len(create.calls) == 1
    out = NM.augment(picked.ids, sent, {i: 2 for i in ALLOWED})
    assert set(out) <= set(ALLOWED)
    if not expected:
        assert out == []


def test_f1_good_output_with_reasoning_prefix_is_accepted():
    assert NM.parse_pick_content('<reasoning>想一下</reasoning>{"ids": ["102", "102", "101"]}',
                                 ALLOWED) == ["102", "101"]


async def test_f1_ai_pick_sends_only_id_and_title_in_a_nonce_block(monkeypatch):
    metered: list = []
    monkeypatch.setattr(usage_metering, "add_llm_usage", lambda m, u: metered.append((m, dict(u))))
    ranked, _s = NM.prefilter(TYPO_REPAIR_TEXT, ROWS)
    sent = NM.model_rows(ROWS, ranked)
    create = _Create(_ids_resp(["101"]))
    picked = await NM.ai_pick(create, model="fake-model", reasoning_effort="low",
                              sentence=TYPO_REPAIR_TEXT, sent=sent, cand_type="contract",
                              timeout_s=5.0)
    assert picked.ids == ("101",) and picked.failed is False
    (kw,) = create.calls                                           # 恰好 1 次
    assert kw["model"] == "fake-model"
    assert kw["extra_body"] == {"reasoning_effort": "low"}
    assert kw["max_completion_tokens"] == NM.NAME_LENIENT_MAX_COMPLETION_TOKENS
    rf = kw["response_format"]["json_schema"]
    assert rf["name"] == NM.NAME_LENIENT_SCHEMA_NAME and rf["strict"] is True
    assert rf["schema"]["properties"]["ids"]["items"]["enum"] == [r["id"] for r in sent] + ["none"]
    roles = [m["role"] for m in kw["messages"]]
    assert roles == ["system", "user", "user"]
    assert "合約" in kw["messages"][0]["content"]
    piece = kw["messages"][1]["content"]
    assert piece.startswith("<<data:") and "<<end:" in piece
    assert _sent_ids_of(kw) == [r["id"] for r in sent]
    assert kw["messages"][2]["content"] == TYPO_REPAIR_TEXT
    whole = json.dumps(kw, ensure_ascii=False)
    for leaked in PII:
        assert leaked not in whole
    assert metered == [("fake-model", {"prompt_tokens": 11, "completion_tokens": 4})]
    assert (picked.prompt_tokens, picked.completion_tokens) == (11, 4)


async def test_f1_ai_pick_failures_are_empty_and_never_retry(monkeypatch):
    monkeypatch.setattr(usage_metering, "add_llm_usage", lambda *_a, **_k: None)
    sent = [{"id": "1", "title": "甲乙"}]
    boom = _Create(exc=RuntimeError("upstream exploded with 學生獨力套房"))
    p = await NM.ai_pick(boom, model="m", reasoning_effort=None, sentence="甲乙", sent=sent,
                         cand_type="estate", timeout_s=5.0)
    assert p.ids == () and p.failed and len(boom.calls) == 1
    slow = _Create(_ids_resp(["1"]), delay=0.5)
    p = await NM.ai_pick(slow, model="m", reasoning_effort=None, sentence="甲乙", sent=sent,
                         cand_type="estate", timeout_s=0.05)
    assert p.ids == () and p.failed and len(slow.calls) == 1 and p.prompt_tokens > 0
    never = _Create(_ids_resp(["1"]))
    for timeout, rows in ((0.0, sent), (-1.0, sent), (5.0, [])):
        p = await NM.ai_pick(never, model="m", reasoning_effort=None, sentence="甲乙", sent=rows,
                             cand_type="estate", timeout_s=timeout)
        assert p.ids == () and p.failed
    assert never.calls == []


async def test_f1_run_once_allows_one_lenient_per_turn_and_caches_the_same_key():
    ctx = _ctx()
    computed: list = []

    async def _compute():
        computed.append(1)
        return NM.LenientOutcome("ok", ("1",), {"1": {"id": "1", "title": "甲"}})

    a = await ctx.run_once(("k1",), _compute)
    b = await ctx.run_once(("k1",), _compute)
    c = await ctx.run_once(("k2",), _compute)
    assert a is b and a.ids == ("1",) and c is None and computed == [1] and ctx.calls == 1


async def test_f1_pick_prefilter_empty_never_calls_the_model():
    create = _Create(_ids_resp(["101"]))
    marks: list = []
    ctx = _ctx(create, marks=marks)
    out = await ctx.pick(sentence=NOWHERE, rows=ROWS, cand_type="estate", truncated=False)
    assert out.status == "ok" and out.ids == () and create.calls == [] and ctx.model_calls == 0
    assert marks == [NM.V_NAME_LENIENT_NONE]


async def test_f1_pick_deadline_too_short_never_calls_the_model():
    create = _Create(_ids_resp(["101"]))
    ctx = _ctx(create, remaining=NM.NAME_LENIENT_DEADLINE_MARGIN_S)
    out = await ctx.pick(sentence=TYPO_REPAIR_TEXT, rows=ROWS, cand_type="estate", truncated=False)
    assert out.ids == () and create.calls == []
    assert NM.V_NAME_LENIENT_MODEL_FAILED in ctx.marks


def test_f1_sentence_is_this_turn_message_only_when_the_name_was_touched():
    ctx = _ctx(user_message="整句話", touched={"estate_name"})
    assert ctx.sentence_for("estate_name", "名稱值") == "整句話"
    assert ctx.sentence_for("contract_ref", "名稱值") == "名稱值"
    ctx = _ctx(user_message="整句話", touched=())
    assert ctx.sentence_for("estate_name", "名稱值") == "名稱值"


# ════════════════════════════════════════════════════════════════════
# 假 API（依 (role, viewer) 回列、記錄出向參數）——身分負向與性質測試
# ════════════════════════════════════════════════════════════════════
class _FakeAPI:
    """`get_estate_status`／`get_contracts` 替身。列依 `(role_id, viewer_user_id)` 給；沒帶 viewer ⇒
    回整個 role 的列（＝真 JGB 不吃 viewer 時的團隊範圍；正對照「拿掉 viewer」要被抓到）。"""

    def __init__(self, estates: dict, contracts: dict):
        self.estates, self.contracts = estates, contracts
        self.calls: list = []

    def _rows(self, table: dict, role_id, viewer):
        if viewer is None:
            out, seen = [], set()
            for (role, _v), rows in table.items():
                for r in rows:
                    if role == role_id and r["id"] not in seen:
                        seen.add(r["id"])
                        out.append(r)
            return out
        return list(table.get((role_id, viewer), []))

    async def get_estate_status(self, role_id=None, keyword=None, viewer_user_id=None, **kw):
        self.calls.append(("estates", dict(role_id=role_id, keyword=keyword,
                                           viewer_user_id=viewer_user_id, **kw)))
        rows = self._rows(self.estates, role_id, viewer_user_id)
        if keyword is not None:
            k = keyword.strip()
            rows = [r for r in rows if k in r["title"] or str(r["id"]) == k]
        return {"success": True, "data": [dict(r) for r in rows]}

    async def get_contracts(self, role_id=None, viewer_user_id=None, keyword=None,
                            contract_ids=None, per_page=None, **kw):
        self.calls.append(("contracts", dict(role_id=role_id, keyword=keyword,
                                             viewer_user_id=viewer_user_id,
                                             contract_ids=contract_ids, per_page=per_page, **kw)))
        rows = self._rows(self.contracts, role_id, viewer_user_id)
        if contract_ids is not None:
            wanted = set(str(contract_ids).split(","))
            rows = [r for r in rows if str(r["id"]) in wanted]
        if keyword is not None:
            rows = [r for r in rows if keyword.strip() in r["title"]]
        return {"success": True, "data": [dict(r) for r in rows],
                "pagination": {"has_more": False}}

    async def get_bills(self, role_id=None, viewer_user_id=None, **kw):
        """延期繳費選定物件後的帳單查詢（寬鬆路徑不會走到；現行路徑走到時回空列）。"""
        self.calls.append(("bills", dict(role_id=role_id, viewer_user_id=viewer_user_id, **kw)))
        return {"success": True, "data": [], "pagination": {"has_more": False}}


_TITLES = [
    "學生獨立套房可租補", "基隆溫馨一人宅套房", "台北文山-離塵一房(國泰)", "捷仕堂大一廳一房",
    "海大質感獨立套房高級廚房可租補", "基隆獨立共生公寓雅房", "台北中正-小南門單身貴族分租套房D",
    "台北信義-市政府寵物友善單人房(永豐信用卡)", "【智慧電錶】台北大安-古亭歐風優質套房A",
    "合成展示合約 甲", "合成展示合約 乙", "測試物件", "基隆好房", "台北萬華-龍山寺溫馨雅房",
    "新北板橋-府中站前精緻套房", "桃園中壢-中原大學旁學生套房",
]
_IDENTS = [("20151", "12291"), ("20151", "990002"), ("30303", "777")]


def _universe(seed: int):
    rng = random.Random(seed)
    estates, contracts, nid = {}, {}, [100000]

    def _row(title, **extra):
        nid[0] += rng.randint(1, 9)
        return {"id": nid[0], "title": title, **extra}

    for key in _IDENTS:
        estates[key] = [_row(t, address="地址") for t in rng.sample(_TITLES, rng.randint(3, 9))]
        contracts[key] = [
            _row(t, estate_id=rng.choice(estates[key])["id"], is_history=rng.random() < 0.2,
                 to_user_phone="09%08d" % rng.randint(0, 10 ** 8 - 1),
                 to_user_email=f"u{rng.randint(1, 999)}@example.com")
            for t in rng.sample(_TITLES, rng.randint(3, 9))]
    return estates, contracts


def _mutate(rng, title: str) -> str:
    """錯字＋只講一半：換掉一個字、截掉頭尾。"""
    chars = list(title)
    i = rng.randrange(len(chars))
    chars[i] = rng.choice("力里理禮立麗曆")
    s = "".join(chars)
    a = rng.randint(0, max(0, len(s) // 4))
    b = len(s) - rng.randint(0, max(0, len(s) // 4))
    return s[a:b] or s


_PATHS = ["repair", "contract_create", "bill_contract", "bill_estate", "due_extend"]


def _payload(path: str, name: str) -> dict:
    if path == "repair":
        return {"estate_name": name, "description": "冷氣不冷"}
    if path == "contract_create":
        return {"estate_name": name, "date_start": "2026-11-01", "date_end": "2027-10-31",
                "rent": 12000, "deposit_amount": 24000, "to_user_email": "w1-test@example.com",
                "to_user_phone": "0912345678", "title": "租約甲"}
    if path == "bill_contract":
        return {"contract_ref": name, "title": "管理費", "total": 1000, "date_expire": "2026-11-30"}
    if path == "bill_estate":
        return {"estate_name": name, "title": "管理費", "total": 1000, "date_expire": "2026-11-30"}
    return {"estate_name": name, "period": "7月那期", "days": 3}


_ACTION_OF = {"repair": "repair_create", "contract_create": "contract_create",
              "bill_contract": "manual_bill_create", "bill_estate": "manual_bill_create",
              "due_extend": "bill_due_extend"}


async def _resolve(path: str, ident, payload: dict, ctx):
    """跑一次現行名稱解析（帶 `candidates=True` 與寬鬆脈絡）⇒ `(result, chosen_id)`。"""
    action = _ACTION_OF[path]
    if path == "repair":
        return await C._prepare_repair_estate(ident, action, payload, candidates=True,
                                              pick_right=True, name_lenient=ctx)
    if path == "due_extend":
        _ready, res, _bill, estate = await C._pr_resolve_bill(
            ident, action, payload, today=TODAY, program_pick=None, said={}, name_lenient=ctx)
        return res, (estate or {}).get("id")
    res, estate_id, _scope = await C._prepare_closed_action(
        ident, action, payload, candidates=True, pick_right=True, name_lenient=ctx)
    return res, estate_id


def _current_lookup_empty(path: str, api: _FakeAPI, key, name: str) -> bool:
    ref = name.strip()
    if path == "bill_contract":
        rows = api.contracts.get(key, [])
        if ref.isdigit():
            return not any(str(r["id"]) == ref for r in rows)
        return not any(ref in r["title"] for r in rows)
    return not any(ref in r["title"] or str(r["id"]) == ref for r in api.estates.get(key, []))


def _cand_type(path: str) -> str:
    return "contract" if path == "bill_contract" else "estate"


# ════════════════════════════════════════════════════════════════════
# 身分負向（S-2）：缺 role、缺 user、非 property_manager ⇒ API 與模型呼叫皆 0 次
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("who", ["no_role", "no_user", "empty_user", "tenant"])
@pytest.mark.parametrize("path", _PATHS)
async def test_f1_identity_negative_never_calls_api_or_model(monkeypatch, who, path):
    estates, contracts = _universe(7)
    fake = _FakeAPI(estates, contracts)
    monkeypatch.setattr(jgb2_tools, "_api_singleton", fake)
    ident = {"no_role": lambda: _pm_missing(role=None), "no_user": lambda: _pm_missing(user=None),
             "empty_user": lambda: _pm_missing(user="  "), "tenant": _tenant}[who]()
    create = _Create(_ids_resp(["none"]))
    ctx = _ctx(create, user_message=TYPO_STUDENT, touched={"estate_name", "contract_ref"})
    # 1) 寬鬆入口本身
    res = await C._name_lenient_result(
        ident, _ACTION_OF[path], _payload(path, TYPO_STUDENT),
        field="contract_ref" if path == "bill_contract" else "estate_name",
        cand_type=_cand_type(path), name=TYPO_STUDENT, missing_label="物件", name_lenient=ctx)
    assert res is None
    rows = await C.name_lenient_rows_for_ids(
        ident, action=_ACTION_OF[path],
        field="contract_ref" if path == "bill_contract" else "estate_name",
        cand_type=_cand_type(path), ids=["100001"])
    assert rows == []
    assert fake.calls == [] and create.calls == [] and ctx.calls == 0 and ctx.model_calls == 0
    # 2) 整條名稱解析（現行查找 ＋ 寬鬆）：寬鬆一次都不跑、模型 0 次
    await _resolve(path, ident, _payload(path, TYPO_STUDENT), ctx)
    assert create.calls == [] and ctx.calls == 0 and ctx.model_calls == 0
    lenient_lists = [c for c in fake.calls
                     if (c[0] == "estates" and c[1].get("keyword") is None)
                     or (c[0] == "contracts" and c[1].get("per_page") == NM.NAME_LENIENT_LIST_MAX)]
    assert lenient_lists == [], fake.calls


async def test_f1_identity_positive_control_same_inputs_do_call(monkeypatch):
    """正對照：同一組輸入換成完整業者身分 ⇒ 真的有出向與模型呼叫（上一支的 0 不是工具壞了）。"""
    estates, contracts = _universe(7)
    key = ("20151", "12291")
    target = estates[key][0]["title"]
    fake = _FakeAPI(estates, contracts)
    monkeypatch.setattr(jgb2_tools, "_api_singleton", fake)
    create = _Create(_ids_resp(["none"]))
    ctx = _ctx(create)
    res = await C._name_lenient_result(
        _pm(), "repair_create", _payload("repair", target[1:] + "啦"), field="estate_name",
        cand_type="estate", name=target[1:] + "啦", missing_label="物件", name_lenient=ctx)
    assert res is not None and fake.calls and len(create.calls) == 1


# ════════════════════════════════════════════════════════════════════
# 性質測試（≥200 組）
# ════════════════════════════════════════════════════════════════════
PROPERTY_CASES = 240


def _property_case(seed: int):
    rng = random.Random(seed)
    estates, contracts = _universe(seed)
    key = rng.choice(_IDENTS)
    path = rng.choice(_PATHS)
    own = (contracts if path == "bill_contract" else estates)[key]
    others = [r for k, rows in (contracts if path == "bill_contract" else estates).items()
              if k != key for r in rows]
    kind = rng.choice(["exact", "substring", "typo", "typo", "typo", "other", "garbage", "digit"])
    if kind == "exact":
        name = rng.choice(own)["title"]
    elif kind == "substring":
        t = rng.choice(own)["title"]
        name = t[: max(2, len(t) // 2)]
    elif kind == "typo":
        name = _mutate(rng, rng.choice(own)["title"])
    elif kind == "other":
        name = rng.choice(others)["title"] if others else "不存在的名稱"
    elif kind == "garbage":
        name = rng.choice(["火星基地", "隨便講講", "那個那個", "ＸＹＺ大樓", "嗯"])
    else:
        name = str(rng.randint(1, 10 ** 7))
    model_mode = rng.choice(["subset", "others", "mixed", "none", "free_text", "raise", "all"])
    other_ids = [str(r["id"]) for r in others]

    def _answer(kwargs):
        sent = _sent_ids_of(kwargs)
        if model_mode == "subset":
            return _ids_resp(rng.sample(sent, min(len(sent), rng.randint(1, 3))))
        if model_mode == "others":
            return _ids_resp(rng.sample(other_ids, min(len(other_ids), 3)) or ["none"])
        if model_mode == "mixed":
            return _ids_resp(rng.sample(sent, 1) + rng.sample(other_ids, min(2, len(other_ids))))
        if model_mode == "none":
            return _ids_resp(["none"])
        if model_mode == "free_text":
            return "應該是第一筆吧"
        if model_mode == "all":
            return _ids_resp(sent)
        raise RuntimeError("model down")

    return key, path, name, estates, contracts, _answer, model_mode


async def test_f1_property_lenient_only_after_none_never_selects_and_stays_in_identity(monkeypatch):
    """F1 性質測試 (甲)：隨機 240 組（身分 × 五條名稱解析路徑 × 名稱講法 × 假模型行為）；(乙) 缺名稱
    觸發的樣本另見 `test_f1_property_r4_missing_only_when_name_empty_asked_and_typed`。斷言：
    (1) 寬鬆路徑只在現行查無時發生（且現行查無、名稱非純數字時一定發生）；
    (2) 結果從不直接選定（⛔ 回編號、⛔ 寫 payload 的 estate_id／contract_id）；
    (3) 候選 ⊆ 送模型清單 ⊆ 本身分 API 列；
    (4) 每支出向帶 role_id 且 viewer_user_id＝本人（viewer 證據僅替身）。"""
    triggered = shown = not_found = 0
    for seed in range(PROPERTY_CASES):
        key, path, name, estates, contracts, answer, model_mode = _property_case(seed)
        fake = _FakeAPI(estates, contracts)
        monkeypatch.setattr(jgb2_tools, "_api_singleton", fake)
        role, user = key
        ident = _pm(user=user, role=role)
        field = "contract_ref" if path == "bill_contract" else "estate_name"
        create = _Create(fn=answer) if model_mode != "raise" else _Create(exc=RuntimeError("down"))
        ctx = _ctx(create, user_message=f"{name} 幫我處理", touched={field})
        payload = _payload(path, name)
        before = dict(payload)
        empty = _current_lookup_empty(path, fake, key, name)
        res, chosen = await _resolve(path, ident, payload, ctx)
        tag = (seed, path, name, model_mode)
        # (1)
        if ctx.calls:
            assert empty, tag
        if empty and not name.strip().isdigit():
            assert ctx.calls == 1, tag
        assert len(create.calls) <= 1 and ctx.model_calls <= 1, tag
        # (4)
        assert fake.calls, tag
        for _what, params in fake.calls:
            assert params["role_id"] == role and params["viewer_user_id"] == user, (tag, params)
        if not ctx.calls:
            assert create.calls == [], tag
            continue
        triggered += 1
        # (2)
        assert chosen is None, tag
        assert "estate_id" not in payload and "contract_id" not in payload, tag
        assert {k: payload[k] for k in before if k in payload} == \
            {k: before[k] for k in before if k in payload}, tag
        assert res is not None, tag
        own_ids = {str(r["id"]) for r in (contracts if path == "bill_contract" else estates)[key]}
        sent = _sent_ids_of(create.calls[0]) if create.calls else []
        # (3)
        assert set(sent) <= own_ids, tag
        if C.is_name_not_found(res) is not None:
            not_found += 1
            assert res.ok is False and res.text_for_model == NM.NAME_NOT_FOUND_TEXT, tag
            continue
        data = res.data
        assert data.get(C.NAME_LENIENT_KEY) is True, tag
        cands = [str(r["id"]) for r in data["candidates"]]
        assert cands and set(cands) <= set(sent) <= own_ids, tag
        assert len(cands) <= NM.NAME_LENIENT_CAP, tag
        assert data[C.CANDIDATE_TYPE_KEY] == _cand_type(path) and data["field"] == field, tag
        for r in data["candidates"]:
            assert "to_user_phone" not in r and "to_user_email" not in r, tag
        shown += 1
    # 量尺自證：三種結果都真的出現過（否則這支測試證明不了任何事）
    print(f"F12_PROPERTY cases={PROPERTY_CASES} triggered={triggered} shown={shown} "
          f"not_found={not_found}")
    assert triggered >= 60 and shown >= 20 and not_found >= 20, (triggered, shown, not_found)


# ════════════════════════════════════════════════════════════════════
# runtime：錯字命中、找不到、按鈕／打字選定（真 registry＋mock transport）
# ════════════════════════════════════════════════════════════════════
def _repair_intent(name: str, desc: str = "冷氣不冷"):
    return _intent("repair_create", estate_name=name, description=desc)


async def test_f1_typo_repair_lists_lenient_candidates_and_pick_issues_the_card(api):
    """FR-1、FR-2：錯字名稱 ⇒ 程式固定前言＋候選清單＋`pick:` 按鈕（⛔ 出卡）；畫面編號＝候選集 `ids`；
    本回合寬鬆模型呼叫恰 1 次、主模型 0 次；按鈕選定 ⇒ 卡上是選中那筆。"""
    w = _World()
    res, provider = await _t(w, TYPO_REPAIR_TEXT, intents=[_repair_intent(TYPO_STUDENT)],
                             lenient=[_ids_resp([STUDENT_ID])])
    assert res.answer.startswith(NM.NAME_LENIENT_LEAD_TEXT + "\n"), res.answer
    assert NM.NAME_LENIENT_TRUNCATED_NOTE not in res.answer          # fixture 83 筆 < 200
    shown = _pick_ids(res)
    assert shown and shown[0] == STUDENT_ID
    cands = _agent(w)[WRITE_CANDIDATES_KEY]
    assert cands["ids"] == shown and cands["type"] == "estate" and cands["field"] == "estate_name"
    assert len(provider.lenient_calls) == 1 and len(provider.calls) == 0
    visible = {str(r["id"]) for r in (await api.get_estate_status(
        role_id=ROLE, keyword=None, viewer_user_id=OWNER))["data"]}
    sent = _sent_ids_of(provider.lenient_calls[0])
    assert set(shown) <= set(sent) <= visible
    assert res.trace.pending_id is None and w.db.rows == []
    assert NM.shown_mark("estate", len(shown)) in res.trace.violations
    assert w.draft()["fields"]["estate_name"] == TYPO_STUDENT       # 草稿保留（⛔ 改寫成正名）
    res2, provider2 = await _t(w, f"pick:estate:{STUDENT_ID}")
    assert res2.outcome["state"] == "confirm_pending", res2.answer
    assert f"物件編號：{STUDENT_ID}" in res2.answer
    assert str(w.pending()[res2.trace.pending_id]["payload"]["estate_id"]) == STUDENT_ID
    assert provider2.lenient_calls == [] and len(provider2.calls) == 0


async def test_f1_typo_repair_typed_pick_uses_the_lenient_set_without_a_model_call(api):
    """打字選定（DSP-110 甲′）：候選集出自寬鬆路徑時，意圖呼叫的動態 enum＝候選集；寬鬆模型 0 次。"""
    w = _World()
    await _t(w, TYPO_REPAIR_TEXT, intents=[_repair_intent(TYPO_STUDENT)],
             lenient=[_ids_resp([STUDENT_ID])])
    shown = _agent(w)[WRITE_CANDIDATES_KEY]["ids"]
    raw = json.dumps({"action": "repair_create", "fields": [], WF.PICK_ID_KEY: STUDENT_ID},
                     ensure_ascii=False)
    res, provider = await _t(w, "可租補那間", intents=[_intent(raw=raw)])
    (kw,) = provider.intent_calls
    enum = kw["response_format"]["json_schema"]["schema"]["properties"][WF.PICK_ID_KEY]["enum"]
    assert enum == shown + [WF.PICK_ID_NONE]
    assert provider.lenient_calls == []
    assert WC.V_CANDIDATE_PICK_TYPED in res.trace.violations
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert f"物件編號：{STUDENT_ID}" in res.answer


async def test_f1_single_lenient_hit_is_still_listed_not_selected(api):
    """FR-2：寬鬆只有 1 筆也列候選（⛔ 直接出卡）。"""
    w = _World()
    # fixture 上「學生獨力套房 冷氣不冷」前篩 67338 得 7 分、次高 5 分 ⇒ 補齊後只有 1 筆
    res, _p = await _t(w, TYPO_REPAIR_TEXT, intents=[_repair_intent(TYPO_STUDENT)],
                       lenient=[_ids_resp([STUDENT_ID])])
    assert _pick_ids(res) == [STUDENT_ID], res.answer
    assert res.trace.pending_id is None and res.outcome["state"] == "clarifying"
    assert w.db.rows == [] and w.writes() == []


async def test_f1_typo_contract_ref_lists_contract_candidates(api):
    """合約名稱（manual_bill_create 的 contract_ref）錯字 ⇒ 合約候選；送模型清單只來自帶 viewer 的
    `get_contracts(per_page=200)`。"""
    w = _World()
    text = f"幫我開帳單：合約 {CONTRACT_TYPO}，名稱 管理費，金額 1000，期限 2026/11/30"
    res, provider = await _t(w, text, intents=[_intent(
        "manual_bill_create", contract_ref=CONTRACT_TYPO, title="管理費", total="1000",
        date_expire="2026/11/30")], lenient=[_ids_resp(["85516"])])
    assert res.answer.startswith(NM.NAME_LENIENT_LEAD_TEXT), res.answer
    assert _pick_ids(res)[0] == "85516"
    assert _agent(w)[WRITE_CANDIDATES_KEY]["type"] == "contract"
    lists = [p for _m, path, p in _transport_calls(api)
             if "contracts" in path and (p or {}).get("per_page") == NM.NAME_LENIENT_LIST_MAX]
    assert lists and all(p.get("viewer_user_id") == OWNER and p.get("role_id") == ROLE
                         and "keyword" not in p for p in lists), lists
    (kw,) = provider.lenient_calls
    whole = json.dumps(kw["messages"], ensure_ascii=False)
    assert "to_user" not in whole and "@" not in whole and not re.search(r"09\d{8}", whole)
    assert "85516" in _sent_ids_of(kw)


async def test_f1_not_found_gives_fixed_text_clears_name_and_reasks_only_the_name(api):
    """FR-3：寬鬆也落空 ⇒ `NAME_NOT_FOUND_TEXT`（⛔ 回顯原話）；草稿清掉查不到的名稱、該欄標已追問；
    下一句只補其他欄位 ⇒ 只重問名稱（⛔ 再回查不到出口）。"""
    w = _World()
    res, provider = await _t(w, NOWHERE_REPAIR_TEXT, intents=[_repair_intent(NOWHERE)])
    assert res.answer == NM.NAME_NOT_FOUND_TEXT, res.answer
    assert NOWHERE not in res.answer
    assert res.trace.pending_id is None and _pick_ids(res) == []
    draft = w.draft()
    assert "estate_name" not in draft["fields"] and draft["fields"].get("description")
    assert "estate_name" in draft["asked"], draft
    assert NM.V_NAME_LENIENT_NOT_FOUND_EXIT in res.trace.violations
    assert len(provider.calls) == 0
    assert len(provider.lenient_calls) <= 1          # fixture 上前篩 2 列（67651、68007）⇒ 1 次、AI 回 none
    res2, provider2 = await _t(w, "是漏水", intents=[_intent("repair_create", description="漏水")])
    assert res2.answer == ASK_TEXT.format(labels="物件"), res2.answer
    for exit_text in (NM.NAME_NOT_FOUND_TEXT, "系統裡查不到這個編號或名稱"):
        assert exit_text not in res2.answer
    assert provider2.lenient_calls == []


async def test_f1_due_extend_estate_typo_lists_estate_candidates_then_bills(api):
    """FR-7（含帳單延期先定物件）：延期繳費的物件名稱錯字 ⇒ 物件寬鬆候選（「選對紀錄」開），寬鬆模型 1 次、
    ⛔ 出卡。⚠️ 只驗第一段：選定物件之後的第二段（帳單 ≥2 張 ⇒ 選帳單）見執行報告「未達」一節——
    草稿裡的錯字名稱被 `_pr_fill_bill_display` 的 S-F2 名稱一致檢查擋成查無，需裁決，本檔不鎖該行為。"""
    typo = "基隆溫心一人宅"
    w = _World()
    res, provider = await _t(w, f"{typo} 7月那期 延後 3 天", intents=[_intent(
        "bill_due_extend", estate_name=typo, period="7月那期", days="3")],
        lenient=[_ids_resp(["67652"])])
    assert res.answer.startswith(NM.NAME_LENIENT_LEAD_TEXT), res.answer
    assert _pick_ids(res)[0] == "67652" and _agent(w)[WRITE_CANDIDATES_KEY]["type"] == "estate"
    assert "有效合約" in res.answer                         # 選對紀錄的物件投影（annotate=True）
    assert len(provider.lenient_calls) == 1 and res.trace.pending_id is None
    assert w.db.rows == [] and w.writes() == []


@pytest.mark.parametrize("shape", ["contract_create", "manual_bill_contract_ref"])
async def test_f1_lenient_pick_resumes_single_stage_flows_to_the_card(api, shape):
    """選定後回原流程（單段）：建合約的物件、手動帳單的合約名稱錯字 ⇒ 寬鬆候選 ⇒ 按鈕選定 ⇒ 卡上是選中那筆；
    選定回合寬鬆模型 0 次。"""
    typo = "基隆溫心一人宅"
    if shape == "contract_create":
        text = (f"{typo} 開合約 2026-11-01 到 2027-10-31 租金 12000 押金 24000 "
                "w1-test@example.com 0912345678 標題 租約甲")
        intent = _intent("contract_create", estate_name=typo, date_start="2026-11-01",
                         date_end="2027-10-31", rent="12000", deposit_amount="24000",
                         to_user_email="w1-test@example.com", to_user_phone="0912345678",
                         title="租約甲")
        pick, rid, key, line = "pick:estate:67652", "67652", "estate_id", "（編號 67652）"
    else:
        text = f"幫我開帳單：合約 {CONTRACT_TYPO}，名稱 管理費，金額 1000，期限 2026/11/30"
        intent = _intent("manual_bill_create", contract_ref=CONTRACT_TYPO, title="管理費",
                         total="1000", date_expire="2026/11/30")
        pick, rid, key, line = "pick:contract:85516", "85516", "contract_id", "（編號 85516）"
    w = _World()
    res, provider = await _t(w, text, intents=[intent], lenient=[_ids_resp([rid])])
    assert res.answer.startswith(NM.NAME_LENIENT_LEAD_TEXT) and _pick_ids(res)[0] == rid
    assert len(provider.lenient_calls) == 1 and res.trace.pending_id is None
    res2, provider2 = await _t(w, pick)
    assert res2.outcome["state"] == "confirm_pending", res2.answer
    assert line in res2.answer
    assert str(w.pending()[res2.trace.pending_id]["payload"][key]) == rid
    assert provider2.lenient_calls == [] and len(provider2.calls) == 0


def _seed_bill_draft(w: _World, contract_ref: str) -> None:
    from services.agent import runtime as runtime_mod
    w.state = {"agent": {WRITE_DRAFT_KEY: {
        "action": "manual_bill_create",
        "fields": {"contract_ref": contract_ref, "title": "管理費", "total": "1000",
                   "date_expire": "2026-11-30"},
        "idle_turns": 0, "created_by_role": runtime_mod._write_draft_owner(w.ident), "asked": []}}}


async def test_f1_b2_state_reply_uses_the_draft_name_and_lists_lenient_candidates(api):
    """B2 (3) 狀態回話（草稿欄位齊、本回合沒講名稱）⇒ 寬鬆比對用**草稿裡的名稱值**（⛔ 本句），
    列寬鬆候選；寬鬆模型恰 1 次。"""
    w = _World()
    _seed_bill_draft(w, CONTRACT_TYPO)
    res, provider = await _t(w, "我先去看一下", [_out_model()], intents=[_intent("none")],
                             lenient=[_ids_resp(["85516"])])
    assert f"{WF.TRACE_WRITE_REPLY_STATE_PREFIX}{WF.WRITE_REPLY_STATE_CANDIDATES}" in \
        res.trace.violations, res.trace.violations
    assert NM.NAME_LENIENT_LEAD_TEXT in res.answer and _pick_ids(res)[0] == "85516"
    (kw,) = provider.lenient_calls
    assert kw["messages"][2]["content"] == CONTRACT_TYPO
    assert _agent(w)[WRITE_CANDIDATES_KEY]["ids"] == _pick_ids(res)


async def test_f1_b2_state_reply_not_found_clears_the_name_and_marks_asked(api):
    w = _World()
    _seed_bill_draft(w, "火星合約")
    res, _provider = await _t(w, "我先去看一下", [_out_model()], intents=[_intent("none")])
    assert f"{WF.TRACE_WRITE_REPLY_STATE_PREFIX}{WF.WRITE_REPLY_STATE_NAME_NOT_FOUND}" in \
        res.trace.violations, res.trace.violations
    assert res.answer.endswith(NM.NAME_NOT_FOUND_TEXT) and "火星合約" not in res.answer
    draft = w.draft()
    assert "contract_ref" not in draft["fields"] and "contract_ref" in draft["asked"], draft
    assert res.trace.pending_id is None


def _out_model():
    from tests.unit.agent.test_write_draft_flow_req import _out
    return _out("模型自己寫的話。")


async def test_f1_model_none_also_gives_the_not_found_exit(api):
    """前篩有列、AI 回 none ⇒ 同一個找不到出口；寬鬆模型恰 1 次。"""
    w = _World()
    res, provider = await _t(w, TYPO_REPAIR_TEXT, intents=[_repair_intent(TYPO_STUDENT)],
                             lenient=[_ids_resp(["none"])])
    assert res.answer == NM.NAME_NOT_FOUND_TEXT and len(provider.lenient_calls) == 1


async def test_f1_exact_or_many_hits_never_trigger_lenient(api):
    """FR-4：現行查找命中 ≥1 筆 ⇒ 寬鬆 0 次（唯一出卡、多筆走 A-2a 候選）。"""
    w = _World()
    res, provider = await _t(w, f"{STUDENT_ESTATE} 冷氣不冷", intents=[_repair_intent(STUDENT_ESTATE)])
    assert res.outcome["state"] == "confirm_pending" and provider.lenient_calls == []
    w = _World()
    twin = "台北文山-離塵一房(國泰)"
    res, provider = await _t(w, f"{twin} 冷氣不冷", intents=[_repair_intent(twin)])
    assert provider.lenient_calls == [] and _pick_ids(res) == ["40303", "26007"]
    assert not res.answer.startswith(NM.NAME_LENIENT_LEAD_TEXT)


# ════════════════════════════════════════════════════════════════════
# 等價：A-2a 關、開關 off、`jgb2.query.estates`、`repair_create`
# ════════════════════════════════════════════════════════════════════
_SCENARIOS = {
    "typo": (TYPO_REPAIR_TEXT, lambda: _repair_intent(TYPO_STUDENT)),
    "nowhere": (NOWHERE_REPAIR_TEXT, lambda: _repair_intent(NOWHERE)),
    "exact": (f"{STUDENT_ESTATE} 冷氣不冷", lambda: _repair_intent(STUDENT_ESTATE)),
    "contract_typo": (
        f"幫我開帳單：合約 {CONTRACT_TYPO}，名稱 管理費，金額 1000，期限 2026/11/30",
        lambda: _intent("manual_bill_create", contract_ref=CONTRACT_TYPO, title="管理費",
                        total="1000", date_expire="2026/11/30")),
}


async def _scenario_run(api, scenario):
    text, intent = _SCENARIOS[scenario]
    before = len(api._mock_transport.calls)
    w = _World()
    res, provider = await _t(w, text, script=[], intents=[intent()],
                             lenient=[_ids_resp([STUDENT_ID, "85516"])])
    return _snap(res), _transport_calls(api)[before:], provider, w


@pytest.mark.parametrize("scenario", list(_SCENARIOS))
async def test_f1_a2a_off_lenient_on_is_identical_and_never_calls_the_model(api, monkeypatch,
                                                                           scenario):
    monkeypatch.setenv(WF.WRITE_CANDIDATES_ENV, "off")
    on, on_calls, p_on, _w = await _scenario_run(api, scenario)
    monkeypatch.setenv(NM.NAME_LENIENT_ENV, "off")
    off, off_calls, p_off, _w = await _scenario_run(api, scenario)
    assert on == off and on_calls == off_calls
    assert p_on.lenient_calls == [] and p_off.lenient_calls == []


@pytest.mark.parametrize("scenario", list(_SCENARIOS))
async def test_f1_off_run_is_identical_to_f12_removed(api, monkeypatch, scenario):
    """off-run 逐字相同：`AGENT_NAME_LENIENT=off` 與「拿掉 F12 兩個接點」（寬鬆入口恆回 None、runtime
    恆不給脈絡）的同一回合逐字相同、JGB 出向相同、寬鬆模型 0 次。"""
    monkeypatch.setenv(NM.NAME_LENIENT_ENV, "off")
    off, off_calls, p_off, _w = await _scenario_run(api, scenario)
    monkeypatch.delenv(NM.NAME_LENIENT_ENV)

    async def _never(*_a, **_k):
        return None

    from services.agent import runtime as runtime_mod
    monkeypatch.setattr(C, "_name_lenient_result", _never)
    monkeypatch.setattr(runtime_mod.AgentRuntime, "_name_lenient_ctx", lambda *a, **k: None)
    ref, ref_calls, p_ref, _w = await _scenario_run(api, scenario)
    assert off == ref and off_calls == ref_calls
    assert p_off.lenient_calls == [] and p_ref.lenient_calls == []


async def test_f1_estates_tool_and_repair_create_unchanged_on_vs_off(api, monkeypatch):
    """`jgb2.query.estates` 輸出與 `repair_create` 出卡流程：on 與 off 逐字相同（S-8：共用 adapter 不動）。"""
    out = {}
    for mode in ("on", "off"):
        if mode == "off":
            monkeypatch.setenv(NM.NAME_LENIENT_ENV, "off")
        reg = _Reg(_pool())
        tool = []
        for kw in ({"keyword": TYPO_STUDENT}, {"keyword": STUDENT_ESTATE}, {}):
            r = await reg.call(_pm(), "jgb2.query.estates", kw, 3.0, stage="M1")
            tool.append((r.ok, r.error, r.data, r.text_for_model,
                         [(p.source, p.text) for p in r.provenance]))
        snap, calls, provider, w = await _scenario_run(api, "exact")
        (card,) = [p["payload"] for p in w.pending().values()]
        out[mode] = (tool, snap, calls, card, provider.lenient_calls)
    assert out["on"] == out["off"]
    assert '"confirm_pending"' in out["on"][1][0] and out["on"][1][1] is False   # 前提：真的出了卡
    assert out["on"][4] == []


# ════════════════════════════════════════════════════════════════════
# log／trace：只記型別與筆數
# ════════════════════════════════════════════════════════════════════
async def test_f1_log_and_trace_never_carry_sentence_name_or_id(api, caplog):
    caplog.set_level(logging.DEBUG)
    w = _World()
    res1, _p = await _t(w, TYPO_REPAIR_TEXT, intents=[_repair_intent(TYPO_STUDENT)],
                        lenient=[_ids_resp([STUDENT_ID])])
    shown = _pick_ids(res1)
    w2 = _World()
    res2, _p = await _t(w2, NOWHERE_REPAIR_TEXT, intents=[_repair_intent(NOWHERE)])
    assert shown and res2.answer == NM.NAME_NOT_FOUND_TEXT              # 前提自證：兩條都真的走到
    marks = [v for res in (res1, res2) for v in res.trace.violations if v.startswith(NM.V_NAME_LENIENT_PREFIX)]
    assert marks, "寬鬆標記應出現"
    lenient_logs = [r.getMessage() for r in caplog.records
                    if r.name == NM.__name__ or NM.V_NAME_LENIENT_PREFIX in r.getMessage()]
    assert lenient_logs, "寬鬆 log 應出現（正對照）"
    for text in marks + lenient_logs:
        for secret in (TYPO_STUDENT, NOWHERE, TYPO_REPAIR_TEXT, NOWHERE_REPAIR_TEXT, STUDENT_ESTATE,
                       "冷氣不冷", *shown):
            assert secret not in text, (secret, text)
    all_logs = "\n".join(r.getMessage() for r in caplog.records)
    for secret in (TYPO_STUDENT, NOWHERE):
        assert secret not in all_logs
    trace_dump = json.dumps([list(res1.trace.violations), list(res2.trace.violations)],
                            ensure_ascii=False)
    for secret in (TYPO_STUDENT, NOWHERE, STUDENT_ID):
        assert secret not in trace_dump
    stored = json.dumps(_agent(w).get(WRITE_CANDIDATES_KEY), ensure_ascii=False)
    assert TYPO_STUDENT not in stored and TYPO_REPAIR_TEXT not in stored
    assert WRITE_DRAFT_KEY in _agent(w2)


# ════════════════════════════════════════════════════════════════════
# 主會話裁 §5.1 (A)：寬鬆來源的選定 ⇒ 程式把草稿名稱改寫成本身分清單上的系統名稱
# ════════════════════════════════════════════════════════════════════
KEELUNG_ID, KEELUNG_TITLE = "67652", "基隆溫馨一人宅套房"
KEELUNG_TYPO = "基隆溫心一人宅"
KEELUNG_JULY_BILLS = ["709739", "709740"]
KEELUNG_VALID_CONTRACTS = ["84972", "88247", "89296"]
OTHER_ESTATE_BILL = "769258"                   # 物件 68926（合約 89481）的帳單，12291 看得到


async def _due_extend_to_bill_list(w: _World):
    res, provider = await _t(w, f"{KEELUNG_TYPO} 7月那期 延後 3 天", intents=[_intent(
        "bill_due_extend", estate_name=KEELUNG_TYPO, period="7月那期", days="3")],
        lenient=[_ids_resp([KEELUNG_ID])])
    assert res.answer.startswith(NM.NAME_LENIENT_LEAD_TEXT) and _pick_ids(res)[0] == KEELUNG_ID
    assert WC.is_lenient(_agent(w)[WRITE_CANDIDATES_KEY])
    assert w.draft()["fields"]["estate_name"] == KEELUNG_TYPO        # 列候選回合 ⛔ 改寫
    res2, provider2 = await _t(w, f"pick:estate:{KEELUNG_ID}")
    return res, provider, res2, provider2


async def test_f1_rewrite_due_extend_typo_pick_estate_then_bill_issues_the_card(api):
    """(a) 延期繳費：錯字物件 ⇒ 寬鬆選物件 ⇒ 列帳單 ⇒ 選帳單 ⇒ 出延期卡，卡上物件與帳單編號正確。"""
    w = _World()
    _r1, provider1, res2, provider2 = await _due_extend_to_bill_list(w)
    assert len(provider1.lenient_calls) == 1
    assert WC.V_NAME_LENIENT_REWRITE in res2.trace.violations, res2.trace.violations
    assert w.draft()["fields"]["estate_name"] == KEELUNG_TITLE        # 系統名稱（本身分清單上那一列）
    assert sorted(_pick_ids(res2)) == KEELUNG_JULY_BILLS, res2.answer
    cands = _agent(w)[WRITE_CANDIDATES_KEY]
    assert cands["type"] == "bill" and not WC.is_lenient(cands)
    assert provider2.lenient_calls == [] and len(provider2.calls) == 0
    res3, provider3 = await _t(w, "pick:bill:709739")
    assert res3.outcome["state"] == "confirm_pending", res3.answer
    payload = w.pending()[res3.trace.pending_id]["payload"]
    assert str(payload["bill_id"]) == "709739"
    assert "709739" in res3.answer and KEELUNG_ID in res3.answer and KEELUNG_TITLE in res3.answer
    assert provider3.lenient_calls == [] and len(provider3.calls) == 0
    assert w.writes() == []                                          # 只出卡、⛔ 寫入 JGB


async def test_f1_rewrite_manual_bill_estate_typo_pick_estate_then_contract_issues_the_card(api):
    """(b) 手開帳單以物件：錯字物件 ⇒ 寬鬆選物件 ⇒ 3 份有效合約 ⇒ 選合約 ⇒ 出卡，卡上合約編號正確。"""
    w = _World()
    res, provider = await _t(
        w, f"幫我開帳單：物件 {KEELUNG_TYPO}，名稱 管理費，金額 1000，期限 2026/11/30",
        intents=[_intent("manual_bill_create", estate_name=KEELUNG_TYPO, title="管理費",
                         total="1000", date_expire="2026/11/30")],
        lenient=[_ids_resp([KEELUNG_ID])])
    assert res.answer.startswith(NM.NAME_LENIENT_LEAD_TEXT) and _pick_ids(res)[0] == KEELUNG_ID
    assert len(provider.lenient_calls) == 1
    res2, provider2 = await _t(w, f"pick:estate:{KEELUNG_ID}")
    assert WC.V_NAME_LENIENT_REWRITE in res2.trace.violations
    assert w.draft()["fields"]["estate_name"] == KEELUNG_TITLE
    assert sorted(_pick_ids(res2)) == KEELUNG_VALID_CONTRACTS, res2.answer
    assert provider2.lenient_calls == [] and len(provider2.calls) == 0
    res3, provider3 = await _t(w, "pick:contract:88247")
    assert res3.outcome["state"] == "confirm_pending", res3.answer
    payload = w.pending()[res3.trace.pending_id]["payload"]
    assert str(payload["contract_id"]) == "88247"
    assert "88247" in res3.answer
    assert provider3.lenient_calls == [] and len(provider3.calls) == 0


async def test_f1_rewrite_keeps_s_f2_other_estate_bill_is_not_found(api):
    """(c) S-F2 仍成立：寬鬆選定物件 67652（草稿已改寫成系統名稱）後，模型經 tool 路徑自帶別的物件
    （68926）的帳單編號 ⇒ 查無固定句、⛔ 出卡。正對照：同一份草稿帶 67652 自己的帳單 ⇒ 出卡。"""
    w = _World()
    await _due_extend_to_bill_list(w)
    estate_name = w.draft()["fields"]["estate_name"]
    assert estate_name == KEELUNG_TITLE
    status, row = await C.viewer_bill_row(jgb2_tools._get_api(), ROLE, OWNER, OTHER_ESTATE_BILL)
    assert status == "one" and str(row["estate_id"]) != KEELUNG_ID     # 前提：看得到、且屬別的物件
    pool = _pool()
    reg = F.build_registry(F.FacadeDeps(get_db_pool=lambda: pool, stage="M1"))
    who = F.namespaced_identity(_pm())

    async def _call(bill_id):
        args = {"summary": "確認", "payload": json.dumps({
            "action": "bill_due_extend", "estate_name": estate_name, "bill_id": bill_id, "days": 3},
            ensure_ascii=False)}
        return await reg.call(who, "confirm.request", args, timeout_s=10, stage="M1", for_model=True)

    other = await _call(OTHER_ESTATE_BILL)
    assert (other.ok, other.error) == (False, "NO_MATCH"), (other.ok, other.error, other.data)
    assert [p.source for p in other.provenance] == [jgb2_tools.NOT_FOUND_SOURCE]
    own = await _call("709739")
    assert own.ok, (own.error, own.data)
    assert own.data.get("pending_id")


async def test_f1_rewrite_exact_name_a2a_pick_flow_is_identical_to_f12_removed(api, monkeypatch):
    """(d) A-2a 精確名稱多筆（台北文山兩筆同名）的列候選＋選定出卡：開著 F12 與「F12 拿掉」逐字相同，
    候選集形狀＝A-2a 封閉鍵（⛔ 寬鬆標記），選定回合 ⛔ 改寫標記。"""
    twin = "台北文山-離塵一房(國泰)"
    text = f"{twin} 冷氣不冷"

    async def _run():
        w = _World()
        r1, p1 = await _t(w, text, intents=[_repair_intent(twin)])
        assert set(_agent(w)[WRITE_CANDIDATES_KEY]) == WC.CANDIDATE_SET_KEYS
        first = _pick_ids(r1)[0]
        r2, p2 = await _t(w, f"pick:estate:{first}")
        assert r2.outcome["state"] == "confirm_pending", r2.answer
        return [_snap(r1), _snap(r2)], (p1.lenient_calls, p2.lenient_calls), w.draft()

    on_snaps, on_lenient, on_draft = await _run()
    assert all(WC.V_NAME_LENIENT_REWRITE not in s[0] for s in on_snaps)
    assert on_lenient == ([], [])
    monkeypatch.setattr(C, "_name_lenient_result", _none_async)
    monkeypatch.setattr(_runtime_cls(), "_name_lenient_ctx", lambda *a, **k: None)
    monkeypatch.setattr(_runtime_cls(), "_name_lenient_pick_rewrite", _none_async_method)
    off_snaps, _off_lenient, off_draft = await _run()
    assert on_snaps == off_snaps
    assert on_draft == off_draft


async def _none_async(*_a, **_k):
    return None


async def _none_async_method(self, *_a, **_k):
    return None


def _runtime_cls():
    from services.agent.runtime import AgentRuntime
    return AgentRuntime


async def test_f1_rewrite_only_from_candidate_set_rows(api):
    """(e) 改寫值只來自候選集列（本身分清單上該編號那一列）：
    - 候選集外的編號（按鈕／打字）⇒ 選定不成立、⛔ 改寫；
    - `picked` 被竄改成候選集外的編號 ⇒ ⛔ 改寫；
    - `name_lenient_picked_title`：別人看得到、本人看不到的列／不存在的編號／不合形狀 ⇒ `None`；
      本人看得到的那一列 ⇒ 系統名稱（正對照）。"""
    # 按鈕帶候選集外的編號 ⇒ 失效固定句、草稿名稱不動
    w = _World()
    res, _p = await _t(w, f"{KEELUNG_TYPO} 7月那期 延後 3 天", intents=[_intent(
        "bill_due_extend", estate_name=KEELUNG_TYPO, period="7月那期", days="3")],
        lenient=[_ids_resp([KEELUNG_ID])])
    assert _pick_ids(res) == [KEELUNG_ID]
    bad, _p2 = await _t(w, "pick:estate:68926")
    assert bad.answer == WC.CANDIDATE_PICK_INVALID_TEXT
    assert WC.V_NAME_LENIENT_REWRITE not in bad.trace.violations
    assert w.draft()["fields"]["estate_name"] == KEELUNG_TYPO
    # 打字：AI 回候選集外的編號 ⇒ 不成立、⛔ 改寫
    # （不成立 ⇒ 程式依草稿重列；草稿名稱仍是錯字 ⇒ 重列回合再走一次寬鬆，假模型回同一筆）
    typed, _p3 = await _t(w, "選 68926 那一間", intents=[_intent(raw=json.dumps(
        {"action": "bill_due_extend", "fields": [], WF.PICK_ID_KEY: "68926"}))],
        lenient=[_ids_resp([KEELUNG_ID])])
    assert WC.V_NAME_LENIENT_REWRITE not in typed.trace.violations
    assert _pick_ids(typed) == [KEELUNG_ID], typed.answer
    assert w.draft()["fields"]["estate_name"] == KEELUNG_TYPO
    # `picked` 竄改成候選集外的編號：F12 r6（R6-S4）起讀回即判形狀不合（`picked ∈ ids`）；縱深防禦——
    # 未經讀回的竄改值直接送進程式改寫入口，仍不動草稿
    cands = dict(_agent(w)[WRITE_CANDIDATES_KEY], picked="68926")
    loaded, _inv = WC.load_write_candidates(cands)
    assert loaded is None and _inv is True
    assert WC.is_lenient(cands)
    rt = w.runtime(_Provider([]))
    acc = type("Acc", (), {})()
    acc.violations = []
    acc.write_draft = type("WD", (), {})()
    acc.write_draft.candidates = cands
    acc.write_draft.draft = w.draft()
    acc.write_draft.pr_anchor = None
    await rt._name_lenient_pick_rewrite(acc, w.ident, w.state)
    assert acc.violations == [] and w.draft()["fields"]["estate_name"] == KEELUNG_TYPO
    # 專用查詢：只回本身分清單上那一列的系統名稱
    owner = _pm()
    part = _pm(user="22491")
    kw = dict(action="repair_create", field="estate_name", cand_type="estate")
    assert await C.name_lenient_picked_title(owner, pick_id=STUDENT_ID, **kw) == STUDENT_ESTATE
    assert await C.name_lenient_picked_title(part, pick_id=STUDENT_ID, **kw) is None
    assert await C.name_lenient_picked_title(owner, pick_id="99999999", **kw) is None
    assert await C.name_lenient_picked_title(owner, pick_id=" 67338", **kw) is None
    assert await C.name_lenient_picked_title(_tenant(), pick_id=STUDENT_ID, **kw) is None


async def test_f1_lenient_model_call_counts_in_llm_calls(api, monkeypatch):
    """寬鬆模型呼叫計入本回合 `llm_calls`：同一句錯字報修，on 比 off 多 1。"""
    async def _run():
        w = _World()
        res, provider = await _t(w, TYPO_REPAIR_TEXT, intents=[_repair_intent(TYPO_STUDENT)],
                                 lenient=[_ids_resp([STUDENT_ID])])
        return res, provider

    on, p_on = await _run()
    assert len(p_on.lenient_calls) == 1 and _pick_ids(on)
    monkeypatch.setenv(NM.NAME_LENIENT_ENV, "off")
    off, p_off = await _run()
    assert p_off.lenient_calls == [] and not _pick_ids(off)
    assert on.trace.llm_calls == off.trace.llm_calls + 1, (on.trace.llm_calls, off.trace.llm_calls)


async def test_f1_manual_bill_estate_not_found_reasks_estate_label(api):
    """手開帳單以物件、寬鬆也落空 ⇒ 查不到固定句；下一句只補其他欄位 ⇒ 追問標籤是「物件」（⛔「合約」）。"""
    w = _World()
    res, _p = await _t(
        w, f"幫我開帳單：物件 {NOWHERE}，名稱 管理費，金額 1000，期限 2026/11/30",
        intents=[_intent("manual_bill_create", estate_name=NOWHERE, title="管理費",
                         total="1000", date_expire="2026/11/30")])
    assert res.answer == NM.NAME_NOT_FOUND_TEXT, res.answer
    assert "estate_name" not in w.draft()["fields"]
    res2, _p2 = await _t(w, "金額改 1200", intents=[_intent("manual_bill_create", total="1200")])
    assert res2.answer == ASK_TEXT.format(labels="物件"), res2.answer


# ════════════════════════════════════════════════════════════════════
# 整句來源（計畫 §4.2）：名稱在前一回合講、這回合只補欄位 ⇒ 用草稿裡的名稱欄值當整句——
# 即使本回合的合併（意圖呼叫依對話歷史把同一個名稱再吐一次、值閘比對整段會話原話而放行）
# 把名稱鍵又加進 `touched`。主會話實測（常駐容器、mock JGB）：第 1 句講名稱、第 2 句只補日期／
# 租金／Email ⇒ 寬鬆用了第 2 句 ⇒ `name_lenient:none` ⇒ 查不到固定句（3/3）。
# ════════════════════════════════════════════════════════════════════
_CC_TYPO = "基隆溫心一人宅"                       # 物件 67652「基隆溫馨一人宅套房」的錯字＋只講一半
_CC_REST = dict(date_start="2026-11-01", date_end="2027-10-31", rent="12000",
                deposit_amount="24000", to_user_email="w1-test@example.com",
                to_user_phone="0912345678", title="租約甲")
_CC_REST_TEXT = ("2026-11-01 到 2027-10-31 租金 12000 押金 24000 "
                 "w1-test@example.com 0912345678 標題 租約甲")
_MB_REST = dict(title="管理費", total="1000", date_expire="2026/11/30")
_MB_REST_TEXT = "名稱 管理費，金額 1000，期限 2026/11/30"
_TURN1_TEXT = {"contract_create": f"{_CC_TYPO}那間要新增合約",
               "manual_bill_contract_ref": f"合約 {CONTRACT_TYPO} 要開一張帳單"}


async def _name_first_then_rest(api, shape, *, turn2_text=None, rid_lenient, script=()):
    """第 1 句只講名稱（表單不齊 ⇒ 程式追問其他欄位、⛔ 查找）；第 2 句補齊其他欄位，意圖呼叫把
    第 1 句的名稱**再吐一次**（同值）⇒ 名稱鍵進本回合 `touched`。回第 2 回合 `(res, provider, w)`。

    r5：第 1 句在 (丙) 名稱先查生效時會當回合就查（FR-11）——本 helper 測的是 r4 R1／R4（名稱留在草稿、
    下一回合才查），故第 1 句在 `AGENT_NAME_LENIENT=off` 下送（等同 r5 之前的第 1 回合：名稱進草稿、
    ⛔ 查找），第 2 句回到呼叫端的開關值。(丙) 自己的行為見 `test_f12_name_early_r5_req.py`。"""
    w = _World()
    if shape == "contract_create":
        key, name, action = "estate_name", _CC_TYPO, "contract_create"
        text1, rest, rest_text = _TURN1_TEXT[shape], _CC_REST, _CC_REST_TEXT
    else:
        key, name, action = "contract_ref", CONTRACT_TYPO, "manual_bill_create"
        text1, rest, rest_text = _TURN1_TEXT[shape], _MB_REST, _MB_REST_TEXT
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv(NM.NAME_LENIENT_ENV, "off")
        res1, p1 = await _t(w, text1, intents=[_intent(action, **{key: name})])
    assert p1.lenient_calls == [] and res1.outcome["state"] == "clarifying", res1.answer
    assert w.draft()["fields"][key] == name and w.draft()["action"] == action
    res2, p2 = await _t(w, turn2_text or rest_text, script,
                        intents=[_intent(action, **{key: name}, **rest)],
                        lenient=[_ids_resp([rid_lenient])])
    return res2, p2, w


@pytest.mark.parametrize("shape, rid, ctype", [("contract_create", "67652", "estate"),
                                               ("manual_bill_contract_ref", "85516", "contract")])
async def test_f1_name_in_turn1_rest_in_turn2_uses_the_draft_name_even_if_merge_retouches(
        api, monkeypatch, shape, rid, ctype):
    """FR-1／§4.2（R1 回歸＋r4 R4）：名稱前一回合講、本回合只補欄位，合併把名稱鍵又加進 `touched`（同值）
    ⇒ 不算本回合講過（⛔ 用本回合補欄位那句）；r4 起整句＝最近一則含名稱欄值的既有使用者訊息（第 1 句）；
    目標成為候選、⛔ 查不到固定句。"""
    from services.agent import runtime as runtime_mod
    seen: list = []
    orig = runtime_mod.AgentRuntime._name_lenient_ctx

    def _spy(self, acc, *a, **k):
        out = orig(self, acc, *a, **k)
        if out is not None:
            seen.append(set(acc.write_draft.touched))
        return out

    monkeypatch.setattr(runtime_mod.AgentRuntime, "_name_lenient_ctx", _spy)
    res, provider, w = await _name_first_then_rest(api, shape, rid_lenient=rid)
    key = "estate_name" if ctype == "estate" else "contract_ref"
    # 前提自證：本回合的合併確實把名稱鍵加回 `touched`（缺陷的觸發形狀）
    assert seen and all(key in t for t in seen), seen
    assert res.answer != NM.NAME_NOT_FOUND_TEXT, res.answer
    (kw,) = provider.lenient_calls
    turn1 = _TURN1_TEXT[shape]
    rest_text = _CC_REST_TEXT if ctype == "estate" else _MB_REST_TEXT
    assert kw["messages"][2]["content"] == turn1                     # R4：第 1 句（含名稱）
    assert kw["messages"][2]["content"] != rest_text                 # R1：⛔ 本回合補欄位那句
    assert res.answer.startswith(NM.NAME_LENIENT_LEAD_TEXT) and _pick_ids(res)[0] == rid, res.answer
    cands = _agent(w)[WRITE_CANDIDATES_KEY]
    assert cands["type"] == ctype and cands["field"] == key and cands["ids"] == _pick_ids(res)
    assert res.trace.pending_id is None and w.writes() == []


@pytest.mark.parametrize("shape, rid", [("contract_create", "67652"),
                                        ("manual_bill_contract_ref", "85516")])
async def test_f1_name_said_again_this_turn_still_uses_the_whole_sentence(api, shape, rid):
    """§4.2「整句＝這一回合使用者原話」：本回合使用者句子裡有草稿名稱值 ⇒ 整句（行為不變）。"""
    name = _CC_TYPO if shape == "contract_create" else CONTRACT_TYPO
    rest_text = _CC_REST_TEXT if shape == "contract_create" else _MB_REST_TEXT
    turn2 = f"{name} {rest_text}"
    res, provider, _w = await _name_first_then_rest(api, shape, turn2_text=turn2, rid_lenient=rid)
    (kw,) = provider.lenient_calls
    assert kw["messages"][2]["content"] == turn2
    assert _pick_ids(res)[0] == rid, res.answer


def test_f1_name_said_this_turn_uses_normalized_containment():
    """名稱算「本回合講了」的判準：NFKC、大小寫、空白與標點都不計（全形／半形、多空白、標點夾雜）。"""
    from services.agent import runtime as runtime_mod
    said = runtime_mod._name_said_in_message
    assert said("Ａ棟 101室", "請幫我 a棟101 室，開合約")
    assert said("捷仕堂大一廳一房", "合約：捷仕堂、大一廳一房 要開帳單")
    assert not said("海大套房", "2026-11-01 到 2027-10-31 租金 12000")
    assert not said("", "任何句子") and not said("海大套房", "") and not said(None, "海大套房")
    assert not said("，。", "，。")                        # 只剩標點 ⇒ 空鍵 ⇒ 不算講了


# ════════════════════════════════════════════════════════════════════
# r4（計畫 §4.2 (乙)／R4、§4.3、§4.5；清單 F1 r4 項、FR-3、FR-9、FR-10；資安 S-13～S-15）
# ════════════════════════════════════════════════════════════════════
_KEELUNG_TURN_ASK = f"{_CC_TYPO}那間要新增合約"                       # 意圖呼叫沒抽到物件名稱（R3 形狀）
_MB_TURN_ASK = f"合約 {CONTRACT_TYPO} 要開一張帳單，名稱 管理費"      # 意圖呼叫沒抽到合約名稱（R3 形狀）
_R4_SHAPES = {
    # shape: (本句, 意圖（缺名稱欄）, 名稱欄, 型別, 目標編號, 系統名稱, 名稱欄標籤)
    "estate_contract_create": (_KEELUNG_TURN_ASK, lambda: _intent("contract_create"),
                               "estate_name", "estate", KEELUNG_ID, KEELUNG_TITLE, "物件"),
    "contract_manual_bill": (_MB_TURN_ASK, lambda: _intent("manual_bill_create", title="管理費"),
                             "contract_ref", "contract", "85516", "捷仕堂大一廳一房", "合約"),
}


def _r4_ctx(create=None, *, user_message="", typed=True, user_texts=(), reask_key=None, marks=None):
    create = create or _Create(_ids_resp(["none"]))
    texts = list(user_texts)
    return C.NameLenientTurnCtx(
        create_factory=lambda: create, model="fake-model", reasoning_effort=None,
        user_message=user_message, touched=(), remaining_s=lambda: 20.0,
        marks=[] if marks is None else marks, user_texts=lambda: texts, typed=typed,
        reask_key=reask_key)


def _labels_of(action: str, payload: dict) -> list:
    return WF.missing_labels(action, {"action": action, **payload})


@pytest.mark.parametrize("shape", list(_R4_SHAPES))
async def test_f1_r4_missing_name_lists_candidates_then_pick_resumes_and_asks_the_rest(api, shape):
    """(乙) 缺名稱觸發：物件型（建合約）與合約型（手開帳單）各一。名稱沒進草稿 ⇒ 以**本句**寬鬆比對、
    (乙) 專用固定前言＋候選（⛔ 出卡、⛔ 草稿寫名稱）；按鈕選定 ⇒ 草稿名稱＝系統名稱、回原流程只追問其餘欄位。"""
    text, intent, key, ctype, rid, title, label = _R4_SHAPES[shape]
    w = _World()
    res, provider = await _t(w, text, intents=[intent()], lenient=[_ids_resp([rid])])
    # (乙) 專用固定前言，⛔ (甲) 前言、⛔ 回顯原話
    assert res.answer.startswith(C.NAME_LENIENT_MISSING_LEAD_TEXT + "\n"), res.answer
    assert NM.NAME_LENIENT_LEAD_TEXT not in res.answer and NM.NAME_NOT_FOUND_TEXT not in res.answer
    lead = res.answer.split("\n", 1)[0]
    assert lead == C.NAME_LENIENT_MISSING_LEAD_TEXT and text not in res.answer
    assert C.V_NAME_LENIENT_TRIGGER_MISSING in res.trace.violations
    assert C.V_NAME_LENIENT_TRIGGER_NOTFOUND not in res.trace.violations
    (kw,) = provider.lenient_calls                                  # 本回合寬鬆模型恰 1 次
    assert kw["messages"][2]["content"] == text                     # 整句＝本回合原話
    assert len(provider.calls) == 0 and res.trace.pending_id is None
    shown = _pick_ids(res)
    assert shown and shown[0] == rid
    cands = _agent(w)[WRITE_CANDIDATES_KEY]
    assert cands["ids"] == shown and cands["type"] == ctype and cands["field"] == key
    assert cands["name_fp"] == WC.name_fp("") and WC.is_lenient(cands)
    assert key not in w.draft()["fields"]                          # 列候選回合 ⛔ 寫名稱
    # 選定 ⇒ 回原流程：草稿名稱改寫成系統名稱；只追問其餘欄位（⛔ 再問名稱、⛔ 再跑寬鬆）
    res2, provider2 = await _t(w, f"pick:{ctype}:{rid}")
    assert WC.V_NAME_LENIENT_REWRITE in res2.trace.violations, res2.trace.violations
    assert w.draft()["fields"][key] == title
    assert res2.outcome["state"] == "clarifying", res2.answer
    rest = _labels_of(w.draft()["action"], {k: v for k, v in w.draft()["fields"].items()})
    assert rest and label not in rest
    assert res2.answer == ASK_TEXT.format(labels="、".join(rest)), res2.answer
    assert provider2.lenient_calls == [] and len(provider2.calls) == 0
    assert C.V_NAME_LENIENT_TRIGGER_MISSING not in res2.trace.violations
    assert w.writes() == []


# ════════════════════════════════════════════════════════════════════
# F12 P2-1（F8 驗證員）：寬鬆選定後補齊欄位那一回合，合併把客人前面講的名稱再吐一次 ⇒ ⛔ 蓋掉系統名稱、
# ⛔ 再列候選；直接依選定編號出卡（清單 F1「選定後下一回合追問其餘欄位、出卡時依選定編號精確查」）。
# F12 r6（計畫 §11.4 第 4、5 點；r6 清單 F1 但書「p21／p2a 各支改寫為 r6 契約」）：擋下改由選定後的名稱合併
# 規則（`_write_candidates_name_rule`）決定——候選集內講法、不是本回合講的 ⇒ 丟棄（`write_candidate_name_kept`）；
# 候選集外且本回合講 ⇒ 依新名稱重查（`write_candidate_name_new`）。⛔ 以「名稱在選定標記前或後」判斷（FR-15）。
# ════════════════════════════════════════════════════════════════════
_P21_SPOKEN = {"estate_contract_create": _CC_TYPO, "contract_manual_bill": CONTRACT_TYPO}
_P21_REST = {"estate_contract_create": (_CC_REST, _CC_REST_TEXT, "estate_id"),
             "contract_manual_bill": (_MB_REST, _MB_REST_TEXT, "contract_id")}


async def _p21_pick_then_ask(w: _World, shape: str):
    text, intent, key, ctype, rid, title, _label = _R4_SHAPES[shape]
    res, _p = await _t(w, text, intents=[intent()], lenient=[_ids_resp([rid])])
    assert _pick_ids(res)[0] == rid, res.answer
    res2, _p2 = await _t(w, f"pick:{ctype}:{rid}")
    assert WC.V_NAME_LENIENT_REWRITE in res2.trace.violations
    assert res2.outcome["state"] == "clarifying" and w.draft()["fields"][key] == title
    return key, rid, title


@pytest.mark.parametrize("shape", list(_R4_SHAPES))
async def test_f1_p21_fill_turn_after_lenient_pick_issues_the_card_by_picked_id(api, shape):
    """V04／V12 形狀：選定 ⇒ 追問其餘欄位 ⇒ 客人只補欄位、意圖呼叫把第 1 句的錯字名稱再吐一次 ⇒
    草稿名稱維持系統名稱、⛔ 寬鬆再觸發、⛔ 再列候選；直接出卡，卡上是選定那一筆。
    r6：該名稱值不出自本回合原話 ⇒ 名稱合併規則丟棄、trace `write_candidate_name_kept`。"""
    w = _World()
    key, rid, title = await _p21_pick_then_ask(w, shape)
    action = w.draft()["action"]
    rest, rest_text, id_key = _P21_REST[shape]
    res3, p3 = await _t(w, rest_text, intents=[_intent(action, **{key: _P21_SPOKEN[shape]}, **rest)])
    assert res3.outcome["state"] == "confirm_pending", res3.answer
    assert str(w.pending()[res3.trace.pending_id]["payload"][id_key]) == rid
    assert w.draft()["fields"][key] == title
    assert WC.V_CANDIDATE_NAME_KEPT in res3.trace.violations, res3.trace.violations
    assert WC.V_CANDIDATE_NAME_NEW not in res3.trace.violations
    assert not [v for v in res3.trace.violations if v.startswith("name_lenient:trigger:")]
    assert p3.lenient_calls == [] and _pick_ids(res3) == []
    assert w.writes() == []


@pytest.mark.parametrize("shape", list(_R4_SHAPES))
async def test_f1_p21_control_without_guard_relists_the_candidates(api, monkeypatch, shape):
    """正對照（r6 清單 F1 (h)「名稱合併改成照收不驗來源」）：名稱合併規則恆回 `None`（照現行合併）⇒ 同一段
    對話重現 P2-1（寬鬆 notfound 再觸發、再列候選、⛔ 出卡）。"""
    monkeypatch.setattr(_runtime_cls(), "_write_candidates_name_rule", lambda *a, **k: None)
    w = _World()
    key, rid, _title = await _p21_pick_then_ask(w, shape)
    action = w.draft()["action"]
    rest, rest_text, _id_key = _P21_REST[shape]
    res3, p3 = await _t(w, rest_text, intents=[_intent(action, **{key: _P21_SPOKEN[shape]}, **rest)],
                        lenient=[_ids_resp([rid])])
    assert res3.trace.pending_id is None, res3.answer
    assert C.V_NAME_LENIENT_TRIGGER_NOTFOUND in res3.trace.violations, res3.trace.violations
    assert _pick_ids(res3) == [rid] and len(p3.lenient_calls) == 1


@pytest.mark.parametrize("shape", list(_R4_SHAPES))
async def test_f1_p21_name_said_again_this_turn_is_not_kept(api, shape):
    """本回合客人自己又講了名稱（錯字、候選集外）。r6：(乙) 來源的原講法是空字串，依新名稱解綁重查（FR-13）。
    選定後回合改指令式（計畫 `plan-post-pick-commands-20261024.md` §4.3）：意圖 `fields` 的名稱值一律丟棄，
    改講清單以外的名稱只認 AI 回的 `name` 指令（程式驗過候選集外且本回合講）⇒ 假模型改回 `name` 指令。
    修復輪 1（§8.2 點 2）：解綁前先用新名稱做一次前置查找；寬鬆查找的列含現在選定的那筆 ⇒ 維持選定、還原名稱
    （`write_candidate_name_precheck:keep`、⛔ `write_candidate_name_new`），同回合只打一次寬鬆模型，卡是選定的那筆。"""
    w = _World()
    key, rid, _title = await _p21_pick_then_ask(w, shape)
    action = w.draft()["action"]
    rest, rest_text, id_key = _P21_REST[shape]
    spoken = _P21_SPOKEN[shape]
    assert _agent(w)[WRITE_CANDIDATES_KEY][WC.ORIGIN_KEY] == ""          # 前提：(乙) 原講法為空字串
    res3, p3 = await _t(w, f"{spoken} {rest_text}",
                        intents=[_intent_cmd(action, [("name", spoken)], **{key: spoken}, **rest)],
                        lenient=[_ids_resp([rid])])
    assert WC.V_CANDIDATE_NAME_PRECHECK_KEEP in res3.trace.violations, res3.trace.violations
    assert WC.V_CANDIDATE_NAME_NEW not in res3.trace.violations, res3.trace.violations
    assert C.V_NAME_LENIENT_TRIGGER_NOTFOUND in res3.trace.violations, res3.trace.violations
    assert len(p3.lenient_calls) == 1 and res3.trace.pending_id is not None, res3.answer
    assert str(w.pending()[res3.trace.pending_id]["payload"][id_key]) == str(rid)


async def test_f1_p2a_retract_in_own_turn_then_fill_issues_the_new_one(api):
    """第 2 次 F8 P2-A（N15 形狀）改寫為 r6 契約：寬鬆選定 A ⇒ 單獨一句改口要候選集外的 B（AI 有抽到 B）⇒
    名稱合併規則判候選集外且本回合講 ⇒ `write_candidate_name_new`、解綁、依新名稱重查（B 精確唯一、其餘欄位仍缺
    ⇒ 追問、⛔ 出卡）；下一回合只補欄位 ⇒ 卡＝B、⛔ 卡出已撤回的 A。
    （r5 版本是「改口那句意圖沒抽到 B、下一回合才把 B 吐出來」——r6 不再以原話位置猜改口，那種 AI 理解
    失敗的形狀屬計畫 §11.5 已知取捨，由 F10 量。）
    選定後回合改指令式：改講清單以外的名稱 ⇒ AI 回 `name` 指令 ⇒ 假模型照此回。"""
    w = _World()
    key, rid, title = await _p21_pick_then_ask(w, "estate_contract_create")
    retract = f"改成 {STUDENT_ESTATE} 那間"
    res3, _p3 = await _t(w, retract, intents=[_intent_cmd("contract_create", [("name", STUDENT_ESTATE)],
                                                          **{key: STUDENT_ESTATE})])
    assert WC.V_CANDIDATE_NAME_NEW in res3.trace.violations, res3.trace.violations
    assert w.draft()["fields"][key] == STUDENT_ESTATE and res3.trace.pending_id is None, res3.answer
    assert WRITE_CANDIDATES_KEY not in _agent(w) or _agent(w)[WRITE_CANDIDATES_KEY] is None
    rest, rest_text, id_key = _P21_REST["estate_contract_create"]
    res4, _p4 = await _t(w, rest_text, intents=[_intent("contract_create", **{key: STUDENT_ESTATE}, **rest)])
    assert w.draft() is None or w.draft()["fields"].get(key) in (STUDENT_ESTATE, None)
    assert res4.outcome["state"] == "confirm_pending", res4.answer
    assert str(w.pending()[res4.trace.pending_id]["payload"][id_key]) == STUDENT_ID != rid


async def test_f1_p2a_control_old_this_turn_rule_loses_the_new_name(api, monkeypatch):
    """正對照（r6 清單 F1 (d)「在本回合原話 ⇒ 解綁、依新名稱重查」）：名稱合併規則把「候選集外且本回合講」改判
    丟棄 ⇒ 改口那句的新名稱被丟（⛔ `write_candidate_name_new`），下一回合的卡不是新名稱那筆（上一支失敗）。
    r6 §11.14：改口那回合 AI 回 `rechoice=retract` ⇒ 程式另把選定撤回、重列，所以 r5 的 P2-A 形狀（卡出已撤回的
    A）不再出現；原名 `..._reproduces_the_retracted_card` 依此改名。
    F12 r6 復原第 5 輪（§11.15.3 第 6 點）：選定後且意圖解析成功的回合，名稱欄值先收集、由單次決定判「改講新名稱」——
    「候選集外且本回合講」的判定抽成 `_write_candidates_name_is_new`（名稱合併規則與單次決定共用），暫改處隨之改成它
    （改判否＝原暫改的「new ⇒ drop」）。"""
    monkeypatch.setattr(_runtime_cls(), "_write_candidates_name_is_new", lambda self, *a, **k: False)
    w = _World()
    key, rid, _title = await _p21_pick_then_ask(w, "estate_contract_create")
    res3, _p3 = await _t(w, f"改成 {STUDENT_ESTATE} 那間",
                         [_fake_response(_fake_message(content="想處理哪一件事？"))] * 3,
                         intents=[_intent_rc6("contract_create", "retract", WF.PICK_ID_NONE,
                                              **{key: STUDENT_ESTATE})])
    assert WC.V_CANDIDATE_NAME_NEW not in res3.trace.violations, res3.trace.violations
    rest, rest_text, id_key = _P21_REST["estate_contract_create"]
    res4, _p4 = await _t(w, rest_text, intents=[_intent("contract_create", **{key: STUDENT_ESTATE}, **rest)])
    assert (res4.trace.pending_id is None
            or str(w.pending()[res4.trace.pending_id]["payload"][id_key]) != STUDENT_ID), res4.answer


async def test_f1_p2a_said_before_pick_only_boundaries(api):
    """r6 改寫（原 `_name_said_before_pick_only` 判準已移除，FR-15）：選定後名稱合併規則
    `_write_candidates_name_rule` 的分類邊界（計畫 §11.4 第 4 點）——候選集內講法（等於或被包含於原講法、
    被包含於本回合帶身分取得的候選正名）⇒ 丟棄；包含原講法的較長名稱、本回合講 ⇒ 新名稱；不是本回合講 ⇒
    丟棄；本回合已改選、`pick_id`＝選定 ⇒ 丟棄；同值 ⇒ `same`；非名稱欄、空值、解綁 ⇒ 不適用。"""
    from services.agent import runtime as runtime_mod
    w = _World()
    # (甲) 寬鬆：講法「基隆溫心一人宅」⇒ 寬鬆列 KEELUNG ⇒ 選定 ⇒ 原講法存正規化字串
    res, _p = await _t(w, f"{_CC_TYPO}那間要新增合約", intents=[_intent("contract_create", estate_name=_CC_TYPO)],
                       lenient=[_ids_resp([KEELUNG_ID])])
    assert _pick_ids(res) == [KEELUNG_ID], res.answer
    await _t(w, f"pick:estate:{KEELUNG_ID}")
    cands = _agent(w)[WRITE_CANDIDATES_KEY]
    assert cands["picked"] == KEELUNG_ID and cands[WC.ORIGIN_KEY] == runtime_mod._name_said_key(_CC_TYPO)
    rt = w.runtime(_Provider([]))
    f = WF.FORMS["contract_create"].field("estate_name")
    other = WF.FORMS["contract_create"].field("rent")

    def acc_for(message, *, pid=None, repick=None, rows=None, draft=None):
        wd = runtime_mod._WriteDraftTurn(draft=draft or w.draft(), owner="x", user_texts=[message])
        wd.candidates = dict(cands)
        wd.user_message = message
        wd.intent_consumed = True
        wd.intent_pick_id = pid
        wd.pick_offered = (KEELUNG_ID,)
        wd.repick_target = repick
        wd.offered_rows = {KEELUNG_ID: {"id": KEELUNG_ID, "title": KEELUNG_TITLE}} if rows is None else rows
        acc = type("Acc", (), {})()
        acc.violations, acc.write_draft = [], wd
        return acc

    def rule(raw, message, **kw):
        return rt._write_candidates_name_rule(acc_for(message, **kw), w.ident, f, raw, defer=False)

    assert rule(_CC_TYPO, "電話 0912345678") == "drop"                       # 不是本回合講
    assert rule(_CC_TYPO, f"{_CC_TYPO} 電話 0912345678") == "drop"           # ＝原講法（本回合重述）
    assert rule("溫心一人宅", "溫心一人宅 電話") == "drop"                     # 被包含於原講法
    assert rule("溫馨一人宅", "溫馨一人宅 電話") == "drop"                     # 被包含於候選正名
    assert rule("溫馨一人宅", "溫馨一人宅 電話", rows={}) == "new"            # 本回合取列失敗 ⇒ 只套原講法
    assert rule(f"{_CC_TYPO}二館", f"{_CC_TYPO}二館 電話") == "new"          # 包含原講法的較長名稱 ⇒ 重查
    assert rule(STUDENT_ESTATE, f"改成 {STUDENT_ESTATE}") == "new"           # 候選集外、本回合講
    assert rule(STUDENT_ESTATE, f"改成 {STUDENT_ESTATE}", repick="99") == "drop"   # 本回合已改選
    assert rule(STUDENT_ESTATE, f"改成 {STUDENT_ESTATE}", pid=KEELUNG_ID) == "drop"  # pick_id＝選定
    assert rule(KEELUNG_TITLE, KEELUNG_TITLE) == "same"                     # 與草稿現值相同
    assert rt._write_candidates_name_rule(acc_for("租金 12000"), w.ident, other, "12000",
                                          defer=False) is None              # 非候選集那一欄
    assert rule("  ", "  ") is None and rule(None, "x") is None             # 空值、非字串
    unbound = dict(w.draft(), fields=dict(w.draft()["fields"], estate_name="別的名稱"))
    assert rule(STUDENT_ESTATE, f"改成 {STUDENT_ESTATE}", draft=unbound) is None   # 解綁 ⇒ 不適用
    acc = acc_for("x")
    acc.write_draft.intent_consumed = False
    assert rt._write_candidates_name_rule(acc, w.ident, f, STUDENT_ESTATE, defer=True) == "defer"


async def test_f1_p21_model_proposal_with_spoken_name_keeps_the_pick(api):
    """模型自呼 `confirm.request`（提議）帶第 1 句的錯字名稱、意圖呼叫沒抽名稱 ⇒ 同樣擋下、依選定編號出卡。
    r6：提議的名稱值暫存到拿到 `pick_id` 之後才依名稱合併規則處理（判定順序 N-1）⇒ 不是本回合講 ⇒ 丟棄；
    提議轉成的程式呼叫也帶 `program_pick`（V7-2）。"""
    from tests.unit.agent.test_runtime_req import _tool_call_response
    shape = "estate_contract_create"
    w = _World()
    key, rid, title = await _p21_pick_then_ask(w, shape)
    rest, rest_text, id_key = _P21_REST[shape]
    proposal = {"summary": "確認", "payload": json.dumps(
        {"action": "contract_create", key: _P21_SPOKEN[shape], **rest}, ensure_ascii=False)}
    res3, p3 = await _t(w, rest_text, [_tool_call_response("confirm.request", proposal)])
    assert "confirm_source:program_proposal" in res3.trace.violations   # 前提：卡由提議合併觸發
    assert res3.outcome["state"] == "confirm_pending", res3.answer
    assert str(w.pending()[res3.trace.pending_id]["payload"][id_key]) == rid
    assert w.draft()["fields"][key] == title
    assert WC.V_CANDIDATE_NAME_KEPT in res3.trace.violations, res3.trace.violations
    assert p3.lenient_calls == []


async def _r4_run(api, shape, *, lenient):
    text, intent, *_ = _R4_SHAPES[shape]
    before = len(api._mock_transport.calls)
    w = _World()
    res, provider = await _t(w, text, intents=[intent()], lenient=lenient)
    return res, provider, w, _transport_calls(api)[before:]


def _without_lenient_marks(res) -> tuple:
    return (res.answer, res.outcome, res.quick_replies, res.ask_target,
            [v for v in res.trace.violations if not v.startswith(NM.V_NAME_LENIENT_PREFIX)])


@pytest.mark.parametrize("shape", list(_R4_SHAPES))
async def test_f1_r4_missing_name_empty_result_is_identical_to_off_run(api, monkeypatch, shape):
    """(乙) 回空 ⇒ 回覆與 off-run 逐字相同：⛔ 查不到固定句、`asked` 與草稿欄位不變（FR-3 收窄、FR-9）。
    差別只有 trace 的寬鬆型別標記（觸發型別＋`none`）與那一次清單查詢。"""
    on, p_on, w_on, calls_on = await _r4_run(api, shape, lenient=[_ids_resp(["none"])])
    monkeypatch.setenv(NM.NAME_LENIENT_ENV, "off")
    off, p_off, w_off, calls_off = await _r4_run(api, shape, lenient=None)
    assert _without_lenient_marks(on) == _without_lenient_marks(off)
    assert NM.NAME_NOT_FOUND_TEXT not in on.answer and on.answer.startswith("要完成這筆建立")
    assert w_on.draft() == w_off.draft()                            # 欄位與 `asked` 皆同
    assert WRITE_CANDIDATES_KEY not in _agent(w_on)
    assert C.V_NAME_LENIENT_TRIGGER_MISSING in on.trace.violations    # 前提自證：(乙) 真的跑了
    assert len(p_on.lenient_calls) == 1 and p_off.lenient_calls == []
    assert NM.V_NAME_LENIENT_NOT_FOUND_EXIT not in on.trace.violations
    extra = [c for c in calls_on if c not in calls_off]
    assert extra and all((p or {}).get("viewer_user_id") == OWNER for _m, _p, p in extra), extra


async def test_f1_r4_button_and_marker_turns_never_trigger_missing(api):
    """按鈕／`pick:`／`select:`／確認記號回合 ⇒ (乙) 不觸發（打字判準 `_name_lenient_typed_turn`；confirm 端
    `typed=False` ⇒ 0 次出向、0 次模型）；runtime：草稿缺名稱時送失效的 `pick:` 按鈕 ⇒ 寬鬆 0 次。"""
    from services.agent import runtime as runtime_mod

    class _WD:
        def __init__(self, msg, pick_button=False):
            self.user_message, self.pick_button, self.asked = msg, pick_button, []

    typed = runtime_mod._name_lenient_typed_turn
    for msg in ("pick:estate:67652", "pick:contract:85516", "select:bill:12345",
                "confirm_submit:0123456789abcdef", "confirm_edit:0123456789abcdef",
                "confirm_cancel:0123456789abcdef", "", "   "):
        assert typed(_WD(msg)) is False, msg
    assert typed(_WD(_KEELUNG_TURN_ASK, pick_button=True)) is False
    assert typed(_WD(_KEELUNG_TURN_ASK)) is True                     # 正對照
    # confirm 端：typed=False ⇒ 0 次出向、0 次模型
    estates, contracts = _universe(7)
    fake = _FakeAPI(estates, contracts)
    import services.agent.tools.jgb2 as _j
    orig = _j._api_singleton
    _j._api_singleton = fake
    try:
        for flag in (False, True):
            create = _Create(_ids_resp([str(estates[("20151", "12291")][0]["id"])]))
            ctx = _r4_ctx(create, user_message=estates[("20151", "12291")][0]["title"], typed=flag)
            res = await C.missing_name_lenient(_pm(), "repair_create", {"description": "漏水"},
                                               labels=["物件"], name_lenient=ctx)
            if not flag:
                assert res is None and fake.calls == [] and create.calls == [] and ctx.calls == 0
            else:
                assert ctx.calls == 1 and fake.calls                # 正對照：打字 ⇒ 真的跑
    finally:
        _j._api_singleton = orig
    # runtime：先建出缺名稱的草稿（(乙) 回空），再送一顆失效的 `pick:` 按鈕
    w = _World()
    await _t(w, _KEELUNG_TURN_ASK, intents=[_intent("contract_create")], lenient=[_ids_resp(["none"])])
    assert "estate_name" not in w.draft()["fields"]
    res2, provider2 = await _t(w, f"pick:estate:{KEELUNG_ID}")
    assert provider2.lenient_calls == [], res2.answer
    assert C.V_NAME_LENIENT_TRIGGER_MISSING not in res2.trace.violations


async def test_f1_r4_notfound_and_missing_share_one_lenient_run_per_turn(monkeypatch):
    """(甲)(乙) 同回合合計 ≤1 次寬鬆、≤1 次模型呼叫（同一份 `run_once`；先跑哪一個都一樣）。"""
    estates, contracts = _universe(11)
    key = ("20151", "12291")
    target = estates[key][0]
    for order in ("notfound_first", "missing_first"):
        fake = _FakeAPI(estates, contracts)
        monkeypatch.setattr(jgb2_tools, "_api_singleton", fake)
        create = _Create(_ids_resp([str(target["id"])]))
        ctx = _r4_ctx(create, user_message=target["title"][1:] + "冷氣壞了")

        async def _notfound():
            return await C._name_lenient_result(
                _pm(), "repair_create", {"estate_name": target["title"][1:] + "啦"},
                field="estate_name", cand_type="estate", name=target["title"][1:] + "啦",
                missing_label="物件", name_lenient=ctx)

        async def _missing():
            return await C.missing_name_lenient(_pm(), "contract_create", {}, labels=_labels_of(
                "contract_create", {}), name_lenient=ctx)

        first, second = ((_notfound, _missing) if order == "notfound_first" else (_missing, _notfound))
        r1 = await first()
        r2 = await second()
        assert r1 is not None and r2 is None, (order, r1, r2)
        assert ctx.calls == 1 and ctx.model_calls == 1 and len(create.calls) == 1, order
        trig = [m for m in ctx.marks if m.startswith("name_lenient:trigger:")]
        assert len(trig) == 1, (order, ctx.marks)


def test_f1_r4_sentence_source_order():
    """R4 整句來源（純函式）：值出現在本句 ⇒ 本句；否則最近一則含該值的既有使用者訊息（正規化比對）；
    都沒有 ⇒ 名稱值。"""
    pick = C.name_lenient_sentence
    old1, old2 = "捷士堂一廳一房 開帳單", "合約：捷士堂、一廳一房 要改一下"
    now = "名稱 管理費，金額 1000"
    assert pick("捷士堂一廳一房", now, [old1, old2, now]) == old2          # 最近一則（正規化去標點）
    assert pick("捷士堂一廳一房", now, [old1, "隨便講講", now]) == old1
    assert pick("捷士堂一廳一房", f"捷士堂一廳一房 {now}", [old1, now]) == f"捷士堂一廳一房 {now}"
    assert pick("火星基地", now, [old1, now]) == "火星基地"                  # 都沒有 ⇒ 名稱值
    assert pick("", now, [old1]) == "" and pick(None, now, [old1]) == ""
    assert C.name_said_key("Ａ棟 101室，") == "a棟101室"


@pytest.mark.parametrize("who", ["no_role", "no_user", "empty_user", "tenant"])
@pytest.mark.parametrize("action, payload, labels", [
    ("repair_create", {"description": "漏水"}, ["物件"]),
    ("contract_create", {}, None),
    ("manual_bill_create", {"title": "管理費"}, ["合約"]),
])
async def test_f1_r4_missing_identity_negative_never_calls_api_or_model(monkeypatch, who, action,
                                                                         payload, labels):
    """(乙) 身分負向（S-13）：缺 role、缺 user、非 property_manager ⇒ API 與模型呼叫皆 0 次；
    正對照：同一組輸入換成完整業者身分 ⇒ 真的有出向與模型呼叫。"""
    estates, contracts = _universe(7)
    key = ("20151", "12291")
    fake = _FakeAPI(estates, contracts)
    monkeypatch.setattr(jgb2_tools, "_api_singleton", fake)
    pool = contracts[key] if action == "manual_bill_create" else estates[key]
    sentence = pool[0]["title"][1:] + " 幫我處理"
    labels = labels if labels is not None else _labels_of(action, payload)
    ident = {"no_role": lambda: _pm_missing(role=None), "no_user": lambda: _pm_missing(user=None),
             "empty_user": lambda: _pm_missing(user="  "), "tenant": _tenant}[who]()
    create = _Create(_ids_resp([str(pool[0]["id"])]))
    ctx = _r4_ctx(create, user_message=sentence)
    res = await C.missing_name_lenient(ident, action, dict(payload), labels=labels, name_lenient=ctx)
    assert res is None
    assert fake.calls == [] and create.calls == [] and ctx.calls == 0 and ctx.model_calls == 0
    assert ctx.marks == []
    # 正對照
    create_ok = _Create(_ids_resp([str(pool[0]["id"])]))
    ctx_ok = _r4_ctx(create_ok, user_message=sentence)
    res_ok = await C.missing_name_lenient(_pm(), action, dict(payload), labels=labels,
                                          name_lenient=ctx_ok)
    assert res_ok is not None and fake.calls and len(create_ok.calls) == 1
    assert res_ok.data[C.NAME_LENIENT_MISSING_KEY] is True and res_ok.data[C.NAME_LENIENT_KEY] is True
    for _what, params in fake.calls:
        assert params["role_id"] == ROLE and params["viewer_user_id"] == OWNER


@pytest.mark.parametrize("env", [(NM.NAME_LENIENT_ENV, "off"), (WF.WRITE_CANDIDATES_ENV, "off")])
async def test_f1_r4_missing_switch_off_or_a2a_off_never_calls(api, monkeypatch, env):
    """(乙) 在開關 off、A-2a 關時清單查詢與模型呼叫皆 0 次（confirm 端與 runtime 端）。"""
    estates, contracts = _universe(7)
    target = estates[("20151", "12291")][0]
    monkeypatch.setenv(*env)
    fake = _FakeAPI(estates, contracts)
    orig = jgb2_tools._api_singleton
    monkeypatch.setattr(jgb2_tools, "_api_singleton", fake)
    create = _Create(_ids_resp([str(target["id"])]))
    ctx = _r4_ctx(create, user_message=target["title"])
    assert await C.missing_name_lenient(_pm(), "repair_create", {"description": "漏水"},
                                        labels=["物件"], name_lenient=ctx) is None
    assert fake.calls == [] and create.calls == [] and ctx.calls == 0
    monkeypatch.setattr(jgb2_tools, "_api_singleton", orig)
    for shape in _R4_SHAPES:
        res, provider, w, calls = await _r4_run(api, shape, lenient=None)
        assert provider.lenient_calls == [] and C.V_NAME_LENIENT_TRIGGER_MISSING not in \
            res.trace.violations
        assert not [p for _m, path, p in calls
                    if (p or {}).get("per_page") == NM.NAME_LENIENT_LIST_MAX
                    or ("estate" in path and "keyword" not in (p or {}))], calls


@pytest.mark.parametrize("action, payload", [
    ("estate_create", {"title": "新物件"}),
    ("contract_create", {}),
    ("manual_bill_create", {"title": "管理費"}),
])
async def test_f1_r4_missing_real_jgb_not_supported_actions_never_call(monkeypatch, action, payload):
    """S-14：接真 JGB（`use_mock=False`）時建物件、建合約、手開帳單的 (乙) 清單查詢與模型呼叫皆 0 次；
    正對照：同一假 API 改 `use_mock=True` 時建合約／手開帳單真的有出向。"""
    estates, contracts = _universe(7)
    fake = _FakeAPI(estates, contracts)
    fake.use_mock = False
    monkeypatch.setattr(jgb2_tools, "_api_singleton", fake)
    pool = contracts[("20151", "12291")] if action == "manual_bill_create" else \
        estates[("20151", "12291")]
    create = _Create(_ids_resp([str(pool[0]["id"])]))
    ctx = _r4_ctx(create, user_message=pool[0]["title"])
    labels = _labels_of(action, payload)
    assert await C.missing_name_lenient(_pm(), action, dict(payload), labels=labels,
                                        name_lenient=ctx) is None
    assert fake.calls == [] and create.calls == [] and ctx.calls == 0
    if action != "estate_create":
        fake.use_mock = True
        ctx2 = _r4_ctx(_Create(_ids_resp([str(pool[0]["id"])])), user_message=pool[0]["title"])
        assert await C.missing_name_lenient(_pm(), action, dict(payload), labels=labels,
                                            name_lenient=ctx2) is not None
        assert fake.calls


def _count(haystack: str, needle: str) -> int:
    return haystack.count(needle)


def _state_dump(w: _World) -> str:
    return json.dumps(w.state, ensure_ascii=False, sort_keys=True)


async def test_f1_r4_sentence_is_never_stored_logged_or_traced(api, monkeypatch, caplog):
    """FR-10／S-15：R4 選出的舊句只進送模型的 messages——
    - 同一回合 R4 開／R4 拿掉（整句來源恆回名稱值）：兩邊都列同一份候選，`agent_state`（＝寫進
      `form_sessions.collected_data` 的內容）序列化**逐字相同**；
    - 同一回合 on／off（`AGENT_NAME_LENIENT`）：`agent_state` 只多出候選集一鍵（鍵集合＝候選集封閉鍵），
      草稿鍵集合相同；選中句子出現次數不多於 `dialog` 原有次數；草稿名稱欄仍是名稱值（⛔ 句子）；
    - 候選結果 `query`：(甲)＝名稱值、(乙)＝空字串；
    - 同一份 log／trace 捕捉：搜不到選中句子與名稱，**且**搜得到觸發型別標記（正對照：捕捉沒壞）。"""
    caplog.set_level(logging.DEBUG)
    queries: list = []
    orig_cands = C._name_candidates_result

    def _spy(*a, **k):
        out = orig_cands(*a, **k)
        queries.append(k.get("query"))
        return out

    monkeypatch.setattr(C, "_name_candidates_result", _spy)
    shape = "contract_create"
    turn1 = _TURN1_TEXT[shape]
    on, p_on, w_on = await _name_first_then_rest(api, shape, rid_lenient=KEELUNG_ID)
    (kw,) = p_on.lenient_calls
    assert kw["messages"][2]["content"] == turn1                      # 前提自證：R4 選了舊句
    assert _pick_ids(on) and queries == [_CC_TYPO], queries           # (甲) query＝名稱值
    records_on = list(caplog.records)
    # R4 拿掉（整句來源恆回名稱值）⇒ 狀態逐字相同
    orig_sentence = C.name_lenient_sentence
    monkeypatch.setattr(C, "name_lenient_sentence", lambda value, *_a, **_k: value)
    ref, p_ref, w_ref = await _name_first_then_rest(api, shape, rid_lenient=KEELUNG_ID)
    assert p_ref.lenient_calls[0]["messages"][2]["content"] == _CC_TYPO and _pick_ids(ref)
    assert _state_dump(w_on) == _state_dump(w_ref)
    monkeypatch.setattr(C, "name_lenient_sentence", orig_sentence)   # ⛔ undo()：會連 fixture 的環境一起撤
    # on／off
    monkeypatch.setenv(NM.NAME_LENIENT_ENV, "off")
    # off 時 (甲) 不跑、查無交還主模型（現行）⇒ 給主模型一則固定收尾，⛔ 含使用者原話
    _off, _p_off, w_off = await _name_first_then_rest(
        api, shape, rid_lenient=KEELUNG_ID,
        script=[_fake_response(_fake_message(content="請再確認物件名稱。"))] * 3)
    assert _p_off.lenient_calls == []
    monkeypatch.delenv(NM.NAME_LENIENT_ENV)
    st_on, st_off = _agent(w_on), _agent(w_off)
    assert set(st_on) - set(st_off) <= {WRITE_CANDIDATES_KEY}, (set(st_on), set(st_off))
    assert set(st_on[WRITE_CANDIDATES_KEY]) <= WC.CANDIDATE_SET_KEYS_LENIENT
    if WRITE_DRAFT_KEY in st_off:
        assert set(st_on[WRITE_DRAFT_KEY]) == set(st_off[WRITE_DRAFT_KEY])
    assert st_on[WRITE_DRAFT_KEY]["fields"]["estate_name"] == _CC_TYPO
    for w in (w_on, w_off):
        dialog = json.dumps(_agent(w).get("dialog") or [], ensure_ascii=False)
        assert _count(_state_dump(w), turn1) <= _count(dialog, turn1), (_state_dump(w), dialog)
    # (乙) query＝空字串
    queries.clear()
    w2 = _World()
    res2, _p2 = await _t(w2, _MB_TURN_ASK, intents=[_R4_SHAPES["contract_manual_bill"][1]()],
                         lenient=[_ids_resp(["85516"])])
    assert _pick_ids(res2) and queries == [""], queries
    # log／trace：同一份捕捉（含已知標記才算捕捉沒壞）
    joined = "\n".join([r.getMessage() for r in records_on] + list(on.trace.violations))
    assert C.V_NAME_LENIENT_TRIGGER_NOTFOUND in joined, "捕捉壞了：搜不到已知觸發標記"
    joined2 = "\n".join([r.getMessage() for r in caplog.records] + list(res2.trace.violations))
    assert C.V_NAME_LENIENT_TRIGGER_MISSING in joined2, "捕捉壞了：搜不到已知觸發標記"
    for text in (joined, joined2):
        for secret in (turn1, _CC_TYPO, _MB_TURN_ASK, CONTRACT_TYPO):
            assert secret not in text, secret


# ════════════════════════════════════════════════════════════════════
# 性質測試 (乙)（F1 性質 (1) 延伸到 (乙)；(甲) 見 `test_f1_property_lenient_only_after_none_*`）
# ════════════════════════════════════════════════════════════════════
_R4_ACTIONS = {
    "repair": ("repair_create", {"description": "冷氣不冷"}, "estate_name", "estate"),
    "contract_create": ("contract_create", {"date_start": "2026-11-01", "rent": 12000},
                        "estate_name", "estate"),
    "bill_contract": ("manual_bill_create", {"title": "管理費"}, "contract_ref", "contract"),
    "due_extend": ("bill_due_extend", {"days": 3}, "estate_name", "estate"),
}


async def test_f1_property_r4_missing_only_when_name_empty_asked_and_typed(monkeypatch):
    """F1 性質 (乙)：隨機 240 組（身分 × 四個動作 × 名稱有無 × 追問含不含名稱欄 × 打字與否 × 句子講法 ×
    假模型行為）。斷言：(1) (乙) 只在「名稱欄空、追問含該名稱欄、本回合打字」時發生（三者皆成立且句子非空
    ⇒ 一定發生）；(2) 結果從不直接選定（⛔ 寫 payload）；(3) 候選 ⊆ 送模型清單 ⊆ 本身分 API 列；
    (4) 每支出向帶 role_id 且 viewer_user_id＝本人；模型呼叫 ≤1；`query`＝空字串。"""
    triggered = shown = 0
    for seed in range(PROPERTY_CASES):
        rng = random.Random(10_000 + seed)
        estates, contracts = _universe(seed)
        key = rng.choice(_IDENTS)
        role, user = key
        path = rng.choice(list(_R4_ACTIONS))
        action, base, field, ctype = _R4_ACTIONS[path]
        own = (contracts if ctype == "contract" else estates)[key]
        others = [r for k, rows in (contracts if ctype == "contract" else estates).items()
                  if k != key for r in rows]
        name_present = rng.random() < 0.3
        payload = dict(base)
        if name_present:
            payload[field] = rng.choice(own)["title"]
        full = _labels_of(action, payload)
        f_label = WF.FORMS[action].field(field).label
        ask_has_name = rng.random() < 0.75
        labels = full if ask_has_name else [lb for lb in full if lb != f_label] or ["期限"]
        typed = rng.random() < 0.8
        kind = rng.choice(["typo", "typo", "exact", "garbage", "empty"])
        sentence = {"typo": lambda: _mutate(rng, rng.choice(own)["title"]) + " 幫我處理",
                    "exact": lambda: rng.choice(own)["title"],
                    "garbage": lambda: rng.choice(["隨便講講", "那個那個", "嗯", "火星基地"]),
                    "empty": lambda: "  "}[kind]()
        mode = rng.choice(["subset", "others", "none", "free_text", "raise"])
        other_ids = [str(r["id"]) for r in others]

        def _answer(kwargs, _mode=mode, _rng=rng, _other=other_ids):
            sent = _sent_ids_of(kwargs)
            if _mode == "subset":
                return _ids_resp(_rng.sample(sent, min(len(sent), _rng.randint(1, 3))))
            if _mode == "others":
                return _ids_resp(_rng.sample(_other, min(len(_other), 3)) or ["none"])
            if _mode == "none":
                return _ids_resp(["none"])
            return "應該是第一筆吧"

        fake = _FakeAPI(estates, contracts)
        monkeypatch.setattr(jgb2_tools, "_api_singleton", fake)
        create = _Create(fn=_answer) if mode != "raise" else _Create(exc=RuntimeError("down"))
        ctx = _r4_ctx(create, user_message=sentence, typed=typed)
        before = dict(payload)
        res = await C.missing_name_lenient(_pm(user=user, role=role), action, payload,
                                           labels=labels, name_lenient=ctx)
        tag = (seed, path, name_present, ask_has_name, typed, kind, mode)
        cond = (not name_present) and (f_label in labels) and typed
        # (1)
        if ctx.calls:
            assert cond, tag
        if cond and kind != "empty":
            assert ctx.calls == 1, tag
        assert len(create.calls) <= 1 and ctx.model_calls <= 1, tag
        # (4)
        for _what, params in fake.calls:
            assert params["role_id"] == role and params["viewer_user_id"] == user, (tag, params)
        if not ctx.calls:
            assert fake.calls == [] and create.calls == [], tag
            assert res is None, tag
            continue
        triggered += 1
        # (2)
        assert payload == before and "estate_id" not in payload and "contract_id" not in payload, tag
        own_ids = {str(r["id"]) for r in own}
        sent = _sent_ids_of(create.calls[0]) if create.calls else []
        # (3)
        assert set(sent) <= own_ids, tag
        if res is None:
            continue
        data = res.data
        assert data[C.NAME_LENIENT_MISSING_KEY] is True and data[C.NAME_LENIENT_KEY] is True, tag
        cands = [str(r["id"]) for r in data["candidates"]]
        assert cands and set(cands) <= set(sent) <= own_ids and len(cands) <= NM.NAME_LENIENT_CAP, tag
        assert data["field"] == field and data[C.CANDIDATE_TYPE_KEY] == ctype, tag
        assert "查詢條件：無" in res.text_for_model, tag                 # query＝空字串
        shown += 1
    print(f"F12_PROPERTY_R4 cases={PROPERTY_CASES} triggered={triggered} shown={shown}")
    assert triggered >= 60 and shown >= 10, (triggered, shown)
