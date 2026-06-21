"""
對話式回答設定管理 API（option-routing R19 / 設計 X4）。

讓後台畫面管理「對話規則」設定，免下 SQL。每筆設定存於 knowledge_base
（category='對話規則'）：answer=persona 規則文字、target_user=[角色]、
generation_metadata.conversational_config=設定本體（answer_mode/grounding_scope/
entry/topic_scope/enabled/seed）。寫入後清快取（config + rules）。
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()

CONFIG_CATEGORY = "對話規則"
# 與 routers/chat.py TARGET_USER_ROLES 一致（角色白名單，安全防呆）
ALLOWED_ROLES = ['tenant', 'landlord', 'property_manager', 'system_admin', 'prospect']


class ConversationalConfigPayload(BaseModel):
    id: Optional[int] = None          # 有則更新，無則新增
    label: str                        # question_summary（顯示用標題）
    target_user: str                  # 角色（persona_role）
    rules_text: str                   # persona 規則（→ knowledge_base.answer）
    config: Dict[str, Any] = {}       # 設定本體（answer_mode/grounding_scope/entry/topic_scope/enabled/seed）
    is_active: bool = True


def _reset_caches() -> None:
    try:
        from services.conversational_config import reset_cache as reset_cfg
        from services.conversational_rules import reset_cache as reset_rules
        reset_cfg()
        reset_rules()
    except Exception as e:
        print(f"⚠️ 清對話設定快取失敗：{e}")


def _parse_md(md: Any) -> Dict[str, Any]:
    if isinstance(md, str):
        try:
            return json.loads(md or "{}")
        except Exception:
            return {}
    return md or {}


@router.get("/api/v1/conversational-configs")
async def list_configs(request: Request) -> List[Dict[str, Any]]:
    """列出所有對話設定。"""
    db_pool = request.app.state.db_pool
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, question_summary, answer, target_user, is_active, generation_metadata "
            "FROM knowledge_base WHERE category = $1 ORDER BY id",
            CONFIG_CATEGORY,
        )
    out = []
    for r in rows:
        md = _parse_md(r["generation_metadata"])
        out.append({
            "id": r["id"],
            "label": r["question_summary"],
            "target_user": (r["target_user"] or [None])[0],
            "rules_text": r["answer"],
            "is_active": r["is_active"],
            "config": md.get("conversational_config") or {},
        })
    return out


@router.post("/api/v1/conversational-configs")
async def upsert_config(payload: ConversationalConfigPayload, request: Request) -> Dict[str, Any]:
    """新增/更新一筆對話設定（寫 knowledge_base + 清快取）。"""
    if payload.target_user not in ALLOWED_ROLES:
        raise HTTPException(400, f"target_user 必須是 {ALLOWED_ROLES} 之一")
    cfg = dict(payload.config or {})
    # persona_role 以 target_user 為準；answer_mode 預設 conversational
    cfg["persona_role"] = payload.target_user
    cfg.setdefault("answer_mode", "conversational")
    cfg.setdefault("key", payload.target_user)
    if cfg["answer_mode"] not in ("direct", "conversational"):
        raise HTTPException(400, "answer_mode 必須是 direct 或 conversational")
    md = {"conversational_config": cfg}

    db_pool = request.app.state.db_pool
    async with db_pool.acquire() as conn:
        if payload.id:
            row = await conn.fetchrow(
                "UPDATE knowledge_base SET question_summary=$2, answer=$3, target_user=$4::text[], "
                "is_active=$5, generation_metadata = COALESCE(generation_metadata,'{}'::jsonb) || $6::jsonb, "
                "updated_at=now() WHERE id=$1 AND category=$7 RETURNING id",
                payload.id, payload.label, payload.rules_text, [payload.target_user],
                payload.is_active, json.dumps(md), CONFIG_CATEGORY,
            )
            if not row:
                raise HTTPException(404, f"找不到設定 id={payload.id}")
            cid = row["id"]
        else:
            row = await conn.fetchrow(
                "INSERT INTO knowledge_base (question_summary, answer, category, target_user, "
                "is_active, generation_metadata) VALUES ($1,$2,$3,$4::text[],$5,$6::jsonb) RETURNING id",
                payload.label, payload.rules_text, CONFIG_CATEGORY, [payload.target_user],
                payload.is_active, json.dumps(md),
            )
            cid = row["id"]
    _reset_caches()
    return {"id": cid, "ok": True, "note": "已儲存並清快取（新設定即時生效）"}


@router.delete("/api/v1/conversational-configs/{config_id}")
async def delete_config(config_id: int, request: Request) -> Dict[str, Any]:
    """刪除一筆對話設定。"""
    db_pool = request.app.state.db_pool
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "DELETE FROM knowledge_base WHERE id=$1 AND category=$2 RETURNING id",
            config_id, CONFIG_CATEGORY,
        )
    if not row:
        raise HTTPException(404, f"找不到設定 id={config_id}")
    _reset_caches()
    return {"ok": True}
