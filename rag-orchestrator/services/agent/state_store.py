"""`NamespacedStateStore`（spec agentic-mcp-orchestration・任務 2.6）。

`/mcp` 進來的回合狀態**不得以裸 `session_id` 存取**——這是 2.6／2.7 前置
security review 的唯一 P1（`.kiro/specs/agentic-mcp-orchestration/reviews/
m1-security-review-2.6-2.7.md`）：

> `conversational_engine.get_state/_save/_close` 與
> `form_manager._get_session_state_sync` 都**沒有 vendor 條件**（正對照：
> `form_manager.py` 另一處有 `vendor_id` 條件，證明 grep 有效）⇒ 持 vendor 2
> 的 key、帶他人的 `session_id`，就能讀寫他人的對話。

處置＝**命名空間鍵**：`mcp:{api_key_id}:{vendor_id}:{session_id}`。
REST 路徑（`routers/agent_entry.py:EngineStateStore`）維持裸 `session_id` 不變，
兩條路徑因此**天然分池**，⛔ 不共用會話列。

## 為什麼前綴不會被撞開
`api_key_id` 與 `vendor_id` 都是**整數**（`api_keys.id`／`vendors.id`），
前綴 `mcp:<int>:<int>:` 裡不可能出現由呼叫端控制的 `:`；唯一由呼叫端控制的
是最後一段 `session_id`。因此「不同 (key, vendor) 卻算出同一把鍵」在型別層
就不可能發生——⛔ 這不是靠字串跳脫維持的，別把兩個 id 改成字串。

## 為什麼不另寫 SQL
`load`／`start`／`save` 一律轉呼 `ConversationalEngine.get_state`／`_start`／
`_save`（同一張 `form_sessions`、同一組 SQL）。⛔ 不在本檔寫第二份 SQL——
兩份 SQL 會各自演化，而「隔離謂詞單一來源」是本專案的既有紀律。

## fail-closed
`api_key_id`／`vendor_id` 缺、或算出的鍵超過 `form_sessions.session_id`
的 `VARCHAR(100)`（實查 2026-09-05）⇒ 建構當下 `raise ValueError`。
⛔ 不「退回裸 session_id」——那正是被擋掉的那條路。
"""
from __future__ import annotations

import time
from typing import Any, Optional

from services.agent.agent_session import AgentSession

#: `form_sessions.session_id` 的欄位長度（實查測試庫 information_schema，2026-09-05）。
#: 超過會在 INSERT 當下被 DB 拒；寧可在組鍵時就明說，⛔ 不讓它變成一次 500。
SESSION_ID_MAX_LEN = 100

#: `_start` 的 `config_key` 舊預設（任務 2.6 brief 當時 M1 的 `/mcp` 對話對象只
#: 有 prospect）。**L8（Plan R R3）**：REST 路徑（`routers/agent_entry.py`）
#: 已經是 `f"agent:{identity.audience}"`（依受眾），`/mcp` 這邊落後——
#: `NamespacedStateStore.start()` 新增 `audience` 參數依受眾組字串，這個舊
#: 預設值**原封不動**保留當「沒給 `config_key`／`audience` 時」的相容值
#: （⛔ 不改既有列的鍵值——舊列的 `config_key='agent:prospect'` 讀取邏輯
#: 不看這個值，仍照常相容）。
DEFAULT_CONFIG_KEY = "agent:prospect"


def config_key_for(audience: Optional[str]) -> str:
    """`agent:<audience>`；`audience` 缺值 ⇒ 回舊預設 `DEFAULT_CONFIG_KEY`
    （L8｜Plan R R3，相容既有呼叫端不傳 `audience` 的路徑）。"""
    if not audience:
        return DEFAULT_CONFIG_KEY
    return f"agent:{audience}"

#: 命名空間前綴，⛔ 不得省略（見模組 docstring）。
NAMESPACE = "mcp"

#: W8 (5)／DSP-042：同一個 `session_id` 隔多久再進算「新的一段對話」。
#: 30 分鐘（Plan W8 (5)），⛔ 不從 env 讀——這是對外契約的一部分
#: （`AgentTurnOutput.session_expired` 何時為 true），可調等於呼叫端無從預期。
SESSION_IDLE_TTL_S = 1800

#: 過期戳在 `state["agent"]` 裡的鍵。
#: ⚠️ **為什麼不看 `form_sessions.updated_at`**（security-reviewer S8-7）：
#: 那個欄位**不存在**（實查 `services/conversational_engine.py` 的 `_save`：
#: 它更新的是 `last_activity_at`，而 `get_state` 也不回這一欄）。照字面實作
#: 只會得到一個永遠不過期的閘。故過期戳存進 state JSON，跟著既有
#: `collected_data` 一起落地，⛔ 不新增 DB 欄位、⛔ 不另寫第二份 SQL。
LAST_TURN_AT_KEY = "last_turn_at"


