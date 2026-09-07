"""
JGB System API 服務

JGB 好租寶外部 API 的 client 封裝，支援 mock/real 模式切換。
提供查詢方法：帳單、發票、合約、點交資格、繳費紀錄、修繕、租客摘要等。

環境變數：
- JGB_API_BASE_URL: JGB API base URL
- JGB_API_KEY: API Key
- USE_MOCK_JGB_API: mock/real 切換（預設 true）
"""

import os
import re
import logging
from typing import Any, Optional

from services.jgb.contract_fixtures import ContractFixtureTable
from services.jgb.estate_fixtures import (
    ALLOWED_SORT_FIELDS,
    DEFAULT_PER_PAGE as ESTATE_DEFAULT_PER_PAGE,
    MAX_PER_PAGE as ESTATE_MAX_PER_PAGE,
    EstateFixtureTable,
    project_estate,
)
from services.jgb.fixtures import BillFixtureTable
from services.jgb.meter_fixtures import MeterFixtureTable
from services.jgb.repair_fixtures import RepairFixtureTable
from services.jgb.team_fixtures import TeamMemberFixtureTable
from services.jgb.transport import (  # noqa: F401  (FALLBACK_MESSAGE 對外沿用)
    FALLBACK_MESSAGE,
    JGBMockTransport,
    MissingCredentialError,
    RealHttpTransport,
    Transport,
    TransportResponse,
    UnexpectedRealNetworkError,
)

logger = logging.getLogger(__name__)

# 降級回答訊息（FALLBACK_MESSAGE 已隨 _send 下移至 services/jgb/transport.py）
DEGRADED_MESSAGE = "請先登入以查詢您的個人資料。"


