"""unit:合約 5 子面向資料四件套種子驗證（contract-conversational-facets 任務 3.1–3.3 / R1.1–1.5, R2.4–2.6, R5.x, R7.2）。

三支部署種子為唯一事實來源，直接讀檔解析驗內容（避免漂移；實際寫入 DB 為部署作業）：
  - add_contract_facet_categories_v2.sql：5 子分類 parent=系統合約、冪等；_domain_faces 衍生含 6 面向。
  - seed_contract_facet_system_context.sql：5 列脈絡（categories=[面向]）300–600 字；
    合約異動列含申請書三段骨架＋團隊擁有者提示；三層疊加長度預算 ≤4500；INSERT-only。
  - seed_contract_facet_configs.sql：5 筆 config 經 _config_from_row 解析正確
    （topic_scope.category=面向；診斷 4 面向 select='api' 同狀態判斷形狀；建約引導 select='category'）；
    persona_role 為面向專屬鍵（不得用 property_manager——load_rules 以 role 鍵取最新，共用鍵會蓋掉狀態判斷規則）；
    persona 規則含面向差異錨點與「API 現值為準」。
"""
import json
import os
import re

import pytest
from unittest.mock import AsyncMock, MagicMock

from services import conversational_config as cc

pytestmark = pytest.mark.unit

_MIG = os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "migrations")
FACETS = ["合約異動", "退租收尾", "續約", "建約引導", "簽署排障"]


def _read(name):
    with open(os.path.join(_MIG, name), encoding="utf-8") as f:
        return f.read()


# ════════ 3.1 category_config 子分類 ════════

@pytest.mark.req("contract-conversational-facets:1.1")
def test_categories_v2_inserts_five_children_idempotent():
    sql = _read("add_contract_facet_categories_v2.sql")
    for facet in FACETS:
        m = re.search(rf"SELECT '{facet}'.*?'系統合約', TRUE, \d+\s*\nWHERE NOT EXISTS", sql)
        assert m, f"缺子分類 {facet}（parent=系統合約、冪等 WHERE NOT EXISTS）"
    assert "UPDATE category_config" not in sql and "DELETE" not in sql


@pytest.mark.req("contract-conversational-facets:8.1")
async def test_domain_faces_derives_six_facets():
    """_domain_faces 由 category_config 衍生：任一子面向進場 → 集合含全部 6 面向（含狀態判斷）。"""
    from services.conversational_engine import _domain_faces
    from services.conversational_config import ConversationalConfig
    children = ["狀態判斷"] + FACETS

    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value="系統合約")
    conn.fetch = AsyncMock(return_value=[{"category_value": c} for c in children])
    pool = MagicMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=ctx)

    cfg = ConversationalConfig(key="contract_change",
                               topic_scope={"mode": "category", "category": "合約異動"})
    faces = await _domain_faces(pool, cfg)
    assert set(faces) == set(children) and len(faces) == 6


# ════════ 3.2 系統脈絡 5 列 ════════

def _context_bodies():
    sql = _read("seed_contract_facet_system_context.sql")
    pairs = re.findall(
        r"'系統脈絡：合約領域-([^']+?)\(子面向\)',\s*\$CTX\$(.*?)\$CTX\$", sql, re.DOTALL)
    return dict(pairs)


@pytest.mark.req("contract-conversational-facets:1.3")
def test_context_five_rows_within_length_budget():
    bodies = _context_bodies()
    assert set(bodies) == set(FACETS)
    for facet, body in bodies.items():
        assert 300 <= len(body) <= 600, f"{facet} 脈絡 {len(body)} 字，超出 300–600 規格"


@pytest.mark.req("contract-conversational-facets:2.4")
def test_change_context_carries_application_skeleton():
    body = _context_bodies()["合約異動"]
    # 申請書三段骨架關鍵 token（e2e 斷言同源）
    assert "service@jgbsmart.com" in body
    assert "異動前" in body and "異動後" in body
    assert "【申請書填寫內容】" in body and "【範本與提交】" in body and "【注意事項】" in body
    assert "團隊擁有者" in body                      # R2.5 團隊管理者提示
    assert "藍字" in body and "不一致" in body        # R2.6 區分事實
    assert "保留" in body and "費用" in body          # 金箍棒保留異動與否及費用權利


@pytest.mark.req("contract-conversational-facets:1.5")
def test_context_stack_budget_with_existing_parent():
    """三層長度預算：既有母『系統合約』＋最長新子 ≤ 4500 − base 概算（比照前例 base≈560）。"""
    parent = re.findall(r"\$CTX\$(.*?)\$CTX\$",
                        _read("seed_domain_contract_system_context.sql"), re.DOTALL)[0]
    longest = max(len(b) for b in _context_bodies().values())
    assert 560 + len(parent) + longest <= 4500


@pytest.mark.req("contract-conversational-facets:1.3")
def test_context_seed_insert_only_tagged_by_facet():
    sql = _read("seed_contract_facet_system_context.sql")
    assert sql.count("INSERT INTO knowledge_base") == 5
    assert "UPDATE knowledge_base" not in sql and "DELETE FROM knowledge_base" not in sql
    for facet in FACETS:
        assert f"ARRAY['{facet}']::text[]" in sql    # 一列一面向（categories 單值）


