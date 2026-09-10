"""unit：**文件回合禁用樣式**（Plan `inputs/plan-walkthrough-fixes-batch6-20260910.md` 單元 E｜line-bot #6／#3）。

病灶：文件歸納回合的回覆說「已把憑證掛到該戶既有的帳單上」（承諾一個做不到的寫入）、
「要我把這張憑證的資料存為系統帳單並匯入嗎？」（提議做不到的事）。規格：
**文件回合不寫回、不建單**，所以這兩種句式在該回合一律是承諾做不到的事。

治法在 Verifier 層、以**封閉詞表按「一類」維護**（`feedback_no_special_case_fixes`）：
規則檔 `document_turn_forbid_terms` 兩條正則＝(a) 完成式寫入宣稱、(b) 提議寫入；
`verify(..., document_turn=True)` 才跑。⛔ 不逐句特例、⛔ 不在提示詞寫例子。

本檔的六節（缺任一節，這個閘都可能是壞的而沒有人知道）：
0. 規則檔真的有這張表（正對照——否則下面的「沒被擋」全部沒有意義）；
1. **正向**：兩類各 ≥4 句真的被擋，且拒因是 `FORBIDDEN_TERM`（⛔ 不是別的步驟）；
2. **誤殺**：狀態詞（「已逾期」「已發送」…）≥3 句 ⛔ 不得被咬——正則要求動詞落在
   封閉表內，⛔ 不用裸「已」（那會把整個帳務語彙掃掉）；
3. **不溢出**：同一句在 `document_turn=False` 下放行（預設值行為逐位不變）；
4. **缺鍵不啟用**：規則檔沒這個鍵 ⇒ 整步不跑；
5. **觀察模式仍擋**：`FORBIDDEN_TERM` 屬機敏類，⛔ 不在 `_GROUNDING_OBSERVE_REASONS` 裡。

⚠️ 受測句一律做成「⑥' 之前每一步都會過」的形狀（純問句免引用；陳述句配一份**合格**
引用），否則句子先死在 ②，`ok=False` 照樣成立而本檔什麼都沒證明——那是假綠。
每條正向斷言因此都比對 `reason`，⛔ 不只比 `ok`。

離線、不接觸真 DB／真 LLM。
"""
import json
from pathlib import Path
from typing import Optional

import pytest

from services.agent.output_schema import AgentOutput, VerifierRules
from services.agent.provenance_units import resolve_refs
from services.agent.tools.registry import ToolResult
from services.agent.verifier import _GROUNDING_OBSERVE_REASONS, OutputVerifier

pytestmark = pytest.mark.unit

_RULES_PATH = Path(__file__).resolve().parents[3] / "config" / "agent_verifier_rules.json"
_NONCE = "FIXTURE0000000000"


@pytest.fixture(scope="module")
def rules() -> VerifierRules:
    return VerifierRules.load(_RULES_PATH)


@pytest.fixture(scope="module")
def verifier(rules: VerifierRules) -> OutputVerifier:
    return OutputVerifier(rules)


# ---------------------------------------------------------------- 受測句的兩種載體

def _pure_question(text: str) -> tuple[AgentOutput, dict]:
    """**純問句**載體：句尾是「？」、子句不含 `assertion_terms` ⇒ 步②免引用，
    ⑥' 之前每一步都過。適用於不含「可以／需要」等能力動詞的提議句。"""
    out = AgentOutput.model_validate({
        "kind": "ask",
        "sentences": [{"text": text, "kind": "question", "refs": []}],
        "fact_class": "other",
        "handoff_reason": None,
        "ask_target": "confirm_intent",
    })
    return out, {}


