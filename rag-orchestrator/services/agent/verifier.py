"""`OutputVerifier`（spec agentic-mcp-orchestration・任務 2.3，design.md 元件 6）。

七步順序（全部通過才放行；第一個踩到的違規決定 `VerifierVerdict.reason`）：
①敏感五類 ②白名單句型（逐筆結構檢查＋逐片段「純」條件降級） ③覆蓋＋極性
④來源可引用 ⑤導流白名單 ⑥禁詞 ⑦handoff 詞後置掃描。

**DSP-028：②③④的量測單位是「筆」與「片段」，①⑤⑥⑦的量測單位是拼接後的 `answer`**
——後者是安全側（掃的字串就是送出去的字串），跨筆拆數字／拆禁詞的規避靠它擋。

**DSP-033：步③的「覆蓋率」與「極性」由 NLI 蘊涵分數取代**，但 ⛔ 不是整條拆掉——
NLI 之前仍有兩道**決定性**硬拒（r18 F-2）：
  (i) **floor**：片段與來源句的有意義字元交集 <4 ⇒ `QUOTE_NOT_COVERING`
      （語義收窄為絕對下限，DSP-029 的 ratio 分支退場）；
  (ii) **窄化極性**：同一 `assertion_terms` 詞根兩側皆出現、且恰一側被否定
      ⇒ `POLARITY_MISMATCH`（181 句實測與 NLI 單獨同為 69%／9%，零代價）。
  (iii) 通過前兩道才問 NLI：`p_entail < nli_tau` ⇒ `NOT_ENTAILED`。
⚠️ **NLI 不可用一律降級、⛔ 不轉人**（可用性）：該回合改跑 DSP-029 的
ratio(常數 0.5)∧全極性語義，verdict 照常產生，由 Runtime 記 `nli_degraded`。
⚠️ 降級模式跑的是**比較鬆**的那把尺（62%／9% vs 69%／9%）——所以驗收①②④
一律把降級回合分開計（F-10），⛔ 不得把兩批混在一起算放行率。

**只 import `presales_gate`／`conversational_config`**（design 元件 6 收尾一句）：
`SENSITIVE`、`FactClass`、`HANDOFF_WORDS`、`scan_handoff_mentions` 來自 `services.presales_gate`，
⛔ 不複製這些封閉集合到本檔——那樣兩處會各自演化、對不上。
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from services.agent.nli_client import (  # DSP-033：步③的 NLI 依賴（必填注入，見 __init__）
    FakeNliClient,
    NliClient,
    NliPair,
    NliPairsCapped,
    NliUnavailable,
)
from services.agent.output_schema import AgentOutput, Sentence, VerifierRules, VerifierVerdict
from services.agent.provenance_units import (  # 葉模組：切句與 refs 解析（DSP-029 落地取捨④）
    _SENTENCE_ENDS,
    ResolvedRef,
    _split_sentences,
    split_sentences,
)
from services.agent.tools.registry import ToolResult
from services.presales_gate import FactClass, HANDOFF_WORDS, HandoffReason, SENSITIVE, scan_handoff_mentions

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
    """
    return f"rule#{index}"


#: fixture 案內未指定 `nonce` 時的缺省值（`_assert_all` 用）。⛔ 只給 fixture／自證用，
#: 產線 nonce 一律來自 `prompt_assembler.new_nonce()`——固定值在真線路上等於沒有 nonce。
_FIXTURE_NONCE = "FIXTURE0000000000"


def _is_legal_fact_class(value: Optional[str]) -> bool:
    return isinstance(value, str) and value in {fc.value for fc in FactClass}


#: 降級模式（`/nli` 不可用）的相對覆蓋率門檻——**程式常數**（DSP-033 v7）。
#: 0.5 ＝ rules 1.3.0 那個**已移除**的相對覆蓋率欄位現值，⛔ 不再從規則集讀
#: （欄位名見 `.claude/DECISIONS.md` DSP-033；⛔ 刻意不在程式裡留它的字面名字，
#: 免得 grep 得到一個其實已經不存在的設定鍵）：
#: 留在規則集裡，它看起來像一個「可以調」的線上參數，實際上只在服務掛掉的那些
#: 回合生效——一個調了幾乎沒有效果、但改動會被記進 `rules_sha` 的旋鈕，
#: 比沒有旋鈕更容易誤導人。
_DEGRADED_COVERAGE_RATIO = 0.5

#: NLI 句對的配對鍵：`(筆索引, 片段索引, ref 索引)`（r18 F-11）。
#: ⚠️ **片段索引一定要在鍵裡**：同一筆可能被切成多個片段而共用同一組 `refs`，
#: 少了它，兩個片段對同一個 ref 的分數會互相蓋掉——而那正是「跨片段夾帶捏造」
#: 這條攻擊路徑要用的縫。由 `_fact_fragments` 產生（唯一產生點），
#: `tests/unit/agent/test_verifier_req.py::test_pair_key_includes_the_fragment_index` 守住。
PairKey = tuple[int, int, int]