# ════════ 3.3 對話 config 5 筆 ════════

def _configs():
    sql = _read("seed_contract_facet_configs.sql")
    out = {}
    for key, block in re.findall(
            r"-- BEGIN_METADATA_JSON (\w+)(.*?)-- END_METADATA_JSON", sql, re.DOTALL):
        meta = json.loads(block[block.index("{"):block.rindex("}") + 1])
        role = meta["conversational_config"]["persona_role"]
        out[key] = cc._config_from_row([role], meta)
    return out


def _rules_texts():
    sql = _read("seed_contract_facet_configs.sql")
    return dict(re.findall(r"'對話規則：([^']+?)',\s*\$RULES\$(.*?)\$RULES\$", sql, re.DOTALL))


@pytest.mark.req("contract-conversational-facets:1.2")
def test_five_configs_route_by_facet_category():
    cfgs = _configs()
    expect = {"contract_change": "合約異動", "contract_closeout": "退租收尾",
              "contract_renew": "續約", "contract_create_guide": "建約引導",
              "contract_sign": "簽署排障"}
    assert set(cfgs) == set(expect)
    for key, facet in expect.items():
        cfg = cfgs[key]
        assert cfg.enabled and cfg.answer_mode == "conversational"
        assert cfg.topic_scope == {"mode": "category", "category": facet}
        assert cfg.answer_rules and "API 現值" in cfg.answer_rules


@pytest.mark.req("contract-conversational-facets:1.2")
def test_diagnosis_configs_share_status_grounding_shape():
    cfgs = _configs()
    for key in ("contract_change", "contract_closeout", "contract_renew", "contract_sign"):
        gs = cfgs[key].grounding_scope
        assert gs["select"] == "api" and gs["endpoint"] == "jgb_contracts"
        assert gs["required_slots"] == ["contract_ref"]
        assert gs["params"] == {"role_id": "{session.role_id}"}
        assert gs["search_params"] == [{"contract_ids": "{form.contract_ref}"},
                                       {"keyword": "{form.contract_ref}"}]
        assert gs["result_mapping"]["candidate_cap"] == 8       # 沿用狀態判斷形狀


@pytest.mark.req("contract-conversational-facets:3.3")
def test_closeout_declares_secondary_call_for_bills():
    """退租收尾宣告 secondary_call（G3）：單筆收斂後查帳單、attach 為 bills（{row.id} 插值）。"""
    sec = _configs()["contract_closeout"].grounding_scope["secondary_call"]
    assert sec["endpoint"] == "jgb_bills"
    assert sec["params"]["contract_ids"] == "{row.id}"
    assert sec["attach_as"] == "bills" and sec["list_path"] == "data"
    # 合約異動宣告 G5 permissions 附掛（權限擋 vs 狀態擋分流，contract 7.4）
    g5 = _configs()["contract_change"].grounding_scope["secondary_call"]
    assert g5["endpoint"] == "jgb_member_permissions"
    assert g5["params"]["user_id"] == "{session.user_id}"
    assert g5["attach_as"] == "requester_permissions"
    # 其餘 3 面向不宣告（不做無謂二次查詢）
    for key in ("contract_renew", "contract_sign", "contract_create_guide"):
        assert "secondary_call" not in (_configs()[key].grounding_scope or {})


@pytest.mark.req("contract-conversational-facets:5.1")
def test_create_guide_grounds_by_knowledge_category():
    gs = _configs()["contract_create_guide"].grounding_scope
    assert gs["select"] == "category" and gs["category"] == "建約引導"
    assert gs["target_user"] == "property_manager"              # 知識過濾用真實角色


@pytest.mark.req("contract-conversational-facets:11.1")
def test_persona_roles_are_facet_scoped_not_property_manager():
    """load_rules 以 target_user 鍵取最新一筆——共用 property_manager 會蓋掉既有狀態判斷規則。"""
    sql = _read("seed_contract_facet_configs.sql")
    roles = [cfg.persona_role for cfg in _configs().values()]
    assert len(set(roles)) == 5                                  # 各自獨立
    assert "property_manager" not in roles
    assert "ARRAY['property_manager']" not in sql                # 規則列鍵也不共用


@pytest.mark.req("contract-conversational-facets:2.1")
def test_persona_rules_carry_facet_specific_behaviors():
    rules = _rules_texts()
    assert "要改哪個項目" in rules["合約異動"]                     # 追問「要改什麼」
    for slot in ("change_item", "change_before", "change_after"):
        assert slot in rules["合約異動"]                          # 申請書槽位
    assert "查閱權限" in rules["合約異動"]                        # 狀態擋 vs 權限擋分流
    assert "退租型態" in rules["退租收尾"] or "closeout_type" in rules["退租收尾"]
    assert "不追問其他欄位" in rules["續約"]                      # 直趨收斂
    assert "兩輪" in rules["建約引導"]
    assert '涉及特定合約現況）→ scope="switch"' in rules["建約引導"].replace("（", "（") \
        or 'scope="switch"' in rules["建約引導"]                  # 跨型態轉出
    assert "客服" in rules["建約引導"]                            # 特殊個案導客服
    assert "現象" in rules["簽署排障"] and "客服" in rules["簽署排障"]
    for text in rules.values():
        assert "API 現值為準" in text                             # R7.2 全含
