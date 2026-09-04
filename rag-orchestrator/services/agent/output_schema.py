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
    """一筆引用。`source` 格式如 `kb:3600`／`outline:contract`／`help:qa06`／`jgb2:bills#ref`。"""
    tool_call_id: str
    source: str
    quote: str


class SentenceCite(BaseModel):
    """`answer` 裡一句的分類與引用索引。`cite` 是 `AgentOutput.citations` 的索引清單。"""
    sent: int
    kind: Literal["fact", "question", "greeting", "routing"]
    cite: list[int] = Field(default_factory=list)


class AgentOutput(BaseModel):
    """模型一輪回覆的結構化輸出（`response_format` json_schema strict）。"""
    kind: Literal["answer", "ask", "recommend", "handoff"]
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    sentence_map: list[SentenceCite] = Field(default_factory=list)
    fact_class: Optional[str] = None  # 見檔案頂端說明：刻意不是 FactClass 型別
    handoff_reason: Optional[str] = None


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
    sent: Optional[int] = None
    term_id: Optional[str] = Field(default=None, pattern=TERM_ID_PATTERN)
    quote_len: Optional[int] = None


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

    @classmethod
    def load(cls, path: str | Path) -> "VerifierRules":
        raw = Path(path).read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        data = json.loads(raw)
        data["sha256"] = sha
        return cls.model_validate(data)


__all__ = ["Citation", "SentenceCite", "AgentOutput", "VerdictReason", "VerifierVerdict",
           "VerifierRules", "TERM_ID_PATTERN"]
