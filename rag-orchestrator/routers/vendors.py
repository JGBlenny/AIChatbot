"""
Vendors API Router
業者管理 API - 管理包租代管業者及其配置參數
"""
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, date
import os
import psycopg2
import psycopg2.extras
import asyncio
import httpx
from services.sop_utils import parse_sop_excel, identify_cashflow_sensitive_items
from services.cache_service import CacheService


router = APIRouter(prefix="/api/v1/vendors", tags=["vendors"])


def get_db_connection():
    """建立資料庫連接"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'postgres'),
        port=int(os.getenv('DB_PORT', 5432)),
        user=os.getenv('DB_USER', 'aichatbot'),
        password=os.getenv('DB_PASSWORD', 'aichatbot_password'),
        database=os.getenv('DB_NAME', 'aichatbot_admin')
    )


# ========== Schemas ==========

class VendorCreate(BaseModel):
    """建立業者請求"""
    code: str = Field(..., description="業者代碼", min_length=1, max_length=50)
    name: str = Field(..., description="業者名稱", min_length=1, max_length=200)
    short_name: Optional[str] = Field(None, description="簡稱", max_length=100)
    contact_phone: Optional[str] = Field(None, description="聯絡電話", max_length=50)
    contact_email: Optional[str] = Field(None, description="聯絡郵箱", max_length=100)
    address: Optional[str] = Field(None, description="公司地址")
    subscription_plan: str = Field("basic", description="訂閱方案")
    business_types: List[str] = Field(
        default_factory=lambda: ["property_management"],
        description="業態類型陣列（可多選）：system_provider(系統商)、full_service(包租型)、property_management(代管型)"
    )
    created_by: str = Field("admin", description="建立者")


class VendorUpdate(BaseModel):
    """更新業者請求"""
    name: Optional[str] = Field(None, description="業者名稱", max_length=200)
    short_name: Optional[str] = Field(None, description="簡稱", max_length=100)
    contact_phone: Optional[str] = Field(None, description="聯絡電話", max_length=50)
    contact_email: Optional[str] = Field(None, description="聯絡郵箱", max_length=100)
    address: Optional[str] = Field(None, description="公司地址")
    subscription_plan: Optional[str] = Field(None, description="訂閱方案")
    business_types: Optional[List[str]] = Field(
        None,
        description="業態類型陣列（可多選）：system_provider(系統商)、full_service(包租型)、property_management(代管型)"
    )
    is_active: Optional[bool] = Field(None, description="是否啟用")
    updated_by: str = Field("admin", description="更新者")


class VendorResponse(BaseModel):
    """業者回應"""
    id: int
    code: str
    name: str
    short_name: Optional[str]
    contact_phone: Optional[str]
    contact_email: Optional[str]
    address: Optional[str]
    subscription_plan: str
    business_types: List[str]
    subscription_status: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]


class VendorConfigItem(BaseModel):
    """業者配置項目"""
    category: str = Field(..., description="分類")
    param_key: str = Field(..., description="參數鍵")
    param_value: str = Field(..., description="參數值")
    data_type: str = Field("string", description="資料型別")
    display_name: Optional[str] = Field(None, description="顯示名稱")
    description: Optional[str] = Field(None, description="參數說明")
    unit: Optional[str] = Field(None, description="單位")


class VendorConfigUpdate(BaseModel):
    """批次更新業者配置"""
    configs: List[VendorConfigItem] = Field(..., description="配置列表")


# ========== API Endpoints ==========

@router.get("", response_model=List[VendorResponse])
async def list_vendors(
    is_active: Optional[bool] = None,
    subscription_plan: Optional[str] = None
):
    """
    獲取業者列表

    可選過濾條件：
    - is_active: 是否啟用
    - subscription_plan: 訂閱方案
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 明確選擇欄位，避免包含已棄用的 business_type
        query = """
            SELECT
                id, code, name, short_name, contact_phone, contact_email,
                address, subscription_plan, business_types, subscription_status,
                is_active, created_at, updated_at
            FROM vendors
            WHERE 1=1
        """
        params = []

        if is_active is not None:
            query += " AND is_active = %s"
            params.append(is_active)

        if subscription_plan:
            query += " AND subscription_plan = %s"
            params.append(subscription_plan)

        query += " ORDER BY created_at DESC"

        cursor.execute(query, params)
        vendors = cursor.fetchall()
        cursor.close()

        return [VendorResponse(**dict(v)) for v in vendors]

    finally:
        conn.close()


@router.post("", response_model=VendorResponse, status_code=201)
async def create_vendor(vendor: VendorCreate):
    """建立新業者"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查代碼是否已存在
        cursor.execute("SELECT id FROM vendors WHERE code = %s", (vendor.code,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=400,
                detail=f"業者代碼已存在: {vendor.code}"
            )

        # 插入業者
        cursor.execute("""
            INSERT INTO vendors (
                code, name, short_name, contact_phone, contact_email,
                address, subscription_plan, business_types, subscription_status,
                subscription_start_date, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            vendor.code,
            vendor.name,
            vendor.short_name,
            vendor.contact_phone,
            vendor.contact_email,
            vendor.address,
            vendor.subscription_plan,
            vendor.business_types,
            'active',
            date.today(),
            vendor.created_by
        ))

        new_vendor = cursor.fetchone()
        conn.commit()
        cursor.close()

        return VendorResponse(**dict(new_vendor))

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"建立業者失敗: {str(e)}")
    finally:
        conn.close()


@router.get("/by-code/{vendor_code}", response_model=VendorResponse)
async def get_vendor_by_code(vendor_code: str):
    """根據業者代碼獲取業者詳情"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("SELECT * FROM vendors WHERE code = %s", (vendor_code,))
        vendor = cursor.fetchone()
        cursor.close()

        if not vendor:
            raise HTTPException(status_code=404, detail=f"找不到代碼為 {vendor_code} 的業者")

        return VendorResponse(**dict(vendor))

    finally:
        conn.close()


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(vendor_id: int):
    """獲取業者詳情"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("SELECT * FROM vendors WHERE id = %s", (vendor_id,))
        vendor = cursor.fetchone()
        cursor.close()

        if not vendor:
            raise HTTPException(status_code=404, detail="業者不存在")

        return VendorResponse(**dict(vendor))

    finally:
        conn.close()


