"""一次性真實 e2e（不 commit）：真 db_pool + 真 LLM(gpt-4o) + 真 jgb2 API + 真設定。

完全比照 app.py 組裝 ConversationalEngine，跑多輪對話、多合約狀態，印出「成像」（真實使用者
看到的回覆）。驗證 API 驗證式流程：id/數字名稱/同名消歧/切換回滾/查無重識別。
role_id=20151（property_manager）。session 用唯一 id，跑前先關殘留 COLLECTING。
"""
import asyncio
import os
import uuid

import asyncpg

os.environ["USE_MOCK_JGB_API"] = "false"  # 真 jgb2 preview

from services.conversational_engine import ConversationalEngine
from services.conversational_rules import load_rules
from services.system_context import get_system_context
from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
from services.api_call_handler import get_api_call_handler
from services.llm_answer_optimizer import LLMAnswerOptimizer
from services.conversational_config import get_config

ROLE_ID = "20151"
VENDOR_ID = 7


async def _pool():
    return await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "postgres"), port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aichatbot_admin"), user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"), min_size=2, max_size=6)


def _build_engine(pool):
    return ConversationalEngine(
        db_pool=pool,
        optimizer=LLMAnswerOptimizer(config={"enable_synthesis": False}),
        retriever=VendorKnowledgeRetrieverV2(),
        get_system_context=get_system_context,
        rules_loader=load_rules,
        api_handler=get_api_call_handler(pool),
    )


async def _snapshot(pool, sid):
    async with pool.acquire() as c:
        row = await c.fetchrow(
            "SELECT collected_data FROM form_sessions WHERE session_id=$1 AND form_id='conversational' "
            "AND state='COLLECTING' ORDER BY id DESC LIMIT 1", sid)
    if not row or not row["collected_data"]:
        return {}, None
    import json
    cd = row["collected_data"]
    cd = cd if isinstance(cd, dict) else json.loads(cd)
    cands = [c.get("label") for c in (cd.get("pending_candidates") or [])]
    return cd.get("collected_fields"), (cands or None)


async def run(pool, eng, cfg, title, turns):
    sid = f"e2e-{uuid.uuid4().hex[:10]}"
    print(f"\n{'='*78}\n{title}\n{'='*78}")
    for i, msg in enumerate(turns, 1):
        print(f"\n  第{i}輪  👤 使用者：「{msg}」")
        res = await eng.handle(sid, "u1", VENDOR_ID, msg, config=cfg,
                               start_if_absent=True, role_id=ROLE_ID)
        if res is None:
            print("        🤖 (降級 None — 交一般流程)")
        else:
            ans = (res.get("answer") or "").strip()
            tag = "收斂✅" if res.get("converged") else ("追問" if res.get("conversational") else "?")
            print(f"        🤖 [{tag}] {ans}")
        cf, cands = await _snapshot(pool, sid)
        print(f"        └─ collected={cf}" + (f"  candidates={cands}" if cands else ""))
    async with pool.acquire() as c:
        await c.execute("UPDATE form_sessions SET state='COMPLETED' WHERE session_id=$1", sid)


async def main():
    pool = await _pool()
    cfg = await get_config(pool, "contract_diag")
    print(f"設定 key={cfg.key} select={cfg.grounding_scope.get('select')} "
          f"search_params={cfg.grounding_scope.get('search_params')}")
    eng = _build_engine(pool)

    # S1 簽約前三態（1 待發送→2 等租客簽→4 等房東簽）＋下一步追問
    await run(pool, eng, cfg, "S1 簽約前三態（1待發送/2等租客/4等房東）＋下一步追問",
              ["幫我看 85100 這份怎麼還沒生效",
               "所以下一步是我要做什麼？",
               "那 84927 呢 這份卡在哪",
               "喔等租客簽。那 84972 咧",
               "這份是換我要簽了對吧？"])

    # S2 執行中雙態＋操作可否（8 待點交三操作 / 32 已點交可續約）
    await run(pool, eng, cfg, "S2 執行中雙態（8待點交/32執行中）＋操作可否追問",
              ["85193",
               "我可以直接點退不點交嗎？",
               "了解。那 84328 這間現在能做什麼",
               "它可以點退嗎？",
               "好，那就先續約"])

    # S3 歷史三態盤點（1024 可點退 / 64 殘留值歷史 / 2048 結束）——最容易幻覺的一組
    await run(pool, eng, cfg, "S3 歷史三態（1024可點退/64歷史無操作/2048結束）連續切換",
              ["84800 這份是不是結束了",
               "那還能退租嗎？",
               "84908 呢 我記得它送過點退",
               "所以點退算完成了嗎？",
               "最後 84912",
               "這幾份都到期了，有哪份還能做事的嗎？"])

    # S4 同名三份不同狀態（消歧→逐份確認→回頭再選另一份）
    await run(pool, eng, cfg, "S4 同名三份不同狀態（消歧→確認→回頭選另一份）",
              ["基隆溫馨一人宅套房",
               "第二個",
               "這份現在什麼狀態",
               "嗯…我要看的好像是另一份。再列一次基隆溫馨一人宅套房",
               "最後一個",
               "這份跟剛剛那份狀態一樣嗎？"])

    # S5 混合壓力（打錯→數字名稱→防誤切→離題→回來→比較）
    await run(pool, eng, cfg, "S5 混合壓力（打錯/0626/防誤切/離題重路由/回來/比較）",
              ["查 88888888",
               "打錯，是 0626",
               "1",
               "月租 20000 沒錯吧",
               "對了幫我報修一下冷氣",
               "回來，0626 那份能點交嗎",
               "它跟 84328 哪個先到期？"])

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
