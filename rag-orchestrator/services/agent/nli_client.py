"""`nli-model` 服務的 client（spec agentic-mcp-orchestration・DSP-033）。

Verifier 步③要問的是「這個片段有沒有被它引的來源句支撐」。答案來自
`nli-model` 容器的 `POST /nli`，本檔是**唯一**的呼叫點。

## 兩條紀律，理由都在失敗方向
1. **⛔ 不快取可用性**（r18 F-10）。每回合實打、失敗即降級、下回合重試。
   快取「服務掛了」會讓一次瞬斷變成一段時間的全域降級，而降級期間 Verifier
   跑的是**比較鬆**的那把尺（現行 ratio∧全極性，抓到 62% vs NLI 的 69%）——
   把放行率的漂移藏進一個沒人會去看的旗標裡，是最不該省的那種省。
2. **⛔ 不 log body**（r18 F-12）。送出去的 `premise` 是知識庫原文、
   `hypothesis` 是模型寫給使用者的句子；把它們印進 log 等於在 2.6 security
   review P2 擋掉的所有出口之外，另外開一個。例外訊息只留型別名。

## 逾時只有一條公式（r18 F-4）
`逾時 = 句對數 × NLI_PAIR_TIMEOUT_MS`，回合上限 `NLI_MAX_PAIRS`。
⛔ 沒有第二個逾時常數——多一個就會出現「這次是哪個逾時踩到的」這種
查不清楚的問題，而降級與否正是靠它決定。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol, Sequence

#: compose 宣告的服務位置（容器視角）；⛔ 不用 localhost（容器內指向自己）。
DEFAULT_NLI_URL = "http://nli-model:8000"
DEFAULT_PAIR_TIMEOUT_MS = 400
DEFAULT_MAX_PAIRS = 12

#: 服務端對單一句對回的錯誤碼（該對判拒，⛔ 不是整回合降級）。
ERR_HYPOTHESIS_TOO_LONG = "hypothesis_too_long"


@dataclass(frozen=True)
class NliPair:
    """`premise` ＝解析後的來源句，`hypothesis` ＝模型寫的那個片段。

    ⚠️ 方向 ⛔ 不可對調：NLI 問的是「前提是否蘊涵假設」，
    對調之後量到的是「模型那句話是否蘊涵來源」——那是另一個命題，
    而且對『多講了原文沒有的東西』這種捏造完全不敏感。
    """

    premise: str
    hypothesis: str


class NliUnavailable(RuntimeError):
    """本回合取不到 NLI 分數 ⇒ Verifier 走降級尺並記 `nli_degraded`。

    ⛔ 訊息只放型別／狀態碼，**不放回應內容**。
    """


class NliPairsCapped(NliUnavailable):
    """句對數超過 `NLI_MAX_PAIRS`（F-4）。

    與逾時分開計（`nli_pairs_capped` vs `nli_degraded` 之外的另一個 violation），
    因為兩者的處置不同：逾時是服務側的容量問題，超限是模型一次寫了太多需要
    查證的句子——後者不該被前者的告警比率吃掉。
    """


class NliClient(Protocol):
    """`score(pairs) -> list[float|None]`。`None` ＝該對取不到分數
    （例如 `hypothesis_too_long`）⇒ 由呼叫端判拒，⛔ 不是降級訊號。"""

    async def score(self, pairs: Sequence[NliPair]) -> list: ...


def _coerce_score(raw: Any) -> Optional[float]:
    """服務端每一格是 float 或 `{"error": ...}`。

    🔴 認不得的形狀一律回 `None`（＝該對判拒），⛔ 不回一個猜出來的數字：
    這裡的失敗方向必須是拒絕，回 1.0 之類的預設值等於讓格式漂移直接變成放行。
    """
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
        return value if 0.0 <= value <= 1.0 else None
    return None


class HttpNliClient:
    """打 `nli-model` 的 `POST /nli`。

    `last_model_sha` 記最近一次**成功**回應帶回來的權重指紋，供 trace 落
    `nli_model_sha`（可稽核定義：`entail_score`＋`nli_model_sha`＋`nli_tau`
    三者同存才重算得出 verdict）。⚠️ 它是觀測值不是憑據——真正判 `nli_ready`
    的是服務端自己的 canary＋指紋比對（r18 F-6）。
    """

    def __init__(
        self,
        url: str = DEFAULT_NLI_URL,
        *,
        pair_timeout_ms: int = DEFAULT_PAIR_TIMEOUT_MS,
        max_pairs: int = DEFAULT_MAX_PAIRS,
    ) -> None:
        self.url = (url or DEFAULT_NLI_URL).rstrip("/")
        self.pair_timeout_ms = int(pair_timeout_ms)
        self.max_pairs = int(max_pairs)
        self.last_model_sha: str = ""

    def timeout_s(self, n_pairs: int) -> float:
        """F-4 的唯一逾時公式。⛔ 不另設下限或上限常數。"""
        return (max(1, int(n_pairs)) * self.pair_timeout_ms) / 1000.0

    async def score(self, pairs: Sequence[NliPair]) -> list:
        pairs = list(pairs)
        if not pairs:
            return []
        if len(pairs) > self.max_pairs:
            raise NliPairsCapped(f"pairs={len(pairs)} > max_pairs={self.max_pairs}")

        import httpx

        payload = {"pairs": [{"premise": p.premise, "hypothesis": p.hypothesis} for p in pairs]}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s(len(pairs))) as client:
                resp = await client.post(f"{self.url}/nli", json=payload)
        except Exception as exc:  # noqa: BLE001 — 逾時／連線失敗／DNS 皆同一個處置
            # ⛔ 只留型別名：httpx 的例外字串會帶上完整 URL 與部分請求內容。
            raise NliUnavailable(type(exc).__name__) from None
        if resp.status_code != 200:
            raise NliUnavailable(f"http_{resp.status_code}")
        try:
            data = resp.json()
        except ValueError:
            raise NliUnavailable("bad_json") from None
        scores = data.get("scores") if isinstance(data, dict) else None
        # F-11：長度不符 ⇒ 降級。配對是靠**順序**做的，長度一旦不同就無從得知
        # 哪一格對應哪一對——拿錯位的分數去判 verdict 比沒有分數更糟。
        if not isinstance(scores, list) or len(scores) != len(pairs):
            raise NliUnavailable("length_mismatch")
        self.last_model_sha = str((data.get("model_sha") or "")) if isinstance(data, dict) else ""
        return [_coerce_score(s) for s in scores]

    async def health(self) -> Optional[dict]:
        """`GET /health` 透傳給 orchestrator 的 agent health（r18 F-6）。

        取不到一律回 `None`＝**不 ready**，⛔ 不回一個「大概沒事」的字典。
        逾時沿用同一條公式（一對句子的預算），⛔ 不另立常數。
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=self.timeout_s(1)) as client:
                resp = await client.get(f"{self.url}/health")
        except Exception:  # noqa: BLE001
            return None
        if resp.status_code != 200:
            return None
        try:
            data = resp.json()
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        self.last_model_sha = str(data.get("model_sha") or "") or self.last_model_sha
        return {
            "nli_ready": bool(data.get("nli_ready")),
            "model_sha": str(data.get("model_sha") or ""),
            "canary_ok": bool(data.get("canary_ok")),
        }


