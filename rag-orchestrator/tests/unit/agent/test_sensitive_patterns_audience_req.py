"""unit：U3——答案側 `sensitive_patterns` 的**受眾範圍**
（Plan `inputs/plan-document-summary-demo-20260909.md` §U3／W9-11／W9-12／W9-17）。

被測的三件事：

1. **鍵真的被載入**：`VerifierRules` 是 pydantic 白名單模型，未宣告的鍵會被
   **靜默忽略**——規則檔加了 `sensitive_patterns_audiences` 卻讀不到，其失敗方向是
   「放寬沒生效」或「放寬全域生效」，兩種都不會有人發現。故本檔第一組測試是
   載入正對照（值來自檔案、不是程式預設）＋反對照（未宣告的鍵確實會被吃掉）。
2. **放寬的邊界**：規則檔 10 條樣式**逐條各一句**，同一句在三種受眾狀態下的判定——
   `property_manager` 放行／`prospect` 照擋／**沒給 audience** 照擋（fail-closed）。
   ⚠️ 逐條而不是只測金額：Plan 放寬的是**整張表**對 pm 的效力，只測金額等於沒測到
   `保證`／`金管會`／`資安法` 那幾條到底有沒有跟著放。
3. **⛔ 沒有溢出**：敏感五類（`fact_class ∈ SENSITIVE`）與問句側
   `question_sensitive_patterns` 不受 audience 影響——這兩道閘是另外兩件事。

離線、不接觸真 DB／真 LLM；一律用**出貨規則檔**（⛔ 不自造規則集，那樣測到的是
測試自己寫的表，不是線上那把尺）。
"""
from __future__ import annotations

import inspect
import json
import re

import pytest

from services.agent.output_schema import AgentOutput, VerifierRules
from services.agent.provenance_units import resolve_refs
from services.agent.question_sensitivity import question_sensitive
from services.agent.tools.registry import ToolResult
from services.agent.verifier import _FIXTURE_NONCE, OutputVerifier
from services.presales_gate import SENSITIVE

from tests.unit.agent.test_verifier_req import _RULES_PATH

_REQ = "knowledge-outline-and-intent-architecture:U3"

pytestmark = [pytest.mark.unit, pytest.mark.req(_REQ)]

#: 受眾值域來自 `identity.audience_of` 的決定性推導（封閉三值）；這裡只用得到兩個。
_PM = "property_manager"
_PROSPECT = "prospect"

#: 規則檔 `sensitive_patterns` **逐條各一句**，索引＝規則檔陣列索引。
#: ⚠️ 每一句都必須**只**命中自己那一條——`verify()` 回最先命中的那條，一句踩到兩條時
#: `term_id` 就對不回本表的索引，逐條斷言會退化成「其實只測到比較前面那條」。
#: 這件事由 `test_each_sentence_hits_exactly_its_own_pattern` 當正對照守住。
_ONE_SENTENCE_PER_PATTERN: tuple[str, ...] = (
    "本期電費金額為 4,249 元。",
    "本期滯納金比率為 2%。",
    "調整比率記為百分之20。",
    "保證金的收取方式列於合約第三條。",
    "個資法的相關說明列於合約附件。",
    "GDPR 的相關說明列於合約附件。",
    "ISO 27001 的驗證範圍列於合約附件。",
    "SOC 2 的稽核報告列於合約附件。",
    "金管會的相關說明列於合約附件。",
    "資安法的相關說明列於合約附件。",
)

#: 三個受眾狀態下都不該踩到樣式表的對照句（用來驗「放寬沒有把別的閘一起關掉」）。
_NEUTRAL_SENTENCE = "合約條款的內容請以正式文件為準。"


@pytest.fixture(scope="module")
def rules() -> VerifierRules:
    return VerifierRules.load(_RULES_PATH)


@pytest.fixture(scope="module")
def verifier(rules: VerifierRules) -> OutputVerifier:
    return OutputVerifier(rules)


def _verify(verifier: OutputVerifier, sentence: str, *, audience=None, fact_class="other"):
    """一句、有效引用的最小回合：引文＝句子本身 ⇒ 覆蓋／極性／可引用全過。

    這樣寫是刻意的：本檔要量的是①的敏感樣式那一關，其餘六關必須是**通的**，
    否則 pm 放行的斷言會被別的拒因掩蓋（看起來擋住了，其實擋的是引用不足）。
    `resolved`／`resolve_errors` 走系統的 `resolve_refs`，⛔ 不在測試裡另寫解析。
    """
    payload = {
        "kind": "answer",
        "sentences": [{
            "text": sentence,
            "kind": "fact",
            "refs": [f"[{_FIXTURE_NONCE}:t1:kb:9101§0]"],
        }],
        "fact_class": fact_class,
        "handoff_reason": None,
    }
    out = AgentOutput.model_validate(payload)
    tool_results = {
        "t1": ToolResult.model_validate({
            "ok": True,
            "provenance": [{"source": "kb:9101", "text": sentence, "citable": True}],
            "text_for_model": "",
        })
    }
    resolved, resolve_errors = resolve_refs(out, tool_results, _FIXTURE_NONCE)
    return verifier.verify(
        out, tool_results, "這份文件幫我看一下。", None,
        resolved=resolved, resolve_errors=resolve_errors, audience=audience)


