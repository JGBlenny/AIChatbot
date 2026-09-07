"""售前閘門的決定性部分（spec presales-grounding-gate，design.md 元件 1）。

**只有純函式**：門檻讀值（唯一讀值點）、`fact_class` 正規化、handoff 建構、封閉三詞掃描。
⛔ 無 I/O、無 LLM、無 DB。引擎（`conversational_engine`）與路由（`routers/chat.py`）只呼叫這裡，⛔ 不各自實作。

為什麼要有這一層（2026-09-04 盤查根因，`docs/presales-assistant-rootcause-20260904.md`）：
售前對話在知識庫無佐證時仍由 LLM 生成事實——「不杜撰」寫在 prompt 裡擋不住（同題五次三種立場）。
閘門必須是程式，不是叮嚀。

⚠️ 三個刻意的「不」：
- `parse_fact_class` ⛔ 不做大小寫／同義正規化——容忍變體等於讓 brain 的資料品質問題靜默通過（比照 `instance_applicability.knowledge_instance_applicability`）。
- `HANDOFF_WORDS` 是**封閉集合**——它治的是「三個詞出現就補訊號」，⛔ 不擴成「這句是不是在轉人」的開放語義判斷（`feedback_rule_vs_layer`）。
- `presales_threshold` 壞值回決策層預設、⛔ 不回 0——0 就是 2026-09-04 之前的病灶（`_converge_grounding` 的 `similarity_threshold=0.0`）。
"""
from __future__ import annotations

import math
import os
import unicodedata
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Dict, Final, FrozenSet, Iterable, Mapping, Optional, Tuple

from services.decision_layer import DecisionConfig

#: 售前專用門檻覆寫鍵；未設或壞值 ⇒ 沿用決策層唯一讀值點 `DecisionConfig.kb_threshold`（需求 1.2／1.3）
THRESHOLD_ENV: Final[str] = "PRESALES_GROUNDING_THRESHOLD"
#: D6 抽取式作答的開關。業主 2026-09-04 二次裁決：**預設關**——先補知識（DSP-008、3600／3610／3584 講法）再考慮開。
#: 關＝事實題有知識時交 LLM 依知識合成（temp 0.2、逐項對照）；開＝貼 top-1 知識原文。三條路（converge／inline／ask 反問句）同一開關。
EXTRACTIVE_ENV: Final[str] = "PRESALES_EXTRACTIVE"
_TRUTHY: Final[FrozenSet[str]] = frozenset({"1", "true", "on", "yes"})


def extractive_enabled() -> bool:
    """env PRESALES_EXTRACTIVE ∈ {1,true,on,yes}（不分大小寫）⇒ True；未設或其他值 ⇒ False（預設關）。唯一讀值點。"""
    return (os.getenv(EXTRACTIVE_ENV) or "").strip().lower() in _TRUTHY


class FactClass(str, Enum):
    """brain 對本輪問題的封閉分類（需求 3.1）。值域改動＝改需求，⛔ 不在程式內以關鍵字判類。"""
    customer_reference = "customer_reference"
    pricing = "pricing"
    contract_sla = "contract_sla"
    compliance = "compliance"
    security = "security"
    feature = "feature"
    other = "other"


#: 盤查 P0-1「要求的行為」五類的一對一映射（需求 2.2）
SENSITIVE: Final[FrozenSet[FactClass]] = frozenset({
    FactClass.customer_reference, FactClass.pricing, FactClass.contract_sla, FactClass.compliance, FactClass.security,
})

#: 封閉詞集（需求 4.2）：出現即補 handoff 訊號；⛔ 不擴成開放語義。
#:   「沒有資料」是我們自己在合成 prompt 要求 LLM 說的句式（【逐項對照】「這部分我沒有資料」）——
#:   e2e 第二輪抓到它出現時沒有出口（B4），故納入：承認沒資料就要給「找真人」。
HANDOFF_WORDS: Final[Tuple[str, ...]] = ("專人", "真人", "客服", "沒有資料")


