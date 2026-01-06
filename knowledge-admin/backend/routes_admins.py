"""
管理員帳號管理 API
提供管理員的 CRUD 操作、密碼重設等功能
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, validator
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os
import re

from auth_utils import get_password_hash
from routes_auth import get_current_user

router = APIRouter(prefix="/api/admins", tags=["管理員管理"])

# HTTP Bearer token scheme
security = HTTPBearer()

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

class AdminBase(BaseModel):
    """管理員基礎資料"""
    email: Optional[str] = None
    full_name: Optional[str] = None

class AdminCreate(AdminBase):
    """新增管理員請求"""
    username: str
    password: str

    @validator('username')
    def validate_username(cls, v):
        if not v:
            raise ValueError('帳號不能為空')
        if len(v) < 3 or len(v) > 50:
            raise ValueError('帳號長度必須在 3-50 字元之間')
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('帳號只能包含英數字和底線')
        return v

    @validator('password')
    def validate_password(cls, v):
        if not v:
            raise ValueError('密碼不能為空')
        return v

class AdminUpdate(BaseModel):
    """更新管理員請求"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

    @validator('email')
    def validate_email(cls, v):
        if v is not None and v != '':
            # 簡單的 email 格式驗證
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
                raise ValueError('Email 格式不正確')
        return v

class AdminResponse(BaseModel):
    """管理員回應"""
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class AdminListResponse(BaseModel):
    """管理員列表回應"""
    items: List[AdminResponse]
    total: int
    limit: int
    offset: int

class ResetPasswordRequest(BaseModel):
    """重設密碼請求"""
    new_password: str

    @validator('new_password')
    def validate_password(cls, v):
        if not v:
            raise ValueError('新密碼不能為空')
        return v

class ChangePasswordRequest(BaseModel):
    """修改密碼請求"""
    current_password: str
    new_password: str

    @validator('new_password')
    def validate_password(cls, v):
        if not v:
            raise ValueError('新密碼不能為空')
        return v


# ========== API 端點 ==========

