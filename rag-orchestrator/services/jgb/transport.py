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
import os
import re
from typing import Any, Literal, Optional, Protocol, TypedDict

import httpx

from services.jgb.contract_fixtures import (
    EXTERNAL_CONTRACT_FIELDS,
    INTERNAL_CONTRACT_FIELDS,
    project_contract,
)
from services.jgb.estate_fixtures import (
    ALLOWED_SORT_FIELDS as ESTATE_ALLOWED_SORT_FIELDS,
    DEFAULT_PER_PAGE as ESTATE_DEFAULT_PER_PAGE,
    EXTERNAL_ESTATE_FIELDS,
    INTERNAL_ESTATE_FIELDS,
    MAX_PER_PAGE as ESTATE_MAX_PER_PAGE,
    build_contract_required_fields,
    project_estate,
)
from services.jgb.fixtures import EXTERNAL_BILL_FIELDS
from services.jgb.repair_fixtures import repair_categories

logger = logging.getLogger(__name__)

# transport 層對外的降級訊息（原位於 jgb_system_api，隨 _send 一併下移）
FALLBACK_MESSAGE = "目前無法查詢資料，請稍後再試或聯繫您的管理師。"

HttpMethod = Literal["GET", "POST", "PATCH"]


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


class UnsupportedMockParameterError(TransportError):
    """production 會據以過濾、但替身**無法忠實模擬**的參數。

    ⚠️ 一律 raise，**不得靜默忽略**——靜默忽略等於替身自行捏造一個答案，
    而呼叫端會把它當成事實（`viewer_user_id` 舊行為即為此類）。
    """


class UnexpectedRealNetworkError(TransportError):
    """在 mock 模式下走到了真實網路路徑。

    目前唯一觸發點：`use_mock=True` 但未裝配 mock transport。
    """