class HandoffReason(str, Enum):
    no_grounding = "no_grounding"                        # 事實題、grounding 為空
    sensitive_no_grounding = "sensitive_no_grounding"    # 同上且 fact_class ∈ SENSITIVE
    llm_mentioned_handoff = "llm_mentioned_handoff"      # LLM 路徑文字含封閉詞（後置掃描補訊號）
    partial_grounding = "partial_grounding"              # D6：多項目事實題只回得了 top-1 知識，其餘沒資料（抽取式＋固定尾句）
    # ── agent 路徑新增兩值（spec agentic-mcp-orchestration 任務 2.4）──
    # ⚠️ **純加值**：既有四值的字面量、`build_handoff`／`build_llm_mention_handoff`／
    #    `build_partial_handoff` 的推導規則一律不動——這兩值不由任何 `build_*` 產生，
    #    只能由 `services/agent/tools/handoff.py:handoff_request` 依模型指定的 reason 建構，
    #    以及由 AgentRuntime（任務 2.1）在降級時直接指定。
    tool_unavailable = "tool_unavailable"                # 工具逾時／server 不可用，重試一次仍失敗（design 錯誤處理表）
    budget_exhausted = "budget_exhausted"                # 工具呼叫數／重寫次數／deadline 任一耗盡（design 預算計數表）


#: D6 多項目問句的封閉分隔詞（業主 2026-09-04）：命中任一 ⇒ 視為「一次問多個項目」。⛔ 不含逗號（幾乎每句都有）、不做語義判斷。
MULTI_ITEM_SEPARATORS: Final[Tuple[str, ...]] = ("、", "和", "跟", "與", "及", "含", "包含")


def is_multi_item_question(text: Optional[str]) -> bool:
    """問句是否一次列了多個項目（封閉分隔詞）。"""
    if not text:
        return False
    return any(sep in text for sep in MULTI_ITEM_SEPARATORS)


#: R2.11（e2e 第三輪 A1）：使用者「有沒有在問問題」的封閉表面標記。⛔ 只看字面標記、不做語義判斷；
#: 漏判（問句沒帶標記）只會回到舊行為，誤判（非問句含「幾」）只會多跑一次知識查詢。
QUESTION_MARKERS: Final[Tuple[str, ...]] = ("？", "?", "嗎", "呢", "可不可以", "能不能", "有沒有", "是否", "能否",
                                            "怎麼", "如何", "多少", "幾")
#: 句末標點（拆句用）
_SENTENCE_ENDS: Final[Tuple[str, ...]] = ("。", "！", "!", "？", "?", "\n")
#: brain 反問句裡「陳述部分」達此長度才視為在作答（「了解。」「好的，」這類招呼不算）。
ASK_DECLARATIVE_MIN_CHARS: Final[int] = 8


def looks_like_question(text: Optional[str]) -> bool:
    """使用者這一句是否像在問問題（封閉標記任一命中）。"""
    if not text:
        return False
    return any(m in text for m in QUESTION_MARKERS)


def split_declaratives(text: Optional[str]) -> Tuple[str, str]:
    """把 brain 的 next_question 拆成（陳述部分, 問句部分）。以句末標點切句，句末是「？／?」的歸問句，其餘歸陳述。
    ⛔ 純結構：不判內容真假。回傳兩段皆已 strip。"""
    if not text:
        return "", ""
    sents, buf = [], ""
    for ch in text:
        buf += ch
        if ch in _SENTENCE_ENDS:
            sents.append(buf); buf = ""
    if buf.strip():
        sents.append(buf)
    decl = "".join(x for x in sents if x.rstrip()[-1:] not in ("？", "?"))
    ques = "".join(x for x in sents if x.rstrip()[-1:] in ("？", "?"))
    return decl.strip(), ques.strip()


_CLAUSE_SEPS: Final[Tuple[str, ...]] = ("，", ",")


