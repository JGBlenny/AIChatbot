"""
意圖管理 API 路由
提供意圖的 CRUD 操作
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
import asyncpg

router = APIRouter()


class IntentCreate(BaseModel):
    """新增意圖請求"""
    name: str = Field(..., description="意圖名稱")
    type: str = Field(..., description="意圖類型")
    description: str = Field("", description="意圖描述")
    keywords: List[str] = Field(default_factory=list, description="關鍵字列表")
    confidence_threshold: float = Field(0.80, ge=0.0, le=1.0, description="信心度閾值")
    api_required: bool = Field(False, description="是否需要 API")
    api_endpoint: Optional[str] = Field(None, description="API 端點")
    api_action: Optional[str] = Field(None, description="API 動作")
    created_by: str = Field("admin", description="建立人員")


class IntentUpdate(BaseModel):
    """更新意圖請求"""
    name: Optional[str] = Field(None, description="意圖名稱")
    type: Optional[str] = Field(None, description="意圖類型")
    description: Optional[str] = Field(None, description="意圖描述")
    keywords: Optional[List[str]] = Field(None, description="關鍵字列表")
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="信心度閾值")
    api_required: Optional[bool] = Field(None, description="是否需要 API")
    api_endpoint: Optional[str] = Field(None, description="API 端點")
    api_action: Optional[str] = Field(None, description="API 動作")
    updated_by: str = Field("admin", description="更新人員")
    reclassify_knowledge: bool = Field(False, description="是否重新分類知識庫")
    reclassify_mode: str = Field("none", description="重新分類模式: none/low_confidence/all")


class IntentToggle(BaseModel):
    """啟用/停用意圖請求"""
    is_enabled: bool = Field(..., description="是否啟用")


@router.get("/intents")
async def get_all_intents(
    req: Request,
    enabled_only: bool = False,
    intent_type: Optional[str] = None,
    order_by: str = 'name'
):
    """
    取得所有意圖

    Args:
        enabled_only: 只取得啟用的意圖
        intent_type: 過濾意圖類型（knowledge/data_query/action/hybrid）
        order_by: 排序方式（name/usage_count）
    """
    try:
        async with req.app.state.db_pool.acquire() as conn:
            # 構建查詢，包含 has_embedding 欄位
            query = "SELECT *, embedding IS NOT NULL as has_embedding FROM intents WHERE 1=1"
            params = []
            param_count = 0

            if enabled_only:
                query += " AND is_enabled = true"

            if intent_type:
                param_count += 1
                query += f" AND type = ${param_count}"
                params.append(intent_type)

            # 排序
            order_mapping = {
                'name': 'name',
                'usage_count': 'usage_count DESC, name'
            }
            query += f" ORDER BY {order_mapping.get(order_by, 'name')}"

            rows = await conn.fetch(query, *params)

            return {
                "intents": [dict(row) for row in rows],
                "total": len(rows)
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得意圖列表失敗: {str(e)}"
        )


@router.get("/intents/stats")
async def get_intent_stats(req: Request):
    """取得意圖統計資訊"""
    try:
        async with req.app.state.db_pool.acquire() as conn:
            # 總體統計
            total = await conn.fetchval("SELECT COUNT(*) FROM intents")
            enabled = await conn.fetchval(
                "SELECT COUNT(*) FROM intents WHERE is_enabled = true"
            )

            # 按類型統計
            by_type = await conn.fetch("""
                SELECT
                    type,
                    COUNT(*) as total,
                    SUM(CASE WHEN is_enabled THEN 1 ELSE 0 END) as enabled,
                    AVG(knowledge_count) as avg_knowledge
                FROM intents
                GROUP BY type
                ORDER BY type
            """)

            # 知識庫覆蓋率（前 10 個）
            coverage = await conn.fetch("""
                SELECT
                    id,
                    name,
                    type,
                    knowledge_count,
                    usage_count
                FROM intents
                WHERE is_enabled = true
                ORDER BY knowledge_count DESC, usage_count DESC
                LIMIT 10
            """)

            # 最常使用的意圖（前 10 個）
            top_used = await conn.fetch("""
                SELECT
                    id,
                    name,
                    type,
                    usage_count,
                    last_used_at
                FROM intents
                WHERE usage_count > 0
                ORDER BY usage_count DESC
                LIMIT 10
            """)

            return {
                "total_intents": total,
                "enabled_intents": enabled,
                "disabled_intents": total - enabled,
                "by_type": [dict(row) for row in by_type],
                "knowledge_coverage": [dict(row) for row in coverage],
                "top_used": [dict(row) for row in top_used]
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得統計資訊失敗: {str(e)}"
        )


@router.get("/intents/{intent_id}")
async def get_intent(intent_id: int, req: Request):
    """取得特定意圖"""
    try:
        async with req.app.state.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM intents WHERE id = $1",
                intent_id
            )

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到意圖 ID: {intent_id}"
                )

            return dict(row)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"取得意圖詳情失敗: {str(e)}"
        )


@router.post("/intents")
async def create_intent(request: IntentCreate, req: Request):
    """新增意圖"""
    try:
        async with req.app.state.db_pool.acquire() as conn:
            # 檢查名稱是否已存在
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM intents WHERE name = $1)",
                request.name
            )

            if exists:
                raise HTTPException(
                    status_code=400,
                    detail=f"意圖名稱 '{request.name}' 已存在"
                )

            # 插入新意圖
            intent_id = await conn.fetchval("""
                INSERT INTO intents (
                    name, type, description, keywords,
                    confidence_threshold, is_enabled,
                    api_required, api_endpoint, api_action,
                    created_by
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
            """,
                request.name,
                request.type,
                request.description,
                request.keywords,
                request.confidence_threshold,
                True,  # 預設啟用
                request.api_required,
                request.api_endpoint,
                request.api_action,
                request.created_by
            )

            # 重新載入意圖分類器
            intent_classifier = req.app.state.intent_classifier
            intent_classifier.reload_intents()

            return {
                "message": "意圖已建立",
                "intent_id": intent_id
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"建立意圖失敗: {str(e)}"
        )


@router.put("/intents/{intent_id}")
async def update_intent(
    intent_id: int,
    request: IntentUpdate,
    req: Request
):
    """更新意圖"""
    try:
        async with req.app.state.db_pool.acquire() as conn:
            # 檢查意圖是否存在
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM intents WHERE id = $1)",
                intent_id
            )

            if not exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到意圖 ID: {intent_id}"
                )

            # 構建更新語句
            updates = []
            params = []
            param_count = 0

            if request.name is not None:
                param_count += 1
                updates.append(f"name = ${param_count}")
                params.append(request.name)

            if request.type is not None:
                param_count += 1
                updates.append(f"type = ${param_count}")
                params.append(request.type)

            if request.description is not None:
                param_count += 1
                updates.append(f"description = ${param_count}")
                params.append(request.description)

            if request.keywords is not None:
                param_count += 1
                updates.append(f"keywords = ${param_count}")
                params.append(request.keywords)

            if request.confidence_threshold is not None:
                param_count += 1
                updates.append(f"confidence_threshold = ${param_count}")
                params.append(request.confidence_threshold)

            if request.api_required is not None:
                param_count += 1
                updates.append(f"api_required = ${param_count}")
                params.append(request.api_required)

            if request.api_endpoint is not None:
                param_count += 1
                updates.append(f"api_endpoint = ${param_count}")
                params.append(request.api_endpoint)

            if request.api_action is not None:
                param_count += 1
                updates.append(f"api_action = ${param_count}")
                params.append(request.api_action)

            if not updates:
                return {"message": "沒有要更新的欄位"}

            # 加入更新人員
            param_count += 1
            updates.append(f"updated_by = ${param_count}")
            params.append(request.updated_by)

            # 執行更新
            param_count += 1
            query = f"""
                UPDATE intents
                SET {', '.join(updates)}
                WHERE id = ${param_count}
            """
            params.append(intent_id)

            await conn.execute(query, *params)

            # 重新載入意圖分類器
            intent_classifier = req.app.state.intent_classifier
            intent_classifier.reload_intents()

            # 處理知識庫重新分類
            reclassify_result = None
            if request.reclassify_knowledge and request.reclassify_mode != "none":
                from services.knowledge_classifier import KnowledgeClassifier

                try:
                    knowledge_classifier = KnowledgeClassifier()

                    if request.reclassify_mode == "all":
                        # 重新分類此意圖的所有知識
                        result = knowledge_classifier.classify_batch(
                            filters={"intent_ids": [intent_id]},
                            batch_size=100,
                            dry_run=False
                        )
                        reclassify_result = {
                            "mode": "all",
                            "processed": result.get('total_processed', 0),
                            "success": result.get('success_count', 0)
                        }
                    elif request.reclassify_mode == "low_confidence":
                        # 只重新分類低信心度的知識
                        result = knowledge_classifier.classify_batch(
                            filters={
                                "intent_ids": [intent_id],
                                "max_confidence": 0.7
                            },
                            batch_size=100,
                            dry_run=False
                        )
                        reclassify_result = {
                            "mode": "low_confidence",
                            "processed": result.get('total_processed', 0),
                            "success": result.get('success_count', 0)
                        }
                except Exception as e:
                    reclassify_result = {
                        "error": f"重新分類失敗: {str(e)}"
                    }

            response = {
                "message": "意圖已更新",
                "intent_id": intent_id
            }

            if reclassify_result:
                response["reclassify_result"] = reclassify_result

            return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"更新意圖失敗: {str(e)}"
        )


@router.delete("/intents/{intent_id}")
async def delete_intent(intent_id: int, req: Request):
    """
    刪除意圖（軟刪除，設為 disabled）

    注意：這是軟刪除，實際上是將 is_enabled 設為 false
    """
    try:
        async with req.app.state.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE intents
                SET is_enabled = false
                WHERE id = $1
            """, intent_id)

            # 檢查是否有更新
            rows_affected = int(result.split()[-1])

            if rows_affected == 0:
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到意圖 ID: {intent_id}"
                )

            # 重新載入意圖分類器
            intent_classifier = req.app.state.intent_classifier
            intent_classifier.reload_intents()

            return {
                "message": "意圖已刪除（軟刪除）",
                "intent_id": intent_id
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"刪除意圖失敗: {str(e)}"
        )


