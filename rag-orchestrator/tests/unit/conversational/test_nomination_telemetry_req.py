"""unit：Stage 1 nomination telemetry 的四欄語義與失效隔離。

要鎖的三件事：

> ① `null`（不適用）／`[]`（跑過且零候選）**不得混用**——混了就污染比例統計
> ② 量到的是 **nomination**，不是 commit——delegation 後兩者會不同
> ③ telemetry 故障**不得**改變 routing——observability 不是 execution dependency
"""
from unittest.mock import MagicMock, patch

import pytest

from services.conversational_config import ConversationalConfig

pytestmark = pytest.mark.unit


def _cfg(key, category=None):
    return ConversationalConfig(
        key=key, persona_role=f"pm_{key}", enabled=True,
        topic_scope={"mode": "category", "category": category or f"cat_{key}"},
        grounding_scope={"select": "api", "endpoint": "jgb_bills",
                         "required_slots": ["bill_ref"]})


class _Sink:
    """攔截 `_meter_decision`，收集本輪落下的 nomination snapshot。"""

    def __init__(self):
        self.snaps = []

    def __call__(self, snapshot=None, facet_event=None):
        if snapshot and "nomination" in snapshot:
            self.snaps.append(snapshot["nomination"])

    @property
    def last(self):
        assert self.snaps, "沒有落下任何 nomination snapshot"
        return self.snaps[-1]


async def _run_classification(monkeypatch, cats, registry, resolver_table,
                              similarity=0.9):
    from routers import chat as chat_mod
    from services.decision_layer import DecisionConfig

    sink = _Sink()
    monkeypatch.setattr(chat_mod, "_meter_decision", sink)
    monkeypatch.setattr(chat_mod, "_knowledge_category", lambda b: list(cats))
    monkeypatch.setattr(chat_mod, "_instance_gate_decision", lambda _m: None)
    monkeypatch.setattr(chat_mod, "_instance_hint_suppressed", lambda _d, _c: False)

    async def _resolve(_pool, cfg, _msg):
        return resolver_table.get(getattr(cfg, "key", None), (None, "no_face"))

    monkeypatch.setattr(chat_mod, "_resolve_pre_commit_candidate", _resolve)

    async def _lookup(_pool, cat):
        return registry.get(cat)

    with patch("services.conversational_config.config_for_category", new=_lookup):
        out = await chat_mod._diagnosis_config_for_knowledge(
            MagicMock(), {"id": 4657, "similarity": similarity},
            DecisionConfig(form_trigger_threshold=0.75), user_message="問句")
    return out, sink


# ── ① null vs [] 的三態語義（不變量 I3）────────────────────────────────────

@pytest.mark.req("conversational-routing-execution:stage1-telemetry")
def test_non_classification_entry_writes_null_not_empty_list(monkeypatch):
    """非 classification 進場 → candidate 欄位是 `null`，**不是** `[]`。

    ⚠️ `[]` 專指「nomination 執行過且零候選」；非 classification 路徑
    根本不適用 classification nomination，寫 `[]` 會被統計成「有跑但沒候選」。
    """
    from routers import chat as chat_mod
    sink = _Sink()
    monkeypatch.setattr(chat_mod, "_meter_decision", sink)
    chat_mod._meter_entry_source(chat_mod.ENTRY_SOURCE_EXISTING_SESSION)
    s = sink.last
    assert s["entry_source"] == "existing_session"
    assert s["nomination_candidate_facet_keys"] is None
    assert s["top1_knowledge_id"] is None and s["top1_categories"] is None


@pytest.mark.req("conversational-routing-execution:stage1-telemetry")
async def test_classification_without_top1_writes_empty_list(monkeypatch):
    """classification 但未達門檻／無 top1 → candidate 是 `[]`，**不是**缺席也不是 `null`。"""
    (cfg, _), sink = await _run_classification(
        monkeypatch, ["cat_a"], {"cat_a": _cfg("a")}, {}, similarity=0.10)
    s = sink.last
    assert cfg is None
    assert s["entry_source"] == "classification"
    assert s["nomination_candidate_facet_keys"] == [], "未達門檻仍須落 []，不得缺席"


