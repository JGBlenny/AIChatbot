#!/usr/bin/env python3
"""售前缺口地圖 v2（PLAN-retrieval-coverage P2.5；業主 2026-09-04 定最優先）。

v1 → v2 依 plan-verifier REVISE（P0＋6 P1＋5 P2）與 verifier REFUTED 改：
  ① 兩層分開：cause_state（元件層，只分成因 S／V／N／FALSE_HIT／UNCLASSIFIED）與 entry_state（使用者層，依 handoff 訊號），
     coverage 只在兩層都成立且回答命中 rubric 全部必含群時才成立——⛔ 不再用檢索分數單獨判「已覆蓋」（PLAN P2.5 ⛔ 不做）。
  ② 關鍵詞掃**全庫**並標 prospect 可見性 ⇒ 池外有對題列 = V（可見性），⛔ 不併入缺口。
  ③ 對題性：命中列文必須命中 rubric 任一必含群，否則不計（v1「通知」撈到租客不繳、「專人」撈到六筆尾句）。
  ④ 缺口不再是 catch-all：無權威來源 ⇒ UNCLASSIFIED；有 ⇒ N_CAND（待 G0 四查落檔）。
  ⑤ 固定句改讀 conversational_config.PRESALES_HANDOFF_MESSAGE，並以 handoff.reason 為主判。
  ⑥ 每格量全部問句；cause 跨問句不一致 ⇒ UNSTABLE。
  ⑦ 開跑先過三個正對照（檢索／ILIKE／固定句），任一失敗 exit 3；_meta 落指紋（HEAD、image、池筆數、池 max(updated_at)、門檻、demand sha256、G2）。
⛔ 不寫 DB。須在 rag-orchestrator 容器內跑。

用法（容器內）：python3 tools/gapmap/presales_gap_map.py --demand demand.json --out map.json --head <git sha> --image <image id> [--g2 '<json>'] [--api URL] [--threshold 0.5] [--no-api]
      渲染：python3 tools/gapmap/presales_gap_map.py --render map.json > map.md
"""
import argparse, asyncio, hashlib, json, os, sys, time, urllib.request, uuid

FIXED_REASONS = {"no_grounding", "sensitive_no_grounding"}
POOL_PRED = "business_types && ARRAY['system_provider'] AND (target_user IS NULL OR target_user && ARRAY['prospect'])"
KW_SQL = ("SELECT id, question_summary, answer, (" + POOL_PRED + ") AS visible FROM knowledge_base "
          "WHERE is_active AND answer<>'' AND (question_summary ILIKE $1 OR answer ILIKE $1) LIMIT 12")
POOL_STAT_SQL = "SELECT count(*), max(COALESCE(updated_at, created_at))::text FROM knowledge_base WHERE is_active AND answer<>'' AND " + POOL_PRED


