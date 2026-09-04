"""`OutputVerifier`（spec agentic-mcp-orchestration・任務 2.3，design.md 元件 6）。

七步順序（全部通過才放行；第一個踩到的違規決定 `VerifierVerdict.reason`）：
①敏感五類 ②白名單句型（含 schema 覆蓋檢查與「純」條件降級） ③逐字＋覆蓋＋極性
④來源可引用 ⑤導流白名單 ⑥禁詞 ⑦handoff 詞後置掃描。

**只 import `presales_gate`／`conversational_config`**（design 元件 6 收尾一句）：
`SENSITIVE`、`FactClass`、`HANDOFF_WORDS`、`scan_handoff_mentions` 來自 `services.presales_gate`，
⛔ 不複製這些封閉集合到本檔——那樣兩處會各自演化、對不上。
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Optional

from services.agent.output_schema import AgentOutput, SentenceCite, VerifierRules, VerifierVerdict
from services.agent.tools.registry import Provenance, ToolResult
from services.presales_gate import FactClass, HANDOFF_WORDS, SENSITIVE, scan_handoff_mentions

#: 「純」條件切子句用的封閉分隔詞（design：逗號／頓號／分號）。
_CLAUSE_SEPS: tuple[str, ...] = ("，", ",", "、", "；", ";")
#: 句末標點（拆句用，⛔ 與 `presales_gate._sentences` 各自維護——那邊是決策層私有符號，
#: 這裡是 verifier 自己拆句做 schema 覆蓋檢查，兩處標點集合恰好同源純屬巧合，不是耦合）。
_SENTENCE_ENDS: tuple[str, ...] = ("。", "！", "!", "？", "?", "\n")
#: 問句結尾標記（NFKC 後判定）。
_QUESTION_ENDS: tuple[str, ...] = ("？", "?")
#: 問候詞封閉表（結構判定用，非業務可調規則，故不放進 `VerifierRules`）。
_GREETING_PHRASES: frozenset[str] = frozenset({
    "您好", "你好", "嗨", "哈囉", "早安", "午安", "晚安",
    "謝謝", "謝謝您", "不客氣", "感謝您的詢問", "很高興為您服務", "您好，很高興為您服務",
})
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


def _split_sentences(text: str) -> list[str]:
    sents: list[str] = []
    buf = ""
    for ch in text:
        buf += ch
        if ch in _SENTENCE_ENDS:
            sents.append(buf)
            buf = ""
    if buf:
        sents.append(buf)
    return sents


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
    """
    return f"rule#{index}"


def _is_legal_fact_class(value: Optional[str]) -> bool:
    return isinstance(value, str) and value in {fc.value for fc in FactClass}


