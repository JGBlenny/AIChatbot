"""四道出口閘與回合收尾（Plan R R1｜`inputs/plan-structural-refactor-20260910.md` §0）。

**本檔是純搬移**：四支 `_apply_*` 與它們的固定句、`_handoff_fact_class`／
`_sensitive_self_report_overridden` 逐字從 `runtime.py` 搬來，⛔ 一個條件、一個
順序、一個文案都沒有改。`runtime.py` 原樣 re-export，既有 import 路徑不變。

新增的只有兩件事：

- `EXIT_GATES`——四道閘的**依序表**。順序本身是契約（見各閘 docstring 的
  「排在 X 之後」註記），把它寫成一張表是為了讓「順序」變成可讀、可測的資料，
  ⛔ 不是為了讓誰去重排它。
- `finalize()`——原 `_run_turn_body` 的閉包 `_finalize` 升為模組級。四道閘、
  三個狀態寫點（`LAST_ASK_TARGET_KEY`／`handoff_cache`／`fixed_streak`）、
  `outcome` 預設、dialog、決策快照，全部在這一支裡，⛔ 不再散在閉包裡。
"""
from __future__ import annotations

from typing import Any, Optional

from services.agent.agent_session import AgentSession
from services.agent.output_schema import ASK_TARGETS
from services.agent.question_sensitivity import question_sensitive
from services.agent.turn_context import (
    SELECT_SCOPE_KEY,
    TurnAccumulator,
    TurnResult,
    _emit_agent_decision,
    default_outcome,
    make_outcome,
)
from services.presales_gate import SENSITIVE, FactClass


#: L15 (a)⑤：範圍外時使用者看到的**指路固定句**。單一句、對所有受眾一體適用；
#: ⛔ 無任何插值（L15-13：帶 id／名稱等於用回話的差別揭露存在性）。
SCOPE_EXIT_TEXT = "這個對話只看你點選的那一戶；要查別戶請回清單點那一戶。"


def _apply_scope_exit(result: TurnResult, *, scope_in: int, scope_out: int,
                      agent_state: Optional[dict] = None) -> TurnResult:
    """L15 (a)④：**唯一接句點**——模型迴圈產出的每一個 `TurnResult` 都經這裡。

    - 全部範圍外（`scope_out>0 and scope_in==0`）⇒ 整個答案換成固定句、
      `kind="answer"`、`handoff=None`（⛔ 不進 handoff cache：`_finalize` 只對
      `trace.final_kind == "handoff"` 寫快取，故這裡連 `final_kind` 一起改）。
    - 部分範圍外 ⇒ 答案末尾接一行固定句。
    - 沒有範圍外 ⇒ 逐字不動。

    第六批 #10：`agent_state` 給的話，**這一回合出現過範圍外查詢就清掉物件記憶**
    ——使用者已經在講另一戶了，留著上一個名字只會讓下一張確認卡填錯物件。
    ⚠️ 缺省 `None` ⇒ 只做原本那三件事（模組級函式，測試直接呼叫它時不必給狀態）。
    """
    if scope_out <= 0:
        return result
    if isinstance(agent_state, dict):
        # R3：`estate_carry` 是唯一的 `until_scope_exit` 鍵——清它就是
        # `AgentSession.scope_exit()`（⛔ 值不變，只是換個落點）。
        AgentSession(agent_state).scope_exit()
    if scope_in == 0:
        result.answer = SCOPE_EXIT_TEXT
        result.kind = "answer"
        result.handoff = None
        result.trace.final_kind = "answer"
        result.trace.handoff_reason = None
        result.outcome = make_outcome("out_of_scope", expects="none")
        return result
    result.answer = result.answer.rstrip() + "\n" + SCOPE_EXIT_TEXT
    return result


#: S4 §5：零查詢轉人的追問固定句。單一句、⛔ 無任何插值（同 `SCOPE_EXIT_TEXT`
#: 的紀律——帶物件名稱等於用回話的差別揭露存在性）。
#: 非敏感的轉人原因（封閉集合）：兩道降級閘與 T2 改寫提示都只認這一組——
#: `no_grounding`（模型自報查無）與 `llm_mentioned_handoff`（模型在文字裡自己寫了轉人
#: 詞、後掃描補的訊號）。2026-09-09 verifier F1：模型用後者繞過兩出口 ⇒ 併入同一組；
#: 敏感類（`sensitive_no_grounding`）與預算耗盡一律不在此列。
NON_SENSITIVE_HANDOFF_REASONS: frozenset = frozenset({"no_grounding", "llm_mentioned_handoff"})

