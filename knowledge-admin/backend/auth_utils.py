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
# ⛔ 不得加回預設值。這支檔進版控，任何硬編碼後備＝簽發金鑰對全世界公開，
# 攻擊者可自簽任意 admin JWT，後台所有 Depends(get_current_user) 保護一併失效。
# 缺值就讓程序起不來（大聲失敗），⛔ 不要靜默退回可預測的字串。
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY 未設。請在 .env 設定強隨機值後重啟；"
        "⛔ 不得在原始碼提供預設值。"
    )
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