@dataclass
class VerifyOutcome:
    """`verify_async` 的回傳：verdict 之外，Runtime 還要知道這一回合是**用哪把尺**判的。

    ⛔ `degraded`／`pairs_capped` 刻意**不放進 `VerifierVerdict`**：verdict 會落
    `usage_events.decision_snapshot.agent`，多一個欄位就要動 `agent_boundary.py`
    的封閉白名單不變量；而且它描述的是「這次判定的環境」而非「這次判定的結論」，
    掛在 verdict 上會讓兩件事在稽核時分不開。
    """

    verdict: VerifierVerdict
    #: `/nli` 逾時／非 200／未就緒／長度不符 ⇒ 該回合走 DSP-029 舊尺。
    degraded: bool = False
    #: 句對數超過 `NLI_MAX_PAIRS`（F-4）。**與逾時分開計**——兩者處置不同。
    pairs_capped: bool = False
    #: 最近一次成功回應帶回的權重指紋（進 `TurnTrace.nli_model_sha`）。
    nli_model_sha: str = ""


class OutputVerifier:
    def __init__(self, rules: VerifierRules, *, nli_client: NliClient):
        """`nli_client` 是**必填關鍵字參數、⛔ 無隱式預設**（DSP-033 P1-2）。

        ⚠️ 給預設值就會出現「忘了注入 ⇒ 步③靜靜退回舊尺」這條路徑，而那個
        失敗方向是**放行**（舊尺抓到 62% vs 新尺 69%），且沒有任何徵兆——
        降級是個要被記進 trace、要被 health 告警的事件，⛔ 不可以是一個
        建構子少寫一個參數就達成的預設狀態。
        """
        self.rules = rules
        self._nli = nli_client
        self._sensitive_patterns = [re.compile(p) for p in rules.sensitive_patterns]
        # 窄化極性的「詞根」＝ `assertion_terms` 扣掉**它自己就是否定形**的那些。
        # ⚠️ 兩張表都來自規則集，⛔ 不另立第三份否定詞表：現行 1.4.0 下
        # `不支援／不會／無法／不能` 同時列在兩表，扣掉後剩
        # `可以／支援／需要／會／能／提供／支持／包含/內建/整合/自動` 這些肯定形詞根。
        _negators = set(rules.negation_terms)
        self._polarity_roots: tuple[str, ...] = tuple(
            t for t in rules.assertion_terms if t not in _negators)

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
    ) -> VerifierVerdict:
        """**同步入口＝降級尺**（DSP-033 取捨，見下方「為什麼分兩個入口」）。

        `resolved`／`resolve_errors` 由**呼叫端**（Runtime／`self_test`）以
        `services.agent.provenance_units.resolve_refs` 算好傳進來，鍵是
        `(筆索引, ref 索引)`（DSP-029a）。

        ⚠️ 兩者刻意是**必填關鍵字參數、⛔ 無預設值**（r13 F-A）：解析後的引文
        ⛔ 不掛在 `AgentOutput`／`Sentence` 上，所以 Verifier 沒有別的地方拿得到它；
        給預設值等於允許「忘了傳 ⇒ 引用檢查靜靜失去比對對象」，而那個失敗方向是放行。

        ⚠️ `tool_results` 在 DSP-029a 之後**本方法已不再讀它**——來源的 `citable`
        旗標隨 `ResolvedRef` 一起傳進來，⛔ 不再於此二次查表（兩處各查一次就會出現
        「解析用 A 筆 provenance、可引用旗標讀到 B 筆」的分歧）。參數保留是刻意的：
        它是 design 元件 6 的介面契約，Runtime／測試都以這個形狀對接。

        ## 為什麼分兩個入口（DSP-033 P1-1 的選擇）
        NLI 是一次 HTTP 呼叫，⛔ 不得阻塞事件迴圈。可選的兩種形狀是
        「`async verify`」與「同步 client 包 `asyncio.to_thread`」，這裡選**前者**：
          * `verify_async(...)` ＝ 產線入口（Runtime 用），會問 NLI；
          * `verify(...)`（本方法）＝ **降級尺**，⛔ 永遠不碰 NLI。
        理由是 `asyncio.to_thread` 那條路會讓「同步呼叫」在 event loop 裡看起來
        仍然可行，於是任何一個忘了 `await` 的呼叫點都會**安靜地**跑到執行緒池裡
        去打真服務——包括 `bootstrap.build_runtime` 的啟動自證（P1-2 明令
        「啟動 ⛔ 不依賴 `/nli` 可用」）。把同步入口釘死成降級尺之後，
        「同步路徑打到真服務」在型別上就不成立。
        """
        return self._verify_core(
            out, tool_results, user_message, handoff,
            resolved=resolved, resolve_errors=resolve_errors, scores=None)

    # ------------------------------------------------------------------
    async def verify_async(
        self,
        out: AgentOutput,
        tool_results: dict[str, ToolResult],
        user_message: str,
        handoff: Optional[dict],
        *,
        resolved: dict[tuple[int, int], ResolvedRef],
        resolve_errors: dict[tuple[int, int], str],
    ) -> VerifyOutcome:
        """**產線入口**（DSP-033）：問一次 NLI，回 verdict＋這次用的是哪把尺。

        單次 HTTP 帶該回合**所有**句對（服務端逐對推論，P2-5）；
        `NliUnavailable`（含逾時／非 200／未就緒／長度不符）與 `NliPairsCapped`
        一律降級，⛔ 不 raise 給 Runtime——NLI 掛掉不該讓回合失敗（可用性）。
        """
        keys, pairs = self._pairs_for(out, resolved)
        if not pairs:
            # 走不到步③（handoff／敏感／沒有 fact 片段／refs 全解析失敗）：
            # 空 dict 與 `None` 在這裡的差別只有「萬一真的跑到步③」時才顯現，
            # 而那個方向是**拒**（沒有分數＝不蘊涵），⛔ 不是放行。
            return VerifyOutcome(
                self._verify_core(
                    out, tool_results, user_message, handoff,
                    resolved=resolved, resolve_errors=resolve_errors, scores={}),
                nli_model_sha=self._model_sha(),
            )
        try:
            raw = await self._nli.score(pairs)
        except NliPairsCapped:
            return self._degraded(
                out, tool_results, user_message, handoff,
                resolved=resolved, resolve_errors=resolve_errors, pairs_capped=True)
        except NliUnavailable:
            return self._degraded(
                out, tool_results, user_message, handoff,
                resolved=resolved, resolve_errors=resolve_errors, pairs_capped=False)
        except Exception:  # noqa: BLE001 — client 的任何意外一律等同不可用
            return self._degraded(
                out, tool_results, user_message, handoff,
                resolved=resolved, resolve_errors=resolve_errors, pairs_capped=False)
        if not isinstance(raw, list) or len(raw) != len(pairs):
            # F-11 的第二道（`HttpNliClient` 已擋一次）：假 client／未來的別種
            # 實作若回錯長度，⛔ 不得靠 zip 的截斷行為靜靜錯位配對。
            return self._degraded(
                out, tool_results, user_message, handoff,
                resolved=resolved, resolve_errors=resolve_errors, pairs_capped=False)
        return VerifyOutcome(
            self._verify_core(
                out, tool_results, user_message, handoff,
                resolved=resolved, resolve_errors=resolve_errors,
                scores=dict(zip(keys, raw))),
            nli_model_sha=self._model_sha(),
        )

    # ------------------------------------------------------------------
    def _model_sha(self) -> str:
        return str(getattr(self._nli, "last_model_sha", "") or "")

    def _degraded(
        self, out, tool_results, user_message, handoff, *,
        resolved, resolve_errors, pairs_capped: bool,
    ) -> VerifyOutcome:
        """降級：跑 DSP-029 舊尺（ratio 常數 0.5 ∧ 全極性），verdict 照常產生。"""
        return VerifyOutcome(
            self._verify_core(
                out, tool_results, user_message, handoff,
                resolved=resolved, resolve_errors=resolve_errors, scores=None),
            degraded=True,
            pairs_capped=pairs_capped,
            nli_model_sha=self._model_sha(),
        )

    # ------------------------------------------------------------------
    def _fact_fragments(self, out: AgentOutput):
        """逐 `(筆索引, 片段索引, 片段本文)` 產出**被判為 fact 的非空片段**。

        ⚠️ 片段索引是 `_split_sentences` 的原始序號（**含**被跳過的空片段），
        ⛔ 不是「第幾個非空片段」——`_pairs_for` 與 `_verify_core` 兩處各自
        走一次這個產生器，序號必須是同一套，否則分數會配到別的片段上。
        本方法是那個序號的**唯一**產生點。
        """
        for i, sentence in enumerate(out.sentences):
            for f, fragment in enumerate(_split_sentences(sentence.text)):
                if fragment.strip() == "":
                    continue
                if self._effective_kind(fragment, sentence) != "fact":
                    continue
                yield i, f, fragment

    def _pairs_for(self, out: AgentOutput, resolved: dict) -> tuple[list[PairKey], list[NliPair]]:
        """該回合要問 NLI 的 `(keys, pairs)`。

        ⚠️ 這裡**不**預先跳過「等一下會先被 floor／窄化極性擋掉」的句對：那需要
        把步③的判斷邏輯複製一份到收集階段，而兩份邏輯遲早會分歧；分歧的後果是
        某些片段拿不到分數 ⇒ 被判 `NOT_ENTAILED`（誤殺）。代價是偶爾多送幾對，
        而回合上限本來就只有 `NLI_MAX_PAIRS=12`。
        ⚠️ `out.kind == "handoff"` 與敏感題在步①就 return 了，收句對只是白費——
        故這裡先擋掉，免得敏感題的捏造 sentences 平白撐爆 12 對上限。
        """
        if out.kind == "handoff":
            return [], []
        if not _is_legal_fact_class(out.fact_class):
            return [], []
        if FactClass(out.fact_class) in SENSITIVE:
            return [], []
        keys: list = []
        pairs: list = []
        for i, f, fragment in self._fact_fragments(out):
            for j in range(len(out.sentences[i].refs)):
                ref = resolved.get((i, j))
                if ref is None:
                    continue          # 解析失敗的標記在步③之前就致命，⛔ 不必問 NLI
                keys.append((i, f, j))
                pairs.append(NliPair(premise=ref.quote, hypothesis=fragment))
        return keys, pairs

    # ------------------------------------------------------------------
    def _verify_core(
        self,
        out: AgentOutput,
        tool_results: dict[str, ToolResult],
        user_message: str,
        handoff: Optional[dict],
        *,
        resolved: dict[tuple[int, int], ResolvedRef],
        resolve_errors: dict[tuple[int, int], str],
        scores: Optional[dict],
    ) -> VerifierVerdict:
        """七步本體。`scores is None` ⇒ **降級尺**；`scores` 是 dict ⇒ **NLI 尺**。

        ⚠️ dict 裡查不到的鍵一律當成「沒有分數」＝不蘊涵（拒）。這個預設方向是
        刻意的：配對邏輯若哪天出錯，結果會是誤殺（看得見、會被驗收②量到），
        ⛔ 不是漏放（看不見）。
        """
        nli_mode = scores is not None
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
                return VerifierVerdict(
                    ok=False, reason="SCHEMA", schema_cause="handoff_reason_invalid")
            return VerifierVerdict(ok=True)
        if fact_class in SENSITIVE:
            return VerifierVerdict(ok=False, reason="SENSITIVE_TOPIC")
        answer_nfkc = _nfkc(out.answer)
        for i, pattern in enumerate(self._sensitive_patterns):
            if pattern.search(answer_nfkc):
                return VerifierVerdict(
                    ok=False, reason="SENSITIVE_TOPIC", term_id=_rule_id(i))

        # ①' DSP-029 r13 #2：答案裡出現片段標記樣式 ⇒ SCHEMA(marker_in_answer)。
        # 契約寫「步⑥前」，這裡取**最早**的合法位置（①之後、②之前），⛔ 不是放寬：
        # ⚠️ 放在③之後它會變成**不可達的死檢查**——標記字串（16 位十六進位＋來源＋
        # 編號）帶進來的字元在來源原文裡一個都不存在，於是相對覆蓋率一定先判
        # QUOTE_NOT_COVERING，marker_in_answer 永遠輪不到。一條永遠不會觸發的安全
        # 檢查比沒有更糟（它讓人以為這個出口被守著）。量測單位與①⑤⑥⑦同為拼接後的
        # `answer`——掃的字串就是送出去的字串。
        if _UNIT_MARKER_RE.search(answer_nfkc):
            return VerifierVerdict(
                ok=False, reason="SCHEMA", schema_cause="marker_in_answer")

        # ② 逐筆 schema 檢查（DSP-028 (a)(b)(c)）——⛔ 不再比對「句數＝標籤數」：
        # 文字與標籤同筆攜帶後，拼接相等是定義，不是要靠檢查維持的巧合。
        # (a) 非 handoff 卻沒有任何一筆 ⇒ 沒有東西可以驗，一律 SCHEMA
        #     （handoff 在上面已 return，走不到這裡）。
        if not out.sentences:
            return VerifierVerdict(
                ok=False, reason="SCHEMA", schema_cause="empty_sentences")
        # (b) 任一筆 text 全空白 ⇒ SCHEMA（空筆會讓「每個字都屬於某一筆」失去意義）。
        for i, sentence in enumerate(out.sentences):
            if sentence.text.strip() == "":
                return VerifierVerdict(
                    ok=False, reason="SCHEMA", schema_cause="empty_text", sent=i)
        # ②～④ 逐筆 → 逐片段：型別複核（「純」條件降級）→ fact 需 refs → 覆蓋／極性／可引用
        # ⚠️ 一筆可能被模型塞進多個句子（「您好！我們支援批次匯入。」標成 greeting）。
        # 片段**只繼承 `kind`／`refs` 這兩個標籤，⛔ 不繼承驗證結果**——每個非空片段
        # 各自跑 `_effective_kind`（以片段本文判）與③④（比對文字一律用片段本文，
        # ⛔ 不用整筆、⛔ 不用拼接後的 answer）。
        # ⚠️ r11 安全審 F-6（尾隨換行切出的空白片段跳過複核）與「非 fact 片段
        # 不進③④」兩條，已下沉到 `_fact_fragments`——那裡是片段序號的唯一產生點，
        # ⛔ 不得在這裡另寫一份走法（`_pairs_for` 也走同一個產生器，兩處序號
        # 一旦不同，NLI 分數就會配到別的片段上）。
        # ①⑤⑥⑦仍對拼接全文掃描，⛔ 跳過空片段不等於那些字沒被看過。
        for i, f, fragment in self._fact_fragments(out):
            sentence = out.sentences[i]
            if not sentence.refs:
                return VerifierVerdict(ok=False, reason="UNCITED_ASSERTION", sent=i)
            # DSP-029a（r15 #4）：標記解析失敗**只在這裡**致命——被降級為 fact 的
            # 片段所在那一筆。非 fact 筆的 refs 解析失敗 ⛔ 不影響 verdict，維持
            # v4「只看被引用到的」決策：讓模型多寫的裝飾性引用決定整回合生死，
            # 只會憑空推高拒絕率，而真正的風險一定出現在某個事實句的 refs 裡。
            for j in range(len(sentence.refs)):
                cause = resolve_errors.get((i, j))
                if cause is not None:
                    return VerifierVerdict(
                        ok=False, reason="SCHEMA", schema_cause=cause, sent=i)
                # 正對照：既不在 `resolve_errors` 也不在 `resolved`，代表呼叫端傳
                # 進來的兩個 dict 本身不完整（例如自己算了一半）⇒ ⛔ 不得靜默放行。
                if (i, j) not in resolved:
                    raise ValueError(
                        f"verify() 收到不完整的 refs 解析結果：第 {i} 筆第 {j} 個標記"
                        "既不在 resolved 也不在 resolve_errors——請用 "
                        "services.agent.provenance_units.resolve_refs 產生這兩個 dict"
                    )
            # r11 安全審 F-1（量詞寫死）：這個片段必須在**該筆 `refs` 之中**
            # 至少有一個解析結果完整通過③④（長度＋覆蓋＋極性＋citable）。
            # ⛔ 不得以「同筆的別的片段已經通過」代替——那正是跨片段夾帶捏造的出口。
            last_failure: Optional[VerifierVerdict] = None
            best_score: Optional[float] = None
            for j in range(len(sentence.refs)):
                score = None if scores is None else scores.get((i, f, j))
                if score is not None and (best_score is None or score > best_score):
                    best_score = score
                failure = self._verify_ref(
                    i, fragment, resolved[(i, j)], score=score, nli_mode=nli_mode)
                if failure is None:
                    last_failure = None
                    break
                last_failure = failure
            if last_failure is not None:
                if last_failure.reason == "NOT_ENTAILED":
                    # DSP-033：`entail_score` ＝**該片段**在它那一筆所有解析後
                    # 來源句上的最大分（⛔ 不是最後一句的分）——F-1 的量詞是
                    # 「至少一句 ≥ τ」，所以決定生死的是最大值，稽核要看的也是它。
                    last_failure = last_failure.model_copy(
                        update={"entail_score": (
                            None if best_score is None else round(best_score, 4))})
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

    def _verify_ref(
        self,
        sent: int,           # DSP-028：**筆索引**（片段不另編號）
        sentence_text: str,  # DSP-028：**片段本文**（⛔ 不是整筆、⛔ 不是拼接後的 answer）
        ref: ResolvedRef,    # DSP-029a：**解析後**的來源片段（⛔ 不取自模型輸出）
        *,
        score: Optional[float],   # DSP-033：這一對的 p_entail（降級模式為 None）
        nli_mode: bool,
    ) -> Optional[VerifierVerdict]:
        source_unit = ref.quote
        unit_nfkc = _nfkc(source_unit)
        if len(unit_nfkc) < self.rules.min_quote_len:
            # DSP-029：模型不再抄字，這條量的是**來源片段本身太短**（例如只有
            # 「【範本】」這種標籤行）——太短的片段撐不起一個事實斷言。⛔ 不因為
            # 「不是模型的錯」就取消它：短片段仍然是不足的依據。
            return VerifierVerdict(ok=False, reason="QUOTE_TOO_SHORT", sent=sent, quote_len=len(unit_nfkc))

        # `QUOTE_NOT_VERBATIM` 在模型端已不可達（引文是系統從原文切出來的）。
        # 這裡不再有對應分支——拒因列舉仍保留該值（trace 相容），由
        # `tests/unit/agent/test_verifier_req.py` 的**程式層**測試守住
        # 「解析結果必為 provenance 原文的子字串」這個不變量。

        # ③(i) 覆蓋——**兩種語義，看的是哪把尺**：
        #   NLI 模式：只剩絕對下限（有意義字元交集 <4）＝ r18 F-2 保留的
        #     「連四個字都對不上就別談蘊涵」硬拒；DSP-029 的 ratio 分支退場
        #     （它在 181 句上的誤殺是新尺退不掉的那一塊）。
        #   降級模式：回復 DSP-029 的 ratio∧絕對下限（`max()` 取嚴的那個）。
        # ⚠️ 兩種模式**共用 `QUOTE_NOT_COVERING` 這個代碼**，所以拒因分佈要跟
        # `nli_degraded` 一起看，⛔ 不得直接把兩批數字加總比較。
        fragment_chars = _meaningful_chars(sentence_text)
        overlap = fragment_chars & _meaningful_chars(source_unit)
        need = (
            self.rules.min_coverage_chars
            if nli_mode
            else max(
                self.rules.min_coverage_chars,
                math.ceil(_DEGRADED_COVERAGE_RATIO * len(fragment_chars)),
            )
        )
        if len(overlap) < need:
            return VerifierVerdict(ok=False, reason="QUOTE_NOT_COVERING", sent=sent, quote_len=len(unit_nfkc))

        # ③(ii) 極性——NLI 模式走**窄化**版，降級模式走 DSP-021 全極性。
        polarity_term = (
            self._narrow_polarity_term(sentence_text, source_unit)
            if nli_mode
            else self._full_polarity_term(sentence_text, source_unit)
        )
        if polarity_term is not None:
            return VerifierVerdict(
                ok=False, reason="POLARITY_MISMATCH", sent=sent, term_id=polarity_term)

        # DSP-029a：`citable` 隨解析結果一起傳進來，⛔ 不在此二次查 `tool_results`。
        # ⚠️ 位置在 NLI 之前是刻意的：不可引用的來源就算蘊涵成立也不能用，
        # 先擋掉可以少送一對進 NLI，且拒因是比較精確的那一個。
        if not ref.citable:
            return VerifierVerdict(ok=False, reason="SOURCE_NOT_CITABLE", sent=sent)

        # ③(iii) NLI：p_entail < τ ⇒ NOT_ENTAILED。
        # ⚠️ `score is None`（該對錯誤，例如 `hypothesis_too_long`）同樣算不蘊涵——
        # 「算不出分數」⛔ 不得與「分數夠高」同一個結論。
        # ⚠️ `term_id` 固定 None（r18 F-15）：這不是規則集裡任一條規則命中的結果。
        # ⚠️ 這裡填的 `entail_score` 是**這一對**的分數；呼叫端會用該片段所有 ref
        # 的最大分覆寫它（見 `_verify_core`），⛔ 不是在這裡就決定最終值。
        if nli_mode:
            rounded = None if score is None else round(float(score), 4)
            if rounded is None or rounded < self.rules.nli_tau:
                return VerifierVerdict(
                    ok=False, reason="NOT_ENTAILED", sent=sent, entail_score=rounded)

        return None

    # ------------------------------------------------------------------
    def _full_polarity_term(self, sentence_text: str, source_unit: str) -> Optional[str]:
        """DSP-021 全極性（**降級模式**用）：兩側「有沒有否定詞」須一致。

        ⚠️ 這把尺在 181 句上是 71%／13%——誤殺高於現行水準，DSP-033 因此
        ⛔ 不在 NLI 模式保留它。留在降級路徑是為了「服務掛掉時的尺 ＝ 上線前
        那把尺」，⛔ 不是因為它比較好。
        """
        sentence_nfkc = _nfkc(sentence_text)
        unit_nfkc = _nfkc(source_unit)
        sent_hits = [i for i, t in enumerate(self.rules.negation_terms) if t in sentence_nfkc]
        unit_hits = [i for i, t in enumerate(self.rules.negation_terms) if t in unit_nfkc]
        if bool(sent_hits) != bool(unit_hits):
            return _rule_id((sent_hits or unit_hits)[0])
        return None

    def _negation_index_for_root(self, text: str, root: str) -> Optional[int]:
        """`root` 在 `text` 裡是否被否定；是則回**否定詞在 `negation_terms` 的索引**。

        兩種形狀，兩者都只認規則集裡的封閉否定詞表（⛔ 不另立否定前綴表）：
          (a) 否定詞本身就含這個詞根且出現在文字裡（「不支援」⊃「支援」）；
          (b) 否定詞緊貼在詞根之前（「無法」＋「支援」、「沒有」＋「提供」）。
        ⚠️ 回索引而不是布林，是為了讓 `POLARITY_MISMATCH` 的 `term_id` 維持
        「指向 `negation_terms` 的第幾條」這個既有語義——換一張表會讓歷史 trace
        的 `term_id` 指向錯誤的規則集。
        """
        for idx, term in enumerate(self.rules.negation_terms):
            if root and root in term and term in text:
                return idx
        for m in re.finditer(re.escape(root), text):
            prefix = text[: m.start()]
            for idx, term in enumerate(self.rules.negation_terms):
                if prefix.endswith(term):
                    return idx
        return None

    def _narrow_polarity_term(self, sentence_text: str, source_unit: str) -> Optional[str]:
        """**窄化極性**（NLI 模式；r18 F-2）：同一 `assertion_terms` 詞根**兩側皆
        出現**、且**恰一側被否定** ⇒ 極性翻轉。

        ⚠️ 與全極性的差別只有一句話：全極性問「兩邊有沒有否定詞」，窄化極性問
        「**同一件事**在兩邊的肯否定是不是一致」。前者會把「來源提到某個不相干
        的否定」算成不一致（181 句實測誤殺 13%），後者不會（9%，與 NLI 單獨同）。
        ⚠️ 詞根兩側都要出現才判——只有一側出現時「這句話在講的是不是同一件事」
        本來就該交給 NLI 判，⛔ 不由規則層搶答。
        """
        sentence_nfkc = _nfkc(sentence_text)
        unit_nfkc = _nfkc(source_unit)
        for root in self._polarity_roots:
            if root not in sentence_nfkc or root not in unit_nfkc:
                continue
            sent_idx = self._negation_index_for_root(sentence_nfkc, root)
            unit_idx = self._negation_index_for_root(unit_nfkc, root)
            if (sent_idx is None) != (unit_idx is None):
                return _rule_id(sent_idx if sent_idx is not None else unit_idx)
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
    #: 自證的兩種模式（DSP-033 P1-2：兩組假 client 各跑一遍三檔 fixture）。
    #: ⛔ 兩組都是**假** client：`bootstrap.build_runtime` 在啟動路徑上呼叫
    #: `self_test`，而「啟動 ⛔ 不依賴 `/nli` 可用」是 P1-2 的明文。
    SELF_TEST_MODES: tuple = ("nli", "degraded")

    def self_test(self, fixtures_dir: str | Path) -> int:
        """尺自證：`known_fabrications.json` 全拒、`known_good.json` 全放，否則 raise（啟動紅）。

        **DSP-033：兩種模式各跑一遍**——NLI 模式用釘住分數的假 client（分數取自
        案內 `nli_scores`），降級模式用永遠 raise `NliUnavailable` 的假 client。
        ⚠️ 只驗一種模式等於只證明了一半：降級尺是服務掛掉時**真的會生效**的那把
        尺，它若在某次重構裡壞掉，症狀只會在下一次 NLI 中斷時出現。

        **第三檔 `known_open.json`（DSP-029 r13 #1）**：已知**擋不住**的捏造句，
        以 `expect_ok=True` 載入——它們現在確實會被放行，這份檔案的用途是把
        「已知未擋」寫成可執行的事實，而不是讓人以為已經擋住了。
        ⛔ 不得把這些案例塞進 `known_fabrications.json` 宣稱已擋（那會讓自證變成
        假綠）。DSP-033 已把其中「需要管理者權限」一句搬進 `known_fabrications`
        （τ=0.40 下 p_ent 0.36 ⇒ `NOT_ENTAILED`）；另兩句留在本檔並標
        `nli_blind_spot: true`——⛔ 不得宣稱 NLI 擋住了它們。
        回傳 `known_open.json` 的案例數（＝目前仍放行的已知捏造句數），供驗收單列。

        ⚠️ `known_open.json` **不存在時視為 0 筆**——`tests/unit/agent/test_bootstrap_req.py`
        會用只有兩個檔的臨時目錄跑自證。出貨那份 fixture 目錄一定要有它，由
        `test_verifier_req.py::test_shipped_fixtures_include_known_open` 當正對照守住。
        """
        fixtures_dir = Path(fixtures_dir)
        known_open = fixtures_dir / "known_open.json"
        counts = set()
        for mode in self.SELF_TEST_MODES:
            self._assert_all(fixtures_dir / "known_fabrications.json",
                             expect_ok=False, mode=mode)
            self._assert_all(fixtures_dir / "known_good.json",
                             expect_ok=True, mode=mode)
            if known_open.exists():
                counts.add(self._assert_all(known_open, expect_ok=True, mode=mode))
        return counts.pop() if counts else 0

    # ------------------------------------------------------------------
    @staticmethod
    def _fixture_scores(case: dict, keys: list) -> list:
        """案內 `nli_scores` ⇒ 依 `keys` 順序的分數串（NLI 模式假 client 用）。

        `nli_scores` 是 `{"筆:片段:ref": 分數}`，另可用 `"*"` 給預設值；
        **整個鍵不存在時預設 1.0**（＝蘊涵）。理由：既有 fixture 是在 DSP-029
        的尺下寫的，它們要驗的是 floor／極性／結構那幾條，⛔ 不該因為沒標
        NLI 分數就全被 `NOT_ENTAILED` 吃掉——那樣測到的就不是原本那件事了。
        要驗 NLI 拒的案子自己標低分（或標 `null` 模擬 `hypothesis_too_long`）。
        """
        spec = case.get("nli_scores")
        if spec is None:
            return [1.0] * len(keys)
        default = spec.get("*", 1.0)
        return [spec.get(f"{i}:{f}:{j}", default) for (i, f, j) in keys]

    @staticmethod
    def _expected(case: dict, key: str, mode: str, default=None):
        """取案內期望值：`<key>_<mode>` 優先，其次 `<key>`，都沒有就 `default`。

        ⚠️ 用 `in` 判存在而不是取值判真假——`expected_reason: null`（known_good）
        與「沒標」是兩件事，前者要比對、後者不比對。
        """
        scoped = f"{key}_{mode}"
        if scoped in case:
            return case[scoped], True
        if key in case:
            return case[key], True
        return default, False

    def _assert_all(self, path: Path, *, expect_ok: bool, mode: str = "nli") -> int:
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

            # DSP-033：兩組**假** client（⛔ 不觸網、⛔ 不載模型）。
            keys, pairs = self._pairs_for(out, resolved)
            if mode == "degraded":
                client = FakeNliClient(error=NliUnavailable("self_test_degraded_mode"))
            else:
                client = FakeNliClient(scores=self._fixture_scores(case, keys))
            outcome = self._verify_with_client(
                client, out, tool_results, case.get("user_message", ""), case.get("handoff"),
                resolved=resolved, resolve_errors=resolve_errors, keys=keys, pairs=pairs)
            verdict = outcome.verdict

            case_expect_ok, _ = self._expected(case, "expect_ok", mode, expect_ok)
            if verdict.ok != case_expect_ok:
                raise RuntimeError(
                    f"OutputVerifier self_test 失敗（{mode} 模式）：{path.name} 案例 {case.get('id')} "
                    f"預期 ok={case_expect_ok}，實得 {verdict.model_dump()}"
                )
            # r11 安全審 F-3：只比 `ok` 會假綠——fixture 機械轉換若把某案例的違規
            # 性質改掉（例如本來測 QUOTE_NOT_COVERING、轉完變成 SCHEMA），`ok=False`
            # 照樣成立，尺已經不量原本那件事卻沒有人知道。fixture 有 `expected_reason`
            # 這個鍵時，reason 必須相等（known_good 的值是 None，同樣要相等）。
            want_reason, has_reason = self._expected(case, "expected_reason", mode)
            if has_reason and verdict.reason != want_reason:
                raise RuntimeError(
                    f"OutputVerifier self_test 失敗（{mode} 模式）：{path.name} 案例 {case.get('id')} "
                    f"預期 reason={want_reason}，實得 reason={verdict.reason}"
                )
            # 同理（DSP-029 r13 #7）：`SCHEMA` 有八種子成因，只比 `reason` 一樣會假綠——
            # fixture 標了 `expected_schema_cause` 就必須對得上。
            want_cause, has_cause = self._expected(case, "expected_schema_cause", mode)
            if has_cause and verdict.schema_cause != want_cause:
                raise RuntimeError(
                    f"OutputVerifier self_test 失敗（{mode} 模式）：{path.name} 案例 {case.get('id')} "
                    f"預期 schema_cause={want_cause}，實得 schema_cause={verdict.schema_cause}"
                )
            # DSP-033 r18 F-15：`NOT_ENTAILED` 的 `term_id` 必須是 None。
            # ⚠️ 用 `in` 判存在——`"expected_term_id": null` 是「必須為 None」，
            # 沒標才是「不比對」。
            want_term, has_term = self._expected(case, "expected_term_id", mode)
            if has_term and verdict.term_id != want_term:
                raise RuntimeError(
                    f"OutputVerifier self_test 失敗（{mode} 模式）：{path.name} 案例 {case.get('id')} "
                    f"預期 term_id={want_term}，實得 term_id={verdict.term_id}"
                )
            # 正對照：降級模式**必須真的降級**，NLI 模式**必須沒有降級**。
            # 少了這條，兩個模式跑的可能都是同一把尺，而自證會全綠。
            # ⚠️ 例外：`pairs` 為空的案（handoff／敏感／在步③之前就被拒）根本沒有
            # 問過 NLI，那不叫降級——把它算成降級會讓 `nli_degraded` 這個訊號
            # 在產線上被一堆敏感題灌爆，health 的比率也就失去意義。
            expect_degraded = (mode == "degraded") and bool(pairs)
            if outcome.degraded is not expect_degraded:
                raise RuntimeError(
                    f"OutputVerifier self_test 失敗：{path.name} 案例 {case.get('id')} "
                    f"在 {mode} 模式下 degraded={outcome.degraded}（預期 {expect_degraded}）"
                    "——兩模式沒有真的分開跑"
                )
        return len(cases)

    def _verify_with_client(
        self, client, out, tool_results, user_message, handoff, *,
        resolved, resolve_errors, keys, pairs,
    ) -> VerifyOutcome:
        """`verify_async` 的**同步孿生**，⛔ 只給 `self_test` 與假 client 用。

        ⚠️ 它靠 `client.score_sync(...)`，而 `HttpNliClient` 刻意**沒有**這支方法
        ——所以「啟動自證誤打真服務」在型別上就不成立（P1-2）。
        ⚠️ 判定邏輯 ⛔ 不在這裡重寫：它與 `verify_async` 共用 `_verify_core`，
        差別只有取分數那一步是同步的。
        """
        if not pairs:
            return VerifyOutcome(
                self._verify_core(
                    out, tool_results, user_message, handoff,
                    resolved=resolved, resolve_errors=resolve_errors, scores={}),
                nli_model_sha=str(getattr(client, "last_model_sha", "") or ""),
            )
        try:
            raw = client.score_sync(pairs)
        except NliUnavailable as exc:
            return VerifyOutcome(
                self._verify_core(
                    out, tool_results, user_message, handoff,
                    resolved=resolved, resolve_errors=resolve_errors, scores=None),
                degraded=True,
                pairs_capped=isinstance(exc, NliPairsCapped),
                nli_model_sha=str(getattr(client, "last_model_sha", "") or ""),
            )
        if not isinstance(raw, list) or len(raw) != len(pairs):
            return VerifyOutcome(
                self._verify_core(
                    out, tool_results, user_message, handoff,
                    resolved=resolved, resolve_errors=resolve_errors, scores=None),
                degraded=True,
                nli_model_sha=str(getattr(client, "last_model_sha", "") or ""),
            )
        return VerifyOutcome(
            self._verify_core(
                out, tool_results, user_message, handoff,
                resolved=resolved, resolve_errors=resolve_errors,
                scores=dict(zip(keys, raw))),
            nli_model_sha=str(getattr(client, "last_model_sha", "") or ""),
        )


__all__ = ["OutputVerifier", "VerifyOutcome", "split_sentences"]
