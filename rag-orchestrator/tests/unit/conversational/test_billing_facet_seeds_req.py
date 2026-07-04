"""unit:帳務面向資料四件套種子驗證（billing-conversational-facets 任務 4.1–4.3 / R1, R7.2）。

種子檔為唯一事實來源，直接讀檔解析（實際寫入 DB 為部署作業）：
  - add_billing_facet_categories.sql：母系統帳務＋5 子、冪等；_domain_faces 衍生 5 面向。
  - seed_billing_facet_system_context.sql：母（狀態機表）＋5 子各 300–600 字；
    關鍵 ground truth 錨（超商 5/15/25、可見三條件、number 空、兩機制、一元帳單）；預算 ≤4500。
  - seed_billing_facet_configs.sql：5 config 解析正確；persona_role 帳務專屬鍵（不與
    property_manager／合約鍵共用）；診斷 4 面向 select=api＋bill_ref/合約鏈；
    金流排障/發票 secondary_call 宣告；皆含金額紅線。
"""
import json
import os
import re

import pytest
from unittest.mock import AsyncMock, MagicMock

from services import conversational_config as cc

pytestmark = pytest.mark.unit

_MIG = os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "migrations")
FACETS = ["繳費金流排障", "帳單異常", "發票", "滯納金", "帳單設定引導"]


def _read(name):
    with open(os.path.join(_MIG, name), encoding="utf-8") as f:
        return f.read()


# ════════ 4.1 categories ════════

@pytest.mark.req("billing-conversational-facets:1.1")
def test_categories_five_children_idempotent():
    sql = _read("add_billing_facet_categories.sql")
    for facet in FACETS:
        assert re.search(rf"SELECT '{facet}'.*?'系統帳務', TRUE, \d+\s*\nWHERE NOT EXISTS", sql), facet
    assert "UPDATE category_config" not in sql and "DELETE" not in sql


@pytest.mark.req("billing-conversational-facets:1.1")
async def test_domain_faces_derives_five():
    from services.conversational_engine import _domain_faces
    from services.conversational_config import ConversationalConfig
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value="系統帳務")
    conn.fetch = AsyncMock(return_value=[{"category_value": f} for f in FACETS])
    pool = MagicMock()
    ctx = MagicMock(); ctx.__aenter__ = AsyncMock(return_value=conn); ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=ctx)
    cfg = ConversationalConfig(key="billing_flow",
                               topic_scope={"mode": "category", "category": "繳費金流排障"})
    assert set(await _domain_faces(pool, cfg)) == set(FACETS)


# ════════ 4.2 系統脈絡 ════════

def _bodies():
    sql = _read("seed_billing_facet_system_context.sql")
    child = dict(re.findall(r"'系統脈絡：帳務領域-([^']+?)\(子面向\)',\s*\$CTX\$(.*?)\$CTX\$", sql, re.DOTALL))
    parent = re.findall(r"母共用\)',\s*\$CTX\$(.*?)\$CTX\$", sql, re.DOTALL)[0]
    return parent, child


@pytest.mark.req("billing-conversational-facets:1.3")
def test_context_rows_and_length_budget():
    parent, child = _bodies()
    assert set(child) == set(FACETS)
    for facet, body in child.items():
        assert 300 <= len(body) <= 600, f"{facet} 脈絡 {len(body)} 字，超出 300–600"
    assert 560 + len(parent) + max(len(b) for b in child.values()) <= 4500


@pytest.mark.req("billing-conversational-facets:1.3")
def test_context_carries_ground_truth_anchors():
    parent, child = _bodies()
    for v in (1, 2, 8, 16, 32, 64):
        assert str(v) in parent                              # 狀態機表
    assert "待對帳" in parent and "存值" in parent
    assert "5、15、25" in child["繳費金流排障"]                # 超商撥付時程
    assert "三條件" in child["帳單異常"] or "付款方" in child["帳單異常"]
    assert "三軌" in child["發票"] or "到帳後" in child["發票"]
    assert "差額發票" in child["發票"] and "客服" in child["發票"]
    assert "機制" in child["滯納金"] and "不累加" in child["滯納金"]
    assert "一元帳單" in child["帳單設定引導"]
    sql = _read("seed_billing_facet_system_context.sql")
    assert sql.count("INSERT INTO knowledge_base") == 6      # 母＋5 子
    assert "UPDATE knowledge_base" not in sql


# ════════ 4.3 configs ════════

def _configs():
    sql = _read("seed_billing_facet_configs.sql")
    out = {}
    for key, block in re.findall(r"-- BEGIN_METADATA_JSON (\w+)(.*?)-- END_METADATA_JSON", sql, re.DOTALL):
        meta = json.loads(block[block.index("{"):block.rindex("}") + 1])
        role = meta["conversational_config"]["persona_role"]
        out[key] = cc._config_from_row([role], meta)
    return out


@pytest.mark.req("billing-conversational-facets:1.2")
def test_five_configs_route_by_facet():
    cfgs = _configs()
    expect = {"billing_flow": "繳費金流排障", "billing_anomaly": "帳單異常",
              "billing_invoice": "發票", "billing_late_fee": "滯納金",
              "billing_setup_guide": "帳單設定引導"}
    assert set(cfgs) == set(expect)
    for key, facet in expect.items():
        cfg = cfgs[key]
        assert cfg.enabled and cfg.topic_scope == {"mode": "category", "category": facet}
        assert cfg.answer_rules and ("金額" in cfg.answer_rules or "現值" in cfg.answer_rules)


@pytest.mark.req("billing-conversational-facets:1.6")
def test_persona_roles_billing_scoped():
    roles = [c.persona_role for c in _configs().values()]
    assert len(set(roles)) == 5
    assert all(r.startswith("pm_billing_") for r in roles)
    assert "property_manager" not in roles


@pytest.mark.req("billing-conversational-facets:2.1")
def test_grounding_shapes():
    cfgs = _configs()
    for key in ("billing_flow", "billing_anomaly", "billing_invoice"):
        gs = cfgs[key].grounding_scope
        assert gs["select"] == "api" and gs["endpoint"] == "jgb_bills"
        assert gs["required_slots"] == ["bill_ref"]
        assert gs["search_params"] == [{"bill_ref": "{form.bill_ref}"}]     # adapter 多層在領域檔
        assert gs["result_mapping"]["label_fields"] == ["title", "sub_title", "date_expire", "total"]
    lf = cfgs["billing_late_fee"].grounding_scope
    assert lf["endpoint"] == "jgb_contracts" and lf["required_slots"] == ["contract_ref"]
    sg = cfgs["billing_setup_guide"].grounding_scope
    assert sg["select"] == "category" and sg["category"] == "帳單設定引導"
    assert sg["limit"] == 14   # 面向知識 12 筆 > 預設 8——id 排序擠新知識（estate M2 同款根因）


@pytest.mark.req("billing-conversational-facets:7.5")
def test_secondary_call_declarations():
    cfgs = _configs()
    sec = cfgs["billing_flow"].grounding_scope["secondary_call"]
    assert sec["endpoint"] == "jgb_payment_logs" and sec["attach_as"] == "payment_logs"
    assert sec["params"]["bill_id"] == "{row.id}" and sec["list_path"] == "data.payment_logs"
    sec2 = cfgs["billing_invoice"].grounding_scope["secondary_call"]
    assert sec2["endpoint"] == "jgb_invoices" and sec2["attach_as"] == "invoices"
    for key in ("billing_anomaly", "billing_late_fee", "billing_setup_guide"):
        assert "secondary_call" not in (cfgs[key].grounding_scope or {})
