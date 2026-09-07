"""單一 JSON fixture 檔的載入器（transport-extension-full-coverage）。

**定位**：`services/jgb/fixture_data/demo_vendor4.json` 是 vendor4 demo 的
**唯一資料來源**——帳單／合約／物件／電表／團隊成員／修繕全部從這裡讀，
不得在各 `*_fixtures.py` 模組裡另外維護一份平行的硬編碼資料。

每次呼叫 `demo_rows()`／`demo_section()` 皆回傳**深拷貝**，
使每個 `JGBMockTransport` 實例（進而每個 `JGBSystemAPI` 實例）都拿到
獨立的可變記憶體狀態——寫入只改自己那份拷貝，不會互相汙染，
也不會改到磁碟上的原始 JSON。
"""

import copy
import json
from pathlib import Path
from typing import Any

_FIXTURE_PATH = Path(__file__).parent / "fixture_data" / "demo_vendor4.json"


def _load() -> "dict[str, Any]":
    with open(_FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


#: 行程內只讀一次磁碟；後續呼叫皆對這份記憶體副本做深拷貝。
_DATA: "dict[str, Any]" = _load()


def demo_rows(domain: str) -> "list[dict[str, Any]]":
    """回傳 `domain`（如 `"bills"`／`"contracts"`）的列表型資料，深拷貝。"""
    rows = _DATA.get(domain)
    return copy.deepcopy(rows) if isinstance(rows, list) else []


def demo_section(key: str) -> Any:
    """回傳任意頂層鍵的資料（例如 `"repair_categories"`），深拷貝。"""
    return copy.deepcopy(_DATA.get(key))


def demo_visibility(domain: str) -> "dict[str, list[int]]":
    """回傳 `f"{domain}_visibility"` 的宣告表：`{str(row_id): [user_id, ...]}`。

    ⚠️ 缺 key（未宣告）與存在但空陣列（宣告為「無人可見」）是**兩種不同事實**，
    呼叫端不得把兩者混為一談。
    """
    table = _DATA.get(f"{domain}_visibility")
    return copy.deepcopy(table) if isinstance(table, dict) else {}
