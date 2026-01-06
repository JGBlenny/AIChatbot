"""
認證相關路由
提供登入、登出、獲取當前用戶等 API
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os

from auth_utils import verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/api/auth", tags=["認證"])

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

class LoginRequest(BaseModel):
    """登入請求"""
    username: str
    password: str

class LoginResponse(BaseModel):
    """登入回應"""
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserResponse(BaseModel):
    """用戶資料回應"""
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    is_active: bool

# ========== 認證依賴函數 ==========

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    驗證 JWT token 並返回當前用戶

    用途：作為 FastAPI dependency，保護需要認證的 API

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token = credentials.credentials

    # 解碼 token
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 從資料庫獲取用戶
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, email, full_name, is_active FROM admins WHERE username = %s",
                (username,)
            )
            user = cur.fetchone()

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user['is_active']:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is disabled",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return dict(user)
    finally:
        conn.close()

# ========== API 端點 ==========

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    管理員登入

    Args:
        request: 包含 username 和 password

    Returns:
        access_token: JWT token
        token_type: "bearer"
        user: 用戶資料

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 查詢用戶
            cur.execute(
                "SELECT id, username, password_hash, email, full_name, is_active FROM admins WHERE username = %s",
                (request.username,)
            )
            user = cur.fetchone()

            # 驗證用戶存在
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="帳號或密碼錯誤",
                )

            # 驗證密碼
            if not verify_password(request.password, user['password_hash']):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="帳號或密碼錯誤",
                )

            # 驗證帳號是否啟用
            if not user['is_active']:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="帳號已停用",
                )

            # 更新最後登入時間
            cur.execute(
                "UPDATE admins SET last_login_at = %s WHERE id = %s",
                (datetime.now(), user['id'])
            )
            conn.commit()

            # 生成 JWT token
            access_token = create_access_token(data={"sub": user['username']})

            # 返回登入結果
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "email": user['email'],
                    "full_name": user['full_name'],
                    "is_active": user['is_active']
                }
            }
    finally:
        conn.close()

@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """
    管理員登出

    Note: JWT 是無狀態的，實際登出由前端清除 token 完成
          這個端點主要用於記錄登出事件（未來可擴展）

    Returns:
        成功訊息
    """
    return {"message": "登出成功"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """
    獲取當前登入用戶資料

    需要在 Authorization header 中提供有效的 JWT token

    Returns:
        當前用戶資料
    """
    return user

@router.get("/health")
async def auth_health_check():
    """
    認證服務健康檢查

    Returns:
        服務狀態
    """
    return {"status": "ok", "service": "auth"}