@router.put("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(vendor_id: int, vendor: VendorUpdate):
    """更新業者資訊"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id FROM vendors WHERE id = %s", (vendor_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="業者不存在")

        # 構建更新語句
        update_fields = []
        params = []

        if vendor.name is not None:
            update_fields.append("name = %s")
            params.append(vendor.name)

        if vendor.short_name is not None:
            update_fields.append("short_name = %s")
            params.append(vendor.short_name)

        if vendor.contact_phone is not None:
            update_fields.append("contact_phone = %s")
            params.append(vendor.contact_phone)

        if vendor.contact_email is not None:
            update_fields.append("contact_email = %s")
            params.append(vendor.contact_email)

        if vendor.address is not None:
            update_fields.append("address = %s")
            params.append(vendor.address)

        if vendor.subscription_plan is not None:
            update_fields.append("subscription_plan = %s")
            params.append(vendor.subscription_plan)

        if vendor.business_types is not None:
            update_fields.append("business_types = %s")
            params.append(vendor.business_types)

        if vendor.is_active is not None:
            update_fields.append("is_active = %s")
            params.append(vendor.is_active)

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        update_fields.append("updated_by = %s")
        params.append(vendor.updated_by)

        params.append(vendor_id)

        query = f"""
            UPDATE vendors
            SET {', '.join(update_fields)}
            WHERE id = %s
            RETURNING *
        """

        cursor.execute(query, params)
        updated_vendor = cursor.fetchone()
        conn.commit()
        cursor.close()

        return VendorResponse(**dict(updated_vendor))

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"更新業者失敗: {str(e)}")
    finally:
        conn.close()


@router.delete("/{vendor_id}")
async def delete_vendor(vendor_id: int):
    """刪除業者（軟刪除）"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # 檢查業者是否存在
        cursor.execute("SELECT id FROM vendors WHERE id = %s", (vendor_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="業者不存在")

        # 軟刪除（設為不啟用）
        cursor.execute("""
            UPDATE vendors
            SET is_active = false,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (vendor_id,))

        conn.commit()
        cursor.close()

        return {"message": "業者已停用", "vendor_id": vendor_id}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"刪除業者失敗: {str(e)}")
    finally:
        conn.close()


# ========== 業者配置管理 ==========

@router.get("/{vendor_id}/configs")
async def get_vendor_configs(vendor_id: int, category: Optional[str] = None):
    """
    獲取業者配置參數（結合系統參數定義和業者設定值）

    可選過濾：
    - category: 參數分類（payment, contract, service, contact）

    返回格式：
    {
      "payment": [
        {
          "param_key": "payment_day",
          "param_value": "5",  // 業者設定的值或預設值
          "display_name": "繳費日",
          "data_type": "number",
          "unit": "日",
          "description": "...",
          "placeholder": "...",
          "is_required": true,
          "display_order": 1
        }
      ]
    }
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id FROM vendors WHERE id = %s", (vendor_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="業者不存在")

        # 獲取系統參數定義和業者設定值（LEFT JOIN）
        query = """
            SELECT
                spd.category,
                spd.param_key,
                COALESCE(vc.param_value, spd.default_value) as param_value,
                spd.display_name,
                spd.data_type,
                spd.unit,
                spd.description,
                spd.placeholder,
                spd.is_required,
                spd.display_order,
                CASE WHEN vc.id IS NOT NULL THEN true ELSE false END as has_custom_value
            FROM system_param_definitions spd
            LEFT JOIN vendor_configs vc ON (
                vc.vendor_id = %s AND
                vc.param_key = spd.param_key AND
                vc.is_active = true
            )
            WHERE spd.is_active = true
        """
        params = [vendor_id]

        if category:
            query += " AND spd.category = %s"
            params.append(category)

        query += " ORDER BY spd.category, spd.display_order, spd.param_key"

        cursor.execute(query, params)
        configs = cursor.fetchall()
        cursor.close()

        # 按分類組織
        result = {}
        for config in configs:
            cat = config['category']
            if cat not in result:
                result[cat] = []
            result[cat].append(dict(config))

        return result

    finally:
        conn.close()


@router.put("/{vendor_id}/configs")
async def update_vendor_configs(vendor_id: int, config_update: VendorConfigUpdate):
    """
    批次更新業者配置參數（只更新值，參數定義來自系統）

    規則：
    - 只允許更新 param_value
    - param_key 必須存在於 system_param_definitions
    - 不允許新增或刪除參數
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # 檢查業者是否存在
        cursor.execute("SELECT id FROM vendors WHERE id = %s", (vendor_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="業者不存在")

        # 批次更新配置（只儲存值）
        for config in config_update.configs:
            # 驗證 param_key 是否為有效的系統參數
            cursor.execute("""
                SELECT id, category FROM system_param_definitions
                WHERE param_key = %s AND is_active = true
            """, (config.param_key,))

            param_def = cursor.fetchone()
            if not param_def:
                raise HTTPException(
                    status_code=400,
                    detail=f"無效的參數: {config.param_key}（參數不存在於系統定義中）"
                )

            # 更新或插入業者設定值
            cursor.execute("""
                INSERT INTO vendor_configs (
                    vendor_id, category, param_key, param_value
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (vendor_id, category, param_key)
                DO UPDATE SET
                    param_value = EXCLUDED.param_value,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                vendor_id,
                param_def[1],  # category from system definition
                config.param_key,
                config.param_value
            ))

        conn.commit()
        cursor.close()

        # 清除快取
        from services.vendor_parameter_resolver import VendorParameterResolver
        resolver = VendorParameterResolver()
        resolver.clear_cache(vendor_id)

        return {
            "message": "配置已更新",
            "vendor_id": vendor_id,
            "updated_count": len(config_update.configs)
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"更新配置失敗: {str(e)}")
    finally:
        conn.close()


@router.get("/{vendor_id}/stats")
async def get_vendor_stats(vendor_id: int):
    """獲取業者統計資訊"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT * FROM vendors WHERE id = %s", (vendor_id,))
        vendor = cursor.fetchone()
        if not vendor:
            raise HTTPException(status_code=404, detail="業者不存在")

        # 統計配置參數數量
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM vendor_configs
            WHERE vendor_id = %s AND is_active = true
            GROUP BY category
        """, (vendor_id,))
        config_stats = cursor.fetchall()

        # 統計知識數量
        cursor.execute("""
            SELECT
                COUNT(*) as total_knowledge,
                COUNT(CASE WHEN scope = 'vendor' THEN 1 END) as vendor_knowledge,
                COUNT(CASE WHEN scope = 'customized' THEN 1 END) as customized_knowledge
            FROM knowledge_base
            WHERE vendor_id = %s
        """, (vendor_id,))
        knowledge_stats = cursor.fetchone()

        cursor.close()

        return {
            "vendor": dict(vendor),
            "config_counts": {row['category']: row['count'] for row in config_stats},
            "total_configs": sum(row['count'] for row in config_stats),
            "knowledge": dict(knowledge_stats) if knowledge_stats else {}
        }

    finally:
        conn.close()


# ========== SOP 管理 ==========

class SOPCategoryCreate(BaseModel):
    """建立 SOP 分類"""
    category_name: str = Field(..., description="分類名稱", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="分類說明")
    display_order: int = Field(0, description="顯示順序", ge=0)


class SOPItemCreate(BaseModel):
    """建立 SOP 項目"""
    category_id: int = Field(..., description="所屬分類ID")
    item_number: int = Field(..., description="項次編號", ge=1)
    item_name: str = Field(..., description="項目名稱", min_length=1, max_length=200)
    content: str = Field(..., description="項目內容")
    keywords: Optional[List[str]] = Field(None, description="檢索關鍵字（提升搜尋準確度）")
    template_id: Optional[int] = Field(None, description="來源範本ID（記錄從哪個範本複製而來）")
    intent_ids: Optional[List[int]] = Field(None, description="關聯意圖ID列表")
    priority: int = Field(50, description="優先級（0-100）", ge=0, le=100)

    # 🔄 流程配置欄位
    trigger_mode: Optional[str] = Field(None, description="觸發模式: manual, immediate (當 next_action 不是 none 時必填)")
    next_action: str = Field("none", description="後續動作: none, form_fill, api_call, form_then_api")
    trigger_keywords: Optional[List[str]] = Field(None, description="觸發關鍵詞（manual 模式使用）")
    immediate_prompt: Optional[str] = Field(None, description="確認提示詞（immediate 模式使用）")
    followup_prompt: Optional[str] = Field(None, description="後續提示詞")
    next_form_id: Optional[str] = Field(None, description="後續表單ID（form_fill, form_then_api 使用）")
    next_api_config: Optional[dict] = Field(None, description="後續API配置（api_call, form_then_api 使用）")


class SOPItemUpdate(BaseModel):
    """更新 SOP 項目"""
    item_name: str = Field(..., description="項目名稱")
    content: str = Field(..., description="項目內容")
    keywords: Optional[List[str]] = Field(None, description="檢索關鍵字（提升搜尋準確度）")
    # intent_ids: DEPRECATED - 已廢棄，SOP 現在使用 Group-based embedding 檢索，不再需要意圖關聯
    # priority: DEPRECATED - 已廢棄，現代檢索完全基於向量相似度，不使用優先級排序

    # 🔧 流程配置字段
    trigger_mode: Optional[str] = Field(default=None, description="觸發模式：manual, immediate (當 next_action 不是 none 時必填)")
    next_action: str = Field(default='none', description="後續動作：none, form_fill, api_call, form_then_api")
    trigger_keywords: Optional[List[str]] = Field(default=None, description="觸發關鍵詞（manual 模式使用）")
    immediate_prompt: Optional[str] = Field(default=None, description="確認提示詞（immediate 模式使用）")
    next_form_id: Optional[str] = Field(default=None, description="關聯的表單 ID")
    next_api_config: Optional[dict] = Field(default=None, description="API 配置")
    followup_prompt: Optional[str] = Field(default=None, description="後續提示詞")


@router.get("/{vendor_id}/sop/categories")
async def get_sop_categories(vendor_id: int):
    """
    獲取業者的 SOP 分類列表

    Returns:
        List[Dict]: SOP 分類列表，包含 id, category_name, description, display_order
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id FROM vendors WHERE id = %s", (vendor_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="業者不存在")

        # 獲取 SOP 分類
        cursor.execute("""
            SELECT id, category_name, description, display_order
            FROM vendor_sop_categories
            WHERE vendor_id = %s
            ORDER BY display_order
        """, (vendor_id,))

        categories = cursor.fetchall()
        cursor.close()

        return [dict(cat) for cat in categories]

    finally:
        conn.close()


@router.get("/{vendor_id}/sop/items")
async def get_sop_items(vendor_id: int, category_id: Optional[int] = None):
    """
    獲取業者的 SOP 項目列表

    Args:
        vendor_id: 業者ID
        category_id: 可選的分類ID過濾

    Returns:
        List[Dict]: SOP 項目列表，包含所有欄位及關聯的意圖名稱
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id FROM vendors WHERE id = %s", (vendor_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="業者不存在")

        # 獲取 SOP 項目（包含群組資訊、範本來源、多意圖支援、流程配置）
        query = """
            SELECT
                vsi.id,
                vsi.category_id,
                vsi.vendor_id,
                vsi.group_id,
                vsg.group_name,
                vsi.item_number,
                vsi.item_name,
                vsi.content,
                vsi.keywords,
                vsi.template_id,
                vsi.priority,
                pt.item_name as template_item_name,
                vsi.is_active,
                vsi.created_at,
                vsi.updated_at,
                -- 🔄 流程配置欄位
                vsi.trigger_mode,
                vsi.next_action,
                vsi.trigger_keywords,
                vsi.immediate_prompt,
                vsi.next_form_id,
                vsi.next_api_config,
                vsi.followup_prompt,
                COALESCE(
                    (SELECT ARRAY_AGG(vsii.intent_id ORDER BY vsii.intent_id)
                     FROM vendor_sop_item_intents vsii
                     WHERE vsii.sop_item_id = vsi.id),
                    ARRAY[]::INTEGER[]
                ) as intent_ids
            FROM vendor_sop_items vsi
            LEFT JOIN vendor_sop_groups vsg ON vsi.group_id = vsg.id
            LEFT JOIN platform_sop_templates pt ON vsi.template_id = pt.id
            WHERE vsi.vendor_id = %s AND vsi.is_active = TRUE
        """
        params = [vendor_id]

        if category_id:
            query += " AND vsi.category_id = %s"
            params.append(category_id)

        query += " ORDER BY vsi.category_id, vsi.item_number"

        cursor.execute(query, params)
        items = cursor.fetchall()
        cursor.close()

        return [dict(item) for item in items]

    finally:
        conn.close()


@router.put("/{vendor_id}/sop/items/{item_id}")
async def update_sop_item(vendor_id: int, item_id: int, item_update: SOPItemUpdate, request: Request):
    """
    更新 SOP 項目

    智能檢測邏輯：
    - 只在 item_name、content、group_id 變更時才重新生成 embeddings
    - 其他欄位變更不觸發重新生成

    Args:
        vendor_id: 業者ID
        item_id: SOP項目ID
        item_update: 更新資料
        request: Request 對象（用於訪問 db_pool）

    Returns:
        Dict: 更新後的 SOP 項目
    """
    # 🔒 嚴格限制：驗證 trigger_mode 和 next_action 組合
    # 當 next_action 是 'none' 時，trigger_mode 可以是 null
    if item_update.next_action == 'none':
        # next_action 為 'none' 時，trigger_mode 應該是 null
        if item_update.trigger_mode is not None:
            raise HTTPException(
                status_code=400,
                detail="❌ 當後續動作為 'none' 時，不需要設定觸發模式"
            )
    else:
        # next_action 不是 'none' 時，需要有效的 trigger_mode
        VALID_TRIGGER_MODES = ['manual', 'immediate']
        if item_update.trigger_mode not in VALID_TRIGGER_MODES:
            raise HTTPException(
                status_code=400,
                detail=f"❌ 當後續動作不是 'none' 時，必須選擇有效的觸發模式：{', '.join(VALID_TRIGGER_MODES)}"
            )

    # 🔒 驗證必填字段
    if item_update.trigger_mode == 'manual':
        if not item_update.trigger_keywords or len(item_update.trigger_keywords) == 0:
            raise HTTPException(status_code=400, detail="❌ manual 模式必須設定至少一個觸發關鍵詞")

    # immediate 模式的 immediate_prompt 可以為空（系統有預設值）

    if item_update.next_action in ['form_fill', 'form_then_api']:
        if not item_update.next_form_id:
            raise HTTPException(status_code=400, detail="❌ 此後續動作必須選擇表單")

    if item_update.next_action in ['api_call', 'form_then_api']:
        if not item_update.next_api_config:
            raise HTTPException(status_code=400, detail="❌ 此後續動作必須配置 API")

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id FROM vendors WHERE id = %s", (vendor_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="業者不存在")

        # 🔍 查詢當前值（用於智能檢測變更）
        cursor.execute("""
            SELECT item_name, content, group_id
            FROM vendor_sop_items
            WHERE id = %s AND vendor_id = %s
        """, (item_id, vendor_id))
        current = cursor.fetchone()
        if not current:
            raise HTTPException(status_code=404, detail="SOP 項目不存在或不屬於該業者")

        # 🧠 智能檢測：判斷是否需要重新生成 embeddings
        need_regenerate = (
            (item_update.item_name and item_update.item_name != current['item_name']) or
            (item_update.content and item_update.content != current['content']) or
            (hasattr(item_update, 'group_id') and item_update.group_id is not None and item_update.group_id != current['group_id'])
        )

        # 更新 SOP 項目基本資訊
        update_fields = []
        params = []

        update_fields.append("item_name = %s")
        params.append(item_update.item_name)

        update_fields.append("content = %s")
        params.append(item_update.content)

        # 更新檢索關鍵字
        if item_update.keywords is not None:
            update_fields.append("keywords = %s")
            params.append(item_update.keywords)

        # ⚠️ DEPRECATED: priority 欄位已廢棄，不再更新

        # 🔧 更新流程配置字段
        update_fields.append("trigger_mode = %s")
        params.append(item_update.trigger_mode)

        update_fields.append("next_action = %s")
        params.append(item_update.next_action)

        update_fields.append("trigger_keywords = %s")
        params.append(item_update.trigger_keywords if item_update.trigger_keywords else None)

        update_fields.append("immediate_prompt = %s")
        params.append(item_update.immediate_prompt)

        update_fields.append("next_form_id = %s")
        params.append(item_update.next_form_id)

        update_fields.append("next_api_config = %s")
        params.append(psycopg2.extras.Json(item_update.next_api_config) if item_update.next_api_config else None)

        update_fields.append("followup_prompt = %s")
        params.append(item_update.followup_prompt)

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([item_id, vendor_id])

        query = f"""
            UPDATE vendor_sop_items
            SET {', '.join(update_fields)}
            WHERE id = %s AND vendor_id = %s
            RETURNING *
        """

        cursor.execute(query, params)
        updated_item = cursor.fetchone()

        # ⚠️ DEPRECATED: 意圖關聯已廢棄，SOP 現在使用 Group-based embedding 檢索
        # 不再更新 vendor_sop_item_intents 表，現有資料保留但不再使用

        conn.commit()

        # 查詢更新後的完整資訊（包含 intent_ids）
        cursor.execute("""
            SELECT
                vsi.*,
                COALESCE(
                    (SELECT ARRAY_AGG(vsii.intent_id ORDER BY vsii.intent_id)
                     FROM vendor_sop_item_intents vsii
                     WHERE vsii.sop_item_id = vsi.id),
                    ARRAY[]::INTEGER[]
                ) as intent_ids
            FROM vendor_sop_items vsi
            WHERE vsi.id = %s
        """, (item_id,))

        final_item = cursor.fetchone()
        cursor.close()

        # 🚀 背景重新生成 embeddings（如果需要）
        if need_regenerate and hasattr(request.app.state, 'db_pool'):
            from services.sop_embedding_generator import generate_sop_embeddings_async
            asyncio.create_task(
                generate_sop_embeddings_async(
                    db_pool=request.app.state.db_pool,
                    sop_item_id=item_id
                )
            )
            print(f"🚀 [SOP Update] 已觸發背景 embedding 重新生成 (ID: {item_id})")

        # 🗑️ 清除該業者的所有緩存（確保更新後的內容立即生效）
        try:
            cache_service = CacheService()
            cleared_count = cache_service.invalidate_by_vendor_id(vendor_id)
            print(f"🗑️ [SOP Update] 已清除業者 {vendor_id} 的緩存 ({cleared_count} 條)")
        except Exception as e:
            # 緩存清除失敗不影響主流程
            print(f"⚠️ [SOP Update] 緩存清除失敗: {e}")

        return dict(final_item)

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"更新 SOP 項目失敗: {str(e)}")
    finally:
        conn.close()