class FakeNliClient:
    """測試與**啟動自證**用的假 client（⛔ 不觸網、⛔ 不載模型）。

    三種驅動方式擇一：
      * `scores`：依序回這一串（長度不符呼叫端的 pairs 時照回，
        讓「長度不符 ⇒ 降級」這條路徑測得到）；
      * `fn`：`fn(pair) -> float | None`；
      * `error`：每次呼叫都 raise 它（降級模式自證用）。

    ⚠️ 另備一支**同步** `score_sync`：`OutputVerifier.self_test` 在
    `bootstrap.build_runtime` 裡是同步呼叫的，而 `build_runtime` 可能在
    app 啟動的 event loop 裡跑，⛔ 不能用 `asyncio.run`。
    `HttpNliClient` 刻意**沒有** `score_sync`——啟動自證因此不可能誤打真服務
    （P1-2：啟動 ⛔ 不依賴 `/nli` 可用）。
    """

    def __init__(
        self,
        scores: Optional[Sequence[Optional[float]]] = None,
        fn: Optional[Callable[[NliPair], Optional[float]]] = None,
        error: Optional[BaseException] = None,
        *,
        model_sha: str = "fake-nli-model-sha",
    ) -> None:
        if sum(x is not None for x in (scores, fn, error)) != 1:
            raise ValueError("FakeNliClient：scores／fn／error 恰擇一")
        self._scores = list(scores) if scores is not None else None
        self._fn = fn
        self._error = error
        self.last_model_sha = model_sha
        self.calls: list = []

    def score_sync(self, pairs: Sequence[NliPair]) -> list:
        pairs = list(pairs)
        self.calls.append(pairs)
        if self._error is not None:
            raise self._error
        if self._scores is not None:
            return list(self._scores)
        return [self._fn(p) for p in pairs]

    async def score(self, pairs: Sequence[NliPair]) -> list:
        return self.score_sync(pairs)

    async def health(self) -> Optional[dict]:
        if self._error is not None:
            return None
        return {"nli_ready": True, "model_sha": self.last_model_sha, "canary_ok": True}


def client_from_env() -> HttpNliClient:
    """`NLI_URL`／`NLI_PAIR_TIMEOUT_MS`／`NLI_MAX_PAIRS`（compose 宣告，見
    `docker-compose.prod.yml`）。壞值退回預設並印警告，⛔ 不讓啟動炸——
    NLI 不可用只該降級，⛔ 不該讓整個 agent 起不來（可用性，DSP-033）。"""
    def _int(key: str, default: int) -> int:
        raw = os.getenv(key, "").strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            print(f"⚠️ [agent] {key}={raw!r} 非整數，退回預設 {default}")
            return default
        if value <= 0:
            print(f"⚠️ [agent] {key}={value} 必須 >0，退回預設 {default}")
            return default
        return value

    return HttpNliClient(
        os.getenv("NLI_URL", "").strip() or DEFAULT_NLI_URL,
        pair_timeout_ms=_int("NLI_PAIR_TIMEOUT_MS", DEFAULT_PAIR_TIMEOUT_MS),
        max_pairs=_int("NLI_MAX_PAIRS", DEFAULT_MAX_PAIRS),
    )


__all__ = [
    "DEFAULT_MAX_PAIRS",
    "DEFAULT_NLI_URL",
    "DEFAULT_PAIR_TIMEOUT_MS",
    "ERR_HYPOTHESIS_TOO_LONG",
    "FakeNliClient",
    "HttpNliClient",
    "NliClient",
    "NliPair",
    "NliPairsCapped",
    "NliUnavailable",
    "client_from_env",
]
