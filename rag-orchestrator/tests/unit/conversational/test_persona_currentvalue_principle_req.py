"""unit:合約診斷 persona 含「以 API 現值為準」原則（domain-conversational-facets 任務 2.2｜R3.2）。

混合 grounding 下，領域基底架構（system_md）供解讀、API 現值為準。此原則以**資料**（persona
rules_text）承載，非程式硬編。驗證合約診斷對話規則種子之 answer 含此原則語意，且能被
`conversational_config._config_from_row` 正常解析（不破壞既有設定）。
"""
import json
import os
import re

import pytest

from services import conversational_config as cc

pytestmark = pytest.mark.unit

SEED = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                    "database", "migrations", "seed_conversational_diagnosis_contract_rule.sql")


def _seed_sql():
    with open(SEED, encoding="utf-8") as f:
        return f.read()


def _persona_text(sql):
    return re.search(r"\$RULES\$(.*?)\$RULES\$", sql, re.DOTALL).group(1)


# ── persona 作答依據原則：依 API 現值算好的中文事實/判定作答、不複述代碼、不自行推翻（R3.2）──
@pytest.mark.req("domain-conversational-facets:3.2")
def test_persona_contains_current_value_precedence_principle():
    persona = _persona_text(_seed_sql())
    assert "現值" in persona           # 依 API 現值判定
    assert "代碼" in persona           # 不要複述內部代碼（如「狀態值 32」）
    assert "推翻" in persona           # 不自行推翻系統給的判定
    assert "轉專人" in persona         # 查無/不確定導向專人


# ── 種子仍可正常解析為設定（不回歸；R7.2）──
@pytest.mark.req("domain-conversational-facets:7.2")
def test_seed_still_parses_to_config():
    sql = _seed_sql()
    block = re.search(r"-- BEGIN_METADATA_JSON(.*?)-- END_METADATA_JSON", sql, re.DOTALL).group(1)
    md = json.loads(block[block.index("{"):block.rindex("}") + 1])
    cfg = cc._config_from_row(["property_manager"], md)
    assert cfg is not None
    assert cfg.key == "contract_diag"
    assert cfg.persona_role == "property_manager"
    assert cfg.grounding_scope.get("select") == "api"
