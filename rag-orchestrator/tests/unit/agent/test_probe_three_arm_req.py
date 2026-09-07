"""unit：`tools/canon/probe_three_arm.py`（spec knowledge-outline-and-intent-architecture・
任務 4.4・H7；Plan `inputs/plan-4.4a-outline-probe-definition-20260907.md` §1 H7／§4）。

全部離線、假 embedding backend（⛔ 不打真 embedding-api，也不真的跑——見模組
docstring「本工具不打真 embedding 跑」）。覆蓋：三臂 recall@1/3/5 計算（沿
`index_eval.rank_fines`／`recall_at_k`）；`--loo article` 拒絕（唯一接受值
`exact`）；缺 `--sub-map` 大聲失敗；phrasing 的 sub 不在 sub-map 大聲失敗；
快取讀寫分工——3.4 主快取唯讀查詢、⛔ 永不覆寫，只寫 `--cache-out`；`--cache-out`
命中時不再呼叫後端。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from types import SimpleNamespace

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))  # tests/unit/agent → rag-orchestrator
_TOOLS_CANON = os.path.join(_RAG, "tools", "canon")

sys.path.insert(0, _RAG)
if _TOOLS_CANON not in sys.path:
    sys.path.insert(0, _TOOLS_CANON)

import tools.canon.index_eval as ie  # noqa: E402
import tools.canon.probe_three_arm as pta  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:4.4")]


# ---------------------------------------------------------------------------
# 共用小夾具
# ---------------------------------------------------------------------------

_CANON_TEXT = """---
audience: prospect
version: test
reviewers: [owner]
language: zh-TW
budget_tokens: 1000
target_user: [prospect]
business_types: [system_provider]
---
## A 測試粗目 {#A}
### 細目一 {#prospect/A/one}
- sources: [helpcenter:art1]
- phrasings:
  - {text: "講法甲", source: "koyu:art1#1", status: approved}
- instance_applicability: general
內容句一。
### 細目二 {#prospect/A/two}
- sources: [helpcenter:art2]
- phrasings:
  - {text: "講法乙", source: "koyu:art2#1", status: approved}
