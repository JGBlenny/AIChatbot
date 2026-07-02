"""
對話式回答設定層（option-routing R19 / 元件 15）— 資料驅動。

「對話式回答模式」是通用回答模式（不綁售前）：每個面向以一筆設定 opt-in 啟用
conversational（多輪自適應問答→收斂）；未設定的面向一律 direct（單次直答）。

**設定來源（資料驅動）**：knowledge_base 中 `category='對話規則'` 的每一列同時承載：
  - `answer`        → 該角色的對話規則（persona，見 conversational_rules 載入）
  - `target_user[]` → 角色（persona_role）
  - `generation_metadata.conversational_config`（jsonb）→ 設定本體：
        { key, answer_mode, persona_role?, enabled?,
          topic_scope{mode:all|category|keywords, ...}（進入方式：all=整角色 freetext / 主題命中）,
          grounding_scope{select:vector|category|ids, target_user, mode, vendor_id?, category?, kb_ids?}, seed? }

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
    seed: Optional[str] = None
    # topic_scope：啟用粒度。{"mode":"all"}=整角色（prospect）；
    #   {"mode":"category","category":"退租結算"} / {"mode":"keywords","keywords":[...]} = 主題級（檢索命中才進）
    topic_scope: Dict[str, Any] = field(default_factory=lambda: {"mode": "all"})
    enabled: bool = True
    # answer_rules：本對話的「收斂作答規則」（如：底稿在手直接答、禁推託語、只有一份時比較請補識別）。
    #   屬對話行為、隨設定走（換面向不消失、新領域不用抄面向脈絡）；收斂組答時附加於系統脈絡後。
    answer_rules: Optional[str] = None
    # cta_rules：推薦型收斂（cta_mode=force）才附加的 CTA/排版塊（時機仍由程式決定，保持確定性；
    #   內容資料化——業務連結/收束格式不再硬編在共用合成程式）。
    cta_rules: Optional[str] = None


# 售前收斂作答規則（原 optimizer 硬編之 PRESALES_SYNTH_RULES 原文外移）：
#   隨售前設定走、後台可編；合約等其他對話不再吃到（各對話吃各自規則）。
PRESALES_ANSWER_RULES = (
    "【合成鐵則（必守）】\n"
    "- 只用「系統脈絡 + 可用知識」內的事實，嚴禁新增、誇大或杜撰（尤其價格、競品、IoT 規格）。\n"
    "- 不報價：價格/級距一律導 [查看方案與費用](https://www.jgbsmart.com/pricing) 或留資，不講數字。\n"
    "- 競品：不主動點名；被問且本次有 E1 事實才中立比較，未列明說「不確定，建議向對方確認」，不斷言對方沒有。\n"
    "- 系統脈絡與知識都沒有的『細節』才導 demo/專人；功能「有沒有/能不能」這類，知識或系統"
    "脈絡有提到就**直接回答（有就說有、簡述怎麼運作）**，別動不動推 demo。\n"
    "- **不必每則回覆都推 demo**：一般追問把問題答清楚即可。只有在『推薦結論』或『使用者表示"
    "要行動/想看實際操作』時，才附上預約連結 [立即預約 demo](https://www.jgbsmart.com/demo-form) 。\n"
    "- 口吻：顧問式、親切專業、簡潔不誇大；可依使用者情境個人化。\n"
    "- 排版可讀性：短答 1–2 句即可、不硬湊；**一次要講多個點（如競品比較、多項功能）就用"
    "『• 條列』分行呈現，每點一行，別擠成一大段**。\n"
    "- 連結一律用 **markdown 格式 [標籤](網址)**、**禁止貼裸網址**："
    "預約 → [立即預約 demo](https://www.jgbsmart.com/demo-form)；"
    "方案 → [查看方案與費用](https://www.jgbsmart.com/pricing)。"
)

# 售前推薦收斂 CTA/排版塊（原 optimizer cta_mode=force 硬編塊原文外移；force 時機仍由程式判定）：
PRESALES_CTA_RULES = (
    "【整篇排版與收束（必照，一次寫好）】讓回覆好讀且收尾整合：\n"
    "1. 開頭 1–2 句：同理使用者情境 + 點出可解決的問題。\n"
    "2. 中段：用『• 分行條列』列出最相關的功能/價值（約 3–5 點，每點一行，"
    "不要擠成一大段文字）。\n"
    "3. 結尾：**只用『一個』整合的「下一步」區塊**收束（不要分散成多段、不要重複收尾）；"
    "把行動呼籲集中放這裡，分行條列。範例：\n"
    "下一步：\n"
    "• 免費試用一個月，親自體驗\n"
    "• 預約 demo 或留聯絡方式，由專人帶您看 👉 [立即預約 demo](https://www.jgbsmart.com/demo-form) 🙂\n"
    "（想先看方案與費用可參考 [查看方案與費用](https://www.jgbsmart.com/pricing)）\n"
    "※ 重點規則：①連結一律用 **markdown 格式 [標籤](網址)、禁止裸網址**；"
    "「[立即預約 demo](https://www.jgbsmart.com/demo-form)」務必出現、不可省略。"
    "②「預約 demo」與「留聯絡方式／我們聯繫您」是**同一個動作（聯繫專人）**，"
    "**合併成同一行**，不要拆成兩點重複。③價格一律導 [查看方案與費用](https://www.jgbsmart.com/pricing) 或留資、不講數字。"
)

# code 內建 fallback（DB 無設定 metadata 時用）；售前為第一個設定。
PRESALES_CONFIG = ConversationalConfig(
    key="presales",
    answer_mode="conversational",
    persona_role="prospect",
    grounding_scope={"target_user": "prospect", "mode": "b2b"},
    # 進入方式＝freetext（engine-first）：prospect 打字直接進，不靠選單入口（entry 已移除）。
    answer_rules=PRESALES_ANSWER_RULES,
    cta_rules=PRESALES_CTA_RULES,
)
_CODE_DEFAULTS: Dict[str, ConversationalConfig] = {PRESALES_CONFIG.key: PRESALES_CONFIG}

# 進程級快取（每輪都要查設定，不可每次查庫；資料更新後重啟或呼叫 reset_cache）
_cache: Dict[str, Any] = {"loaded": False, "by_key": {}, "by_role": {}, "by_category": {}}


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
        seed=md.get("seed"),
        topic_scope=md.get("topic_scope") or {"mode": "all"},
        enabled=md.get("enabled", True),
        answer_rules=md.get("answer_rules"),
        cta_rules=md.get("cta_rules"),
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
        # 欄位級保底（DB 優先、code 補洞）：DB 同鍵設定存在但缺 answer_rules/cta_rules
        # （如尚未跑回填 migration）→ 用 code 預設補，避免售前合成丟規則。
        cfg = by_key[k]
        if cfg is not c:
            if cfg.answer_rules is None:
                cfg.answer_rules = c.answer_rules
            if cfg.cta_rules is None:
                cfg.cta_rules = c.cta_rules
    _cache["by_key"] = by_key
    _cache["by_role"] = {
        c.persona_role: c for c in by_key.values()
        if c.answer_mode == "conversational" and c.persona_role and c.enabled
    }
    # by_category：topic_scope.mode=='category' 且啟用者，以其 category 入索引（診斷型面向路由用）
    _cache["by_category"] = {
        (c.topic_scope or {}).get("category"): c
        for c in by_key.values()
        if c.answer_mode == "conversational" and c.enabled
        and (c.topic_scope or {}).get("mode") == "category"
        and (c.topic_scope or {}).get("category")
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


async def config_for_category(db_pool, category: Optional[str]) -> Optional[ConversationalConfig]:
    """
    分類路由（conversational-diagnosis R1.3）：依「檢索到知識的分類」取對應之診斷型對話設定。
    僅 topic_scope.mode=='category' 且啟用者會被索引；未命中/未啟用/非 category 模式回 None。
    """
    if not category:
        return None
    await _load(db_pool)
    return _cache["by_category"].get(category)


def reset_cache() -> None:
    """清快取（設定資料更新後可呼叫；或進程重啟自然重載）。"""
    _cache["loaded"] = False
    _cache["by_key"] = {}
    _cache["by_role"] = {}
    _cache["by_category"] = {}
