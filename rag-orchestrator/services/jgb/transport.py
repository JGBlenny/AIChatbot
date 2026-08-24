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
    """`(method, path)` 無法解析為 **唯一** logical endpoint。

    `reason` 目前有兩個值：

    * ``"ambiguous"`` —— 有多於一個樣板同時命中同一條 concrete path（4.2 拋出）；
    * ``"no_match"``  —— `resolve_endpoint` 回 `None`，由 transport 邊界拋出（4.3）。

    ⚠️ `resolve_endpoint` **本身**對查無仍回 `None`（design 三態決定表），
    「回 None → 拋例外」的決定發生在 `JGBMockTransport.send`，
    使 endpoint identity 與 admission 兩層維持分離。
    """

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


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


# ── 4.2：template endpoint 解析 ────────────────────────────────────────────
def match_template(template: str, path: str) -> Optional[dict[str, str]]:
    """以 **樣板語義** 比對，命中回傳抽出的 path 參數，未命中回 `None`。

    ⚠️ 刻意與 resolver 分開：`match_template` 只回答「這條 path 是否符合這個樣板、
    以及各 placeholder 吃到什麼」，不知道 endpoint 的存在。
    如此 adapter 測試日後能直接驗「`bill_id` 確實是從 concrete path 解析出來的」，
    而不只是「有命中 detail 路由」。

    規則（逐條對應驗收）：

    1. 靜態段必須**完全相同**；
    2. `{name}` 只吃**單一** path segment——`{bill_id}` 不得匹配 ``123/456``；
    3. 段數不同一律不匹配；
    4. 空 segment（如 ``/bills/``）不算有效 placeholder 值。

    ⚠️ **不得**改成 `path in WHITELIST` 或任何等價的 literal membership 判定——
    detail path 實際為 ``/api/external/v1/bills/12345``，字面永遠不會命中樣板。
    """
    t_segs = template.strip("/").split("/")
    p_segs = path.strip("/").split("/")
    if len(t_segs) != len(p_segs):
        return None

    extracted: dict[str, str] = {}
    for t, p in zip(t_segs, p_segs):
        if t.startswith("{") and t.endswith("}"):
            if not p:                      # `/bills/` → 空值不算命中
                return None
            extracted[t[1:-1]] = p
        elif t != p:                       # 靜態段須完全相同
            return None
    return extracted


#: 路由表：`(method, path template, endpoint_key)`。
#: 契約基準 design.md §元件 3（對齊 jgb2 `External\BillApiController@index/@show`）。
ROUTES: "tuple[tuple[HttpMethod, str, str], ...]" = (
    ("GET", "/api/external/v1/bills", "bills"),
    ("GET", "/api/external/v1/bills/{bill_id}", "bill_detail"),
)


def resolve_endpoint(method: HttpMethod, path: str) -> Optional[str]:
    """以樣板比對解析 `endpoint_key`；查無對應回 `None`。

    ⚠️ **歧義即失敗**：若多於一個樣板同時命中，`raise UnresolvedEndpointError`
    （`reason="ambiguous"`），**不得**取宣告順序的第一筆——
    否則 correctness 會被綁在 registry 的 incidental ordering 上。

    ⚠️ **本函式只回答 endpoint identity，不回答「可否在 mock 執行」**：
    「已遷移」（`MIGRATED_ENDPOINTS`）屬 4.3 的責任，刻意不在此消費，
    避免 `resolved == safe-to-mock` 再次變成隱性 fallback。
    """
    hits = [key for m, template, key in ROUTES
            if m == method and match_template(template, path) is not None]
    if len(hits) > 1:
        raise UnresolvedEndpointError(
            f"多個樣板同時命中 {method} {path}：{hits}", reason="ambiguous"
        )
    return hits[0] if hits else None


# ── 4.3：migration admission gate ─────────────────────────────────────────
#: 已遷移至 transport 層的 **endpoint_key**（migration admission set）。
#: ⚠️ 只放 endpoint identity，**不放 concrete path**、不再做一次樣板比對——
#:    endpoint identity 的唯一權威是 4.2 的 `resolve_endpoint`。
MIGRATED_ENDPOINTS: "frozenset[str]" = frozenset({"bills", "bill_detail"})


class JGBMockTransport:
    """契約保真替身（4.3 只做 admission gate；回應建構屬 4.5）。

    三態決定（`use_mock` 為真且請求抵達本類）：

    ==========================  ==========================  =========================
    `resolve_endpoint`          `∈ MIGRATED_ENDPOINTS`      行為
    ==========================  ==========================  =========================
    回 `None`                   —                           `UnresolvedEndpointError`
    命中                        ❌                          `UnmigratedMockEndpointError`
    命中                        ✅                          依契約回應（4.5）
    ==========================  ==========================  =========================

    ⚠️ **上述任何一種失敗都 SHALL NOT fallback 至真實 HTTP。**
    本類**不持有** real transport、也不 import 它——
    「跑到真網路」在此**結構上不可達**，而不只是靠沒有寫那行 fallback。
    """

    def __init__(self, fixtures: Optional[Any] = None) -> None:
        #: fixture 表由 4.4 提供；未裝配時「已遷移」端點一律 `MissingFixtureError`
        self.fixtures = fixtures

    async def send(
        self, method: HttpMethod, path: str, *,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> TransportResponse:
        endpoint_key = resolve_endpoint(method, path)   # 歧義 → ambiguous（4.2）

        if endpoint_key is None:
            raise UnresolvedEndpointError(
                f"無法解析為任何 logical endpoint：{method} {path}", reason="no_match"
            )
        if endpoint_key not in MIGRATED_ENDPOINTS:
            raise UnmigratedMockEndpointError(
                f"endpoint 尚未遷移至 mock transport：{endpoint_key}（{method} {path}）"
            )
        if self.fixtures is None:
            raise MissingFixtureError(
                f"endpoint 已遷移但未裝配 fixture 表：{endpoint_key}（{method} {path}）"
            )
        raise NotImplementedError("回應建構屬任務 4.5")
