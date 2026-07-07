"""unit:合約診斷對話規則種子內容正確（conversational-diagnosis 任務 8.1 / R8.1）。

驗證部署種子 `database/migrations/seed_conversational_diagnosis_contract_rule.sql` 的設定內容：
其 generation_metadata 經 `_config_from_row` 解析後 == 設計指定之 ConversationalConfig
（topic_scope=category:條件診斷:合約；grounding_scope=api/jgb_contracts/required_slots/params/
result_mapping）。種子為唯一事實來源，測試直接讀檔解析，避免內容漂移。

註：實際寫入 DB 為部署作業（psql 套用本檔），不在單元測試內執行。
"""
import json
import os
import re

import pytest

from services import conversational_config as cc

pytestmark = pytest.mark.unit

SEED = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                    "database", "migrations", "seed_conversational_diagnosis_contract_rule.sql")


def _read_sql():
    with open(SEED, encoding="utf-8") as f:
        return f.read()


def _load_metadata():
    sql = _read_sql()
    m = re.search(r"-- BEGIN_METADATA_JSON(.*?)-- END_METADATA_JSON", sql, re.DOTALL)
    assert m, "種子缺少 metadata JSON 標記區塊"
    block = m.group(1)
    return json.loads(block[block.index("{"):block.rindex("}") + 1])


@pytest.mark.req("conversational-diagnosis:8.1")
def test_seed_metadata_parses_to_contract_diag_config():
    cfg = cc._config_from_row(["property_manager"], _load_metadata())
    assert cfg is not None
    assert cfg.key == "contract_diag"
    assert cfg.persona_role == "property_manager"
    assert cfg.answer_mode == "conversational"
    assert cfg.enabled is True
    assert cfg.topic_scope == {"mode": "category", "category": "狀態判斷"}


@pytest.mark.req("conversational-diagnosis:8.1")
def test_seed_grounding_scope_is_api_with_full_mapping():
    gs = cc._config_from_row(["property_manager"], _load_metadata()).grounding_scope
    assert gs["select"] == "api"
    assert gs["endpoint"] == "jgb_contracts"
    assert gs["required_slots"] == ["contract_ref"]
    # API 驗證式（後端當裁判）：共用 params 只放身分過濾；識別走 search_params 依序試
    #   （先當 id、查無再當名稱）——因後端 id 與關鍵字為 AND 不能同送。數字名稱（如 0626）不漏。
    assert gs["params"] == {"role_id": "{session.role_id}"}
    assert gs["search_params"] == [
        {"contract_ids": "{form.contract_ref}"},
        {"keyword": "{form.contract_ref}"},
    ]
    assert gs["result_mapping"] == {
        "list_path": "data", "id_field": "id",
        "label_field": "title", "refine_param": "contract_ids",
        # domain-conversational-facets 任務 3/4：候選帶區別欄位（期間）+ 過多分流上限
        "label_fields": ["title", "date_start", "date_end"],
        "label_date_fields": ["date_start", "date_end"],
        "candidate_cap": 8,
    }


@pytest.mark.req("conversational-diagnosis:8.1")
def test_seed_indexed_by_category_router():
    """種子設定可被分類路由（config_for_category）以其 category 命中。"""
    md = _load_metadata()
    cfg = cc._config_from_row(["property_manager"], md)
    # 模擬 by_category 索引條件（topic_scope.mode==category 且 enabled）
    assert (cfg.topic_scope or {}).get("mode") == "category"
    assert (cfg.topic_scope or {}).get("category") == "狀態判斷"
    assert cfg.enabled is True


@pytest.mark.req("conversational-diagnosis:8.1")
def test_seed_is_rules_row_and_idempotent():
    sql = _read_sql()
    assert "'對話規則'" in sql                 # category=對話規則
    assert "property_manager" in sql           # target_user 角色（rules 載入鍵）
    assert "WHERE NOT EXISTS" in sql           # 冪等：重跑不重複插入


@pytest.mark.req("conversational-diagnosis:8.1")
def test_seed_rules_text_covers_required_behaviors():
    """rules_text 涵蓋：追問識別槽位、條件不足 ask、收齊 converge、多筆反問。"""
    sql = _read_sql()
    assert "contract_ref" in sql               # 追問識別槽位
    assert "ask" in sql and "converge" in sql  # 兩種 action
    assert "多筆" in sql                        # 多筆反問指引
