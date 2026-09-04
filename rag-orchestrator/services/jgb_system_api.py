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
    build_contract_required_fields,
    project_estate,
)
from services.jgb.fixtures import BillFixtureTable
from services.jgb.transport import (  # noqa: F401  (FALLBACK_MESSAGE 對外沿用)
    FALLBACK_MESSAGE,
    JGBMockTransport,
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
        self._real_transport: Transport = RealHttpTransport(
            self.api_base_url, self.api_key, self.timeout
        )
        #: 4.3：mock 模式裝配替身；fixture 表由 4.4 提供，未裝配前「已遷移」端點
        #: 一律 MissingFixtureError——**任何失敗都不會退回 real transport**。
        #: 4.6：裝配 fixture 表，使 bills／bill_detail／contracts 三個**已遷移**端點
        #: 能依契約回應；其餘端點仍走方法級 mock——逐端點現況與稽核成本見
        #: `.kiro/specs/conversational-routing-execution/transport-migration-inventory.md`。
        #: estates 尚未遷入 transport（見 transport-migration-inventory.md），
        #: 但替身資料已對照 EstateApiController 逐鍵，改由 fixture 表供應。
        self._estate_fixtures = EstateFixtureTable()
        self._mock_transport: Optional[Transport] = (
            JGBMockTransport(BillFixtureTable(), ContractFixtureTable())
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
        **kwargs,
    ) -> dict[str, Any]:
        """查詢修繕進度"""
        if not self._validate_identity(role_id, user_id):
            return self._degraded_response()

        if self.use_mock:
            return self._mock_get_repairs(role_id, user_id, status)

        params: dict[str, Any] = {"role_id": role_id, "user_id": user_id}
        if status:
            params["status"] = status
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

        if self.use_mock:
            return self._mock_get_estates(role_id, keyword, per_page)

        params: dict[str, Any] = {
            "role_id": role_id,
            "keyword": keyword,
            "per_page": per_page,
        }
        return await self._request("/api/external/v1/estates", params)

    async def get_repair_categories(
        self,
        **kwargs,
    ) -> dict[str, Any]:
        """取得修繕分類樹（不需要 role_id）"""
        if self.use_mock:
            return self._mock_get_repair_categories()

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
        **kwargs,
    ) -> dict[str, Any]:
        """建立修繕單"""
        if not role_id:
            return self._degraded_response()

        if self.use_mock:
            return self._mock_create_repair(
                role_id, estate_id, category_id, item_id,
                broken_reason, broken_note, emergency_status
            )

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
        return await self._post_request("/api/external/v1/repairs", data)

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
        if self.use_mock:
            return self._mock_team_members(role_id, keyword)
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
        if self.use_mock:
            return self._mock_member_permissions(role_id, user_id)
        raw = await self._request(
            f"/api/external/v1/roles/{role_id}/members/{user_id}/permissions", {})
        data = (raw or {}).get("data")
        return {"success": bool((raw or {}).get("success")),
                "data": [data] if isinstance(data, dict) else []}

    #: `TeamMemberApiController::ABILITY_WHITELIST`（:17-32）逐鍵 **32 個**。
    #: production 一律回滿 32 鍵（成員取 `Role::getPermissionByCharacter` 的值，
    #: 擁有者全 true）——舊 mock 只回 6 鍵，是 production 產不出來的形狀。
    _ABILITY_WHITELIST: "tuple[str, ...]" = (
        "show_estate", "show_owner_estate", "add_estate", "edit_estate",
        "assign_estate", "export_estate",
        "show_contract", "show_owner_contract", "add_contract", "edit_contract",
        "send_contract_invitation", "sign_contract", "assign_contract", "export_contract",
        "show_bill", "show_owner_bill", "add_bill", "receive_bill", "pay_bill", "export_bill",
        "show_role", "edit_role", "show_role_team", "edit_role_team",
        "edit_role_payment", "edit_role_subscription",
        "show_repair", "show_owner_repair", "edit_repair", "export_repair",
        "show_recharge_account", "edit_recharge_account",
    )

    #: 團隊成員替身（`members()`:113-183）。三種形狀刻意併存：
    #: 擁有者（character_id=0、character_name='團隊擁有者'）／一般成員／
    #: **character_name 為 None** 的成員（pivot 無 character_id，:135-137 的 null 分支）。
    _TEAM_MEMBERS: "tuple[dict[str, Any], ...]" = (
        {"member_user_id": 100, "character_id": 0, "character_name": "團隊擁有者",
         "is_owner": True, "_email": "owner@example.com", "_name": "王小明"},
        {"member_user_id": 292, "character_id": 1151, "character_name": "檢視者",
         "is_owner": False, "_email": "viewer@example.com", "_name": "陳小美"},
        {"member_user_id": 305, "character_id": None, "character_name": None,
         "is_owner": False, "_email": "nochar@example.com", "_name": "李小華"},
    )

    def _mock_team_members(self, role_id: str, keyword: str) -> dict[str, Any]:
        """`GET /roles/{role_id}/members`（`TeamMemberApiController@members`）。

        照抄：`keyword` 必填（缺→400，adapter 已擋）；對 **email 與 name** 做
        **不分大小寫的 contains** 比對，email 先判、命中即 `match_field='email'`，
        否則才比 name（:161-170）；同一人只回一次；**不回 email／phone 明文**（:112）。
        ⚠️ 舊 mock 不論 keyword 一律回同一列 ⇒ 「查無此成員」分支在替身上測不到。
        """
        kw = str(keyword).lower()
        data = []
        for m in self._TEAM_MEMBERS:
            if kw in m["_email"].lower():
                field = "email"
            elif kw in m["_name"].lower():
                field = "name"
            else:
                continue
            data.append({"member_user_id": m["member_user_id"],
                         "character_id": m["character_id"],
                         "character_name": m["character_name"],
                         "is_owner": m["is_owner"], "match_field": field})
        return {"success": True, "data": data}

    def _mock_member_permissions(self, role_id: str, user_id: str) -> dict[str, Any]:
        """`GET /roles/{id}/members/{uid}/permissions`（同檔 `permissions()`:42-98）。

        照抄回應形狀：`data = {role_id, user_id, is_member, is_owner, character, abilities}`
        ——`character` 是 **{id, name, display} 物件**，production **沒有** `character_name` 這個鍵
        （舊 mock 憑空給了它）；`abilities` 一律 32 鍵。
        擁有者 → 全 true（:64-69）；查無此成員 → 404（我方折疊為 success:False）。
        """
        member = next((m for m in self._TEAM_MEMBERS
                       if str(m["member_user_id"]) == str(user_id)), None)
        if member is None:
            return {"success": False, "data": []}

        if member["is_owner"]:
            abilities = {k: True for k in self._ABILITY_WHITELIST}
            character = {"id": 0, "name": "團隊擁有者", "display": None}
        else:
            granted = {"show_owner_bill", "show_owner_contract", "show_owner_estate",
                       "show_repair", "show_owner_repair"}
            abilities = {k: (k in granted) for k in self._ABILITY_WHITELIST}
            character = ({"id": member["character_id"], "name": member["character_name"],
                          "display": None} if member["character_id"] else None)
        return {"success": True, "data": [{
            "role_id": int(role_id) if str(role_id).isdigit() else role_id,
            "user_id": int(user_id) if str(user_id).isdigit() else user_id,
            "is_member": True, "is_owner": member["is_owner"],
            "character": character, "abilities": abilities,
        }]}

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

        if self.use_mock:
            # `formatMeter()` 逐鍵 15 欄（MeterApiController:152-172）。三列刻意涵蓋
            # production 的兩個衍生規則：
            #   · meter_type = manufacturer ∈ {Miezo, DAE, SkyWatch} ? cloud : manual（:157/:162）
            #   · is_poweron 的**三態**：-1（從未連線）→ **null**，0/1 → false/true（:167）
            #     ——舊 mock 只有 True，null 這一態在替身上從來測不到。
            rows = [
                {"id": 501, "estate_id": 9001, "estate_name": "海大質感獨立套房",
                 "name": "3F 分電表", "manufacturer": "DAE", "meter_type": "cloud",
                 "is_online": True, "is_topup": True, "enable_topup": True,
                 "balance": 350.0, "available_meter": 87.5, "current_reading": 1234.5,
                 "is_poweron": True, "is_low_battery": False,
                 "synced_at": "2026-07-04 10:35:00"},
                {"id": 502, "estate_id": 9002, "estate_name": "新北新莊-富貴500-14B05",
                 "name": "總電表", "manufacturer": "Panasonic", "meter_type": "manual",
                 "is_online": False, "is_topup": False, "enable_topup": False,
                 "balance": 0.0, "available_meter": 0.0, "current_reading": 8890.0,
                 "is_poweron": None, "is_low_battery": True,
                 "synced_at": "2026-06-30 08:00:00"},
                {"id": 503, "estate_id": None, "estate_name": None,
                 "name": "未綁定物件的電表", "manufacturer": "SkyWatch",
                 "meter_type": "cloud",
                 "is_online": True, "is_topup": False, "enable_topup": True,
                 "balance": 12.5, "available_meter": 3.0, "current_reading": 42.0,
                 "is_poweron": False, "is_low_battery": False,
                 "synced_at": "2026-07-04 10:30:00"},
            ]
            # production 以 iot_estate 中間表過濾 estate_id（:31-39）——未綁定者查不到。
            if estate_id:
                rows = [m for m in rows if str(m.get("estate_id")) == str(estate_id)]
        else:
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

        if self.use_mock:
            # 與 get_estates 共用同一份 fixture（含 is_open=1 硬過濾）——
            # 舊版是一列寫死的手抄資料，永遠有結果，sentinel 分支測不到。
            rows = [project_estate(e) for e in self._estate_fixtures.visible_rows()]
        else:
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

        if self.use_mock:
            # `show()` 同樣硬過濾 active=1／is_open=1，不在其中即 404（:121-128）。
            row = self._estate_fixtures.by_id(int(eid))
            if row is None:
                return {"success": False, "data": []}
            detail = project_estate(row)
            # `formatEstate($estate, true)` 才有的四個欄位（:280-286）；
            # fixture 未賦值故為 None（皆為可空欄位），不假造內容。
            detail.update({"description": None, "traffic": None,
                           "nearby": None, "notes": None})
            # ⚠️ production **一律列出 16 個必填欄位**；舊 mock 的 `fields: []`
            #    是 production 產不出來的形狀。
            detail["contract_required_fields"] = build_contract_required_fields()
            return {"success": True, "data": [detail]}

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

    def _mock_get_bills(
        self,
        role_id: str,
        user_id: str,
        month: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict[str, Any]:
        """對齊 BillApiController@index"""
        logger.info(f"[MOCK] get_bills: role_id={role_id}, user_id={user_id}")
        return {
            "success": True,
            "mapping": {
                "status": {
                    "1": "待發送",
                    "2": "待繳費",
                    "8": "待對帳",
                    "16": "已繳費",
                    "32": "排定發送",
                    "64": "已失效",
                },
                "invoice_status": {
                    "0": "未開發票",
                    "1": "已開發票",
                    "2": "發票異常",
                },
                "type": {
                    "1": "一般租金",
                    "2": "點退",
                    "3": "新增帳單",
                    "4": "罰款",
                    "5": "儲值",
                    "6": "押金設算息",
                },
            },
            "data": [
                {
                    "id": 12345,
                    "contract_id": 678,
                    "estate_id": 456,
                    "type": 1,
                    "category": 3,
                    "bit_status": 2,
                    "title": "2026年4月租金",
                    "sub_title": "2026/04/01 ~ 2026/04/30",
                    "currency": "TWD",
                    "total": 25000.00,
                    "final_total": 25000.00,
                    "rate": 1.0,
                    "date_start": 20260401,
                    "date_end": 20260430,
                    "date_expire": 20260405,
                    "date_expire_note": None,
                    "cycle": 1,
                    "days": 30,
                    "is_auto_pay": False,
                    "is_paid_on_time": None,
                    "online_payment_method": "newebpay",
                    "online_payment_action": "atm",
                    "payment_id": None,
                    "invoice_status": 0,
                    "invoice_number": None,
                    "ready_at": "2026-03-25 10:30:00",
                    "pay_at": None,
                    "complete_at": None,
                    "created_at": "2026-03-25 10:30:00",
                    "updated_at": "2026-04-01 00:00:00",
                },
                {
                    "id": 12340,
                    "contract_id": 678,
                    "estate_id": 456,
                    "type": 1,
                    "category": 3,
                    "bit_status": 16,
                    "title": "2026年3月租金",
                    "sub_title": "2026/03/01 ~ 2026/03/31",
                    "currency": "TWD",
                    "total": 25000.00,
                    "final_total": 25000.00,
                    "rate": 1.0,
                    "date_start": 20260301,
                    "date_end": 20260331,
                    "date_expire": 20260305,
                    "date_expire_note": None,
                    "cycle": 1,
                    "days": 31,
                    "is_auto_pay": False,
                    "is_paid_on_time": 1,
                    "online_payment_method": "newebpay",
                    "online_payment_action": "credit_card",
                    "payment_id": 9876,
                    "invoice_status": 1,
                    "invoice_number": "AZ00000120",
                    "ready_at": "2026-02-25 10:30:00",
                    "pay_at": "2026-03-03 14:00:00",
                    "complete_at": "2026-03-03 15:00:00",
                    "created_at": "2026-02-25 10:30:00",
                    "updated_at": "2026-03-03 15:00:00",
                },
                {
                    "id": 12350,
                    "contract_id": 678,
                    "estate_id": 456,
                    "type": 1,
                    "category": 3,
                    "bit_status": 64,
                    "title": "2025年12月租金",
                    "sub_title": "2025/12/01 ~ 2025/12/31",
                    "currency": "TWD",
                    "total": 25000.00,
                    "final_total": 25000.00,
                    "rate": 1.0,
                    "date_start": 20251201,
                    "date_end": 20251231,
                    "date_expire": 20251205,
                    "date_expire_note": None,
                    "cycle": 1,
                    "days": 31,
                    "is_auto_pay": False,
                    "is_paid_on_time": None,
                    "online_payment_method": "newebpay",
                    "online_payment_action": "atm",
                    "payment_id": None,
                    "invoice_status": 0,
                    "invoice_number": None,
                    "ready_at": "2025-11-25 10:30:00",
                    "pay_at": None,
                    "complete_at": None,
                    "created_at": "2025-11-25 10:30:00",
                    "updated_at": "2025-12-06 00:00:00",
                },
            ],
            "pagination": {
                "current_page": 1,
                "per_page": 50,
                "total": 3,
                "total_pages": 1,
                "has_more": False,
            },
        }

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

    def _mock_get_contracts(
        self,
        role_id: str,
        user_id: str,
        status: Optional[str] = None,
    ) -> dict[str, Any]:
        """對齊 ContractApiController@index（含 d2b0117 診斷欄位）"""
        logger.info(f"[MOCK] get_contracts: role_id={role_id}, user_id={user_id}")
        return {
            "success": True,
            "mapping": {
                "bit_status": {
                    "1": "已建立", "2": "已發送簽約邀請",
                    "4": "租客已簽名", "8": "雙方簽名完成",
                    "16": "已發送點交", "32": "租客同意點交",
                    "64": "已發送點退", "128": "租客同意點退",
                    "256": "提前解約中", "512": "提前解約已確認",
                    "1024": "歷史合約", "2048": "歷史完成",
                },
            },
            "data": [
                {
                    "id": 678,
                    "status": 5,
                    "bit_status": 47,
                    "active": 1,
                    "is_history": 0,
                    "is_history_done": 0,
                    "estate_id": 456,
                    "title": "信義區套房A",
                    "city": "台北市",
                    "district": "信義區",
                    "address": "信義路五段7號",
                    "currency": "TWD",
                    "rent": 25000.00,
                    "deposit_amount": 50000.00,
                    "date_start": 20260101,
                    "date_end": 20261231,
                    "allow_early_termination": True,
                    "early_termination_days": 30,
                    "is_auto_generate_invoice": 0,
                    "to_user_connect": True,
                    "is_tenant_registered": True,
                    "to_user_phone": "0912345678",
                    "to_user_email": "tenant@example.com",
                    "property_purpose_key": 1,
                    "father_id": None,
                    "early_termination_wish_date_end": None,
                    # 診斷用：滯納金設定
                    "enable_late_fee": 1,
                    "calc_late_fee_buffer_days": 7,
                    "late_fee_percent": 5.0,
                    # 診斷用：提前解約違約金設定
                    "early_termination_penalty_type": 1,
                    "early_termination_penalty": 1.0,
                    "early_termination_penalty_amount": 25000.00,
                    "early_termination_notice_date": None,
                    "created_at": "2025-12-10 09:00:00",
                    "updated_at": "2026-01-01 00:00:00",
                },
                {
                    "id": 600,
                    "status": 10,
                    "bit_status": 3087,
                    "active": 1,
                    "is_history": 1,
                    "is_history_done": 1,
                    "estate_id": 400,
                    "title": "中山區雅房B",
                    "city": "台北市",
                    "district": "中山區",
                    "address": "中山北路二段10號",
                    "currency": "TWD",
                    "rent": 18000.00,
                    "deposit_amount": 36000.00,
                    "date_start": 20250101,
                    "date_end": 20251231,
                    "allow_early_termination": False,
                    "early_termination_days": 0,
                    "is_auto_generate_invoice": 0,
                    "to_user_connect": True,
                    "is_tenant_registered": True,
                    "to_user_phone": "0923456789",
                    "to_user_email": "tenant2@example.com",
                    "property_purpose_key": 1,
                    "father_id": None,
                    "early_termination_wish_date_end": None,
                    "enable_late_fee": 0,
                    "calc_late_fee_buffer_days": 0,
                    "late_fee_percent": 0.0,
                    "early_termination_penalty_type": None,
                    "early_termination_penalty": 0.0,
                    "early_termination_penalty_amount": 0.0,
                    "early_termination_notice_date": None,
                    "created_at": "2024-12-05 09:00:00",
                    "updated_at": "2025-12-31 23:59:59",
                },
            ],
            "pagination": {
                "current_page": 1,
                "per_page": 50,
                "total": 2,
                "total_pages": 1,
                "has_more": False,
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

    def _mock_get_repairs(
        self,
        role_id: str,
        user_id: str = None,
        status: Optional[int] = None,
        estate_id: Optional[int] = None,
        category_id: Optional[int] = None,
        is_urgent: Optional[int] = None,
        keyword: Optional[str] = None,
    ) -> dict[str, Any]:
        """`GET /repairs`（`RepairApiController@index`）——**已對照 jgb2 原始碼**。

        照抄：`role_id` 必填（:25）；恆定 `role_id` 與 `active=1`（:47-48）；
        篩選 `status`／`estate_id`／`category_id`／`is_urgent`（→ **emergency_status**，:64）／
        `keyword`（`estate_title` 等欄位 LIKE，:67-75）；分頁 50／200。
        ⚠️ 舊 mock **所有篩選參數都忽略**、pagination 寫死。投影 38 鍵（formatRepair）本來就對。
        ⚠️ `is_urgent` 對映的是 `emergency_status`——**這個欄位的語義曾經反轉過**
        （見 conversational-repair 的地雷紀錄），不可望文生義。
        """
        logger.info(f"[MOCK] get_repairs: role_id={role_id}, user_id={user_id}")
        rows = [

            {
                "id": 3001,
                "status": 16,
                "emergency_status": 1,  # 非緊急（漏水已完成修繕）
                "estate_id": 456,
                "estate_title": "信義區套房A",
                "estate_full_address": "台北市信義區信義路五段7號3樓",
                "estate_room_number": "3F-1",
                "contract_id": 678,
                "category_id": 2,
                "category_name": "衛浴維修",
                "item_id": 202,
                "item_name": "水龍頭",
                "broken_reason": "漏水",
                "broken_note": "廚房水龍頭持續滴水",
                "broken_photos": [],
                "currency": "TWD",
                "total": 3500.00,
                "manufacturer_name": "信義水電行",
                "manufacturer_phone": "02-2345-6789",
                "user_id": 1001,
                "user_name": "張管理",
                "user_phone": "0911-111-111",
                "user_email": "manager@example.com",
                "to_user_id": int(user_id) if user_id else 2001,
                "to_user_name": "王小明",
                "to_user_phone": "0912-345-678",
                "to_user_email": "tenant@example.com",
                "agent_user_id": None,
                "agent_name": None,
                "user_note": "已完成修繕",
                "to_user_note": None,
                "apply_at": "20260405090000",
                "assign_at": "20260407100000",
                "complete_at": "20260412140000",
                "finish_at": None,
                "archive_at": None,
                "created_at": "2026-04-05 09:00:00",
                "updated_at": "2026-04-12 14:00:00",
            },
            {
                "id": 3002,
                "status": 1,
                "emergency_status": 2,  # 緊急（冷氣不冷、天氣熱盼盡快）
                "estate_id": 456,
                "estate_title": "信義區套房A",
                "estate_full_address": "台北市信義區信義路五段7號3樓",
                "estate_room_number": "3F-1",
                "contract_id": 678,
                "category_id": 1,
                "category_name": "家電維修",
                "item_id": 101,
                "item_name": "冷氣機",
                "broken_reason": "不冷",
                "broken_note": "開機後完全沒有冷風，已檢查過濾網",
                "broken_photos": [],
                "currency": "TWD",
                "total": None,
                "manufacturer_name": None,
                "manufacturer_phone": None,
                "user_id": 1001,
                "user_name": "張管理",
                "user_phone": "0911-111-111",
                "user_email": "manager@example.com",
                "to_user_id": int(user_id) if user_id else 2001,
                "to_user_name": "王小明",
                "to_user_phone": "0912-345-678",
                "to_user_email": "tenant@example.com",
                "agent_user_id": None,
                "agent_name": None,
                "user_note": None,
                "to_user_note": "希望能盡快處理，天氣很熱",
                "apply_at": "20260415140000",
                "assign_at": None,
                "complete_at": None,
                "finish_at": None,
                "archive_at": None,
                "created_at": "2026-04-15 14:00:00",
                "updated_at": "2026-04-15 14:00:00",
            },
        ]
        if status not in (None, ""):
            rows = [r for r in rows if r["status"] == int(status)]
        if estate_id not in (None, ""):
            rows = [r for r in rows if r["estate_id"] == int(estate_id)]
        if category_id not in (None, ""):
            rows = [r for r in rows if r["category_id"] == int(category_id)]
        if is_urgent not in (None, ""):
            rows = [r for r in rows if r["emergency_status"] == int(is_urgent)]
        if keyword:
            kw = str(keyword)
            rows = [r for r in rows if kw in str(r.get("estate_title") or "")]
        total = len(rows)
        return {
            "success": True,
            "mapping": {
                "status": {
                    "1": "申請中",
                    "2": "安排修繕",
                    "16": "完成修繕",
                    "32": "結單",
                    "64": "封存",
                },
                "emergency_status": {
                    "1": "非緊急",
                    "2": "緊急",
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

    def _mock_get_estates(
        self,
        role_id: str,
        keyword: str = "",
        per_page: int = 10,
        **params: Any,
    ) -> dict[str, Any]:
        """`GET /estates`（`EstateApiController@index`）——**已對照 jgb2 原始碼**（2026-08-25）。

        逐條照抄 production，包含它的怪癖：

        * 恆定 where `active=1` **且 `is_open=1`**（:52-53）——只回**招租刊登中**的物件。
          舊版 mock 沒有這道過濾 ⇒ 會回 production 根本查不到的物件；
          「查無＝非刊登中」那條 sentinel 口徑因此在替身上從未被走到。
        * `role_id` 是 **applyFilters 的一般篩選**（:184-186），不是授權——寫錯就換一組結果集。
          舊版 mock 把 role_id 直接寫進每一列 ⇒ **任何 role 都命中**（過度寬鬆）。
        * `keyword` 只比 `title`（:189-192），**不含 address**；production 先跳脫
          `%`／`_` 再 LIKE，故使用者輸入的萬用字元是字面值——Python 的 `in` 同語義。
        * `use_for` 不在 residential／business／parking_space 三者內 → **靜默忽略**（:149-155）。
        * 排序白名單 id／created_at／updated_at／rent／size，其餘**回退 `updated_at`**（:60-66）；
          方向非 asc 一律 desc。
        * 分頁：預設 50、上限 200；`total_pages = ceil(total/per_page)`（**不特判 total=0**，
          結果同為 0）；`has_more = page < total_pages`。
        * `mapping`：production 回 `{countries, building}`，`countries` 由 countrys／citys／
          districts 三張表組出（:490-536）。**本替身不模擬**，故不輸出該鍵（沿用舊行為，
          消費端目前無人讀取——見 estates-source-audit.md「未涵蓋」）。
        """
        logger.info(f"[MOCK] get_estates: role_id={role_id}, keyword={keyword}")
        rows = self._estate_fixtures.visible_rows()

        if role_id:
            rows = [e for e in rows if e.get("role_id") == int(role_id)]
        if params.get("user_id"):
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
        if keyword:
            rows = [e for e in rows if str(keyword) in str(e.get("title") or "")]

        sort_by = params.get("sort_by")
        if sort_by not in ALLOWED_SORT_FIELDS:
            sort_by = "updated_at"
        descending = str(params.get("sort_direction", "desc")).lower() != "asc"
        rows.sort(key=lambda e: (e.get(sort_by) is None, e.get(sort_by)),
                  reverse=descending)

        page = max(1, int(params.get("page", 1) or 1))
        size = min(ESTATE_MAX_PER_PAGE, max(1, int(per_page or ESTATE_DEFAULT_PER_PAGE)))
        total = len(rows)
        total_pages = -(-total // size)
        offset = (page - 1) * size
        return {
            "success": True,
            "data": [project_estate(e) for e in rows[offset:offset + size]],
            "pagination": {
                "current_page": page, "per_page": size, "total": total,
                "total_pages": total_pages, "has_more": page < total_pages,
            },
        }

    def _mock_get_repair_categories(self) -> dict[str, Any]:
        """對齊 RepairApiController@categories"""
        logger.info("[MOCK] get_repair_categories")
        return {
            "success": True,
            "data": [
                {
                    "id": 1,
                    "name": "家電維修",
                    "items": [
                        {
                            "id": 101,
                            "name": "冷氣機",
                            "broken_reasons": ["不冷", "漏水", "異音", "無法開機"],
                        },
                        {
                            "id": 102,
                            "name": "洗衣機",
                            "broken_reasons": ["不轉", "漏水", "異音"],
                        },
                        {
                            "id": 103,
                            "name": "冰箱",
                            "broken_reasons": ["不冷", "異音", "結霜"],
                        },
                    ],
                },
                {
                    "id": 2,
                    "name": "衛浴維修",
                    "items": [
                        {
                            "id": 201,
                            "name": "馬桶",
                            "broken_reasons": ["堵塞", "漏水", "沖水異常"],
                        },
                        {
                            "id": 202,
                            "name": "水龍頭",
                            "broken_reasons": ["漏水", "無法關閉", "水量不足"],
                        },
                    ],
                },
                {
                    "id": 3,
                    "name": "結構修繕",
                    "items": [
                        {
                            "id": 301,
                            "name": "牆壁",
                            "broken_reasons": ["裂縫", "滲水", "壁癌"],
                        },
                        {
                            "id": 302,
                            "name": "地板",
                            "broken_reasons": ["隆起", "破損", "漏水"],
                        },
                        {
                            "id": 303,
                            "name": "門窗",
                            "broken_reasons": ["無法關閉", "玻璃破損", "鎖具故障"],
                        },
                    ],
                },
            ],
        }

    def _mock_create_repair(
        self,
        role_id: str,
        estate_id: int,
        category_id: int,
        item_id: int,
        broken_reason: str,
        broken_note: str = "",
        emergency_status: int = 1,
    ) -> dict[str, Any]:
        """對齊 RepairApiController@store"""
        logger.info(
            f"[MOCK] create_repair: role_id={role_id}, estate_id={estate_id}, "
            f"category_id={category_id}, item_id={item_id}"
        )
        return {
            "success": True,
            "data": {
                "id": 12346,
                "status": 1,
                "emergency_status": emergency_status,
                "estate_id": estate_id,
                "estate_title": "信義區精緻套房",
                "estate_full_address": "台北市信義區信義路五段7號3樓",
                "estate_room_number": "3F-1",
                "contract_id": None,
                "category_id": category_id,
                "category_name": "家電維修",
                "item_id": item_id,
                "item_name": "冷氣機",
                "broken_reason": broken_reason,
                "broken_note": broken_note,
                "broken_photos": [],
                "currency": "TWD",
                "total": None,
                "manufacturer_name": None,
                "manufacturer_phone": None,
                "user_id": 1001,
                "user_name": "張管理",
                "user_phone": "0911-111-111",
                "user_email": "manager@example.com",
                "to_user_id": None,
                "to_user_name": None,
                "to_user_phone": None,
                "to_user_email": None,
                "agent_user_id": None,
                "agent_name": None,
                "user_note": None,
                "to_user_note": None,
                "apply_at": "20260422190000",
                "assign_at": None,
                "complete_at": None,
                "finish_at": None,
                "archive_at": None,
                "created_at": "2026-04-22 19:00:00",
                "updated_at": "2026-04-22 19:00:00",
            },
        }

    # ------------------------------------------------------------------
    # v1.1 Mock implementations
    # ------------------------------------------------------------------

    def _mock_get_bill_detail(
        self, role_id: str, bill_id: int
    ) -> dict[str, Any]:
        """對齊 BillApiController@show"""
        logger.info(f"[MOCK] get_bill_detail: role_id={role_id}, bill_id={bill_id}")
        return {
            "success": True,
            "mapping": {
                "status": {
                    "1": "待發送", "2": "待繳費", "8": "待對帳",
                    "16": "已繳費", "32": "排定發送", "64": "已失效",
                },
                "type": {
                    "1": "一般租金", "2": "點退", "3": "新增帳單",
                    "4": "罰款", "5": "儲值", "6": "押金設算息",
                },
                "unit_type": {
                    "": "無單位",
                    "degree": "度",
                    "day": "日",
                    "month": "月",
                },
            },
            "data": {
                "id": bill_id,
                "contract_id": 678,
                "estate_id": 456,
                "type": 1,
                "category": 3,
                "bit_status": 2,
                "title": "2026年4月租金",
                "sub_title": "2026/04/01 ~ 2026/04/30",
                "currency": "TWD",
                "total": 25000.00,
                "final_total": 25000.00,
                "rate": 1.0,
                "date_start": 20260401,
                "date_end": 20260430,
                "date_expire": 20260405,
                "date_expire_note": None,
                "cycle": 1,
                "days": 30,
                "is_auto_pay": False,
                "is_paid_on_time": None,
                "online_payment_method": "newebpay",
                "online_payment_action": "atm",
                "payment_id": None,
                "invoice_status": 0,
                "invoice_number": None,
                "ready_at": "2026-03-25 10:30:00",
                "pay_at": None,
                "complete_at": None,
                "pay_info": {
                    "type": "online",
                    "manufacturer": "newebpay",
                    "action": "atm",
                    "expire_ymd": "2026/04/10",
                    "atm_info": {
                        "bank_code": "004",
                        "bank_name": "台灣銀行",
                        "atm": "9103522178643201",
                        "expire": "2026-04-10",
                    },
                },
                "details": [
                    {
                        "id": 101,
                        "label": "租金",
                        "unit_price": 25000.00,
                        "unit_type": None,
                        "unit_count": 1.00,
                        "measurement_before": None,
                        "measurement_after": None,
                        "total_price": 25000.00,
                        "active": 1,
                    },
                    {
                        "id": 102,
                        "label": "電費",
                        "unit_price": 5.50,
                        "unit_type": "degree",
                        "unit_count": 120.00,
                        "measurement_before": 1000.00,
                        "measurement_after": 1120.00,
                        "total_price": 660.00,
                        "active": 1,
                    },
                ],
                "created_at": "2026-03-25T10:30:00+08:00",
                "updated_at": "2026-04-01T00:00:00+08:00",
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
