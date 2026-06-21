"""
對話式回答設定層（option-routing R19 / 元件 15）— 資料驅動。

「對話式回答模式」是通用回答模式（不綁售前）：每個面向以一筆設定 opt-in 啟用
conversational（多輪自適應問答→收斂）；未設定的面向一律 direct（單次直答）。

**設定來源（資料驅動）**：knowledge_base 中 `category='對話規則'` 的每一列同時承載：
  - `answer`        → 該角色的對話規則（persona，見 conversational_rules 載入）
  - `target_user[]` → 角色（persona_role）
  - `generation_metadata.conversational_config`（jsonb）→ 設定本體：
        { key, answer_mode, persona_role?, grounding_scope{target_user,mode,vendor_id?,category?,keywords?},
          entry{form_id, option_values[]}, seed? }

**新增一組面向/角色 = 後台加一筆「對話規則」（含上述 metadata），零改程式。**
DB 未提供時以 code 內建預設（presales）fallback。
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

CONFIG_CATEGORY = "對話規則"


@dataclass
class ConversationalConfig:
    key: str
    answer_mode: str = "conversational"
    persona_role: Optional[str] = None
    # grounding_scope：收斂時的知識範圍。
    #   - select: "vector"(語意檢索,廣主題) | "category"(整批撈某分類,決定性) | "ids"(明列 kb_ids,最決定性)
    #   - 既有鍵：target_user / mode(b2b·b2c) / vendor_id / category / keywords / kb_ids
    grounding_scope: Dict[str, Any] = field(default_factory=dict)
    entry: Dict[str, Any] = field(default_factory=dict)
    seed: Optional[str] = None
    # topic_scope：啟用粒度。{"mode":"all"}=整角色（prospect）；
    #   {"mode":"category","category":"退租結算"} / {"mode":"keywords","keywords":[...]} = 主題級（檢索命中才進）
    topic_scope: Dict[str, Any] = field(default_factory=lambda: {"mode": "all"})
    enabled: bool = True


# code 內建 fallback（DB 無設定 metadata 時用）；售前為第一個設定。
PRESALES_CONFIG = ConversationalConfig(
    key="presales",
    answer_mode="conversational",
    persona_role="prospect",
    grounding_scope={"target_user": "prospect", "mode": "b2b", "vendor_id": 1},
    entry={"form_id": "presales_entry", "option_values": ["fit", "pain"]},
)
_CODE_DEFAULTS: Dict[str, ConversationalConfig] = {PRESALES_CONFIG.key: PRESALES_CONFIG}

# 進程級快取（每輪都要查設定，不可每次查庫；資料更新後重啟或呼叫 reset_cache）
_cache: Dict[str, Any] = {"loaded": False, "by_key": {}, "by_role": {}}


def _config_from_row(target_user: Optional[List[str]], metadata: Any) -> Optional[ConversationalConfig]:
    """由一列「對話規則」的 target_user + generation_metadata 組出設定（無 config metadata → None）。"""
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata or "{}")
        except Exception:
            metadata = {}
    md = (metadata or {}).get("conversational_config") or {}
    role = (target_user or [None])[0]
    if not md and not role:
        return None
    persona_role = md.get("persona_role") or role
    return ConversationalConfig(
        key=md.get("key") or persona_role or "default",
        answer_mode=md.get("answer_mode", "conversational"),
        persona_role=persona_role,
        grounding_scope=md.get("grounding_scope") or {"target_user": persona_role, "mode": "b2b"},
        entry=md.get("entry") or {},
        seed=md.get("seed"),
        topic_scope=md.get("topic_scope") or {"mode": "all"},
        enabled=md.get("enabled", True),
    )


async def _load(db_pool) -> None:
    if _cache["loaded"]:
        return
    by_key: Dict[str, ConversationalConfig] = {}
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT target_user, generation_metadata FROM knowledge_base "
                "WHERE category = $1 AND is_active = TRUE",
                CONFIG_CATEGORY,
            )
        for r in rows:
            cfg = _config_from_row(r["target_user"], r["generation_metadata"])
            if cfg:
                by_key[cfg.key] = cfg
        if by_key:
            print(f"✅ [conversational config] 由 DB 載入 {len(by_key)} 組設定")
    except Exception as e:
        print(f"⚠️ [conversational config] DB 載入失敗，用 code 預設：{e}")
    # code 預設補上 DB 未覆蓋者
    for k, c in _CODE_DEFAULTS.items():
        by_key.setdefault(k, c)
    _cache["by_key"] = by_key
    _cache["by_role"] = {
        c.persona_role: c for c in by_key.values()
        if c.answer_mode == "conversational" and c.persona_role and c.enabled
    }
    _cache["loaded"] = True


async def get_config(db_pool, key: Optional[str]) -> Optional[ConversationalConfig]:
    """依設定鍵取設定（續對話還原用）。"""
    await _load(db_pool)
    return _cache["by_key"].get(key) if key else None


async def config_for_target_user(db_pool, target_user: Optional[str]) -> Optional[ConversationalConfig]:
    """
    answer_mode dispatch（R19.1/19.2）：依角色取「該角色的 conversational 設定」。
    未設定（回 None）者一律走 direct。
    """
    if not target_user:
        return None
    await _load(db_pool)
    return _cache["by_role"].get(target_user)


async def config_for_entry(db_pool, form_id: str, option_value: Any) -> Optional[ConversationalConfig]:
    """依選單入口取設定：某選單表單的某選項 value 是否為某 conversational 面向的入口。"""
    if not form_id:
        return None
    await _load(db_pool)
    for cfg in _cache["by_key"].values():
        if cfg.answer_mode != "conversational":
            continue
        entry = cfg.entry or {}
        if entry.get("form_id") == form_id:
            values = entry.get("option_values") or []
            if option_value in values or str(option_value) in [str(v) for v in values]:
                return cfg
    return None


def reset_cache() -> None:
    """清快取（設定資料更新後可呼叫；或進程重啟自然重載）。"""
    _cache["loaded"] = False
    _cache["by_key"] = {}
    _cache["by_role"] = {}
