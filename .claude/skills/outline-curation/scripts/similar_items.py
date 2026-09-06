#!/usr/bin/env python3
"""步 3 phrasing：相似細目**待審清單**（knowledge-outline-and-intent-architecture 任務 2.2｜design 元件 1）。

細目「標題＋已掛講法」兩兩算相似度 → `payload.similar_pairs[] = {a, b, score, method}`（超過門檻者）。
⛔ **本腳本永遠不合併任何細目、不改任何 id、不動 `structure-proposal.json`**：它只出清單，合併與否由人裁決
（design 元件 1「只產待審清單、⛔ 不自動合併」；R2.5）。

後端兩種，`method` 寫進 payload：
  embedding_cosine        環境變數 `EMBEDDING_API_URL` 有設時使用。請求形狀取自
                          `rag-orchestrator/services/embedding_utils.py::EmbeddingClient.get_embedding`
                          與 `services/knowledge_completion_loop/embedding_client.py`：
                          `POST <url>`、body `{"text": "<文字>"}`、回應 `{"embedding": [float, ...]}`。
                          ⛔ 不印 URL、⛔ 不印任何環境變數；呼叫失敗一律大聲失敗（exit 2），⛔ 不靜默退回字面法。
  char_bigram_jaccard     沒設環境變數時的決定性字面後備（與 `phrasing_map.py` 同一把尺）。

⛔ 無 `datetime.now()`、⛔ 不讀 `.env`、⛔ 不讀 DB；標準庫 only。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_VERSION = "0.1.0"
DEFAULT_THRESHOLD = 0.30
LEXICAL_METHOD = "char_bigram_jaccard"
VECTOR_METHOD = "embedding_cosine"


def _load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, f"{name}.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


_env = _load_sibling("_envelope")
_pm = _load_sibling("phrasing_map")


def build_profiles(structure_path: str, phrasing_map_path=None):
    """回 (依 id 升冪的 [(fine_id, profile 文字)], 講法清單)。profile＝細目標題＋已掛講法文字。"""
    fines = _pm.load_fines(structure_path)
    phrasings = []
    if phrasing_map_path:
        doc = _pm._load_json(phrasing_map_path)
        payload = doc["payload"] if "payload" in doc else doc
        phrasings = list(payload.get("phrasings", []))
    by_fine = {}
    for p in phrasings:
        by_fine.setdefault(p["fine_id"], []).append(p["text"])
    profiles = []
    for f in fines:
        texts = [f["title"]] + sorted(by_fine.get(f["id"], []))
        profiles.append((f["id"], " ".join(texts)))
    return profiles, phrasings


# ---------------------------------------------------------------------------
# 後端
# ---------------------------------------------------------------------------

def _embed(url: str, text: str):
    import urllib.request

    req = urllib.request.Request(
        url,
        data=json.dumps({"text": text}, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:          # noqa: S310 — URL 只來自環境變數
        if resp.status != 200:
            raise RuntimeError(f"embedding API 非 200（status={resp.status}）")   # ⛔ 不印 URL
        vec = json.loads(resp.read().decode("utf-8")).get("embedding")
    if not vec:
        raise RuntimeError("embedding API 回應缺 embedding 欄位")                 # ⛔ 不印 URL
    return [float(x) for x in vec]


def _cosine(a, b) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return num / (na * nb)


def score_pairs(profiles, threshold: float, embedding_url=None):
    """回 (pairs, method)。pairs 依 (-score, a, b) 排序，a<b（⛔ 不重複、⛔ 不自比）。"""
    if embedding_url:
        vecs = {fid: _embed(embedding_url, text) for fid, text in profiles}
        method = VECTOR_METHOD

        def sim(i, j):
            return _cosine(vecs[profiles[i][0]], vecs[profiles[j][0]])
    else:
        bgs = [_pm.bigrams(text) for _, text in profiles]
        method = LEXICAL_METHOD

        def sim(i, j):
            return _pm.jaccard(bgs[i], bgs[j])

    pairs = []
    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            s = sim(i, j)
            if s >= threshold:
                a, b = sorted((profiles[i][0], profiles[j][0]))
                pairs.append({"a": a, "b": b, "score": round(s, 4), "method": method})
    pairs.sort(key=lambda p: (-p["score"], p["a"], p["b"]))
    return pairs, method


def build(structure_path, phrasing_map_path, threshold, embedding_url=None, merge_phrasings=True):
    profiles, phrasings = build_profiles(structure_path, phrasing_map_path)
    pairs, method = score_pairs(profiles, threshold, embedding_url)
    payload = {
        "phrasings": phrasings if merge_phrasings else [],
        "similar_pairs": pairs,
        "params": {"threshold": threshold, "method": method, "fines": len(profiles),
                   "merged_phrasing_map": bool(phrasing_map_path and merge_phrasings)},
    }
    return payload


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--structure", required=True, help="runs/<run>/structure-proposal.json")
    p.add_argument("--phrasing-map", default=None, help="runs/<run>/phrasing-map.json（有給則 profile 含講法）")
    p.add_argument("--merge-into", dest="merge", action="store_true", default=True,
                   help="輸出的 payload.phrasings 沿用 --phrasing-map 的講法（預設）")
    p.add_argument("--no-merge", dest="merge", action="store_false",
                   help="輸出的 payload.phrasings 留空陣列（相似清單獨立成一份 envelope）")
    p.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                   help=f"相似門檻，預設 {DEFAULT_THRESHOLD}")
    p.add_argument("--out", required=True)
    p.add_argument("--skill-version", default=SKILL_VERSION)
    a = p.parse_args()

    url = os.environ.get("EMBEDDING_API_URL") or None      # ⛔ 不印出來
    payload = build(a.structure, a.phrasing_map, a.threshold, url, merge_phrasings=a.merge)

    inputs_sha = {"structure": _env.sha256_file(a.structure)}
    if a.phrasing_map:
        inputs_sha["phrasing_map"] = _env.sha256_file(a.phrasing_map)
    env = _env.make_envelope(step="phrasing", skill_version=a.skill_version, inputs_sha=inputs_sha,
                             deterministic=(payload["params"]["method"] == LEXICAL_METHOD),
                             payload=payload, raw_outputs_path=None)
    schema_path = os.path.join(os.path.dirname(_HERE), "schemas", "phrasing-map.json")
    _env.validate(env, _env.load_schema(schema_path))
    _env.write_json(a.out, env)
    print(f"similar-items: 細目 {payload['params']['fines']}｜method {payload['params']['method']}"
          f"｜門檻 {a.threshold}｜待審相似對 {len(payload['similar_pairs'])}（⛔ 未合併任何細目）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
