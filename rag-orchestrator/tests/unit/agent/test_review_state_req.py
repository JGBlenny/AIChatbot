"""unit：內容已審狀態單一來源（spec knowledge-outline-and-intent-architecture 任務 3.1）。

離線、⛔ 不接觸 DB——本檔驗的是**常數與純函式**，以及「migration 的 regex 字串
逐位元組等於 `review_state.DOMAIN_REGEX`」這個 drift 閘門。

Python 側判定與 PostgreSQL 側判定是否真的一致，⛔ 不在本檔宣稱：那要真的問 DB，
由 `tests/integration/agent/test_review_state_visibility_req.py` 對 §3 全表逐值
跑 `SELECT %s ~ %s` 比對（Plan §5.1／§5.4）。
"""
import ast
import os
import re

import pytest

from services.agent.canon import review_state as rs

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:3.1")]

_RAG_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_MIGRATION = os.path.join(
    _RAG_ROOT, "database", "migrations", "20260907_outline_approved_by_domain.sql")
_ROLLBACK = os.path.join(
    _RAG_ROOT, "database", "migrations", "rollback",
    "20260907_outline_approved_by_domain_rollback.sql")
_DUMP_TOOL = os.path.join(_RAG_ROOT, "tools", "agent_outline_dump.py")

_CONSTRAINT_NAME = "chk_outline_approved_by_domain"

#: Plan §3 單一真值表：`(值, 內容已審可見?, CHECK 允許?)`。
#: ⚠️ `None`（NULL）不在此表——它由 CHECK 的 `IS NULL` 前半段放行，
#: `is_domain_value(None)` 只判字串值，見該函式 docstring。
DOMAIN_TABLE = [
    ("reviewed:owner", True, True),
    ("reviewed:王", True, True),
    ("reviewed:", False, False),                 # 空 reviewer
    ("reviewed: ", False, False),                # 冒號後只有空白
    ("reviewed: alice", False, False),           # ⚠️ LIKE 'reviewed:_%' 會放行這個
    ("reviewed:\tbob", False, False),            # tab
    ("reviewed:　bob", False, False),        # U+3000 全形空白（PG 與 Python 是否一致由 integration 實查）
    ("Reviewed:owner", False, False),            # 大小寫
    (" reviewed:owner", False, False),           # 前導空白
    ("REVIEWED:owner", False, False),
    ("pool-marked-20260905", False, True),       # 池標記：允許但**不可見**
    ("pool-marked-2026", False, False),          # 日期不是 8 位
    ("owner-20260905", False, False),            # 現況 29 列
    ("", False, False),
]


# ── 謂詞形狀 ────────────────────────────────────────────────────────────

def test_predicate_shape_exactly_one_placeholder_and_param():
    sql, params = rs.content_reviewed_predicate()
    assert sql.count("%s") == 1, f"佔位符不是恰一個：{sql!r}"
    assert params == [rs.REVIEWED_REGEX]
    assert sql.startswith(" AND "), f"片段必須能直接接在 WHERE 之後：{sql!r}"
    assert rs.COLUMN in sql
    assert "$1" not in sql, "⛔ 不得混用 asyncpg 佔位符（build_visibility_predicate 是 %s 風格）"


def test_predicate_is_regex_not_like():
    """⛔ 不得回頭用 `LIKE`——`_` 吃空白，`reviewed: alice` 會被放行（F3）。"""
    sql, _params = rs.content_reviewed_predicate()
    assert " ~ %s" in sql
    assert "LIKE" not in sql.upper()


def test_column_constant_is_the_real_column_name():
    assert rs.COLUMN == "outline_approved_by"
    assert rs.REVIEWED_PREFIX == "reviewed:"
    assert rs.POOL_MARK_PREFIX == "pool-marked-"


# ── §3 真值表（Python 鏡像）────────────────────────────────────────────

@pytest.mark.parametrize("value,visible,allowed", DOMAIN_TABLE)
def test_domain_table_python_mirror(value, visible, allowed):
    assert rs.is_reviewed_value(value) is visible, f"{value!r} 的可見判定與 §3 不符"
    assert rs.is_domain_value(value) is allowed, f"{value!r} 的值域判定與 §3 不符"


@pytest.mark.parametrize("value,visible,allowed", DOMAIN_TABLE)
def test_visible_subset_of_allowed(value, visible, allowed):
    """可見 ⊂ CHECK 允許——可見卻不在值域內是矛盾（會被 CHECK 擋在門外的值卻算已審）。"""
    if visible:
        assert allowed, f"{value!r} 可見卻不在值域內"


def test_pool_mark_is_allowed_but_not_visible():
    """池標記≠內容已審（design 元件 5）——D1 改寫後 29 列仍不可見。"""
    assert rs.is_domain_value("pool-marked-20260905") is True
    assert rs.is_reviewed_value("pool-marked-20260905") is False


