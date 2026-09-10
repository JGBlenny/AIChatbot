"""舊鏈隔離 S3（Plan 第 5 稿 D 案）：新線自有的會話狀態層。

**為什麼要有這個檔**：新線（`/mcp`、`agent_entry.py`）過去借用 `ConversationalEngine`
的 `get_state`／`_start`／`_save`／`_close` 四個方法存取 `form_sessions`——但引擎
其餘 1,581 行（brain 呼叫、grounding、確認流程…）新線完全不用。量過：新線只命中
這四個方法，合計 43 行純 SQL，只依賴 `db_pool`／`json`／`CONVERSATIONAL_FORM_ID`
這個字串常數，對 `api_handler`（引擎另一個依賴）**零命中**。為了 43 行養一個
1,581 行的引擎、連帶養它注入的一串依賴，不划算——這個類別就是抽出來的那 43 行。

**⛔ SQL 逐字照搬，一個字都不准改**：同一張 `form_sessions` 表、同一組欄位、
同一個 `form_id='conversational'`（`CONVERSATIONAL_FORM_ID`，見 `services/form_contract`）。
**既有 DB 資料列必須繼續可讀**——這是搬移的前提，不是搬移的副作用。

**方法名 vs 舊引擎**：舊引擎裡是 `get_state`／`_start`／`_save`／`_close`
（後三者底線開頭，因為它們是引擎私有介面、只給 `NamespacedStateStore` 和
`EngineStateStore` 轉呼）。搬到本檔後**四個都改公開名**：`get_state`／`start`／
`save`／`close`——因為本檔本身就是給別的模組當狀態層用的獨立類別，不再是
「私有方法、外部靠繞過命名慣例轉呼」的關係。呼叫端（`state_store.py`、
`routers/agent_entry.py`）已同步改叫公開名。

**簽章不變**：`start()` 的參數順序 `session_id, user_id, vendor_id, config_key,
seed_topic=None, role_id=None` 與舊引擎的 `_start` 逐字相同——呼叫端不用改傳參方式。
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from services.form_contract import CONVERSATIONAL_FORM_ID


class AgentSessionStore:
    """`/mcp`／`agent_entry.py` 共用的會話狀態層（取代舊鏈 `ConversationalEngine`
    的狀態子集）。只認 `db_pool`，不依賴引擎其餘的 brain／grounding／確認邏輯。
    """

    def __init__(self, db_pool) -> None:
        self.db_pool = db_pool

    async def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT collected_data FROM form_sessions "
                "WHERE session_id=$1 AND form_id=$2 AND state='COLLECTING' "
                "ORDER BY id DESC LIMIT 1",
                session_id, CONVERSATIONAL_FORM_ID,
            )
        if not row or row["collected_data"] is None:
            return None
        cd = row["collected_data"]
        return cd if isinstance(cd, dict) else json.loads(cd)

    async def start(self, session_id, user_id, vendor_id, config_key, seed_topic=None,
                    role_id=None) -> Dict[str, Any]:
        # 會話識別存入 state：續對話時 _ground_by_api 僅收 (state, config)，需從 state 取
        # session_data（role_id/vendor_id/session_id/user_id）打 API（診斷面向資料權限過濾）。
        state = {"config_key": config_key, "collected_fields": {}, "asked_count": 0,
                 "session_id": session_id, "user_id": user_id,
                 "vendor_id": vendor_id, "role_id": role_id}
        if seed_topic:
            state["collected_fields"]["_seed"] = seed_topic
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO form_sessions (session_id, user_id, vendor_id, form_id, state, "
                "current_field_index, collected_data) VALUES ($1,$2,$3,$4,'COLLECTING',0,$5::jsonb)",
                session_id, user_id, vendor_id, CONVERSATIONAL_FORM_ID, json.dumps(state),
            )
        return state

    async def save(self, session_id, state):
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE form_sessions SET collected_data=$2::jsonb, last_activity_at=now() "
                "WHERE id=(SELECT id FROM form_sessions WHERE session_id=$1 AND form_id=$3 "
                "AND state='COLLECTING' ORDER BY id DESC LIMIT 1)",
                session_id, json.dumps(state), CONVERSATIONAL_FORM_ID,
            )

    async def close(self, session_id):
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE form_sessions SET state='COMPLETED', completed_at=now() "
                "WHERE session_id=$1 AND form_id=$2 AND state='COLLECTING'",
                session_id, CONVERSATIONAL_FORM_ID,
            )


__all__ = ["AgentSessionStore"]
