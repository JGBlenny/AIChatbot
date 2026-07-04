# -*- coding: utf-8 -*-
"""一次性（不 commit）：548 題全量乾淨重跑＋強化 rubric 雙票評審。"""
import asyncio, json, os, uuid
import aiohttp, psycopg2
from openai import AsyncOpenAI

BASE = os.getenv("RAG_API_URL", "http://rag-orchestrator:8100")
client = AsyncOpenAI()
RUBRIC = """你是客服品質評審。系統是「多輪對話式」客服。輸出 JSON：{"grade":"...","why":"12字內"}
判定規則（依序）：
1. 回答的主要內容是「反問/要求提供資訊」（如請提供編號、請問您是想…嗎）才可能是 ASK_*；
   只要回答含有實質的說明內容（流程/條件/定義/步驟），一律不是 ASK_*。
2. ASK_OK：追問合理——問題需要特定對象（某份合約/帳單/物件/成員）或確有歧義需分流。
   ASK_BAD：問題是通則（流程/定義/功能說明），不需任何特定對象即可回答，卻被要求提供識別。
3. GOOD：實質回答且主題對——能回答到問題的核心即可，不要求逐字完備。
4. WRONG：實質回答但主題錯位/答非所問（講了別的功能）。
5. NOFOUND：回答「找不到資訊、請聯絡客服」。
6. BROKEN：系統錯誤訊息（找不到表單定義/請重新開始/亂碼）。"""

conn = psycopg2.connect(host=os.getenv("DB_HOST","postgres"), dbname="aichatbot_admin",
                        user="aichatbot", password=os.getenv("DB_PASSWORD",""))
cur = conn.cursor()
cur.execute("""SELECT DISTINCT ON (r.test_question) r.test_question,
       COALESCE(s.expected_answer,''), COALESCE(array_to_string(s.expected_keywords,'、'),'')
FROM backtest_results r LEFT JOIN test_scenarios s ON s.test_question=r.test_question
WHERE r.run_id=291 ORDER BY r.test_question""")
rows = cur.fetchall()
print(f"全量 {len(rows)} 題")

sem_api = asyncio.Semaphore(4); sem_llm = asyncio.Semaphore(10)

async def ask(session, q):
    async with sem_api:
        for attempt in range(3):
            try:
                async with session.post(f"{BASE}/api/v1/message", json={
                    "message": q, "vendor_id": 2, "mode": "b2b",
                    "target_user": "property_manager", "role_id": "37305",
                    "session_id": f"fc-{uuid.uuid4().hex[:10]}", "stream": False},
                    timeout=aiohttp.ClientTimeout(total=90)) as r:
                    d = await r.json()
                    return (d.get("answer") or "").strip()
            except Exception:
                if attempt == 2: return "[REQUEST_FAILED]"
                await asyncio.sleep(3*(attempt+1))

async def vote(q, a, exp, kw):
    u = f"問題：{q}\n系統回答：{a[:500]}"
    if exp: u += f"\n（參考）期望答案要點：{exp[:200]}"
    elif kw: u += f"\n（參考）期望關鍵詞：{kw}"
    r = await client.chat.completions.create(model="gpt-4o-mini", temperature=0,
        response_format={"type":"json_object"},
        messages=[{"role":"system","content":RUBRIC},{"role":"user","content":u}])
    return json.loads(r.choices[0].message.content).get("grade","?")

async def grade(q, a, exp, kw):
    async with sem_llm:
        try:
            v1 = await vote(q, a, exp, kw)
            v2 = await vote(q, a, exp, kw)
            if v1 == v2: return v1
            v3 = await vote(q, a, exp, kw)   # 仲裁票
            return v3 if v3 in (v1, v2) else v1
        except Exception:
            return "EVAL_ERR"

async def main():
    async with aiohttp.ClientSession() as session:
        answers = await asyncio.gather(*[ask(session, q) for q,_,_ in rows])
    grades = await asyncio.gather(*[grade(q, a, exp, kw) for (q,exp,kw), a in zip(rows, answers)])
    from collections import Counter
    c = Counter(grades); n = len(grades)
    ok = c.get("GOOD",0)+c.get("ASK_OK",0)
    print("@@DIST@@", dict(c.most_common()))
    print(f"@@FINAL@@ 合格 {ok}/{n} = {ok/n*100:.1f}%")
    json.dump([{"q":q,"a":a[:300],"grade":g} for (q,_,_),a,g in zip(rows,answers,grades)],
              open("/app/scripts/backtest/fullclean_out.json","w",encoding="utf-8"), ensure_ascii=False)
asyncio.run(main())