def _cited_fact(text: str, prov_text: str) -> tuple[AgentOutput, dict]:
    """**合格引用的事實句**載體：陳述句（以及含「可以／需要」而被步②降級成 fact
    的問句）沒辦法免引用，故給它一份真的過得了覆蓋／極性／可引用的引文。

    ⚠️ `prov_text` 刻意是**單一句**（不含中間句號）：`provenance_units` 依句末標點
    切片段，`§0` 只會是第一句——多句的話標記指到的就不是我們以為的那一段。"""
    out = AgentOutput.model_validate({
        "kind": "answer",
        "sentences": [
            {"text": text, "kind": "fact", "refs": [f"[{_NONCE}:t1:doc:receipt§0]"]}
        ],
        "fact_class": "other",
        "handoff_reason": None,
    })
    tool_results = {
        "t1": {
            "ok": True,
            "provenance": [{"source": "doc:receipt", "text": prov_text, "citable": True}],
            "text_for_model": "",
        }
    }
    return out, tool_results


def _verify(verifier: OutputVerifier, out: AgentOutput, tool_results: dict, *,
            document_turn: bool):
    """與產線同一條路：`resolve_refs` → `verify`。⛔ 不在本檔另寫一套引用解析。"""
    trs = {tid: ToolResult.model_validate(tr) for tid, tr in tool_results.items()}
    resolved, resolve_errors = resolve_refs(out, trs, _NONCE)
    return verifier.verify(
        out, trs, "這是我的繳費收據", None,
        resolved=resolved, resolve_errors=resolve_errors,
        document_turn=document_turn)


def _run(verifier: OutputVerifier, case: tuple[str, Optional[str]], *, document_turn: bool):
    text, prov = case
    out, trs = _cited_fact(text, prov) if prov else _pure_question(text)
    return _verify(verifier, out, trs, document_turn=document_turn)


def _ids(cases) -> list[str]:
    return [c[0][:8] for c in cases]


# ══════════════════════════════════════════════ 0. 規則檔載得到（正對照）

def test_rules_file_declares_both_classes():
    """正對照組：先確認規則檔真的有這張表、而且是**兩類各一條**。

    pydantic 白名單會**靜默忽略未宣告鍵**——`VerifierRules` 忘了宣告欄位時，規則檔
    加了鍵也讀不到，而那個失敗方向是「閘悄悄沒開」。這條把「表在不在」與「表咬不咬」
    分開報，不然第 1 節全紅時看不出是規則沒載到還是判定寫錯。"""
    rules = VerifierRules.load(_RULES_PATH)
    assert rules.version == "1.6.2"
    assert rules.document_turn_forbid_terms is not None, (
        "規則檔缺 `document_turn_forbid_terms`，或 `VerifierRules` 沒宣告這個欄位"
    )
    assert len(rules.document_turn_forbid_terms) == 2, "兩類：完成式寫入宣稱／提議寫入"


# ══════════════════════════════════════════════ 1. 正向：兩類各 ≥4 句被擋

#: (a) **完成式寫入宣稱**。陳述句 ⇒ 每句配一份合格引用。
_DONE_CLAIMS: list[tuple[str, Optional[str]]] = [
    ("已把憑證掛到該戶既有的帳單上。", "業者於後台核對後，才由專員把憑證掛到該戶既有的帳單上。"),
    ("已存成系統帳單。", "核對通過後由業者存成系統帳單。"),
    ("已建立一張對應的帳單。", "業者核對後會建立一張對應的帳單。"),
    ("已匯入這張收據的金額欄位。", "業者於後台匯入這張收據的金額欄位。"),
    ("已上傳附件到該筆帳單。", "業者於後台上傳附件到該筆帳單。"),
    ("已寫入備註欄。", "業者於後台寫入備註欄。"),
    ("憑證已經匯入系統帳單了。", "憑證已經匯入系統帳單了。"),   # 1.6.2：verifier P2-2「已經＋動詞」（無把／將）漏網；引文＝句子且 ≥10 字
    ("這筆資料已經寫入備註欄了。", "這筆資料已經寫入備註欄了。"),
]

