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
    created_by: str = Field("admin", description="建立者")


class VendorUpdate(BaseModel):
    """更新業者請求"""
    name: Optional[str] = Field(None, description="業者名稱", max_length=200)
    short_name: Optional[str] = Field(None, description="簡稱", max_length=100)
    contact_phone: Optional[str] = Field(None, description="聯絡電話", max_length=50)
    contact_email: Optional[str] = Field(None, description="聯絡郵箱", max_length=100)
    address: Optional[str] = Field(None, description="公司地址")
    subscription_plan: Optional[str] = Field(None, description="訂閱方案")
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

        query = "SELECT * FROM vendors WHERE 1=1"
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
                address, subscription_plan, subscription_status,
                subscription_start_date, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            vendor.code,
            vendor.name,
            vendor.short_name,
            vendor.contact_phone,
            vendor.contact_email,
            vendor.address,
            vendor.subscription_plan,
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
    獲取業者配置參數

    可選過濾：
    - category: 參數分類（payment, contract, service, contact）
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 檢查業者是否存在
        cursor.execute("SELECT id FROM vendors WHERE id = %s", (vendor_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="業者不存在")

        # 獲取配置
        query = """
            SELECT
                id, category, param_key, param_value,
                data_type, display_name, description, unit,
                is_active, created_at, updated_at
            FROM vendor_configs
            WHERE vendor_id = %s AND is_active = true
        """
        params = [vendor_id]

        if category:
            query += " AND category = %s"
            params.append(category)

        query += " ORDER BY category, param_key"

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
    """批次更新業者配置參數"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # 檢查業者是否存在
        cursor.execute("SELECT id FROM vendors WHERE id = %s", (vendor_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="業者不存在")

        # 批次更新配置
        for config in config_update.configs:
            cursor.execute("""
                INSERT INTO vendor_configs (
                    vendor_id, category, param_key, param_value,
                    data_type, display_name, description, unit
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (vendor_id, category, param_key)
                DO UPDATE SET
                    param_value = EXCLUDED.param_value,
                    data_type = EXCLUDED.data_type,
                    display_name = EXCLUDED.display_name,
                    description = EXCLUDED.description,
                    unit = EXCLUDED.unit,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                vendor_id,
                config.category,
                config.param_key,
                config.param_value,
                config.data_type,
                config.display_name,
                config.description,
                config.unit
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
