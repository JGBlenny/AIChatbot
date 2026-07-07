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
import re
from typing import Any, Dict, List, Optional

from services.conversational_config import ConversationalConfig, get_config

CONVERSATIONAL_FORM_ID = "conversational"
MAX_ASKS = 20  # 提問硬上限（絕對保底；收斂時機交由 AI 自行判斷，此值僅防失控無限問）

# API grounding 結果契約（conversational-diagnosis R3.4–R3.6）：
#   {"kind":"converge", "grounding": str}                        # 1 筆 → 合成
#   {"kind":"ask", "answer": str}                                # 0 筆 / 失敗 → 重問或降級
#   {"kind":"ask", "answer": str, "candidates":[{"id","label"}]} # N 筆 → 列候選
ApiGroundingResult = Dict[str, Any]


def _dig_path(obj: Any, path: Optional[str]) -> Any:
    """依點分隔路徑取值（list_path 由設定指定，程式不硬編面向欄位）。"""
    cur = obj
    for key in (path or "").split("."):
        if not key:
            continue
        if isinstance(cur, dict):
            cur = cur.get(key)
        else:
            return None
    return cur


def _fmt_ymd(value: Any) -> str:
    """Ymd（如 '20240115' / 20240115）→ 'Y/m/d'（'2024/01/15'）；非 8 位數字原樣回傳。
    純格式化，欄位由 result_mapping.label_date_fields 指定（不硬編面向欄位）。"""
    s = str(value).strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[0:4]}/{s[4:6]}/{s[6:8]}"
    return s


def _build_candidate_label(row: Dict[str, Any], mapping: Dict[str, Any]) -> Optional[str]:
    """組候選標籤（區別欄位）：有 label_fields → 依序取值以「｜」串接（label_date_fields 者格式化）；
    無 → 回退單 label_field（向後相容）。欄位一律讀 result_mapping（零硬編，R4.2/R6.1）。"""
    label_fields = mapping.get("label_fields")
    single = mapping.get("label_field")
    if not label_fields:
        return row.get(single) if single else None
    date_fields = set(mapping.get("label_date_fields") or [])
    parts = []
    for f in label_fields:
        v = row.get(f)
        if v is None or v == "":
            continue
        parts.append(_fmt_ymd(v) if f in date_fields else str(v))
    if parts:
        return "｜".join(parts)
    return row.get(single) if single else None


def _looks_like_identifier(msg: Optional[str]) -> bool:
    """本句是否為「明確識別」（純數字編號）。只認純數字（2–15 位），文字名稱仍交 brain。"""
    m = (msg or "").strip()
    return m.isdigit() and 2 <= len(m) <= 15


# id-like token：4–15 位數字；排除「與日期分隔符（/ - .）或其他數字相鄰」者——
#   日期（2026/12/30、2026-12-30）是結構性特徵，不是識別；抽成識別會誤觸切換探查
#   （e2e 真跑揪出：申請書槽位回答含租期日期 → keyword=2026 誤中含數字標題的多筆合約）。
_ID_TOKEN_RE = re.compile(r"(?<![\d/\-])(?<!\d\.)\d{4,15}(?![\d/\-])(?!\.\d)")


_ROW_TMPL_RE = re.compile(r"\{row\.([A-Za-z0-9_]+)\}")
_SESSION_TMPL_RE = re.compile(r"\{session\.([A-Za-z0-9_]+)\}")


def _resolve_row_template(value: Any, row: Dict[str, Any]) -> Any:
    """把參數值中的 {row.<field>} 以主查詢結果列插值（secondary_call 用，通用零硬編）。
    非字串原樣回；{session.*}/{form.*} 模板不動——留給 api_handler 既有解析。"""
    if not isinstance(value, str):
        return value
    return _ROW_TMPL_RE.sub(lambda m: str(row.get(m.group(1)) or ""), value)


def _extract_identifier(msg: Optional[str]) -> Optional[str]:
    """抽「候選識別」：純數字整句（2–15 位）直接回；否則從句中抽第一個 id-like token（≥4 位）。
    抓不到回 None（純文字名稱等交 brain）。

    ★ API 驗證式（後端當裁判）：這裡**只做結構性抽取**、不靠金額/單位語意 guard 預先分類——
      抽到的識別交 `prepare` 先搜後提交（`_ground_by_api` 探查），查無則回滾保留原識別、
      落回 brain（不誤切、不清有效槽）。刻意不累積領域特例清單。純位置語義，不硬編面向欄位。"""
    m = (msg or "").strip()
    if not m:
        return None
    if m.isdigit() and 2 <= len(m) <= 15:
        return m
    mt = _ID_TOKEN_RE.search(m)
    return mt.group(0) if mt else None


