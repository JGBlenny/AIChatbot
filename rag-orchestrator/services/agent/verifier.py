"""`OutputVerifier`（spec agentic-mcp-orchestration・任務 2.3，design.md 元件 6）。

七步順序（全部通過才放行；第一個踩到的違規決定 `VerifierVerdict.reason`）：
①敏感五類 ②白名單句型（逐筆結構檢查＋逐片段「純」條件降級） ③覆蓋＋極性
④來源可引用 ⑤導流白名單 ⑥禁詞 ⑥'文件回合禁用樣式 ⑦handoff 詞後置掃描。

**文件回合（第六批單元 E）**：`verify(..., document_turn=True)` 才多跑 ⑥'——
文件歸納回合 ⛔ 不寫回、⛔ 不建單，故「已把憑證掛到帳單上」（完成式寫入宣稱）與
「要我存成系統帳單並匯入嗎？」（提議寫入）在該回合一律是承諾做不到的事。
預設 `False`＝**逐位不變**；⛔ 不在此改既有 `forbid_terms` 的語義。

**DSP-028：②③④的量測單位是「筆」與「片段」，①⑤⑥⑦的量測單位是拼接後的 `answer`**
——後者是安全側（掃的字串就是送出去的字串），跨筆拆數字／拆禁詞的規避靠它擋。

**受眾（U3）**：`verify(..., audience=)` 只決定①的**後半**（`sensitive_patterns`
那張樣式表）要不要掃——規則檔的 `sensitive_patterns_audiences` 宣告它對哪些受眾生效，
缺值一律照擋。①的**前半**（`fact_class in SENSITIVE` 敏感五類）與②～⑦⛔ 不受受眾影響。

**模式（W6-b3）**：`OutputVerifier.mode` 決定每一類違規是「照擋」還是「只記錄到
`VerifierVerdict.observed`、繼續往下跑」——⛔ 模式感知只在本檔，外層⛔ 不得翻判定。

**只 import `presales_gate`／`conversational_config`**（design 元件 6 收尾一句）：
`SENSITIVE`、`FactClass`、`HANDOFF_WORDS`、`scan_handoff_mentions` 來自 `services.presales_gate`，
⛔ 不複製這些封閉集合到本檔——那樣兩處會各自演化、對不上。
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Optional, get_args

from services.agent.identity import Audience as _Audience
from services.agent.output_schema import (
    ASK_TARGETS,
    AgentOutput,
    Sentence,
    VerifierRules,
    VerifierVerdict,
)
from services.agent.provenance_units import (  # 葉模組：切句與 refs 解析（DSP-029 落地取捨④）
    _SENTENCE_ENDS,
    ResolvedRef,
    _split_sentences,
    split_sentences,
)
from services.agent.tools.registry import ToolResult
from services.presales_gate import FactClass, HANDOFF_WORDS, HandoffReason, SENSITIVE, scan_handoff_mentions

#: U3／W9-11：`verify(audience=)` 的**封閉值域**——直接讀 `identity.Audience`
#: 那份 `Literal`，⛔ 不在本檔另抄一份字串集合。值域外的字串一律視同缺值
#: （＝照擋，見 `_sensitive_patterns_apply`）。
KNOWN_AUDIENCES: frozenset = frozenset(get_args(_Audience))

#: 「純」條件切子句用的封閉分隔詞（design：逗號／頓號／分號）。
_CLAUSE_SEPS: tuple[str, ...] = ("，", ",", "、", "；", ";")
#: 句末標點（拆片段用，⛔ 與 `presales_gate._sentences` 各自維護——那邊是決策層私有符號，
#: 這裡是 verifier 自己拆句做 schema 覆蓋檢查，兩處標點集合恰好同源純屬巧合，不是耦合）。
#: 問句結尾標記（NFKC 後判定）。
_QUESTION_ENDS: tuple[str, ...] = ("？", "?")
#: 問候詞封閉表（結構判定用，非業務可調規則，故不放進 `VerifierRules`）。
_GREETING_PHRASES: frozenset[str] = frozenset({
    "您好", "你好", "嗨", "哈囉", "早安", "午安", "晚安",
    "謝謝", "謝謝您", "不客氣", "感謝您的詢問", "很高興為您服務", "您好，很高興為您服務",
})
#: DSP-029a：資料段片段標記 `[{nonce}:{tool_call_id}:{source}§{i}]` 的樣式。模型把它
#: 抄進回覆就是 `SCHEMA(marker_in_answer)`——那既是把系統的內部標記漏給使用者，也是
#: 「引文由系統解析」這條契約被繞過的訊號（模型在自己造引用外觀）。
#: ⚠️ 掃的是 **NFKC 後**的 `answer`：全形括號在 NFKC 會折回半形，靠字形躲不掉。
#: ⚠️ 三段式與 `provenance_units._REF_RE` 是同一個格式的兩個用途（掃描 vs 解析），
#: ⛔ 改一邊就要改另一邊；`tests/unit/agent/test_prompt_assembler_req.py` 有兩側對齊測試。
_UNIT_MARKER_RE = re.compile(r"\[[0-9A-Za-z]{8,64}:[^\]\s:]+:[^\]\s]+§\d+\]")
#: URL／電話樣式（結構偵測用；是否在白名單由 `VerifierRules.allowed_routes` 決定）。
_URL_RE = re.compile(r"https?://[\w\-./%?=&#]+", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?:\+?886[-\s]?)?0?9\d{2}[-\s]?\d{3}[-\s]?\d{3}|0\d{1,2}[-\s]?\d{3,4}[-\s]?\d{4}")
#: 中文停用字元（覆蓋比對用，字元集合而非詞集合——design「非停用詞字元交集」）。
_STOPWORD_CHARS: frozenset[str] = frozenset(
    "的了是在和與及或也就都而那這裡呢嗎啊喔吧著得地之其以為對把被讓很更最還再只才又並且但不過跟給向由於"
    "自從至到中內外上下前後左右一二三四五六七八九十百千萬個件次回種類項筆條款號碼元請問您我們你妳他她它我"
    "會能可以不沒要想要有將已經正在此該些每各另同樣如若則便即使雖然雖是但是所以因為雖說然而不管無論"
    "，,。.！!？?、；;：:（(）)「」『』【】\"'\n\t "
)


def _nfkc(text: Optional[str]) -> str:
    return unicodedata.normalize("NFKC", text or "")



def _split_clauses(sentence: str) -> list[str]:
    pattern = "|".join(re.escape(sep) for sep in _CLAUSE_SEPS)
    parts = re.split(pattern, sentence)
    return [p for p in parts if p.strip()]


def _meaningful_chars(text: str) -> set[str]:
    return {ch for ch in _nfkc(text) if ch not in _STOPWORD_CHARS}


def _rule_id(index: int) -> str:
    """`VerifierVerdict.term_id` 的**唯一**形式：`rule#<規則集內索引>`。

    2.6 前置 security review P2：原本這裡填的是**字面詞／regex 本身**
    （`pattern.pattern`／`term`），而 verdict 會被 `_emit_agent_decision` 落進
    `usage_events.decision_snapshot.agent`、也會由 2.7 的 trace 端點印出來
    ⇒ 等於把「我們在擋什麼」逐字外洩（敏感樣式、禁詞表、否定詞表）。

    改存索引後，`(reason, term_id)` 兩者合起來才定位得到規則——`reason` 決定
    查哪一張表（`SENSITIVE_TOPIC`→`sensitive_patterns`、`FORBIDDEN_TERM`→
    `forbid_terms`、`POLARITY_MISMATCH`→`negation_terms`），`term_id` 是該表內
    的 0-based 索引；再配上同一份 trace 裡的 `rules_sha` 才對得回具體規則集
    版本。⛔ 索引**不跨表全域編號**：那需要固定表的串接順序，規則集加一張表
    就會讓歷史 trace 的編號整批漂掉。

    ⚠️ 一個 `reason` 對到**不只一張表**時，第二張起要加**基底**（同
    `_PAIR_TERM_ID_BASE` 的作法）——`FORBIDDEN_TERM` 現在有 `forbid_terms`
    與 `document_turn_forbid_terms` 兩張，不加基底的話 `rule#0` 指不出是哪一張。
    """
    return f"rule#{index}"


#: W6-b3：`AGENT_VERIFIER_MODE` 的值域。**解析（含相容舊旗）唯一在
#: `services.agent.health.verifier_mode()`**，⛔ 本檔不讀 env——尺不自己決定要不要開；
#: 模式由組裝端（`app._wrap_verifier_observe_only`）交進來。
VERIFIER_MODES: tuple[str, ...] = ("enforce", "grounding_observe", "observe_only")
DEFAULT_VERIFIER_MODE = "enforce"

#: `grounding_observe` 的**觀察類**（DSP-040／W6-b3）＝「引用解析與涵蓋」這一族。
_GROUNDING_OBSERVE_REASONS: frozenset[str] = frozenset({
    "UNCITED_ASSERTION", "QUOTE_TOO_SHORT", "QUOTE_NOT_COVERING", "SOURCE_NOT_CITABLE",
})
#: ⚠️ `SCHEMA` 是**共用拒因**，⛔ 不得整類觀察（plan-verifier r2 #1）：只有這四個
#: 「引用解析失敗」子成因觀察；`marker_in_answer`（標記外洩）／`handoff_reason_invalid`
#: ／`handoff_reason_mismatch`（S4 敏感配對，U2 的准入建立在它之上）／`ask_target_invalid`
#: ／`empty_*` 都是安全或契約子成因，**照擋**。
_GROUNDING_OBSERVE_SCHEMA_CAUSES: frozenset[str] = frozenset({
    "ref_invalid", "ref_source_not_found", "ref_ambiguous", "unit_out_of_range",
})

#: `negation_status_pairs` 的 `term_id` 基底。`TERM_ID_PATTERN` 只認 `rule#<十進位>`，
#: 而 `POLARITY_MISMATCH` 現在有**兩張表**（裸詞 `negation_terms`／主題錨定 pairs），
#: 索引不加基底就會撞在一起（`rule#3` 指不出是哪一張）。⛔ 不改 `TERM_ID_PATTERN`：
#: 那會讓既有 trace 的 term_id 形狀多一種，消費端要一起改。
_PAIR_TERM_ID_BASE = 1000


def _pair_rule_id(index: int) -> str:
    """`negation_status_pairs` 第 `index` 筆的 `term_id`（＝`rule#{1000+index}`）。"""
    return _rule_id(_PAIR_TERM_ID_BASE + index)


#: `document_turn_forbid_terms` 的 `term_id` 基底（同 `_PAIR_TERM_ID_BASE` 的理由）：
#: `FORBIDDEN_TERM` 現在有兩張表（全回合字面表 `forbid_terms`／文件回合正則表），
#: 索引不加基底 `rule#0` 會撞在一起，trace 反查不出被擋的是哪一條規則。
#: ⛔ 不改 `TERM_ID_PATTERN`：形狀仍是 `rule#<十進位>`，消費端不用動。
_DOC_TURN_TERM_ID_BASE = 2000


def _doc_turn_rule_id(index: int) -> str:
    """`document_turn_forbid_terms` 第 `index` 筆的 `term_id`（＝`rule#{2000+index}`）。"""
    return _rule_id(_DOC_TURN_TERM_ID_BASE + index)


#: fixture 案內未指定 `nonce` 時的缺省值（`_assert_all` 用）。⛔ 只給 fixture／自證用，
#: 產線 nonce 一律來自 `prompt_assembler.new_nonce()`——固定值在真線路上等於沒有 nonce。
_FIXTURE_NONCE = "FIXTURE0000000000"


def _is_legal_fact_class(value: Optional[str]) -> bool:
    return isinstance(value, str) and value in {fc.value for fc in FactClass}


class OutputVerifier:
    """`mode`（W6-b3）：`enforce`（預設、全部照擋）／`grounding_observe`（引用解析與
    涵蓋類只記錄、其餘照擋）／`observe_only`（全部只記錄＝舊 `AGENT_VERIFIER_OBSERVE_ONLY`
    的語義）。

    ⚠️ **模式感知在 `verify()` 內部**（security-reviewer r1 F1）：外層包一層把
    `ok=False` 翻成 `ok=True` 的作法會讓短路後的機敏類**根本沒跑**——先命中的引用類
    直接 return，`SENSITIVE_TOPIC`／`ROUTE_NOT_ALLOWED`／`FORBIDDEN_TERM` 連看都沒看過，
    翻完的 `ok=True` 因此不代表「機敏類通過」。
    """

    def __init__(self, rules: VerifierRules, *, mode: str = DEFAULT_VERIFIER_MODE):
        self.rules = rules
        self._sensitive_patterns = [re.compile(p) for p in rules.sensitive_patterns]
        #: 文件回合禁用樣式（單元 E）。規則檔缺鍵 ⇒ `None` ⇒ 空表 ⇒ ⑥' 整步不跑。
        #: ⚠️ 樣式在**建構當下**編譯：規則檔寫壞的正則要在啟動就炸（fail loud），
        #: ⛔ 不做「編譯失敗就跳過這條」的容錯——那個失敗方向是**閘悄悄少一條**。
        self._document_turn_forbid = [
            re.compile(p) for p in (rules.document_turn_forbid_terms or [])
        ]
        self._mode = DEFAULT_VERIFIER_MODE
        self.mode = mode

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str) -> None:
        """⛔ 值域外一律 raise（fail loud）：打錯字若靜默落回某個模式，可能是**整把尺
        關掉**，而那個失敗方向沒有人會發現。env 端的容錯（未知值 ⇒ enforce）在
        `health.verifier_mode()`，那是**解析**；這裡是**設定**。"""
        if value not in VERIFIER_MODES:
            raise ValueError(
                f"OutputVerifier.mode 只認 {VERIFIER_MODES}，收到 {value!r}"
            )
        self._mode = value

    def _sensitive_patterns_apply(self, audience: Optional[str]) -> bool:
        """這一回合要不要跑 `sensitive_patterns`（U3／W9-11、W9-12）。

        四個 **套用**（＝照擋）條件，任一成立即掃：
        1. `rules.sensitive_patterns_audiences is None`——規則檔沒宣告受眾，
           語義是**全受眾**（本欄位出現以前的行為），⛔ 不是「沒宣告就關掉」；
        2. `audience is None`——呼叫端沒給受眾。`OutputVerifier` 是行程級單例、
           呼叫點不只一處，任何一處忘了傳都不得**靜默**關掉售前守門，
           故缺值的方向是照擋而不是放行；
        3. `audience` **不在 `identity.Audience` 的封閉值域內**——「未知」與
           「缺值」是同一件事（W9-11 逐字：缺／未知 ⇒ 照擋）。⚠️ 少了這一條，
           呼叫端傳一個沒推導過的字串（例如 `target_user` 原值 `"system_admin"`、
           或任何打錯的字）會落進「有值但不在清單內」⇒ **跳過整張樣式表**，
           而那正是 fail-open：守門被一個拼字錯誤關掉，且沒有任何徵兆；
        4. `audience` 在規則檔宣告的清單內。

        只有「規則檔有宣告清單 **且** `audience` 是封閉值域內的值 **且** 不在
        清單內」才跳過。

        ⚠️ 這裡放寬的是**整張樣式表**對該受眾的效力，⛔ 不是逐條豁免，也⛔ 不看
        這一句有沒有引用資料段——豁免若由引用行為決定，等於把開關交給模型的引用，
        而引用標記正是文件線可被誘導的東西（W9-17）。
        ⚠️ 敏感五類（`fact_class in SENSITIVE`）與問句側 `question_sensitive_patterns`
        ⛔ 不受本判定影響：那是另外兩道閘，各自有各自的值域。
        ⚠️ `audience` 的值域來自 `identity.Audience` 的決定性推導（封閉三值）。
        本檔以 `typing.get_args(identity.Audience)` **讀那一份**，⛔ 不另抄一份
        集合——抄一份的失敗方向是「那邊加了受眾、這邊沒跟上」，而症狀是新受眾
        被當成未知值一路照擋（或反過來，取決於誰先漂），兩者都不會有徵兆。
        `services.agent.identity` 只 import `dataclasses`／`typing`，⛔ 不會與
        本檔既有的 `presales_gate`／`output_schema` 形成循環。
        """
        return self._audience_scope_applies(self.rules.sensitive_patterns_audiences, audience)

    def _route_check_apply(self, audience: Optional[str]) -> bool:
        """這一回合要不要跑 ⑤ 導流白名單（`ROUTE_NOT_ALLOWED`）——語義與
        `_sensitive_patterns_apply` 完全相同（W9 情境①：售前 CTA 守門對 pm 引資料段的
        交易序號誤殺），規則鍵 `route_check_audiences`。"""
        return self._audience_scope_applies(self.rules.route_check_audiences, audience)

    @staticmethod
    def _audience_scope_applies(declared: Optional[list], audience: Optional[str]) -> bool:
        """受眾範圍制的共用判定（四個套用條件見 `_sensitive_patterns_apply` docstring）。"""
        if declared is None:
            return True
        if audience is None:
            return True
        # W9-11（U3 收尾）：值域外＝未知 ⇒ 視同缺值＝照擋。
        if audience not in KNOWN_AUDIENCES:
            return True
        return audience in declared

    def _is_observed(self, verdict: VerifierVerdict) -> bool:
        """這個違規在目前模式下是「只記錄」還是「照擋」。⛔ 以**拒因＋子成因**界定，
        不是整個 `SCHEMA` 一起（見 `_GROUNDING_OBSERVE_SCHEMA_CAUSES`）。"""
        if self._mode == "enforce":
            return False
        if self._mode == "observe_only":
            return True
        if verdict.reason in _GROUNDING_OBSERVE_REASONS:
            return True
        # 2026-09-09 誤殺量測（smoke-rag 一輪 98 句）：裸詞表極性命中 12、幾乎全是引文側
        # 含否定詞或多 ref 一側缺否定詞的假陽性 ⇒ `grounding_observe` 下裸詞極性降為
        # 觀察類；主題錨定 pair（兩側都有狀態詞才算）沒有誤殺，照擋。
        if verdict.reason == "POLARITY_MISMATCH" and verdict.polarity_source == "term":
            return True
        return (
            verdict.reason == "SCHEMA"
            and verdict.schema_cause in _GROUNDING_OBSERVE_SCHEMA_CAUSES
        )

    @staticmethod
    def _observed_key(verdict: VerifierVerdict) -> str:
        if verdict.reason == "SCHEMA" and verdict.schema_cause:
            return f"SCHEMA:{verdict.schema_cause}"
        if verdict.reason == "POLARITY_MISMATCH" and verdict.polarity_source:
            return f"POLARITY_MISMATCH:{verdict.polarity_source}"
        return verdict.reason or "UNKNOWN"

    # ------------------------------------------------------------------
    def verify(
        self,
        out: AgentOutput,
        tool_results: dict[str, ToolResult],
        user_message: str,
        handoff: Optional[dict],
        *,
        resolved: dict[tuple[int, int], ResolvedRef],
        resolve_errors: dict[tuple[int, int], str],
        audience: Optional[str] = None,
        document_turn: bool = False,
    ) -> VerifierVerdict:
        """`resolved`／`resolve_errors` 由**呼叫端**（Runtime／`self_test`）以
        `services.agent.provenance_units.resolve_refs` 算好傳進來，鍵是
        `(筆索引, ref 索引)`（DSP-029a）。

        ⚠️ 兩者刻意是**必填關鍵字參數、⛔ 無預設值**（r13 F-A）：解析後的引文
        ⛔ 不掛在 `AgentOutput`／`Sentence` 上，所以 Verifier 沒有別的地方拿得到它；
        給預設值等於允許「忘了傳 ⇒ 引用檢查靜靜失去比對對象」，而那個失敗方向是放行。

        `audience`（U3）：本回合的受眾（`identity.resolved_audience()` 的值）。
        **只影響 `sensitive_patterns` 這一張表要不要掃**（見
        `_sensitive_patterns_apply`），⛔ 不影響敏感五類、極性、引用、導流、禁詞、
        handoff 任何一步。⚠️ 刻意**有預設值 `None`**、且 `None` 的方向是**照擋**：
        呼叫點不只一處，忘了傳的失敗方向必須是「多擋」而不是「少擋」。

        ⚠️ `tool_results` 在 DSP-029a 之後**本方法已不再讀它**——來源的 `citable`
        旗標隨 `ResolvedRef` 一起傳進來，⛔ 不再於此二次查表（兩處各查一次就會出現
        「解析用 A 筆 provenance、可引用旗標讀到 B 筆」的分歧）。參數保留是刻意的：
        它是 design 元件 6 的介面契約，Runtime／測試都以這個形狀對接。

        `document_turn`（單元 E）：本回合是不是**文件歸納回合**（使用者傳了文件、
        系統只做擷取與歸納）。⛔ 只加開步 ⑥'（`document_turn_forbid_terms`），
        ⛔ 不影響其他任何一步、也 ⛔ 不改 `forbid_terms` 的語義。
        ⚠️ 預設 `False` 的方向是**少擋**——與 `audience` 相反，理由是這張表的內容
        （「已建立」「要我匯入嗎」）在**一般寫入回合是正確的話**，缺值就照擋會把
        確認卡與修繕建單的正常回覆整批誤殺。判「這回合是不是文件回合」的責任因此
        在呼叫端（Runtime／第二波 B 接線），⛔ 不由這把尺自己猜。
        """
        observed: list[str] = []

        def _hit(verdict: VerifierVerdict):
            """一次違規的**去向**：觀察類 ⇒ 記進 `observed`、回 `None`（呼叫端**繼續**跑
            後面的類）；照擋類 ⇒ 回傳該 verdict（呼叫端立刻 return）。
            ⛔ 呼叫端不得忽略回傳值——忽略＝把照擋類降級成觀察類。"""
            if self._is_observed(verdict):
                key = self._observed_key(verdict)
                if key not in observed:
                    observed.append(key)
                return None
            verdict.observed = list(observed)
            return verdict

        def _pass() -> VerifierVerdict:
            return VerifierVerdict(ok=True, observed=list(observed))

        # ① 敏感五類（fail-closed：缺／非法一律視為敏感）
        if not _is_legal_fact_class(out.fact_class):
            hit = _hit(VerifierVerdict(ok=False, reason="SENSITIVE_TOPIC"))
            if hit is not None:
                return hit
            # 觀察（只可能是 `observe_only`）：`fact_class` 不合法時後面每一步都沒有依據
            # 可跑（`FactClass(...)` 會丟 ValueError）⇒ 就地放行，語義與舊外層旗相同。
            return _pass()
        fact_class = FactClass(out.fact_class)
        # DSP-021：`kind=handoff` 是敏感五類**應走**的出口——fact_class ∈ SENSITIVE 在
        # 這裡是正確標記，⛔ 不拒；`handoff_reason` 必須在 `HandoffReason` 值域內
        # （模型曾回自由文字「敏感主題」）。模型的 `answer` 文字不會到使用者手上
        # （Runtime 換成 `effective_handoff_message` 固定句），故 ②～⑦ 不對它跑。
        # 影子 2026-09-05：模型正確改轉人卻因逐句標籤留空被 ② 判 SCHEMA、
        # 兩拒耗盡 ⇒ 每個敏感題都多花兩次模型呼叫、reason 誤記 budget_exhausted。
        # DSP-028：handoff 時 `sentences` **允許留空**（也允許是模型自己寫的捏造文字）
        # ——那段文字不會到使用者手上，②(a) 的空陣列 SCHEMA 因此只對非 handoff 生效。
        if out.kind == "handoff":
            if out.handoff_reason not in {r.value for r in HandoffReason}:
                hit = _hit(VerifierVerdict(
                    ok=False, reason="SCHEMA", schema_cause="handoff_reason_invalid"))
                if hit is not None:
                    return hit
            # F1：敏感五類必須配 sensitive_no_grounding——把「敏感類配敏感原因」從
            # 提示詞承諾升格為 schema 驗證，對所有回合一體適用（S4 §5）。
            # ⚠️ `elif`：`handoff_reason` 不合法時這條沒有依據可判（維持舊順序）。
            elif fact_class in SENSITIVE and out.handoff_reason != "sensitive_no_grounding":
                hit = _hit(VerifierVerdict(
                    ok=False, reason="SCHEMA", schema_cause="handoff_reason_mismatch"))
                if hit is not None:
                    return hit
            return _pass()
        if fact_class in SENSITIVE:
            hit = _hit(VerifierVerdict(ok=False, reason="SENSITIVE_TOPIC"))
            if hit is not None:
                return hit
        answer_nfkc = _nfkc(out.answer)
        # U3：這張表只對規則檔宣告的受眾生效（缺值＝照擋，見 `_sensitive_patterns_apply`）。
        # ⚠️ 上面那條 `fact_class in SENSITIVE` 在**這個判定之外**，⛔ 不受受眾影響。
        if self._sensitive_patterns_apply(audience):
            for i, pattern in enumerate(self._sensitive_patterns):
                if pattern.search(answer_nfkc):
                    hit = _hit(VerifierVerdict(
                        ok=False, reason="SENSITIVE_TOPIC", term_id=_rule_id(i)))
                    if hit is not None:
                        return hit
                    break  # 觀察：同一類記一次就夠，⛔ 不把整張敏感樣式表逐條掃出來

        # ①' DSP-029 r13 #2：答案裡出現片段標記樣式 ⇒ SCHEMA(marker_in_answer)。
        # 契約寫「步⑥前」，這裡取**最早**的合法位置（①之後、②之前），⛔ 不是放寬：
        # ⚠️ 放在③之後它會變成**不可達的死檢查**——標記字串（16 位十六進位＋來源＋
        # 編號）帶進來的字元在來源原文裡一個都不存在，於是相對覆蓋率一定先判
        # QUOTE_NOT_COVERING，marker_in_answer 永遠輪不到。一條永遠不會觸發的安全
        # 檢查比沒有更糟（它讓人以為這個出口被守著）。量測單位與①⑤⑥⑦同為拼接後的
        # `answer`——掃的字串就是送出去的字串。
        if _UNIT_MARKER_RE.search(answer_nfkc):
            hit = _hit(VerifierVerdict(
                ok=False, reason="SCHEMA", schema_cause="marker_in_answer"))
            if hit is not None:
                return hit

        # ①-b T1（Plan `inputs/plan-walkthrough-fixes-batch2-20260909.md` §2）：
        # 追問契約——`kind=ask` 的**追問對象**必須是 `ASK_TARGETS` 值域內的一項。
        # ⚠️ 排在敏感三關（①fact_class／敏感樣式）**之後**：敏感題就算 `ask_target`
        #    也填錯，該回的仍是 `SENSITIVE_TOPIC`——把它降級成 SCHEMA 等於用一個
        #    格式問題蓋掉一個內容問題，失敗方向不對。
        # ⚠️ `ask_target` 缺（None）與填了值域外的字串是**同一種病**（追問對象不明），
        #    ⛔ 不分兩個成因：模型端的修法完全一樣（改填值域內的一項）。
        if out.kind == "ask" and out.ask_target not in ASK_TARGETS:
            hit = _hit(VerifierVerdict(
                ok=False, reason="SCHEMA", schema_cause="ask_target_invalid"))
            if hit is not None:
                return hit

        # ② 逐筆 schema 檢查（DSP-028 (a)(b)(c)）——⛔ 不再比對「句數＝標籤數」：
        # 文字與標籤同筆攜帶後，拼接相等是定義，不是要靠檢查維持的巧合。
        # (a) 非 handoff 卻沒有任何一筆 ⇒ 沒有東西可以驗，一律 SCHEMA
        #     （handoff 在上面已 return，走不到這裡）。
        if not out.sentences:
            hit = _hit(VerifierVerdict(
                ok=False, reason="SCHEMA", schema_cause="empty_sentences"))
            if hit is not None:
                return hit
            return _pass()  # 觀察：沒有筆 ⇒ 逐筆檢查無物可跑
        # (b) 任一筆 text 全空白 ⇒ SCHEMA（空筆會讓「每個字都屬於某一筆」失去意義）。
        for i, sentence in enumerate(out.sentences):
            if sentence.text.strip() == "":
                hit = _hit(VerifierVerdict(
                    ok=False, reason="SCHEMA", schema_cause="empty_text", sent=i))
                if hit is not None:
                    return hit
        # ②～④ 逐筆 → 逐片段：型別複核（「純」條件降級）→ fact 需 refs → 覆蓋／極性／可引用
        # ⚠️ 一筆可能被模型塞進多個句子（「您好！我們支援批次匯入。」標成 greeting）。
        # 片段**只繼承 `kind`／`refs` 這兩個標籤，⛔ 不繼承驗證結果**——每個非空片段
        # 各自跑 `_effective_kind`（以片段本文判）與③④（比對文字一律用片段本文，
        # ⛔ 不用整筆、⛔ 不用拼接後的 answer）。
        for i, sentence in enumerate(out.sentences):
            for fragment in _split_sentences(sentence.text):
                # r11 安全審 F-6：尾隨換行切出的空白片段跳過複核——它沒有內容可以是
                # 斷言，卻會因為結構複核不過被降級成 fact ⇒ 憑空推高 UNCITED_ASSERTION。
                # ①⑤⑥⑦仍對拼接全文掃描，⛔ 這裡跳過不等於那些字沒被看過。
                if fragment.strip() == "":
                    continue
                if self._effective_kind(fragment, sentence) != "fact":
                    continue
                if not sentence.refs:
                    hit = _hit(VerifierVerdict(
                        ok=False, reason="UNCITED_ASSERTION", sent=i))
                    if hit is not None:
                        return hit
                    continue  # 觀察：沒有引文可比對，③④對這個片段無物可跑
                # DSP-029a（r15 #4）：標記解析失敗**只在這裡**致命——被降級為 fact 的
                # 片段所在那一筆。非 fact 筆的 refs 解析失敗 ⛔ 不影響 verdict，維持
                # v4「只看被引用到的」決策：讓模型多寫的裝飾性引用決定整回合生死，
                # 只會憑空推高拒絕率，而真正的風險一定出現在某個事實句的 refs 裡。
                usable: list[int] = []
                for j in range(len(sentence.refs)):
                    cause = resolve_errors.get((i, j))
                    if cause is not None:
                        hit = _hit(VerifierVerdict(
                            ok=False, reason="SCHEMA", schema_cause=cause, sent=i))
                        if hit is not None:
                            return hit
                        # 觀察（Plan §2 r3 註記③）：解析失敗的 ref **後續逐 ref 檢查
                        # 跳過它**——`resolved[(i, j)]` 根本不存在，拿不到引文。
                        continue
                    # 正對照：既不在 `resolve_errors` 也不在 `resolved`，代表呼叫端傳
                    # 進來的兩個 dict 本身不完整（例如自己算了一半）⇒ ⛔ 不得靜默放行。
                    if (i, j) not in resolved:
                        raise ValueError(
                            f"verify() 收到不完整的 refs 解析結果：第 {i} 筆第 {j} 個標記"
                            "既不在 resolved 也不在 resolve_errors——請用 "
                            "services.agent.provenance_units.resolve_refs 產生這兩個 dict"
                        )
                    usable.append(j)
                if not usable:
                    continue  # 觀察：這一筆的 refs 全部解析失敗 ⇒ 沒有引文可比對
                # r11 安全審 F-1（量詞寫死）：這個片段必須在**該筆 `refs` 之中**
                # 至少有一個解析結果完整通過③④（長度＋覆蓋＋citable）。
                # ⛔ 不得以「同筆的別的片段已經通過」代替——那正是跨片段夾帶捏造的出口。
                #
                # **多 ref 聚合**（plan-verifier r1 #3／r2 #2）：
                #  * 引用類（`QUOTE_TOO_SHORT`／`QUOTE_NOT_COVERING`／`SOURCE_NOT_CITABLE`）
                #    維持既有語義：至少一個 ref 完整通過即通過，否則回 `last_failure`；
                #  * 極性類（`POLARITY_MISMATCH`）**任一 ref 命中即擋**——⛔ 不得被
                #    另一個通過的 ref 洗掉。
                # ⚠️ 極性先記著、⛔ 不立刻 return：引用類的 `last_failure` 優先回報，
                #    這樣 `enforce` 下既有拒因與拒絕率一字不變（只有「別的 ref 洗掉
                #    極性」那一種情況會多擋，那正是 r1 #3 要收的洞）。
                last_failure: Optional[VerifierVerdict] = None
                polarity_failure: Optional[VerifierVerdict] = None
                citation_ok = False
                for j in usable:
                    ref_failure: Optional[VerifierVerdict] = None
                    for failure in self._ref_failures(i, fragment, resolved[(i, j)]):
                        if self._is_observed(failure):
                            _hit(failure)  # 只記錄（必回 None）
                            continue
                        if failure.reason == "POLARITY_MISMATCH":
                            if polarity_failure is None:
                                polarity_failure = failure
                            continue
                        if ref_failure is None:
                            ref_failure = failure
                    if ref_failure is None:
                        citation_ok = True
                    else:
                        last_failure = ref_failure
                if not citation_ok and last_failure is not None:
                    last_failure.observed = list(observed)
                    return last_failure
                if polarity_failure is not None:
                    polarity_failure.observed = list(observed)
                    return polarity_failure

        # ⑤ 導流白名單（受眾範圍制，同 ①；pm 引資料段的序號／編號不再被電話正則咬）
        route_verdict = self._verify_routes(answer_nfkc) if self._route_check_apply(audience) else None
        if route_verdict is not None:
            hit = _hit(route_verdict)
            if hit is not None:
                return hit

        # ⑥ 禁詞
        for i, term in enumerate(self.rules.forbid_terms):
            if term in answer_nfkc:
                hit = _hit(VerifierVerdict(
                    ok=False, reason="FORBIDDEN_TERM", term_id=_rule_id(i)))
                if hit is not None:
                    return hit
                break  # 觀察：同一類記一次就夠

        # ⑥' 文件回合禁用樣式（單元 E｜line-bot #6／#3）
        # 文件歸納回合 ⛔ 不寫回、⛔ 不建單 ⇒ 完成式寫入宣稱與提議寫入都是承諾做不到的事。
        # ⚠️ 掃的是 **NFKC 後的整段 `answer`**（同 ①⑤⑥⑦）：跨筆拆字的規避靠它擋。
        # ⚠️ 拒因刻意沿用 `FORBIDDEN_TERM`（⛔ 不新增拒因）：它屬**機敏類**，
        # `_GROUNDING_OBSERVE_REASONS` 不含它 ⇒ `grounding_observe` 下**照擋**。
        # 這一點是本閘的重點——真線上的這種句子多半同時引用失敗，若降成觀察類，
        # 引用類被觀察放過之後就沒有人擋得住「已把憑證掛到帳單上」了。
        if document_turn:
            for i, pattern in enumerate(self._document_turn_forbid):
                if pattern.search(answer_nfkc):
                    hit = _hit(VerifierVerdict(
                        ok=False, reason="FORBIDDEN_TERM", term_id=_doc_turn_rule_id(i)))
                    if hit is not None:
                        return hit
                    break  # 觀察：同一類記一次就夠

        # ⑦ handoff 詞後置掃描
        if scan_handoff_mentions(out.answer) and not handoff:
            hit = _hit(VerifierVerdict(ok=False, reason="HANDOFF_WORD_NO_HANDOFF"))
            if hit is not None:
                return hit

        return _pass()

    # ------------------------------------------------------------------
    def _effective_kind(self, sentence_text: str, sentence: Sentence) -> str:
        """「純」條件（design 元件 6 步②）：子句命中 `assertion_terms` ⇒ 降級 fact；
        否則白名單三型各自的程式端結構複核，複核不過同樣降級 fact。

        全程對 NFKC 正規化後的文字判定（⛔ 不對原始字面）——全形字母／全形冒號斜線
        這類「看起來不像 URL」的變形，NFKC 後就是普通 ASCII，routing 結構判定與
        步⑤ 的導流白名單掃描本來就用同一份正規化文字，兩處標準不一致只會讓合法
        變形寫法被錯判成 fact 而卡在免不了的 UNCITED_ASSERTION，繞過了真正該擋
        它的步⑤。"""
        if sentence.kind == "fact":
            return "fact"
        norm = _nfkc(sentence_text)
        clauses = _split_clauses(norm)
        for clause in clauses:
            if any(term in clause for term in self.rules.assertion_terms):
                return "fact"
        stripped = norm.strip()
        if sentence.kind == "question":
            if stripped and stripped[-1] in _QUESTION_ENDS:
                return "question"
            return "fact"
        if sentence.kind == "greeting":
            bare = stripped.rstrip("".join(_SENTENCE_ENDS)).strip()
            if bare in _GREETING_PHRASES:
                return "greeting"
            return "fact"
        if sentence.kind == "routing":
            if _URL_RE.search(norm) or _PHONE_RE.search(norm):
                return "routing"
            return "fact"
        return "fact"

    def _verify_ref(
        self,
        sent: int,           # DSP-028：**筆索引**（片段不另編號）
        sentence_text: str,  # DSP-028：**片段本文**（⛔ 不是整筆、⛔ 不是拼接後的 answer）
        ref: ResolvedRef,    # DSP-029a：**解析後**的來源片段（⛔ 不取自模型輸出）
    ) -> Optional[VerifierVerdict]:
        """相容介面：回這個 ref 的**第一個**違規（沒有 ⇒ `None`）。
        ⚠️ `verify()` ⛔ 不走這條——它要的是**全部**違規（見 `_ref_failures`）。"""
        failures = self._ref_failures(sent, sentence_text, ref)
        return failures[0] if failures else None

    def _ref_failures(
        self,
        sent: int,
        sentence_text: str,
        ref: ResolvedRef,
    ) -> list[VerifierVerdict]:
        """這個 ref 的**全部**違規，順序固定：
        `QUOTE_TOO_SHORT` → `QUOTE_NOT_COVERING` → `POLARITY_MISMATCH` → `SOURCE_NOT_CITABLE`。

        ⚠️ **⛔ 不短路**（security-reviewer r1 F1 的同一個病）：短路在這裡會讓
        「先掛掉的引用類」把後面的極性類吃掉——`grounding_observe` 下引用類只是觀察，
        覆蓋率不足的句子仍然必須拿得到極性判定。要不要擋是 `verify()` 依模式決定的，
        本函式只負責**把違規全部找出來**。
        """
        failures: list[VerifierVerdict] = []
        source_unit = ref.quote
        unit_nfkc = _nfkc(source_unit)
        if len(unit_nfkc) < self.rules.min_quote_len:
            # DSP-029：模型不再抄字，這條量的是**來源片段本身太短**（例如只有
            # 「【範本】」這種標籤行）——太短的片段撐不起一個事實斷言。⛔ 不因為
            # 「不是模型的錯」就取消它：短片段仍然是不足的依據。
            failures.append(VerifierVerdict(
                ok=False, reason="QUOTE_TOO_SHORT", sent=sent, quote_len=len(unit_nfkc)))

        # `QUOTE_NOT_VERBATIM` 在模型端已不可達（引文是系統從原文切出來的）。
        # 這裡不再有對應分支——拒因列舉仍保留該值（trace 相容），由
        # `tests/unit/agent/test_verifier_req.py` 的**程式層**測試守住
        # 「解析結果必為 provenance 原文的子字串」這個不變量。

        # DSP-029：覆蓋率改**片段側相對值**。舊的絕對門檻 4 字對長句形同虛設
        # （R4 抽審：捏造句只要跟原文共用四個常見字就過），改成「你自己寫的這個
        # 片段，至少一半的有意義字元要在來源片段裡出現」，句子越長要求越高。
        # 絕對下限仍在——`max()` 取嚴的那個，短句不會因為 ratio 算出 1、2 而失守。
        fragment_chars = _meaningful_chars(sentence_text)
        overlap = fragment_chars & _meaningful_chars(source_unit)
        need = max(
            self.rules.min_coverage_chars,
            math.ceil(self.rules.min_coverage_ratio * len(fragment_chars)),
        )
        if len(overlap) < need:
            failures.append(VerifierVerdict(
                ok=False, reason="QUOTE_NOT_COVERING", sent=sent, quote_len=len(unit_nfkc)))

        sentence_nfkc = _nfkc(sentence_text)
        # DSP-021：極性在**詞組層級**比對——句子與引文「有沒有否定詞」須一致，⛔ 不逐詞
        # 要求同一個字面（真線路 2026-09-05：句子「不支持」、引文「不支援」被判不一致，
        # 兩邊其實同為否定）。term_id 記的是句子側（或引文側）第一個命中的否定詞索引。
        sent_hits = [i for i, t in enumerate(self.rules.negation_terms) if t in sentence_nfkc]
        unit_hits = [i for i, t in enumerate(self.rules.negation_terms) if t in unit_nfkc]  # 解析後片段側
        if bool(sent_hits) != bool(unit_hits):
            failures.append(VerifierVerdict(
                ok=False, reason="POLARITY_MISMATCH", sent=sent,
                term_id=_rule_id((sent_hits or unit_hits)[0]), polarity_source="term"))
        else:
            # W6-b3（plan-verifier r3 #1）：**主題錨定**極性——裸「尚未」「未」⛔ 不進
            # `negation_terms`（整段引文比對會誤殺「句子沒提到該主題、引文另一段落有
            # 否定」的正確句）。改以 `(否定詞, 狀態詞)` 配對比對，兩側都必須談到
            # **同一個狀態詞**才算數：
            #   * `neg+status` 在句子、`status` 在引文 ⇒ 句子側否定；
            #   * `neg+status` 在引文、`status` 在句子 ⇒ 引文側否定；
            #   * 兩者不一致 ⇒ `POLARITY_MISMATCH`。
            # 正例：句「尚未逾期」對引文「已逾期 8 天」⇒ 擋；
            # 反例（`known_open` 的 `r4_edit_contract_requires_admin_role`）：句子不含
            # 「回簽」、引文含「管理方尚未回簽」⇒ **不**命中。
            # ⚠️ 只在裸詞那條沒命中時才判（`else`）：同一個片段回兩筆 POLARITY 沒有
            # 額外資訊，term_id 反而會挑到後面那張表、對不回既有 trace 的解讀方式。
            for idx, pair in enumerate(self.rules.negation_status_pairs):
                neg = (pair or {}).get("neg") or ""
                status = (pair or {}).get("status") or ""
                if not neg or not status:
                    continue
                combo = _nfkc(neg + status)
                # 2026-09-09 第四批回測：錨定改成「對面要有**肯定形** `已＋狀態詞`」——
                # 裸狀態詞會撞複合詞（「繳費期限」裡的「繳費」讓「待繳費」被判成否定對肯定，
                # 5 次誤殺、2 回合預算耗盡轉人）。只有一側否定、另一側明寫「已＋狀態」才是衝突；
                # 「待繳費」對「繳費期限」／「待發送」對「尚未發送」都不算。
                affirmed = _nfkc("已" + status)
                sent_negated = combo in sentence_nfkc and affirmed in unit_nfkc
                unit_negated = combo in unit_nfkc and affirmed in sentence_nfkc
                if sent_negated != unit_negated:
                    failures.append(VerifierVerdict(
                        ok=False, reason="POLARITY_MISMATCH", sent=sent,
                        term_id=_pair_rule_id(idx), polarity_source="pair"))
                    break

        # DSP-029a：`citable` 隨解析結果一起傳進來，⛔ 不在此二次查 `tool_results`。
        if not ref.citable:
            failures.append(VerifierVerdict(
                ok=False, reason="SOURCE_NOT_CITABLE", sent=sent))

        return failures

    def _verify_routes(self, answer_nfkc: str) -> Optional[VerifierVerdict]:
        compact = re.sub(r"\s+", "", answer_nfkc)
        allowed_compact = [re.sub(r"\s+", "", _nfkc(r)) for r in self.rules.allowed_routes]
        for match in _URL_RE.finditer(compact):
            token = match.group(0).rstrip(".,;，。！？)）\"'")
            if not any(token == r or token in r or r in token for r in allowed_compact):
                return VerifierVerdict(ok=False, reason="ROUTE_NOT_ALLOWED")
        for match in _PHONE_RE.finditer(compact):
            token = match.group(0)
            if not any(token in r for r in allowed_compact):
                return VerifierVerdict(ok=False, reason="ROUTE_NOT_ALLOWED")
        return None

    # ------------------------------------------------------------------
    def self_test(self, fixtures_dir: str | Path) -> int:
        """尺自證：`known_fabrications.json` 全拒、`known_good.json` 全放，否則 raise（啟動紅）。

        **第三檔 `known_open.json`（DSP-029 r13 #1）**：已知**擋不住**的捏造句，
        以 `expect_ok=True` 載入——它們現在確實會被放行，這份檔案的用途是把
        「已知未擋」寫成可執行的事實，而不是讓人以為已經擋住了。
        ⛔ 不得把這些案例塞進 `known_fabrications.json` 宣稱已擋（那會讓自證變成
        假綠）；等 DSP-030 的新資訊規則真的擋住它們，再整案搬檔。
        回傳 `known_open.json` 的案例數（＝目前仍放行的已知捏造句數），供驗收單列。

        **U3 受眾三組**：fixture 案可選填 `audience`（`_assert_all` 原樣交給
        `verify()`）。缺鍵＝`None`＝照擋，故既有案例判定不變；新增的三組是
        「pm 受眾含金額 ⇒ 放」「prospect 同句 ⇒ 擋」「缺 audience 同句 ⇒ 擋」，
        自證因此同時是**放寬有沒有溢出到別的受眾**的正反對照。
        ⚠️ 自證釘 `enforce`（見下），⛔ 受眾放寬不得靠模式差異來假綠。

        **文件回合（單元 E）**：fixture 案可選填 `document_turn`（同樣原樣交給
        `verify()`）。缺鍵＝`False`＝⑥' 不跑，故既有案例判定不變；新增的三組是
        「文件回合『已把憑證掛到帳單上』⇒ 擋」「同句非文件回合 ⇒ 不因此擋」
        「文件回合中性句 ⇒ 放」，自證因此同時是**新閘有沒有溢出到一般回合**的正反對照。

        ⚠️ `known_open.json` **不存在時視為 0 筆**——`tests/unit/agent/test_bootstrap_req.py`
        會用只有兩個檔的臨時目錄跑自證。出貨那份 fixture 目錄一定要有它，由
        `test_verifier_req.py::test_shipped_fixtures_include_known_open` 當正對照守住。
        """
        fixtures_dir = Path(fixtures_dir)
        # security-reviewer r1 F2：**自證一律以 `enforce` 跑**，⛔ 不受 `mode` 影響——
        # 觀察模式下「捏造句全被放行」會讓 `known_fabrications` 全綠，尺自己失效卻
        # 印出綠燈，而這把尺正是啟動紅的唯一憑據。
        prev_mode = self._mode
        self._mode = DEFAULT_VERIFIER_MODE
        try:
            self._assert_all(fixtures_dir / "known_fabrications.json", expect_ok=False)
            self._assert_all(fixtures_dir / "known_good.json", expect_ok=True)
            known_open = fixtures_dir / "known_open.json"
            if not known_open.exists():
                return 0
            return self._assert_all(known_open, expect_ok=True)
        finally:
            self._mode = prev_mode

    def _assert_all(self, path: Path, *, expect_ok: bool) -> int:
        cases = json.loads(path.read_text(encoding="utf-8"))
        for case in cases:
            out = AgentOutput.model_validate(case["agent_output"])
            tool_results = {
                tid: ToolResult.model_validate(tr) for tid, tr in case.get("tool_results", {}).items()
            }
            # DSP-029a：引用是標記字串，解析由 `resolve_refs` 做。
            # ⛔ 這裡不得自己另寫一套解析——跟 Runtime 用**同一個函式**才叫自證。
            # 案內 `nonce` 是該案標記裡用的代碼；缺省 `_FIXTURE_NONCE` 供
            # 「不刻意測 nonce」的案例共用（測 nonce 不符的案例自己填別的值）。
            from services.agent.provenance_units import resolve_refs

            nonce = case.get("nonce") or _FIXTURE_NONCE
            resolved, resolve_errors = resolve_refs(out, tool_results, nonce)
            # U3：案內 `audience` 是**選填**——沒寫就是 `None`＝照擋，既有每一個案例
            # 的判定因此一字不變（新增的三組受眾案例自己填）。
            # 單元 E：案內 `document_turn` 是**選填**——缺鍵＝`False`＝⑥' 不跑，
            # 既有每一個案例的判定因此一字不變（新增的文件回合案例自己填 true）。
            verdict = self.verify(
                out, tool_results, case.get("user_message", ""), case.get("handoff"),
                resolved=resolved, resolve_errors=resolve_errors,
                audience=case.get("audience"),
                document_turn=bool(case.get("document_turn", False)))
            if verdict.ok != expect_ok:
                raise RuntimeError(
                    f"OutputVerifier self_test 失敗：{path.name} 案例 {case.get('id')} "
                    f"預期 ok={expect_ok}，實得 {verdict.model_dump()}"
                )
            # r11 安全審 F-3：只比 `ok` 會假綠——fixture 機械轉換若把某案例的違規
            # 性質改掉（例如本來測 QUOTE_NOT_COVERING、轉完變成 SCHEMA），`ok=False`
            # 照樣成立，尺已經不量原本那件事卻沒有人知道。fixture 有 `expected_reason`
            # 這個鍵時，reason 必須相等（known_good 的值是 None，同樣要相等）。
            if "expected_reason" in case and verdict.reason != case["expected_reason"]:
                raise RuntimeError(
                    f"OutputVerifier self_test 失敗：{path.name} 案例 {case.get('id')} "
                    f"預期 reason={case['expected_reason']}，實得 reason={verdict.reason}"
                )
            # 同理（DSP-029 r13 #7）：`SCHEMA` 有八種子成因，只比 `reason` 一樣會假綠——
            # fixture 標了 `expected_schema_cause` 就必須對得上。
            if ("expected_schema_cause" in case
                    and verdict.schema_cause != case["expected_schema_cause"]):
                raise RuntimeError(
                    f"OutputVerifier self_test 失敗：{path.name} 案例 {case.get('id')} "
                    f"預期 schema_cause={case['expected_schema_cause']}，"
                    f"實得 schema_cause={verdict.schema_cause}"
                )
        return len(cases)



__all__ = ["OutputVerifier", "split_sentences", "VERIFIER_MODES", "DEFAULT_VERIFIER_MODE"]
