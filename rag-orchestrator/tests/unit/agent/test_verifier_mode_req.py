"""unit：`AGENT_VERIFIER_MODE`（W6-b3／DSP-040 正式參數）。

覆蓋（Plan `inputs/plan-walkthrough-fixes-batch3-20260909.md` §2 驗收）：
- 模式解析三態＋相容舊旗 `AGENT_VERIFIER_OBSERVE_ONLY`＋值域外字（fail-closed 回 enforce）；
- 兩個模組的封閉集合對齊（`health.VERIFIER_MODES` vs `verifier.VERIFIER_MODES`）；
- 健檢：新鍵 `verifier_mode`、**保留鍵** `verifier_observe_only`（煙囪 §20-5 有斷言）；
- 守衛：`observe_only`＋非 mock ⇒ 啟動 raise；`grounding_observe`＋非 mock ⇒
  `premise.red_flags` 記紅（⛔ 不阻起）；
- 觀察類／照擋類**逐類真值表**（以拒因＋子成因界定，⛔ 不是整個 `SCHEMA` 一起）；
- 短路證明：同時違反引用類與 `forbid_terms` 的一案在 `grounding_observe` 下 `ok=False`
  （security-reviewer r1 F1：外層翻判定會讓機敏類根本沒跑）；
- 多 ref 聚合：引用類維持「至少一個 ref 完整通過」、極性類任一命中即擋；
- `self_test` 在**任何**模式下皆綠（釘死 enforce，security r1 F2）；
- 觀察判定（`ok=True` 且 `observed` 非空）⛔ 不遞增 `counters.rewrites`。

離線：不接真 DB／真 LLM／真 JGB API。
"""
import json
from pathlib import Path

import pytest

from services.agent import health as health_mod
from services.agent.output_schema import AgentOutput, VerifierRules
from services.agent.provenance_units import resolve_refs
from services.agent.tools.registry import ToolResult
from services.agent.verifier import (
    DEFAULT_VERIFIER_MODE,
    VERIFIER_MODES,
    OutputVerifier,
)

pytestmark = pytest.mark.unit

_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "agent"
_RULES_PATH = Path(__file__).resolve().parents[3] / "config" / "agent_verifier_rules.json"

#: 本檔用的固定 nonce（形狀須合 `provenance_units._REF_RE`：8–64 位英數）。
NONCE = "MODE000000000000"
#: 覆蓋充足、長度足夠、兩側皆無否定詞的「乾淨」來源片段與對應句子。
CLEAN_UNIT = "系統支援租客資料匯入功能，格式為 Excel。"
CLEAN_SENTENCE = "系統支援租客資料匯入功能。"


def _marker(tool_call_id: str, source: str, index: int = 0, nonce: str = NONCE) -> str:
    return f"[{nonce}:{tool_call_id}:{source}§{index}]"


def _tool_results(*provenance: dict, tool_call_id: str = "t1") -> dict:
    return {
        tool_call_id: ToolResult.model_validate(
            {"ok": True, "provenance": list(provenance), "text_for_model": ""}
        )
    }


def _prov(text: str, *, source: str = "kb:1000", citable: bool = True) -> dict:
    return {"source": source, "text": text, "citable": citable}


def _out(**overrides) -> dict:
    base = {
        "kind": "answer",
        "sentences": [],
        "fact_class": "feature",
        "handoff_reason": None,
    }
    base.update(overrides)
    return base


def _fact(text: str, refs: list) -> dict:
    return {"text": text, "kind": "fact", "refs": refs}


def _verify(verifier: OutputVerifier, out_dict: dict, tool_results: dict, *, handoff=None):
    """與產線同一個順序：`resolve_refs` → `verify`。
    ⛔ 不在本檔另寫一套解析——那樣測到的是本檔的解析，不是系統的解析。"""
    out = AgentOutput.model_validate(out_dict)
    resolved, resolve_errors = resolve_refs(out, tool_results, NONCE)
    return verifier.verify(
        out, tool_results, "測試問題", handoff,
        resolved=resolved, resolve_errors=resolve_errors)


@pytest.fixture(scope="module")
def rules() -> VerifierRules:
    return VerifierRules.load(_RULES_PATH)


def _verifier(rules: VerifierRules, mode: str) -> OutputVerifier:
    return OutputVerifier(rules, mode=mode)