def ask(api, msg, sid):
    body = json.dumps({"message": msg, "mode": "b2b", "target_user": "prospect", "session_id": sid}).encode()
    req = urllib.request.Request(api, data=body, headers={"Content-Type": "application/json"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=240) as r:
        d = json.loads(r.read().decode())
    return {"answer": d.get("answer"), "handoff": d.get("handoff"), "elapsed_s": round(time.time() - t, 2)}


def hits_groups(text, groups):
    """回傳命中的必含群數（每群任一詞命中即算）。"""
    t = text or ""
    return sum(1 for g in groups if any(term in t for term in g))


def row_relevant(row, rubric):
    groups = (rubric or {}).get("must") or []
    if not groups:
        return None                                  # 無 rubric ⇒ 無法判對題
    need = min(2, len(groups))                       # 多群 rubric 要命中 ≥2 群才算對題（v2.1：單群命中太鬆，「國泰」一詞就把金流列舉當成差異比較）
    return hits_groups((row.get("question_summary") or "") + " " + (row.get("answer") or ""), groups) >= need


def entry_state_of(api, fixed_msg):
    if not api or api.get("error"):
        return "error"
    a = (api.get("answer") or "").strip(); h = api.get("handoff") or {}
    if a == fixed_msg or h.get("reason") in FIXED_REASONS:
        return "fixed"
    if not h and a.endswith(("？", "?")) and len(a) <= 80:
        return "ask_back"
    return "answered_handoff" if h else "answered"


def cause_state_of(cell, top, kw_rows, threshold):
    if cell.get("policy") == "deliberate_no":
        return ("DELIBERATE_NO" if cell.get("policy_ref") else "UNCLASSIFIED(刻意不補無裁決引用)"), ""
    if cell.get("intent") == "advice":
        return "ADVICE", ""
    if cell.get("intent") == "cta":
        return "CTA", "出口題：看入口是否給連結／找真人，不分 S／N"
    rubric = cell.get("rubric") or {}
    if not rubric.get("must"):
        return "UNCLASSIFIED(無rubric)", ""
    if top and float(top[0]["similarity"]) >= threshold:
        rel = row_relevant(top[0], rubric)
        return ("S_OK" if rel else "FALSE_HIT"), f"top-1 {top[0]['id']} {top[0]['similarity']:.3f}" + ("" if rel else " 不對題")
    rel_rows = [r for r in kw_rows if row_relevant(r, rubric)]
    vis = [r for r in rel_rows if r["visible"]]
    if vis:
        return "S", f"對題列可見 {[r['id'] for r in vis][:5]}；top-1 {top[0]['id'] if top else '-'} {top[0]['similarity'] if top else 0:.3f}"
    if rel_rows:
        return "V", f"對題列僅池外 {[r['id'] for r in rel_rows][:5]}（可見性）"
    auth = (cell.get("g0") or {}).get("authority") or "none"
    if auth.startswith("none") or auth.startswith("n/a"):
        return "UNCLASSIFIED(待G0)", "池內外皆無對題列、無權威來源"
    return "N_CAND", f"池內外皆無對題列；權威來源：{auth}"


def coverage_of(cell, cause, entry, api):
    a = (api or {}).get("answer") or ""
    rubric = cell.get("rubric") or {}
    if cause.startswith("DELIBERATE_NO"):
        return "符合(刻意不補)" if entry == "fixed" else "⚠️刻意不補卻非固定句"
    if cause == "ADVICE":
        return "n/a(一般建議)" if entry in ("answered", "answered_handoff") else "未覆蓋"
    if cell.get("intent") == "recommend":
        return "已覆蓋" if entry in ("answered", "answered_handoff", "ask_back") else "未覆蓋"
    if not rubric.get("must"):
        return "未判定(待尺)"
    if cell.get("intent") == "cta":
        return "已覆蓋" if (entry != "fixed" and hits_groups(a, rubric["must"]) == len(rubric["must"])) else "未覆蓋"
    if cause != "S_OK" or entry not in ("answered", "answered_handoff"):
        return "未覆蓋"
    if hits_groups(a, rubric["must"]) < len(rubric["must"]):
        return "未覆蓋(回答未含必含)"
    if any(f in a for f in rubric.get("forbid") or []):
        return "已覆蓋⚠️"
    return "已覆蓋"


async def run(args):
    sys.path.insert(0, "/app")
    import asyncpg
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
    from services.conversational_config import PRESALES_HANDOFF_MESSAGE
    demand = json.load(open(args.demand, encoding="utf-8"))
    sha = hashlib.sha256(open(args.demand, "rb").read()).hexdigest()
    r = VendorKnowledgeRetrieverV2()
    conn = await asyncpg.connect(host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
                                 user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
                                 database=os.getenv("DB_NAME", "aichatbot_admin"))

    async def retrieve(q):
        res = await r.retrieve(query=q, vendor_id=0, top_k=3, similarity_threshold=0.0, target_user="prospect", mode="b2b", return_unfiltered=True)
        return [{"id": x.get("id"), "similarity": round(float(x.get("similarity") or 0), 3),
                 "question_summary": (x.get("question_summary") or ""), "answer": (x.get("answer") or "")} for x in res[:3]]

    # ── 正對照（尺自證，任一敗 ⇒ exit 3）──
    controls = {}
    c1 = await retrieve("可以免費試用嗎"); controls["retrieval_3611"] = bool(c1 and c1[0]["id"] == 3611 and c1[0]["similarity"] >= 0.9)
    c2 = await conn.fetch(KW_SQL, "%電子發票%"); controls["ilike_電子發票>=1"] = len(c2) >= 1
    fixed_cells = [c for c in demand["cells"] if c.get("policy") == "deliberate_no"]
    if fixed_cells and not args.no_api:
        a = ask(args.api, fixed_cells[0]["questions"][0], f"backtest_session_gapmap_ctl_{uuid.uuid4().hex[:4]}")
        controls["fixed_sentence"] = (a.get("answer") == PRESALES_HANDOFF_MESSAGE and (a.get("handoff") or {}).get("reason") in FIXED_REASONS)
    pool_n, pool_max = await conn.fetchrow(POOL_STAT_SQL)
    meta = {**demand["_meta"], "run_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "threshold": args.threshold, "api": args.api,
            "fingerprint": {"git_head": args.head, "image": args.image, "pool_count": pool_n, "pool_max_updated_at": pool_max,
                            "demand_sha256": sha, "fixed_message_sha256": hashlib.sha256(PRESALES_HANDOFF_MESSAGE.encode()).hexdigest()[:16]},
            "g2": (json.loads(args.g2) if args.g2 and args.g2.strip().startswith("{") else (args.g2 or "未跑")), "controls": controls}
    out = {"_meta": meta, "cells": []}
    base = json.load(open(args.merge_into, encoding="utf-8")) if args.merge_into else None
    only = set(x.strip() for x in args.only.split(",")) if args.only else None
    if not all(controls.values()):
        print("⛔ 正對照失敗，尺不可信，本輪作廢：", controls); json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1); return 3

    for c in demand["cells"]:
        if only and c["id"] not in only:
            if base:
                keep = next((x for x in base["cells"] if x["id"] == c["id"]), None)
                if keep:
                    out["cells"].append(keep)
            continue
        per_q = []
        for qi, q in enumerate(c["questions"]):
            top = await retrieve(q)
            kw_rows = []
            for k in c.get("keywords", []):
                kw_rows += [dict(row) for row in await conn.fetch(KW_SQL, f"%{k}%")]
            seen = set(); kw_rows = [x for x in kw_rows if not (x["id"] in seen or seen.add(x["id"]))]
            api = None
            if not args.no_api:
                try:
                    api = ask(args.api, q, f"backtest_session_gapmap_{c['id']}_{qi}_{uuid.uuid4().hex[:4]}")
                except Exception as e:
                    api = {"answer": None, "handoff": None, "error": repr(e)}
            cause, why = cause_state_of(c, top, kw_rows, args.threshold)
            entry = entry_state_of(api, PRESALES_HANDOFF_MESSAGE)
            per_q.append({"q": q, "top3": [{"id": t["id"], "similarity": t["similarity"], "q": t["question_summary"][:20]} for t in top],
                          "kw_relevant": [{"id": x["id"], "visible": x["visible"], "q": x["question_summary"][:20]} for x in kw_rows if row_relevant(x, c.get("rubric"))][:8],
                          "api": api, "cause_state": cause, "cause_why": why, "entry_state": entry})
        causes = {p["cause_state"] for p in per_q}
        cell_cause = per_q[0]["cause_state"] if len(causes) == 1 else f"UNSTABLE{sorted(causes)}"
        cov = coverage_of(c, per_q[0]["cause_state"], per_q[0]["entry_state"], per_q[0]["api"])
        rec = {**c, "per_question": per_q, "cause_state": cell_cause, "entry_state": per_q[0]["entry_state"], "coverage": cov}
        out["cells"].append(rec)
        print(f"{c['id']} cause={cell_cause:22} entry={per_q[0]['entry_state']:16} cov={cov:14} {c['module']}/{c['topic'][:14]} {per_q[0]['cause_why'][:50]}", flush=True)
        json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)   # 沿用格（--only 之外）也要落檔——首版漏了這行，掉了尾端 8 格
    await conn.close(); print("saved", args.out, f"cells={len(out['cells'])}"); return 0


