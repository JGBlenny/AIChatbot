"""`provenance_units`／`resolve_refs`（spec agentic-mcp-orchestration・DSP-029／DSP-029a）。

**編號側與解析側的唯一共用點**。DSP-029 把 `Citation` 從「模型抄一段引文」改成
「模型填一個來源片段編號」之後，系統有兩處要把同一份 `Provenance.text` 切成同一串
片段：

  1. **編號側**——送給模型的資料段，每個片段行首貼
     `[{nonce}:{tool_call_id}:{source}§{i}]`
     （`services/agent/prompt_assembler.py:wrap_provenance_data`／`unit_marker`）；
  2. **解析側**——模型把整串標記原樣照抄進 `Sentence.refs` 之後，把它拆回
     `(nonce, tool_call_id, source, i)` 並取出第 i 個片段
     （本檔 `resolve_refs`，由 `services/agent/runtime.py` 呼叫）。

⚠️ **兩側各寫一份切法就是這個設計的致命傷**：切法只要差一個空片段，模型看到的
`§3` 與系統解析的第 3 片段就不是同一句，而失敗方向是**放行**（解析出來的是別的
句子，覆蓋檢查照樣可能過）。故本檔只有一個切法函式，兩側都只准呼叫它
（r13 F-B；`tests/unit/agent/test_prompt_assembler_req.py` 有兩側對齊測試）。

切法本身 ⛔ 不在本檔重寫：直接用 `services.agent.verifier.split_sentences`
——Verifier 步②把模型的一筆拆成片段用的也是它，三處同一把尺。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional



# ---------------------------------------------------------------------------
# 切句（Verifier 步②與 unit 編號共用的唯一實作；原在 verifier.py，DSP-029 落地取捨④下沉）
# ---------------------------------------------------------------------------

_SENTENCE_ENDS: tuple[str, ...] = ("。", "！", "!", "？", "?", "\n")


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



def split_sentences(text: str) -> list[str]:
    """公開版切句（DSP-021）：呼叫端要重現「系統怎麼切片段」時用它，
    與 `verify()` 步②(d) 用的是同一個函式，⛔ 不得另寫一份規則。

    DSP-028 後 Runtime 的 SCHEMA 回饋改為直接指出結構成因（空陣列／第 N 筆空 text／
    第 N 筆的標記解析不了），不再回報切句結果；此函式仍公開，
    供測試與工具重現片段邊界。"""
    return _split_sentences(text)


# ---------------------------------------------------------------------------
# 大綱的保留 tool_call_id（原正規化函式已於 DSP-029a 退役，見下方說明）
# ---------------------------------------------------------------------------

#: 大綱章節預載成 provenance 時用的保留 `tool_call_id`（DSP-020）。
#: ⚠️ **`_canonicalize_outline_sources` 已於 DSP-029a 退役、函式與呼叫點一併刪除**：
#: 它做的是「把模型自己填的 `source` 標籤收斂成一種寫法」（去掉誤抄的中文標題、
#: 補回被吃掉的 `outline:` 前綴）。DSP-029a 之後模型不再自己填 `source`——它照抄
#: 整串標記，標籤沒有第二種寫法可以被正規化，這個函式的前提在資料上就不存在了。
#: ⛔ 不要因為「留著也不會怎樣」而復活它：它會在標記本身被抄壞時把壞標記改成
#: 一個看似合法的來源，失敗方向是放行。
OUTLINE_TOOL_CALL_ID = "outline"


def provenance_units(text: str) -> list[str]:
    """`Provenance.text` ⇒ 可被引用的片段串（0-based，順序即編號）。

    ＝ `split_sentences(text)` 去掉 `strip() == ""` 的片段。

    ⚠️ **空片段一定要丟掉、⛔ 不能保留成佔位**：大綱章節本文是多行（每列一行
    `- 摘要：答案`），`split_sentences` 把 `\n` 也當句末標點，於是「句號後緊接
    換行」會切出一個只有 `\n` 的片段。留著它，模型在資料段裡會看到一個空的
    `[…§n]` 行——那既是可被引用的空引文（覆蓋檢查對空字串沒有意義），也讓編號
    平白多出模型無法對應的洞。
    """
    return [piece for piece in split_sentences(text or "") if piece.strip() != ""]


def find_provenance(tool_results: dict, tool_call_id: str, source: str) -> Optional[Any]:
    """在某次工具回傳裡依 `source` **完全相等**找 provenance；找不到回 `None`。

    ⚠️ DSP-029 之後 `source` 是**定址的一部分**（`(tool_call_id, source, unit)`），
    ⛔ 不再有 DSP-021 那種「標籤錯但引文逐字出現在同一次回傳的別筆 provenance ⇒
    仍放行」的補救——那條補救的前提是「引文本身可以獨立驗真」，改成指向編號後
    引文是**算出來的**，標籤錯就等於指到別的句子，補救會直接變成放行捏造。
    ⚠️ DSP-029a：三段定址全部來自模型照抄的標記，⛔ 已無任何機械正規化在它之前。
    """
    tool_result = tool_results.get(tool_call_id)
    for prov in (getattr(tool_result, "provenance", None) or []):
        if prov.source == source:
            return prov
    return None


#: 一筆 `Sentence.refs` 字串的合法形狀：`[{nonce}:{tool_call_id}:{source}§{i}]`。
#: **對方括號與前後空白寬容**（模型常漏抄一邊括號或帶進空白，那不是引用錯誤，
#: 是抄寫毛邊）；⛔ 但對 `nonce`／三段結構本身不寬容——nonce 是防偽的唯一憑據。
#: 第三段（`source`）允許含 `:`（`kb:3600`／`outline:lease`／`jgb2:bills#ref`），
#: 所以它吃到**最後一個** `§` 為止；第二段（`tool_call_id`）⛔ 不含 `:`。
_REF_RE = re.compile(
    r"^\s*\[?([0-9A-Za-z]{8,64}):([^:\]\s]+):([^\]\s]+)§(\d+)\]?\s*$"
)


@dataclass(frozen=True)
class ResolvedRef:
    """一筆 `refs` 解析成功的結果：**引文原文、可引用旗標、來源代碼**。

    ⛔ 不寫回 `AgentOutput`／`Sentence`（r13 F-A）：解析後的原文一旦掛在模型輸出上，
    就會跟著 `decision_snapshot`／trace 外流，那正是 2.6 security review P2 擋掉的事。
    本物件只在 Runtime → Verifier 這一段記憶體內傳遞。
    """

    quote: str
    citable: bool
    source: str


def resolve_refs(
    out: Any, tool_results_by_id: dict, nonce: str
) -> tuple[dict[tuple[int, int], ResolvedRef], dict[tuple[int, int], str]]:
    """`AgentOutput.sentences[*].refs` ⇒ `(resolved, errors)`，鍵皆為 `(筆索引, ref 索引)`。

    - `resolved[(i, j)]` ＝ 第 i 筆第 j 個標記解析出來的 `ResolvedRef`；
    - `errors[(i, j)]` ＝ 該標記的 `schema_cause`，兩個 dict 的鍵互斥。

    四種失敗（DSP-029a）：
      * 格式不合、或 `nonce` 不等於**本回合**的 nonce ⇒ `ref_invalid`
        （nonce 內含即證明這串標記出自本回合的資料段，順帶把「標記抄進 text」
        與「憑空捏一個標記」用同一把尺擋掉）；
      * `(tool_call_id, source)` 在 `tool_results_by_id` 找不到 provenance
        ⇒ `ref_source_not_found`；
      * 同一次工具回傳裡同名 `source` 有多筆且**文字不同** ⇒ `ref_ambiguous`
        （同文取任一：那不是歧義，是重複）；
      * `provenance_units(text)[i]` 越界 ⇒ `unit_out_of_range`。

    ⚠️ 編號一律走 `provenance_units`，⛔ 不在此另寫切法（r13 F-B）。
    """
    resolved: dict[tuple[int, int], ResolvedRef] = {}
    errors: dict[tuple[int, int], str] = {}
    for i, sentence in enumerate(getattr(out, "sentences", None) or []):
        for j, ref in enumerate(getattr(sentence, "refs", None) or []):
            match = _REF_RE.match(ref if isinstance(ref, str) else "")
            if match is None or match.group(1) != nonce:
                errors[(i, j)] = "ref_invalid"
                continue
            tool_call_id, source, index = match.group(2), match.group(3), int(match.group(4))
            prov = find_provenance(tool_results_by_id, tool_call_id, source)
            if prov is None:
                errors[(i, j)] = "ref_source_not_found"
                continue
            # 歧義只在**同一次工具回傳內**成立（跨呼叫由 `tool_call_id` 分開）——
            # 主流程 search→get 是兩個 tool_call，故不會撞到這條；它是後備。
            tool_result = tool_results_by_id.get(tool_call_id)
            same_source = [
                p for p in (getattr(tool_result, "provenance", None) or [])
                if p.source == source
            ]
            if len({p.text for p in same_source}) > 1:
                errors[(i, j)] = "ref_ambiguous"
                continue
            units = provenance_units(prov.text)
            if index >= len(units):
                errors[(i, j)] = "unit_out_of_range"
                continue
            resolved[(i, j)] = ResolvedRef(
                quote=units[index], citable=bool(prov.citable), source=source)
    return resolved, errors


__all__ = ["OUTLINE_TOOL_CALL_ID", "ResolvedRef", "provenance_units",
           "find_provenance", "resolve_refs"]
