"""檢索量尺量測：`tools/canon/ruler_eval.py`（spec knowledge-outline-and-intent-architecture；
Plan `.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-9.12-retrieval-ruler-20260924.md`）。

受測物＝`CandidateSelector.select`（K 名候選）在新三層正本的**全審暫存副本**上（現行正本全未審、
可見子集為空，故本工具自己把 `--canon-src` 複製到暫存目錄、每個細目補 `reviewed`，⛔ 不動 repo 正本）。

量什麼（Plan §6）：每題的答案集合＝主 gold ∪ `also_ok`（只取該身分看得到的）；
- `rank`：答案集合中最前面那個的名次；`hit@K`＝rank ≤ K；
- `coarse_hit`：前 K 名候選的粗目集合 ∩ 答案集合的粗目集合 ≠ ∅；`shelf_hit` 同理（架）；
- 層級斷言：`hit ⇒ coarse_hit ⇒ shelf_hit`（違反即非 0 退出——那是算法錯，⛔ 不是資料）。
- 另算 K=10 作參考。

報告（stdout＋`--out` JSON）：全體、依 leak／type／audience／shelf／coarse_id（逐粗目附 n，只作描述）
與 leak×type×shelf 組成表。⚠️ none 層是「審題者判定不借詞子集上的條件 recall」，⛔ 不是母體估計。

重映（Plan §5）：凍結題集檔 ⛔ 不改；正本重生成改到細目 id 時，以 `--remap <json>`
（`{"from_canon_sha", "to_canon_sha", "map": {舊 id: 新 id}}`，只能追加）在量測時套用。

⚠️ 題目文字會外送：`EmbeddingUtilsBackend` → `embedding-api` 容器 → OpenAI `text-embedding-3-small`
（`embedding-service/app.py`），⛔ 不是純本機；本工具不呼叫生成式 LLM。⛔ 輸出 rows 不帶題目文字（欄位白名單）。
用法（容器內）：
    python3 tools/canon/ruler_eval.py --questions <凍結題集.json> --out <rows.json> [--remap <map.json>]
    python3 tools/canon/ruler_eval.py --self-test     # 合成題試跑（題目＝細目標題），驗格式與層級斷言
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter, defaultdict

_RAG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _RAG not in sys.path:
    sys.path.insert(0, _RAG)

DEFAULT_CANON_SRC = os.path.join(_RAG, "canon", "jgb")
DEFAULT_VENDOR_ID = 1
REVIEW_MARK = "\n- reviewed: {by: ruler-eval, at: 2026-09-24}"


class RulerError(RuntimeError):
    """量測前提不成立（大聲失敗）。"""


# ───────────────────────── 純函式（單元測試對象）─────────────────────────


def shelf_of(fine_id: str) -> str:
    """`jgb/B/member-seat-limit` ⇒ `B`。"""
    parts = fine_id.split("/")
    if len(parts) < 3:
        raise RulerError(f"細目 id 形狀不合：{fine_id!r}")
    return parts[1]


def apply_remap(items: list[dict], remap: dict | None, canon_sha: str) -> list[dict]:
    """依重映檔把 gold／also_ok 換成新 id；⛔ 不改原 items。`to_canon_sha` 須等於受測正本 sha。"""
    if not remap:
        return items
    if remap.get("to_canon_sha") != canon_sha:
        raise RulerError(f"重映檔 to_canon_sha={remap.get('to_canon_sha')!r} ≠ 受測正本 {canon_sha!r}")
    m = remap.get("map") or {}
    out = []
    for it in items:
        new = dict(it)
        new["fine_id"] = m.get(it["fine_id"], it["fine_id"])
        new["also_ok"] = [m.get(a, a) for a in it.get("also_ok", [])]
        out.append(new)
    return out


def score_row(order: list[str], answers: set[str], coarse_of: dict[str, str], k: int = 5) -> dict:
    """一題的命中與名次。`order`＝可見細目依分數排序；`answers`＝可見的答案集合（非空）。"""
    if not answers:
        raise RulerError("答案集合為空（gold 與 also_ok 皆不可見）")
    pos = {f: i + 1 for i, f in enumerate(order)}
    missing = [a for a in answers if a not in pos]
    if missing:
        raise RulerError(f"答案不在可見排序內：{missing}")
    rank = min(pos[a] for a in answers)
    topk = order[:k]
    ans_coarses = {coarse_of[a] for a in answers}
    ans_shelves = {shelf_of(a) for a in answers}
    row = {
        "rank": rank,
        "hit": rank <= k,
        "hit10": rank <= 10,
        "coarse_hit": bool(ans_coarses & {coarse_of[f] for f in topk}),
        "shelf_hit": bool(ans_shelves & {shelf_of(f) for f in topk}),
    }
    if row["hit"] and not row["coarse_hit"]:
        raise RulerError("層級斷言失敗：細目命中但粗目未命中")
    if row["coarse_hit"] and not row["shelf_hit"]:
        raise RulerError("層級斷言失敗：粗目命中但架未命中")
    return row


def summarize(rows: list[dict], key: str | None) -> list[dict]:
    """依 `key` 分組的 n／hit／hit10／coarse_hit／shelf_hit 比率。"""
    groups: dict = defaultdict(list)
    for r in rows:
        groups[r.get(key) if key else "ALL"].append(r)
    out = []
    for g, rs in sorted(groups.items(), key=lambda kv: str(kv[0])):
        n = len(rs)
        out.append({
            "group": key or "ALL", "value": g, "n": n,
            "hit": round(sum(r["hit"] for r in rs) / n, 4),
            "hit10": round(sum(r["hit10"] for r in rs) / n, 4),
            "coarse_hit": round(sum(r["coarse_hit"] for r in rs) / n, 4),
            "shelf_hit": round(sum(r["shelf_hit"] for r in rs) / n, 4),
        })
    return out


def composition(rows: list[dict]) -> dict:
    """leak×type×shelf 組成表（放在主數字旁，說明 none 層的組成偏差）。"""
    return {
        "leak_x_type": {f"{a}|{b}": n for (a, b), n in sorted(Counter((r.get("leak"), r["type"]) for r in rows).items())},
        "leak_x_shelf": {f"{a}|{b}": n for (a, b), n in sorted(Counter((r.get("leak"), r["shelf"]) for r in rows).items())},
    }


# ───────────────────────── 正本與量測 ─────────────────────────


def build_fullreview_copy(canon_src: str, dst_root: str):
    """把 `canon_src`（九架目錄）複製到 `dst_root/jgb`、每個尚未審的細目補 `reviewed`
    （已經有的跳過——S4 之後 D／E 會混入真的 `reviewed`，無條件附加會撞 `canon_parser`
    的『屬性重複 reviewed』），回 `(doc, marked)`（`marked`＝本次新插入的條數）。
    """
    from services.agent.canon.canon_parser import FINE_HEADING_RE, export_catalog, export_json, parse_canon_dir

    dst = os.path.join(dst_root, "jgb")
    os.makedirs(dst)
    pat = re.compile(FINE_HEADING_RE.pattern, re.M)
    marked = 0
    total_headings = 0
    for name in sorted(os.listdir(canon_src)):
        if re.fullmatch(r"[A-I]\.md", name):
            text = open(os.path.join(canon_src, name), encoding="utf-8").read()
            matches = list(pat.finditer(text))
            total_headings += len(matches)
            pieces, cursor = [], 0
            for i, m in enumerate(matches):
                next_start = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                pieces.append(text[cursor:m.end()])
                block = text[m.end():next_start]
                if not re.search(r"^- reviewed:", block, re.M):
                    pieces.append(REVIEW_MARK)
                    marked += 1
                cursor = m.end()
            pieces.append(text[cursor:])
            open(os.path.join(dst, name), "w", encoding="utf-8").write("".join(pieces))
    if total_headings == 0:
        raise RulerError("全審副本一個細目都沒標到（FINE_HEADING_RE 對不上？）")
    doc = parse_canon_dir(dst)
    export_json(doc, os.path.join(dst_root, "jgb.json"))
    export_catalog(doc, os.path.join(dst, "CATALOG.md"))
    still_unreviewed = sum(1 for f in doc.fines() if f.reviewed_by is None)
    if still_unreviewed:
        raise RulerError(f"全審副本仍有 {still_unreviewed} 條未審細目")
    return doc, marked


#: 查詢 embedding 偶發逾時（選取器硬上限 3 秒）⇒ 重試；同一句的向量是決定性的，重試不影響結果。
RETRIES = 4


async def _retry(make_call):
    """`None` 視為暫時失敗重試；仍 `None` 就回 `None`（呼叫端大聲失敗）。"""
    for attempt in range(RETRIES):
        out = await make_call()
        if out is not None:
            return out
        await asyncio.sleep(1.0 * (attempt + 1))
    return None


def _source_sha(canon_src: str) -> str:
    h = hashlib.sha256()
    for name in sorted(os.listdir(canon_src)):
        if re.fullmatch(r"[A-I]\.md", name):
            h.update(name.encode())
            h.update(open(os.path.join(canon_src, name), "rb").read())
    return h.hexdigest()


async def measure(items: list[dict], canon_src: str, vendor_id: int, k: int) -> tuple[list[dict], dict]:
    from services.agent.canon.canon_assembler import load_canon_or_die
    from services.agent.canon.candidate_selector import K as SELECTOR_K, CandidateSelector
    from services.agent.canon.fine_index import EmbeddingUtilsBackend, FineIndex
    from services.agent.identity import Identity
    from services.agent.outline import resolve_vendor_business_types

    with tempfile.TemporaryDirectory() as td:
        root = os.path.join(td, "canon")
        os.makedirs(root)
        _doc, marked = build_fullreview_copy(canon_src, root)
        doc = load_canon_or_die(root)
        coarse_of = {f.id: c.id for c in doc.coarses for f in c.fines}
        idx = FineIndex(EmbeddingUtilsBackend())
        await idx.prepare(doc)
        if idx.state != "ready":
            raise RulerError(f"索引非 ready：{idx.state}")
        sel = CandidateSelector(idx)
        vbt_cache: dict = {}
        rows = []
        for it in items:
            aud = it["audience"]
            ident = Identity(vendor_id=vendor_id, target_user=aud, mode="b2b", session_id="ruler-eval")
            if aud not in vbt_cache:
                vbt_cache[aud] = resolve_vendor_business_types(ident)
            vbt = vbt_cache[aud]
            vis = idx.visible_subset(ident, doc, vendor_business_types=vbt)
            if it["fine_id"] not in vis:
                raise RulerError(f"主 gold 對指派身分不可見：{it.get('id') or it.get('slot')}")
            qv = await _retry(lambda: sel._embed_query(it["q"]))
            if qv is None:
                raise RulerError(f"查詢 embedding 失敗（重試 {RETRIES} 次）")
            scored = sorted(((sel._best_entry(f, qv)[0], f) for f in vis), key=lambda x: (-x[0], x[1]))
            order = [f for _s, f in scored]
            live = await _retry(lambda: sel.select(doc, ident, it["q"], vendor_business_types=vbt))
            if live is None or live["candidate_ids"] != order[:SELECTOR_K]:
                raise RulerError(f"量測排序與 select() 不一致：{it.get('id') or it.get('slot')}")
            unknown = [a for a in [it["fine_id"], *it.get("also_ok", [])] if a not in coarse_of]
            if unknown:
                raise RulerError(f"答案 id 在受測正本不存在（重映漏了？）：{unknown}")
            answers = {it["fine_id"], *[a for a in it.get("also_ok", []) if a in vis]}
            row = score_row(order, answers, coarse_of, k)
            rows.append({**{key: it.get(key) for key in ("id", "slot", "fine_id", "coarse_id", "type", "audience", "leak", "origin")},
                         "shelf": shelf_of(it["fine_id"]), "coarse_id": coarse_of[it["fine_id"]], **row,
                         "n_visible": len(vis), "top5": order[:5]})
        meta = {
            "canon_src": os.path.relpath(canon_src, _RAG), "canon_src_sha256": _source_sha(canon_src),
            "fullreview_doc_sha256": doc.canon_sha256, "fullreview_marked": marked,
            "embedding_backend": type(idx.backend).__name__, "embedding_dim": idx.dim,
            "embedding_model_env": os.getenv("EMBEDDING_MODEL"),
            "vendor_id": vendor_id, "vendor_business_types": {a: sorted(v) for a, v in vbt_cache.items()},
            "k": k,
        }
        return rows, meta


def report(rows: list[dict]) -> dict:
    return {
        "summary": [s for key in (None, "leak", "type", "audience", "shelf", "origin") for s in summarize(rows, key)],
        "by_coarse": summarize(rows, "coarse_id"),
        "composition": composition(rows),
    }


def _print_report(rep: dict) -> None:
    for s in rep["summary"]:
        print(f"  {s['group']:8} {str(s['value']):14} n={s['n']:3} hit@5={s['hit']:.3f} hit@10={s['hit10']:.3f} "
              f"coarse={s['coarse_hit']:.3f} shelf={s['shelf_hit']:.3f}")
    print(f"  by_coarse: {len(rep['by_coarse'])} 列（逐粗目附 n，只作描述）")


def _self_test(canon_src: str, vendor_id: int) -> int:
    """合成題：每架取第一個細目、題目＝其標題（⛔ 不是量尺題，不看量尺結果）。驗流程、格式、層級斷言。"""
    from services.agent.canon.canon_parser import parse_canon_dir

    doc = parse_canon_dir(canon_src)
    items, seen = [], set()
    for c in doc.coarses:
        for f in c.fines:
            sh = shelf_of(f.id)
            if sh in seen:
                continue
            seen.add(sh)
            aud = "property_manager" if "property_manager" in f.target_user else f.target_user[0]
            items.append({"id": f"synthetic:{sh}", "q": f.title, "fine_id": f.id, "also_ok": [],
                          "audience": aud, "type": "直接", "leak": "strong", "origin": "synthetic"})
    rows, meta = asyncio.run(measure(items, canon_src, vendor_id, 5))
    rep = report(rows)
    ok = len(rows) == len(items) and rep["summary"][0]["n"] == len(items) and meta["fullreview_marked"] > 0
    print(f"{'✅' if ok else '❌'} self-test：{len(rows)} 題合成題、層級斷言通過、meta={meta['fullreview_doc_sha256'][:12]}")
    return 0 if ok else 1


def load_hash_norm():
    """Plan 9.13 §4：唯一正規化 `canon_phrasing_frozen_disjoint.hash_norm`（⛔ 不在本檔另寫一份）。
    容器內以唯讀掛載 `scripts/audit/checks` 到 `/repo_checks`；host 直接走 repo 路徑。找不到 ⇒ 大聲失敗。"""
    import importlib.util
    for d in (os.getenv("RULER_CHECKS_DIR"), "/repo_checks", os.path.join(os.path.dirname(_RAG), "scripts", "audit", "checks")):
        path = os.path.join(d, "canon_phrasing_frozen_disjoint.py") if d else None
        if path and os.path.isfile(path):
            spec = importlib.util.spec_from_file_location("canon_phrasing_frozen_disjoint", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.hash_norm
    raise RulerError("找不到 canon_phrasing_frozen_disjoint.hash_norm（容器請 -v scripts/audit/checks:/repo_checks:ro）")


def join_text(items: list[dict], text_items: list[dict], hash_norm) -> list[dict]:
    """把 repo 外的 `{id, q}` 併回無文字的 index；逐題驗 `hash_norm(q) == q_sha256`，缺題或不符 ⇒ 大聲失敗。"""
    by_id = {t["id"]: t["q"] for t in text_items}
    out = []
    for it in items:
        q = by_id.get(it["id"])
        if q is None:
            raise RulerError(f"文字檔缺題：{it['id']}")
        if hash_norm(q) != it.get("q_sha256"):
            raise RulerError(f"題目 hash 不符：{it['id']}")
        out.append({**it, "q": q})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--questions")
    ap.add_argument("--out")
    ap.add_argument("--remap")
    ap.add_argument("--text-file", help="repo 外的 {id, q} 題目檔（題目文字不進 git 的題集用）")
    ap.add_argument("--canon-src", default=DEFAULT_CANON_SRC)
    ap.add_argument("--vendor-id", type=int, default=DEFAULT_VENDOR_ID)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return _self_test(a.canon_src, a.vendor_id)
    if not (a.questions and a.out):
        ap.error("需要 --questions 與 --out（或 --self-test）")
    frozen = json.load(open(a.questions, encoding="utf-8"))
    items = frozen.get("items")
    if not items:
        raise RulerError("凍結題集沒有 items")
    if a.text_file:
        texts = json.load(open(a.text_file, encoding="utf-8"))
        items = join_text(items, texts.get("items", texts) if isinstance(texts, dict) else texts, load_hash_norm())
    elif any("q" not in it for it in items):
        raise RulerError("題集沒有題目文字且未給 --text-file")
    remap = json.load(open(a.remap, encoding="utf-8")) if a.remap else None
    from services.agent.canon.canon_parser import parse_canon_dir
    src_doc_sha = parse_canon_dir(a.canon_src).canon_sha256
    frozen_sha = (frozen.get("_meta") or {}).get("canon_src_doc_sha256")
    if not frozen_sha or len(frozen_sha) != 64:
        raise RulerError("凍結 _meta.canon_src_doc_sha256 缺或不是完整 64 碼")
    if remap:
        if remap.get("from_canon_sha") != frozen_sha:
            raise RulerError("重映檔 from_canon_sha ≠ 凍結 _meta 的正本 sha")
        items = apply_remap(items, remap, src_doc_sha)
    elif src_doc_sha != frozen_sha:
        raise RulerError(f"受測正本 sha {src_doc_sha[:12]} ≠ 凍結 _meta {frozen_sha[:12]}，且未給 --remap")
    rows, meta = asyncio.run(measure(items, a.canon_src, a.vendor_id, a.k))
    rep = report(rows)
    meta["questions_sha256"] = hashlib.sha256(open(a.questions, "rb").read()).hexdigest()
    meta["canon_src_doc_sha256"] = src_doc_sha
    for note_key in ("leak_note", "also_ok_note"):
        meta[note_key] = (frozen.get("_meta") or {}).get(note_key)
    json.dump({"meta": meta, "report": rep, "rows": rows}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False))
    _print_report(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