# ============================================================ 1. 模式解析


def _clear_flags(monkeypatch):
    monkeypatch.delenv(health_mod.AGENT_VERIFIER_MODE_ENV, raising=False)
    monkeypatch.delenv(health_mod.AGENT_VERIFIER_OBSERVE_ONLY_ENV, raising=False)


def test_verifier_mode_defaults_to_enforce(monkeypatch):
    _clear_flags(monkeypatch)
    assert health_mod.verifier_mode() == "enforce"


@pytest.mark.parametrize("mode", ["enforce", "grounding_observe", "observe_only"])
def test_verifier_mode_parses_each_value(monkeypatch, mode):
    _clear_flags(monkeypatch)
    monkeypatch.setenv(health_mod.AGENT_VERIFIER_MODE_ENV, mode)
    assert health_mod.verifier_mode() == mode
    # 大小寫與前後空白不影響（與其他旗同慣例）。
    monkeypatch.setenv(health_mod.AGENT_VERIFIER_MODE_ENV, f"  {mode.upper()} ")
    assert health_mod.verifier_mode() == mode


@pytest.mark.parametrize("truthy", ["1", "true", "TRUE", "yes", "on"])
def test_legacy_observe_only_flag_maps_to_observe_only(monkeypatch, truthy):
    """相容一版：`AGENT_VERIFIER_OBSERVE_ONLY` truthy ⇒ `observe_only`。"""
    _clear_flags(monkeypatch)
    monkeypatch.setenv(health_mod.AGENT_VERIFIER_OBSERVE_ONLY_ENV, truthy)
    assert health_mod.verifier_mode() == "observe_only"


def test_explicit_mode_wins_over_legacy_flag(monkeypatch):
    """兩旗矛盾時以**正式參數**為準（⛔ 不是「哪個比較寬鬆就聽哪個」）。"""
    _clear_flags(monkeypatch)
    monkeypatch.setenv(health_mod.AGENT_VERIFIER_OBSERVE_ONLY_ENV, "true")
    monkeypatch.setenv(health_mod.AGENT_VERIFIER_MODE_ENV, "enforce")
    assert health_mod.verifier_mode() == "enforce"


def test_unknown_mode_value_falls_back_to_enforce(monkeypatch):
    """打錯字 ⇒ **enforce**（fail-closed）。⛔ 不得靜默落回任何觀察模式——
    那個失敗方向是「整把尺關掉而沒有人知道」。"""
    _clear_flags(monkeypatch)
    monkeypatch.setenv(health_mod.AGENT_VERIFIER_MODE_ENV, "groundig_observe")
    assert health_mod.verifier_mode() == "enforce"
    # 正對照：打錯字**不會**讓相容旗接手放寬。
    monkeypatch.setenv(health_mod.AGENT_VERIFIER_OBSERVE_ONLY_ENV, "true")
    assert health_mod.verifier_mode() == "enforce"


def test_mode_value_sets_are_aligned_across_modules():
    """`health`（解析）與 `verifier`（執行）是同一個封閉集合的兩個用途——
    兩邊分岔＝健檢說的模式跟尺實際跑的模式不是同一個。"""
    assert tuple(health_mod.VERIFIER_MODES) == tuple(VERIFIER_MODES)
    assert health_mod.DEFAULT_VERIFIER_MODE == DEFAULT_VERIFIER_MODE == "enforce"


def test_verifier_rejects_out_of_range_mode(rules):
    """設定端 ⛔ 不容錯（容錯只在 env 解析那一層）。"""
    with pytest.raises(ValueError):
        OutputVerifier(rules, mode="observe")
    v = OutputVerifier(rules)
    with pytest.raises(ValueError):
        v.mode = "off"
    assert v.mode == "enforce"


# ============================================================ 2. 健檢輸出與守衛


class _FakeRegistry:
    def union_specs(self, *_a, **_k):
        return [{"name": "kb.get"}]

    def write_tools_enabled(self):
        return False


