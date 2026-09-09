"""unit：U2——程式側問句敏感判定＋兩道閘的准入
（Plan `inputs/plan-walkthrough-fixes-batch3-20260909.md` §3）。

被測的三件事：
1. 規則檔載入正對照——`VerifierRules.load(出貨規則檔).question_sensitive_patterns`
   筆數＝檔內筆數且非空（pydantic 白名單會靜默忽略未宣告欄位；沒有這條，
   規則檔加了鍵卻讀不到也不會有人發現）。
2. `question_sensitive()` 的真值表：SENSITIVE 五類各一句正例＋物管領域負例。
3. 兩道閘的准入：模型自報 `sensitive_no_grounding`＋`fact_class ∈ SENSITIVE`，
   而程式判這一句非敏感 ⇒ 走既有降級／兩出口並記
   `sensitive_self_report_overridden`；程式判敏感 ⇒ ⛔ 一個欄位都不動。
"""
from __future__ import annotations

import json

import pytest

from services.agent.output_schema import VerifierRules
from services.agent.question_sensitivity import question_sensitive
from services.agent.runtime import (
    ASK_TARGET_TEXT,
    NO_DATA_TEXT,
    NO_JUDGEMENT_TEXT,
    ToolCallRecord,
    TurnResult,
    TurnTrace,
    _apply_handoff_data_exits,
    _apply_handoff_without_lookup,
)
from services.presales_gate import SENSITIVE, FactClass

from tests.unit.agent.test_verifier_req import _RULES_PATH

pytestmark = pytest.mark.unit

_REQ = "knowledge-outline-and-intent-architecture:U2"


@pytest.fixture()
def rules() -> VerifierRules:
    return VerifierRules.load(_RULES_PATH)


# ---------------------------------------------------------------------------
# 1. 規則檔載入正對照
# ---------------------------------------------------------------------------
def test_rules_load_exposes_question_sensitive_patterns(rules):
    """出貨規則檔的筆數要原封不動地到得了模型欄位（正對照＝非空）。"""
    on_disk = json.loads(_RULES_PATH.read_bytes())["question_sensitive_patterns"]

    assert len(on_disk) > 0, "規則檔本身是空的 ⇒ 這條測試失去意義（正對照不成立）"
    assert len(rules.question_sensitive_patterns) == len(on_disk)
    assert rules.question_sensitive_patterns == on_disk
    # SENSITIVE 五類各一組（Plan §3：以五類維護）
    assert len(on_disk) == len(SENSITIVE) == 5


def test_default_is_empty_when_key_absent():
    """未配置 ⇒ 預設空表、判定一律非敏感（⛔ 不因缺鍵而炸）。"""
    bare = VerifierRules(
        version="t", sha256="0" * 64, sensitive_patterns=[], negation_terms=[],
        forbid_terms=[], allowed_routes=[], assertion_terms=[],
    )
    assert bare.question_sensitive_patterns == []
    assert question_sensitive("你們抽成幾成", bare) is False


# ---------------------------------------------------------------------------
# 2. 分類器真值表
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "message",
    [
        "你們抽成幾成？",                    # pricing
        "服務費率怎麼算",                    # pricing
        "一個月多少錢",                      # pricing（`test_outline_citation_seed_req`
                                             #  的既有案例：它必須仍然轉人）
        "SLA 保證多久回應",                  # contract_sla
        "合約條款可以先看嗎",                # contract_sla
        "有哪些業者在用你們系統",            # customer_reference
        "有沒有導入案例可以參考",            # customer_reference
        "符合個資法嗎",                      # compliance
        "你們有 GDPR 合規嗎",                # compliance
        "資安怎麼做",                        # security
        "有 ISO 27001 嗎",                   # security
        "有ＩＳＯ27001嗎",                   # NFKC：全形拉丁字母同樣命中
    ],
)
def test_sensitive_questions_match(message, rules):
    assert question_sensitive(message, rules) is True