@pytest.mark.req("conversational-routing-execution:stage1-telemetry")
async def test_categories_without_mapping_keeps_categories_and_empty_candidates(monkeypatch):
    """不變量 I7：category 存在但無 Face mapping → **保留原 category**、candidate `[]`。

    ⚠️ 這正是本 Stage 最想量的 failure shape，instrumentation 層不得自行 drop。
    """
    (cfg, _), sink = await _run_classification(
        monkeypatch, ["沒人管的分類", "另一個沒人管的"], {}, {})
    s = sink.last
    assert cfg is None
    assert s["top1_categories"] == ["沒人管的分類", "另一個沒人管的"]
    assert s["nomination_candidate_facet_keys"] == []


# ── ② 量的是 nomination，不是 commit ────────────────────────────────────────

@pytest.mark.req("conversational-routing-execution:stage1-telemetry")
async def test_telemetry_records_full_nomination_not_commit(monkeypatch):
    """★ 正控制：第一候選 no-commit、第二候選 commit
    → 候選清單仍須**完整兩個**，且順序保留。

    同時證三件事：
      1. telemetry 量的是 nomination，不是 commit；
      2. 完整候選沒有因第一個結果而消失；
      3. first-commit-wins 迭代還活著。
    """
    a, b = _cfg("a"), _cfg("b")
    (cfg, _), sink = await _run_classification(
        monkeypatch, ["cat_a", "cat_b"], {"cat_a": a, "cat_b": b},
        {"a": (None, "no_face"), "b": (b, "authoritative")})
    assert cfg is b, "first-commit-wins 應由第二候選 commit"
    assert sink.last["nomination_candidate_facet_keys"] == ["a", "b"]


@pytest.mark.req("conversational-routing-execution:stage1-telemetry")
async def test_delegation_to_non_nominated_face_does_not_rewrite_candidates(monkeypatch):
    """不變量 I1：commit 到**非提名** Face 時，候選清單不得被 committed facet 覆寫。"""
    a = _cfg("a")
    elsewhere = _cfg("contract_closeout")
    (cfg, _), sink = await _run_classification(
        monkeypatch, ["cat_a"], {"cat_a": a}, {"a": (elsewhere, "authoritative")})
    assert cfg is elsewhere
    assert sink.last["nomination_candidate_facet_keys"] == ["a"], \
        "候選清單被 commit 結果污染 → telemetry 變成從結果反推"


@pytest.mark.req("conversational-routing-execution:stage1-telemetry")
async def test_top1_snapshot_is_the_row_nomination_saw(monkeypatch):
    """`top1_knowledge_id` 與 `top1_categories` 必須同源於 nomination 當下那一筆。"""
    a = _cfg("a")
    (_cfg_out, _), sink = await _run_classification(
        monkeypatch, ["cat_a"], {"cat_a": a}, {"a": (a, "authoritative")})
    s = sink.last
    assert s["top1_knowledge_id"] == 4657
    assert s["top1_categories"] == ["cat_a"]


# ── ③ telemetry 故障不得影響 routing（failure injection）──────────────────