async def _health(monkeypatch, **env):
    """健檢的最小可跑組態：工具與 DB 探針一律綠，只量旗標與 red_flags。"""
    from services.agent import mcp_facade

    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    monkeypatch.setattr(mcp_facade, "union_specs", lambda *_a, **_k: [{"name": "kb.get"}])
    monkeypatch.setattr(mcp_facade, "mcp_sdk_available", lambda: (True, ""))
    monkeypatch.setattr(mcp_facade, "premise_stats", lambda: {})
    monkeypatch.setattr(mcp_facade, "agent_configured", lambda: False)
    monkeypatch.setattr(health_mod, "_check_kb_reachable",
                        lambda _p: _async_value((True, "ok")))
    monkeypatch.setattr(health_mod, "_check_agent_scope_ready",
                        lambda _p: _async_value((True, "ok")))
    return await health_mod.compute_agent_health(
        registry=_FakeRegistry(), get_kb_pool=None, stage="M1")


async def _async_value(value):
    return value


@pytest.mark.asyncio
async def test_health_reports_mode_and_keeps_legacy_key(monkeypatch):
    """新鍵 `verifier_mode`；**舊鍵 `verifier_observe_only` 保留**（煙囪 §20-5 斷言它）。"""
    out = await _health(monkeypatch, AGENT_VERIFIER_MODE="grounding_observe",
                        AGENT_VERIFIER_OBSERVE_ONLY=None, USE_MOCK_JGB_API="true")
    assert out["checks"]["verifier_mode"] == "grounding_observe"
    assert out["checks"]["verifier_observe_only"] is False

    out = await _health(monkeypatch, AGENT_VERIFIER_MODE=None,
                        AGENT_VERIFIER_OBSERVE_ONLY="true", USE_MOCK_JGB_API="true")
    assert out["checks"]["verifier_mode"] == "observe_only"
    assert out["checks"]["verifier_observe_only"] is True

    out = await _health(monkeypatch, AGENT_VERIFIER_MODE=None,
                        AGENT_VERIFIER_OBSERVE_ONLY=None, USE_MOCK_JGB_API="true")
    assert out["checks"]["verifier_mode"] == "enforce"
    assert out["checks"]["verifier_observe_only"] is False


@pytest.mark.asyncio
async def test_grounding_observe_on_real_api_is_a_premise_red_flag(monkeypatch):
    """F3：`grounding_observe` 是第一個能在**真 API** 上關掉引用檢查的組態 ⇒ 健檢記紅。
    ⛔ 不阻起（阻起的是 `observe_only`）。"""
    out = await _health(monkeypatch, AGENT_VERIFIER_MODE="grounding_observe",
                        AGENT_VERIFIER_OBSERVE_ONLY=None, USE_MOCK_JGB_API="false")
    assert health_mod.VERIFIER_GROUNDING_OBSERVE_ON_REAL_API_FLAG in out["checks"]["premise"]["red_flags"]
    assert out["status"] == "red"

    # 正對照①：同一個模式配替身 ⇒ 沒有這支旗、狀態綠。
    out = await _health(monkeypatch, AGENT_VERIFIER_MODE="grounding_observe",
                        AGENT_VERIFIER_OBSERVE_ONLY=None, USE_MOCK_JGB_API="true")
    assert health_mod.VERIFIER_GROUNDING_OBSERVE_ON_REAL_API_FLAG not in out["checks"]["premise"]["red_flags"]
    assert out["status"] == "ok"

    # 正對照②：真 API 但 enforce ⇒ 沒有這支旗（旗量的是模式，不是「有沒有接真 API」）。
    out = await _health(monkeypatch, AGENT_VERIFIER_MODE="enforce",
                        AGENT_VERIFIER_OBSERVE_ONLY=None, USE_MOCK_JGB_API="false")
    assert health_mod.VERIFIER_GROUNDING_OBSERVE_ON_REAL_API_FLAG not in out["checks"]["premise"]["red_flags"]


class _StubVerifier:
    """只有 `mode` 這個屬性會被相容層碰到（`OutputVerifier.mode` 的 setter 行為
    另由 `test_verifier_rejects_out_of_range_mode` 守）。"""

    def __init__(self):
        self.mode = "enforce"


class _StubRuntime:
    def __init__(self):
        self.verifier = _StubVerifier()


