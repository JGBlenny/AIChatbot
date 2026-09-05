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
        "sentences": [{"text": "您好", "kind": "greeting", "cite": []}],
        "citations": [],
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
        "sentences": [{"text": "您好", "kind": "greeting", "cite": []}],
        "citations": [],
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
