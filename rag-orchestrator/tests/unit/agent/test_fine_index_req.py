"""unit：細目索引 `FineIndex`（spec knowledge-outline-and-intent-architecture 任務 3.3a）。

Plan `inputs/plan-3.3-fine-index-selector-20260907.md` §4「3.3a」1–5。

⚠️ 本檔**不碰版控正本**（`rag-orchestrator/canon/*`）——所有情境都用合成正本（`parse_canon_text`），
正本的真實講法是（去識別後的）真流量，⛔ 不拿它當測試材料。
⚠️ 隱私那條測試的正對照組（先證明 `caplog`／`capsys` 兩個擷取器都活著）**⛔ 不得刪**：
沒有它，「沒抓到任何文字」可能只是量尺壞了。
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging

import pytest

from services.agent.canon import fine_index as FI
from services.agent.canon.canon_parser import parse_canon_text
from services.agent.canon.fine_index import (
    MAX_BATCH,
    EmbeddingUtilsBackend,
    FineIndex,
    get_index,
    register_index,
    reset_index_registry,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:3.3"),
]

# ── 合成材料 ────────────────────────────────────────────────────────────
# 標題／講法都塞了唯一可搜尋的標記字串（`ZZTITLE*`／`ZZPHRASE*`），隱私測試就靠它們判外洩。

_FRONT_MATTER = """---
audience: prospect
version: 2026-09-07.test
reviewers: [test]
language: zh-TW
budget_tokens: 12000
target_user: [prospect]
business_types: [system_provider]
---
## 合成粗目 {#A}
"""

_TITLES = ("標題甲ZZTITLEA", "標題乙ZZTITLEB", "標題丙ZZTITLEC")


def _fine_block(slug: str, title: str, phrasings: list[tuple[str, str]]) -> str:
    lines = [f"### {title} {{#prospect/A/{slug}}}", "- phrasings:"]
    for text, status in phrasings:
        lines.append(f'  - {{text: "{text}", source: "question_summary:1", status: {status}}}')
    lines += [
        "- sources: [kb:1]",
        "- reviewed: {by: test, at: 2026-09-07}",
        "- instance_applicability: general",
        f"內容句{slug}",
        "",
    ]
    return "\n".join(lines)


def _doc_three_statuses():
    """3 細目，每細目 approved／proposed／retired 講法各一 ⇒ 鍵數＝3 標題＋3 approved＝6。"""
    body = "".join(
        _fine_block(
            f"fine-{i}",
            _TITLES[i],
            [
                (f"講法核可ZZPHRASEOK{i}", "approved"),
                (f"講法提案ZZPHRASEPROPOSED{i}", "proposed"),
                (f"講法退役ZZPHRASERETIRED{i}", "retired"),
            ],
        )
        for i in range(3)
    )
    return parse_canon_text(_FRONT_MATTER + body)


def _doc_twelve_keys():
    """3 細目 × (1 標題＋3 approved 講法)＝12 鍵 ⇒ 必然要分 2 批以上（≥9，§4.1）。"""
    body = "".join(
        _fine_block(
            f"fine-{i}",
            _TITLES[i],
            [(f"講法核可ZZPHRASEOK{i}{j}", "approved") for j in range(3)],
        )
        for i in range(3)
    )
    return parse_canon_text(_FRONT_MATTER + body)


def _secret_texts(doc) -> list[str]:
    """這份合成正本裡「⛔ 不得外洩」的全部文字：細目標題＋所有講法（含未進索引的）。"""
    out = []
    for fine in doc.fines():
        out.append(fine.title)
        out.extend(p.text for p in fine.phrasings)
    return out


def _vector_for(text: str, dim: int = 4) -> list[float]:
    """決定性假向量（同文字必同向量，跨行程穩定）——⛔ 不用 `hash()`（有 PYTHONHASHSEED）。"""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [(digest[i] + 1) / 256.0 for i in range(dim)]


class _FakeBackend:
    """記錄每次呼叫筆數的假 embedding 後端（建構子注入，樣式同 `_FakeEmbeddingClient`）。"""

    def __init__(self, *, none_for: tuple = (), raises: bool = False, override: dict = None):
        self.calls: list[int] = []
        self.texts: list[str] = []
        self._none_for = set(none_for)
        self._raises = raises
        self._override = override or {}

    def recover(self):
        """讓後端恢復正常（測「失敗不入快取、重試可復原」用）。"""
        self._none_for = set()
        self._raises = False

    async def embed(self, texts):
        self.calls.append(len(texts))
        self.texts.extend(texts)
        if self._raises:
            raise RuntimeError("後端故障（測試用）")
        out = []
        for t in texts:
            if t in self._none_for:
                out.append(None)
            elif t in self._override:
                out.append(self._override[t])
            else:
                out.append(_vector_for(t))
        return out


def _snapshot(index: FineIndex) -> str:
    """索引的決定性序列化（比較「兩次 prepare 逐位元相同」用）。"""
    return json.dumps(
        [[fid, [[kind, list(vec)] for kind, vec in index.entries_for(fid)]] for fid in index.fine_ids],
        ensure_ascii=False, sort_keys=True,
    )


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_index_registry()
    yield
    reset_index_registry()


# ══════════════════════════════════════════════════════════════════════
# §4.1 鍵集合、分批、決定性
# ══════════════════════════════════════════════════════════════════════

async def test_keys_are_titles_plus_approved_phrasings_only():
    """鍵數＝細目數＋approved 講法數；proposed／retired ⛔ 不進索引。"""
    doc = _doc_three_statuses()
    backend = _FakeBackend()
    index = FineIndex(backend)
    await index.prepare(doc)

    assert index.state == "ready"
    assert index.entry_count == 6, index.entry_count          # 3 標題 ＋ 3 approved
    assert index.dim == 4
    for fine in doc.fines():
        kinds = [kind for kind, _v in index.entries_for(fine.id)]
        assert kinds == ["title", "phrasing"], (fine.id, kinds)
    # 正對照：proposed／retired 的文字**確實存在於正本**，只是沒被送去 embed
    assert any(p.status == "proposed" for f in doc.fines() for p in f.phrasings)
    embedded = set(backend.texts)
    for fine in doc.fines():
        for phrasing in fine.phrasings:
            assert (phrasing.text in embedded) is (phrasing.status == "approved"), phrasing


async def test_backend_is_called_in_batches_of_at_most_eight():
    """§4.1：假後端記錄每次呼叫長度 ⇒ 最大 ≤8，且 12 鍵必然拆成 ≥2 批。"""
    doc = _doc_twelve_keys()
    backend = _FakeBackend()
    index = FineIndex(backend)
    await index.prepare(doc)

    assert index.entry_count == 12
    assert sum(backend.calls) == 12
    assert len(backend.calls) >= 2, backend.calls
    assert max(backend.calls) <= MAX_BATCH == 8, backend.calls


async def test_batch_ceiling_cannot_be_widened_by_constructor():
    """`batch` 是保護不是旋鈕：傳 100 仍以 `MAX_BATCH` 為上限（⛔ 不讓 189 條一次打爆 API）。"""
    doc = _doc_twelve_keys()
    backend = _FakeBackend()
    await FineIndex(backend, batch=100).prepare(doc)
    assert max(backend.calls) <= MAX_BATCH, backend.calls


async def test_prepare_is_deterministic_and_ordered_by_fine_then_phrasing():
    """同 doc＋同後端回值 ⇒ 索引逐位元相同；鍵順序＝細目序＋講法序。"""
    doc = _doc_twelve_keys()
    first, second = FineIndex(_FakeBackend()), FineIndex(_FakeBackend())
    await first.prepare(doc)
    await second.prepare(doc)

    assert _snapshot(first) == _snapshot(second)
    assert first.fine_ids == tuple(f.id for f in doc.fines())
    # 講法序：第一個細目的三個講法向量，順序須與正本相同
    approved = [p.text for p in doc.fines()[0].phrasings if p.status == "approved"]
    expected = [tuple(_normalized(_vector_for(t))) for t in approved]
    got = [vec for kind, vec in first.entries_for(doc.fines()[0].id) if kind == "phrasing"]
    assert got == expected


def _normalized(vec):
    norm = sum(v * v for v in vec) ** 0.5
    return [v / norm for v in vec]


async def test_vectors_are_l2_normalized():
    doc = _doc_three_statuses()
    index = FineIndex(_FakeBackend())
    await index.prepare(doc)
    for fid in index.fine_ids:
        for _kind, vec in index.entries_for(fid):
            assert abs(sum(v * v for v in vec) ** 0.5 - 1.0) < 1e-9


async def test_entries_for_never_exposes_internal_key_ids():
    """內部鍵 id（`title`／`ph:<sha8>`）⛔ 不出現在任何回傳值（F18：記 id＝可還原問句）。"""
    doc = _doc_twelve_keys()
    index = FineIndex(_FakeBackend())
    await index.prepare(doc)
    serialized = json.dumps(
        {fid: index.entries_for(fid) for fid in index.fine_ids}, ensure_ascii=False, default=list
    )
    assert "ph:" not in serialized
    # 正對照：內部確實有算出 `ph:` 形狀的鍵 id（不是因為根本沒實作才找不到）
    assert FI._phrasing_key_id("講法核可ZZPHRASEOK00").startswith("ph:")
    assert len(FI._phrasing_key_id("x")) == len("ph:") + 8


# ══════════════════════════════════════════════════════════════════════
# §4.2 三態
# ══════════════════════════════════════════════════════════════════════

def test_state_is_absent_before_any_prepare():
    index = FineIndex(_FakeBackend())
    assert index.state == "absent"
    assert index.prepared_key is None and index.prepared_sha is None
    assert index.entry_count == 0 and index.dim is None


async def test_ready_state_records_prepared_key():
    doc = _doc_three_statuses()
    index = FineIndex(_FakeBackend())
    await index.prepare(doc)
    assert index.state == "ready"
    assert index.prepared_key == (doc.canon_sha256, doc.phrasing_set_sha256)
    assert index.prepared_sha == doc.canon_sha256


async def test_single_none_vector_yields_not_ready_with_no_partial_index():
    """任一 `None` ⇒ `not_ready` 且**整份丟棄**（⛔ 不以殘缺集合服務）。"""
    doc = _doc_three_statuses()
    backend = _FakeBackend(none_for=(_TITLES[1],))
    index = FineIndex(backend)
    await index.prepare(doc)

    assert index.state == "not_ready"
    assert index.entry_count == 0
    assert index.prepared_key is None and index.prepared_sha is None and index.dim is None
    assert index.entries_for(doc.fines()[0].id) == []   # 先成功的那些也不留


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
async def test_nan_or_inf_vector_yields_not_ready(bad):
    doc = _doc_three_statuses()
    index = FineIndex(_FakeBackend(override={_TITLES[0]: [bad, 0.1, 0.1, 0.1]}))
    await index.prepare(doc)
    assert index.state == "not_ready" and index.entry_count == 0


async def test_zero_norm_vector_yields_not_ready():
    doc = _doc_three_statuses()
    index = FineIndex(_FakeBackend(override={_TITLES[0]: [0.0, 0.0, 0.0, 0.0]}))
    await index.prepare(doc)
    assert index.state == "not_ready" and index.entry_count == 0


async def test_dimension_mismatch_yields_not_ready():
    doc = _doc_three_statuses()
    index = FineIndex(_FakeBackend(override={_TITLES[1]: [0.1, 0.2]}))
    await index.prepare(doc)
    assert index.state == "not_ready" and index.entry_count == 0


async def test_backend_exception_yields_not_ready_without_raising():
    """後端 raise ⇒ `prepare` ⛔ 不 raise，落 `not_ready`。"""
    doc = _doc_three_statuses()
    index = FineIndex(_FakeBackend(raises=True))
    await index.prepare(doc)          # ⛔ 不得拋
    assert index.state == "not_ready" and index.entry_count == 0


async def test_backend_timeout_yields_not_ready():
    """後端 sleep 超過注入的小逾時 ⇒ 該批全 `None` ⇒ `not_ready`（預設後端的 `wait_for`）。"""

    class _SleepyClient:
        def __init__(self):
            self.calls = 0

        async def get_embeddings_batch(self, texts, verbose=False):
            self.calls += 1
            await asyncio.sleep(5)          # 遠大於下面注入的 0.05s
            return [[1.0] * 4 for _ in texts]   # pragma: no cover — 逾時後不會走到

    client = _SleepyClient()
    index = FineIndex(EmbeddingUtilsBackend(client=client, timeout_s=0.05))
    await index.prepare(_doc_three_statuses())

    assert index.state == "not_ready" and index.entry_count == 0
    assert client.calls >= 1, "後端根本沒被呼叫 ⇒ 這條測的不是逾時"


async def test_default_backend_chunks_and_forces_verbose_false():
    """預設後端：自行分批 ≤8、`verbose=False` 固定（既有 client 的 verbose 會 print 文字）。"""

    class _RecordingClient:
        def __init__(self):
            self.sizes = []
            self.verbose_flags = []

        async def get_embeddings_batch(self, texts, verbose=False):
            self.sizes.append(len(texts))
            self.verbose_flags.append(verbose)
            return [_vector_for(t) for t in texts]

    client = _RecordingClient()
    backend = EmbeddingUtilsBackend(client=client)
    out = await backend.embed([f"文字{i}" for i in range(20)])

    assert len(out) == 20 and all(v is not None for v in out)
    assert max(client.sizes) <= MAX_BATCH, client.sizes
    assert client.verbose_flags == [False] * len(client.sizes)


async def test_default_backend_returns_all_none_for_a_failing_batch():
    """預設後端：client 例外 ⇒ **該批**全 `None`，⛔ 不 raise 出去。"""

    class _AngryClient:
        async def get_embeddings_batch(self, texts, verbose=False):
            raise RuntimeError("embedding API 掛了（測試用）")

    out = await EmbeddingUtilsBackend(client=_AngryClient()).embed(["a", "b", "c"])
    assert out == [None, None, None]


# ══════════════════════════════════════════════════════════════════════
# §4.3 快取
# ══════════════════════════════════════════════════════════════════════

async def test_repeated_prepare_same_doc_does_not_call_backend_again():
    doc = _doc_three_statuses()
    backend = _FakeBackend()
    index = FineIndex(backend)

    await index.prepare(doc)
    calls_after_first = len(backend.calls)
    snapshot = _snapshot(index)

    await index.prepare(doc)
    assert len(backend.calls) == calls_after_first
    assert _snapshot(index) == snapshot
    assert index.state == "ready"


async def test_flipping_one_phrasing_status_changes_sha_and_rebuilds():
    """改一條講法狀態 ⇒ `canon_sha256` 變 ⇒ 重建（⛔ 不吃到舊索引）。"""
    doc = _doc_three_statuses()
    text = _FRONT_MATTER + "".join(
        _fine_block(
            f"fine-{i}",
            _TITLES[i],
            [
                (f"講法核可ZZPHRASEOK{i}", "approved"),
                # 原本 proposed 的這條翻成 approved
                (f"講法提案ZZPHRASEPROPOSED{i}", "approved" if i == 0 else "proposed"),
                (f"講法退役ZZPHRASERETIRED{i}", "retired"),
            ],
        )
        for i in range(3)
    )
    flipped = parse_canon_text(text)
    assert flipped.canon_sha256 != doc.canon_sha256
    assert flipped.phrasing_set_sha256 != doc.phrasing_set_sha256

    backend = _FakeBackend()
    index = FineIndex(backend)
    await index.prepare(doc)
    calls_after_first = len(backend.calls)

    await index.prepare(flipped)
    assert len(backend.calls) > calls_after_first, "sha 變了卻沒重建"
    assert index.entry_count == 7                       # 多了一條 approved
    assert index.prepared_sha == flipped.canon_sha256


async def test_failed_prepare_is_not_cached_so_a_retry_can_recover():
    """⚠️ **本片解讀**：快取只記成功那一次。

    把失敗也快取起來，會讓一次瞬時的 embedding 失敗永久釘死 `not_ready`、再跑 `prepare`
    也救不回來。`not_ready` 期間索引本來就不服務（3.3b `select` 回 `None`），
    允許重試 ⛔ 不放寬任何可見性或分數。
    """
    doc = _doc_three_statuses()
    backend = _FakeBackend(none_for=(_TITLES[0],))
    index = FineIndex(backend)
    await index.prepare(doc)
    assert index.state == "not_ready"
    calls_after_failure = len(backend.calls)

    backend.recover()                   # 同一份正本、後端恢復後再 prepare 一次
    await index.prepare(doc)
    assert len(backend.calls) > calls_after_failure, "失敗被快取了 ⇒ 後端根本沒再被呼叫"
    assert index.state == "ready" and index.entry_count == 6


# ══════════════════════════════════════════════════════════════════════
# 註冊點
# ══════════════════════════════════════════════════════════════════════

async def test_registry_round_trip_and_reset():
    index = FineIndex(_FakeBackend())
    assert get_index("prospect") is None
    register_index("prospect", index)
    assert get_index("prospect") is index
    reset_index_registry()
    assert get_index("prospect") is None


def test_register_index_rejects_unknown_audience():
    with pytest.raises(ValueError):
        register_index("landlord", FineIndex(_FakeBackend()))
    # 正對照：合法受眾確實收得下（不是每個值都被擋）
    register_index("tenant", FineIndex(_FakeBackend()))
    assert get_index("tenant") is not None


# ══════════════════════════════════════════════════════════════════════
# §4.4 health：三態都經 `register_index` 構造，且 ⛔ 不致紅
# ══════════════════════════════════════════════════════════════════════

async def _health():
    from services.agent import mcp_facade as F
    from services.agent.health import compute_agent_health

    registry = F.build_registry(F.FacadeDeps(
        get_db_pool=lambda: None, get_kb_pool=lambda: None, get_retriever=None))
    return await compute_agent_health(registry=registry, get_kb_pool=None, stage="M0")


async def test_health_reports_three_index_states_and_never_turns_red():
    """三態各一案＋未註冊 ⇒ health 都印得出來，且 `status`／`red_flags` **完全不受影響**。

    ⚠️ 這裡用**差分**斷言而不是「status == ok」：本測試沒有 kb pool，baseline 本來就紅；
    要證的是「索引狀態 ⛔ 不參與致紅判定」，不是「這台機器現在是綠的」。
    """
    baseline = await _health()

    doc = _doc_three_statuses()
    ready = FineIndex(_FakeBackend())
    await ready.prepare(doc)
    not_ready = FineIndex(_FakeBackend(raises=True))
    await not_ready.prepare(doc)
    absent = FineIndex(_FakeBackend())

    register_index("prospect", ready)
    register_index("property_manager", not_ready)
    register_index("tenant", absent)

    result = await _health()
    idx = result["checks"]["canon"]["index"]

    assert idx["prospect"] == {
        "state": "ready", "prepared_sha": doc.canon_sha256, "entries": 6, "dim": 4,
    }
    assert idx["property_manager"]["state"] == "not_ready"
    assert idx["property_manager"]["prepared_sha"] is None
    assert idx["property_manager"]["entries"] == 0
    assert idx["tenant"]["state"] == "absent"

    # ⛔ 不致紅：三態註冊前後 status 與 red_flags 一模一樣
    assert result["status"] == baseline["status"]
    assert result["checks"]["premise"]["red_flags"] == baseline["checks"]["premise"]["red_flags"]
    # 既有 canon 欄位沒被覆蓋掉（正對照）
    assert "sha256" in result["checks"]["canon"] and "dir" in result["checks"]["canon"]


async def test_health_reports_absent_for_every_unregistered_audience():
    result = await _health()
    idx = result["checks"]["canon"]["index"]
    assert set(idx) == {"prospect", "property_manager", "tenant"}
    assert all(v["state"] == "absent" for v in idx.values()), idx


# ══════════════════════════════════════════════════════════════════════
# §4.5 隱私：caplog＋capsys 皆無任何細目標題／講法文字（含失敗路徑）
# ══════════════════════════════════════════════════════════════════════

async def test_no_title_or_phrasing_text_reaches_logs_or_stdout(caplog, capsys):
    """⚠️ 正對照組先跑：先證明 `caplog` 與 `capsys` **兩個擷取器都活著**。

    沒有這一步，「兩邊都乾淨」可能只是量尺壞了（既有 client 走 `print` 不走 `logging`，
    只看 `caplog` 會全綠地漏掉 stdout）。
    """
    caplog.set_level(logging.DEBUG)
    marker = "ZZCAPTUREPROBE"
    logging.getLogger("tests.fine_index.probe").warning(marker)
    print(marker)
    probe_out = capsys.readouterr()
    assert marker in caplog.text, "caplog 沒抓到標記 ⇒ 日誌擷取器壞了，下面的斷言不成立"
    assert marker in probe_out.out, "capsys 沒抓到標記 ⇒ stdout 擷取器壞了，下面的斷言不成立"

    doc = _doc_three_statuses()
    secrets = _secret_texts(doc)
    assert len(secrets) == 3 + 9    # 3 標題 ＋ 每細目 3 講法

    # ① 正常路徑
    await FineIndex(_FakeBackend()).prepare(doc)
    # ② 有 None 的失敗路徑
    await FineIndex(_FakeBackend(none_for=(_TITLES[0],))).prepare(doc)
    # ③ 後端 raise 的失敗路徑
    await FineIndex(_FakeBackend(raises=True)).prepare(doc)
    # ④ 預設後端 + 會爆的 client（例外訊息不得帶出文字）
    class _AngryClient:
        async def get_embeddings_batch(self, texts, verbose=False):
            raise RuntimeError("embedding API 掛了（測試用）")

    await FineIndex(EmbeddingUtilsBackend(client=_AngryClient())).prepare(doc)

    captured = capsys.readouterr()
    haystack = caplog.text + captured.out + captured.err
    leaked = [s for s in secrets if s in haystack]
    assert not leaked, f"文字外洩到 log／stdout：{leaked}"
    # 內部鍵 id 同樣不得外洩
    assert "ph:" not in haystack