def strip_declarative_clauses(question_text: str) -> Tuple[str, str]:
    """問句**內部**的作答子句（D6 上線後 brain 的新漏法：「物件和合約的資料也可以匯入，您還有其他想了解的功能嗎？」——
    斷言與反問同一句，句末是「？」，`split_declaratives` 看不到）。規則：以逗號拆子句，最後一個子句視為問句本體；
    其餘子句若**不含問句標記且 ≥ ASK_DECLARATIVE_MIN_CHARS** ⇒ 視為作答子句。回傳（作答子句串接, 剝掉作答子句後的問句）。"""
    out_q, decl = [], []
    for sent in _sentences(question_text):
        if sent.rstrip()[-1:] not in ("？", "?"):
            out_q.append(sent); continue
        parts = [sent]
        for sep in _CLAUSE_SEPS:
            parts = [q for part in parts for q in part.split(sep)]
        parts = [x for x in parts if x.strip()]
        keep = []
        for i, clause in enumerate(parts):
            is_last = i == len(parts) - 1
            if not is_last and len(clause.strip()) >= ASK_DECLARATIVE_MIN_CHARS and not looks_like_question(clause):
                decl.append(clause.strip())
            else:
                keep.append(clause.strip())
        out_q.append("，".join(keep))
    return "".join(decl), "".join(out_q).strip()


def _sentences(text: Optional[str]) -> list:
    sents, buf = [], ""
    for ch in (text or ""):
        buf += ch
        if ch in _SENTENCE_ENDS:
            sents.append(buf); buf = ""
    if buf.strip():
        sents.append(buf)
    return sents


def analyze_ask(user_message: Optional[str], next_question: Optional[str]) -> Optional[Tuple[str, str, str]]:
    """R2.11：使用者在問問題，而 brain 用 `ask`（沒填 inline_answer）卻在 next_question 裡作答。
    回傳 None ⇒ 放行（純反問、或使用者沒在問）；否則 (how, 剩下的問句, 被判為作答的陳述文字)：
    ("sentence", 問句部分, 陳述) ⇒ 有 ≥ ASK_DECLARATIVE_MIN_CHARS 的獨立陳述句（e2e 第三輪 A1：「我們的系統支援租客批次匯入…合約和歷史帳單。請問…？」）；
    ("clause", 剝掉子句後的問句, 子句) ⇒ 只有問句內的作答子句。兩者都要走 grounding；沒知識時 sentence ⇒ 固定句、clause ⇒ 只剩問句（不升格固定句，
    因為「如果您有 20 間物件，最在意哪一點？」這類合法前綴也會被判成子句——誤判方向刻意往「少講一句」錯，不往「放行斷言」錯）。"""
    if not looks_like_question(user_message):
        return None
    decl, ques = split_declaratives(next_question)
    if len(decl) >= ASK_DECLARATIVE_MIN_CHARS:
        return "sentence", ques, decl
    cdecl, q_only = strip_declarative_clauses(ques or (next_question or ""))
    if cdecl:
        return "clause", q_only, cdecl
    return None


def ask_is_answering(user_message: Optional[str], next_question: Optional[str]) -> bool:
    """R2.11 的布林版（相容）。"""
    return analyze_ask(user_message, next_question) is not None


@dataclass(frozen=True)
class Handoff:
    """結構化轉人訊號（需求 4.1）。`message` 為固定文案，⛔ 不回顯使用者輸入。"""
    reason: HandoffReason
    fact_class: FactClass
    channel: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {"reason": self.reason.value, "fact_class": self.fact_class.value,
                "channel": self.channel, "message": self.message}


def presales_threshold() -> float:
    """售前 grounding 門檻的**唯一讀值點**（需求 1.2／1.3）。

    `PRESALES_GROUNDING_THRESHOLD`（[0,1]）覆寫；未設／不可解析／越界／NaN ⇒ `DecisionConfig.load().kb_threshold`
    並 print 警告。⛔ 不 raise、⛔ 不回 0。
    """
    fallback = float(DecisionConfig.load().kb_threshold)
    raw = os.getenv(THRESHOLD_ENV)
    if raw is None or raw.strip() == "":
        return fallback
    try:
        val = float(raw)
    except (TypeError, ValueError):
        print(f"⚠️ [presales_gate] {THRESHOLD_ENV}={raw!r} 不可解析，回決策層 kb_threshold={fallback}")
        return fallback
    if math.isnan(val) or not (0.0 <= val <= 1.0):
        print(f"⚠️ [presales_gate] {THRESHOLD_ENV}={raw!r} 不在 [0,1]，回決策層 kb_threshold={fallback}")
        return fallback
    return val


