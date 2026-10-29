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

import calendar
import copy
import datetime
import hashlib
import json
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
from services.jgb.fixture_store import demo_section, demo_visibility
from services.jgb.fixtures import EXTERNAL_BILL_FIELDS, _bill as _bill_defaults
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
        files: Optional[list] = None,
    ) -> TransportResponse:
        """`files`（UD-3）：有值 ⇒ `multipart/form-data`——`data` 是同名表單欄位（值一律字串）、
        `files`＝`[(欄位名, (檔名, 位元組, content_type)), ...]`；`None` ⇒ 現行 JSON body。
        ⚠️ 只有 `JGBSystemAPI._send` 在 `files` 有值時才帶這個參數（既有替身不必實作）。"""
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
        #: 與 `calls` 逐筆平行的 body 紀錄（`bodies[i]` 對應 `calls[i]`；GET 為 `None`）。
        #: 站內幫手 S0（jgb2-req#23）：寫入 body 的身分欄位要能被斷言。
        #: ⛔ `calls` 三元組的形狀不變（既有測試解包 `(method, path, params)`），
        #: body 因此另開屬性，不塞進三元組。存的是深拷貝，事後改動原 dict 不影響紀錄。
        self.bodies: "list[Optional[dict[str, Any]]]" = []
        #: UD-3：與 `calls` 逐筆平行的 multipart 檔案紀錄（`files[i]` 對應 `calls[i]`；JSON 呼叫為 `None`）。
        #: 存 `(欄位名, 檔名, content_type, 位元組)`——只供單元測試斷言送出的檔（⛔ 進任何 log）。
        self.files: "list[Optional[list]]" = []

    async def send(
        self, method: HttpMethod, path: str, *,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        files: Optional[list] = None,
    ) -> TransportResponse:
        self.calls.append((method, path, params))
        self.bodies.append(copy.deepcopy(data))
        if files is None:
            self.files.append(None)
            return await self.inner.send(method, path, params=params, data=data)
        self.files.append([(f, spec[0], spec[2], bytes(spec[1])) for f, spec in files])
        return await self.inner.send(method, path, params=params, data=data, files=files)


class MissingCredentialError(TransportError):
    """真 API transport 建構時憑證為空（agent-write-tools W1b／S-5）。

    ⚠️ 這是**大聲失敗**，不是降級：`X-API-Key` 空字串送出去只會被 jgb2 拒，
    但那個 401 會被 `_fallback_response()` 折成一句「暫時無法取得資料」——
    於是「這台機器沒帶憑證」看起來和「jgb2 剛好掛了」一模一樣，⛔ 不可接受。
    """


class RealHttpTransport:
    """真 HTTP 實作：只負責送出請求與把傳輸層失敗轉成契約外殼。

    ⚠️ 本類**不承擔任何 rag 端邏輯**（不做參數推導、不做結果過濾）——
    那些屬於 `JGBSystemAPI` 與各面向 formatter。

    ⚠️ **建構期就要有憑證**（S-5）：`api_key` 空／全空白 ⇒ `MissingCredentialError`。
    ⛔ 這不是改憑證來源，也不是改 header 邏輯（`_headers` 一字未動）——只是把
    「沒有憑證」從一個到執行期才靜默降級的狀態，提早成一個開不起來的狀態。
    """

    def __init__(self, base_url: str, api_key: str, timeout: float) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            # ⛔ 訊息不含任何憑證片段（連長度都不印）。
            raise MissingCredentialError(
                "RealHttpTransport 建構失敗：JGB API 憑證為空"
                "（USE_MOCK_JGB_API=false 時必須提供 JGB_API_KEY）"
            )
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

    @staticmethod
    def _fallback_response(code: int = 500) -> TransportResponse:
        return {"success": False, "error": {"code": code, "message": FALLBACK_MESSAGE}}

    async def send(
        self, method: HttpMethod, path: str, *,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        files: Optional[list] = None,
    ) -> TransportResponse:
        url = f"{self.base_url}{path}"
        # UD-3：有檔 ⇒ multipart（`data`＝表單欄位、`files`＝`broken_photos[]`）；否則現行 JSON。
        body_kwargs: "dict[str, Any]" = (
            {"data": data, "files": files} if files is not None else {"json": data})
        # 站內幫手 S5（F8／S5-17）：log 只記方法、**端點樣板**（路徑參數以佔位符取代）、
        # 例外類別、狀態碼——⛔ 不記完整網址（路徑段含 role_id／user_id／編號）、
        # ⛔ 不記例外訊息（httpx 的 `HTTPStatusError` 訊息含完整 query）。
        template = endpoint_template(method, path)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method, url,
                    params=params, **body_kwargs,
                    headers=self._headers(),
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            logger.error("JGB API %s %s 逾時：%s", method, template, type(e).__name__)
            return self._fallback_response()
        except httpx.HTTPStatusError as e:
            status = int(e.response.status_code) if e.response is not None else 0
            logger.error("JGB API %s %s 錯誤：%s %d", method, template, type(e).__name__, status)
            # S5（S5-1）：**4xx 保留狀態碼**（403／404＝查無與無權的同一類，上層據此分辨
            # 「查無」與「沒查成」）；5xx 與其他照舊折成 500。訊息一律固定句。
            return self._fallback_response(status if 400 <= status < 500 else 500)
        except httpx.HTTPError as e:
            logger.error("JGB API %s %s 錯誤：%s", method, template, type(e).__name__)
            return self._fallback_response()
        except ValueError as e:                      # 回應不是 JSON
            logger.error("JGB API %s %s 回應解析失敗：%s", method, template, type(e).__name__)
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
    # ── 站內幫手 S0（plan-assistant-11-items-20261014 §3b）——contract: proposed ──
    # JGB 尚未實作；形狀以 jgb2-api-requests.md #16～#22 為準。⚠️ 路徑刻意避開
    # `/bills/{bill_id}`（會被它吃掉成歧義），統計掛在三段式 `/bills/summary/unpaid`。
    ("GET", "/api/external/v1/bills/summary/unpaid", "assistant_unpaid_bills"),            # jgb2-req#16
    ("GET", "/api/external/v1/repairs/in-progress", "assistant_in_progress_repairs"),      # jgb2-req#17
    ("GET", "/api/external/v1/contracts/expiring", "assistant_expiring_contracts"),        # jgb2-req#18
    ("POST", "/api/external/v1/estates", "assistant_create_estate"),                       # jgb2-req#19
    ("POST", "/api/external/v1/contracts", "assistant_create_contract"),                   # jgb2-req#20
    ("POST", "/api/external/v1/bills/manual", "assistant_create_bill"),                    # jgb2-req#21
)


def endpoint_template(method: HttpMethod, path: str) -> str:
    """`(method, path)` ⇒ 路由表裡的**樣板字串**（路徑參數仍是 `{name}`）；解析不到 ⇒
    `"<unresolved>"`。站內幫手 S5（F8）：log 與讀取紀錄只准印樣板，⛔ 印實際路徑。"""
    try:
        hits = [template for m, template, _ in ROUTES
                if m == method and match_template(template, path) is not None]
    except Exception:  # noqa: BLE001 — 只是取樣板，⛔ 讓 log 自己炸
        hits = []
    return hits[0] if len(hits) == 1 else "<unresolved>"


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

