"""unit：nomination 兩段化的**行為等價**（Stage 1 observability 的前置）。

要鎖的命題：

> **把「提名」從「裁決」抽出來、並提前列舉完整候選，
>   不得改變 candidate evaluation order、resolver authority、suppression 與 final routing。**

⚠️ 為什麼需要這一整套：舊碼把 `config_for_category` 與 resolver **交錯**，
第一個 commit 就短路 return——所以「候選集合一樣」**不等於**「行為一樣」，
`first-commit-wins` 讓**順序**具有語義。因此本檔除了逐形狀等價，
還有一條**負控制**：把候選順序反轉，測試必須紅。
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


def _cfg(key, category=None, requires_instance=False):
    gs = {"select": "api", "endpoint": "jgb_bills", "required_slots": ["bill_ref"]}
    if requires_instance:
        gs["requires_instance_reference"] = True
    return ConversationalConfig(
        key=key, persona_role=f"pm_{key}", enabled=True,
        topic_scope={"mode": "category", "category": category or f"cat_{key}"},
        grounding_scope=gs)


class _Recorder:
    """記錄 resolver 的**呼叫順序**——順序不變是本檔的核心斷言之一。"""

    def __init__(self, table):
        self.table = table          # key → (config|None, authority)
        self.calls = []

    async def resolve(self, _pool, cfg, _msg):
        k = getattr(cfg, "key", None)
        self.calls.append(k)
        return self.table.get(k, (None, "no_face"))


class _GateDecision:
    """最小的 gate 判定替身——只需帶 `reason`（production 的抑制訊息會讀它）。"""
    verdict = "block"
    reason = "stub"


async def _run(monkeypatch, cats, registry, resolver_table,
               suppressed=(), best=None):
    """以受控替身跑 `_diagnosis_config_for_knowledge`，回 (結果, resolver 呼叫序)。"""
    from routers import chat as chat_mod
    from services.decision_layer import DecisionConfig

    rec = _Recorder(resolver_table)
    # ⚠️ **P1f 後抑制接縫換人**：production 改呼叫 `_applicability_suppressed(top1, cfg)`，
    #    回 `(suppressed, reason)`；lexical 判定只留作 telemetry，不再具 authority。
    #    替身照新接縫給值——⛔ 不得繼續 stub 已卸任的 `_instance_hint_suppressed`，
    #    否則測試會在 production 早已不看它的情況下仍然「通過」（假綠）。
    _decision = _GateDecision() if suppressed else None
    monkeypatch.setattr(chat_mod, "_knowledge_category", lambda _b: list(cats))
    monkeypatch.setattr(chat_mod, "_instance_gate_decision", lambda _m: _decision)
    monkeypatch.setattr(
        chat_mod, "_applicability_suppressed",
        lambda _k, cfg: ((True, "stub_suppressed")
                         if getattr(cfg, "key", None) in suppressed else (False, None)))
    monkeypatch.setattr(chat_mod, "_resolve_pre_commit_candidate", rec.resolve)

    async def _lookup(_pool, cat):
        return registry.get(cat)

    with patch("services.conversational_config.config_for_category", new=_lookup):
        out = await chat_mod._diagnosis_config_for_knowledge(
            MagicMock(), best or {"id": 1, "similarity": 0.9},
            DecisionConfig(form_trigger_threshold=0.75), user_message="問句")
    return out, rec.calls


# ── 12 個形狀（等價 oracle：final routing／committed facet／authority／呼叫順序）──

@pytest.mark.req("conversational-routing-execution:stage1-nomination")
async def test_shape01_first_category_no_candidate_second_commits(monkeypatch):
    """① 第一 category 無 candidate，第二個 commit。"""
    b = _cfg("b")
    (cfg, auth), calls = await _run(
        monkeypatch, ["無此分類", "cat_b"], {"cat_b": b}, {"b": (b, "authoritative")})
    assert cfg is b and auth == "authoritative"
    assert calls == ["b"], "無 config 的 category 不得觸發 resolver"


@pytest.mark.req("conversational-routing-execution:stage1-nomination")
async def test_shape02_first_candidate_commits(monkeypatch):
    """② 第一 candidate 就 commit → 後續 candidate **不得**被裁決（first-commit-wins）。"""
    a, b = _cfg("a"), _cfg("b")
    (cfg, _), calls = await _run(
        monkeypatch, ["cat_a", "cat_b"], {"cat_a": a, "cat_b": b},
        {"a": (a, "authoritative"), "b": (b, "authoritative")})
    assert cfg is a
    assert calls == ["a"], "短路語義被破壞：第二個候選不該進 resolver"


@pytest.mark.req("conversational-routing-execution:stage1-nomination")
async def test_shape03_first_no_commit_second_commits(monkeypatch):
    """③ 第一 candidate no-commit，第二 candidate commit——順序必須是 a→b。"""
    a, b = _cfg("a"), _cfg("b")
    (cfg, _), calls = await _run(
        monkeypatch, ["cat_a", "cat_b"], {"cat_a": a, "cat_b": b},
        {"a": (None, "no_face"), "b": (b, "authoritative")})
    assert cfg is b
    assert calls == ["a", "b"]


@pytest.mark.req("conversational-routing-execution:stage1-nomination")
async def test_shape04_all_candidates_no_commit(monkeypatch):
    """④ 多 candidate 全部 no-commit → 不進面向，且**每個**都被裁決過。"""
    from services.responsibility import FACE_NONE
    a, b = _cfg("a"), _cfg("b")
    (cfg, auth), calls = await _run(
        monkeypatch, ["cat_a", "cat_b"], {"cat_a": a, "cat_b": b},
        {"a": (None, "no_face"), "b": (None, "no_face")})
    assert cfg is None and auth == FACE_NONE
    assert calls == ["a", "b"]


@pytest.mark.req("conversational-routing-execution:stage1-nomination")
async def test_shape05_suppression_skips_first_second_commits(monkeypatch):
    """⑤ 第一個被 suppression 擋掉 → **不得**進 resolver；第二個照常 commit。"""
    a, b = _cfg("a"), _cfg("b")
    (cfg, _), calls = await _run(
        monkeypatch, ["cat_a", "cat_b"], {"cat_a": a, "cat_b": b},
        {"a": (a, "authoritative"), "b": (b, "authoritative")}, suppressed=("a",))
    assert cfg is b
    assert calls == ["b"], "被抑制的候選不得被送進 resolver"


@pytest.mark.req("conversational-routing-execution:stage1-nomination")
async def test_shape06_delegation_commits_to_non_nominated_face(monkeypatch):
    """⑥ authoritative delegation：最終 commit 到**不在提名清單**的 Face。

    ⚠️ 這條同時證明不變量 I1——`committed_facet ∈ nomination_candidate_keys`
    **不是**必要條件，⛔ 不得寫成不變量。
    """
    from routers.chat import nomination_candidate_keys, _nominate_face_candidates
    a = _cfg("a")
    elsewhere = _cfg("contract_closeout")
    (cfg, auth), calls = await _run(
        monkeypatch, ["cat_a"], {"cat_a": a}, {"a": (elsewhere, "authoritative")})
    assert cfg is elsewhere and auth == "authoritative"
    assert calls == ["a"], "resolver 的 seed 仍是被提名的那個"


@pytest.mark.req("conversational-routing-execution:stage1-nomination")
async def test_shape07_technical_fail_open_authority_preserved(monkeypatch):
    """⑦ technical fail-open 的 authority 值必須原樣傳出（不得被兩段化吃掉）。"""
    from services.responsibility import FACE_COMPAT_FAIL_OPEN
    a = _cfg("a")
    (cfg, auth), _ = await _run(
        monkeypatch, ["cat_a"], {"cat_a": a}, {"a": (a, FACE_COMPAT_FAIL_OPEN)})
    assert cfg is a and auth == FACE_COMPAT_FAIL_OPEN


@pytest.mark.req("conversational-routing-execution:stage1-nomination")
async def test_shape08_resolver_exception_propagates_unchanged(monkeypatch):
    """⑧ resolver 例外的傳播行為不得因兩段化而改變。"""
    from routers import chat as chat_mod
    from services.decision_layer import DecisionConfig
    a = _cfg("a")

    async def _boom(*_a, **_k):
        raise RuntimeError("boom")

    async def _lookup(_pool, cat):
        return {"cat_a": a}.get(cat)

    monkeypatch.setattr(chat_mod, "_knowledge_category", lambda _b: ["cat_a"])
    monkeypatch.setattr(chat_mod, "_instance_gate_decision", lambda _m: None)
    monkeypatch.setattr(chat_mod, "_instance_hint_suppressed", lambda _d, _c: False)
    monkeypatch.setattr(chat_mod, "_resolve_pre_commit_candidate", _boom)
    with patch("services.conversational_config.config_for_category", new=_lookup):
        with pytest.raises(RuntimeError):
            await chat_mod._diagnosis_config_for_knowledge(
                MagicMock(), {"id": 1, "similarity": 0.9},
                DecisionConfig(form_trigger_threshold=0.75), user_message="問句")


@pytest.mark.req("conversational-routing-execution:stage1-nomination")
async def test_shape09_unknown_category_yields_no_candidate(monkeypatch):
    """⑨ 未 mapping 的 category → 無候選、不觸發 resolver（不變量 I7 的執行側）。"""
    from services.responsibility import FACE_NONE
    (cfg, auth), calls = await _run(monkeypatch, ["沒人管的分類"], {}, {})
    assert cfg is None and auth == FACE_NONE and calls == []


@pytest.mark.req("conversational-routing-execution:stage1-nomination")
async def test_shape10_duplicate_config_still_resolved_twice(monkeypatch):
    """⑩ 同一 config 掛在兩個 category → **執行序列不得去重**。

    ⚠️ 這條是兩段化最容易踩的坑：回報欄位要去重，但執行**不能**去重——
    舊碼會對同一個 config 跑兩次 resolver（LLM 判定不保證兩次相同，
    第二次可能 commit）。去重等於默默拿掉那次機會。
    """
    from routers.chat import nomination_candidate_keys, _nominate_face_candidates
    a = _cfg("a")
    calls_seen = []

    async def _table(_pool, cfg, _msg):
        calls_seen.append(getattr(cfg, "key", None))
        return (a, "authoritative") if len(calls_seen) == 2 else (None, "no_face")

    from routers import chat as chat_mod
    from services.decision_layer import DecisionConfig

    async def _lookup(_pool, cat):
        return {"cat_x": a, "cat_y": a}.get(cat)

    monkeypatch.setattr(chat_mod, "_knowledge_category", lambda _b: ["cat_x", "cat_y"])
    monkeypatch.setattr(chat_mod, "_instance_gate_decision", lambda _m: None)
    monkeypatch.setattr(chat_mod, "_instance_hint_suppressed", lambda _d, _c: False)
    monkeypatch.setattr(chat_mod, "_resolve_pre_commit_candidate", _table)
    with patch("services.conversational_config.config_for_category", new=_lookup):
        cfg, _ = await chat_mod._diagnosis_config_for_knowledge(
            MagicMock(), {"id": 1, "similarity": 0.9},
            DecisionConfig(form_trigger_threshold=0.75), user_message="問句")
        cands = await _nominate_face_candidates(MagicMock(), {"id": 1})
    assert calls_seen == ["a", "a"], "執行序列被去重 → 第二次 commit 機會被拿掉"
    assert cfg is a
    # 回報欄位**要**去重
    assert nomination_candidate_keys([("cat_x", a), ("cat_y", a)]) == ["a"]


@pytest.mark.req("conversational-routing-execution:stage1-nomination")
async def test_shape11_empty_categories(monkeypatch):
    """⑪ 沒有 categories → 無候選、不觸發 resolver。"""
    from services.responsibility import FACE_NONE
    (cfg, auth), calls = await _run(monkeypatch, [], {}, {})
    assert cfg is None and auth == FACE_NONE and calls == []


@pytest.mark.req("conversational-routing-execution:stage1-nomination")
async def test_shape12_below_threshold_short_circuits_before_nomination(monkeypatch):
    """⑫ 未達門檻 → 連提名都不做（不得因兩段化而提前列舉）。"""
    from routers import chat as chat_mod
    from services.decision_layer import DecisionConfig
    from services.responsibility import FACE_NONE
    called = {"n": 0}

    async def _lookup(_pool, _cat):
        called["n"] += 1
        return None

    monkeypatch.setattr(chat_mod, "_knowledge_category", lambda _b: ["cat_a"])
    with patch("services.conversational_config.config_for_category", new=_lookup):
        cfg, auth = await chat_mod._diagnosis_config_for_knowledge(
            MagicMock(), {"id": 1, "similarity": 0.10},
            DecisionConfig(form_trigger_threshold=0.75), user_message="問句")
    assert cfg is None and auth == FACE_NONE
    assert called["n"] == 0, "未達門檻卻仍列舉候選 → eager evaluation 洩漏"


# ── 負控制：順序具語義，集合相同不代表行為相同 ──────────────────────────────

@pytest.mark.req("conversational-routing-execution:stage1-nomination")
async def test_negative_control_reversed_order_changes_outcome(monkeypatch):
    """⚠️ 若把候選順序反轉，結果**必須**不同——否則本檔的等價斷言沒有鑑別力。"""
    a, b = _cfg("a"), _cfg("b")
    table = {"a": (a, "authoritative"), "b": (b, "authoritative")}
    (fwd, _), fwd_calls = await _run(
        monkeypatch, ["cat_a", "cat_b"], {"cat_a": a, "cat_b": b}, table)
    (rev, _), rev_calls = await _run(
        monkeypatch, ["cat_b", "cat_a"], {"cat_a": a, "cat_b": b}, table)
    assert fwd is a and rev is b, "順序反轉卻得到同一結果 → first-commit-wins 已失效"
    assert fwd_calls == ["a"] and rev_calls == ["b"]
