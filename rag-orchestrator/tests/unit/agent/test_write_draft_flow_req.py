"""unit：寫入草稿由程式掌握 W1＋W1b＋W1c（plan-write-flow-program-owned-20261017 §2／§8／§9；DSP-085）。

凍結驗收清單 `.kiro/specs/agentic-mcp-orchestration/acceptance-write-flow-20261017.md`（r9）的
**單元測試部分**：#3（缺欄與追問由同一張表驅動）、#6（`AGENT_WRITE_DRAFT=off` 與現行相同；W1b：
主輸出 schema on／off 皆與改動前逐位相同）、#8（改談別的不污染草稿；捏造值進不了草稿；W1b 問句
凍結、整句填入、物件補值、意圖呼叫解析／逾時／收尾；安全審查 F1～F4 與 W1b 安全處置；W1c 程式優先
與 W1c 安全處置 F1～F3；W1c 修正 §9.11：數字欄位取單一數字 token、系統物件名稱優先且同段原話
不填兩欄、程式優先等待分級）。

**W1c 程式優先只在 verifier 帶 `rules` 時走**（§9.7 F3：rules 缺 ⇒ 不走）。既有替身 `FakeVerifier`
沒有 `rules` ⇒ 既有 W1／W1b 測試照舊走輸出後觸發點（後備路徑）；W1c 測試以 `program_first=True`
換成帶真規則檔（`config/agent_verifier_rules.json`）的 `_RulesVerifier`。

資料走真 `JGBSystemAPI`＋`JGBMockTransport`（`assistant_demo_vendor4.json`）＋真
`mcp_facade.build_registry`；全部離線，⛔ 打 Bedrock／OpenAI。

**測試替身（W1b）**：意圖判斷呼叫與主模型走**同一個 client**（`provider.async_client`），
`_Provider` 依 `response_format.json_schema.name`（`write_forms.WRITE_INTENT_SCHEMA_NAME`）分流：
主模型呼叫照 `FakeCompletions` 慣例消耗 `script`（耗盡即斷言失敗 ⇒ 多叫一次模型會被抓到）；
意圖呼叫消耗 `intents`（未給 ⇒ 一律回 `{"action":"none"}`），每一項可以是回應物件、原始字串
（當 `message.content`）、或 `callable(kwargs)`（可回 awaitable，用來模擬逾時與失敗）。

期望值由測試自己寫死（fixture 原始 JSON 人工查證），⛔ 引用被測物輸出當期望：
  - 67338「學生獨立套房可租補」：只有 12291 看得到；
  - 67652「基隆溫馨一人宅套房」：帳單 709744（status 1、date_expire 20261101、2026-11 那期）；
  - 707995「台北信義-市政府寵物友善單人房(永豐信用卡)」：該名稱只對到這一張帳單
    （date_expire 20260701）。
"""
from __future__ import annotations

import asyncio
import inspect
import itertools
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from tests.unit.agent.confirm_pool_double import attach_token_tx  # 第 3 步 A7：token 寫入交易替身

from services import jgb_system_api as api_mod
from services import usage_metering
from services.agent import mcp_facade as F
from services.agent import runtime as runtime_mod
from services.agent import write_forms as WF
from services.agent.agent_session import WRITE_DRAFT_KEY
from services.agent.budget import Budget
from services.agent.confirm_card import (
    CLOSED_ACTION_ANY_OF,
    CLOSED_ACTION_FIELDS,
    _REF_ALTERNATIVES,
    _given,
    missing_required_labels,
)
from services.agent.identity import Identity
from services.agent.output_schema import AgentOutput, VerifierRules
from services.agent.question_sensitivity import question_sensitive
from services.agent.runtime import (
    LAST_ASK_TARGET_KEY,
    AgentRuntime,
    ImageTurnInput,
    ReservedCallIds,
    TurnAccumulator,
    _agent_output_response_format,
    _is_question,
)
from services.agent.tools import confirm as C
from services.agent.tools import jgb2 as jgb2_tools
from services.agent.tools.registry import Provenance, ToolResult
from services.jgb import bills as _bills
from services.jgb import fixture_store
from services.jgb.transport import MOCK_WRITE_LOG_ENV, RecordingTransport

from tests.unit.agent.test_runtime_req import (
    FakeAssembler, FakeClock, FakeCompletions, FakeVerifier, VerifierVerdict,
    _fake_message, _fake_response, _fake_tool_call,
)

pytestmark = [pytest.mark.unit, pytest.mark.req("agentic-mcp-orchestration:plan-write-flow-W1")]

FIXTURE = (Path(__file__).resolve().parents[3]
           / "services" / "jgb" / "fixture_data" / "assistant_demo_vendor4.json")
RULES_PATH = Path(__file__).resolve().parents[3] / "config" / "agent_verifier_rules.json"
ROLE, OWNER = "20151", "12291"
TODAY = date(2026, 10, 17)
STUDENT_ESTATE = "學生獨立套房可租補"            # 67338，只有 12291 看得到
KEELUNG_ESTATE = "基隆溫馨一人宅套房"            # 67652，帳單 709744 = 2026-11 那期
SINGLE_BILL_ESTATE = "台北信義-市政府寵物友善單人房(永豐信用卡)"   # 只對到帳單 707995
SCRIPT_C3 = "2026年11月1日到2027年10月31日，月租12000元，承租人信箱 w1-test@example.com"
SCRIPT_D2 = f"{KEELUNG_ESTATE} 11月那期"
ASK_TEXT = C.MISSING_FIELDS_ASK_TEMPLATE
MODEL_TEXT = "好的，我來幫您處理。"


#: 改動前（基準 81f42ea3、W1 未動任何檔之前）在測試容器內以
#: `json.dumps(_agent_output_response_format(), ensure_ascii=False)` 產生的輸出，原樣寫死
#: （⛔ 由被測物現算）。#6（W1b）：on 與 off 時都必須與它逐位相同。
PRE_CHANGE_RESPONSE_FORMAT = r'''{"type": "json_schema", "json_schema": {"name": "AgentOutput", "strict": true, "schema": {"$defs": {"Sentence": {"description": "模型逐句輸出的**一筆**：文字、分類與依據標記同筆攜帶（DSP-028／DSP-029a）。\n\n`text` 要含句尾標點；⛔ 一筆不放兩句（放兩句時 Verifier 會把它切成片段逐一複核，\n片段只**繼承** `kind`／`refs` 標籤、⛔ 不繼承驗證結果）。\n\n**DSP-029a：`refs` 是標記字串本身，⛔ 不再是任何陣列的索引。**\n起因見 `.claude/DECISIONS.md` DSP-029a：舊契約要模型自己對齊\n`tool_call_id`／`source`／`unit` 三個定址欄位，R5 實測 162 回合裡 119 次錯在\n三欄互混。標記已經整串印在資料段那一行的行首，照抄一個字串是模型做得到的動作，\n對齊三個欄位不是。解析在 `services.agent.provenance_units.resolve_refs`，\n⛔ 解析結果不寫回本模型任何欄位（r13 F-A：掛上去就會跟著\n`decision_snapshot`／trace 外流）。", "properties": {"text": {"title": "Text", "type": "string"}, "kind": {"enum": ["fact", "question", "greeting", "routing"], "title": "Kind", "type": "string"}, "refs": {"description": "事實句填其依據所在那一行開頭的標記，原樣照抄。", "items": {"type": "string"}, "title": "Refs", "type": "array"}}, "required": ["text", "kind", "refs"], "title": "Sentence", "type": "object", "additionalProperties": false}}, "description": "模型一輪回覆的結構化輸出（`response_format` json_schema strict）。\n\n**DSP-028：⛔ 模型不再輸出 `answer` 欄，也不再輸出另一張逐句對照表**——舊契約要模型自己保證\n「句數等於標籤數、順序對得上」，句數不等時程式只能猜哪筆標籤配哪一句，猜錯的\n方向是放行。改成文字與標籤同筆攜帶後，「拼接後等於送出的字串」變成定義而不是\n要靠檢查維持的巧合。\n\n**DSP-029a：⛔ 不再有 `citations` 陣列**——引用就是 `Sentence.refs` 裡的標記字串，\n句子與依據之間不再隔一層索引（索引本身是另一個會對錯的東西）。", "properties": {"kind": {"description": "本輪回覆的型別：answer 直接回答、ask 反問澄清、recommend 建議下一步、handoff 轉真人（轉人時 sentences 可留空）。", "enum": ["answer", "ask", "recommend", "handoff"], "title": "Kind", "type": "string"}, "sentences": {"description": "回覆逐句一筆 {text, kind, refs}；text 含句尾標點、⛔ 一筆不放兩句。系統把各筆 text 原樣接起來就是使用者看到的整段話，⛔ 不另外給 answer 欄位。", "items": {"$ref": "#/$defs/Sentence"}, "title": "Sentences", "type": "array"}, "fact_class": {"type": "string", "enum": ["customer_reference", "pricing", "contract_sla", "compliance", "security", "feature", "other"], "description": "本輪問題的事實類別；產品功能／操作方式一律 feature，五類敏感值只配 kind=handoff。"}, "handoff_reason": {"anyOf": [{"type": "string", "enum": ["no_grounding", "sensitive_no_grounding", "llm_mentioned_handoff", "partial_grounding", "tool_unavailable", "budget_exhausted"]}, {"type": "null"}], "description": "kind=handoff 時必填：敏感五類 sensitive_no_grounding、查無資料 no_grounding；其他 kind 填 null。"}, "ask_target": {"anyOf": [{"type": "string", "enum": ["estate", "community", "address", "bill_id", "repair_id", "contract_id", "meter", "date", "description", "urgency", "confirm_intent", "choice", "photo", "document", "identity", "scale", "team", "pain", "interested"]}, {"type": "null"}], "description": "kind=ask 時必填：這一句要問使用者的東西，只能是下列其中一個值：estate、community、address、bill_id、repair_id、contract_id、meter、date、description、urgency、confirm_intent、choice、photo、document、identity、scale、team、pain、interested；其他 kind 填 null。"}}, "required": ["kind", "sentences", "fact_class", "handoff_reason", "ask_target"], "title": "AgentOutput", "type": "object", "additionalProperties": false}}}'''

# ---------------------------------------------------------------------------
# 夾具與小工具
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr(_bills, "_today", lambda: TODAY)
    monkeypatch.delenv("AGENT_WRITE_DRAFT", raising=False)
    monkeypatch.delenv(WF.WRITE_PROPOSAL_ENV, raising=False)      # A+ 片：未設＝on
    monkeypatch.setenv("AGENT_WRITE_TOOLS_ENABLED", "true")