def _synth_context(system_md: Optional[str], config, cta_mode: Optional[str] = None) -> Optional[str]:
    """收斂組答用的系統脈絡＝領域脈絡＋本對話 answer_rules（＋推薦型再加 cta_rules）。

    - answer_rules：本對話的作答行為（如底稿在手直接答/禁推託），收斂一律附加；
    - cta_rules：CTA/排版塊，僅 cta_mode=='force'（推薦型收斂）附加——時機由程式決定（確定性），
      內容由設定承載（業務連結/收束格式不硬編共用程式）。皆未設 → 原樣（向後相容）。"""
    parts = [system_md]
    parts.append(getattr(config, "answer_rules", None))
    if cta_mode == "force":
        parts.append(getattr(config, "cta_rules", None))
    parts = [p for p in parts if p]
    return "\n\n".join(parts) if parts else system_md


def _domain_key(config) -> Optional[str]:
    """領域鍵（載入 per-領域系統脈絡用）：
      - 診斷型面向（topic_scope.mode=='category'）→ 用其**母/子分類值** topic_scope.category
        （每個診斷領域唯一，如 '條件診斷：合約'；同角色多領域不撞鍵）；
      - 角色級面向（如售前 mode=='all'）→ 用 persona_role（=target_user，如 'prospect'）。
    全讀設定，程式不硬編任何領域字面。"""
    ts = getattr(config, "topic_scope", None) or {}
    if ts.get("mode") == "category" and ts.get("category"):
        return ts.get("category")
    return getattr(config, "persona_role", None)


async def _domain_faces(db_pool, config) -> List[str]:
    """本領域可用面向集合（mid-session-switch 方案B）：
      1. `topic_scope.faces` 明列 → 直接用（設定驅動、優先）。
      2. 未明列 → 由 category_config 衍生：進入面向（topic_scope.category）之**母分類的所有子分類**
         （沿用父層展開慣例，免每領域重複列面向）。進入面向本身必在集合內。
      3. 皆無 / 衍生失敗 → 空清單＝不啟用換面向（向後相容、不阻斷）。"""
    ts = getattr(config, "topic_scope", None) or {}
    explicit = ts.get("faces")
    if isinstance(explicit, list):
        return list(explicit)
    cat = ts.get("category")
    if not cat:
        return []
    try:
        async with db_pool.acquire() as conn:
            parent = await conn.fetchval(
                "SELECT parent_value FROM category_config WHERE category_value = $1 AND is_active = TRUE",
                cat,
            )
            base = parent or cat  # cat 本身即母分類（無 parent）→ 取其子分類
            rows = await conn.fetch(
                "SELECT category_value FROM category_config WHERE parent_value = $1 AND is_active = TRUE "
                "ORDER BY display_order NULLS LAST, category_value",
                base,
            )
        faces = [r["category_value"] for r in rows]
        if cat not in faces:
            faces.append(cat)  # 進入面向必在集合內
        return faces
    except Exception as e:
        print(f"⚠️ 面向集合衍生失敗（不啟用換面向）：{e}")
        return []


_DIALOG_CAP = 6


def _note_turn(state: dict, user_message: str, ai_text: str) -> None:
    """ask 返回點記入滾動對話史（供 brain 知道自己問過什麼——2026-07-07 線上實測：
    無史則純中文名稱識別對不上槽位、且會原句重問；帶數字識別有決定性抽取兜底才未現形）。"""
    d = state.setdefault("dialog", [])
    d.append({"u": (user_message or "")[:200], "a": (ai_text or "")[:300]})
    if len(d) > _DIALOG_CAP:
        del d[:-_DIALOG_CAP]


def _has_basic_info(fields: dict, config=None) -> bool:
    """收斂前的最低資訊門檻（conversational-diagnosis R2.1/R2.5）。
    有設定 grounding_scope.required_slots → 全部必填槽位到齊才足夠（診斷面向，槽位讀設定）；
    無 → 維持售前預設：至少知道身分 + （規模 或 痛點）。"""
    fields = fields or {}
    required = (getattr(config, "grounding_scope", None) or {}).get("required_slots") if config else None
    if required:
        return all(fields.get(k) for k in required)
    has_identity = bool(fields.get("identity"))
    has_scale_or_pain = bool(fields.get("scale") or fields.get("pain"))
    return has_identity and has_scale_or_pain


