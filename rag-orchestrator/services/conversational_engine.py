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
    async def handle(self, session_id, user_id, vendor_id, user_message,
                     config: Optional[ConversationalConfig] = None,
                     start_if_absent=True, seed_topic=None) -> Optional[Dict[str, Any]]:
        """
        跑一輪對話。config 為入口/新建時的面向設定；續對話（state 已存在）時若未傳則由
        state.config_key 還原。回 {answer, conversational:True, converged:bool} 或 None（呼叫端降級）。
        """
        try:
            state = await self.get_state(session_id)
            if state is None:
                if not start_if_absent or config is None:
                    return None
                state = await self._start(session_id, user_id, vendor_id, config.key, seed_topic)
            # 續對話：以 state 內的 config_key 還原設定（不依賴呼叫端再傳）
            if config is None:
                config = get_config(state.get("config_key"))
            if config is None:
                return None

            system_md = await self._get_system_context(self.db_pool)
            rules_text = await self._load_rules(self.db_pool, config.persona_role)
            if not rules_text:
                return None  # 該角色無規則 → 不啟用 conversational，降級

            step = self.optimizer.conversational_step(rules_text, system_md, state, user_message)
            if step is None:
                # brain 失敗 → 降級；若是剛起的新會話，關掉以免殘留 COLLECTING
                if state.get("asked_count", 0) == 0:
                    await self._close(session_id)
                return None

            # 更新已收集欄位
            for k, v in (step.get("extracted_fields") or {}).items():
                if v:
                    state.setdefault("collected_fields", {})[k] = v

            asked = state.get("asked_count", 0)
            collected = state.get("collected_fields", {})
            # converge_kind：'answer'＝回答明確事實問題（競品/價格/功能，直接用知識 grounding）；
            # 其餘＝'recommend'（產品適配推薦，需基本資訊）
            converge_kind = (step.get("converge_kind") or "recommend").lower()

            # 收斂最低門檻：**僅推薦型**需要基本資訊（身分 + 規模或痛點）；事實型直接答不卡。
            # 基本資訊不足就想做推薦型收斂 → 先補問關鍵 1 題（用 brain 一併給的備用 next_question）。
            if step["action"] == "converge" and converge_kind != "answer" \
                    and not _has_basic_info(collected) and asked < MAX_ASKS and step.get("next_question"):
                print("🛑 推薦型收斂但基本資訊不足，先補問再收斂（避免空泛推薦）")
                step = {**step, "action": "ask"}

            # 程式層硬上限（絕對保底，防失控無限問；正常收斂由 AI 判斷）
            if step["action"] == "ask" and asked >= MAX_ASKS:
                print(f"⛓️ 對話提問達絕對上限（{MAX_ASKS}），強制收斂")
                step = {**step, "action": "converge"}

            if step["action"] == "ask":
                state["asked_count"] = asked + 1
                await self._save(session_id, state)
                return {"answer": step.get("next_question"), "conversational": True, "converged": False}

            # converge → 取知識 grounding + 合成（事實型答問 / 推薦型推薦）
            reco = await self._converge(
                state, step.get("converge_topic"), system_md, user_message, config, converge_kind,
            )
            if not reco:
                return None
            # 收斂後**不關閉會話**，保留已收集情境讓後續追問接得上（給完推薦使用者常會再追問，
            # 關閉會導致下一輪重問身分/戶數）。只有使用者「取消」才結束（見 chat.py 續對話 hook）。
            if converge_kind != "answer":
                state["recommended"] = True  # 標記已給過推薦：後續正面回應改引導 CTA、不重述方案
            await self._save(session_id, state)
            return {"answer": reco, "conversational": True, "converged": converge_kind != "answer"}
        except Exception as e:
            print(f"❌ 對話引擎 handle 失敗（降級）：{e}")
            return None

    async def _converge(self, state, converge_topic, system_md, user_message,
                        config: ConversationalConfig, converge_kind: str = "recommend") -> Optional[str]:
        """
        依設定 grounding_scope 檢索知識當 grounding，合成回答。
        - recommend：以已收集欄位（身分/規模/痛點）為主組檢索 → 個人化推薦。
        - answer：以使用者問題為主組檢索（競品/價格/功能等）→ grounded 直答。
        知識一律當「事實底稿」，由 synthesize_presales_answer 合成（不直吐、受合規護欄約束）。
        """
        fields = state.get("collected_fields", {})
        scope = config.grounding_scope or {}
        # 組檢索查詢：事實型以使用者問題為主；推薦型以欄位為主。兩者都帶 user_message 提升命中。
        parts = [str(fields.get(k, "")) for k in ("identity", "scale", "pain", "interested")]
        extra = [converge_topic] if converge_topic else []
        if converge_kind == "answer":
            kw = [user_message] + extra
        else:
            kw = [p for p in parts if p] + extra + (scope.get("keywords") or ["方案推薦"])
            if user_message:
                kw = kw + [user_message]
        query = " ".join([k for k in kw if k])
        grounding = ""
        try:
            emb = await self.retriever.embedding_client.get_embedding(query, verbose=False)
            if emb:
                res = await self.retriever._vector_search(
                    emb,
                    vendor_id=scope.get("vendor_id", 1),
                    top_k=5,
                    similarity_threshold=0.0,
                    target_user=scope.get("target_user"),
                    mode=scope.get("mode", "b2b"),
                    vector_limit=20,
                )
                grounding = "\n\n".join(r.get("answer", "") for r in res[:3] if r.get("answer"))
        except Exception as e:
            print(f"⚠️ 對話引擎收斂檢索失敗：{e}")
        # 累積情境 = 已收集欄位（供推薦個人化）。事實型答問(answer)不帶情境，避免回答前
        # 先複述舊 profile/方案（直接針對問題回答）。
        if converge_kind == "answer":
            ctx = None
        else:
            ctx = [{"field_label": k, "selected_label": str(v)} for k, v in fields.items() if k != "_seed" and v]
        if not grounding:
            grounding = "（依系統脈絡的功能索引與已知情境給適合建議；無確切知識的細節導向 demo/專人，不杜撰、不報價）"
        # 推薦型結尾必帶 demo CTA（明確下一步）；事實型答問/追問抑制連結（保持自然、不每則推銷）
        cta_mode = "force" if converge_kind != "answer" else "suppress"
        return await asyncio.to_thread(
            self.optimizer.synthesize_presales_answer, grounding, ctx, system_md, user_message, cta_mode,
        )