# ─────────────────────────────────────────────── 1. 鍵真的被載入（(a)）

def test_rules_load_exposes_sensitive_patterns_audiences(rules):
    """出貨規則檔的 `sensitive_patterns_audiences` 要原封不動地到得了模型欄位。

    正對照：先確認**檔案裡真的有這個鍵**——否則下面的相等斷言可能只是
    「兩邊都缺」而恆成立。"""
    on_disk = json.loads(_RULES_PATH.read_bytes())

    assert "sensitive_patterns_audiences" in on_disk, (
        "規則檔沒有這個鍵 ⇒ 這組測試失去意義（正對照不成立）")
    assert rules.sensitive_patterns_audiences == on_disk["sensitive_patterns_audiences"]
    assert rules.sensitive_patterns_audiences == [_PROSPECT]


def test_value_comes_from_the_file_not_from_a_default(tmp_path, rules):
    """反證「其實是程式預設值恰好長這樣」：改檔案裡的值，載入結果必須跟著改。"""
    raw = json.loads(_RULES_PATH.read_bytes())
    raw["sensitive_patterns_audiences"] = ["tenant"]
    path = tmp_path / "rules_other_audience.json"
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    assert VerifierRules.load(path).sensitive_patterns_audiences == ["tenant"]
    # 出貨那份沒被動到
    assert rules.sensitive_patterns_audiences == [_PROSPECT]


def test_an_undeclared_key_really_is_swallowed_silently(tmp_path):
    """反對照：pydantic 白名單**確實**會靜默吃掉未宣告的鍵。

    沒有這條，上面兩條只證明「值對得上」，證明不了「**因為宣告了欄位**才讀得到」——
    而那正是這一類 bug（規則檔改了、程式讀不到、沒有人發現）的成因。"""
    raw = json.loads(_RULES_PATH.read_bytes())
    raw["sensitive_patterns_audiences_typo"] = ["prospect"]
    path = tmp_path / "rules_typo_key.json"
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    loaded = VerifierRules.load(path)
    assert not hasattr(loaded, "sensitive_patterns_audiences_typo")
    assert loaded.sensitive_patterns_audiences == [_PROSPECT]   # 正牌的那個仍在


# ─────────────────────────────────────────────── 2. 表本身沒被動到（驗收 3）

def test_sensitive_patterns_table_is_still_the_ten_the_plan_lists(rules):
    """驗收③：Plan 逐條列的條數＝規則檔陣列長度。⛔ 放寬受眾不得順手增刪樣式。"""
    assert len(rules.sensitive_patterns) == 10
    assert rules.sensitive_patterns == [
        r"\d+(?:\.\d+)?\s*(?:元|塊|萬|億|折)",
        r"\d+(?:\.\d+)?\s*%",
        r"百分之\d+",
        "保證",
        "個資法",
        "GDPR",
        r"ISO\s?27001",
        r"SOC\s?2",
        "金管會",
        "資安法",
    ]
    assert len(_ONE_SENTENCE_PER_PATTERN) == len(rules.sensitive_patterns), (
        "測試句數與規則檔條數脫節 ⇒ 逐條斷言會漏掉新加的樣式")


def test_each_sentence_hits_exactly_its_own_pattern(rules):
    """正對照：每一句只命中自己那一條。⛔ 沒有這條，下面的 `term_id` 逐條斷言
    可能只是「大家都先撞到第 0 條」。"""
    compiled = [re.compile(p) for p in rules.sensitive_patterns]
    for i, sentence in enumerate(_ONE_SENTENCE_PER_PATTERN):
        hits = [j for j, pat in enumerate(compiled) if pat.search(sentence)]
        assert hits == [i], (i, sentence, hits)
    # 中性句一條都不踩（下面「五類不受影響」那組要靠它把樣式表排除在外）
    assert not any(p.search(_NEUTRAL_SENTENCE) for p in compiled)


# ─────────────────────────────────────────────── 3. 逐條 × 三種受眾狀態（(b)(c)(d)）

@pytest.mark.parametrize("index", range(len(_ONE_SENTENCE_PER_PATTERN)))
def test_property_manager_is_not_blocked_by_any_of_the_ten_patterns(verifier, index):
    """(b) pm 受眾：10 條樣式各一句**皆放行**（放寬的是整張表，不是只有金額那條）。"""
    verdict = _verify(verifier, _ONE_SENTENCE_PER_PATTERN[index], audience=_PM)
    assert verdict.ok is True, (index, verdict.model_dump())


@pytest.mark.parametrize("index", range(len(_ONE_SENTENCE_PER_PATTERN)))
def test_prospect_is_still_blocked_by_every_pattern(verifier, index):
    """(c) prospect 受眾：同樣 10 句照擋，`term_id` 對得回規則檔索引。"""
    verdict = _verify(verifier, _ONE_SENTENCE_PER_PATTERN[index], audience=_PROSPECT)
    assert verdict.ok is False
    assert verdict.reason == "SENSITIVE_TOPIC"
    assert verdict.term_id == f"rule#{index}"


