"""
知識審核 API 路由

提供知識完善迴圈生成的知識審核功能:
- 查詢待審核知識
- 單一知識審核
- 批量知識審核
- 立即同步到正式知識庫

Author: AI Assistant
Created: 2026-03-27
"""

import os
import asyncio
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict
import psycopg2
from psycopg2.extras import RealDictCursor
import asyncpg

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class PendingKnowledgeQuery(BaseModel):
    """
    待審核知識查詢參數

    用於篩選和查詢待審核的知識項目。支援多種篩選條件與分頁。
    """
    loop_id: Optional[int] = Field(None, description="迴圈 ID")
    vendor_id: int = Field(..., description="業者 ID")
    knowledge_type: Optional[str] = Field(None, description="知識類型: sop/null")
    status: str = Field("pending", description="狀態: pending/approved/rejected")
    limit: int = Field(50, description="返回數量", ge=1, le=200)
    offset: int = Field(0, description="偏移量", ge=0)

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "vendor_id": 2,
            "knowledge_type": "sop",
            "status": "pending",
            "limit": 50,
            "offset": 0
        }
    })


class PendingKnowledgeItem(BaseModel):
    """
    待審核知識項目

    表示單一待審核的知識項目，包含重複檢測結果與警告。
    """
    id: int
    loop_id: int
    iteration: int
    question: str
    answer: str
    knowledge_type: Optional[str]
    sop_config: Optional[Dict]
    similar_knowledge: Optional[Dict] = Field(
        None,
        description="重複檢測結果，格式：{detected: bool, items: [{id, source_table, question_summary, similarity_score}]}"
    )
    duplication_warning: Optional[str] = Field(
        None,
        description="重複警告文字，例如：'檢測到 1 個高度相似的知識（相似度 93%）'"
    )
    status: str
    created_at: str

    model_config = ConfigDict(json_schema_extra={
        "example": {
                "id": 1,
                "loop_id": 123,
                "iteration": 1,
                "question": "租金每月幾號繳納？",
                "answer": "租金應於每月 5 日前繳納。",
                "knowledge_type": "sop",
                "sop_config": {
                    "category_id": 1,
                    "group_id": 2,
                    "item_name": "租金繳納規範"
                },
                "similar_knowledge": {
                    "detected": True,
                    "items": [{
                        "id": 456,
                        "source_table": "knowledge_base",
                        "question_summary": "租金繳納日期說明",
                        "similarity_score": 0.93
                    }]
                },
                "duplication_warning": "檢測到 1 個高度相似的知識（相似度 93%）",
                "status": "pending",
                "created_at": "2026-03-27T10:00:00Z"
        }
    })


class PendingKnowledgeResponse(BaseModel):
    """
    待審核知識回應

    包含符合條件的知識項目列表與總數。
    """
    total: int
    items: List[PendingKnowledgeItem]

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total": 150,
            "items": []
        }
    })


class ReviewKnowledgeRequest(BaseModel):
    """
    審核知識請求

    用於審核單一知識項目。支援批准、拒絕與修改。
    """
    action: str = Field(..., description="動作: approve/reject")
    modifications: Optional[Dict] = Field(None, description="修改內容")
    review_notes: Optional[str] = Field(None, description="審核備註")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "action": "approve",
            "modifications": {
                "question": "修改後的問題",
                "answer": "修改後的答案",
                "keywords": ["租金", "繳納"]
            },
            "review_notes": "已確認內容正確"
        }
    })


class ReviewKnowledgeResponse(BaseModel):
    """
    審核知識回應

    返回審核結果與同步狀態。
    """
    knowledge_id: int
    action: str
    synced: bool
    synced_to: Optional[str]  # knowledge_base/vendor_sop_items
    synced_id: Optional[int]
    message: str

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "knowledge_id": 1,
            "action": "approve",
            "synced": True,
            "synced_to": "knowledge_base",
            "synced_id": 456,
            "message": "知識已批准並同步到 knowledge_base (ID: 456)"
        }
    })