@pytest.mark.parametrize(
    "message",
    [
        "要不要催他",                        # Plan §3 指名的負例
        "怎麼辦",                            # Plan §3 指名的負例
        "756248 你建議我怎麼做",
        "756248 這張帳單是不是逾期了",
        "含滯納金要多少？",                  # 租客帳單金額，⛔ 不是售前報價
        "769246 那張多少錢",
        "合約 89481 什麼時候到期",           # 租約到期，⛔ 不是服務合約條款
        "89481續約要怎用",
        "幫我把這戶租金調高 5%",
        "浴室天花板漏水",
        "催繳草稿怎麼分級",
        "就 8 月租金那張",                   # 誤判量測抓到過的誤殺（「月租」子字串）
        "你知道我是誰嗎？要不要先登入？",
        "",
    ],
)
def test_non_sensitive_questions_do_not_match(message, rules):
    assert question_sensitive(message, rules) is False


def test_question_sensitive_has_no_side_effects(rules):
    before = list(rules.question_sensitive_patterns)
    question_sensitive("你們抽成幾成", rules)
    assert rules.question_sensitive_patterns == before


# ---------------------------------------------------------------------------
# 素材：轉人結果
# ---------------------------------------------------------------------------
def _handoff_result(
    *,
    handoff_reason: str = "sensitive_no_grounding",
    fact_class: str = FactClass.pricing.value,
    tool_calls: list | None = None,
) -> TurnResult:
    trace = TurnTrace(
        trace_id="t-u2",
        tool_calls=list(tool_calls or []),
        final_kind="handoff",
        handoff_reason=handoff_reason,
    )
    handoff_dict = {
        "reason": handoff_reason,
        "fact_class": fact_class,
        "channel": "line",
        "message": "已為你轉真人客服，請稍候。",
    }
    return TurnResult(
        kind="handoff",
        answer=handoff_dict["message"],
        handoff=handoff_dict,
        quick_replies=[],
        trace=trace,
    )


def _ok_call(*, empty: bool) -> ToolCallRecord:
    return ToolCallRecord(
        id="call-1", name="jgb2.query.bills", args_summary={},
        ms=1, status="ok", n_items=0 if empty else 2, empty=empty,
    )


# ---------------------------------------------------------------------------
# 3. 兩道閘的准入真值表
# ---------------------------------------------------------------------------
def test_zero_lookup_overridden_downgrades_to_ask_target(rules):
    """自報敏感＋程式判非敏感＋零查詢 ⇒ 追問固定句＋記 override。"""
    result = _handoff_result()
    out = _apply_handoff_without_lookup(result, {}, "要不要催他", rules)

    assert out.answer == ASK_TARGET_TEXT
    assert out.kind == "answer"
    assert out.handoff is None
    assert out.trace.final_kind == "answer"
    assert out.trace.handoff_reason is None
    assert out.outcome["state"] == "clarifying"
    assert "handoff_without_lookup" in out.trace.violations
    assert "sensitive_self_report_overridden" in out.trace.violations


def test_data_exit_overridden_downgrades_to_no_judgement(rules):
    """自報敏感＋程式判非敏感＋有資料 ⇒ NO_JUDGEMENT＋記 override。"""
    result = _handoff_result(tool_calls=[_ok_call(empty=False)])
    out = _apply_handoff_data_exits(result, "要不要催他", rules)

    assert out.answer == NO_JUDGEMENT_TEXT
    assert out.kind == "answer"
    assert out.ask_target == "confirm_intent"
    assert out.outcome["state"] == "clarifying"
    assert "handoff_no_judgement" in out.trace.violations
    assert "sensitive_self_report_overridden" in out.trace.violations


def test_data_exit_overridden_all_empty_goes_no_data(rules):
    result = _handoff_result(tool_calls=[_ok_call(empty=True)])
    out = _apply_handoff_data_exits(result, "要不要催他", rules)

    assert out.answer == NO_DATA_TEXT
    assert out.kind == "answer"
    assert "handoff_no_data" in out.trace.violations
    assert "sensitive_self_report_overridden" in out.trace.violations


