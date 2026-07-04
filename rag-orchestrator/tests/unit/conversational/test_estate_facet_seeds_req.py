"""unit:物件面向資料四件套種子驗證（estate-conversational-facets 任務 2.1–2.3 / R1, R2, R3, R4）。

種子檔為唯一事實來源，直接讀檔解析（實際寫入 DB 為部署作業）：
  - add_estate_facet_categories.sql：2 子掛既有母 `物件管理`（id 61 重用——不新建不修改母列）。
  - seed_estate_facet_system_context.sql：母薄層（兩軸一句話版）＋2 子 300–600 字；
    真碼口徑錨（兩軸/刪除三擋/通知中心/地址雙層/店舖/建約前提/查不到紅線）；≤4500。
  - seed_estate_facet_configs.sql：pm_estate_* 專屬鍵；引導 select=category＋明填 target_user；
    診斷 select=api jgb_estate_status＋deterministic_id:false＋secondary_call jgb_estate_detail；
    紅線全掛（不代操作／不斷言已刪除／地址只用對外顯示版）。
"""
import json
import os
import re

import pytest

from services import conversational_config as cc

pytestmark = pytest.mark.unit

_MIG = os.path.join(os.path.dirname(__file__), "..", "..", "..", "database", "migrations")
FACETS = ["物件操作引導", "物件現況診斷"]


def _read(name):
    with open(os.path.join(_MIG, name), encoding="utf-8") as f:
        return f.read()


# ════════ 2.1 categories：重用母列 ════════

@pytest.mark.req("estate-conversational-facets:1.1")
def test_categories_two_children_under_existing_parent():
    sql = _read("add_estate_facet_categories.sql")
    for facet in FACETS:
        assert re.search(rf"SELECT '{facet}'.*?'物件管理', TRUE, \d+\s*\nWHERE NOT EXISTS", sql), facet
    # 母列 id 61 既存——不得新建母、不得 UPDATE/DELETE 任何列
    assert "SELECT '物件管理', '物件管理'" not in sql, "不得新建母列（id 61 重用）"
    assert "UPDATE category_config" not in sql and "DELETE" not in sql


# ════════ 2.2 系統脈絡 ════════

def _bodies():
    sql = _read("seed_estate_facet_system_context.sql")
    child = dict(re.findall(r"'系統脈絡：物件領域-([^']+?)\(子面向\)',\s*\$CTX\$(.*?)\$CTX\$", sql, re.DOTALL))
    parent = re.findall(r"母共用\)',\s*\$CTX\$(.*?)\$CTX\$", sql, re.DOTALL)[0]
    return parent, child


@pytest.mark.req("estate-conversational-facets:1.5")
def test_context_rows_and_length_budget():
    parent, child = _bodies()
    assert set(child) == set(FACETS)
    assert len(parent) <= 300                                 # 母薄層
    for facet, body in child.items():
        assert 300 <= len(body) <= 600, f"{facet} 脈絡 {len(body)} 字，超出 300–600"
    assert 560 + len(parent) + max(len(b) for b in child.values()) <= 4500


@pytest.mark.req("estate-conversational-facets:1.3")
def test_parent_layer_two_axis_without_branch_details():
    """母層＝兩軸一句話版＋邊界；批次/店舖/地址細節一律下沉子層。"""
    parent, _ = _bodies()
    assert "兩條" in parent or "獨立" in parent               # 兩軸模型
    for kw in ("通知中心", "10MB", "/p/", "必填"):
        assert kw not in parent, f"母層含子層細節「{kw}」"


@pytest.mark.req("estate-conversational-facets:2.3")
def test_guide_context_carries_ground_truth_anchors():
    _, child = _bodies()
    guide = child["物件操作引導"]
    assert "刪除" in guide and "合約" in guide                 # 刪除三擋（有約不可刪）
    assert "對外" in guide and "完整地址" in guide             # 地址雙層
    assert "/p/" in guide or "招租店舖" in guide               # 店舖
    assert "儲存" in guide                                    # 儲存行為提醒
    assert "不影響既有合約" in guide or "既有合約" in guide     # 快照原則（有約可編輯）
    # 批次上傳範圍外（使用者裁定 2026-07-04）：脈絡不含批次機制、明文導客服
    assert "10MB" not in guide and "通知中心" not in guide
    assert "批次上傳" in guide and "客服" in guide


