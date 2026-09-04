"""unit 層：知識批次匯入工具的欄位契約（steering knowledge.md「instance applicability 必填契約」P1d）。
2026-09-04 盤查 retrieval-improvement-loop 時抓到：舊工具完全不寫 generation_metadata.instance_applicability，
照它匯入的任何新列都會被不變量 10 列為未宣告；updates 也會把未宣告舊列的 updated_at 推過生效日。
"""
import json

import pytest

from tools import import_facet_knowledge as imp

pytestmark = pytest.mark.unit


def _k(**over):
    base = {"question": "物件批次匯入", "answer": "系統支援物件批次匯入。", "target_user": ["property_manager"],
            "instance_applicability": "general"}
    base.update(over)
    return base


# ── 驗證：缺／錯就整批不寫 ─────────────────────────────────────────────────────
def test_valid_batch_has_no_errors():
    assert imp.validate_batch({"knowledge": [_k()], "anchors": [{"facet": "登入排障", "question": "登不進去", "instance_applicability": "instance"}]}) == []


def test_missing_declaration_is_an_error_by_default():
    errs = imp.validate_batch({"knowledge": [_k(instance_applicability=None)]})
    assert len(errs) == 1 and "缺 instance_applicability" in errs[0]


def test_legacy_flag_allows_missing_but_not_illegal():
    assert imp.validate_batch({"knowledge": [_k(instance_applicability=None)]}, allow_legacy_undeclared=True) == []
    errs = imp.validate_batch({"knowledge": [_k(instance_applicability="Instance")]}, allow_legacy_undeclared=True)
    assert len(errs) == 1 and "不合法" in errs[0]          # ⛔ 變體不猜（與 services/instance_applicability 同紀律）


@pytest.mark.parametrize("bad", ["true", "是", "GENERAL", "unknown", ""])
def test_illegal_values_rejected(bad):
    assert any("不合法" in e for e in imp.validate_batch({"knowledge": [_k(instance_applicability=bad)]}))


def test_anchor_requires_facet_and_declaration():
    errs = imp.validate_batch({"anchors": [{"question": "登不進去"}]})
    assert any("缺 facet" in e for e in errs) and any("缺 instance_applicability" in e for e in errs)


def test_array_fields_must_be_lists():
    errs = imp.validate_batch({"knowledge": [_k(target_user="property_manager")]})
    assert any("target_user 必須是陣列" in e for e in errs)


def test_update_entry_needs_id_and_content():
    errs = imp.validate_batch({"updates": [{"id": "3600"}]})
    assert any("id 必須是整數" in e for e in errs) and any("至少一個" in e for e in errs)


# ── 寫入形狀：鍵名與 services/instance_applicability 讀取契約一致 ───────────────
def test_generation_metadata_shape_matches_reader():
    from services.instance_applicability import knowledge_instance_applicability, KNOWLEDGE_APPLICABILITY_KEY
    meta = imp.build_generation_metadata(_k(instance_applicability="instance"))
    assert meta[KNOWLEDGE_APPLICABILITY_KEY] == "instance"
    assert knowledge_instance_applicability({"generation_metadata": meta}) == "instance"   # 讀得回來
    assert imp.build_generation_metadata(_k(instance_applicability=None)) is None            # legacy ⇒ 不寫鍵


def test_insert_params_defaults_and_overrides():
    p = imp.insert_params_knowledge(_k())
    assert p["business_types"] == ["system_provider"] and p["generation_metadata"]["instance_applicability"] == "general"
    p2 = imp.insert_params_knowledge(_k(business_types=["property_agency"], target_user=["prospect"]))
    assert p2["business_types"] == ["property_agency"] and p2["target_user"] == ["prospect"]
    a = imp.insert_params_anchor({"facet": "登入排障", "question": "登不進去", "instance_applicability": "instance"})
    assert a["answer"] == "" and a["categories"] == ["登入排障"] and a["target_user"] == ["property_manager"]


# ── updates：不得把未宣告舊列悄悄推過生效日 ────────────────────────────────────
def test_update_refused_when_row_undeclared_and_batch_silent():
    verdict, why = imp.update_decision(None, {"id": 3600, "question": "線上簽約"})
    assert verdict == "refuse" and "尚未宣告" in why


def test_update_allowed_when_row_declared_or_batch_declares():
    assert imp.update_decision({"instance_applicability": "general"}, {"id": 3600, "answer": "x"}) == ("write", None)
    assert imp.update_decision(json.dumps({"instance_applicability": "general"}), {"id": 3600, "answer": "x"}) == ("write", None)
    assert imp.update_decision(None, {"id": 3600, "answer": "x", "instance_applicability": "general"}) == ("write", "general")
    assert imp.update_decision({"instance_applicability": "Instance"}, {"id": 1, "answer": "x"})[0] == "refuse"   # 既有值是變體 ⇒ 視同未宣告


def test_argv_parsing():
    assert imp._parse_argv(["a.json", "--dry-run"]) == ("a.json", True, False)
    assert imp._parse_argv(["--allow-legacy-undeclared"])[1:] == (False, True)
