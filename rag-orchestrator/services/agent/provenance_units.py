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

from services.agent.verifier import split_sentences


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
