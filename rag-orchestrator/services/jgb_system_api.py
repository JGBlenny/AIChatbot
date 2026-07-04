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
import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

# 降級回答訊息
DEGRADED_MESSAGE = "請先登入以查詢您的個人資料。"
FALLBACK_MESSAGE = "目前無法查詢資料，請稍後再試或聯繫您的管理師。"


class JGBSystemAPI:
    """JGB External API Client（mock/real 切換）"""

    def __init__(self):
        self.api_base_url = os.getenv(
            "JGB_API_BASE_URL", "https://www.jgbsmart.com"
        )
        self.api_key = os.getenv("JGB_API_KEY", "")
        self.use_mock = os.getenv("USE_MOCK_JGB_API", "true").lower() == "true"
        self.timeout = 10.0

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

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

    async def _send(
        self, method: str, path: str, *,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Send HTTP request to JGB API with error/timeout handling."""
        url = f"{self.api_base_url}{path}"
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
            return self._fallback_response(f"API 逾時: {str(e)}")
        except httpx.HTTPError as e:
            logger.error(f"JGB API {method} 錯誤: {url} - {e}")
            return self._fallback_response(f"API 錯誤: {str(e)}")

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
        **kwargs,
    ) -> dict[str, Any]:
        """查詢帳單列表。

        授權形態：
          - 租客情境（既有）：role_id + user_id（身分保護，缺一降級）；
          - b2b per-contract / per-bill：role_id + contract_ids 或 bill_ref——
            與 get_contracts 相同以 role_id 為授權主體，不需 user_id。

        `bill_ref` 識別語意參數（adapter，billing-conversational-facets R2.1）：
          純數字 → 先 get_bill_detail 直查（單筆包成列）；查無 → 當合約 id 解析；
          非數字 → get_contracts(keyword) 解析 → 取第一筆合約 → 該合約帳單列候選。
          解析失敗/例外 → 空列不拋（引擎走 0 筆追問路，不炸降級句）。
        """
        if not (self._validate_identity(role_id, user_id)
                or (role_id and (contract_ids or bill_ref))):
            return self._degraded_response()

        if self.use_mock:
            return self._mock_get_bills(role_id, user_id, month, status)

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
            params["contract_ids"] = contract_ids
        if month:
            params["month"] = month
        if status:
            params["status"] = status
        return await self._request("/api/external/v1/bills", params)

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
        **kwargs,
    ) -> dict[str, Any]:
        """查詢合約狀態總覽"""
        if not role_id:
            return self._degraded_response()

        if self.use_mock:
            return self._mock_get_contracts(role_id, user_id, status)

        params: dict[str, Any] = {"role_id": role_id}
        if contract_ids:
            params["contract_ids"] = contract_ids
        if keyword:
            params["keyword"] = keyword
        return await self._request(
            "/api/external/v1/contracts/status-overview", params
        )

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
            return self._mock_get_estates(role_id, keyword)

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

        if self.use_mock:
            return self._mock_get_bill_detail(role_id, bill_id)

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
        """查詢付款交易的金流 API 日誌"""
        if not role_id:
            return self._degraded_response()

        if self.use_mock:
            return self._mock_get_payment_logs(role_id, payment_id, bill_id)

        params: dict[str, Any] = {"role_id": role_id}
        if payment_id is not None:
            params["payment_id"] = payment_id
        if bill_id is not None:
            params["bill_id"] = bill_id
        if transaction_id:
            params["transaction_id"] = transaction_id
        return await self._request("/api/external/v1/payment-logs", params)

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

        if self.use_mock:
            return self._mock_get_invoice_logs(role_id, invoice_id, bill_id)

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
        keyword = (keyword or "").strip()
        if not role_id or not keyword:
            return self._degraded_response()
        if self.use_mock:
            return {"success": True, "data": [{
                "member_user_id": 292, "character_id": 1151, "character_name": "檢視者",
                "is_owner": False, "match_field": "email"}]}
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
            return {"success": True, "data": [{
                "character_name": "檢視者",
                "abilities": {"show_bill": False, "show_owner_bill": True,
                              "show_contract": False, "show_owner_contract": True,
                              "show_estate": False, "show_owner_estate": True}}]}
        raw = await self._request(
            f"/api/external/v1/roles/{role_id}/members/{user_id}/permissions", {})
        data = (raw or {}).get("data")
        return {"success": bool((raw or {}).get("success")),
                "data": [data] if isinstance(data, dict) else []}

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
            return {"success": True, "data": []}   # mock 預設看不到（owner-scoped 未指派）
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

        端點無 keyword 參數 → 拉全列（per_page=200）後 client 端以 keyword 對
        estate_name/name 過濾（後端當裁判精神：查無回空列不拋）；estate_id 原生透傳。
        欄位：is_online/is_poweron/balance/available_meter/current_reading/synced_at 等
        （消費端注意：離線時皆為最後同步快照；is_poweron 三態失真見 J-I1，builder 端防護）。
        """
        if not role_id:
            return self._degraded_response()

        if self.use_mock:
            rows = [{
                "id": 501, "estate_id": 9001, "estate_name": "海大質感獨立套房",
                "name": "3F 分電表", "manufacturer": "DAE", "meter_type": "cloud",
                "is_online": True, "is_topup": True, "enable_topup": True,
                "balance": 350.0, "available_meter": 87.5, "current_reading": 1234.5,
                "is_poweron": True, "is_low_battery": False,
                "synced_at": "2026-07-04 10:35:00"}]
        else:
            params: dict[str, Any] = {"role_id": role_id, "per_page": 200}
            if estate_id:
                params["estate_id"] = estate_id
            raw = await self._request("/api/external/v1/meters", params)
            if not (raw or {}).get("success"):
                return {"success": False, "data": []}
            data = raw.get("data")
            rows = data if isinstance(data, list) else []

        kw = (keyword or "").strip()
        if kw:
            rows = [m for m in rows
                    if kw in (m.get("estate_name") or "") or kw in (m.get("name") or "")]
        return {"success": True, "data": rows}

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

    def _mock_get_invoices(
        self,
        role_id: str,
        user_id: str,
        bill_id: Optional[int] = None,
        status: Optional[int] = None,
    ) -> dict[str, Any]:
        """對齊 InvoiceApiController@index"""
        logger.info(f"[MOCK] get_invoices: role_id={role_id}, user_id={user_id}")
        return {
            "success": True,
            "mapping": {
                "status": {
                    "0": "未開立",
                    "1": "已開立",
                    "2": "作廢",
                    "3": "折讓",
                    "4": "作廢折讓",
                },
                "category": {
                    "B2B": "企業對企業發票",
                    "B2C": "企業對消費者發票",
                },
                "tax_type": {
                    "1": "應稅",
                    "2": "零稅率",
                    "3": "免稅",
                    "9": "混合",
                },
            },
            "data": [
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
            ],
            "pagination": {
                "current_page": 1,
                "per_page": 50,
                "total": 2,
                "total_pages": 1,
                "has_more": False,
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
        user_id: str,
        month: Optional[str] = None,
    ) -> dict[str, Any]:
        """對齊 PaymentApiController@index"""
        logger.info(f"[MOCK] get_payments: role_id={role_id}, user_id={user_id}")
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
            "data": [
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
            ],
            "pagination": {
                "current_page": 1,
                "per_page": 50,
                "total": 2,
                "total_pages": 1,
                "has_more": False,
            },
        }

    def _mock_get_repairs(
        self,
        role_id: str,
        user_id: str,
        status: Optional[str] = None,
    ) -> dict[str, Any]:
        """對齊 RepairApiController@index"""
        logger.info(f"[MOCK] get_repairs: role_id={role_id}, user_id={user_id}")
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
                    "1": "緊急",
                    "2": "非緊急",
                },
            },
            "data": [
                {
                    "id": 3001,
                    "status": 16,
                    "emergency_status": 2,
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
                    "emergency_status": 1,
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
            ],
            "pagination": {
                "current_page": 1,
                "per_page": 50,
                "total": 2,
                "total_pages": 1,
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
    ) -> dict[str, Any]:
        """對齊 EstateApiController@index"""
        logger.info(f"[MOCK] get_estates: role_id={role_id}, keyword={keyword}")
        all_estates = [
            {
                "id": 54126,
                "url": "https://www.jgbsmart.com/house/AABBCC?living=1",
                "user_id": 1001,
                "role_id": int(role_id) if role_id else 20151,
                "role_id_comment": "房東編號",
                "team_id": int(role_id) if role_id else 20151,
                "team_id_comment": "團隊編號（同 role_id）",
                "team_name": "好租管理",
                "team_name_comment": "物件歸屬",
                "serial_id": None,
                "title": "信義區精緻套房",
                "status": 2,
                "country": "TW",
                "country_id": 1,
                "city": "台北市",
                "city_id": 2,
                "district": "信義區",
                "district_id": 10,
                "address": "信義路五段7號",
                "full_address": "台北市信義區信義路五段7號3樓",
                "display_address": "信義路五段7號",
                "full_display_address": "台北市信義區信義路五段7號3樓",
                "latitude": "25.03360000",
                "longitude": "121.56480000",
                "use_for": "residential",
                "space_type": "flat",
                "building": "condo",
                "room_count": 1,
                "size": 15,
                "size_data": {"size": {"m2": 15, "sqm": 4.54, "sq_ft": 161.46}},
                "direction": "south",
                "floor": "3",
                "total_floor": "12",
                "rent": 25000,
                "currency": "TWD",
                "deposit": 2,
                "deposit_type": 0,
                "deposit_amount": 50000,
                "fees": None,
                "management_fee": 0,
                "facilities": None,
                "labels_fees": None,
                "avatar": None,
                "gallery": None,
                "floor_plan": None,
                "vr_url": None,
                "community_id": None,
                "community_name": None,
                "property_purpose_key": 1,
                "bit_status": 1026,
                "created_at": "2025-01-15 10:30:00",
                "updated_at": "2025-03-20 14:25:00",
                "estate_room_number": "3F-1",
            },
            {
                "id": 54200,
                "url": "https://www.jgbsmart.com/house/DDEEFF?living=1",
                "user_id": 1001,
                "role_id": int(role_id) if role_id else 20151,
                "role_id_comment": "房東編號",
                "team_id": int(role_id) if role_id else 20151,
                "team_id_comment": "團隊編號（同 role_id）",
                "team_name": "好租管理",
                "team_name_comment": "物件歸屬",
                "serial_id": None,
                "title": "中山區溫馨雅房",
                "status": 2,
                "country": "TW",
                "country_id": 1,
                "city": "台北市",
                "city_id": 2,
                "district": "中山區",
                "district_id": 4,
                "address": "中山北路二段10號",
                "full_address": "台北市中山區中山北路二段10號5樓",
                "display_address": "中山北路二段10號",
                "full_display_address": "台北市中山區中山北路二段10號5樓",
                "latitude": "25.06120000",
                "longitude": "121.52250000",
                "use_for": "residential",
                "space_type": "flat",
                "building": "apartment",
                "room_count": 1,
                "size": 8,
                "size_data": {"size": {"m2": 8, "sqm": 2.42, "sq_ft": 86.11}},
                "direction": "east",
                "floor": "5",
                "total_floor": "7",
                "rent": 12000,
                "currency": "TWD",
                "deposit": 2,
                "deposit_type": 0,
                "deposit_amount": 24000,
                "fees": None,
                "management_fee": 0,
                "facilities": None,
                "labels_fees": None,
                "avatar": None,
                "gallery": None,
                "floor_plan": None,
                "vr_url": None,
                "community_id": None,
                "community_name": None,
                "property_purpose_key": 1,
                "bit_status": 1026,
                "created_at": "2025-02-01 09:00:00",
                "updated_at": "2025-04-10 11:00:00",
                "estate_room_number": "5F-2",
            },
            {
                "id": 54305,
                "url": "https://www.jgbsmart.com/house/GGHHII?living=1",
                "user_id": 1001,
                "role_id": int(role_id) if role_id else 20151,
                "role_id_comment": "房東編號",
                "team_id": int(role_id) if role_id else 20151,
                "team_id_comment": "團隊編號（同 role_id）",
                "team_name": "好租管理",
                "team_name_comment": "物件歸屬",
                "serial_id": None,
                "title": "大安區景觀兩房",
                "status": 2,
                "country": "TW",
                "country_id": 1,
                "city": "台北市",
                "city_id": 2,
                "district": "大安區",
                "district_id": 6,
                "address": "敦化南路一段100號",
                "full_address": "台北市大安區敦化南路一段100號12樓",
                "display_address": "敦化南路一段100號",
                "full_display_address": "台北市大安區敦化南路一段100號12樓",
                "latitude": "25.04210000",
                "longitude": "121.54920000",
                "use_for": "residential",
                "space_type": "flat",
                "building": "condo",
                "room_count": 2,
                "size": 25,
                "size_data": {"size": {"m2": 25, "sqm": 7.56, "sq_ft": 269.10}},
                "direction": "west",
                "floor": "12",
                "total_floor": "15",
                "rent": 35000,
                "currency": "TWD",
                "deposit": 2,
                "deposit_type": 0,
                "deposit_amount": 70000,
                "fees": None,
                "management_fee": 2000,
                "facilities": None,
                "labels_fees": None,
                "avatar": None,
                "gallery": None,
                "floor_plan": None,
                "vr_url": None,
                "community_id": None,
                "community_name": None,
                "property_purpose_key": 1,
                "bit_status": 1026,
                "created_at": "2025-03-10 14:00:00",
                "updated_at": "2025-05-01 16:30:00",
                "estate_room_number": "12F-A",
            },
        ]
        # 簡易關鍵字過濾
        if keyword:
            filtered = [
                e for e in all_estates
                if keyword in e["title"] or keyword in e["full_address"]
            ]
        else:
            filtered = all_estates

        return {
            "success": True,
            "data": filtered,
            "pagination": {
                "current_page": 1,
                "per_page": 10,
                "total": len(filtered),
                "total_pages": 1,
                "has_more": False,
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
        """對齊 PaymentLogApiController@index"""
        logger.info(f"[MOCK] get_payment_logs: role_id={role_id}, payment_id={payment_id}, bill_id={bill_id}")
        return {
            "success": True,
            "mapping": {
                "action": {
                    "credit_card": "信用卡", "atm": "ATM 轉帳",
                    "cvs": "超商代碼", "cvs_barcode": "超商條碼",
                    "icashpay": "愛金卡",
                    "google_pay": "Google Pay", "samsung_pay": "Samsung Pay",
                },
                "type": {"bill": "帳單付款", "subscription": "訂閱付款", "topup": "儲值"},
            },
            "data": [
                {
                    "id": 50001,
                    "role_id": int(role_id) if role_id else 0,
                    "payment_id": payment_id or 9876,
                    "transaction_id": "TXN20260401123456",
                    "manufacturer": "newebpay",
                    "action": "credit_card",
                    "type": "bill",
                    "amount": "25000",
                    "note": "信用卡授權失敗",
                    "response": {
                        "Status": "LIB10002",
                        "Message": "信用卡授權失敗，請確認卡片資訊",
                    },
                    "created_at": "2026-04-01T14:00:00+08:00",
                },
            ],
            "pagination": {
                "current_page": 1, "per_page": 50,
                "total": 1, "total_pages": 1, "has_more": False,
            },
        }

    def _mock_get_invoice_logs(
        self, role_id: str, invoice_id: Optional[int] = None,
        bill_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """對齊 InvoiceLogApiController@index"""
        logger.info(f"[MOCK] get_invoice_logs: role_id={role_id}, invoice_id={invoice_id}, bill_id={bill_id}")
        return {
            "success": True,
            "mapping": {
                "action": {
                    "issue": "開立", "invalid": "作廢",
                    "allowance": "折讓", "allowance_invalid": "作廢折讓",
                    "search": "查詢",
                },
            },
            "data": [
                {
                    "id": 60001,
                    "invoice_id": invoice_id or 5001,
                    "bill_id": bill_id or 12345,
                    "manufacturer": "ezpay",
                    "action": "issue",
                    "type": "bill",
                    "http_code": 200,
                    "response_data": {
                        "RtnCode": 1,
                        "RtnMsg": "開立發票成功",
                        "InvoiceNumber": "AZ00000123",
                    },
                    "note": None,
                    "created_at": "2026-04-01T10:00:00+08:00",
                },
            ],
            "pagination": {
                "current_page": 1, "per_page": 50,
                "total": 1, "total_pages": 1, "has_more": False,
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
