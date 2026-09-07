"""候選細目選取（spec knowledge-outline-and-intent-architecture 元件 6・任務 3.3b）。

一回合的流程：**先切可見子集、再在子集內算分**，取 `(-score, fine_id)` 排序的前
`K` 名。索引不可用／正本 sha 不符／查詢 embedding 失敗一律回 `None`——
呼叫端（4.1）據此退回可見細目全集＋toc（`CandidateOutlineDoc.from_visible`，1.16；⛔ 不是未過濾整份大綱），⛔ 本模組不回半成品。

## 三條硬規則（⛔ 這三條是本檔存在的理由，改動前先看 Plan §1.6／§4.7）

1. **失敗只會回 `None`，⛔ 不會變寬**：`state != "ready"`、`canon_sha256` 不符、
   查詢向量拿不到（例外／逾時／`None`／形狀不合）——四種情況一律 `None`。
   ⚠️ ⛔ 不得改成「拿不到向量就把可見細目全給」：那會讓一次 embedding 故障
   靜默變成「候選＝全部」。
2. **不可見的細目一律不出現在 `candidate_ids`**，即使它分數最高。可見性在算分**之前**
   就切掉（`FineIndex.visible_subset` → `canon_assembler.canon_visible`，3.2 已與
   `build_visibility_predicate` 驗過零分歧），⛔ 不在排序後再過濾（那種寫法一旦
   有人動排序就會漏）。
3. **⛔ 不記講法 id、⛔ 不 log 查詢**（F18／業主 2026-09-07 §8.1；任務 3.7 擴及內文句）：
   `Selection` 只帶 `winning_key_kind ∈ {"title","phrasing","content"}`。講法對照表就在
   repo，記 `ph:<sha8>` 等於一次查表就還原出使用者問句；內文句是正本答案本文，
   ⛔ 不記 `ct:*`，同待遇。本模組 ⛔ 不得有 `print`；`logging` 只准帶數量／狀態／例外型別名。

## 為什麼沒有分數門檻（⛔ 不要「順手」補一個）
design 決議：K 名之內全給，該不該用由模型與 Verifier 守。餘弦可以是負的，
一個叫 `MIN_SCORE` 的常數會誘導後人寫 `score >= MIN_SCORE`，那是**第二道**沒有經過
驗收的過濾器。故本檔連常數都不定義。

## `miss_kind` 的四個值
- `hit`：有候選。
- `none_visible`：可見子集是空的（身分看不到任何細目）。
- `no_candidate`：可見子集非空、但沒有任何可見細目有索引項。
  ⚠️ **在 `ready` 狀態下不可達**——`FineIndex.prepare` 對每個細目至少建一個標題鍵，
  且任一鍵失敗就整份丟成 `not_ready`。保留於列舉是為了讓 4.1 的 trace 值域封閉；
  以測試釘住「只有刻意構造的索引才走得到」。
- `index_unavailable`：**本函式⛔ 不回傳它**。索引不可用時 `select` 回 `None`，
  由 4.1 在 trace 上寫這個值（Plan §1.6：「`index_unavailable` 由 runtime 以 `None` 判讀」）。
"""
from __future__ import annotations

import asyncio
import logging
from typing import Literal, Optional, TypedDict

from services.agent.canon.canon_parser import CanonDoc
from services.agent.canon.fine_index import EmbeddingBackend, FineIndex, KeyKind, _normalize

logger = logging.getLogger(__name__)

#: 一回合最多給模型幾個候選細目（design 元件 6）。
K: int = 5
#: 查詢向量的**硬上限**逾時。⛔ 不因建構參數而放寬（同 `fine_index.MAX_BATCH` 的理由：
#: 這是對「一回合不得為了選候選而卡住」的保護，不是可調旋鈕）。
QUERY_EMBED_TIMEOUT_S: float = 3.0

MissKind = Literal["hit", "none_visible", "no_candidate", "index_unavailable"]


class Selection(TypedDict):
    """一回合的選取結果。

    ⛔ **無 `winning_key`／無 `ph:*`／無 `ct:*`**（業主 2026-09-07 §8.1 裁：trace 不記講法 id；
    任務 3.7 擴及內文句鍵）。
    `winning_key_kind` 與 `scores` 只涵蓋 `candidate_ids` 內的細目——沒進候選的細目
    連分數都不外流。
    """

    candidate_ids: list[str]
    winning_key_kind: dict[str, KeyKind]
    scores: dict[str, float]
    miss_kind: MissKind


def _dot(a, b) -> float:
    """兩個**已 L2 正規化**向量的內積＝餘弦。

    ⚠️ 兩邊都正規化過（索引項在 `FineIndex.prepare`、查詢在 `_embed_query`），
    故 ⛔ 不需要也不得在此再除一次範數。
    """
    return sum(x * y for x, y in zip(a, b))