@router.patch("/intents/{intent_id}/toggle")
async def toggle_intent(
    intent_id: int,
    request: IntentToggle,
    req: Request
):
    """啟用/停用意圖"""
    try:
        async with req.app.state.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE intents
                SET is_enabled = $1
                WHERE id = $2
            """, request.is_enabled, intent_id)

            # 檢查是否有更新
            rows_affected = int(result.split()[-1])

            if rows_affected == 0:
                raise HTTPException(
                    status_code=404,
                    detail=f"找不到意圖 ID: {intent_id}"
                )

            # 重新載入意圖分類器
            intent_classifier = req.app.state.intent_classifier
            intent_classifier.reload_intents()

            status = "啟用" if request.is_enabled else "停用"
            return {
                "message": f"意圖已{status}",
                "intent_id": intent_id,
                "is_enabled": request.is_enabled
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"切換意圖狀態失敗: {str(e)}"
        )


@router.post("/intents/reload")
async def reload_intents(req: Request):
    """
    重新載入意圖配置

    手動觸發意圖分類器重新從資料庫載入意圖
    """
    try:
        intent_classifier = req.app.state.intent_classifier
        success = intent_classifier.reload_intents()

        if success:
            return {
                "message": "意圖配置已重新載入",
                "total_intents": len(intent_classifier.intents),
                "last_reload": intent_classifier.last_reload.isoformat() if intent_classifier.last_reload else None
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="重新載入意圖失敗"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"重新載入意圖失敗: {str(e)}"
        )


@router.post("/intents/regenerate-embeddings")
async def regenerate_intent_embeddings(req: Request):
    """
    批量生成所有缺失的意圖 embedding

    查找所有 embedding IS NULL 的意圖，為每個意圖調用 Embedding API 生成向量
    並更新到資料庫
    """
    try:
        from services.embedding_utils import get_embedding_client

        # 獲取 embedding 客戶端
        embedding_client = get_embedding_client()

        async with req.app.state.db_pool.acquire() as conn:
            # 1. 查詢所有沒有 embedding 的意圖
            rows = await conn.fetch("""
                SELECT id, name, description
                FROM intents
                WHERE embedding IS NULL
                ORDER BY id
            """)

            total = len(rows)

            if total == 0:
                return {
                    "success": True,
                    "message": "所有意圖已有向量",
                    "total": 0,
                    "generated": 0
                }

            # 2. 逐筆生成 embedding
            success_count = 0
            failed_ids = []

            for row in rows:
                intent_id = row['id']
                intent_name = row['name']
                intent_description = row['description']

                # 生成用於 embedding 的文本（結合名稱和描述）
                text_for_embedding = intent_name
                if intent_description:
                    text_for_embedding += f". {intent_description}"

                try:
                    # 調用 Embedding API
                    embedding_vector = await embedding_client.get_embedding(text_for_embedding)

                    if embedding_vector:
                        # 轉換為 PostgreSQL 向量格式
                        vector_str = '[' + ','.join(map(str, embedding_vector)) + ']'

                        # 更新到資料庫
                        await conn.execute("""
                            UPDATE intents
                            SET embedding = $1::vector
                            WHERE id = $2
                        """, vector_str, intent_id)

                        success_count += 1
                    else:
                        failed_ids.append(intent_id)

                except Exception as e:
                    print(f"⚠️  生成 intent {intent_id} embedding 失敗: {str(e)}")
                    failed_ids.append(intent_id)

            # 3. 重新載入意圖分類器以使用新的 embeddings
            intent_classifier = req.app.state.intent_classifier
            intent_classifier.reload_intents()

            return {
                "success": True,
                "message": f"批量生成完成，成功 {success_count}/{total}",
                "total": total,
                "generated": success_count,
                "failed": len(failed_ids),
                "failed_ids": failed_ids if failed_ids else None
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"批量生成 embedding 失敗: {str(e)}"
        )
