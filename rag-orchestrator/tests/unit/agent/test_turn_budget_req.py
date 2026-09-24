"""unit：`check_turn_budget`（spec knowledge-outline-and-intent-architecture・9.8 DSP-059 D′ S1）。

Plan `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-9.8-turn-budget-dprime-20260916.md`
§2 第 1 列／S1 驗收 ①③⑥。

覆蓋：
- ①：合成 fixture（3 架、7 可引用節、2 未審）——K 上界的量測式（citable 過濾、
  toc 排除、取最大 `min(K,n)` 個節之和）。
- ③：env 只縮不放（兩尺、prospect／pm 兩身分）。
- ⑥：業者身分翻轉可觀察——`build_audience_outline("property_manager")` 在 S1 前
  必炸（`OutlineBudgetExceeded`，見 baseline 記錄），S1 後 `_agent_turn_preflight`
  不再回 `ERR_AGENT_UNAVAILABLE`。
"""
from __future__ import annotations

import re
import types

import pytest

from services.agent import mcp_facade as F
from services.agent.canon.canon_assembler import reset_canon_registry
from services.agent.canon.candidate_selector import K
from services.agent.canon.fine_index import reset_index_registry
from services.agent.identity import Identity
from services.agent.outline import (
    OUTLINE_K_TOKEN_LIMIT,
    OUTLINE_TOC_TOKEN_LIMIT,
    OutlineBudgetExceeded,
    OutlineSection,
    TurnBudget,
    _count_tokens,
    build_audience_outline,
    check_turn_budget,
    default_k_token_limit,
    default_toc_token_limit,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:9.8-S1"),
]


@pytest.fixture(autouse=True)
def _clean_registries():
    reset_canon_registry()
    reset_index_registry()
    yield
    reset_canon_registry()
    reset_index_registry()


# ═══════════════════════════════════════════════════════════════════
# ① 合成 fixture：3 架、7 可引用節、2 未審
# ═══════════════════════════════════════════════════════════════════


def _section(id_, title, text, *, citable=True):
    return OutlineSection(id=id_, title=title, text=text, citable=citable)


#: 7 個可引用節（來自 3 個假想架 X／Y／Z），文字長度遞增以拉開 token 差距，
#: 讓「取最大 5 個」與「取全部」在數字上可分辨。
_CITABLE_SECTIONS = [
    _section("jgb/X/a", "節A", "內容" * 2),
    _section("jgb/X/b", "節B", "內容" * 4),
    _section("jgb/Y/c", "節C", "內容" * 8),
    _section("jgb/Y/d", "節D", "內容" * 16),
    _section("jgb/Y/e", "節E", "內容" * 32),
    _section("jgb/Z/f", "節F", "內容" * 64),
    _section("jgb/Z/g", "節G", "內容" * 128),
]
#: 2 個未審節（citable=False）——一個內容短，一個刻意灌 5,000 字，用來證明
#: 「未審標題節不計入」（⛔ 不是因為它本來就小才沒進 top-K，而是它被過濾掉）。
_UNREVIEWED_SHORT = _section("jgb/X/unreviewed-short", "未審短節", "", citable=False)
_UNREVIEWED_HUGE = _section(
    "jgb/Z/unreviewed-huge", "未審長節（灌文字）", "灌" * 5_000, citable=False
)

_TOC = OutlineSection(id="outline:toc", title="目錄", text="jgb/X/a｜節A\njgb/Y/c｜節C", citable=False)


def _expected_k_upper(sections: list[OutlineSection], k: int) -> int:
    """獨立於 `check_turn_budget` 內部實作、直接用 `_count_tokens` 手算——
    ⛔ 不呼叫被測函式驗自己（cross-check，同 acceptance ② 的 print-then-pin 精神）。
    """
    from services.agent.canon.canon_assembler import TOC_SECTION_ID

    per = sorted(
        (
            _count_tokens(f"【{s.id}】{s.title}\n{s.text}")[0]
            for s in sections
            if s.citable and s.id != TOC_SECTION_ID
        ),
        reverse=True,
    )
    return sum(per[: min(k, len(per))])


