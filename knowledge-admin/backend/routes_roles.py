"""
角色管理 API
提供角色的 CRUD 操作、權限分配等功能
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, validator
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os
import re

from routes_auth import get_current_user

router = APIRouter(prefix="/api/roles", tags=["角色管理"])

# 資料庫配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "aichatbot_admin")
DB_USER = os.getenv("DB_USER", "aichatbot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "aichatbot_password")

def get_db_connection():
    """建立資料庫連線"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor
    )

# ========== 資料模型 ==========

class RoleBase(BaseModel):
    """角色基礎資料"""
    display_name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    """新增角色請求"""
    name: str

    @validator('name')
    def validate_name(cls, v):
        if not v:
            raise ValueError('角色代碼不能為空')
        if len(v) < 3 or len(v) > 50:
            raise ValueError('角色代碼長度必須在 3-50 字元之間')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('角色代碼只能包含英數字和底線')
        return v

class RoleUpdate(BaseModel):
    """更新角色請求"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[int]] = None

class RoleResponse(BaseModel):
    """角色回應"""
    id: int
    name: str
    display_name: str
    description: Optional[str]
    is_system: bool
    created_at: datetime
    updated_at: datetime
    permission_count: Optional[int] = 0
    user_count: Optional[int] = 0

class RoleDetailResponse(RoleResponse):
    """角色詳情回應（含權限列表）"""
    permissions: List[dict]

class RoleListResponse(BaseModel):
    """角色列表回應"""
    items: List[RoleResponse]
    total: int

# ========== API 端點 ==========

@router.get("", response_model=RoleListResponse)
async def list_roles(
    search: Optional[str] = None,
    is_system: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    列出所有角色

    - **search**: 搜尋關鍵字（搜尋 name, display_name, description）
    - **is_system**: 篩選系統角色 (true/false/all)
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 構建查詢條件
        conditions = []
        params = []

        if search:
            conditions.append("(name ILIKE %s OR display_name ILIKE %s OR description ILIKE %s)")
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern, search_pattern])

        if is_system and is_system != "all":
            conditions.append("is_system = %s")
            params.append(is_system == "true")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 查詢角色列表（含權限數量和用戶數量）
        query = f"""
            SELECT
                r.id, r.name, r.display_name, r.description, r.is_system,
                r.created_at, r.updated_at,
                COUNT(DISTINCT rp.permission_id) as permission_count,
                COUNT(DISTINCT ar.admin_id) as user_count
            FROM roles r
            LEFT JOIN role_permissions rp ON r.id = rp.role_id
            LEFT JOIN admin_roles ar ON r.id = ar.role_id
            WHERE {where_clause}
            GROUP BY r.id, r.name, r.display_name, r.description, r.is_system, r.created_at, r.updated_at
            ORDER BY
                CASE WHEN r.name = 'super_admin' THEN 0 ELSE 1 END,
                r.created_at DESC
        """
        cur.execute(query, params)
        roles = cur.fetchall()

        return {
            "items": roles,
            "total": len(roles)
        }

    finally:
        cur.close()
        conn.close()


@router.get("/{role_id}", response_model=RoleDetailResponse)
async def get_role(
    role_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    獲取單一角色詳情（含權限列表）
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 查詢角色基本資料
        cur.execute("""
            SELECT
                r.id, r.name, r.display_name, r.description, r.is_system,
                r.created_at, r.updated_at,
                COUNT(DISTINCT rp.permission_id) as permission_count,
                COUNT(DISTINCT ar.admin_id) as user_count
            FROM roles r
            LEFT JOIN role_permissions rp ON r.id = rp.role_id
            LEFT JOIN admin_roles ar ON r.id = ar.role_id
            WHERE r.id = %s
            GROUP BY r.id
        """, (role_id,))

        role = cur.fetchone()

        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")

        # 查詢角色的權限列表
        cur.execute("""
            SELECT p.id, p.name, p.display_name, p.resource, p.action, p.description
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            WHERE rp.role_id = %s
            ORDER BY p.resource, p.action
        """, (role_id,))

        permissions = cur.fetchall()

        return {
            **dict(role),
            "permissions": permissions
        }

    finally:
        cur.close()
        conn.close()


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    新增自訂角色

    - **name**: 角色代碼（3-50 字元，只能包含英數字和底線）
    - **display_name**: 角色顯示名稱
    - **description**: 角色說明（選填）
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 檢查角色代碼是否已存在
        cur.execute("SELECT id FROM roles WHERE name = %s", (data.name,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="角色代碼已存在")

        # 新增角色（自訂角色 is_system = false）
        query = """
            INSERT INTO roles (name, display_name, description, is_system)
            VALUES (%s, %s, %s, false)
            RETURNING id, name, display_name, description, is_system, created_at, updated_at
        """
        cur.execute(query, (data.name, data.display_name, data.description))
        role = cur.fetchone()

        conn.commit()

        return {
            **dict(role),
            "permission_count": 0,
            "user_count": 0
        }

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"新增角色失敗: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    data: RoleUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    更新角色資料

    注意：
    - 不允許修改角色代碼（name）
    - 可以更新顯示名稱、說明和權限
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 檢查角色是否存在
        cur.execute("SELECT id, is_system FROM roles WHERE id = %s", (role_id,))
        role = cur.fetchone()

        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")

        # 更新基本資料
        updates = []
        params = []

        if data.display_name is not None:
            updates.append("display_name = %s")
            params.append(data.display_name)

        if data.description is not None:
            updates.append("description = %s")
            params.append(data.description)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(role_id)

            query = f"""
                UPDATE roles
                SET {', '.join(updates)}
                WHERE id = %s
            """
            cur.execute(query, params)

        # 更新權限（如果提供）
        if data.permission_ids is not None:
            # 刪除現有權限
            cur.execute("DELETE FROM role_permissions WHERE role_id = %s", (role_id,))

            # 插入新權限
            if data.permission_ids:
                for permission_id in data.permission_ids:
                    cur.execute("""
                        INSERT INTO role_permissions (role_id, permission_id)
                        VALUES (%s, %s)
                        ON CONFLICT (role_id, permission_id) DO NOTHING
                    """, (role_id, permission_id))

        conn.commit()

        # 重新查詢角色資料
        cur.execute("""
            SELECT
                r.id, r.name, r.display_name, r.description, r.is_system,
                r.created_at, r.updated_at,
                COUNT(DISTINCT rp.permission_id) as permission_count,
                COUNT(DISTINCT ar.admin_id) as user_count
            FROM roles r
            LEFT JOIN role_permissions rp ON r.id = rp.role_id
            LEFT JOIN admin_roles ar ON r.id = ar.role_id
            WHERE r.id = %s
            GROUP BY r.id
        """, (role_id,))

        updated_role = cur.fetchone()

        return updated_role

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"更新角色失敗: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    刪除角色

    注意：
    - 不能刪除系統角色
    - 刪除角色會同時刪除相關的權限關聯和用戶關聯（CASCADE）
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 檢查角色是否存在
        cur.execute("SELECT id, is_system, name FROM roles WHERE id = %s", (role_id,))
        role = cur.fetchone()

        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")

        # 不允許刪除系統角色
        if role['is_system']:
            raise HTTPException(status_code=403, detail="不能刪除系統角色")

        # 刪除角色
        cur.execute("DELETE FROM roles WHERE id = %s", (role_id,))

        conn.commit()

        return {"message": f"角色 '{role['name']}' 已刪除"}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"刪除角色失敗: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.get("/permissions/all")
async def get_all_permissions(current_user: dict = Depends(get_current_user)):
    """
    獲取所有可用的權限列表（用於權限選擇器）

    按資源分組返回
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 查詢所有權限
        cur.execute("""
            SELECT id, name, display_name, resource, action, description
            FROM permissions
            ORDER BY resource, action
        """)

        all_permissions = cur.fetchall()

        # 按資源分組
        grouped = {}
        for perm in all_permissions:
            resource = perm['resource']
            if resource not in grouped:
                grouped[resource] = []
            grouped[resource].append(dict(perm))

        # 轉換為列表格式
        result = []
        resource_icons = {
            'knowledge': '📚',
            'intent': '🎯',
            'test': '🧪',
            'vendor': '🏢',
            'sop': '📄',
            'config': '⚙️',
            'document': '📝',
            'admin': '👤',
            'role': '🔐'
        }

        resource_names = {
            'knowledge': '知識庫管理',
            'intent': '意圖管理',
            'test': '測試與回測',
            'vendor': '業者管理',
            'sop': '平台 SOP',
            'config': '配置管理',
            'document': '文檔處理',
            'admin': '管理員管理',
            'role': '角色管理'
        }

        for resource, permissions in grouped.items():
            result.append({
                'resource': resource,
                'title': resource_names.get(resource, resource),
                'icon': resource_icons.get(resource, '📦'),
                'permissions': permissions
            })

        return result

    finally:
        cur.close()
        conn.close()
