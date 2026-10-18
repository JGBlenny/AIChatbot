"""模型原始輸出的推理段與 JSON 擷取（主迴圈與寫入意圖呼叫共用）。

主線第 1 步「正式接線（本地替換 gpt-oss）」（`plan-oss-wiring-step1-20261018.md` §3.2）：
Bedrock Chat Completions 的 gpt-oss 把推理以 `<reasoning>…</reasoning>` 夾在 `content` 最前面
（第 0 步探測 Q2：`message` 只有 content／refusal／role 三鍵），assistant 訊息的 `reasoning`／
`reasoning_content` 欄位不會進 prompt（Q3：prompt_tokens 差 0），`reasoning: {exclude: true}` 收下但
不生效（Q1）⇒ 只能在程式端剝除。推理原文 ⛔ 給使用者看、⛔ 帶進下一次取樣
（OpenAI「handle raw CoT」：「You therefore should not show raw CoT to end users.」）。

- `final_segment`：只取**最後一個 `</reasoning>` 之後**的最終段——推理段裡的 JSON 樣字串
  ⛔ 搶先被解析；有 `<reasoning>` 卻沒收尾 ⇒ 沒有最終段（`None`）。
- `iter_json_objects`：對文字**逐個 `{` 位置**試 `raw_decode`，依序產出解得出的頂層物件
  （解出後跳過其範圍，巢狀的不另算）——容忍前綴雜字（2026-10-17 實測 strict 輸出前多了「以下」）
  與後綴雜字。

⛔ 本模組不判斷值域，也不決定要不要清理（主迴圈由 `AgentRuntime(clean_llm_output=…)` 開關決定）。
"""
from __future__ import annotations

import json
from typing import Any, Final, Iterator, Optional

REASONING_OPEN: Final[str] = "<reasoning>"
REASONING_CLOSE: Final[str] = "</reasoning>"


def has_reasoning(content: Any) -> bool:
    """`content` 是否夾了推理標籤（開或關任一）。"""
    return isinstance(content, str) and (REASONING_OPEN in content or REASONING_CLOSE in content)


def final_segment(content: Any) -> Optional[str]:
    """最後一個 `</reasoning>` 之後的文字；沒有標籤 ⇒ 原文；有開頭沒收尾或非字串 ⇒ `None`。"""
    if not isinstance(content, str):
        return None
    close = content.rfind(REASONING_CLOSE)
    if close >= 0:
        return content[close + len(REASONING_CLOSE):]
    if REASONING_OPEN in content:
        return None
    return content


def iter_json_objects(text: str) -> Iterator[Any]:
    """依出現順序產出 `text` 中每個解得出的頂層 JSON 值（只從 `{` 起解）。"""
    decoder = json.JSONDecoder()
    i = text.find("{")
    while i >= 0:
        try:
            obj, end = decoder.raw_decode(text, i)
        except ValueError:
            i = text.find("{", i + 1)
            continue
        yield obj
        i = text.find("{", max(end, i + 1))