@pytest.fixture()
def api(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.delenv("MOCK_FAIL_NEXT_WRITE", raising=False)
    monkeypatch.delenv(MOCK_WRITE_LOG_ENV, raising=False)
    monkeypatch.setattr(fixture_store, "_DATA", fixture_store._DATA)
    fixture_store.load_from(FIXTURE)
    a = api_mod.JGBSystemAPI()
    a._mock_transport = RecordingTransport(a._mock_transport)
    monkeypatch.setattr(jgb2_tools, "_api_singleton", a)
    return a


def _pm(user: str = OWNER, role: str = ROLE) -> Identity:
    return F.namespaced_identity(Identity(
        vendor_id=4, target_user="property_manager", mode="b2b", role_id=role, user_id=user,
        session_id="w1", api_key_id=1, entry="mcp"))


def _prospect() -> Identity:
    return F.namespaced_identity(Identity(
        vendor_id=4, target_user="prospect", mode="b2b", user_id="p1",
        session_id="w1p", api_key_id=1, entry="mcp"))


def _pool():
    pool = AsyncMock()
    pool.execute = AsyncMock(return_value="INSERT 0 1")
    pool.fetchrow = AsyncMock(return_value=None)
    return attach_token_tx(pool)


class _Reg:
    """真 `mcp_facade.build_registry` 的薄包裝：記下每一次工具呼叫的結果（前提自證用）。

    `estates_override`：`{keyword: ToolResult}`——前置查詢的物件關鍵字查詢改回替身結果
    （「替身唯一命中」用；其餘一律走真 registry）。`yield_first`：每次呼叫前先讓出事件迴圈幾次
    （讓並行的意圖判斷 task 在提前出口之前跑完）。"""

    def __init__(self, pool, *, estates_override=None, yield_first: int = 0):
        self.inner = F.build_registry(F.FacadeDeps(get_db_pool=lambda: pool, stage="M1"))
        self.results: list = []
        self.estates_override = dict(estates_override or {})
        self.yield_first = yield_first

    def to_openai_tools(self, identity, stage, *, readonly_view=False):
        return self.inner.to_openai_tools(identity, stage, readonly_view=readonly_view)

    def specs_for(self, *a, **kw):
        return self.inner.specs_for(*a, **kw)

    async def call(self, identity, name, args, timeout_s, **kw):
        for _ in range(self.yield_first):
            await asyncio.sleep(0)
        if name == "jgb2.query.estates" and args.get("keyword") in self.estates_override:
            result = self.estates_override[args["keyword"]]
        else:
            result = await self.inner.call(identity, name, args, timeout_s, **kw)
        self.results.append((name, args, result))
        return result

    def confirm_calls(self) -> list:
        return [(args, res) for name, args, res in self.results if name == "confirm.request"]


def _unique_estate_hit(title: str = STUDENT_ESTATE, estate_id: str = "67338") -> ToolResult:
    """`jgb2.query.estates` 恰好命中一列（`_ok_candidates` 單列形狀，列上有 `title`）的替身。"""
    facts = f"找到 1 個物件：{title}。"
    return ToolResult(ok=True, data={"facts": facts, "candidates": [{"id": estate_id, "title": title}]},
                      provenance=[Provenance(source="jgb2:estates#1", text=facts, citable=True)],
                      text_for_model=facts)


class _Provider:
    """主模型＋意圖判斷呼叫的替身（同一個 `async_client`，依 response_format 名稱分流）。"""

    def __init__(self, script, intents=None):
        self.main = FakeCompletions(script)
        self.intent_script = None if intents is None else list(intents)
        self.intent_calls: list = []
        self.async_client = SimpleNamespace(chat=SimpleNamespace(completions=self))

    @property
    def calls(self):
        return self.main.calls

    async def create(self, **kwargs):
        rf = kwargs.get("response_format") or {}
        if (rf.get("json_schema") or {}).get("name") == WF.WRITE_INTENT_SCHEMA_NAME:
            self.intent_calls.append(kwargs)
            if self.intent_script is None:
                return _intent("none")
            assert self.intent_script, "意圖呼叫腳本已耗盡——測試少寫了一步"
            step = self.intent_script.pop(0)
            if callable(step):
                step = step(kwargs)
                if inspect.isawaitable(step):
                    step = await step
            if isinstance(step, str):
                step = _fake_response(_fake_message(content=step), prompt_tokens=7, completion_tokens=3)
            return step
        return await self.main.create(**kwargs)


def _intent(action: str = "none", *, raw=None, pt: int = 7, ct: int = 3, **fields):
    """意圖判斷呼叫的假回應（`message.content`＝模型原始輸出字串）。"""
    content = raw if raw is not None else json.dumps(
        {"action": action, "fields": [{"key": k, "value": v} for k, v in fields.items()]},
        ensure_ascii=False)
    return _fake_response(_fake_message(content=content), prompt_tokens=pt, completion_tokens=ct)


def _out(answer: str = MODEL_TEXT, *, kind: str = "answer", ask_target=None,
         fact_class: str = "feature", handoff_reason=None, raw_extra=None):
    payload = {
        "kind": kind,
        "sentences": [] if not answer else [{"text": answer, "kind": "greeting", "refs": []}],
        "fact_class": fact_class,
        "handoff_reason": handoff_reason,
        "ask_target": ask_target,
    }
    if raw_extra:
        payload.update(raw_extra)
    return _fake_response(_fake_message(content=json.dumps(payload, ensure_ascii=False)))


def _call(name: str, args: dict, call_id: str = "c1"):
    return _fake_response(_fake_message(tool_calls=[_fake_tool_call(name, args, call_id=call_id)]))


def _confirm_args(payload: dict) -> dict:
    return {"summary": "確認", "payload": json.dumps(payload, ensure_ascii=False)}


class _RulesVerifier(FakeVerifier):
    """W1c：帶真規則檔 `rules` 的替身（程式優先的前提，§9.7 F3）；`verify` 照 `FakeVerifier`。"""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.rules = VerifierRules.load(RULES_PATH)


def _rt(provider, reg, budget=None, *, program_first: bool = False) -> AgentRuntime:
    verifier_cls = _RulesVerifier if program_first else FakeVerifier
    return AgentRuntime(provider, reg, verifier_cls([VerifierVerdict(ok=True)] * 6), FakeAssembler(),
                        budget or Budget(), stage="M1", clock=FakeClock())


async def _turn(identity, message, state, script, *, intents=None, budget=None, pool=None, reg=None,
                program_first: bool = False, **kw):
    pool = pool or _pool()
    reg = reg or _Reg(pool)
    provider = _Provider(script, intents)
    rt = _rt(provider, reg, budget, program_first=program_first)
    res = await rt.run_turn(identity, message, state, **kw)
    # W1b：每一回合結束時意圖呼叫都已收尾（登記清空）。
    assert rt._write_intent_calls == {}
    return res, reg, provider, pool


def _draft(state) -> dict:
    return (state.get("agent") or {}).get(WRITE_DRAFT_KEY)


def _seed(identity, action: str, fields: dict, *, users=(), idle: int = 0, asked=()) -> dict:
    """測試直接設草稿狀態（`users`＝之前回合的使用者原話，放進 dialog）。"""
    dialog = []
    for text in users:
        dialog += [{"role": "user", "content": text}, {"role": "assistant", "content": "好的。"}]
    return {"agent": {
        "dialog": dialog,
        WRITE_DRAFT_KEY: {"action": action, "fields": dict(fields), "idle_turns": idle,
                          "created_by_role": runtime_mod._write_draft_owner(identity),
                          "asked": list(asked)},
    }}


def _program_records(res) -> list:
    return [r for r in res.trace.tool_calls if str(r.id).startswith("wdprog-")]


# ════════════════════════════════════════════════════════════════════
# #3 缺欄計算與追問由同一張表驅動
# ════════════════════════════════════════════════════════════════════
def _old_missing_required_labels(action, payload):
    """改動前（`81f42ea3:rag-orchestrator/services/agent/confirm_card.py`）的
    `missing_required_labels` 逐字搬來當**對照組**（⛔ 引用被測物）。"""
    if action not in CLOSED_ACTION_FIELDS or not isinstance(payload, dict):
        return []
    alternatives = _REF_ALTERNATIVES.get(action, {})
    labels: list = []
    for f in CLOSED_ACTION_FIELDS[action]:
        if not f.required or f.kind == "sys_id" or _given(payload.get(f.key)):
            continue
        if any(_given(payload.get(alt)) for alt in alternatives.get(f.key, ())):
            continue
        labels.append(f.label)
    for keys, label in CLOSED_ACTION_ANY_OF[action]:
        if not any(_given(payload.get(k)) for k in keys):
            labels.append(label)
    return labels


def _old_repair_missing(payload):
    """改動前 `tools/confirm.py` 修繕缺欄區塊（A9）逐字搬來當對照組。"""
    legacy = {"estate_name": "物件", "description": "問題描述"}
    return [label for key, label in legacy.items()
            if not isinstance(payload.get(key), str) or not payload.get(key).strip()]


def _old_ask_target(missing):
    """改動前 runtime 缺欄追問的 ask_target 推導（逐字）。"""
    return ("estate" if "物件" in missing
            else "description" if missing == ["問題描述"] else None)


_SAMPLE_VALUE = {"text": "樣本", "enum": None, "int": 3, "number": 12.5, "date": "20261201",
                 "email": "a@b.co", "phone": "0912345678", "sys_id": 7}


def _closed_payload_space(action):
    """封閉動作所有「必填欄位＋至少一組＋替代來源」鍵的子集（給／不給、空白值）。"""
    keys = [f.key for f in CLOSED_ACTION_FIELDS[action] if f.required]
    keys += [k for group, _ in CLOSED_ACTION_ANY_OF[action] for k in group]
    keys += [a for alts in _REF_ALTERNATIVES.get(action, {}).values() for a in alts]
    keys = list(dict.fromkeys(keys))
    fields = {f.key: f for f in CLOSED_ACTION_FIELDS[action]}
    for mask in itertools.product((0, 1, 2), repeat=len(keys)):
        payload = {}
        for key, m in zip(keys, mask):
            if m == 0:
                continue
            f = fields.get(key)
            if m == 2:
                payload[key] = "  "                      # 空白＝沒給
            elif f is not None and f.kind == "enum":
                payload[key] = next(iter(f.choices))
            else:
                payload[key] = _SAMPLE_VALUE.get(f.kind if f else "text", "樣本")
        yield payload


@pytest.mark.parametrize("action", sorted(CLOSED_ACTION_FIELDS))
def test_closed_actions_missing_labels_identical_to_pre_change(action):
    """#3：封閉三動作缺欄標籤與改動前**逐字**相同（窮舉必填／至少一組／替代來源的給與不給）。"""
    n = 0
    for payload in _closed_payload_space(action):
        old = _old_missing_required_labels(action, payload)
        assert missing_required_labels(action, payload) == old, payload
        assert WF.missing_labels(action, payload) == old, payload
        n += 1
    assert n >= 3 ** 4                                  # 正對照：真的窮舉到了


def test_repair_missing_labels_identical_to_pre_change():
    """#3：修繕缺欄（含「非字串＝缺」的 A9 判準）與改動前逐字相同。"""
    values = [None, "", "  ", "冷氣不冷", 123]
    seen_nonempty = False
    for est, desc in itertools.product(values, values):
        payload = {"action": "repair_create"}
        if est is not None:
            payload["estate_name"] = est
        if desc is not None:
            payload["description"] = desc
        old = _old_repair_missing(payload)
        assert WF.missing_labels("repair_create", payload) == old, payload
        seen_nonempty = seen_nonempty or bool(old)
    assert seen_nonempty


@pytest.mark.parametrize("missing", [
    ["物件"],                                        # 只缺物件
    ["物件", "問題描述"],                            # 缺物件＋其他（修繕）
    ["物件", "起租日", "租金"],                      # 缺物件＋其他（合約）
    ["問題描述"],                                    # 只缺問題描述
    ["金額"],                                        # 只缺非物件的單一欄
    ["物件名稱"],
    ["承租人 Email 或電話"],
    ["起租日", "到期日"],                            # 缺多個非物件欄
    ["帳單項目", "金額", "繳費期限"],
    ["合約"],
])
def test_ask_target_identical_to_pre_change_for_named_combinations(missing):
    """#3：修繕與封閉三動作的各缺欄組合，`ask_target` 與改動前逐位相同。"""
    assert WF.ask_target_for_missing(missing) == _old_ask_target(missing)


@pytest.mark.parametrize("action", ["repair_create", *sorted(CLOSED_ACTION_FIELDS)])
def test_ask_target_identical_to_pre_change_over_all_missing_sets(action):
    """#3：窮舉每支（修繕＋封閉三動作）可能產生的缺欄清單 ⇒ 表導出的 ask_target 與舊式逐位相同。"""
    payloads = (_closed_payload_space(action) if action in CLOSED_ACTION_FIELDS else
                ({"estate_name": e, "description": d}
                 for e, d in itertools.product([None, "x"], [None, "y"])))
    seen = set()
    for payload in payloads:
        missing = WF.missing_labels(action, payload)
        seen.add(tuple(missing))
        assert WF.ask_target_for_missing(missing) == _old_ask_target(missing), missing
    assert len(seen) >= 3


#: 5 支動作各缺一個必填欄（模型自己呼叫 `confirm.request`）⇒ (payload, 缺欄標籤, ask_target, asked 鍵)。
_ONE_MISSING = [
    ({"action": "repair_create", "estate_name": STUDENT_ESTATE}, ["問題描述"], "description",
     ["description"]),
    ({"action": "bill_due_extend", "estate_name": KEELUNG_ESTATE, "period": "11月那期"},
     ["延後天數"], None, ["days"]),
    ({"action": "estate_create", "city": "台北市", "district": "大安區", "address": "某路 1 號",
      "use_for": "residential"}, ["物件名稱"], None, ["title"]),
    ({"action": "contract_create", "date_start": "20261101", "date_end": "20271031",
      "rent": 12000, "to_user_email": "w1-test@example.com"}, ["物件"], "estate", ["estate_name"]),
    ({"action": "manual_bill_create", "contract_ref": "某合約", "title": "清潔費",
      "date_expire": "20261201"}, ["金額"], None, ["total"]),
]


#: A+ 片：使用者這句話含 `_ONE_MISSING` 各 payload 的值（模型提議經值閘合併進草稿後，程式依草稿
#: 發出的 `confirm.request` 缺的仍只有那一欄）。日期用使用者常見寫法（模型參數仍是 `YYYYMMDD`）。
_ONE_MISSING_USER_TEXT = {
    "repair_create": f"{STUDENT_ESTATE} 要報修",
    "bill_due_extend": f"{KEELUNG_ESTATE} 11月那期 帳單延期",
    "estate_create": "新增物件 台北市 大安區 某路 1 號",
    "contract_create": "開合約 2026-11-01 到 2027-10-31 租金 12000 w1-test@example.com",
    "manual_bill_create": "某合約 開帳單 清潔費 期限 2026-12-01",
}


@pytest.mark.parametrize("proposal", ["on", "off"])
@pytest.mark.parametrize("payload,labels,ask_target,asked", _ONE_MISSING,
                         ids=[p["action"] for p, _, _, _ in _ONE_MISSING])
async def test_each_write_action_missing_one_field_gets_program_ask(api, monkeypatch, payload, labels,
                                                                    ask_target, asked, proposal):
    """#3：5 支動作各缺一個必填欄 ⇒ 回 `missing_fields`、程式追問句（⛔ 再叫模型）、
    ask_target 由表導出並寫進 `LAST_ASK_TARGET_KEY`；W1b：程式追問出口寫 `asked`（表單鍵）。

    A+ 片（改寫，原意圖不變）：`proposal=off`＝改前行為的正對照（模型參數直接執行，使用者句子不必
    含值）；`proposal=on`＝模型呼叫只當提議，值須出現在使用者原話才進草稿，程式依草稿發出的
    `confirm.request`（`summary` 為程式常數）得到同一個缺欄清單。"""
    from services.agent.runtime import WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY
    if proposal == "off":
        monkeypatch.setenv(WF.WRITE_PROPOSAL_ENV, "off")
        message = "幫我處理一下"
    else:
        message = _ONE_MISSING_USER_TEXT[payload["action"]]
    state: dict = {}
    res, reg, provider, pool = await _turn(_pm(), message, state,
                                           [_call("confirm.request", _confirm_args(payload))])
    (_args, first), = reg.confirm_calls()
    if proposal == "on":
        assert _args["summary"] == WRITE_DRAFT_PROGRAM_CONFIRM_SUMMARY
        assert "write_proposal" in res.trace.violations
    else:
        assert _args["summary"] == "確認" and "write_proposal" not in res.trace.violations
    assert (first.ok, first.error) == (False, "INVALID_INPUT")
    assert first.data["missing_fields"] == labels
    assert res.answer == ASK_TEXT.format(labels="、".join(labels))
    assert res.outcome["state"] == "clarifying"
    assert "confirm_missing_fields_ask" in res.trace.violations
    assert state["agent"][LAST_ASK_TARGET_KEY] == ask_target == WF.ask_target_for_missing(labels)
    assert len(provider.calls) == 1                     # 程式追問：模型只被叫了第一次
    pool.execute.assert_not_called()   # 原斷言保留（A7 前 INSERT 走這裡）
    assert pool.insert.call_count == 0 and pool.burn.call_count == 0                    # ⛔ 寫 token
    assert _draft(state)["action"] == payload["action"] and _draft(state)["asked"] == asked


async def test_bill_due_extend_missing_bill_and_estate_asks_for_estate_and_period(api):
    """#3：`bill_due_extend` 缺 bill_id 且缺 estate_name ⇒ 程式追問句、標籤含物件與期別、
    `ask_target=estate`。"""
    state: dict = {}
    res, reg, _p, _pool_ = await _turn(_pm(), "幫我延帳單 7 天", state, [
        _call("confirm.request", _confirm_args({"action": "bill_due_extend", "days": 7}))])
    (_a, first), = reg.confirm_calls()
    assert first.data["missing_fields"] == ["物件", "期別"]
    assert res.answer == ASK_TEXT.format(labels="物件、期別")
    assert state["agent"][LAST_ASK_TARGET_KEY] == "estate"
    assert _draft(state)["asked"] == ["estate_name", "period"]


async def test_bill_due_extend_model_call_missing_days_now_gets_program_ask(api):
    """#3（明列行為變更）：模型自呼 `bill_due_extend` 缺 `days` ⇒ 回 `missing_fields`、程式追問
    （改動前是不帶清單的 `INVALID_INPUT`、交回模型）。"""
    direct = await C.confirm_request(
        _pm(), _confirm_args({"action": "bill_due_extend", "estate_name": KEELUNG_ESTATE,
                               "period": "11月那期"}), db_pool=_pool())
    assert (direct.ok, direct.error, direct.data) == (
        False, "INVALID_INPUT", {"missing_fields": ["延後天數"], "action": "bill_due_extend"})
    assert C.missing_fields_ask_text(direct) == ASK_TEXT.format(labels="延後天數")


async def test_repair_model_call_with_empty_description_asks_for_description(api):
    """#3：模型自己呼叫 `confirm.request` 帶 `description:""` ⇒ 程式追問「問題描述」
    （改動前 A9 同樣；對照組 `_old_repair_missing`）。"""
    payload = {"action": "repair_create", "estate_name": STUDENT_ESTATE, "description": ""}
    assert _old_repair_missing(payload) == ["問題描述"]               # 改動前
    state: dict = {}
    res, reg, _p, _pool_ = await _turn(_pm(), f"幫我報修{STUDENT_ESTATE}", state,
                                       [_call("confirm.request", _confirm_args(payload))])
    assert res.answer == ASK_TEXT.format(labels="問題描述")           # 改動後
    assert state["agent"][LAST_ASK_TARGET_KEY] == "description"


async def test_bill_due_extend_model_call_without_period_unchanged(api):
    """#3：模型自己呼叫 `{bill_due_extend, days:7, estate_name:<只有一張帳單的物件>}`（不帶期別）
    ⇒ 與改動前逐位相同：缺欄檢查不觸發，照舊以物件對到唯一帳單出卡（期望值寫死自 fixture）。"""
    payload = {"action": "bill_due_extend", "days": 7, "estate_name": SINGLE_BILL_ESTATE}
    assert WF.missing_labels("bill_due_extend", payload) == []        # 新閘對它是惰性的
    res = await C.confirm_request(_pm(), _confirm_args(payload), db_pool=_pool())
    assert res.ok is True, res.error
    assert res.data["payload"] == {
        "action": "bill_due_extend", "days": 7, "estate_name": SINGLE_BILL_ESTATE,
        "bill_id": "707995", "date_expire_before": "20260701", "date_expire_after": "20261024",
    }
    assert res.data["card"] == (
        "即將調整帳單到期日，請確認：\n"
        "・帳單編號：707995\n・原到期日：2026/07/01\n・起算日：2026/10/17\n"
        "・延後天數：7 天\n・新到期日：2026/10/24\n請從下方按鈕擇一。"
    )
    assert res.data["hint"] == C.BILL_MATCH_HINT


async def test_bill_draft_program_trigger_reaches_confirm_pending(api, monkeypatch):
    """#3：草稿 `{"days":"7","estate_name":"基隆溫馨一人宅套房","period":"11月那期"}` 經程式觸發
    得 `confirm_pending`（`to_payload` 把 "7" 轉成 int）；卡上帳單＝709744、延後 7 天。

    第 3 步 A1：「出卡即清」只在 `AGENT_WRITE_LIFECYCLE=off`（現行行為）成立——本條原斷言照舊
    在 off 下驗；on 時出卡保留草稿由 `test_step3_write_lifecycle_req.py` 驗。"""
    monkeypatch.setenv("AGENT_WRITE_LIFECYCLE", "off")
    ident = _pm()
    state = _seed(ident, "bill_due_extend", {"estate_name": KEELUNG_ESTATE, "period": "11月那期"},
                  users=["我想把一張帳單延後繳", SCRIPT_D2], asked=["days"])
    res, reg, provider, pool = await _turn(ident, "延 7 天", state, [_out()],
                                           intents=[_intent("bill_due_extend", days="7")])
    assert WF.to_payload("bill_due_extend", {"days": "7", "estate_name": KEELUNG_ESTATE,
                                             "period": "11月那期"})["days"] == 7
    assert res.outcome["state"] == "confirm_pending"
    assert "・帳單編號：709744" in res.answer and "・延後天數：7 天" in res.answer
    assert "・新到期日：2026/11/08" in res.answer
    assert "write_draft_program_confirm" in res.trace.violations
    assert len(_program_records(res)) == 1 and len(provider.calls) == 1
    assert _draft(state) is None                        # 出卡即清
    pool.insert.assert_called_once()                   # 一張 token


async def test_contract_draft_script_c_values_reach_card(api):
    """#3／腳本 C：使用者原話用腳本 C 第三句、意圖呼叫帶 date_end=2027-10-31 與
    to_user_email ⇒ 兩者進草稿、觸發後卡上到期日 2027/10/31、信箱 w1-test@example.com。"""
    ident = _pm()
    state = _seed(ident, "contract_create", {"estate_name": STUDENT_ESTATE},
                  users=["幫我建立一份新合約", f"物件是{STUDENT_ESTATE}"])
    captured: dict = {}
    real_persist = AgentRuntime._write_draft_persist

    def _spy(self, acc, agent_state):
        real_persist(self, acc, agent_state)
        captured.update(json.loads(json.dumps(agent_state.get(WRITE_DRAFT_KEY))))

    AgentRuntime._write_draft_persist = _spy
    try:
        res, reg, provider, _pool_ = await _turn(ident, SCRIPT_C3, state, [_out()], intents=[_intent(
            "contract_create", date_start="2026-11-01", date_end="2027-10-31", rent="12000",
            to_user_email="w1-test@example.com")])
    finally:
        AgentRuntime._write_draft_persist = real_persist
    assert captured["fields"]["date_end"] == "2027-10-31"
    assert captured["fields"]["to_user_email"] == "w1-test@example.com"
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert f"・物件：{STUDENT_ESTATE}（編號 67338）" in res.answer
    assert "・起租日：2026/11/01" in res.answer and "・到期日：2027/10/31" in res.answer
    assert "・租金：12,000 元" in res.answer
    assert "・承租人 Email：w1-test@example.com" in res.answer


async def test_category_outside_tree_is_dropped_and_trigger_still_runs(api):
    """#3：意圖呼叫帶分類樹外的值 ⇒ 不進草稿（violation），程式觸發照常出卡（歸其他）。"""
    state: dict = {}
    res, reg, provider, _pool_ = await _turn(
        _pm(), f"{STUDENT_ESTATE} 冷氣不冷，分類是外星維修", state, [_out()],
        intents=[_intent("repair_create", estate_name=STUDENT_ESTATE, description="冷氣不冷",
                         category_name="外星維修")])
    assert "write_intent_category_invalid" in res.trace.violations
    (args, _res), = reg.confirm_calls()
    assert "category_name" not in json.loads(args["payload"])
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert "・修繕分類：其他（未指定，歸其他）" in res.answer
    # 正對照：同一支閘對樹內的大類放行（樹內值確實進得了 payload）。
    state2: dict = {}
    res2, reg2, _p2, _pool2 = await _turn(
        _pm(), f"{STUDENT_ESTATE} 冷氣不冷，家電維修", state2, [_out()],
        intents=[_intent("repair_create", estate_name=STUDENT_ESTATE, description="冷氣不冷",
                         category_name="家電維修")])
    assert json.loads(reg2.confirm_calls()[0][0]["payload"])["category_name"] == "家電維修"


async def test_intent_only_turn_gets_program_ask_then_name_is_caught_by_pre_lookup(api):
    """#3：只表態意圖（`fields` 空）⇒ 程式追問句＋表導出 ask_target；下一句名稱經前置查詢唯一
    命中寫進草稿 ⇒ 再追問問題描述（模型兩回合都沒呼叫工具）。#8 W1b r2：缺 [物件, 問題描述] 後
    輸入物件名 ⇒ `description` 不被填入（`asked` 兩欄 ⇒ 不整句填入）、程式追問問題描述。"""
    ident = _pm()
    state: dict = {}
    res1, reg1, p1, _ = await _turn(ident, "能幫我新增一張修繕單嗎", state, [_out()],
                                    intents=[_intent("repair_create")])
    assert res1.answer == ASK_TEXT.format(labels="物件、問題描述")
    assert "confirm_missing_fields_ask" in res1.trace.violations
    assert state["agent"][LAST_ASK_TARGET_KEY] == "estate"
    assert _draft(state)["fields"] == {} and _draft(state)["asked"] == ["estate_name", "description"]
    res2, reg2, p2, _ = await _turn(ident, STUDENT_ESTATE, state, [_out()])     # 意圖＝none
    assert "write_draft_name_caught" in res2.trace.violations
    assert "write_draft_answer_filled" not in res2.trace.violations
    assert _draft(state)["fields"] == {"estate_name": STUDENT_ESTATE}           # description 未填
    assert res2.answer == ASK_TEXT.format(labels="問題描述")
    assert state["agent"][LAST_ASK_TARGET_KEY] == "description"
    assert len(p1.calls) == 1 and len(p2.calls) == 1
    assert len(p1.intent_calls) == 1 and len(p2.intent_calls) == 1


async def test_contract_name_caught_from_real_program_ask_and_contract_ref_untouched(api):
    """#3：`contract_create` 從**真的**程式缺欄追問回合開始（缺物件 ⇒ `ask_target=estate` 寫入
    `LAST_ASK_TARGET_KEY`，⛔ 由測試直接設狀態），下一句為唯一命中物件名 ⇒ 名稱寫進
    `estate_name`、`contract_ref` 不寫。"""
    ident = _pm()
    state: dict = {}
    res1, *_ = await _turn(ident, "幫我建立一份新合約", state, [_out()],
                           intents=[_intent("contract_create")])
    assert res1.answer.startswith("要完成這筆建立，還需要：物件")
    assert state["agent"][LAST_ASK_TARGET_KEY] == "estate"
    res2, *_ = await _turn(ident, STUDENT_ESTATE, state, [_out()])
    fields = _draft(state)["fields"]
    assert fields == {"estate_name": STUDENT_ESTATE}
    assert "contract_ref" not in fields
    assert res2.answer == ASK_TEXT.format(labels="起租日、到期日、租金、承租人 Email 或電話")


async def test_repair_draft_with_emergency_two_reaches_card_marked_urgent(api, monkeypatch):
    """#3：草稿 `{"estate_name":…,"description":"冷氣不冷","emergency_status":"2"}` 經程式觸發得
    `confirm_pending`、卡上急迫程度為「緊急」（`to_payload` 轉 int 2）。

    第 3 步 A4：意圖呼叫直接填代碼 "2" 只在 `AGENT_WRITE_LIFECYCLE=off`（現行）成立——本條原斷言
    照舊在 off 下驗；on 時只收標籤「緊急」由 `test_step3_write_lifecycle_req.py` 的 #6 驗。"""
    monkeypatch.setenv("AGENT_WRITE_LIFECYCLE", "off")
    assert WF.to_payload("repair_create", {"emergency_status": "2"}) == {"emergency_status": 2}
    state: dict = {}
    res, reg, provider, _pool_ = await _turn(
        _pm(), f"{STUDENT_ESTATE} 冷氣不冷，很急", state, [_out()],
        intents=[_intent("repair_create", estate_name=STUDENT_ESTATE, description="冷氣不冷",
                         emergency_status="2")])
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert "・急迫程度：緊急" in res.answer
    assert "・問題描述：冷氣不冷" in res.answer


# ════════════════════════════════════════════════════════════════════
# #6 `AGENT_WRITE_DRAFT=off` 時與現行相同；W1b：主輸出 schema on／off 皆與改動前逐位相同
# ════════════════════════════════════════════════════════════════════
def test_response_format_is_byte_identical_to_pre_change_snapshot():
    """#6（W1b）：`_agent_output_response_format()` 與改動前逐位相同（主輸出不再帶寫入意圖；
    開關不影響它）。快照 `PRE_CHANGE_RESPONSE_FORMAT` 是**改動前程式**在測試容器內產生後寫死。"""
    snapshot = PRE_CHANGE_RESPONSE_FORMAT
    assert "write_intent" not in snapshot                          # 正對照：快照本身是舊形狀
    assert json.dumps(_agent_output_response_format(), ensure_ascii=False) == snapshot
    assert "write_intent" not in AgentOutput.model_fields


@pytest.mark.parametrize("env", ["on", "off"])
async def test_runtime_sends_pre_change_main_schema_on_and_off(api, monkeypatch, env):
    """#6（W1b）：on 與 off 下，runtime 送給**主模型**的 `response_format` 都與快照逐位相同。"""
    monkeypatch.setenv("AGENT_WRITE_DRAFT", env)
    _res, _reg, provider, _ = await _turn(_pm(), "謝謝", {}, [_out()])
    assert json.dumps(provider.calls[0]["response_format"], ensure_ascii=False) == \
        PRE_CHANGE_RESPONSE_FORMAT


async def test_off_sends_no_intent_call_and_never_writes_draft(api, monkeypatch):
    """#6：off ⇒ 不發意圖判斷呼叫、⛔ 寫 `write_draft`、⛔ 程式觸發 confirm（意圖替身就算回寫入
    意圖也用不到）。"""
    monkeypatch.setenv("AGENT_WRITE_DRAFT", "off")
    state: dict = {}
    res, reg, provider, pool = await _turn(_pm(), "能幫我新增一張修繕單嗎", state, [_out()],
                                           intents=[_intent("repair_create")])
    assert provider.intent_calls == []
    assert WRITE_DRAFT_KEY not in state["agent"]
    assert reg.confirm_calls() == [] and not _program_records(res)
    assert res.answer == MODEL_TEXT                                # 模型原輸出照常出
    assert not any(str(v).startswith("write_intent") for v in res.trace.violations)
    pool.execute.assert_not_called()   # 原斷言保留（A7 前 INSERT 走這裡）
    assert pool.insert.call_count == 0 and pool.burn.call_count == 0
    # 正對照：同一句在 on 下真的會發意圖呼叫、建草稿＋程式觸發。
    monkeypatch.delenv("AGENT_WRITE_DRAFT")
    state_on: dict = {}
    res_on, reg_on, p_on, _ = await _turn(_pm(), "能幫我新增一張修繕單嗎", state_on, [_out()],
                                          intents=[_intent("repair_create")])
    assert len(p_on.intent_calls) == 1
    assert _draft(state_on) is not None and len(_program_records(res_on)) == 1


async def test_off_clears_a_leftover_draft(api, monkeypatch):
    """#6：off 撤回草稿機制——殘留的草稿清掉、⛔ 注入、⛔ 觸發。"""
    monkeypatch.setenv("AGENT_WRITE_DRAFT", "off")
    ident = _pm()
    state = _seed(ident, "repair_create", {"estate_name": STUDENT_ESTATE}, users=[STUDENT_ESTATE],
                  asked=["description"])
    res, reg, provider, _ = await _turn(ident, "冷氣不冷", state, [_out()],
                                        intents=[_intent("repair_create", description="冷氣不冷")])
    assert WRITE_DRAFT_KEY not in state["agent"]
    assert "進行中的建立" not in json.dumps(provider.calls[0]["messages"], ensure_ascii=False)
    assert reg.confirm_calls() == [] and provider.intent_calls == []


@pytest.mark.parametrize("env", ["on", "off"])
async def test_existing_fake_outputs_without_write_intent_still_validate(api, monkeypatch, env):
    """#6：不帶 `write_intent` 的既有假輸出在 on 與 off 下皆通過 `model_validate`、照常出。"""
    monkeypatch.setenv("AGENT_WRITE_DRAFT", env)
    legacy = {"kind": "answer", "sentences": [{"text": "好的。", "kind": "greeting", "refs": []}],
              "fact_class": "feature", "handoff_reason": None}
    AgentOutput.model_validate(legacy)
    state: dict = {}
    res, reg, *_ = await _turn(_pm(), "謝謝", state, [
        _fake_response(_fake_message(content=json.dumps(legacy, ensure_ascii=False)))])
    assert res.answer == "好的。" and reg.confirm_calls() == []
    assert WRITE_DRAFT_KEY not in state["agent"]


@pytest.mark.parametrize("value,expected", [(None, True), ("", True), ("  ", True),
                                            ("on", True), ("off", False)])
def test_switch_unset_and_empty_mean_on(monkeypatch, value, expected):
    """#6：未設與空字串皆為 on。"""
    if value is None:
        monkeypatch.delenv("AGENT_WRITE_DRAFT", raising=False)
    else:
        monkeypatch.setenv("AGENT_WRITE_DRAFT", value)
    assert WF.write_draft_enabled_from_env() is expected
    rt = _rt(_Provider([]), _Reg(_pool()))
    assert rt._write_draft_on is expected


def test_switch_invalid_value_fails_at_startup_with_reason(monkeypatch, caplog):
    """#6：值 `xyz` ⇒ 建構期失敗並印原因（訊息含變數名、壞值與允許值域）。"""
    monkeypatch.setenv("AGENT_WRITE_DRAFT", "xyz")
    with pytest.raises(ValueError) as exc:
        _rt(_Provider([]), _Reg(_pool()))
    assert "AGENT_WRITE_DRAFT" in str(exc.value) and "'xyz'" in str(exc.value)
    assert "on／off" in str(exc.value)
    assert "AGENT_WRITE_DRAFT" in caplog.text


async def test_intent_call_schema_lists_form_actions_and_keys_and_is_strict(api):
    """#6（W1b）：意圖判斷呼叫的 schema description 含表單導出的動作名與鍵名；每一層 object 都封閉
    （OpenAI strict）；同一個模型、`max_completion_tokens` 800；輸入＝系統句＋dialog＋當句。"""
    ident = _pm()
    state = {"agent": {"dialog": [{"role": "user", "content": "先前那句"},
                                  {"role": "assistant", "content": "先前的回覆"}]}}
    _res, _reg, provider, _ = await _turn(ident, "謝謝", state, [_out()])
    (call,) = provider.intent_calls
    assert call["model"] == provider.calls[0]["model"]
    assert call["max_completion_tokens"] == 800
    assert "tools" not in call
    rf = call["response_format"]
    assert rf["type"] == "json_schema" and rf["json_schema"]["strict"] is True
    assert rf["json_schema"]["name"] == WF.WRITE_INTENT_SCHEMA_NAME
    schema = rf["json_schema"]["schema"]
    descriptions = " ".join([schema["description"], schema["properties"]["action"]["description"],
                             schema["properties"]["fields"]["items"]["properties"]["key"]["description"]])
    for form in WF.FORMS.values():
        assert form.action in schema["description"]
        assert form.action in schema["properties"]["action"]["description"]
        for key in form.user_word_keys:
            assert key in schema["description"], key
            assert key in descriptions
    assert schema["properties"]["action"]["enum"] == [*WF.FORMS, "none"]
    key_enum = schema["properties"]["fields"]["items"]["properties"]["key"]["enum"]
    for system_key in ("estate_id", "contract_id", "date_expire_before", "date_expire_after"):
        assert system_key not in key_enum                       # system 來源鍵模型填不進來
    assert "bill_id" in key_enum                                 # 口述編號屬 user_words

    def walk(n):
        if isinstance(n, dict):
            assert "default" not in n
            if n.get("type") == "object" or "properties" in n:
                assert n.get("additionalProperties") is False
                assert set(n.get("required", [])) == set(n.get("properties", {}))
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)

    walk(schema)
    assert call["messages"] == [
        {"role": "system", "content": WF.WRITE_INTENT_SYSTEM_PROMPT},
        {"role": "user", "content": "先前那句"},
        {"role": "assistant", "content": "先前的回覆"},
        {"role": "user", "content": "謝謝"},
    ]
    assert WF.write_intent_description() in WF.WRITE_INTENT_SYSTEM_PROMPT


