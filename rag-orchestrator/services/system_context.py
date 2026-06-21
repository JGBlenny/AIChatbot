"""
系統脈絡 md 載入器（option-routing R13 / 元件 10）。

從 knowledge_base 以保留分類 '系統脈絡' 載入售前系統脈絡 md，記憶體快取（每次合成注入，
不可每次查庫）。載入失敗 → 回內建最小合規 prompt（不阻斷對話、告警）。
"""

from typing import Optional

SYSTEM_DOC_CATEGORY = "系統脈絡"
# 大小守門：md 設計上限約 1500 中文字；以字元寬鬆估 ~4500，超過告警（不阻斷）
MAX_CHARS_WARN = 4500

# 載入失敗時的內建最小合規 prompt（確保即使 md 缺失，合成仍守住合規鐵則）
MINIMAL_FALLBACK = (
    "你是金箍棒智慧物管的售前顧問。只用提供的知識回答，不報價（價格導 https://www.jgbsmart.com/pricing 或留資、不講數字），"
    "競品保持中立、只憑事實、未列明說「不確定」、不斷言對方沒有；無法確認的事實導向 demo 或專人，"
    "每段收束到一個明確下一步。口吻顧問式、親切專業、簡潔不誇大。"
)

# 進程級快取
_cache = {"loaded": False, "md": None}


async def get_system_context(db_pool) -> str:
    """
    取得系統脈絡 md（快取）。載入失敗或無資料 → 回最小合規 prompt。

    Args:
        db_pool: asyncpg 連接池
    Returns:
        系統脈絡 md 文字（或最小合規 prompt）
    """
    if _cache["loaded"]:
        return _cache["md"] or MINIMAL_FALLBACK
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT answer FROM knowledge_base "
                "WHERE category = $1 AND is_active = TRUE "
                "ORDER BY id DESC LIMIT 1",
                SYSTEM_DOC_CATEGORY,
            )
        md = row["answer"] if row and row["answer"] else None
        if md and len(md) > MAX_CHARS_WARN:
            print(f"⚠️ 系統脈絡 md 偏大（{len(md)} 字元），建議精簡（每次合成皆注入）")
        _cache["md"] = md
        _cache["loaded"] = True
        if not md:
            print("⚠️ 未找到系統脈絡 md（category='系統脈絡'），使用最小合規 prompt")
            return MINIMAL_FALLBACK
        return md
    except Exception as e:
        print(f"❌ 系統脈絡 md 載入失敗，使用最小合規 prompt：{e}")
        return MINIMAL_FALLBACK


def reset_cache() -> None:
    """清快取（md 更新後可呼叫；或進程重啟自然重載）。"""
    _cache["loaded"] = False
    _cache["md"] = None