@router.get("", response_model=AdminListResponse)
async def list_admins(
    search: Optional[str] = None,
    is_active: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """
    列出所有管理員

    - **search**: 搜尋關鍵字（搜尋 username, email, full_name）
    - **is_active**: 篩選啟用狀態 (true/false/all)
    - **limit**: 每頁筆數
    - **offset**: 偏移量
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 構建查詢條件
        conditions = []
        params = []

        if search:
            conditions.append("(username ILIKE %s OR email ILIKE %s OR full_name ILIKE %s)")
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern, search_pattern])

        if is_active and is_active != "all":
            conditions.append("is_active = %s")
            params.append(is_active == "true")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 查詢總數
        count_query = f"SELECT COUNT(*) FROM admins WHERE {where_clause}"
        cur.execute(count_query, params)
        total = cur.fetchone()['count']

        # 查詢列表（不返回 password_hash）
        query = f"""
            SELECT id, username, email, full_name, is_active,
                   last_login_at, created_at, updated_at
            FROM admins
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        cur.execute(query, params)
        admins = cur.fetchall()

        return {
            "items": admins,
            "total": total,
            "limit": limit,
            "offset": offset
        }

    finally:
        cur.close()
        conn.close()


@router.get("/{admin_id}", response_model=AdminResponse)
async def get_admin(
    admin_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    獲取單一管理員資料
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        query = """
            SELECT id, username, email, full_name, is_active,
                   last_login_at, created_at, updated_at
            FROM admins
            WHERE id = %s
        """
        cur.execute(query, (admin_id,))
        admin = cur.fetchone()

        if not admin:
            raise HTTPException(status_code=404, detail="管理員不存在")

        return admin

    finally:
        cur.close()
        conn.close()


@router.post("", response_model=AdminResponse, status_code=status.HTTP_201_CREATED)
async def create_admin(
    data: AdminCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    新增管理員

    - **username**: 登入帳號（3-50 字元，只能包含英數字和底線）
    - **password**: 密碼（至少 8 字元，需包含大小寫字母和數字）
    - **email**: Email（選填）
    - **full_name**: 姓名（選填）
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 檢查帳號是否已存在
        cur.execute("SELECT id FROM admins WHERE username = %s", (data.username,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="帳號已存在")

        # 加密密碼
        password_hash = get_password_hash(data.password)

        # 新增管理員
        query = """
            INSERT INTO admins (username, password_hash, email, full_name)
            VALUES (%s, %s, %s, %s)
            RETURNING id, username, email, full_name, is_active,
                      last_login_at, created_at, updated_at
        """
        cur.execute(query, (data.username, password_hash, data.email, data.full_name))
        admin = cur.fetchone()

        conn.commit()

        return admin

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"新增管理員失敗: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.put("/{admin_id}", response_model=AdminResponse)
async def update_admin(
    admin_id: int,
    data: AdminUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    更新管理員資料

    注意：
    - 不允許修改 username（帳號創建後不可變）
    - 不允許在此 API 修改密碼（使用專用的重設密碼 API）
    """
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 檢查管理員是否存在
        cur.execute("SELECT id FROM admins WHERE id = %s", (admin_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="管理員不存在")

        # 構建更新語句
        updates = []
        params = []

        if data.email is not None:
            updates.append("email = %s")
            params.append(data.email)

        if data.full_name is not None:
            updates.append("full_name = %s")
            params.append(data.full_name)

        if data.is_active is not None:
            # 防止停用自己
            if admin_id == current_user["id"] and not data.is_active:
                raise HTTPException(status_code=403, detail="無法停用自己的帳號")
            updates.append("is_active = %s")
            params.append(data.is_active)

        if not updates:
            raise HTTPException(status_code=400, detail="沒有需要更新的欄位")

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(admin_id)

        query = f"""
            UPDATE admins
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, username, email, full_name, is_active,
                      last_login_at, created_at, updated_at
        """
        cur.execute(query, params)
        admin = cur.fetchone()

        conn.commit()

        return admin

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"更新管理員失敗: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.post("/{admin_id}/reset-password")
async def reset_admin_password(
    admin_id: int,
    data: ResetPasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    重設管理員密碼

    注意：
    - 管理員不能重設自己的密碼（必須使用「修改密碼」功能）
    """
    # 防止重設自己的密碼
    if admin_id == current_user["id"]:
        raise HTTPException(status_code=403, detail="無法重設自己的密碼，請使用「修改密碼」功能")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 檢查管理員是否存在
        cur.execute("SELECT id FROM admins WHERE id = %s", (admin_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="管理員不存在")

        # 加密新密碼
        password_hash = get_password_hash(data.new_password)

        # 更新密碼
        query = """
            UPDATE admins
            SET password_hash = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        cur.execute(query, (password_hash, admin_id))

        conn.commit()

        return {"message": "密碼已重設成功"}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"重設密碼失敗: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.delete("/{admin_id}")
async def delete_admin(
    admin_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    刪除管理員（軟刪除，設定 is_active = false）

    注意：
    - 不能停用自己的帳號
    """
    # 防止停用自己
    if admin_id == current_user["id"]:
        raise HTTPException(status_code=403, detail="無法停用自己的帳號")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 檢查管理員是否存在
        cur.execute("SELECT id FROM admins WHERE id = %s", (admin_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="管理員不存在")

        # 軟刪除（設定 is_active = false）
        query = """
            UPDATE admins
            SET is_active = false, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        cur.execute(query, (admin_id,))

        conn.commit()

        return {"message": "管理員已停用"}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"停用管理員失敗: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.post("/me/change-password")
async def change_own_password(
    data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    修改自己的密碼

    需要提供舊密碼驗證
    """
    from auth_utils import verify_password

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 獲取當前用戶的密碼 hash
        cur.execute(
            "SELECT password_hash FROM admins WHERE id = %s",
            (current_user["id"],)
        )
        result = cur.fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="用戶不存在")

        # 驗證舊密碼
        if not verify_password(data.current_password, result["password_hash"]):
            raise HTTPException(status_code=401, detail="舊密碼錯誤")

        # 加密新密碼
        new_password_hash = get_password_hash(data.new_password)

        # 更新密碼
        query = """
            UPDATE admins
            SET password_hash = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        cur.execute(query, (new_password_hash, current_user["id"]))

        conn.commit()

        return {"message": "密碼修改成功"}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"修改密碼失敗: {str(e)}")
    finally:
        cur.close()
        conn.close()
