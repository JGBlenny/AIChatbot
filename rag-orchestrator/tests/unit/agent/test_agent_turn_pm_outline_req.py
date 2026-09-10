"""unit：DSP-037（業主 2026-09-07 裁）S1a＋S1b——pm 受眾接上 `agent.turn` 與**自己的**正本大綱。

Plan：`.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-mcp-demo-key-and-flag-20260907.md`

覆蓋：
- (a) S1a：`AGENT_TURN_SPEC["stage"]` 對 pm 開 M1、tenant **缺鍵＝永不可見**、prospect 不變。
- (b) pm 回合的 `trace.outline_sha` ＝ **當場以啟動同式現算**的 pm 大綱 sha
      （⛔ 不比 `canon_sha256`——那是正本雜湊，不是大綱雜湊），且 ≠ prospect 那一份。
- (c) pm 正本缺檔 ⇒ pm 的 `agent.turn` 回 `AGENT_UNAVAILABLE`／fail-closed，prospect 照常。
- (d) pm 回合走候選路徑：`miss_kind='hit'`、候選 ≤ K、⛔ 無 `candidate_selector_error`／
      `candidate_none_visible`（假 embedding 後端，⛔ 不打真 API）。
- (e) health：索引三態映射含兩受眾；**pm 索引非 ready ⇒ 紅**（正對照：兩者皆 ready ⇒ 不紅）。
- (f) `build_prospect_outline` 的 sha 不因泛化而變（與 `build_audience_outline("prospect")` 同值、
      且同一份正本重跑決定性相同）。

⚠️ 身分一律 `vendor_id=0`：pm＋真實 vendor_id 會讓 `resolve_vendor_business_types`
去問 `VendorParameterResolver`（真 DB），unit 層 ⛔ 不碰 DB。
"""
from __future__ import annotations

import shutil
import types

import pytest

from services.agent import mcp_facade as F
from services.agent.budget import Budget
from services.agent.canon.canon_assembler import (
    build_canon_toc,
    build_outline,
    load_canon_or_die,
    register_canon,
    reset_canon_registry,
    resolve_canon_dir,
)
from services.agent.canon.candidate_selector import K, CandidateSelector
from services.agent.canon.fine_index import (
    FineIndex,
    register_index,
    reset_index_registry,
)
from services.agent.identity import Identity
from services.agent.outline import (
    _build_doc,
    build_audience_outline,
    build_prospect_outline,
)
from services.agent.prompt_assembler import PromptAssembler
from services.agent.runtime import AgentRuntime
from services.agent.tools.registry import ToolRegistry

from tests.unit.agent.test_runtime_req import (  # noqa: E402
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    _final_response,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:DSP-037"),
]

PM = Identity(vendor_id=0, target_user="property_manager", mode="b2b",
              session_id="s-pm", api_key_id=1)
PROSPECT = Identity(vendor_id=0, target_user="prospect", mode="b2b",
                    session_id="s-pr", api_key_id=1)
TENANT = Identity(vendor_id=0, target_user="tenant", mode="b2c",
                  session_id="s-tn", api_key_id=1)


@pytest.fixture(autouse=True)
def _reset_registries():
    reset_canon_registry()
    reset_index_registry()
    yield
    reset_canon_registry()
    reset_index_registry()


class _FakeBackend:
    """假 embedding 後端：所有文字同一個單位向量 ⇒ `prepare` 必 ready、分數全同
    ⇒ 排序落在決定性的 `(-score, fine_id)` 字典序（⛔ 不打真 API）。"""

    def __init__(self, *, raises: bool = False) -> None:
        self._raises = raises

    async def embed(self, texts):
        if self._raises:
            raise RuntimeError("後端故障（測試用）")
        return [[1.0, 0.0] for _ in texts]


def _real_assembler() -> PromptAssembler:
    return PromptAssembler(lambda identity: "persona-x", lambda identity: "policy-x")


def _runtime_with_selectors(*, provider, selectors):
    return AgentRuntime(
        provider,
        FakeRegistry(),
        FakeVerifier(),
        _real_assembler(),
        Budget(),
        stage="M1",
        candidate_selectors=selectors,
    )


def _expected_pm_outline_sha() -> str:
    """啟動同式**現算**一次 pm 大綱 sha（⛔ 不從 `build_audience_outline` 抄回傳值，
    那樣等於拿被測物驗自己）。式子＝`build_outline` 的節 ＋ 靜態身分的 `outline:toc`，
    再走 `_build_doc`（version＝正本 version）。"""
    canon = load_canon_or_die(resolve_canon_dir(), "property_manager")
    static_identity = Identity(vendor_id=0, target_user="property_manager", mode="b2b")
    toc = build_canon_toc(canon, static_identity, vendor_business_types=frozenset())
    doc = _build_doc(
        audience=canon.audience,
        sections=list(build_outline(canon).sections) + [toc],
        version=canon.version,
    )
    return doc.sha256