@router.post("/{vendor_id}/sop/categories", status_code=201)
async def create_sop_category(vendor_id: int, category: SOPCategoryCreate):
    """
    建立新的 SOP 分類

    Args:
        vendor_id: 業者ID
        category: 分類資料

    Returns:
        Dict: 新建立的 SOP 分類
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id FROM vendors WHERE id = %s", (vendor_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="業者不存在")

        # 插入新分類
        cursor.execute("""
            INSERT INTO vendor_sop_categories (
                vendor_id, category_name, description, display_order
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id, vendor_id, category_name, description, display_order, created_at
        """, (
            vendor_id,
            category.category_name,
            category.description,
            category.display_order
        ))

        new_category = cursor.fetchone()
        conn.commit()
        cursor.close()

        return dict(new_category)

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"建立 SOP 分類失敗: {str(e)}")
    finally:
        conn.close()


@router.post("/{vendor_id}/sop/items", status_code=201)
async def create_sop_item(vendor_id: int, item: SOPItemCreate, request: Request):
    """
    建立新的 SOP 項目

    Args:
        vendor_id: 業者ID
        item: SOP 項目資料
        request: Request 對象（用於訪問 db_pool）

    Returns:
        Dict: 新建立的 SOP 項目
    """
    # 🔒 嚴格限制：驗證 trigger_mode 和 next_action 組合
    # 當 next_action 是 'none' 時，trigger_mode 可以是 null
    if item.next_action == 'none':
        # next_action 為 'none' 時，trigger_mode 應該是 null
        if item.trigger_mode is not None:
            raise HTTPException(
                status_code=400,
                detail="❌ 當後續動作為 'none' 時，不需要設定觸發模式"
            )
    else:
        # next_action 不是 'none' 時，需要有效的 trigger_mode
        VALID_TRIGGER_MODES = ['manual', 'immediate']
        if item.trigger_mode not in VALID_TRIGGER_MODES:
            raise HTTPException(
                status_code=400,
                detail=f"❌ 當後續動作不是 'none' 時，必須選擇有效的觸發模式：{', '.join(VALID_TRIGGER_MODES)}"
            )

    # 🔒 驗證必填字段
    if item.trigger_mode == 'manual':
        if not item.trigger_keywords or len(item.trigger_keywords) == 0:
            raise HTTPException(status_code=400, detail="❌ manual 模式必須設定至少一個觸發關鍵詞")

    if item.next_action in ['form_fill', 'form_then_api']:
        if not item.next_form_id:
            raise HTTPException(status_code=400, detail="❌ 此後續動作必須選擇表單")

    if item.next_action in ['api_call', 'form_then_api']:
        if not item.next_api_config:
            raise HTTPException(status_code=400, detail="❌ 此後續動作必須配置 API")

    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id FROM vendors WHERE id = %s", (vendor_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="業者不存在")

        # 檢查分類是否存在且屬於該業者
        cursor.execute("""
            SELECT id FROM vendor_sop_categories
            WHERE id = %s AND vendor_id = %s
        """, (item.category_id, vendor_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="分類不存在或不屬於該業者")

        # 檢查意圖是否存在（如果有指定）
        if item.intent_ids:
            for intent_id in item.intent_ids:
                cursor.execute("SELECT id FROM intents WHERE id = %s", (intent_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=400, detail=f"意圖 ID {intent_id} 不存在")

        # 檢查範本是否存在（如果有指定）
        if item.template_id:
            cursor.execute("SELECT id FROM platform_sop_templates WHERE id = %s AND is_active = TRUE", (item.template_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail=f"範本 ID {item.template_id} 不存在或已停用")

        # 插入新 SOP 項目（包含流程配置欄位）
        cursor.execute("""
            INSERT INTO vendor_sop_items (
                category_id, vendor_id, item_number, item_name, content,
                keywords, template_id, priority,
                trigger_mode, next_action, trigger_keywords, immediate_prompt,
                followup_prompt, next_form_id, next_api_config
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            item.category_id,
            vendor_id,
            item.item_number,
            item.item_name,
            item.content,
            item.keywords if item.keywords else [],
            item.template_id,
            item.priority,
            item.trigger_mode,
            item.next_action,
            item.trigger_keywords,
            item.immediate_prompt,
            item.followup_prompt,
            item.next_form_id,
            psycopg2.extras.Json(item.next_api_config) if item.next_api_config else None
        ))

        new_item = cursor.fetchone()
        new_item_id = new_item['id']

        # 插入意圖關聯
        if item.intent_ids:
            for intent_id in item.intent_ids:
                cursor.execute("""
                    INSERT INTO vendor_sop_item_intents (sop_item_id, intent_id)
                    VALUES (%s, %s)
                """, (new_item_id, intent_id))

        conn.commit()

        # 查詢完整的項目資訊（包含 intent_ids）
        cursor.execute("""
            SELECT
                vsi.*,
                COALESCE(
                    (SELECT ARRAY_AGG(vsii.intent_id ORDER BY vsii.intent_id)
                     FROM vendor_sop_item_intents vsii
                     WHERE vsii.sop_item_id = vsi.id),
                    ARRAY[]::INTEGER[]
                ) as intent_ids
            FROM vendor_sop_items vsi
            WHERE vsi.id = %s
        """, (new_item_id,))

        final_item = cursor.fetchone()
        cursor.close()

        # 🚀 背景生成 embeddings（不阻塞回應）
        if hasattr(request.app.state, 'db_pool'):
            from services.sop_embedding_generator import generate_sop_embeddings_async
            asyncio.create_task(
                generate_sop_embeddings_async(
                    db_pool=request.app.state.db_pool,
                    sop_item_id=new_item_id
                )
            )
            print(f"🚀 [SOP Create] 已觸發背景 embedding 生成 (ID: {new_item_id})")

        return dict(final_item)

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"建立 SOP 項目失敗: {str(e)}")
    finally:
        conn.close()