#: 各受眾共用（prospect 也會經過同一道閘），措辭不帶任何一條線的名詞。
ASK_TARGET_TEXT = "想處理哪一件事？講名稱或編號就可以。"


def _handoff_fact_class(result: TurnResult) -> Optional[FactClass]:
    """`result.handoff["fact_class"]` 解析成封閉值域；缺值／值域外 ⇒ `None`。"""
    try:
        return FactClass((result.handoff or {}).get("fact_class"))
    except ValueError:
        return None


def _sensitive_self_report_overridden(
    result: TurnResult, message: str, rules: Any
) -> bool:
    """U2（Plan `plan-walkthrough-fixes-batch3-20260909.md` §3）：模型**自報**敏感，
    但程式側判這一句不是敏感題 ⇒ 這次自報不算准入豁免，本回合照走兩道降級閘。

    三個條件全成立才算（缺任一 ⇒ `False`＝維持現狀轉人）：
    - `trace.handoff_reason == "sensitive_no_grounding"`（模型自報敏感時 Verifier
      強制的原因值；⛔ 不改 `NON_SENSITIVE_HANDOFF_REASONS` 集合本身）
    - `fact_class ∈ SENSITIVE`
    - `question_sensitive(message, rules) is False`（程式側第二意見）

    ⚠️ **`rules` 拿不到 ⇒ 一律 `False`**：判不出來的時候要往「維持轉人」錯，
    ⛔ 不能往「降級成固定句」錯（feedback「規則只能治封閉集合」：非用規則不可時
    刻意往可回復的方向錯）。
    ⛔ 本函式**不改任何欄位**——不改寫 `out.fact_class`、不動 `result.handoff`
    （security r1 F7：改寫 fact_class 會反轉答案側的 `SENSITIVE_TOPIC` 擋法）。
    """
    if result.trace.handoff_reason != "sensitive_no_grounding":
        return False
    if _handoff_fact_class(result) not in SENSITIVE:
        return False
    if rules is None:
        return False
    return question_sensitive(message, rules) is False


def _apply_handoff_without_lookup(
    result: TurnResult, agent_state: dict, message: str = "", rules: Any = None
) -> TurnResult:
    """S4 §5：零查詢的 `no_grounding` 轉人降級成追問（與 `_apply_scope_exit` 同層）。

    條件全為封閉欄位（缺任一 ⇒ 不降級）：
    - `result.kind == "handoff"`
    - `result.trace.handoff_reason ∈ NON_SENSITIVE_HANDOFF_REASONS`
      **或**（U2）`_sensitive_self_report_overridden` 成立
    - `fact_class` 不在敏感五類（敏感類一律不動，仍轉人）；U2 那條路例外——
      自報敏感被程式推翻時 ⛔ 不享這道豁免，並多記一筆
      `sensitive_self_report_overridden`
    - 本回合沒有任何工具呼叫（`trace.tool_calls` 為空）
    - 沒有釘住的 select 範圍（`SELECT_SCOPE_KEY` 為 `None`）

    降級時**五欄一起改**（mirrors `_apply_scope_exit`）：`answer`／`kind`／
    `handoff`／`trace.final_kind`／`trace.handoff_reason`，另設
    `outcome=clarifying` 並記一筆 `violations`。
    """
    if result.kind != "handoff":
        return result
    overridden = _sensitive_self_report_overridden(result, message, rules)
    if result.trace.handoff_reason not in NON_SENSITIVE_HANDOFF_REASONS and not overridden:
        return result
    # U2：自報敏感被程式推翻的那條路，⛔ 不再享 `fact_class ∈ SENSITIVE` 的豁免
    # ——它走的是同一組固定句出口（`ASK_TARGET_TEXT`），⛔ 不會吐敏感內容。
    if _handoff_fact_class(result) in SENSITIVE and not overridden:
        return result
    if len(result.trace.tool_calls) != 0:
        return result
    if agent_state.get(SELECT_SCOPE_KEY) is not None:
        return result
    result.answer = ASK_TARGET_TEXT
    result.kind = "answer"
    result.handoff = None
    result.trace.final_kind = "answer"
    result.trace.handoff_reason = None
    result.outcome = make_outcome("clarifying", expects="text")
    result.trace.violations.append("handoff_without_lookup")
    if overridden:
        result.trace.violations.append("sensitive_self_report_overridden")
    return result