# ════════════════════════════════════════════════════════════════════
# #8 改談別的不污染草稿；捏造值進不了草稿；安全審查 F1～F4
# ════════════════════════════════════════════════════════════════════
async def test_fabricated_text_and_number_and_out_of_domain_enum_never_enter_draft(api):
    """#8：意圖呼叫填使用者沒講的文字／數字、值域外的 `emergency_status`（"3"）
    ⇒ 皆不進草稿並記 violation（正對照：同一筆裡使用者講過的物件名稱照常進）。"""
    state: dict = {}
    res, reg, *_ = await _turn(_pm(), f"{STUDENT_ESTATE} 要報修", state, [_out()], intents=[
        _intent("repair_create", estate_name=STUDENT_ESTATE, description="浴室漏水",
                emergency_status="3")])
    fields = _draft(state)["fields"]
    assert fields == {"estate_name": STUDENT_ESTATE}
    assert "write_intent_value_not_in_user_words" in res.trace.violations
    assert "write_intent_value_out_of_domain" in res.trace.violations
    state2: dict = {}
    res2, *_ = await _turn(_pm(), "我想把一張帳單延後繳", state2, [_out()],
                           intents=[_intent("bill_due_extend", days="30")])
    assert "days" not in _draft(state2)["fields"]
    assert "write_intent_value_not_in_user_words" in res2.trace.violations


