"""
認證工具函數
提供密碼驗證、JWT token 生成與驗證、權限管理
"""
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# 密碼加密配置
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# 資料庫配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "aichatbot_admin")
DB_USER = os.getenv("DB_USER", "aichatbot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "aichatbot_password")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    驗證密碼

    Args:
        plain_password: 明文密碼
        hashed_password: bcrypt 加密的密碼雜湊

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    生成密碼雜湊

    Args:
        password: 明文密碼

    Returns:
        bcrypt 加密的密碼雜湊
    """
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    生成 JWT access token

    Args:
        data: 要編碼到 token 中的資料（通常包含 sub: username）
        expires_delta: token 有效期（預設 24 小時）

    Returns:
        JWT token 字串
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """
    解碼並驗證 JWT token

    Args:
        token: JWT token 字串

    Returns:
        解碼後的 payload，驗證失敗返回 None
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# ==========================================
# 資料庫連線
# ==========================================

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

# ==========================================
# 權限管理函數
# ==========================================

async def get_user_permissions(admin_id: int) -> List[str]:
    """
    查詢用戶的所有權限

    Args:
        admin_id: 管理員 ID

    Returns:
        權限名稱列表，如 ['knowledge:view', 'knowledge:create', ...]
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT p.name
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                JOIN admin_roles ar ON rp.role_id = ar.role_id
                WHERE ar.admin_id = %s
            """, (admin_id,))
            return [row['name'] for row in cur.fetchall()]
    finally:
        conn.close()

async def get_user_roles(admin_id: int) -> List[dict]:
    """
    查詢用戶的所有角色

    Args:
        admin_id: 管理員 ID

    Returns:
        角色列表，如 [{'name': 'super_admin', 'display_name': '超級管理員'}, ...]
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT r.name, r.display_name
                FROM roles r
                JOIN admin_roles ar ON r.id = ar.role_id
                WHERE ar.admin_id = %s
            """, (admin_id,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

async def has_permission(admin_id: int, permission: str) -> bool:
    """
    檢查用戶是否擁有特定權限

    Args:
        admin_id: 管理員 ID
        permission: 權限名稱，如 'knowledge:view'

    Returns:
        True if user has permission, False otherwise
    """
    user_permissions = await get_user_permissions(admin_id)

    # 超級管理員擁有所有權限
    if '*:*' in user_permissions:
        return True

    # 檢查具體權限
    if permission in user_permissions:
        return True

    # 檢查通配符權限（如 knowledge:*）
    if ':' in permission:
        resource, action = permission.split(':', 1)
        if f'{resource}:*' in user_permissions:
            return True

    return False

def require_permission(permission: str):
    """
    創建一個權限檢查依賴

    用法:
    @app.get("/api/knowledge", dependencies=[Depends(require_permission("knowledge:view"))])
    async def list_knowledge():
        # ...

    Args:
        permission: 需要的權限，如 'knowledge:view'

    Returns:
        FastAPI dependency function
    """
    async def permission_checker(user: dict = Depends(lambda: None)):
        """
        權限檢查函數

        注意：需要在使用時注入 get_current_user
        """
        # 這裡暫時返回，實際使用時需要配合 get_current_user
        # 在 routes 中直接使用 get_current_user 並檢查權限
        return user

    return permission_checker