def test_observe_only_requires_mock_jgb_api(monkeypatch):
    """守衛看**解析後的 mode**（F3），⛔ 不綁舊 env 的字面值。"""
    import app as app_mod

    _clear_flags(monkeypatch)
    monkeypatch.setenv(health_mod.AGENT_VERIFIER_MODE_ENV, "observe_only")
    monkeypatch.setenv("USE_MOCK_JGB_API", "false")
    runtime = _StubRuntime()
    with pytest.raises(RuntimeError):
        app_mod._wrap_verifier_observe_only(runtime, None)

    # 相容旗走同一條守衛（它解析成同一個 mode）。
    _clear_flags(monkeypatch)
    monkeypatch.setenv(health_mod.AGENT_VERIFIER_OBSERVE_ONLY_ENV, "true")
    with pytest.raises(RuntimeError):
        app_mod._wrap_verifier_observe_only(_StubRuntime(), None)

    # 正對照：配替身 ⇒ 不 raise，且模式**交到 Verifier 手上**。
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    runtime = _StubRuntime()
    app_mod._wrap_verifier_observe_only(runtime, None)
    assert runtime.verifier.mode == "observe_only"


def test_grounding_observe_does_not_block_startup_even_on_real_api(monkeypatch):
    import app as app_mod

    _clear_flags(monkeypatch)
    monkeypatch.setenv(health_mod.AGENT_VERIFIER_MODE_ENV, "grounding_observe")
    monkeypatch.setenv("USE_MOCK_JGB_API", "false")
    runtime = _StubRuntime()
    app_mod._wrap_verifier_observe_only(runtime, None)   # ⛔ 不 raise
    assert runtime.verifier.mode == "grounding_observe"


def test_compat_layer_does_not_wrap_verify(monkeypatch, rules):
    """security-reviewer r1 F1：相容層**只交模式**，⛔ 不再包 `verify()`、不翻判定。"""
    import app as app_mod

    _clear_flags(monkeypatch)
    monkeypatch.setenv(health_mod.AGENT_VERIFIER_MODE_ENV, "observe_only")
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")

    class _R:
        pass

    runtime = _R()
    runtime.verifier = OutputVerifier(rules)
    before = runtime.verifier.verify
    app_mod._wrap_verifier_observe_only(runtime, None)
    assert runtime.verifier.verify == before, "verify 被外層換掉＝短路後的機敏類不會跑"
    assert runtime.verifier.mode == "observe_only"


# ============================================================ 3. 逐類真值表

#: 觀察類（`grounding_observe` 下只記錄）＝引用解析與涵蓋這一族。
_OBSERVED_CASES = {
    "UNCITED_ASSERTION": (
        _out(sentences=[_fact("我們支援租客資料匯入功能。", [])]),
        _tool_results(_prov(CLEAN_UNIT)),
    ),
    "QUOTE_TOO_SHORT": (
        _out(sentences=[_fact("我們支援匯入。", [_marker("t1", "kb:1000")])]),
        _tool_results(_prov("【範本】")),
    ),
    "QUOTE_NOT_COVERING": (
        # ⚠️ 句子刻意避開 `HANDOFF_WORDS`（「客服」）與 `forbid_terms`：
        # 這一格要量的是覆蓋率，混進別的照擋類就量不到它。
        _out(sentences=[_fact("我們也提供假日的到府安裝喔。", [_marker("t1", "kb:1000")])]),
        _tool_results(_prov(CLEAN_UNIT)),
    ),
    "SOURCE_NOT_CITABLE": (
        _out(sentences=[_fact(CLEAN_SENTENCE, [_marker("t1", "kb:1000")])]),
        _tool_results(_prov(CLEAN_UNIT, citable=False)),
    ),
    "SCHEMA:ref_invalid": (
        _out(sentences=[_fact(CLEAN_SENTENCE, ["這不是一個標記"])]),
        _tool_results(_prov(CLEAN_UNIT)),
    ),
    "SCHEMA:ref_source_not_found": (
        _out(sentences=[_fact(CLEAN_SENTENCE, [_marker("t1", "kb:9999")])]),
        _tool_results(_prov(CLEAN_UNIT)),
    ),
    "SCHEMA:ref_ambiguous": (
        _out(sentences=[_fact(CLEAN_SENTENCE, [_marker("t1", "kb:1000")])]),
        _tool_results(_prov(CLEAN_UNIT), _prov("同名來源但文字不同，這才是歧義。")),
    ),
    "SCHEMA:unit_out_of_range": (
        _out(sentences=[_fact(CLEAN_SENTENCE, [_marker("t1", "kb:1000", index=9)])]),
        _tool_results(_prov(CLEAN_UNIT)),
    ),
}