def test_synthetic_k_upper_matches_hand_computed_top5_sum():
    all_sections = _CITABLE_SECTIONS + [_UNREVIEWED_SHORT, _UNREVIEWED_HUGE]
    expected = _expected_k_upper(all_sections, K)
    result = check_turn_budget(all_sections, _TOC, k_limit=10_000, toc_limit=10_000)
    assert isinstance(result, TurnBudget)
    assert result.k_upper == expected
    # 印出後釘（本檔材料固定，值必為常數；用手算式交叉核，⛔ 不是自證）
    assert result.k_upper == expected == 794  # 釘整數：本檔材料固定，手算式交叉核（⛔ 不是自證）


def test_k_limit_1_raises_positive_control_10000_passes():
    with pytest.raises(OutlineBudgetExceeded):
        check_turn_budget(_CITABLE_SECTIONS, _TOC, k_limit=1, toc_limit=10_000)
    # 正對照：上限夠大照樣通過
    check_turn_budget(_CITABLE_SECTIONS, _TOC, k_limit=10_000, toc_limit=10_000)


def test_unreviewed_section_text_does_not_change_k_upper_even_when_huge():
    """未審節（citable=False）文字塞 5,000 字，k_upper 仍不變——它從未進入量測池。"""
    without_unreviewed = check_turn_budget(
        _CITABLE_SECTIONS, _TOC, k_limit=10_000, toc_limit=10_000
    )
    with_huge_unreviewed = check_turn_budget(
        _CITABLE_SECTIONS + [_UNREVIEWED_HUGE], _TOC, k_limit=10_000, toc_limit=10_000
    )
    assert with_huge_unreviewed.k_upper == without_unreviewed.k_upper


def test_only_3_citable_sections_k_upper_is_sum_of_all_3():
    """可引用節只有 3 個（< K=5）時，K 上界＝這 3 個節之和；正對照：7 個節時取最大 5 個。"""
    three = _CITABLE_SECTIONS[:3]
    result_three = check_turn_budget(three, _TOC, k_limit=100_000, toc_limit=10_000)
    expected_three = sum(
        _count_tokens(f"【{s.id}】{s.title}\n{s.text}")[0] for s in three
    )
    assert result_three.k_upper == expected_three

    # 正對照：7 個節時只取最大 5 個（⛔ 不是全部 7 個之和）
    result_seven = check_turn_budget(_CITABLE_SECTIONS, _TOC, k_limit=100_000, toc_limit=10_000)
    expected_seven_all = sum(
        _count_tokens(f"【{s.id}】{s.title}\n{s.text}")[0] for s in _CITABLE_SECTIONS
    )
    assert result_seven.k_upper < expected_seven_all


def test_toc_section_none_yields_zero_toc_numbers():
    result = check_turn_budget(_CITABLE_SECTIONS, None, k_limit=100_000, toc_limit=100_000)
    assert result.toc_tokens == 0
    assert result.toc_lines == 0


def test_toc_over_limit_raises_independently_of_k_upper():
    """toc 超標即使 K 上界在限內也要 raise——兩尺各自守門，不互相抵銷。"""
    huge_toc = OutlineSection(id="outline:toc", title="目錄", text="項目\n" * 5_000, citable=False)
    with pytest.raises(OutlineBudgetExceeded):
        check_turn_budget(_CITABLE_SECTIONS, huge_toc, k_limit=100_000, toc_limit=1)


