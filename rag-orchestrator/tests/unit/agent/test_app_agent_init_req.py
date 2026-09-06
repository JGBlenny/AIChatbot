"""unit：`app.py::_init_agent_runtime`（Plan `inputs/plan-m-d-runtime-wiring-
20260907.md` §2.4-7｜knowledge-outline-and-intent-architecture:4.1）。

覆蓋：真實 `build_prospect_outline`（讀 git 正本，離線、決定性）＋假 embedding
後端（⛔ 不打真 API）跑一次完整 `_init_agent_runtime`：
- 索引 ready 時，主 runtime 與 shadow factory 建出的 runtime 持有**同一個**
  `CandidateSelector`（`is`）。
- 後端永不回應 ⇒ 在（monkeypatch 縮短的）`PREPARE_TOTAL_TIMEOUT_S` 內返回、
  索引落在非 ready 狀態、啟動不 raise。
"""
from __future__ import annotations

import types

import pytest

from services.agent.canon.canon_assembler import reset_canon_registry
from services.agent.canon.fine_index import reset_index_registry

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:4.1"),
]


@pytest.fixture(autouse=True)
def _reset_registries():
    reset_canon_registry()
    reset_index_registry()
    yield
    reset_canon_registry()
    reset_index_registry()


def _fake_app():
    app = types.SimpleNamespace()
    app.state = types.SimpleNamespace()
    app.state.db_pool = None
    return app


class _AllOnesBackend:
    """假 embedding 後端：任何文字都給同一個 2 維向量 ⇒ `prepare` 必為 ready
    （⛔ 不打真 embedding API，離線、決定性）。"""

    async def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


class _NeverRespondingBackend:
    """假 embedding 後端：永不返回（模擬卡死的 embedding API）。"""

    async def embed(self, texts):
        import asyncio

        await asyncio.sleep(999)
        return [[1.0, 0.0] for _ in texts]  # pragma: no cover — 永遠跑不到這裡


async def test_index_ready_and_main_shadow_share_same_selector(monkeypatch):
    import app as app_module
    from services.agent.canon import fine_index as fine_index_mod
    import services.llm_provider as llm_provider_mod

    monkeypatch.setattr(fine_index_mod, "EmbeddingUtilsBackend", lambda: _AllOnesBackend())
    monkeypatch.setattr(
        llm_provider_mod, "get_llm_provider",
        lambda *a, **k: types.SimpleNamespace(async_client=None),
    )

    fake_app = _fake_app()
    await app_module._init_agent_runtime(fake_app)

    assert fake_app.state.agent_runtime is not None
    index = fine_index_mod.get_index("prospect")
    assert index is not None and index.state == "ready"

    main_selector = fake_app.state.agent_runtime._candidate_selector
    assert main_selector is not None

    shadow_runner = fake_app.state.shadow_runner
    assert shadow_runner is not None
    shadow_runtime = shadow_runner._runtime_factory(readonly_view=True)
    assert shadow_runtime._candidate_selector is main_selector


async def test_never_responding_backend_returns_within_shortened_timeout_and_never_raises(
    monkeypatch,
):
    import app as app_module
    from services.agent.canon import fine_index as fine_index_mod

    # Plan §2.4-7：縮短逾時測耗時上界（⛔ 不真的等 60 秒）——`app.py` 用
    # `from services.agent.canon.fine_index import PREPARE_TOTAL_TIMEOUT_S`
    # 呼叫期取值，monkeypatch 模組屬性即可生效。
    monkeypatch.setattr(fine_index_mod, "PREPARE_TOTAL_TIMEOUT_S", 0.2)
    monkeypatch.setattr(fine_index_mod, "EmbeddingUtilsBackend", lambda: _NeverRespondingBackend())
    import services.llm_provider as llm_provider_mod

    monkeypatch.setattr(
        llm_provider_mod, "get_llm_provider",
        lambda *a, **k: types.SimpleNamespace(async_client=None),
    )

    fake_app = _fake_app()
    clock = __import__("time").monotonic
    start = clock()
    await app_module._init_agent_runtime(fake_app)  # 啟動不 raise（正是本測試的斷言之一）
    elapsed = clock() - start

    assert elapsed < 5.0, f"耗時 {elapsed}s——沒有真的套用縮短後的逾時"
    index = fine_index_mod.get_index("prospect")
    assert index is not None
    assert index.state in {"absent", "not_ready"}
    # 啟動仍然建出 runtime（降級服務，⛔ 不掛啟動）。
    assert fake_app.state.agent_runtime is not None
