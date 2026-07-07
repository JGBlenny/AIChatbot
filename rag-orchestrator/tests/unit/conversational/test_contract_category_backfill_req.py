"""unit:合約查詢知識補標診斷分類（conversational-diagnosis 任務 8.2 / R8.2）。

驗證補標種子 `database/migrations/backfill_contract_knowledge_diagnosis_category.sql`：
  - 將合約查詢知識（自身 api_config 端點＝jgb_contracts，或其 form_id 對應之 form_schema 端點＝
    jgb_contracts）的 `categories` 補上 `條件診斷:合約`；冪等、僅 active、不碰保留分類。
  - 補標值與 8.1 對話規則設定的 topic_scope.category 完全一致（否則分類路由不命中）。
  - 補標後的知識列經 `_knowledge_category` 取得該分類 → 可被分類路由命中。
種子為部署作業（psql 套用），DB 寫入不在單元測試內執行。
"""
import json
import os
import re

import pytest

from routers.chat import _knowledge_category

pytestmark = pytest.mark.unit

_HERE = os.path.dirname(__file__)
BACKFILL = os.path.join(_HERE, "..", "..", "..", "database", "migrations",
                        "backfill_contract_knowledge_diagnosis_category.sql")
RULE_SEED = os.path.join(_HERE, "..", "..", "..", "database", "migrations",
                         "seed_conversational_diagnosis_contract_rule.sql")
DIAG_CATEGORY = "狀態判斷"


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── 補標值與設定路由鍵一致（跨資料工件不變式）──
@pytest.mark.req("conversational-diagnosis:8.2")
def test_backfill_category_matches_rule_topic_scope():
    sql = _read(BACKFILL)
    assert f"'{DIAG_CATEGORY}'" in sql
    # 對照 8.1 對話規則 topic_scope.category
    rule_sql = _read(RULE_SEED)
    m = re.search(r"-- BEGIN_METADATA_JSON(.*?)-- END_METADATA_JSON", rule_sql, re.DOTALL)
    md = json.loads(m.group(1)[m.group(1).index("{"):m.group(1).rindex("}") + 1])
    assert md["conversational_config"]["topic_scope"]["category"] == DIAG_CATEGORY


# ── 補標目標欄位 categories + 冪等 + 僅 active + 不碰保留分類 ──
@pytest.mark.req("conversational-diagnosis:8.2")
def test_backfill_targets_categories_idempotent_and_safe():
    sql = _read(BACKFILL)
    assert "categories" in sql                                   # 補多值欄位（_knowledge_category 先讀）
    assert "array_append" in sql or "||" in sql                  # 加值
    assert "@>" in sql and "NOT" in sql                          # 冪等：已含則不重複加
    assert "is_active" in sql                                    # 僅 active
    assert "對話規則" in sql                                      # 明確排除保留分類（避免違反 CHECK）


# ── 補標預測：以合約 API 端點識別（自身或 form_schema），不硬編 id ──
@pytest.mark.req("conversational-diagnosis:8.2")
def test_backfill_predicate_uses_contract_endpoint_not_hardcoded_ids():
    sql = _read(BACKFILL)
    assert "jgb_contracts" in sql                                # 以端點識別合約查詢知識
    assert "form_schemas" in sql                                 # 涵蓋 form_fill（端點在 form_schema）
    assert not re.search(r"\bid\s*=\s*\d+\b", sql)               # 不以硬編 id 鎖列


# ── 補標後行為：_knowledge_category 取得診斷分類 → 路由可命中 ──
@pytest.mark.req("conversational-diagnosis:8.2")
def test_backfilled_knowledge_yields_diagnosis_category():
    # 模擬補標後的知識列（categories 已含診斷分類）
    bk = {"id": 1, "similarity": 0.9, "action_type": "form_fill", "form_id": "contract_query",
          "categories": ["合約", DIAG_CATEGORY]}
    assert DIAG_CATEGORY in _knowledge_category(bk)
