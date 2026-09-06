"""內容已審狀態的**單一來源**（spec knowledge-outline-and-intent-architecture・任務 3.1）。

design 元件 5／決策 8／不變量 32；Plan `inputs/plan-3.1-review-state-20260907.md` §1／§3。

## 這個檔回答什麼命題
`knowledge_base.outline_approved_by` 這一欄的**值域**（哪些值合法）與
**謂詞**（哪些值算「內容已審、可被 agent 路徑取用」）——兩者都只在這裡定義，
其他任何檔案（`tools/kb.py`、`tools/agent_outline_dump.py`、
migration SQL）一律引用本檔常數，⛔ 不得自行寫出 `outline_approved_by` 字面
（不變量 32：`scripts/audit/checks/agent_boundary.py:check_32_review_state_single_source`）。

## 值域（業主 2026-09-07 裁 (a)：收嚴，並回寫 design）
| 值 | CHECK 允許 | 謂詞可見 |
|---|---|---|
| `reviewed:<who>`（who 非空、不含空白） | 是 | **是** |
| `pool-marked-<YYYYMMDD>` | 是 | **否** |
| `NULL` | 是 | 否 |
| 其餘（含現況 29 列的 `owner-20260905`、大小寫變體、前導空白） | 否 | 否 |

**可見 ⊂ CHECK 允許**：池標記（`pool-marked-*`）是「這一列屬於某次盤點的池」，
⛔ **不是**「內容已審」——D1 把 29 列 `owner-20260905` 改寫成 `pool-marked-<date>`
之後它們**仍然不可見**，要到正本細目匯入寫進 `reviewed:<who>` 才會進場。
（D1 前整池對 agent 路徑視為未審，是**預期**行為，不是回歸。）

## ⛔ 為什麼是 regex 不是 `LIKE`
`LIKE 'reviewed:_%'` 的 `_` 是「任一字元」——**空白也算**，於是
`reviewed: alice`（冒號後有空白、reviewer 其實是空的）會被放行；
`LIKE 'reviewed:%'` 更寬，連 `reviewed:` 空 reviewer 都放行。
兩者都讓「誰核可的」這個欄位可以是空的，等於審核紀錄可以造假成空白。
故謂詞與 CHECK 一律用 POSIX regex，且**用同一個字串常數**，真值表必然相同。

## ⛔ 為什麼是兩組常數而不是共用一個字串
PostgreSQL 的 POSIX regex 支援字元類 `[[:space:]]`，Python `re` **不支援**
（會被當成字元集合 `[:aces]`，語義完全不同）。故 SQL 側用
`REVIEWED_REGEX`／`DOMAIN_REGEX`（`[[:space:]]`），Python 側用
`REVIEWED_REGEX_PY`／`DOMAIN_REGEX_PY`（`\\S`）——兩組**並列、⛔ 不共用字串**，
由測試對 Plan §3 全表逐值比對兩邊結果相同（實查 2026-09-07：15 個值全部一致，
含 U+3000 全形空白——PG 的 `[[:space:]]` 與 Python 的 `\\S` 對它判定相同）。
drift 由 `tests/unit/agent/test_review_state_req.py` 與 migration 檔的逐字比對擋。

⛔ 本檔無 DB、無 I/O、無 import 副作用——它只是一組常數與兩個純函式。
"""
from __future__ import annotations

import re
from typing import Any, List, Tuple

#: 審核欄位名。⛔ 其他檔案要拼這個欄位名一律 import 本常數（不變量 32）。
COLUMN = "outline_approved_by"

#: 內容已審值的前綴：`reviewed:<who>`。
REVIEWED_PREFIX = "reviewed:"

#: 池標記值的前綴：`pool-marked-<YYYYMMDD>`（D1 由 `owner-20260905` 改寫而來）。
#: ⚠️ 池標記**不是**內容已審，見檔頭值域表。
POOL_MARK_PREFIX = "pool-marked-"

#: 內容已審謂詞（**PostgreSQL POSIX**）。⛔ 勿把 `[[:space:]]` 拿去餵 Python `re`。
REVIEWED_REGEX = r"^reviewed:[^[:space:]]+$"

#: 值域（**PostgreSQL POSIX**）——migration `20260907_outline_approved_by_domain.sql`
#: 的 CHECK 逐字使用這個字串（測試逐位元組比對，drift 必紅）。
DOMAIN_REGEX = r"^(reviewed:[^[:space:]]+|pool-marked-[0-9]{8})$"

#: `REVIEWED_REGEX` 的 Python 鏡像（`\S` ⇄ `[^[:space:]]`）。
REVIEWED_REGEX_PY = r"^reviewed:\S+$"

#: `DOMAIN_REGEX` 的 Python 鏡像。
DOMAIN_REGEX_PY = r"^(reviewed:\S+|pool-marked-[0-9]{8})$"


def content_reviewed_predicate() -> Tuple[str, List[str]]:
    """回 `(" AND kb.outline_approved_by ~ %s", [REVIEWED_REGEX])`。

    **正向白名單**：只有 `reviewed:<who>` 進場，值域外任何值（含 `NULL`、
    現況 29 列的 `owner-20260905`、大小寫變體、前導空白、空 reviewer）
    一律視為未審 ⇒ 取不到。

    psycopg2 `%s` 佔位符（與 `build_visibility_predicate` 同款，⛔ 不混用
    asyncpg `$n`）；**恰一個 `%s`、恰一個參數**，呼叫端把片段接在 SQL 尾、
    參數同序延長即可。

    ⛔ 只在 agent 路徑拼接（現況唯一呼叫端＝`tools/kb.py:fetch_visible_row`；
    ⚠️ `outline.py` 的售前池查詢已於 3.2 退役——大綱改由 git 正本組裝，
    「未審不可引用」在正本側由 `FineItem.reviewed_by` 承擔，見
    `services/agent/canon/canon_assembler.py:canon_visible`）；⛔ 不併入
    `build_visibility_predicate`（那是**可見性**單一來源，不變量 29 紅線；
    本謂詞是**審核狀態**，兩者是兩條各自獨立的閘門，合併會讓其中一邊
    改動時誤傷另一邊）。
    """
    return f" AND kb.{COLUMN} ~ %s", [REVIEWED_REGEX]


def is_reviewed_value(value: Any) -> bool:
    """這個值算不算「內容已審」（Python 側鏡像，供測試與離線判定）。

    `None`／非 `str` ⇒ `False`（fail-closed：判不出來就不算已審）。
    """
    if not isinstance(value, str):
        return False
    return re.fullmatch(REVIEWED_REGEX_PY, value) is not None


def is_domain_value(value: Any) -> bool:
    """這個值在不在 CHECK 允許的值域內（**不含 `NULL`**）。

    `None` ⇒ `False`——⚠️ 這不代表 `NULL` 違反 CHECK：CHECK 寫成
    `outline_approved_by IS NULL OR outline_approved_by ~ DOMAIN_REGEX`，
    `NULL` 由前半段放行。本函式只判**字串值**，`NULL` 的處置在 SQL 那一半。
    """
    if not isinstance(value, str):
        return False
    return re.fullmatch(DOMAIN_REGEX_PY, value) is not None