class RecordingTransport:
    """出向參數斷言鉤子（agentic-mcp-orchestration 任務 1.5）。

    包一層 `Transport` 實作，`send()` 前先把 `(method, path, params)` 追加到
    `self.calls`，再原樣轉呼叫 `inner`——inner 拋的例外（例如
    `JGBMockTransport` 對 `viewer_user_id` 的 `UnsupportedMockParameterError`）
    原樣往外傳，⛔ 不吞、不放寬：本類**只驗證「有沒有轉發」**，
    不改變 inner 的任何行為（含大聲失敗）。
    """

    def __init__(self, inner: Transport) -> None:
        self.inner = inner
        self.calls: "list[tuple[HttpMethod, str, Optional[dict[str, Any]]]]" = []

    async def send(
        self, method: HttpMethod, path: str, *,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> TransportResponse:
        self.calls.append((method, path, params))
        return await self.inner.send(method, path, params=params, data=data)


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
    ("GET", "/api/external/v1/estates", "estates"),
    ("GET", "/api/external/v1/estates/{estate_id}", "estate_detail"),
    ("GET", "/api/external/v1/meters", "meters"),
    ("GET", "/api/external/v1/roles/{role_id}/members", "team_members"),
    ("GET", "/api/external/v1/roles/{role_id}/members/{user_id}/permissions",
     "member_permissions"),
    ("GET", "/api/external/v1/repairs", "repairs"),
    ("GET", "/api/external/v1/repairs/categories", "repair_categories"),
    ("POST", "/api/external/v1/repairs", "create_repair"),
    ("POST", "/agent/v1/bills", "create_bill"),
    ("POST", "/agent/v1/contracts", "create_contract"),
    ("POST", "/agent/v1/estates", "create_estate"),
    ("PATCH", "/agent/v1/bills/{bill_id}", "patch_bill"),
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
MIGRATED_ENDPOINTS: "frozenset[str]" = frozenset({
    "bills", "bill_detail", "contracts",
    "estates", "estate_detail", "meters",
    "team_members", "member_permissions",
    "repairs", "repair_categories", "create_repair",
    "create_bill", "create_contract", "create_estate", "patch_bill",
})

#: 寫入路徑端點（`MOCK_FAIL_NEXT_WRITE` 失敗注入的作用範圍；讀端點不受影響）。
WRITE_ENDPOINTS: "frozenset[str]" = frozenset({
    "create_bill", "create_contract", "create_estate", "create_repair", "patch_bill",
})


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
                 contract_fixtures: Optional[Any] = None, *,
                 estate_fixtures: Optional[Any] = None,
                 meter_fixtures: Optional[Any] = None,
                 team_fixtures: Optional[Any] = None,
                 repair_fixtures: Optional[Any] = None) -> None:
        #: fixture 表由 4.4 提供；未裝配時「已遷移」端點一律 `MissingFixtureError`
        self.fixtures = fixtures
        #: 合約 fixture（transport-extension）；未裝配時 contracts 亦為 `MissingFixtureError`
        self.contract_fixtures = contract_fixtures
        #: 物件／電表／團隊成員／修繕 fixture（transport-extension-full-coverage）——
        #: 皆為選用；未裝配時對應端點一律 `MissingFixtureError`，不得靜默降級。
        self.estate_fixtures = estate_fixtures
        self.meter_fixtures = meter_fixtures
        self.team_fixtures = team_fixtures
        self.repair_fixtures = repair_fixtures
        #: 冪等快取：`{(endpoint_key, token): TransportResponse}`——同一 token 重送
        #: 回同一份 receipt、不重複建。存活期＝本 transport 實例的生命週期。
        self._idempotency_cache: "dict[tuple[str, str], TransportResponse]" = {}
        #: 失敗注入旗標（實例屬性，優先於 env）：`True` 時下一個寫入端點呼叫
        #: 回 `{success:false, code:500}` 且狀態不變，用畢自動清除（一次性）。
        self.fail_next_write: bool = False

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
        if endpoint_key in WRITE_ENDPOINTS and self._consume_fail_next_write():
            # 失敗注入（測試工具）：狀態不動，直接短路回 500——旗（實例屬性或
            # env `MOCK_FAIL_NEXT_WRITE=1`）用畢即清，故只影響「下一個」寫入。
            return self._error(500, "模擬寫入失敗（MOCK_FAIL_NEXT_WRITE）")
        if self.fixtures is None:
            raise MissingFixtureError(
                f"endpoint 已遷移但未裝配 fixture 表：{endpoint_key}（{method} {path}）"
            )

        params = params or {}
        data = data or {}
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

        if endpoint_key == "estates":
            self._require(self.estate_fixtures, "estates")
            return self._estates_index(params)
        if endpoint_key == "estate_detail":
            self._require(self.estate_fixtures, "estate_detail")
            estate_id = match_template(
                "/api/external/v1/estates/{estate_id}", path
            )["estate_id"]
            return self._estates_show(estate_id)
        if endpoint_key == "meters":
            self._require(self.meter_fixtures, "meters")
            return self._meters_index(params)
        if endpoint_key == "team_members":
            self._require(self.team_fixtures, "team_members")
            return self._team_members_index(params)
        if endpoint_key == "member_permissions":
            self._require(self.team_fixtures, "member_permissions")
            ids = match_template(
                "/api/external/v1/roles/{role_id}/members/{user_id}/permissions", path
            )
            return self._member_permissions(ids["role_id"], ids["user_id"])
        if endpoint_key == "repairs":
            self._require(self.repair_fixtures, "repairs")
            return self._repairs_index(params)
        if endpoint_key == "repair_categories":
            return self._repair_categories()
        if endpoint_key == "create_repair":
            self._require(self.repair_fixtures, "create_repair")
            return self._with_idempotency("create_repair", data,
                                          lambda: self._create_repair(data))

        if endpoint_key == "create_bill":
            return self._with_idempotency("create_bill", data,
                                          lambda: self._create_bill(data))
        if endpoint_key == "create_contract":
            if self.contract_fixtures is None:
                raise MissingFixtureError("create_contract 已遷移但未裝配合約 fixture 表")
            return self._with_idempotency("create_contract", data,
                                          lambda: self._create_contract(data))
        if endpoint_key == "create_estate":
            self._require(self.estate_fixtures, "create_estate")
            return self._with_idempotency("create_estate", data,
                                          lambda: self._create_estate(data))
        if endpoint_key == "patch_bill":
            bill_id = match_template("/agent/v1/bills/{bill_id}", path)["bill_id"]
            return self._with_idempotency(
                f"patch_bill:{bill_id}", data, lambda: self._patch_bill(bill_id, data))

        raise MissingFixtureError(f"已遷移但無回應實作：{endpoint_key}")

    def _require(self, table: Optional[Any], endpoint_key: str) -> None:
        """已遷移端點各自的 fixture 表未裝配 → `MissingFixtureError`（不得靜默降級）。"""
        if table is None:
            raise MissingFixtureError(
                f"endpoint 已遷移但未裝配對應 fixture 表：{endpoint_key}"
            )

    def _consume_fail_next_write(self) -> bool:
        """檢查並清除失敗注入旗：實例屬性 `self.fail_next_write` 優先於
        env `MOCK_FAIL_NEXT_WRITE=1`；命中即清除（一次性，不影響後續寫入）。
        """
        if self.fail_next_write:
            self.fail_next_write = False
            return True
        if os.getenv("MOCK_FAIL_NEXT_WRITE") == "1":
            os.environ.pop("MOCK_FAIL_NEXT_WRITE", None)
            return True
        return False

    def _with_idempotency(
        self, endpoint_key: str, data: "dict[str, Any]", build: Any,
    ) -> TransportResponse:
        """寫入端點共用的冪等包裝：同 `(endpoint_key, token)` 重送回同一份 receipt。

        ⚠️ `Transport.send()` 沒有 header 通道，`Idempotency-Key` 因此**透過 body**
        傳遞（`idempotency_key` 或 `confirmation_token` 任一鍵）——這是 transport
        協定本身的限制，不是遺漏；真 HTTP 實作對應到 header 的轉譯屬呼叫端責任。
        """
        token = data.get("idempotency_key") or data.get("confirmation_token")
        if not token:
            return build()
        cache_key = (endpoint_key, str(token))
        if cache_key in self._idempotency_cache:
            return self._idempotency_cache[cache_key]
        result = build()
        self._idempotency_cache[cache_key] = result
        return result

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
        * `user_id`：`where('to_user_id', (int) user_id)`（:63-65）——⚠️ `to_user_id`
          **不在 formatContract 投影內**，故它在 fixture 是內部欄位、回應中不得出現；
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

        user_id = params.get("user_id")
        if user_id not in (None, ""):
            rows = [r for r in rows if r.get("to_user_id") == _php_intval(str(user_id))]

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
            "data": [project_contract(r) for r in rows[offset:offset + per_page]],
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

        **兩個 production 有、替身沒有的過濾**（2026-08-25 盤查登記，不得讀成已證）：

        * `viewer_user_id`（:41-47）——經 `ExternalViewerScope` → `VisibleScope::resolve`
          → `Bill::queryThisUser`，依 roleType（owner／agent／biglandlord／tenant）與
          `show_*` 權限旗標，過濾 `owner_role_id`／`issue_target_role_id`／`estate_id`／
          `contract_id`。前兩者**不在 33 欄投影內**，權限表也不在 fixture 射程——
          替身無法「算出」可見性，但可以**照 fixture 的宣告**回答（transport-extension-
          full-coverage）：每筆帳單在 `bill_visibility`（`BillFixtureTable.visible_to()`）
          宣告可見的 `user_id` 清單，宣告過就依宣告過濾；**未宣告的列**仍
          `raise UnsupportedMockParameterError`（誠實紀律：沒有宣告就不假裝答得出來）。
        * `user_id`（:50-55）——production 是
          `whereHas('belongContract', to_user_id = user_id AND active = 1)`。
          ⚠️ **跨域連貫修正（2026-09-08）後現況更新**：帳單已改指向既有 contract
          fixture 的真實 id（678／600），三個 fixture 宇宙不再互不連通——但這
          只解了**資料連貫**，本函式仍未實作 `to_user_id` 過濾邏輯。
          ⚠️ 登記為 **GAP-B1（邏輯缺口，非資料缺口）**：目前**照舊忽略**，
          故「帶了 user_id 仍拿到全部帳單」是替身的缺口、**不是** production
          行為。實作過濾邏輯屬另一個需要授權的 slice（見 transport-migration-inventory.md）。
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

        # ⚠️ viewer_user_id 在其他過濾**之後**才判定：只對「已經是候選」的列
        # 要求宣告過可見性，不因為 fixture 裡某筆不相干的列未宣告就整批拒答。
        viewer_user_id = params.get("viewer_user_id")
        if viewer_user_id not in (None, ""):
            visible_to = getattr(self.fixtures, "visible_to", None)
            if visible_to is None:
                # 舊 fixture 表（未提供 `visible_to()`）：無法忠實模擬，一律拒答。
                raise UnsupportedMockParameterError(
                    "GET /bills 的 viewer_user_id 圈定依賴權限主體（UserData）與非投影欄位，"
                    "替身無法忠實模擬；不得以忽略該參數的結果回答可見性問題。"
                )
            try:
                viewer_int = int(viewer_user_id)
            except (TypeError, ValueError):
                raise UnsupportedMockParameterError(
                    f"viewer_user_id 非合法整數：{viewer_user_id!r}"
                )
            filtered: "list[dict[str, Any]]" = []
            for r in rows:
                declared = visible_to(r["id"])
                if declared is None:
                    raise UnsupportedMockParameterError(
                        f"帳單 {r['id']} 未在 fixture 宣告 viewer 可見性（bill_visibility），"
                        "替身無法忠實模擬；不得以忽略該參數的結果回答可見性問題。"
                    )
                if viewer_int in declared:
                    filtered.append(r)
            rows = filtered

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

    # ── transport-extension-full-coverage：estates／meters／team／repairs ──

    def _estates_index(self, params: "dict[str, Any]") -> TransportResponse:
        """`GET /estates`（`EstateApiController@index`）——邏輯照抄舊方法級 mock
        （`JGBSystemAPI._mock_get_estates`），只是資料來源換成共用 fixture。"""
        rows = self.estate_fixtures.visible_rows()

        role_id = params.get("role_id")
        if role_id:
            # ⚠️ 型別正規化（收案修正）：`create_estate` 寫入時 role_id 原樣存字串，
            # 種子列則是 int——比對前雙邊皆轉字串，否則新建物件（字串 role_id）
            # 永遠比對不到、不會出現在自己 role 的列表裡。
            rows = [e for e in rows if str(e.get("role_id")) == str(role_id)]
        if params.get("user_id") not in (None, ""):
            rows = [e for e in rows if e.get("user_id") == int(params["user_id"])]
        if params.get("status") not in (None, ""):
            rows = [e for e in rows if e.get("status") == int(params["status"])]
        use_for = params.get("use_for")
        if use_for in ("residential", "business", "parking_space"):
            rows = [e for e in rows if e.get("use_for") == use_for]
        for key in ("city_id", "district_id"):
            if params.get(key) not in (None, ""):
                rows = [e for e in rows if e.get(key) == int(params[key])]
        if params.get("rent_min") not in (None, ""):
            rows = [e for e in rows if (e.get("rent") or 0) >= int(params["rent_min"])]
        if params.get("rent_max") not in (None, ""):
            rows = [e for e in rows if (e.get("rent") or 0) <= int(params["rent_max"])]
        keyword = params.get("keyword")
        if keyword:
            rows = [e for e in rows if str(keyword) in str(e.get("title") or "")]

        sort_by = params.get("sort_by")
        if sort_by not in ESTATE_ALLOWED_SORT_FIELDS:
            sort_by = "updated_at"
        descending = str(params.get("sort_direction", "desc")).lower() != "asc"
        rows.sort(key=lambda e: (e.get(sort_by) is None, e.get(sort_by)),
                  reverse=descending)

        page = max(1, int(params.get("page", 1) or 1))
        size = min(ESTATE_MAX_PER_PAGE,
                   max(1, int(params.get("per_page", ESTATE_DEFAULT_PER_PAGE) or 1)))
        total = len(rows)
        total_pages = -(-total // size) if total else 0
        offset = (page - 1) * size
        return {
            "success": True,
            "data": [project_estate(e) for e in rows[offset:offset + size]],
            "pagination": {
                "current_page": page, "per_page": size, "total": total,
                "total_pages": total_pages, "has_more": page < total_pages,
            },
        }

    def _estates_show(self, estate_id: str) -> TransportResponse:
        """`GET /estates/{id}`（`show()` → `formatEstate($estate, true)`）。"""
        try:
            row = self.estate_fixtures.by_id(int(estate_id))
        except (TypeError, ValueError):
            row = None
        if row is None:
            return self._error(404, "物件不存在或未招租刊登中")
        detail = project_estate(row)
        detail.update({"description": None, "traffic": None,
                       "nearby": None, "notes": None})
        detail["contract_required_fields"] = build_contract_required_fields()
        return {"success": True, "data": detail}

    def _meters_index(self, params: "dict[str, Any]") -> TransportResponse:
        """`GET /meters`（`MeterApiController@index`）——`keyword` 比對 `iots.name`
        或綁定物件的 `estate_name`（皆 LIKE）；`estate_id` 走中間表過濾，未綁定者查不到。
        """
        if not params.get("role_id"):
            return self._error(400, "role_id 為必填參數")
        rows = self.meter_fixtures.rows()

        estate_id = params.get("estate_id")
        if estate_id not in (None, ""):
            rows = [m for m in rows if str(m.get("estate_id")) == str(estate_id)]
        keyword = params.get("keyword")
        if keyword:
            kw = str(keyword)
            rows = [m for m in rows
                    if kw in str(m.get("name") or "") or kw in str(m.get("estate_name") or "")]

        total = len(rows)
        return {
            "success": True,
            "data": rows,
            "pagination": {"current_page": 1, "per_page": 200, "total": total,
                           "total_pages": -(-total // 200) if total else 0,
                           "has_more": False},
        }

    def _team_members_index(self, params: "dict[str, Any]") -> TransportResponse:
        """`GET /roles/{role_id}/members`（`TeamMemberApiController@members`）。

        `keyword` 必填（缺→400）；對 email／name 做不分大小寫 contains，email 先判、
        命中即 `match_field='email'`，否則才比對 name；**不回 email／phone 明文**。
        """
        keyword = params.get("keyword")
        if not keyword:
            return self._error(400, "keyword 為必填參數")
        kw = str(keyword).lower()
        data = []
        for m in self.team_fixtures.rows():
            email = str(m.get("email") or "").lower()
            name = str(m.get("name") or "").lower()
            if kw in email:
                field = "email"
            elif kw in name:
                field = "name"
            else:
                continue
            data.append({"member_user_id": m["member_user_id"],
                        "character_id": m["character_id"],
                        "character_name": m["character_name"],
                        "is_owner": m["is_owner"], "match_field": field})
        return {"success": True, "data": data}

    def _member_permissions(self, role_id: str, user_id: str) -> TransportResponse:
        """`GET /roles/{id}/members/{uid}/permissions`。

        `character` 是 `{id, name, display}` 物件（**沒有** `character_name` 鍵）；
        `abilities` 一律 32 鍵；擁有者全 true；查無此成員 → 折疊為 `success:False`。

        ⚠️ `data` 是**單一物件**（真 API 形狀）——`JGBSystemAPI.get_member_permissions`
        自己把它正規化成單元素 list（`[data] if isinstance(data, dict) else []`）；
        本層若在這裡就先包成 list，會被那段正規化誤判成「非 dict」而清空。
        """
        member = self.team_fixtures.by_user_id(user_id)
        if member is None:
            return {"success": False, "data": []}

        abilities = self.team_fixtures.abilities_for(member)
        if member["is_owner"]:
            character = {"id": 0, "name": member["character_name"], "display": None}
        else:
            character = ({"id": member["character_id"], "name": member["character_name"],
                          "display": None} if member["character_id"] else None)
        return {"success": True, "data": {
            "role_id": int(role_id) if str(role_id).isdigit() else role_id,
            "user_id": int(user_id) if str(user_id).isdigit() else user_id,
            "is_member": True, "is_owner": member["is_owner"],
            "character": character, "abilities": abilities,
        }}

    def _repairs_index(self, params: "dict[str, Any]") -> TransportResponse:
        """`GET /repairs`（`RepairApiController@index`）——`role_id` 必填、恆定 `active=1`；
        `is_urgent` 對映 `emergency_status`（語義曾反轉過，不可望文生義）。
        """
        if not params.get("role_id"):
            return self._error(400, "role_id 為必填參數")
        rows = self.repair_fixtures.rows()

        if params.get("status") not in (None, ""):
            rows = [r for r in rows if r["status"] == int(params["status"])]
        if params.get("estate_id") not in (None, ""):
            rows = [r for r in rows if r["estate_id"] == int(params["estate_id"])]
        if params.get("category_id") not in (None, ""):
            rows = [r for r in rows if r["category_id"] == int(params["category_id"])]
        if params.get("is_urgent") not in (None, ""):
            rows = [r for r in rows if r["emergency_status"] == int(params["is_urgent"])]
        keyword = params.get("keyword")
        if keyword:
            rows = [r for r in rows if str(keyword) in str(r.get("estate_title") or "")]

        total = len(rows)
        return {
            "success": True,
            "mapping": {
                "status": {"1": "申請中", "2": "安排修繕", "16": "完成修繕",
                          "32": "結單", "64": "封存"},
                "emergency_status": {"1": "非緊急", "2": "緊急"},
            },
            "data": rows,
            "pagination": {"current_page": 1, "per_page": 50, "total": total,
                           "total_pages": -(-total // 50) if total else 0,
                           "has_more": False},
        }

    def _repair_categories(self) -> TransportResponse:
        return {"success": True, "data": repair_categories()}

    # ── transport-extension-full-coverage：寫入路徑 ─────────────────────────

    def _create_repair(self, data: "dict[str, Any]") -> TransportResponse:
        """`POST /repairs`（`RepairApiController@store`）。"""
        if not data.get("role_id"):
            return self._error(400, "role_id 為必填參數")
        overrides = {
            "estate_id": data.get("estate_id"),
            "category_id": data.get("category_id"),
            "item_id": data.get("item_id"),
            "broken_reason": data.get("broken_reason"),
            "broken_note": data.get("broken_note", ""),
            "emergency_status": data.get("emergency_status", 1),
            "contract_id": data.get("contract_id"),
            "broken_photos": data.get("broken_photos") or [],
            "apply_at": "20260908190000",
            "created_at": "2026-09-08 19:00:00",
            "updated_at": "2026-09-08 19:00:00",
        }
        row = self.repair_fixtures.create(overrides)
        return {"success": True, "data": row}

    def _create_bill(self, data: "dict[str, Any]") -> TransportResponse:
        """`POST /agent/v1/bills`（agent 寫入 demo 端點，非 External API 既有方法）。

        ⚠️ 這不是對 jgb2 既有 controller 的保真——是本刀新增、供 agentic 寫入示範用的
        端點；投影仍受 `assert_external_projection` 約束，不得長出投影外欄位。
        """
        if not data.get("role_id"):
            return self._error(400, "role_id 為必填參數")
        now = "2026-09-08 19:00:00"
        overrides = {k: v for k, v in data.items() if k in EXTERNAL_BILL_FIELDS}
        overrides.setdefault("created_at", now)
        overrides.setdefault("updated_at", now)
        overrides.setdefault("id", max([r["id"] for r in self.fixtures.rows()],
                                       default=0) + 1)
        row = self.fixtures.create(overrides)
        return {"success": True, "data": {"id": row["id"], "created_at": row["created_at"]}}

    def _create_contract(self, data: "dict[str, Any]") -> TransportResponse:
        """`POST /agent/v1/contracts`（agent 寫入 demo 端點）。"""
        if not data.get("role_id"):
            return self._error(400, "role_id 為必填參數")
        now = "2026-09-08 19:00:00"
        allowed = EXTERNAL_CONTRACT_FIELDS | INTERNAL_CONTRACT_FIELDS
        overrides = {k: v for k, v in data.items() if k in allowed}
        overrides.setdefault("created_at", now)
        overrides.setdefault("updated_at", now)
        overrides.setdefault("id", max([r["id"] for r in self.contract_fixtures.rows()],
                                       default=0) + 1)
        row = self.contract_fixtures.create(overrides)
        return {"success": True, "data": {"id": row["id"], "created_at": row["created_at"]}}

    def _create_estate(self, data: "dict[str, Any]") -> TransportResponse:
        """`POST /agent/v1/estates`（agent 寫入 demo 端點）。"""
        if not data.get("role_id"):
            return self._error(400, "role_id 為必填參數")
        now = "2026-09-08 19:00:00"
        allowed = EXTERNAL_ESTATE_FIELDS | INTERNAL_ESTATE_FIELDS
        overrides = {k: v for k, v in data.items() if k in allowed}
        overrides.setdefault("created_at", now)
        overrides.setdefault("updated_at", now)
        overrides.setdefault("id", max([r["id"] for r in self.estate_fixtures.rows()],
                                       default=0) + 1)
        row = self.estate_fixtures.create(overrides)
        return {"success": True, "data": {"id": row["id"], "created_at": row["created_at"]}}

    #: PATCH /agent/v1/bills/{id} 只准改到期日；其他鍵一律 4xx。
    _PATCH_BILL_ALLOWED_KEYS: "frozenset[str]" = frozenset({
        "due_date", "due_date_shift_days", "idempotency_key", "confirmation_token",
    })

    def _patch_bill(self, bill_id: str, data: "dict[str, Any]") -> TransportResponse:
        """`PATCH /agent/v1/bills/{id}`：只准改 `due_date`（對映 `date_expire`）。"""
        foreign = set(data) - self._PATCH_BILL_ALLOWED_KEYS
        if foreign:
            return self._error(422, f"PATCH /bills 僅允許調整到期日，不支援的欄位：{sorted(foreign)}")
        try:
            row = self.fixtures.by_id(int(bill_id))
        except (TypeError, ValueError):
            row = None
        if row is None:
            return self._error(404, "帳單不存在或無權存取")

        before = row["date_expire"]

        def _to_date(ymd: int) -> str:
            s = str(ymd)
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"

        def _from_date(s: str) -> int:
            return int(str(s).replace("-", ""))

        if "due_date" in data:
            after = _from_date(data["due_date"])
        elif "due_date_shift_days" in data:
            import datetime
            d = datetime.date(before // 10000, (before // 100) % 100, before % 100)
            d2 = d + datetime.timedelta(days=int(data["due_date_shift_days"]))
            after = int(d2.strftime("%Y%m%d"))
        else:
            return self._error(422, "PATCH /bills 需帶 due_date 或 due_date_shift_days")

        row["date_expire"] = after
        row["updated_at"] = "2026-09-08 19:00:00"
        return {
            "success": True,
            "data": {
                "id": row["id"],
                "due_date_before": _to_date(before),
                "due_date_after": _to_date(after),
                "updated_at": row["updated_at"],
            },
        }
