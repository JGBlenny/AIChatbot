"""JGB External API 的 HTTP transport 契約（任務 4.1）。

`JGBSystemAPI` **只依賴本模組的 `Transport` Protocol**，不直接碰 httpx——
如此 mock 與 real 兩個實作共用**同一份 caller-facing 契約**，
替身才不會長成「測試專用 API」（R4.1、R9.4）。

⚠️ 本檔**只定義契約與 real 實作**。endpoint 樣板解析（4.2）、
未遷移端點的 fail loudly（4.3）、fixture 表（4.4）與 mock 回應（4.5）
**不在本任務內**——本檔僅先把失敗型別**宣告**好，供後續任務使用。

契約基準：`.kiro/specs/conversational-routing-execution/design.md` §元件 3，
外殼對齊 jgb2 `External\\BillApiController@index/@show`。
"""

import logging
from typing import Any, Literal, Optional, Protocol, TypedDict

import httpx

logger = logging.getLogger(__name__)

# transport 層對外的降級訊息（原位於 jgb_system_api，隨 _send 一併下移）
FALLBACK_MESSAGE = "目前無法查詢資料，請稍後再試或聯繫您的管理師。"

HttpMethod = Literal["GET", "POST"]


class Pagination(TypedDict):
    """分頁外殼（對齊 External API 回應）。"""
    current_page: int
    per_page: int
    total: int
    total_pages: int
    has_more: bool


class TransportResponse(TypedDict, total=False):
    """External API 回應外殼。

    ⚠️ `total=False`：真 API 各端點回傳的鍵不一致（list 有 pagination、
    detail 沒有；錯誤時只有 success/error），故全部為選用鍵——
    **不得**為了讓型別好看就在 mock 端補真 API 不存在的鍵。
    """
    success: bool
    mapping: dict[str, dict[str, str]]
    data: "list[dict[str, Any]] | dict[str, Any]"
    pagination: Pagination
    error: dict[str, Any]


class Transport(Protocol):
    """HTTP transport 契約；real 與 mock 兩實作共用。

    ⚠️ 實作**不得**讓底層例外（httpx 等）逸出到呼叫端——
    呼叫端只看得到 `TransportResponse`，或本模組定義的 `TransportError` 子類。
    """

    async def send(
        self, method: HttpMethod, path: str, *,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> TransportResponse:
        ...


# ── 失敗型別（本任務只宣告，供 4.2／4.3 使用）────────────────────────────
class TransportError(Exception):
    """transport 契約層的失敗基底。

    ⚠️ 這些是**harness fidelity 失效**，不是可降級的業務錯誤：
    它們必須炸出來，不得被轉成「查無資料」之類的正常回應。
    """


class UnresolvedEndpointError(TransportError):
    """`(method, path)` 無法解析為任何 logical endpoint（4.2 使用）。"""


class UnmigratedMockEndpointError(TransportError):
    """endpoint 尚未遷移至 mock transport（4.3 使用）。

    ⚠️ 此時 **SHALL NOT** fallback 至真實 HTTP——
    靜默 fallback 的失效模式是 integration 測試對 jgb2 發出真請求。
    """


class MissingFixtureError(TransportError):
    """endpoint 已遷移，但 fixture 表缺對應資料（4.4／4.5 使用）。"""


class UnexpectedRealNetworkError(TransportError):
    """在 mock 模式下走到了真實網路路徑。

    目前唯一觸發點：`use_mock=True` 但未裝配 mock transport。
    """


class RealHttpTransport:
    """真 HTTP 實作：只負責送出請求與把傳輸層失敗轉成契約外殼。

    ⚠️ 本類**不承擔任何 rag 端邏輯**（不做參數推導、不做結果過濾）——
    那些屬於 `JGBSystemAPI` 與各面向 formatter。
    """

    def __init__(self, base_url: str, api_key: str, timeout: float) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

    @staticmethod
    def _fallback_response() -> TransportResponse:
        return {"success": False, "error": {"code": 500, "message": FALLBACK_MESSAGE}}

    async def send(
        self, method: HttpMethod, path: str, *,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> TransportResponse:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method, url,
                    params=params, json=data,
                    headers=self._headers(),
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            logger.error(f"JGB API {method} 逾時: {url} - {e}")
            return self._fallback_response()
        except httpx.HTTPError as e:
            logger.error(f"JGB API {method} 錯誤: {url} - {e}")
            return self._fallback_response()