@router.delete("/{vendor_id}/sop/items/{item_id}")
async def delete_sop_item(vendor_id: int, item_id: int):
    """
    刪除 SOP 項目（軟刪除）

    Args:
        vendor_id: 業者ID
        item_id: SOP項目ID

    Returns:
        Dict: 刪除結果訊息
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # 檢查業者是否存在
        cursor.execute("SELECT id FROM vendors WHERE id = %s", (vendor_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="業者不存在")

        # 檢查 SOP 項目是否存在且屬於該業者
        cursor.execute("""
            SELECT id FROM vendor_sop_items
            WHERE id = %s AND vendor_id = %s AND is_active = TRUE
        """, (item_id, vendor_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="SOP 項目不存在或不屬於該業者")

        # 軟刪除（設為不啟用）
        cursor.execute("""
            UPDATE vendor_sop_items
            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND vendor_id = %s
        """, (item_id, vendor_id))

        conn.commit()
        cursor.close()

        return {
            "message": "SOP 項目已刪除",
            "vendor_id": vendor_id,
            "item_id": item_id
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"刪除 SOP 項目失敗: {str(e)}")
    finally:
        conn.close()


# ========== SOP 範本管理（簡化架構）==========

class CopyTemplateRequest(BaseModel):
    """複製範本請求"""
    template_id: int = Field(..., description="要複製的範本ID")
    category_id: int = Field(..., description="目標分類ID（業者的分類）")
    item_number: Optional[int] = Field(None, description="項次編號（不指定則自動分配）")


class CopyCategoryTemplatesRequest(BaseModel):
    """複製整個分類的範本請求"""
    platform_category_id: int = Field(..., description="平台分類ID（要複製的分類）")
    vendor_category_id: Optional[int] = Field(None, description="目標業者分類ID（不指定則自動創建同名分類）")


class CopyAllTemplatesRequest(BaseModel):
    """複製整份業種範本請求（所有分類）"""
    pass  # 不需要參數，根據業者的 business_type 自動複製所有符合的範本


@router.get("/{vendor_id}/sop/available-templates")
async def get_available_templates(vendor_id: int, category_id: Optional[int] = None):
    """
    取得業者可用的平台 SOP 範本列表（根據業種過濾）

    此端點使用 v_vendor_available_sop_templates 檢視，
    只顯示符合業者業種的範本，並標記已複製的範本。

    Args:
        vendor_id: 業者ID
        category_id: 可選的分類ID過濾

    Returns:
        List[Dict]: 範本列表，包含：
            - 範本資訊（template_id, item_name, content等）
            - already_copied: 是否已複製
            - vendor_sop_item_id: 如已複製，對應的 vendor_sop_items.id
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id, business_types FROM vendors WHERE id = %s AND is_active = TRUE", (vendor_id,))
        vendor = cursor.fetchone()
        if not vendor:
            raise HTTPException(status_code=404, detail="業者不存在")

        # 取得可用範本（已自動根據業種過濾，包含群組資訊）
        query = """
            SELECT
                vendor_id,
                vendor_name,
                vendor_business_types,
                category_id,
                category_name,
                category_description,
                group_id,
                group_name,
                template_id,
                item_number,
                item_name,
                content,
                template_notes,
                customization_hint,
                business_type,
                intent_ids,
                priority,
                already_copied,
                vendor_sop_item_id
            FROM v_vendor_available_sop_templates
            WHERE vendor_id = %s
        """
        params = [vendor_id]

        if category_id:
            query += " AND category_id = %s"
            params.append(category_id)

        query += " ORDER BY category_name, item_number"

        cursor.execute(query, params)
        templates = cursor.fetchall()
        cursor.close()

        return [dict(t) for t in templates]

    finally:
        conn.close()


