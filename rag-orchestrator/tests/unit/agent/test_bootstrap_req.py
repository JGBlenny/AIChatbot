"""unit：`services.agent.bootstrap.build_runtime`（spec agentic-mcp-orchestration
任務 2.5）。

覆蓋：
- 正常路徑：真規則檔＋真 fixtures ⇒ 組出 `AgentRuntime`，且 `rules_sha`／
  `outline_sha` 被掛在回傳物件上（暴露給 health 用，見任務 brief）。
- 自證失敗（壞 fixture：`known_fabrications.json` 裡放一個實際會被判 `ok=True`
  的案例）⇒ `build_runtime` 直接 raise（啟動紅，⛔ 不吞例外續跑）。
- `outline_doc` 給了就把它的 `sha256` 帶到 `runtime.outline_sha`；不給則空字串。

全部離線：不呼叫真 OpenAI、不接觸真 DB（`db_pool` 只是原樣收下的參數）。
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.agent.bootstrap import DEFAULT_FIXTURES_DIR, DEFAULT_RULES_PATH, build_runtime
from services.agent.nli_client import FakeNliClient, HttpNliClient
from services.agent.runtime import AgentRuntime

pytestmark = pytest.mark.unit


def _fake_provider():
    return SimpleNamespace(async_client=SimpleNamespace(chat=SimpleNamespace(completions=None)))


def _fake_registry():
    return SimpleNamespace()


# ---------------------------------------------------------------------------
# 1. 正常路徑
# ---------------------------------------------------------------------------


def test_build_runtime_with_real_rules_and_fixtures_succeeds():
    runtime = build_runtime(None, _fake_provider(), _fake_registry())

    assert isinstance(runtime, AgentRuntime)
    assert isinstance(runtime.rules_sha, str) and runtime.rules_sha
    assert runtime.outline_sha == ""  # 沒給 outline_doc


def test_build_runtime_exposes_outline_sha_when_outline_doc_given():
    outline_doc = SimpleNamespace(sha256="outline-sha-abc")
    runtime = build_runtime(None, _fake_provider(), _fake_registry(), outline_doc=outline_doc)

    assert runtime.outline_sha == "outline-sha-abc"


def test_build_runtime_passes_through_runtime_kwargs():
    runtime = build_runtime(
        None, _fake_provider(), _fake_registry(), readonly_view=True, stage="M0"
    )
    assert runtime.readonly_view is True


def test_build_runtime_default_does_not_set_attempt_sink():
    """tasks 4.3c：正式路徑 ⛔ 不設 `attempt_sink`——它是
    `tools/agent_eval.py --dump-texts` 專用的離線儀表化旁路，`build_runtime`
    不傳這個 kwarg 時 `AgentRuntime` 必須落在自己的預設值 `None`。"""
    runtime = build_runtime(None, _fake_provider(), _fake_registry())
    assert runtime._attempt_sink is None


# ---------------------------------------------------------------------------
# 2. 自證失敗 ⇒ raise（壞 fixture）
# ---------------------------------------------------------------------------

#: 一個實際上會被 `OutputVerifier.verify` 判 `ok=True` 的案例（純問候句、
#: 無事實斷言、不需要 citation）——刻意放進 `known_fabrications.json`
#: （原本該全拒），製造「自證與規則集對不上」的情境。
_WRONGLY_PASSING_CASE = {
    "id": "bad_fixture_actually_passes",
    "note": "壞 fixture：這其實是個乾淨的問候句，會被判 ok=True，"
    "放進 known_fabrications.json 應該讓 self_test 失敗",
    "user_message": "你好",
    "agent_output": {
        "kind": "answer",
        "sentences": [{"text": "您好", "kind": "greeting", "refs": []}],
        "fact_class": "feature",
        "handoff_reason": None,
    },
    "tool_results": {},
    "handoff": None,
}

_TRIVIAL_GOOD_CASE = {
    "id": "trivial_good",
    "note": "known_good.json 佔位——self_test 會先跑 known_fabrications.json，"
    "本檔案案例在壞 fixture 測試裡不會被讀到",
    "user_message": "你好",
    "agent_output": {
        "kind": "answer",
        "sentences": [{"text": "您好", "kind": "greeting", "refs": []}],
        "fact_class": "feature",
        "handoff_reason": None,
    },
    "tool_results": {},
    "handoff": None,
}


def test_build_runtime_raises_when_self_test_fixtures_mismatch_rules(tmp_path: Path):
    fixtures_dir = tmp_path / "agent_fixtures"
    fixtures_dir.mkdir()
    (fixtures_dir / "known_fabrications.json").write_text(
        json.dumps([_WRONGLY_PASSING_CASE], ensure_ascii=False), encoding="utf-8"
    )
    (fixtures_dir / "known_good.json").write_text(
        json.dumps([_TRIVIAL_GOOD_CASE], ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(RuntimeError, match="self_test 失敗"):
        build_runtime(
            None,
            _fake_provider(),
            _fake_registry(),
            fixtures_dir=fixtures_dir,
        )


def test_build_runtime_raises_when_rules_path_missing(tmp_path: Path):
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(FileNotFoundError):
        build_runtime(None, _fake_provider(), _fake_registry(), rules_path=missing)


# ---------------------------------------------------------------------------
# 3. 預設路徑真的指到 repo 內的檔案（正對照——路徑本身沒有算錯目錄）
# ---------------------------------------------------------------------------


def test_default_paths_point_at_real_repo_files():
    assert DEFAULT_RULES_PATH.exists(), f"{DEFAULT_RULES_PATH} 不存在——路徑算錯了"
    assert (DEFAULT_FIXTURES_DIR / "known_fabrications.json").exists()
    assert (DEFAULT_FIXTURES_DIR / "known_good.json").exists()


@pytest.mark.unit
def test_budget_from_env_reads_three_keys_and_falls_back(monkeypatch):
    from services.agent.bootstrap import budget_from_env
    monkeypatch.delenv("AGENT_BUDGET_TOOL_CALLS", raising=False)
    monkeypatch.delenv("AGENT_BUDGET_REWRITES", raising=False)
    monkeypatch.delenv("AGENT_BUDGET_DEADLINE_S", raising=False)
    d = budget_from_env()
    assert (d.max_tool_calls, d.max_rewrites, d.deadline_s) == (4, 2, 20.0)
    monkeypatch.setenv("AGENT_BUDGET_TOOL_CALLS", "6")
    monkeypatch.setenv("AGENT_BUDGET_REWRITES", "abc")      # 壞值 ⇒ 預設
    monkeypatch.setenv("AGENT_BUDGET_DEADLINE_S", "-3")     # 越界 ⇒ 預設
    e = budget_from_env()
    assert (e.max_tool_calls, e.max_rewrites, e.deadline_s) == (6, 2, 20.0)


# ---------------------------------------------------------------------------
# DSP-033：NLI client 的必填注入與啟動不依賴 `/nli`
# ---------------------------------------------------------------------------


def test_output_verifier_requires_an_explicit_nli_client():
    """P1-2：`OutputVerifier` 的 `nli_client` 是**必填關鍵字參數、⛔ 無隱式預設**。

    ⚠️ 給預設值就會出現「忘了注入 ⇒ 步③靜靜退回舊尺」這條路徑，而那個失敗方向
    是**放行**（舊尺抓到 62% vs 新尺 69%），且沒有任何徵兆。降級是要被記進 trace、
    被 health 告警的事件，⛔ 不可以是建構子少寫一個參數就達成的預設狀態。
    """
    from services.agent.output_schema import VerifierRules
    from services.agent.verifier import OutputVerifier

    rules = VerifierRules.load(DEFAULT_RULES_PATH)
    with pytest.raises(TypeError):
        OutputVerifier(rules)
    # 正對照：帶了就建得起來（否則上面只是在說「這個建構子永遠會炸」）
    OutputVerifier(rules, nli_client=FakeNliClient(scores=[]))


def test_build_runtime_builds_an_http_client_from_env_by_default(monkeypatch):
    """未給 `nli_client` ⇒ 由 env 建 `HttpNliClient`，並外掛到 runtime 供 health 讀。

    ⚠️ health 拿得到的只有 `app.state.agent_runtime`；⛔ 不讓它去
    `runtime.verifier._nli` 挖——那會把 Verifier 的私有欄位變成 health 的公開契約。
    """
    monkeypatch.setenv("NLI_URL", "http://nli-model:8000")
    monkeypatch.setenv("NLI_MAX_PAIRS", "12")
    runtime = build_runtime(None, _fake_provider(), _fake_registry())
    assert isinstance(runtime.nli_client, HttpNliClient)
    assert runtime.nli_client.url == "http://nli-model:8000"
    assert runtime.nli_client.max_pairs == 12
    # τ 也外掛（health 回報用）；值來自規則集，⛔ 不是另一個 env
    assert runtime.nli_tau == 0.40


def test_build_runtime_accepts_an_injected_client():
    """測試與離線工具**必須**顯式傳假 client——不傳就是真的 HTTP client，
    單元測試會去解析 `nli-model` 這個主機名（觸網）。"""
    fake = FakeNliClient(fn=lambda pair: 1.0)
    runtime = build_runtime(None, _fake_provider(), _fake_registry(), nli_client=fake)
    assert runtime.nli_client is fake
    assert runtime.verifier._nli is fake


def test_startup_self_test_never_touches_the_injected_client():
    """P1-2：啟動 ⛔ 不依賴 `/nli` 可用——`self_test` 用的是它自己內建的兩組假 client。

    反證：注入一個「一被呼叫就炸」的 client，`build_runtime` 仍須成功。
    正對照：同一個 client 被 Verifier 拿去用時確實會炸（否則這條只是在說
    「這個 client 根本不會炸」）。
    """
    class _Exploding:
        last_model_sha = ""

        def score_sync(self, pairs):
            raise AssertionError("啟動自證打了真服務——P1-2 被違反")

        async def score(self, pairs):
            raise AssertionError("啟動自證打了真服務——P1-2 被違反")

    runtime = build_runtime(None, _fake_provider(), _fake_registry(), nli_client=_Exploding())
    assert runtime.nli_client.__class__.__name__ == "_Exploding"
    with pytest.raises(AssertionError):
        _Exploding().score_sync([])


def test_self_test_runs_both_rulers_at_startup():
    """DSP-033：啟動自證跑 NLI 與降級兩種模式（`SELF_TEST_MODES`）。

    ⚠️ 只驗一種等於只證明了一半：降級尺是服務掛掉時**真的會生效**的那把尺，
    它若在某次重構裡壞掉，症狀只會在下一次 NLI 中斷時出現。
    """
    from services.agent.verifier import OutputVerifier

    assert OutputVerifier.SELF_TEST_MODES == ("nli", "degraded")
    runtime = build_runtime(None, _fake_provider(), _fake_registry(),
                            nli_client=FakeNliClient(scores=[]))
    assert runtime.verifier.SELF_TEST_MODES == ("nli", "degraded")