- instance_applicability: general
內容句二。
"""


def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def _write_canon(tmp_path):
    path = str(tmp_path / "prospect.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(_CANON_TEXT)
    return path


def _write_topics(tmp_path, phrasings=None):
    phrasings = phrasings if phrasings is not None else [
        {"q": "問法一", "sub": "subA", "type": "直接", "src": "t"},
        {"q": "問法二", "sub": "subB", "type": "直接", "src": "t"},
    ]
    path = str(tmp_path / "topics-v2.json")
    _write(path, {"_meta": {}, "topics": [{"id": "T1", "phrasings": phrasings, "boundary": []}]})
    return path


def _write_sub_map(tmp_path, mapping):
    path = str(tmp_path / "sub-map.json")
    _write(path, mapping)
    return path


def _fake_vector(text: str) -> list:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [(digest[i % len(digest)] + 1) / 256.0 for i in range(1536)]


class _FakeBackend:
    def __init__(self, none_for=()):
        self._none_for = set(none_for)
        self.calls = 0

    async def embed(self, texts):
        self.calls += 1
        out = []
        for t in texts:
            out.append(None if t in self._none_for else _fake_vector(t))
        return out


class _ExplodingBackend:
    async def embed(self, texts):
        raise AssertionError("不該呼叫後端——快取應命中")


def _args(tmp_path, *, topics_path, sub_map_path, canon_path, loo="exact", backend=None,
          embedding_cache=None, cache_out=None, out_json=None):
    return SimpleNamespace(
        topics=topics_path, sub_map=sub_map_path, canon=canon_path, loo=loo, backend=backend,
        embedding_cache=embedding_cache or str(tmp_path / "primary-cache.json"),
        cache_out=cache_out or str(tmp_path / "cache-out.json"),
        out_json=out_json or str(tmp_path / "out.json"),
    )


# ---------------------------------------------------------------------------
# --loo article 拒絕（唯一接受值 exact）
# ---------------------------------------------------------------------------

def test_loo_article_rejected(tmp_path):
    topics_path = _write_topics(tmp_path)
    sub_map_path = _write_sub_map(tmp_path, {"subA": ["prospect/A/one"], "subB": ["prospect/A/two"]})
    canon_path = _write_canon(tmp_path)
    args = _args(tmp_path, topics_path=topics_path, sub_map_path=sub_map_path, canon_path=canon_path,
                 loo="article", backend=_FakeBackend())
    with pytest.raises(SystemExit) as exc:
        pta.run(args)
    assert exc.value.code == pta.EXIT_FAIL


def test_loo_none_also_rejected(tmp_path):
    topics_path = _write_topics(tmp_path)
    sub_map_path = _write_sub_map(tmp_path, {"subA": [], "subB": []})
    canon_path = _write_canon(tmp_path)
    args = _args(tmp_path, topics_path=topics_path, sub_map_path=sub_map_path, canon_path=canon_path,
                 loo="none", backend=_FakeBackend())
    with pytest.raises(SystemExit) as exc:
        pta.run(args)
    assert exc.value.code == pta.EXIT_FAIL


# ---------------------------------------------------------------------------
# 缺 sub-map／sub 不在 sub-map ⇒ 大聲失敗
# ---------------------------------------------------------------------------

def test_missing_sub_map_fails_loud(tmp_path):
    topics_path = _write_topics(tmp_path)
    canon_path = _write_canon(tmp_path)
    args = _args(tmp_path, topics_path=topics_path,
                 sub_map_path=str(tmp_path / "does-not-exist.json"),
                 canon_path=canon_path, backend=_FakeBackend())
    with pytest.raises(SystemExit) as exc:
        pta.run(args)
    assert exc.value.code == pta.EXIT_FAIL


def test_phrasing_sub_missing_from_map_fails_loud(tmp_path):
    topics_path = _write_topics(tmp_path)
    sub_map_path = _write_sub_map(tmp_path, {"subA": ["prospect/A/one"]})  # subB 缺席
    canon_path = _write_canon(tmp_path)
    args = _args(tmp_path, topics_path=topics_path, sub_map_path=sub_map_path, canon_path=canon_path,
                 backend=_FakeBackend())
    with pytest.raises(SystemExit) as exc:
        pta.run(args)
    assert exc.value.code == pta.EXIT_FAIL


# ---------------------------------------------------------------------------
# 三臂 recall@1/3/5：假向量下形狀正確、mappable 只算 gold 非空的句子
# ---------------------------------------------------------------------------

def test_three_arms_computed_with_fake_vectors(tmp_path):
    topics_path = _write_topics(tmp_path, phrasings=[
        {"q": "問法一", "sub": "subA", "type": "直接", "src": "t"},
        {"q": "問法二", "sub": "subB", "type": "直接", "src": "t"},
        {"q": "問法三（無 gold）", "sub": "subC", "type": "直接", "src": "t"},
    ])
    sub_map_path = _write_sub_map(tmp_path, {
        "subA": ["prospect/A/one"], "subB": ["prospect/A/two"], "subC": [],
    })
    canon_path = _write_canon(tmp_path)
    backend = _FakeBackend()
    args = _args(tmp_path, topics_path=topics_path, sub_map_path=sub_map_path, canon_path=canon_path,
                 backend=backend)
    rc = pta.run(args)
    assert rc == pta.EXIT_OK

    with open(args.out_json, encoding="utf-8") as f:
        report = json.load(f)
    assert report["loo_mode"] == "exact"
    assert report["n"] == 3
    assert report["mappable"] == 2  # subC 的 gold 是空清單 ⇒ 不算 mappable
    assert set(report["arms"].keys()) == {ie.ARM_TITLE, ie.ARM_TITLE_PHRASING, ie.ARM_TITLE_PHRASING_CONTENT}
    for arm_report in report["arms"].values():
        assert arm_report["mappable"] == 2
        for key in ("recall_at_1", "recall_at_3", "recall_at_5"):
            assert arm_report[key] is not None
            assert 0.0 <= arm_report[key] <= 1.0
    assert "canon_sha256" in report and report["canon_sha256"]
    assert report["inputs_sha256"]["topics"] and report["inputs_sha256"]["sub_map"]


def test_compute_three_arm_recall_positive_control():
    """手算：F1 的標題向量與查詢向量同向 ⇒ title 臂 recall@1 應為 1/1。"""
    fine_keys = {
        "F1": {ie.ARM_TITLE: [("title", "F1標題", None)]},
        "F2": {ie.ARM_TITLE: [("title", "F2標題", None)]},
    }
    key_vecs = {
        "F1標題": [1.0] + [0.0] * 1535,
        "F2標題": [0.0, 1.0] + [0.0] * 1534,
    }
    phrasings = [{"q": "查詢句", "gold": ["F1"]}]
    key_vecs["查詢句"] = [1.0] + [0.0] * 1535

    out = {}
    for arm in (ie.ARM_TITLE,):
        hit1 = 0
        ranked = ie.rank_fines(fine_keys, arm, key_vecs["查詢句"], "查詢句", None, "exact")
        assert ranked[0][0] == "F1"
        if ie.recall_at_k(ranked, {"F1"}, 1):
            hit1 += 1
        out[arm] = hit1
    assert out[ie.ARM_TITLE] == 1


# ---------------------------------------------------------------------------
# 快取讀寫分工：3.4 主快取唯讀、⛔ 永不覆寫；命中時不呼叫後端
# ---------------------------------------------------------------------------

def test_never_overwrites_primary_cache(tmp_path):
    primary_path = str(tmp_path / "primary.json")
    ie.write_embedding_cache(primary_path, {})  # 建一份「空」主快取（模擬 3.4 快取存在但鍵不合）
    with open(primary_path, encoding="utf-8") as f:
        primary_before = f.read()

    cache_out_path = str(tmp_path / "cache-out.json")
    backend = _FakeBackend()
    vectors = pta.compute_embeddings_never_overwrite_primary(
        ["甲句", "乙句"], backend, primary_path, cache_out_path,
    )
    assert set(vectors.keys()) == {"甲句", "乙句"}
    assert os.path.isfile(cache_out_path)  # 新快取寫到 cache-out

    with open(primary_path, encoding="utf-8") as f:
        primary_after = f.read()
    assert primary_after == primary_before  # 3.4 主快取檔案位元組不變——⛔ 未被覆寫


def test_cache_out_hit_skips_backend_call(tmp_path):
    primary_path = str(tmp_path / "primary.json")
    cache_out_path = str(tmp_path / "cache-out.json")
    backend = _FakeBackend()
    pta.compute_embeddings_never_overwrite_primary(["甲句"], backend, primary_path, cache_out_path)
    assert backend.calls == 1

    # 第二次呼叫：cache-out 已有精確鍵集合 ⇒ 不該再打後端（爆炸後端證明沒被呼叫）
    vectors = pta.compute_embeddings_never_overwrite_primary(
        ["甲句"], _ExplodingBackend(), primary_path, cache_out_path,
    )
    assert set(vectors.keys()) == {"甲句"}


def test_primary_cache_hit_used_when_keys_match_exactly(tmp_path):
    """正對照：3.4 主快取若鍵集合剛好對得上（極端情況），也該被讀到、⛔ 不強迫重打後端。"""
    primary_path = str(tmp_path / "primary.json")
    cache_out_path = str(tmp_path / "does-not-exist-cache-out.json")
    seed_backend = _FakeBackend()
    import asyncio

    vectors = asyncio.run(seed_backend.embed(["甲句"]))
    ie.write_embedding_cache(primary_path, {ie._cache_key("甲句"): vectors[0]})

    result = pta.compute_embeddings_never_overwrite_primary(
        ["甲句"], _ExplodingBackend(), primary_path, cache_out_path,
    )
    assert set(result.keys()) == {"甲句"}
    assert not os.path.isfile(cache_out_path)  # 命中主快取 ⇒ 不需要另寫 cache-out