@router.post("/{vendor_id}/sop/copy-template", status_code=201)
async def copy_template_to_vendor(vendor_id: int, copy_request: CopyTemplateRequest, request: Request):
    """
    複製平台範本到業者 SOP

    將平台範本的內容複製到業者的 vendor_sop_items 中，
    業者可以之後自行編輯調整內容。

    Args:
        vendor_id: 業者ID
        request: 複製請求（包含 template_id, category_id, item_number）

    Returns:
        Dict: 新建立的 SOP 項目
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id, business_types FROM vendors WHERE id = %s AND is_active = TRUE", (vendor_id,))
        vendor = cursor.fetchone()
        if not vendor:
            raise HTTPException(status_code=404, detail="業者不存在")

        # 檢查範本是否存在且符合業者業種
        cursor.execute("""
            SELECT
                pt.id,
                pt.item_number,
                pt.item_name,
                pt.content,
                pt.business_type,
                pt.priority,
                COALESCE(
                    (SELECT ARRAY_AGG(psti.intent_id ORDER BY psti.intent_id)
                     FROM platform_sop_template_intents psti
                     WHERE psti.template_id = pt.id),
                    ARRAY[]::INTEGER[]
                ) as intent_ids
            FROM platform_sop_templates pt
            WHERE pt.id = %s AND pt.is_active = TRUE
        """, (copy_request.template_id,))
        template = cursor.fetchone()

        if not template:
            raise HTTPException(status_code=404, detail=f"範本 ID {copy_request.template_id} 不存在或已停用")

        # 驗證業種匹配（使用陣列操作）
        if template['business_type'] and template['business_type'] not in vendor['business_types']:
            raise HTTPException(
                status_code=400,
                detail=f"範本業種類型 ({template['business_type']}) 與業者業種 ({', '.join(vendor['business_types'])}) 不符"
            )

        # 檢查分類是否存在且屬於該業者
        cursor.execute("""
            SELECT id FROM vendor_sop_categories
            WHERE id = %s AND vendor_id = %s AND is_active = TRUE
        """, (copy_request.category_id, vendor_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="分類不存在或不屬於該業者")

        # 檢查是否已複製此範本
        cursor.execute("""
            SELECT id FROM vendor_sop_items
            WHERE vendor_id = %s AND template_id = %s AND is_active = TRUE
        """, (vendor_id, copy_request.template_id))
        existing = cursor.fetchone()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"已複製此範本（SOP項目 ID: {existing['id']}），請直接編輯現有項目"
            )

        # 決定項次編號
        item_number = copy_request.item_number
        if item_number is None:
            # 自動分配：找到該分類下最大的 item_number + 1
            cursor.execute("""
                SELECT COALESCE(MAX(item_number), 0) + 1 AS next_number
                FROM vendor_sop_items
                WHERE category_id = %s AND vendor_id = %s
            """, (copy_request.category_id, vendor_id))
            item_number = cursor.fetchone()['next_number']

        # 插入新 SOP 項目（複製範本內容）
        cursor.execute("""
            INSERT INTO vendor_sop_items (
                category_id,
                vendor_id,
                item_number,
                item_name,
                content,
                template_id,
                priority
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            copy_request.category_id,
            vendor_id,
            item_number,
            template['item_name'],
            template['content'],
            copy_request.template_id,
            template['priority']
        ))

        new_item = cursor.fetchone()
        new_item_id = new_item['id']

        # 插入意圖關聯（從範本複製）
        if template['intent_ids']:
            for intent_id in template['intent_ids']:
                cursor.execute("""
                    INSERT INTO vendor_sop_item_intents (sop_item_id, intent_id)
                    VALUES (%s, %s)
                """, (new_item_id, intent_id))

        conn.commit()

        # 🚀 背景生成 embeddings（不阻塞回應）
        if hasattr(request.app.state, 'db_pool'):
            from services.sop_embedding_generator import generate_sop_embeddings_async
            asyncio.create_task(
                generate_sop_embeddings_async(
                    db_pool=request.app.state.db_pool,
                    sop_item_id=new_item_id
                )
            )
            print(f"🚀 [SOP Copy Template] 已觸發背景 embedding 生成 (ID: {new_item_id})")

        # 查詢完整資訊
        cursor.execute("""
            SELECT
                vsi.*,
                COALESCE(
                    (SELECT ARRAY_AGG(vsii.intent_id ORDER BY vsii.intent_id)
                     FROM vendor_sop_item_intents vsii
                     WHERE vsii.sop_item_id = vsi.id),
                    ARRAY[]::INTEGER[]
                ) as intent_ids
            FROM vendor_sop_items vsi
            WHERE vsi.id = %s
        """, (new_item_id,))

        final_item = cursor.fetchone()
        cursor.close()

        return {
            **dict(final_item),
            "message": "範本已成功複製，可以進行編輯調整",
            "template_id": copy_request.template_id
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"複製範本失敗: {str(e)}")
    finally:
        conn.close()


@router.post("/{vendor_id}/sop/copy-category-templates", status_code=201)
async def copy_category_templates_to_vendor(vendor_id: int, request: CopyCategoryTemplatesRequest):
    """
    複製整個平台分類的所有範本到業者 SOP

    將平台分類下的所有範本項目複製到業者的 vendor_sop_items 中。
    如果未指定業者分類，則自動創建同名分類。

    Args:
        vendor_id: 業者ID
        request: 複製請求（包含 platform_category_id, vendor_category_id）

    Returns:
        Dict: 複製結果，包含新建立的分類和所有 SOP 項目
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id, business_types FROM vendors WHERE id = %s AND is_active = TRUE", (vendor_id,))
        vendor = cursor.fetchone()
        if not vendor:
            raise HTTPException(status_code=404, detail="業者不存在")

        # 檢查平台分類是否存在
        cursor.execute("""
            SELECT id, category_name, description, display_order
            FROM platform_sop_categories
            WHERE id = %s AND is_active = TRUE
        """, (request.platform_category_id,))
        platform_category = cursor.fetchone()

        if not platform_category:
            raise HTTPException(status_code=404, detail=f"平台分類 ID {request.platform_category_id} 不存在或已停用")

        # 取得該分類下的所有範本（符合業者業種，使用陣列操作）
        cursor.execute("""
            SELECT
                pt.id,
                pt.item_number,
                pt.item_name,
                pt.content,
                pt.business_type,
                pt.priority,
                COALESCE(
                    (SELECT ARRAY_AGG(psti.intent_id ORDER BY psti.intent_id)
                     FROM platform_sop_template_intents psti
                     WHERE psti.template_id = pt.id),
                    ARRAY[]::INTEGER[]
                ) as intent_ids
            FROM platform_sop_templates pt
            WHERE pt.category_id = %s
              AND pt.is_active = TRUE
              AND (pt.business_type = ANY(%s) OR pt.business_type IS NULL)
            ORDER BY pt.item_number
        """, (request.platform_category_id, vendor['business_types']))
        templates = cursor.fetchall()

        if not templates:
            raise HTTPException(
                status_code=404,
                detail=f"平台分類 '{platform_category['category_name']}' 下沒有符合業者業種的範本"
            )

        # 檢查是否已複製該分類的範本
        template_ids = [t['id'] for t in templates]
        cursor.execute("""
            SELECT COUNT(*) as copied_count
            FROM vendor_sop_items
            WHERE vendor_id = %s AND template_id = ANY(%s) AND is_active = TRUE
        """, (vendor_id, template_ids))
        result = cursor.fetchone()

        if result['copied_count'] > 0:
            raise HTTPException(
                status_code=400,
                detail=f"已複製該分類的部分範本（{result['copied_count']} 個），請檢查並刪除後再重新複製整個分類"
            )

        # 決定業者分類
        vendor_category_id = request.vendor_category_id

        if not vendor_category_id:
            # 自動創建同名分類
            cursor.execute("""
                INSERT INTO vendor_sop_categories (
                    vendor_id, category_name, description, display_order
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id, category_name, description, display_order
            """, (
                vendor_id,
                platform_category['category_name'],
                platform_category['description'],
                platform_category['display_order']
            ))
            new_category = cursor.fetchone()
            vendor_category_id = new_category['id']
            category_created = True
        else:
            # 檢查指定的業者分類是否存在
            cursor.execute("""
                SELECT id, category_name FROM vendor_sop_categories
                WHERE id = %s AND vendor_id = %s AND is_active = TRUE
            """, (vendor_category_id, vendor_id))
            existing_category = cursor.fetchone()

            if not existing_category:
                raise HTTPException(status_code=400, detail="指定的業者分類不存在或不屬於該業者")

            new_category = existing_category
            category_created = False

        # 批次複製所有範本項目
        copied_items = []
        for template in templates:
            # 插入新 SOP 項目
            cursor.execute("""
                INSERT INTO vendor_sop_items (
                    category_id,
                    vendor_id,
                    item_number,
                    item_name,
                    content,
                    template_id,
                    priority
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                vendor_category_id,
                vendor_id,
                template['item_number'],
                template['item_name'],
                template['content'],
                template['id'],
                template['priority']
            ))

            new_item = cursor.fetchone()
            new_item_id = new_item['id']

            # 插入意圖關聯（從範本複製）
            if template['intent_ids']:
                for intent_id in template['intent_ids']:
                    cursor.execute("""
                        INSERT INTO vendor_sop_item_intents (sop_item_id, intent_id)
                        VALUES (%s, %s)
                    """, (new_item_id, intent_id))

            copied_items.append({'id': new_item_id})

        conn.commit()
        cursor.close()

        return {
            "message": f"成功複製分類 '{platform_category['category_name']}'，共 {len(copied_items)} 個範本項目",
            "platform_category": {
                "id": platform_category['id'],
                "name": platform_category['category_name']
            },
            "vendor_category": {
                "id": vendor_category_id,
                "name": new_category['category_name'],
                "created": category_created
            },
            "copied_items_count": len(copied_items),
            "copied_items": copied_items
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"複製分類範本失敗: {str(e)}")
    finally:
        conn.close()


