"""S1-B：production entry 的 responsibility observation 契約。

⚠️ 本片的完成標準**不是**「R-29 開始執行」，而是
「已能穩定、可稽核地算出 R-29 winner，且對既有使用者路徑零 authority／execution 變化」。
"""
import asyncio

import pytest

from services import responsibility_telemetry as rt

pytestmark = pytest.mark.unit

QUERY = "我要查這張帳單的收據實際收了多少錢"

# 真實檢索觀測到的 pre-drop rows（2026-09-01，vendor_id=2／b2b／property_manager）
ROWS = [
    {"id": 4640, "vector_similarity": 0.739, "search_method": "vector", "keyword_boost": 1.2},
    {"id": 4657, "vector_similarity": 0.559, "search_method": "vector", "keyword_boost": 1.0},
    {"id": 3407, "vector_similarity": 0.619, "search_method": "vector", "keyword_boost": 1.2},
    {"id": 4637, "vector_similarity": 0.604, "search_method": "vector", "keyword_boost": 1.0},
]


class _FakeEmbeddingClient:
    async def get_embedding(self, text, verbose=False):
        return [0.01] * 1536


def _fake_batch_rerank(scores_by_rid):
    """⚠️ 必須回傳 **exact set**——少一個就違反 G17 契約，score_batch 會拋。"""
    def _fn(user_query, payload):
        return {rid: scores_by_rid.get(rid, 0.5) for rid in payload}
    return _fn


@pytest.fixture(autouse=True)
def _clean_cache():
    rt._CACHE.clear()
    yield
    rt._CACHE.clear()


@pytest.fixture()
def wired(monkeypatch):
    """接上真 artifact ＋ 決定性的 embedding／rerank 替身。"""
    monkeypatch.setenv(rt.ENV_FLAG, "true")
    monkeypatch.setattr("services.embedding_utils.get_embedding_client",
                        lambda *a, **k: _FakeEmbeddingClient())
    monkeypatch.setattr(rt, "_batch_rerank_fn",
                        lambda: _fake_batch_rerank({"R-29": 0.99, "R-31": 0.80}))


def _observe(rows, facet=None):
    return asyncio.get_event_loop().run_until_complete(
        rt.observe(rows, QUERY, committed_facet=facet))


# ── 主線：完整跑到 winner ────────────────────────────────────────────
def test_observation_runs_through_to_winner(wired):
    obs = _observe(ROWS, facet="billing_anomaly")
    assert obs["status"] == rt.STATUS_OK
    assert obs["pre_drop_row_ids"] == [4640, 4657, 3407, 4637]
    assert sorted(obs["nominated"]) == ["R-29", "R-31"]
    assert obs["winner"] == "R-29"
    assert obs["binding_available"] is True


def test_observation_declares_zero_authority(wired):
    """⛔ 零 authority handoff／零 session write 必須是**結構上可稽核的宣告**。"""
    obs = _observe(ROWS, facet="billing_anomaly")
    assert obs["session_write"] == 0
    assert obs["authority_handoff"].startswith("NONE")


def test_observe_never_calls_build_responsibility_session(wired, monkeypatch):
    """S1-B 的硬邊界：build_responsibility_session call count 必須為 0。"""
    calls = []
    import services.responsibility_session as rsess
    monkeypatch.setattr(rsess, "build_responsibility_session",
                        lambda *a, **k: calls.append(1))
    _observe(ROWS, facet="billing_anomaly")
    assert calls == [], "S1-B ⛔ 不得建立 responsibility session"


# ── 反控制 ①：4640 是 R-29 唯一提名證據 ──────────────────────────────
def test_removing_4640_removes_r29(wired):
    obs = _observe([r for r in ROWS if r["id"] != 4640], facet="billing_anomaly")
    assert "R-29" not in (obs["nominated"] or [])
    assert obs["winner"] != "R-29"


def test_facet_name_alone_cannot_reconstitute_r29(wired):
    """⚠️ 即使 committed facet 是 billing_anomaly，缺 4640 時也 ⛔ 不得長出 R-29
    ——這證明 S1-B 沒有偷偷建立 facet→responsibility 的 authority mapping。"""
    obs = _observe([r for r in ROWS if r["id"] != 4640], facet="billing_anomaly")
    assert "R-29" not in (obs["nominated"] or [])
    obs2 = _observe([], facet="billing_anomaly")
    assert obs2["status"] == rt.STATUS_NO_NOMINATION
    assert obs2["winner"] is None


# ── 反控制 ②：availability ⛔ 不得影響 semantic winner ────────────────
def test_masked_binding_availability_does_not_change_winner(wired, monkeypatch):
    """遮掉 R-29 的 binding availability，winner **仍必須是 R-29**。
    ⛔ 不得翻成 R-31——semantic authority 不受 runtime capability availability 影響。"""
    monkeypatch.setattr(rt, "binding_available", lambda rid: False)
    obs = _observe(ROWS, facet="billing_anomaly")
    assert obs["winner"] == "R-29", "availability 影響了 winner ⇒ 順序鐵則被違反"
    assert obs["binding_available"] is False


def test_winner_selected_before_availability_is_checked(wired, monkeypatch):
    """⛔ 不得先過濾成「有 binding 的責任」再選 winner。"""
    seen = []
    monkeypatch.setattr(rt, "binding_available",
                        lambda rid: seen.append(rid) or True)
    obs = _observe(ROWS, facet="billing_anomaly")
    assert seen == [obs["winner"]], "availability 被查了不只 winner ⇒ 疑似用於過濾候選"


# ── 失敗語義：ERROR ≠ 沒有 winner ────────────────────────────────────
def test_artifact_failure_is_error_not_no_nomination(wired, monkeypatch):
    def _boom():
        raise RuntimeError("artifact 壞了")
    monkeypatch.setattr(rt, "_artifacts", _boom)
    obs = _observe(ROWS, facet="billing_anomaly")
    assert obs["status"] == rt.STATUS_ERROR
    assert obs["status"] != rt.STATUS_NO_NOMINATION
    assert obs["winner"] is None
    assert "不等於" in obs["_semantics"]


def test_scorer_failure_is_error(wired, monkeypatch):
    monkeypatch.setattr(rt, "_batch_rerank_fn",
                        lambda: (_ for _ in ()).throw(RuntimeError("reranker down")))
    obs = _observe(ROWS, facet="billing_anomaly")
    assert obs["status"] == rt.STATUS_ERROR
    assert obs["winner"] is None


def test_partial_rerank_response_is_error_not_silent(wired, monkeypatch):
    """⚠️ exact-set 契約：漏回一個 id ⛔ 不得靜默降級為 vector-only。"""
    monkeypatch.setattr(rt, "_batch_rerank_fn",
                        lambda: (lambda q, payload: {"R-29": 0.99}))
    obs = _observe(ROWS, facet="billing_anomaly")
    assert obs["status"] == rt.STATUS_ERROR


def test_error_log_line_is_explicit(wired, monkeypatch):
    monkeypatch.setattr(rt, "_artifacts",
                        lambda: (_ for _ in ()).throw(RuntimeError("x")))
    line = rt.log_line(_observe(ROWS))
    assert "ERROR" in line and "非『無 winner』" in line


# ── 旗標 ────────────────────────────────────────────────────────────
def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv(rt.ENV_FLAG, raising=False)
    assert rt.enabled() is False
    assert _observe(ROWS)["status"] == rt.STATUS_DISABLED
    assert rt.log_line({"status": rt.STATUS_DISABLED}) is None
