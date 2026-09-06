"""步 1 離線量測：`tools/canon/index_eval.py`（spec knowledge-outline-and-intent-architecture 元件 10 步 1；
Plan `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-3.4-index-eval-20260907.md`）。

三臂（只標題／標題＋approved 講法／再加內文）對 38 細目量 recall@1/3/5，gold 由「文章→細目」決定性對映
（細目 `sources` 含 `helpcenter:<slug>`），$0（本機 embedding，`EmbeddingUtilsBackend`）；⛔ 不派判者。

`--dry-run` 是硬閘門：只做材料凍結／422 重生／gold 映射／可對映句計數，**不打 embedding**；
全跑（打 embedding、寫 session 狀態）需要 `inputs/object-under-test.md` 核可欄非空。

⛔ 不 log 查詢句以外的任何個資（句子本身是業主正本材料，可寫進 `inputs/` 輸出）。
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import unicodedata
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_VERSION = "0.1.0"

DEFAULT_HELPCENTER_DIR = "/Users/lenny/jgb/幫助中心/JGB幫助中心_HTML_交付_20260818"
HELPCENTER_SUFFIX = "_zh-Hant.html"

KOYU_ALL_NON_OP_TYPES = ("直接", "口語", "情境", "俗稱", "邊界")
EXPECTED_N = 422
EXPECTED_EXCLUDED_FROZEN = 48
EXPECTED_FROZEN_SET_SIZE = 54
MAPPABLE_LIMITED_THRESHOLD = 30
MIN_LIMITED_TYPES_FOR_HARD_STOP = 3

MD5_SALT = "presales-s1-2026-09-06:"

# 三個髒鍵 → 別名（§7.1 業主核准：三個都視為同一篇）。
DEFAULT_ALIASES = {
    "TOFILL-beike": "beike",
    "TOFILL-repair": "repair",
    "property（原": "property",
}

DELIBERATE_LABELS_EXCLUDED = frozenset({"deliberate_no", "no_source"})


# ---------------------------------------------------------------------------
# repo 根與動態載入（同一套技巧見 phrasing_map.py `_load_hook`／`_load_sibling`）
# ---------------------------------------------------------------------------

def find_repo_root() -> str:
    """**資料根**（狀態檔／`object-under-test.md`／CLI 相對路徑解析用）：與 `_envelope.find_repo_root` 同一套
    契約——`CLAUDE_PROJECT_DIR` 優先，否則從 cwd 往上找 `.claude/settings.json`；⛔ 不用 `__file__` 推——
    測試要能用 tmp repo root 隔離狀態檔（brief：「approval present ⇒ state keys written (use a temp repo
    root via CLAUDE_PROJECT_DIR)」），與 `_infra_root()`（見下）刻意分開。"""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return env
    cur = os.path.abspath(os.getcwd())
    while True:
        if os.path.isfile(os.path.join(cur, ".claude", "settings.json")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            raise RuntimeError("找不到 repo 根：CLAUDE_PROJECT_DIR 未設，且 cwd 往上無 .claude/settings.json")
        cur = parent


def _rag_root() -> str:
    """`rag-orchestrator/` 本身的位置（`services.*` 這些 runtime 套件的根）：⛔ 不透過 repo 根推算——
    容器內這棵樹掛在 `/app`（非 `<repo根>/rag-orchestrator`），只有從本檔位置往上兩層
    （`tools/canon`→`tools`→`rag-orchestrator`）在 host／容器兩種佈局下都對。"""
    return os.path.dirname(os.path.dirname(_HERE))


def _infra_root() -> str:
    """**repo 根**（載入 `phrasing_map.py`／`outline_gate.py`／`_envelope.py` 這些 `.claude/` 下的共用
    基礎設施用）：一律用 `__file__` 往上推，⛔ 不受 `CLAUDE_PROJECT_DIR` 影響——這些是本檔的程式相依，
    不是測試要隔離的資料，同 `phrasing_map.py::_load_hook` 的 `up4` 手法。host：`_rag_root()` 的上一層；
    容器：`_rag_root()`＝`/app`，上一層＝`/`，恰好對上 `.claude` 的掛載點 `/.claude`。"""
    return os.path.dirname(_rag_root())


def _load_module_from_path(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _find_under_repo_root(rel_path: str):
    """容器內 `.claude` 掛在 `/.claude`（見 phrasing_map.py 同名註解），補一個 `/` 候選。"""
    for base in (_infra_root(), "/"):
        p = os.path.join(base, rel_path)
        if os.path.isfile(p):
            return p
    raise RuntimeError(f"找不到 {rel_path}（repo 根候選皆無）")


_phrasing_map = None
_outline_gate = None
_envelope = None


def _pm():
    global _phrasing_map
    if _phrasing_map is None:
        _phrasing_map = _load_module_from_path(
            "phrasing_map",
            _find_under_repo_root(os.path.join(".claude", "skills", "outline-curation", "scripts", "phrasing_map.py")),
        )
    return _phrasing_map


def _hook():
    global _outline_gate
    if _outline_gate is None:
        _outline_gate = _load_module_from_path(
            "outline_gate", _find_under_repo_root(os.path.join(".claude", "hooks", "outline_gate.py"))
        )
    return _outline_gate


def _env():
    global _envelope
    if _envelope is None:
        _envelope = _load_module_from_path(
            "_envelope",
            _find_under_repo_root(os.path.join(".claude", "skills", "outline-curation", "scripts", "_envelope.py")),
        )
    return _envelope


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 材料凍結
# ---------------------------------------------------------------------------

class MaterialFreezeError(SystemExit):
    def __init__(self, msg: str):
        print(f"[index_eval] 材料凍結失敗：{msg}", file=sys.stderr)
        super().__init__(2)


def load_frozen_54(topics_path: str) -> list:
    """`topics-v2.json` 全部 `q`（遞迴收集，與判定 5 `_collect_q` 同一支）；回傳原始清單（保序、含重複）。"""
    doc = _load_json(topics_path)
    out: list = []
    _hook()._collect_q(doc, out)
    return out


def freeze_materials(canon_path: str, koyu_path: str, rule_path: str, topics_path: str,
                      helpcenter_dir: str, rule_sha_recompute_dir: str | None = None) -> dict:
    """材料凍結：讀四份材料＋算 sha；不合格（幫助中心目錄缺）⇒ exit 2。回傳輸入 sha 與衍生值。"""
    if not os.path.isdir(helpcenter_dir):
        raise MaterialFreezeError(f"--helpcenter-dir 不存在：{helpcenter_dir}")

    canon_sha = sha256_file(canon_path)
    koyu_sha = sha256_file(koyu_path)
    rule_sha = sha256_file(rule_path)
    topics_sha = sha256_file(topics_path)
    helpcenter_dir_sha = _pm().dir_digest(helpcenter_dir, HELPCENTER_SUFFIX)

    rule = _load_json(rule_path)
    frozen_54 = load_frozen_54(topics_path)

    rule_sha256_recomputed = None
    rule_sha256_note = "sha 原計法未留"
    if rule_sha_recompute_dir and os.path.isdir(rule_sha_recompute_dir):
        # 規則檔本身沒留原計法腳本；本函式只做「有沒有找到」的查證，不臆測計法。
        rule_sha256_note = "sha 原計法未留（raw/phrasing-20260906/ 下無計算腳本）"

    return {
        "canon_sha256": canon_sha,
        "koyu_sha256": koyu_sha,
        "rule_file_sha256": rule_sha,
        "rule_file_declared_sha256": rule.get("sha256"),
        "rule_sha256_recomputed": rule_sha256_recomputed,
        "rule_sha256_note": rule_sha256_note,
        "topics_v2_sha256": topics_sha,
        "helpcenter_dir_sha256": helpcenter_dir_sha,
        "rule": rule,
        "frozen_54_raw": frozen_54,
    }


# ---------------------------------------------------------------------------
# 422 句重生
# ---------------------------------------------------------------------------

def _md5_key(q: str) -> str:
    return hashlib.md5((MD5_SALT + q).encode("utf-8")).hexdigest()


def regenerate_422(koyu_path: str, frozen_norm_set: frozenset) -> tuple:
    """依規則重生 422 句：每篇每型（直接/口語/情境/俗稱/邊界）各取 1 句——排除操作型與凍結題後，
    以 `md5(SALT+q)` 升冪取第一。回傳 (sentences, by_type, excluded_frozen_recomputed)。

    `sentences` 每筆：{article, type, q, source（=`koyu:<article>#<n>`）}。
    """
    doc = _load_json(koyu_path)
    arts = doc["articles"]
    norm = _pm().norm

    sentences = []
    by_type: dict = {}
    excluded_frozen = 0
    for slug in sorted(arts):
        by_type_pool: dict = defaultdict(list)
        for p in arts[slug].get("phrasings", []):
            t = p.get("type")
            if t == "操作":
                continue
            if t not in KOYU_ALL_NON_OP_TYPES:
                continue
            q = str(p["q"])
            if norm(q) in frozen_norm_set:
                excluded_frozen += 1
                continue
            by_type_pool[t].append({"article": slug, "type": t, "q": q,
                                     "source": f"koyu:{slug}#{p['n']}"})
        for t in KOYU_ALL_NON_OP_TYPES:
            pool = by_type_pool.get(t) or []
            if not pool:
                continue
            pool.sort(key=lambda r: _md5_key(r["q"]))
            picked = pool[0]
            sentences.append(picked)
            by_type[t] = by_type.get(t, 0) + 1

    return sentences, dict(sorted(by_type.items())), excluded_frozen


def verify_freeze_three_way(rule: dict, n: int, by_type: dict, excluded_frozen_recomputed: int) -> list:
    """三項全等：n／by_type／excluded_frozen_recomputed。回不相等清單（空＝全等）。"""
    mismatches = []
    if n != rule.get("n"):
        mismatches.append(f"n：規則檔 {rule.get('n')} vs 重生 {n}")
    if by_type != rule.get("by_type"):
        mismatches.append(f"by_type：規則檔 {rule.get('by_type')} vs 重生 {by_type}")
    if excluded_frozen_recomputed != rule.get("excluded_frozen"):
        mismatches.append(
            f"excluded_frozen：規則檔 {rule.get('excluded_frozen')} vs 重算 {excluded_frozen_recomputed}"
        )
    return mismatches


# ---------------------------------------------------------------------------
# gold 映射（文章 → 細目）
# ---------------------------------------------------------------------------

def _fine_helpcenter_slugs(fine) -> list:
    out = []
    for s in fine.sources:
        if s.startswith("helpcenter:"):
            out.append(s[len("helpcenter:"):])
    return out


def build_koyu_article_map(koyu_path: str, helpcenter_dir: str, fines, aliases: dict) -> dict:
    """`inputs/koyu-article-map.json` 的內容：article 鍵 → 檔案存在？→ 細目 id 集合；
    ＋ `unresolved`（原始，對不到檔案）／`unresolved_after_alias`（套別名後仍對不到）。

    別名只影響「找不找得到檔案」，不改變鍵本身在輸出裡的呈現（鍵仍是原始 koyu 鍵）。
    """
    doc = _load_json(koyu_path)
    keys = sorted(doc["articles"].keys())
    files = set(os.listdir(helpcenter_dir))

    slug_to_fines: dict = defaultdict(list)
    for f in fines:
        for slug in _fine_helpcenter_slugs(f):
            slug_to_fines[slug].append(f.id)
    for slug in slug_to_fines:
        slug_to_fines[slug] = sorted(set(slug_to_fines[slug]))

    unresolved = []
    unresolved_after_alias = []
    articles: dict = {}
    for key in keys:
        candidate_slug = key
        file_exists = f"{candidate_slug}{HELPCENTER_SUFFIX}" in files
        if not file_exists:
            unresolved.append(key)
            aliased = aliases.get(key)
            if aliased is not None:
                candidate_slug = aliased
                file_exists = f"{candidate_slug}{HELPCENTER_SUFFIX}" in files
            if not file_exists:
                unresolved_after_alias.append(key)
        articles[key] = {
            "slug": candidate_slug,
            "file_exists": file_exists,
            "fine_ids": slug_to_fines.get(candidate_slug, []),
        }

    return {
        "articles": articles,
        "unresolved": sorted(unresolved),
        "unresolved_after_alias": sorted(unresolved_after_alias),
    }


def articles_with_gold_count(article_map: dict) -> int:
    return sum(1 for a in article_map["articles"].values() if a["file_exists"] and a["fine_ids"])


def gold_for_sentence(sentence: dict, article_map: dict) -> list:
    """句子的 gold 細目 id 集合；文章對不到任何細目 ⇒ 空清單（呼叫端據此排除並計數）。"""
    info = article_map["articles"].get(sentence["article"])
    if not info or not info["file_exists"]:
        return []
    return info["fine_ids"]


# ---------------------------------------------------------------------------
# 可對映句計數（dry-run 用；不需要 embedding）
# ---------------------------------------------------------------------------

def mappable_counts_by_type(sentences: list, article_map: dict) -> dict:
    """每型「可對映句數」＝gold 非空的句子數。"""
    counts: dict = {}
    for s in sentences:
        gold = gold_for_sentence(s, article_map)
        counts.setdefault(s["type"], {"mappable": 0, "total": 0})
        counts[s["type"]]["total"] += 1
        if gold:
            counts[s["type"]]["mappable"] += 1
    return dict(sorted(counts.items()))


def limited_types(mappable: dict, threshold: int = MAPPABLE_LIMITED_THRESHOLD) -> list:
    return sorted(t for t, c in mappable.items() if c["mappable"] < threshold)


# ---------------------------------------------------------------------------
# 三臂鍵集合（來自正本 CanonDoc；full-run 用）
# ---------------------------------------------------------------------------

ARM_TITLE = "title"
ARM_TITLE_PHRASING = "title+phrasing"
ARM_TITLE_PHRASING_CONTENT = "title+phrasing+content"
ARMS = (ARM_TITLE, ARM_TITLE_PHRASING, ARM_TITLE_PHRASING_CONTENT)


def _phrasing_article(source: str):
    """從講法 `source` 抽出文章 slug（LOO article 用）；抽不到 ⇒ None。"""
    if source.startswith("koyu:"):
        rest = source[len("koyu:"):]
        return rest.split("#", 1)[0]
    if source.startswith("helpcenter:"):
        return source[len("helpcenter:"):]
    return None


def build_fine_keys(fines) -> dict:
    """`{fine_id: {arm: [(key_kind, text, article_or_None), ...]}}`（title／phrasing 用 approved／content_units）。"""
    out: dict = {}
    for f in fines:
        title_key = ("title", f.title, None)
        phrasing_keys = [
            ("phrasing", p.text, _phrasing_article(p.source))
            for p in f.phrasings if p.status == "approved"
        ]
        content_keys = [("content", u, None) for u in f.content_units]
        out[f.id] = {
            ARM_TITLE: [title_key],
            ARM_TITLE_PHRASING: [title_key] + phrasing_keys,
            ARM_TITLE_PHRASING_CONTENT: [title_key] + phrasing_keys + content_keys,
        }
    return out


def all_index_texts(fine_keys: dict) -> list:
    texts = set()
    for arms in fine_keys.values():
        for keys in arms.values():
            for _kind, text, _art in keys:
                texts.add(text)
    return sorted(texts)


# ---------------------------------------------------------------------------
# embedding 快取
# ---------------------------------------------------------------------------

def _cache_key(text: str) -> str:
    return sha256_text(unicodedata.normalize("NFKC", text))


def load_embedding_cache(cache_path: str, expected_keys: set) -> dict:
    if not os.path.isfile(cache_path):
        return {}
    try:
        raw = _load_json(cache_path)
    except (OSError, json.JSONDecodeError):
        return {}
    vectors = raw.get("vectors") if isinstance(raw, dict) else None
    if not isinstance(vectors, dict):
        return {}
    # 校驗：維度＝1536 且筆數＝鍵數；不符 ⇒ 不採信（呼叫端會重算）。
    if set(vectors.keys()) != set(expected_keys):
        return {}
    for v in vectors.values():
        if not isinstance(v, list) or len(v) != 1536:
            return {}
    return vectors


def write_embedding_cache(cache_path: str, vectors: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(cache_path)), exist_ok=True)
    tmp = cache_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"dim": 1536, "vectors": vectors}, f, ensure_ascii=False)
    os.replace(tmp, cache_path)


class EmbeddingFailure(SystemExit):
    def __init__(self, msg: str):
        print(f"[index_eval] embedding 失敗：{msg}", file=sys.stderr)
        super().__init__(4)


def compute_embeddings(texts: list, backend, cache_path: str) -> dict:
    """回 `{text: vector}`；任一 `None`／維度≠1536 ⇒ 大聲失敗（exit 4）、⛔ 不寫快取。

    `backend` 需提供 async `embed(list[str]) -> list[Optional[list[float]]]`（同 `EmbeddingBackend` 協定）。
    """
    keys = sorted(set(texts))
    cache_keys = {_cache_key(t) for t in keys}
    cached = load_embedding_cache(cache_path, cache_keys)
    if cached:
        return {t: cached[_cache_key(t)] for t in keys}

    vectors = asyncio.run(backend.embed(keys))
    if not isinstance(vectors, (list, tuple)) or len(vectors) != len(keys):
        raise EmbeddingFailure(f"後端回傳筆數不符（要 {len(keys)} 筆）")

    failed = 0
    out: dict = {}
    for t, v in zip(keys, vectors):
        if v is None or not isinstance(v, (list, tuple)) or len(v) != 1536:
            failed += 1
            continue
        out[t] = list(v)
    if failed:
        raise EmbeddingFailure(f"{failed}/{len(keys)} 筆向量缺漏或維度不符（1536）⇒ 大聲失敗，快取未寫入")

    cache_payload = {_cache_key(t): v for t, v in out.items()}
    write_embedding_cache(cache_path, cache_payload)
    return out


# ---------------------------------------------------------------------------
# 分數與排序
# ---------------------------------------------------------------------------

def _cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (na * nb)


def score_fine_for_query(keys: list, query_vec, query_text: str, query_article, loo_mode: str) -> float:
    """該細目在某臂的分數＝過濾後鍵集合上的 max cos；集合為空 ⇒ 0.0。"""
    norm = _pm().norm
    best = 0.0
    any_key = False
    q_norm = norm(query_text)
    for kind, text, article in keys:
        if loo_mode == "exact" and norm(text) == q_norm:
            continue
        if loo_mode == "article" and article is not None and query_article is not None and article == query_article:
            continue
        vec = _KEY_VECS.get(text)
        if vec is None:
            continue
        any_key = True
        s = _cosine(vec, query_vec)
        if s > best:
            best = s
    return best if any_key else 0.0


_KEY_VECS: dict = {}


def rank_fines(fine_keys: dict, arm: str, query_vec, query_text: str, query_article, loo_mode: str) -> list:
    """回 `[(fine_id, score), ...]`，排序 `(-score, fine_id)`。"""
    scored = []
    for fine_id, arms in fine_keys.items():
        s = score_fine_for_query(arms[arm], query_vec, query_text, query_article, loo_mode)
        scored.append((fine_id, s))
    scored.sort(key=lambda t: (-t[1], t[0]))
    return scored


def recall_at_k(ranked: list, gold: set, k: int) -> bool:
    top_k = {fid for fid, _s in ranked[:k]}
    return bool(top_k & gold)


def count_loo_exclusions(fine_keys: dict, arm: str, gold: set, query_text: str, query_article, loo_mode: str) -> int:
    """該句在 gold 細目集合的這個臂上、這個 LOO 模式會剔除幾把鍵（診斷用：報表的「被剔除鍵數」）。"""
    norm = _pm().norm
    q_norm = norm(query_text)
    n = 0
    for fid in gold:
        for _kind, text, article in fine_keys.get(fid, {}).get(arm, []):
            if loo_mode == "exact" and norm(text) == q_norm:
                n += 1
            elif loo_mode == "article" and article is not None and query_article is not None and article == query_article:
                n += 1
    return n


# ---------------------------------------------------------------------------
# 第二份材料（55 格代表問句）
# ---------------------------------------------------------------------------

def load_second_material(map_v2_path: str, canon_v3_path: str) -> tuple:
    """回 (cells, excluded_count)：cells＝[{cell_id, question, gold: set(fine_id)}]（deliberate_no／no_source 已排除）；
    excluded_count＝被排除的格數。"""
    m = _load_json(map_v2_path)
    labels_doc = _load_json(canon_v3_path)
    payload = labels_doc["payload"] if "payload" in labels_doc else labels_doc
    by_cell: dict = defaultdict(set)
    label_of: dict = {}
    for row in payload["labels"]:
        cid = row["cell_id"]
        label_of.setdefault(cid, row["label"])
        if row["label"] not in DELIBERATE_LABELS_EXCLUDED:
            by_cell[cid].add(row["fine_id"])

    cells_index = {c["id"]: c for c in m["cells"]}
    cells = []
    excluded = 0
    for cid in sorted(cells_index):
        c = cells_index[cid]
        if label_of.get(cid) in DELIBERATE_LABELS_EXCLUDED:
            excluded += 1
            continue
        q = (c.get("questions") or [None])[0]
        if not q:
            continue
        cells.append({"cell_id": cid, "question": q, "gold": sorted(by_cell.get(cid, set()))})
    return cells, excluded


# ---------------------------------------------------------------------------
# misrouted
# ---------------------------------------------------------------------------

def misrouted_for_query(sentence: dict, ranked: list, gold: set, fine_keys: dict, arm: str,
                         query_vec, query_text: str, query_article: str, loo_mode: str) -> dict | None:
    """勝出鍵為講法且其所屬細目 ∉ gold ⇒ 回一筆紀錄；否則 None。"""
    if not ranked:
        return None
    winner_id, winner_score = ranked[0]
    if winner_id in gold or winner_score <= 0:
        return None
    # 判斷贏得該分數的鍵種類：重算一次挑出達到 best 分數的那把鍵。
    norm = _pm().norm
    q_norm = norm(query_text)
    best_kind = None
    for kind, text, article in fine_keys[winner_id][arm]:
        if loo_mode == "exact" and norm(text) == q_norm:
            continue
        if loo_mode == "article" and article is not None and query_article is not None and article == query_article:
            continue
        vec = _KEY_VECS.get(text)
        if vec is None:
            continue
        if abs(_cosine(vec, query_vec) - winner_score) < 1e-9:
            best_kind = kind
            break
    if best_kind != "phrasing":
        return None
    return {
        "article": sentence.get("article"), "type": sentence.get("type"), "q": query_text,
        "winning_fine_id": winner_id, "gold": sorted(gold),
    }


# ---------------------------------------------------------------------------
# object-under-test.md 核可欄
# ---------------------------------------------------------------------------

def object_under_test_approved(repo_root: str, rel_path: str) -> bool:
    return _hook()._object_under_test_approved(repo_root, rel_path)


# ---------------------------------------------------------------------------
# 主流程（dry-run）
# ---------------------------------------------------------------------------

def run_dry(args) -> int:
    repo_root = find_repo_root()
    canon_path = args.canon
    koyu_path = args.koyu
    rule_path = args.rule
    topics_path = args.topics

    materials = freeze_materials(canon_path, koyu_path, rule_path, topics_path, args.helpcenter_dir,
                                  rule_sha_recompute_dir=args.rule_sha_recompute_dir)
    norm = _pm().norm
    frozen_norm_set = frozenset(norm(q) for q in materials["frozen_54_raw"] if q)

    sentences, by_type, excluded_frozen_recomputed = regenerate_422(koyu_path, frozen_norm_set)
    n = len(sentences)

    mismatches = verify_freeze_three_way(materials["rule"], n, by_type, excluded_frozen_recomputed)
    if mismatches:
        print("[index_eval] 凍結三項全等失敗：", file=sys.stderr)
        for m in mismatches:
            print(f"  - {m}", file=sys.stderr)
        return 2

    fines = _load_fines(canon_path)

    aliases = dict(DEFAULT_ALIASES)
    article_map = build_koyu_article_map(koyu_path, args.helpcenter_dir, fines, aliases)
    n_gold_articles = articles_with_gold_count(article_map)

    mappable = mappable_counts_by_type(sentences, article_map)
    limited = limited_types(mappable)

    print(f"n={n}")
    print(f"by_type={json.dumps(by_type, ensure_ascii=False)}")
    print(f"frozen_set_size={len(materials['frozen_54_raw'])}")
    print(f"excluded_frozen_recomputed={excluded_frozen_recomputed}")
    print(f"rule_file_declared_sha256={materials['rule_file_declared_sha256']}")
    print(f"rule_sha256_note={materials['rule_sha256_note']}")
    print(f"articles_with_gold={n_gold_articles}")
    print(f"koyu_article_map.unresolved={article_map['unresolved']}")
    print(f"koyu_article_map.unresolved_after_alias={article_map['unresolved_after_alias']}")
    print(f"inputs_sha.helpcenter_dir={materials['helpcenter_dir_sha256']}")
    for t, c in mappable.items():
        print(f"mappable[{t}]={c['mappable']}/{c['total']}")
    print(f"limited_types={limited}")

    os.makedirs(os.path.dirname(os.path.abspath(args.article_map_out)), exist_ok=True)
    with open(args.article_map_out, "w", encoding="utf-8") as f:
        json.dump(article_map, f, ensure_ascii=False, indent=2, sort_keys=True)

    if len(limited) >= MIN_LIMITED_TYPES_FOR_HARD_STOP:
        print(
            f"[index_eval] ≥{MIN_LIMITED_TYPES_FOR_HARD_STOP} 型可對映句 "
            f"<{MAPPABLE_LIMITED_THRESHOLD}（{limited}）⇒ 本片不足以支撐 3.6，停下回主 session 裁（§7.3）",
            file=sys.stderr,
        )
        return 3
    return 0


def _load_fines(canon_path: str):
    rag_root = _rag_root()
    if rag_root not in sys.path:
        sys.path.insert(0, rag_root)
    from services.agent.canon.canon_parser import parse_canon  # noqa: E402
    doc = parse_canon(canon_path)
    return list(doc.fines())


# ---------------------------------------------------------------------------
# 主流程（全跑）
# ---------------------------------------------------------------------------

def _repo_relative(path: str, repo_root: str) -> str:
    """狀態檔只寫 repo 相對路徑：絕對路徑（容器內常見）先對 repo_root 取 relpath；
    相對路徑視為已相對 repo_root（與 Stop hook 的 join 語義一致）。逃出 repo 的路徑回空字串。"""
    rel = os.path.relpath(path, repo_root) if os.path.isabs(path) else os.path.normpath(path)
    if rel == os.curdir or rel.startswith(os.pardir):
        return ""
    return rel


def run_full(args) -> int:
    repo_root = find_repo_root()
    oud_rel = _repo_relative(args.object_under_test, repo_root)
    if not object_under_test_approved(repo_root, oud_rel):
        print(f"[index_eval] 全跑前置：{oud_rel} 不存在或核可欄為空 ⇒ 拒絕", file=sys.stderr)
        return 2

    materials = freeze_materials(args.canon, args.koyu, args.rule, args.topics, args.helpcenter_dir,
                                  rule_sha_recompute_dir=args.rule_sha_recompute_dir)
    norm = _pm().norm
    frozen_norm_set = frozenset(norm(q) for q in materials["frozen_54_raw"] if q)
    sentences, by_type, excluded_frozen_recomputed = regenerate_422(args.koyu, frozen_norm_set)
    n = len(sentences)
    mismatches = verify_freeze_three_way(materials["rule"], n, by_type, excluded_frozen_recomputed)
    if mismatches:
        for m in mismatches:
            print(f"[index_eval] {m}", file=sys.stderr)
        return 2

    fines = _load_fines(args.canon)
    aliases = dict(DEFAULT_ALIASES)
    article_map = build_koyu_article_map(args.koyu, args.helpcenter_dir, fines, aliases)

    article_map_out = getattr(args, "article_map_out", None)
    if article_map_out:
        os.makedirs(os.path.dirname(os.path.abspath(article_map_out)), exist_ok=True)
        with open(article_map_out, "w", encoding="utf-8") as f:
            json.dump(article_map, f, ensure_ascii=False, indent=2, sort_keys=True)

    fine_keys = build_fine_keys(fines)
    index_texts = all_index_texts(fine_keys)
    query_texts = [s["q"] for s in sentences]

    second_cells, second_excluded = load_second_material(args.map_v2, args.answerability_canon)
    query_texts += [c["question"] for c in second_cells]

    all_texts = sorted(set(index_texts) | set(query_texts))

    rag_root = _rag_root()
    if rag_root not in sys.path:
        sys.path.insert(0, rag_root)
    from services.agent.canon.fine_index import EmbeddingUtilsBackend  # noqa: E402

    backend = EmbeddingUtilsBackend()
    vectors = compute_embeddings(all_texts, backend, args.embedding_cache)
    global _KEY_VECS
    _KEY_VECS = vectors

    report = build_report(sentences, second_cells, second_excluded, fine_keys, article_map, materials,
                           excluded_frozen_recomputed, by_type, n)

    os.makedirs(os.path.dirname(os.path.abspath(args.out_json)), exist_ok=True)
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True)
    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(render_report_md(report))

    if getattr(args, "report", None) == "misrouted":
        for loo_mode, data in report["results"]["main"].items():
            print(f"[index_eval] misrouted（loo={loo_mode}）：{len(data['misrouted'])} 筆")
            for row in data["misrouted"]:
                print(f"  - {row['article']}/{row['type']} → {row['winning_fine_id']}（gold={row['gold']}）")

    state_path = _env().state_file_path(repo_root)
    prior_evals = []
    if os.path.isfile(state_path):
        try:
            with open(state_path, encoding="utf-8") as f:
                prior_evals = (json.load(f) or {}).get("evals_ran") or []
        except (OSError, json.JSONDecodeError):
            prior_evals = []
    _env().update_state(repo_root, {
        "evals_ran": list(dict.fromkeys(list(prior_evals) + ["index_eval"])),
        "materials_frozen": True,
        "object_under_test_path": oud_rel,
    })
    print(f"[index_eval] 全跑完成：{args.out_json}")
    return 0


def build_report(sentences, second_cells, second_excluded, fine_keys, article_map, materials,
                  excluded_frozen_recomputed, by_type, n) -> dict:
    gold_by_query = []
    for s in sentences:
        gold = set(gold_for_sentence(s, article_map))
        gold_by_query.append((s, gold))

    results = {"main": {}, "second_material": {}}
    for loo_mode in ("exact", "article"):
        arm_report = {}
        misrouted = []
        excluded_keys_total = 0
        affected_sentences_set: set = set()
        for arm in ARMS:
            per_type = defaultdict(lambda: {"total": 0, "mappable": 0, "hit1": 0, "hit3": 0, "hit5": 0})
            for s, gold in gold_by_query:
                t = s["type"]
                per_type[t]["total"] += 1
                if not gold:
                    continue
                per_type[t]["mappable"] += 1
                q_vec = _KEY_VECS.get(s["q"])
                if q_vec is None:
                    continue
                q_article = s["article"]
                ranked = rank_fines(fine_keys, arm, q_vec, s["q"], q_article, loo_mode)
                if recall_at_k(ranked, gold, 1):
                    per_type[t]["hit1"] += 1
                if recall_at_k(ranked, gold, 3):
                    per_type[t]["hit3"] += 1
                if recall_at_k(ranked, gold, 5):
                    per_type[t]["hit5"] += 1
                if arm == ARM_TITLE_PHRASING_CONTENT:
                    excl = count_loo_exclusions(fine_keys, arm, gold, s["q"], q_article, loo_mode)
                    if excl:
                        excluded_keys_total += excl
                        affected_sentences_set.add((s["article"], s["type"], s["q"]))
                    mr = misrouted_for_query(s, ranked, gold, fine_keys, arm, q_vec, s["q"], q_article, loo_mode)
                    if mr:
                        misrouted.append(mr)
            arm_report[arm] = {
                t: {
                    "total": c["total"], "mappable": c["mappable"],
                    "limited": c["mappable"] < MAPPABLE_LIMITED_THRESHOLD,
                    "recall_at_1": _safe_div(c["hit1"], c["mappable"]),
                    "recall_at_3": _safe_div(c["hit3"], c["mappable"]),
                    "recall_at_5": _safe_div(c["hit5"], c["mappable"]),
                }
                for t, c in sorted(per_type.items())
            }
        results["main"][loo_mode] = {
            "arms": arm_report,
            "misrouted": misrouted,
            "excluded_keys_total": excluded_keys_total,
            "affected_sentences": len(affected_sentences_set),
        }

    for loo_mode in ("exact", "article"):
        arm_report = {}
        for arm in ARMS:
            total, mappable, hit1, hit3, hit5 = 0, 0, 0, 0, 0
            for c in second_cells:
                total += 1
                gold = set(c["gold"])
                if not gold:
                    continue
                mappable += 1
                q_vec = _KEY_VECS.get(c["question"])
                if q_vec is None:
                    continue
                ranked = rank_fines(fine_keys, arm, q_vec, c["question"], None, loo_mode)
                if recall_at_k(ranked, gold, 1):
                    hit1 += 1
                if recall_at_k(ranked, gold, 3):
                    hit3 += 1
                if recall_at_k(ranked, gold, 5):
                    hit5 += 1
            arm_report[arm] = {
                "total": total, "mappable": mappable, "limited": mappable < MAPPABLE_LIMITED_THRESHOLD,
                "recall_at_1": _safe_div(hit1, mappable), "recall_at_3": _safe_div(hit3, mappable),
                "recall_at_5": _safe_div(hit5, mappable),
            }
        results["second_material"][loo_mode] = {"arms": arm_report, "excluded_deliberate": second_excluded}

    return {
        "inputs_sha": {k: materials[k] for k in (
            "canon_sha256", "koyu_sha256", "rule_file_sha256", "rule_file_declared_sha256",
            "rule_sha256_recomputed", "rule_sha256_note", "topics_v2_sha256", "helpcenter_dir_sha256",
        )},
        "n": n, "by_type": by_type, "excluded_frozen_recomputed": excluded_frozen_recomputed,
        "articles_with_gold": articles_with_gold_count(article_map),
        "unresolved": article_map["unresolved"], "unresolved_after_alias": article_map["unresolved_after_alias"],
        "results": results,
    }


def _safe_div(a, b):
    return round(a / b, 4) if b else None


def render_report_md(report: dict) -> str:
    lines = ["# index_eval 報表", "", f"n={report['n']}｜articles_with_gold={report['articles_with_gold']}", ""]
    for section in ("main", "second_material"):
        lines.append(f"## {section}")
        for loo_mode, data in report["results"][section].items():
            lines.append(f"### loo={loo_mode}")
            for arm, per in data["arms"].items():
                lines.append(f"- {arm}: {json.dumps(per, ensure_ascii=False)}")
        lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--canon", default=os.path.join("rag-orchestrator", "canon", "prospect.md"))
    p.add_argument("--koyu", default=os.path.join(
        ".kiro", "specs", "presales-grounding-gate", "coverage-map", "sources", "koyu-v2-phrasings.json"))
    p.add_argument("--rule", default=os.path.join(
        ".kiro", "specs", "knowledge-outline-and-intent-architecture", "inputs",
        "phrasing-selection-rule-20260906.json"))
    p.add_argument("--topics", default=os.path.join(
        ".kiro", "specs", "presales-grounding-gate", "coverage-map", "topics-v2.json"))
    p.add_argument("--helpcenter-dir", default=DEFAULT_HELPCENTER_DIR)
    p.add_argument("--rule-sha-recompute-dir", default=os.path.join(
        ".claude", "skills", "outline-curation", "raw", "phrasing-20260906"))
    p.add_argument("--article-map-out", default=os.path.join(
        ".kiro", "specs", "knowledge-outline-and-intent-architecture", "inputs", "koyu-article-map.json"))
    p.add_argument("--map-v2", default=os.path.join(
        ".kiro", "specs", "presales-grounding-gate", "coverage-map", "map-v2.json"))
    p.add_argument("--answerability-canon", default=os.path.join(
        ".claude", "skills", "outline-curation", "runs", "2026-09-06T00-00-00Z", "answerability-canon-v3.json"))
    p.add_argument("--object-under-test", default=os.path.join(
        ".kiro", "specs", "knowledge-outline-and-intent-architecture", "inputs", "object-under-test.md"))
    p.add_argument("--embedding-cache", default=os.path.join(
        ".claude", "skills", "outline-curation", "raw", "index-eval-20260907", "embeddings.json"))
    p.add_argument("--out-json", default=os.path.join(
        ".kiro", "specs", "knowledge-outline-and-intent-architecture", "inputs", "index-eval-20260907.json"))
    p.add_argument("--out-md", default=os.path.join(
        ".kiro", "specs", "knowledge-outline-and-intent-architecture", "inputs", "m-c-index-eval-20260907.md"))
    p.add_argument("--loo", choices=("exact", "article"), default=None, help="未使用（兩模式一律都出）")
    p.add_argument("--report", choices=("misrouted",), default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--skill-version", default=SKILL_VERSION)
    return p


def _resolve_repo_relative(args) -> None:
    repo_root = find_repo_root()

    def r(rel):
        return rel if os.path.isabs(rel) else os.path.join(repo_root, rel)

    args.canon = r(args.canon)
    args.koyu = r(args.koyu)
    args.rule = r(args.rule)
    args.topics = r(args.topics)
    args.rule_sha_recompute_dir = r(args.rule_sha_recompute_dir)
    args.article_map_out = r(args.article_map_out)
    args.map_v2 = r(args.map_v2)
    args.answerability_canon = r(args.answerability_canon)
    args.object_under_test = args.object_under_test  # 相對 repo 根（Stop hook 契約）
    args.embedding_cache = r(args.embedding_cache)
    args.out_json = r(args.out_json)
    args.out_md = r(args.out_md)


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)
    _resolve_repo_relative(args)
    if args.dry_run:
        return run_dry(args)
    return run_full(args)


if __name__ == "__main__":
    sys.exit(main())