@router.post("/{vendor_id}/sop/copy-category/{platform_category_id}", status_code=201)
async def copy_category_to_vendor(vendor_id: int, platform_category_id: int, overwrite: bool = False):
    """
    複製單個平台分類的所有範本到業者 SOP

    Args:
        vendor_id: 業者ID
        platform_category_id: 平台分類ID
        overwrite: 如果該分類已存在，是否覆蓋（預設為 False）

    Returns:
        Dict: 複製結果，包含新建立的分類、群組和 SOP 項目統計
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id, business_types, name FROM vendors WHERE id = %s AND is_active = TRUE", (vendor_id,))
        vendor = cursor.fetchone()
        if not vendor:
            raise HTTPException(status_code=404, detail="業者不存在")

        # 檢查平台分類是否存在
        cursor.execute("""
            SELECT id, category_name, description, display_order
            FROM platform_sop_categories
            WHERE id = %s AND is_active = TRUE
        """, (platform_category_id,))
        platform_category = cursor.fetchone()
        if not platform_category:
            raise HTTPException(status_code=404, detail="平台分類不存在")

        # 檢查該分類是否已存在於業者 SOP 中
        cursor.execute("""
            SELECT id, category_name
            FROM vendor_sop_categories
            WHERE vendor_id = %s AND category_name = %s
        """, (vendor_id, platform_category['category_name']))
        existing_category = cursor.fetchone()

        deleted_items = 0
        deleted_groups = 0
        deleted_category = False

        if existing_category:
            if not overwrite:
                raise HTTPException(
                    status_code=409,
                    detail=f"分類「{platform_category['category_name']}」已存在，如需覆蓋請設定 overwrite=true"
                )

            # 覆蓋模式：刪除現有的該分類項目
            vendor_category_id = existing_category['id']

            cursor.execute("""
                DELETE FROM vendor_sop_items
                WHERE category_id = %s AND vendor_id = %s
            """, (vendor_category_id, vendor_id))
            deleted_items = cursor.rowcount

            cursor.execute("""
                DELETE FROM vendor_sop_groups
                WHERE category_id = %s AND vendor_id = %s
            """, (vendor_category_id, vendor_id))
            deleted_groups = cursor.rowcount

            cursor.execute("""
                DELETE FROM vendor_sop_categories
                WHERE id = %s AND vendor_id = %s
            """, (vendor_category_id, vendor_id))
            deleted_category = True

        # 創建業者分類
        cursor.execute("""
            INSERT INTO vendor_sop_categories (
                vendor_id, category_name, description, display_order
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id, category_name
        """, (
            vendor_id,
            platform_category['category_name'],
            platform_category['description'],
            platform_category['display_order']
        ))
        new_category = cursor.fetchone()
        vendor_category_id = new_category['id']

        # 取得該分類下的所有平台群組
        cursor.execute("""
            SELECT DISTINCT
                pg.id as platform_group_id,
                pg.group_name,
                pg.display_order
            FROM platform_sop_groups pg
            INNER JOIN platform_sop_templates pt ON pt.group_id = pg.id
            WHERE pg.category_id = %s
              AND pt.is_active = TRUE
              AND (pt.business_type = ANY(%s) OR pt.business_type IS NULL)
            ORDER BY pg.display_order
        """, (platform_category_id, vendor['business_types']))
        platform_groups = cursor.fetchall()

        # 創建群組映射 {platform_group_id: vendor_group_id}
        group_id_mapping = {}
        for platform_group in platform_groups:
            cursor.execute("""
                INSERT INTO vendor_sop_groups (
                    vendor_id, category_id, group_name, display_order, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (
                vendor_id,
                vendor_category_id,
                platform_group['group_name'],
                platform_group['display_order']
            ))
            new_group = cursor.fetchone()
            group_id_mapping[platform_group['platform_group_id']] = new_group['id']

        # 取得該分類下的所有範本
        cursor.execute("""
            SELECT
                pt.id,
                pt.group_id,
                pt.item_number,
                pt.item_name,
                pt.content,
                pt.priority,
                COALESCE(
                    (SELECT ARRAY_AGG(psti.intent_id ORDER BY psti.intent_id)
                     FROM platform_sop_template_intents psti
                     WHERE psti.template_id = pt.id),
                    ARRAY[]::INTEGER[]
                ) as intent_ids
            FROM platform_sop_templates pt
            WHERE pt.category_id = %s
              AND pt.is_active = TRUE
              AND (pt.business_type = ANY(%s) OR pt.business_type IS NULL)
            ORDER BY pt.item_number
        """, (platform_category_id, vendor['business_types']))
        templates = cursor.fetchall()

        if not templates:
            raise HTTPException(
                status_code=404,
                detail=f"分類「{platform_category['category_name']}」中沒有符合業者業種的範本"
            )

        # 批次複製範本項目
        new_item_ids = []
        for template in templates:
            # 從映射中找到對應的 vendor group_id
            vendor_group_id = group_id_mapping.get(template['group_id']) if template['group_id'] else None

            cursor.execute("""
                INSERT INTO vendor_sop_items (
                    category_id,
                    vendor_id,
                    group_id,
                    item_number,
                    item_name,
                    content,
                    template_id,
                    priority
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                vendor_category_id,
                vendor_id,
                vendor_group_id,
                template['item_number'],
                template['item_name'],
                template['content'],
                template['id'],
                template['priority']
            ))
            new_item = cursor.fetchone()
            new_item_id = new_item['id']

            # 插入意圖關聯（從範本複製）
            if template['intent_ids']:
                for intent_id in template['intent_ids']:
                    cursor.execute("""
                        INSERT INTO vendor_sop_item_intents (sop_item_id, intent_id)
                        VALUES (%s, %s)
                    """, (new_item_id, intent_id))

            new_item_ids.append(new_item_id)

        # 為所有新建立的 SOP 項目生成 embeddings
        embeddings_generated = 0
        embeddings_failed = 0

        for item_id in new_item_ids:
            try:
                # 取得項目資訊
                cursor.execute("""
                    SELECT vsi.id, vsi.content, vsi.item_name,
                           vsg.group_name
                    FROM vendor_sop_items vsi
                    LEFT JOIN vendor_sop_groups vsg ON vsi.group_id = vsg.id
                    WHERE vsi.id = %s
                """, (item_id,))
                item = cursor.fetchone()

                if item:
                    content = item['content']
                    item_name = item['item_name']
                    group_name = item['group_name'] or ''

                    # 生成 primary embedding（使用 group_name + item_name）
                    primary_text = f"{group_name} {item_name}".strip()
                    primary_embedding = await generate_embedding(primary_text)

                    # 生成 fallback embedding（使用 content）
                    fallback_embedding = await generate_embedding(content)

                    # 轉換為 pgvector 格式
                    primary_vector = str(primary_embedding)
                    fallback_vector = str(fallback_embedding)

                    # 更新資料庫（同時更新 primary 和 fallback）
                    cursor.execute("""
                        UPDATE vendor_sop_items
                        SET
                            primary_embedding = %s,
                            fallback_embedding = %s
                        WHERE id = %s
                    """, (primary_embedding, fallback_embedding, item_id))
                    embeddings_generated += 1

            except Exception as e:
                print(f"為 item {item_id} 生成 embedding 失敗: {e}")
                embeddings_failed += 1

        conn.commit()
        cursor.close()

        return {
            "message": f"成功複製分類「{platform_category['category_name']}」，共 {len(new_item_ids)} 個項目",
            "vendor_id": vendor_id,
            "vendor_name": vendor['name'],
            "category_id": vendor_category_id,
            "category_name": platform_category['category_name'],
            "overwritten": deleted_category,
            "deleted_items": deleted_items,
            "deleted_groups": deleted_groups,
            "groups_created": len(platform_groups),
            "items_copied": len(new_item_ids),
            "embeddings_generated": embeddings_generated,
            "embeddings_failed": embeddings_failed
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"複製分類失敗: {str(e)}")
    finally:
        conn.close()


@router.post("/{vendor_id}/sop/copy-all-templates", status_code=201)
async def copy_all_templates_to_vendor(vendor_id: int, request: Request, business_type: Optional[str] = None):
    """
    複製平台範本到業者 SOP（支援全部或單一業態）

    根據業者的 business_types 或指定的 business_type，自動複製所有符合的平台範本分類和項目。
    會自動創建與平台同名的分類，並批次複製所有範本項目。

    Args:
        vendor_id: 業者ID
        request: FastAPI Request 對象（用於訪問 db_pool 生成 embeddings）
        business_type: 可選，指定單一業態（full_service/property_management/universal/null），
                      若未指定則複製業者所有業態

    Returns:
        Dict: 複製結果，包含所有新建立的分類和 SOP 項目統計
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id, business_types, name FROM vendors WHERE id = %s AND is_active = TRUE", (vendor_id,))
        vendor = cursor.fetchone()
        if not vendor:
            raise HTTPException(status_code=404, detail="業者不存在")

        # 刪除所有現有的 SOP 項目（覆蓋模式）
        cursor.execute("""
            DELETE FROM vendor_sop_items
            WHERE vendor_id = %s
        """, (vendor_id,))
        deleted_items_count = cursor.rowcount

        # 刪除所有現有的 SOP 群組
        cursor.execute("""
            DELETE FROM vendor_sop_groups
            WHERE vendor_id = %s
        """, (vendor_id,))
        deleted_groups_count = cursor.rowcount

        # 刪除所有現有的 SOP 分類
        cursor.execute("""
            DELETE FROM vendor_sop_categories
            WHERE vendor_id = %s
        """, (vendor_id,))
        deleted_categories_count = cursor.rowcount

        # 處理 business_type 參數（將 "universal"/"null" 轉為 None）
        business_type_filter = None
        if business_type and business_type.lower() not in ['universal', 'null', 'none']:
            business_type_filter = business_type

        # 構建查詢條件
        if business_type is not None:
            # 指定單一業態
            if business_type_filter is None:
                # 只查詢通用型（business_type IS NULL）
                business_type_condition = "pt.business_type IS NULL"
                query_params = []
            else:
                # 查詢特定業態
                business_type_condition = "pt.business_type = %s"
                query_params = [business_type_filter]

            business_type_label = {
                'full_service': '包租型',
                'property_management': '代管型',
                None: '通用型'
            }.get(business_type_filter, business_type_filter)
        else:
            # 複製業者所有業態（原邏輯）
            business_type_condition = "(pt.business_type = ANY(%s) OR pt.business_type IS NULL)"
            query_params = [vendor['business_types']]
            business_type_label = f"所有業態 ({', '.join(vendor['business_types'])})"

        # 取得所有符合條件的平台分類和範本
        cursor.execute(f"""
            SELECT DISTINCT
                pc.id as category_id,
                pc.category_name,
                pc.description,
                pc.display_order
            FROM platform_sop_categories pc
            INNER JOIN platform_sop_templates pt ON pt.category_id = pc.id
            WHERE pc.is_active = TRUE
              AND pt.is_active = TRUE
              AND {business_type_condition}
            ORDER BY pc.display_order, pc.category_name
        """, query_params)
        platform_categories = cursor.fetchall()

        if not platform_categories:
            raise HTTPException(
                status_code=404,
                detail=f"沒有找到符合條件 ({business_type_label}) 的範本分類"
            )

        # 統計資訊
        created_categories = []
        copied_items_total = 0
        copied_groups_total = 0
        all_new_item_ids = []  # 記錄所有新建立的 item ID，用於後續生成 embedding

        # 逐個分類處理
        for platform_category in platform_categories:
            # 創建業者分類
            cursor.execute("""
                INSERT INTO vendor_sop_categories (
                    vendor_id, category_name, description, display_order
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id, category_name
            """, (
                vendor_id,
                platform_category['category_name'],
                platform_category['description'],
                platform_category['display_order']
            ))
            new_category = cursor.fetchone()
            vendor_category_id = new_category['id']

            # 取得該分類下的所有平台群組
            group_query_params = [platform_category['category_id']] + query_params
            cursor.execute(f"""
                SELECT DISTINCT
                    pg.id as platform_group_id,
                    pg.group_name,
                    pg.display_order
                FROM platform_sop_groups pg
                INNER JOIN platform_sop_templates pt ON pt.group_id = pg.id
                WHERE pg.category_id = %s
                  AND pt.is_active = TRUE
                  AND {business_type_condition}
                ORDER BY pg.display_order
            """, group_query_params)
            platform_groups = cursor.fetchall()

            # 創建群組映射 {platform_group_id: vendor_group_id}
            group_id_mapping = {}
            for platform_group in platform_groups:
                cursor.execute("""
                    INSERT INTO vendor_sop_groups (
                        vendor_id, category_id, group_name, display_order, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                """, (
                    vendor_id,
                    vendor_category_id,
                    platform_group['group_name'],
                    platform_group['display_order']
                ))
                new_group = cursor.fetchone()
                group_id_mapping[platform_group['platform_group_id']] = new_group['id']
                copied_groups_total += 1

            # 取得該分類下的所有範本（包含 group_id）
            template_query_params = [platform_category['category_id']] + query_params
            cursor.execute(f"""
                SELECT
                    pt.id,
                    pt.group_id,
                    pt.item_number,
                    pt.item_name,
                    pt.content,
                    pt.priority,
                    COALESCE(
                        (SELECT ARRAY_AGG(psti.intent_id ORDER BY psti.intent_id)
                         FROM platform_sop_template_intents psti
                         WHERE psti.template_id = pt.id),
                        ARRAY[]::INTEGER[]
                    ) as intent_ids
                FROM platform_sop_templates pt
                WHERE pt.category_id = %s
                  AND pt.is_active = TRUE
                  AND {business_type_condition}
                ORDER BY pt.item_number
            """, template_query_params)
            templates = cursor.fetchall()

            # 批次複製範本項目
            copied_items = []
            for template in templates:
                # 從映射中找到對應的 vendor group_id
                vendor_group_id = group_id_mapping.get(template['group_id']) if template['group_id'] else None

                cursor.execute("""
                    INSERT INTO vendor_sop_items (
                        category_id,
                        vendor_id,
                        group_id,
                        item_number,
                        item_name,
                        content,
                        template_id,
                        priority
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    vendor_category_id,
                    vendor_id,
                    vendor_group_id,
                    template['item_number'],
                    template['item_name'],
                    template['content'],
                    template['id'],
                    template['priority']
                ))
                new_item = cursor.fetchone()
                new_item_id = new_item['id']

                # 插入意圖關聯（從範本複製）
                if template['intent_ids']:
                    for intent_id in template['intent_ids']:
                        cursor.execute("""
                            INSERT INTO vendor_sop_item_intents (sop_item_id, intent_id)
                            VALUES (%s, %s)
                        """, (new_item_id, intent_id))

                copied_items.append(new_item_id)
                all_new_item_ids.append(new_item_id)

            # 記錄該分類的複製結果
            created_categories.append({
                "category_id": vendor_category_id,
                "category_name": platform_category['category_name'],
                "items_count": len(copied_items)
            })
            copied_items_total += len(copied_items)

        conn.commit()
        conn.close()

        # 🚀 背景批量生成 embeddings（不阻塞回應）
        if all_new_item_ids and request and hasattr(request.app.state, 'db_pool'):
            from services.sop_embedding_generator import generate_batch_sop_embeddings_async
            asyncio.create_task(
                generate_batch_sop_embeddings_async(
                    db_pool=request.app.state.db_pool,
                    sop_item_ids=all_new_item_ids,
                    batch_size=5
                )
            )
            print(f"🚀 [SOP Copy] 已觸發背景 embedding 批量生成 ({len(all_new_item_ids)} 個項目)")

        # 組合訊息
        message_parts = []
        if deleted_items_count > 0 or deleted_categories_count > 0:
            message_parts.append(f"已刪除現有 SOP（{deleted_categories_count} 個分類、{deleted_items_count} 個項目）")

        # 根據 business_type 參數顯示不同訊息
        if business_type is not None:
            message_parts.append(f"成功為業者「{vendor['name']}」複製 {business_type_label} SOP 範本")
        else:
            message_parts.append(f"成功為業者「{vendor['name']}」複製整份 SOP 範本（{business_type_label}）")

        if all_new_item_ids:
            message_parts.append(f"已觸發背景 embedding 生成（{len(all_new_item_ids)} 個項目）")

        return {
            "message": "，".join(message_parts),
            "business_type_copied": business_type_label,
            "vendor_business_types": vendor['business_types'],
            "deleted_categories": deleted_categories_count,
            "deleted_items": deleted_items_count,
            "categories_created": len(created_categories),
            "groups_created": copied_groups_total,
            "total_items_copied": copied_items_total,
            "embedding_generation_triggered": len(all_new_item_ids) if all_new_item_ids else 0,
            "categories": created_categories
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"複製整份範本失敗: {str(e)}")
    finally:
        if conn and not conn.closed:
            conn.close()


# ========== Excel 匯入功能 ==========

@router.post("/{vendor_id}/sop/import-excel", status_code=201)
async def import_sop_from_excel(
    vendor_id: int,
    file: UploadFile = File(...),
    overwrite: bool = False,
    request: Request = None
):
    """
    從 Excel 檔案匯入 SOP

    支援的 Excel 格式：
    - 第一欄：分類名稱
    - 第二欄：分類說明
    - 第三欄：項目序號
    - 第四欄：項目名稱
    - 第五欄：項目內容

    Args:
        vendor_id: 業者ID
        file: 上傳的 Excel 檔案（.xlsx 或 .xls）
        overwrite: 是否覆蓋現有 SOP（預設為 False）
        request: FastAPI Request 對象

    Returns:
        Dict: 匯入結果統計
    """
    conn = get_db_connection()

    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id, name FROM vendors WHERE id = %s AND is_active = TRUE", (vendor_id,))
        vendor = cursor.fetchone()
        if not vendor:
            raise HTTPException(status_code=404, detail="業者不存在")

        # 檢查檔案類型
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="不支援的檔案格式，請上傳 .xlsx 或 .xls 檔案"
            )

        # 讀取檔案內容
        file_content = await file.read()

        # 解析 Excel
        try:
            sop_data = parse_sop_excel(file_content)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if not sop_data['categories']:
            raise HTTPException(status_code=400, detail="Excel 檔案中沒有找到有效的 SOP 資料")

        # 如果需要覆蓋，先刪除現有的 SOP
        deleted_items = 0
        deleted_categories = 0

        if overwrite:
            cursor.execute("DELETE FROM vendor_sop_items WHERE vendor_id = %s", (vendor_id,))
            deleted_items = cursor.rowcount

            cursor.execute("DELETE FROM vendor_sop_groups WHERE vendor_id = %s", (vendor_id,))

            cursor.execute("DELETE FROM vendor_sop_categories WHERE vendor_id = %s", (vendor_id,))
            deleted_categories = cursor.rowcount
        else:
            # 檢查是否已有 SOP
            cursor.execute("SELECT COUNT(*) as count FROM vendor_sop_items WHERE vendor_id = %s", (vendor_id,))
            result = cursor.fetchone()
            if result['count'] > 0:
                raise HTTPException(
                    status_code=409,
                    detail=f"業者已有 {result['count']} 個 SOP 項目，如需覆蓋請設定 overwrite=true"
                )

        # 匯入 SOP（三層結構：Categories → Groups → Items）
        created_categories = 0
        created_groups = 0
        created_items = 0
        all_item_ids = []

        for cat_idx, category in enumerate(sop_data['categories'], 1):
            # 1. 插入分類
            cursor.execute("""
                INSERT INTO vendor_sop_categories (
                    vendor_id, category_name, display_order
                )
                VALUES (%s, %s, %s)
                RETURNING id
            """, (
                vendor_id,
                category['name'],
                cat_idx
            ))

            category_id = cursor.fetchone()['id']
            created_categories += 1

            # 2. 插入群組並處理項目
            for grp_idx, group in enumerate(category['groups'], 1):
                # 插入群組
                cursor.execute("""
                    INSERT INTO vendor_sop_groups (
                        vendor_id, category_id, group_name, display_order
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (
                    vendor_id,
                    category_id,
                    group['name'],
                    grp_idx
                ))

                group_id = cursor.fetchone()['id']
                created_groups += 1

                # 3. 插入群組下的所有項目
                for item in group['items']:
                    # 識別是否需要金流判斷
                    cashflow_info = identify_cashflow_sensitive_items(item['name'], item['content'])

                    cursor.execute("""
                        INSERT INTO vendor_sop_items (
                            category_id,
                            vendor_id,
                            group_id,
                            item_number,
                            item_name,
                            content,
                            priority,
                            requires_cashflow_check,
                            cashflow_through_company,
                            cashflow_direct_to_landlord
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        category_id,
                        vendor_id,
                        group_id,  # 關聯群組
                        item['number'],
                        item['name'],
                        item['content'],
                        50,  # 預設優先級
                        cashflow_info['requires_cashflow'],
                        cashflow_info['through_company'],
                        cashflow_info['direct_to_landlord']
                    ))

                    item_id = cursor.fetchone()['id']
                    created_items += 1
                    all_item_ids.append(item_id)

        conn.commit()
        cursor.close()

        # 🚀 背景批量生成 embeddings（不阻塞回應）
        if all_item_ids and request and hasattr(request.app.state, 'db_pool'):
            from services.sop_embedding_generator import generate_batch_sop_embeddings_async
            asyncio.create_task(
                generate_batch_sop_embeddings_async(
                    db_pool=request.app.state.db_pool,
                    sop_item_ids=all_item_ids,
                    batch_size=5
                )
            )
            print(f"🚀 [Excel Import] 已觸發背景 embedding 批量生成 ({len(all_item_ids)} 個項目)")

        # 組合回應訊息
        message_parts = []
        if deleted_items > 0:
            message_parts.append(f"已刪除原有 {deleted_categories} 個分類、{deleted_items} 個項目")

        message_parts.append(f"成功從 Excel 匯入 {created_categories} 個分類、{created_groups} 個群組、{created_items} 個 SOP 項目")

        if all_item_ids:
            message_parts.append(f"已觸發背景 embedding 生成")

        return {
            "message": "，".join(message_parts),
            "vendor_id": vendor_id,
            "vendor_name": vendor['name'],
            "file_name": file.filename,
            "deleted_categories": deleted_categories,
            "deleted_items": deleted_items,
            "created_categories": created_categories,
            "created_groups": created_groups,
            "created_items": created_items,
            "embedding_generation_triggered": len(all_item_ids)
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"匯入失敗: {str(e)}")
    finally:
        if conn and not conn.closed:
            conn.close()


# ========== Embedding 管理功能 ==========

@router.post("/{vendor_id}/sop/regenerate-embeddings", status_code=200)
async def regenerate_sop_embeddings(vendor_id: int, request: Request):
    """
    批量重新生成業者 SOP 的 embeddings

    功能：
    - 查找該業者所有缺少 embedding 的 SOP 項目
    - 在背景批量生成 embeddings（primary + fallback）
    - 不阻塞 API 回應

    Args:
        vendor_id: 業者ID
        request: Request 對象（用於訪問 db_pool）

    Returns:
        Dict: 批量生成任務資訊
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id, name FROM vendors WHERE id = %s", (vendor_id,))
        vendor = cursor.fetchone()
        if not vendor:
            raise HTTPException(status_code=404, detail="業者不存在")

        # 查詢所有缺少 embedding 的 SOP 項目
        cursor.execute("""
            SELECT id, item_name
            FROM vendor_sop_items
            WHERE vendor_id = %s
              AND is_active = TRUE
              AND (primary_embedding IS NULL OR fallback_embedding IS NULL)
            ORDER BY id
        """, (vendor_id,))

        missing_items = cursor.fetchall()
        missing_ids = [item['id'] for item in missing_items]

        cursor.close()

        if not missing_ids:
            return {
                "message": f"業者「{vendor['name']}」的所有 SOP 項目都已有 embedding",
                "vendor_id": vendor_id,
                "vendor_name": vendor['name'],
                "total_items": 0,
                "missing_items": []
            }

        # 🚀 背景批量生成 embeddings（不阻塞回應）
        if hasattr(request.app.state, 'db_pool'):
            from services.sop_embedding_generator import generate_batch_sop_embeddings_async
            asyncio.create_task(
                generate_batch_sop_embeddings_async(
                    db_pool=request.app.state.db_pool,
                    sop_item_ids=missing_ids,
                    batch_size=5
                )
            )
            print(f"🚀 [SOP Regenerate] 已觸發批量 embedding 生成：業者 {vendor_id}，共 {len(missing_ids)} 個項目")

        return {
            "message": f"已觸發批量 embedding 生成：{len(missing_ids)} 個項目",
            "vendor_id": vendor_id,
            "vendor_name": vendor['name'],
            "total_items": len(missing_ids),
            "missing_items": [
                {"id": item['id'], "item_name": item['item_name']}
                for item in missing_items
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量生成失敗: {str(e)}")
    finally:
        if conn and not conn.closed:
            conn.close()