async def run_topics(args):
    """主題模式：覆蓋單位＝主題＋owner＋問法樣本（業主 2026-09-04：1～3 句太少）。每句量 owner_hit／answered／rubric_hit，主題算命中率。"""
    sys.path.insert(0, "/app")
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
    from services.conversational_config import PRESALES_HANDOFF_MESSAGE
    spec = json.load(open(args.topics, encoding="utf-8")); sha = hashlib.sha256(open(args.topics, "rb").read()).hexdigest()
    thr_c = float(spec["_meta"].get("complete_threshold", 0.8))
    r = VendorKnowledgeRetrieverV2()
    out = {"_meta": {**spec["_meta"], "run_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "threshold": args.threshold, "api": args.api,
                     "fingerprint": {"git_head": args.head, "image": args.image, "topics_sha256": sha}, "g2": args.g2 or "未跑"}, "topics": []}
    for tp in spec["topics"]:
        rows = []; brows = []
        forbid = tp.get("forbid") or {}
        def _forbid_hit(sub, a):
            return [w for w in (forbid.get(sub) or []) + (forbid.get("*") or []) if w in a]
        for ph in tp.get("boundary") or []:
            api = None
            if not args.no_api:
                try:
                    api = ask(args.api, ph["q"], f"backtest_session_topicb_{tp['id']}_{uuid.uuid4().hex[:4]}")
                except Exception as e:
                    api = {"answer": None, "handoff": None, "error": repr(e)}
            entry = entry_state_of(api, PRESALES_HANDOFF_MESSAGE); a = (api or {}).get("answer") or ""
            ok = entry == "fixed" or (any(w in a for w in ("沒有資料", "專人", "找真人")) and not _forbid_hit(ph.get("sub", "*"), a))
            brows.append({**ph, "entry_state": entry, "boundary_ok": ok, "answer_head": a.replace("\n", " ")[:80]})
            print(f"{tp['id']} 邊界   ok={'Y' if ok else '-'} entry={entry:16} {ph['q'][:22]}", flush=True)
        for ph in tp["phrasings"]:
            res = await r.retrieve(query=ph["q"], vendor_id=0, top_k=3, similarity_threshold=0.0, target_user="prospect", mode="b2b", return_unfiltered=True)
            top = [{"id": x.get("id"), "similarity": round(float(x.get("similarity") or 0), 3)} for x in res[:3]]
            t1 = top[0] if top else {"id": None, "similarity": 0}
            api = None
            if not args.no_api:
                try:
                    api = ask(args.api, ph["q"], f"backtest_session_topic_{tp['id']}_{uuid.uuid4().hex[:4]}")
                except Exception as e:
                    api = {"answer": None, "handoff": None, "error": repr(e)}
            entry = entry_state_of(api, PRESALES_HANDOFF_MESSAGE)
            groups = tp["subtopic_rubrics"].get(ph["sub"]) or []
            a = (api or {}).get("answer") or ""
            fh = _forbid_hit(ph["sub"], a)
            rec = {**ph, "top3": top, "owner_hit": t1["id"] in tp["owner"], "alias_hit": t1["id"] in tp.get("transitional_alias", []),
                   "over_threshold": t1["similarity"] >= args.threshold, "entry_state": entry, "forbid_hit": fh,
                   "rubric_hit": bool(groups) and entry in ("answered", "answered_handoff") and hits_groups(a, groups) == len(groups) and not fh,
                   "answer_head": a.replace("\n", " ")[:80]}
            rows.append(rec)
            print(f"{tp['id']} {ph['sub']:5} owner={'Y' if rec['owner_hit'] else ('a' if rec['alias_hit'] else '-')} top1={t1['id']}@{t1['similarity']:.2f} entry={entry:16} rubric={'Y' if rec['rubric_hit'] else '-'} {ph['q'][:22]}", flush=True)
        n = len(rows)
        m = {"n": n, "owner_hit_rate": round(sum(x["owner_hit"] for x in rows) / n, 2), "alias_hit_rate": round(sum(x["alias_hit"] for x in rows) / n, 2),
             "answered_rate": round(sum(x["entry_state"] in ("answered", "answered_handoff") for x in rows) / n, 2),
             "rubric_hit_rate": round(sum(x["rubric_hit"] for x in rows) / n, 2)}
        if brows:
            m["boundary_n"] = len(brows); m["boundary_ok_rate"] = round(sum(x["boundary_ok"] for x in brows) / len(brows), 2)
        m["forbid_hits"] = sum(1 for x in rows if x.get("forbid_hit"))
        m["complete"] = m["rubric_hit_rate"] >= thr_c and (not brows or m["boundary_ok_rate"] >= float(spec["_meta"].get("boundary_threshold", 0.9)))
        by_sub = {}
        for x in rows:
            d = by_sub.setdefault(x["sub"], {"n": 0, "rubric_hit": 0, "owner_hit": 0})
            d["n"] += 1; d["rubric_hit"] += x["rubric_hit"]; d["owner_hit"] += x["owner_hit"]
        out["topics"].append({**{k: v for k, v in tp.items() if k not in ("phrasings", "boundary")}, "metrics": m, "by_subtopic": by_sub, "phrasings": rows, "boundary": brows})
        print(f"== {tp['topic']}: n={n} owner_hit={m['owner_hit_rate']} alias_hit={m['alias_hit_rate']} answered={m['answered_rate']} rubric_hit={m['rubric_hit_rate']} complete={m['complete']}", flush=True)
        json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("saved", args.out); return 0


