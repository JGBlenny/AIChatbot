"""unit:帳號面向資料四件套種子驗證（account-conversational-facets 任務 2.1–2.3 / R1, R2, R3, R4, R5）。

種子檔為唯一事實來源，直接讀檔解析（實際寫入 DB 為部署作業）：
  - add_account_facet_categories.sql：母帳號中心＋4 子、冪等；_domain_faces 衍生 4 面向。
  - seed_account_facet_system_context.sql：母薄層（名詞對照，不含兩類機制細節）＋
    4 子各 300–600 字；機制數字錨（300 秒/三次/120 秒/72 小時/確切寫法/變更角色）；≤4500。
  - seed_account_facet_configs.sql：4 config 解析正確；pm_account_* 專屬鍵；
    登入排障 select=api jgb_contracts、其餘 select=category；驗證碼紅線全掛。
"""
import json
import os
import re

import pytest
from unittest.mock import AsyncMock, MagicMock

from services import conversational_config as cc

pytestmark = pytest.mark.unit

_MIG = os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "migrations")
FACETS = ["註冊驗證排障", "登入排障", "帳號綁定異動", "團隊成員權限"]
EXTERNAL = ["註冊驗證排障", "登入排障"]          # 外部類（進不了系統的人）
INTERNAL = ["帳號綁定異動", "團隊成員權限"]      # 內部類（已登入業者）


def _read(name):
    with open(os.path.join(_MIG, name), encoding="utf-8") as f:
        return f.read()


# ════════ 2.1 categories ════════

@pytest.mark.req("account-conversational-facets:1.1")
def test_categories_four_children_idempotent():
    sql = _read("add_account_facet_categories.sql")
    for facet in FACETS:
        assert re.search(rf"SELECT '{facet}'.*?'帳號中心', TRUE, \d+\s*\nWHERE NOT EXISTS", sql), facet
    assert "UPDATE category_config" not in sql and "DELETE" not in sql


@pytest.mark.req("account-conversational-facets:7.1")
async def test_domain_faces_derives_four():
    from services.conversational_engine import _domain_faces
    from services.conversational_config import ConversationalConfig
    conn = MagicMock()
    conn.fetchval = AsyncMock(return_value="帳號中心")
    conn.fetch = AsyncMock(return_value=[{"category_value": f} for f in FACETS])
    pool = MagicMock()
    ctx = MagicMock(); ctx.__aenter__ = AsyncMock(return_value=conn); ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=ctx)
    cfg = ConversationalConfig(key="account_login",
                               topic_scope={"mode": "category", "category": "登入排障"})
    assert set(await _domain_faces(pool, cfg)) == set(FACETS)


# ════════ 2.2 系統脈絡 ════════

def _bodies():
    sql = _read("seed_account_facet_system_context.sql")
    child = dict(re.findall(r"'系統脈絡：帳號領域-([^']+?)\(子面向\)',\s*\$CTX\$(.*?)\$CTX\$", sql, re.DOTALL))
    parent = re.findall(r"母共用\)',\s*\$CTX\$(.*?)\$CTX\$", sql, re.DOTALL)[0]
    return parent, child


@pytest.mark.req("account-conversational-facets:1.5")
def test_context_rows_and_length_budget():
    parent, child = _bodies()
    assert set(child) == set(FACETS)
    assert len(parent) <= 300                                # 母薄層（R1.3 隔離的前提）
    for facet, body in child.items():
        assert 300 <= len(body) <= 600, f"{facet} 脈絡 {len(body)} 字，超出 300–600"
    assert 560 + len(parent) + max(len(b) for b in child.values()) <= 4500


@pytest.mark.req("account-conversational-facets:1.3")
def test_parent_layer_free_of_class_mechanism_details():
    """母層只放名詞對照——外部類機制詞（驗證碼/LINE）與內部類機制詞（申請書/變更角色）都不得出現。"""
    parent, _ = _bodies()
    for kw in ("驗證碼", "LINE", "申請書", "變更角色", "忘記密碼"):
        assert kw not in parent, f"母層含機制細節「{kw}」，違反薄母層自律"


