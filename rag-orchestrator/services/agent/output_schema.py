"""`AgentOutput`／`VerifierRules`／`VerifierVerdict` 資料模型（spec agentic-mcp-orchestration・任務 2.3，design.md 元件 6）。

⛔ 只放資料模型，判斷邏輯在 `services/agent/verifier.py`。pydantic v2（見 requirements.txt `pydantic>=2.13,<3`）。

**`AgentOutput.fact_class` 刻意型別為 `Optional[str]`，不是 `FactClass` 列舉**（設計取捨，見任務回報）：
design 元件 6 要求 verifier 對「`fact_class` 缺／不合法」做 fail-closed 判斷——如果這個欄位型別是
`FactClass`，pydantic 在**建構 `AgentOutput` 這一步**就會因為非法值直接 raise，verifier 永遠看不到
「非法值」這個狀態，也就測不到 fail-closed 分支。生產路徑上，OpenAI `response_format` 的
`json_schema strict` 仍會把 schema 送成封閉 enum；這裡放寬只是讓 verifier 自己能做「缺／非法」
與「合法值但屬 SENSITIVE」的兩段式判斷（`services/agent/verifier.py::_classify_fact_class`）。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Sentence(BaseModel):
    """模型逐句輸出的**一筆**：文字、分類與依據標記同筆攜帶（DSP-028／DSP-029a）。

    `text` 要含句尾標點；⛔ 一筆不放兩句（放兩句時 Verifier 會把它切成片段逐一複核，
    片段只**繼承** `kind`／`refs` 標籤、⛔ 不繼承驗證結果）。

    **DSP-029a：`refs` 是標記字串本身，⛔ 不再是任何陣列的索引。**
    起因見 `.claude/DECISIONS.md` DSP-029a：舊契約要模型自己對齊
    `tool_call_id`／`source`／`unit` 三個定址欄位，R5 實測 162 回合裡 119 次錯在
    三欄互混。標記已經整串印在資料段那一行的行首，照抄一個字串是模型做得到的動作，
    對齊三個欄位不是。解析在 `services.agent.provenance_units.resolve_refs`，
    ⛔ 解析結果不寫回本模型任何欄位（r13 F-A：掛上去就會跟著
    `decision_snapshot`／trace 外流）。
    """
    text: str
    kind: Literal["fact", "question", "greeting", "routing"]
    refs: list[str] = Field(
        default_factory=list,
        description=(
            "事實句填其依據所在那一行開頭的標記，原樣照抄。"
        ),
    )


class AgentOutput(BaseModel):
    """模型一輪回覆的結構化輸出（`response_format` json_schema strict）。

    **DSP-028：⛔ 模型不再輸出 `answer` 欄，也不再輸出另一張逐句對照表**——舊契約要模型自己保證
    「句數等於標籤數、順序對得上」，句數不等時程式只能猜哪筆標籤配哪一句，猜錯的
    方向是放行。改成文字與標籤同筆攜帶後，「拼接後等於送出的字串」變成定義而不是
    要靠檢查維持的巧合。

    **DSP-029a：⛔ 不再有 `citations` 陣列**——引用就是 `Sentence.refs` 裡的標記字串，
    句子與依據之間不再隔一層索引（索引本身是另一個會對錯的東西）。
    """
    kind: Literal["answer", "ask", "recommend", "handoff"] = Field(
        description=(
            "本輪回覆的型別：answer 直接回答、ask 反問澄清、recommend 建議下一步、"
            "handoff 轉真人（轉人時 sentences 可留空）。"
        )
    )
    sentences: list[Sentence] = Field(
        default_factory=list,
        description=(
            "回覆逐句一筆 {text, kind, refs}；text 含句尾標點、⛔ 一筆不放兩句。"
            "系統把各筆 text 原樣接起來就是使用者看到的整段話，⛔ 不另外給 answer 欄位。"
        ),
    )
    fact_class: Optional[str] = None  # 見檔案頂端說明：刻意不是 FactClass 型別
    handoff_reason: Optional[str] = None

    @property
    def answer(self) -> str:
        """使用者實際會看到的整段文字＝逐筆 `text` 直接拼接（⛔ 不補空白、不補標點）。

        **刻意用純 `@property`、⛔ 不用 pydantic `computed_field`**（r11 安全審 F-4）：
        `computed_field` 會讓 `model_json_schema()` 把 `answer` 列進 properties，而
        `services/agent/runtime.py:strict_json_schema` 把每一層的 `required` 設成
        「全部 properties」⇒ OpenAI strict schema 會**回頭要求模型輸出 `answer`**，
        等於把剛拆掉的雙軌契約原封不動裝回去。純 property 不進 schema，也不進
        `model_dump()`，`answer` 因此只有一個導出點——步①⑤⑥⑦掃的字串就是送出的字串。
        """
        return "".join(s.text for s in self.sentences)


#: 11＋1 個結構化拒因（design 元件 6 全文；DSP-033 補 `NOT_ENTAILED`）。
#: ⚠️ `QUOTE_NOT_COVERING`／`POLARITY_MISMATCH` 兩碼**沿用但語義收窄**（DSP-033）：
#: NLI 模式下前者只在「有意義字元交集 <4」這條絕對下限觸發（ratio 分支退場）、
#: 後者只在「同一 `assertion_terms` 詞根兩側皆出現且恰一側被否定」時觸發。
#: 降級模式（`/nli` 不可用）下兩碼回復現行 ratio∧全極性語義——同一個代碼在兩種
#: 模式下量的不是同一件事，故 trace 另有 `nli_degraded` 這個 violation 可以分流，
#: ⛔ 不得只看拒因分佈就對兩批數字做比較。
VerdictReason = Literal[
    "SENSITIVE_TOPIC",
    "UNCITED_ASSERTION",
    "QUOTE_NOT_VERBATIM",
    "QUOTE_TOO_SHORT",
    "QUOTE_NOT_COVERING",
    "POLARITY_MISMATCH",
    "NOT_ENTAILED",
    "SOURCE_NOT_CITABLE",
    "ROUTE_NOT_ALLOWED",
    "FORBIDDEN_TERM",
    "HANDOFF_WORD_NO_HANDOFF",
    "SCHEMA",
]


#: `term_id` 的唯一合法形式（2.6 前置 security review P2）：`rule#<規則集內索引>`。
#: ⛔ **不得填字面詞／regex 本身**——verdict 會落進
#: `usage_events.decision_snapshot.agent`，也會被 2.7 的 trace 端點印出來，
#: 填字面值等於把敏感樣式表／禁詞表／否定詞表逐字外洩。
#: 產生點是 `services/agent/verifier.py:_rule_id()`；這裡用 pydantic `pattern`
#: 把契約釘在型別上，任何想塞字面詞的呼叫端會在建構當下就炸。
TERM_ID_PATTERN = r"^rule#\d+$"


class VerifierVerdict(BaseModel):
    """結構化拒因。⛔ 不放原文（`sent`／`term_id`／`quote_len` 是索引與長度，不是內容）。

    `term_id` 只認 `rule#<n>`：`reason` 決定查哪一張規則表
    （`SENSITIVE_TOPIC`→`sensitive_patterns`、`FORBIDDEN_TERM`→`forbid_terms`、
    `POLARITY_MISMATCH`→`negation_terms`），`n` 是該表內 0-based 索引，
    再配 trace 的 `rules_sha` 才對得回具體規則集版本。

    **`NOT_ENTAILED` 的 `term_id` 固定為 `None`**（DSP-033 r18 F-15）：它不是
    規則集裡任何一條規則命中的結果，硬塞一個索引會讓稽核順著它去查一張根本
    無關的表。定位這種拒絕要靠 `entail_score`＋`nli_model_sha`＋`nli_tau`。
    """
    ok: bool
    reason: Optional[VerdictReason] = None
    #: DSP-028：**筆索引**（`AgentOutput.sentences` 的 index），⛔ 不是切片段後的片段序號——
    #: 一筆裡若含多個片段，任一片段違規都記在該筆的索引上（`trace_view` 顯示為「筆次」）。
    sent: Optional[int] = None
    term_id: Optional[str] = Field(default=None, pattern=TERM_ID_PATTERN)
    quote_len: Optional[int] = None
    #: DSP-033：`NOT_ENTAILED` 時該片段在**它那一筆全部解析後來源句**上取得的
    #: 最大 p_entail（0–1，四捨五入 4 位）。⛔ 不是原文——它是一個分數，
    #: 與 `nli_model_sha`（trace）＋`nli_tau`（rules）三者同存才重算得出 verdict。
    #: ⚠️ `|score − τ| < 0.005` 視為 borderline：跨機一致性不保證到那個精度。
    #: ⚠️ 只進 trace／snapshot，**⛔ 不進回饋給模型的 messages**（r18 F-3）——
    #: 告訴模型「你差 0.02 分」等於教它往門檻上調而不是往有據上改。
    entail_score: Optional[float] = None
    #: DSP-029 r13 #7：`SCHEMA` 的**子成因**（封閉列舉）。原本只回 `SCHEMA` 三個字，
    #: 模型與稽核都看不出是哪一種；引用改成標記字串後，「標記本身不合格式／不是
    #: 本回合的」與「標記合格式但指不到東西」是不同的病，不分流等於把它們混進同一格。
    #: DSP-029a：`cite_out_of_range` 退場（`cite` 索引已不存在），改為
    #: `ref_invalid`（格式不合或 nonce 非本回合）／`ref_source_not_found`／`ref_ambiguous`。
    #: ⛔ 只放列舉值，**不攜帶任何模型文字或來源原文**——它會落
    #: `usage_events.decision_snapshot.agent`，也會被 trace 端點印出來。
    schema_cause: Optional[
        Literal[
            "empty_sentences",
            "empty_text",
            "ref_invalid",
            "ref_source_not_found",
            "ref_ambiguous",
            "unit_out_of_range",
            "marker_in_answer",
            "handoff_reason_invalid",
        ]
    ] = None


class VerifierRules(BaseModel):
    """規則集。`load()` 是唯一建構入口——`sha256` 一律由載入時的檔案位元組計算，
    ⛔ 不信任 json 檔內任何 `sha256` 欄位（避免檔案改了但欄位忘記同步，`sha256` 就失去自證意義）。
    """
    version: str
    sha256: str
    sensitive_patterns: list[str]
    negation_terms: list[str]
    forbid_terms: list[str]
    allowed_routes: list[str]
    assertion_terms: list[str]
    min_quote_len: int = 6
    #: DSP-033：NLI 模式下這是覆蓋尺的**全部**——「片段與來源句的有意義字元
    #: 交集 < 4」是 NLI 之前的決定性硬拒（r18 F-2 保留的絕對下限）。
    #: ⚠️ DSP-029 的**相對覆蓋率欄位已移除**（名字見 DSP-033）：它只在降級
    #: 模式下還活著，而降級模式的比例固定為程式常數
    #: `services.agent.verifier._DEGRADED_COVERAGE_RATIO`（0.5＝rules 1.3.0 現值），
    #: ⛔ 不再從規則集讀——留在這裡會讓人以為調它可以影響線上那把尺。
    min_coverage_chars: int = 4
    #: DSP-033：NLI 蘊涵門檻。片段在其所在筆的解析後來源句上，至少一句
    #: `p_entail ≥ nli_tau` 才算有據（F-1 量詞）。τ=0.40 是在第八輪 181 句盲標
    #: **新樣本**上、凍結約束「誤殺 ≤10% 取最大抓到率」下選出來的
    #: （抓到 69%／誤殺 9%，現行規則同批 62%／9%）。
    #: ⛔ 不得為了讓 `known_open` 自證好看而調它（DSP-033 F-1：⛔ 不調 τ 救自證）。
    #: ⚠️ 它進規則集是為了跟著 `rules_sha` 一起版本化——改它就是換一把尺，
    #: 而 trace 必須看得出換過。`max_length` 若變更也要重校 τ（r18 F-8）。
    nli_tau: float = 0.40

    @classmethod
    def load(cls, path: str | Path) -> "VerifierRules":
        raw = Path(path).read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        data = json.loads(raw)
        data["sha256"] = sha
        return cls.model_validate(data)


__all__ = ["Sentence", "AgentOutput", "VerdictReason", "VerifierVerdict",
           "VerifierRules", "TERM_ID_PATTERN"]
