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
import re
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
    ("GET", "/api/external/v1/contracts/status-overview", "contracts"),
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


def _php_intval(token: str) -> int:
    """PHP `intval()` 的取前綴數字語義（照抄 production 的 contract_ids 解析）。"""
    import re as _re
    m = _re.match(r"\s*([+-]?\d+)", token or "")
    return int(m.group(1)) if m else 0


# ── 4.3：migration admission gate ─────────────────────────────────────────
#: 已遷移至 transport 層的 **endpoint_key**（migration admission set）。
#: ⚠️ 只放 endpoint identity，**不放 concrete path**、不再做一次樣板比對——
#:    endpoint identity 的唯一權威是 4.2 的 `resolve_endpoint`。
MIGRATED_ENDPOINTS: "frozenset[str]" = frozenset({"bills", "bill_detail", "contracts"})


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

    #: 分頁常數（`BillApiController:13-14`）
    DEFAULT_PER_PAGE: int = 50
    MAX_PER_PAGE: int = 200

    #: `sort_by` 白名單（`BillApiController:88`）——不在其中者回退 `created_at`
    ALLOWED_SORT_FIELDS: "frozenset[str]" = frozenset({
        "date_expire", "created_at", "total", "updated_at",
    })

    #: `getMapping()` 逐鍵（`BillApiController:173-197`）
    MAPPING: "dict[str, dict[int, str]]" = {
        "status": {1: "待發送", 2: "待繳費", 8: "待對帳", 16: "已繳費",
                   32: "排定發送", 64: "已失效"},
        "invoice_status": {0: "未開發票", 1: "已開發票", 2: "發票異常"},
        "type": {1: "一般租金", 2: "點退", 3: "新增帳單",
                 4: "罰款", 5: "儲值", 6: "押金設算息"},
    }

    def __init__(self, fixtures: Optional[Any] = None,
                 contract_fixtures: Optional[Any] = None) -> None:
        #: fixture 表由 4.4 提供；未裝配時「已遷移」端點一律 `MissingFixtureError`
        self.fixtures = fixtures
        #: 合約 fixture（transport-extension）；未裝配時 contracts 亦為 `MissingFixtureError`
        self.contract_fixtures = contract_fixtures

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

        params = params or {}
        if endpoint_key == "bills":
            return self._bills_index(params)
        if endpoint_key == "contracts":
            if self.contract_fixtures is None:
                raise MissingFixtureError("contracts 已遷移但未裝配合約 fixture 表")
            return self._contracts_index(params)
        if endpoint_key == "bill_detail":
            bill_id = match_template(
                "/api/external/v1/bills/{bill_id}", path
            )["bill_id"]                                    # 4.2 已保證命中
            return self._bills_show(bill_id, params)
        raise MissingFixtureError(f"已遷移但無回應實作：{endpoint_key}")

    # ── 4.5：依真 API **實際存在**的參數過濾 ──────────────────────────────
    @staticmethod
    def _error(code: int, message: str) -> TransportResponse:
        """對齊 `errorResponse()`（EstateApiController:560-569）。"""
        return {"success": False, "error": {"code": code, "message": message}}

    def _contracts_index(self, params: "dict[str, Any]") -> TransportResponse:
        """`GET /contracts/status-overview`（`ContractApiController@index`）。

        **已對照 jgb2 原始碼**（2026-08-25 M2 audit），逐條照抄其實際行為：

        * `role_id` 必填，缺 → 400（:23-25）；
        * 恆加 `active=1` 與 `is_newest=1` 兩條 where（:51-52）；
        * `contract_ids`：`array_map('intval', explode(','))` → `whereIn('id')`（:67-70）——
          **`intval` 語義**：取前綴數字，無數字得 0（故 "abc" 變 0、匹配不到）；
        * `keyword`：先跳脫 `%`／`_`，再 `title LIKE '%kw%'`（:72-75）——
          ⚠️ **只比 `title`，不含 `address`**（本 mock 首版誤加 address，M2 已修）；
        * `orderBy('id','desc')`（:77）；
        * 分頁：`total_pages` 在 total=0 時為 **0**、`has_more = page < total_pages`（:80-101）。
        """
        if not params.get("role_id"):
            return self._error(400, "role_id 為必填參數")

        rows = [r for r in self.contract_fixtures.rows()
                if r.get("active") == 1 and r.get("is_newest") == 1]

        raw_ids = params.get("contract_ids")
        if raw_ids not in (None, ""):
            wanted = {_php_intval(t) for t in str(raw_ids).split(",")}
            rows = [r for r in rows if r["id"] in wanted]

        keyword = params.get("keyword")
        if keyword not in (None, ""):
            kw = str(keyword)
            rows = [r for r in rows if kw in str(r.get("title") or "")]

        rows.sort(key=lambda r: r["id"], reverse=True)

        page = max(1, int(params.get("page", 1) or 1))
        per_page = min(self.MAX_PER_PAGE,
                       max(1, int(params.get("per_page", self.DEFAULT_PER_PAGE) or 1)))
        total = len(rows)
        total_pages = -(-total // per_page) if total > 0 else 0
        offset = (page - 1) * per_page
        return {
            "success": True,
            "mapping": getattr(self.contract_fixtures, "MAPPING", {}),
            "data": rows[offset:offset + per_page],
            "pagination": {"current_page": page, "per_page": per_page, "total": total,
                           "total_pages": total_pages, "has_more": page < total_pages},
        }

    def _bills_index(self, params: "dict[str, Any]") -> TransportResponse:
        """`GET /bills`（`BillApiController@index:19-125`）。

        ⚠️ 逐條對齊 production，**包含它的怪癖**——mock 的價值在保真，不在「比較合理」：

        * `month` 非法格式 → **靜默忽略**（不報錯）：production 只在 `preg_match` 命中時才加條件（:78-85）；
        * `month` 區間為 ``YYYYMM01 ~ YYYYMM31`` **inclusive**（:81-83），
          **不是** ``[月初, 次月初)``——2 月同樣用 31，這是 production 的實際行為；
        * `sort_by` 不在白名單 → **回退 `created_at`**（非拒絕，:88-96）；
        * `sort_direction` 非 asc/desc → 回退 `desc`。
        """
        if not params.get("role_id"):
            return self._error(400, "role_id 為必填參數")

        rows = list(self.fixtures.rows())

        for key in ("contract_id", "status", "type"):
            if params.get(key) not in (None, ""):
                rows = [r for r in rows if r[key] == int(params[key])]
        if params.get("bill_id") not in (None, ""):
            rows = [r for r in rows if r["id"] == int(params["bill_id"])]

        month = params.get("month")
        # production：`preg_match('/^\d{4}-\d{2}$/')` 命中才加條件；不命中＝靜默忽略
        if month not in (None, "") and re.fullmatch(r"\d{4}-\d{2}", str(month)):
            ym = int(str(month).replace("-", ""))
            start, end = ym * 100 + 1, ym * 100 + 31
            rows = [r for r in rows if start <= r["date_expire"] <= end]

        sort_by = params.get("sort_by")
        if sort_by not in self.ALLOWED_SORT_FIELDS:
            sort_by = "created_at"
        direction = str(params.get("sort_direction", "desc")).lower()
        if direction not in ("asc", "desc"):
            direction = "desc"
        rows.sort(key=lambda r: r[sort_by], reverse=(direction == "desc"))

        page = max(1, int(params.get("page", 1) or 1))
        per_page = min(self.MAX_PER_PAGE,
                       max(1, int(params.get("per_page", self.DEFAULT_PER_PAGE) or 1)))
        total = len(rows)
        total_pages = -(-total // per_page) if total else 0
        offset = (page - 1) * per_page

        return {
            "success": True,
            "mapping": self.MAPPING,
            "data": rows[offset:offset + per_page],
            "pagination": {
                "current_page": page, "per_page": per_page, "total": total,
                "total_pages": total_pages, "has_more": page < total_pages,
            },
        }

    def _bills_show(self, bill_id: str, params: "dict[str, Any]") -> TransportResponse:
        """`GET /bills/{bill_id}`（`BillApiController@show:203-231`）。

        ⚠️ **404 的資訊折疊必須照抄**：production 對「不存在」與「無權存取」回**同一句**
        「帳單不存在或無權存取」（:230）。
        mock **不得**偷偷拆成 404-not-found ／ 403-no-access——
        否則上層會取得 production 根本沒有的辨識能力（同 N1 的 E5 結論：404 仍是 ambiguous fact）。

        ⚠️ **無 pagination**：detail 回應不帶 `pagination`（對齊 :232-260 的回應組裝）。
        """
        if not params.get("role_id"):
            return self._error(400, "role_id 為必填參數")
        try:
            row = self.fixtures.by_id(int(bill_id))
        except (TypeError, ValueError):
            row = None
        if row is None:
            return self._error(404, "帳單不存在或無權存取")
        return {"success": True, "mapping": self.MAPPING, "data": row}