#: 照擋類（`grounding_observe` 下仍 `ok=False`）——`SCHEMA` 的安全與契約子成因、
#: 極性類、機敏三類。`(out, tool_results, handoff, expected_reason, expected_cause)`
_ENFORCED_CASES = {
    "SCHEMA:marker_in_answer": (
        _out(sentences=[{"text": f"{_marker('t1', 'kb:1000')} 這是資料段。",
                         "kind": "greeting", "refs": []}]),
        _tool_results(_prov(CLEAN_UNIT)), None, "SCHEMA", "marker_in_answer",
    ),
    "SCHEMA:handoff_reason_invalid": (
        _out(kind="handoff", handoff_reason="敏感主題", sentences=[]),
        {}, {"reason": "x"}, "SCHEMA", "handoff_reason_invalid",
    ),
    "SCHEMA:handoff_reason_mismatch": (
        _out(kind="handoff", fact_class="pricing", handoff_reason="no_grounding",
             sentences=[]),
        {}, {"reason": "no_grounding"}, "SCHEMA", "handoff_reason_mismatch",
    ),
    "SCHEMA:ask_target_invalid": (
        _out(kind="ask", ask_target="不在值域內",
             sentences=[{"text": "請問是哪一間？", "kind": "question", "refs": []}]),
        {}, None, "SCHEMA", "ask_target_invalid",
    ),
    "SCHEMA:empty_sentences": (
        _out(sentences=[]), {}, None, "SCHEMA", "empty_sentences",
    ),
    "SCHEMA:empty_text": (
        _out(sentences=[{"text": "   ", "kind": "greeting", "refs": []}]),
        {}, None, "SCHEMA", "empty_text",
    ),
    "POLARITY_MISMATCH": (
        _out(sentences=[_fact("系統目前的帳單格式是固定的，無法自訂設定。",
                              [_marker("t1", "kb:1000")])]),
        _tool_results(_prov("帳單格式可以彈性調整，依需求自訂欄位，聯繫客服協助設定。")),
        None, "POLARITY_MISMATCH", None,
    ),
    "SENSITIVE_TOPIC": (
        _out(fact_class="pricing",
             sentences=[{"text": "這個問題我幫您說明。", "kind": "greeting", "refs": []}]),
        {}, None, "SENSITIVE_TOPIC", None,
    ),
    "ROUTE_NOT_ALLOWED": (
        _out(sentences=[{"text": "請看 https://evil.example.com/promo", "kind": "routing",
                         "refs": []}]),
        {}, None, "ROUTE_NOT_ALLOWED", None,
    ),
    "FORBIDDEN_TERM": (
        _out(sentences=[{"text": "本方案永久免費。", "kind": "greeting", "refs": []}]),
        {}, None, "FORBIDDEN_TERM", None,
    ),
    "HANDOFF_WORD_NO_HANDOFF": (
        _out(sentences=[{"text": "您好，我幫您轉專人。", "kind": "greeting", "refs": []}]),
        {}, None, "HANDOFF_WORD_NO_HANDOFF", None,
    ),
}


@pytest.mark.parametrize("name", sorted(_OBSERVED_CASES))
def test_grounding_observe_only_records_citation_classes(rules, name):
    out_dict, tool_results = _OBSERVED_CASES[name]
    verdict = _verify(_verifier(rules, "grounding_observe"), out_dict, tool_results)
    assert verdict.ok is True, verdict.model_dump()
    assert name in verdict.observed, verdict.observed


@pytest.mark.parametrize("name", sorted(_OBSERVED_CASES))
def test_enforce_still_blocks_citation_classes(rules, name):
    """正對照：同一批案在 `enforce` 下**照擋**——否則上面那組全綠只證明案例造壞了。"""
    out_dict, tool_results = _OBSERVED_CASES[name]
    verdict = _verify(_verifier(rules, "enforce"), out_dict, tool_results)
    assert verdict.ok is False, verdict.model_dump()
    assert verdict.observed == []