# ═══════════════════════════════════════════════════════════════════
# ③ env 只縮不放：兩尺、prospect／pm 兩身分
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.parametrize(
    "audience,env_key,default_fn,constant_table",
    [
        ("prospect", "AGENT_OUTLINE_K_TOKEN_LIMIT_PROSPECT", default_k_token_limit, OUTLINE_K_TOKEN_LIMIT),
        ("property_manager", "AGENT_OUTLINE_K_TOKEN_LIMIT_PM", default_k_token_limit, OUTLINE_K_TOKEN_LIMIT),
        ("prospect", "AGENT_OUTLINE_TOC_TOKEN_LIMIT_PROSPECT", default_toc_token_limit, OUTLINE_TOC_TOKEN_LIMIT),
        ("property_manager", "AGENT_OUTLINE_TOC_TOKEN_LIMIT_PM", default_toc_token_limit, OUTLINE_TOC_TOKEN_LIMIT),
    ],
)
def test_env_only_lowers_never_raises(monkeypatch, audience, env_key, default_fn, constant_table):
    monkeypatch.delenv(env_key, raising=False)
    assert default_fn(audience) == constant_table[audience]     # 未設 ⇒ 常數

    monkeypatch.setenv(env_key, "1")
    assert default_fn(audience) == 1                            # 設更小 ⇒ 生效

    monkeypatch.setenv(env_key, "99999")
    assert default_fn(audience) == constant_table[audience]     # 設更大 ⇒ 仍用常數


@pytest.mark.parametrize(
    "audience,env_key,default_fn,constant_table",
    [
        ("prospect", "AGENT_OUTLINE_K_TOKEN_LIMIT_PROSPECT", default_k_token_limit, OUTLINE_K_TOKEN_LIMIT),
        ("property_manager", "AGENT_OUTLINE_TOC_TOKEN_LIMIT_PM", default_toc_token_limit, OUTLINE_TOC_TOKEN_LIMIT),
    ],
)
def test_invalid_env_value_raises_not_ignored(
    monkeypatch, audience, env_key, default_fn, constant_table
):
    """env 設了但不是合法整數 ⇒ raise，⛔ 不靜默忽略。

    正對照：同一個 audience／env_key 組合，**未設** env 時照常回常數（證明上面的
    raise 真的是「值不合法」造成，不是這組參數本身就會炸）。
    """
    monkeypatch.delenv(env_key, raising=False)
    assert default_fn(audience) == constant_table[audience]      # 正對照：未設 ⇒ 常數

    monkeypatch.setenv(env_key, "not-an-int")
    with pytest.raises(ValueError, match=re.escape(env_key)):
        default_fn(audience)


# ═══════════════════════════════════════════════════════════════════
# ⑥ 業者身分翻轉可觀察：pm 的 agent.turn 不再 fail-closed
# ═══════════════════════════════════════════════════════════════════


class _FakeSessionStore:
    async def get_state(self, session_id):
        return None

    async def start(self, *a, **k):
        return {}

    async def save(self, *a, **k):
        return None


PM_IDENTITY = Identity(
    vendor_id=0, target_user="property_manager", mode="b2b",
    session_id="s-pm-s1-accept6", api_key_id=1,
)


async def test_pm_agent_turn_preflight_no_longer_unavailable_after_s1():
    """S1 前：`build_audience_outline("property_manager")` 在工作樹正本上必炸
    `OutlineBudgetExceeded`（見本檔完成報告貼的『S1 前』紅字輸出——同一份正本、
    同一支呼叫，S1 前跑的是舊 `check_budget` 量整份視圖，pm 視圖 token_count=10,896
    > 舊上限 8,000）。S1 後：兩尺都在限內，pm 視圖組得起來（⛔ 不 raise）⇒
    9.8 DSP-059 D′ S2：權威旗標是 `agent_audiences`（frozenset，⛔ 不再是
    `agent_outlines`）⇒ `_agent_turn_preflight` 不再 fail-closed。
    """
    await build_audience_outline("property_manager")  # ⛔ 不 raise 即證明 S1 兩尺皆過

    app = types.SimpleNamespace(state=types.SimpleNamespace(
        agent_runtime=object(),                       # 非 None 即可，preflight 只判存在
        agent_session_store=_FakeSessionStore(),
        agent_audiences=frozenset({"property_manager"}),
    ))
    deps = F.FacadeDeps(get_db_pool=lambda: None, get_app=lambda: app)

    F.reset_agent_turn_cap()
    code = F._agent_turn_preflight(deps, PM_IDENTITY)
    assert code != F.ERR_AGENT_UNAVAILABLE, code
    assert code is None, code