@pytest.mark.parametrize("index", range(len(_ONE_SENTENCE_PER_PATTERN)))
def test_missing_audience_is_fail_closed(verifier, index):
    """(d) 呼叫端沒給 audience ⇒ 照擋。

    `OutputVerifier` 是行程級單例、呼叫點不只一處；缺值若放行，任何一處忘了傳
    都會**靜默**關掉售前守門，而那個失敗方向沒有人會發現。"""
    verdict = _verify(verifier, _ONE_SENTENCE_PER_PATTERN[index])
    assert verdict.ok is False
    assert verdict.reason == "SENSITIVE_TOPIC"
    assert verdict.term_id == f"rule#{index}"


def test_audience_does_not_leak_into_the_verdict(verifier):
    """受眾是判定的輸入，⛔ 不得成為 verdict 的內容——verdict 會落
    `usage_events.decision_snapshot.agent`、也會被 trace 端點印出來。"""
    verdict = _verify(verifier, _ONE_SENTENCE_PER_PATTERN[0], audience=_PROSPECT)
    dumped = json.dumps(verdict.model_dump(), ensure_ascii=False)
    assert _PROSPECT not in dumped and _PM not in dumped


# ─────────────────────────────────────────────── 4. 缺鍵＝舊行為（(e)）

def test_missing_key_in_rules_file_blocks_every_audience(tmp_path):
    """(e) 規則檔沒有 `sensitive_patterns_audiences` ⇒ **全受眾**照擋（本欄位出現
    以前的行為）。⛔ 缺鍵不是「關掉這張表」——那個方向會讓舊規則檔一上線就整張守門消失。"""
    raw = json.loads(_RULES_PATH.read_bytes())
    assert "sensitive_patterns_audiences" in raw, "正對照：要拿掉的鍵本來就不在，這條沒測到東西"
    raw.pop("sensitive_patterns_audiences")
    path = tmp_path / "rules_1_4_1_shape.json"
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    legacy = VerifierRules.load(path)
    assert legacy.sensitive_patterns_audiences is None
    legacy_verifier = OutputVerifier(legacy)

    for index, sentence in enumerate(_ONE_SENTENCE_PER_PATTERN):
        verdict = _verify(legacy_verifier, sentence, audience=_PM)
        assert verdict.ok is False, (index, verdict.model_dump())
        assert verdict.reason == "SENSITIVE_TOPIC"
    # 正對照：同一份舊形狀規則檔，中性句仍放行（⛔ 不是「什麼都擋」）
    assert _verify(legacy_verifier, _NEUTRAL_SENTENCE, audience=_PM).ok is True


# ─────────────────────────────────────────────── 5. ⛔ 沒有溢出（(f)(g)）

@pytest.mark.parametrize("audience", [_PM, _PROSPECT, None])
@pytest.mark.parametrize("fact_class", sorted(fc.value for fc in SENSITIVE))
def test_sensitive_fact_classes_are_untouched_by_audience(verifier, audience, fact_class):
    """(g) 敏感五類是**另一道閘**（`fact_class ∈ SENSITIVE`），⛔ 不受 audience 影響。

    句子刻意用一條樣式都不踩的中性句，且斷言 `term_id is None`——樣式表命中一定會
    填 `term_id`，沒有它才證明這個 `SENSITIVE_TOPIC` 來自五類分支而不是樣式表。"""
    verdict = _verify(verifier, _NEUTRAL_SENTENCE, audience=audience, fact_class=fact_class)
    assert verdict.ok is False
    assert verdict.reason == "SENSITIVE_TOPIC"
    assert verdict.term_id is None


@pytest.mark.parametrize("audience", [_PM, _PROSPECT, None])
def test_non_sensitive_fact_class_with_neutral_sentence_passes(verifier, audience):
    """上面那組的正對照：同一句換成非敏感 `fact_class` ⇒ 三種受眾狀態全放行。
    沒有它，「五類照擋」可能只是這句話本身過不了別的關。"""
    assert _verify(verifier, _NEUTRAL_SENTENCE, audience=audience).ok is True


def test_question_side_patterns_are_out_of_scope(rules):
    """(f) 問句側 `question_sensitive_patterns` **不在本次範圍**：表沒動、判定不吃受眾。"""
    on_disk = json.loads(_RULES_PATH.read_bytes())["question_sensitive_patterns"]
    assert len(on_disk) == len(SENSITIVE) == 5
    assert rules.question_sensitive_patterns == on_disk

    # 判定函式的簽章裡根本沒有受眾這個維度（⛔ 不是「有但沒用」）
    assert list(inspect.signature(question_sensitive).parameters) == ["message", "rules"]
    # 真值表正反對照：售前價格題仍判敏感、物管帳單題仍判非敏感
    assert question_sensitive("你們的報價是多少？", rules) is True
    assert question_sensitive("這張電費單的金額怎麼看？", rules) is False
