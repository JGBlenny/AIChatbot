"""unit:IoT 面向資料四件套種子驗證（iot-conversational-facets 任務 2.1–2.3 / R1, R2.6, R3, R5.5）。

種子檔為唯一事實來源，直接讀檔解析（實際寫入 DB 為部署作業）：
  - add_iot_facet_categories.sql：母智慧設備＋2 子、冪等；_domain_faces 衍生 2 面向。
  - seed_iot_facet_system_context.sql：母薄層（名詞對照，不含分支細節）＋2 子各 300–600 字；
    機制數字錨（每小時同步/自動復電/帳號失效/對帳）；≤4500。
  - seed_iot_facet_configs.sql：2 config 解析正確；pm_iot_* 專屬鍵；
    電表排障 select=api jgb_meters＋deterministic_id:false、設定引導 select=category＋
    明填 target_user；不代操作紅線全掛。
"""
import json
import os
import re

import pytest
from unittest.mock import AsyncMock, MagicMock

from services import conversational_config as cc

pytestmark = pytest.mark.unit

_MIG = os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "migrations")
FACETS = ["電表排障", "IoT設定引導"]


def _read(name):
    with open(os.path.join(_MIG, name), encoding="utf-8") as f:
        return f.read()


# ════════ 2.1 categories ════════

@pytest.mark.req("iot-conversational-facets:1.1")
def test_categories_two_children_idempotent():
    sql = _read("add_iot_facet_categories.sql")
    for facet in FACETS:
        assert re.search(rf"SELECT '{facet}'.*?'智慧設備', TRUE, \d+\s*\nWHERE NOT EXISTS", sql), facet
    assert "UPDATE category_config" not in sql and "DELETE" not in sql


@pytest.mark.req("iot-conversational-facets:1.2")
async def test_domain_faces_derives_two():
    from services.conversational_engine import _domain_faces
    from services.conversational_config import ConversationalConfig
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value="智慧設備")
    conn.fetch = AsyncMock(return_value=[{"category_value": f} for f in FACETS])
    pool = MagicMock()
    ctx = MagicMock(); ctx.__aenter__ = AsyncMock(return_value=conn); ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=ctx)
    cfg = ConversationalConfig(key="iot_meter",
                               topic_scope={"mode": "category", "category": "電表排障"})
    assert set(await _domain_faces(pool, cfg)) == set(FACETS)


# ════════ 2.2 系統脈絡 ════════

def _bodies():
    sql = _read("seed_iot_facet_system_context.sql")
    child = dict(re.findall(r"'系統脈絡：IoT領域-([^']+?)\(子面向\)',\s*\$CTX\$(.*?)\$CTX\$", sql, re.DOTALL))
    parent = re.findall(r"母共用\)',\s*\$CTX\$(.*?)\$CTX\$", sql, re.DOTALL)[0]
    return parent, child


@pytest.mark.req("iot-conversational-facets:1.5")
def test_context_rows_and_length_budget():
    parent, child = _bodies()
    assert set(child) == set(FACETS)
    assert len(parent) <= 300                                # 母薄層
    for facet, body in child.items():
        assert 300 <= len(body) <= 600, f"{facet} 脈絡 {len(body)} 字，超出 300–600"
    assert 560 + len(parent) + max(len(b) for b in child.values()) <= 4500


@pytest.mark.req("iot-conversational-facets:1.3")
def test_parent_layer_free_of_branch_details():
    """母層只放名詞對照——分支細節（自動復電/帳密真因/對帳）不得出現。"""
    parent, _ = _bodies()
    for kw in ("自動復電", "帳號密碼", "對帳", "申請"):
        assert kw not in parent, f"母層含分支細節「{kw}」"
    assert "台科電" in parent                                 # 名詞對照（台科電=DAE）


@pytest.mark.req("iot-conversational-facets:2.6")
def test_context_carries_ground_truth_anchors():
    _, child = _bodies()
    meter = child["電表排障"]
    assert "每小時" in meter                                  # 同步頻率機制
    assert "自動復電" in meter and "自動" in meter             # 儲值耗盡斷/復電
    assert "帳號" in meter and ("密碼" in meter or "API 服務" in meter)   # DAE 帳號失效真因
    assert "對帳" in meter                                    # 儲值 webhook 補認口徑
    assert "最後同步" in meter or "截至" in meter              # 離線快照語義
    setup = child["IoT設定引導"]
    assert "單價" in setup and ("台科電" in setup or "廠商" in setup)   # 單價為廠商端設定
    assert "串接" in setup or "綁定" in setup
    assert "帳務" in setup                                    # 儲值金流入帳分界
    sql = _read("seed_iot_facet_system_context.sql")
    assert sql.count("INSERT INTO knowledge_base") == 3       # 母＋2 子
    assert "UPDATE knowledge_base" not in sql


# ════════ 2.3 configs ════════

def _configs():
    sql = _read("seed_iot_facet_configs.sql")
    out = {}
    for key, block in re.findall(r"-- BEGIN_METADATA_JSON (\w+)(.*?)-- END_METADATA_JSON", sql, re.DOTALL):
        meta = json.loads(block[block.index("{"):block.rindex("}") + 1])
        role = meta["conversational_config"]["persona_role"]
        out[key] = cc._config_from_row([role], meta)
    return out


@pytest.mark.req("iot-conversational-facets:1.2")
def test_two_configs_route_by_facet():
    cfgs = _configs()
    expect = {"iot_meter": "電表排障", "iot_setup": "IoT設定引導"}
    assert set(cfgs) == set(expect)
    for key, facet in expect.items():
        cfg = cfgs[key]
        assert cfg.enabled and cfg.topic_scope == {"mode": "category", "category": facet}


@pytest.mark.req("iot-conversational-facets:1.6")
def test_persona_roles_iot_scoped():
    roles = [c.persona_role for c in _configs().values()]
    assert len(set(roles)) == 2
    assert all(r.startswith("pm_iot_") for r in roles)


@pytest.mark.req("iot-conversational-facets:2.1")
def test_grounding_shapes():
    cfgs = _configs()
    meter = cfgs["iot_meter"].grounding_scope
    assert meter["select"] == "api" and meter["endpoint"] == "jgb_meters"
    assert meter["required_slots"] == ["meter_ref"]
    assert meter["deterministic_id"] is False                 # 識別多為物件名/房號文字
    assert {"keyword": "{form.meter_ref}"} in meter["search_params"]
    assert meter["result_mapping"]["label_fields"] == ["name", "estate_name", "meter_type"]
    setup = cfgs["iot_setup"].grounding_scope
    assert setup["select"] == "category" and setup["category"] == "IoT設定引導"
    # 收斂檢索 target_user 必須明填（account 坑：漏填 fallback persona_role → grounding 恆空）
    assert setup["target_user"] == "property_manager"


@pytest.mark.req("iot-conversational-facets:5.5")
def test_no_remote_operation_red_line_everywhere():
    """不代操作紅線：兩 config 的 answer_rules 都必須明文（只指路不代執行）。"""
    for key, cfg in _configs().items():
        rules = cfg.answer_rules or ""
        assert ("不代" in rules or "只指路" in rules or "代為操作" in rules), f"{key} 缺不代操作紅線"