@pytest.mark.parametrize("name", sorted(_ENFORCED_CASES))
def test_grounding_observe_still_blocks_safety_and_polarity_classes(rules, name):
    out_dict, tool_results, handoff, reason, cause = _ENFORCED_CASES[name]
    verdict = _verify(_verifier(rules, "grounding_observe"), out_dict, tool_results,
                      handoff=handoff)
    assert verdict.ok is False, verdict.model_dump()
    assert verdict.reason == reason
    assert verdict.schema_cause == cause


@pytest.mark.parametrize("name", sorted(_ENFORCED_CASES))
def test_observe_only_records_everything(rules, name):
    """`observe_only`＝**全部**觀察（維持相容旗的現行語義）。"""
    out_dict, tool_results, handoff, _reason, _cause = _ENFORCED_CASES[name]
    verdict = _verify(_verifier(rules, "observe_only"), out_dict, tool_results,
                      handoff=handoff)
    assert verdict.ok is True, verdict.model_dump()
    assert verdict.observed, "全類觀察卻沒記到任何一類＝觀察紀錄壞了"


def test_short_circuit_does_not_let_a_citation_class_swallow_forbidden_term(rules):
    """security-reviewer r1 F1 的**短路證明**：同一案同時違反引用類（觀察）與
    `forbid_terms`（照擋）⇒ `grounding_observe` 下仍 `ok=False`。

    舊作法（外層把 `ok=False` 翻成 `ok=True`）在這個案上會回 `ok=True`：引用類先命中
    就 `return` 了，禁詞那一步**根本沒跑**。"""
    out_dict = _out(sentences=[
        _fact("我們提供永久免費的匯入服務。", [_marker("t1", "kb:1000")]),
    ])
    tool_results = _tool_results(_prov("系統支援租客資料匯入功能，需另行報價。"))

    verdict = _verify(_verifier(rules, "grounding_observe"), out_dict, tool_results)
    assert verdict.ok is False
    assert verdict.reason == "FORBIDDEN_TERM"
    # 正對照：引用類確實命中了（所以這案真的走過「觀察 ⇒ 繼續跑」那條路）。
    assert "QUOTE_NOT_COVERING" in verdict.observed


def test_observed_ref_is_skipped_in_later_per_ref_checks(rules):
    """r3 註記③：解析失敗且被觀察的 ref ⇒ 後續逐 ref 檢查跳過它
    （`resolved[(i, j)]` 不存在，⛔ 不得 KeyError、⛔ 不得拿別的 ref 頂替）。"""
    out_dict = _out(sentences=[_fact(CLEAN_SENTENCE, ["壞標記", _marker("t1", "kb:1000")])])
    tool_results = _tool_results(_prov(CLEAN_UNIT))
    verdict = _verify(_verifier(rules, "grounding_observe"), out_dict, tool_results)
    assert verdict.ok is True
    assert "SCHEMA:ref_invalid" in verdict.observed


# ============================================================ 4. 多 ref 聚合


def test_enforce_keeps_at_least_one_ref_fully_passes_semantics(rules):
    """引用類聚合**不變**（r11 F-1 刻意設計）：ref A 覆蓋不足＋ref B 全過 ⇒ `ok=True`。"""
    out_dict = _out(sentences=[_fact(CLEAN_SENTENCE, [
        _marker("t1", "kb:2000"),   # A：覆蓋不足
        _marker("t1", "kb:1000"),   # B：完整通過
    ])])
    tool_results = _tool_results(
        _prov(CLEAN_UNIT, source="kb:1000"),
        _prov("假日客服支援時間為上午九點到下午五點。", source="kb:2000"),
    )
    verdict = _verify(_verifier(rules, "enforce"), out_dict, tool_results)
    assert verdict.ok is True, verdict.model_dump()


def test_polarity_mismatch_on_any_ref_blocks_even_if_another_ref_passes(rules):
    """plan-verifier r1 #3：極性類**任一 ref 命中即擋**——⛔ 不得被通過的 ref 洗掉。"""
    out_dict = _out(sentences=[_fact("系統無法自訂帳單格式。", [
        _marker("t1", "kb:3000"),   # A：極性一致（引文也是否定）
        _marker("t1", "kb:4000"),   # B：極性不符（引文是正向）
    ])])
    tool_results = _tool_results(
        _prov("系統無法自訂帳單格式，需要由客服協助調整。", source="kb:3000"),
        _prov("系統可以自訂帳單格式，由您在後台自行調整。", source="kb:4000"),
    )
    verdict = _verify(_verifier(rules, "enforce"), out_dict, tool_results)
    assert verdict.ok is False
    assert verdict.reason == "POLARITY_MISMATCH"

    # `grounding_observe` 下同樣照擋（極性類不是觀察類）。
    verdict = _verify(_verifier(rules, "grounding_observe"), out_dict, tool_results)
    assert verdict.ok is False
    assert verdict.reason == "POLARITY_MISMATCH"