#: 站內幫手 S0 新增、**尚未由 JGB 實作**的端點（`contract: proposed`，jgb2-req#16～#21）。
#: ⚠️ 刻意**不放進** `MIGRATED_ENDPOINTS`：那份是「已遷移的既有 jgb2 端點」帳本
#: （`test_transport_migration_gate_req` 釘死其內容）；提案中的端點是另一類事實，
#: 分開列才不會把「JGB 還沒有的契約」讀成「已遷移的真端點」。
PROPOSED_ENDPOINTS: "frozenset[str]" = frozenset({
    "assistant_unpaid_bills", "assistant_in_progress_repairs", "assistant_expiring_contracts",
    "assistant_create_estate", "assistant_create_contract", "assistant_create_bill",
})

#: 站內幫手 S2：替身寫入紀錄的 env 名（值＝JSON Lines 檔路徑；未設 ⇒ 完全不寫）。
MOCK_WRITE_LOG_ENV: str = "JGB_MOCK_WRITE_LOG"

#: 寫入路徑端點（`MOCK_FAIL_NEXT_WRITE` 失敗注入與 `JGB_MOCK_WRITE_LOG` 的作用範圍；讀端點不受影響）。
WRITE_ENDPOINTS: "frozenset[str]" = frozenset({
    "create_bill", "create_contract", "create_estate", "create_repair", "patch_bill",
    "assistant_create_estate", "assistant_create_contract", "assistant_create_bill",
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
        #: 站內幫手 S0：`assistant_demo_vendor4.json` 的 `assistant_demo` 段（其他 fixture 為 `None`，
        #: 此時新端點一律 `MissingFixtureError`）；修繕可見性宣告（其他三域的宣告在各自 fixture 表上）。
        self._assistant_cfg: "Optional[dict[str, Any]]" = demo_section("assistant_demo")
        self._repair_visibility: "dict[str, list[int]]" = demo_visibility("repair")
        #: S1（DSP-074／jgb2-req#24）：電表、帳號（團隊成員列，鍵＝member_user_id）的可見性宣告。
        self._meter_visibility: "dict[str, list[int]]" = demo_visibility("meter")
        self._account_visibility: "dict[str, list[int]]" = demo_visibility("account")
        #: 本 transport 實例內「新建列」的可見性宣告：`{(domain, row_id): [user_id, ...]}`。
        #: 新建列 = 建立者＋團隊擁有者可見（用 overlay 而非改 fixture 表，見 `_declare_created`）。
        self._created_visible: "dict[tuple[str, int], list[int]]" = {}

    async def send(
        self, method: HttpMethod, path: str, *,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        files: Optional[list] = None,
    ) -> TransportResponse:
        """派發（`_dispatch`）＋替身寫入紀錄（`JGB_MOCK_WRITE_LOG`，見 `_append_write_log`）。

        ⚠️ 紀錄只在**本類**（mock）裡：`RealHttpTransport` 只多了 multipart 分支，真 HTTP 路徑不寫任何紀錄。

        UD-3：`files` 有值 ⇒ 依 multipart 收（只開給 `POST /repairs`，見 `_multipart_repair_body`）：
        表單欄位轉回型別、每個 `broken_photos[]` 檔驗型別（magic bytes）／大小／張數，算出
        `{filename, content_type, size, sha256}` 放進 body 的 `broken_photos`（列上記中繼資料）。
        ⛔ 照片位元組進紀錄：紀錄的 body 只有中繼資料。
        """
        rejected: Optional[TransportResponse] = None
        if files is not None:
            body, rejected = self._multipart_repair_body(method, path, data, files)
            if rejected is None:
                data = body
        received = copy.deepcopy(data) if isinstance(data, dict) else data
        if rejected is not None:
            resp = rejected               # 紀錄照寫（body 只有表單欄位字串，⛔ 位元組）
        else:
            resp = await self._dispatch(method, path, params=params, data=data)
        log_path = os.getenv(MOCK_WRITE_LOG_ENV)
        if log_path:
            endpoint_key = resolve_endpoint(method, path)
            if endpoint_key in WRITE_ENDPOINTS:
                self._append_write_log(log_path, endpoint_key, path, received, resp,
                                       multipart=files is not None)
            else:
                self._append_read_log(log_path, endpoint_key, method, path, params or {})
        return resp

    # ── UD-3：`POST /repairs` 的 multipart（照片本體＋同名表單欄位） ─────────────
    #: multipart 只收這個檔案欄位名（每筆一個檔；JGB 規格 §5 `broken_photos[]`）。
    MULTIPART_PHOTO_FIELD: str = "broken_photos[]"
    #: 修繕單一次最多附幾張（＝`confirm_card.REPAIR_PHOTOS_MAX`、UD-1 上傳票 repair `max_files`）。
    #: ⚠️ JSON 中繼資料與 multipart 兩條路共用這一個值；fixture `photo_policy.max_count` 不再讀。
    REPAIR_PHOTO_MAX_COUNT: int = 10
    #: 表單欄位一律是字串，轉回 JSON 路徑的整數型別（其餘欄位維持字串）。
    _MULTIPART_INT_FIELDS: "frozenset[str]" = frozenset({
        "estate_id", "category_id", "item_id", "emergency_status", "contract_id",
    })
    _PHOTO_MAGIC: "dict[str, Any]" = {
        "image/jpeg": lambda b: b.startswith(b"\xff\xd8\xff"),
        "image/png": lambda b: b.startswith(b"\x89PNG"),
        "image/webp": lambda b: b.startswith(b"RIFF") and b[8:12] == b"WEBP",
    }

    def _photo_policy(self) -> "dict[str, Any]":
        cfg = self._assistant_cfg or {}
        policy = (((cfg.get("endpoints") or {}).get("jgb2-req#22") or {}).get("photo_policy") or {})
        return {
            "content_types": tuple(policy.get("content_types") or ("image/jpeg", "image/png", "image/webp")),
            "max_bytes": int(policy.get("max_bytes") or 5 * 1024 * 1024),
        }

    def _multipart_repair_body(
        self, method: str, path: str, form: Any, files: Any,
    ) -> "tuple[Optional[dict[str, Any]], Optional[TransportResponse]]":
        """multipart ⇒ `(body, None)`；不收 ⇒ `(None, 錯誤回應)`。⛔ 回傳或記錄任何位元組。"""
        if method != "POST" or resolve_endpoint(method, path) != "create_repair":
            return None, self._error(415, "只有建立修繕單收 multipart/form-data")
        if not isinstance(form, dict) or not all(
                isinstance(k, str) and isinstance(v, str) for k, v in form.items()):
            return None, self._error(422, "multipart 表單欄位必須是字串")
        if "broken_photos" in form:
            return None, self._error(422, "multipart 的照片只能放在 broken_photos[] 檔案欄位")
        body: "dict[str, Any]" = {}
        for k, v in form.items():
            if k in self._MULTIPART_INT_FIELDS:
                if not re.fullmatch(r"-?[0-9]{1,18}", v):
                    return None, self._error(422, f"{k} 必須是整數")
                body[k] = int(v)
            else:
                body[k] = v
        policy = self._photo_policy()
        if not isinstance(files, list) or not 1 <= len(files) <= self.REPAIR_PHOTO_MAX_COUNT:
            return None, self._error(422, f"broken_photos 最多 {self.REPAIR_PHOTO_MAX_COUNT} 張")
        photos: list = []
        for item in files:
            ok = (isinstance(item, tuple) and len(item) == 2 and item[0] == self.MULTIPART_PHOTO_FIELD
                  and isinstance(item[1], tuple) and len(item[1]) == 3)
            if ok:
                filename, content, ctype = item[1]
                ok = (isinstance(filename, str) and 0 < len(filename) <= 100
                      and isinstance(content, (bytes, bytearray))
                      and ctype in policy["content_types"]
                      and 0 < len(content) <= policy["max_bytes"]
                      and self._PHOTO_MAGIC.get(ctype, lambda b: False)(bytes(content[:12])))
            if not ok:
                return None, self._error(422, "broken_photos[] 每個檔須為 jpeg／png／webp（內容與型別相符）且 ≤ 5 MB")
            photos.append({"filename": filename, "content_type": ctype, "size": len(content),
                           "sha256": hashlib.sha256(bytes(content)).hexdigest()})
        body["broken_photos"] = photos
        return body, None

    # ── 站內幫手 S5（§3i 第 1 點，A3(a)）：替身**讀取**呼叫紀錄 ────────────────
    #: 讀取紀錄的檔名＝寫入紀錄路徑加這個後綴（同一個 env 開關、另一個檔：既有的
    #: 寫入紀錄行數比對〔確認 +1、取消／越權不變〕因此不受讀取行影響）。
    READ_LOG_SUFFIX: str = ".reads.jsonl"

    @staticmethod
    def _identity_flags(path: str, source: "dict[str, Any]") -> "tuple[bool, bool]":
        """`(has_role_id, has_viewer)`：role 可在參數或 `/roles/{role_id}/` 路徑段；viewer＝
        `viewer_user_id`（提案統計端點 #16～#18 的 viewer 欄名是 `user_id`）。"""
        has_role = source.get("role_id") not in (None, "") or bool(
            re.search(r"/roles/[^/]+", path))
        has_viewer = source.get("viewer_user_id") not in (None, "") or (
            resolve_endpoint("GET", path) in PROPOSED_ENDPOINTS
            and source.get("user_id") not in (None, ""))
        return has_role, has_viewer

    def _append_read_log(self, log_path: str, endpoint_key: Optional[str], method: str,
                         path: str, params: "dict[str, Any]") -> None:
        """讀端點每次呼叫追加一行：`endpoint_key`、端點樣板、`has_role_id`、`has_viewer`。

        ⛔ **只記布林**：參數值（role_id、user_id、編號、keyword）一律不落檔。
        寫檔失敗只記 error log、⛔ 不拋（讀取本身已完成）。
        """
        has_role, has_viewer = self._identity_flags(path, params)
        line = {"endpoint_key": endpoint_key, "template": endpoint_template(method, path),
                "has_role_id": has_role, "has_viewer": has_viewer}
        try:
            with open(log_path + self.READ_LOG_SUFFIX, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")
        except OSError as exc:
            logger.error("替身讀取紀錄寫檔失敗（%s）：%s", MOCK_WRITE_LOG_ENV, type(exc).__name__)

    # ── 站內幫手 S2（plan §3f「替身寫入紀錄」）：寫入前後快照 ─────────────────
    #: 寫入端點 → 被寫的領域（紀錄「建立或更新後的那一列」從這個領域的 fixture 表讀回）。
    _WRITE_DOMAIN: "dict[str, str]" = {
        "create_repair": "repairs",
        "create_bill": "bills", "patch_bill": "bills", "assistant_create_bill": "bills",
        "create_contract": "contracts", "assistant_create_contract": "contracts",
        "create_estate": "estates", "assistant_create_estate": "estates",
    }

    def _domain_table(self, domain: str) -> Optional[Any]:
        return {"bills": self.fixtures, "contracts": self.contract_fixtures,
                "estates": self.estate_fixtures, "repairs": self.repair_fixtures}[domain]

    def _append_write_log(self, log_path: str, endpoint_key: str, path: str,
                          body: Any, resp: TransportResponse, *, multipart: bool = False) -> None:
        """env `JGB_MOCK_WRITE_LOG` 有值時，每次寫入端點呼叫後追加一行 JSON。

        欄位：`endpoint_key`、`body`（替身收到的 request body——即 `JGBSystemAPI` 守門與
        身分覆寫之後的那一份）、`status`（成功 200，失敗取 `error.code`）、`row`（建立或
        更新後的那一列，從 fixture 表讀回；失敗或讀不到為 `null`）、`counts`（四域列數）。
        ⚠️ 冪等鍵（＝確認 token）一律遮成 `"<redacted>"`：token ⛔ 落檔（同
        `confirm.PendingRedemption` 的紀律），紀錄只需要知道「有帶」。
        ⚠️ 寫紀錄失敗只記 error log、⛔ 不拋：寫入本身已發生，拋出去會讓上層把一次
        成功的寫入當成失敗（缺行會在「前後 `wc -l`」比對時現形）。
        ⚠️ `send` 拋例外（未解析端點、fixture 未裝配…）時沒有回應 ⇒ 不寫紀錄。
        """
        if isinstance(body, dict):
            body = {k: ("<redacted>" if k in self._IDEMPOTENCY_KEYS else v) for k, v in body.items()}
        ok = bool((resp or {}).get("success"))
        status = 200 if ok else ((resp or {}).get("error") or {}).get("code")
        domain = self._WRITE_DOMAIN[endpoint_key]
        row = None
        table = self._domain_table(domain)
        resp_data = (resp or {}).get("data")
        row_id = resp_data.get("id") if ok and isinstance(resp_data, dict) else None
        if row_id is not None and table is not None:
            try:
                found = table.by_id(int(row_id))
            except (TypeError, ValueError):
                found = None
            row = copy.deepcopy(found) if found is not None else None
        counts = {}
        for name in ("estates", "contracts", "bills", "repairs"):
            t = self._domain_table(name)
            counts[name] = len(t.rows()) if t is not None else None
        line = {"endpoint_key": endpoint_key, "path": path, "body": body,
                "status": status, "row": row, "counts": counts}
        if multipart:
            # UD-3：照片以 multipart 檔案收到（body／row 的 `broken_photos` 是替身算出的中繼資料）。
            line["multipart"] = True
        try:
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(line, ensure_ascii=False, sort_keys=True, default=str) + "\n")
        except OSError as exc:
            logger.error("替身寫入紀錄寫檔失敗（%s）：%s", MOCK_WRITE_LOG_ENV, type(exc).__name__)

    async def _dispatch(
        self, method: HttpMethod, path: str, *,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> TransportResponse:
        endpoint_key = resolve_endpoint(method, path)   # 歧義 → ambiguous（4.2）

        if endpoint_key is None:
            raise UnresolvedEndpointError(
                f"無法解析為任何 logical endpoint：{method} {path}", reason="no_match"
            )
        if endpoint_key not in MIGRATED_ENDPOINTS and endpoint_key not in PROPOSED_ENDPOINTS:
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
        if endpoint_key in PROPOSED_ENDPOINTS:
            return self._send_proposed(endpoint_key, params, data)
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
            return self._estates_show(estate_id, params)
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
            return self._member_permissions(ids["role_id"], ids["user_id"], params)
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
        if self._foreign_team(params):             # S5 6b：他團隊 ⇒ 與查無同形（空列表）
            rows = []

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

        # S1（DSP-074，contract: proposed）：assistant fixture 下依 `contract_visibility` 過濾 viewer。
        rows = self._viewer_scoped(params, "contract", rows)

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
        if self._foreign_team(params):             # S5 6b：他團隊 ⇒ 與查無同形（空列表）
            rows = []

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

        # `keyword`：同 `_contracts_index`，`title LIKE '%kw%'`（只比 title，收案 3
        # 恢復——W0b 重寫時遺失，與 viewer 圈定並存，過濾順序不影響結果）。
        keyword = params.get("keyword")
        if keyword not in (None, ""):
            kw = str(keyword)
            rows = [r for r in rows if kw in str(r.get("title") or "")]

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
        if row is None or self._foreign_team(params):   # S5 6b：他團隊 ⇒ 與不存在同一句
            return self._error(404, "帳單不存在或無權存取")
        # S1 修正（DSP-074）：assistant fixture 下帶 viewer ⇒ 依 `bill_visibility` 過濾；
        # 看不到＝與「不存在」同一句（折疊，不洩漏資源是否存在）。非 assistant fixture 行為不變。
        viewer = params.get("viewer_user_id")
        if self._assistant_cfg is not None and viewer not in (None, ""):
            try:
                viewer_int = int(viewer)
            except (TypeError, ValueError):
                raise UnsupportedMockParameterError(f"viewer_user_id 非合法整數：{viewer!r}")
            if not self._is_visible("bill", row["id"], viewer_int):
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
        rows = self._viewer_scoped(params, "estate", rows)       # S1：DSP-074，assistant fixture 才啟用

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

    def _estates_show(self, estate_id: str,
                      params: "Optional[dict[str, Any]]" = None) -> TransportResponse:
        """`GET /estates/{id}`（`show()` → `formatEstate($estate, true)`）。

        站內幫手 S5（6b／jgb2-req#24，contract: proposed）：assistant fixture 下，物件
        不屬 `role_id` 的團隊、或帶了 viewer 而這位成員看不到 ⇒ 與「不存在」同一句 404
        （折疊，不洩漏存在與否）；其他 fixture 行為不變。
        """
        params = params or {}
        try:
            row = self.estate_fixtures.by_id(int(estate_id))
        except (TypeError, ValueError):
            row = None
        if row is not None and self._assistant_cfg is not None:
            if self._foreign_team(params) or str(row.get("role_id")) != str(params.get("role_id")):
                row = None
            elif not self._viewer_scoped(params, "estate", [row]):
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
        rows = self._viewer_scoped(params, "meter", rows)        # S1：DSP-074，assistant fixture 才啟用

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
        members = self._viewer_scoped(                           # S1：DSP-074，assistant fixture 才啟用
            params, "account", self.team_fixtures.rows(), id_key="member_user_id")
        for m in members:
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

    def _member_permissions(self, role_id: str, user_id: str,
                            params: "Optional[dict[str, Any]]" = None) -> TransportResponse:
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
        # S1：viewer 看不到這個帳號 ⇒ 與「查無此成員」同形折疊（DSP-074，assistant fixture 才啟用）。
        if not self._viewer_scoped(params or {}, "account", [member], id_key="member_user_id"):
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
        if self._foreign_team(params):             # S5 6b：他團隊 ⇒ 與查無同形（空列表）
            rows = []

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
        rows = self._viewer_scoped(params, "repair", rows)       # S1：DSP-074，assistant fixture 才啟用

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
        # jgb2-req#22／#23（contract: proposed）：載入 assistant_demo 段時才啟用的加碼檢查
        # （歸屬／未知欄位 422、物件歸屬折疊、照片中繼資料）；其他 fixture 行為不變。
        assistant = self._assistant_cfg is not None
        if assistant:
            rejected = self._assistant_repair_checks(data)
            if rejected is not None:
                return rejected
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
        if assistant:
            # 讀回時要看得到物件與分類名稱（真 API 的 formatRepair 會帶）；歸屬人取自登入身分。
            estate = next(e for e in self.estate_fixtures.rows() if e["id"] == int(data["estate_id"]))
            overrides.update(estate_title=estate.get("title"),
                             estate_full_address=estate.get("full_address"),
                             user_id=int(data["user_id"]), agent_user_id=int(data["user_id"]))
            for cat in repair_categories():
                if cat["id"] == data.get("category_id"):
                    overrides["category_name"] = cat["name"]
                    for item in cat.get("items", []):
                        if item["id"] == data.get("item_id"):
                            overrides["item_name"] = item["name"]
        row = self.repair_fixtures.create(overrides)
        if assistant:
            self._declare_created("repair", row["id"], int(data["user_id"]))
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
        # 站內幫手 S5（F5／jgb2-req#23 擴及 PATCH）：寫入 body 帶登入身分。
        "role_id", "user_id",
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
        # S5（jgb2-req#23，contract: proposed）：assistant fixture 下驗身分、團隊與這位成員
        # 看不看得到這張帳單；不符 ⇒ 與不存在同一句（折疊）。其他 fixture 行為不變。
        if self._assistant_cfg is not None:
            ident, err = self._assistant_identity(data)
            if err:
                return err
            if not self._is_visible("bill", row["id"], ident[1]):
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

    # ══════════════════════════════════════════════════════════════════════
    # 站內幫手 S0（plan-assistant-11-items-20261014 §3b）——contract: proposed
    #
    # ⚠️ 本段全部是「期望契約」的替身：JGB 尚未實作，形狀以
    # `.kiro/specs/agentic-mcp-orchestration/jgb2-api-requests.md` #16～#24 為準，
    # ⛔ 不可讀成 JGB 已存在的行為，⛔ 不得據此宣稱 e2e 已驗。
    # 資料來源是 `assistant_demo_vendor4.json`（含 `assistant_demo` 段）；載入其他 fixture
    # 時這些端點一律 `MissingFixtureError`（大聲失敗，不退回猜測）。
    # ══════════════════════════════════════════════════════════════════════

    #: 帳單 status（`MAPPING["status"]`）：2 待繳費、8 待對帳 視為「未收」；1 待發送／32 排定發送
    #: 尚未寄出、16 已繳費、64 已失效 都不是未收。（提案語義，待 JGB 確認 8 是否算未收）
    _UNPAID_BILL_STATUSES: "frozenset[int]" = frozenset({2, 8})
    #: 修繕 status：1 申請中、2 安排修繕、16 完成修繕 視為「執行中（未結案）」；32 結單、64 封存不算。
    _IN_PROGRESS_REPAIR_STATUSES: "frozenset[int]" = frozenset({1, 2, 16})
    #: 寫入 body 中「歸屬欄位」：由登入身分決定，呼叫端 ⛔ 指定（F4）。
    _OWNERSHIP_KEYS: "frozenset[str]" = frozenset({
        "team_id", "owner_user_id", "owner_role_id", "vendor_id", "to_user_id",
        "agent_user_id", "created_by", "issue_target_role_id",
    })
    _FOLD_MESSAGE: str = "不存在或無權存取"
    _IDEMPOTENCY_KEYS: "frozenset[str]" = frozenset({"idempotency_key", "confirmation_token"})
    #: 與其他寫入端點相同的固定戳記（fixture 時間，非現在）。
    _PROPOSED_NOW: str = "2026-09-08 19:00:00"

    _ESTATE_BODY_KEYS: "frozenset[str]" = frozenset({
        "role_id", "user_id", "title", "city", "district", "address", "use_for",
        "space_type", "building", "room_count", "size", "rent", "floor",
    }) | _IDEMPOTENCY_KEYS
    _CONTRACT_BODY_KEYS: "frozenset[str]" = frozenset({
        "role_id", "user_id", "estate_id", "title", "to_user_email", "to_user_phone",
        "date_start", "date_end", "rent", "deposit_amount",
    }) | _IDEMPOTENCY_KEYS
    _BILL_BODY_KEYS: "frozenset[str]" = frozenset({
        "role_id", "user_id", "contract_id", "title", "sub_title", "total", "date_expire",
    }) | _IDEMPOTENCY_KEYS
    #: `POST /repairs` 在提案契約下的 body 鍵（既有鍵＋`user_id`）。
    _REPAIR_BODY_KEYS: "frozenset[str]" = frozenset({
        "role_id", "user_id", "estate_id", "category_id", "item_id", "broken_reason",
        "broken_note", "emergency_status", "contract_id", "broken_photos",
    }) | _IDEMPOTENCY_KEYS

    # ── 共用：身分、歸屬、可見性 ─────────────────────────────────────────

    def _need_assistant_cfg(self) -> "dict[str, Any]":
        if self._assistant_cfg is None:
            raise MissingFixtureError(
                "站內幫手提案端點需要 assistant_demo_vendor4.json 的 assistant_demo 段"
                "（JGB_MOCK_FIXTURE 指向它，或單元測試 fixture_store.load_from）"
            )
        return self._assistant_cfg

    def _fold(self) -> TransportResponse:
        """越權／不存在 **同一句**（折疊，不洩漏資源是否存在；對齊 `_bills_show`）。"""
        return self._error(404, self._FOLD_MESSAGE)

    def _assistant_identity(
        self, source: "dict[str, Any]",
    ) -> "tuple[Optional[tuple[int, int]], Optional[TransportResponse]]":
        """驗 `role_id`＋`user_id`（缺→400、非整數→422、角色非本團隊或非成員→折疊 404）。"""
        cfg = self._need_assistant_cfg()
        for key in ("role_id", "user_id"):
            if source.get(key) in (None, ""):
                return None, self._error(400, f"{key} 為必填參數")
        try:
            role_id, user_id = int(source["role_id"]), int(source["user_id"])
        except (TypeError, ValueError):
            return None, self._error(422, "role_id、user_id 必須為整數")
        if role_id != int(cfg["role_id"]):
            return None, self._fold()
        self._require(self.team_fixtures, "assistant_identity")
        if self.team_fixtures.by_user_id(user_id) is None:
            return None, self._fold()
        return (role_id, user_id), None

    def _owner_user_ids(self) -> "list[int]":
        return [int(m["member_user_id"]) for m in self.team_fixtures.rows() if m.get("is_owner")]

    def _declared_viewers(self, domain: str, row_id: int) -> "Optional[list[int]]":
        """這筆資料宣告的可見 user_id；**未宣告回 None**（不假裝答得出來）。"""
        created = self._created_visible.get((domain, int(row_id)))
        if created is not None:
            return created
        if domain == "bill":
            return self.fixtures.visible_to(row_id)
        if domain == "contract":
            return self.contract_fixtures.visible_to(row_id)
        if domain == "estate":
            return self.estate_fixtures.visible_to(row_id)
        if domain == "repair":
            return self._repair_visibility.get(str(row_id))
        if domain == "meter":
            return self._meter_visibility.get(str(row_id))
        if domain == "account":
            return self._account_visibility.get(str(row_id))
        raise ValueError(f"未知的可見性領域：{domain}")

    def _is_visible(self, domain: str, row_id: int, viewer: int) -> bool:
        declared = self._declared_viewers(domain, row_id)
        if declared is None:
            raise UnsupportedMockParameterError(
                f"{domain} {row_id} 未在 fixture 宣告可見成員（{domain}_visibility），"
                "替身無法忠實模擬依成員可見範圍的過濾；不得以忽略該限制的結果回答。"
            )
        return viewer in declared

    def _foreign_team(self, params: "dict[str, Any]") -> bool:
        """站內幫手 S5（6b）：assistant fixture 下 `role_id` 不是 fixture 團隊 ⇒ `True`
        （呼叫端回與「不存在」同形的折疊結果）。非 assistant fixture／沒帶 role ⇒ `False`
        （既有行為不變；缺 role 的 400 由各端點自己判）。"""
        if self._assistant_cfg is None or params.get("role_id") in (None, ""):
            return False
        return str(params.get("role_id")) != str(self._assistant_cfg.get("role_id"))

    def _viewer_scoped(self, params: "dict[str, Any]", domain: str,
                       rows: "list[dict[str, Any]]", id_key: str = "id") -> "list[dict[str, Any]]":
        """S1（DSP-074／jgb2-req#24，contract: proposed）：既有讀取端點依 `viewer_user_id` 的可見範圍過濾。

        只在載入 `assistant_demo` 段的 fixture 且帶了非空 `viewer_user_id` 時啟用——
        其他 fixture 或沒帶 viewer 時回傳原 rows（既有行為不變）。是**過濾**不是圈定成空：
        成員看得到的列照常回；未在 fixture 宣告可見性的列 ⇒ `UnsupportedMockParameterError`
        （沿 `_bills_index` 的誠實紀律）。
        """
        viewer = params.get("viewer_user_id")
        if self._assistant_cfg is None or viewer in (None, ""):
            return rows
        try:
            viewer_int = int(viewer)
        except (TypeError, ValueError):
            raise UnsupportedMockParameterError(f"viewer_user_id 非合法整數：{viewer!r}")
        return [r for r in rows if self._is_visible(domain, r[id_key], viewer_int)]

    def _declare_created(self, domain: str, row_id: int, creator: int) -> None:
        self._created_visible[(domain, int(row_id))] = sorted({creator, *self._owner_user_ids()})

    def _estate_owner_role(self, estate_id: int) -> "Optional[int]":
        for e in self.estate_fixtures.rows():
            if e["id"] == estate_id:
                try:
                    return int(e.get("role_id"))
                except (TypeError, ValueError):
                    return None
        return None

    def _usable_estate(self, estate_id: Any, role_id: int, viewer: int) -> "Optional[dict[str, Any]]":
        """本團隊、且 viewer 看得到的物件列；他團隊／不存在／本團隊但 viewer 看不到 ⇒ `None`（呼叫端折疊）。"""
        try:
            eid = int(estate_id)
        except (TypeError, ValueError):
            return None
        for e in self.estate_fixtures.rows():
            if e["id"] == eid:
                if self._estate_owner_role(eid) != role_id or not self._is_visible("estate", eid, viewer):
                    return None
                return e
        return None

    def _usable_contract(self, contract_id: Any, role_id: int, viewer: int) -> "Optional[dict[str, Any]]":
        """合約歸屬＝其物件的歸屬（合約列本身無 role_id）。"""
        try:
            cid = int(contract_id)
        except (TypeError, ValueError):
            return None
        for c in self.contract_fixtures.rows():
            if c["id"] == cid:
                if self._estate_owner_role(c.get("estate_id")) != role_id:
                    return None
                if not self._is_visible("contract", cid, viewer):
                    return None
                return c
        return None

    def _write_guard(self, data: "dict[str, Any]", allowed: "frozenset[str]"
                     ) -> "tuple[Optional[tuple[int, int]], Optional[TransportResponse]]":
        """F4 守門：歸屬欄位／未知欄位 → 422（比照 `_PATCH_BILL_ALLOWED_KEYS`）；再驗身分。

        ⚠️ `role_id`＋`user_id` 是**身分欄位**（#23：寫入 body 一律帶，由 JGB 驗），不是歸屬欄位；
        歸屬欄位（`team_id`／`owner_user_id`／`vendor_id`／`to_user_id`…）只能由登入身分決定。
        """
        ownership = sorted(set(data) & self._OWNERSHIP_KEYS)
        if ownership:
            return None, self._error(422, f"歸屬欄位由登入身分決定，不得指定：{ownership}")
        foreign = sorted(set(data) - allowed)
        if foreign:
            return None, self._error(422, f"不支援的欄位：{foreign}")
        return self._assistant_identity(data)

    @staticmethod
    def _parse_ymd(value: Any) -> "Optional[datetime.date]":
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _add_months(d: "datetime.date", months: int) -> "datetime.date":
        y, m = divmod(d.month - 1 + months, 12)
        year, month = d.year + y, m + 1
        return datetime.date(year, month, min(d.day, calendar.monthrange(year, month)[1]))

    def _paginate(self, items: "list[Any]", params: "dict[str, Any]"
                  ) -> "tuple[list[Any], dict[str, Any]]":
        page = max(1, int(params.get("page", 1) or 1))
        per_page = min(self.MAX_PER_PAGE,
                       max(1, int(params.get("per_page", self.DEFAULT_PER_PAGE) or 1)))
        total = len(items)
        total_pages = -(-total // per_page) if total else 0
        offset = (page - 1) * per_page
        return items[offset:offset + per_page], {
            "current_page": page, "per_page": per_page, "total": total,
            "total_pages": total_pages, "has_more": page < total_pages,
        }

    def _send_proposed(self, endpoint_key: str, params: "dict[str, Any]",
                       data: "dict[str, Any]") -> TransportResponse:
        if endpoint_key == "assistant_unpaid_bills":
            return self._assistant_unpaid_bills(params)
        if endpoint_key == "assistant_in_progress_repairs":
            return self._assistant_in_progress_repairs(params)
        if endpoint_key == "assistant_expiring_contracts":
            return self._assistant_expiring_contracts(params)
        self._require(self.estate_fixtures, endpoint_key)
        self._require(self.contract_fixtures, endpoint_key)
        builders = {
            "assistant_create_estate": self._assistant_create_estate,
            "assistant_create_contract": self._assistant_create_contract,
            "assistant_create_bill": self._assistant_create_bill,
        }
        return self._with_idempotency(endpoint_key, data, lambda: builders[endpoint_key](data))

    def _read_guard(self, params: "dict[str, Any]", allowed: "frozenset[str]"
                    ) -> "tuple[Optional[tuple[int, int]], Optional[datetime.date], Optional[TransportResponse]]":
        foreign = sorted(set(params) - allowed)
        if foreign:
            return None, None, self._error(422, f"不支援的參數：{foreign}")
        ident, err = self._assistant_identity(params)
        if err:
            return None, None, err
        as_of = datetime.date.today()
        if params.get("as_of") not in (None, ""):
            as_of = self._parse_ymd(params["as_of"])
            if as_of is None:
                return None, None, self._error(422, "as_of 必須為 YYYY-MM-DD")
        return ident, as_of, None

    # ── jgb2-req#16（contract: proposed）──────────────────────────────────

    def _assistant_unpaid_bills(self, params: "dict[str, Any]") -> TransportResponse:
        """`GET /bills/summary/unpaid`——jgb2-req#16，contract: proposed。

        未收帳單的加總＋逐筆明細，**依 `user_id`（viewer）的可見範圍過濾**（DSP-074；
        ⛔ 不是 mcp-facade §4.2 的「圈定成空」）。`scope=this_month`＝`date_expire` 落在
        `as_of` 當月；`scope=overdue`＝`date_expire < as_of`。`count`／`total_amount` 涵蓋
        **全部符合者**，`items` 才分頁（A4：總額必須等於明細逐筆相加，不因分頁而少）。
        """
        self._require(self.fixtures, "assistant_unpaid_bills")
        ident, as_of, err = self._read_guard(
            params, frozenset({"role_id", "user_id", "scope", "as_of", "page", "per_page"}))
        if err:
            return err
        scope = params.get("scope")
        if scope not in ("this_month", "overdue"):
            return self._error(422, "scope 必須為 this_month 或 overdue")
        _, viewer = ident
        as_of_int = as_of.year * 10000 + as_of.month * 100 + as_of.day
        rows = [b for b in self.fixtures.rows() if b["status"] in self._UNPAID_BILL_STATUSES]
        if scope == "overdue":
            rows = [b for b in rows if b["date_expire"] < as_of_int]
        else:
            lo = as_of.year * 10000 + as_of.month * 100
            rows = [b for b in rows if lo + 1 <= b["date_expire"] <= lo + 31]
        rows = [b for b in rows if self._is_visible("bill", b["id"], viewer)]
        rows.sort(key=lambda b: (b["date_expire"], b["id"]))
        total_amount = sum(b["total"] for b in rows)
        items = [{k: b.get(k) for k in ("id", "contract_id", "estate_id", "title", "sub_title",
                                       "total", "currency", "date_expire", "status")}
                 for b in rows]
        page_items, pagination = self._paginate(items, params)
        return {
            "success": True,
            "data": {"scope": scope, "as_of": as_of.isoformat(), "currency": "TWD",
                     "count": len(rows), "total_amount": total_amount, "items": page_items},
            "pagination": pagination,
        }

    # ── jgb2-req#17（contract: proposed）──────────────────────────────────

    def _assistant_in_progress_repairs(self, params: "dict[str, Any]") -> TransportResponse:
        """`GET /repairs/in-progress`——jgb2-req#17，contract: proposed。

        未結案（status 1／2／16）修繕單的全量清單，依 viewer 可見範圍過濾，分頁；
        排序 `apply_at` 新到舊。回應只投影必要欄位（不含報修人電話／email）。
        """
        self._require(self.repair_fixtures, "assistant_in_progress_repairs")
        ident, _, err = self._read_guard(
            params, frozenset({"role_id", "user_id", "page", "per_page"}))
        if err:
            return err
        _, viewer = ident
        rows = [r for r in self.repair_fixtures.rows()
                if r["status"] in self._IN_PROGRESS_REPAIR_STATUSES]
        rows = [r for r in rows if self._is_visible("repair", r["id"], viewer)]
        rows.sort(key=lambda r: (str(r.get("apply_at") or ""), r["id"]), reverse=True)
        keys = ("id", "status", "emergency_status", "estate_id", "estate_title",
                "estate_full_address", "category_id", "category_name", "item_id", "item_name",
                "broken_reason", "broken_note", "apply_at", "assign_at", "complete_at", "updated_at")
        items = [{k: r.get(k) for k in keys} for r in rows]
        page_items, pagination = self._paginate(items, params)
        return {
            "success": True,
            "mapping": {"status": {"1": "申請中", "2": "安排修繕", "16": "完成修繕"},
                        "emergency_status": {"1": "非緊急", "2": "緊急"}},
            "data": {"count": len(rows), "items": page_items},
            "pagination": pagination,
        }

    # ── jgb2-req#18（contract: proposed）──────────────────────────────────

    def _assistant_expiring_contracts(self, params: "dict[str, Any]") -> TransportResponse:
        """`GET /contracts/expiring`——jgb2-req#18，contract: proposed。

        `months`（預設 3，1～24）個月內到期的合約：`active=1`、`is_newest=1`、`is_history=0`，
        且 `as_of <= date_end <= as_of + months 個月`（兩端含；月底以當月最後一天為界）。
        依 viewer 可見範圍過濾；`days_left` 由伺服端算好（決定性程式算事實）。
        """
        self._require(self.contract_fixtures, "assistant_expiring_contracts")
        ident, as_of, err = self._read_guard(
            params, frozenset({"role_id", "user_id", "months", "as_of", "page", "per_page"}))
        if err:
            return err
        months = params.get("months", 3)
        try:
            months = int(months)
        except (TypeError, ValueError):
            return self._error(422, "months 必須為 1～24 的整數")
        if not 1 <= months <= 24:
            return self._error(422, "months 必須為 1～24 的整數")
        _, viewer = ident
        end = self._add_months(as_of, months)
        lo = as_of.year * 10000 + as_of.month * 100 + as_of.day
        hi = end.year * 10000 + end.month * 100 + end.day
        rows = [c for c in self.contract_fixtures.rows()
                if c.get("active") == 1 and c.get("is_newest") == 1 and c.get("is_history") == 0
                and lo <= c["date_end"] <= hi]
        rows = [c for c in rows if self._is_visible("contract", c["id"], viewer)]
        rows.sort(key=lambda c: (c["date_end"], c["id"]))
        keys = ("id", "title", "estate_id", "city", "district", "address", "rent",
                "deposit_amount", "date_start", "date_end", "status", "bit_status")
        items = []
        for c in rows:
            s = str(c["date_end"])
            days_left = (datetime.date(int(s[:4]), int(s[4:6]), int(s[6:])) - as_of).days
            items.append({**{k: c.get(k) for k in keys}, "days_left": days_left})
        page_items, pagination = self._paginate(items, params)
        return {
            "success": True,
            "data": {"months": months, "as_of": as_of.isoformat(), "window_end": end.isoformat(),
                     "count": len(rows), "items": page_items},
            "pagination": pagination,
        }

    # ── jgb2-req#19（contract: proposed）──────────────────────────────────

    def _assistant_create_estate(self, data: "dict[str, Any]") -> TransportResponse:
        """`POST /estates`——jgb2-req#19，contract: proposed。建立物件，**照使用者給的值**。

        必填：`title`／`city`／`district`／`address`／`use_for`；`city`＋`district` 須能對到既有的
        縣市／行政區代碼（JGB 端以名稱解析），對不到 422。⛔ 沒給的欄位留空，不補隨機值。
        """
        ident, err = self._write_guard(data, self._ESTATE_BODY_KEYS)
        if err:
            return err
        role_id, viewer = ident
        for key in ("title", "city", "district", "address", "use_for"):
            if data.get(key) in (None, ""):
                return self._error(400, f"{key} 為必填參數")
        for key, limit in (("title", 60), ("address", 100), ("city", 20), ("district", 20),
                           ("space_type", 20), ("building", 20), ("floor", 10)):
            v = data.get(key)
            if v is not None and (not isinstance(v, str) or not v.strip() or len(v) > limit):
                return self._error(422, f"{key} 必須為 1～{limit} 字的文字")
        if data["use_for"] not in ("residential", "business", "parking_space"):
            return self._error(422, "use_for 必須為 residential／business／parking_space")
        for key, lo, hi in (("rent", 0, 99_999_999), ("room_count", 0, 99)):
            v = data.get(key)
            if v is not None and (isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi):
                return self._error(422, f"{key} 必須為 {lo}～{hi} 的整數")
        size = data.get("size")
        if size is not None and (isinstance(size, bool) or not isinstance(size, (int, float))
                                 or not 0 < size <= 100000):
            return self._error(422, "size 必須為大於 0 的數字")
        region = next((e for e in self.estate_fixtures.rows()
                       if e.get("city") == data["city"] and e.get("district") == data["district"]),
                      None)
        if region is None:
            return self._error(422, "無法辨識縣市／行政區")
        template = next(e for e in self.estate_fixtures.rows()
                        if self._estate_owner_role(e["id"]) == role_id)
        now = self._PROPOSED_NOW
        row: "dict[str, Any]" = {k: None for k in EXTERNAL_ESTATE_FIELDS}
        row.update({
            "role_id": role_id, "team_id": role_id, "user_id": viewer,
            "role_id_comment": template.get("role_id_comment"),
            "team_id_comment": template.get("team_id_comment"),
            "team_name": template.get("team_name"),
            "team_name_comment": template.get("team_name_comment"),
            "title": data["title"], "status": 1,
            "country": region.get("country"), "country_id": region.get("country_id"),
            "city": region["city"], "city_id": region["city_id"],
            "district": region["district"], "district_id": region["district_id"],
            "address": data["address"], "display_address": data["address"],
            "full_address": f"{region['city']}{region['district']}{data['address']}",
            "full_display_address": f"{region['city']}{region['district']}{data['address']}",
            "use_for": data["use_for"], "space_type": data.get("space_type"),
            "building": data.get("building"), "room_count": data.get("room_count"),
            "size": data.get("size"), "floor": data.get("floor"),
            "rent": data.get("rent"), "currency": "TWD",
            "fees": [], "facilities": [], "bit_status": 0,
            "created_at": now, "updated_at": now,
            "active": 1, "is_open": 1,
        })
        row["id"] = max([e["id"] for e in self.estate_fixtures.rows()], default=0) + 1
        created = self.estate_fixtures.create(row)
        self._declare_created("estate", created["id"], viewer)
        return {"success": True, "data": project_estate(created)}

    # ── jgb2-req#20（contract: proposed）──────────────────────────────────

    def _assistant_create_contract(self, data: "dict[str, Any]") -> TransportResponse:
        """`POST /contracts`——jgb2-req#20，contract: proposed。建立合約，**照使用者給的值**。

        必填：`estate_id`／`date_start`／`date_end`（YYYY-MM-DD）／`rent`，以及 `to_user_email`
        或 `to_user_phone` 至少一個。物件不是本團隊的、或這位成員看不到 ⇒ 折疊 404
        （與「物件不存在」同一句，不洩漏存在與否）。
        """
        ident, err = self._write_guard(data, self._CONTRACT_BODY_KEYS)
        if err:
            return err
        role_id, viewer = ident
        for key in ("estate_id", "date_start", "date_end", "rent"):
            if data.get(key) in (None, ""):
                return self._error(400, f"{key} 為必填參數")
        if not (data.get("to_user_email") or data.get("to_user_phone")):
            return self._error(400, "to_user_email 與 to_user_phone 至少需要一個")
        estate = self._usable_estate(data["estate_id"], role_id, viewer)
        if estate is None:
            return self._fold()                       # 先擋歸屬，再談欄位值（不給探測）
        start, end = self._parse_ymd(data["date_start"]), self._parse_ymd(data["date_end"])
        if start is None or end is None or end <= start:
            return self._error(422, "date_start／date_end 必須為 YYYY-MM-DD，且結束日晚於起始日")
        for key, lo, hi in (("rent", 1, 99_999_999), ("deposit_amount", 0, 99_999_999)):
            v = data.get(key, 0 if key == "deposit_amount" else None)
            if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
                return self._error(422, f"{key} 必須為 {lo}～{hi} 的整數")
        email, phone = data.get("to_user_email"), data.get("to_user_phone")
        if email is not None and (not isinstance(email, str) or len(email) > 100
                                  or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)):
            return self._error(422, "to_user_email 格式不正確")
        if phone is not None and (not isinstance(phone, str)
                                  or not re.fullmatch(r"[0-9+\-]{8,15}", phone)):
            return self._error(422, "to_user_phone 格式不正確")
        title = data.get("title") or estate.get("title")
        if not isinstance(title, str) or not title.strip() or len(title) > 60:
            return self._error(422, "title 必須為 1～60 字的文字")
        now = self._PROPOSED_NOW
        new_id = max([c["id"] for c in self.contract_fixtures.rows()], default=0) + 1
        row: "dict[str, Any]" = {k: None for k in EXTERNAL_CONTRACT_FIELDS}
        row.update({
            "id": new_id, "father_id": new_id, "status": 1, "bit_status": 1,
            "active": 1, "is_newest": 1, "is_history": 0, "is_history_done": 0,
            "estate_id": estate["id"], "title": title,
            "city": estate.get("city"), "district": estate.get("district"),
            "address": estate.get("full_address"), "currency": "TWD",
            "rent": data["rent"], "deposit_amount": data.get("deposit_amount", 0),
            "date_start": int(start.strftime("%Y%m%d")), "date_end": int(end.strftime("%Y%m%d")),
            "allow_early_termination": False, "is_auto_generate_invoice": 0,
            "to_user_connect": False, "is_tenant_registered": False,
            "to_user_phone": phone, "to_user_email": email,
            "property_purpose_key": estate.get("property_purpose_key"),
            "enable_late_fee": 0, "calc_late_fee_buffer_days": 0, "late_fee_percent": 0,
            "created_at": now, "updated_at": now,
        })
        created = self.contract_fixtures.create(row)
        self._declare_created("contract", created["id"], viewer)
        return {"success": True, "data": project_contract(created)}

    # ── jgb2-req#21（contract: proposed）──────────────────────────────────

    def _assistant_create_bill(self, data: "dict[str, Any]") -> TransportResponse:
        """`POST /bills/manual`（手動帳單）——jgb2-req#21，contract: proposed。**照使用者給的值**。

        必填：`contract_id`／`title`／`total`／`date_expire`（YYYY-MM-DD）。合約不是本團隊的、
        或這位成員看不到 ⇒ 折疊 404。新帳單 `type=3`（新增帳單）、`status=1`（待發送）。
        """
        self._require(self.fixtures, "assistant_create_bill")
        ident, err = self._write_guard(data, self._BILL_BODY_KEYS)
        if err:
            return err
        role_id, viewer = ident
        for key in ("contract_id", "title", "total", "date_expire"):
            if data.get(key) in (None, ""):
                return self._error(400, f"{key} 為必填參數")
        contract = self._usable_contract(data["contract_id"], role_id, viewer)
        if contract is None:
            return self._fold()
        title, sub_title, total = data["title"], data.get("sub_title"), data["total"]
        if not isinstance(title, str) or not title.strip() or len(title) > 60:
            return self._error(422, "title 必須為 1～60 字的文字")
        if sub_title is not None and (not isinstance(sub_title, str) or len(sub_title) > 100):
            return self._error(422, "sub_title 必須為 100 字以內的文字")
        if isinstance(total, bool) or not isinstance(total, (int, float)) or not 0 < total <= 9_999_999:
            return self._error(422, "total 必須為 0～9,999,999 之間大於 0 的數字")
        expire = self._parse_ymd(data["date_expire"])
        if expire is None:
            return self._error(422, "date_expire 必須為 YYYY-MM-DD")
        now = self._PROPOSED_NOW
        # 金額欄位照 jgb2 投影語義（null 壓成 0）取 `_bill_defaults` 的浮點預設；其餘欄位留 None。
        # ⚠️ 不直接寫金額欄位名：`make audit` 不變量 7 規定 services/jgb/ 的金額欄位走語義層。
        row: "dict[str, Any]" = {k: None for k in EXTERNAL_BILL_FIELDS}
        row.update({k: v for k, v in _bill_defaults().items() if isinstance(v, float)})
        row.update({
            "id": max([b["id"] for b in self.fixtures.rows()], default=0) + 1,
            "contract_id": contract["id"], "estate_id": contract.get("estate_id"),
            "type": 3, "category": 3, "status": 1, "bit_status": 1,
            "title": title, "sub_title": sub_title or "", "currency": "TWD",
            "total": total, "rate": 1.0,
            "date_expire": int(expire.strftime("%Y%m%d")),
            "is_auto_pay": False, "invoice_status": 0, "is_archived": False,
            "created_at": now, "updated_at": now,
        })
        created = self.fixtures.create(row)
        self._declare_created("bill", created["id"], viewer)
        return {"success": True, "data": dict(created)}

    # ── jgb2-req#22（contract: proposed）：擴充既有 POST /repairs ───────────

    def _assistant_repair_checks(self, data: "dict[str, Any]") -> "Optional[TransportResponse]":
        """提案契約對 `POST /repairs` 的加碼檢查（jgb2-req#22／#23，contract: proposed）。

        只在載入了 `assistant_demo` 段時啟用——其他 fixture 的既有行為一字不動。檢查順序：
        歸屬／未知欄位 422 → 身分 → 物件歸屬（折疊 404）→ 照片中繼資料。
        `broken_photos` 的提案形狀：`[{filename, content_type, size, sha256}]`（上傳本體走
        multipart／預簽上傳，見接口 A／F10；`Transport` 只傳 JSON，故替身驗中繼資料）。
        """
        cfg = self._assistant_cfg
        ident, err = self._write_guard(data, self._REPAIR_BODY_KEYS)
        if err:
            return err
        role_id, viewer = ident
        if self._usable_estate(data.get("estate_id"), role_id, viewer) is None:
            return self._fold()
        if (data.get("contract_id") is not None
                and self._usable_contract(data["contract_id"], role_id, viewer) is None):
            return self._fold()
        photos = data.get("broken_photos")
        if photos in (None, []):
            return None
        policy = cfg["endpoints"]["jgb2-req#22"]["photo_policy"]
        if not isinstance(photos, list) or len(photos) > self.REPAIR_PHOTO_MAX_COUNT:
            return self._error(422, f"broken_photos 最多 {self.REPAIR_PHOTO_MAX_COUNT} 張")
        for p in photos:
            if (not isinstance(p, dict) or set(p) != {"filename", "content_type", "size", "sha256"}
                    or not isinstance(p["filename"], str) or not p["filename"]
                    or len(p["filename"]) > 100
                    or p["content_type"] not in policy["content_types"]
                    or isinstance(p["size"], bool) or not isinstance(p["size"], int)
                    or not 0 < p["size"] <= policy["max_bytes"]
                    or not isinstance(p["sha256"], str)
                    or not re.fullmatch(r"[0-9a-f]{64}", p["sha256"])):
                return self._error(422, "broken_photos 每張須為 {filename, content_type, size, sha256}，"
                                        "型別為 jpeg／png／webp 且 ≤ 5 MB")
        return None
