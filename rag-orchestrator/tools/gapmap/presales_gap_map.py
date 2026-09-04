#!/usr/bin/env python3
"""售前缺口地圖（PLAN-retrieval-coverage P2.5，業主 2026-09-04 定最優先）。

輸入 demand JSON（需求側格子：模組×主題×代表問句×關鍵詞×policy），對每格：
  ① 元件層：retrieve()（prospect 池，return_unfiltered）取 top-3 與分數 ⇒ 判「供給有／表示法缺／缺口」（⚠️ 只做成因分類，⛔ 不得當療效）
  ② 關鍵詞：ILIKE 掃 prospect 可見池（含 target_user IS NULL 通用列）⇒ 區分 S（有列撈不到）與 N（真無）
  ③ 使用者層：POST /api/v1/message 冷 session（backtest_session_ 前綴）⇒ 固定句／非固定句
輸出 map JSON；`--render` 把 JSON 轉成 Markdown 表。⛔ 不寫 DB。須在 rag-orchestrator 容器內跑（要 services 與 DB／API 網路）。

用法（容器內）：python3 tools/gapmap/presales_gap_map.py --demand demand.json --out map.json [--api http://localhost:8100/api/v1/message] [--threshold 0.5]
      渲染（任一處）：python3 tools/gapmap/presales_gap_map.py --render map.json > map.md
"""
import argparse, asyncio, json, os, sys, time, urllib.request, uuid

FIXED = "這題我這邊沒有可靠資料，幫您轉專人——點下方的『找真人』。"
POOL_SQL = ("SELECT id, question_summary FROM knowledge_base WHERE is_active AND answer<>'' "
            "AND business_types && ARRAY['system_provider'] AND (target_user IS NULL OR target_user && ARRAY['prospect']) "
            "AND (question_summary ILIKE $1 OR answer ILIKE $1) LIMIT 5")


def ask(api, msg, sid):
    body = json.dumps({"message": msg, "mode": "b2b", "target_user": "prospect", "session_id": sid}).encode()
    req = urllib.request.Request(api, data=body, headers={"Content-Type": "application/json"})
    t = time.time()
    with urllib.request.urlopen(req, timeout=240) as r:
        d = json.loads(r.read().decode())
    return {"answer": d.get("answer"), "handoff": d.get("handoff"), "elapsed_s": round(time.time() - t, 2)}


def classify(cell, top, kw_hits, api, threshold):
    is_fixed = (api or {}).get("answer") == FIXED
    if cell["policy"] == "deliberate_no":
        return "刻意不補", ("✅ 固定句" if is_fixed else "⚠️ 未走固定句")
    supply = bool(top) and float(top[0]["similarity"]) >= threshold
    if supply and not is_fixed:
        return "已覆蓋", f"top-1 {top[0]['id']} {top[0]['similarity']:.3f}"
    if supply and is_fixed:
        return "有知識被擋", f"top-1 {top[0]['id']} {top[0]['similarity']:.3f} 但入口固定句"
    if kw_hits:
        return "表示法缺", f"top-1 {top[0]['id'] if top else '-'} {top[0]['similarity'] if top else 0:.3f}；關鍵詞命中 {[h['id'] for h in kw_hits][:5]}" + ("" if is_fixed else "；入口非固定句（LLM 以系統脈絡答）")
    return "缺口(待G0)", ("入口固定句" if is_fixed else "入口非固定句（LLM 以系統脈絡答，需核對）")


async def run(args):
    sys.path.insert(0, "/app")
    import asyncpg
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
    demand = json.load(open(args.demand, encoding="utf-8"))
    r = VendorKnowledgeRetrieverV2()
    conn = await asyncpg.connect(host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
                                 user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
                                 database=os.getenv("DB_NAME", "aichatbot_admin"))
    out = {"_meta": {**demand["_meta"], "run_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "threshold": args.threshold, "api": args.api}, "cells": []}
    for c in demand["cells"]:
        q = c["questions"][0]
        res = await r.retrieve(query=q, vendor_id=0, top_k=3, similarity_threshold=0.0, target_user="prospect", mode="b2b", return_unfiltered=True)
        top = [{"id": x.get("id"), "similarity": round(float(x.get("similarity") or 0), 3), "q": (x.get("question_summary") or "")[:20]} for x in res[:3]]
        kw_hits = []
        for k in c.get("keywords", []):
            rows = await conn.fetch(POOL_SQL, f"%{k}%")
            kw_hits += [{"id": row["id"], "q": row["question_summary"][:20], "kw": k} for row in rows]
        api = None
        if not args.no_api:
            try:
                api = ask(args.api, q, f"backtest_session_gapmap_{c['id']}_{uuid.uuid4().hex[:4]}")
            except Exception as e:
                api = {"answer": None, "handoff": None, "error": repr(e)}
        state, evidence = classify(c, top, kw_hits, api, args.threshold)
        out["cells"].append({**c, "measured_question": q, "top3": top, "keyword_hits": kw_hits[:8], "api": api, "state": state, "evidence": evidence})
        print(f"{c['id']} {state:8} {c['module']}/{c['topic'][:16]:16} {evidence[:70]}", flush=True)
        json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    await conn.close()
    print("saved", args.out)


def render(path):
    m = json.load(open(path, encoding="utf-8"))
    cells = m["cells"]; order = ["已覆蓋", "有知識被擋", "表示法缺", "缺口(待G0)", "刻意不補"]
    counts = {s: sum(1 for c in cells if c["state"] == s) for s in order}
    lines = [f"# 售前缺口地圖 {m['_meta']['version']}（{m['_meta']['run_at'][:10]}，門檻 {m['_meta']['threshold']}）", "",
             "> 地圖是盤點不是療效；療效以劇本 e2e 為準。元件層分數只用來分 S／N。", "",
             "| 狀態 | 格數 |", "|---|---|"] + [f"| {s} | {counts[s]} |" for s in order] + ["", "| # | 模組 | 主題 | 狀態 | 代表問句 | 證據 | 入口回答（前 60 字） | 幫助中心 |", "|---|---|---|---|---|---|---|---|"]
    for c in cells:
        a = ((c.get("api") or {}).get("answer") or "").replace("\n", " ")[:60]
        lines.append(f"| {c['id']} | {c['module']} | {c['topic']} | **{c['state']}** | {c['measured_question'][:28]} | {c['evidence']} | {a} | {'、'.join(c.get('help_center', [])) or '-'} |")
    lines += ["", "## 下一輪選題（依狀態）", ""]
    for s in ("有知識被擋", "表示法缺", "缺口(待G0)"):
        ids = [f"{c['id']} {c['topic']}" for c in cells if c["state"] == s]
        lines.append(f"- **{s}**（{len(ids)}）：" + ("；".join(ids) if ids else "無"))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demand"); ap.add_argument("--out"); ap.add_argument("--render")
    ap.add_argument("--api", default="http://localhost:8100/api/v1/message"); ap.add_argument("--threshold", type=float, default=float(os.getenv("PRESALES_GROUNDING_THRESHOLD", "0.5")))
    ap.add_argument("--no-api", action="store_true")
    a = ap.parse_args()
    if a.render:
        sys.stdout.write(render(a.render))
    else:
        asyncio.run(run(a))
