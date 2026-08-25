"""把 brain 替身接到任務 8 之後的介面（需求 5.2）。

`conversational_engine` 自 2026-08-26 起呼叫 `conversational_step_result()`
（回 `StepResult`），而非舊的 `conversational_step()`（回 dict）。
替身若只 stub 舊方法，引擎會拿到一個不可 await 的 MagicMock → 全數降級。

本 helper **兩個都接**：新介面回 `StepResult`、舊介面維持回 payload，
使既有測試的斷言逐位不變，同時涵蓋相容層。
"""
from unittest.mock import AsyncMock

from services.llm_answer_optimizer import StepResult


def as_step_result(payload):
    """payload（dict 或 None）→ `StepResult`；None 代表模型沒給可解析內容。"""
    if payload is None:
        return None
    return StepResult(
        payload=payload,
        scope="switch" if payload.get("scope") == "switch" else "stay",
        face=payload.get("face") if isinstance(payload.get("face"), str) else None,
        delegate_facet_key=payload.get("delegate_facet_key"),
    )


def stub_step(optimizer, payload=None, *, called: bool = True):
    """把 `optimizer` 的兩個 brain 介面都接上同一份 payload。

    `called=False`：只掛可斷言「沒被呼叫」的 AsyncMock，不預設回傳值。
    """
    if not called:
        optimizer.conversational_step = AsyncMock()
        optimizer.conversational_step_result = AsyncMock()
        return optimizer
    optimizer.conversational_step = AsyncMock(return_value=payload)
    optimizer.conversational_step_result = AsyncMock(return_value=as_step_result(payload))
    return optimizer