# ═══════════════════════════════════════════════════════════════════
# (a) S1a：stage 對照表
# ═══════════════════════════════════════════════════════════════════


def test_s1a_stage_opens_pm_keeps_tenant_invisible_and_prospect_unchanged():
    deps = F.FacadeDeps(get_db_pool=lambda: None)
    registry = ToolRegistry()
    registry.register(F.AGENT_TURN_SPEC, F._make_agent_turn(deps))

    def names(identity, stage="M1"):
        return {s["name"] for s in registry.specs_for(identity, stage, for_model=False)}

    assert F.AGENT_TURN_NAME in names(PM)                    # DSP-037 新增
    assert F.AGENT_TURN_NAME not in names(TENANT)            # 缺鍵＝永不可見
    assert F.AGENT_TURN_NAME in names(PROSPECT)              # 不變（正對照組）
    assert F.AGENT_TURN_NAME not in names(PM, "M0")          # stage 未到仍不可見
    # ⛔ 模型視角一律看不到（facade_only）——pm 開放 ⛔ 不等於開給模型自呼
    assert F.AGENT_TURN_NAME not in {
        s["name"] for s in registry.specs_for(PM, "M5", for_model=True)
    }


# ═══════════════════════════════════════════════════════════════════
# (b)(d) pm 回合：outline_sha 現算相符、走候選路徑
# ═══════════════════════════════════════════════════════════════════


async def test_pm_turn_uses_pm_outline_sha_and_hits_candidate_path():
    pm_doc = await build_audience_outline("property_manager")
    expected_sha = _expected_pm_outline_sha()
    assert pm_doc.sha256 == expected_sha

    canon = load_canon_or_die(resolve_canon_dir(), "property_manager")
    index = FineIndex(_FakeBackend())
    await index.prepare(canon)
    assert index.state == "ready", "假後端下 prepare 必須 ready，否則本測試量的是降級路徑"
    register_index("property_manager", index)

    runtime = _runtime_with_selectors(
        provider=FakeProvider([_final_response(answer="pm 的答案")]),
        selectors={"property_manager": CandidateSelector(index)},
    )
    result = await runtime.run_turn(
        PM, "拍照開修繕單怎麼做", {"agent": {"outline": pm_doc, "dialog": []}}
    )

    # (b) trace 的大綱 sha ＝ 現算的 pm 大綱 sha
    assert result.trace.outline_sha == expected_sha
    # (d) 候選路徑
    assert result.trace.miss_kind == "hit"
    assert 0 < len(result.trace.candidate_ids) <= K
    assert all(fid.startswith("property_manager/") for fid in result.trace.candidate_ids)
    assert "candidate_selector_error" not in result.trace.violations
    assert "candidate_none_visible" not in result.trace.violations
    assert "candidate_fallback_full_outline" not in result.trace.violations


async def test_pm_outline_sha_differs_from_prospect():
    """兩份正本是兩份大綱——sha 相等就代表某一邊拿錯了正本（本片要修的正是那個洞）。"""
    pm_doc = await build_audience_outline("property_manager")
    prospect_doc = await build_audience_outline("prospect")
    assert pm_doc.sha256 != prospect_doc.sha256
    assert pm_doc.audience == "property_manager"
    assert prospect_doc.audience == "prospect"


async def test_pm_turn_without_pm_selector_degrades_visible_not_prospect_index():
    """對照表有、卻缺 pm ⇒ 降級成可見細目全集＋toc，並在 trace 記
    `candidate_fallback_full_outline`（⛔ 不靜默回退去用 prospect 的索引）。"""
    pm_doc = await build_audience_outline("property_manager")
    prospect_canon = load_canon_or_die(resolve_canon_dir(), "prospect")
    prospect_index = FineIndex(_FakeBackend())
    await prospect_index.prepare(prospect_canon)
    register_index("prospect", prospect_index)

    runtime = _runtime_with_selectors(
        provider=FakeProvider([_final_response(answer="降級也要答")]),
        selectors={"prospect": CandidateSelector(prospect_index)},
    )
    result = await runtime.run_turn(
        PM, "拍照開修繕單怎麼做", {"agent": {"outline": pm_doc, "dialog": []}}
    )
    assert "candidate_fallback_full_outline" in result.trace.violations
    assert result.trace.miss_kind == "index_unavailable"
    assert result.trace.candidate_ids == []