def parse_fact_class(value: Any) -> FactClass:
    """非 str／不在 enum ⇒ `other`（需求 3.2）。⛔ 不 strip、不 lower、不同義映射。"""
    if isinstance(value, str):
        try:
            return FactClass(value)
        except ValueError:
            return FactClass.other
    return FactClass.other


def build_handoff(fact_class: FactClass, *, channel: str, message: str) -> Handoff:
    """事實題空 grounding 的 handoff；reason 由敏感性決定，`message` 一律照傳（需求 2.2／4.1）。"""
    reason = HandoffReason.sensitive_no_grounding if fact_class in SENSITIVE else HandoffReason.no_grounding
    return Handoff(reason=reason, fact_class=fact_class, channel=channel, message=message)


def build_llm_mention_handoff(fact_class: FactClass, *, channel: str, message: str) -> Handoff:
    """LLM 路徑後置掃描命中時的 handoff（需求 4.2）。"""
    return Handoff(reason=HandoffReason.llm_mentioned_handoff, fact_class=fact_class, channel=channel, message=message)


def build_partial_handoff(fact_class: FactClass, *, channel: str, message: str) -> Handoff:
    """D6：抽取式作答只涵蓋部分項目時的 handoff（reason=partial_grounding；message＝固定尾句）。"""
    return Handoff(reason=HandoffReason.partial_grounding, fact_class=fact_class, channel=channel, message=message)


def scan_handoff_mentions(text: Optional[str]) -> bool:
    """封閉三詞任一出現 ⇒ True（需求 4.2）。None／空字串 ⇒ False。"""
    if not text:
        return False
    return any(w in text for w in HANDOFF_WORDS)


# ---------------------------------------------------------------------------
# 身分反問句型表（Plan `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/
# plan-m-d-runtime-wiring-20260907.md` §4.1-7／-8；業主 2026-09-07 核：30 句全收、
# 第 4 節三條誤殺風險走 (b)「先留著量」、主張縮為「**agent 路徑內**不重問」）
# ---------------------------------------------------------------------------

#: 售前五欄位（identity／scale／team／pain／interested，來源
#: `inputs/kb3645-presales-dialogue-rules-20260906.md`）的「模型正在向對方**索取**這個
#: 欄位」句型片段。內容＝業主核可的
#: `inputs/identity-reask-patterns-draft-20260907.md` 三十列**逐字**（測試對該檔逐列對帳）。
#:
#: ⛔ **只給測試與掃描用**（`tests/unit/agent/test_identity_no_reask_req.py`；4.4b 對真
#: 輸出量「一次一題、已知不重問」）。**⛔ 一個字都不得被渲染進任何 prompt**：
#: `services/agent/agent_rules.py`／`prompt_assembler.py`／`outline.py`／`runtime.py`
#: ⛔ 不得引用本符號或 `reask_hits`——把「不要講這些句子」寫給模型看，只會教它換句話問，
#: 而 `SENSITIVE` 被 `agent_rules._SENSITIVE_LINE` 反射進政策文的先例 ⛔ 不得在這裡重演
#: （那條先例是刻意保留的，⛔ 不動它）。回歸鎖在同名測試的「不進 prompt 掃描」。
#:
#: 比對規則（`reask_hits`）：**兩側都 NFKC** ＋ **子字串**，⛔ 不用正則。下表句型**已是
#: NFKC 形式**、且一律**不含標點**——標點是最容易漂的部分（`?`／`嗎?`／`呢`），
#: 寫進句型只會降低召回；全形括號／問號寫了更等於埋一顆 NFKC 後永遠比不到的地雷。
#:
#: ⛔ **任何欄位都不得清空**：空 tuple 會讓「不得匹配」這種否定斷言恆真（＝一把瞎尺）。
#: 非空守門與「清空必紅」的正對照都在同名測試的第一節。
#:
#: ⚠️ 它 ⛔ 不是「這句有沒有禮貌／該不該收斂」的尺；它只回答一件事：這句在問對方
#: **是誰／多大／幾人／痛在哪／想看什麼**嗎。已知誤殺（業主裁定先留著量、⛔ 不加個案
#: 例外分支；要改就以「一類」為單位收窄或整條拿掉）：`interested` 的「有興趣的功能」
#: 也可能出現在陳述句、`pain` 的「有什麼困擾」也可能出現在同理句、`scale` 的
#: 「大概幾間」／「多少間房」可能被 CTA 文案掃到。
IDENTITY_REASK_PATTERNS: Final[Mapping[str, Tuple[str, ...]]] = MappingProxyType({
    "identity": (
        "您是個人房東",
        "是個人房東還是",
        "包租代管還是",
        "請問您的身分",
        "您是房東還是",
        "您是自己收租",
    ),
    "scale": (
        "管理多少戶",
        "您有幾戶",
        "大概幾間",
        "目前管理的戶數",
        "多少間房",
        "規模大概多少",
    ),
    "team": (
        "有沒有團隊",
        "團隊有幾位",
        "是自己一個人管",
        "幾個人一起",
        "有其他同事",
        "多人協作",
    ),
    "pain": (
        "主要的痛點",
        "最困擾您的",
        "目前遇到什麼問題",
        "最想解決的",
        "哪個環節最花時間",
        "有什麼困擾",
    ),
    "interested": (
        "對哪些功能有興趣",
        "想先了解哪個功能",
        "有興趣的功能",
        "最想看哪一塊",
        "哪個部分比較需要",
        "想優先導入",
    ),
})


