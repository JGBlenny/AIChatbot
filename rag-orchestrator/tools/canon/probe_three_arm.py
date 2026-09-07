"""4.4a H7 離線三臂 r@k：`tools/canon/probe_three_arm.py`（spec
knowledge-outline-and-intent-architecture・任務 4.4；Plan
`.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-4.4a-outline-probe-definition-20260907.md`
§1 H7／§4「H7 執行入口」）。

3.7 收案時記下的未驗命題：**內文鍵增益是否只是記住來源**——round9 46 問法
（非 helpcenter／koyu 改寫）不是 koyu 衍生句，`loo_mode="exact"` 在這批材料上
等於「一把鍵都不剔」（`article` 模式才會剔同文章鍵，但這批問句沒有 `article`
可比對）；凍結成 `--loo exact` 唯一值——⛔ 不接受 `article`，那會在沒有 LOO
效果的情況下假裝有做 LOO。

沿用 `tools/canon/index_eval.py` 的 `build_fine_keys`／`rank_fines`／
`recall_at_k`／`score_fine_for_query`，⛔ 不另開一套算法（兩把尺要能對得上）。

⛔ 本工具不打真 embedding 跑（本片單元測試一律假向量）；真的要跑（46 句
≈$0.001）由呼叫端另外決定何時執行，見 Plan §4。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import index_eval as ie  # noqa: E402 — 同目錄，重用 422／embedding／rank 基礎設施

EXIT_OK = 0
EXIT_FAIL = 2

ONLY_ACCEPTED_LOO = "exact"


class ProbeFailure(SystemExit):
    def __init__(self, msg: str):
        print(f"[probe_three_arm] {msg}", file=sys.stderr)
        super().__init__(EXIT_FAIL)


def _load_json(path: str) -> Any:
    if not os.path.isfile(path):
        raise ProbeFailure(f"輸入檔缺失：{path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 46 問法 + gold（依 sub → sub-map）
# ---------------------------------------------------------------------------

def load_phrasings_with_gold(topics_path: str, sub_map: dict) -> list:
    """回 `[{"q":..., "sub":..., "gold": [...]}]`（46 問法，`gold` 由 `sub_map` 決定）。

    ⛔ 遇到不在 `sub_map` 鍵集合裡的 `sub` 一律 fail loud（同 `outline_probe_select`
    的 A／C 紀律——⛔ 不靜默把它當「無 gold」排除，那等於用這支工具自己選題）。
    """
    doc = _load_json(topics_path)
    out = []
    subs_seen = set()
    for topic in doc.get("topics", []):
        for item in topic.get("phrasings", []):
            sub = item.get("sub", "")
            subs_seen.add(sub)
            out.append({"q": item["q"], "sub": sub})
    missing = sorted(s for s in subs_seen if s not in sub_map)
    if missing:
        raise ProbeFailure(f"phrasing 的 sub 不在 --sub-map 鍵集合裡（⛔ 不靜默排除）：{missing}")
    for row in out:
        row["gold"] = list(sub_map.get(row["sub"], []))
    return out


# ---------------------------------------------------------------------------
# embedding：primary（3.4 快取）唯讀查詢，寫入一律走 --cache-out（⛔ 不覆寫 3.4 快取）
# ---------------------------------------------------------------------------

def compute_embeddings_never_overwrite_primary(
    texts: list, backend: Any, primary_cache_path: str, cache_out_path: str,
) -> dict:
    """同 `index_eval.compute_embeddings` 的邏輯（含大聲失敗、維度校驗），差別只在
    快取讀寫的路徑分工：**讀**先查 `cache_out_path`（本工具自己上次寫的），
    再查 `primary_cache_path`（3.4 的快取，唯讀）；**寫**只寫 `cache_out_path`，
    `primary_cache_path` 永遠不被本函式開檔寫入。"""
    keys = sorted(set(texts))
    cache_keys = {ie._cache_key(t) for t in keys}

    for candidate_path in (cache_out_path, primary_cache_path):
        cached = ie.load_embedding_cache(candidate_path, cache_keys)
        if cached:
            return {t: cached[ie._cache_key(t)] for t in keys}

    vectors = asyncio.run(backend.embed(keys))
    if not isinstance(vectors, (list, tuple)) or len(vectors) != len(keys):
        raise ie.EmbeddingFailure(f"後端回傳筆數不符（要 {len(keys)} 筆）")

    failed = 0
    out: dict = {}
    for t, v in zip(keys, vectors):
        if v is None or not isinstance(v, (list, tuple)) or len(v) != 1536:
            failed += 1
            continue
        out[t] = list(v)
    if failed:
        raise ie.EmbeddingFailure(f"{failed}/{len(keys)} 筆向量缺漏或維度不符（1536）⇒ 大聲失敗，快取未寫入")

    cache_payload = {ie._cache_key(t): v for t, v in out.items()}
    ie.write_embedding_cache(cache_out_path, cache_payload)
    return out


# ---------------------------------------------------------------------------
# 三臂 recall@1/3/5
# ---------------------------------------------------------------------------

def compute_three_arm_recall(phrasings: list, fine_keys: dict, key_vecs: dict, *, loo_mode: str) -> dict:
    """`phrasings`：`[{"q","gold"}]`；只算 `gold` 非空（可對映）的句子。回
    `{arm: {"recall_at_1":..,"recall_at_3":..,"recall_at_5":..,"mappable":..}}`。"""
    mappable = [p for p in phrasings if p.get("gold")]
    out = {}
    for arm in ie.ARMS:
        hit1 = hit3 = hit5 = 0
        for p in mappable:
            q_vec = key_vecs.get(p["q"])
            if q_vec is None:
                continue
            ranked = ie.rank_fines(fine_keys, arm, q_vec, p["q"], None, loo_mode)
            gold = set(p["gold"])
            if ie.recall_at_k(ranked, gold, 1):
                hit1 += 1
            if ie.recall_at_k(ranked, gold, 3):
                hit3 += 1
            if ie.recall_at_k(ranked, gold, 5):
                hit5 += 1
        n = len(mappable)
        out[arm] = {
            "recall_at_1": ie._safe_div(hit1, n),
            "recall_at_3": ie._safe_div(hit3, n),
            "recall_at_5": ie._safe_div(hit5, n),
            "mappable": n,
        }
    return out


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def run(args) -> int:
    if args.loo != ONLY_ACCEPTED_LOO:
        raise ProbeFailure(
            f"--loo 只接受 {ONLY_ACCEPTED_LOO!r}（凍結值；問句非 koyu 衍生 ⇒ article 模式一把鍵都不剔、"
            f"等於無 LOO）：收到 {args.loo!r}"
        )

    sub_map = _load_json(args.sub_map)
    phrasings = load_phrasings_with_gold(args.topics, sub_map)

    fines = ie._load_fines(args.canon)
    fine_keys = ie.build_fine_keys(fines)
    index_texts = ie.all_index_texts(fine_keys)
    query_texts = [p["q"] for p in phrasings if p.get("gold")]
    all_texts = sorted(set(index_texts) | set(query_texts))

    if getattr(args, "backend", None) is not None:
        backend = args.backend  # 測試注入
    else:
        from services.agent.canon.fine_index import EmbeddingUtilsBackend

        backend = EmbeddingUtilsBackend()

    key_vecs = compute_embeddings_never_overwrite_primary(
        all_texts, backend, args.embedding_cache, args.cache_out,
    )

    arms_report = compute_three_arm_recall(phrasings, fine_keys, key_vecs, loo_mode=args.loo)

    n_mappable = sum(1 for p in phrasings if p.get("gold"))
    report = {
        "loo_mode": args.loo,
        "n": len(phrasings),
        "mappable": n_mappable,
        "arms": arms_report,
        "canon_sha256": ie.sha256_file(args.canon),
        "inputs_sha256": {
            "topics": ie.sha256_file(args.topics),
            "sub_map": ie.sha256_file(args.sub_map),
        },
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"[probe_three_arm] 完成：mappable={n_mappable}/{len(phrasings)} → {args.out_json}")
    return EXIT_OK


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--topics", default=os.path.join(
        ".kiro", "specs", "presales-grounding-gate", "coverage-map", "topics-v2.json"))
    p.add_argument("--sub-map", default=os.path.join(
        ".kiro", "specs", "knowledge-outline-and-intent-architecture", "inputs",
        "outline-probe-sub-map-20260907.json"))
    p.add_argument("--canon", default=os.path.join("rag-orchestrator", "canon", "prospect.md"))
    p.add_argument("--embedding-cache", default=os.path.join(
        ".claude", "skills", "outline-curation", "raw", "index-eval-20260907", "embeddings.json"),
        help="3.4 的快取（唯讀查詢，⛔ 本工具永不覆寫它）")
    p.add_argument("--cache-out", default=os.path.join(
        ".claude", "skills", "outline-curation", "raw", "probe-three-arm-20260907", "embeddings.json"),
        help="本工具自己的快取（讀寫都走這裡；缺 ⇒ 打 embedding 後寫入這裡）")
    p.add_argument("--loo", default=ONLY_ACCEPTED_LOO, help="唯一接受值：exact（凍結）")
    p.add_argument("--out-json", default=os.path.join(
        ".kiro", "specs", "knowledge-outline-and-intent-architecture", "inputs",
        "probe-three-arm-20260907.json"))
    return p


def _resolve_repo_relative(args) -> None:
    repo_root = ie.find_repo_root()

    def r(rel):
        return rel if os.path.isabs(rel) else os.path.join(repo_root, rel)

    args.topics = r(args.topics)
    args.sub_map = r(args.sub_map)
    args.canon = r(args.canon)
    args.embedding_cache = r(args.embedding_cache)
    args.cache_out = r(args.cache_out)
    args.out_json = r(args.out_json)


def main(argv: Optional[list[str]] = None, *, backend: Any = None) -> int:
    args = build_arg_parser().parse_args(argv)
    args.backend = backend
    _resolve_repo_relative(args)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
