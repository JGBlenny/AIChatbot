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


class Citation(BaseModel):
    """一筆引用：**指向來源的第幾句**，⛔ 不再由模型抄引文（DSP-029）。

    `source` 格式如 `kb:3600`／`outline:contract`／`help:qa06`／`jgb2:bills#ref`。
    引文由 Runtime 依 `(tool_call_id, source, unit)` 從 `Provenance.text` 以
    `services.agent.provenance_units.provenance_units` 切出第 `unit` 個片段解析，
    另以 `resolved` 傳進 Verifier——**⛔ 解析結果不得寫回本模型任何欄位**
    （r13 F-A：解析後的原文一旦掛在 `AgentOutput` 上，就會跟著
    `decision_snapshot`／trace 外流，那正是 2.6 security review P2 擋掉的事）。
    """
    tool_call_id: str
    source: str
    unit: int = Field(
        description=(
            "來源片段編號：資料段裡每個片段行首標記 [代碼:來源§編號] 的那個編號（從 0 起算）。"
            "填你要引用的那一句的編號，⛔ 不要把片段文字抄進來、⛔ 不要填負數。"
        )
    )


class Sentence(BaseModel):
    """模型逐句輸出的**一筆**：文字與它的分類、引用索引同筆攜帶（DSP-028）。

    `text` 要含句尾標點；⛔ 一筆不放兩句（放兩句時 Verifier 會把它切成片段逐一複核，
    片段只**繼承** `kind`／`cite` 標籤、⛔ 不繼承驗證結果）。
    `cite` 是 `AgentOutput.citations` 的索引清單。
    """
    text: str
    kind: Literal["fact", "question", "greeting", "routing"]
    cite: list[int] = Field(default_factory=list)


class AgentOutput(BaseModel):
    """模型一輪回覆的結構化輸出（`response_format` json_schema strict）。

    **DSP-028：⛔ 模型不再輸出 `answer` 欄，也不再輸出另一張逐句對照表**——舊契約要模型自己保證
    「句數等於標籤數、順序對得上」，句數不等時程式只能猜哪筆標籤配哪一句，猜錯的
    方向是放行。改成文字與標籤同筆攜帶後，「拼接後等於送出的字串」變成定義而不是
    要靠檢查維持的巧合。
    """
    kind: Literal["answer", "ask", "recommend", "handoff"] = Field(
        description=(
            "本輪回覆的型別：answer 直接回答、ask 反問澄清、recommend 建議下一步、"
            "handoff 轉真人（轉人時 sentences 與 citations 可留空）。"
        )
    )
    sentences: list[Sentence] = Field(
        default_factory=list,
        description=(
            "回覆逐句一筆 {text, kind, cite}；text 含句尾標點、⛔ 一筆不放兩句。"
            "系統把各筆 text 原樣接起來就是使用者看到的整段話，⛔ 不另外給 answer 欄位。"
        ),
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description=(
            "引用清單：每筆指出某個事實句出自哪一次工具回傳或哪一個大綱章節的第幾句"
            "（tool_call_id＋source＋unit）；句子那一側在自己的 cite 填本清單的索引（從 0 起算）。"
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


#: 11 個結構化拒因（design 元件 6 全文）。
VerdictReason = Literal[
    "SENSITIVE_TOPIC",
    "UNCITED_ASSERTION",
    "QUOTE_NOT_VERBATIM",
    "QUOTE_TOO_SHORT",
    "QUOTE_NOT_COVERING",
    "POLARITY_MISMATCH",
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
    """
    ok: bool
    reason: Optional[VerdictReason] = None
    #: DSP-028：**筆索引**（`AgentOutput.sentences` 的 index），⛔ 不是切片段後的片段序號——
    #: 一筆裡若含多個片段，任一片段違規都記在該筆的索引上（`trace_view` 顯示為「筆次」）。
    sent: Optional[int] = None
    term_id: Optional[str] = Field(default=None, pattern=TERM_ID_PATTERN)
    quote_len: Optional[int] = None
    #: DSP-029 r13 #7：`SCHEMA` 的**子成因**（封閉列舉）。原本只回 `SCHEMA` 三個字，
    #: 模型與稽核都看不出是哪一種；引用改指向來源句編號後又多了三種結構性失敗
    #: （來源不存在／編號越界／把標記抄進 text），不分流等於把它們混進同一格。
    #: ⛔ 只放列舉值，**不攜帶 source／unit 以外的模型文字**——它會落
    #: `usage_events.decision_snapshot.agent`，也會被 trace 端點印出來。
    schema_cause: Optional[
        Literal[
            "empty_sentences",
            "empty_text",
            "cite_out_of_range",
            "source_not_found",
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
    min_coverage_chars: int = 4
    #: DSP-029：覆蓋率改**片段側相對值**——被驗的那個片段（模型自己寫的句子）
    #: 有意義字元中，至少這個比例要出現在解析出來的來源片段裡。絕對下限
    #: `min_coverage_chars` 仍在（`max(...)`），兩者是「取嚴的那個」而非二選一。
    min_coverage_ratio: float = 0.5

    @classmethod
    def load(cls, path: str | Path) -> "VerifierRules":
        raw = Path(path).read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        data = json.loads(raw)
        data["sha256"] = sha
        return cls.model_validate(data)


__all__ = ["Citation", "Sentence", "AgentOutput", "VerdictReason", "VerifierVerdict",
           "VerifierRules", "TERM_ID_PATTERN"]
