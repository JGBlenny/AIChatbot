"""模型前的程式段（Plan R R1｜`inputs/plan-structural-refactor-20260910.md` §0）。

`_run_turn_body` 在叫模型之前有**六個程式終止路徑**，順序本身是契約
（各段的理由逐條抄自原 `runtime.py`，⛔ 一個條件、一個順序都沒有改）：

  ① 文件回合 ⛔ 不接受 `confirm_submit`（排在確認段**之前**——確認段一進去就會
     兌現，那時候再擋已經來不及）；
  ② 文件擷取不出可用欄位 ⇒ 固定句，⛔ 不進模型；
  ③ 照片的三條程式終止路徑（失敗／逾時／要先問分類）；
  ④ 確認段（三顆按鈕的機器值）——DSP-038／W3，**排在同題重問快取之前**；
  ⑤ 清單點選段（`select:<type>:<id>`）——W8 (1)，理由同上；
  ⑥ handoff 快取重播（同題重問）。

⚠️ **`handoff_cache` 的 `setdefault` 排在 ⑤ 之後**（逐字保留原順序）：提早建這個
鍵，會讓每一個從 ①–⑤ 早退的回合都在 `agent_state` 裡多出一個 `handoff_cache`
空 dict——那是會被序列化落 `form_sessions.collected_data` 的狀態形狀改變。

⛔ **本檔不 import `runtime`**（那會成環）：需要的 runtime 方法一律經傳進來的
`rt`（`AgentRuntime` 實例）呼叫；純函式（`_parse_confirm_value`／`_cache_key`）
的結果由呼叫端算好傳進來——兩者都是純函式，提前算 ⛔ 不改變任何行為。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from services.agent.turn_context import (
    LAST_ASK_TARGET_KEY,
    TurnResult,
    TurnTrace,
    _append_dialog,
    _emit_agent_decision,
)


@dataclass
class ProgramSegmentOutcome:
    """`run_program_segments` 的回傳。

    `result` 非 `None` ⇒ 這一回合到此為止（⛔ 不進模型）。`cache`／`cache_key`
    只有在**六段都沒有命中**時才有意義——`cache` 是
    `agent_state.setdefault("handoff_cache", {})` 的那一個物件（同一個 dict，
    ⛔ 不是副本），之後由 `exit_gates.finalize` 寫入。
    """

    result: Optional[TurnResult] = None
    cache: Optional[dict] = None
    cache_key: str = ""


async def run_program_segments(
    rt: Any, identity: Any, user_message: str, agent_state: dict, *,
    image: Any, document: Any, trace_id: str, start: float,
    doc_trace: dict, confirm_value: Optional[tuple], cache_key: str,
) -> ProgramSegmentOutcome:
    """模型前的六段；命中任一段即回 `ProgramSegmentOutcome(result=...)`。"""
    # W9-1 落點①：文件回合 ⛔ 不接受 `confirm_submit`——排在確認段**之前**
    # （確認段一進去就會兌現，那時候再擋已經來不及）。
    if document is not None and confirm_value is not None:
        return ProgramSegmentOutcome(result=rt._document_turn_no_write(
            document, agent_state=agent_state, user_message=user_message,
            trace_id=trace_id, start=start,
        ))
    # W9 U2：擷取不出可用欄位 ⇒ 固定句，⛔ 不進模型（排在最前，同影像三條）。
    document_turn = rt._document_program_turn(
        document, agent_state=agent_state, user_message=user_message,
        trace_id=trace_id, start=start,
    )
    if document_turn is not None:
        return ProgramSegmentOutcome(result=document_turn)
    # W8 (2)：照片的三條程式終止路徑**排在最前**——失敗／逾時／要先問分類的
    # 回合根本不該進確認段、快取或模型。
    image_turn = rt._image_program_turn(
        image, agent_state=agent_state, user_message=user_message,
        trace_id=trace_id, start=start,
    )
    if image_turn is not None:
        return ProgramSegmentOutcome(result=image_turn)
    # DSP-038／W3：⚠️ **排在同題重問快取之前**——機器值不是「一題」，
    # 它是一次狀態轉移；讓它先落進快取比對只會多一次無謂的字串雜湊。
    confirmed = await rt._run_confirm_segment(
        identity, user_message, agent_state, trace_id, start
    )
    if confirmed is not None:
        return ProgramSegmentOutcome(result=confirmed)
    # W8 (1)：清單點選機器值同樣**排在同題重問快取之前**（理由同上：它是
    # 一次狀態轉移，不是「一題」）。兩段的正則值域互斥（`confirm_*:` vs
    # `select:`），⛔ 順序不影響結果，排在後面只是讓既有的確認鏈先判。
    selected = await rt._run_select_segment(
        identity, user_message, agent_state, trace_id, start
    )
    if selected is not None:
        return ProgramSegmentOutcome(result=selected)
    cache = agent_state.setdefault("handoff_cache", {})

    cached = cache.get(cache_key)
    if cached is not None:
        trace = TurnTrace(
            trace_id=trace_id,
            llm_calls=0,
            final_kind="handoff",
            handoff_reason=(cached.get("handoff") or {}).get("reason"),
            latency_ms=int((rt._clock() - start) * 1000),
            violations=[f"replayed_from:{cached.get('trace_id', '')}"],
            # W9 U2：重播出口同樣標明「這一回合帶了文件」——⛔ 不留預設值
            # 假裝沒帶（稽核上「有帶文件卻走重播」正是要看得見的事）。
            **doc_trace,
        )
        _emit_agent_decision(trace)
        _append_dialog(agent_state, user_message, cached.get("answer", ""))
        # T1：三個寫點之三（plan-verifier r3 #1）——重播出口既不經
        # `_finalize` 也不經 `_finish_confirm_turn`，⛔ 不寫就會讓上一回合的
        # 追問對象跨過一個完整回合殘留下來。
        agent_state[LAST_ASK_TARGET_KEY] = None
        return ProgramSegmentOutcome(result=TurnResult(
            kind="handoff",
            answer=cached.get("answer", ""),
            handoff=cached.get("handoff"),
            quick_replies=list(cached.get("quick_replies", [])),
            trace=trace,
        ))
    return ProgramSegmentOutcome(result=None, cache=cache, cache_key=cache_key)
