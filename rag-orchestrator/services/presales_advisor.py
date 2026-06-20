"""
AI 引導式售前顧問 orchestrator（option-routing R14–R18 / 元件 11/13/14）。

職責：管理顧問對話狀態（存 form_sessions 偽會話 form_id='presales_advisor'）、
每輪呼叫 brain（LLMAnswerOptimizer.advisor_step）、收斂時依已收集欄位檢索 grounding 並
重用 synthesize_presales_answer 生成推薦。失敗回 None 交呼叫端降級。

狀態（form_sessions.collected_data，jsonb）：
  {"collected_fields": {identity, scale, team, pain, interested}, "asked_count": int}
"""

import json
from typing import Optional, Dict, Any

ADVISOR_FORM_ID = "presales_advisor"


class PresalesAdvisor:
    def __init__(self, db_pool, optimizer, retriever, get_system_context):
        self.db_pool = db_pool
        self.optimizer = optimizer
        self.retriever = retriever
        self._get_system_context = get_system_context  # async fn(db_pool)->str

    # ---------- 狀態（元件 11，R16） ----------
    async def get_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT collected_data FROM form_sessions "
                "WHERE session_id=$1 AND form_id=$2 AND state='COLLECTING' "
                "ORDER BY id DESC LIMIT 1",
                session_id, ADVISOR_FORM_ID,
            )
        if not row or row["collected_data"] is None:
            return None
        cd = row["collected_data"]
        return cd if isinstance(cd, dict) else json.loads(cd)

    async def _start(self, session_id, user_id, vendor_id, seed_topic=None) -> Dict[str, Any]:
        state = {"collected_fields": {}, "asked_count": 0}
        if seed_topic:
            state["collected_fields"]["_seed"] = seed_topic
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO form_sessions (session_id, user_id, vendor_id, form_id, state, "
                "current_field_index, collected_data) VALUES ($1,$2,$3,$4,'COLLECTING',0,$5::jsonb)",
                session_id, user_id, vendor_id, ADVISOR_FORM_ID, json.dumps(state),
            )
        return state

    async def _save(self, session_id, state):
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE form_sessions SET collected_data=$2::jsonb, updated_at=now() "
                "WHERE id=(SELECT id FROM form_sessions WHERE session_id=$1 AND form_id=$3 "
                "AND state='COLLECTING' ORDER BY id DESC LIMIT 1)",
                session_id, json.dumps(state), ADVISOR_FORM_ID,
            )

    async def _close(self, session_id):
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE form_sessions SET state='COMPLETED', updated_at=now() "
                "WHERE session_id=$1 AND form_id=$2 AND state='COLLECTING'",
                session_id, ADVISOR_FORM_ID,
            )

    def is_active_state(self, session_state: Optional[Dict]) -> bool:
        return bool(session_state and session_state.get("form_id") == ADVISOR_FORM_ID)

    # ---------- 主流程（元件 12/13/14） ----------
    async def handle(self, session_id, user_id, vendor_id, user_message,
                     start_if_absent=True, seed_topic=None) -> Optional[Dict[str, Any]]:
        """
        回 {answer, advisor:True, converged:bool} 或 None（呼叫端降級）。
        """
        try:
            state = await self.get_state(session_id)
            if state is None:
                if not start_if_absent:
                    return None
                state = await self._start(session_id, user_id, vendor_id, seed_topic)

            system_md = await self._get_system_context(self.db_pool)
            step = self.optimizer.advisor_step(system_md, state, user_message)
            if step is None:
                return None  # brain 失敗 → 降級

            # 更新已收集欄位
            for k, v in (step.get("extracted_fields") or {}).items():
                if v:
                    state.setdefault("collected_fields", {})[k] = v

            if step["action"] == "ask":
                state["asked_count"] = state.get("asked_count", 0) + 1
                await self._save(session_id, state)
                return {"answer": step.get("next_question"), "advisor": True, "converged": False}

            # converge → 取 grounding + 合成推薦
            reco = await self._converge(state, step.get("converge_topic"), system_md, user_message)
            await self._close(session_id)
            if not reco:
                return None
            return {"answer": reco, "advisor": True, "converged": True}
        except Exception as e:
            print(f"❌ 顧問 handle 失敗（降級）：{e}")
            return None

    async def _converge(self, state, converge_topic, system_md, user_message) -> Optional[str]:
        """依已收集欄位檢索 prospect 知識當 grounding，合成個人化推薦。"""
        fields = state.get("collected_fields", {})
        # 組檢索查詢：身分 + 規模 + 痛點 + 主軸
        parts = [str(fields.get(k, "")) for k in ("identity", "scale", "pain", "interested")]
        query = " ".join([p for p in parts if p] + ([converge_topic] if converge_topic else []) + ["方案推薦"])
        grounding = ""
        try:
            emb = await self.retriever.embedding_client.get_embedding(query, verbose=False)
            if emb:
                res = await self.retriever._vector_search(
                    emb, vendor_id=1, top_k=5, similarity_threshold=0.0,
                    target_user="prospect", mode="b2b", vector_limit=20,
                )
                grounding = "\n\n".join(r.get("answer", "") for r in res[:3] if r.get("answer"))
        except Exception as e:
            print(f"⚠️ 顧問收斂檢索失敗：{e}")
        # 累積情境 = 已收集欄位
        ctx = [{"field_label": k, "selected_label": str(v)} for k, v in fields.items() if k != "_seed" and v]
        if not grounding:
            grounding = "（依系統脈絡的功能索引與已知情境給適合建議；無確切知識的細節導向 demo/專人，不杜撰、不報價）"
        import asyncio
        return await asyncio.to_thread(
            self.optimizer.synthesize_presales_answer, grounding, ctx, system_md, user_message,
        )
