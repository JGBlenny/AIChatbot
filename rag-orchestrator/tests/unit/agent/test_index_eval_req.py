"""unit：`tools/canon/index_eval.py`（spec knowledge-outline-and-intent-architecture 元件 10 步 1・任務 3.4）。

Plan：`.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-3.4-index-eval-20260907.md` §1／§4。
全部離線、假 embedding backend（⛔ 不打真 `embedding-api`）。覆蓋 brief 「Tests」節逐項：
規則重生決定性＋md5 排序；操作／凍結排除；三項全等 exit 2；gold 映射（別名、一對多、unresolved
raw／after-alias、對不到細目的句子計數）；LOO exact／article（正對照：不開 LOO 分數來自被剔除鍵）；
recall@k；misrouted；claim ceiling（<30 ⇒ limited）；None 向量 ⇒ 非 0 退出＋快取未寫入（正對照：
正常向量寫入快取）；`--dry-run` ≥3 型 limited ⇒ exit 3；全跑無核可 ⇒ exit 2；核可後狀態鍵寫入
（用 `CLAUDE_PROJECT_DIR` 指向 tmp repo root 隔離）。
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from types import SimpleNamespace

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_RAG = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))  # tests/unit/agent → tests/unit → tests → rag-orchestrator
_REPO = os.path.dirname(_RAG)

sys.path.insert(0, _RAG)
from tools.canon import index_eval as ie  # noqa: E402

pytestmark = [pytest.mark.unit, pytest.mark.req("knowledge-outline-and-intent-architecture:3.4")]


# ---------------------------------------------------------------------------
# 共用小夾具
# ---------------------------------------------------------------------------

def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(obj, str):
            f.write(obj)
        else:
            json.dump(obj, f, ensure_ascii=False)


def _koyu_doc():
    """2 篇：art1（含操作／邊界，且與凍結題重複一句）、art2（較少型別，供 unmapped／limited 用途）。"""
    return {
        "articles": {
            "art1": {
                "title": "文章一", "phrasings": [
                    {"n": 1, "type": "直接", "q": "art1直接甲"},
                    {"n": 2, "type": "直接", "q": "art1直接乙"},
                    {"n": 3, "type": "口語", "q": "art1口語甲"},
                    {"n": 4, "type": "情境", "q": "art1情境甲"},
                    {"n": 5, "type": "俗稱", "q": "art1俗稱甲"},
                    {"n": 6, "type": "邊界", "q": "art1邊界甲"},
                    {"n": 7, "type": "操作", "q": "art1操作甲（不得入選）"},
                    {"n": 8, "type": "直接", "q": "凍結重複句"},  # 與 topics-v2 凍結題重複
                ],
            },
            "art2": {
                "title": "文章二", "phrasings": [
                    {"n": 1, "type": "直接", "q": "art2直接甲"},
                    {"n": 2, "type": "口語", "q": "art2口語甲"},
                ],
            },
            "art3": {
                "title": "文章三（檔案存在但無細目引用）", "phrasings": [
                    {"n": 1, "type": "直接", "q": "art3直接甲"},
                ],
            },
            "TOFILL-hidden": {
                "title": "髒鍵（別名後解到 art3）", "phrasings": [
                    {"n": 1, "type": "直接", "q": "hidden直接甲"},
                ],
            },
            "artmissing": {
                "title": "無檔案文章", "phrasings": [
                    {"n": 1, "type": "直接", "q": "artmissing直接甲"},
                ],
            },
        }
    }


def _topics_doc():
    """`_collect_q` 會遞迴收集所有 `q`——含「凍結重複句」對應 art1#8。"""
    return {"_meta": {}, "topics": [
        {"id": "T1", "phrasings": [{"q": "凍結重複句", "sub": "s", "type": "直接", "src": "t"}],
         "boundary": [{"q": "邊界凍結句無對應", "sub": "s", "type": "邊界", "src": "t"}]},
    ]}