#: (b) **提議寫入**。不含 `assertion_terms` 的走純問句；含「可以／需要」的會被步②
#: 降級成 fact，故改走合格引用載體（⛔ 不是因為它們比較不重要——是載體限制）。
_WRITE_OFFERS: list[tuple[str, Optional[str]]] = [
    ("要我把這張憑證的資料存為系統帳單並匯入嗎？", None),
    ("要不要我幫您建立一張帳單？", None),
    ("請提供要掛到的本月帳單編號或指定戶別，我就幫您掛上。",   # 1.6.1：改寫後的承諾句式（line-bot #3 第二版）
     "後台流程說明：請提供要掛到的本月帳單編號或指定戶別，我就幫您掛上，是業者端的用語。"),
    ("收到編號後我會把憑證附加到那張帳單。",
     "後台流程說明：收到編號後我會把憑證附加到那張帳單，是業者端的用語。"),
    ("要我把附件上傳到那筆修繕單嗎？", None),
    ("要不要我把這張收據附加到帳單上？", None),
    ("需要我把它匯入系統嗎？", "後台流程說明：需要我把它匯入系統嗎，是業者端的確認用語。"),
    ("我可以幫您把這張收據附加到帳單上嗎？",
     "後台流程說明：我可以幫您把這張收據附加到帳單上嗎，是業者端的確認用語。"),
]


@pytest.mark.parametrize("case", _DONE_CLAIMS, ids=_ids(_DONE_CLAIMS))
def test_done_write_claims_are_blocked_in_document_turn(verifier, case):
    verdict = _run(verifier, case, document_turn=True)
    assert verdict.ok is False
    assert verdict.reason == "FORBIDDEN_TERM", (
        f"{case[0]!r} 被擋在別的步驟（{verdict.model_dump()}）——那不是本閘的證據"
    )


@pytest.mark.parametrize("case", _WRITE_OFFERS, ids=_ids(_WRITE_OFFERS))
def test_write_offers_are_blocked_in_document_turn(verifier, case):
    verdict = _run(verifier, case, document_turn=True)
    assert verdict.ok is False
    assert verdict.reason == "FORBIDDEN_TERM", (
        f"{case[0]!r} 被擋在別的步驟（{verdict.model_dump()}）——那不是本閘的證據"
    )


def test_term_id_distinguishes_the_two_forbid_tables(verifier):
    """`FORBIDDEN_TERM` 現在有**兩張表**（全回合字面表 `forbid_terms`／文件回合正則表
    `document_turn_forbid_terms`）。term_id 不加基底的話 `rule#0` 指不出是哪一張，
    trace 反查就斷了（同 `_PAIR_TERM_ID_BASE` 的理由）。"""
    assert _run(verifier, _DONE_CLAIMS[0], document_turn=True).term_id == "rule#2000"
    assert _run(verifier, _WRITE_OFFERS[0], document_turn=True).term_id == "rule#2001"
    # 正對照：既有 `forbid_terms` 的編號**沒有**被推走（同 reason、不同表）。
    legacy = _run(verifier, ("終身保固嗎？", None), document_turn=True)
    assert legacy.reason == "FORBIDDEN_TERM" and legacy.term_id == "rule#0"


def test_verdict_carries_no_model_text(verifier):
    """拒因 ⛔ 不得攜帶原文——verdict 會落 `usage_events.decision_snapshot.agent`
    並由 trace 端點印出（2.6 security review P2）。"""
    verdict = _run(verifier, _WRITE_OFFERS[0], document_turn=True)
    dumped = json.dumps(verdict.model_dump(), ensure_ascii=False)
    assert "憑證" not in dumped and "匯入" not in dumped


# ══════════════════════════════════════════════ 2. 誤殺：狀態詞不得被咬

#: 文件回合裡**合法**的中性歸納句。重點是「已」後面接的是**狀態詞**而非寫入動詞——
#: 正則要求動詞落在封閉表內，⛔ 不用裸「已」。
#: ⚠️ 一律做成純問句：其他步驟因此不會有意見，唯一可能的拒因就是 ⑥'。
_NEUTRAL_IN_DOCUMENT_TURN: list[tuple[str, Optional[str]]] = [
    ("這張帳單已逾期了嗎？", None),
    ("通知已發送給房東了嗎？", None),
    ("款項已入帳了嗎？", None),
    ("這份合約已簽署了嗎？", None),
    ("這張收據已作廢了嗎？", None),
    ("付款方式是轉帳嗎？", None),
    ("要我幫您查一下這一期的繳費狀況嗎？", None),
    ("這張帳單已逾期，請上傳繳費收據好嗎？", None),
]