# ════════════════════════════════════════════════════════════════════
# T1：追問契約 `ask_target`（Plan `inputs/plan-walkthrough-fixes-batch2-20260909.md` §2）
# ════════════════════════════════════════════════════════════════════


def _apply_ask_target_gate(result: TurnResult) -> TurnResult:
    """T1：最終輸出是 `kind=ask` 卻沒有合法追問對象 ⇒ 換成指路固定句。

    ⚠️ 這是**保底閘**，不是主檢查：主檢查在 Verifier
    （`SCHEMA/ask_target_invalid`），但正式站的觀察模式
    （`AGENT_VERIFIER_OBSERVE_ONLY`）下 Verifier 不擋，所以出口這一層必須自己
    再判一次——⛔ 不得假設「Verifier 過了就一定合法」。

    條件全為封閉欄位：`kind == "ask"` 且 `ask_target ∉ ASK_TARGETS`
    （缺值與值域外同一條）。命中時四欄一起改（mirrors `_apply_handoff_without_lookup`）：
    `answer`／`outcome`／`trace.violations`，外加把 `ask_target` 歸零——
    ⚠️ **歸零是刻意的**：一個值域外的字串若留在 `TurnResult.ask_target` 上，
    `_finalize` 就會把它寫進 `agent_state[LAST_ASK_TARGET_KEY]`，讓「本會話的
    上一個追問對象」這個封閉欄位變成模型可以塞任意字串的地方。

    ⛔ **不改 `kind`**：這一回合仍然是在追問（`outcome=clarifying/expects=text`），
    改成 `answer` 會讓呼叫端以為問題已經答完。
    """
    if result.kind != "ask":
        return result
    if result.ask_target in ASK_TARGETS:
        return result
    result.answer = ASK_TARGET_TEXT
    result.ask_target = None
    result.outcome = make_outcome("clarifying", expects="text")
    result.trace.violations.append("ask_target_invalid")
    return result


# ════════════════════════════════════════════════════════════════════
# T2：兩出口——資料裡沒有 vs 不做判斷（Plan `inputs/plan-walkthrough-fixes-batch2-20260909.md` §3）
# ════════════════════════════════════════════════════════════════════

#: 全部工具結果為空（`status=="ok"` 且 `empty`）時的固定句。⛔ 無插值——
#: 帶物件名稱等於用回話的差別揭露存在性（同 `SCOPE_EXIT_TEXT`／`ASK_TARGET_TEXT`）。
NO_DATA_TEXT = "系統裡查不到這一筆或這一類資料；請確認名稱或編號，或換一個查法。"

#: 至少一筆工具結果有資料、但模型改寫後仍轉人（或改寫預算已耗盡）時的固定句。
#: ⛔ 無插值。
NO_JUDGEMENT_TEXT = "這題要看你的判斷；我這邊能給的是系統資料，要我列出來嗎？"