@pytest.mark.parametrize("message", ["你們抽成幾成", "有 ISO 27001 嗎"])
def test_sensitive_question_leaves_handoff_untouched(message, rules):
    """程式也判敏感 ⇒ 兩道閘 ⛔ 一個欄位都不動（正對照：仍轉人）。"""
    for gate, call in (
        (_apply_handoff_without_lookup,
         lambda r: _apply_handoff_without_lookup(r, {}, message, rules)),
        (_apply_handoff_data_exits,
         lambda r: _apply_handoff_data_exits(r, message, rules)),
    ):
        result = _handoff_result(tool_calls=[_ok_call(empty=False)])
        snapshot = dict(result.handoff)
        out = call(result)

        assert out.kind == "handoff", gate.__name__
        assert out.answer == snapshot["message"]
        assert out.handoff == snapshot          # ⛔ fact_class 沒被改寫
        assert out.trace.handoff_reason == "sensitive_no_grounding"
        assert out.trace.violations == []


def test_rules_missing_keeps_handoff(rules):
    """規則拿不到 ⇒ ⛔ 不准入（往維持轉人的方向錯）。"""
    result = _handoff_result()
    out = _apply_handoff_without_lookup(result, {}, "要不要催他", None)
    assert out.kind == "handoff"
    assert out.trace.violations == []


def test_non_sensitive_fact_class_with_sensitive_reason_untouched(rules):
    """`fact_class` 不在敏感五類、原因卻是 `sensitive_no_grounding`
    ⇒ 不屬於這條新路（既有行為不變：仍轉人）。"""
    result = _handoff_result(fact_class=FactClass.feature.value)
    out = _apply_handoff_without_lookup(result, {}, "要不要催他", rules)
    assert out.kind == "handoff"
    assert out.trace.violations == []


# ---------------------------------------------------------------------------
# 既有非敏感路徑不受影響（回歸）
# ---------------------------------------------------------------------------
def test_existing_no_grounding_path_unchanged_even_for_sensitive_question(rules):
    """`no_grounding`＋非敏感 `fact_class` ⇒ 照舊降級，⛔ 不因問句敏感而改判
    （這道閘的資格只加不減；問句敏感度只用在被推翻的那條路）。"""
    result = _handoff_result(
        handoff_reason="no_grounding", fact_class=FactClass.feature.value
    )
    out = _apply_handoff_without_lookup(result, {}, "你們抽成幾成", rules)

    assert out.answer == ASK_TARGET_TEXT
    assert out.trace.violations == ["handoff_without_lookup"]


def test_llm_mentioned_handoff_path_unchanged(rules):
    result = _handoff_result(
        handoff_reason="llm_mentioned_handoff", fact_class=FactClass.other.value,
        tool_calls=[_ok_call(empty=False)],
    )
    out = _apply_handoff_data_exits(result, "怎麼辦", rules)

    assert out.answer == NO_JUDGEMENT_TEXT
    assert out.trace.violations == ["handoff_no_judgement"]


def test_sensitive_no_grounding_still_transfers_without_rules_by_default():
    """兩道閘的預設參數（既有呼叫端不傳 message／rules）⇒ 行為與改動前一致。"""
    result = _handoff_result()
    assert _apply_handoff_without_lookup(result, {}).kind == "handoff"
    assert _apply_handoff_data_exits(result).kind == "handoff"


# ---------------------------------------------------------------------------
# `_finalize` 有把 message 串下去
# ---------------------------------------------------------------------------
def test_finalize_threads_message_into_both_gates():
    """釘住串接：`_finalize` 呼叫兩道閘時要帶 `user_message` 與規則集。"""
    import inspect

    from services.agent import runtime as rt

    src = " ".join(inspect.getsource(rt.AgentRuntime._run_turn_body).split())
    assert '_qs_rules = getattr(self.verifier, "rules", None)' in src
    assert "_apply_handoff_without_lookup( result, agent_state, user_message, _qs_rules )" in src
    assert "_apply_handoff_data_exits(result, user_message, _qs_rules)" in src