async def test_model_confirm_payload_with_unsaid_text_never_enters_draft(api):
    """#8：模型 `confirm.request` payload 帶使用者沒講的文字 ⇒ 不進草稿並記 violation；
    系統解析的編號鍵一律不進。"""
    ident = _pm()
    state: dict = {}
    payload = {"action": "contract_create", "estate_name": STUDENT_ESTATE, "title": "捏造的合約名稱",
               "estate_id": 67338}
    res, reg, *_ = await _turn(ident, f"幫我建立{STUDENT_ESTATE}的合約", state, [
        _call("confirm.request", _confirm_args(payload))])
    fields = _draft(state)["fields"]
    assert fields == {"estate_name": STUDENT_ESTATE}
    assert "write_intent_value_not_in_user_words" in res.trace.violations
    assert res.outcome["state"] == "clarifying"                       # 模型那一次照舊（缺欄追問）


@pytest.mark.parametrize("raw,violation", [
    ('{"action": "pay_rent", "fields": []}', "write_intent_out_of_domain"),
    ('{"action": "repair_create", "fields": [{"key": "role_id", "value": "1"}]}',
     "write_intent_out_of_domain"),
    ('{"action": "repair_create", "fields": [{"key": "estate_id", "value": "67338"}]}',
     "write_intent_out_of_domain"),
    ('{"action": "repair_create", "fields": "not-a-list"}', "write_intent_out_of_domain"),
    ('{"action": 3, "fields": []}', "write_intent_out_of_domain"),
    ('not-an-object', "write_intent_unparsed"),
])
async def test_out_of_domain_intent_response_never_builds_a_draft(api, raw, violation):
    """#8（W1b 觀察點＝意圖呼叫的回應解析）：值域外的 `action`／`key`（含 system 鍵、身分鍵）或
    形狀壞掉 ⇒ 主回合 `answer` 照常出、草稿不建（整份意圖丟棄）、記 violation。"""
    state: dict = {}
    res, reg, provider, _ = await _turn(_pm(), "可以幫我處理嗎", state, [_out()], intents=[raw])
    assert len(provider.intent_calls) == 1
    assert violation in res.trace.violations
    assert res.answer == MODEL_TEXT
    assert _draft(state) is None and reg.confirm_calls() == []


async def test_draft_values_never_reach_decision_snapshot(api, monkeypatch):
    """#8：草稿值不出現在 `decision_snapshot`（只見動作名與鍵名）。"""
    captured: list = []
    monkeypatch.setattr(usage_metering, "set_agent_decision", lambda d: captured.append(d))
    state: dict = {}
    await _turn(_pm(), f"{STUDENT_ESTATE} 冷氣不冷", state, [_out()], intents=[
        _intent("repair_create", estate_name=STUDENT_ESTATE, description="冷氣不冷")])
    blob = json.dumps(captured, ensure_ascii=False)
    assert captured
    assert STUDENT_ESTATE not in blob and "冷氣不冷" not in blob
    assert "write_draft_action:repair_create" in blob                 # 正對照：鍵名有記
    assert "write_draft_keys:description,estate_name" in blob


async def test_f1_prospect_gets_no_intent_call_no_token_and_no_draft(api):
    """#8／F1：prospect 身分（看不到任何 `jgb2.action.*`）⇒ 不發意圖判斷呼叫、不寫 token、不建草稿；
    可見性閘本身另以「看得到修繕、看不到的動作」驗 `write_intent_action_not_visible`。"""
    state: dict = {}
    pool = _pool()
    res, reg, provider, _ = await _turn(_prospect(), "我要報修冷氣不冷", state, [_out()],
                                        intents=[_intent("repair_create", description="冷氣不冷")],
                                        pool=pool)
    assert provider.intent_calls == []
    assert WRITE_DRAFT_KEY not in state["agent"]
    assert reg.confirm_calls() == []
    pool.execute.assert_not_called()   # 原斷言保留（A7 前 INSERT 走這裡）
    assert pool.insert.call_count == 0 and pool.burn.call_count == 0
    # 可見性閘：草稿合併時對看不到的動作記 violation（registry 只露出修繕單）。
    class _OnlyRepair(_Reg):
        def specs_for(self, *a, **kw):
            return [s for s in self.inner.specs_for(*a, **kw)
                    if not str(s.get("name", "")).startswith("jgb2.action.")
                    or s["name"] == "jgb2.action.repair_create"]
    state2: dict = {}
    res2, reg2, p2, _ = await _turn(_pm(), "幫我建立一份新合約", state2, [_out()],
                                    intents=[_intent("contract_create")], reg=_OnlyRepair(_pool()))
    assert len(p2.intent_calls) == 1
    assert "write_intent_action_not_visible" in res2.trace.violations
    assert _draft(state2) is None and reg2.confirm_calls() == []


async def test_f2_full_tool_budget_then_answer_is_not_budget_exhausted(api):
    """#8／F2：模型先用滿工具預算再作答 ⇒ 程式觸發不計入、不受預算限制，答案不變成
    `budget_exhausted`（得程式追問句）。"""
    budget = Budget(max_tool_calls=3)
    query = ("jgb2.query.estates", {"face": "物件現況診斷", "keyword": "不存在的物件XYZ"})
    script = [_call(*query, call_id=f"q{i}") for i in range(3)]
    script.append(_out())
    state: dict = {}
    res, reg, provider, _ = await _turn(_pm(), "幫我看一下然後報修", state, script, budget=budget,
                                        intents=[_intent("repair_create")])
    assert len([r for r in res.trace.tool_calls if r.name == "jgb2.query.estates"]) == 3   # 前提：用滿
    assert (res.handoff or {}).get("reason") != "budget_exhausted"
    assert res.answer == ASK_TEXT.format(labels="物件、問題描述")
    assert len(_program_records(res)) == 1
    # 正對照：預算真的用滿了——模型自己再打第 4 次工具就是 budget_exhausted。
    script2 = [_call(*query, call_id=f"q{i}") for i in range(4)]
    res2, *_ = await _turn(_pm(), "幫我看一下然後報修", {}, script2, budget=budget)
    assert res2.handoff["reason"] == "budget_exhausted"


async def test_f3_photo_turn_model_confirm_keeps_photo_description_out_of_draft(api):
    """#8／F3：照片回合模型自己呼叫 `confirm.request` ⇒ 照片辨識描述不進草稿、不進下一回合 messages。"""
    ident = _pm()
    photo_desc = "天花板有明顯水漬與剝落痕跡"
    image = ImageTurnInput(status="ok", facts="照片看起來是房屋結構類的損壞。", processed=1, total=1,
                           suggested_category="天花板", suggested_description=photo_desc)
    state: dict = {}
    res1, reg1, *_ = await _turn(ident, "幫我報修這個", state, [
        _call("confirm.request", _confirm_args({"action": "repair_create"}))], image=image)
    (args1, first), = reg1.confirm_calls()
    assert photo_desc in json.loads(args1["payload"])["description"]   # 前提：照片描述進了那一次 payload
    assert first.data["missing_fields"] == ["物件"]
    draft = _draft(state)
    assert draft is not None and photo_desc not in json.dumps(draft, ensure_ascii=False)
    res2, reg2, p2, _ = await _turn(ident, "謝謝", state, [_out()])
    assert photo_desc not in json.dumps(p2.calls[0]["messages"], ensure_ascii=False)
    assert photo_desc not in json.dumps(p2.intent_calls[0]["messages"], ensure_ascii=False)
    assert "進行中的建立：建立修繕單" in json.dumps(p2.calls[0]["messages"], ensure_ascii=False)


async def test_f4_injection_is_not_citable_reserved_and_forged_id_rejected(api, monkeypatch):
    """#8／F4：草稿注入段 `citable=False`、id 在 `ReservedCallIds` 內、只放標籤、排在使用者這句之前；
    模型偽造同 id ⇒ `tool_call_id_collides_with_reserved`。"""
    nonce = "0123456789abcdef"
    monkeypatch.setattr(runtime_mod, "new_nonce", lambda: nonce)
    ids = ReservedCallIds.from_nonce(nonce)
    assert ids.write_draft == "wd-01234567" and ids.write_draft in ids.all
    injected: list = []
    real_inject = TurnAccumulator.inject

    def _spy(self, label, call_id, text, *, citable, source, data=None):
        injected.append((label, call_id, text, citable))
        return real_inject(self, label, call_id, text, citable=citable, source=source, data=data)

    monkeypatch.setattr(TurnAccumulator, "inject", _spy)
    ident = _pm()
    state = _seed(ident, "repair_create", {"estate_name": STUDENT_ESTATE}, users=[STUDENT_ESTATE])
    forged = _call("jgb2.query.estates", {"face": "物件現況診斷", "keyword": "不存在的物件XYZ"},
                   call_id=ids.write_draft)
    sent: list = []

    def _first(kwargs):
        sent.append(json.loads(json.dumps(kwargs["messages"], ensure_ascii=False)))   # 當下快照
        return forged

    res, reg, provider, _ = await _turn(ident, "幫我看看", state, [_first, _out()])
    wd = [i for i in injected if i[0] == runtime_mod.WRITE_DRAFT_LABEL]
    assert len(wd) == 1
    _label, call_id, text, citable = wd[0]
    assert call_id == ids.write_draft and citable is False
    assert text == "進行中的建立：建立修繕單；已有：物件；還缺：問題描述"
    assert STUDENT_ESTATE not in text                                  # ⛔ 放使用者值
    first_msgs = sent[0]
    assert first_msgs[-1] == {"role": "user", "content": "幫我看看"}  # DSP-022：使用者這句最後
    assert any(f":{ids.write_draft}:" in str(m.get("content")) for m in first_msgs[:-1])
    assert "tool_call_id_collides_with_reserved" in res.trace.violations


# ════════════════════════════════════════════════════════════════════
# #8 W1b：續答由程式接收、問句凍結、物件補值
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("text,expected", [
    ("冷氣不冷嗎", True), ("可以嗎？", True), ("可以?", True), ("可以﹖", True), ("可以？ ", True),
    ("那押金呢", True), ("可以嗎。", True), ("好嗎！", True), ("好嗎~", True), ("好嗎～", True),
    ("好嗎…", True), ("好嗎...", True), ("好嗎、", True), ("好嗎​", True), ("好嗎\n", True),
    ("租金可以設定自動扣款嗎", True), ("A棟呢", True),
    ("冷氣不冷", False), ("嗎啡很貴", False), ("延 7 天", False), ("", False), ("冷氣不冷。", False),
    (STUDENT_ESTATE, False), (None, False),
])
def test_question_rule_is_structural(text, expected):
    """#8 W1b（§8.1-2／安全處置 5b）：問句判準——`sanitize_data_piece`＋NFKC 後，去尾端空白與
    句末字元（。！!～~、.…），最後是「？」「?」「﹖」或「嗎」「呢」⇒ 問句。"""
    assert _is_question(text) is expected


async def _program_ask_description(ident, state) -> None:
    """前置：真的程式缺欄追問回合，只缺問題描述（`asked=[description]`）。"""
    res, *_ = await _turn(ident, f"{STUDENT_ESTATE} 要報修", state, [_out()],
                          intents=[_intent("repair_create", estate_name=STUDENT_ESTATE)])
    assert res.answer == ASK_TEXT.format(labels="問題描述")              # 前提：程式追問
    assert _draft(state)["asked"] == ["description"]


async def test_statement_answer_after_program_ask_fills_the_asked_text_field_and_issues_card(api):
    """#8 W1b：非問句的續答 ⇒ 填入上回合程式追問的第一個（唯一一個）文字欄位，程式觸發出卡
    （意圖呼叫回 none 也接得到——續答不問模型）。"""
    ident = _pm()
    state: dict = {}
    await _program_ask_description(ident, state)
    res, reg, provider, _ = await _turn(ident, "冷氣不冷", state, [_out()])     # 意圖＝none
    assert "write_draft_answer_filled" in res.trace.violations
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert "・問題描述：冷氣不冷" in res.answer
    assert f"・物件：{STUDENT_ESTATE}" in res.answer


async def test_question_after_program_ask_freezes_the_draft_and_main_model_answers(api):
    """#8 W1b（§8.5-3）：程式追問後送「冷氣不冷嗎」且意圖假回應帶 `repair_create`／`description`
    ⇒ 草稿不變（除 `asked` 清空）、不觸發、answer 為主模型輸出、閒置計數不加。"""
    ident = _pm()
    state: dict = {}
    await _program_ask_description(ident, state)
    before = json.loads(json.dumps(_draft(state)))
    res, reg, provider, _ = await _turn(ident, "冷氣不冷嗎", state, [_out("冷氣不冷可能是濾網髒了。")],
                                        intents=[_intent("repair_create", description="冷氣不冷")])
    assert res.answer == "冷氣不冷可能是濾網髒了。"
    assert reg.confirm_calls() == [] and not _program_records(res)
    assert "write_draft_question_frozen" in res.trace.violations
    after = _draft(state)
    assert after == dict(before, asked=[])
    assert after["idle_turns"] == before["idle_turns"] == 0


async def test_question_frozen_turn_does_not_inject_the_draft_line(api):
    """#8（W1c verifier F1）：問句凍結回合 ⛔ 注入「進行中的建立」那一行（交主模型正常回答）；
    正對照：同一份草稿在非問句回合仍會注入。"""
    ident = _pm()
    state: dict = {}
    await _program_ask_description(ident, state)
    res, reg, provider, _ = await _turn(ident, "租金可以設定自動扣款嗎", state, [_out("可以設定。")])
    assert "write_draft_question_frozen" in res.trace.violations
    assert "進行中的建立" not in json.dumps(provider.calls[0]["messages"], ensure_ascii=False)
    res2, reg2, provider2, _ = await _turn(ident, "冷氣也有異音", state, [_out()])
    assert any("進行中的建立" in json.dumps(c["messages"], ensure_ascii=False) for c in provider2.calls) \
        or reg2.confirm_calls() != [] or _program_records(res2)


