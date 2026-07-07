"""unit:收斂作答規則 answer_rules——掛在各自對話設定上、收斂時加載（per 對話，非領域知識）。

「資料在手直接答/禁推託/只有一份時比較請補編號」是**該對話（API 單筆診斷）的作答行為**，
不是領域背景知識：放面向系統脈絡會（1）切到別面向就消失（2）新診斷領域得各抄一份。
故設計為 config.answer_rules（設定資料承載，零改碼可調），引擎收斂組答時附加於 system_md 後；
面向系統脈絡回歸純領域框架。mock 隔離，確定性 unit。
"""
import json
import os
import re

import pytest
from unittest.mock import AsyncMock, MagicMock

from services import conversational_config as cc
from services.conversational_engine import ConversationalEngine
from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit

SEED = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                    "database", "migrations", "seed_conversational_diagnosis_contract_rule.sql")


# ── 設定解析：metadata.answer_rules → config.answer_rules（未設 → None，向後相容）──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_config_parses_answer_rules():
    md = {"conversational_config": {"key": "k", "answer_rules": "鐵則文字"}}
    cfg = cc._config_from_row(["property_manager"], md)
    assert cfg.answer_rules == "鐵則文字"
    cfg2 = cc._config_from_row(["property_manager"], {"conversational_config": {"key": "k"}})
    assert cfg2.answer_rules is None


def _cfg(answer_rules=None):
    return ConversationalConfig(
        key="contract_diag", persona_role="property_manager",
        grounding_scope={"select": "api", "endpoint": "e", "required_slots": ["contract_ref"],
                         "params": {}, "result_mapping": {"list_path": "data", "id_field": "id",
                                                          "label_field": "title"}},
        topic_scope={"mode": "category", "category": "狀態判斷"},
        answer_rules=answer_rules)


def _engine():
    optimizer = MagicMock()
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=optimizer, retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="DOMAIN_MD"),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=MagicMock())
    eng._save = AsyncMock()
    eng._ground_by_api = AsyncMock(return_value={"kind": "converge", "grounding": "G"})
    return eng


# ── 確定性識別收斂：decision.system_md ＝ 領域脈絡＋answer_rules ──
@pytest.mark.req("domain-conversational-facets:3.2")
async def test_deterministic_fill_converge_appends_answer_rules():
    eng = _engine()
    eng.get_state = AsyncMock(return_value={"config_key": "contract_diag",
                                            "collected_fields": {}, "asked_count": 1})
    d = await eng.prepare("s", "u", 7, "84800", config=_cfg("【作答鐵則】不推託"))
    assert d["kind"] == "converge"
    assert d["system_md"].startswith("DOMAIN_MD")
    assert d["system_md"].endswith("【作答鐵則】不推託")


# ── 插點A（候選選擇）收斂：同樣附加 ──
@pytest.mark.req("domain-conversational-facets:3.2")
async def test_candidate_pick_converge_appends_answer_rules():
    eng = _engine()
    eng.get_state = AsyncMock(return_value={
        "config_key": "contract_diag", "collected_fields": {},
        "pending_candidates": [{"id": 1, "label": "A"}, {"id": 2, "label": "B"}]})
    d = await eng.prepare("s", "u", 7, "1", config=_cfg("【作答鐵則】不推託"))
    assert d["kind"] == "converge"
    assert d["system_md"].endswith("【作答鐵則】不推託")


# ── brain 收斂（插點B）：同樣附加 ──
@pytest.mark.req("domain-conversational-facets:3.2")
async def test_brain_converge_appends_answer_rules(monkeypatch):
    eng = _engine()
    eng.optimizer.conversational_step = MagicMock(return_value={
        "action": "converge", "converge_kind": "answer",
        "extracted_fields": {"contract_ref": "84800"}, "scope": "stay"})
    eng.get_state = AsyncMock(return_value={"config_key": "contract_diag",
                                            "collected_fields": {"contract_ref": "84800"},
                                            "asked_count": 1})
    import services.conversational_engine as ce
    monkeypatch.setattr(ce, "_domain_faces", AsyncMock(return_value=[]))
    d = await eng.prepare("s", "u", 7, "它現在能點交嗎", config=_cfg("【作答鐵則】不推託"))
    assert d["kind"] == "converge"
    assert d["system_md"].endswith("【作答鐵則】不推託")


# ── 未設 answer_rules → system_md 原樣（不加空行、向後相容售前）──
@pytest.mark.req("domain-conversational-facets:3.2")
async def test_no_answer_rules_leaves_system_md_untouched():
    eng = _engine()
    eng.get_state = AsyncMock(return_value={"config_key": "contract_diag",
                                            "collected_fields": {}, "asked_count": 1})
    d = await eng.prepare("s", "u", 7, "84800", config=_cfg(None))
    assert d["system_md"] == "DOMAIN_MD"


# ── 種子：合約診斷設定帶 answer_rules（鐵則隨對話走，不住面向脈絡）──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_contract_seed_carries_answer_rules():
    with open(SEED, encoding="utf-8") as f:
        sql = f.read()
    block = re.search(r"-- BEGIN_METADATA_JSON(.*?)-- END_METADATA_JSON", sql, re.DOTALL).group(1)
    md = json.loads(block[block.index("{"):block.rindex("}") + 1])
    rules = md["conversational_config"].get("answer_rules") or ""
    assert "編號｜名稱" in rules          # 底稿識別頭：編號≡名稱同一份
    for stall in ("查無", "稍等"):
        assert stall in rules             # 禁推託語
    assert "比較" in rules                # 只有一份時比較→請補另一份
    cfg = cc._config_from_row(["property_manager"], md)
    assert cfg.answer_rules             # 能被解析載入
