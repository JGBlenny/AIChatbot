"""unit：政策文一句改動＋`outline:` 前綴／裸 id 對 `kb_get` 與
`resolve_canon_section` 的行為（Plan `inputs/plan-m-d-runtime-wiring-20260907.md`
§2.4-9｜knowledge-outline-and-intent-architecture:4.1）。

⛔ 不改 `kb_get` 路由／錯誤碼——本檔只是把既有路由行為釘成回歸測試，
證明政策句講的「id 形狀為 `outline:` 加上目錄那一行的章節 id」與實際程式一致。
"""
from __future__ import annotations

import pytest

from services.agent import agent_rules
from services.agent.canon.canon_assembler import (
    get_canon,
    register_canon,
    resolve_canon_section,
    reset_canon_registry,
)
from services.agent.canon.canon_parser import parse_canon_text
from services.agent.identity import Identity
from services.agent.outline import make_outline_resolver
from services.agent.tools.kb import kb_get

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:4.1"),
]

_FRONT_MATTER = """---
audience: prospect
version: 2026-09-07.policy-kb-test
reviewers: [test]
language: zh-TW
budget_tokens: 12000
target_user: [prospect]
business_types: [system_provider]
---
## 合成粗目 {#A}
### 標題X {#prospect/A/visible-fine}
- sources: [kb:1]
- target_user: [prospect]
- business_types: [system_provider]
- reviewed: {by: test, at: 2026-09-07}
- instance_applicability: general
內容X
"""

_BARE_FINE_ID = "prospect/A/visible-fine"
B2B_PROSPECT = Identity(vendor_id=1, target_user="prospect", mode="b2b")


@pytest.fixture(autouse=True)
def _reset():
    reset_canon_registry()
    yield
    reset_canon_registry()


# ---------------------------------------------------------------------------
# 政策文一句改動
# ---------------------------------------------------------------------------


def test_policy_text_drops_ban_and_states_outline_prefix_shape():
    text = agent_rules._POLICY_TEXT
    assert "⛔ 不需要、也不要為了引用大綱去呼叫 `kb.get`" not in text
    assert "kb.get" in text and "整節後再引用" in text
    assert "outline:" in text


# ---------------------------------------------------------------------------
# `kb_get`：`outline:` 前綴命中 vs 裸 id INVALID_INPUT
# ---------------------------------------------------------------------------


async def test_kb_get_hits_with_outline_prefix_and_rejects_bare_id():
    doc = parse_canon_text(_FRONT_MATTER)
    register_canon("prospect", doc)
    resolver = make_outline_resolver({})

    ok_result = await kb_get(
        B2B_PROSPECT, {"kb_id": f"outline:{_BARE_FINE_ID}"},
        db_pool=None, outline_resolver=resolver,
    )
    assert ok_result.ok is True
    assert ok_result.provenance[0].citable is True

    bad_result = await kb_get(
        B2B_PROSPECT, {"kb_id": _BARE_FINE_ID},
        db_pool=None, outline_resolver=resolver,
    )
    assert bad_result.ok is False and bad_result.error == "INVALID_INPUT"


def test_resolve_canon_section_returns_no_match_for_bare_id():
    """裸 id 對 `resolve_canon_section` 是 `NO_MATCH`（不是 `INVALID_INPUT`——
    那是 `kb_get` 路由層自己的判斷，⛔ 兩者不得混為一談）。"""
    doc = parse_canon_text(_FRONT_MATTER)
    register_canon("prospect", doc)
    result = resolve_canon_section(
        doc, B2B_PROSPECT, _BARE_FINE_ID, vendor_business_types=frozenset()
    )
    assert result.ok is False and result.error == "NO_MATCH"


async def test_kb_get_toc_is_not_citable():
    doc = parse_canon_text(_FRONT_MATTER)
    register_canon("prospect", doc)
    resolver = make_outline_resolver({})
    result = await kb_get(
        B2B_PROSPECT, {"kb_id": "outline:toc"}, db_pool=None, outline_resolver=resolver,
    )
    assert result.ok is True
    assert result.provenance[0].citable is False
