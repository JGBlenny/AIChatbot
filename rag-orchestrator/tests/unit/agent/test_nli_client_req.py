"""unit：`services/agent/nli_client.py`（spec agentic-mcp-orchestration・DSP-033）。

覆蓋 r18 的四條處置，每一條的失敗方向都寫在測試的 docstring 裡：
- **F-4** 逾時只有一條公式（對數 × `NLI_PAIR_TIMEOUT_MS`），超過 `NLI_MAX_PAIRS` ⇒ `NliPairsCapped`
- **F-11** `len(scores) != len(pairs)` ⇒ `NliUnavailable`（⛔ 不靠 zip 截斷靜靜錯位配對）
- **F-12** 例外訊息 ⛔ 不含 request／response body
- **F-10** ⛔ 不快取可用性：每次呼叫都實打，失敗之後下一次仍然會打

⛔ **不觸網**：`httpx.AsyncClient` 一律以假物件替換（`monkeypatch`），
本檔沒有任何一條會真的解析 `nli-model` 這個主機名。
"""
from __future__ import annotations

import json

import pytest

from services.agent import nli_client as nli_mod
from services.agent.nli_client import (
    DEFAULT_MAX_PAIRS,
    DEFAULT_NLI_URL,
    DEFAULT_PAIR_TIMEOUT_MS,
    FakeNliClient,
    HttpNliClient,
    NliPair,
    NliPairsCapped,
    NliUnavailable,
    client_from_env,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------- 假 httpx

class _FakeResponse:
    def __init__(self, status_code=200, payload=None, raw=None):
        self.status_code = status_code
        self._payload = payload
        self._raw = raw

    def json(self):
        if self._raw is not None:
            raise ValueError("not json")
        return self._payload


class _FakeAsyncClient:
    """記下建構時的 `timeout` 與每一次請求；可設定固定回應或例外。"""

    instances: list = []

    def __init__(self, *, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.timeout = None
        self.requests: list = []

    def factory(self):
        outer = self

        class _Ctx:
            def __init__(self, *args, **kwargs):
                outer.timeout = kwargs.get("timeout")
                _FakeAsyncClient.instances.append(outer)

            async def __aenter__(self_inner):
                return self_inner

            async def __aexit__(self_inner, *exc_info):
                return False

            async def post(self_inner, url, json=None):
                outer.requests.append(("POST", url, json))
                if outer.exc is not None:
                    raise outer.exc
                return outer.response

            async def get(self_inner, url):
                outer.requests.append(("GET", url, None))
                if outer.exc is not None:
                    raise outer.exc
                return outer.response

        return _Ctx


def _install(monkeypatch, *, response=None, exc=None) -> _FakeAsyncClient:
    fake = _FakeAsyncClient(response=response, exc=exc)
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", fake.factory())
    return fake


def _pairs(n: int) -> list:
    return [NliPair(premise=f"前提{i}。", hypothesis=f"假設{i}。") for i in range(n)]


# ---------------------------------------------------------------- F-4 逾時公式

@pytest.mark.parametrize("n_pairs,expected_s", [(1, 0.4), (2, 0.8), (5, 2.0), (12, 4.8)])
def test_timeout_is_pairs_times_pair_budget(n_pairs, expected_s):
    """F-4：`逾時 = 句對數 × NLI_PAIR_TIMEOUT_MS`。⛔ 沒有第二個逾時常數。"""
    client = HttpNliClient("http://nli-model:8000", pair_timeout_ms=400)
    assert client.timeout_s(n_pairs) == pytest.approx(expected_s)


async def test_timeout_actually_reaches_httpx(monkeypatch):
    """正對照：公式算出來的值真的被交給 httpx——只驗 `timeout_s()` 等於
    只驗了一個沒人用的函式。"""
    fake = _install(monkeypatch, response=_FakeResponse(payload={
        "scores": [0.9, 0.8, 0.7], "model_sha": "s"}))
    client = HttpNliClient("http://nli-model:8000", pair_timeout_ms=250)
    await client.score(_pairs(3))
    assert fake.timeout == pytest.approx(0.75)


async def test_pairs_over_cap_raises_pairs_capped_without_any_request(monkeypatch):
    """F-4：超過 `NLI_MAX_PAIRS` ⇒ `NliPairsCapped`（`NliUnavailable` 的子類，
    呼叫端一律降級）。⛔ 不得先送出去再說——那正是要防的資源放大。"""
    fake = _install(monkeypatch, response=_FakeResponse(payload={
        "scores": [0.5, 0.5, 0.5], "model_sha": "s"}))
    client = HttpNliClient(max_pairs=3)
    with pytest.raises(NliPairsCapped):
        await client.score(_pairs(4))
    assert fake.requests == [], "超限仍然發了請求"
    assert issubclass(NliPairsCapped, NliUnavailable)

    # 正對照：剛好等於上限要送得出去，否則上面只是在說「什麼都送不出去」。
    assert await client.score(_pairs(3)) == [0.5, 0.5, 0.5]
    assert len(fake.requests) == 1


async def test_empty_pairs_makes_no_request(monkeypatch):
    fake = _install(monkeypatch, response=_FakeResponse(payload={"scores": []}))
    assert await HttpNliClient().score([]) == []
    assert fake.requests == []


# ---------------------------------------------------------------- F-11 長度不符

async def test_length_mismatch_raises_unavailable(monkeypatch):
    """F-11：配對靠**順序**，長度一旦不同就無從得知哪一格對應哪一對。
    🔴 拿錯位的分數去判 verdict 比沒有分數更糟——那會誤殺／漏放，而且看不出來。"""
    _install(monkeypatch, response=_FakeResponse(payload={"scores": [0.9], "model_sha": "s"}))
    with pytest.raises(NliUnavailable):
        await HttpNliClient().score(_pairs(2))


@pytest.mark.parametrize("payload", [
    {"scores": "not-a-list"},
    {"scores": None},
    {},
    ["not", "a", "dict"],
])
async def test_malformed_body_raises_unavailable(monkeypatch, payload):
    _install(monkeypatch, response=_FakeResponse(payload=payload))
    with pytest.raises(NliUnavailable):
        await HttpNliClient().score(_pairs(1))


async def test_non_200_raises_unavailable(monkeypatch):
    _install(monkeypatch, response=_FakeResponse(status_code=503, payload={"error": "not_ready"}))
    with pytest.raises(NliUnavailable):
        await HttpNliClient().score(_pairs(1))


async def test_per_pair_error_becomes_none_not_a_failure(monkeypatch):
    """單一句對的錯誤（`hypothesis_too_long`）⇒ 那一格是 `None`，
    ⛔ **不是**整回合降級——降級是「這把尺換了」，一對算不出來只是那一對判拒。"""
    _install(monkeypatch, response=_FakeResponse(payload={
        "scores": [0.91, {"error": nli_mod.ERR_HYPOTHESIS_TOO_LONG}], "model_sha": "s"}))
    assert await HttpNliClient().score(_pairs(2)) == [0.91, None]


@pytest.mark.parametrize("raw,expected", [
    (0.5, 0.5), (1, 1.0), (0, 0.0),
    (1.5, None), (-0.1, None),          # 值域外 ⇒ 判拒，⛔ 不夾逼成 1.0／0.0
    (True, None), ("0.9", None), (None, None), ({"error": "x"}, None),
])
def test_score_coercion_fails_closed(raw, expected):
    """🔴 認不得的形狀一律 `None`（＝該對判拒）。
    ⛔ 不回一個猜出來的數字：格式漂移的失敗方向必須是拒絕，不是放行。"""
    assert nli_mod._coerce_score(raw) == expected


# ---------------------------------------------------------------- F-12 不 log body

async def test_exception_message_carries_no_body(monkeypatch):
    """F-12：`premise` 是知識庫原文、`hypothesis` 是要給使用者看的句子。
    例外訊息（會進 log／trace）⛔ 不得帶上它們，也不得帶回應內容。"""
    secret_premise = "租客張三的身分證字號是 A123456789。"
    secret_reply = "資料庫連線字串 postgres://user:pw@host/db"
    _install(monkeypatch, exc=RuntimeError(f"connect failed to {secret_reply}"))
    with pytest.raises(NliUnavailable) as ei:
        await HttpNliClient().score([NliPair(premise=secret_premise, hypothesis="假設。")])
    text = str(ei.value)
    assert secret_premise not in text
    assert secret_reply not in text
    assert text == "RuntimeError", "⛔ 只留型別名"


async def test_non_200_message_is_only_the_status_code(monkeypatch):
    secret = "知識庫原文不該出現在這裡"
    _install(monkeypatch, response=_FakeResponse(status_code=500, payload={"detail": secret}))
    with pytest.raises(NliUnavailable) as ei:
        await HttpNliClient().score([NliPair(premise=secret, hypothesis="h")])
    assert str(ei.value) == "http_500"
    assert secret not in str(ei.value)


async def test_client_logs_nothing_at_all_on_failure(monkeypatch, caplog):
    """⛔ 本模組不 log：任何一行 log 都是一個新的原文出口。
    降級這件事由 Runtime 記進 `TurnTrace.violations`（結構化、無原文）。"""
    import logging

    _install(monkeypatch, exc=RuntimeError("boom 租客原文"))
    with caplog.at_level(logging.DEBUG, logger="services.agent.nli_client"):
        with pytest.raises(NliUnavailable):
            await HttpNliClient().score([NliPair(premise="租客原文", hypothesis="h")])
    assert caplog.records == []


# ---------------------------------------------------------------- F-10 不快取可用性

async def test_availability_is_not_cached_next_call_retries(monkeypatch):
    """F-10：⛔ 不快取可用性。一次失敗之後，下一回合**照樣實打**。

    ⚠️ 快取「服務掛了」會讓一次瞬斷變成一段時間的全域降級，而降級期間跑的是
    比較鬆的那把尺——把放行率的漂移藏進一個沒人看的旗標裡。
    """
    client = HttpNliClient()
    failing = _install(monkeypatch, exc=RuntimeError("down"))
    with pytest.raises(NliUnavailable):
        await client.score(_pairs(1))
    assert len(failing.requests) == 1

    ok = _install(monkeypatch, response=_FakeResponse(payload={
        "scores": [0.77], "model_sha": "sha-after-recovery"}))
    assert await client.score(_pairs(1)) == [0.77]
    assert len(ok.requests) == 1, "第二次沒有實打——可用性被快取了"
    assert client.last_model_sha == "sha-after-recovery"


def test_client_holds_no_availability_state():
    """正對照：實例上沒有任何看起來像「服務狀態快取」的欄位。
    ⛔ 不是靠註解宣稱不快取，而是釘住它連放的地方都沒有。"""
    client = HttpNliClient()
    assert set(vars(client)) == {"url", "pair_timeout_ms", "max_pairs", "last_model_sha"}


# ---------------------------------------------------------------- /health 透傳

async def test_health_passthrough_shape(monkeypatch):
    _install(monkeypatch, response=_FakeResponse(payload={
        "nli_ready": True, "model_sha": "a" * 64, "canary_ok": True}))
    info = await HttpNliClient().health()
    assert info == {"nli_ready": True, "model_sha": "a" * 64, "canary_ok": True}


@pytest.mark.parametrize("kwargs", [
    {"exc": RuntimeError("down")},
    {"response": _FakeResponse(status_code=503, payload={"error": "x"})},
    {"response": _FakeResponse(raw="<html>")},
    {"response": _FakeResponse(payload=["not", "a", "dict"])},
])
async def test_health_returns_none_when_unreachable(monkeypatch, kwargs):
    """🔴 探不到一律 `None`＝**不 ready**，⛔ 不回一個「大概沒事」的字典——
    健檢那一端會把 `None` 判成紅（agent health 紅），這是刻意的 fail-loud。"""
    _install(monkeypatch, **kwargs)
    assert await HttpNliClient().health() is None


async def test_health_timeout_reuses_the_same_formula(monkeypatch):
    """⛔ 不另立健檢逾時常數：用同一條公式的「一對句子」預算。"""
    fake = _install(monkeypatch, response=_FakeResponse(payload={
        "nli_ready": True, "model_sha": "x", "canary_ok": True}))
    await HttpNliClient(pair_timeout_ms=300).health()
    assert fake.timeout == pytest.approx(0.3)


# ---------------------------------------------------------------- 請求形狀

async def test_request_body_is_the_pairs_array(monkeypatch):
    fake = _install(monkeypatch, response=_FakeResponse(payload={
        "scores": [0.1, 0.2], "model_sha": "s"}))
    await HttpNliClient("http://nli-model:8000/").score([
        NliPair(premise="p1", hypothesis="h1"),
        NliPair(premise="p2", hypothesis="h2"),
    ])
    method, url, body = fake.requests[0]
    assert method == "POST"
    assert url == "http://nli-model:8000/nli", "尾斜線要被 rstrip，⛔ 不得變成 //nli"
    assert body == {"pairs": [
        {"premise": "p1", "hypothesis": "h1"},
        {"premise": "p2", "hypothesis": "h2"},
    ]}
    # 送出去的 JSON 只有這兩個鍵——⛔ 不夾帶 identity／session／vendor 任何一格
    assert set(json.loads(json.dumps(body))["pairs"][0]) == {"premise", "hypothesis"}


# ---------------------------------------------------------------- env 組裝

def test_client_from_env_defaults(monkeypatch):
    for key in ("NLI_URL", "NLI_PAIR_TIMEOUT_MS", "NLI_MAX_PAIRS"):
        monkeypatch.delenv(key, raising=False)
    client = client_from_env()
    assert client.url == DEFAULT_NLI_URL
    assert client.pair_timeout_ms == DEFAULT_PAIR_TIMEOUT_MS == 400
    assert client.max_pairs == DEFAULT_MAX_PAIRS == 12


@pytest.mark.parametrize("bad", ["abc", "0", "-5", ""])
def test_client_from_env_bad_values_fall_back_and_do_not_raise(monkeypatch, bad):
    """壞值退回預設，⛔ 不讓啟動炸——NLI 不可用只該降級，
    不該讓整個 agent 起不來（DSP-033 可用性）。"""
    monkeypatch.setenv("NLI_MAX_PAIRS", bad)
    monkeypatch.setenv("NLI_PAIR_TIMEOUT_MS", bad)
    client = client_from_env()
    assert client.max_pairs == DEFAULT_MAX_PAIRS
    assert client.pair_timeout_ms == DEFAULT_PAIR_TIMEOUT_MS


def test_client_from_env_reads_overrides(monkeypatch):
    monkeypatch.setenv("NLI_URL", "http://elsewhere:9000")
    monkeypatch.setenv("NLI_PAIR_TIMEOUT_MS", "250")
    monkeypatch.setenv("NLI_MAX_PAIRS", "6")
    client = client_from_env()
    assert (client.url, client.pair_timeout_ms, client.max_pairs) == (
        "http://elsewhere:9000", 250, 6)


# ---------------------------------------------------------------- 假 client 的邊界

def test_http_client_has_no_sync_entry_point():
    """P1-2：`OutputVerifier.self_test` 走的是 `score_sync`，而 `HttpNliClient`
    刻意**沒有**這支方法——所以「啟動自證誤打真服務」在型別上就不成立。

    正對照：`FakeNliClient` 有這支，否則本條只是在說「兩個都沒有」。"""
    assert not hasattr(HttpNliClient(), "score_sync")
    assert hasattr(FakeNliClient(scores=[0.5]), "score_sync")


def test_fake_client_requires_exactly_one_driver():
    with pytest.raises(ValueError):
        FakeNliClient()
    with pytest.raises(ValueError):
        FakeNliClient(scores=[0.5], fn=lambda p: 0.5)


async def test_fake_client_sync_and_async_agree():
    fake = FakeNliClient(fn=lambda p: 0.42)
    pairs = _pairs(2)
    assert fake.score_sync(pairs) == await fake.score(pairs) == [0.42, 0.42]