class OutputVerifier:
    def __init__(self, rules: VerifierRules):
        self.rules = rules
        self._sensitive_patterns = [re.compile(p) for p in rules.sensitive_patterns]

    # ------------------------------------------------------------------
    def verify(
        self,
        out: AgentOutput,
        tool_results: dict[str, ToolResult],
        user_message: str,
        handoff: Optional[dict],
    ) -> VerifierVerdict:
        # ① 敏感五類（fail-closed：缺／非法一律視為敏感）
        if not _is_legal_fact_class(out.fact_class):
            return VerifierVerdict(ok=False, reason="SENSITIVE_TOPIC")
        fact_class = FactClass(out.fact_class)
        if fact_class in SENSITIVE:
            return VerifierVerdict(ok=False, reason="SENSITIVE_TOPIC")
        answer_nfkc = _nfkc(out.answer)
        for i, pattern in enumerate(self._sensitive_patterns):
            if pattern.search(answer_nfkc):
                return VerifierVerdict(
                    ok=False, reason="SENSITIVE_TOPIC", term_id=_rule_id(i))

        # ② 白名單句型：schema 覆蓋檢查
        sents = _split_sentences(out.answer)
        if len(sents) != len(out.sentence_map):
            return VerifierVerdict(ok=False, reason="SCHEMA")
        if _nfkc("".join(sents)) != answer_nfkc:
            return VerifierVerdict(ok=False, reason="SCHEMA")
        by_index = sorted(out.sentence_map, key=lambda s: s.sent)
        if [s.sent for s in by_index] != list(range(len(sents))):
            return VerifierVerdict(ok=False, reason="SCHEMA")

        # ②～④ 逐句：型別複核（「純」條件降級）→ fact 需 cite → 逐字／覆蓋／極性／可引用
        for cite in by_index:
            sentence_text = sents[cite.sent]
            effective_kind = self._effective_kind(sentence_text, cite)
            if effective_kind != "fact":
                continue
            if not cite.cite:
                return VerifierVerdict(ok=False, reason="UNCITED_ASSERTION", sent=cite.sent)
            for idx in cite.cite:
                if idx < 0 or idx >= len(out.citations):
                    return VerifierVerdict(ok=False, reason="SCHEMA", sent=cite.sent)
                citation = out.citations[idx]
                verdict = self._verify_citation(cite.sent, sentence_text, citation, tool_results)
                if verdict is not None:
                    return verdict

        # ⑤ 導流白名單
        route_verdict = self._verify_routes(answer_nfkc)
        if route_verdict is not None:
            return route_verdict

        # ⑥ 禁詞
        for i, term in enumerate(self.rules.forbid_terms):
            if term in answer_nfkc:
                return VerifierVerdict(
                    ok=False, reason="FORBIDDEN_TERM", term_id=_rule_id(i))

        # ⑦ handoff 詞後置掃描
        if scan_handoff_mentions(out.answer) and not handoff:
            return VerifierVerdict(ok=False, reason="HANDOFF_WORD_NO_HANDOFF")

        return VerifierVerdict(ok=True)

    # ------------------------------------------------------------------
    def _effective_kind(self, sentence_text: str, cite: SentenceCite) -> str:
        """「純」條件（design 元件 6 步②）：子句命中 `assertion_terms` ⇒ 降級 fact；
        否則白名單三型各自的程式端結構複核，複核不過同樣降級 fact。

        全程對 NFKC 正規化後的文字判定（⛔ 不對原始字面）——全形字母／全形冒號斜線
        這類「看起來不像 URL」的變形，NFKC 後就是普通 ASCII，routing 結構判定與
        步⑤ 的導流白名單掃描本來就用同一份正規化文字，兩處標準不一致只會讓合法
        變形寫法被錯判成 fact 而卡在免不了的 UNCITED_ASSERTION，繞過了真正該擋
        它的步⑤。"""
        if cite.kind == "fact":
            return "fact"
        norm = _nfkc(sentence_text)
        clauses = _split_clauses(norm)
        for clause in clauses:
            if any(term in clause for term in self.rules.assertion_terms):
                return "fact"
        stripped = norm.strip()
        if cite.kind == "question":
            if stripped and stripped[-1] in _QUESTION_ENDS:
                return "question"
            return "fact"
        if cite.kind == "greeting":
            bare = stripped.rstrip("".join(_SENTENCE_ENDS)).strip()
            if bare in _GREETING_PHRASES:
                return "greeting"
            return "fact"
        if cite.kind == "routing":
            if _URL_RE.search(norm) or _PHONE_RE.search(norm):
                return "routing"
            return "fact"
        return "fact"

    def _verify_citation(
        self,
        sent: int,
        sentence_text: str,
        citation,
        tool_results: dict[str, ToolResult],
    ) -> Optional[VerifierVerdict]:
        quote_nfkc = _nfkc(citation.quote)
        if len(quote_nfkc) < self.rules.min_quote_len:
            return VerifierVerdict(ok=False, reason="QUOTE_TOO_SHORT", sent=sent, quote_len=len(quote_nfkc))

        tool_result = tool_results.get(citation.tool_call_id)
        provenances: list[Provenance] = list(tool_result.provenance) if tool_result else []
        matched: Optional[Provenance] = None
        for prov in provenances:
            if prov.source != citation.source:
                continue
            if quote_nfkc in _nfkc(prov.text):
                matched = prov
                break
        if matched is None:
            return VerifierVerdict(ok=False, reason="QUOTE_NOT_VERBATIM", sent=sent, quote_len=len(quote_nfkc))

        overlap = _meaningful_chars(sentence_text) & _meaningful_chars(citation.quote)
        if len(overlap) < self.rules.min_coverage_chars:
            return VerifierVerdict(ok=False, reason="QUOTE_NOT_COVERING", sent=sent, quote_len=len(quote_nfkc))

        sentence_nfkc = _nfkc(sentence_text)
        for i, term in enumerate(self.rules.negation_terms):
            in_sentence = term in sentence_nfkc
            in_quote = term in quote_nfkc
            if in_sentence != in_quote:
                return VerifierVerdict(
                    ok=False, reason="POLARITY_MISMATCH", sent=sent, term_id=_rule_id(i))

        if not matched.citable:
            return VerifierVerdict(ok=False, reason="SOURCE_NOT_CITABLE", sent=sent)

        return None

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
    def self_test(self, fixtures_dir: str | Path) -> None:
        """尺自證：`known_fabrications.json` 全拒、`known_good.json` 全放，否則 raise（啟動紅）。"""
        fixtures_dir = Path(fixtures_dir)
        self._assert_all(fixtures_dir / "known_fabrications.json", expect_ok=False)
        self._assert_all(fixtures_dir / "known_good.json", expect_ok=True)

    def _assert_all(self, path: Path, *, expect_ok: bool) -> None:
        cases = json.loads(path.read_text(encoding="utf-8"))
        for case in cases:
            out = AgentOutput.model_validate(case["agent_output"])
            tool_results = {
                tid: ToolResult.model_validate(tr) for tid, tr in case.get("tool_results", {}).items()
            }
            verdict = self.verify(out, tool_results, case.get("user_message", ""), case.get("handoff"))
            if verdict.ok != expect_ok:
                raise RuntimeError(
                    f"OutputVerifier self_test 失敗：{path.name} 案例 {case.get('id')} "
                    f"預期 ok={expect_ok}，實得 {verdict.model_dump()}"
                )


__all__ = ["OutputVerifier"]
