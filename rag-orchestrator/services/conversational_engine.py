"""
對話式回答模式 engine（option-routing R14–R19 / 元件 11/12/13/14/15）。

通用「對話式回答」引擎：對 answer_mode=conversational 的面向，依設定（ConversationalConfig）
驅動多輪自適應提問→收斂。售前（prospect）為第一個設定；新增面向/角色＝加設定資料 + 規則資料。

職責：
  - 管理對話狀態（存 form_sessions 偽會話 form_id='conversational'，含 config_key）。
  - 每輪呼叫 brain（LLMAnswerOptimizer.conversational_step）；規則由 rules_loader 依設定
    persona_role 載入後外傳（引擎不綁角色）。
  - 收斂時依設定 grounding_scope 限定檢索知識（多面向不互撈），重用
    synthesize_presales_answer 生成個人化推薦。
失敗回 None 交呼叫端降級（不阻斷對話）。

狀態（form_sessions.collected_data, jsonb）：
  {"config_key": str, "collected_fields": {...}, "asked_count": int}
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from services.conversational_config import ConversationalConfig, get_config

CONVERSATIONAL_FORM_ID = "conversational"
MAX_ASKS = 20  # 提問硬上限（絕對保底；收斂時機交由 AI 自行判斷，此值僅防失控無限問）


def _has_basic_info(fields: dict) -> bool:
    """收斂前的最低資訊門檻：至少知道身分 + （規模 或 痛點）才足以給有意義的推薦。"""
    fields = fields or {}
    has_identity = bool(fields.get("identity"))
    has_scale_or_pain = bool(fields.get("scale") or fields.get("pain"))
    return has_identity and has_scale_or_pain


class ConversationalEngine:
    def __init__(self, db_pool, optimizer, retriever, get_system_context, rules_loader):
        self.db_pool = db_pool
        self.optimizer = optimizer
        self.retriever = retriever
        self._get_system_context = get_system_context  # async fn(db_pool)->str
        self._load_rules = rules_loader                 # async fn(db_pool, role)->Optional[str]

    # ---------- 狀態（元件 11，R16） ----------
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

    async def _start(self, session_id, user_id, vendor_id, config_key, seed_topic=None) -> Dict[str, Any]:
        state = {"config_key": config_key, "collected_fields": {}, "asked_count": 0}
        if seed_topic:
            state["collected_fields"]["_seed"] = seed_topic
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO form_sessions (session_id, user_id, vendor_id, form_id, state, "
                "current_field_index, collected_data) VALUES ($1,$2,$3,$4,'COLLECTING',0,$5::jsonb)",
                session_id, user_id, vendor_id, CONVERSATIONAL_FORM_ID, json.dumps(state),
            )
        return state

    async def _save(self, session_id, state):
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE form_sessions SET collected_data=$2::jsonb, last_activity_at=now() "
                "WHERE id=(SELECT id FROM form_sessions WHERE session_id=$1 AND form_id=$3 "
                "AND state='COLLECTING' ORDER BY id DESC LIMIT 1)",
                session_id, json.dumps(state), CONVERSATIONAL_FORM_ID,
            )

    async def _close(self, session_id):
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE form_sessions SET state='COMPLETED', completed_at=now() "
                "WHERE session_id=$1 AND form_id=$2 AND state='COLLECTING'",
                session_id, CONVERSATIONAL_FORM_ID,
            )

    def is_active_state(self, session_state: Optional[Dict]) -> bool:
        return bool(session_state and session_state.get("form_id") == CONVERSATIONAL_FORM_ID)

    # ---------- 主流程（元件 12/13/14） ----------
    async def prepare(self, session_id, user_id, vendor_id, user_message,
                      config: Optional[ConversationalConfig] = None,
                      start_if_absent=True, seed_topic=None) -> Optional[Dict[str, Any]]:
        """
        跑 brain + gate，回「決策」（converge 僅先取 grounding、尚未合成/未 save）：
          {'kind':'ask','answer':<問句>}（已 +1 並 save asked_count）
          {'kind':'converge', grounding, ctx, cta_mode, converge_kind, system_md, session_id, state, user_message}
          None（降級）
        供 handle()（非串流合成）與 stream_answer()（串流合成）共用，避免重複 brain 邏輯。
        """
        try:
            state = await self.get_state(session_id)
            if state is None:
                if not start_if_absent or config is None:
                    return None
                state = await self._start(session_id, user_id, vendor_id, config.key, seed_topic)
            # 續對話：以 state 內的 config_key 還原設定（不依賴呼叫端再傳）
            if config is None:
                config = await get_config(self.db_pool, state.get("config_key"))
            if config is None:
                return None

            system_md = await self._get_system_context(self.db_pool)
            rules_text = await self._load_rules(self.db_pool, config.persona_role)
            if not rules_text:
                return None  # 該角色無規則 → 降級

            step = self.optimizer.conversational_step(rules_text, system_md, state, user_message)
            if step is None:
                if state.get("asked_count", 0) == 0:
                    await self._close(session_id)  # 新會話 brain 失敗 → 關掉殘留 COLLECTING
                return None

            for k, v in (step.get("extracted_fields") or {}).items():
                if v:
                    state.setdefault("collected_fields", {})[k] = v

            asked = state.get("asked_count", 0)
            collected = state.get("collected_fields", {})
            converge_kind = (step.get("converge_kind") or "recommend").lower()

            # 推薦型基本資訊門檻（事實型不卡）
            if step["action"] == "converge" and converge_kind != "answer" \
                    and not _has_basic_info(collected) and asked < MAX_ASKS and step.get("next_question"):
                print("🛑 推薦型收斂但基本資訊不足，先補問再收斂（避免空泛推薦）")
                step = {**step, "action": "ask"}
            # 程式層硬上限
            if step["action"] == "ask" and asked >= MAX_ASKS:
                print(f"⛓️ 對話提問達絕對上限（{MAX_ASKS}），強制收斂")
                step = {**step, "action": "converge"}

            if step["action"] == "ask":
                state["asked_count"] = asked + 1
                await self._save(session_id, state)
                return {"kind": "ask", "answer": step.get("next_question")}

            grounding, ctx, cta_mode = await self._converge_grounding(
                state, step.get("converge_topic"), user_message, config, converge_kind)
            return {"kind": "converge", "grounding": grounding, "ctx": ctx, "cta_mode": cta_mode,
                    "converge_kind": converge_kind, "system_md": system_md,
                    "session_id": session_id, "state": state, "user_message": user_message}
        except Exception as e:
            print(f"❌ 對話引擎 prepare 失敗（降級）：{e}")
            return None

    async def _finalize_converge(self, decision) -> None:
        """converge 合成完成後：推薦型標記 recommended；保存狀態（不關閉會話，續對話接得上）。"""
        state = decision["state"]
        if decision["converge_kind"] != "answer":
            state["recommended"] = True
        await self._save(decision["session_id"], state)

    async def handle(self, session_id, user_id, vendor_id, user_message,
                     config: Optional[ConversationalConfig] = None,
                     start_if_absent=True, seed_topic=None) -> Optional[Dict[str, Any]]:
        """非串流：回 {answer, conversational, converged} 或 None（降級）。"""
        decision = await self.prepare(session_id, user_id, vendor_id, user_message,
                                      config, start_if_absent, seed_topic)
        if decision is None:
            return None
        if decision["kind"] == "ask":
            return {"answer": decision["answer"], "conversational": True, "converged": False}
        reco = await asyncio.to_thread(
            self.optimizer.synthesize_presales_answer,
            decision["grounding"], decision["ctx"], decision["system_md"],
            decision["user_message"], decision["cta_mode"])
        if not reco:
            return None
        await self._finalize_converge(decision)
        return {"answer": reco, "conversational": True, "converged": decision["converge_kind"] != "answer"}

    async def stream_answer(self, decision):
        """串流：依決策 yield 文字 chunk。ask→整句一次；converge→真 token 串流，結束後 finalize。"""
        if not decision:
            return
        if decision["kind"] == "ask":
            q = decision.get("answer") or ""
            if q:
                yield q
            return
        got = False
        async for chunk in self.optimizer.synthesize_presales_answer_stream(
                decision["grounding"], decision["ctx"], decision["system_md"],
                decision["user_message"], decision["cta_mode"]):
            if chunk:
                got = True
                yield chunk
        if got:
            await self._finalize_converge(decision)

    async def _converge_grounding(self, state, converge_topic, user_message, config, converge_kind):
        """取 grounding（選材三態）+ 累積情境 ctx + cta_mode；不合成。回 (grounding, ctx, cta_mode)。"""
        fields = state.get("collected_fields", {})
        scope = config.grounding_scope or {}
        parts = [str(fields.get(k, "")) for k in ("identity", "scale", "pain", "interested")]
        extra = [converge_topic] if converge_topic else []
        if converge_kind == "answer":
            kw = [user_message] + extra
        else:
            kw = [p for p in parts if p] + extra + (scope.get("keywords") or ["方案推薦"])
            if user_message:
                kw = kw + [user_message]
        query = " ".join([k for k in kw if k])
        # 選材三態（決定性優先；非功能需求 #1）：ids 明列 / category 整批 / vector 語意（預設）
        select = (scope.get("select") or "vector").lower()
        grounding = ""
        try:
            if select == "ids" and scope.get("kb_ids"):
                grounding = await self._grounding_by_ids(scope["kb_ids"])
            elif select == "category" and scope.get("category"):
                grounding = await self._grounding_by_category(scope["category"], scope.get("target_user"))
            else:  # vector
                emb = await self.retriever.embedding_client.get_embedding(query, verbose=False)
                if emb:
                    res = await self.retriever._vector_search(
                        emb, vendor_id=scope.get("vendor_id") or 0, top_k=5,
                        similarity_threshold=0.0, target_user=scope.get("target_user"),
                        mode=scope.get("mode", "b2b"), vector_limit=20)
                    grounding = "\n\n".join(r.get("answer", "") for r in res[:3] if r.get("answer"))
        except Exception as e:
            print(f"⚠️ 對話引擎收斂檢索失敗（select={select}）：{e}")
        # 事實型答問不帶情境（避免回答前複述舊 profile）；推薦型帶情境做個人化
        if converge_kind == "answer":
            ctx = None
        else:
            ctx = [{"field_label": k, "selected_label": str(v)} for k, v in fields.items() if k != "_seed" and v]
        if not grounding:
            grounding = "（依系統脈絡的功能索引與已知情境給適合建議；無確切知識的細節導向 demo/專人，不杜撰、不報價）"
        cta_mode = "force" if converge_kind != "answer" else "suppress"
        return grounding, ctx, cta_mode

    # ---------- grounding 決定性選材（不靠向量） ----------
    async def _grounding_by_ids(self, kb_ids, limit: int = 8) -> str:
        """明列知識 id → 取其 answer 串接（決定性；只取 active）。"""
        try:
            ids = [int(i) for i in (kb_ids or [])][:limit]
            if not ids:
                return ""
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT answer FROM knowledge_base WHERE id = ANY($1::int[]) "
                    "AND is_active = TRUE AND answer <> ''",
                    ids,
                )
            return "\n\n".join(r["answer"] for r in rows if r["answer"])
        except Exception as e:
            print(f"⚠️ grounding_by_ids 失敗：{e}")
            return ""

    async def _grounding_by_category(self, category: str, target_user=None, limit: int = 8) -> str:
        """某主題分類整批撈 → 串接 answer（決定性；窄主題用；可無 embedding）。

        主題分類以多值欄位 categories 為準（category-multi-select 任務 3.1）：
        語意＝「categories 含此主題值」（$1 = ANY(categories)），涵蓋掛多個主題的列。
        """
        # 父層展開：選父層時自動涵蓋其子分類（與 admin 知識篩選一致）
        cat_match = (
            "($1 = ANY(categories) OR categories && COALESCE("
            "(SELECT array_agg(category_value::text) FROM category_config WHERE parent_value = $1), "
            "'{}'::text[]))"
        )
        try:
            async with self.db_pool.acquire() as conn:
                if target_user:
                    rows = await conn.fetch(
                        f"SELECT answer FROM knowledge_base WHERE {cat_match} AND is_active = TRUE "
                        "AND answer <> '' AND (target_user IS NULL OR target_user @> ARRAY[$2]::text[]) "
                        "ORDER BY priority DESC NULLS LAST, id LIMIT $3",
                        category, target_user, limit,
                    )
                else:
                    rows = await conn.fetch(
                        f"SELECT answer FROM knowledge_base WHERE {cat_match} AND is_active = TRUE "
                        "AND answer <> '' ORDER BY priority DESC NULLS LAST, id LIMIT $2",
                        category, limit,
                    )
            return "\n\n".join(r["answer"] for r in rows if r["answer"])
        except Exception as e:
            print(f"⚠️ grounding_by_category 失敗：{e}")
            return ""