def test_coverage_failure_no_longer_swallows_the_polarity_verdict(rules):
    """`grounding_observe`：覆蓋率先掛（觀察）的句子**仍拿得到極性判定**（照擋）。"""
    out_dict = _out(sentences=[_fact("這個功能無法使用。", [_marker("t1", "kb:1000")])])
    tool_results = _tool_results(_prov("匯入排程於每日凌晨自動執行，成功後寄出通知信。"))
    verdict = _verify(_verifier(rules, "grounding_observe"), out_dict, tool_results)
    assert verdict.ok is False
    assert verdict.reason == "POLARITY_MISMATCH"
    assert "QUOTE_NOT_COVERING" in verdict.observed


# ============================================================ 5. self_test 釘死 enforce


@pytest.mark.parametrize("mode", ["enforce", "grounding_observe", "observe_only"])
def test_self_test_is_green_under_every_mode(rules, mode):
    """security r1 F2：自證一律以 `enforce` 跑。

    ⚠️ 這條**自帶正對照**：`self_test` 要求 `known_fabrications.json` **全被拒**；
    模式若真的傳導進去，觀察模式下那些案會全部放行 ⇒ `RuntimeError`。不 raise 就是
    「模式沒有污染自證」的證據。"""
    verifier = OutputVerifier(rules, mode=mode)
    assert verifier.self_test(_FIXTURES_DIR) == len(
        json.loads((_FIXTURES_DIR / "known_open.json").read_text(encoding="utf-8")))
    assert verifier.mode == mode, "self_test 跑完必須把模式還原"


@pytest.mark.parametrize("env", ["enforce", "grounding_observe", "observe_only", "", "typo"])
def test_bootstrap_self_test_passes_under_every_mode_env(monkeypatch, env, tmp_path):
    """啟動路徑（`bootstrap.build_runtime` 的自證）在**任何**模式旗值下都起得來。"""
    from services.agent import bootstrap

    _clear_flags(monkeypatch)
    if env:
        monkeypatch.setenv(health_mod.AGENT_VERIFIER_MODE_ENV, env)
    runtime = bootstrap.build_runtime(None, object(), _FakeRegistry())
    assert runtime.rules_sha
    # 組裝完成時的模式仍是預設值——模式是 `app` 相容層在**之後**才交的。
    assert runtime.verifier.mode == "enforce"


# ============================================================ 6. 觀察判定不算拒絕


@pytest.mark.asyncio
async def test_observed_verdict_does_not_count_as_a_rewrite():
    """`ok=True` 且 `observed` 非空 ⛔ 不得遞增 `counters.rewrites`。

    量法：把改寫預算設成 0（`rewrite_exhausted` 用 `>=`，第 1 次拒絕就耗盡）。
    觀察判定若被當成拒絕，這回合會變成 `handoff_reason=budget_exhausted` 的固定句。
    """
    from services.agent.budget import Budget
    from services.agent.output_schema import VerifierVerdict
    from tests.unit.agent.test_runtime_req import (
        FakeProvider, FakeRegistry, FakeVerifier, _final_response, _identity, _runtime,
    )

    provider = FakeProvider([_final_response(kind="answer", answer="這是答案。")])
    verifier = FakeVerifier(results=[
        VerifierVerdict(ok=True, observed=["QUOTE_NOT_COVERING", "SCHEMA:ref_invalid"]),
    ])
    runtime = _runtime(provider=provider, registry=FakeRegistry(call_results=[]),
                       verifier=verifier, budget=Budget(max_rewrites=0))
    result = await runtime.run_turn(_identity(), "問題", {})

    assert result.kind == "answer"
    assert result.answer == "這是答案。"
    assert (result.handoff or {}).get("reason") != "budget_exhausted"
    assert len(provider.calls) == 1, "觀察判定被當成拒絕 ⇒ 會多打一次模型"
