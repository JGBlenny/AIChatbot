"""Agent 路徑的上限封閉表（DSP-045）。

業主 2026-09-10 裁：「之後架構是每個團隊自己上 OpenAI key 自己用額度，只要避免
惡意攻擊，目前不用設這麼細，而且不設在 env 根本沒人記得」＋「額度不擋」。

在此之前，`agent.turn`／一般 MCP 工具／`kb.get`／照片／PDF 五道上限各自散在
`mcp_facade.py`／`tools/registry.py`／`image_fetch.py`，各自讀一個同名 env
（`AGENT_TURN_CAP`／`RATE_PER_MIN`／`KB_GET_CAP`／`IMAGE_COUNT_CAP_PER_HOUR`／
`FILE_COUNT_CAP_PER_HOUR`）覆寫。收成這一張表之後：

- 數值**收成一張封閉表**，預設寬鬆到只擋惡意（不是逐團隊、逐業者細分的額度——
  那是「額度不擋」的既有裁決，見 DSP-045 前半、`services/usage_metering.py`）。
- **⛔ 不再讀任何 env 覆寫**——「不設在 env 根本沒人記得」，這條表就是唯一
  的真相來源。想改上限＝改這個檔＋走程式審查，⛔ 不是改 `.env` 就能默默生效。
- 生效值由 `/api/v1/agent/health`（`services/agent/health.py`）的
  `checks.limits` 回報（`effective()`）。

**唯一例外：`AGENT_LIMITS_TEST_OVERRIDE_JSON`**——這是測試鉤子，⛔ 不是給production
用的旋鈕。只有在 `PYTEST_CURRENT_TEST` 存在（即行程正跑在 pytest 底下）時才生效，
值是 JSON object（例：`{"tool_calls_per_minute": 2}`），只認 `AgentLimits` 已有
的欄位名、其餘鍵靜默略過；解析失敗或行程不是 pytest ⇒ 一律退回預設值。這讓既有
「設一個很小的上限、斷言 `RATE_LIMITED`」的單元測試不必逐一改寫成直接建
`AgentLimits(...)` 物件再想辦法注入。

目標架構（BYO OpenAI key per team，額度自付）另立設計，本檔只記方向、不實作。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, fields, replace
from typing import Any


@dataclass(frozen=True)
class AgentLimits:
    """封閉欄位——五道上限的預設值（DSP-045）。每回合預算（`Budget`）不在此，
    仍由既有 `services/agent/bootstrap.py` 管（`AGENT_BUDGET_*` env，未變動）。"""

    turns_per_hour: int = 1200
    tool_calls_per_minute: int = 600
    kb_get_per_hour: int = 3000
    images_per_hour: int = 600
    files_per_hour: int = 100


_DEFAULT_LIMITS = AgentLimits()

#: 測試鉤子的 env 名（見模組 docstring）。⛔ 唯一允許被讀取的 env——不是給
#: production 用的第二種覆寫管道。
AGENT_LIMITS_TEST_OVERRIDE_ENV = "AGENT_LIMITS_TEST_OVERRIDE_JSON"

_VALID_FIELDS = {f.name for f in fields(AgentLimits)}


def _resolve() -> AgentLimits:
    """算出這一刻生效的 `AgentLimits`。非 pytest 行程／未設鉤子／解析失敗
    ⇒ 一律 `_DEFAULT_LIMITS`（fail-closed 回預設，⛔ 不是回寬鬆值）。"""
    if os.environ.get("PYTEST_CURRENT_TEST") is None:
        return _DEFAULT_LIMITS
    raw = os.environ.get(AGENT_LIMITS_TEST_OVERRIDE_ENV)
    if not raw:
        return _DEFAULT_LIMITS
    try:
        overrides: Any = json.loads(raw)
    except (ValueError, TypeError):
        return _DEFAULT_LIMITS
    if not isinstance(overrides, dict):
        return _DEFAULT_LIMITS
    filtered = {k: v for k, v in overrides.items() if k in _VALID_FIELDS}
    if not filtered:
        return _DEFAULT_LIMITS
    try:
        return replace(_DEFAULT_LIMITS, **filtered)
    except TypeError:
        return _DEFAULT_LIMITS


class _LimitsProxy:
    """`LIMITS.<欄位>` 存取時即時解析（讓測試鉤子在既有的 `monkeypatch.setenv`
    使用型態下仍然生效——`AgentLimits` 本身是 frozen dataclass，若 `LIMITS` 是
    在 import 當下就算好的固定實例，測試在函式內才設的 env 不會反映出來）。
    產品路徑（`PYTEST_CURRENT_TEST` 不存在）下，這裡解析出來的值＝`_DEFAULT_LIMITS`，
    等同一份不會變的封閉表。"""

    def __getattr__(self, name: str) -> Any:
        return getattr(_resolve(), name)

    def __repr__(self) -> str:  # pragma: no cover - 除錯用
        return f"LIMITS({_resolve()!r})"


#: 模組級單例。讀取處一律 `LIMITS.<欄位>`，⛔ 不各自重算。
LIMITS = _LimitsProxy()


def effective() -> dict:
    """供健檢（`services/agent/health.py` 的 `checks.limits`）：這一刻生效的
    五個數字，一個 dict、只列數字。"""
    current = _resolve()
    return {f.name: getattr(current, f.name) for f in fields(current)}
