"""`OutputVerifier`（spec agentic-mcp-orchestration・任務 2.3，design.md 元件 6）。

七步順序（全部通過才放行；第一個踩到的違規決定 `VerifierVerdict.reason`）：
①敏感五類 ②白名單句型（逐筆 schema 檢查＋逐片段「純」條件降級） ③逐字＋覆蓋＋極性
④來源可引用 ⑤導流白名單 ⑥禁詞 ⑦handoff 詞後置掃描。

**DSP-028：②③④的量測單位是「筆」與「片段」，①⑤⑥⑦的量測單位是拼接後的 `answer`**
——後者是安全側（掃的字串就是送出去的字串），跨筆拆數字／拆禁詞的規避靠它擋。

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

from services.agent.output_schema import AgentOutput, Sentence, VerifierRules, VerifierVerdict
from services.agent.tools.registry import Provenance, ToolResult
from services.presales_gate import FactClass, HANDOFF_WORDS, HandoffReason, SENSITIVE, scan_handoff_mentions

#: 「純」條件切子句用的封閉分隔詞（design：逗號／頓號／分號）。
_CLAUSE_SEPS: tuple[str, ...] = ("，", ",", "、", "；", ";")
#: 句末標點（拆片段用，⛔ 與 `presales_gate._sentences` 各自維護——那邊是決策層私有符號，
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
                return VerifierVerdict(ok=False, reason="SCHEMA")
            return VerifierVerdict(ok=True)
        if fact_class in SENSITIVE:
            return VerifierVerdict(ok=False, reason="SENSITIVE_TOPIC")
        answer_nfkc = _nfkc(out.answer)
        for i, pattern in enumerate(self._sensitive_patterns):
            if pattern.search(answer_nfkc):
                return VerifierVerdict(
                    ok=False, reason="SENSITIVE_TOPIC", term_id=_rule_id(i))

        # ② 逐筆 schema 檢查（DSP-028 (a)(b)(c)）——⛔ 不再比對「句數＝標籤數」：
        # 文字與標籤同筆攜帶後，拼接相等是定義，不是要靠檢查維持的巧合。
        # (a) 非 handoff 卻沒有任何一筆 ⇒ 沒有東西可以驗，一律 SCHEMA
        #     （handoff 在上面已 return，走不到這裡）。
        if not out.sentences:
            return VerifierVerdict(ok=False, reason="SCHEMA")
        # (b) 任一筆 text 全空白 ⇒ SCHEMA（空筆會讓「每個字都屬於某一筆」失去意義）。
        for i, sentence in enumerate(out.sentences):
            if sentence.text.strip() == "":
                return VerifierVerdict(ok=False, reason="SCHEMA", sent=i)
        # (c) 任一 cite 索引越界 ⇒ SCHEMA。⚠️ **負索引也是越界**（r11 安全審 F-5）：
        #     python 的 `citations[-1]` 會靜靜取到最後一筆合法引用，等於讓模型用 -1
        #     借別句的引用來替自己的斷言背書。重複索引可接受（同一筆引用支撐多個片段）。
        for i, sentence in enumerate(out.sentences):
            for idx in sentence.cite:
                if idx < 0 or idx >= len(out.citations):
                    return VerifierVerdict(ok=False, reason="SCHEMA", sent=i)

        # ②～④ 逐筆 → 逐片段：型別複核（「純」條件降級）→ fact 需 cite → 逐字／覆蓋／極性／可引用
        # ⚠️ 一筆可能被模型塞進多個句子（「您好！我們支援批次匯入。」標成 greeting）。
        # 片段**只繼承 `kind`／`cite` 這兩個標籤，⛔ 不繼承驗證結果**——每個非空片段
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
                if not sentence.cite:
                    return VerifierVerdict(ok=False, reason="UNCITED_ASSERTION", sent=i)
                # r11 安全審 F-1（量詞寫死）：這個片段必須在**該筆 `cite` 之中**
                # 至少有一筆 citation 完整通過③④（逐字＋覆蓋＋極性＋citable）。
                # ⛔ 不得以「同筆的別的片段已經通過」代替——那正是跨片段夾帶捏造的出口。
                last_failure: Optional[VerifierVerdict] = None
                for idx in sentence.cite:
                    failure = self._verify_citation(i, fragment, out.citations[idx], tool_results)
                    if failure is None:
                        last_failure = None
                        break
                    last_failure = failure
                if last_failure is not None:
                    return last_failure

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

    def _verify_citation(
        self,
        sent: int,          # DSP-028：**筆索引**（片段不另編號）
        sentence_text: str,  # DSP-028：**片段本文**（⛔ 不是整筆、⛔ 不是拼接後的 answer）
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
            # DSP-021：source 標籤錯、引文卻逐字存在於**同一次工具回傳**的別筆 provenance
            # （真線路 2026-09-05：引文出自大綱「房源」節、模型標成 outline:lease）——
            # 尺量的是「這段字是不是真的在回傳原文裡」，標籤是元資料；仍限同一個
            # tool_call_id、仍要逐字、citable 以**實際命中**的那筆為準（⛔ 不能靠改標籤
            # 把不可引用的字洗成可引用）。citable 的先找，都沒有才落到不可引用的那筆。
            for prov in sorted(provenances, key=lambda pv: not pv.citable):
                if quote_nfkc in _nfkc(prov.text):
                    matched = prov
                    break
        if matched is None:
            return VerifierVerdict(ok=False, reason="QUOTE_NOT_VERBATIM", sent=sent, quote_len=len(quote_nfkc))

        overlap = _meaningful_chars(sentence_text) & _meaningful_chars(citation.quote)
        if len(overlap) < self.rules.min_coverage_chars:
            return VerifierVerdict(ok=False, reason="QUOTE_NOT_COVERING", sent=sent, quote_len=len(quote_nfkc))

        sentence_nfkc = _nfkc(sentence_text)
        # DSP-021：極性在**詞組層級**比對——句子與引文「有沒有否定詞」須一致，⛔ 不逐詞
        # 要求同一個字面（真線路 2026-09-05：句子「不支持」、引文「不支援」被判不一致，
        # 兩邊其實同為否定）。term_id 記的是句子側（或引文側）第一個命中的否定詞索引。
        sent_hits = [i for i, t in enumerate(self.rules.negation_terms) if t in sentence_nfkc]
        quote_hits = [i for i, t in enumerate(self.rules.negation_terms) if t in quote_nfkc]
        if bool(sent_hits) != bool(quote_hits):
            return VerifierVerdict(
                ok=False, reason="POLARITY_MISMATCH", sent=sent,
                term_id=_rule_id((sent_hits or quote_hits)[0]))

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
            # r11 安全審 F-3：只比 `ok` 會假綠——fixture 機械轉換若把某案例的違規
            # 性質改掉（例如本來測 QUOTE_NOT_COVERING、轉完變成 SCHEMA），`ok=False`
            # 照樣成立，尺已經不量原本那件事卻沒有人知道。fixture 有 `expected_reason`
            # 這個鍵時，reason 必須相等（known_good 的值是 None，同樣要相等）。
            if "expected_reason" in case and verdict.reason != case["expected_reason"]:
                raise RuntimeError(
                    f"OutputVerifier self_test 失敗：{path.name} 案例 {case.get('id')} "
                    f"預期 reason={case['expected_reason']}，實得 reason={verdict.reason}"
                )


def split_sentences(text: str) -> list[str]:
    """公開版切句（DSP-021）：呼叫端要重現「系統怎麼切片段」時用它，
    與 `verify()` 步②(d) 用的是同一個函式，⛔ 不得另寫一份規則。

    DSP-028 後 Runtime 的 SCHEMA 回饋改為直接指出「空陣列／第 N 筆空 text／
    第 N 筆 cite 越界」三種原因，不再回報切句結果；此函式仍公開，
    供測試與工具重現片段邊界。"""
    return _split_sentences(text)


__all__ = ["OutputVerifier", "split_sentences"]
