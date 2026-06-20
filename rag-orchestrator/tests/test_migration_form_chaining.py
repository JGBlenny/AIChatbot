"""
Test suite for form-chaining migration (task 1.1).
Feature: form-chaining
Task: 1.1 - 撰寫 migration：form_schemas 新增 next_form_id 欄位 + FK + 索引

本測試對 migration SQL 檔做靜態驗證（不需資料庫），確認檔案內容滿足設計：
- 新增可空 next_form_id VARCHAR(100)
- 自我參照 FK → form_schemas(form_id) ON DELETE SET NULL
- 索引 idx_form_schemas_next_form_id
- 具冪等性（IF NOT EXISTS / 約束存在性守衛）
- 以交易包覆（BEGIN/COMMIT）

需求：1.1, 1.4, 7.3
"""

import os
import re

import pytest

MIGRATION_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "database", "migrations",
    "add_next_form_id_to_form_schemas.sql",
)


@pytest.fixture(scope="module")
def sql() -> str:
    assert os.path.exists(MIGRATION_PATH), f"migration 檔不存在：{MIGRATION_PATH}"
    with open(MIGRATION_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _norm(text: str) -> str:
    """壓平空白並轉小寫，便於語意比對。"""
    return re.sub(r"\s+", " ", text).lower()


def test_adds_nullable_next_form_id_column(sql):
    """新增可空 next_form_id VARCHAR(100)，且具冪等性（IF NOT EXISTS）。"""
    n = _norm(sql)
    assert re.search(
        r"add column if not exists next_form_id varchar\(100\)", n
    ), "缺少冪等的 ADD COLUMN IF NOT EXISTS next_form_id VARCHAR(100)"
    # 可空：不得帶 NOT NULL 限制
    assert "next_form_id varchar(100) not null" not in n, "next_form_id 不應為 NOT NULL"


def test_self_referencing_fk_on_delete_set_null(sql):
    """FK 自我參照 form_schemas(form_id)，ON DELETE SET NULL。"""
    n = _norm(sql)
    assert "foreign key (next_form_id)" in n, "缺少 next_form_id 外鍵宣告"
    assert re.search(
        r"references form_schemas\s*\(\s*form_id\s*\)", n
    ), "FK 應參照 form_schemas(form_id)"
    assert "on delete set null" in n, "FK 應為 ON DELETE SET NULL"


def test_creates_index(sql):
    """建立索引 idx_form_schemas_next_form_id（冪等）。"""
    n = _norm(sql)
    assert re.search(
        r"create index if not exists idx_form_schemas_next_form_id\s+on\s+form_schemas\s*\(\s*next_form_id\s*\)",
        n,
    ), "缺少冪等索引 idx_form_schemas_next_form_id ON form_schemas(next_form_id)"


def test_fk_creation_is_idempotent(sql):
    """FK 建立需具冪等守衛（Postgres ADD CONSTRAINT 不支援 IF NOT EXISTS）。"""
    n = _norm(sql)
    # 以 pg_constraint 存在性守衛，避免重跑時報 duplicate constraint
    assert "pg_constraint" in n, "FK 建立應以 pg_constraint 存在性守衛維持冪等"


def test_wrapped_in_transaction(sql):
    """以交易包覆，失敗可整體回滾。"""
    n = _norm(sql)
    assert "begin;" in n, "缺少 BEGIN;"
    assert "commit;" in n, "缺少 COMMIT;"