def _apply_handoff_data_exits(
    result: TurnResult, message: str = "", rules: Any = None
) -> TurnResult:
    """T2：`no_grounding` 轉人依工具結果是否有資料分成兩個出口（與
    `_apply_ask_target_gate` 同層、在其之後）。

    條件全為封閉欄位（缺任一 ⇒ 不動）：
    - `result.kind == "handoff"`
    - `result.trace.handoff_reason ∈ NON_SENSITIVE_HANDOFF_REASONS`
      **或**（U2）`_sensitive_self_report_overridden` 成立
    - `fact_class` 不在敏感五類（敏感類一律不動，仍轉人）；U2 那條路例外，同上
    - `result.trace.tool_calls` 非空

    命中後先看有沒有「不能拿 `ToolCallRecord.empty` 判定」的筆——任一筆
    `status != "ok"`（`error`／`timeout`／`rejected`），或本回合有
    `tool_call_id_collides_with_reserved`（撞名保留 id）⇒ **整段不動**，
    維持既有出口（`sensitive_no_grounding`／`llm_mentioned_handoff`／
    `budget_exhausted` 也在這條路上，本函式對它們同樣不動）。

    剩下的情況（全部工具結果 `status=="ok"`）依 `empty` 分流：
    - 全部 `empty` ⇒ `kind=answer`、`answer=NO_DATA_TEXT`、
      `outcome=answered`、`violations += ["handoff_no_data"]`。
    - 至少一筆非 `empty` ⇒ `kind=answer`、`answer=NO_JUDGEMENT_TEXT`、
      `ask_target=confirm_intent`、`outcome=clarifying`、
      `violations += ["handoff_no_judgement"]`（此路只有在模型迴圈內的
      改寫提示——§3 的「迴圈內改寫」——已經重試過仍轉人，或改寫預算已耗盡
      時才會走到這裡；本函式本身 ⛔ 不呼叫模型）。

    五欄一起改（mirrors `_apply_scope_exit`／`_apply_handoff_without_lookup`）：
    `answer`／`kind`／`handoff`／`trace.final_kind`／`trace.handoff_reason`，
    另設 `outcome` 並記一筆 `violations`；NO_JUDGEMENT 分支另外設
    `result.ask_target = "confirm_intent"`——`_finalize` 把
    `agent_state[LAST_ASK_TARGET_KEY]` 寫成「本回合 `ask_target` 是否落在
    `ASK_TARGETS` 值域內」（見 `_finalize` 的寫點，⛔ 不再只認 `kind=="ask"`），
    使這個 `kind=="answer"` 的回合一樣能把 `confirm_intent` 帶進下一回合，供
    T3 的肯定語＝授權判定使用。
    """
    if result.kind != "handoff":
        return result
    overridden = _sensitive_self_report_overridden(result, message, rules)
    if result.trace.handoff_reason not in NON_SENSITIVE_HANDOFF_REASONS and not overridden:
        return result
    # U2：理由同 `_apply_handoff_without_lookup`——被推翻的自報敏感 ⛔ 不享豁免，
    # 走同一組固定句出口（`NO_DATA_TEXT`／`NO_JUDGEMENT_TEXT`）。
    if _handoff_fact_class(result) in SENSITIVE and not overridden:
        return result
    tool_calls = result.trace.tool_calls
    if not tool_calls:
        return result
    if "tool_call_id_collides_with_reserved" in result.trace.violations:
        return result
    if any(r.status != "ok" for r in tool_calls):
        return result
    if all(r.empty for r in tool_calls):
        result.answer = NO_DATA_TEXT
        result.kind = "answer"
        result.handoff = None
        result.trace.final_kind = "answer"
        result.trace.handoff_reason = None
        result.outcome = make_outcome("answered", expects="text")
        result.trace.violations.append("handoff_no_data")
        if overridden:
            result.trace.violations.append("sensitive_self_report_overridden")
        return result
    result.answer = NO_JUDGEMENT_TEXT
    result.kind = "answer"
    result.handoff = None
    result.trace.final_kind = "answer"
    result.trace.handoff_reason = None
    result.ask_target = "confirm_intent"
    result.outcome = make_outcome("clarifying", expects="text")
    result.trace.violations.append("handoff_no_judgement")
    if overridden:
        result.trace.violations.append("sensitive_self_report_overridden")
    return result


# ---------------------------------------------------------------------------
# R1：四道閘的依序表 ＋ 模組級 `finalize`
# ---------------------------------------------------------------------------

#: **四道出口閘的順序**（Plan R R1；⛔ 順序即契約，不得重排）。
#: 每一格是 `(名稱, 呼叫器)`；呼叫器統一收 `(result, agent_state, user_message,
#: qs_rules)` 四個參數，各閘只取自己要的那幾個——⛔ 不為了「參數一致」去改任何
#: 一支閘的簽名（那些簽名有既有測試逐條釘住）。
#:
#: 順序的理由（逐條見各閘 docstring）：
#:   ① `_apply_scope_exit`   ——**唯一接句點**，排在 handoff cache 與 dialog 之前。
#:   ② `_apply_handoff_without_lookup` —— 排在 ① 之後：範圍外的回合已經被換成
#:      固定句，不該再被當成一次零查詢轉人來判。
#:   ③ `_apply_ask_target_gate` —— 排在 ② 之後（T1／security r1 #3）。
#:   ④ `_apply_handoff_data_exits` —— 排在 ③ 之後：T2 的 NO_JUDGEMENT 分支會把
#:      `kind` 換成 `answer` 並另設 `ask_target="confirm_intent"`，排在 ask_target
#:      閘之後才不會被那道只認 `kind=="ask"` 的閘動到。
def _gate_scope_exit(result, agent_state, user_message, qs_rules, scope_counts):
    # L15 (a)④：**唯一接句點**，排在 handoff cache 與 dialog 之前——
    # 全範圍外的回合在這裡就已經是 `kind="answer"`，故 ⛔ 不會進快取，
    # dialog 存的也是使用者看到的那一句（含接句）。
    return _apply_scope_exit(
        result, scope_in=scope_counts["in"], scope_out=scope_counts["out"],
        agent_state=agent_state,
    )


