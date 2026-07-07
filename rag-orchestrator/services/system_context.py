"""
系統脈絡 md 載入器（option-routing R13 / 元件 10；domain-conversational-facets 元件 1）。

從 knowledge_base 以保留分類 '系統脈絡' 載入系統脈絡 md，記憶體快取（每次合成注入，
不可每次查庫）。載入失敗 → 回內建最小合規 prompt（不阻斷對話、告警）。

**面向化疊加（domain-conversational-facets · 面向模型）**：
  system_md = 通用 base ＋（沿領域鍵組出的領域層，母在前、子面向在後）。
  - base       = category='系統脈絡' 且 target_user IS NULL 的通用列（共用產品底座）。
  - 角色級領域鍵（如售前 'prospect'）→ 比對 `target_user`（比照 load_rules），單層 append。
  - 診斷面向領域鍵（如子分類 '狀態判斷'）→ 沿 category_config 父鏈（母『系統合約』→子『狀態判斷』）
    逐層取 categories 命中的系統脈絡列，**母共用在前、命中的子面向在後**疊加。
    → 只載入當下問到的面向，避免把整個領域知識每輪常駐（token 隨面向數成長時仍精簡）。
  - 無領域鍵 / 無任何領域層 → 只回 base；base 亦無 → MINIMAL_FALLBACK。
  - 快取 per-key（key = domain_key 或 ""）。
領域鍵由呼叫端讀設定給定（診斷＝topic_scope.category、售前＝persona_role/target_user），程式不硬編。
"""

from typing import Dict, List, Optional

SYSTEM_DOC_CATEGORY = "系統脈絡"
# 大小守門：md 設計上限約 1500 中文字；以字元寬鬆估 ~4500，超過告警（不阻斷）
MAX_CHARS_WARN = 4500

# 載入失敗時的內建最小合規 prompt（確保即使 md 缺失，合成仍守住合規鐵則）
MINIMAL_FALLBACK = (
    "你是金箍棒智慧物管的售前顧問。只用提供的知識回答，不報價（價格導 [查看方案與費用](https://www.jgbsmart.com/pricing) 或留資、不講數字），連結一律用 markdown 格式 [標籤](網址)、禁止裸網址，"
    "競品保持中立、只憑事實、未列明說「不確定」、不斷言對方沒有；無法確認的事實導向 demo 或專人，"
    "每段收束到一個明確下一步。口吻顧問式、親切專業、簡潔不誇大。"
)

# per-key 進程級快取：key = domain_key 或 ""；值 = 已疊加之 system_md（None 表 base 缺）。
_cache: Dict[str, Optional[str]] = {}


async def _fetch_base(conn) -> Optional[str]:
    """通用 base：category='系統脈絡'、**無 target_user 亦無 categories**（真正通用列）的最新有效列。

    領域/面向列以 target_user 或 categories 標記；base 兩者皆空，故以此區分，
    避免把某個領域面向列（target_user 也是 NULL、但有 categories）誤當 base。"""
    row = await conn.fetchrow(
        "SELECT answer FROM knowledge_base "
        "WHERE category = $1 AND is_active = TRUE AND target_user IS NULL "
        "AND (categories IS NULL OR cardinality(categories) = 0) "
        "ORDER BY id DESC LIMIT 1",
        SYSTEM_DOC_CATEGORY,
    )
    return row["answer"] if row and row["answer"] else None


async def _fetch_category_chain(conn, domain_key: str) -> List[str]:
    """回領域鍵在 category_config 的父鏈（含自身），**母在前、子在後**。
    領域鍵不在 category_config（如角色級鍵）→ 回 [domain_key]（單層，交由 categories 比對）。"""
    rows = await conn.fetch(
        "WITH RECURSIVE chain AS ("
        "  SELECT category_value, parent_value, 0 AS depth FROM category_config WHERE category_value = $1"
        "  UNION ALL"
        "  SELECT c.category_value, c.parent_value, ch.depth + 1"
        "    FROM category_config c JOIN chain ch ON c.category_value = ch.parent_value"
        ") SELECT category_value FROM chain ORDER BY depth DESC",
        domain_key,
    )
    chain = [r["category_value"] for r in rows]
    return chain or [domain_key]


async def _fetch_appends(conn, domain_key: str) -> List[str]:
    """回領域 append 串列（已排序：母共用在前、子面向在後）。
    角色級鍵（售前）走 target_user，單層；診斷面向走 category 父鏈，多層。"""
    # 角色級（售前等）：target_user 命中 → 單層 append
    role_row = await conn.fetchrow(
        "SELECT answer FROM knowledge_base "
        "WHERE category = $1 AND is_active = TRUE AND target_user @> ARRAY[$2]::text[] "
        "ORDER BY id DESC LIMIT 1",
        SYSTEM_DOC_CATEGORY, domain_key,
    )
    if role_row and role_row["answer"]:
        return [role_row["answer"]]

    # 診斷面向：沿 category 父鏈（母→子）逐層取系統脈絡列，母共用在前、子面向在後
    appends: List[str] = []
    for cat in await _fetch_category_chain(conn, domain_key):
        row = await conn.fetchrow(
            "SELECT answer FROM knowledge_base "
            "WHERE category = $1 AND is_active = TRUE AND $2 = ANY(categories) "
            "ORDER BY id DESC LIMIT 1",
            SYSTEM_DOC_CATEGORY, cat,
        )
        if row and row["answer"]:
            appends.append(row["answer"])
    return appends


async def get_system_context(db_pool, domain_key: Optional[str] = None) -> str:
    """
    取得（面向化疊加後的）系統脈絡 md（per-key 快取）。

    Args:
        db_pool: asyncpg 連接池
        domain_key: 領域鍵——診斷面向＝子分類值（如 '狀態判斷'）；售前＝target_user（'prospect'）；
                    None/"" 表通用（只回 base）。
    Returns:
        base ＋（母共用 + 子面向，若有）疊加後的 system_md；base 缺或載入失敗 → 最小合規 prompt。
    """
    key = domain_key or ""
    if key in _cache:
        return _cache[key] or MINIMAL_FALLBACK

    try:
        async with db_pool.acquire() as conn:
            base = await _fetch_base(conn)
            appends = await _fetch_appends(conn, domain_key) if domain_key else []
    except Exception as e:
        # 例外不快取，下次重試（避免暫時性 DB 故障被固化為 fallback）
        print(f"❌ 系統脈絡 md 載入失敗，使用最小合規 prompt：{e}")
        return MINIMAL_FALLBACK

    if base:
        md = "\n\n".join([base] + appends)
    else:
        md = None
        print("⚠️ 未找到通用系統脈絡 base（category='系統脈絡', target_user IS NULL），使用最小合規 prompt")

    if md and len(md) > MAX_CHARS_WARN:
        print(f"⚠️ 系統脈絡 md 偏大（{len(md)} 字元，key={key or '通用'}），建議精簡或拆面向（每次合成皆注入）")

    _cache[key] = md
    return md or MINIMAL_FALLBACK


def reset_cache() -> None:
    """清全部 per-key 快取（md 更新後可呼叫；或進程重啟自然重載）。"""
    _cache.clear()