@pytest.mark.req("account-conversational-facets:2.2")
def test_context_carries_ground_truth_anchors():
    _, child = _bodies()
    reg = child["註冊驗證排障"]
    assert "300 秒" in reg or "5 分鐘" in reg                 # TTL（research 主題 1）
    assert "三次" in reg or "3 次" in reg                     # 錯誤次數失效
    assert "120 秒" in reg and "72 小時" in reg               # 冷卻＋快速驗證信
    assert "客服" in reg                                      # B.Bug 導客服
    login = child["登入排障"]
    assert "LINE" in login and "帳號密碼" in login            # 帳密帳號不能 LINE 快速登入
    assert "確切寫法" in login                                 # 大小寫口徑
    assert "忘記密碼" in login and ("身分" in login or "角色" in login)
    binding = child["帳號綁定異動"]
    assert "申請書" in binding and "客服" in binding           # 後台作業出口
    assert "簽署" in binding                                   # 藍字兩但書
    team = child["團隊成員權限"]
    assert "變更角色" in team and "註冊" in team               # 成員需先註冊＋角色指派
    sql = _read("seed_account_facet_system_context.sql")
    assert sql.count("INSERT INTO knowledge_base") == 5       # 母＋4 子
    assert "UPDATE knowledge_base" not in sql


@pytest.mark.req("account-conversational-facets:1.3")
def test_class_isolation_between_children():
    """外部類子層不得含內部類機制詞；內部類子層不得含外部類機制詞。"""
    _, child = _bodies()
    for f in EXTERNAL:
        assert "申請書" not in child[f], f"外部面向「{f}」滲入內部類機制"
    for f in INTERNAL:
        assert "驗證碼" not in child[f], f"內部面向「{f}」滲入外部類機制"


# ════════ 2.3 configs ════════

def _configs():
    sql = _read("seed_account_facet_configs.sql")
    out = {}
    for key, block in re.findall(r"-- BEGIN_METADATA_JSON (\w+)(.*?)-- END_METADATA_JSON", sql, re.DOTALL):
        meta = json.loads(block[block.index("{"):block.rindex("}") + 1])
        role = meta["conversational_config"]["persona_role"]
        out[key] = cc._config_from_row([role], meta)
    return out


@pytest.mark.req("account-conversational-facets:1.2")
def test_four_configs_route_by_facet():
    cfgs = _configs()
    expect = {"account_register": "註冊驗證排障", "account_login": "登入排障",
              "account_binding": "帳號綁定異動", "account_team": "團隊成員權限"}
    assert set(cfgs) == set(expect)
    for key, facet in expect.items():
        cfg = cfgs[key]
        assert cfg.enabled and cfg.topic_scope == {"mode": "category", "category": facet}


@pytest.mark.req("account-conversational-facets:1.6")
def test_persona_roles_account_scoped():
    roles = [c.persona_role for c in _configs().values()]
    assert len(set(roles)) == 4
    assert all(r.startswith("pm_account_") for r in roles)
    assert "property_manager" not in roles


@pytest.mark.req("account-conversational-facets:3.1")
def test_grounding_shapes():
    cfgs = _configs()
    login = cfgs["account_login"].grounding_scope
    assert login["select"] == "api" and login["endpoint"] == "jgb_contracts"
    assert login["required_slots"] == ["contract_ref"]
    assert {"contract_ids": "{form.contract_ref}"} in login["search_params"]
    assert login["result_mapping"]["label_fields"] == ["title", "date_start", "date_end"]
    for key, facet in (("account_register", "註冊驗證排障"),
                       ("account_binding", "帳號綁定異動"),
                       ("account_team", "團隊成員權限")):
        gs = cfgs[key].grounding_scope
        assert gs["select"] == "category" and gs["category"] == facet
        assert "secondary_call" not in gs
        # 收斂檢索的 target_user 必須明填：漏填會 fallback 到 persona_role
        # （pm_account_*），與知識列的 property_manager 對不上 → grounding 恆空
        assert gs["target_user"] == "property_manager", f"{key} 缺 grounding target_user"


@pytest.mark.req("account-conversational-facets:6.2")
def test_verification_code_red_line_everywhere():
    """驗證碼紅線：四 config 的 answer_rules 都必須明文禁止輸出驗證碼值。"""
    for key, cfg in _configs().items():
        assert cfg.answer_rules and "驗證碼" in cfg.answer_rules, f"{key} 缺驗證碼紅線"


@pytest.mark.req("account-conversational-facets:1.7")
def test_external_personas_speak_proxy_mode():
    """外部類 persona（代問模式）：規則文字含轉述給租客的定調；內部類則為業者自身操作。"""
    sql = _read("seed_account_facet_configs.sql")
    rules = dict(re.findall(r"'對話規則：([^']+)',\s*\$RULES\$(.*?)\$RULES\$", sql, re.DOTALL))
    assert set(rules) == set(FACETS)
    for f in EXTERNAL:
        assert "轉述" in rules[f] or "轉達" in rules[f], f"外部面向「{f}」persona 缺代問模式定調"
    assert "申請書" in rules["帳號綁定異動"]