_CN_NUM = {"一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _parse_ordinal(msg: str, n: int) -> Optional[int]:
    """把口語序數解析成 1-based 序號（候選 ≤ 個位數，支援 1–10）：
    純數字 / 中文數字(一二…十) / 第X個·第X筆 / 頭一個 → X；最後一個·最後一筆 → n。
    無法解析或越界 → None。純位置語義，不硬編面向。"""
    m = (msg or "").strip()
    if not m:
        return None
    if any(k in m for k in ("最後", "最尾", "最末")):
        return n if n >= 1 else None
    core = m
    for ch in ("第", "個", "筆", "份", "那", "這", "號", "位", "、", " "):
        core = core.replace(ch, "")
    core = core.strip()
    idx = None
    if core.isdigit():
        idx = int(core)
    elif core in _CN_NUM:
        idx = _CN_NUM[core]
    elif "頭" in m:
        idx = 1
    return idx if (idx is not None and 1 <= idx <= n) else None


def _match_candidate(user_message: Optional[str],
                     candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """確定性比對使用者選擇（pre-LLM，conversational-diagnosis R3.5/R2.2/R2.3）。

    依序：序號/口語序數（1-based，最自然）→ id 完全比對 → label 子字串（雙向、忽略大小寫）。
    無法判定回 None（交插點 A 再次反問）。候選的 id/label 由 result_mapping 決定，不硬編面向。
    """
    msg = (user_message or "").strip()
    if not msg or not candidates:
        return None
    # 1) 序號 / 口語序數（第二個 / 二 / 最後一個…）——優先於 id，符合「請選 1/2/3」直覺
    ordinal = _parse_ordinal(msg, len(candidates))
    if ordinal is not None:
        return candidates[ordinal - 1]
    # 2) id 完全比對
    for c in candidates:
        if str(c.get("id")) == msg:
            return c
    # 3) label 子字串（雙向、忽略大小寫）
    low = msg.lower()
    for c in candidates:
        label = str(c.get("label") or "").strip().lower()
        if label and (low in label or label in low):
            return c
    return None


def _ask_pick_again(candidates: List[Dict[str, Any]]) -> str:
    """無法對應選擇時再次列出候選反問（label 取自 result_mapping，不硬編面向）。"""
    listing = "\n".join(f"{i + 1}. {c.get('label')}" for i, c in enumerate(candidates))
    return f"不好意思，沒能對應到您的選擇，請問是以下哪一筆？\n{listing}"


class ConversationalEngine:
    def __init__(self, db_pool, optimizer, retriever, get_system_context, rules_loader,
                 api_handler=None):
        self.db_pool = db_pool
        self.optimizer = optimizer
        self.retriever = retriever
        self._get_system_context = get_system_context  # async fn(db_pool, domain_key=None)->str
        self._load_rules = rules_loader                 # async fn(db_pool, role)->Optional[str]
        # 診斷型對話的 API grounding 用（conversational-diagnosis R3.1）；
        # 可選，不傳為 None（向後相容售前）。實際 grounding 於 select:"api" 分支使用。
        self.api_handler = api_handler

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

    async def _start(self, session_id, user_id, vendor_id, config_key, seed_topic=None,
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
                      start_if_absent=True, seed_topic=None, role_id=None) -> Optional[Dict[str, Any]]:
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
                state = await self._start(session_id, user_id, vendor_id, config.key, seed_topic,
                                          role_id=role_id)
            # 續對話：以 state 內的 config_key 還原設定（不依賴呼叫端再傳）
            if config is None:
                config = await get_config(self.db_pool, state.get("config_key"))
            if config is None:
                return None

            # 【插點 A — pre-LLM 候選選擇輪（不依賴 LLM step）】
            # 上一輪 API 多筆已存 pending_candidates；本輪為「選擇」而非新問題：
            #   確定性比對 → 命中設 id 槽位、清候選 → 走單筆 api 收斂；未命中 → 再次列出反問。
            pending = state.get("pending_candidates")
            if pending:
                picked = _match_candidate(user_message, pending)
                if picked is None:
                    _ask_text = _ask_pick_again(pending)
                    _note_turn(state, user_message, _ask_text)
                    await self._save(session_id, state)
                    return {"kind": "ask", "answer": _ask_text}
                gscope = config.grounding_scope or {}
                slot = (gscope.get("required_slots") or [None])[0]  # 讀設定，不硬編面向欄位
                if slot:
                    state.setdefault("collected_fields", {})[slot] = picked["id"]
                state.pop("pending_candidates", None)
                await self._save(session_id, state)
                # 以單一 id 走 select:api 單筆收斂（確定性，不經 LLM step）
                # 領域鍵＝當輪面向（state.face；未曾切換＝進入面向）；插點A 不跑 brain（護欄1：待答中不切）
                system_md = await self._get_system_context(
                    self.db_pool, state.get("face") or _domain_key(config))
                r = await self._ground_by_api(state, config, user_message=user_message)
                if r["kind"] == "converge":
                    await self._save(session_id, state)   # 落地 grounding_note（後續輪 brain 取現況）
                    return {"kind": "converge", "grounding": r["grounding"], "ctx": None,
                            "cta_mode": "factual", "converge_kind": "answer", "system_md": _synth_context(system_md, config),
                            "session_id": session_id, "state": state, "user_message": user_message}
                # 仍非單筆（資料異動，少見）→ 安全降級回 ask（含可能新候選）
                if r.get("candidates"):
                    state["pending_candidates"] = r["candidates"]
                _note_turn(state, user_message, r["answer"])
                await self._save(session_id, state)   # 存檔：含 0 筆時清空的無效 slot
                return {"kind": "ask", "answer": r["answer"]}

            # 【確定性識別填槽/切換 — pre-LLM】診斷面向：本句抽得到「明確識別編號」（純數字或
            #   句中 id-like，如「那換 84328 呢?」）、且與現填不同（含未填）→ 直接填/換槽走單筆收斂，
            #   不靠 brain（LLM 對數字抽取/更新不穩，如「84800」抽不到、切換不更新）。slot 讀設定，零硬編。
            gscope = config.grounding_scope or {}
            required = gscope.get("required_slots") or []
            slot = required[0] if required else None
            _ident = _extract_identifier(user_message) if slot else None
            _prev_ident = (state.get("collected_fields") or {}).get(slot) if slot else None
            # deterministic_id=false：主槽為名字型（如成員 email/名字），數字非其值 →
            #   跳過決定性數字抽取，交 brain 抽（避免把資源編號誤填成員槽）。預設 true（向後相容）。
            if (gscope.get("select") or "").lower() == "api" and gscope.get("deterministic_id", True) \
                    and slot and _ident is not None and _ident != _prev_ident:
                # ★ 先搜後提交（API 驗證式）：以候選識別探查，命中才提交；查無則回滾、不誤切。
                state.setdefault("collected_fields", {})[slot] = _ident
                state.pop("pending_candidates", None)   # 換識別 → 清舊候選
                r = await self._ground_by_api(state, config, user_message=user_message)   # 0 筆時內部會清該 slot
                if r["kind"] == "converge":
                    await self._save(session_id, state)
                    system_md = await self._get_system_context(
                        self.db_pool, state.get("face") or _domain_key(config))
                    return {"kind": "converge", "grounding": r["grounding"], "ctx": None,
                            "cta_mode": "factual", "converge_kind": "answer", "system_md": _synth_context(system_md, config),
                            "session_id": session_id, "state": state, "user_message": user_message}
                if r.get("candidates"):
                    state["pending_candidates"] = r["candidates"]
                    _note_turn(state, user_message, r["answer"])
                    await self._save(session_id, state)
                    return {"kind": "ask", "answer": r["answer"]}
                # 0 筆 → 不提交此識別（後端當裁判）：
                if _prev_ident is not None:
                    # 原本已有有效識別 → 回滾保留，落回 brain 當作對原識別的追問（不誤切、不清有效槽）。
                    state.setdefault("collected_fields", {})[slot] = _prev_ident
                    await self._save(session_id, state)
                    # 不 return，續走下方 brain 流程
                else:
                    # 首次識別即查無（無可回滾）→ slot 已被清空，回追問請重新識別。
                    _note_turn(state, user_message, r["answer"])
                    await self._save(session_id, state)
                    return {"kind": "ask", "answer": r["answer"]}

            # 領域鍵＝當輪面向（state.face；首輪＝進入面向 _domain_key）：per-領域系統脈絡疊加（R2.1/R2.2）
            faces = await _domain_faces(self.db_pool, config)
            entry_key = _domain_key(config)
            current_face = state.get("face") or entry_key
            system_md = await self._get_system_context(self.db_pool, current_face)
            rules_text = await self._load_rules(self.db_pool, config.persona_role)
            if not rules_text:
                return None  # 該角色無規則 → 降級

            step = self.optimizer.conversational_step(rules_text, system_md, state, user_message, faces=faces)
            if step is None:
                if state.get("asked_count", 0) == 0:
                    await self._close(session_id)  # 新會話 brain 失敗 → 關掉殘留 COLLECTING
                return None

            # 【中途切換 scope（換 config）— mid-session-switch 方案B / D2】
            # brain 判定這句明顯不屬本 config 職責 → 關會話、回 None，由 chat.py 落回一般流程對「當前訊息」重路由。
            # （護欄1：pending_candidates 在時已於插點A 先行返回，走不到這裡＝待答中不切。）
            if step.get("scope") == "switch":
                print("🔀 [conversational] brain 判定離題(scope=switch) → 關會話、重路由當前訊息")
                await self._close(session_id)
                return None

            # 【中途切換 face（換面向）— 護欄4】當輪面向在集合內才切；越界/空 → 退回進入面向。
            face = step.get("face")
            face_key = face if (face and face in faces) else entry_key
            state["face"] = face_key
            if face_key != current_face:
                system_md = await self._get_system_context(self.db_pool, face_key)

            for k, v in (step.get("extracted_fields") or {}).items():
                if v:
                    state.setdefault("collected_fields", {})[k] = v

            asked = state.get("asked_count", 0)
            collected = state.get("collected_fields", {})
            converge_kind = (step.get("converge_kind") or "recommend").lower()

            # 推薦型基本資訊門檻（事實型不卡）
            if step["action"] == "converge" and converge_kind != "answer" \
                    and not _has_basic_info(collected, config) and asked < MAX_ASKS and step.get("next_question"):
                print("🛑 推薦型收斂但基本資訊不足，先補問再收斂（避免空泛推薦）")
                step = {**step, "action": "ask"}
            # 程式層硬上限
            if step["action"] == "ask" and asked >= MAX_ASKS:
                print(f"⛓️ 對話提問達絕對上限（{MAX_ASKS}），強制收斂")
                step = {**step, "action": "converge"}

            if step["action"] == "ask":
                state["asked_count"] = asked + 1
                _note_turn(state, user_message, step.get("next_question"))
                await self._save(session_id, state)
                return {"kind": "ask", "answer": step.get("next_question")}

            # 【插點 B】收斂選材：select=='api' → API grounding（可降級回 ask）；否則既有知識 grounding。
            gscope = config.grounding_scope or {}
            if (gscope.get("select") or "").lower() == "api":
                # 【收斂槽位保底】persona 要求「識別收齊才收斂」，但 LLM 機率性越權——未齊就打 API
                #   只會全量撈取後仍反問（最貴的查詢做追問就能做的事；無 role_id 情境更會炸降級句）。
                #   程式層強制（讀設定零硬編，R2.1/R7.3）：required_slots 未齊 → 轉追問、不打 API。
                #   達 MAX_ASKS 例外放行（保留強制收斂防死問迴圈）。
                _missing = [k for k in (gscope.get("required_slots") or []) if not collected.get(k)]
                if _missing and asked < MAX_ASKS:
                    print(f"🛡️ 收斂槽位未齊（{_missing}）→ 程式保底轉追問（不打 API）")
                    state["asked_count"] = asked + 1
                    _ask_text = (step.get("next_question")
                                 or "請先提供查詢所需的識別資訊（如編號或名稱），以便繼續。")
                    _note_turn(state, user_message, _ask_text)
                    await self._save(session_id, state)
                    return {"kind": "ask", "answer": _ask_text}
                r = await self._ground_by_api(state, config, user_message=user_message)
                if r["kind"] == "ask":  # 0/N 筆或 API 失敗 → 降級回追問（非 converge，R3.4/R3.5）
                    state["asked_count"] = asked + 1  # 維持提問次數上限保護（R2.4）
                    if r.get("candidates"):
                        state["pending_candidates"] = r["candidates"]  # 供下一輪確定性選擇（任務 5.2）
                    _note_turn(state, user_message, r["answer"])
                    await self._save(session_id, state)
                    return {"kind": "ask", "answer": r["answer"]}
                grounding, ctx, cta_mode = r["grounding"], None, "factual"  # 1 筆 → 事實型合成（不複述情境/不推 CTA）
                await self._save(session_id, state)   # 落地 grounding_note（後續輪 brain 取現況）
            else:
                grounding, ctx, cta_mode = await self._converge_grounding(
                    state, step.get("converge_topic"), user_message, config, converge_kind)
            return {"kind": "converge", "grounding": grounding, "ctx": ctx, "cta_mode": cta_mode,
                    "converge_kind": converge_kind,
                    "system_md": _synth_context(system_md, config, cta_mode),
                    "session_id": session_id, "state": state, "user_message": user_message}
        except Exception as e:
            print(f"❌ 對話引擎 prepare 失敗（降級）：{e}")
            return None

    async def _finalize_converge(self, decision, answer_text: Optional[str] = None) -> None:
        """converge 合成完成後：推薦型標記 recommended；答案記入對話史（brain 才知道
        自己剛答過什麼，使用者複述/追問出口時不重述整段——2026-07-07 實測）；保存狀態。"""
        state = decision["state"]
        if decision["converge_kind"] != "answer":
            state["recommended"] = True
        if answer_text:
            _note_turn(state, decision.get("user_message") or "", answer_text)
        await self._save(decision["session_id"], state)

    async def handle(self, session_id, user_id, vendor_id, user_message,
                     config: Optional[ConversationalConfig] = None,
                     start_if_absent=True, seed_topic=None, role_id=None) -> Optional[Dict[str, Any]]:
        """非串流：回 {answer, conversational, converged} 或 None（降級）。"""
        decision = await self.prepare(session_id, user_id, vendor_id, user_message,
                                      config, start_if_absent, seed_topic, role_id=role_id)
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
        await self._finalize_converge(decision, answer_text=reco)
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
        buf: List[str] = []
        async for chunk in self.optimizer.synthesize_presales_answer_stream(
                decision["grounding"], decision["ctx"], decision["system_md"],
                decision["user_message"], decision["cta_mode"]):
            if chunk:
                buf.append(chunk)
                yield chunk
        if buf:
            await self._finalize_converge(decision, answer_text="".join(buf))

    # ---------- API grounding（select:"api"，conversational-diagnosis R3.1–R3.6/R6.1/R6.3） ----------
    async def _ground_by_api(self, state: Dict[str, Any],
                             config: "ConversationalConfig",
                             user_message: str = "") -> ApiGroundingResult:
        """收齊槽位後呼叫設定指定之 API，依回傳筆數分三路（1/0/N）。

        重用既有 `api_handler.execute_api_call`（不另寫 API 邏輯，R3.2）：
          - api_config 的 endpoint/params 一律讀 `grounding_scope`（R3.3，不硬編端點/參數）；
          - slot 走 `form_data` 通道（= collected_fields），會話資訊走 session_data（含 role_id，R3.1）；
          - 資料列以 `result_mapping.list_path` 取出、候選 id/label 以 `id_field`/`label_field` 取，
            全部由設定驅動（R6.1，程式不出現特定面向欄位字面）。
          - `user_message`/`state.face` 透傳給決定性 formatter 選 fact 集（contract-conversational-facets
            R7.1）：原句走既有 user_input 通道、face 為選配參數，皆不在引擎解讀。
        API 例外/失敗 → 安全 ask 降級（R3.6），不拋出。
        """
        scope = config.grounding_scope or {}
        mapping = scope.get("result_mapping") or {}
        endpoint = scope.get("endpoint")
        base_params = scope.get("params") or {}
        # ★ API 驗證式（後端當裁判）：`search_params` 明列多組「搜尋嘗試」，依序試、第一組有結果即止——
        #   因後端常把 id 與關鍵字當 AND 不能同送（如合約：先當 id 查、查無再當名稱查，數字名稱不漏）。
        #   未設 → 單組（base_params），向後相容。overlay 疊在 base_params 上；全讀設定，不硬編面向欄位。
        overlays = scope.get("search_params") or [None]
        form_data = state.get("collected_fields") or {}
        session_data = {
            "role_id": state.get("role_id"),
            "vendor_id": state.get("vendor_id"),
            "session_id": state.get("session_id"),
            "user_id": state.get("user_id"),
        }

        # 【身分參數保底】設定宣告需要的 {session.<key>} 缺值 → 禁打 API、誠實降級——
        #   先前行為：缺值參數被靜默丟棄 → 端點缺必要參數報錯 → 誤導性「忙線」句
        #   （回測/租客無 role_id 情境實測踩到）。零硬編：掃設定模板取需求鍵。
        needed_session_keys: set = set()
        for v in list(base_params.values()) + [v for o in overlays if o for v in o.values()]:
            if isinstance(v, str):
                needed_session_keys.update(_SESSION_TMPL_RE.findall(v))
        missing_session = [k for k in needed_session_keys if not session_data.get(k)]
        if missing_session:
            print(f"🛡️ API grounding 缺必要身分參數 {missing_session} → 不打 API，誠實降級")
            return {"kind": "ask",
                    "answer": "目前的登入身分無法進行此查詢（缺少必要的帳號資訊），"
                              "請以對應的帳號身分登入後再試，或由專人協助您。"}

        result: Dict[str, Any] = {}
        rows: List[Any] = []
        for overlay in overlays:
            params = {**base_params, **overlay} if overlay else dict(base_params)
            api_config = {"endpoint": endpoint, "params": params}
            try:
                # face：state 未設（第一句帶識別直收斂、brain 未跑）→ fallback 進入面向
                # （同系統脈絡載入慣例 _domain_key；未註冊面向由 formatter 端 fallback 原路）
                result = await self.api_handler.execute_api_call(
                    api_config, session_data, form_data,
                    user_input={"message": user_message} if user_message else None,
                    face=state.get("face") or _domain_key(config),
                )
            except Exception as e:  # 逾時/連線等例外 → 不阻斷（R3.6）
                print(f"⚠️ API grounding 呼叫失敗（降級 ask）：{e}")
                return {"kind": "ask", "answer": "目前查詢系統忙線，請稍後再試或由專人協助您。"}
            result = result or {}
            if not result.get("success"):
                return {"kind": "ask", "answer": "目前查詢系統忙線，請稍後再試或由專人協助您。"}
            rows = _dig_path(result.get("data"), mapping.get("list_path"))
            if rows is None:
                rows = []
            elif not isinstance(rows, list):
                rows = [rows]
            if rows:
                break   # 有結果 → 用這組（不再試後續嘗試）

        # 0 筆：不杜撰，回到追問請使用者確認/更正識別（R3.4）。
        #   ★ 清掉無效的識別槽位——否則殘留無效值會卡住下一句重新識別（讀設定 required_slots，零硬編）。
        if not rows:
            collected = state.get("collected_fields") or {}
            for slot in (scope.get("required_slots") or []):
                collected.pop(slot, None)
            return {"kind": "ask",
                    "answer": "查無對應的資料，請再確認一下識別資訊（如編號或名稱）是否正確？"}

        # N 筆：候選帶區別欄位（label_fields）+ 過多分流（candidate_cap）
        #   （domain-conversational-facets 元件3/D4，R4；id/label 欄位皆讀 result_mapping，零硬編）
        if len(rows) > 1:
            id_field = mapping.get("id_field")
            candidates = [{"id": r.get(id_field), "label": _build_candidate_label(r, mapping)}
                          for r in rows]
            cap = mapping.get("candidate_cap")
            if cap and len(candidates) > cap:
                # 大集合分流（D4）：API 通常只吃關鍵字查詢/精確 id 兩種參數——
                #   不同名大集合可靠「補更明確識別」縮小關鍵字；同名多份補條件重查無效，只能列候選/給精確 id。
                #   skip_refine（設定驅動，預設關）：同母體多期資料（如同一合約的帳單）
                #   補識別縮不了 → 跳過補識別輪直接截斷列候選（帳單診斷 e2e 逼出）。
                noun = mapping.get("entity_noun", "合約")
                if not mapping.get("skip_refine") and not state.get("_refine_requested"):
                    state["_refine_requested"] = True  # prepare 隨後 _save（供下一輪判斷是否補不動）
                    return {"kind": "ask",
                            "answer": (f"符合的{noun}較多（找到 {len(candidates)} 筆），"
                                       f"請提供更明確的識別（完整物件名稱、{noun}編號，或租期），以便縮小範圍。")}
                # 已補過仍 > cap（同名多份重查無效）→ 截斷列前 cap 筆並提示可給編號直接指定（避免死迴圈）
                shown = candidates[:cap]
                listing = "\n".join(f"{i + 1}. {c['label']}" for i, c in enumerate(shown))
                return {"kind": "ask",
                        "answer": (f"符合的{noun}有多筆（僅顯示前 {cap} 筆），您可回覆序號選擇，"
                                   f"或直接提供{noun}編號指定：\n{listing}"),
                        "candidates": shown}
            # N ≤ cap（或未設 cap＝不限）→ 列候選供選序號（同名多份靠區別欄位辨識）
            state.pop("_refine_requested", None)  # 已可列出＝分流解決，清補條件標記
            listing = "\n".join(f"{i + 1}. {c['label']}" for i, c in enumerate(candidates))
            return {"kind": "ask",
                    "answer": f"找到多筆資料，請問您指的是哪一筆？\n{listing}",
                    "candidates": candidates}

        # 1 筆：以 API 回傳作為合成底稿（R3.1/R3.4）——
        #   label（哪一筆）+ formatted_response（formatter 已把碼翻成中文事實/可否操作），組文字；
        #   兩者皆無則退而序列化該列（label/欄位皆讀設定，程式不硬編面向欄位，R6.1）。
        #   ★ 由 formatter 產「乾淨中文 facts」餵 LLM 組話——不餵原始碼讓 LLM 自行解碼
        #     （已證實 LLM 解碼會幻覺/張冠李戴/代碼外洩）。
        state.pop("_refine_requested", None)  # 收斂＝分流解決，清補條件標記

        # 【secondary_call】單筆收斂後的二次查詢（G3；grounding_scope 宣告才執行，R3.3/R10.2）：
        #   params 支援 {row.<field>} 以本列插值；結果 rows 掛在主列 attach_as 鍵，
        #   再以 handler 重格式化（face 貫穿）→ facts 含二次資料。失敗沿用主底稿（降級不阻斷）。
        #   支援單一（secondary_call）或多個（secondary_calls 清單，依賴同一主列、各自 attach）。
        #   params 以 {row.*}（本列，此處插值）＋{form.*}/{session.*}（下游 _prepare_params 解）混用；
        #   各結果掛主列 attach_as 鍵。全部 attach 後**重格式化一次**（face 貫穿）。失敗降級不阻斷。
        secondary_calls = scope.get("secondary_calls")
        if not secondary_calls:
            single = scope.get("secondary_call")
            secondary_calls = [single] if single else []
        attached_any = False
        for secondary in secondary_calls:
            if not (secondary or {}).get("endpoint"):
                continue
            try:
                sec_params = {k: _resolve_row_template(v, rows[0])
                              for k, v in (secondary.get("params") or {}).items()}
                sec_result = await self.api_handler.execute_api_call(
                    {"endpoint": secondary["endpoint"], "params": sec_params},
                    session_data, form_data)
                if (sec_result or {}).get("success"):
                    sec_rows = _dig_path(sec_result.get("data"), secondary.get("list_path") or "data")
                    rows[0][secondary.get("attach_as") or "secondary"] = \
                        sec_rows if isinstance(sec_rows, list) else []
                    attached_any = True
            except Exception as e:
                print(f"⚠️ secondary_call 失敗（沿用主查詢底稿，不阻斷）：{e}")
        if attached_any:
            reformatted = self.api_handler.format_api_result(
                result.get("data"), endpoint=endpoint,
                user_input={"message": user_message} if user_message else None,
                form_data=form_data, face=state.get("face") or _domain_key(config))
            if reformatted:
                result = {**result, "formatted_response": reformatted}

        # 收斂底稿開頭帶「識別值｜名稱」：讓 LLM 能把使用者用的編號/名稱對回這筆事實。
        #   （使用者常用 id 稱呼，但 formatter facts 只帶名稱；grounding 不含 id → LLM 會誤判成
        #     「這不是他問的那筆」而推託/要求再提供。）id/label 皆讀 result_mapping，零硬編面向欄位。
        #   suppress_head_id：id 為內部個資（如成員 user_id）時不進底稿，只留名稱（遮罩防線）。
        rid = (rows[0].get(mapping.get("id_field"))
               if mapping.get("id_field") and not mapping.get("suppress_head_id") else None)
        label = rows[0].get(mapping.get("label_field")) if mapping.get("label_field") else None
        head = "｜".join(str(p) for p in (rid, label) if p is not None and p != "")
        parts = [p for p in (head, result.get("formatted_response")) if p]
        grounding = "\n".join(parts) if parts else str(rows[0])
        # ★ 底稿摘要回饋 state：後續輪 brain 才知道系統已查得的現況（如租期起迄）——
        #   否則會回頭問使用者系統早就有的值（2026-07-07 申請書槽位實測：問「目前的租期是什麼」）。
        state["grounding_note"] = grounding[:600]
        return {"kind": "converge", "grounding": grounding}

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
            # 修正(retrieval-fixes #8):grounding_scope 漏填 target_user 時,預設用 persona_role
            #   (如 prospect),避免 retriever 把 None 正規化成 tenant → prospect 收斂時誤抓租客知識。
            scope_target_user = scope.get("target_user") or getattr(config, "persona_role", None)
            if select == "ids" and scope.get("kb_ids"):
                grounding = await self._grounding_by_ids(scope["kb_ids"])
            elif select == "category" and scope.get("category"):
                # limit 可由 grounding_scope 宣告（通用擴充；預設 8）——面向知識超過 8 筆時
                # priority 同分靠 id 排序會把新知識擠出底稿（estate 抽驗逼出）。
                grounding = await self._grounding_by_category(
                    scope["category"], scope_target_user,
                    limit=int(scope.get("limit") or 8))
            else:  # vector
                emb = await self.retriever.embedding_client.get_embedding(query, verbose=False)
                if emb:
                    res = await self.retriever._vector_search(
                        emb, vendor_id=scope.get("vendor_id") or 0, top_k=5,
                        similarity_threshold=0.0, target_user=scope_target_user,
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