class CandidateSelector:
    """`FineIndex` ＋ 身分 ＋ 查詢 → top-K 候選細目 id。

    Args:
        index: 已 `prepare` 的索引。查詢向量取自 `index.backend`（同一個模型，
            否則兩邊向量空間不同、餘弦無意義）。
        backend: 覆寫查詢用後端（測試注入）；省略 ⇒ 用 `index.backend`。
        timeout_s: 查詢 embedding 的逾時；一律再與 `QUERY_EMBED_TIMEOUT_S` **取小**
            ——⛔ 不得放寬到 3 秒以上（保護，不是旋鈕）。
    """

    def __init__(
        self,
        index: FineIndex,
        backend: Optional[EmbeddingBackend] = None,
        *,
        timeout_s: float = QUERY_EMBED_TIMEOUT_S,
    ) -> None:
        self._index = index
        self._backend = backend
        self._timeout_s = min(float(timeout_s), QUERY_EMBED_TIMEOUT_S)

    @property
    def index(self) -> FineIndex:
        """唯讀存取底層索引（任務 4.1：降級路徑要用 `visible_subset`，比照
        `FineIndex.backend` 的唯讀 property 先例）。⛔ 無 setter、不改任何邏輯。
        """
        return self._index

    async def select(
        self,
        doc: CanonDoc,
        identity,
        query: str,
        *,
        vendor_business_types: frozenset[str] = frozenset(),
    ) -> Optional[Selection]:
        """這一回合該給模型哪幾個細目；不可服務 ⇒ `None`（⛔ 不回半成品）。

        `query` 由呼叫端組（4.1 負責「當前＋上一則 user 訊息」的程式規則），
        本函式只收字串、⛔ 不看對話歷史、⛔ 不記錄這個字串。
        """
        if self._index.state != "ready":
            logger.debug("candidate_selector: 索引非 ready（%s）⇒ 不服務", self._index.state)
            return None
        if doc.canon_sha256 != self._index.prepared_sha:
            # 索引是對別份正本建的 ⇒ 分數對不上這份 doc 的細目，⛔ 不勉強服務。
            logger.warning("candidate_selector: 索引與正本 sha 不符 ⇒ 不服務")
            return None

        query_vector = await self._embed_query(query)
        if query_vector is None:
            return None

        visible = self._index.visible_subset(
            identity, doc, vendor_business_types=vendor_business_types
        )
        if not visible:
            return Selection(
                candidate_ids=[], winning_key_kind={}, scores={}, miss_kind="none_visible"
            )

        scored: list[tuple[str, float, KeyKind]] = []
        for fine_id in visible:
            best = self._best_entry(fine_id, query_vector)
            if best is None:
                continue
            score, kind = best
            scored.append((fine_id, score, kind))

        if not scored:
            # 見模組 docstring：`ready` 狀態下不可達（每個細目至少有標題鍵）。
            logger.warning(
                "candidate_selector: 可見細目 %d 個、但都沒有索引項 ⇒ no_candidate", len(visible)
            )
            return Selection(
                candidate_ids=[], winning_key_kind={}, scores={}, miss_kind="no_candidate"
            )

        # 排序 `(-score, fine_id)`：同分一律字典序，⛔ 不留任何非決定性（集合迭代序）。
        scored.sort(key=lambda item: (-item[1], item[0]))
        top = scored[:K]
        return Selection(
            candidate_ids=[fid for fid, _s, _k in top],
            winning_key_kind={fid: kind for fid, _s, kind in top},
            scores={fid: score for fid, score, _k in top},
            miss_kind="hit",
        )

    # ── 內部 ────────────────────────────────────────────────────────

    def _best_entry(self, fine_id: str, query_vector) -> Optional[tuple[float, KeyKind]]:
        """該細目分數最高的索引項 `(score, kind)`；無索引項 ⇒ `None`。

        同分序 `title > phrasing > content`（Plan §1.6／§1.2-7、業主 2026-09-07 §8.1 裁）——
        ⚠️ 用明示的比較鍵，⛔ 不依賴 `entries_for` 的回傳順序碰巧把標題排在前面
        （那是另一個檔的實作細節，改了這裡會靜默跟著變）。
        """
        best_key: Optional[tuple[float, int]] = None
        best: Optional[tuple[float, KeyKind]] = None
        for kind, vector in self._index.entries_for(fine_id):
            score = _dot(query_vector, vector)
            # 同分：title(0) > phrasing(-1) > content(-2)
            tie_rank = 0 if kind == "title" else -1 if kind == "phrasing" else -2
            key = (score, tie_rank)
            if best_key is None or key > best_key:
                best_key, best = key, (score, kind)
        return best

    async def _embed_query(self, query: str) -> Optional[tuple[float, ...]]:
        """查詢向量（已 L2 正規化）；任何失敗 ⇒ `None`。

        ⛔ 失敗一律 `None`，⛔ 不得退成「跳過算分把可見細目全給」。
        ⛔ 例外訊息只印型別名——`query` 是使用者原句，印出去等於外洩。
        """
        backend = self._backend if self._backend is not None else self._index.backend
        if backend is None:
            logger.warning("candidate_selector: 沒有 embedding 後端 ⇒ 不服務")
            return None
        try:
            vectors = await asyncio.wait_for(backend.embed([query]), self._timeout_s)
        except Exception as exc:  # noqa: BLE001 — 一回合內：任何失敗都退成「不服務」
            # ⚠️ CancelledError 是 BaseException，⛔ 不在此吞掉。
            logger.warning(
                "candidate_selector: 查詢 embedding 失敗（%s）⇒ 不服務", type(exc).__name__
            )
            return None
        if not isinstance(vectors, (list, tuple)) or len(vectors) != 1 or vectors[0] is None:
            logger.warning("candidate_selector: 查詢 embedding 回傳形狀不合 ⇒ 不服務")
            return None
        # 維度必須與索引一致（`_normalize` 的 `dim` 參數會擋），且 NaN／零範數一律不合格。
        normalized = _normalize(vectors[0], self._index.dim)
        if normalized is None:
            logger.warning("candidate_selector: 查詢向量不合法（維度／NaN／零範數）⇒ 不服務")
            return None
        return normalized
