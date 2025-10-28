"""
Vendors API Router
業者管理 API - 管理包租代管業者及其配置參數
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, date
import os
import psycopg2
import psycopg2.extras


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
    template_id: Optional[int] = Field(None, description="來源範本ID（記錄從哪個範本複製而來）")
    intent_ids: Optional[List[int]] = Field(None, description="關聯意圖ID列表")
    priority: int = Field(50, description="優先級（0-100）", ge=0, le=100)


class SOPItemUpdate(BaseModel):
    """更新 SOP 項目"""
    item_name: str = Field(..., description="項目名稱")
    content: str = Field(..., description="項目內容")
    intent_ids: Optional[List[int]] = Field(None, description="關聯意圖ID列表（支援多意圖）")
    priority: Optional[int] = Field(None, description="優先級（0-100）", ge=0, le=100)


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

        # 獲取 SOP 項目（包含群組資訊、範本來源、多意圖支援）
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
                vsi.template_id,
                vsi.priority,
                pt.item_name as template_item_name,
                vsi.is_active,
                vsi.created_at,
                vsi.updated_at,
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
async def update_sop_item(vendor_id: int, item_id: int, item_update: SOPItemUpdate):
    """
    更新 SOP 項目

    Args:
        vendor_id: 業者ID
        item_id: SOP項目ID
        item_update: 更新資料

    Returns:
        Dict: 更新後的 SOP 項目
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id FROM vendors WHERE id = %s", (vendor_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="業者不存在")

        # 檢查 SOP 項目是否存在且屬於該業者
        cursor.execute("""
            SELECT id FROM vendor_sop_items
            WHERE id = %s AND vendor_id = %s
        """, (item_id, vendor_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="SOP 項目不存在或不屬於該業者")

        # 驗證所有意圖是否存在（如果有指定）
        if item_update.intent_ids:
            for intent_id in item_update.intent_ids:
                cursor.execute("SELECT id FROM intents WHERE id = %s", (intent_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=400, detail=f"意圖 ID {intent_id} 不存在")

        # 更新 SOP 項目基本資訊
        update_fields = []
        params = []

        update_fields.append("item_name = %s")
        params.append(item_update.item_name)

        update_fields.append("content = %s")
        params.append(item_update.content)

        if item_update.priority is not None:
            update_fields.append("priority = %s")
            params.append(item_update.priority)

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

        # 更新多意圖關聯表
        if item_update.intent_ids is not None:
            # 先刪除所有現有關聯
            cursor.execute("""
                DELETE FROM vendor_sop_item_intents
                WHERE sop_item_id = %s
            """, (item_id,))

            # 插入新的意圖關聯
            for intent_id in item_update.intent_ids:
                cursor.execute("""
                    INSERT INTO vendor_sop_item_intents (sop_item_id, intent_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """, (item_id, intent_id))

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
async def create_sop_item(vendor_id: int, item: SOPItemCreate):
    """
    建立新的 SOP 項目

    Args:
        vendor_id: 業者ID
        item: SOP 項目資料

    Returns:
        Dict: 新建立的 SOP 項目
    """
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

        # 插入新 SOP 項目
        cursor.execute("""
            INSERT INTO vendor_sop_items (
                category_id, vendor_id, item_number, item_name, content,
                template_id, priority
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            item.category_id,
            vendor_id,
            item.item_number,
            item.item_name,
            item.content,
            item.template_id,
            item.priority
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
        cursor.execute("SELECT id, business_type FROM vendors WHERE id = %s AND is_active = TRUE", (vendor_id,))
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
async def copy_template_to_vendor(vendor_id: int, request: CopyTemplateRequest):
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
        """, (request.template_id,))
        template = cursor.fetchone()

        if not template:
            raise HTTPException(status_code=404, detail=f"範本 ID {request.template_id} 不存在或已停用")

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
        """, (request.category_id, vendor_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=400, detail="分類不存在或不屬於該業者")

        # 檢查是否已複製此範本
        cursor.execute("""
            SELECT id FROM vendor_sop_items
            WHERE vendor_id = %s AND template_id = %s AND is_active = TRUE
        """, (vendor_id, request.template_id))
        existing = cursor.fetchone()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"已複製此範本（SOP項目 ID: {existing['id']}），請直接編輯現有項目"
            )

        # 決定項次編號
        item_number = request.item_number
        if item_number is None:
            # 自動分配：找到該分類下最大的 item_number + 1
            cursor.execute("""
                SELECT COALESCE(MAX(item_number), 0) + 1 AS next_number
                FROM vendor_sop_items
                WHERE category_id = %s AND vendor_id = %s
            """, (request.category_id, vendor_id))
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
            request.category_id,
            vendor_id,
            item_number,
            template['item_name'],
            template['content'],
            request.template_id,
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
            "template_id": request.template_id
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


@router.post("/{vendor_id}/sop/copy-all-templates", status_code=201)
async def copy_all_templates_to_vendor(vendor_id: int):
    """
    複製整份業種範本到業者 SOP（一次複製所有分類）

    根據業者的 business_type，自動複製所有符合的平台範本分類和項目。
    會自動創建與平台同名的分類，並批次複製所有範本項目。

    Args:
        vendor_id: 業者ID

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

        # 刪除所有現有的 SOP 分類
        cursor.execute("""
            DELETE FROM vendor_sop_categories
            WHERE vendor_id = %s
        """, (vendor_id,))
        deleted_categories_count = cursor.rowcount

        # 取得所有符合業者業種的平台分類和範本（使用陣列操作）
        cursor.execute("""
            SELECT DISTINCT
                pc.id as category_id,
                pc.category_name,
                pc.description,
                pc.display_order
            FROM platform_sop_categories pc
            INNER JOIN platform_sop_templates pt ON pt.category_id = pc.id
            WHERE pc.is_active = TRUE
              AND pt.is_active = TRUE
              AND (pt.business_type = ANY(%s) OR pt.business_type IS NULL)
            ORDER BY pc.display_order, pc.category_name
        """, (vendor['business_types'],))
        platform_categories = cursor.fetchall()

        if not platform_categories:
            raise HTTPException(
                status_code=404,
                detail=f"沒有找到符合業者業種 ({vendor['business_type']}) 的範本分類"
            )

        # 統計資訊
        created_categories = []
        copied_items_total = 0

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

            # 取得該分類下的所有範本
            cursor.execute("""
                SELECT
                    pt.id,
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
            """, (platform_category['category_id'], vendor['business_types']))
            templates = cursor.fetchall()

            # 批次複製範本項目
            copied_items = []
            for template in templates:
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

                copied_items.append(new_item_id)

            # 記錄該分類的複製結果
            created_categories.append({
                "category_id": vendor_category_id,
                "category_name": new_category['category_name'],
                "items_count": len(copied_items)
            })
            copied_items_total += len(copied_items)

        conn.commit()
        cursor.close()

        # 組合訊息
        message_parts = []
        if deleted_items_count > 0 or deleted_categories_count > 0:
            message_parts.append(f"已刪除現有 SOP（{deleted_categories_count} 個分類、{deleted_items_count} 個項目）")
        message_parts.append(f"成功為業者「{vendor['name']}」複製整份 SOP 範本")

        return {
            "message": "，".join(message_parts),
            "business_types": vendor['business_types'],
            "deleted_categories": deleted_categories_count,
            "deleted_items": deleted_items_count,
            "categories_created": len(created_categories),
            "total_items_copied": copied_items_total,
            "categories": created_categories
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"複製整份範本失敗: {str(e)}")
    finally:
        conn.close()
