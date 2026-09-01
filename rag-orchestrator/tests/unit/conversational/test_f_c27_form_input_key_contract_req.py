"""F-C27：responsibility-mode form 的輸入鍵必須逐字符合 resolver 的 input contract。

⚠️ 這條是 2026-09-01 於 S2 接線前 inspect 逼出來的：
   legacy `jgb_bill_diagnosis` 收 `bill_id`，而 `bill.by_ref.v1` 讀 `bill_ref`，
   `form_manager` 以 field_name 逐字建 collected_data（⛔ 無改名層）
   ⇒ 若讓 R-29 重用 legacy form，resolver 每次拿到 None → INVALID_INPUT，
     表面只會看到「請提供帳單編號」無限追問。

⚠️ 本檔刻意做成**靜態**（讀 migration SQL），⛔ 不依賴 DB：
   要在**源頭**擋住 drift，而不是等部署後才發現。
"""
import json
import os
import re

import pytest

from services.responsibility_completion import _RESOLVER_SPECS

pytestmark = pytest.mark.unit

_HERE = os.path.dirname(os.path.abspath(__file__))
MIGRATION = os.path.abspath(os.path.join(
    _HERE, "..", "..", "..", "database", "migrations",
    "20260901_r29_responsibility_form.sql"))

#: R-29 的 responsibility-owned form。⚠️ 穩定身分，⛔ 不得與 legacy 共用；
#: ⚠️ 輸入 shape 相同 ⛔ 不等於 semantic responsibility 相同 ⇒ 其他責任 ⛔ 不得自動共用。
FORM_ID = "resp_r29_receipt_actual_amount"
INPUT_CONTRACT = "bill.by_ref.v1"
EXPECTED_PROMPT = "請提供帳單編號"


def _fields_from_migration():
    sql = open(MIGRATION, encoding="utf-8").read()
    m = re.search(r"'(\[\{.*?\}\])'::jsonb", sql, re.S)
    assert m, "migration 內找不到 fields JSON——⛔ 契約無法驗證"
    return json.loads(m.group(1))


def test_positive_control_migration_file_exists():
    """沒有它，下面所有斷言都只是在驗一個不存在的檔。"""
    assert os.path.isfile(MIGRATION)
    assert FORM_ID in open(MIGRATION, encoding="utf-8").read()


def test_form_collects_exactly_one_field():
    fields = _fields_from_migration()
    assert len(fields) == 1, "⛔ 多要了不需要的欄位"


def test_field_name_matches_resolver_input_contract():
    """**F-C27 本體**：form 的 field_name 必須逐字等於 input contract 的 form_ref_field。"""
    expected = _RESOLVER_SPECS[INPUT_CONTRACT]["form_ref_field"]
    actual = _fields_from_migration()[0]["field_name"]
    assert actual == expected, (
        f"form field_name={actual!r} 與 {INPUT_CONTRACT} 期望的 {expected!r} 不符"
        f"——⛔ 禁止隱式 rename（explicit adapter count = 0）")


def test_prompt_is_exact():
    """⚠️ prompt 暫不提非數字 ref：該分支的外部驗證（D1-R2）尚未執行，
    ⛔ UI 不承諾尚未 externally validated 的能力。放寬需另裁。"""
    field = _fields_from_migration()[0]
    assert field["prompt"] == EXPECTED_PROMPT
    for forbidden in ("合約編號", "物件名稱"):
        assert forbidden not in field["prompt"], (
            f"prompt 承諾了 {forbidden}，但 nonnumeric branch 尚未外部驗證")


def test_field_is_required():
    assert _fields_from_migration()[0]["required"] is True


def _sql_without_comments(path):
    """⚠️ 必須先剝除 `--` 註解：註解裡寫「⛔ 不 UPDATE …」不該被判成執行了 UPDATE。"""
    lines = []
    for ln in open(path, encoding="utf-8"):
        lines.append(re.sub(r"--.*$", "", ln))
    return "\n".join(lines)


def test_migration_is_additive_only():
    """⛔ 不得 UPDATE legacy、⛔ 不得 backfill session。"""
    sql = _sql_without_comments(MIGRATION).upper()
    for forbidden in ("UPDATE ", "DELETE ", "DROP ", "TRUNCATE ", "ALTER "):
        assert forbidden not in sql, f"migration 含非 additive 操作：{forbidden.strip()}"
    assert "ON CONFLICT (FORM_ID) DO NOTHING" in sql, "⛔ 缺少以 stable identity 為準的冪等保護"


def test_rollback_targets_only_this_identity():
    """⛔ 不得依欄位名稱刪「所有收 bill_ref 的 form」、⛔ 不得碰 legacy。"""
    rb = os.path.join(os.path.dirname(MIGRATION), "rollback",
                      "20260901_r29_responsibility_form_rollback.sql")
    assert os.path.isfile(rb)
    sql = _sql_without_comments(rb)
    assert FORM_ID in sql
    assert "form_id = 'resp_r29_receipt_actual_amount'" in sql, \
        "⛔ rollback 必須以 stable identity 為條件"
    assert "bill_ref" not in sql, "⛔ 不得依欄位名稱刪除（會誤刪其他收 bill_ref 的 form）"
    assert "jgb_bill_diagnosis" not in sql, "⛔ rollback 觸及 legacy form"


def test_legacy_form_id_is_not_reused():
    sql = open(MIGRATION, encoding="utf-8").read()
    assert "'jgb_bill_diagnosis'" not in sql