def reask_hits(text: Optional[str], fields: Iterable[str]) -> Dict[str, Tuple[str, ...]]:
    """`text` 命中了 `fields` 這些欄位的哪些反問句型（**兩側 NFKC ＋ 子字串**）。

    回傳只含**有命中**的欄位 ⇒ 空 dict ＝「這句沒有在索取這些欄位」；純函式、無 I/O。

    ⛔ 未知欄位名一律 `ValueError`：打錯欄位名會讓「不得命中」的否定斷言恆真，
    那正是靜默失敗的形狀（同理，⛔ 不對未知欄位回空 dict）。
    ⚠️ 值域內的欄位若被清成空 tuple，本函式**照樣**回不命中——守門是常數那邊的
    非空斷言，⛔ 不在這裡補救（補救了就看不出表被清空）。
    ⛔ 這支與 `IDENTITY_REASK_PATTERNS` 都不得被 prompt 組裝路徑引用（見常數說明）。
    """
    requested = tuple(fields)
    unknown = sorted({f for f in requested if f not in IDENTITY_REASK_PATTERNS})
    if unknown:
        raise ValueError(
            f"未知的反問欄位 {unknown}；值域＝{sorted(IDENTITY_REASK_PATTERNS)}"
        )
    normalized = unicodedata.normalize("NFKC", text or "")
    hits: Dict[str, Tuple[str, ...]] = {}
    for field in requested:
        matched = tuple(
            pattern for pattern in IDENTITY_REASK_PATTERNS[field]
            if unicodedata.normalize("NFKC", pattern) in normalized
        )
        if matched:
            hits[field] = matched
    return hits


__all__ = [
    "THRESHOLD_ENV", "EXTRACTIVE_ENV", "extractive_enabled", "FactClass", "SENSITIVE", "HANDOFF_WORDS", "MULTI_ITEM_SEPARATORS", "HandoffReason", "Handoff",
    "presales_threshold", "parse_fact_class", "build_handoff", "build_llm_mention_handoff", "build_partial_handoff",
    "scan_handoff_mentions", "is_multi_item_question",
    "QUESTION_MARKERS", "ASK_DECLARATIVE_MIN_CHARS", "looks_like_question", "split_declaratives", "ask_is_answering",
    "strip_declarative_clauses", "analyze_ask",
    "IDENTITY_REASK_PATTERNS", "reask_hits",
]