@pytest.mark.parametrize("value", [None, 123, object(), b"reviewed:owner"])
def test_non_string_values_are_not_reviewed(value):
    """`None`／非字串 ⇒ fail-closed 判 False（⛔ 不丟例外、⛔ 不當已審）。"""
    assert rs.is_reviewed_value(value) is False
    assert rs.is_domain_value(value) is False


def test_two_regex_constants_are_not_shared_strings():
    """PG POSIX 與 Python 是兩組常數：`[[:space:]]` ⛔ 不能餵給 Python `re`。"""
    assert "[:space:]" in rs.REVIEWED_REGEX and "[:space:]" in rs.DOMAIN_REGEX
    assert "[:space:]" not in rs.REVIEWED_REGEX_PY and "[:space:]" not in rs.DOMAIN_REGEX_PY
    assert r"\S" in rs.REVIEWED_REGEX_PY and r"\S" in rs.DOMAIN_REGEX_PY
    # 反證：POSIX 字元類餵進 Python 會變成「字元集合」，語義完全不同——
    # `reviewed:a` 這種正常值會被判不合法，證明兩者不可共用。
    assert re.fullmatch(rs.REVIEWED_REGEX, "reviewed:a") is None
    assert re.fullmatch(rs.REVIEWED_REGEX_PY, "reviewed:a") is not None


# ── migration 檔（逐位元組比對）─────────────────────────────────────────

def _migration_src():
    assert os.path.exists(_MIGRATION), f"{_MIGRATION} 不存在"
    with open(_MIGRATION, encoding="utf-8") as f:
        return f.read()


def test_migration_regex_literal_is_byte_for_byte_domain_regex():
    """drift 閘門：CHECK 的 regex 與 `DOMAIN_REGEX` 必須逐位元組相同。

    不同就代表 DB 值域與程式判定分家了——那正是這條不變量要擋的事。
    """
    src = _migration_src()
    literals = re.findall(r"~ '([^']*)'", src)
    assert literals, "migration 內找不到 `~ '<regex>'` 字面——檔案結構變了，本比對失效"
    assert rs.DOMAIN_REGEX in literals, (
        f"migration 的 regex {literals!r} 與 review_state.DOMAIN_REGEX "
        f"{rs.DOMAIN_REGEX!r} 不同"
    )


def test_migration_has_constraint_name_and_not_valid_and_idempotent_guard():
    src = _migration_src()
    assert _CONSTRAINT_NAME in src
    assert "NOT VALID" in src, "⛔ 少了 NOT VALID：29 列 owner-20260905 會讓 ALTER 整個中止"
    assert "pg_constraint" in src and "IF NOT EXISTS" in src, "缺冪等守衛"
    assert "DO $$" in src


def test_migration_validate_step_is_commented_out_for_owner_to_run():
    """`VALIDATE CONSTRAINT` 只能是**註解**——它必須在業主改寫 29 列之後才跑（D1）。"""
    src = _migration_src()
    validate_lines = [ln for ln in src.splitlines() if "VALIDATE CONSTRAINT" in ln]
    assert validate_lines, "找不到 D1 的 VALIDATE CONSTRAINT 步驟說明"
    for ln in validate_lines:
        assert ln.lstrip().startswith("--"), f"VALIDATE 沒有被註解掉，會在 D1 前執行：{ln!r}"


def test_rollback_file_exists_and_drops_the_constraint():
    assert os.path.exists(_ROLLBACK), f"{_ROLLBACK} 不存在"
    with open(_ROLLBACK, encoding="utf-8") as f:
        src = f.read()
    assert "DROP CONSTRAINT" in src and _CONSTRAINT_NAME in src


# ── `tools/agent_outline_dump.py` 的欄位名來自 COLUMN（不變量 32 的一處落點）──

def test_agent_outline_dump_has_no_column_literal_outside_docstrings():
    """dump 工具的 SQL／輸出字串一律由 `review_state.COLUMN` 組出。

    掃描界定同不變量 32：AST 字串常數（含 f-string 字面片段），
    ⛔ 排除 docstring（那裡談這個欄位是說明，不是送進 DB 的字串）。
    """
    with open(_DUMP_TOOL, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
    doc_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                doc_ids.add(id(body[0].value))
    offenders = [
        (getattr(n, "lineno", 0), n.value)
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
        and id(n) not in doc_ids and rs.COLUMN in n.value
    ]
    assert not offenders, f"tools/agent_outline_dump.py 仍有寫死的欄位名字面：{offenders}"
    # 正對照：這個檔真的有取用單一來源（否則上面的「沒有字面」可能只是掃錯檔）
    assert "from services.agent.canon.review_state import COLUMN" in src