@pytest.mark.parametrize("case", _NEUTRAL_IN_DOCUMENT_TURN, ids=_ids(_NEUTRAL_IN_DOCUMENT_TURN))
def test_neutral_sentences_survive_the_document_turn_gate(verifier, case):
    """⚠️ 這一節量的是**誤殺**。最後兩句是刻意的邊界：
    「要我…查…嗎」是**讀取**（(b) 類只收寫入動詞，讀取類請求不得被連坐）；
    「已逾期，請上傳…」則是 (a) 類**處置式**分支的邊界——那個分支要求
    「已(經)把／將」開頭且不跨子句標點，所以狀態詞後面另起一句的「上傳」
    ⛔ 不得被連坐。這一條就是「處置式不要放成裸間隔」的量尺。"""
    verdict = _run(verifier, case, document_turn=True)
    assert verdict.reason != "FORBIDDEN_TERM", (
        f"{case[0]!r} 被文件回合閘誤殺——詞表太寬（{verdict.model_dump()}）"
    )
    assert verdict.ok is True, f"意外被別的步驟擋下：{verdict.model_dump()}"


# ══════════════════════════════════════════════ 3. 不溢出：非文件回合放行

@pytest.mark.parametrize("case", _DONE_CLAIMS + _WRITE_OFFERS,
                         ids=_ids(_DONE_CLAIMS + _WRITE_OFFERS))
def test_same_sentences_pass_outside_document_turn(verifier, case):
    """⛔ 這個閘只在文件回合開。同一句在確認卡／修繕建單回合是**正確的話**，
    預設 `document_turn=False` 必須逐位不變。少了這一節，⑥' 可能是「對所有回合都擋」
    而沒有人發現——那會誤殺寫入鏈的正常回覆。"""
    verdict = _run(verifier, case, document_turn=False)
    assert verdict.ok is True, f"非文件回合被誤擋：{verdict.model_dump()}"


def test_document_turn_defaults_to_false(verifier):
    """⚠️ **預設值就是既有行為**：不傳 `document_turn` 與傳 `False` 必須同判。
    第二波 B 才接線 Runtime，接線前產線一律走這條預設路徑。"""
    out, _ = _pure_question(_WRITE_OFFERS[0][0])
    resolved, resolve_errors = resolve_refs(out, {}, _NONCE)
    verdict = verifier.verify(
        out, {}, "這是我的繳費收據", None,
        resolved=resolved, resolve_errors=resolve_errors)
    assert verdict.ok is True


# ══════════════════════════════════════════════ 4. 缺鍵不啟用

def _rules_without_key(rules: VerifierRules) -> VerifierRules:
    data = rules.model_dump()
    data.pop("document_turn_forbid_terms", None)
    return VerifierRules(**data)


def test_missing_key_disables_the_gate(rules):
    """規則檔沒有 `document_turn_forbid_terms` ⇒ 整步不跑（舊規則檔行為一字不變）。

    ⚠️ 這一欄的缺鍵方向刻意是**不啟用**，與 `sensitive_patterns_audiences` 的
    「缺鍵＝全受眾＝照擋」**相反**：那一欄的舊行為是「掃」，這一欄的舊行為是
    「根本沒有這張表」。"""
    legacy_rules = _rules_without_key(rules)
    assert legacy_rules.document_turn_forbid_terms is None
    v = OutputVerifier(legacy_rules)
    assert _run(v, _WRITE_OFFERS[0], document_turn=True).ok is True, "缺鍵時不該啟用"
    # 正對照：同一把尺對**既有** `forbid_terms` 仍然咬得動——否則上面那個 `ok=True`
    # 可能只是因為整把尺壞了（規則物件建不起來、answer 空字串……）。
    legacy_hit = _run(v, ("終身保固嗎？", None), document_turn=True)
    assert legacy_hit.ok is False and legacy_hit.reason == "FORBIDDEN_TERM"


