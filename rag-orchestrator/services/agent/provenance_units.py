"""`provenance_units`／`resolve_citations`（spec agentic-mcp-orchestration・DSP-029）。

**編號側與解析側的唯一共用點**。DSP-029 把 `Citation` 從「模型抄一段引文」改成
「模型填一個來源片段編號」之後，系統有兩處要把同一份 `Provenance.text` 切成同一串
片段：

  1. **編號側**——送給模型的資料段，每個片段行首貼 `[{nonce}:{source}§{i}]`
     （`services/agent/prompt_assembler.py:wrap_provenance_data`）；
  2. **解析側**——模型回 `unit=i` 之後，把第 i 個片段解析回引文
     （本檔 `resolve_citations`，由 `services/agent/runtime.py` 呼叫）。

⚠️ **兩側各寫一份切法就是這個設計的致命傷**：切法只要差一個空片段，模型看到的
`§3` 與系統解析的第 3 片段就不是同一句，而失敗方向是**放行**（解析出來的是別的
句子，覆蓋檢查照樣可能過）。故本檔只有一個切法函式，兩側都只准呼叫它
（r13 F-B；`tests/unit/agent/test_prompt_assembler_req.py` 有兩側對齊測試）。

切法本身 ⛔ 不在本檔重寫：直接用 `services.agent.verifier.split_sentences`
——Verifier 步②把模型的一筆拆成片段用的也是它，三處同一把尺。
"""
from __future__ import annotations

from typing import Any, Optional

from services.agent.output_schema import AgentOutput



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

    DSP-028 後 Runtime 的 SCHEMA 回饋改為直接指出「空陣列／第 N 筆空 text／
    第 N 筆 cite 越界」三種原因，不再回報切句結果；此函式仍公開，
    供測試與工具重現片段邊界。"""
    return _split_sentences(text)


# ---------------------------------------------------------------------------
# 大綱保留 tool_call_id 與 source 機械正規化（原在 runtime.py，下沉以解 verifier↔runtime 循環）
# ---------------------------------------------------------------------------

OUTLINE_TOOL_CALL_ID = "outline"


def _canonicalize_outline_sources(out: AgentOutput) -> AgentOutput:
    """DSP-021：只對 `tool_call_id == OUTLINE_TOOL_CALL_ID` 的引用做**機械**正規化——
    去掉 id 後面誤抄的標題（`outline:listing 房源` → `outline:listing`）、補回被吃掉的
    `outline:` 前綴（`positioning` → `outline:positioning`）。真線路 2026-09-05 兩種都出現過，
    而 Verifier 找不到來源時回的是 QUOTE_NOT_VERBATIM（引文其實逐字）。
    ⛔ 不碰 `unit`、不碰其他 tool_call_id：這不是放寬尺，是把「同一個 id 的兩種寫法」
    收斂成一種，section id 仍要與 provenance 完全相等才解析得到片段。

    ⚠️ DSP-029 之後這條**更要緊**：`source` 從元資料變成定址的一部分
    （`(tool_call_id, source, unit)`），標籤錯不再有「引文逐字仍放行」的補救，
    直接就是 `SCHEMA(source_not_found)`。"""
    if not out.citations:
        return out
    changed = False
    fixed = []
    for c in out.citations:
        if c.tool_call_id == OUTLINE_TOOL_CALL_ID:
            token = (c.source or "").strip().split()[0] if (c.source or "").strip() else ""
            if token and not token.startswith("outline:"):
                token = f"outline:{token}"
            if token != c.source:
                c = c.model_copy(update={"source": token})
                changed = True
        fixed.append(c)
    return out.model_copy(update={"citations": fixed}) if changed else out


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
    大綱 `source` 的兩種抄錯（帶標題／缺前綴）仍由
    `runtime._canonicalize_outline_sources` 機械正規化收斂。
    """
    tool_result = tool_results.get(tool_call_id)
    for prov in (getattr(tool_result, "provenance", None) or []):
        if prov.source == source:
            return prov
    return None


def resolve_citations(
    out: Any, tool_results: dict
) -> tuple[dict[int, str], dict[int, str]]:
    """`AgentOutput.citations` ⇒ `(resolved, errors)`。

    - `resolved[i]` ＝ 第 i 筆引用解析出來的**來源片段原文**；
    - `errors[i]` ＝ 該筆解析失敗的 `schema_cause`
      （`source_not_found`／`unit_out_of_range`），兩個 dict 的鍵互斥。

    ⛔ **解析結果不寫回 `AgentOutput`／`Citation`**（r13 F-A）：回傳新的 dict，
    由呼叫端另行傳給 Verifier。負數 `unit` 一律算越界——python 的 `units[-1]`
    會靜靜取到最後一個片段，那正是 r11 F-5 在 `cite` 索引上擋過的同一型繞道。
    """
    resolved: dict[int, str] = {}
    errors: dict[int, str] = {}
    for i, citation in enumerate(getattr(out, "citations", None) or []):
        prov = find_provenance(tool_results, citation.tool_call_id, citation.source)
        if prov is None:
            errors[i] = "source_not_found"
            continue
        units = provenance_units(prov.text)
        unit = citation.unit
        if (
            not isinstance(unit, int)
            or isinstance(unit, bool)
            or unit < 0
            or unit >= len(units)
        ):
            errors[i] = "unit_out_of_range"
            continue
        resolved[i] = units[unit]
    return resolved, errors


__all__ = ["provenance_units", "find_provenance", "resolve_citations"]