# ═══════════════════════════════════════════════════════════════════
# (c) pm 正本缺檔 ⇒ pm fail-closed、prospect 照常
# ═══════════════════════════════════════════════════════════════════


def _canon_dir_without_pm(tmp_path):
    """只含 prospect 兩檔的正本目錄（⛔ 不動版控 `canon/`）。"""
    src = resolve_canon_dir()
    dst = tmp_path / "canon"
    dst.mkdir()
    for name in ("prospect.md", "prospect.json"):
        shutil.copy2(src / name, dst / name)
    assert not (dst / "property_manager.md").exists()
    return dst


class _FakeEngine:
    """形狀對齊 `services.agent.session_persistence.AgentSessionStore`（公開方法名）。"""

    async def get_state(self, session_id):
        return None

    async def start(self, *a, **k):
        return {}

    async def save(self, *a, **k):
        return None


async def test_missing_pm_canon_skips_pm_only_and_fails_closed(monkeypatch, tmp_path):
    import app as app_module
    from services.agent.canon import fine_index as fine_index_mod
    import services.llm_provider as llm_provider_mod

    monkeypatch.setenv("DB_ENV", "test")          # `AGENT_CANON_DIR` 只在 test 生效
    monkeypatch.setenv("AGENT_CANON_DIR", str(_canon_dir_without_pm(tmp_path)))
    monkeypatch.setattr(fine_index_mod, "EmbeddingUtilsBackend", lambda: _FakeBackend())
    monkeypatch.setattr(
        llm_provider_mod, "get_llm_provider",
        lambda *a, **k: types.SimpleNamespace(async_client=None),
    )

    app = types.SimpleNamespace(state=types.SimpleNamespace(db_pool=None))
    await app_module._init_agent_runtime(app)     # ⛔ 不 raise：只跳過 pm

    # prospect 照常組起來（正對照組：缺的是 pm，不是整條路）
    assert app.state.agent_runtime is not None
    assert set(app.state.agent_outlines) == {"prospect"}
    assert app.state.agent_outline is app.state.agent_outlines["prospect"]

    app.state.agent_session_store = _FakeEngine()
    deps = F.FacadeDeps(get_db_pool=lambda: None, get_app=lambda: app)

    # 門面層：pm ⇒ AGENT_UNAVAILABLE；prospect ⇒ 放行（preflight 回 None）
    F.reset_agent_turn_cap()
    assert F._agent_turn_preflight(deps, PM) == F.ERR_AGENT_UNAVAILABLE
    assert F._agent_turn_preflight(deps, PROSPECT) is None

    # 取大綱層：pm 取不到（⛔ 不回退成 prospect 那一份）
    assert F._outline_for_audience(deps, "property_manager") is F._OUTLINE_UNAVAILABLE
    assert F._outline_for_audience(deps, "prospect") is app.state.agent_outlines["prospect"]


async def test_tool_fn_never_injects_another_audiences_outline():
    """繞過門面直呼 `registry.call()` 的第二道網：pm 取不到大綱 ⇒ 封閉值域的
    `NO_MATCH`，⛔ 不塞 prospect 大綱、⛔ 不跑回合。"""
    seen: dict = {}

    class _Runtime:
        async def run_turn(self, identity, message, state):
            seen["outline"] = state.get("agent", {}).get("outline")
            return types.SimpleNamespace(
                answer="ok", kind="answer", handoff=None, quick_replies=[],
                trace=types.SimpleNamespace(trace_id="t1"),
            )

    prospect_doc = await build_audience_outline("prospect")
    app = types.SimpleNamespace(state=types.SimpleNamespace(
        agent_runtime=_Runtime(),
        agent_session_store=_FakeEngine(),
        agent_outlines={"prospect": prospect_doc},
    ))
    deps = F.FacadeDeps(get_db_pool=lambda: None, get_app=lambda: app)
    registry = ToolRegistry()
    registry.register(F.AGENT_TURN_SPEC, F._make_agent_turn(deps))

    pm_result = await registry.call(PM, F.AGENT_TURN_NAME, {"message": "嗨"}, 5.0, stage="M1")
    assert pm_result.ok is False and pm_result.error == "NO_MATCH"
    assert "outline" not in seen, "⛔ pm 回合根本不該跑起來，更不該看到任何大綱"

    # 正對照組：prospect 同一條路照樣跑得完，且看到的是 prospect 那一份
    ok_result = await registry.call(
        PROSPECT, F.AGENT_TURN_NAME, {"message": "嗨"}, 5.0, stage="M1"
    )
    assert ok_result.ok is True, ok_result.error
    assert seen["outline"] is prospect_doc


