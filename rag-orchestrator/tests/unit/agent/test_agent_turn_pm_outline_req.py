"""unit：DSP-037（業主 2026-09-07 裁）S1a＋S1b——pm 受眾接上 `agent.turn` 與**自己的**正本大綱。

Plan：`.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-mcp-demo-key-and-flag-20260907.md`

覆蓋：
- (a) S1a：`AGENT_TURN_SPEC["stage"]` 對 pm 開 M1、tenant **缺鍵＝永不可見**、prospect 不變。
- (b) pm 回合的 `trace.outline_sha` ＝ **當場以啟動同式現算**的 pm 大綱 sha
      （⛔ 不比 `canon_sha256`——那是正本雜湊，不是大綱雜湊），且 ≠ prospect 那一份。
- (c) pm **視圖**組不起來（DSP-058 後正本只有一份，改以預算上限逼它失敗）⇒ pm 的
      `agent.turn` 回 `AGENT_UNAVAILABLE`／fail-closed，prospect 照常；
      **正本本身缺席** ⇒ 整條 agent 路徑不可用（⛔ 不是某受眾跳過）。
- (d) pm 回合走候選路徑：`miss_kind='hit'`、候選 ≤ K、⛔ 無 `candidate_selector_error`／
      `candidate_none_visible`（假 embedding 後端，⛔ 不打真 API）。
- (e) health：索引三態映射含兩受眾；**pm 索引非 ready ⇒ 紅**（正對照：兩者皆 ready ⇒ 不紅）。
- (f) `build_prospect_outline` 的 sha 不因泛化而變（與 `build_audience_outline("prospect")` 同值、
      且同一份正本重跑決定性相同）。

⚠️ 身分一律 `vendor_id=0`：pm＋真實 vendor_id 會讓 `resolve_vendor_business_types`
去問 `VendorParameterResolver`（真 DB），unit 層 ⛔ 不碰 DB。
"""
from __future__ import annotations

import pathlib
import re
import shutil
import types

import pytest

