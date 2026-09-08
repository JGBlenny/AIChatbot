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
import os
from pathlib import Path
from typing import Any

#: 預設＝demo 替身（真資料子集，遮罩後，全部對 demo 使用者可見）。
#: 環境變數 `JGB_MOCK_FIXTURE` 可指到別的 JSON——測試套件在 `tests/conftest.py` 以它指向
#: `tests/fixtures/jgb/regression_vendor4.json`（凍結的回歸宇宙：含合成鏈 900001／678／456…），
#: 所以合成測試列 ⛔ 不再放進 demo 檔（2026-09-08 業主「清掉測試資料」：demo 業務用關鍵字
#: 會撈到同 role 的合成合約，狀態碼還是不合法的 5）。⚠️ 在 import 時讀一次，之後不可換。
_FIXTURE_PATH = Path(
    os.environ.get("JGB_MOCK_FIXTURE")
    or (Path(__file__).parent / "fixture_data" / "demo_vendor4.json")
)


def _load() -> "dict[str, Any]":
    with open(_FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


#: 行程內只讀一次磁碟；後續呼叫皆對這份記憶體副本做深拷貝。
_DATA: "dict[str, Any]" = _load()


def load_from(path: "str | Path") -> None:
    """**測試專用 seam**：就地換掉行程內的 `_DATA`，改讀 `path` 指的 JSON。

    ⚠️ 正式流程的 fixture 路徑（`_FIXTURE_PATH`）只在模組 import 時依
    `JGB_MOCK_FIXTURE` 決定一次，不應在執行期改道；本函式只給需要驗證
    「某一份 fixture 檔本身、繞過 `JGB_MOCK_FIXTURE` 覆寫」的測試使用
    （例如驗證 `demo_vendor4.json`——測試套件平常吃的是 `regression_vendor4.json`）。
    呼叫端負責在測試結束後把 `_DATA` 復原（`monkeypatch.setattr` 或
    `try/finally` 存回舊值），否則會汙染同一行程內後續建構的 `*FixtureTable`。
    """
    global _DATA
    with open(path, encoding="utf-8") as f:
        _DATA = json.load(f)


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
