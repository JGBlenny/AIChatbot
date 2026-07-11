"""integration：續跑補圖併槽（conversational-repair 任務 2.4 / R2.6）。

真 DB（form_sessions 偽會話）＋真引擎狀態 SQL（_start/get_state/_save）＋mock Vision。
驗證對話進行中補圖：辨識結果經 engine.ingest_recognition 併入現有會話 collected_fields，
且落地到 form_sessions.collected_data（跨進程可讀）——不中斷對話、不覆蓋已填槽。

前置：僅需 form_sessions 表（既有）。不依賴修繕面向配置 seed（3.3），故可獨立跑。
DB 不可達 → skip。
"""
import json
import os

import pytest

pytestmark = pytest.mark.integration


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.fixture
async def pool():
    import asyncpg
    try:
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    except Exception as e:
        pytest.skip(f"無法連 DB：{e}")
        return
    yield p
    await p.close()


def _tx_scope():
    return {
        "select": "api",
        "required_slots": ["estate", "category", "urgency"],
        "execute_endpoint": "jgb_create_repair",
        "inference_confidence": 0.7,
        "candidate_max": 3,
        "facet_key": "repair",
    }


def _tx_cfg():
    from services.conversational_config import ConversationalConfig
    return ConversationalConfig(key="repair_it", persona_role="tenant",
                                grounding_scope=_tx_scope())


def _repair_tree():
    """修繕分類樹（get_repair_categories 形狀）：含「冷氣」→「室內機」以供名稱→id 解析。"""
    return {
        "success": True,
        "data": [
            {"id": 11, "name": "冷氣", "items": [
                {"id": 101, "name": "室內機", "broken_reasons": ["漏水"]},
            ]},
        ],
    }


def _engine(pool):
    from unittest.mock import AsyncMock, MagicMock
    from services.conversational_engine import ConversationalEngine
    # api_handler.jgb_api.get_repair_categories 需為 async（ingest 走名稱→id 解析）；
    # 純 MagicMock 的 get_repair_categories 不可 await，會降級成顯示名候選（非本測試意圖）。
    api_handler = MagicMock()
    api_handler.jgb_api.get_repair_categories = AsyncMock(return_value=_repair_tree())
    return ConversationalEngine(
        db_pool=pool, optimizer=MagicMock(), retriever=None,
        get_system_context=AsyncMock(return_value="SYS"),
        rules_loader=AsyncMock(return_value="RULES"), api_handler=api_handler)


async def _cleanup(pool, sid):
    await pool.execute("DELETE FROM form_sessions WHERE session_id=$1", sid)


@pytest.mark.req("conversational-repair:2.6")
async def test_continuation_image_merges_into_persisted_session(pool):
    """已存在的修繕會話補圖：高信心辨識 → 分類槽併入並落地 form_sessions。"""
    sid = "it-repair-ingest-1"
    eng = _engine(pool)
    await _cleanup(pool, sid)
    try:
        # 起一個進行中修繕會話（estate 已由使用者/prefill 填，category 尚空）。
        state = await eng._start(sid, "u-it", 2, "repair_it", role_id="r-it")
        state["collected_fields"] = {"estate": {"value": "信義套房", "source": "user"}}
        await eng._save(sid, state)

        recognition = {"is_damage": True, "confidence": 0.9,
                       "suggested_category": "冷氣", "suggested_item": "室內機",
                       "suggested_reason": "漏水", "suggested_emergency": 1}
        await eng.ingest_recognition(sid, recognition, _tx_cfg())

        # 讀回 DB 落地狀態（跨呼叫可見）。
        reloaded = await eng.get_state(sid)
        cf = reloaded["collected_fields"]
        assert cf["estate"]["value"] == "信義套房", "既有使用者槽位保留"
        assert cf["category"]["value"] == "冷氣" and cf["category"]["source"] == "inferred"
        # 急迫性推斷落 emergency_status 槽（classify_recognition 對齊 execute_params）。
        assert cf["emergency_status"]["value"] == 1 and cf["emergency_status"]["source"] == "inferred"
    finally:
        await _cleanup(pool, sid)


@pytest.mark.req("conversational-repair:2.6")
async def test_continuation_low_confidence_sets_candidates_persisted(pool):
    """低信心辨識 → 候選寫入 pending_candidates 並落地（下一輪確定性選擇）。"""
    sid = "it-repair-ingest-2"
    eng = _engine(pool)
    await _cleanup(pool, sid)
    try:
        state = await eng._start(sid, "u-it", 2, "repair_it", role_id="r-it")
        await eng._save(sid, state)
        recognition = {"is_damage": True, "confidence": 0.4,
                       "suggested_category": "冷氣", "secondary_damages": ["牆面"]}
        await eng.ingest_recognition(sid, recognition, _tx_cfg())
        reloaded = await eng.get_state(sid)
        assert reloaded.get("pending_candidates"), "低信心應落地候選"
        assert "category" not in reloaded.get("collected_fields", {})
    finally:
        await _cleanup(pool, sid)
