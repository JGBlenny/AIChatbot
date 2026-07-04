# -*- coding: utf-8 -*-
"""一次性回填（不 commit）：4389 題 LLM 受眾分類 → request_target_user/mode。"""
import asyncio, json, os
import psycopg2
from openai import AsyncOpenAI

conn = psycopg2.connect(host=os.getenv("DB_HOST","postgres"), dbname="aichatbot_admin",
                        user="aichatbot", password=os.getenv("DB_PASSWORD",""))
cur = conn.cursor()
cur.execute("SELECT id, test_question FROM test_scenarios WHERE request_target_user IS NULL ORDER BY id")
rows = cur.fetchall()
print(f"待分類 {len(rows)}")

client = AsyncOpenAI(); sem = asyncio.Semaphore(16)
SYS = """判斷這句客服問題的「提問者角色」。輸出 JSON {"role":"..."}，三選一：
- property_manager：房東/物管/業者視角——管理物件、發帳單、建合約、收租、開發票、設定系統、處理租客的申請
- tenant：租客視角——繳我的房租、我的押金、我要報修、我的帳單、我要搬走、房間設備問題
- prospect：還沒使用系統的潛在客戶——詢價、方案比較、適不適合我、功能有沒有
判斷依據是「誰會問這句話」，模糊時依語氣與利益方向judge。"""

async def cls(sid, q):
    async with sem:
        try:
            r = await client.chat.completions.create(model="gpt-4o-mini", temperature=0,
                response_format={"type":"json_object"},
                messages=[{"role":"system","content":SYS},{"role":"user","content":q}])
            role = json.loads(r.choices[0].message.content).get("role","")
            return sid, role if role in ("property_manager","tenant","prospect") else None
        except Exception:
            return sid, None

async def main():
    out = await asyncio.gather(*[cls(sid,q) for sid,q in rows])
    ok = [(r, "b2c" if r=="tenant" else "b2b", sid) for sid, r in out if r]
    from psycopg2.extras import execute_batch
    execute_batch(cur, "UPDATE test_scenarios SET request_target_user=%s, request_mode=%s WHERE id=%s", ok, page_size=200)
    conn.commit()
    from collections import Counter
    print("@@DONE@@", dict(Counter(r for _,r in out if r)), "未分類:", sum(1 for _,r in out if not r))

asyncio.run(main())
