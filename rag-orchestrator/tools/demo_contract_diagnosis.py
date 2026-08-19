"""一次性驗證（不 commit）：用「真的」元件跑,不自己造 filter/格式化。

真：ConversationalConfig（讀 8.1 種子）、ConversationalEngine 控制流、_ground_by_api、
    APICallHandler.execute_api_call、JGBSystemAPI mock（_mock_get_contracts，原樣）、
    jgb_response_formatter（原樣）。→ 完全是系統的行為,我不插手過濾/格式化。
仍 stub（無 OpenAI，無法跑真 LLM）：optimizer.conversational_step 逐輪腳本化、規則/系統脈絡。
"""
import asyncio
import json
import os
import re
from unittest.mock import AsyncMock, MagicMock

os.environ.setdefault("USE_MOCK_JGB_API", "true")

from services.api_call_handler import APICallHandler
from services.conversational_engine import ConversationalEngine
from services import conversational_config as cc

SEED = os.path.join(os.path.dirname(__file__), "..", "database", "migrations",
                    "seed_conversational_diagnosis_contract_rule.sql")


def _load_seed_config():
    with open(SEED, encoding="utf-8") as f:
        sql = f.read()
    block = re.search(r"-- BEGIN_METADATA_JSON(.*?)-- END_METADATA_JSON", sql, re.DOTALL).group(1)
    return cc._config_from_row(["property_manager"], json.loads(block[block.index("{"):block.rindex("}") + 1]))


CFG = _load_seed_config()


def _build_engine():
    handler = APICallHandler(db_pool=None)   # 真 handler：api_registry['jgb_contracts']=真 JGBSystemAPI.get_contracts
    eng = ConversationalEngine(
        db_pool=MagicMock(), optimizer=MagicMock(), retriever=MagicMock(),
        get_system_context=AsyncMock(return_value="SYS"),
        rules_loader=AsyncMock(return_value="合約診斷 persona"), api_handler=handler)
    store = {}
    async def get_state(sid): return store.get(sid)
    async def _start(sid, uid, vid, ck, seed_topic=None, role_id=None):
        st = {"config_key": ck, "collected_fields": {}, "asked_count": 0,
              "session_id": sid, "user_id": uid, "vendor_id": vid, "role_id": role_id}
        store[sid] = st; return st
    async def _save(sid, state): store[sid] = state
    eng.get_state, eng._start, eng._save = get_state, _start, _save
    return eng, store


ASK = {"action": "ask", "converge_kind": "answer", "extracted_fields": {},
       "next_question": "請問是哪一份合約？可給合約編號或物件名稱。"}
def CONVERGE(ref):
    return {"action": "converge", "converge_kind": "answer", "extracted_fields": {"contract_ref": ref}}


def _script(steps):
    it = iter(steps)
    return lambda *a, **k: next(it)


async def turn(eng, sid, msg):
    d = await eng.prepare(sid, "u1", 7, msg, config=CFG, start_if_absent=True, role_id="20151")
    if d is None:
        print("    ⟶ (降級 None)"); return
    if d["kind"] == "ask":
        print(f'    ⟶ ask：{d["answer"]}')
    else:
        print(f'    ⟶ converge｜grounding：\n        {d["grounding"]}')


async def raw_api_probe():
    """直接看真 handler 對 jgb_contracts 的原始回傳（不經引擎）——證明 mock 實際行為。"""
    h = APICallHandler(db_pool=None)
    api_config = {"endpoint": "jgb_contracts", "params": CFG.grounding_scope["params"]}
    for label, form in [("keyword=套房", {"contract_ref": "套房"}),
                        ("keyword=和平大樓", {"contract_ref": "和平大樓"}),
                        ("contract_ids=678", {"contract_ref": "678"})]:
        r = await h.execute_api_call(api_config, {"role_id": "20151", "vendor_id": 7}, form)
        rows = (r.get("data") or {}).get("data") if isinstance(r.get("data"), dict) else None
        n = len(rows) if isinstance(rows, list) else "?"
        titles = [x.get("title") for x in rows] if isinstance(rows, list) else None
        print(f'  {label:16s} → success={r.get("success")} 筆數={n} titles={titles}')


async def scenario(title, msgs):
    print(f"\n{'='*70}\n{title}\n{'='*70}")
    eng, store = _build_engine()
    eng.optimizer.conversational_step = _script([s for _, s in msgs if s is not None])
    sid = "demo-" + title[:6]
    for i, (msg, _s) in enumerate(msgs, 1):
        print(f'\n  第{i}輪　使用者：「{msg}」')
        await turn(eng, sid, msg)
        st = store.get(sid, {})
        if st.get("pending_candidates"):
            print(f'        （pending_candidates＝{[c["label"] for c in st["pending_candidates"]]}）')
        print(f'        （collected_fields＝{st.get("collected_fields")}，asked_count＝{st.get("asked_count")}）')


async def main():
    print(f"設定：key={CFG.key} select={CFG.grounding_scope.get('select')} endpoint={CFG.grounding_scope.get('endpoint')}")
    await scenario("完整一輪　模糊→追問→給完整物件名(3筆)→列候選→選2→單筆收斂(真 API 真格式化)",
                   [("我的合約狀態怪怪的", ASK),
                    ("基隆溫馨一人宅套房", CONVERGE("基隆溫馨一人宅套房")),
                    ("2", None)])   # 第3輪走插點A(pre-LLM)


if __name__ == "__main__":
    asyncio.run(main())
