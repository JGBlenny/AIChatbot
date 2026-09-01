"""S1-B：production entry 的 responsibility **observation**（⛔ 零 authority）。

```text
pre_drop_rows → mapping → collapse → canonical scoring → winner → binding_available
```

⚠️ **本模組只計算 decision，⛔ 自身不做 authority handoff**：
⛔ 不寫 session、⛔ 不呼叫 `build_responsibility_session`、⛔ 不改 facet flow。
handoff 由呼叫端（chat.py）依 `handoff_eligible` 決定——**一輪只 canonical score 一次**，
⛔ 不得 telemetry 算一次、authority 再算一次。

⚠️ **cheap activation gate（業主裁定 2026-09-01）**：
```text
pre-drop rows → row→responsibility mapping（便宜，無網路）
  nominated ∩ MIGRATION_ALLOWLIST == ∅ → ⛔ 完全不跑 canonical scorer，走既有 facet
  否則                                  → 對**全部** nominated 做 canonical scoring
```
⚠️ 閘門只省成本，⛔ **不決定 authority**——authority 仍由 canonical winner 決定。
⛔ **不得**用 committed facet 當閘門：facet 與 responsibility 無 machine mapping
（`FACET_RESPONSIBILITY_COMPATIBILITY_CONTRACT = NOT_ESTABLISHED`），
用 facet 當開關等於讓 facet 決定 responsibility 能不能進場。

⚠️ **失敗語義（業主裁定 2026-09-01）**：artifact／mapping／scorer 失敗一律回
`status=ERROR`，⛔ **不得**折疊成「沒有 responsibility winner」——
把基礎設施故障偽裝成正常無提名，會讓新架構壞掉時完全看不見。
`NO_NOMINATION` 與 `ERROR` 是**兩種不同狀態**，⛔ 不得互相冒充。

⚠️ 本模組**永不向 request path 拋例外**：telemetry 故障 ⛔ 不得打死使用者請求；
但它必須在 log／回傳結構留下明確錯誤，且該輪 telemetry 驗收 ⛔ 不得算 PASS。
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Mapping, Optional

STATUS_OK = "OK"
STATUS_NO_NOMINATION = "NO_NOMINATION"
STATUS_ERROR = "ERROR"
STATUS_DISABLED = "DISABLED"
#: cheap gate 未命中——⚠️ 這是**省成本的正常路徑**，⛔ 不是 ERROR、⛔ 也不是 NO_NOMINATION
STATUS_SKIPPED_NOT_CANDIDATE = "SKIPPED_NOT_CANDIDATE"

ENV_FLAG = "RESPONSIBILITY_TELEMETRY"
#: 逗號分隔的 responsibility id；空＝不啟用任何 handoff（S2 預設關閉）
ENV_ALLOWLIST = "RESPONSIBILITY_MIGRATION_ALLOWLIST"

#: ⚠️ 快取只存**已驗證通過**的 artifact；驗證失敗 ⛔ 不快取（否則一次故障會被記住）
_CACHE: Dict[str, Any] = {}


def enabled() -> bool:
    return os.getenv(ENV_FLAG, "false").strip().lower() == "true"


def migration_allowlist() -> frozenset:
    """⚠️ 只作 **cheap activation gate** 與 handoff 資格判斷，
    ⛔ 不得用來過濾 canonical scoring 的候選集合（否則 semantic winner 會被閹割）。"""
    raw = os.getenv(ENV_ALLOWLIST, "")
    return frozenset(x.strip() for x in raw.split(",") if x.strip())


def _artifacts():
    if "registry" not in _CACHE:
        from services.responsibility_artifacts import load
        registry, embeddings, report = load()
        import services.responsibility_collapse as rc
        _CACHE["registry"] = registry
        _CACHE["embeddings"] = embeddings
        _CACHE["report"] = report
        _CACHE["mapping"] = rc.load_mapping_from_registry(registry)
    return (_CACHE["registry"], _CACHE["embeddings"],
            _CACHE["mapping"], _CACHE["report"])


def _batch_rerank_fn():
    """回傳符合 G17 exact-set 契約的 batch rerank 函式。

    ⚠️ 用 `score_batch` 而非逐筆 `score`：整批一次呼叫，且 requested IDs 必須 ==
    returned IDs——⛔ 只比數量會假綠（partial response 會悄悄改變 ranking population）。
    """
    from services.semantic_reranker import SemanticReranker
    reranker = SemanticReranker()

    def _fn(user_query: str, payload: Mapping[str, str]) -> Dict[str, float]:
        rids = list(payload.keys())
        candidates = [{"id": rid, "answer": payload[rid],
                       "content": payload[rid], "question_summary": payload[rid]}
                      for rid in rids]
        out = reranker.rerank(user_query, candidates, top_k=len(candidates))
        scores: Dict[str, float] = {}
        for c in out:
            cid = c.get("id")
            if cid in payload:
                scores[cid] = float(c.get("semantic_score")
                                    or c.get("rerank_score") or 0.0)
        return scores      # ⚠️ 集合不符時由 score_batch 依契約拋，⛔ 此處不補齊

    return _fn


def binding_available(responsibility_id: str) -> bool:
    """⚠️ 僅供觀測；⛔ **不得**用來過濾候選或影響 winner 選取。"""
    from services.fulfillment_registry import bindings_for
    return bool(bindings_for(responsibility_id))


async def observe(pre_drop_rows: Optional[List[Mapping[str, Any]]],
                  user_query: str,
                  committed_facet: Optional[str] = None) -> Dict[str, Any]:
    """對一輪請求做 responsibility observation。⚠️ **永不拋例外**。"""
    t0 = time.time()
    if not enabled():
        return {"status": STATUS_DISABLED}
    base: Dict[str, Any] = {
        "committed_facet": committed_facet,
        "pre_drop_row_ids": [r.get("id") for r in (pre_drop_rows or [])],
        "authority_handoff": "NONE（S1-B telemetry-only）",
        "session_write": 0,
    }
    try:
        registry, embeddings, mapping, report = _artifacts()
        base["registry_digest"] = report["registry_digest"][:16]

        import services.responsibility_collapse as rc
        nominated = rc.select_nominated(list(pre_drop_rows or []), mapping, limit=20)
        base["nominated"] = [c["responsibility_id"] for c in nominated]
        allow = migration_allowlist()
        base["migration_allowlist"] = sorted(allow)
        if not nominated:
            base["status"] = STATUS_NO_NOMINATION
            base["winner"] = None
            base["_semantics"] = "⚠️ 合法的『本輪沒有責任被提名』，⛔ 與 ERROR 不同"
            base["elapsed_ms"] = int((time.time() - t0) * 1000)
            return base

        # ── cheap activation gate ────────────────────────────────────
        # ⚠️ allowlist 非空時才啟用閘門；allowlist 為空且 telemetry 開啟＝
        #    **診斷模式**（對全部 nominated 打分，成本較高），⛔ 非 production 預設。
        if allow and not (set(base["nominated"]) & allow):
            base.update({
                "status": STATUS_SKIPPED_NOT_CANDIDATE,
                "winner": None,
                "scorer_invocations": 0,
                "handoff_eligible": False,
                "_semantics": ("⚠️ nominated 未包含任何 migration-enabled responsibility ⇒ "
                               "⛔ 不跑 canonical scorer（省成本），走既有 facet；"
                               "⛔ 這不是 ERROR、⛔ 也不是 NO_NOMINATION"),
                "elapsed_ms": int((time.time() - t0) * 1000),
            })
            return base

        from services.embedding_utils import get_embedding_client
        from services.responsibility_scoring import ResponsibilityScorer
        query_embedding = await get_embedding_client().get_embedding(user_query)
        if not query_embedding:
            raise RuntimeError("query embedding 取得失敗——⛔ 不得以零向量帶過")

        scorer = ResponsibilityScorer(registry, embeddings, rerank_fn=lambda q, t: [])
        scored = scorer.score_batch(nominated, user_query, query_embedding,
                                    _batch_rerank_fn())
        scored.sort(key=lambda s: -s["final_similarity"])
        winner = scored[0]["responsibility_id"]

        base.update({
            "status": STATUS_OK,
            "scores": {s["responsibility_id"]: round(s["final_similarity"], 4)
                       for s in scored},
            "winner": winner,
            "winner_final_similarity": round(scored[0]["final_similarity"], 4),
            # ⚠️ availability 在 winner **決定之後**才查——⛔ 不得用它過濾候選
            "binding_available": binding_available(winner),
            "scorer_invocations": 1,      # ⚠️ 一輪只打一次分（S1 記錄與 S2 authority 共用同一份）
            "elapsed_ms": int((time.time() - t0) * 1000),
        })
        # ── handoff 資格（⚠️ 只回報，handoff 動作由呼叫端執行）──────────
        # ⛔ winner 不在 allowlist ⇒ 不 handoff，且 ⛔ 不得改選 runner-up
        # ⛔ winner 在 allowlist 但無 binding ⇒ **明確 handoff 失敗**，
        #    ⛔ 不得 fallback runner-up、⛔ 不得標成 responsibility success
        in_allow = winner in allow
        base["winner_in_allowlist"] = in_allow
        base["handoff_eligible"] = bool(in_allow and base["binding_available"])
        if in_allow and not base["binding_available"]:
            base["handoff_failure"] = ("WINNER_HAS_NO_REGISTERED_BINDING"
                                       "——⛔ 不得 fallback runner-up、⛔ 不得標成 responsibility success")
        return base
    except Exception as exc:                                     # noqa: BLE001
        base.update({
            "status": STATUS_ERROR,
            "winner": None,
            "error_class": type(exc).__name__,
            "error": str(exc)[:300],
            "handoff_eligible": False,      # ⚠️ 失敗一律不得 handoff
            "_semantics": ("⚠️ RESPONSIBILITY_TELEMETRY_ERROR ⛔ **不等於**"
                           "『沒有 responsibility winner』——⛔ 不得折疊成 NO_NOMINATION，"
                           "本輪 telemetry 驗收 ⛔ 不得算 PASS"),
            "elapsed_ms": int((time.time() - t0) * 1000),
        })
        return base


def log_line(obs: Mapping[str, Any]) -> Optional[str]:
    """把 observation 壓成單行可稽核日誌。⚠️ DISABLED 不印，避免噪音。"""
    st = obs.get("status")
    if st == STATUS_DISABLED:
        return None
    if st == STATUS_ERROR:
        return (f"❌ [responsibility-telemetry] ERROR {obs.get('error_class')}: "
                f"{obs.get('error')} ⛔ 非『無 winner』")
    if st == STATUS_NO_NOMINATION:
        return (f"🔭 [responsibility-telemetry] NO_NOMINATION"
                f"（facet={obs.get('committed_facet')}）")
    return (f"🔭 [responsibility-telemetry] nominated={obs.get('nominated')} "
            f"→ winner={obs.get('winner')} ({obs.get('winner_final_similarity')}) "
            f"binding_available={obs.get('binding_available')} "
            f"facet={obs.get('committed_facet')} "
            f"⛔ authority_handoff=NONE｜{obs.get('elapsed_ms')}ms")
