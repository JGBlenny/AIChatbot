"""`Budget`（spec agentic-mcp-orchestration・任務 2.1｜design 元件 1）。

design 只定義了不可變的預算「上限」（`Budget`）；本檔另加 `BudgetCounters`——
一次 `run_turn` 內部的可變計數器，**不是 design 型別**，純粹是
`AgentRuntime` 記帳用的內部小物件，⛔ 不對外（不進 `TurnTrace`／不進
`TurnResult`）。

**計數語意（design 元件 1 預算計數表，`runtime.py` 逐事件呼叫這裡的方法）**：
- 模型發出的每一個 tool call（含被丟棄、含身分鍵、含逾時重試）都呼叫
  `BudgetCounters.tool_calls += 1`。
- Verifier 拒／schema 不符各呼叫 `BudgetCounters.rewrites += 1`。
- `tool_call_exhausted`／`rewrite_exhausted` 用 `>=`：`max_tool_calls=4`
  代表模型最多能把 4 次 tool call 都用掉，第 5 次嘗試才會被擋下；
  `max_rewrites=2` 代表 Verifier／schema 最多能拒兩次，兩次都拒即固定句
  （即「拒→重寫→再拒→固定句」——第 2 次拒絕時已達門檻，不再送第 3 次修正
  機會）。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Budget:
    """design 元件 1；不可變，一個 `AgentRuntime` 實例共用同一份。"""

    max_tool_calls: int = 4
    max_rewrites: int = 2
    deadline_s: float = 20.0


@dataclass
class BudgetCounters:
    """單一 `run_turn` 呼叫內的可變計數器（⛔ 非 design 型別，內部記帳用）。"""

    tool_calls: int = 0
    rewrites: int = 0

    def tool_call_exhausted(self, budget: Budget) -> bool:
        return self.tool_calls >= budget.max_tool_calls

    def rewrite_exhausted(self, budget: Budget) -> bool:
        return self.rewrites >= budget.max_rewrites