def stamp_last_turn(agent_state: dict, now: Optional[float] = None) -> float:
    """把「這一回合結束的時刻」寫進 `agent_state`；回傳寫進去的值。

    ⛔ 呼叫端不得自己 `agent_state["last_turn_at"] = …`——鍵名只有這裡知道。
    """
    ts = time.time() if now is None else float(now)
    AgentSession(agent_state).write_last_turn_at(ts)
    return ts


def is_expired(state: Any, now: Optional[float] = None, ttl_s: float = SESSION_IDLE_TTL_S) -> bool:
    """這一列 state 是不是「上一回合結束後超過 `ttl_s` 才再進來」。

    **⛔ 沒有戳＝不算過期**（fail-open，刻意）：戳是 W8 (5) 才加的，既有的
    session 列一律沒有它。把「沒有戳」當成過期，等於在部署當下把所有進行中的
    對話一次砍掉——而這個閘保護的是「久未使用的對話不該續」，不是任何安全邊界
    （真正的隔離在 `NamespacedStateStore` 的命名空間鍵）。同理，戳是壞型別、
    或時鐘回跳導致 `now < 戳` ⇒ 也不算過期。
    """
    if not isinstance(state, dict):
        return False
    agent_state = state.get("agent")
    if not isinstance(agent_state, dict):
        return False
    stamp = agent_state.get(LAST_TURN_AT_KEY)
    if not isinstance(stamp, (int, float)) or isinstance(stamp, bool):
        return False
    current = time.time() if now is None else float(now)
    return (current - float(stamp)) > ttl_s


class NamespacedStateStore:
    """`/mcp` 回合狀態的存取點；介面與 `routers/agent_entry.py:EngineStateStore` 同形。"""

    def __init__(self, engine: Any, api_key_id: Optional[int], vendor_id: Optional[int]) -> None:
        if api_key_id is None or vendor_id is None:
            raise ValueError(
                "NamespacedStateStore 需要 api_key_id 與 vendor_id 才能組出隔離鍵"
                "（fail-closed：⛔ 不退回裸 session_id）"
            )
        self._engine = engine
        self._api_key_id = api_key_id
        self._vendor_id = vendor_id
        self._prefix = f"{NAMESPACE}:{api_key_id}:{vendor_id}:"

    # ------------------------------------------------------------------
    @property
    def prefix(self) -> str:
        return self._prefix

    def key(self, session_id: str) -> str:
        """`mcp:{api_key_id}:{vendor_id}:{session_id}`；超長 ⇒ `ValueError`。"""
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("session_id 必須是非空字串")
        namespaced = self._prefix + session_id
        if len(namespaced) > SESSION_ID_MAX_LEN:
            raise ValueError(
                f"命名空間鍵長度 {len(namespaced)} 超過 form_sessions.session_id "
                f"上限 {SESSION_ID_MAX_LEN}"
            )
        return namespaced

    # ------------------------------------------------------------------
    async def load(self, session_id: str) -> Optional[dict]:
        return await self._engine.get_state(self.key(session_id))

    async def start(
        self,
        session_id: str,
        user_id: Any,
        vendor_id: Any,
        role_id: Any,
        config_key: Optional[str] = None,
        *,
        audience: Optional[str] = None,
    ) -> dict:
        """L8：`config_key` 顯式給值 ⇒ 照給值用（既有呼叫端行為不變）；
        缺 `config_key` 但給了 `audience` ⇒ `agent:<audience>`；兩者都缺 ⇒
        舊預設 `DEFAULT_CONFIG_KEY`（`"agent:prospect"`，⛔ 不變——`mcp_facade.py`
        目前就是這條路徑，行為逐字不變，接上 `audience` 是 R3b 待辦）。
        """
        effective_key = config_key if config_key is not None else config_key_for(audience)
        return await self._engine._start(
            self.key(session_id), user_id, vendor_id, effective_key, role_id=role_id
        )

    async def save(self, session_id: str, state: dict) -> None:
        await self._engine._save(self.key(session_id), state)

    async def close(self, session_id: str) -> None:
        """把這把鍵目前那列 `COLLECTING` 關掉（W8 (5) 過期換新）。

        ⚠️ 轉呼 `ConversationalEngine._close`（同 `load`／`start`／`save` 的紀律：
        ⛔ 不在本檔寫第二份 SQL）。`_close` 是 `state='COMPLETED'`，**不可逆**——
        Plan §6 W8 回退欄已明列這個取捨（過期列本就不該再續）。
        """
        await self._engine._close(self.key(session_id))


__all__ = [
    "NamespacedStateStore",
    "SESSION_ID_MAX_LEN",
    "DEFAULT_CONFIG_KEY",
    "config_key_for",
    "NAMESPACE",
    "SESSION_IDLE_TTL_S",
    "LAST_TURN_AT_KEY",
    "stamp_last_turn",
    "is_expired",
]