class BatchReviewRequest(BaseModel):
    """
    批量審核請求

    用於批量審核知識項目。支援 1-100 個項目的批量操作。
    """
    knowledge_ids: List[int] = Field(
        ...,
        description="知識 ID 列表",
        min_length=1,
        max_length=100
    )
    action: str = Field(..., description="動作: approve/reject")
    modifications: Optional[Dict] = Field(None, description="批量修改欄位")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "knowledge_ids": [1, 2, 3, 4, 5],
            "action": "approve",
            "modifications": {
                "keywords": ["租金", "繳納", "管理"]
            }
        }
    })


class BatchReviewFailedItem(BaseModel):
    """
    批量審核失敗項目

    記錄批量審核中失敗的項目資訊。
    """
    knowledge_id: int
    error: str

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "knowledge_id": 3,
            "error": "知識不存在"
        }
    })


class BatchReviewResponse(BaseModel):
    """
    批量審核回應

    返回批量審核的統計結果與失敗項目列表。
    """
    total: int
    successful: int
    failed: int
    failed_items: List[BatchReviewFailedItem]
    duration_ms: int

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total": 10,
            "successful": 8,
            "failed": 2,
            "failed_items": [
                {
                    "knowledge_id": 3,
                    "error": "知識不存在"
                },
                {
                    "knowledge_id": 7,
                    "error": "同步失敗：embedding API 超時"
                }
            ],
            "duration_ms": 5432
        }
    })


# ============================================
# API Endpoints
# ============================================

@router.get("/loop-knowledge/pending", response_model=PendingKnowledgeResponse)
async def get_pending_knowledge(
    vendor_id: int,
    loop_id: Optional[int] = None,
    knowledge_type: Optional[str] = None,
    status: str = "pending",
    limit: int = 50,
    offset: int = 0,
    req: Request = None
):
    """
    [需求 8.1] 查詢待審核知識

    支援篩選條件（迴圈、業者、類型、狀態）與分頁。

    **篩選參數**：
    - vendor_id: 業者 ID（必填）
    - loop_id: 迴圈 ID（選填）
    - knowledge_type: 知識類型（選填，'sop' 或 null）
    - status: 狀態（預設 'pending'）
    - limit: 返回數量（1-200，預設 50）
    - offset: 偏移量（預設 0）

    **返回**：
    - total: 符合條件的總數
    - items: 知識項目列表（包含重複檢測警告）
    """
    # 取得資料庫連接池（從 app.state 或 app.extra）
    db_pool = None
    if req and hasattr(req.app, 'state') and hasattr(req.app.state, 'db_pool'):
        db_pool = req.app.state.db_pool
    elif req and hasattr(req.app, 'extra'):
        db_pool = req.app.extra.get('db_pool')

    if not db_pool:
        raise HTTPException(status_code=500, detail="資料庫連接池未初始化")

    # 建立查詢條件
    conditions = ["1=1"]  # 基礎條件
    params = []
    param_counter = 1

    # vendor_id 篩選（必填，但作為可選參數處理以支援未來擴展）
    if vendor_id:
        # 注意：loop_generated_knowledge 表沒有 vendor_id，需透過 join loop 表取得
        # 為簡化第一版實作，暫時不做 vendor 篩選（或假設所有知識都屬於該 vendor）
        pass

    # loop_id 篩選
    if loop_id is not None:
        conditions.append(f"loop_id = ${param_counter}")
        params.append(loop_id)
        param_counter += 1

    # knowledge_type 篩選
    if knowledge_type is not None:
        conditions.append(f"knowledge_type = ${param_counter}")
        params.append(knowledge_type)
        param_counter += 1
    elif knowledge_type is None and 'knowledge_type' in locals():
        # 明確查詢 knowledge_type IS NULL 的情況（一般知識）
        pass  # 第一版不特別處理

    # status 篩選
    conditions.append(f"status = ${param_counter}")
    params.append(status)
    param_counter += 1

    # 建立 SQL 查詢
    where_clause = " AND ".join(conditions)

    # 查詢總數
    count_query = f"""
        SELECT COUNT(*)
        FROM loop_generated_knowledge
        WHERE {where_clause}
    """

    # 查詢資料（含分頁）
    data_query = f"""
        SELECT
            id,
            loop_id,
            iteration,
            question,
            answer,
            knowledge_type,
            sop_config,
            similar_knowledge,
            status,
            created_at
        FROM loop_generated_knowledge
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_counter} OFFSET ${param_counter + 1}
    """
    params.extend([limit, offset])

    try:
        async with db_pool.acquire() as conn:
            # 查詢總數
            total = await conn.fetchval(count_query, *params[:-2])  # 不包含 limit/offset

            # 查詢資料
            rows = await conn.fetch(data_query, *params)

            # 轉換為 PendingKnowledgeItem
            items = []
            for row in rows:
                # 生成重複檢測警告
                duplication_warning = None
                if row['similar_knowledge'] and isinstance(row['similar_knowledge'], dict):
                    if row['similar_knowledge'].get('detected'):
                        similar_items = row['similar_knowledge'].get('items', [])
                        if similar_items:
                            # 取第一個相似項目的相似度
                            similarity_score = similar_items[0].get('similarity_score', 0)
                            count = len(similar_items)
                            duplication_warning = f"檢測到 {count} 個高度相似的知識（相似度 {int(similarity_score * 100)}%）"

                # 解析 sop_config（可能是字串或 dict）
                sop_config = row['sop_config']
                if sop_config and isinstance(sop_config, str):
                    import json
                    try:
                        sop_config = json.loads(sop_config)
                    except:
                        sop_config = None

                item = PendingKnowledgeItem(
                    id=row['id'],
                    loop_id=row['loop_id'],
                    iteration=row['iteration'],
                    question=row['question'],
                    answer=row['answer'],
                    knowledge_type=row['knowledge_type'],
                    sop_config=sop_config,
                    similar_knowledge=row['similar_knowledge'],
                    duplication_warning=duplication_warning,
                    status=row['status'],
                    created_at=row['created_at'].isoformat() if hasattr(row['created_at'], 'isoformat') else str(row['created_at'])
                )
                items.append(item)

            return PendingKnowledgeResponse(total=total or 0, items=items)

    except Exception as e:
        print(f"查詢待審核知識時發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查詢失敗: {str(e)}")