def _rule_doc(n, by_type, excluded_frozen):
    return {"selection_rule": "test", "n": n, "by_type": by_type, "excluded_frozen": excluded_frozen,
            "sha256": "deadbeef", "source": "test", "frozen_at": "2026-09-06"}


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
  - {text: "art1直接甲", source: "koyu:art1#1", status: approved}
  - {text: "同義講法一", source: "koyu:art1#99", status: approved}
- instance_applicability: general
內容句一。
### 細目二 {#prospect/A/two}
- sources: [helpcenter:art2]
- phrasings:
  - {text: "art2直接甲", source: "koyu:art2#1", status: approved}
- instance_applicability: general
內容句二。
## B 測試粗目 {#B}
### 細目三 {#prospect/B/three}
- sources: [helpcenter:art1]
- phrasings:
  - {text: "細目三講法", source: "helpcenter:art1", status: approved}
- instance_applicability: general
內容句三。
"""


def _make_helpcenter_dir(tmp_path):
    d = tmp_path / "helpcenter"
    d.mkdir()
    (d / "art1_zh-Hant.html").write_text("<html><title>文章一</title></html>", encoding="utf-8")
    (d / "art2_zh-Hant.html").write_text("<html><title>文章二</title></html>", encoding="utf-8")
    (d / "art3_zh-Hant.html").write_text("<html><title>文章三</title></html>", encoding="utf-8")
    return str(d)


def _make_materials(tmp_path):
    koyu_path = str(tmp_path / "koyu.json")
    topics_path = str(tmp_path / "topics.json")
    canon_path = str(tmp_path / "prospect.md")
    _write(koyu_path, _koyu_doc())
    _write(topics_path, _topics_doc())
    _write(canon_path, _CANON_TEXT)
    helpcenter_dir = _make_helpcenter_dir(tmp_path)
    return koyu_path, topics_path, canon_path, helpcenter_dir


# ---------------------------------------------------------------------------
# 422 重生：決定性、md5 排序、操作／凍結排除
# ---------------------------------------------------------------------------

def test_regenerate_is_deterministic_and_md5_ordered(tmp_path):
    koyu_path, topics_path, _canon, _hc = _make_materials(tmp_path)
    frozen = frozenset({ie._pm().norm(q) for q in ie.load_frozen_54(topics_path)})

    s1, by_type1, excl1 = ie.regenerate_422(koyu_path, frozen)
    s2, by_type2, excl2 = ie.regenerate_422(koyu_path, frozen)
    assert s1 == s2 and by_type1 == by_type2 and excl1 == excl2

    # art1 有兩句「直接」候選（art1直接甲／art1直接乙，凍結重複句已被排除）；
    # 手算兩者的 md5 排序、驗證取到的是較小者。
    a = ie._md5_key("art1直接甲")
    b = ie._md5_key("art1直接乙")
    winner = "art1直接甲" if a < b else "art1直接乙"
    picked_direct_for_art1 = next(s["q"] for s in s1 if s["article"] == "art1" and s["type"] == "直接")
    assert picked_direct_for_art1 == winner


def test_regenerate_excludes_op_type_and_frozen(tmp_path):
    koyu_path, topics_path, _canon, _hc = _make_materials(tmp_path)
    frozen = frozenset({ie._pm().norm(q) for q in ie.load_frozen_54(topics_path)})
    sentences, by_type, excluded_frozen = ie.regenerate_422(koyu_path, frozen)

    assert all(s["q"] != "art1操作甲（不得入選）" for s in sentences)   # 操作型排除
    assert all(s["q"] != "凍結重複句" for s in sentences)               # 凍結題排除
    # 「凍結重複句」是唯一與 art1 的直接候選重疊、且真的在凍結集合裡的句子 ⇒ excluded_frozen ≥ 1
    assert excluded_frozen >= 1
    assert "邊界" in by_type  # 邊界型不被排除（只排操作）


def test_three_way_freeze_mismatch_detected(tmp_path):
    koyu_path, topics_path, _canon, _hc = _make_materials(tmp_path)
    frozen = frozenset({ie._pm().norm(q) for q in ie.load_frozen_54(topics_path)})
    sentences, by_type, excluded_frozen = ie.regenerate_422(koyu_path, frozen)
    n = len(sentences)

    ok_rule = _rule_doc(n, by_type, excluded_frozen)
    assert ie.verify_freeze_three_way(ok_rule, n, by_type, excluded_frozen) == []

    bad_rule = _rule_doc(n + 1, by_type, excluded_frozen)
    mismatches = ie.verify_freeze_three_way(bad_rule, n, by_type, excluded_frozen)
    assert mismatches and "n：" in mismatches[0]


# ---------------------------------------------------------------------------
# gold 映射：別名、一對多、unresolved raw／after-alias、對不到細目的句子排除計數
# ---------------------------------------------------------------------------

def _load_canon_fines(canon_path):
    return ie._load_fines(canon_path)


def test_koyu_article_map_alias_and_one_to_many(tmp_path):
    koyu_path, _topics, canon_path, hc_dir = _make_materials(tmp_path)
    fines = _load_canon_fines(canon_path)

    no_alias = ie.build_koyu_article_map(koyu_path, hc_dir, fines, aliases={})
    assert "TOFILL-hidden" in no_alias["unresolved"]
    assert "artmissing" in no_alias["unresolved"]
    # 未套別名 ⇒ after_alias 與 raw 相同（沒有別名表可解）
    assert set(no_alias["unresolved_after_alias"]) == set(no_alias["unresolved"])

    aliased = ie.build_koyu_article_map(koyu_path, hc_dir, fines, aliases={"TOFILL-hidden": "art3"})
    assert "TOFILL-hidden" not in aliased["unresolved_after_alias"]
    assert "artmissing" in aliased["unresolved_after_alias"]  # 沒給別名的仍解不開

    # 一篇（art1）對多細目（prospect/A/one 與 prospect/B/three 皆 sources 含 helpcenter:art1）
    assert sorted(aliased["articles"]["art1"]["fine_ids"]) == ["prospect/A/one", "prospect/B/three"]
    # art3 檔案存在但沒有任何細目引用 ⇒ file_exists True、fine_ids 空
    assert aliased["articles"]["art3"]["file_exists"] is True
    assert aliased["articles"]["art3"]["fine_ids"] == []


def test_unmapped_sentence_is_excluded_and_counted(tmp_path):
    koyu_path, topics_path, canon_path, hc_dir = _make_materials(tmp_path)
    fines = _load_canon_fines(canon_path)
    frozen = frozenset({ie._pm().norm(q) for q in ie.load_frozen_54(topics_path)})
    sentences, _by_type, _excl = ie.regenerate_422(koyu_path, frozen)
    article_map = ie.build_koyu_article_map(koyu_path, hc_dir, fines, aliases={"TOFILL-hidden": "art3"})

    art3_sentence = next(s for s in sentences if s["article"] == "art3")
    assert ie.gold_for_sentence(art3_sentence, article_map) == []  # 檔案存在但無細目引用 ⇒ 空 gold

    artmissing_sentence = next(s for s in sentences if s["article"] == "artmissing")
    assert ie.gold_for_sentence(artmissing_sentence, article_map) == []  # 連檔案都沒有

    mappable = ie.mappable_counts_by_type(sentences, article_map)
    direct = mappable["直接"]
    # total 含 art1/art2/art3/TOFILL-hidden/artmissing 的「直接」句；只有 art1／art2 對得到細目。
    assert direct["mappable"] == 2
    assert direct["total"] >= direct["mappable"]


# ---------------------------------------------------------------------------
# claim ceiling（<30 ⇒ limited）
# ---------------------------------------------------------------------------

def test_limited_types_threshold():
    mappable = {"直接": {"mappable": 29, "total": 40}, "口語": {"mappable": 30, "total": 40},
                "情境": {"mappable": 5, "total": 40}}
    limited = ie.limited_types(mappable)
    assert limited == ["情境", "直接"]  # 30 剛好不算 limited；29／5 算


# ---------------------------------------------------------------------------
# --dry-run：≥3 型 limited ⇒ exit 3；三項不等 ⇒ exit 2
# ---------------------------------------------------------------------------

def _dry_args(tmp_path, koyu_path, topics_path, canon_path, hc_dir, rule_path):
    return SimpleNamespace(
        canon=canon_path, koyu=koyu_path, rule=rule_path, topics=topics_path,
        helpcenter_dir=hc_dir, rule_sha_recompute_dir=str(tmp_path / "no-such-dir"),
        article_map_out=str(tmp_path / "koyu-article-map.json"),
    )


def _frozen_and_regen(koyu_path, topics_path):
    frozen = frozenset({ie._pm().norm(q) for q in ie.load_frozen_54(topics_path)})
    return ie.regenerate_422(koyu_path, frozen)


def test_dry_run_exit3_when_three_or_more_types_limited(tmp_path):
    koyu_path, topics_path, canon_path, hc_dir = _make_materials(tmp_path)
    sentences, by_type, excluded_frozen = _frozen_and_regen(koyu_path, topics_path)
    rule_path = str(tmp_path / "rule.json")
    _write(rule_path, _rule_doc(len(sentences), by_type, excluded_frozen))

    args = _dry_args(tmp_path, koyu_path, topics_path, canon_path, hc_dir, rule_path)
    rc = ie.run_dry(args)
    # 這個小語料每型可對映句遠低於 30（只有 art1/art2 兩篇有 gold）⇒ 全部型都 limited ⇒ exit 3
    assert rc == 3


def test_dry_run_exit2_on_freeze_mismatch(tmp_path):
    koyu_path, topics_path, canon_path, hc_dir = _make_materials(tmp_path)
    sentences, by_type, excluded_frozen = _frozen_and_regen(koyu_path, topics_path)
    rule_path = str(tmp_path / "rule.json")
    _write(rule_path, _rule_doc(len(sentences) + 1, by_type, excluded_frozen))  # 刻意錯

    args = _dry_args(tmp_path, koyu_path, topics_path, canon_path, hc_dir, rule_path)
    rc = ie.run_dry(args)
    assert rc == 2


def test_dry_run_exit2_on_missing_helpcenter_dir(tmp_path):
    koyu_path, topics_path, canon_path, _hc = _make_materials(tmp_path)
    sentences, by_type, excluded_frozen = _frozen_and_regen(koyu_path, topics_path)
    rule_path = str(tmp_path / "rule.json")
    _write(rule_path, _rule_doc(len(sentences), by_type, excluded_frozen))

    args = _dry_args(tmp_path, koyu_path, topics_path, canon_path, str(tmp_path / "no-such-helpcenter-dir"), rule_path)
    with pytest.raises(SystemExit) as exc:
        ie.run_dry(args)
    assert exc.value.code == 2


# ---------------------------------------------------------------------------
# LOO exact／article（正對照：不開 LOO 分數來自被剔除鍵）＋ recall@k ＋ misrouted
# ---------------------------------------------------------------------------

def _fake_vector(text: str) -> list:
    """決定性假向量（1536 維，同文字必同向量）。"""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    base = [(digest[i % len(digest)] + 1) / 256.0 for i in range(1536)]
    return base


def test_loo_exact_excludes_literal_match_key():
    fine_keys = {
        "F1": {ie.ARM_TITLE_PHRASING: [("title", "標題F1", None), ("phrasing", "剔除句", None)]},
    }
    ie._KEY_VECS = {"標題F1": _fake_vector("標題F1"), "剔除句": _fake_vector("剔除句")}
    q_vec = _fake_vector("剔除句")  # 查詢句與某把講法鍵文字完全相同

    # 正對照：不開 LOO（none 模式當作無過濾）⇒ 分數應恰為該鍵與自身的餘弦（=1.0）
    score_no_loo = ie.score_fine_for_query(
        fine_keys["F1"][ie.ARM_TITLE_PHRASING], q_vec, "剔除句", None, loo_mode="none")
    assert score_no_loo == pytest.approx(1.0, abs=1e-6)

    # exact LOO ⇒ 該鍵被剔除，分數來自標題鍵（≠1.0，除非湊巧）
    score_loo = ie.score_fine_for_query(
        fine_keys["F1"][ie.ARM_TITLE_PHRASING], q_vec, "剔除句", None, loo_mode="exact")
    assert score_loo != pytest.approx(1.0, abs=1e-6)


def test_loo_article_excludes_same_source_article_keys():
    fine_keys = {
        "F1": {ie.ARM_TITLE_PHRASING: [
            ("title", "標題F1", None),
            ("phrasing", "同文章講法", "art1"),
        ]},
    }
    ie._KEY_VECS = {"標題F1": _fake_vector("標題F1"), "同文章講法": _fake_vector("同文章講法")}
    q_vec = _fake_vector("查詢句本身不同字")

    # 正對照：不開 LOO（none）可能挑中同文章講法鍵
    no_loo_best = max(
        ie._cosine(ie._KEY_VECS["標題F1"], q_vec), ie._cosine(ie._KEY_VECS["同文章講法"], q_vec)
    )
    score_no_loo = ie.score_fine_for_query(
        fine_keys["F1"][ie.ARM_TITLE_PHRASING], q_vec, "查詢句本身不同字", "art1", loo_mode="none")
    assert score_no_loo == pytest.approx(no_loo_best, abs=1e-6)

    score_loo = ie.score_fine_for_query(
        fine_keys["F1"][ie.ARM_TITLE_PHRASING], q_vec, "查詢句本身不同字", "art1", loo_mode="article")
    title_only = ie._cosine(ie._KEY_VECS["標題F1"], q_vec)
    assert score_loo == pytest.approx(title_only, abs=1e-6)


def test_recall_at_k_and_ranking_order():
    fine_keys = {
        "F1": {ie.ARM_TITLE: [("title", "甲標題", None)]},
        "F2": {ie.ARM_TITLE: [("title", "乙標題", None)]},
    }
    ie._KEY_VECS = {"甲標題": [1.0] + [0.0] * 1535, "乙標題": [0.0, 1.0] + [0.0] * 1534}
    q_vec = [1.0] + [0.0] * 1535  # 與 F1 完全相同方向

    ranked = ie.rank_fines(fine_keys, ie.ARM_TITLE, q_vec, "隨便問句", None, loo_mode="none")
    assert ranked[0][0] == "F1"
    assert ie.recall_at_k(ranked, {"F1"}, 1) is True
    assert ie.recall_at_k(ranked, {"F2"}, 1) is False
    assert ie.recall_at_k(ranked, {"F2"}, 2) is True  # top-2 含 F2


def test_misrouted_flags_winning_phrasing_outside_gold():
    fine_keys = {
        "F1": {ie.ARM_TITLE_PHRASING_CONTENT: [("title", "F1標題", None), ("phrasing", "誤掛講法", None)]},
        "GOLD": {ie.ARM_TITLE_PHRASING_CONTENT: [("title", "GOLD標題", None)]},
    }
    ie._KEY_VECS = {
        # 標題向量刻意與 query 正交（cos=0），只有「誤掛講法」與 query 同向（cos=1）——
        # 避免同向不同長度的向量給出相同 cosine，讓「哪把鍵贏」可判定。
        "F1標題": [0.0, 0.1] + [0.0] * 1534, "誤掛講法": [1.0] + [0.0] * 1535,
        "GOLD標題": [0.0, 0.2] + [0.0] * 1534,
    }
    q_vec = [1.0] + [0.0] * 1535
    sentence = {"article": "artX", "type": "直接"}
    ranked = ie.rank_fines(fine_keys, ie.ARM_TITLE_PHRASING_CONTENT, q_vec, "查詢句", None, loo_mode="none")
    assert ranked[0][0] == "F1"  # 誤掛講法分數最高，勝出但 F1 不在 gold
    mr = ie.misrouted_for_query(sentence, ranked, {"GOLD"}, fine_keys, ie.ARM_TITLE_PHRASING_CONTENT,
                                 q_vec, "查詢句", None, loo_mode="none")
    assert mr is not None
    assert mr["winning_fine_id"] == "F1"


# ---------------------------------------------------------------------------
# embedding：None 向量 ⇒ 非 0 退出、快取未寫入（正對照：正常向量寫入快取）
# ---------------------------------------------------------------------------

class _FakeBackend:
    def __init__(self, none_for=()):
        self._none_for = set(none_for)

    async def embed(self, texts):
        out = []
        for t in texts:
            if t in self._none_for:
                out.append(None)
            else:
                out.append(_fake_vector(t))
        return out


def test_compute_embeddings_writes_cache_on_success(tmp_path):
    cache_path = str(tmp_path / "embeddings.json")
    backend = _FakeBackend()
    vectors = ie.compute_embeddings(["甲句", "乙句"], backend, cache_path)
    assert set(vectors.keys()) == {"甲句", "乙句"}
    assert os.path.isfile(cache_path)
    with open(cache_path, encoding="utf-8") as f:
        cached = json.load(f)
    assert cached["dim"] == 1536
    assert len(cached["vectors"]) == 2


def test_compute_embeddings_fails_loud_on_none_and_no_cache_write(tmp_path):
    cache_path = str(tmp_path / "embeddings.json")
    backend = _FakeBackend(none_for={"乙句"})
    with pytest.raises(SystemExit) as exc:
        ie.compute_embeddings(["甲句", "乙句"], backend, cache_path)
    assert exc.value.code != 0
    assert not os.path.isfile(cache_path)


def test_embedding_cache_reload_validated_by_dim_and_keys(tmp_path):
    cache_path = str(tmp_path / "embeddings.json")
    backend = _FakeBackend()
    ie.compute_embeddings(["甲句", "乙句"], backend, cache_path)

    # 校驗通過 ⇒ 第二次呼叫不再呼叫後端（用一個會 raise 的後端證明沒被呼叫到）
    class _ExplodingBackend:
        async def embed(self, texts):
            raise AssertionError("不該呼叫後端——快取應命中")

    vectors = ie.compute_embeddings(["甲句", "乙句"], _ExplodingBackend(), cache_path)
    assert set(vectors.keys()) == {"甲句", "乙句"}

    # 鍵數對不上 ⇒ 快取不採信，會重算（用假後端而非爆炸後端）
    vectors2 = ie.compute_embeddings(["甲句", "乙句", "丙句"], _FakeBackend(), cache_path)
    assert set(vectors2.keys()) == {"甲句", "乙句", "丙句"}


# ---------------------------------------------------------------------------
# 全跑前置：無核可 ⇒ exit 2；核可後 ⇒ 狀態鍵寫入（temp repo root via CLAUDE_PROJECT_DIR）
# ---------------------------------------------------------------------------

def _tmp_repo_root(tmp_path):
    root = tmp_path / "tmp-repo"
    (root / ".claude" / "hooks" / "state" / "outline-gate").mkdir(parents=True)
    (root / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    (root / ".kiro" / "specs" / "knowledge-outline-and-intent-architecture" / "inputs").mkdir(parents=True)
    return root


def test_full_run_refuses_without_approval(tmp_path, monkeypatch):
    root = _tmp_repo_root(tmp_path)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    oud_rel = os.path.join(".kiro", "specs", "knowledge-outline-and-intent-architecture", "inputs",
                            "object-under-test.md")
    # 核可欄空白（沒有值）
    oud_path = root / oud_rel
    oud_path.write_text("核可：\n", encoding="utf-8")

    koyu_path, topics_path, canon_path, hc_dir = _make_materials(tmp_path)
    sentences, by_type, excluded_frozen = _frozen_and_regen(koyu_path, topics_path)
    rule_path = str(tmp_path / "rule.json")
    _write(rule_path, _rule_doc(len(sentences), by_type, excluded_frozen))

    args = SimpleNamespace(
        canon=canon_path, koyu=koyu_path, rule=rule_path, topics=topics_path, helpcenter_dir=hc_dir,
        rule_sha_recompute_dir=str(tmp_path / "no-such-dir"), object_under_test=oud_rel,
        map_v2=str(tmp_path / "map-v2.json"), answerability_canon=str(tmp_path / "canon-v3.json"),
        embedding_cache=str(tmp_path / "embeddings.json"), out_json=str(tmp_path / "out.json"),
        out_md=str(tmp_path / "out.md"),
    )
    rc = ie.run_full(args)
    assert rc == 2


def test_full_run_with_approval_writes_state_keys(tmp_path, monkeypatch):
    root = _tmp_repo_root(tmp_path)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    oud_rel = os.path.join(".kiro", "specs", "knowledge-outline-and-intent-architecture", "inputs",
                            "object-under-test.md")
    oud_path = root / oud_rel
    oud_path.write_text("核可：owner-2026-09-07\n", encoding="utf-8")

    koyu_path, topics_path, canon_path, hc_dir = _make_materials(tmp_path)

    # 第二份材料（55 格）夾具：只需最小可用形狀（1 格，非 deliberate_no）。
    map_v2_path = str(tmp_path / "map-v2.json")
    _write(map_v2_path, {"_meta": {}, "cells": [{"id": "C01", "questions": ["代表問句"]}]})
    canon_v3_path = str(tmp_path / "canon-v3.json")
    _write(canon_v3_path, {"payload": {"labels": [
        {"cell_id": "C01", "label": "answerable", "fine_id": "prospect/A/one"},
    ]}})

    sentences, by_type, excluded_frozen = _frozen_and_regen(koyu_path, topics_path)
    rule_path = str(tmp_path / "rule.json")
    _write(rule_path, _rule_doc(len(sentences), by_type, excluded_frozen))

    embedding_cache = str(tmp_path / "embeddings.json")

    import tools.canon.index_eval as ie_mod

    class _AlwaysBackend:
        async def embed(self, texts):
            return [_fake_vector(t) for t in texts]

    monkeypatch.setattr(ie_mod, "_load_module_from_path",
                         ie_mod._load_module_from_path)  # no-op，確保仍走真實 infra 載入

    def _fake_ensure_backend():
        return _AlwaysBackend()

    # 直接 monkeypatch run_full 內對 EmbeddingUtilsBackend 的取用點：改用 import hook。
    import types
    fake_fine_index_mod = types.ModuleType("services.agent.canon.fine_index")
    fake_fine_index_mod.EmbeddingUtilsBackend = _AlwaysBackend
    monkeypatch.setitem(sys.modules, "services.agent.canon.fine_index", fake_fine_index_mod)

    args = SimpleNamespace(
        canon=canon_path, koyu=koyu_path, rule=rule_path, topics=topics_path, helpcenter_dir=hc_dir,
        rule_sha_recompute_dir=str(tmp_path / "no-such-dir"), object_under_test=oud_rel,
        map_v2=map_v2_path, answerability_canon=canon_v3_path,
        embedding_cache=embedding_cache, out_json=str(tmp_path / "out.json"),
        out_md=str(tmp_path / "out.md"),
    )
    rc = ie_mod.run_full(args)
    assert rc == 0
    assert os.path.isfile(args.out_json)
    assert os.path.isfile(args.out_md)

    state_path = root / ".claude" / "hooks" / "state" / "outline-gate" / "session.json"
    with open(state_path, encoding="utf-8") as f:
        state = json.load(f)
    assert "index_eval" in state["evals_ran"]
    assert state["materials_frozen"] is True
    assert state["object_under_test_path"] == oud_rel


def test_repo_relative_normalises_absolute_and_rejects_escape(tmp_path):
    root = str(tmp_path / "repo")
    os.makedirs(root, exist_ok=True)
    rel = os.path.join(".kiro", "specs", "x", "inputs", "object-under-test.md")
    # 容器內的絕對路徑（verifier 抓到的 P3：曾把 /.kiro/... 寫進 session.json）
    assert ie._repo_relative(os.path.join(root, rel), root) == rel
    # 已是相對路徑 ⇒ 原樣（normpath）
    assert ie._repo_relative(rel, root) == rel
    # 逃出 repo ⇒ 空字串（object_under_test_approved 會拒絕）
    assert ie._repo_relative(os.path.join(root, "..", "outside.md"), root) == ""
    assert ie._repo_relative("../outside.md", root) == ""
