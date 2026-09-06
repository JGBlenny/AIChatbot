"""細目索引（spec knowledge-outline-and-intent-architecture 元件 6・任務 3.3a／3.7）。

啟動時把每個細目的「標題向量＋**approved** 講法向量＋`content_units` 內文句向量」建成記憶體索引
（決定性、三態、**失敗不服務**）。本檔只交元件＋註冊點；`visible_subset`／`CandidateSelector`
（3.3b／3.7）與 runtime 接線（4.1）⛔ 不在此。

## 為什麼要另包一層 `EmbeddingBackend`
既有 `services/embedding_utils.py::EmbeddingClient`（⛔ 本片不改）有三個對啟動索引不安全的性質：
1. `get_embeddings_batch` 對**全部**文字一次 `asyncio.gather`——189 條講法會一次打爆 embedding API；
2. `httpx.AsyncClient(timeout=30.0)` 寫死在單次請求上，**整批沒有上限**；
3. `verbose=True` 會 `print(text[:50])`——講法就是（去識別後的）真流量問句，印出去等於外洩。

所以預設實作 `EmbeddingUtilsBackend` **只包不改**：自行分批 ≤`MAX_BATCH`、每批
`asyncio.wait_for(PREPARE_EMBED_TIMEOUT_S)`、`verbose=False` 固定、任何例外／逾時 ⇒ 該批全 `None`
（⛔ 不 raise 出 `prepare`）。
⚠️ **殘留風險（已知、刻意不修）**：`EmbeddingClient.get_embedding` 例外分支有一行無條件
`print(f"❌ Embedding API 呼叫失敗: {e}")`。那行印的是**例外**（httpx 的 URL／逾時），⛔ 不含
被 embed 的文字；要拿掉它得改 `embedding_utils.py`，不在本片範圍。

## 隱私（本檔的硬規則）
⛔ 本模組任何 `logging`／`print` **一律不得帶入細目標題、講法文字、內文句、查詢字串**——只准印數量與
狀態。內部鍵 id（`title`／`ph:<sha8>`／`ct:<sha8>`）是**內部**識別，⛔ 不出現在任何回傳值／trace
（F18：講法對照表就在 repo，記 id 等於一次查表就還原問句；內文句是正本答案本文，同待遇）。

## 三態與「不以殘缺集合服務」
- `absent`：從未 `prepare`。
- `not_ready`：任一向量 `None`／`NaN`／`inf`／零範數／維度不一致 ⇒ **整份丟棄**（⛔ 不留半份索引）。
- `ready`：全數成功；`prepared_key=(canon_sha256, phrasing_set_sha256)`、`prepared_sha=canon_sha256`。
`canon_sha256` 涵蓋整份 `.md`（講法狀態翻轉必變 sha），`phrasing_set_sha256` 在快取鍵中是冗餘但無害
（design 明列，保留）。

⚠️ **快取只記成功的那一次**（本片解讀，交 verifier／業主覆核）：Plan §1.2「同 key 重複 `prepare`
不重打 embedding」的目的是省 embedding 呼叫；把**失敗**也快取起來會讓一次瞬時的 embedding 失敗
永久釘死成 `not_ready`、無法靠再跑一次 `prepare` 復原。`not_ready` 期間索引本來就不服務
（3.3b `select` 對非 `ready` 一律回 `None`），允許重試 ⛔ 不放寬任何可見性或分數。
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import unicodedata
from typing import Literal, Optional, Protocol, Sequence, get_args

from services.agent.canon.canon_parser import CanonDoc
from services.agent.identity import Audience
from services.embedding_utils import get_embedding_client

logger = logging.getLogger(__name__)

#: 每批 embedding 的**硬上限**（Plan §1.1／tasks 3.3「每批 ≤8」）。⛔ 不因建構參數而放寬——
#: 這是對 embedding API 的保護，不是可調參數。
MAX_BATCH: int = 8
#: `EmbeddingUtilsBackend` 每批的逾時（Plan §1.1）。
PREPARE_EMBED_TIMEOUT_S: float = 30.0
#: 整份 `prepare(doc)` 的**硬上限**（任務 4.1／Plan §2.1-6，業主 2026-09-07 §5-5 裁 60.0）。
#: 呼叫端（`app.py::_init_agent_runtime`）用 `asyncio.wait_for(index.prepare(canon),
#: PREPARE_TOTAL_TIMEOUT_S)` 包住整次啟動索引；逾時取消協程、索引狀態停在 `absent`
#: （`prepare` 只在完成或 `_discard` 時改狀態，取消不留半份）。⛔ 不因建構參數而放寬。
PREPARE_TOTAL_TIMEOUT_S: float = 60.0

IndexState = Literal["absent", "not_ready", "ready"]
KeyKind = Literal["title", "phrasing", "content"]

#: 內部鍵 id（⛔ 不回傳、⛔ 不進 trace）。
TITLE_KEY_ID = "title"
PHRASING_KEY_PREFIX = "ph:"
PHRASING_KEY_SHA_CHARS = 8
#: 內文句鍵前綴（任務 3.7）：`content_units` 每句一鍵，id 產法與 `ph:` 同（NFKC → sha256 前 8 碼）。
CONTENT_KEY_PREFIX = "ct:"
CONTENT_KEY_SHA_CHARS = 8

#: 講法只有 `approved` 才進索引（proposed／retired 不進）。
INDEXED_PHRASING_STATUS = "approved"

#: `Audience` Literal 的字面集合——註冊點只接受這三個（比照 `canon_assembler.CANON_AUDIENCES`）。
INDEX_AUDIENCES: frozenset = frozenset(get_args(Audience))


class EmbeddingBackend(Protocol):
    """`FineIndex` 需要的唯一介面：一批文字 → 一批向量，失敗的那一格是 `None`。

    ⛔ 實作不得 raise（`FineIndex` 仍會防禦性地接住），⛔ 不得印出／記錄任何被 embed 的文字。
    """

    async def embed(self, texts: list[str]) -> list[Optional[list[float]]]:  # pragma: no cover - Protocol
        ...


class EmbeddingUtilsBackend:
    """`EmbeddingBackend` 的預設實作：包既有 `get_embedding_client()`，⛔ 不改它。

    Args:
        batch: 每批文字數；一律再與 `MAX_BATCH` 取小。
        timeout_s: 每批的 `asyncio.wait_for` 逾時。
        client: 測試用建構子注入（樣式同
            `tests/unit/conversational/test_s1b_responsibility_telemetry_req.py::_FakeEmbeddingClient`）；
            省略 ⇒ 第一次呼叫時才取單例（⛔ 不在 import／建構期建連線）。
    """

    def __init__(
        self,
        *,
        batch: int = MAX_BATCH,
        timeout_s: float = PREPARE_EMBED_TIMEOUT_S,
        client=None,
    ) -> None:
        self._batch = _clamp_batch(batch)
        self._timeout_s = float(timeout_s)
        self._client = client

    def _get_client(self):
        if self._client is None:
            self._client = get_embedding_client()
        return self._client

    async def embed(self, texts: list[str]) -> list[Optional[list[float]]]:
        out: list[Optional[list[float]]] = []
        for start in range(0, len(texts), self._batch):
            out.extend(await self._embed_chunk(texts[start:start + self._batch]))
        return out

    async def _embed_chunk(self, chunk: list[str]) -> list[Optional[list[float]]]:
        """任何例外／逾時 ⇒ 該批全 `None`。⛔ 不 raise、⛔ 不記錄任何文字（只記例外型別）。"""
        try:
            vectors = await asyncio.wait_for(
                self._get_client().get_embeddings_batch(chunk, verbose=False),
                self._timeout_s,
            )
        except Exception as exc:  # noqa: BLE001 — 啟動索引：任何失敗都退成「該批不可用」
            # ⚠️ CancelledError 是 BaseException，⛔ 不在此吞掉。
            logger.warning(
                "fine_index: embedding 批次失敗（%s，%d 筆）⇒ 該批視為不可用",
                type(exc).__name__, len(chunk),
            )
            return [None] * len(chunk)
        if not isinstance(vectors, (list, tuple)) or len(vectors) != len(chunk):
            logger.warning(
                "fine_index: embedding 批次回傳筆數不符（要 %d 筆）⇒ 該批視為不可用", len(chunk)
            )
            return [None] * len(chunk)
        return list(vectors)


def _clamp_batch(batch: int) -> int:
    return max(1, min(int(batch), MAX_BATCH))


def _hashed_key_id(prefix: str, text: str, sha_chars: int) -> str:
    """`<prefix><sha8>`（NFKC 後取 sha256 前 `sha_chars` 碼）。⛔ 只作內部識別，不回傳、不進 trace。"""
    normalized = unicodedata.normalize("NFKC", text)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"{prefix}{digest[:sha_chars]}"


def _phrasing_key_id(text: str) -> str:
    """內部鍵 id `ph:<sha8>`（NFKC 後取 sha256 前 8 碼）。⛔ 只作內部識別，不回傳、不進 trace。"""
    return _hashed_key_id(PHRASING_KEY_PREFIX, text, PHRASING_KEY_SHA_CHARS)


def _content_key_id(text: str) -> str:
    """內部鍵 id `ct:<sha8>`（NFKC 後取 sha256 前 8 碼，與 `_phrasing_key_id` 同法）。

    ⛔ 只作內部識別，不回傳、不進 trace（任務 3.7：內文句與講法同待遇）。
    """
    return _hashed_key_id(CONTENT_KEY_PREFIX, text, CONTENT_KEY_SHA_CHARS)


def _normalize(vector: Sequence[float], dim: Optional[int]) -> Optional[tuple[float, ...]]:
    """L2 正規化；不合格 ⇒ `None`（呼叫端據此整份丟棄）。

    不合格＝非序列／空／含非數值／`NaN`／`inf`／零範數／維度與前面的鍵不一致。
    """
    if isinstance(vector, (str, bytes)) or not isinstance(vector, (list, tuple)):
        return None
    if not vector:
        return None
    if dim is not None and len(vector) != dim:
        return None
    values: list[float] = []
    for item in vector:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            return None
        value = float(item)
        if not math.isfinite(value):
            return None
        values.append(value)
    norm = math.sqrt(sum(v * v for v in values))
    if not math.isfinite(norm) or norm <= 0.0:
        return None
    return tuple(v / norm for v in values)


class FineIndex:
    """細目索引：`prepare(doc)` 後對每個細目給出「標題＋approved 講法＋內文句」的正規化向量。

    ⛔ 本類別不查 DB、不看身分、不算分數——可見性與 top-K 是 3.3b 的事。
    """

    def __init__(self, backend: EmbeddingBackend, *, batch: int = MAX_BATCH) -> None:
        self._backend = backend
        self._batch = _clamp_batch(batch)
        self._state: IndexState = "absent"
        self._prepared_key: Optional[tuple[str, str]] = None
        # 內部結構帶內部鍵 id（`title`／`ph:<sha8>`）——⛔ `entries_for` 不回傳它。
        self._entries: dict[str, tuple[tuple[KeyKind, str, tuple[float, ...]], ...]] = {}
        self._order: tuple[str, ...] = ()
        self._dim: Optional[int] = None

    # ── 讀取面（3.3b／health 只透過這些取值） ──────────────────────────

    @property
    def state(self) -> IndexState:
        return self._state

    @property
    def prepared_key(self) -> Optional[tuple[str, str]]:
        """`(canon_sha256, phrasing_set_sha256)`；非 `ready` ⇒ `None`。"""
        return self._prepared_key

    @property
    def prepared_sha(self) -> Optional[str]:
        """這份索引是對**哪一份正本**建的（3.3b `select` 首行比對用）；非 `ready` ⇒ `None`。"""
        return self._prepared_key[0] if self._prepared_key else None

    @property
    def dim(self) -> Optional[int]:
        return self._dim

    @property
    def backend(self) -> EmbeddingBackend:
        """建索引用的那個後端。

        `CandidateSelector` 的查詢向量**必須**與索引項出自同一個後端／同一個模型，
        否則兩邊的向量空間不同、餘弦分數毫無意義。⛔ 唯讀，不提供 setter——
        換後端要重建整份索引（`prepare` 才會重打 embedding）。
        """
        return self._backend

    @property
    def entry_count(self) -> int:
        return sum(len(v) for v in self._entries.values())

    @property
    def content_key_count(self) -> int:
        """`content` 鍵（`content_units` 每句一鍵）的總數；非 `ready` ⇒ 0（任務 3.7）。"""
        if self._state != "ready":
            return 0
        return sum(
            1 for entries in self._entries.values() for kind, _key_id, _vec in entries
            if kind == "content"
        )

    @property
    def fine_ids(self) -> tuple[str, ...]:
        """有索引項的細目 id，順序＝正本細目序。"""
        return self._order

    def entries_for(self, fine_id: str) -> list[tuple[KeyKind, tuple[float, ...]]]:
        """該細目的索引項 `[(key_kind, 已正規化向量), …]`，順序＝標題、再依講法序。

        ⛔ 回傳**不含**內部鍵 id；向量以 tuple 回傳（不可變，呼叫端改不到索引本體）。
        """
        return [(kind, vector) for kind, _key_id, vector in self._entries.get(fine_id, ())]

    def visible_subset(
        self, identity, doc: CanonDoc, *, vendor_business_types: frozenset[str]
    ) -> frozenset[str]:
        """這個身分看得到的細目 id 集合（任務 3.3b；Plan §1.5）。

        **薄集合包裝**：規則⛔ 一條都不在這裡——逐細目一律問 3.2 的
        `canon_assembler.canon_visible`（已與 `build_visibility_predicate` 驗過零分歧）。
        在這裡再寫一套判準，就會出現第二份可見性真相，⚠️ 兩份遲早走岔。

        ⚠️ **與索引本身無關**：不看 `self._entries`、不看 `state`、⛔ 不查 DB、⛔ 不打 embedding。
        掛在 `FineIndex` 上只是因為 `CandidateSelector` 的唯一相依是索引（Plan §1.5／1.6）；
        未 `prepare` 的索引照樣算得出正確的可見子集。

        ⚠️ `canon_assembler` 走**函式內 import**：它在模組層 import
        `VendorKnowledgeRetrieverV2`（psycopg2 ／ DB 棧）。本檔是啟動期索引，
        ⛔ 不在 import 時把 DB 棧拉進來（同 Plan §6「`register_index` 不 import
        `canon_assembler`」的理由；`canon_assembler` ↔ `outline` 也用同一招）。
        """
        from services.agent.canon.canon_assembler import canon_visible  # 見 docstring

        return frozenset(
            fine.id
            for fine in doc.fines()
            if canon_visible(identity, fine, vendor_business_types=vendor_business_types)
        )

    # ── 建置 ─────────────────────────────────────────────────────────

    async def prepare(self, doc: CanonDoc) -> None:
        """建索引。⛔ **不 raise**：任何失敗一律落成 `not_ready` 並丟棄整份索引。"""
        key = (doc.canon_sha256, doc.phrasing_set_sha256)
        if self._state == "ready" and self._prepared_key == key:
            return  # 快取：同一份正本已建好 ⇒ ⛔ 不重打 embedding

        plan = self._key_plan(doc)
        if not plan:
            # 沒有任何可索引的鍵（正本無細目）⇒ 沒有東西可服務，fail closed。
            self._discard("正本沒有任何可索引的鍵")
            return

        vectors = await self._embed_all([text for _fid, _kind, _kid, text in plan])
        if vectors is None:
            self._discard("embedding 後端不可用")
            return

        built: dict[str, list[tuple[KeyKind, str, tuple[float, ...]]]] = {}
        order: list[str] = []
        dim: Optional[int] = None
        for (fine_id, kind, key_id, _text), raw in zip(plan, vectors):
            normalized = _normalize(raw, dim) if raw is not None else None
            if normalized is None:
                # 任一格壞掉 ⇒ 整份丟棄（⛔ 不以殘缺集合服務）。
                self._discard("有向量缺漏或不合法")
                return
            dim = len(normalized)
            if fine_id not in built:
                built[fine_id] = []
                order.append(fine_id)
            built[fine_id].append((kind, key_id, normalized))

        self._entries = {fid: tuple(items) for fid, items in built.items()}
        self._order = tuple(order)
        self._dim = dim
        self._prepared_key = key
        self._state = "ready"
        logger.info(
            "fine_index: ready（細目 %d、索引項 %d、維度 %s）",
            len(self._order), self.entry_count, self._dim,
        )

    def _key_plan(self, doc: CanonDoc) -> list[tuple[str, KeyKind, str, str]]:
        """決定性鍵順序 `[(fine_id, kind, key_id, text), …]`：細目序 → 標題 → 講法序取 `approved`
        → `content_units` 每句一鍵（正本序，任務 3.7）。

        內部鍵 id（`title`／`ph:<sha8>`／`ct:<sha8>`）只在索引**內部**存在，⛔ 不出現在任何回傳值／trace。
        ⛔ 內文句不去重、不過濾：`content_units` 已由 parser 保證非空（F8 保證屬性區塊不落入其中）；
        跨細目或同細目內重複的句子各保留自己那把鍵（鍵 id 相同無妨，索引以位置存）。
        """
        plan: list[tuple[str, KeyKind, str, str]] = []
        for fine in doc.fines():
            plan.append((fine.id, "title", TITLE_KEY_ID, fine.title))
            for phrasing in fine.phrasings:
                if phrasing.status != INDEXED_PHRASING_STATUS:
                    continue
                plan.append((fine.id, "phrasing", _phrasing_key_id(phrasing.text), phrasing.text))
            for content_unit in fine.content_units:
                plan.append((fine.id, "content", _content_key_id(content_unit), content_unit))
        return plan

    async def _embed_all(self, texts: list[str]) -> Optional[list[Optional[list[float]]]]:
        """分批（≤`MAX_BATCH`）呼叫後端；後端 raise 或回傳筆數不符 ⇒ `None`（整份失敗）。"""
        out: list[Optional[list[float]]] = []
        for start in range(0, len(texts), self._batch):
            chunk = texts[start:start + self._batch]
            try:
                vectors = await self._backend.embed(list(chunk))
            except Exception as exc:  # noqa: BLE001 — 後端不該 raise，但 prepare ⛔ 不得因此炸掉
                logger.warning(
                    "fine_index: 後端 embed 丟例外（%s，%d 筆）⇒ 索引不可用",
                    type(exc).__name__, len(chunk),
                )
                return None
            if not isinstance(vectors, (list, tuple)) or len(vectors) != len(chunk):
                logger.warning("fine_index: 後端回傳筆數不符（要 %d 筆）⇒ 索引不可用", len(chunk))
                return None
            out.extend(vectors)
        return out

    def _discard(self, reason: str) -> None:
        """落成 `not_ready` 並丟棄整份索引。`reason` ⛔ 只准是固定字面，不得帶入任何正本文字。"""
        self._state = "not_ready"
        self._prepared_key = None
        self._entries = {}
        self._order = ()
        self._dim = None
        logger.warning("fine_index: not_ready（%s）", reason)


# ---------------------------------------------------------------------------
# 模組層註冊點（比照 `canon_assembler.register_canon`）
# ---------------------------------------------------------------------------

_INDEX_REGISTRY: dict = {}


def register_index(audience: str, index: FineIndex) -> None:
    """登記某受眾**這個行程實際使用的那份**索引（4.1 與 health 的唯一取用點）。"""
    if audience not in INDEX_AUDIENCES:
        raise ValueError(
            f"audience={audience!r} 不是 Audience 字面（合法值 {sorted(INDEX_AUDIENCES)}）"
        )
    _INDEX_REGISTRY[audience] = index


def get_index(audience: str) -> Optional[FineIndex]:
    """該受眾已註冊的索引；未註冊 ⇒ `None`。"""
    return _INDEX_REGISTRY.get(audience)


def reset_index_registry() -> None:
    """清空註冊表（測試隔離用；⛔ 產線不呼叫）。"""
    _INDEX_REGISTRY.clear()


def index_registry_states() -> dict:
    """health 用的觀測值：`{audience: {state, prepared_sha, entries, dim, content_keys}}`。

    三個受眾一律列出，未註冊 ⇒ `{"state": "absent", …}`（Plan §1.3「取不到 ⇒ absent」）。
    ⛔ 不重建索引、⛔ 不觸發任何 embedding；取值失敗只降級成 `absent`＋型別名。
    ⚠️ **4.1 接線後**：本函式的回傳值本身仍只是觀測值、⛔ 不重建——但
    `health.compute_agent_health` 在 `mcp_facade.agent_configured()` 為真時，
    會拿這裡的 `state` 去判紅（`absent`／`not_ready` ⇒ 紅）。3.3a／3.7 時期
    「不致紅」僅限**尚未接線**那段期間；接線後「索引不在」代表產線降級中，
    不再是「尚未建置」。
    """
    out: dict = {}
    for audience in sorted(INDEX_AUDIENCES):
        out[audience] = _observe(audience)
    return out


_ABSENT_STATE = {
    "state": "absent", "prepared_sha": None, "entries": 0, "dim": None, "content_keys": 0,
}


def _observe(audience: str) -> dict:
    try:
        index = get_index(audience)
        if index is None:
            return dict(_ABSENT_STATE)
        return {
            "state": index.state,
            "prepared_sha": index.prepared_sha,
            "entries": index.entry_count,
            "dim": index.dim,
            "content_keys": index.content_key_count,
        }
    except Exception as exc:  # noqa: BLE001 — 健檢不因取值失敗而崩
        return dict(_ABSENT_STATE, detail=f"{type(exc).__name__}")