from services.agent import mcp_facade as F
from services.agent.budget import Budget
from services.agent.canon.canon_assembler import (
    CANON_DIR_ENV,
    DB_ENV_KEY,
    build_canon_toc,
    build_outline,
    load_canon_or_die,
    register_canon,
    reset_canon_registry,
    resolve_canon_dir,
)
from services.agent.canon.canon_parser import (
    CANON_NAME,
    export_catalog,
    export_json,
    parse_canon_dir,
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


#: 9.8 DSP-059 D′ S2：trace 的大綱 sha 現在直接就是 `canon.canon_sha256`——
#: 沒有再需要「啟動同式現算一次視圖 sha」這個輔助函式了（那個量尺量的是預組
#: `OutlineDoc` 的 sha，S2 後不存在這個物件）。


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


async def test_pm_turn_uses_pm_outline_sha_and_hits_candidate_path(monkeypatch, tmp_path):
    """計畫 9.10 S4：版控正本 515 條全未審，pm 視圖無可見已審細目 ⇒ 候選必
    `none_visible`。本測試要驗的是「候選路徑真的能命中」，改指向 `tmp_path`
    下的全審副本（`AGENT_CANON_DIR`，僅 `DB_ENV=test` 生效；⛔ 不動版控 `canon/`）。"""
    monkeypatch.setenv(DB_ENV_KEY, "test")
    monkeypatch.setenv(CANON_DIR_ENV, str(_all_reviewed_canon_dir(tmp_path)))
    canon = load_canon_or_die(resolve_canon_dir())
    register_canon(canon)
    pm_doc = await build_audience_outline("property_manager")

    index = FineIndex(_FakeBackend())
    await index.prepare(canon)
    assert index.state == "ready", "假後端下 prepare 必須 ready，否則本測試量的是降級路徑"
    register_index("property_manager", index)

    runtime = _runtime_with_selectors(
        provider=FakeProvider([_final_response(answer="pm 的答案")]),
        selectors={"property_manager": CandidateSelector(index)},
    )
    result = await runtime.run_turn(
        PM, "拍照開修繕單怎麼做", {"agent": {"dialog": []}}
    )

    # (b) 9.8 DSP-059 D′ S2：trace 的大綱 sha ＝ 正本 sha（⛔ 不再是預組視圖的 sha——
    # 每回合現組的 `CandidateOutlineDoc.sha256` 直接複製 `canon.canon_sha256`）。
    assert result.trace.outline_sha == canon.canon_sha256
    # (d) 候選路徑
    assert result.trace.miss_kind == "hit"
    assert 0 < len(result.trace.candidate_ids) <= K
    # DSP-058：細目 id 首段是**正本名** `jgb`（⛔ 不再是受眾名）；受眾隔離看的是視圖與
    # `visible_subset`，不是 id 前綴——故另外斷言候選都在 pm 視圖的節 id 內。
    pm_section_ids = {s.id for s in pm_doc.sections}
    assert all(fid.startswith("jgb/") for fid in result.trace.candidate_ids)
    assert set(result.trace.candidate_ids) <= pm_section_ids
    assert "candidate_selector_error" not in result.trace.violations
    assert "candidate_none_visible" not in result.trace.violations
    assert "candidate_fallback_toc_only" not in result.trace.violations


async def test_pm_outline_sha_differs_from_prospect():
    """一份正本、兩份視圖——sha 相等就代表視圖沒有真的切開（DSP-058 後這是隔離的主證據）。"""
    pm_doc = await build_audience_outline("property_manager")
    prospect_doc = await build_audience_outline("prospect")
    assert pm_doc.sha256 != prospect_doc.sha256
    assert pm_doc.audience == "property_manager"
    assert prospect_doc.audience == "prospect"


async def test_pm_turn_without_pm_selector_degrades_to_toc_only():
    """對照表有、卻缺 pm ⇒ 降級為 toc-only（9.8 DSP-059 D′：⛔ 不再是可見細目全集），
    並在 trace 記 `candidate_fallback_toc_only`（⛔ 不靜默回退去用 prospect 那個 selector）。"""
    canon = load_canon_or_die(resolve_canon_dir())
    register_canon(canon)
    prospect_index = FineIndex(_FakeBackend())
    await prospect_index.prepare(canon)
    register_index("prospect", prospect_index)

    runtime = _runtime_with_selectors(
        provider=FakeProvider([_final_response(answer="降級也要答")]),
        selectors={"prospect": CandidateSelector(prospect_index)},
    )
    result = await runtime.run_turn(
        PM, "拍照開修繕單怎麼做", {"agent": {"dialog": []}}
    )
    assert "candidate_fallback_toc_only" in result.trace.violations
    assert result.trace.miss_kind == "index_unavailable"
    assert result.trace.candidate_ids == []


# ═══════════════════════════════════════════════════════════════════
# (c) pm 正本缺檔 ⇒ pm fail-closed、prospect 照常
# ═══════════════════════════════════════════════════════════════════


#: 版控正本目錄的**固定**位置（⛔ 不走 `resolve_canon_dir()`：那支會被 `AGENT_CANON_DIR`
#: 覆寫，測試中途改過 env 之後再呼叫就會複製到剛剛那個假目錄）。
_VERSIONED_CANON_DIR = pathlib.Path(__file__).resolve().parents[3] / "canon"


def _canon_dir_copy(tmp_path, name="canon"):
    """版控正本的 tmp 複本（`jgb/`＋`jgb.json`；⛔ 不動版控 `canon/`）。"""
    src = _VERSIONED_CANON_DIR
    dst = tmp_path / name
    dst.mkdir()
    shutil.copytree(src / "jgb", dst / "jgb")
    shutil.copy2(src / "jgb.json", dst / "jgb.json")
    return dst


#: 計畫 9.10 S4：版控正本 515 條全未審（DSP-066：未審 ⇒ 模型不可見）⇒ 候選路徑
#: 測不到 `miss_kind == "hit"`。這裡需要的是「候選真的能命中」這件事本身，
#: 不是審核狀態 ⇒ 造一份 `tmp_path` 下的全審副本（⛔ 不動版控 `canon/`）。
_FINE_HEADING_RE = re.compile(r"^### .+\{#jgb/[A-Z]/[a-z0-9-]+\}\s*$", re.M)


def _all_reviewed_canon_dir(tmp_path, name="all-reviewed-canon"):
    src = _VERSIONED_CANON_DIR
    dst = tmp_path / name
    shelf_dst = dst / CANON_NAME
    shelf_dst.mkdir(parents=True)
    for letter in "ABCDEFGHI":
        text = (src / CANON_NAME / f"{letter}.md").read_text(encoding="utf-8")
        marked = _FINE_HEADING_RE.sub(
            lambda m: m.group(0) + "\n- reviewed: {by: s4-measurement, at: 2026-09-23}",
            text,
        )
        assert marked != text, f"{letter}.md 沒有任何細目被標 reviewed，注入沒生效"
        (shelf_dst / f"{letter}.md").write_text(marked, encoding="utf-8")
    doc = parse_canon_dir(str(shelf_dst))
    assert all(f.reviewed_by is not None for f in doc.fines()), "仍有未審細目，注入失敗"
    export_json(doc, str(dst / f"{CANON_NAME}.json"))
    export_catalog(doc, str(shelf_dst / "CATALOG.md"))
    return dst


class _FakeEngine:
    """形狀對齊 `services.agent.session_persistence.AgentSessionStore`（公開方法名）。"""

    async def get_state(self, session_id):
        return None

    async def start(self, *a, **k):
        return {}

    async def save(self, *a, **k):
        return None


async def test_failed_pm_view_skips_pm_only_and_fails_closed(monkeypatch, tmp_path):
    """DSP-058 後「pm 正本缺檔」已不存在（只有一份正本）；改以 **pm 視圖組不起來**逼出
    同一條路：⛔ 不 raise、只跳過 pm，prospect 照常。

    計畫 9.10 S4：版控正本 515 條全未審 ⇒ pm 視圖 `k_upper` 恆為 0，原本「壓到 1
    token」的手法在 `0 > 1` 恆假下逼不出超標（負對照變空）。改用**不依賴 `k_upper`
    實際值**的手段：token 數不可能為負，`k_upper（>=0） > -1` 恆成立——這條測的是
    「env 覆寫真的接到 `check_turn_budget` 的比較式、pm 視圖組不起來時整條路真的
    fail-closed」這個契約本身，不依賴正本的審核狀態。"""
    import app as app_module
    from services.agent.canon import fine_index as fine_index_mod
    import services.llm_provider as llm_provider_mod

    monkeypatch.setenv("DB_ENV", "test")          # `AGENT_CANON_DIR` 只在 test 生效
    monkeypatch.setenv("AGENT_CANON_DIR", str(_canon_dir_copy(tmp_path)))
    monkeypatch.setenv("AGENT_OUTLINE_K_TOKEN_LIMIT_PM", "-1")   # pm 視圖必超 K 上界 ⇒ 只跳過 pm
    monkeypatch.setattr(fine_index_mod, "EmbeddingUtilsBackend", lambda: _FakeBackend())
    monkeypatch.setattr(
        llm_provider_mod, "get_llm_provider",
        lambda *a, **k: types.SimpleNamespace(async_client=None),
    )

    app = types.SimpleNamespace(state=types.SimpleNamespace(db_pool=None))
    await app_module._init_agent_runtime(app)     # ⛔ 不 raise：只跳過 pm

    # prospect 照常組起來（正對照組：壞的是 pm 視圖，不是整條路）
    assert app.state.agent_runtime is not None
    # 9.8 DSP-059 D′ S2：權威旗標是 `agent_audiences`（frozenset），⛔ 不再有
    # `agent_outlines`／`agent_outline` 可讀。
    assert app.state.agent_audiences == frozenset({"prospect"})

    app.state.agent_session_store = _FakeEngine()
    deps = F.FacadeDeps(get_db_pool=lambda: None, get_app=lambda: app)

    # 門面層：pm ⇒ AGENT_UNAVAILABLE；prospect ⇒ 放行（preflight 回 None）
    F.reset_agent_turn_cap()
    assert F._agent_turn_preflight(deps, PM) == F.ERR_AGENT_UNAVAILABLE
    assert F._agent_turn_preflight(deps, PROSPECT) is None

    # 就緒層：pm 取不到（⛔ 不回退成 prospect 那一份）；prospect 就緒（回 None）
    assert F._outline_for_audience(deps, "property_manager") is F._OUTLINE_UNAVAILABLE
    assert F._outline_for_audience(deps, "prospect") is None


async def test_missing_canon_disables_the_whole_agent_path(monkeypatch, tmp_path):
    """DSP-058：正本缺席＝**整條 agent 路徑不可用**，⛔ 不是「某個受眾跳過」。

    （agent 開關全關 ⇒ 外層 except fail-soft、不 raise；開著時同一個 except 升啟動紅，
    語義見 `app.py::_init_agent_runtime`。）
    """
    import app as app_module
    from services.agent.canon import fine_index as fine_index_mod
    import services.llm_provider as llm_provider_mod

    empty = tmp_path / "empty-canon"
    empty.mkdir()
    monkeypatch.setenv("DB_ENV", "test")
    monkeypatch.setenv("AGENT_CANON_DIR", str(empty))
    for key in ("AGENT_AUDIENCES", "AGENT_SHADOW_AUDIENCES", "AGENT_TURN_ENABLED"):
        monkeypatch.delenv(key, raising=False)    # agent 開關全關 ⇒ fail-soft
    monkeypatch.setattr(fine_index_mod, "EmbeddingUtilsBackend", lambda: _FakeBackend())
    monkeypatch.setattr(
        llm_provider_mod, "get_llm_provider",
        lambda *a, **k: types.SimpleNamespace(async_client=None),
    )

    app = types.SimpleNamespace(state=types.SimpleNamespace(db_pool=None))
    await app_module._init_agent_runtime(app)

    assert app.state.agent_runtime is None
    assert app.state.agent_audiences == frozenset()
    # 正對照：同一支初始化在正本正常時組得起來（⛔ 不是恆 None）
    monkeypatch.setenv("AGENT_CANON_DIR", str(_canon_dir_copy(tmp_path, "good-canon")))
    app2 = types.SimpleNamespace(state=types.SimpleNamespace(db_pool=None))
    await app_module._init_agent_runtime(app2)
    assert app2.state.agent_runtime is not None
    assert app2.state.agent_audiences == frozenset({"prospect", "property_manager"})


async def test_tool_fn_never_lets_an_unavailable_audience_reach_run_turn():
    """繞過門面直呼 `registry.call()` 的第二道網：pm 不在 `agent_audiences` ⇒
    封閉值域的 `NO_MATCH`、⛔ 不跑回合；prospect 就緒 ⇒ 照常跑起來（9.8 DSP-059
    D′ S2：不再有大綱物件可「注入」——`_agent_turn` 只判就緒與否，每回合的
    候選節由 `Runtime._select_outline` 自己從已註冊的正本現組）。"""
    calls: list = []

    class _Runtime:
        async def run_turn(self, identity, message, state):
            calls.append(identity.resolved_audience())
            return types.SimpleNamespace(
                answer="ok", kind="answer", handoff=None, quick_replies=[],
                trace=types.SimpleNamespace(trace_id="t1"),
            )

    app = types.SimpleNamespace(state=types.SimpleNamespace(
        agent_runtime=_Runtime(),
        agent_session_store=_FakeEngine(),
        agent_audiences=frozenset({"prospect"}),
    ))
    deps = F.FacadeDeps(get_db_pool=lambda: None, get_app=lambda: app)
    registry = ToolRegistry()
    registry.register(F.AGENT_TURN_SPEC, F._make_agent_turn(deps))

    pm_result = await registry.call(PM, F.AGENT_TURN_NAME, {"message": "嗨"}, 5.0, stage="M1")
    assert pm_result.ok is False and pm_result.error == "NO_MATCH"
    assert calls == [], "⛔ pm 回合根本不該跑起來"

    # 正對照組：prospect 同一條路照樣跑得完
    ok_result = await registry.call(
        PROSPECT, F.AGENT_TURN_NAME, {"message": "嗨"}, 5.0, stage="M1"
    )
    assert ok_result.ok is True, ok_result.error
    assert calls == ["prospect"]


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
    canon = load_canon_or_die(resolve_canon_dir())
    register_canon(canon)

    register_index("prospect", await _ready_index(canon))
    pm_not_ready = FineIndex(_FakeBackend(raises=True))
    await pm_not_ready.prepare(canon)
    assert pm_not_ready.state == "not_ready"
    register_index("property_manager", pm_not_ready)

    result = await _health_isolated(monkeypatch)
    canon_state = result["checks"]["canon"]
    # DSP-058：`sha256` 的鍵是**正本名**（一份正本），⛔ 不再是受眾
    assert set(canon_state["sha256"]) == {"jgb"}
    assert canon_state["sha256"]["jgb"] == canon.canon_sha256
    assert canon_state["index"]["prospect"]["state"] == "ready"
    assert canon_state["index"]["property_manager"]["state"] == "not_ready"
    # prospect 是 ready、pm 不是 ⇒ 仍然紅（只看 prospect ⇒ 會是綠的假象）
    assert result["status"] == "red"

    # 正對照組：把 pm 換成 ready ⇒ 這一項不再致紅
    register_index("property_manager", await _ready_index(canon))
    ok_result = await _health_isolated(monkeypatch)
    assert ok_result["checks"]["canon"]["index"]["property_manager"]["state"] == "ready"
    assert ok_result["status"] != "red", ok_result["checks"]


async def test_health_checked_audiences_follow_canon_registration(monkeypatch):
    """受檢受眾集合＝`prospect` ∪（**正本已註冊**時）有視圖的受眾。

    - 正本**未**註冊（啟動中）＋prospect 索引 ready ⇒ 不紅（pm 的 `absent` 不算數：
      「還沒載正本」不是「載了卻缺 pm」）。
    - 正本**已**註冊、pm 索引 absent ⇒ 紅（那代表 pm 視圖或索引在產線缺席＝降級服務）。
      ⚠️ 這是 9.6 的行為改變：S3 前 pm 只在「pm 正本被註冊」時才受檢。
    """
    canon = load_canon_or_die(resolve_canon_dir())
    register_index("prospect", await _ready_index(canon))

    before = await _health_isolated(monkeypatch)
    assert before["checks"]["canon"]["sha256"] == {}
    assert before["checks"]["canon"]["index"]["property_manager"]["state"] == "absent"
    assert before["status"] != "red", before["checks"]

    register_canon(canon)
    after = await _health_isolated(monkeypatch)
    assert after["checks"]["canon"]["index"]["property_manager"]["state"] == "absent"
    assert after["status"] == "red"


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


# ═══════════════════════════════════════════════════════════════════
# ⑥ F2 fail-closed：`_agent_turn_preflight` 只認 `app.state.agent_audiences`
# （frozenset）——屬性缺席／`None`／非集合／空集合四種形狀一律
# `ERR_AGENT_UNAVAILABLE`，⛔ 對任何 falsy 形狀放行；正對照
# `frozenset({"prospect"})` ⇒ `None`（就緒）；tenant 身分即使受眾集合非空
# 也一律不可用（正本沒有 tenant 視圖）。直接組 `FacadeDeps`（`agent_runtime`／
# `agent_session_store` 皆非 None，⛔ 不經 app 啟動 fixture——baseline 受眾
# 失敗會在 preflight ① 短路），且帶合法 `api_key_id`／`vendor_id`／
# `session_id`、未觸頂的時速，否則 preflight ②③ 會以無關理由回
# `INVALID_INPUT`／`RATE_LIMITED`。
# ═══════════════════════════════════════════════════════════════════

_MISSING = object()  # 「屬性根本不存在」的哨兵——與 None／[]／frozenset() 三種 falsy 形狀分開


def _preflight_deps(audiences) -> F.FacadeDeps:
    state = types.SimpleNamespace(agent_runtime=object(), agent_session_store=_FakeEngine())
    if audiences is not _MISSING:
        state.agent_audiences = audiences
    app = types.SimpleNamespace(state=state)
    return F.FacadeDeps(get_db_pool=lambda: None, get_app=lambda: app)


@pytest.mark.parametrize(
    "shape_name, audiences_value",
    [
        ("attribute_absent", _MISSING),
        ("none", None),
        ("non_set_list", ["prospect"]),
        ("empty_frozenset", frozenset()),
    ],
)
def test_agent_turn_preflight_four_unavailable_shapes_of_agent_audiences(shape_name, audiences_value):
    F.reset_agent_turn_cap()
    deps = _preflight_deps(audiences_value)
    code = F._agent_turn_preflight(deps, PROSPECT)
    assert code == F.ERR_AGENT_UNAVAILABLE, (shape_name, code)


def test_agent_turn_preflight_positive_control_frozenset_with_prospect_is_available():
    """正對照：`frozenset({"prospect"})` ⇒ `None`（就緒）——證明上面四格紅
    不是量尺本身瞎了、preflight 永遠回 `ERR_AGENT_UNAVAILABLE`。"""
    F.reset_agent_turn_cap()
    deps = _preflight_deps(frozenset({"prospect"}))
    code = F._agent_turn_preflight(deps, PROSPECT)
    assert code is None, code


def test_agent_turn_preflight_tenant_is_unavailable_even_with_nonempty_audiences():
    """tenant 一行：正本沒有 tenant 視圖，即使 `agent_audiences` 非空（含
    prospect／pm）tenant 仍一律 `ERR_AGENT_UNAVAILABLE`。"""
    F.reset_agent_turn_cap()
    deps = _preflight_deps(frozenset({"prospect", "property_manager"}))
    code = F._agent_turn_preflight(deps, TENANT)
    assert code == F.ERR_AGENT_UNAVAILABLE, code
