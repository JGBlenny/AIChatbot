"""unit：responsibility evaluation context 的單一權威建構點（slice 1）。

要鎖的命題只有一句：

> **pre-entry 與 in-session 必須從同一條路徑取得 rules 與 system context。**

實測病灶（research.md §8.3）：pre-entry 用 `cfg.key`、in-session 用 `_domain_key`，
`billing_anomaly` 兩者 digest 不同 → 「把判定提前」在 production 上不成立。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.conversational_config import ConversationalConfig
from services.responsibility import (
    build_responsibility_context,
    responsibility_context_key,
)

pytestmark = pytest.mark.unit


def _cfg(key="billing_anomaly", category="帳單異常", persona="pm_billing_anomaly"):
    return ConversationalConfig(
        key=key, persona_role=persona,
        topic_scope={"mode": "category", "category": category},
        grounding_scope={"select": "api"})


@pytest.mark.req("face-exit-before-grounding:1")
def test_context_key_prefers_current_face_then_category_then_role():
    cfg = _cfg()
    assert responsibility_context_key(cfg, face="退租收尾") == "退租收尾"   # 當輪面向優先
    assert responsibility_context_key(cfg) == "帳單異常"                    # 診斷面向＝分類值
    role_only = ConversationalConfig(key="presales", persona_role="prospect",
                                     topic_scope={"mode": "all"})
    assert responsibility_context_key(role_only) == "prospect"              # 角色級＝persona_role


@pytest.mark.req("face-exit-before-grounding:1")
def test_engine_domain_key_delegates_to_the_single_definition():
    """引擎的 _domain_key 不得自己再定義一次鍵。"""
    from services.conversational_engine import _domain_key
    cfg = _cfg()
    assert _domain_key(cfg) == responsibility_context_key(cfg) == "帳單異常"


@pytest.mark.req("face-exit-before-grounding:1")
async def test_builder_uses_the_authoritative_key_not_the_facet_key():
    """**回歸鎖**：不得再以 `cfg.key`（如 billing_anomaly）取 system context。"""
    seen = {}

    async def fake_ctx(_pool, key=None):
        seen["key"] = key
        return f"CTX::{key}"

    with patch("services.conversational_rules.load_rules", new=AsyncMock(return_value="RULES")), \
         patch("services.system_context.get_system_context", new=fake_ctx):
        rctx = await build_responsibility_context(MagicMock(), _cfg())

    assert seen["key"] == "帳單異常", f"取脈絡用了非權威鍵：{seen['key']}"
    assert rctx.context_key == "帳單異常" and rctx.system_md == "CTX::帳單異常"
    assert rctx.config_key == "billing_anomaly"          # 面向識別仍保留，只是不拿來取脈絡


@pytest.mark.req("face-exit-before-grounding:1")
async def test_preentry_and_insession_digests_match():
    """同一面向：pre-entry 與 in-session 兩路取得的 digest 必須相同。"""
    from services.conversational_engine import _domain_key

    async def fake_ctx(_pool, key=None):
        return {"帳單異常": "DOMAIN_MD", "billing_anomaly": "BASE_MD"}.get(key, "BASE_MD")

    cfg = _cfg()
    with patch("services.conversational_rules.load_rules", new=AsyncMock(return_value="RULES")), \
         patch("services.system_context.get_system_context", new=fake_ctx):
        pre = await build_responsibility_context(MagicMock(), cfg)          # pre-entry 路徑
        in_session_md = await fake_ctx(None, _domain_key(cfg))              # in-session 路徑

    assert pre.system_md == in_session_md == "DOMAIN_MD"
    assert pre.context_digest == __import__("hashlib").sha1(
        in_session_md.encode()).hexdigest()[:16]


@pytest.mark.req("face-exit-before-grounding:1")
async def test_missing_rules_returns_none_not_an_invented_context():
    """規則取不到 → None（誠實降級）；**不得**用空規則去問模型。"""
    with patch("services.conversational_rules.load_rules", new=AsyncMock(return_value=None)), \
         patch("services.system_context.get_system_context", new=AsyncMock(return_value="X")):
        assert await build_responsibility_context(MagicMock(), _cfg()) is None