async def test_question_with_another_action_intent_does_not_switch_the_draft(api):
    """#8 W1b（§8.5-3「含不同動作的換草稿」）：凍結回合意圖假回應帶另一動作 ⇒ 草稿不被換。"""
    ident = _pm()
    state: dict = {}
    await _program_ask_description(ident, state)
    res, reg, provider, _ = await _turn(ident, "那帳單可以延後繳嗎", state, [_out()],
                                        intents=[_intent("bill_due_extend")])
    assert _draft(state)["action"] == "repair_create"
    assert _draft(state)["fields"] == {"estate_name": STUDENT_ESTATE}
    assert reg.confirm_calls() == []


async def test_program_ask_then_question_then_statement_is_not_filled(api):
    """#8 W1b 安全（1c）：「程式追問→問句（凍結）→陳述」第三句不被整句填入（`asked` 讀出即清）。"""
    ident = _pm()
    state: dict = {}
    await _program_ask_description(ident, state)
    await _turn(ident, "冷氣不冷嗎", state, [_out("可能是濾網髒了。")])
    assert _draft(state)["asked"] == []
    res, reg, *_ = await _turn(ident, "冷氣不冷", state, [_out()])
    assert "write_draft_answer_filled" not in res.trace.violations
    assert _draft(state)["fields"] == {"estate_name": STUDENT_ESTATE}
    assert reg.confirm_calls() == []


async def test_model_written_ask_is_not_followed_by_whole_sentence_fill(api):
    """#8 W1b r2：模型自寫追問（`kind=ask`、`ask_target=description`，經 Verifier）⛔ 寫 `asked`
    ⇒ 下一句不被整句填入。"""
    ident = _pm()
    state = _seed(ident, "repair_create", {"estate_name": STUDENT_ESTATE}, users=[STUDENT_ESTATE])
    res1, *_ = await _turn(ident, "我要報修", state,
                           [_out("請問是什麼問題？", kind="ask", ask_target="description")],
                           intents=[_intent("repair_create")])
    assert state["agent"][LAST_ASK_TARGET_KEY] == "description"     # 前提：上回合是追問 description
    assert "confirm_missing_fields_ask" not in res1.trace.violations
    assert _draft(state)["asked"] == []
    res2, reg2, *_ = await _turn(ident, "冷氣不冷", state, [_out()])
    assert "write_draft_answer_filled" not in res2.trace.violations
    assert "description" not in _draft(state)["fields"]
    assert reg2.confirm_calls() == []


async def test_bill_days_program_ask_keeps_asked_readable_and_receives_days(api):
    """#8 W1b r2：`bill_due_extend` 缺 `days` 的程式追問（`ask_target=None`）之後，`asked` 仍讀得到
    （＝[days]）並可接收（意圖呼叫抽出 days ⇒ 出卡 709744）。"""
    ident = _pm()
    state: dict = {"agent": {"dialog": [{"role": "user", "content": "我想把一張帳單延後繳"},
                                        {"role": "assistant", "content": "好的。"}]}}
    res1, *_ = await _turn(ident, SCRIPT_D2, state, [_call("confirm.request", _confirm_args(
        {"action": "bill_due_extend", "estate_name": KEELUNG_ESTATE, "period": "11月那期"}))])
    assert res1.answer == ASK_TEXT.format(labels="延後天數")
    assert state["agent"][LAST_ASK_TARGET_KEY] is None
    assert _draft(state)["asked"] == ["days"]
    seen: list = []
    real_begin = AgentRuntime._write_draft_begin

    def _spy(self, acc, *a, **kw):
        real_begin(self, acc, *a, **kw)
        seen.append(list(acc.write_draft.asked))

    AgentRuntime._write_draft_begin = _spy
    try:
        res2, reg2, *_ = await _turn(ident, "延 7 天", state, [_out()],
                                     intents=[_intent("bill_due_extend", days="7")])
    finally:
        AgentRuntime._write_draft_begin = real_begin
    assert seen == [["days"]]
    assert res2.outcome["state"] == "confirm_pending", res2.answer
    assert "・帳單編號：709744" in res2.answer and "・延後天數：7 天" in res2.answer


@pytest.mark.parametrize("intent_fields,expect_period", [
    ({}, None),                                           # 意圖呼叫沒抽到 ⇒ 期別仍缺
    # 期別片 P-2：期別改 `period` 型 ⇒ 草稿存值閘正規化的年月（TODAY=2026-10-17、11 月 ⇒ 2026/11），
    # ⛔ 模型原字；本測試的意圖（期別只來自意圖呼叫、⛔ 整句原文）不變。
    ({"estate_name": KEELUNG_ESTATE, "period": "11月那期"}, "2026/11"),
])
async def test_script_d_second_sentence_never_whole_fills_period(api, intent_fields, expect_period):
    """#8 W1b r2：缺 [物件, 期別, 延後天數] 後輸入腳本 D 第二句 ⇒ `period` 不是整句原文
    （`asked` 三欄 ⇒ 不整句填入；期別只來自意圖呼叫）。"""
    ident = _pm()
    state: dict = {}
    res1, *_ = await _turn(ident, "我想把一張帳單延後繳", state, [_out()],
                           intents=[_intent("bill_due_extend")])
    assert res1.answer == ASK_TEXT.format(labels="物件、期別、延後天數")
    assert _draft(state)["asked"] == ["estate_name", "period", "days"]
    res2, *_ = await _turn(ident, SCRIPT_D2, state, [_out()],
                           intents=[_intent("bill_due_extend", **intent_fields)])
    fields = _draft(state)["fields"]
    assert fields.get("period") != SCRIPT_D2
    assert fields.get("period") == expect_period
    assert "write_draft_answer_filled" not in res2.trace.violations


@pytest.mark.parametrize("intent_desc,expected", [
    ("冷氣不冷", "冷氣不冷"),                             # 通過值閘 ⇒ 意圖呼叫值優先
    ("浴室漏水", "冷氣不冷，麻煩盡快"),                   # 不過值閘 ⇒ 用整句值
])
async def test_intent_value_passing_gate_wins_over_whole_sentence(api, intent_desc, expected):
    """#8 W1b r2：同欄衝突時，意圖呼叫值（通過值閘）優先於整句值；不過閘 ⇒ 整句值。"""
    ident = _pm()
    state: dict = {}
    await _program_ask_description(ident, state)
    res, *_ = await _turn(ident, "冷氣不冷，麻煩盡快", state, [_out()],
                          intents=[_intent("repair_create", description=intent_desc)])
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert f"・問題描述：{expected}\n" in res.answer


async def test_other_write_action_statement_is_not_filled_as_description(api):
    """#8 W1b 安全（1a）：程式追問描述→「幫我延後帳單七天」（意圖＝`bill_due_extend`）
    ⇒ `description` 不被填；草稿換成延期繳費並由程式追問其缺欄。"""
    ident = _pm()
    state: dict = {}
    await _program_ask_description(ident, state)
    res, reg, *_ = await _turn(ident, "幫我延後帳單七天", state, [_out()],
                               intents=[_intent("bill_due_extend")])
    assert "write_draft_answer_filled" not in res.trace.violations
    draft = _draft(state)
    assert draft["action"] == "bill_due_extend" and "description" not in draft["fields"]
    assert res.answer == ASK_TEXT.format(labels="物件、期別、延後天數")


async def test_switching_draft_clears_asked(api):
    """#8 W1b 安全（1b）：換草稿時一併清 `asked`（敏感轉人輸出 ⇒ 不觸發，看得到換完的草稿原樣）。"""
    ident = _pm()
    state: dict = {}
    await _program_ask_description(ident, state)
    res, reg, *_ = await _turn(ident, "其實我要建立一份新合約", state, [
        _out("", kind="handoff", fact_class="pricing", handoff_reason="sensitive_no_grounding")],
        intents=[_intent("contract_create")])
    draft = _draft(state)
    assert draft["action"] == "contract_create" and draft["asked"] == [] and draft["fields"] == {}
    assert reg.confirm_calls() == []


async def test_name_caught_when_draft_lacks_estate_without_estate_ask(api):
    """#8 W1b（§8.1-3）：草稿缺物件時，當句唯一命中物件即補（上回合**不需**追問物件；
    名稱 9 字 > 6 ⇒ 靠草稿條件把前置查詢以 `after_name_ask=True` 跑）。"""
    ident = _pm()
    state = _seed(ident, "repair_create", {"description": "冷氣不冷"}, users=["冷氣不冷"])
    assert state["agent"].get(LAST_ASK_TARGET_KEY) is None                 # 前提：沒有追問物件
    res, reg, *_ = await _turn(ident, STUDENT_ESTATE, state, [_out()])
    assert "write_draft_name_caught" in res.trace.violations
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert f"・物件：{STUDENT_ESTATE}" in res.answer
    # 正對照：沒有草稿時同一句不觸發 7～30 字的名稱查詢。
    res0, reg0, *_ = await _turn(ident, STUDENT_ESTATE, {}, [_out()])
    assert not [r for r in reg0.results if r[0] == "jgb2.query.estates"]


async def test_answer_after_description_ask_never_becomes_estate_name(api):
    """#8 W1b 安全（2b）：追問描述→答「頂樓」且替身唯一命中 ⇒ 不寫 `estate_name`
    （正對照：`asked` 為空時同一替身命中 ⇒ 寫入列上 `title`，2a）。"""
    ident = _pm()
    override = {"頂樓": _unique_estate_hit()}
    state = _seed(ident, "repair_create", {}, users=["我要報修"], asked=["description"])
    triggered: list = []
    real = runtime_mod._write_draft_program_message

    def _spy(draft, nonce):
        triggered.append(dict(draft["fields"]))
        return real(draft, nonce)

    runtime_mod._write_draft_program_message = _spy
    try:
        res, reg, *_ = await _turn(ident, "頂樓", state, [_out()],
                                   reg=_Reg(_pool(), estates_override=override))
    finally:
        runtime_mod._write_draft_program_message = real
    assert any(r[0] == "jgb2.query.estates" for r in reg.results)          # 前提：替身真的被查到
    assert "write_draft_name_caught" not in res.trace.violations
    # 草稿（程式觸發當下）沒有 estate_name；整句依 §8.5-2 進了唯一被追問的 description。
    assert triggered == [{"description": "頂樓"}]
    # ⚠️ 既有「物件記憶」（第六批 #10 寫點 (b)／讀點）不屬草稿：前置查詢唯一命中照舊寫
    #    `estate_carry`，`confirm.request` 缺 estate_name 時照舊由它補——本測試只鎖草稿不被寫。
    assert "estate_carry_applied:estate_name" in res.trace.violations
    state2 = _seed(ident, "repair_create", {}, users=["我要報修"])
    res2, *_ = await _turn(ident, "頂樓", state2, [_out()],
                           reg=_Reg(_pool(), estates_override=override))
    assert "write_draft_name_caught" in res2.trace.violations
    assert _draft(state2)["fields"]["estate_name"] == STUDENT_ESTATE          # 列上 title


async def test_question_like_name_answer_is_frozen_even_with_unique_hit(api):
    """#8 W1b 安全（5a）：程式追問後答「A棟呢」且替身唯一命中 ⇒ 草稿不變（凍結包住補名稱）；
    正對照：答「A棟」⇒ 補進名稱。"""
    ident = _pm()
    override = {"A棟呢": _unique_estate_hit(), "A棟": _unique_estate_hit()}
    state: dict = {}
    await _turn(ident, "能幫我新增一張修繕單嗎", state, [_out()], intents=[_intent("repair_create")])
    assert _draft(state)["asked"] == ["estate_name", "description"]
    res, reg, *_ = await _turn(ident, "A棟呢", state, [_out()],
                               reg=_Reg(_pool(), estates_override=override))
    assert any(r[0] == "jgb2.query.estates" for r in reg.results)
    assert _draft(state)["fields"] == {} and "write_draft_name_caught" not in res.trace.violations
    state2: dict = {}
    await _turn(ident, "能幫我新增一張修繕單嗎", state2, [_out()], intents=[_intent("repair_create")])
    res2, *_ = await _turn(ident, "A棟", state2, [_out()],
                           reg=_Reg(_pool(), estates_override=override))
    assert _draft(state2)["fields"] == {"estate_name": STUDENT_ESTATE}


async def test_document_turn_never_writes_asked(api):
    """#8 W1b 安全（1d）：文件回合的程式缺欄追問 ⛔ 寫 `asked`、⛔ 建草稿，也不發意圖呼叫。"""
    from tests.unit.agent.test_assistant_documents_photos_req import _receipt_doc

    payload = {"action": "manual_bill_create", "contract_ref": "89481", "title": "管理費",
               "date_expire": "20261130"}
    state: dict = {"agent": {}}
    res, reg, provider, _ = await _turn(_pm(), "開到合約 89481，期限 20261130", state,
                                        [_call("confirm.request", _confirm_args(payload)), _out()],
                                        document=_receipt_doc())
    assert "confirm_missing_fields_ask" in res.trace.violations          # 前提：真的程式追問
    assert WRITE_DRAFT_KEY not in state["agent"]
    assert provider.intent_calls == []


@pytest.mark.parametrize("message", ["confirm_submit:0123456789abcdef", "select:bill:709744"])
async def test_confirm_submit_and_select_turns_create_no_intent_task(api, message):
    """#8 W1b 安全（3a）：`confirm_submit`／`select:` 回合（程式段結束回合）不建立意圖 task。"""
    created: list = []
    real = AgentRuntime._start_write_intent_call

    def _spy(self, acc, *a, **kw):
        created.append(acc.trace_id)
        return real(self, acc, *a, **kw)

    AgentRuntime._start_write_intent_call = _spy
    try:
        res, reg, provider, _ = await _turn(_pm(), message, {}, [])
    finally:
        AgentRuntime._start_write_intent_call = real
    assert created == [] and provider.intent_calls == [] and provider.calls == []
    assert not any(str(v).startswith("write_intent") for v in res.trace.violations)


# ════════════════════════════════════════════════════════════════════
# #8 W1b：意圖判斷呼叫的解析、逾時、收尾與計量
# ════════════════════════════════════════════════════════════════════
#: `~/jgb-archive/bedrock-eval-20261017/w1/probe/probe_raw.json`／`probe2_raw.json` 的真實回應形狀
#: （推理段文字縮短；最終段原樣）。
_PROBE_SHAPES = [
    ('<reasoning>User asks to create a repair order.</reasoning>{\n  "{"action":"repair_create","fields":[] }',
     {"action": "repair_create", "fields": []}),
    ('<reasoning>No action.</reasoning>{\n{\n  "action": "none",\n  "fields": []\n}',
     {"action": "none", "fields": []}),
    ('<reasoning>x</reasoning>{\n {"action":"none","fields":[] }', {"action": "none", "fields": []}),
    ('<reasoning>x</reasoning>{\n  "{ "action": "bill_due_extend", "fields": [ { "key": "estate_name", '
     '"value": "基隆溫馨一人宅套房" }, { "key": "period", "value": "11月那期" }, { "key": "days", '
     '"value": "7" } ] }',
     {"action": "bill_due_extend", "fields": [{"key": "estate_name", "value": "基隆溫馨一人宅套房"},
                                             {"key": "period", "value": "11月那期"},
                                             {"key": "days", "value": "7"}]}),
    ('<reasoning>x</reasoning>{"{  "action": "none",  "fields": [] }', {"action": "none", "fields": []}),
    ('<reasoning>x</reasoning>action{"answers_pending":false,"action":"none","fields":[]}',
     {"answers_pending": False, "action": "none", "fields": []}),
    ('{"action":"repair_create","fields":[]}', {"action": "repair_create", "fields": []}),
]