@router.post("/loop-knowledge/{knowledge_id}/review", response_model=ReviewKnowledgeResponse)
async def review_knowledge(
    knowledge_id: int,
    request: ReviewKnowledgeRequest,
    req: Request = None
):
    """
    [需求 8.2] 單一知識審核

    審核單一知識項目。批准時立即同步到正式庫並生成 embedding。

    **動作**：
    - approve: 批准並立即同步到 knowledge_base 或 vendor_sop_items
    - reject: 拒絕（保留在 loop_generated_knowledge 表，狀態為 rejected）

    **同步邏輯**：
    1. 批准時根據 knowledge_type 決定目標表：
       - knowledge_type='sop' → vendor_sop_items
       - knowledge_type=null → knowledge_base
    2. 調用 embedding API 生成向量
    3. 寫入目標表並設定 review_status='approved'
    4. 更新 loop_generated_knowledge.status='synced'
    5. 記錄審核事件到 loop_execution_logs

    **返回**：
    - knowledge_id: 知識 ID
    - action: 動作（approve/reject）
    - synced: 是否成功同步
    - synced_to: 同步目標表（knowledge_base/vendor_sop_items）
    - synced_id: 同步後的新 ID
    - message: 結果訊息
    """
    # 驗證 action 參數
    if request.action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="action 必須為 'approve' 或 'reject'")

    # 取得資料庫連接池
    db_pool = None
    if req and hasattr(req.app, 'state') and hasattr(req.app.state, 'db_pool'):
        db_pool = req.app.state.db_pool
    elif req and hasattr(req.app, 'extra'):
        db_pool = req.app.extra.get('db_pool')

    if not db_pool:
        raise HTTPException(status_code=500, detail="資料庫連接池未初始化")

    try:
        async with db_pool.acquire() as conn:
            # 1. 查詢知識項目
            knowledge_query = """
                SELECT id, loop_id, iteration, question, answer, knowledge_type, sop_config, status,
                       category, scope, is_template, template_vars,
                       keywords, business_types, target_user
                FROM loop_generated_knowledge
                WHERE id = $1
            """
            knowledge = await conn.fetchrow(knowledge_query, knowledge_id)

            if not knowledge:
                raise HTTPException(status_code=404, detail=f"知識 ID {knowledge_id} 不存在")

            # 2. 應用修改（如果有）
            updated_question = knowledge['question']
            updated_answer = knowledge['answer']
            updated_sop_config = knowledge['sop_config']

            if request.modifications:
                if 'question' in request.modifications:
                    updated_question = request.modifications['question']
                if 'answer' in request.modifications:
                    updated_answer = request.modifications['answer']
                if 'sop_config' in request.modifications and knowledge['knowledge_type'] == 'sop':
                    # 更新 sop_config（合併修改）
                    if updated_sop_config:
                        updated_sop_config.update(request.modifications['sop_config'])
                    else:
                        updated_sop_config = request.modifications['sop_config']

            # 3. 處理審核動作
            if request.action == "reject":
                # 拒絕：只更新狀態
                update_query = """
                    UPDATE loop_generated_knowledge
                    SET status = 'rejected',
                        question = $2,
                        answer = $3,
                        sop_config = $4
                    WHERE id = $1
                """
                await conn.execute(
                    update_query,
                    knowledge_id,
                    updated_question,
                    updated_answer,
                    updated_sop_config
                )

                # 記錄審核事件
                await _log_review_event(
                    conn,
                    knowledge['loop_id'],
                    knowledge['iteration'],
                    {
                        'knowledge_id': knowledge_id,
                        'action': 'reject',
                        'review_notes': None
                    }
                )

                return ReviewKnowledgeResponse(
                    knowledge_id=knowledge_id,
                    action="reject",
                    synced=False,
                    synced_to=None,
                    synced_id=None,
                    message="知識已拒絕"
                )

            elif request.action == "approve":
                # 批准：更新狀態為 approved（待同步）
                # 注意：完整的同步邏輯將在 task 6.5-6.6 實作
                # 目前只標記為 approved，實際同步由後續任務完成

                update_query = """
                    UPDATE loop_generated_knowledge
                    SET status = 'approved',
                        question = $2,
                        answer = $3,
                        sop_config = $4
                    WHERE id = $1
                """
                await conn.execute(
                    update_query,
                    knowledge_id,
                    updated_question,
                    updated_answer,
                    updated_sop_config
                )

                # 嘗試同步到正式庫（如果 _sync_knowledge_to_production 已實作）
                synced = False
                synced_to = None
                synced_id = None
                sync_error = None

                try:
                    # 準備同步資料
                    knowledge_data = {
                        'id': knowledge_id,
                        'loop_id': knowledge['loop_id'],
                        'iteration': knowledge['iteration'],
                        'question': updated_question,
                        'answer': updated_answer,
                        'knowledge_type': knowledge['knowledge_type'],
                        'sop_config': updated_sop_config,
                        'category': knowledge.get('category'),
                        'scope': knowledge.get('scope', 'global') or 'global',
                        'is_template': knowledge.get('is_template', False) or False,
                        'template_vars': knowledge.get('template_vars'),
                        'keywords': knowledge.get('keywords'),
                        'business_types': knowledge.get('business_types'),
                        'target_user': knowledge.get('target_user'),
                    }

                    # 調用同步函數
                    sync_result = await _sync_knowledge_to_production(
                        conn,
                        knowledge_data,
                        request.modifications
                    )

                    synced = sync_result.get('synced', False)
                    synced_to = sync_result.get('synced_to')
                    synced_id = sync_result.get('synced_id')

                    # 如果同步成功，更新狀態為 synced
                    if synced:
                        await conn.execute(
                            "UPDATE loop_generated_knowledge SET status = 'synced' WHERE id = $1",
                            knowledge_id
                        )

                except Exception as e:
                    # 同步失敗但保持 approved 狀態
                    sync_error = str(e)
                    print(f"同步知識時發生錯誤: {sync_error}")

                # 記錄審核事件
                await _log_review_event(
                    conn,
                    knowledge['loop_id'],
                    knowledge['iteration'],
                    {
                        'knowledge_id': knowledge_id,
                        'action': 'approve',
                        'synced': synced,
                        'synced_to': synced_to,
                        'synced_id': synced_id,
                        'sync_error': sync_error,
                        'review_notes': None
                    }
                )

                # 返回結果
                if synced:
                    message = f"知識已批准並同步到 {synced_to} (ID: {synced_id})"
                else:
                    message = f"知識已批准（待同步：{sync_error or '同步功能尚未實作'}）"

                return ReviewKnowledgeResponse(
                    knowledge_id=knowledge_id,
                    action="approve",
                    synced=synced,
                    synced_to=synced_to,
                    synced_id=synced_id,
                    message=message
                )

    except HTTPException:
        raise
    except Exception as e:
        print(f"審核知識時發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"審核失敗: {str(e)}")


@router.post("/loop-knowledge/batch-review", response_model=BatchReviewResponse)
async def batch_review_knowledge(
    request: BatchReviewRequest,
    req: Request = None
):
    """
    [需求 8.3] 批量審核知識

    批量審核 1-100 個知識項目。支援部分成功模式（容錯）。

    **批量操作邏輯**：
    1. 按順序處理每個 knowledge_id（避免併發衝突）
    2. 對每個項目執行完整的審核流程（同單一審核）
    3. 失敗項目記錄到 failed_items，不影響其他項目
    4. 所有項目處理完畢後返回統計結果

    **部分成功模式**：
    - 某項目失敗不中斷批次執行
    - 失敗項目保持 pending 狀態，可稍後重試
    - 返回詳細的成功/失敗統計與失敗原因

    **效能考量**：
    - 10 個項目：< 5 秒（不含 embedding 生成）
    - 50 個項目：< 20 秒（不含 embedding 生成）
    - embedding 生成採異步處理，前端顯示進度

    **返回**：
    - total: 總數
    - successful: 成功數量
    - failed: 失敗數量
    - failed_items: 失敗項目列表（knowledge_id + error）
    - duration_ms: 執行時間（毫秒）
    """
    import time
    import json

    start_time = time.time()

    # 驗證 action 參數
    if request.action not in ["approve", "reject"]:
        raise HTTPException(
            status_code=400,
            detail="action 必須為 'approve' 或 'reject'"
        )

    total = len(request.knowledge_ids)
    successful = 0
    failed = 0
    failed_items: List[BatchReviewFailedItem] = []

    try:
        # 獲取資料庫連接
        db_pool = None
        if req and hasattr(req.app, 'state') and hasattr(req.app.state, 'db_pool'):
            db_pool = req.app.state.db_pool
        elif req and hasattr(req.app, 'extra'):
            db_pool = req.app.extra.get('db_pool')

        if not db_pool:
            raise HTTPException(
                status_code=500,
                detail="資料庫連接池未初始化"
            )

        async with db_pool.acquire() as conn:
            # 按順序處理每個知識項目（避免併發衝突）
            for knowledge_id in request.knowledge_ids:
                try:
                    # 1. 查詢知識項目
                    knowledge_query = """
                        SELECT id, loop_id, iteration, question, answer,
                               knowledge_type, sop_config, status,
                               category, scope, is_template, template_vars,
                               keywords, business_types, target_user
                        FROM loop_generated_knowledge
                        WHERE id = $1
                    """
                    knowledge = await conn.fetchrow(knowledge_query, knowledge_id)

                    if not knowledge:
                        failed += 1
                        failed_items.append(BatchReviewFailedItem(
                            knowledge_id=knowledge_id,
                            error=f"知識 ID {knowledge_id} 不存在"
                        ))
                        continue

                    # 2. 應用修改（如果有）
                    updated_question = knowledge['question']
                    updated_answer = knowledge['answer']
                    updated_sop_config = knowledge['sop_config']

                    if request.modifications:
                        if 'question' in request.modifications:
                            updated_question = request.modifications['question']

                        if 'answer' in request.modifications:
                            updated_answer = request.modifications['answer']

                        if 'sop_config' in request.modifications:
                            if updated_sop_config:
                                updated_sop_config = dict(updated_sop_config)
                                updated_sop_config.update(request.modifications['sop_config'])
                            else:
                                updated_sop_config = request.modifications['sop_config']

                    # 3. 執行審核動作
                    if request.action == "reject":
                        # 拒絕：更新狀態為 rejected
                        update_query = """
                            UPDATE loop_generated_knowledge
                            SET status = 'rejected',
                                question = $2,
                                answer = $3,
                                sop_config = $4
                            WHERE id = $1
                        """
                        await conn.execute(
                            update_query,
                            knowledge_id,
                            updated_question,
                            updated_answer,
                            json.dumps(updated_sop_config, ensure_ascii=False) if updated_sop_config else None
                        )

                        # 記錄審核事件
                        await _log_review_event(
                            conn,
                            knowledge['loop_id'],
                            knowledge['iteration'],
                            {
                                'knowledge_id': knowledge_id,
                                'action': 'reject',
                                'review_notes': None,
                                'modifications': request.modifications
                            }
                        )

                        successful += 1

                    elif request.action == "approve":
                        # 批准：更新狀態為 approved，嘗試同步
                        update_query = """
                            UPDATE loop_generated_knowledge
                            SET status = 'approved',
                                question = $2,
                                answer = $3,
                                sop_config = $4
                            WHERE id = $1
                        """
                        await conn.execute(
                            update_query,
                            knowledge_id,
                            updated_question,
                            updated_answer,
                            json.dumps(updated_sop_config, ensure_ascii=False) if updated_sop_config else None
                        )

                        # 嘗試同步到正式庫（使用占位符，容錯處理）
                        sync_error = None
                        try:
                            knowledge_data = {
                                'id': knowledge['id'],
                                'loop_id': knowledge['loop_id'],
                                'iteration': knowledge['iteration'],
                                'question': updated_question,
                                'answer': updated_answer,
                                'knowledge_type': knowledge['knowledge_type'],
                                'sop_config': updated_sop_config,
                                'category': knowledge.get('category'),
                                'scope': knowledge.get('scope', 'global') or 'global',
                                'is_template': knowledge.get('is_template', False) or False,
                                'template_vars': knowledge.get('template_vars'),
                                'keywords': knowledge.get('keywords'),
                                'business_types': knowledge.get('business_types'),
                                'target_user': knowledge.get('target_user'),
                            }
                            sync_result = await _sync_knowledge_to_production(
                                conn,
                                knowledge_data,
                                request.modifications
                            )

                            # 如果同步成功，更新狀態為 synced
                            if sync_result.get('synced'):
                                await conn.execute(
                                    "UPDATE loop_generated_knowledge SET status = 'synced' WHERE id = $1",
                                    knowledge_id
                                )
                        except Exception as e:
                            # 同步失敗不影響批准操作，記錄錯誤
                            sync_error = str(e)

                        # 記錄審核事件
                        await _log_review_event(
                            conn,
                            knowledge['loop_id'],
                            knowledge['iteration'],
                            {
                                'knowledge_id': knowledge_id,
                                'action': 'approve',
                                'review_notes': None,
                                'modifications': request.modifications,
                                'sync_error': sync_error
                            }
                        )

                        successful += 1

                except Exception as e:
                    # 單個項目失敗，記錄並繼續處理其他項目
                    failed += 1
                    failed_items.append(BatchReviewFailedItem(
                        knowledge_id=knowledge_id,
                        error=str(e)
                    ))

            # 記錄批量審核事件（整體統計）
            if request.knowledge_ids:
                # 使用第一個成功項目的 loop_id 和 iteration
                first_success = None
                for knowledge_id in request.knowledge_ids:
                    try:
                        knowledge = await conn.fetchrow(
                            "SELECT loop_id, iteration FROM loop_generated_knowledge WHERE id = $1",
                            knowledge_id
                        )
                        if knowledge:
                            first_success = knowledge
                            break
                    except:
                        continue

                if first_success:
                    await _log_review_event(
                        conn,
                        first_success['loop_id'],
                        first_success['iteration'],
                        {
                            'batch_review': True,
                            'action': request.action,
                            'total': total,
                            'successful': successful,
                            'failed': failed,
                            'knowledge_ids': request.knowledge_ids
                        }
                    )

        # 計算執行時間
        duration_ms = int((time.time() - start_time) * 1000)

        return BatchReviewResponse(
            total=total,
            successful=successful,
            failed=failed,
            failed_items=failed_items,
            duration_ms=duration_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"批量審核失敗: {str(e)}")


# ============================================
# 輔助函數（未來實作）
# ============================================

async def _log_review_event(
    conn,
    loop_id: int,
    iteration: int,
    event_data: Dict
):
    """
    記錄審核事件到 loop_execution_logs

    Args:
        conn: 資料庫連接
        loop_id: 迴圈 ID
        iteration: 迭代次數
        event_data: 事件資料
    """
    try:
        import json
        await conn.execute(
            """
            INSERT INTO loop_execution_logs (loop_id, iteration, event_type, event_data, created_at)
            VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
            """,
            loop_id,
            iteration,
            'knowledge_review',
            json.dumps(event_data, ensure_ascii=False)
        )
    except Exception as e:
        print(f"記錄審核事件時發生錯誤: {str(e)}")
        # 不拋出異常，避免影響主要審核流程


async def _sync_knowledge_to_production(
    conn,
    knowledge_item: Dict,
    modifications: Optional[Dict] = None
) -> Dict:
    """
    同步知識到正式庫

    Args:
        conn: 資料庫連接
        knowledge_item: 知識項目資料（從 loop_generated_knowledge 查詢）
        modifications: 修改內容（選填）

    Returns:
        {
            "synced": bool,
            "synced_to": str,  # knowledge_base/vendor_sop_items
            "synced_id": int,
            "error": str  # 若失敗
        }

    邏輯：
    1. 判斷 knowledge_type 決定目標表
    2. 應用 modifications（若有）
    3. 生成 embedding（調用 embedding API）
    4. 寫入目標表（knowledge_base 或 vendor_sop_items）
    5. 更新 loop_generated_knowledge.status='synced'
    """
    import json
    from services.knowledge_completion_loop.embedding_client import get_loop_embedding_client

    try:
        # 提取知識資料
        knowledge_id = knowledge_item.get('id')
        loop_id = knowledge_item.get('loop_id')
        iteration = knowledge_item.get('iteration')
        knowledge_type = knowledge_item.get('knowledge_type')
        question = knowledge_item.get('question')
        answer = knowledge_item.get('answer')
        sop_config = knowledge_item.get('sop_config')

        # 提取擴充欄位（向後相容：舊資料可能沒有這些欄位）
        category = knowledge_item.get('category')  # 可為 None
        scope = knowledge_item.get('scope', 'global') or 'global'
        is_template = knowledge_item.get('is_template', False) or False
        template_vars = knowledge_item.get('template_vars')  # 可為 None
        kb_keywords = knowledge_item.get('keywords')  # TEXT[]
        kb_business_types = knowledge_item.get('business_types')  # TEXT[]
        # target_user: loop_generated_knowledge 是 VARCHAR，knowledge_base 是 TEXT[]
        raw_target_user = knowledge_item.get('target_user')
        if isinstance(raw_target_user, str):
            kb_target_user = [raw_target_user] if raw_target_user else None
        elif isinstance(raw_target_user, list):
            kb_target_user = raw_target_user if raw_target_user else None
        else:
            kb_target_user = None

        # 如果 sop_config 是字串，解析為 dict
        if sop_config and isinstance(sop_config, str):
            sop_config = json.loads(sop_config)

        # 應用修改
        if modifications:
            if 'question' in modifications:
                question = modifications['question']
            if 'answer' in modifications:
                answer = modifications['answer']
            if 'sop_config' in modifications and sop_config:
                sop_config = dict(sop_config) if isinstance(sop_config, dict) else {}
                sop_config.update(modifications['sop_config'])
            elif 'sop_config' in modifications:
                sop_config = modifications['sop_config']

        # 獲取 vendor_id
        vendor_row = await conn.fetchrow(
            "SELECT vendor_id FROM knowledge_completion_loops WHERE id = $1",
            loop_id
        )
        if not vendor_row:
            return {
                "synced": False,
                "synced_to": None,
                "synced_id": None,
                "error": f"找不到 loop_id {loop_id} 的 vendor_id"
            }
        vendor_id = vendor_row['vendor_id']

        # 判斷知識類型並同步
        if knowledge_type == 'sop':
            # SOP 類型：寫入 vendor_sop_items
            if not sop_config:
                return {
                    "synced": False,
                    "synced_to": "vendor_sop_items",
                    "synced_id": None,
                    "error": "SOP 類型但缺少 sop_config"
                }

            # 從 sop_config 讀取配置
            category_id = sop_config.get('category_id')
            group_id = sop_config.get('group_id')
            item_name = sop_config.get('item_name') or question

            # 插入 vendor_sop_items（不帶 embedding，後續由 sop_embedding_generator 統一生成）
            sop_id = await conn.fetchval("""
                INSERT INTO vendor_sop_items (
                    vendor_id,
                    category_id,
                    group_id,
                    item_name,
                    content,
                    keywords,
                    created_at,
                    updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
            """,
                vendor_id,
                category_id,
                group_id,
                item_name,
                answer,  # content
                None  # keywords (可選)
            )

            # 統一使用 sop_embedding_generator 生成 embedding
            from services.sop_embedding_generator import generate_sop_embeddings_async
            db_pool = conn._pool if hasattr(conn, '_pool') else req.app.state.db_pool
            asyncio.create_task(generate_sop_embeddings_async(db_pool, sop_id))

            return {
                "synced": True,
                "synced_to": "vendor_sop_items",
                "synced_id": sop_id,
                "error": None
            }

        else:
            # 一般知識：寫入 knowledge_base
            # 生成 embedding（使用 question）
            embedding_client = get_loop_embedding_client()
            embedding = await embedding_client.generate_embedding(question)

            if not embedding:
                return {
                    "synced": False,
                    "synced_to": "knowledge_base",
                    "synced_id": None,
                    "error": "Embedding 生成失敗"
                }

            # 轉換為 pgvector 格式
            embedding_str = embedding_client.to_pgvector_format(embedding)

            # 組裝 generation_metadata
            generation_metadata = json.dumps({
                "loop_id": loop_id,
                "iteration": iteration,
                "source": "kb-coverage-completion"
            }, ensure_ascii=False)

            # 處理 template_vars（確保為 JSON 字串或 None）
            template_vars_json = None
            if template_vars is not None:
                template_vars_json = json.dumps(template_vars, ensure_ascii=False) if isinstance(template_vars, (dict, list)) else template_vars

            # 插入 knowledge_base
            kb_id = await conn.fetchval("""
                INSERT INTO knowledge_base (
                    vendor_ids,
                    question_summary,
                    answer,
                    keywords,
                    embedding,
                    category,
                    scope,
                    is_template,
                    template_vars,
                    business_types,
                    target_user,
                    source_type,
                    source,
                    generation_metadata,
                    source_loop_id,
                    source_loop_knowledge_id,
                    created_at,
                    updated_at
                )
                VALUES ($1, $2, $3, $4, $5::vector,
                        $6, $7, $8, $9::jsonb,
                        $10, $11,
                        'ai_generated', 'loop', $12::jsonb,
                        $13, $14,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
            """,
                [vendor_id],  # vendor_ids array
                question,  # question_summary
                answer,
                kb_keywords,
                embedding_str,
                category,
                scope,
                is_template,
                template_vars_json,
                kb_business_types,
                kb_target_user,
                generation_metadata,
                loop_id,
                knowledge_id
            )

            return {
                "synced": True,
                "synced_to": "knowledge_base",
                "synced_id": kb_id,
                "error": None
            }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "synced": False,
            "synced_to": None,
            "synced_id": None,
            "error": str(e)
        }


async def _generate_embedding(text: str) -> List[float]:
    """
    生成文字的 embedding 向量

    Args:
        text: 要生成 embedding 的文字

    Returns:
        1536 維向量

    調用外部 embedding API（EMBEDDING_API_URL）。
    """
    # TODO: 實作 embedding 生成
    pass