# ═══════════════════════════════════════════════════════════════════
# (e) health：兩受眾映射；pm 索引非 ready ⇒ 紅
# ═══════════════════════════════════════════════════════════════════


class _FakeKbPool:
    """kb 探針走得通的假 pool（樣式沿 `test_fine_index_req.py`）。"""

    def getconn(self):
        class _Conn:
            def cursor(self):
                class _Cur:
                    def execute(self, *a, **k):
                        pass

                    def fetchone(self):
                        return None

                    def close(self):
                        pass
                return _Cur()
        return _Conn()

    def putconn(self, conn):
        pass


async def _health_isolated(monkeypatch):
    """把與本片無關的紅燈成因撥乾淨，讓 `status` 的絕對值只受索引這一項影響。"""
    from services.agent.health import compute_agent_health
    import services.api_key_auth as api_key_auth

    monkeypatch.setattr(F, "agent_configured", lambda: True)
    monkeypatch.setattr(F, "premise_stats", lambda: {})
    monkeypatch.setattr(api_key_auth, "agent_scope_cols_state", lambda: True)
    registry = F.build_registry(F.FacadeDeps(
        get_db_pool=lambda: None, get_kb_pool=lambda: None, get_retriever=None))
    return await compute_agent_health(
        registry=registry, get_kb_pool=lambda: _FakeKbPool(), stage="M0")


async def _ready_index(canon) -> FineIndex:
    index = FineIndex(_FakeBackend())
    await index.prepare(canon)
    assert index.state == "ready"
    return index


async def test_health_maps_both_audiences_and_pm_not_ready_turns_red(monkeypatch):
    prospect_canon = load_canon_or_die(resolve_canon_dir(), "prospect")
    pm_canon = load_canon_or_die(resolve_canon_dir(), "property_manager")
    register_canon("prospect", prospect_canon)
    register_canon("property_manager", pm_canon)

    register_index("prospect", await _ready_index(prospect_canon))
    pm_not_ready = FineIndex(_FakeBackend(raises=True))
    await pm_not_ready.prepare(pm_canon)
    assert pm_not_ready.state == "not_ready"
    register_index("property_manager", pm_not_ready)

    result = await _health_isolated(monkeypatch)
    canon_state = result["checks"]["canon"]
    assert set(canon_state["sha256"]) == {"prospect", "property_manager"}
    assert canon_state["sha256"]["property_manager"] == pm_canon.canon_sha256
    assert canon_state["index"]["prospect"]["state"] == "ready"
    assert canon_state["index"]["property_manager"]["state"] == "not_ready"
    # prospect 是 ready、pm 不是 ⇒ 仍然紅（S1b 前只看 prospect ⇒ 會是綠的假象）
    assert result["status"] == "red"

    # 正對照組：把 pm 換成 ready ⇒ 這一項不再致紅
    register_index("property_manager", await _ready_index(pm_canon))
    ok_result = await _health_isolated(monkeypatch)
    assert ok_result["checks"]["canon"]["index"]["property_manager"]["state"] == "ready"
    assert ok_result["status"] != "red", ok_result["checks"]


async def test_health_prospect_only_semantics_unchanged(monkeypatch):
    """只註冊 prospect（pm 正本沒上線）⇒ 語義與 S1b 前相同：prospect ready 就不紅。"""
    prospect_canon = load_canon_or_die(resolve_canon_dir(), "prospect")
    register_canon("prospect", prospect_canon)
    register_index("prospect", await _ready_index(prospect_canon))

    result = await _health_isolated(monkeypatch)
    assert result["checks"]["canon"]["index"]["property_manager"]["state"] == "absent"
    assert result["status"] != "red", result["checks"]


# ═══════════════════════════════════════════════════════════════════
# (f) prospect 逐位元不變
# ═══════════════════════════════════════════════════════════════════


async def test_build_prospect_outline_is_thin_alias_and_stays_deterministic():
    alias = await build_prospect_outline(None)
    generic = await build_audience_outline("prospect", None)
    assert alias.sha256 == generic.sha256
    assert alias.text == generic.text
    assert alias.version == generic.version
    assert [s.id for s in alias.sections] == [s.id for s in generic.sections]
    # 決定性：同一份正本重跑同一個 sha
    assert (await build_prospect_outline(None)).sha256 == alias.sha256


async def test_build_audience_outline_rejects_audience_without_canon():
    """tenant 沒有 git 正本 ⇒ 大聲失敗，⛔ 不靜默回一份別人的大綱。"""
    with pytest.raises(ValueError):
        await build_audience_outline("tenant")