def _gate_handoff_without_lookup(result, agent_state, user_message, qs_rules, scope_counts):
    # U2：這道閘要拿得到**使用者這一句**與規則集，才能判「模型自報的敏感站不站得住」。
    return _apply_handoff_without_lookup(result, agent_state, user_message, qs_rules)


def _gate_ask_target(result, agent_state, user_message, qs_rules, scope_counts):
    # T1（security r1 #3）：排在 `_apply_scope_exit` **之後**——範圍外的回合在上面
    # 已經被換成固定句，不該再被當成一次追問來判。
    return _apply_ask_target_gate(result)


def _gate_handoff_data_exits(result, agent_state, user_message, qs_rules, scope_counts):
    # T2：排在 `_apply_ask_target_gate` **之後**——NO_JUDGEMENT 分支會把 `kind`
    # 從 `handoff` 換成 `answer` 並另設 `ask_target="confirm_intent"`；排在 ask_target
    # 閘之後，才不會被那道只認 `kind=="ask"` 的閘動到。
    return _apply_handoff_data_exits(result, user_message, qs_rules)


EXIT_GATES: tuple = (
    ("scope_exit", _gate_scope_exit),
    ("handoff_without_lookup", _gate_handoff_without_lookup),
    ("ask_target_gate", _gate_ask_target),
    ("handoff_data_exits", _gate_handoff_data_exits),
)


def finalize(
    acc: TurnAccumulator, result: TurnResult, *, is_fixed: bool,
    verifier: Any, cache: dict, agent_state: dict, user_message: str,
) -> TurnResult:
    """回合收尾（原 `_run_turn_body` 的閉包 `_finalize`，逐字搬移）。

    ⚠️ 四道閘依 `EXIT_GATES` **依序**跑，⛔ 不得重排（順序理由見該表）。
    U2：兩道閘要拿得到**使用者這一句**與規則集，才能判「模型自報的敏感站不站得住」
    （Plan §3；⛔ 規則拿不到就一律當敏感、維持轉人）。
    """
    # U2：兩道閘要拿得到規則集（⛔ 拿不到 ⇒ `None` ⇒ 一律當敏感、維持轉人）。
    _qs_rules = getattr(verifier, "rules", None)
    for _name, _gate in EXIT_GATES:
        result = _gate(result, agent_state, user_message, _qs_rules, acc.scope_counts)
    if result.outcome is None:
        result.outcome = default_outcome(result)
    # T1：三個寫點之一（模型迴圈的一般出口與所有固定句出口都經這裡）——
    # R3：`AgentSession.end_turn` 收斂本函式原本散寫的
    # `last_ask_target`／`handoff_cache`／`fixed_streak`／`dialog` 四鍵。
    # ⚠️ `ask_target` 讀的是**過完所有出口閘之後**的值：閘門可能把一個
    #    `kind=ask` 的追問對象歸零，殘留舊值等於讓下一回合的程式判定
    #    拿到一個這一回合根本沒有出去的授權訊號。T2（NO_JUDGEMENT）把
    #    `kind` 換成 `answer` 但仍設了合法的 `ask_target=
    #    "confirm_intent"`——⛔ 不再只認 `kind=="ask"`，改認
    #    `ask_target` 是否落在 `ASK_TARGETS` 值域內：其他 `kind` 的
    #    `ask_target` 一律是模型依 schema 填的 `None`，這條件對它們
    #    等價於原本的 `kind=="ask"` 判定。
    AgentSession(agent_state).end_turn(
        user_message=user_message,
        dialog_text=result.answer,
        ask_target=result.ask_target if result.ask_target in ASK_TARGETS else None,
        is_fixed=is_fixed,
        cache=cache if result.trace.final_kind == "handoff" else None,
        cache_key=acc.cache_key if result.trace.final_kind == "handoff" else None,
        cache_entry=(
            {
                "answer": result.answer,
                "handoff": result.handoff,
                "quick_replies": list(result.quick_replies),
                "trace_id": result.trace.trace_id,
            }
            if result.trace.final_kind == "handoff"
            else None
        ),
    )
    _emit_agent_decision(result.trace)
    return result