@pytest.mark.req("estate-conversational-facets:4.2")
def test_diagnosis_context_carries_decision_tree_and_red_line():
    _, child = _bodies()
    diag = child["物件現況診斷"]
    assert "洽談中" in diag and "租約中" in diag               # status 轉譯表
    assert "刊登中" in diag and ("必填" in diag or "欄位" in diag)  # 建約前提決策樹
    assert "已刪除" in diag and "不" in diag                   # 查不到紅線（禁斷言）
    sql = _read("seed_estate_facet_system_context.sql")
    assert sql.count("INSERT INTO knowledge_base") == 3        # 母＋2 子
    assert "UPDATE knowledge_base" not in sql


# ════════ 2.3 configs ════════

def _configs():
    sql = _read("seed_estate_facet_configs.sql")
    out = {}
    for key, block in re.findall(r"-- BEGIN_METADATA_JSON (\w+)(.*?)-- END_METADATA_JSON", sql, re.DOTALL):
        meta = json.loads(block[block.index("{"):block.rindex("}") + 1])
        role = meta["conversational_config"]["persona_role"]
        out[key] = cc._config_from_row([role], meta)
    return out


@pytest.mark.req("estate-conversational-facets:1.2")
def test_two_configs_route_by_facet():
    cfgs = _configs()
    expect = {"estate_guide": "物件操作引導", "estate_diag": "物件現況診斷"}
    assert set(cfgs) == set(expect)
    for key, facet in expect.items():
        assert cfgs[key].enabled
        assert cfgs[key].topic_scope == {"mode": "category", "category": facet}


@pytest.mark.req("estate-conversational-facets:1.6")
def test_persona_roles_estate_scoped():
    roles = [c.persona_role for c in _configs().values()]
    assert len(set(roles)) == 2
    assert all(r.startswith("pm_estate_") for r in roles)


@pytest.mark.req("estate-conversational-facets:1.7")
def test_grounding_shapes():
    cfgs = _configs()
    guide = cfgs["estate_guide"].grounding_scope
    assert guide["select"] == "category" and guide["category"] == "物件操作引導"
    # 收斂檢索 target_user 必須明填（account 坑：漏填 fallback persona_role → grounding 恆空）
    assert guide["target_user"] == "property_manager"

    diag = cfgs["estate_diag"].grounding_scope
    assert diag["select"] == "api" and diag["endpoint"] == "jgb_estate_status"   # 新鍵（修繕表單鍵不可用）
    assert diag["required_slots"] == ["estate_ref"]
    assert diag["deterministic_id"] is False                   # 識別多為物件名文字
    assert {"keyword": "{form.estate_ref}"} in diag["search_params"]
    assert diag["result_mapping"]["label_fields"] == ["title", "display_address", "status_zh"]
    sec = diag["secondary_call"]
    assert sec["endpoint"] == "jgb_estate_detail"
    assert sec["params"] == {"estate_id": "{row.id}"}
    assert sec["attach_as"] == "detail"                        # estates.py builder 讀此鍵


@pytest.mark.req("estate-conversational-facets:2.7")
def test_red_lines_everywhere():
    """紅線：不代操作（兩 config）；診斷不斷言已刪除＋地址只用對外顯示版；
    引導不教重傳＋刪除三擋。"""
    cfgs = _configs()
    for key, cfg in cfgs.items():
        rules = cfg.answer_rules or ""
        assert ("不代" in rules or "只指路" in rules), f"{key} 缺不代操作紅線"
    diag_rules = cfgs["estate_diag"].answer_rules or ""
    assert "已刪除" in diag_rules                              # 查不到紅線明文
    assert "對外顯示" in diag_rules                            # 地址遮罩口徑
    guide_rules = cfgs["estate_guide"].answer_rules or ""
    # 批次範圍外：紅線改「識別後導客服」，不得再教批次機制
    assert "批次上傳範圍外" in guide_rules and "導客服" in guide_rules
    assert "通知中心" not in guide_rules
