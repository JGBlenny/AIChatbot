"""
統一錯誤處理中介軟體

功能：
- 捕獲所有異常並格式化為標準錯誤回應
- 映射自訂異常到適當的 HTTP 狀態碼
- 記錄錯誤到日誌系統
- 提供繁體中文錯誤訊息
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import traceback
from typing import Dict, Any

# Import custom exceptions
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.knowledge_completion_loop.models import (
    KnowledgeCompletionError,
    InvalidStateError,
    LoopNotFoundError,
    BudgetExceededError,
    ErrorCategory
)
from services.knowledge_completion_loop.async_execution_manager import ConcurrentExecutionError


# 錯誤碼映射表
ERROR_CODE_MAPPING = {
    400: "BAD_REQUEST",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "UNPROCESSABLE_ENTITY",
    500: "INTERNAL_SERVER_ERROR",
    503: "SERVICE_UNAVAILABLE"
}


def get_error_code(status_code: int) -> str:
    """取得錯誤碼"""
    return ERROR_CODE_MAPPING.get(status_code, "UNKNOWN_ERROR")


def format_error_response(
    status_code: int,
    message: str,
    details: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    格式化標準錯誤回應

    Args:
        status_code: HTTP 狀態碼
        message: 錯誤訊息
        details: 錯誤詳情（選填）

    Returns:
        標準錯誤格式 {error_code, message, details, timestamp}
    """
    response = {
        "error_code": get_error_code(status_code),
        "message": message,
        "timestamp": datetime.now().isoformat()
    }

    if details:
        response["details"] = details

    return response


def map_exception_to_status_code(exc: Exception) -> int:
    """
    映射異常到 HTTP 狀態碼

    Args:
        exc: 異常實例

    Returns:
        HTTP 狀態碼
    """
    # InvalidStateError → 409 Conflict
    if isinstance(exc, InvalidStateError):
        return 409

    # LoopNotFoundError → 404 Not Found
    if isinstance(exc, LoopNotFoundError):
        return 404

    # ConcurrentExecutionError → 409 Conflict
    if isinstance(exc, ConcurrentExecutionError):
        return 409

    # BudgetExceededError → 422 Unprocessable Entity
    if isinstance(exc, BudgetExceededError):
        return 422

    # HTTPException → 使用原狀態碼
    if isinstance(exc, HTTPException):
        return exc.status_code

    # 其他 KnowledgeCompletionError
    if isinstance(exc, KnowledgeCompletionError):
        # 根據 category 決定狀態碼
        if exc.category == ErrorCategory.VALIDATION_ERROR:
            return 400
        elif exc.category == ErrorCategory.BUSINESS_LOGIC_ERROR:
            return 422
        else:
            return 500

    # 其他異常 → 500 Internal Server Error
    return 500


async def error_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    錯誤處理函數

    Args:
        request: FastAPI Request
        exc: 異常實例

    Returns:
        JSONResponse 標準錯誤回應
    """
    # 決定 HTTP 狀態碼
    status_code = map_exception_to_status_code(exc)

    # 提取錯誤訊息
    if isinstance(exc, HTTPException):
        message = exc.detail
        details = None
    elif isinstance(exc, KnowledgeCompletionError):
        message = exc.message
        details = exc.details
    elif isinstance(exc, ConcurrentExecutionError):
        message = str(exc)
        details = None
    else:
        # 一般異常（不暴露內部錯誤詳情）
        message = "系統發生內部錯誤，請稍後再試"
        details = None

    # 記錄錯誤日誌
    log_error(request, exc, status_code)

    # 格式化錯誤回應
    error_response = format_error_response(status_code, message, details)

    return JSONResponse(
        status_code=status_code,
        content=error_response
    )


def log_error(request: Request, exc: Exception, status_code: int):
    """
    記錄錯誤到日誌

    Args:
        request: FastAPI Request
        exc: 異常實例
        status_code: HTTP 狀態碼
    """
    error_log = {
        "timestamp": datetime.now().isoformat(),
        "path": request.url.path,
        "method": request.method,
        "status_code": status_code,
        "error_type": type(exc).__name__,
        "error_message": str(exc)
    }

    # 記錄 traceback（僅對 500 錯誤）
    if status_code >= 500:
        error_log["traceback"] = traceback.format_exc()

    # 輸出到 console（生產環境應使用專業日誌系統）
    print(f"[ERROR] {error_log}")


def add_error_handling(app: FastAPI):
    """
    添加錯誤處理中介軟體到 FastAPI 應用

    Args:
        app: FastAPI 應用實例
    """
    @app.exception_handler(Exception)
    async def universal_exception_handler(request: Request, exc: Exception):
        return await error_handler(request, exc)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return await error_handler(request, exc)

    @app.exception_handler(KnowledgeCompletionError)
    async def knowledge_completion_error_handler(request: Request, exc: KnowledgeCompletionError):
        return await error_handler(request, exc)

    @app.exception_handler(ConcurrentExecutionError)
    async def concurrent_execution_error_handler(request: Request, exc: ConcurrentExecutionError):
        return await error_handler(request, exc)
