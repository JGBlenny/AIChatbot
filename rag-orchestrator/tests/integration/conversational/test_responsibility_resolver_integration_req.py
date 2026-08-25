"""integration：pre-commit responsibility resolver 的 causal acceptance（slice 4）。

⚠️ **零 OpenAI**：responsibility evaluator 為腳本化替身；本檔驗的是**因果鏈與副作用**，
不是模型判得對不對（那要真 LLM，屬另一輪）。

兩個因果命題：

```text
① pre-entry 與 in-session 取到的 responsibility context **同源**（真 DB，鎖 slice 1 不被設定漂移打回）
② 解析期間**不建立任何 session**——錯的第一候選不得留下 transient COMPLETED 列
```
"""
import asyncio
import os

import pytest

pytestmark = pytest.mark.integration

FACETS = ("bill_diagnosis", "billing_anomaly", "contract_closeout")


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_test"),
    )


@pytest.fixture
async def pool():
    import asyncpg
    from services import conversational_config as cc
    try:
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    except Exception as e:                                   # pragma: no cover
        pytest.skip(f"無法連 DB：{e}")
        return
    cc.reset_cache()
    yield p
    cc.reset_cache()
    await p.close()


# ── ① context 同源（slice 1 的 production 面鎖）──────────────────────────────
@pytest.mark.req("face-exit-before-grounding:1")
@pytest.mark.parametrize("facet", FACETS)
async def test_preentry_context_matches_in_session(pool, facet):
    """實測病灶的回歸鎖：pre-entry 曾以 cfg.key 取脈絡，與 in-session 不同源。"""
    from services.conversational_config import config_for_key
    from services.conversational_engine import _domain_key
    from services.responsibility import build_responsibility_context, _digest
    from services.system_context import get_system_context

    cfg = await config_for_key(pool, facet)
    if cfg is None:
        pytest.skip(f"面向 {facet} 未供裝")
    rctx = await build_responsibility_context(pool, cfg)
    assert rctx is not None, f"{facet} 的 persona 規則取不到"

    in_session_md = await get_system_context(pool, _domain_key(cfg))
    assert rctx.context_key == _domain_key(cfg)
    assert rctx.context_digest == _digest(in_session_md), (
        f"{facet}：pre-entry 與 in-session 的 system context 不同源——"
        f"進場前判的不是進場後那件事")


# ── ② 解析不產生 session（錯的第一候選不留 transient 列）──────────────────────
async def _conversational_rows(session_id):
    import asyncpg
    conn = await asyncpg.connect(**_conn_kwargs())
    try:
        return await conn.fetchval(
            "SELECT count(*) FROM form_sessions WHERE session_id=$1 AND form_id='conversational'",
            session_id)
    finally:
        await conn.close()


@pytest.mark.req("face-exit-before-grounding:1")
async def test_resolution_commits_the_delegated_face_without_creating_sessions(pool):
    """bill_diagnosis → billing_anomaly → contract_closeout：只有最後一個被 commit，
    且**整段解析沒有建立任何 session 列**。"""
    import uuid

    from services.conversational_config import config_for_key
    from services.responsibility import resolve_entry_candidate

    cfgs = {f: await config_for_key(pool, f) for f in FACETS}
    if any(c is None for c in cfgs.values()):
        pytest.skip("面向未供裝")

    # 契約側白名單以測試注入（DB 尚未填 responsibility 資料——那屬資料側工作）
    cfgs["bill_diagnosis"].responsibility = {"delegates": [{"target": "billing_anomaly"}]}
    cfgs["billing_anomaly"].responsibility = {"delegates": [{"target": "contract_closeout"}]}
    cfgs["contract_closeout"].responsibility = {}

    from services.conversational_rules import load_rules
    # rules 原文 → 面向鍵（rules 由**真 DB** 取得，故也順帶證明 evaluator 餵的是真規則）
    rules_to_facet = {await load_rules(pool, c.persona_role): f for f, c in cfgs.items()}
    script = {"bill_diagnosis": ("switch", "billing_anomaly"),
              "billing_anomaly": ("switch", "contract_closeout"),
              "contract_closeout": ("stay", None)}

    class _ScriptedBrain:
        def __init__(self):
            self.seen = []

        async def conversational_step(self, rules, system_md, state, msg, **kw):
            facet = rules_to_facet[rules]          # 餵錯規則會在此 KeyError
            scope, delegate = script[facet]
            self.seen.append((facet, kw.get("delegates")))
            out = {"action": "ask", "next_question": "q", "scope": scope}
            if delegate:
                out["delegate_facet_key"] = delegate
            return out

    brain = _ScriptedBrain()

    sid = f"resolver-it-{uuid.uuid4().hex[:8]}"
    assert await _conversational_rows(sid) == 0

    res = await resolve_entry_candidate(pool, cfgs["bill_diagnosis"], "幫我查點退帳單金額",
                                        optimizer=brain)

    assert res.committed_key == "contract_closeout", f"chain={res.chain}"
    assert res.stop_reason == "stay"
    assert [h["facet_key"] for h in res.chain] == list(FACETS)
    assert [k for k, _ in brain.seen] == list(FACETS)
    # 白名單確實由 contract 提供（元素為 (target, when)，when 未宣告時為 None）
    assert [t for t, _ in brain.seen[0][1]] == ["billing_anomaly"]
    assert [t for t, _ in brain.seen[1][1]] == ["contract_closeout"]
    assert brain.seen[2][1] is None
    # ★ 因果重點：整段解析沒有建立任何 session
    assert await _conversational_rows(sid) == 0, "解析期間不得建立 session"