def test_empty_list_also_disables_the_gate(rules):
    """明寫 `[]`（「這條規則關掉」）與缺鍵在**行為上**同樣是不啟用。"""
    data = rules.model_dump()
    data["document_turn_forbid_terms"] = []
    v = OutputVerifier(VerifierRules(**data))
    assert _run(v, _WRITE_OFFERS[0], document_turn=True).ok is True


def test_broken_regex_fails_loud_at_construction(rules):
    """規則檔寫壞的正則要在**建構當下**炸（fail loud）——⛔ 不做「編譯失敗就跳過
    這條」的容錯，那個失敗方向是閘悄悄少一條而沒有人知道。"""
    data = rules.model_dump()
    data["document_turn_forbid_terms"] = ["已(掛|存"]
    import re as _re

    with pytest.raises(_re.error):
        OutputVerifier(VerifierRules(**data))


# ══════════════════════════════════════════════ 5. 觀察模式仍擋

def test_forbidden_term_is_not_in_the_grounding_observe_set():
    """對照 `_GROUNDING_OBSERVE_REASONS` 本身：`FORBIDDEN_TERM` 屬**機敏類**，
    ⛔ 不在觀察集合內。這條是下面那條行為測試的**成因**，兩條都要在——
    只有行為測試的話，哪天觀察集合被擴充，紅的會是行為測試而看不出原因。"""
    assert "FORBIDDEN_TERM" not in _GROUNDING_OBSERVE_REASONS


@pytest.mark.parametrize("mode", ["enforce", "grounding_observe"])
def test_document_turn_gate_still_blocks_under_grounding_observe(rules, mode):
    v = OutputVerifier(rules, mode=mode)
    verdict = _run(v, _WRITE_OFFERS[0], document_turn=True)
    assert verdict.ok is False
    assert verdict.reason == "FORBIDDEN_TERM"


def test_uncited_write_claim_is_blocked_even_when_citation_is_only_observed(rules):
    """⚠️ 這是本閘的**重點**，也是 line-bot #6 的真實形狀：真線上這種句子多半同時
    引用失敗；引用類在 `grounding_observe` 下被觀察放過之後，若 ⑥' 也降成觀察，
    就沒有人擋得住「已把憑證掛到帳單上」了。"""
    v = OutputVerifier(rules, mode="grounding_observe")
    out = AgentOutput.model_validate({
        "kind": "answer",
        "sentences": [{"text": "已把憑證掛到該戶既有的帳單上。", "kind": "fact", "refs": []}],
        "fact_class": "other",
        "handoff_reason": None,
    })
    verdict = _verify(v, out, {}, document_turn=True)
    assert verdict.ok is False
    assert verdict.reason == "FORBIDDEN_TERM"
    assert "UNCITED_ASSERTION" in verdict.observed, (
        "正對照：引用類確實被觀察放過了——否則本案擋下來的可能是引用而不是 ⑥'"
    )


# ══════════════════════════════════════════════ 6. 跨筆拆字規避

def test_split_across_sentences_is_still_caught(verifier):
    """⑥' 掃的是**拼接後的 `answer`**（同 ①⑤⑥⑦），⛔ 不是逐筆——
    把「要我」和「匯入」拆到兩筆躲不掉。

    ⚠️ 兩筆都做成**純問句**（句尾「？」）：否則先死在 ② `UNCITED_ASSERTION`，
    本測試就變成在測引用而不是在測拆字規避。"""
    out = AgentOutput.model_validate({
        "kind": "ask",
        "sentences": [
            {"text": "要我嗎？", "kind": "question", "refs": []},
            {"text": "匯入這張收據好嗎？", "kind": "question", "refs": []},
        ],
        "fact_class": "other",
        "handoff_reason": None,
        "ask_target": "confirm_intent",
    })
    verdict = _verify(verifier, out, {}, document_turn=True)
    assert verdict.ok is False
    assert verdict.reason == "FORBIDDEN_TERM"
