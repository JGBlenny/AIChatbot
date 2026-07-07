"""unit:母分類組織——診斷 config.topic_scope.category → 領域鍵(persona_role) → 領域脈絡（任務 4.1｜R1.1–1.4）。

一個領域的四件套以「母分類 + 領域鍵（= target_user = persona_role）」關聯，不建新表：
  - 診斷面向以 topic_scope.category 宣告所屬領域（分類路由 config_for_category）；
  - 其 persona_role 即領域鍵，get_system_context 依此載入該領域系統脈絡、load_rules 依此載入規則。
本測試以合約種子驗證此鏈路一致（config → 領域鍵 → 系統脈絡）。
mock，確定性 unit。
"""
import json
import os
import re

import pytest
from unittest.mock import AsyncMock

from services import conversational_config as cc
from services import system_context
from services.system_context import get_system_context, reset_cache

pytestmark = pytest.mark.unit

RULE_SEED = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                         "database", "migrations", "seed_conversational_diagnosis_contract_rule.sql")
CTX_SEED = os.path.join(os.path.dirname(__file__), "..", "..", "..",
                        "database", "migrations", "seed_domain_contract_system_context.sql")


def _rule_config():
    sql = open(RULE_SEED, encoding="utf-8").read()
    block = re.search(r"-- BEGIN_METADATA_JSON(.*?)-- END_METADATA_JSON", sql, re.DOTALL).group(1)
    md = json.loads(block[block.index("{"):block.rindex("}") + 1])
    return cc._config_from_row(["property_manager"], md)


def _ctx_body():
    sql = open(CTX_SEED, encoding="utf-8").read()
    return re.search(r"\$CTX\$(.*?)\$CTX\$", sql, re.DOTALL).group(1)


class _Pool:
    def __init__(self, base, appends):
        self._base, self._appends = base, appends

    def acquire(self):
        base, appends = self._base, self._appends

        class _Conn:
            async def fetchrow(self, sql, *args):
                if "target_user IS NULL" in sql:
                    return {"answer": base}
                if "target_user @>" in sql:
                    v = appends.get(args[1])
                    return {"answer": v} if v else None
                return None

        conn = _Conn()

        class _Ctx:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *a):
                return False

        return _Ctx()


@pytest.fixture(autouse=True)
def _clear():
    reset_cache()
    yield
    reset_cache()


# ── R1.2/R1.3 領域鍵一致：診斷 config 宣告領域分類，其 persona_role＝領域鍵（= target_user）──
@pytest.mark.req("domain-conversational-facets:1.3")
def test_diagnosis_config_declares_domain_and_key():
    cfg = _rule_config()
    # topic_scope.category 宣告所屬領域
    assert cfg.topic_scope.get("mode") == "category"
    assert cfg.topic_scope.get("category")  # 領域分類已宣告
    # 領域鍵＝persona_role（= 規則 target_user；載入脈絡/規則同一把鑰匙）
    assert cfg.persona_role == "property_manager"


# ── R1.3 據領域鍵載入對應領域系統脈絡（合約 config → 合約脈絡，非售前）──
@pytest.mark.req("domain-conversational-facets:1.3")
async def test_domain_key_loads_matching_system_context():
    cfg = _rule_config()
    pool = _Pool(base="BASE售前底座", appends={"property_manager": _ctx_body()})
    md = await get_system_context(pool, cfg.persona_role)   # 以 config 的領域鍵載入
    assert "12 里程碑" in md and "點交＝交屋" in md          # 拿到合約領域脈絡（框架）
    assert md.startswith("BASE售前底座")                     # 疊加於通用 base


# ── R1.4 不建新表：領域鍵沿用既有 target_user 慣例（無新 schema 依賴）──
@pytest.mark.req("domain-conversational-facets:1.4")
def test_domain_key_reuses_target_user_convention():
    # system_context 疊加查詢以 target_user 為領域鍵（比照 load_rules），無新表/新欄位
    src = system_context.__doc__ or ""
    assert "target_user" in src