def render(path):
    m = json.load(open(path, encoding="utf-8")); cells = m["cells"]; fp = m["_meta"].get("fingerprint", {})
    def cnt(key):
        d = {}
        for c in cells:
            d[c[key]] = d.get(c[key], 0) + 1
        return d
    g2 = m["_meta"].get("g2"); g2_flags = [v for v in (g2.values() if isinstance(g2, dict) else []) if isinstance(v, bool)]
    g2_ok = bool(g2_flags) and all(g2_flags)
    L = [f"# 售前缺口地圖 {m['_meta'].get('version')}（{m['_meta']['run_at'][:16]}，門檻 {m['_meta']['threshold']}，{len(cells)} 格）", "",
         "> 地圖是**盤點**不是療效、不是比率分母（分群為後驗人工建構）。cause 是元件層成因、entry 是使用者層入口、coverage 只在兩層都成立且回答命中全部必含群時成立。", "",
         f"- 指紋：HEAD `{fp.get('git_head')}`；image `{fp.get('image')}`；prospect 池 {fp.get('pool_count')} 筆、max(updated_at) {fp.get('pool_max_updated_at')}；demand sha256 `{str(fp.get('demand_sha256'))[:16]}`；固定句 sha `{fp.get('fixed_message_sha256')}`",
         f"- 正對照：{m['_meta'].get('controls')}",
         f"- G2 管線自證：{'PASS' if g2_ok else '⚠️ 未自證或未全過——狀態不可引用'}（{str(g2)[:200]}）", ""]
    for key, title in (("cause_state", "元件層 cause_state"), ("entry_state", "使用者層 entry_state（代表問句）"), ("coverage", "合成 coverage（代表問句）")):
        L += [f"## {title}", "", "| 值 | 格數 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(cnt(key).items(), key=lambda kv: -kv[1])] + [""]
    L += ["## 逐格", "", "| # | 模組 | 主題 | cause | entry | coverage | 成因說明 | 代表問句 | 入口回答（前 50 字） | G0 權威來源 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for c in cells:
        p0 = c["per_question"][0]; a = ((p0.get("api") or {}).get("answer") or "").replace("\n", " ").replace("|", "／")[:50]
        L.append(f"| {c['id']} | {c['module']} | {c['topic']} | {c['cause_state']} | {c['entry_state']} | **{c['coverage']}** | {p0['cause_why'].replace('|','／')[:60]} | {p0['q'][:24]} | {a} | {(c.get('g0') or {}).get('authority','')[:40]} |")
    L += ["", "## 下一輪選題", ""]
    for s, label in (("S", "表示法缺（補講法）"), ("V", "可見性（改資料歸屬，⛔ 非補知識）"), ("N_CAND", "缺口候選（G0 四查落檔後寫知識）"), ("FALSE_HIT", "假命中（檢索對題性問題）")):
        ids = [f"{c['id']} {c['topic']}" for c in cells if c["cause_state"] == s]
        L.append(f"- **{label}**（{len(ids)}）：{'；'.join(ids) if ids else '無'}")
    ids = [f"{c['id']} {c['topic']}" for c in cells if c["cause_state"].startswith("UNCLASSIFIED") or c["cause_state"].startswith("UNSTABLE")]
    L.append(f"- **UNCLASSIFIED／UNSTABLE（交裁決或加講法重量）**（{len(ids)}）：{'；'.join(ids) if ids else '無'}")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demand"); ap.add_argument("--out"); ap.add_argument("--render")
    ap.add_argument("--api", default="http://localhost:8100/api/v1/message")
    ap.add_argument("--threshold", type=float, default=float(os.getenv("PRESALES_GROUNDING_THRESHOLD", "0.5")))
    ap.add_argument("--head", default="unknown"); ap.add_argument("--image", default="unknown"); ap.add_argument("--g2", default="")
    ap.add_argument("--no-api", action="store_true")
    ap.add_argument("--topics", default="", help="主題模式：topics JSON（主題＋owner＋問法樣本）")
    ap.add_argument("--only", default="", help="只重跑這些格（逗號分隔），其餘從 --merge-into 沿用")
    ap.add_argument("--merge-into", default="", help="既有 map JSON；與 --only 併用")
    a = ap.parse_args()
    if a.render:
        sys.stdout.write(render(a.render))
    elif a.topics:
        sys.exit(asyncio.run(run_topics(a)))
    else:
        sys.exit(asyncio.run(run(a)))