class JGBSystemAPI:
    """JGB External API Client（mock/real 切換）"""

    def __init__(self):
        self.api_base_url = os.getenv(
            "JGB_API_BASE_URL", "https://www.jgbsmart.com"
        )
        self.api_key = os.getenv("JGB_API_KEY", "")
        self.use_mock = os.getenv("USE_MOCK_JGB_API", "true").lower() == "true"
        self.timeout = 10.0

        # 任務 4.1：只依賴 Transport Protocol，不直接碰 httpx。
        # mock transport 於 4.2–4.5 裝配；在那之前 mock 模式**不會**走到 _send
        # （22 個公開方法皆有 `if self.use_mock` 前置短路），
        # 故此處留 None，並由 _send 對「mock 模式卻走到真實網路」fail loudly。
        #
        # ⚠️ **agent-write-tools W1b／S-5：real transport 只在 `use_mock=False`
        # 時才建構**，而它的建構期會對空憑證 `raise MissingCredentialError`。
        # 於是「接真 API 卻沒帶 `JGB_API_KEY`」在**建構當下**就炸，⛔ 不會變成
        # 每一次呼叫都被 `_fallback_response()` 折成「暫時無法取得資料」的靜默降級。
        # mock 模式留 `None`：那條路本來就不該有 real transport（`_send` 的
        # `use_mock` 分支根本不碰它），⛔ 不為了「欄位總是有值」而先建一個。
        self._real_transport: Optional[Transport] = (
            None if self.use_mock
            else RealHttpTransport(self.api_base_url, self.api_key, self.timeout)
        )
        #: 4.3：mock 模式裝配替身；fixture 表由 4.4 提供，未裝配前「已遷移」端點
        #: 一律 MissingFixtureError——**任何失敗都不會退回 real transport**。
        #: transport-extension-full-coverage：唯一資料來源是
        #: `services/jgb/fixture_data/demo_vendor4.json`（見 `services/jgb/fixture_store.py`）；
        #: bills／bill_detail／contracts／estates／estate_detail／meters／team_members／
        #: member_permissions／repairs／repair_categories／四個寫入路徑皆已遷入 transport
        #: （見 `services/jgb/transport.py` 的 `MIGRATED_ENDPOINTS`）。
        #: ⚠️ `self._estate_fixtures` 是**唯一** EstateFixtureTable 實例，同時供
        #: estates／estate_detail 端點共用——避免同一份物件資料出現兩份互不同步的拷貝。
        self._estate_fixtures = EstateFixtureTable()
        self._meter_fixtures = MeterFixtureTable()
        self._team_fixtures = TeamMemberFixtureTable()
        self._repair_fixtures = RepairFixtureTable()
        self._mock_transport: Optional[Transport] = (
            JGBMockTransport(
                BillFixtureTable(), ContractFixtureTable(),
                estate_fixtures=self._estate_fixtures,
                meter_fixtures=self._meter_fixtures,
                team_fixtures=self._team_fixtures,
                repair_fixtures=self._repair_fixtures,
            )
            if self.use_mock else None
        )

        logger.info(
            f"JGBSystemAPI 初始化 "
            f"(base_url={self.api_base_url}, use_mock={self.use_mock})"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_identity(role_id: Optional[str], user_id: Optional[str]) -> bool:
        """Check that both role_id and user_id are non-empty."""
        return bool(role_id) and bool(user_id)

    @staticmethod
    def _degraded_response() -> dict[str, Any]:
        return {
            "success": False,
            "error": {"code": 401, "message": DEGRADED_MESSAGE},
        }

    @staticmethod
    def _fallback_response(error_detail: str) -> dict[str, Any]:
        return {
            "success": False,
            "error": {"code": 500, "message": FALLBACK_MESSAGE},
        }

    async def _send(
        self, method: str, path: str, *,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> TransportResponse:
        """依 `use_mock` 派發至 transport 實作（任務 4.1）。

        ⚠️ mock 模式下若未裝配 mock transport，**fail loudly**——
        絕不 fallback 至真實 HTTP（靜默 fallback 的失效模式是
        integration 測試對 jgb2 發出真請求）。
        """
        if self.use_mock:
            if self._mock_transport is None:
                raise UnexpectedRealNetworkError(
                    f"use_mock=True 但未裝配 mock transport：{method} {path}"
                )
            return await self._mock_transport.send(
                method, path, params=params, data=data
            )
        if self._real_transport is None:
            # 只有「建構時是 mock、事後被改成 real」才會走到這裡（測試替身）。
            # ⛔ 不在此臨時建一個 real transport——那等於繞過建構期的憑證守門。
            raise UnexpectedRealNetworkError(
                f"use_mock=False 但未裝配 real transport：{method} {path}"
            )
        return await self._real_transport.send(
            method, path, params=params, data=data
        )

    async def _request(
        self, path: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Send GET request to JGB API."""
        return await self._send("GET", path, params=params)

    async def _post_request(
        self, path: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Send POST request to JGB API with JSON body."""
        return await self._send("POST", path, data=data)

    async def _patch_request(
        self, path: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Send PATCH request to JGB API with JSON body（agent 寫入路徑，任務 transport-extension-full-coverage）。"""
        return await self._send("PATCH", path, data=data)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_bills(
        self,
        role_id: str,
        user_id: str = None,
        month: Optional[str] = None,
        status: Optional[str] = None,
        contract_ids: Optional[str] = None,
        bill_ref: Optional[str] = None,
        viewer_user_id: Optional[str] = None,
        keyword: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """查詢帳單列表。

        授權形態：
          - 租客情境（既有）：role_id + user_id（身分保護，缺一降級）；
          - b2b per-contract / per-bill：role_id + contract_ids 或 bill_ref——
            與 get_contracts 相同以 role_id 為授權主體，不需 user_id。

        `viewer_user_id`（agentic-mcp-orchestration 任務 1.5）：jgb2 端 `viewer_user_id`
        圈定顯式轉發（原被 `**kwargs` 吞掉、從未送達 API）；非空才放進 params，
        照 `get_bill_visibility` 先例。⚠️ mock 對本參數保留 `UnsupportedMockParameterError`
        大聲失敗（`services/jgb/transport.py:_bills_index`）——這是刻意設計，不得放寬。

        `bill_ref` 識別語意參數（adapter，billing-conversational-facets R2.1）：
          純數字 → 先 get_bill_detail 直查（單筆包成列）；查無 → 當合約 id 解析；
          非數字 → get_contracts(keyword) 解析 → 取第一筆合約 → 該合約帳單列候選。
          解析失敗/例外 → 空列不拋（引擎走 0 筆追問路，不炸降級句）。
        """
        if not (self._validate_identity(role_id, user_id)
                or (role_id and (contract_ids or bill_ref))):
            return self._degraded_response()

        # ⚠️ 任務 4.6：**已移除** `if self.use_mock: return self._mock_get_bills(...)`
        #   目的是讓 bill_ref adapter、參數組裝、client 端防衛過濾在測試中**真的執行**，
        #   mock 改由 `_send` 依 `use_mock` 派發至 `JGBMockTransport`（4.1–4.5）。
        #   ⚠️ **混合邊界狀態**：下方非數字分支呼叫 `get_contracts`，而 `jgb_contracts`
        #      **尚未遷移**（仍走方法級 mock）→ 本階段端到端執行的只有**數字分支**；
        #      **不得**聲稱 adapter 已全分支證實。
        # bill_ref 識別解析（後端當裁判：逐層試、命中即止）
        if bill_ref is not None and contract_ids is None:
            ref = str(bill_ref).strip()
            try:
                if ref.isdigit():
                    detail = await self.get_bill_detail(role_id, int(ref))
                    row = (detail or {}).get("data")
                    if (detail or {}).get("success") and isinstance(row, dict) and row:
                        return {"success": True,
                                "mapping": (detail or {}).get("mapping", {}),
                                "data": [row]}
                    contracts = await self.get_contracts(role_id, contract_ids=ref)
                else:
                    contracts = await self.get_contracts(role_id, keyword=ref)
                rows = (contracts or {}).get("data") or []
                if not ((contracts or {}).get("success") and rows):
                    return {"success": True, "data": []}
                contract_ids = rows[0].get("id")
            except Exception as e:
                logger.warning(f"bill_ref 識別解析失敗（回空列降級）：{e}")
                return {"success": True, "data": []}

        params: dict[str, Any] = {"role_id": role_id}
        if user_id:
            params["user_id"] = user_id
        if contract_ids:
            # ⚠️ /bills 的合約過濾參數是 contract_id（單數）——複數會被上游無視、
            #    整個 role 帳單全回（帳單診斷 e2e 實測 50 筆電錶儲值蓋台）。
            params["contract_id"] = contract_ids
        if month:
            params["month"] = month
        if status:
            params["status"] = status
        if viewer_user_id:
            params["viewer_user_id"] = viewer_user_id
        if keyword not in (None, ""):
            params["keyword"] = str(keyword)
        resp = await self._request("/api/external/v1/bills", params)
        # client 端防衛過濾（上游再無視參數也擋得住；沿 get_contracts 過濾先例）：
        # 只在列上帶 contract_id 時啟動，舊形狀列不受影響。
        if contract_ids and (resp or {}).get("success"):
            rows = resp.get("data") or []
            if any(r.get("contract_id") is not None for r in rows if isinstance(r, dict)):
                resp["data"] = [r for r in rows
                                if str(r.get("contract_id")) == str(contract_ids)]
        return resp

    async def get_invoices(
        self,
        role_id: str,
        user_id: str = None,
        bill_id: Optional[int] = None,
        status: Optional[int] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """查詢發票列表。

        授權形態：租客情境 role_id+user_id（既有）；
        b2b per-bill（發票面向 secondary_call）：role_id+bill_id，不需 user_id。
        """
        if not (self._validate_identity(role_id, user_id) or (role_id and bill_id)):
            return self._degraded_response()

        if self.use_mock:
            return self._mock_get_invoices(role_id, user_id, bill_id, status)

        params: dict[str, Any] = {"role_id": role_id}
        if user_id:
            params["user_id"] = user_id
        if bill_id is not None:
            params["bill_id"] = bill_id
        if status is not None:
            params["status"] = status
        return await self._request("/api/external/v1/invoices", params)

    async def get_contracts(
        self,
        role_id: str,
        user_id: str = None,
        contract_ids: str = None,
        keyword: str = None,
        status: Optional[str] = None,
        viewer_user_id: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """查詢合約狀態總覽

        `viewer_user_id`（agentic-mcp-orchestration 任務 1.5）：同 `get_bills`，
        顯式轉發（原被 `**kwargs` 吞掉）；非空才放進 params。目前 mock
        `_contracts_index` 未對此參數設防（不 raise、單純忽略）——圈定語義
        本機不可驗，只驗轉發，真圈定效果留 M3 後線上 e2e（domain 映射表）。
        """
        if not role_id:
            return self._degraded_response()

        # ⚠️ 方法級短路已移除（transport-extension）：contracts 已遷入 JGBMockTransport，
        #    第二次依識別重查才會真的收斂——那正是要驗的 execution 行為，
        #    不得再被恆回全部的方法級 mock 吃掉。`_mock_get_contracts` 保留供其他呼叫點。
        params: dict[str, Any] = {"role_id": role_id}
        if contract_ids:
            params["contract_ids"] = contract_ids
        if keyword:
            params["keyword"] = keyword
        if viewer_user_id:
            params["viewer_user_id"] = viewer_user_id
        result = await self._request(
            "/api/external/v1/contracts/status-overview", params
        )

        # 查無 fallback（多輪回測 run295/296 逼出）：合約 title 格式不一致——
        # 「重慶北137-503」（無前綴）與「台北大同-重慶北5-304」（帶前綴）並存，
        # 業者用物件全名查 → server LIKE 恆查無。沿 get_meters 先例：
        # 以最長 token 重查放寬命中面，client 端全 token 去分隔符 AND 過濾。
        rows = (result or {}).get("data") or []
        if not rows and keyword:
            _sep = re.compile(r"[\s　\-/,，]+")
            tokens = [_sep.sub("", t) for t in re.split(r"[的之在 　,，/\-]+", str(keyword)) if t]
            if len(tokens) >= 2:                              # 可拆才放寬（單詞查無不亂擴）
                widest = max(tokens, key=len)
                retry_params = dict(params)
                retry_params["keyword"] = widest
                retry = await self._request(
                    "/api/external/v1/contracts/status-overview", retry_params
                )
                cand = (retry or {}).get("data") or []

                q_joined = "".join(tokens)

                def _hit(c):
                    title = str(c.get("title") or "")
                    joined = _sep.sub("", title)
                    # 雙向包含：查詢 tokens 全在候選（口語少於存值）
                    # 或候選 tokens 全在查詢（存值無前綴、查詢帶物件全名——run296 實案）
                    if all(t in joined for t in tokens if t):
                        return True
                    c_tokens = [_sep.sub("", t) for t in re.split(r"[的之在 　,，/\-]+", title) if t]
                    return bool(c_tokens) and all(t in q_joined for t in c_tokens)
                filtered = [c for c in cand if _hit(c)]
                return {**(retry or {}), "success": True, "data": filtered}
        return result

    async def get_contract_checkin_eligibility(
        self,
        role_id: str,
        user_id: str,
        contract_id: int,
        **kwargs,
    ) -> dict[str, Any]:
        """查詢合約點交資格"""
        if not self._validate_identity(role_id, user_id):
            return self._degraded_response()

        if self.use_mock:
            return self._mock_get_contract_checkin_eligibility(
                role_id, user_id, contract_id
            )

        params: dict[str, Any] = {"role_id": role_id, "user_id": user_id}
        return await self._request(
            f"/api/external/v1/contracts/{contract_id}/checkin-eligibility",
            params,
        )

    async def get_payments(
        self,
        role_id: str,
        user_id: str,
        month: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """查詢繳費紀錄"""
        if not self._validate_identity(role_id, user_id):
            return self._degraded_response()

        if self.use_mock:
            return self._mock_get_payments(role_id, user_id, month)

        params: dict[str, Any] = {"role_id": role_id, "user_id": user_id}
        if month:
            params["month"] = month
        return await self._request("/api/external/v1/payments", params)

    async def get_repairs(
        self,
        role_id: str,
        user_id: str,
        status: Optional[str] = None,
        estate_id: Optional[str] = None,
        category_id: Optional[str] = None,
        is_urgent: Optional[str] = None,
        keyword: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """查詢修繕進度"""
        if not self._validate_identity(role_id, user_id):
            return self._degraded_response()

        # transport-extension-full-coverage（單一來源徹底）：已移除方法級
        # `_mock_get_repairs` 分支——mock 改由 `_send` 派發至 `JGBMockTransport`
        # （`repairs` 已遷入 `MIGRATED_ENDPOINTS`，資料來源為共用 `RepairFixtureTable`）。
        params: dict[str, Any] = {"role_id": role_id, "user_id": user_id}
        if status:
            params["status"] = status
        if estate_id:
            params["estate_id"] = estate_id
        if category_id:
            params["category_id"] = category_id
        if is_urgent:
            params["is_urgent"] = is_urgent
        if keyword:
            params["keyword"] = keyword
        return await self._request("/api/external/v1/repairs", params)

    async def get_tenant_summary(
        self,
        role_id: str,
        user_id: str,
        **kwargs,
    ) -> dict[str, Any]:
        """查詢租客摘要"""
        if not self._validate_identity(role_id, user_id):
            return self._degraded_response()

        if self.use_mock:
            return self._mock_get_tenant_summary(role_id, user_id)

        params: dict[str, Any] = {"role_id": role_id}
        return await self._request(
            f"/api/external/v1/tenants/{user_id}/summary", params
        )

    async def get_estates(
        self,
        role_id: str,
        keyword: str = "",
        per_page: int = 10,
        **kwargs,
    ) -> dict[str, Any]:
        """搜尋物件"""
        if not role_id:
            return self._degraded_response()

        # transport-extension-full-coverage（單一來源徹底）：已移除方法級
        # （`estates` 已遷入 `MIGRATED_ENDPOINTS`，與 `get_estate_status`／
        # `get_estate_detail` 共用同一個 `self._estate_fixtures` 實例）。
        params: dict[str, Any] = {
            "role_id": role_id,
            "keyword": keyword,
            "per_page": per_page,
        }
        # `applyFilters()` 其餘參數（use_for／sort_by／sort_direction／status／
        # city_id／district_id／rent_min／rent_max／page／user_id 等）原樣透傳——
        # transport 端 `_estates_index` 自行判斷合法值，本層不重複做白名單。
        for k, v in kwargs.items():
            if v is not None:
                params[k] = v
        return await self._request("/api/external/v1/estates", params)

    async def get_repair_categories(
        self,
        **kwargs,
    ) -> dict[str, Any]:
        """取得修繕分類樹（不需要 role_id）"""
        # transport-extension-full-coverage（單一來源徹底）：已移除方法級
        # `_mock_get_repair_categories` 分支——mock 改由 `_send` 派發至
        # `JGBMockTransport`（`repair_categories` 已遷入 `MIGRATED_ENDPOINTS`）。
        return await self._request(
            "/api/external/v1/repairs/categories", {}
        )

    async def create_repair(
        self,
        role_id: str,
        estate_id: int,
        category_id: int,
        item_id: int,
        broken_reason: str,
        broken_note: str = "",
        emergency_status: int = 1,
        contract_id: Optional[int] = None,
        broken_photos: Optional[list] = None,
        idempotency_key: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """建立修繕單

        transport-extension-full-coverage：**已移除** `if self.use_mock:
        return self._mock_create_repair(...)` 短路——mock 改由 `_send` 依
        `use_mock` 派發至 `JGBMockTransport`（`create_repair` 已遷入
        `MIGRATED_ENDPOINTS`，資料來源為共用 `RepairFixtureTable`）。

        `idempotency_key`（agent-write-tools W4）：非空才放進 body——同一把 key
        重送 ⇒ 下游回同一份 receipt、不重複建單（替身端見
        `services/jgb/transport.py:_with_idempotency`）。⚠️ `Transport.send()`
        沒有 header 通道，`Idempotency-Key` 因此走 body，這是協定本身的限制，
        ⛔ 不是把冪等鍵當成一般業務欄位。
        """
        if not role_id:
            return self._degraded_response()

        data: dict[str, Any] = {
            "role_id": role_id,
            "estate_id": estate_id,
            "category_id": category_id,
            "item_id": item_id,
            "broken_reason": broken_reason,
            "broken_note": broken_note,
            "emergency_status": emergency_status,
        }
        if contract_id is not None:
            data["contract_id"] = contract_id
        if broken_photos:
            data["broken_photos"] = broken_photos
        if idempotency_key:
            data["idempotency_key"] = idempotency_key
        return await self._post_request("/api/external/v1/repairs", data)

    async def agent_patch_bill_due_date(
        self,
        bill_id: Any,
        date_expire: str,
        *,
        idempotency_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """`PATCH /agent/v1/bills/{id}`：**只改到期日**（agent-write-tools W4）。

        ⚠️ 這支端點刻意只收 `due_date`：`PATCH` 一個帳單資源本身可以改很多欄位，
        但 agent 這條路只被授權改一件事，於是**能送出去的形狀本身**就把授權範圍
        表達出來（替身端 `_patch_bill` 對投影外欄位一律 422）。
        ⛔ 不在此加第二個可寫欄位——加欄位是正本（design 元件 3）的事。

        `date_expire`：`YYYY-MM-DD`。⛔ 不接受位移天數：使用者確認的是一個確定的
        日期，位移在下游重算一次就多一個「算出不同結果」的機會。

        ⚠️ **demo 期只有替身 transport 走得通**（`USE_MOCK_JGB_API=true`）；
        真 `agent/v1` 的簽章 client 與憑證不在本切片（Plan §2 非目標／S-3 DEFER）。
        """
        data: dict[str, Any] = {"due_date": date_expire}
        if idempotency_key:
            data["idempotency_key"] = idempotency_key
        return await self._patch_request(f"/agent/v1/bills/{bill_id}", data)

    # ------------------------------------------------------------------
    # v1.1 診斷用端點
    # ------------------------------------------------------------------

    async def get_bill_detail(
        self,
        role_id: str,
        bill_id: int,
        **kwargs,
    ) -> dict[str, Any]:
        """查詢單一帳單詳情（含 pay_info + details）"""
        if not role_id:
            return self._degraded_response()

        # ⚠️ 任務 4.6：**已移除** `if self.use_mock: return self._mock_get_bill_detail(...)`
        #   （理由同 get_bills；mock 改由 transport 層依契約回應）
        params: dict[str, Any] = {"role_id": role_id}
        return await self._request(
            f"/api/external/v1/bills/{bill_id}", params
        )

    async def get_payment_logs(
        self,
        role_id: str,
        payment_id: Optional[int] = None,
        bill_id: Optional[int] = None,
        transaction_id: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """查詢某張帳單的付款紀錄與金流日誌（`GET /payment-logs`）。

        **2026-08-25 盤查修正**：

        * production **要求 `role_id` 與 `bill_id` 皆必填**（缺任一即 400）。舊版允許
          只帶 role_id／payment_id ⇒ 線上必然 400，mock 卻回得漂亮。改為缺 bill_id
          即降級，不發那個注定失敗的請求。
        * `payment_id`／`transaction_id` **production 完全不讀**（controller 只取
          role_id 與 bill_id）。保留簽名以相容既有呼叫端，但**不再送出**。
        * 回應信封是 `{bill_id, payments, payment_logs, summary}`，**沒有 `data`**，
          而 `jgb_response_formatter` → `diagnose_payment_logs` 讀的是 `data`。
          在此做 adapter 層正規化：`data` = `payment_logs` 逐列（值全部來自回應本身，
          不補欄位），並帶出 `payments`／`summary`／`bill_id`。
          ⚠️ 這是**正規化**不是捏造。
        """
        if not role_id or bill_id in (None, ""):
            return self._degraded_response()

        if self.use_mock:
            raw = self._mock_get_payment_logs(role_id, payment_id, bill_id)
        else:
            raw = await self._request("/api/external/v1/payment-logs",
                                      {"role_id": role_id, "bill_id": bill_id})
        if not (raw or {}).get("success"):
            return {"success": False, "data": []}

        logs = raw.get("payment_logs")
        payments = raw.get("payments")
        return {
            "success": True,
            "data": logs if isinstance(logs, list) else [],
            "payments": payments if isinstance(payments, list) else [],
            "summary": raw.get("summary") or {},
            "bill_id": raw.get("bill_id"),
        }

    async def get_invoice_logs(
        self,
        role_id: str,
        invoice_id: Optional[int] = None,
        bill_id: Optional[int] = None,
        action: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """查詢發票開立/作廢的 API 日誌"""
        if not role_id:
            return self._degraded_response()

        if invoice_id in (None, "") and bill_id in (None, ""):
            # production：bill_id 或 invoice_id 至少一個，皆缺即 400（:23-25）
            return self._degraded_response()

        if self.use_mock:
            return self._mock_get_invoice_logs(role_id, invoice_id, bill_id, action)

        params: dict[str, Any] = {"role_id": role_id}
        if invoice_id is not None:
            params["invoice_id"] = invoice_id
        if bill_id is not None:
            params["bill_id"] = bill_id
        if action:
            params["action"] = action
        return await self._request("/api/external/v1/invoice-logs", params)

    async def get_tenant_registration(
        self,
        role_id: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """G-A1：查此團隊名下租客的註冊/綁定狀態（登入排障歸屬閘門）。

        授權：role_id 綁定＋伺服器端只回名下租客（found:false 防枚舉，jgb2 已擋）。
        email/phone 至少一（缺則降級不打）；回應單一物件正規化為單元素 list，
        供 secondary_call（list_path='data'）附掛。個資欄位（name/user_id）由消費端不輸出。
        """
        email = (email or "").strip()
        phone = (phone or "").strip()
        if not role_id or not (email or phone):
            return self._degraded_response()

        if self.use_mock:
            return self._mock_get_tenant_registration(role_id, email, phone)

        params: dict[str, Any] = {"role_id": role_id}
        if email:
            params["email"] = email
        if phone:
            params["phone"] = phone
        raw = await self._request("/api/external/v1/tenants/registration-status", params)
        # 單一物件 → 單元素 list（secondary_call 只吃 list）；失敗/無 data 則空 list
        data = (raw or {}).get("data")
        return {"success": bool((raw or {}).get("success")),
                "data": [data] if isinstance(data, dict) else []}

    def _mock_get_tenant_registration(self, role_id, email, phone) -> dict[str, Any]:
        return {"success": True, "data": [{
            "found": True, "is_bound": True, "is_registered": True,
            "lessee_email_verify_status": 1, "lessee_user_id": 0, "lessee_name": ""}]}

    async def get_team_members(
        self,
        role_id: str,
        keyword: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """T1：以 email/名字查此團隊成員（團隊權限面向識別）。

        授權：role_id 綁定＋只回該 role 成員（防枚舉，jgb2 已擋）。
        回應 data 為 list（成員候選：member_user_id/character_name/is_owner/match_field，無明文個資）。
        """
        keyword = str(keyword).strip() if keyword is not None else ""   # 候選 refine 帶 int id 容錯
        if not role_id or not keyword:
            return self._degraded_response()
        # transport-extension-full-coverage：已移除 `if self.use_mock: return
        # self._mock_team_members(...)` 短路——mock 改由 `_send` 派發至
        # `JGBMockTransport`（`team_members` 已遷入 `MIGRATED_ENDPOINTS`）。
        raw = await self._request(
            f"/api/external/v1/roles/{role_id}/members", {"keyword": keyword})
        data = (raw or {}).get("data")
        return {"success": bool((raw or {}).get("success")),
                "data": data if isinstance(data, list) else []}

    async def get_member_permissions(
        self,
        role_id: str,
        user_id: str,
        **kwargs,
    ) -> dict[str, Any]:
        """步驟 3：查成員角色能力旗標（G-A2；32 旗標含成對 show_owner_*）。

        回應正規化為單元素 list（供 secondary_call list_path='data'）：
        {character_name, abilities:{show_bill,show_owner_bill,...}}。
        """
        if not role_id or not user_id:
            return self._degraded_response()
        # transport-extension-full-coverage：已移除 `if self.use_mock: return
        # self._mock_member_permissions(...)` 短路——理由同 `get_team_members`。
        raw = await self._request(
            f"/api/external/v1/roles/{role_id}/members/{user_id}/permissions", {})
        data = (raw or {}).get("data")
        return {"success": bool((raw or {}).get("success")),
                "data": [data] if isinstance(data, dict) else []}

    # ⚠️ `_ABILITY_WHITELIST`／`_TEAM_MEMBERS`／`_mock_team_members`／
    #    `_mock_member_permissions` 已移除（transport-extension-full-coverage）：
    #    `get_team_members`／`get_member_permissions` 現一律經 `_send` →
    #    `JGBMockTransport`，資料與能力白名單改由共用 `services/jgb/team_fixtures.py`
    #    （`TeamMemberFixtureTable`／`ABILITY_WHITELIST`）供應，唯一來源見 fixture_store。

    async def get_bill_visibility(
        self,
        role_id: str,
        viewer_user_id: str,
        bill_id: str,
        **kwargs,
    ) -> dict[str, Any]:
        """T2：某成員視角下這張帳單可不可見（viewer 圈定＋單筆過濾）。

        走列表端點帶 viewer_user_id＋bill_id（非 /bills/{id}，那支不套 viewer 圈定）：
        回結果非空＝看得到、空＝看不到。data 為 list（供 secondary_call）。
        """
        if not (role_id and viewer_user_id and bill_id):
            return self._degraded_response()
        if self.use_mock:
            # ⚠️ mock **不回答可見性**（2026-08-25 盤查改判）。
            # production 的圈定來自 viewer_user_id → ExternalViewerScope → VisibleScope::resolve
            # → Bill::queryThisUser，依 roleType 與 show_* 權限旗標過濾 owner_role_id／
            # issue_target_role_id 等**非投影欄位**，替身射程外（見 transport 的 GAP 說明）。
            # 舊版在此回 {"success": True, "data": []} ＝ **捏造一個「看不到」**，
            # 而 accounts.build_team_permission_facts 會把它當事實講給使用者。
            # 改回降級：secondary attach 只在 success 時掛，故面向自然走「未確認具體資源」措辭。
            return self._degraded_response()
        raw = await self._request("/api/external/v1/bills",
                                  {"role_id": role_id, "viewer_user_id": viewer_user_id,
                                   "bill_id": bill_id})
        data = (raw or {}).get("data")
        return {"success": bool((raw or {}).get("success")),
                "data": data if isinstance(data, list) else []}

    async def get_subscription(
        self,
        role_id: str,
        **kwargs,
    ) -> dict[str, Any]:
        """查詢團隊的訂閱方案與物件額度"""
        if not role_id:
            return self._degraded_response()

        if self.use_mock:
            return self._mock_get_subscription(role_id)

        return await self._request(
            f"/api/external/v1/roles/{role_id}/subscription", {}
        )

    async def get_meters(
        self,
        role_id: str,
        keyword: Optional[str] = None,
        estate_id: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """電表列表（IoT 電表排障識別 adapter）。

        ⚠️ **舊註解說「端點無 keyword 參數」是錯的**（2026-08-25 盤查）：
        `MeterApiController@index:41-56` 有 `keyword`，比對 `iots.name` **或**
        綁定物件的 `estates.title`（皆 LIKE，且 estates 需 active=1）。
        本 adapter 仍**刻意**改走 client 端過濾——理由不是端點沒有，而是端點的
        整串 LIKE 對口語多詞配不中（真資料 e2e 逼出），需要 token 化比對。
        故維持拉全頁（per_page=200，正好是 MAX_PER_PAGE）後自行過濾；estate_id 原生透傳。
        欄位：is_online/is_poweron/balance/available_meter/current_reading/synced_at 等
        （消費端注意：離線時皆為最後同步快照；is_poweron 三態失真見 J-I1，builder 端防護）。
        """
        if not role_id:
            return self._degraded_response()

        # transport-extension-full-coverage：已移除 `if self.use_mock: rows = [...]`
        # 硬編分支——mock 改由 `_send` 派發至 `JGBMockTransport`（`meters` 已遷入
        # `MIGRATED_ENDPOINTS`，資料來源為共用 `MeterFixtureTable`，三列涵蓋
        # `meter_type`／`is_poweron` 三態等既有保真斷言）。
        params: dict[str, Any] = {"role_id": role_id, "per_page": 200}
        if estate_id:
            params["estate_id"] = estate_id
        raw = await self._request("/api/external/v1/meters", params)
        if not (raw or {}).get("success"):
            return {"success": False, "data": []}
        data = raw.get("data")
        rows = data if isinstance(data, list) else []

        kw = str(keyword).strip() if keyword is not None else ""   # 候選 refine 帶 int id 容錯
        if kw:
            # token 化過濾（真資料 e2e 逼出）：口語「新莊富貴500的14B05」對
            # estate_name「新北新莊-富貴500-14B05」整串 substring 配不中——
            # 以虛詞拆 token，比對時兩邊都去分隔符（口語常省略 '-'），
            # 全部 token 命中（AND）estate_name+name 聯合字串才算。
            _sep = re.compile(r"[\s　\-/,，]+")
            tokens = [_sep.sub("", t) for t in re.split(r"[的之在 　,，/\-]+", kw) if t]
            # 純數字 keyword 先當電表 id 直配（候選選定後 refine 以 id 重查）
            if kw.isdigit() and any(str(m.get("id")) == kw for m in rows):
                rows = [m for m in rows if str(m.get("id")) == kw]
            else:
                def _hit(m):
                    joined = _sep.sub("", f"{m.get('estate_name') or ''}｜{m.get('name') or ''}")
                    return all(t in joined for t in tokens if t)
                rows = [m for m in rows if _hit(m)]
        return {"success": True, "data": rows}

    async def get_estate_status(
        self,
        role_id: Optional[str] = None,
        keyword: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """物件現況診斷識別 adapter（estate-conversational-facets 任務 1.1）。

        ⚠️ 與 get_estates（修繕報修表單現役）語義不同，勿混用：
        - 拉頁 per_page=200 後 client 端 token 化過濾 title｜display_address
          （API keyword 只搜 title LIKE，口語多詞配不中——get_meters 同款）
        - 過濾後空集回 sentinel [{"found": False, "keyword": kw}]——引擎 0-row
          會硬編「查無資料」短路（conversational_engine.py:610），sentinel 讓
          builder 接手「非刊登中」口徑（design Issue 1；G-A1 found:false 先例）
        - 每列附 status_zh 轉譯欄（候選標籤用；轉譯邏輯在 services/jgb/estates.py）
        - 端點硬過濾 is_open=1（只回刊登中）——「查不到＝非刊登中」為弱信號，
          口徑紅線見 estates.py builder
        """
        from services.jgb.estates import estate_status_zh   # 延遲匯入（分層慣例）

        # transport-extension-full-coverage：已移除 `if self.use_mock: rows = [...]`
        # 分支——mock 改由 `_send` 派發至 `JGBMockTransport`（`estates` 已遷入
        # `self._estate_fixtures` 實例，非兩份互不同步的拷貝）。
        params: dict[str, Any] = {"per_page": 200}
        if role_id:
            params["role_id"] = role_id
        raw = await self._request("/api/external/v1/estates", params)
        if not (raw or {}).get("success"):
            return {"success": False, "data": []}
        data = raw.get("data")
        rows = data if isinstance(data, list) else []

        kw = str(keyword).strip() if keyword is not None else ""   # int 容錯（候選 refine 先例）
        if kw:
            _sep = re.compile(r"[\s　\-/,，]+")
            tokens = [_sep.sub("", t) for t in re.split(r"[的之在 　,，/\-]+", kw) if t]
            if kw.isdigit() and any(str(e.get("id")) == kw for e in rows):
                rows = [e for e in rows if str(e.get("id")) == kw]
            else:
                def _hit(e):
                    joined = _sep.sub("", f"{e.get('title') or ''}｜"
                                          f"{e.get('display_address') or ''}")
                    return all(t in joined for t in tokens if t)
                rows = [e for e in rows if _hit(e)]
        if not rows:
            return {"success": True, "data": [{"found": False, "keyword": kw}]}
        for e in rows:
            e["status_zh"] = estate_status_zh(e.get("status"))
        return {"success": True, "data": rows}

    async def get_estate_detail(
        self,
        estate_id: Any = None,
        **kwargs,
    ) -> dict[str, Any]:
        """物件單筆深查（GET /estates/{id}；含 contract_required_fields）。

        sentinel 列無 id → secondary_call 會帶空值進來：優雅降級回 success:False
        （引擎 attach 失敗即略過，builder 不依賴 detail 存在）。
        單物件正規化為單元素 list（get_tenant_registration 先例）。
        """
        eid = str(estate_id).strip() if estate_id is not None else ""
        if not eid or eid == "None" or not eid.isdigit():
            return {"success": False, "data": []}

        # transport-extension-full-coverage：已移除 `if self.use_mock: ...` 分支——
        # mock 改由 `_send` 派發至 `JGBMockTransport`（`estate_detail` 已遷入
        # `MIGRATED_ENDPOINTS`，`show()` 語義（is_open=1 硬過濾、16 欄
        # contract_required_fields）現由 `JGBMockTransport._estates_show` 提供）。
        raw = await self._request(f"/api/external/v1/estates/{eid}", {})
        if not (raw or {}).get("success"):
            return {"success": False, "data": []}
        data = raw.get("data")
        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            data = []
        return {"success": True, "data": data}

    async def get_tenant_contracts(
        self,
        role_id: str,
        user_id: str,
        **kwargs,
    ) -> dict[str, Any]:
        """查詢租客名下的有效租約清單（含物件資訊，供修繕報修自動預填）。

        契約形狀（conversational-repair research.md 決策 1 / G1）：
          data: [{contract_id, estate_id, estate_title, display_address}]
          （`room` 無來源——見下方投影對映）

        **真端點（2026-08-25 盤查改判）**：走 `GET /contracts/status-overview` 帶 `user_id`。
        production `ContractApiController@index:63-65` 對該參數施加
        `where('to_user_id', (int) user_id)`，語義即「這位租客名下的合約」。
        ⚠️ 原判定「jgb2 尚未提供租客視角端點」（J 清單 G1）**已作廢**——
        該缺口不存在，先前的 `NotImplementedError` 使本方法在真實模式必然拋例外，
        而呼叫端 `repair_prefill._fetch_contracts` 會吞掉例外 → production 的物件預填
        **靜默失效**，且所有 mock 測試皆綠。本次改為真的接上該端點。

        投影對映（`formatContract` 逐鍵 → 預填契約鍵）：
          contract_id ← `id`｜estate_id ← `estate_id`｜estate_title ← `title`
          display_address ← `city` + `district` + `address`（缺段跳過）
          room ← **無來源**：`formatContract` 沒有房號欄位；`_estate_display` 對缺鍵已容忍，
                 故不輸出此鍵，**不得**拿其他欄位假造。

        「有效」的界線在**本 adapter**：production index 只加 `active=1`／`is_newest=1`，
        **不濾歷史合約**；預填一張已歸檔的租約是錯的，故在此濾掉
        `is_history`／`is_history_done`。此為 adapter 語義，不是 API 語義。

        授權：role_id + user_id 雙證，缺一降級（_validate_identity 慣例）。
        """
        if not self._validate_identity(role_id, user_id):
            return self._degraded_response()

        raw = await self._request(
            "/api/external/v1/contracts/status-overview",
            {"role_id": role_id, "user_id": user_id},
        )
        if not raw or not raw.get("success"):
            return {"success": False, "data": []}

        rows = raw.get("data")
        rows = rows if isinstance(rows, list) else []
        active = [r for r in rows
                  if not r.get("is_history") and not r.get("is_history_done")]
        return {"success": True, "data": [self._as_prefill_contract(r) for r in active]}

    @staticmethod
    def _as_prefill_contract(row: "dict[str, Any]") -> "dict[str, Any]":
        """`formatContract` 一列 → 修繕預填契約（對映見 `get_tenant_contracts`）。"""
        return {
            "contract_id": row.get("id"),
            "estate_id": row.get("estate_id"),
            "estate_title": row.get("title"),
            "display_address": "".join(
                str(row.get(k) or "") for k in ("city", "district", "address")
            ),
        }

    async def get_iot_manufacturers(
        self,
        role_id: str,
        **kwargs,
    ) -> dict[str, Any]:
        """查詢團隊的 IoT 廠商綁定狀態"""
        if not role_id:
            return self._degraded_response()

        if self.use_mock:
            return self._mock_get_iot_manufacturers(role_id)

        params: dict[str, Any] = {"role_id": role_id}
        return await self._request(
            "/api/external/v1/iot-manufacturers", params
        )

    # ------------------------------------------------------------------
    # Mock implementations — 對齊 jgb2 External API 真實回應結構
    # ------------------------------------------------------------------

    #: 發票 fixture（`formatInvoice` 逐鍵，26 欄）——**已對照 jgb2 原始碼**（2026-08-25）。
    #: `App\Invoice` **無 $casts、無 accessor**，故所有欄位都是原始欄位值；
    #: 唯一由控制器加工的是 `tax_rate`：`$invoice->tax_rate ? (float) : null`
    #: ⇒ **0 會變成 null**（InvoiceApiController:125）。
    _INVOICE_ROWS: "tuple[dict[str, Any], ...]" = (

            {
                "id": 5001,
                "bill_id": 12345,
                "payment_id": 9876,
                "manufacturer": "ezpay",
                "number": "AZ00000123",
                "random_num": "1234",
                "status": 1,
                "upload_status": 1,
                "category": "B2C",
                "buyer_name": None,
                "buyer_ubn": None,
                "buyer_address": None,
                "buyer_email": "tenant@example.com",
                "carrier_type": None,
                "carrier_number": None,
                "love_code": None,
                "print_flag": "N",
                "tax_type": 1,
                "tax_rate": 0.05,
                "tax_amt": 1190,
                "amt": 23810,
                "total_amt": 25000,
                "item_data": None,
                "bar_code": None,
                "url": None,
                "added_at": "2026-04-01 10:00:00",
                "invalid_at": None,
                "allowanced_at": None,
            },
            {
                "id": 5002,
                "bill_id": 12340,
                "payment_id": 9870,
                "manufacturer": "ezpay",
                "number": "AZ00000120",
                "random_num": "5678",
                "status": 2,
                "upload_status": 1,
                "category": "B2C",
                "buyer_name": None,
                "buyer_ubn": None,
                "buyer_address": None,
                "buyer_email": "tenant@example.com",
                "carrier_type": None,
                "carrier_number": None,
                "love_code": None,
                "print_flag": "N",
                "tax_type": 1,
                "tax_rate": 0.05,
                "tax_amt": 1190,
                "amt": 23810,
                "total_amt": 25000,
                "item_data": None,
                "bar_code": None,
                "url": None,
                "added_at": "2026-03-01 10:00:00",
                "invalid_at": "2026-03-15 10:00:00",
                "allowanced_at": None,
            },
    )

    #: `getMapping()`（:139-160）的三組枚舉，值取自 `App\Invoice` 常數（:9-23）
    _INVOICE_MAPPING: "dict[str, dict[str, str]]" = {
        "status": {"0": "未開立", "1": "已開立", "2": "作廢",
                   "3": "折讓", "4": "作廢折讓"},
        "category": {"B2B": "企業對企業發票", "B2C": "企業對消費者發票"},
        "tax_type": {"1": "應稅", "2": "零稅率", "3": "免稅", "9": "混合"},
    }

    def _mock_get_invoices(
        self,
        role_id: str,
        user_id: str = None,
        bill_id: Optional[int] = None,
        status: Optional[int] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        """`GET /invoices`（`InvoiceApiController@index`）——**已對照 jgb2 原始碼**。

        * `role_id` 必填，缺 → 400（:19-22）；恆定 join `bills` 且 `bills.active=1`（:40-41）；
        * `bill_id` → `where invoices.bill_id`（:63-65）；`status` → `where invoices.status`（:67-69）；
        * `orderBy('invoices.id','desc')`（:71）——**舊 mock 固定升冪，且兩個參數全部忽略**；
        * 分頁：預設 50、上限 200、`total_pages` 在 total=0 時為 0、`has_more = page < total_pages`。

        ⚠️ **GAP-I1（已登記缺口）**：`user_id` 在 production 是
        `whereExists(contracts.id = bills.contract_id AND contracts.to_user_id = ? AND active=1)`
        ——跨三張表。本替身的發票掛在 bill 12345／12340，帳單 fixture 是 900001-3、
        合約 fixture 是 678／600，**三個 fixture 宇宙不連通**（與 GAP-B1 同源），
        故此參數**照舊忽略**；接通屬另一個 slice。
        """
        logger.info(f"[MOCK] get_invoices: role_id={role_id}, user_id={user_id}")
        rows = [dict(r) for r in self._INVOICE_ROWS]
        if bill_id not in (None, ""):
            rows = [r for r in rows if r["bill_id"] == int(bill_id)]
        if status not in (None, ""):
            rows = [r for r in rows if r["status"] == int(status)]
        rows.sort(key=lambda r: r["id"], reverse=True)

        page = max(1, int(page or 1))
        size = min(200, max(1, int(per_page or 50)))
        total = len(rows)
        total_pages = -(-total // size) if total > 0 else 0
        offset = (page - 1) * size
        return {
            "success": True,
            "mapping": self._INVOICE_MAPPING,
            "data": rows[offset:offset + size],
            "pagination": {
                "current_page": page, "per_page": size, "total": total,
                "total_pages": total_pages, "has_more": page < total_pages,
            },
        }

    def _mock_get_contract_checkin_eligibility(
        self,
        role_id: str,
        user_id: str,
        contract_id: int,
    ) -> dict[str, Any]:
        """對齊 ContractCheckinApiController@show"""
        logger.info(
            f"[MOCK] get_contract_checkin_eligibility: "
            f"role_id={role_id}, user_id={user_id}, contract_id={contract_id}"
        )
        return {
            "success": True,
            "data": {
                "contract_id": contract_id,
                "eligible": True,
                "contract_status": {
                    "bit_status": 8,
                    "label": "已簽署",
                    "is_signed": True,
                },
                "first_bill_status": {
                    "bill_id": 12345,
                    "bit_status": 16,
                    "label": "已繳費",
                    "is_paid": True,
                },
                "deposit_status": {
                    "required_amount": 50000.00,
                    "paid_amount": 50000.00,
                    "is_fulfilled": True,
                },
                "checkin_blockers": [],
            },
        }

    def _mock_get_payments(
        self,
        role_id: str,
        user_id: str = None,
        month: Optional[str] = None,
        bill_id: Optional[int] = None,
        status: Optional[int] = None,
    ) -> dict[str, Any]:
        """`GET /payments`（`PaymentApiController@index`）——**已對照 jgb2 原始碼**。

        照抄：`role_id` 必填；恆定 `payments.paymentable_type = 'App\\Bill'`（:42）
        且帳單需 `owner_role_id = role_id` 且 `active=1`（:50-51）；
        篩選 `user_id`（payments.user_id）／`bill_id`（**payments.paymentable_id**）／
        `status`／`month`；`orderBy('payments.id','desc')`（:80）；
        分頁 50／200，`total_pages` 在 total=0 時為 0。
        ⚠️ 舊 mock **四個篩選參數全部忽略**、順序固定、pagination 寫死 total=2。
        投影 28 鍵（formatPayment:113-143）本來就對，未動。
        """
        logger.info(f"[MOCK] get_payments: role_id={role_id}, user_id={user_id}")
        rows = [

            {
                "id": 9876,
                "bill_id": 12345,
                "no": "JGB20260401001",
                "transaction_id": "TXN20260401123456",
                "user_id": int(user_id) if user_id else 0,
                "role_id": int(role_id) if role_id else 0,
                "creditor_role_id": None,
                "type": 1,
                "status": 2,
                "manufacturer": "newebpay",
                "payment_method": "credit_card",
                "currency": "TWD",
                "orig_currency": "TWD",
                "orig_price": 25000.00,
                "price": 25000.00,
                "final_currency": "TWD",
                "final_price": 25000.00,
                "discount_cash": 0.00,
                "discount_price": 0.00,
                "payment_times": 0,
                "data": None,
                "note": None,
                "items": None,
                "invoice_status": 1,
                "invoice_number": "AZ00000123",
                "ymd": 20260401,
                "payment_completed_ymd": 20260401,
                "payment_completed_at": "2026-04-01 15:30:00",
                "created_at": "2026-04-01 14:00:00",
                "updated_at": "2026-04-01 15:30:00",
            },
            {
                "id": 9870,
                "bill_id": 12340,
                "no": "JGB20260301001",
                "transaction_id": "TXN20260301098765",
                "user_id": int(user_id) if user_id else 0,
                "role_id": int(role_id) if role_id else 0,
                "creditor_role_id": None,
                "type": 1,
                "status": 0,
                "manufacturer": "newebpay",
                "payment_method": "atm",
                "currency": "TWD",
                "orig_currency": "TWD",
                "orig_price": 25000.00,
                "price": 25000.00,
                "final_currency": "TWD",
                "final_price": 25000.00,
                "discount_cash": 0.00,
                "discount_price": 0.00,
                "payment_times": 0,
                "data": None,
                "note": None,
                "items": None,
                "invoice_status": 0,
                "invoice_number": None,
                "ymd": 20260301,
                "payment_completed_ymd": None,
                "payment_completed_at": None,
                "created_at": "2026-03-01 14:00:00",
                "updated_at": "2026-03-01 14:00:00",
            },
        ]
        if bill_id not in (None, ""):
            rows = [r for r in rows if r["bill_id"] == int(bill_id)]
        if status not in (None, ""):
            rows = [r for r in rows if r["status"] == int(status)]
        if month:
            ym = str(month).replace("-", "")[:6]
            rows = [r for r in rows if str(r.get("ymd") or "").startswith(ym)]
        rows.sort(key=lambda r: r["id"], reverse=True)
        total = len(rows)
        return {
            "success": True,
            "mapping": {
                "status": {
                    "-3": "第3次付款",
                    "-2": "第2次付款",
                    "-1": "第1次付款",
                    "0": "付款失敗",
                    "1": "付款中",
                    "2": "付款成功",
                    "99": "取消付款",
                },
                "payment_method": {
                    "credit_card": "信用卡",
                    "atm": "ATM轉帳",
                    "cvs": "超商代碼",
                    "cvs_barcode": "超商條碼",
                    "google_pay": "Google Pay",
                    "samsung_pay": "Samsung Pay",
                    "pay": "中信轉帳Pay",
                    "icashpay": "愛金卡",
                },
                "manufacturer": {
                    "newebpay": "藍新金流",
                    "cathaybk": "國泰世華",
                    "sinopac": "永豐銀行",
                    "ctbc": "中國信託",
                    "icashpay": "愛金卡",
                },
            },
            "data": rows,
            "pagination": {
                "current_page": 1, "per_page": 50, "total": total,
                "total_pages": -(-total // 50) if total > 0 else 0,
                "has_more": False,
            },
        }

    def _mock_get_tenant_summary(
        self,
        role_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        """對齊 TenantApiController@summary（ExistedLessee 模型）"""
        logger.info(
            f"[MOCK] get_tenant_summary: role_id={role_id}, user_id={user_id}"
        )
        return {
            "success": True,
            "data": {
                "tenant_info": {
                    "id": 101,
                    "lessee_user_id": int(user_id) if user_id else 2001,
                    "lessee_role_id": None,
                    "lessor_role_id": int(role_id) if role_id else 20151,
                    "lessee_name": "王小明",
                    "lessee_email": "tenant@example.com",
                    "lessee_registered_phone": "0912345678",
                    "lessee_registered_phone_country": "886",
                    "is_lessee_user_registered": True,
                    "lessee_nationality": "TW",
                    "lessee_birthday": "19900101",
                    "lessee_primary_contact": "0912345678",
                    "lessee_emergency_contact_name": "王大華",
                    "lessee_emergency_contact_phone": "0923456789",
                    "lessee_emergency_contact_relationship": "父子",
                    "active": 1,
                },
                "contract_summary": {
                    "registered_contract_count": 2,
                    "registered_contract_inviting_count": 0,
                    "registered_contract_inviting_next_count": 0,
                    "registered_contract_signed_count": 1,
                    "registered_contract_history_count": 1,
                    "exempt_register_contract_count": 1,
                    "exempt_register_contract_signed_count": 0,
                    "exempt_register_contract_history_count": 1,
                },
                "bill_summary": {
                    "income_bill_count": 24,
                    "income_bill_ready_count": 1,
                    "income_bill_ready_overdue_count": 0,
                    "income_bill_paid_count": 0,
                    "income_bill_complete_count": 22,
                    "income_bill_complete_on_time_count": 19,
                    "income_bill_complete_late_count": 3,
                    "income_bill_paid_on_time_ratio": 86,
                    "payment_bill_count": 0,
                    "payment_bill_ready_count": 0,
                    "payment_bill_paid_count": 0,
                    "payment_bill_complete_count": 0,
                },
                "repair_summary": {
                    "repair_count": 5,
                    "repair_apply_count": 1,
                    "repair_assign_count": 0,
                    "repair_complete_count": 3,
                    "repair_finish_count": 1,
                },
            },
        }


    def _mock_get_payment_logs(
        self, role_id: str, payment_id: Optional[int] = None,
        bill_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """`GET /payment-logs`（`PaymentLogApiController@index`）——**已對照 jgb2 原始碼**。

        ⚠️ 這支端點的**回應信封與其他端點都不同**（:110-119）：
        `{success, bill_id, payments:[...], payment_logs:[...], summary:{...}}`
        ——**沒有 `data`、沒有 `mapping`、沒有 `pagination`**。舊 mock 三個都回了，
        且把日誌放在 `data`；消費端 `diagnose_payment_logs` 讀的正是 `data`
        ⇒ 在 production 永遠拿到空清單（同 get_tenant_contracts 的靜默失效類型）。

        其他照抄：
        * `role_id` 與 `bill_id` **皆必填**，缺任一 → 400（:24-30）；
        * 帳單需 `owner_role_id = role_id` 且 `active=1`，否則 → 404（:34-43）；
        * `payments` 取自 payments 表（`paymentable_type='App\\Bill'`），**涵蓋手動到帳**，
          `price`／`final_price` 被 `(float)` 轉型（:71-72）；
        * `payment_logs` 只取 `whereIn payment_id`（來自上一步），兩者皆 id desc；
        * `summary.has_successful_payment` = payments 中存在 `status == 2`（:116）。

        ⚠️ **`response` 欄不在投影內**：payment_logs 表有 `request`／`response`
        （App/Payment.php:4263 等處寫入），但列映射（:92-105）不回它。舊 mock 憑空給了它，
        而診斷引擎的原因碼分析正是讀它——那段邏輯在 production 沒有資料可用。
        """
        logger.info(f"[MOCK] get_payment_logs: role_id={role_id}, bill_id={bill_id}")
        payments = [
            {
                "source": "payments", "id": 9876, "no": "P20260401001",
                "transaction_id": "TXN20260401123456", "user_id": 9001,
                "role_id": int(role_id) if role_id else 0,
                "type": 1, "status": 1, "manufacturer": "newebpay",
                "payment_method": "credit_card",
                "price": 25000.0, "final_price": 25000.0,
                "invoice_status": 0, "invoice_number": None,
                "note": "信用卡授權失敗", "payment_completed_at": None,
                "created_at": "2026-04-01 14:00:00",
                "updated_at": "2026-04-01 14:00:05",
            },
        ]
        logs = [
            {
                "source": "payment_logs", "id": 50001, "payment_id": 9876,
                "role_id": int(role_id) if role_id else 0,
                "transaction_id": "TXN20260401123456",
                "manufacturer": "newebpay", "action": "credit_card",
                "type": "bill", "amount": "25000",
                "note": "信用卡授權失敗，請確認卡片資訊",
                "created_at": "2026-04-01 14:00:00",
            },
        ]
        return {
            "success": True,
            "bill_id": int(bill_id),
            "payments": payments,
            "payment_logs": logs,
            "summary": {
                "payment_count": len(payments),
                "payment_log_count": len(logs),
                "has_successful_payment": any(p["status"] == 2 for p in payments),
            },
        }

    def _mock_get_invoice_logs(
        self, role_id: str, invoice_id: Optional[int] = None,
        bill_id: Optional[int] = None, action: Optional[str] = None,
    ) -> dict[str, Any]:
        """`GET /invoice-logs`（`InvoiceLogApiController@index`）——**已對照 jgb2 原始碼**。

        照抄：

        * **`bill_id` 或 `invoice_id` 至少一個**，皆缺 → 400（:23-25）；
          ⚠️ 本端點**完全不看 role_id**（controller 沒有任何 role 圈定）；
        * 篩選 `bill_id`／`invoice_id`／`action`（:34-44）；`orderBy('id','desc')`；
        * 回應只有 `data` 與 `pagination`——**沒有 `mapping`**（:60-70）；舊 mock 憑空給了。

        ⚠️ **最關鍵的一處**：production **不回原始 `response_data`**（含買受人 email、
        載具號碼），只回白名單化的 `response_parsed = {status, message, invoice_number,
        random_number, invoice_date}`（:77-79、:97-131）；`Result` 巢狀 JSON 由它先解一層。
        舊 mock 回的是原始 `response_data`，而 `services/jgb/invoices.py` 三處都讀那個鍵
        ⇒ 線上永遠取不到回應內容。已一併修正消費端（改讀 response_parsed）。
        """
        logger.info(f"[MOCK] get_invoice_logs: invoice_id={invoice_id}, bill_id={bill_id}")
        rows = [
            {
                "id": 60001, "invoice_id": 5001, "bill_id": 12345,
                "manufacturer": "ezpay", "action": "issue", "type": "bill",
                "http_code": 200,
                "response_parsed": {
                    "status": "SUCCESS", "message": "開立發票成功",
                    "invoice_number": "AZ00000123", "random_number": "1234",
                    "invoice_date": "2026-04-01",
                },
                "note": None, "created_at": "2026-04-01T10:00:00+08:00",
            },
            {
                "id": 60002, "invoice_id": 5002, "bill_id": 12340,
                "manufacturer": "ezpay", "action": "invalid", "type": "bill",
                "http_code": 200,
                "response_parsed": {
                    "status": "SUCCESS", "message": "作廢發票成功",
                    "invoice_number": "AZ00000120", "random_number": "5678",
                    "invoice_date": "2026-03-01",
                },
                "note": None, "created_at": "2026-03-15T10:00:00+08:00",
            },
            {
                "id": 60003, "invoice_id": 5003, "bill_id": 12333,
                "manufacturer": "ezpay", "action": "issue", "type": "bill",
                "http_code": 500,
                # production 的 parseResponseData 對空回應回 **null**（:100-103）
                "response_parsed": None,
                "note": "上游逾時", "created_at": "2026-02-01T10:00:00+08:00",
            },
        ]
        if bill_id not in (None, ""):
            rows = [r for r in rows if r["bill_id"] == int(bill_id)]
        if invoice_id not in (None, ""):
            rows = [r for r in rows if r["invoice_id"] == int(invoice_id)]
        if action:
            rows = [r for r in rows if r["action"] == action]
        rows.sort(key=lambda r: r["id"], reverse=True)
        total = len(rows)
        return {
            "success": True,
            "data": rows,
            "pagination": {
                "current_page": 1, "per_page": 50, "total": total,
                "total_pages": -(-total // 50) if total > 0 else 0,
                "has_more": False,
            },
        }

    def _mock_get_subscription(self, role_id: str) -> dict[str, Any]:
        """對齊 SubscriptionApiController@show"""
        logger.info(f"[MOCK] get_subscription: role_id={role_id}")
        return {
            "success": True,
            "mapping": {
                "plan_type": {"trial": "試用", "basic": "基本", "advance": "進階"},
            },
            "data": {
                "role_id": int(role_id) if role_id else 0,
                "is_subscribed": 1,
                "plan_id": 3,
                "plan_type": "advance",
                "plan_name": "進階方案",
                "plan_start_ymd": 20260101,
                "plan_end_ymd": 20261231,
                "plan_estate_limit": 50,
                "plan_contract_limit": 100,
                "plan_price": 2990.00,
                "plan_currency": "TWD",
                "plan_cycle": "monthly",
                "estate_usage": {
                    "current_count": 35,
                    "limit": 55,
                    "remain": 20,
                },
            },
        }

    def _mock_get_iot_manufacturers(self, role_id: str) -> dict[str, Any]:
        """對齊 IotManufacturerApiController@index"""
        logger.info(f"[MOCK] get_iot_manufacturers: role_id={role_id}")
        return {
            "success": True,
            "mapping": {
                "manufacturer": {"SkyWatch": "SkyWatch", "Miezo": "Miezo", "DAE": "DAE"},
            },
            "data": [
                {
                    "id": 1,
                    "role_id": int(role_id) if role_id else 0,
                    "manufacturer": "SkyWatch",
                    "manufacturer_user_id": "user_abc123",
                    "is_active": 1,
                },
            ],
            "pagination": {
                "current_page": 1, "per_page": 50,
                "total": 1, "total_pages": 1, "has_more": False,
            },
        }