@pytest.mark.parametrize("raw,expected", _PROBE_SHAPES)
def test_parse_handles_bedrock_prefix_garbage_with_raw_decode(raw, expected):
    """#8 W1b：意圖呼叫回傳前綴殘缺時以逐位置 `raw_decode` 解出（只解析 `</reasoning>` 之後）。"""
    assert WF.parse_write_intent_content(raw) == (expected, WF.PARSE_OK)


@pytest.mark.parametrize("raw,status", [
    ("", WF.PARSE_UNPARSED),
    ('<reasoning>x</reasoning>{\n{"answers_pending":\n  \n  \t\n', WF.PARSE_UNPARSED),   # 截斷
    ('<reasoning>{"action":"contract_create","fields":[]}', WF.PARSE_UNPARSED),           # 推理沒收尾
    ('{"fields": []}', WF.PARSE_UNPARSED),
    ('{"action":"repair_create","fields":[]} {"action":"bill_due_extend","fields":[]}',
     WF.PARSE_AMBIGUOUS),
    (None, WF.PARSE_UNPARSED),
])
def test_parse_unparsable_or_ambiguous(raw, status):
    """#8 W1b（安全處置 3c）：全無法解析 ⇒ unparsed；多個內容不同的 action 物件 ⇒ ambiguous。"""
    assert WF.parse_write_intent_content(raw) == (None, status)


def test_parse_ignores_json_inside_reasoning_and_dedups_identical_objects():
    """#8 W1b（3c）：推理段裡的偽造 JSON 不搶先被解析；同一物件重複出現 ⇒ 仍是那一個。"""
    raw = '<reasoning>{"action":"contract_create","fields":[]}</reasoning>{"action":"none","fields":[]}'
    assert WF.parse_write_intent_content(raw) == ({"action": "none", "fields": []}, WF.PARSE_OK)
    dup = '{"action":"repair_create","fields":[]}\n{"action":"repair_create","fields":[]}'
    assert WF.parse_write_intent_content(dup) == ({"action": "repair_create", "fields": []},
                                                  WF.PARSE_OK)


async def test_prefix_garbage_intent_drives_the_flow_and_unparsed_counts_as_none(api):
    """#8 W1b：前綴殘缺的真實形狀照樣驅動流程（建草稿＋程式追問）；全無法解析 ⇒
    `write_intent_unparsed`、視為 none（主回合照常）；多個不同 action ⇒ `write_intent_ambiguous`。"""
    state: dict = {}
    res, *_ = await _turn(_pm(), "能幫我新增一張修繕單嗎", state, [_out()], intents=[_PROBE_SHAPES[0][0]])
    assert res.answer == ASK_TEXT.format(labels="物件、問題描述")
    state2: dict = {}
    res2, *_ = await _turn(_pm(), "能幫我新增一張修繕單嗎", state2, [_out()],
                           intents=['<reasoning>x</reasoning>{\n{"action":\n  \n'])
    assert "write_intent_unparsed" in res2.trace.violations
    assert res2.answer == MODEL_TEXT and _draft(state2) is None
    state3: dict = {}
    res3, *_ = await _turn(_pm(), "能幫我新增一張修繕單嗎", state3, [_out()], intents=[
        '{"action":"repair_create","fields":[]}{"action":"contract_create","fields":[]}'])
    assert "write_intent_ambiguous" in res3.trace.violations
    assert res3.answer == MODEL_TEXT and _draft(state3) is None


async def test_intent_timeout_does_not_affect_main_turn(api, monkeypatch):
    """#8 W1b：意圖呼叫逾時 ⇒ 視為 none、記 `write_intent_call_failed`，主回合照常；組 trace 時
    仍未完成 ⇒ 取消（`write_intent_call_cancelled`、以輸入字元數估算計入 prompt token）。"""
    monkeypatch.setattr(runtime_mod, "WRITE_INTENT_WAIT_MAX_S", 0.05)
    tasks: list = []

    async def _hang(kwargs):
        tasks.append(asyncio.current_task())
        await asyncio.sleep(30)

    state: dict = {}
    res, reg, provider, _ = await _turn(_pm(), "能幫我新增一張修繕單嗎", state, [_out()],
                                        intents=[_hang])
    assert res.answer == MODEL_TEXT and reg.confirm_calls() == []
    assert "write_intent_call_failed" in res.trace.violations
    assert "write_intent_call_cancelled" in res.trace.violations
    chars = sum(len(m["content"]) for m in provider.intent_calls[0]["messages"])
    assert res.trace.prompt_tokens == 10 + int(chars / 1.1)          # 主模型 10＋估算
    await asyncio.sleep(0)
    assert tasks and all(t.done() for t in tasks)                     # 無殘留 pending task


async def test_intent_failure_does_not_affect_main_turn(api):
    """#8 W1b：意圖呼叫失敗（例外）⇒ 視為 none、記 `write_intent_call_failed`，主回合照常。"""
    def _boom(kwargs):
        raise RuntimeError("bedrock 500")

    res, reg, *_ = await _turn(_pm(), "能幫我新增一張修繕單嗎", {}, [_out()], intents=[_boom])
    assert res.answer == MODEL_TEXT and "write_intent_call_failed" in res.trace.violations
    assert "write_intent_call" not in res.trace.violations


async def test_completed_intent_call_is_metered_into_the_normal_trace(api, monkeypatch):
    """#8 W1b（§8.5-4）：一般出口（`build_trace`）——已完成的意圖呼叫經 `add_llm_usage` 計量、
    token 計入本回合 trace、記 `write_intent_call`；`llm_calls` 只算主模型。"""
    metered: list = []
    real = usage_metering.add_llm_usage
    monkeypatch.setattr(usage_metering, "add_llm_usage",
                        lambda model, usage: (metered.append((model, dict(usage))), real(model, usage)))
    res, reg, provider, _ = await _turn(_pm(), "謝謝", {}, [_out()], intents=[_intent(pt=11, ct=4)])
    assert res.trace.prompt_tokens == 10 + 11 and res.trace.completion_tokens == 5 + 4
    assert res.trace.llm_calls == 1
    assert "write_intent_call" in res.trace.violations
    assert (provider.calls[0]["model"], {"prompt_tokens": 11, "completion_tokens": 4}) in metered


@pytest.mark.parametrize("finished", [True, False])
async def test_early_confirm_exit_settles_the_intent_task(api, finished):
    """#8 W1b r2：模型先呼叫 `confirm.request` 得缺欄（提前出口，`_finish_confirm_turn`）⇒ 意圖 task
    已計量（跑完了：token 含在 `result.trace`）或被取消（沒跑完：估算計入），無殘留 pending task。"""
    tasks: list = []

    async def _step(kwargs):
        tasks.append(asyncio.current_task())
        if not finished:
            await asyncio.sleep(30)
        return _intent(pt=11, ct=4)

    state: dict = {}
    res, reg, provider, _ = await _turn(
        _pm(), "幫我報修", state,
        [_call("confirm.request", _confirm_args({"action": "repair_create"}))],
        intents=[_step], reg=_Reg(_pool(), yield_first=3))
    assert "confirm_missing_fields_ask" in res.trace.violations         # 前提：提前出口
    assert len(provider.intent_calls) == 1
    if finished:
        assert "write_intent_call" in res.trace.violations
        assert (res.trace.prompt_tokens, res.trace.completion_tokens) == (10 + 11, 5 + 4)
    else:
        assert "write_intent_call_cancelled" in res.trace.violations
        chars = sum(len(m["content"]) for m in provider.intent_calls[0]["messages"])
        assert (res.trace.prompt_tokens, res.trace.completion_tokens) == (10 + int(chars / 1.1), 5)
    await asyncio.sleep(0)
    assert tasks and all(t.done() for t in tasks)


async def test_turn_exception_aborts_the_intent_task(api):
    """回合以例外離開（沒有 trace 可組）⇒ 意圖 task 被撤、登記清空（⛔ 孤兒呼叫）。"""
    tasks: list = []

    async def _hang(kwargs):
        tasks.append(asyncio.current_task())
        await asyncio.sleep(30)

    def _explode(kwargs):
        raise RuntimeError("main model down")

    provider = _Provider([_explode], [_hang])
    rt = _rt(provider, _Reg(_pool()))
    with pytest.raises(RuntimeError):
        await rt.run_turn(_pm(), "能幫我新增一張修繕單嗎", {})
    assert rt._write_intent_calls == {}
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert all(t.done() for t in tasks)


# ════════════════════════════════════════════════════════════════════
# 生命週期與讀回驗形狀（§2.1(3)；W1b `asked`）
# ════════════════════════════════════════════════════════════════════
async def test_two_idle_turns_clear_the_draft(api):
    ident = _pm()
    state = _seed(ident, "repair_create", {"estate_name": STUDENT_ESTATE}, users=[STUDENT_ESTATE])
    await _turn(ident, "租金可以設定自動扣款嗎", state, [_out()])
    assert _draft(state)["idle_turns"] == 1
    res, *_ = await _turn(ident, "那押金呢", state, [_out()])
    assert _draft(state) is None and "write_draft_cleared_idle" in res.trace.violations


async def test_other_identity_or_bad_shape_discards_the_draft(api):
    ident = _pm()
    state = _seed(_pm(user="990002"), "repair_create", {"estate_name": STUDENT_ESTATE})
    await _turn(ident, "謝謝", state, [_out()])
    assert _draft(state) is None
    bad = {"agent": {WRITE_DRAFT_KEY: {"action": "repair_create", "fields": {"role_id": "1"},
                                       "idle_turns": 0, "asked": [],
                                       "created_by_role": runtime_mod._write_draft_owner(ident)}}}
    res, *_ = await _turn(ident, "謝謝", bad, [_out()])
    assert _draft(bad) is None and "write_draft_shape_invalid" in res.trace.violations


@pytest.mark.parametrize("asked,ok", [
    ([], True),
    (["description"], True),
    (["estate_name", "description"], True),
    ("description", False),                       # 不是清單
    (["description", "description"], False),      # 重複
    (["days"], False),                            # 別的動作的鍵
    (["category_name", "estate_name", "description", "emergency_status", "x"], False),  # 過長＋表外
    ([1], False),
    (None, False),
])
def test_load_draft_validates_asked(asked, ok):
    """W1b §8.5-1／安全處置 4b：`asked` 讀回驗形狀——清單、元素為該動作表單的 `user_words` 鍵、
    不重複、長度 ≤ 表單欄位數；不合 ⇒ 整份丟棄。"""
    raw = {"action": "repair_create", "fields": {}, "idle_turns": 0, "created_by_role": "x",
           "asked": asked}
    draft, invalid = WF.load_draft(raw)
    assert (draft is not None, invalid) == (ok, not ok)
    # 系統來源鍵不收（延期繳費的原到期日屬 system）。
    sys_raw = dict(raw, action="bill_due_extend", asked=["date_expire_before"])
    assert WF.load_draft(sys_raw) == (None, True)
    # 少了 `asked`（W1 的四鍵形狀）⇒ 形狀不合。
    legacy = {k: v for k, v in raw.items() if k != "asked"}
    assert WF.load_draft(legacy) == (None, True)


def test_asked_keys_for_labels_maps_labels_and_group_labels():
    assert WF.asked_keys_for_labels("repair_create", ["物件", "問題描述"]) == ["estate_name", "description"]
    assert WF.asked_keys_for_labels("bill_due_extend", ["物件", "期別"]) == ["estate_name", "period"]
    assert WF.asked_keys_for_labels("contract_create", ["承租人 Email 或電話"]) == [
        "to_user_email", "to_user_phone"]
    assert WF.asked_keys_for_labels("manual_bill_create", ["合約"]) == ["contract_ref"]
    assert WF.asked_keys_for_labels("nope", ["物件"]) == []


async def test_pinned_scope_neither_injects_nor_triggers(api):
    ident = _pm()
    state = _seed(ident, "repair_create", {"estate_name": STUDENT_ESTATE}, users=[STUDENT_ESTATE],
                  asked=["description"])
    state["agent"]["select_scope"] = {"type": "bill", "estate_id": "67338"}
    res, reg, provider, _ = await _turn(ident, "冷氣不冷", state, [_out()],
                                        intents=[_intent("repair_create", description="冷氣不冷")])
    assert "進行中的建立" not in json.dumps(provider.calls[0]["messages"], ensure_ascii=False)
    assert reg.confirm_calls() == [] and _draft(state) is None
    assert provider.intent_calls == []


def test_forms_cover_exactly_the_confirm_actions_and_hold_no_identity_keys():
    from services.agent.confirm_card import CONFIRM_ACTIONS, IDENTITY_OWNERSHIP_KEYS
    from services.agent.tools.action import ACTION_SPECS

    assert list(WF.FORMS) == list(CONFIRM_ACTIONS)
    assert {s["name"].split(".")[-1] for s, _ in ACTION_SPECS} == set(WF.FORMS)
    for form in WF.FORMS.values():
        assert not set(form.keys) & IDENTITY_OWNERSHIP_KEYS


# ════════════════════════════════════════════════════════════════════
# 程式觸發的條件與結果收尾（§2.1(5)）
# ════════════════════════════════════════════════════════════════════
async def test_nonterminal_program_result_goes_back_to_model_once(monkeypatch, api):
    """非終結結果（無缺欄清單的 `INVALID_INPUT`）⇒ ⛔ 撤回：工具結果回填、再叫一次模型，模型的
    下一個輸出走正常路徑；本回合不再觸發（violation `write_draft_program_confirm_nonterminal`）。"""
    # 第 3 步 A6：有帳單編號的延期卡在開關 on 時會先以 viewer 單筆讀帳單並重算到期日（表單宣告預檢）；本條原斷言驗的是現行路徑 ⇒ 照舊在 `AGENT_WRITE_LIFECYCLE=off` 下驗。
    monkeypatch.setenv("AGENT_WRITE_LIFECYCLE", "off")
    state: dict = {}
    res, reg, provider, _ = await _turn(_pm(), "帳單 709744 延 7 天", state, [
        _out(),
        _out("請問原本的到期日是哪一天？", kind="ask", ask_target="date"),
    ], intents=[_intent("bill_due_extend", bill_id="709744", days="7")])
    (args, first), = reg.confirm_calls()
    assert json.loads(args["payload"]) == {"action": "bill_due_extend", "bill_id": 709744, "days": 7}
    assert (first.ok, first.error, first.data) == (False, "INVALID_INPUT", None)   # 前提：非終結
    assert "write_draft_program_confirm_nonterminal" in res.trace.violations
    assert len(provider.calls) == 2 and len(_program_records(res)) == 1
    assert len(provider.intent_calls) == 1                                         # 意圖只問一次
    assert res.answer == "請問原本的到期日是哪一天？"


async def test_no_trigger_when_remaining_deadline_below_six_seconds(api):
    """剩餘期限 < 6 秒 ⇒ 不觸發、保留模型原輸出（正對照：期限 6 秒時同一續答會觸發）。
    以整句填入驅動（不依賴意圖呼叫是否來得及）。"""
    ident = _pm()

    def _state():
        return _seed(ident, "repair_create", {"estate_name": STUDENT_ESTATE},
                     users=[STUDENT_ESTATE], asked=["description"])

    res, reg, *_ = await _turn(ident, "冷氣不冷", _state(), [_out()], budget=Budget(deadline_s=5.9))
    assert "write_draft_answer_filled" in res.trace.violations          # 前提：真的接收了值
    assert reg.confirm_calls() == [] and res.answer == MODEL_TEXT
    res_ok, reg_ok, *_ = await _turn(ident, "冷氣不冷", _state(), [_out()],
                                     budget=Budget(deadline_s=6.0))
    assert len(reg_ok.confirm_calls()) == 1 and res_ok.outcome["state"] == "confirm_pending"


async def test_sensitive_handoff_takes_priority_over_trigger(api):
    """敏感轉人（`sensitive_no_grounding`）⇒ 不觸發（轉人優先）。"""
    state: dict = {}
    res, reg, *_ = await _turn(_pm(), "修繕費用怎麼算？順便幫我報修", state, [
        _out("", kind="handoff", fact_class="pricing", handoff_reason="sensitive_no_grounding")],
        intents=[_intent("repair_create")])
    assert reg.confirm_calls() == [] and res.kind == "handoff"