@pytest.mark.req("conversational-routing-execution:stage1-telemetry")
async def test_telemetry_write_failure_does_not_change_routing(monkeypatch):
    """★ failure injection：telemetry 寫入丟例外 → routing 結果必須**逐字不變**。

    ⚠️ 不只驗 serialization——直接讓 `_meter_decision` 拋例外，
    證明 observability **不是** execution dependency。
    ⚠️ 刻意**不用** `_run_classification`：那個 helper 會把 `_meter_decision`
    換成 sink，會把注入的例外蓋掉 → 測試變成假綠。
    """
    from routers import chat as chat_mod
    from services.decision_layer import DecisionConfig
    a, b = _cfg("a"), _cfg("b")

    async def _resolve(_pool, cfg, _msg):
        return {"a": (None, "no_face"),
                "b": (b, "authoritative")}.get(getattr(cfg, "key", None), (None, "no_face"))

    async def _lookup(_pool, cat):
        return {"cat_a": a, "cat_b": b}.get(cat)

    def _setup():
        monkeypatch.setattr(chat_mod, "_knowledge_category", lambda _b: ["cat_a", "cat_b"])
        monkeypatch.setattr(chat_mod, "_instance_gate_decision", lambda _m: None)
        monkeypatch.setattr(chat_mod, "_instance_hint_suppressed", lambda _d, _c: False)
        monkeypatch.setattr(chat_mod, "_resolve_pre_commit_candidate", _resolve)

    async def _call():
        with patch("services.conversational_config.config_for_category", new=_lookup):
            return await chat_mod._diagnosis_config_for_knowledge(
                MagicMock(), {"id": 4657, "similarity": 0.9},
                DecisionConfig(form_trigger_threshold=0.75), user_message="問句")

    # 基準：telemetry 正常
    _setup()
    monkeypatch.setattr(chat_mod, "_meter_decision", lambda **_k: None)
    base_cfg, base_auth = await _call()

    # 注入：telemetry 每次都炸
    _setup()
    def _boom(**_kwargs):
        raise RuntimeError("telemetry down")
    monkeypatch.setattr(chat_mod, "_meter_decision", _boom)
    cfg, auth = await _call()

    assert cfg is base_cfg and auth == base_auth, \
        "telemetry 故障改變了 routing → observability 成了 execution dependency"
    assert cfg is b, "基準本身要有意義（應由第二候選 commit），否則此測試無鑑別力"


# ── ④ analysis epoch：face mapping digest ──────────────────────────────────
#
# ⚠️ 為什麼要這格（實查後才確定）：既有 `DecisionConfig.config_hash()` 只雜湊門檻／env，
#    `_generate_config_version()` 只有兩個門檻——**都不涵蓋** Face config 與
#    category→facet 映射，而那是在 DB 裡獨立修改的。
#    沒有這格，改動前後的 production 資料會被混進同一個 funnel。

@pytest.mark.req("conversational-routing-execution:stage1-epoch")
def test_mapping_digest_moves_when_mapping_changes():
    """★ 正控制＋突變：映射改變 → digest 必須跟著變；同映射 → 必須穩定。"""
    from services import conversational_config as cc

    def _fake(key):
        return ConversationalConfig(key=key, persona_role=f"pm_{key}", enabled=True,
                                    topic_scope={"mode": "category", "category": f"cat_{key}"})

    orig_loaded, orig_bycat = cc._cache["loaded"], cc._cache["by_category"]
    try:
        cc._cache["loaded"] = True
        cc._cache["by_category"] = {"甲": _fake("a"), "乙": _fake("b")}
        d1 = cc.mapping_digest()
        d1_again = cc.mapping_digest()
        assert d1 and d1 == d1_again, "同一份映射的 digest 必須穩定（否則無法切 epoch）"

        # 突變①：改掉某 category 指向的面向
        cc._cache["by_category"] = {"甲": _fake("a"), "乙": _fake("CHANGED")}
        assert cc.mapping_digest() != d1, "面向改指向卻 digest 不變 → epoch 邊界看不見"

        # 突變②：移除一個 mapping
        cc._cache["by_category"] = {"甲": _fake("a")}
        assert cc.mapping_digest() != d1, "移除 mapping 卻 digest 不變 → epoch 邊界看不見"
    finally:
        cc._cache["loaded"], cc._cache["by_category"] = orig_loaded, orig_bycat


@pytest.mark.req("conversational-routing-execution:stage1-epoch")
def test_mapping_digest_never_triggers_a_load():
    """⚠️ 觀測不得產生 side effect：快取未載入時回 None，**不得**去讀 DB。"""
    from services import conversational_config as cc
    orig = cc._cache["loaded"]
    try:
        cc._cache["loaded"] = False
        assert cc.mapping_digest() is None, "未載入時應回 None，不得為了記錄而觸發載入"
    finally:
        cc._cache["loaded"] = orig
