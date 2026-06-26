"""主題分類（topic category）正規化工具（spec category-multi-select・元件 3）。

主題分類以 knowledge_base.categories（TEXT[]）為唯一真實來源（SoT）。所有寫入路徑
（loop/AI 生成）統一經 to_categories() 將輸入正規化為陣列，並硬性排除文件角色保留值
（對話規則 / 系統脈絡），與 DB CHECK 約束 chk_categories_no_reserved 構成雙重防護。
"""
from typing import List, Optional, Sequence

# 文件角色標記保留值——不得進入主題分類陣列（需求 2.2）。
RESERVED_CATEGORIES: "frozenset[str]" = frozenset({"對話規則", "系統脈絡"})


def to_categories(
    category: Optional[str] = None,
    categories: Optional[Sequence[str]] = None,
) -> List[str]:
    """將主題分類輸入正規化為去重、保序、排除保留值的字串陣列。

    取值優先序：非空的多值 `categories` 優先；否則由單值 `category` 轉單元素陣列。
    去除空白字串與保留值（對話規則 / 系統脈絡）；保留首次出現順序。
    空輸入回空陣列（語意＝未分類）。

    Args:
        category: 單值主題分類（向後相容來源）。
        categories: 多值主題分類（優先來源）。

    Returns:
        正規化後的主題分類陣列（可為空）。
    """
    source: Sequence[str] = categories if categories else ([category] if category else [])
    seen: set = set()
    result: List[str] = []
    for raw in source:
        value = (raw or "").strip()
        if not value or value in RESERVED_CATEGORIES or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
