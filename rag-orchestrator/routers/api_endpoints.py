"""
API Endpoints 管理路由
用於動態管理系統可用的 API endpoints
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json
from datetime import datetime

router = APIRouter()

# ===== Pydantic Models =====

class ApiEndpointCreate(BaseModel):
    endpoint_id: str = Field(..., description="API 識別碼，唯一", min_length=1, max_length=100)
    endpoint_name: str = Field(..., description="顯示名稱", min_length=1, max_length=200)
    endpoint_icon: Optional[str] = Field('🔌', description="Emoji 圖示")
    description: Optional[str] = Field(None, description="API 描述")
    available_in_knowledge: bool = Field(True, description="是否在知識庫中可用")
    available_in_form: bool = Field(True, description="是否在表單中可用")
    default_params: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="預設參數定義")
    is_active: bool = Field(True, description="是否啟用")
    display_order: int = Field(0, description="顯示順序")
    vendor_id: Optional[int] = Field(None, description="業者 ID，NULL 表示全局")
    related_kb_ids: Optional[List[int]] = Field(None, description="關聯的知識庫 ID 列表")

    # 新增：動態配置欄位
    implementation_type: str = Field('dynamic', description="實作類型：dynamic（動態）或 custom（自定義代碼）")
    api_url: Optional[str] = Field(None, description="API URL，支持變量 {session.xxx}, {form.xxx}")
    http_method: str = Field('GET', description="HTTP 方法：GET, POST, PUT, DELETE")
    request_headers: Optional[Dict[str, Any]] = Field(default_factory=dict, description="請求頭")
    request_body_template: Optional[Dict[str, Any]] = Field(None, description="請求體模板（POST/PUT）")
    request_timeout: int = Field(30, description="請求超時時間（秒）")
    param_mappings: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="參數映射配置")
    response_format_type: str = Field('template', description="響應格式類型：template, raw, custom")
    response_template: Optional[str] = Field(None, description="響應格式化模板")
    custom_handler_name: Optional[str] = Field(None, description="自定義處理器函數名（implementation_type=custom 時使用）")
    retry_times: int = Field(0, description="失敗重試次數")
    cache_ttl: int = Field(0, description="緩存時間（秒），0 表示不緩存")

class ApiEndpointUpdate(BaseModel):
    endpoint_name: Optional[str] = Field(None, description="顯示名稱")
    endpoint_icon: Optional[str] = Field(None, description="Emoji 圖示")
    description: Optional[str] = Field(None, description="API 描述")
    available_in_knowledge: Optional[bool] = Field(None, description="是否在知識庫中可用")
    available_in_form: Optional[bool] = Field(None, description="是否在表單中可用")
    default_params: Optional[List[Dict[str, Any]]] = Field(None, description="預設參數定義")
    is_active: Optional[bool] = Field(None, description="是否啟用")
    display_order: Optional[int] = Field(None, description="顯示順序")
    vendor_id: Optional[int] = Field(None, description="業者 ID")
    related_kb_ids: Optional[List[int]] = Field(None, description="關聯的知識庫 ID 列表")

    # 新增：動態配置欄位
    implementation_type: Optional[str] = Field(None, description="實作類型：dynamic（動態）或 custom（自定義代碼）")
    api_url: Optional[str] = Field(None, description="API URL，支持變量 {session.xxx}, {form.xxx}")
    http_method: Optional[str] = Field(None, description="HTTP 方法：GET, POST, PUT, DELETE")
    request_headers: Optional[Dict[str, Any]] = Field(None, description="請求頭")
    request_body_template: Optional[Dict[str, Any]] = Field(None, description="請求體模板（POST/PUT）")
    request_timeout: Optional[int] = Field(None, description="請求超時時間（秒）")
    param_mappings: Optional[List[Dict[str, Any]]] = Field(None, description="參數映射配置")
    response_format_type: Optional[str] = Field(None, description="響應格式類型：template, raw, custom")
    response_template: Optional[str] = Field(None, description="響應格式化模板")
    custom_handler_name: Optional[str] = Field(None, description="自定義處理器函數名（implementation_type=custom 時使用）")
    retry_times: Optional[int] = Field(None, description="失敗重試次數")
    cache_ttl: Optional[int] = Field(None, description="緩存時間（秒），0 表示不緩存")

class ApiEndpointResponse(BaseModel):
    id: int
    endpoint_id: str
    endpoint_name: str
    endpoint_icon: str
    description: Optional[str] = None
    available_in_knowledge: bool
    available_in_form: bool
    default_params: List[Dict[str, Any]]
    is_active: bool
    display_order: int
    vendor_id: Optional[int] = None
    related_kb_ids: Optional[List[int]] = None
    created_at: datetime
    updated_at: datetime

    # 新增：動態配置欄位
    implementation_type: str
    api_url: Optional[str] = None
    http_method: str
    request_headers: Dict[str, Any]
    request_body_template: Optional[Dict[str, Any]] = None
    request_timeout: int
    param_mappings: List[Dict[str, Any]]
    response_format_type: str
    response_template: Optional[str] = None
    custom_handler_name: Optional[str] = None
    retry_times: int
    cache_ttl: int

# ===== API Routes =====

@router.get("/api-endpoints", response_model=List[ApiEndpointResponse])
async def list_api_endpoints(
    request: Request,
    scope: Optional[str] = None,  # 'knowledge' or 'form' or None (all)
    vendor_id: Optional[int] = None,
    is_active: Optional[bool] = None
):
    """
    獲取 API endpoints 列表

    - scope: 'knowledge' 只返回知識庫可用的，'form' 只返回表單可用的
    - vendor_id: 篩選特定業者 (包含全局的 vendor_id=NULL)
    - is_active: 篩選啟用/停用狀態
    """
    db_pool = request.app.state.db_pool

    # 構建查詢條件
    conditions = []
    params = []
    param_count = 0

    if scope == 'knowledge':
        conditions.append("available_in_knowledge = TRUE")
    elif scope == 'form':
        conditions.append("available_in_form = TRUE")

    if vendor_id is not None:
        param_count += 1
        conditions.append(f"(vendor_id = ${param_count} OR vendor_id IS NULL)")
        params.append(vendor_id)

    if is_active is not None:
        param_count += 1
        conditions.append(f"is_active = ${param_count}")
        params.append(is_active)

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    query = f"""
        SELECT
            id, endpoint_id, endpoint_name, endpoint_icon, description,
            available_in_knowledge, available_in_form,
            default_params, is_active, display_order, vendor_id,
            related_kb_ids,
            created_at, updated_at,
            implementation_type, api_url, http_method, request_headers,
            request_body_template, request_timeout, param_mappings,
            response_format_type, response_template, custom_handler_name,
            retry_times, cache_ttl
        FROM api_endpoints
        WHERE {where_clause}
        ORDER BY display_order ASC, endpoint_name ASC
    """

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

        results = []
        for row in rows:
            row_dict = dict(row)
            # 解析 JSONB 欄位
            if isinstance(row_dict.get('default_params'), str):
                row_dict['default_params'] = json.loads(row_dict['default_params'])
            if isinstance(row_dict.get('request_headers'), str):
                row_dict['request_headers'] = json.loads(row_dict['request_headers'])
            if isinstance(row_dict.get('request_body_template'), str):
                row_dict['request_body_template'] = json.loads(row_dict['request_body_template'])
            if isinstance(row_dict.get('param_mappings'), str):
                row_dict['param_mappings'] = json.loads(row_dict['param_mappings'])
            results.append(ApiEndpointResponse(**row_dict))

        return results

@router.get("/api-endpoints/{endpoint_id}", response_model=ApiEndpointResponse)
async def get_api_endpoint(request: Request, endpoint_id: str):
    """獲取單個 API endpoint 詳情"""
    db_pool = request.app.state.db_pool

    query = """
        SELECT
            id, endpoint_id, endpoint_name, endpoint_icon, description,
            available_in_knowledge, available_in_form,
            default_params, is_active, display_order, vendor_id,
            related_kb_ids,
            created_at, updated_at,
            implementation_type, api_url, http_method, request_headers,
            request_body_template, request_timeout, param_mappings,
            response_format_type, response_template, custom_handler_name,
            retry_times, cache_ttl
        FROM api_endpoints
        WHERE endpoint_id = $1
    """

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(query, endpoint_id)

        if not row:
            raise HTTPException(status_code=404, detail=f"API endpoint '{endpoint_id}' 不存在")

        row_dict = dict(row)
        if isinstance(row_dict.get('default_params'), str):
            row_dict['default_params'] = json.loads(row_dict['default_params'])
        if isinstance(row_dict.get('request_headers'), str):
            row_dict['request_headers'] = json.loads(row_dict['request_headers'])
        if isinstance(row_dict.get('request_body_template'), str):
            row_dict['request_body_template'] = json.loads(row_dict['request_body_template'])
        if isinstance(row_dict.get('param_mappings'), str):
            row_dict['param_mappings'] = json.loads(row_dict['param_mappings'])

        return ApiEndpointResponse(**row_dict)


@router.get("/api-endpoints/{endpoint_id}/related-forms")
async def get_api_endpoint_related_forms(request: Request, endpoint_id: str):
    """
    獲取 API endpoint 關聯的所有 Lookup 表單

    返回使用此 endpoint 的所有表單列表,包含:
    - form_id: 表單 ID
    - form_name: 表單名稱
    - category: Lookup 類別
    - kb_id: 關聯的知識庫 ID
    - kb_question: 知識庫問題摘要
    """
    db_pool = request.app.state.db_pool

    async with db_pool.acquire() as conn:
        # 檢查 endpoint 是否存在
        endpoint_check = await conn.fetchrow(
            "SELECT endpoint_id, endpoint_name FROM api_endpoints WHERE endpoint_id = $1",
            endpoint_id
        )

        if not endpoint_check:
            raise HTTPException(status_code=404, detail=f"API endpoint '{endpoint_id}' 不存在")

        # 查詢使用此端點的所有表單及其關聯知識庫
        query = """
            SELECT
                fs.form_id,
                fs.form_name,
                fs.api_config->'static_params'->>'category' as category,
                kb.id as kb_id,
                kb.question_summary as kb_question
            FROM form_schemas fs
            LEFT JOIN knowledge_base kb ON kb.form_id = fs.form_id
            WHERE fs.api_config->>'endpoint' = $1
            ORDER BY fs.form_id, kb.id
        """

        rows = await conn.fetch(query, endpoint_id)

        # 組合結果
        result = {
            "endpoint_id": endpoint_check['endpoint_id'],
            "endpoint_name": endpoint_check['endpoint_name'],
            "related_forms_count": len(set(row['form_id'] for row in rows)),
            "related_forms": [
                {
                    "form_id": row['form_id'],
                    "form_name": row['form_name'],
                    "category": row['category'],
                    "kb_id": row['kb_id'],
                    "kb_question": row['kb_question']
                }
                for row in rows
            ]
        }

        return result


@router.post("/api-endpoints", response_model=ApiEndpointResponse)
async def create_api_endpoint(request: Request, data: ApiEndpointCreate):
    """創建新的 API endpoint"""
    db_pool = request.app.state.db_pool

    # 檢查 endpoint_id 是否已存在
    check_query = "SELECT id FROM api_endpoints WHERE endpoint_id = $1"

    async with db_pool.acquire() as conn:
        existing = await conn.fetchrow(check_query, data.endpoint_id)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"API endpoint ID '{data.endpoint_id}' 已存在"
            )

        # 插入新記錄
        insert_query = """
            INSERT INTO api_endpoints (
                endpoint_id, endpoint_name, endpoint_icon, description,
                available_in_knowledge, available_in_form,
                default_params, is_active, display_order, vendor_id,
                related_kb_ids,
                implementation_type, api_url, http_method, request_headers,
                request_body_template, request_timeout, param_mappings,
                response_format_type, response_template, custom_handler_name,
                retry_times, cache_ttl
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23)
            RETURNING
                id, endpoint_id, endpoint_name, endpoint_icon, description,
                available_in_knowledge, available_in_form,
                default_params, is_active, display_order, vendor_id,
                related_kb_ids,
                created_at, updated_at,
                implementation_type, api_url, http_method, request_headers,
                request_body_template, request_timeout, param_mappings,
                response_format_type, response_template, custom_handler_name,
                retry_times, cache_ttl
        """

        row = await conn.fetchrow(
            insert_query,
            data.endpoint_id,
            data.endpoint_name,
            data.endpoint_icon,
            data.description,
            data.available_in_knowledge,
            data.available_in_form,
            json.dumps(data.default_params),
            data.is_active,
            data.display_order,
            data.vendor_id,
            data.related_kb_ids,
            data.implementation_type,
            data.api_url,
            data.http_method,
            json.dumps(data.request_headers),
            json.dumps(data.request_body_template) if data.request_body_template else None,
            data.request_timeout,
            json.dumps(data.param_mappings),
            data.response_format_type,
            data.response_template,
            data.custom_handler_name,
            data.retry_times,
            data.cache_ttl
        )

        row_dict = dict(row)
        if isinstance(row_dict.get('default_params'), str):
            row_dict['default_params'] = json.loads(row_dict['default_params'])
        if isinstance(row_dict.get('request_headers'), str):
            row_dict['request_headers'] = json.loads(row_dict['request_headers'])
        if isinstance(row_dict.get('request_body_template'), str):
            row_dict['request_body_template'] = json.loads(row_dict['request_body_template'])
        if isinstance(row_dict.get('param_mappings'), str):
            row_dict['param_mappings'] = json.loads(row_dict['param_mappings'])

        return ApiEndpointResponse(**row_dict)

@router.put("/api-endpoints/{endpoint_id}", response_model=ApiEndpointResponse)
async def update_api_endpoint(request: Request, endpoint_id: str, data: ApiEndpointUpdate):
    """更新 API endpoint"""
    db_pool = request.app.state.db_pool

    # 構建更新語句
    updates = []
    params = []
    param_count = 0

    if data.endpoint_name is not None:
        param_count += 1
        updates.append(f"endpoint_name = ${param_count}")
        params.append(data.endpoint_name)

    if data.endpoint_icon is not None:
        param_count += 1
        updates.append(f"endpoint_icon = ${param_count}")
        params.append(data.endpoint_icon)

    if data.description is not None:
        param_count += 1
        updates.append(f"description = ${param_count}")
        params.append(data.description)

    if data.available_in_knowledge is not None:
        param_count += 1
        updates.append(f"available_in_knowledge = ${param_count}")
        params.append(data.available_in_knowledge)

    if data.available_in_form is not None:
        param_count += 1
        updates.append(f"available_in_form = ${param_count}")
        params.append(data.available_in_form)

    if data.default_params is not None:
        param_count += 1
        updates.append(f"default_params = ${param_count}")
        params.append(json.dumps(data.default_params))

    if data.is_active is not None:
        param_count += 1
        updates.append(f"is_active = ${param_count}")
        params.append(data.is_active)

    if data.display_order is not None:
        param_count += 1
        updates.append(f"display_order = ${param_count}")
        params.append(data.display_order)

    if data.vendor_id is not None:
        param_count += 1
        updates.append(f"vendor_id = ${param_count}")
        params.append(data.vendor_id)

    if data.related_kb_ids is not None:
        param_count += 1
        updates.append(f"related_kb_ids = ${param_count}")
        params.append(data.related_kb_ids)

    # 新增：動態配置欄位
    if data.implementation_type is not None:
        param_count += 1
        updates.append(f"implementation_type = ${param_count}")
        params.append(data.implementation_type)

    if data.api_url is not None:
        param_count += 1
        updates.append(f"api_url = ${param_count}")
        params.append(data.api_url)

    if data.http_method is not None:
        param_count += 1
        updates.append(f"http_method = ${param_count}")
        params.append(data.http_method)

    if data.request_headers is not None:
        param_count += 1
        updates.append(f"request_headers = ${param_count}")
        params.append(json.dumps(data.request_headers))

    if data.request_body_template is not None:
        param_count += 1
        updates.append(f"request_body_template = ${param_count}")
        params.append(json.dumps(data.request_body_template))

    if data.request_timeout is not None:
        param_count += 1
        updates.append(f"request_timeout = ${param_count}")
        params.append(data.request_timeout)

    if data.param_mappings is not None:
        param_count += 1
        updates.append(f"param_mappings = ${param_count}")
        params.append(json.dumps(data.param_mappings))

    if data.response_format_type is not None:
        param_count += 1
        updates.append(f"response_format_type = ${param_count}")
        params.append(data.response_format_type)

    if data.response_template is not None:
        param_count += 1
        updates.append(f"response_template = ${param_count}")
        params.append(data.response_template)

    if data.custom_handler_name is not None:
        param_count += 1
        updates.append(f"custom_handler_name = ${param_count}")
        params.append(data.custom_handler_name)

    if data.retry_times is not None:
        param_count += 1
        updates.append(f"retry_times = ${param_count}")
        params.append(data.retry_times)

    if data.cache_ttl is not None:
        param_count += 1
        updates.append(f"cache_ttl = ${param_count}")
        params.append(data.cache_ttl)

    if not updates:
        raise HTTPException(status_code=400, detail="沒有提供任何更新欄位")

    param_count += 1
    params.append(endpoint_id)

    update_query = f"""
        UPDATE api_endpoints
        SET {', '.join(updates)}
        WHERE endpoint_id = ${param_count}
        RETURNING
            id, endpoint_id, endpoint_name, endpoint_icon, description,
            available_in_knowledge, available_in_form,
            default_params, is_active, display_order, vendor_id,
            related_kb_ids,
            created_at, updated_at,
            implementation_type, api_url, http_method, request_headers,
            request_body_template, request_timeout, param_mappings,
            response_format_type, response_template, custom_handler_name,
            retry_times, cache_ttl
    """

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(update_query, *params)

        if not row:
            raise HTTPException(status_code=404, detail=f"API endpoint '{endpoint_id}' 不存在")

        row_dict = dict(row)
        if isinstance(row_dict.get('default_params'), str):
            row_dict['default_params'] = json.loads(row_dict['default_params'])
        if isinstance(row_dict.get('request_headers'), str):
            row_dict['request_headers'] = json.loads(row_dict['request_headers'])
        if isinstance(row_dict.get('request_body_template'), str):
            row_dict['request_body_template'] = json.loads(row_dict['request_body_template'])
        if isinstance(row_dict.get('param_mappings'), str):
            row_dict['param_mappings'] = json.loads(row_dict['param_mappings'])

        return ApiEndpointResponse(**row_dict)

@router.delete("/api-endpoints/{endpoint_id}")
async def delete_api_endpoint(request: Request, endpoint_id: str):
    """刪除 API endpoint"""
    db_pool = request.app.state.db_pool

    # 檢查是否有知識庫或表單正在使用
    check_knowledge_query = """
        SELECT COUNT(*) as count
        FROM knowledge
        WHERE api_config->>'endpoint' = $1
    """

    check_form_query = """
        SELECT COUNT(*) as count
        FROM form_schemas
        WHERE api_config->>'endpoint' = $1
    """

    async with db_pool.acquire() as conn:
        knowledge_count = await conn.fetchval(check_knowledge_query, endpoint_id)
        form_count = await conn.fetchval(check_form_query, endpoint_id)

        if knowledge_count > 0 or form_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"無法刪除：有 {knowledge_count} 筆知識和 {form_count} 筆表單正在使用此 API endpoint"
            )

        # 刪除記錄
        delete_query = "DELETE FROM api_endpoints WHERE endpoint_id = $1 RETURNING id"
        deleted = await conn.fetchrow(delete_query, endpoint_id)

        if not deleted:
            raise HTTPException(status_code=404, detail=f"API endpoint '{endpoint_id}' 不存在")

        return {"message": f"API endpoint '{endpoint_id}' 已成功刪除", "id": deleted['id']}