async def test_write_not_supported_exit_clears_draft(api, monkeypatch):
    """接真 JGB（`use_mock=False`）時新動作不支援 ⇒ 既有固定句出口、草稿清掉（⛔ 留 Email）。"""
    monkeypatch.setattr(api, "use_mock", False, raising=False)
    state: dict = {}
    res, reg, *_ = await _turn(_pm(), "幫我建合約，承租人信箱 w1-test@example.com", state, [_out()],
                               intents=[_intent("contract_create", to_user_email="w1-test@example.com")])
    assert res.answer == C.WRITE_NOT_SUPPORTED_TEXT
    assert "jgb2_stats_not_supported_exit" in res.trace.violations
    assert _draft(state) is None


# ════════════════════════════════════════════════════════════════════
# 凍結腳本 R／D／T 的單元層重演（意圖替身照 `w1/probe` 的 gpt-oss 實測表現：起手句判得出動作、
# 只回物件名或只回描述的短答判 none、D2／D3 帶欄位；實測仍由主會話在評估容器做）
# ════════════════════════════════════════════════════════════════════
async def test_script_r_reaches_card_even_when_short_answers_are_judged_none(api):
    ident = _pm()
    state: dict = {}
    r1, *_ = await _turn(ident, "能幫我新增一張修繕單嗎", state, [_out()],
                         intents=[_intent("repair_create")])
    assert "confirm_missing_fields_ask" in r1.trace.violations
    r2, *_ = await _turn(ident, STUDENT_ESTATE, state, [_out()], intents=[_intent("none")])
    assert r2.answer == ASK_TEXT.format(labels="問題描述") and "物件" not in r2.answer
    r3, *_ = await _turn(ident, "冷氣不冷", state, [_out()], intents=[_intent("none")])
    assert r3.outcome["state"] == "confirm_pending", r3.answer
    assert f"・物件：{STUDENT_ESTATE}" in r3.answer and "・問題描述：冷氣不冷" in r3.answer


async def test_script_d_reaches_card_for_bill_709744(api):
    ident = _pm()
    state: dict = {}
    await _turn(ident, "我想把一張帳單延後繳", state, [_out()], intents=[_intent("bill_due_extend")])
    d2, *_ = await _turn(ident, SCRIPT_D2, state, [_out()], intents=[
        _intent("bill_due_extend", estate_name=KEELUNG_ESTATE, period="11月那期")])
    assert d2.answer == ASK_TEXT.format(labels="延後天數")
    d3, *_ = await _turn(ident, "延 7 天", state, [_out()],
                         intents=[_intent("bill_due_extend", days="7")])
    assert d3.outcome["state"] == "confirm_pending", d3.answer
    assert "・帳單編號：709744" in d3.answer and "・延後天數：7 天" in d3.answer


async def test_script_t_detour_does_not_pollute_the_draft(api):
    ident = _pm()
    state: dict = {}
    await _turn(ident, "能幫我新增一張修繕單嗎", state, [_out()], intents=[_intent("repair_create")])
    t2, reg2, *_ = await _turn(ident, "租金可以設定自動扣款嗎", state, [_out("可以，在合約的收款設定裡開啟。")],
                               intents=[_intent("none")])
    assert t2.answer == "可以，在合約的收款設定裡開啟。"
    assert reg2.confirm_calls() == [] and "confirm_missing_fields_ask" not in t2.trace.violations
    t3, reg3, *_ = await _turn(ident, STUDENT_ESTATE, state, [_out()], intents=[_intent("none")])
    assert t3.answer == ASK_TEXT.format(labels="問題描述")
    assert t3.outcome["state"] != "confirm_pending"
    assert _draft(state)["fields"] == {"estate_name": STUDENT_ESTATE}


# ════════════════════════════════════════════════════════════════════
# W1c 程式優先（計畫 §9.1／§9.7；清單 r9 #8 W1c 條目）
# ════════════════════════════════════════════════════════════════════
def _main_spy(events: list, response):
    """主模型腳本的一步：記下「主模型在這時被呼叫」與當下送出的 messages 裡有沒有程式觸發的回填。"""
    def _step(kwargs):
        events.append(("main", any(str(m.get("tool_call_id", "")).startswith(
            runtime_mod.WRITE_DRAFT_PROGRAM_ID_PREFIX) for m in kwargs["messages"])))
        return response
    return _step


def test_w1c_intent_system_prompt_ends_with_the_approved_none_sentence():
    """#6／W1c §9.1-3：意圖說明末尾逐字補上業主核可句（同第 0 步探測 `probe3_w1c.py` 的 `ADD`，
    以 "\\n" 接在原說明之後）；期望字串由測試寫死（⛔ 引用被測常數）。"""
    add = ("使用者只說名詞或名詞片語、在問功能怎麼用、或在查資料 ⇒ none；只有使用者明確要系統替他"
           "建立或變更一筆資料，或正在回答進行中的建立所需的資料時，才填動作。")
    assert WF.WRITE_INTENT_SYSTEM_PROMPT.endswith(WF.write_intent_description() + "\n" + add)
    assert runtime_mod.WRITE_DRAFT_PROGRAM_FIRST_WAIT_S == 3.0


async def test_w1c_program_first_terminal_exit_never_calls_the_main_model(api):
    """W1c：程式優先且程式路徑終結（缺欄程式追問）⇒ 主模型未被呼叫（假模型 script 未消耗）、
    `llm_calls=0`；意圖呼叫照常收尾計量。正對照：同一句在 rules 缺（後備路徑）時主模型被呼叫一次。"""
    state: dict = {}
    res, reg, provider, _ = await _turn(_pm(), "能幫我新增一張修繕單嗎", state, [_out()],
                                        intents=[_intent("repair_create", pt=11, ct=4)],
                                        program_first=True)
    assert res.answer == ASK_TEXT.format(labels="物件、問題描述")
    assert provider.calls == [] and len(provider.main.script) == 1          # script 未消耗
    assert res.trace.llm_calls == 0
    assert "write_draft_program_confirm" in res.trace.violations
    assert "confirm_missing_fields_ask" in res.trace.violations
    assert "write_intent_call" in res.trace.violations
    assert (res.trace.prompt_tokens, res.trace.completion_tokens) == (11, 4)
    assert _draft(state)["asked"] == ["estate_name", "description"]
    # 正對照（後備）：rules 缺 ⇒ 主模型先被呼叫，輸出後觸發點才觸發。
    res0, _r0, p0, _ = await _turn(_pm(), "能幫我新增一張修繕單嗎", {}, [_out()],
                                   intents=[_intent("repair_create")])
    assert len(p0.calls) == 1 and res0.answer == ASK_TEXT.format(labels="物件、問題描述")


async def test_w1c_program_first_card_exit_never_calls_the_main_model(api):
    """W1c：程式優先出卡（終結）⇒ 主模型未被呼叫，`confirm_pending`。"""
    state: dict = {}
    res, reg, provider, pool = await _turn(
        _pm(), f"{STUDENT_ESTATE} 冷氣不冷", state, [],
        intents=[_intent("repair_create", estate_name=STUDENT_ESTATE, description="冷氣不冷")],
        program_first=True)
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert provider.calls == [] and res.trace.llm_calls == 0
    assert len(_program_records(res)) == 1
    pool.insert.assert_called_once()


async def test_w1c_f2_statement_answer_with_intent_none_goes_program_first(api):
    """W1c F2：上回合 `asked=[description]`、意圖回 none、非問句 ⇒ 入口條件與輸出後觸發點同一條件
    （`filled`）⇒ 走程式優先且主模型未被呼叫，出卡。"""
    ident = _pm()
    state = _seed(ident, "repair_create", {"estate_name": STUDENT_ESTATE}, users=[STUDENT_ESTATE],
                  asked=["description"])
    res, reg, provider, _ = await _turn(ident, "冷氣不冷", state, [], intents=[_intent("none")],
                                        program_first=True)
    assert "write_draft_answer_filled" in res.trace.violations
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert "・問題描述：冷氣不冷" in res.answer and f"・物件：{STUDENT_ESTATE}" in res.answer
    assert provider.calls == [] and len(provider.intent_calls) == 1


async def test_w1c_intent_wait_timeout_calls_main_model_and_after_output_trigger_still_works(
        api, monkeypatch):
    """W1c F1：意圖等待逾時（以縮短等待上限模擬 >3 秒）⇒ 記 `write_draft_program_first_wait_timeout`、
    ⛔ 記 `write_intent_call_failed`、照常呼叫主模型；輸出後觸發點取得意圖並觸發程式追問。
    （W1c §9.11-3 起無草稿回合的上限是 `WRITE_DRAFT_PROGRAM_FIRST_WAIT_NO_DRAFT_S`，本回合無草稿
    ⇒ 兩個上限一併縮短；斷言不變。）"""
    monkeypatch.setattr(runtime_mod, "WRITE_DRAFT_PROGRAM_FIRST_WAIT_S", 0.05)
    monkeypatch.setattr(runtime_mod, "WRITE_DRAFT_PROGRAM_FIRST_WAIT_NO_DRAFT_S", 0.05)

    async def _late(kwargs):
        await asyncio.sleep(0.3)
        return _intent("repair_create")

    events: list = []
    state: dict = {}
    res, reg, provider, _ = await _turn(_pm(), "能幫我新增一張修繕單嗎", state,
                                        [_main_spy(events, _out())], intents=[_late],
                                        program_first=True)
    assert events == [("main", False)]                       # 主模型先被叫、當下沒有程式回填
    assert "write_draft_program_first_wait_timeout" in res.trace.violations
    assert "write_intent_call_failed" not in res.trace.violations
    assert "write_intent_call" in res.trace.violations        # 後備取用後照常收尾計量
    assert res.answer == ASK_TEXT.format(labels="物件、問題描述")
    assert len(_program_records(res)) == 1 and len(provider.intent_calls) == 1


@pytest.mark.parametrize("message,intent,expect_filled", [
    ("幫我延後帳單七天", "bill_due_extend", False),             # 1a：另一動作 ⇒ 不整句填入
    ("冷氣不冷", "none", True),                                  # 正對照：同條件的續答由後備填入
])
async def test_w1c_f1_late_intent_with_asked_description_leaves_fill_to_after_output(
        api, monkeypatch, message, intent, expect_filled):
    """W1c F1：意圖延遲 >3 秒、`asked=[description]`、非問句 ⇒ 主模型呼叫前**沒有**整句填入
    （程式優先未取用意圖、未填、未觸發）；輸出後觸發點取得意圖後套用 1a（另一動作 ⇒ 不填、換草稿
    並程式追問其缺欄）；正對照：意圖 none 的續答由輸出後觸發點填入並出卡。"""
    monkeypatch.setattr(runtime_mod, "WRITE_DRAFT_PROGRAM_FIRST_WAIT_S", 0.05)
    ident = _pm()
    state = _seed(ident, "repair_create", {"estate_name": STUDENT_ESTATE}, users=[STUDENT_ESTATE],
                  asked=["description"])
    events: list = []
    real_fill = AgentRuntime._write_draft_fill_answer

    async def _fill_spy(self, acc, *a, **kw):
        await real_fill(self, acc, *a, **kw)
        events.append(("fill", WF.V_ANSWER_FILLED in acc.violations))

    async def _late(kwargs):
        await asyncio.sleep(0.3)
        return _intent(intent)

    monkeypatch.setattr(AgentRuntime, "_write_draft_fill_answer", _fill_spy)
    res, reg, provider, _ = await _turn(ident, message, state, [_main_spy(events, _out())],
                                        intents=[_late], program_first=True)
    assert events[0] == ("main", False)                      # 主模型呼叫前：沒有任何填入
    assert "write_draft_program_first_wait_timeout" in res.trace.violations
    assert "write_intent_call_failed" not in res.trace.violations
    assert (WF.V_ANSWER_FILLED in res.trace.violations) is expect_filled
    if expect_filled:
        assert events == [("main", False), ("fill", True)]
        assert res.outcome["state"] == "confirm_pending", res.answer
        assert "・問題描述：冷氣不冷" in res.answer
    else:
        assert events == [("main", False)]                   # 1a：另一動作 ⇒ 整句填入根本不跑
        draft = _draft(state)
        assert draft["action"] == "bill_due_extend" and "description" not in draft["fields"]
        assert res.answer == ASK_TEXT.format(labels="物件、期別、延後天數")


async def test_w1c_program_first_nonterminal_result_calls_main_model_once_with_the_result(monkeypatch, api):
    """W1c：程式優先遇非終結結果（無缺欄清單的 `INVALID_INPUT`）⇒ 主模型被呼叫一次、送出的
    messages 帶程式那一次 `confirm.request` 的回填結果；本回合不再觸發（上限 1 次）。"""
    # 第 3 步 A6：有帳單編號的延期卡在開關 on 時會先以 viewer 單筆讀帳單並重算到期日（表單宣告預檢）；本條原斷言驗的是現行路徑 ⇒ 照舊在 `AGENT_WRITE_LIFECYCLE=off` 下驗。
    monkeypatch.setenv("AGENT_WRITE_LIFECYCLE", "off")
    events: list = []
    res, reg, provider, _ = await _turn(_pm(), "帳單 709744 延 7 天", {}, [
        _main_spy(events, _out("請問原本的到期日是哪一天？", kind="ask", ask_target="date"))],
        intents=[_intent("bill_due_extend", bill_id="709744", days="7")], program_first=True)
    (args, first), = reg.confirm_calls()
    assert (first.ok, first.error, first.data) == (False, "INVALID_INPUT", None)   # 前提：非終結
    assert events == [("main", True)]                        # 主模型一次、帶回填
    tool_msgs = [m for m in provider.calls[0]["messages"]
                 if str(m.get("tool_call_id", "")).startswith(runtime_mod.WRITE_DRAFT_PROGRAM_ID_PREFIX)]
    assert len(tool_msgs) == 1 and tool_msgs[0]["role"] == "tool"
    assert "write_draft_program_confirm_nonterminal" in res.trace.violations
    assert res.trace.violations.count("write_draft_program_confirm") == 1
    assert len(_program_records(res)) == 1 and res.trace.llm_calls == 1
    assert res.answer == "請問原本的到期日是哪一天？"


async def test_w1c_sensitive_question_does_not_go_program_first(api):
    """W1c §9.1-2：使用者當句命中既有問句側敏感樣式 ⇒ 不走程式優先（主模型先被呼叫；輸出後觸發點
    仍可用）。正對照：不敏感的同類句走程式優先（主模型未被呼叫）。"""
    sensitive = "月費多少？順便幫我報修"
    assert question_sensitive(sensitive, VerifierRules.load(RULES_PATH)) is True     # 前提
    events: list = []
    res, reg, provider, _ = await _turn(_pm(), sensitive, {}, [_main_spy(events, _out())],
                                        intents=[_intent("repair_create")], program_first=True)
    assert events == [("main", False)]
    assert "write_draft_program_first_wait_timeout" not in res.trace.violations
    assert res.answer == ASK_TEXT.format(labels="物件、問題描述")              # 後備照常觸發
    # 正對照：不敏感 ⇒ 程式優先。
    plain = "順便幫我報修"
    assert question_sensitive(plain, VerifierRules.load(RULES_PATH)) is False
    res2, _r2, p2, _ = await _turn(_pm(), plain, {}, [_out()], intents=[_intent("repair_create")],
                                   program_first=True)
    assert p2.calls == [] and res2.answer == ASK_TEXT.format(labels="物件、問題描述")


async def test_w1c_f3_verifier_without_rules_does_not_go_program_first(api):
    """W1c F3：`verifier.rules` 缺（`getattr(…, "rules", None) is None`）⇒ 不走程式優先、⛔ 等意圖；
    主模型先被呼叫（正對照：有 rules 時同一句主模型未被呼叫）。"""
    assert getattr(FakeVerifier(), "rules", None) is None                       # 前提
    events: list = []
    res, reg, provider, _ = await _turn(_pm(), "能幫我新增一張修繕單嗎", {},
                                        [_main_spy(events, _out())], intents=[_intent("repair_create")])
    assert events == [("main", False)]
    assert len(_program_records(res)) == 1                                        # 後備觸發
    res2, _r2, p2, _ = await _turn(_pm(), "能幫我新增一張修繕單嗎", {}, [_out()],
                                   intents=[_intent("repair_create")], program_first=True)
    assert p2.calls == []


async def test_w1c_program_first_and_after_output_share_one_decision_function(api, monkeypatch):
    """W1c：`_write_draft_program_first` 與 `_write_draft_after_output` 共用同一個判斷函式
    `_write_draft_decide`——結構上兩者都只經它取用意圖／填入／判觸發（⛔ 各自一份）；行為上兩條路
    各呼叫它一次。"""
    for fn in (AgentRuntime._write_draft_program_first, AgentRuntime._write_draft_after_output):
        src = inspect.getsource(fn)
        assert "self._write_draft_decide(" in src
        for private in ("_await_write_intent", "_write_draft_merge_intent", "_write_draft_fill_answer",
                        "_write_draft_program_message", "WRITE_DRAFT_PROGRAM_MIN_REMAINING_S",
                        "document_writable_action", "SELECT_SCOPE_KEY", "_document_carry_of"):
            assert private not in src, (fn.__name__, private)
    decide_src = inspect.getsource(AgentRuntime._write_draft_decide)
    assert "document is not None or document_writable_action(document) is not None" in decide_src
    calls: list = []
    real = AgentRuntime._write_draft_decide

    async def _spy(self, acc, *a, **kw):
        caller = inspect.stack()[1].function
        calls.append(caller)
        return await real(self, acc, *a, **kw)

    monkeypatch.setattr(AgentRuntime, "_write_draft_decide", _spy)
    await _turn(_pm(), "能幫我新增一張修繕單嗎", {}, [_out()], intents=[_intent("repair_create")],
                program_first=True)
    assert calls == ["_write_draft_program_first"]
    calls.clear()
    await _turn(_pm(), "能幫我新增一張修繕單嗎", {}, [_out()], intents=[_intent("repair_create")])
    assert calls == ["_write_draft_after_output"]


async def test_w1c_question_frozen_turn_does_not_go_program_first(api):
    """W1c（沿用 §8.5-3）：程式追問後的問句 ⇒ 凍結，程式優先不走、主模型照常回答、草稿保留。"""
    ident = _pm()
    state = _seed(ident, "repair_create", {"estate_name": STUDENT_ESTATE}, users=[STUDENT_ESTATE],
                  asked=["description"])
    res, reg, provider, _ = await _turn(ident, "冷氣不冷嗎", state, [_out("可能是濾網髒了。")],
                                        intents=[_intent("repair_create", description="冷氣不冷")],
                                        program_first=True)
    assert res.answer == "可能是濾網髒了。" and len(provider.calls) == 1
    assert reg.confirm_calls() == [] and _draft(state)["fields"] == {"estate_name": STUDENT_ESTATE}


async def test_w1c_off_switch_never_goes_program_first(api, monkeypatch):
    """#6 × W1c：`AGENT_WRITE_DRAFT=off` ⇒ 有 rules 也不發意圖呼叫、不走程式優先、主模型原輸出照出。"""
    monkeypatch.setenv("AGENT_WRITE_DRAFT", "off")
    state: dict = {}
    res, reg, provider, _ = await _turn(_pm(), "能幫我新增一張修繕單嗎", state, [_out()],
                                        intents=[_intent("repair_create")], program_first=True)
    assert provider.intent_calls == [] and len(provider.calls) == 1
    assert res.answer == MODEL_TEXT and WRITE_DRAFT_KEY not in state["agent"]


async def test_w1c_scripts_r_d_t_run_program_first_without_the_main_model(api):
    """W1c：凍結腳本 R／D／T 在程式優先下的單元層重演——寫入回合主模型一次都不被呼叫
    （script 空：多叫一次即斷言失敗）；只有 T 第二句（程式追問後的問句 ⇒ 凍結）交主模型回答。"""
    ident = _pm()
    state: dict = {}
    r1, *_ = await _turn(ident, "能幫我新增一張修繕單嗎", state, [], intents=[_intent("repair_create")],
                         program_first=True)
    assert r1.answer == ASK_TEXT.format(labels="物件、問題描述")
    r2, *_ = await _turn(ident, STUDENT_ESTATE, state, [], intents=[_intent("none")], program_first=True)
    assert r2.answer == ASK_TEXT.format(labels="問題描述") and "物件" not in r2.answer
    r3, *_ = await _turn(ident, "冷氣不冷", state, [], intents=[_intent("none")], program_first=True)
    assert r3.outcome["state"] == "confirm_pending", r3.answer
    assert f"・物件：{STUDENT_ESTATE}" in r3.answer and "・問題描述：冷氣不冷" in r3.answer

    state_d: dict = {}
    await _turn(ident, "我想把一張帳單延後繳", state_d, [], intents=[_intent("bill_due_extend")],
                program_first=True)
    d2, *_ = await _turn(ident, SCRIPT_D2, state_d, [], intents=[
        _intent("bill_due_extend", estate_name=KEELUNG_ESTATE, period="11月那期")], program_first=True)
    assert d2.answer == ASK_TEXT.format(labels="延後天數")
    d3, *_ = await _turn(ident, "延 7 天", state_d, [], intents=[_intent("bill_due_extend", days="7")],
                         program_first=True)
    assert d3.outcome["state"] == "confirm_pending", d3.answer
    assert "・帳單編號：709744" in d3.answer and "・延後天數：7 天" in d3.answer

    state_t: dict = {}
    await _turn(ident, "能幫我新增一張修繕單嗎", state_t, [], intents=[_intent("repair_create")],
                program_first=True)
    t2, reg2, p2, _ = await _turn(ident, "租金可以設定自動扣款嗎", state_t,
                                  [_out("可以，在合約的收款設定裡開啟。")], intents=[_intent("none")],
                                  program_first=True)
    assert t2.answer == "可以，在合約的收款設定裡開啟。" and len(p2.calls) == 1
    assert reg2.confirm_calls() == []
    t3, *_ = await _turn(ident, STUDENT_ESTATE, state_t, [], intents=[_intent("none")], program_first=True)
    assert t3.answer == ASK_TEXT.format(labels="問題描述")
    assert _draft(state_t)["fields"] == {"estate_name": STUDENT_ESTATE}


# ════════════════════════════════════════════════════════════════════
# W1c 修正（計畫 §9.11；根因見 §9.10）
# ════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("value,kind,expected", [
    ("7 天", "int", 7),
    ("延 7 天", "int", 7),
    ("７天", "int", 7),                     # 全形先 NFKC
    ("12,000元", "int", 12000),             # 千分位照 `_THOUSANDS_RE`
    ("7", "int", 7),                        # 純數字照舊
    ("7 到 10 天", "int", None),            # 多個 token ⇒ 不合
    ("7天7夜", "int", None),
    ("七天", "int", None),                  # 零個 token（國字數字不收）⇒ 不合
    ("", "int", None),
    ("7.5 天", "int", None),                # 一個 token 但 int 欄位型別不合
    ("7.5 坪", "number", 7.5),
])
def test_w1c_fix_number_token_takes_exactly_one_number(value, kind, expected):
    """§9.11-1：`int`／`number` 意圖值含恰好一個數字 token ⇒ 取該數字；零個或多個 ⇒ 不合。"""
    assert WF.parse_number_token(value, kind) == expected


@pytest.mark.parametrize("message,days_value,expect_card", [
    ("延 7 天", "7 天", True),               # §9.10 根因 1 的原樣（意圖照抄原話帶單位）
    ("延 7 天", "延 7 天", True),
    ("延 7 到 10 天", "7 到 10 天", False),   # 兩個數字 ⇒ 不進草稿
])
async def test_w1c_fix_days_with_unit_enters_draft_as_seven(api, message, days_value, expect_card):
    """§9.11-1：延期繳費草稿已有物件＋期別、上回合程式追問延後天數；意圖回 `days="7 天"`／
    `"延 7 天"` ⇒ 草稿與程式 `confirm.request` 的 days＝7、出卡 709744；`"7 到 10 天"` ⇒ 不進草稿
    （值閘 violation），不出卡。"""
    ident = _pm()
    state = _seed(ident, "bill_due_extend", {"estate_name": KEELUNG_ESTATE, "period": "11月那期"},
                  users=["我想把一張帳單延後繳", SCRIPT_D2], asked=["days"])
    res, reg, provider, _ = await _turn(
        ident, message, state, [] if expect_card else [_out()],
        intents=[_intent("bill_due_extend", days=days_value)], program_first=True)
    if expect_card:
        assert res.outcome["state"] == "confirm_pending", res.answer
        assert "・帳單編號：709744" in res.answer and "・延後天數：7 天" in res.answer
        (args, _r), = reg.confirm_calls()
        assert json.loads(args["payload"])["days"] == 7
        assert "write_intent_value_not_in_user_words" not in res.trace.violations
        assert provider.calls == []
    else:
        assert res.outcome["state"] != "confirm_pending"
        assert "write_intent_value_not_in_user_words" in res.trace.violations
        assert "days" not in _draft(state)["fields"]
        assert reg.confirm_calls() == []


@pytest.mark.parametrize("program_first", [True, False])
async def test_w1c_fix_split_name_and_description_keeps_system_name_and_drops_description(
        api, program_first):
    """§9.11-2（§9.10 根因 2 的 R2 情境）：程式追問 [物件, 問題描述] 後使用者回物件全名、前置查詢
    唯一命中；意圖呼叫拆成物件「學生獨立套房」＋描述「可租補」⇒ 物件為系統名稱、描述不進草稿、
    記 `write_intent_value_overlaps_name`、程式追問問題描述（不提早出卡）。程式優先與後備兩條路同。"""
    ident = _pm()
    state = _seed(ident, "repair_create", {}, users=["能幫我新增一張修繕單嗎"],
                  asked=["estate_name", "description"])
    res, reg, provider, _ = await _turn(
        ident, STUDENT_ESTATE, state, [] if program_first else [_out()],
        intents=[_intent("repair_create", estate_name="學生獨立套房", description="可租補")],
        program_first=program_first)
    assert "write_draft_name_caught" in res.trace.violations                    # 前提：唯一命中
    assert "write_intent_value_overlaps_name" in res.trace.violations
    assert _draft(state)["fields"] == {"estate_name": STUDENT_ESTATE}
    assert res.answer == ASK_TEXT.format(labels="問題描述")
    assert res.outcome["state"] != "confirm_pending"
    (args, _r), = reg.confirm_calls()
    payload = json.loads(args["payload"])
    assert payload["estate_name"] == STUDENT_ESTATE and "description" not in payload
    # 正對照：無草稿（不跑名稱補值、沒有命中名稱）⇒ 規則不套用，意圖的拆分照舊進草稿。
    state0: dict = {}
    res0, *_ = await _turn(ident, STUDENT_ESTATE, state0, [] if program_first else [_out()],
                           intents=[_intent("repair_create", estate_name="學生獨立套房",
                                            description="可租補")],
                           program_first=program_first)
    assert "write_intent_value_overlaps_name" not in res0.trace.violations
    assert "・問題描述：可租補" in res0.answer


async def test_w1c_fix_value_inside_the_name_segment_is_dropped_and_other_values_kept(api):
    """§9.11-2：意圖文字欄位值是「當句被判為物件名稱那一段」（前置查詢關鍵字）的子字串、但不是系統
    名稱的子字串 ⇒ 同樣丟棄；正對照：不在名稱內的描述（使用者前一句講過、過值閘）照常進草稿並出卡。"""
    ident = _pm()
    override = {"A棟頂樓": _unique_estate_hit()}
    assert "頂樓" not in STUDENT_ESTATE                                          # 前提：只命中那一段
    state = _seed(ident, "repair_create", {}, users=["能幫我新增一張修繕單嗎"],
                  asked=["estate_name", "description"])
    res, reg, provider, _ = await _turn(
        ident, "A棟頂樓", state, [],
        intents=[_intent("repair_create", estate_name="A棟", description="頂樓")],
        reg=_Reg(_pool(), estates_override=override), program_first=True)
    assert any(r[0] == "jgb2.query.estates" for r in reg.results)              # 前提：替身真的被查到
    assert "write_intent_value_overlaps_name" in res.trace.violations
    assert _draft(state)["fields"] == {"estate_name": STUDENT_ESTATE}           # 列上 title
    assert res.answer == ASK_TEXT.format(labels="問題描述")
    # 正對照：描述「冷氣不冷」不在名稱內 ⇒ 進草稿、出卡；物件仍是系統名稱。
    state2 = _seed(ident, "repair_create", {}, users=["能幫我新增一張修繕單嗎", "冷氣不冷"],
                   asked=["estate_name", "description"])
    res2, *_ = await _turn(
        ident, STUDENT_ESTATE, state2, [],
        intents=[_intent("repair_create", estate_name="學生獨立套房", description="冷氣不冷")],
        program_first=True)
    assert "write_intent_value_overlaps_name" not in res2.trace.violations
    assert res2.outcome["state"] == "confirm_pending", res2.answer
    assert f"・物件：{STUDENT_ESTATE}" in res2.answer and "・問題描述：冷氣不冷" in res2.answer


def test_w1c_fix_program_first_wait_tiers():
    """§9.11-3：有草稿 3 秒（不變）、無草稿 1 秒——期望值由測試寫死。"""
    assert runtime_mod.WRITE_DRAFT_PROGRAM_FIRST_WAIT_S == 3.0
    assert runtime_mod.WRITE_DRAFT_PROGRAM_FIRST_WAIT_NO_DRAFT_S == 1.0


async def test_w1c_fix_no_draft_turn_times_out_at_one_second_and_after_output_still_works(api):
    """§9.11-3：無草稿回合、意圖 1.4 秒才回（< 3 秒、> 1 秒）⇒ 程式優先逾時（記
    `write_draft_program_first_wait_timeout`、⛔ `write_intent_call_failed`）、主模型先被呼叫；
    輸出後觸發點取得意圖並程式追問。（真實等待，⛔ 縮短常數。）"""
    async def _late(kwargs):
        await asyncio.sleep(1.4)
        return _intent("repair_create")

    events: list = []
    res, reg, provider, _ = await _turn(_pm(), "能幫我新增一張修繕單嗎", {},
                                        [_main_spy(events, _out())], intents=[_late],
                                        program_first=True)
    assert events == [("main", False)]
    assert "write_draft_program_first_wait_timeout" in res.trace.violations
    assert "write_intent_call_failed" not in res.trace.violations
    assert "write_intent_call" in res.trace.violations
    assert res.answer == ASK_TEXT.format(labels="物件、問題描述")
    assert len(_program_records(res)) == 1


async def test_w1c_fix_draft_turn_still_waits_three_seconds(api):
    """§9.11-3：回合開始時已有草稿、意圖同樣 1.4 秒才回 ⇒ 仍在 3 秒上限內 ⇒ 不逾時、走程式優先，
    主模型未被呼叫（script 空）並出卡。（與上一條同延遲，差別只有回合開始時有無草稿。）"""
    async def _late(kwargs):
        await asyncio.sleep(1.4)
        return _intent("repair_create", description="冷氣不冷")

    ident = _pm()
    state = _seed(ident, "repair_create", {"estate_name": STUDENT_ESTATE}, users=[STUDENT_ESTATE],
                  asked=["description"])
    res, reg, provider, _ = await _turn(ident, "冷氣不冷", state, [], intents=[_late],
                                        program_first=True)
    assert "write_draft_program_first_wait_timeout" not in res.trace.violations
    assert provider.calls == [] and res.trace.llm_calls == 0
    assert res.outcome["state"] == "confirm_pending", res.answer
    assert "・問題描述：冷氣不冷" in res.answer
