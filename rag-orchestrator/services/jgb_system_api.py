"""
JGB System API 服務

JGB 好租寶外部 API 的 client 封裝，支援 mock/real 模式切換。
提供 7 個查詢方法：帳單、發票、合約、點交資格、繳費紀錄、修繕、租客摘要。

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

    async def _request(
        self, path: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Send GET request to JGB API with error/timeout handling."""
        url = f"{self.api_base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url, params=params, headers=self._headers()
                )
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as e:
            logger.error(f"JGB API 逾時: {url} - {e}")
            return self._fallback_response(f"API 逾時: {str(e)}")
        except httpx.HTTPError as e:
            logger.error(f"JGB API 錯誤: {url} - {e}")
            return self._fallback_response(f"API 錯誤: {str(e)}")

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_bills(
        self,
        role_id: str,
        user_id: str,
        month: Optional[str] = None,
        status: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """查詢帳單列表"""
        if not self._validate_identity(role_id, user_id):
            return self._degraded_response()

        if self.use_mock:
            return self._mock_get_bills(role_id, user_id, month, status)

        params: dict[str, Any] = {"role_id": role_id, "user_id": user_id}
        if month:
            params["month"] = month
        if status:
            params["status"] = status
        return await self._request("/api/external/v1/bills", params)

    async def get_invoices(
        self,
        role_id: str,
        user_id: str,
        bill_id: Optional[int] = None,
        status: Optional[int] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """查詢發票列表"""
        if not self._validate_identity(role_id, user_id):
            return self._degraded_response()

        if self.use_mock:
            return self._mock_get_invoices(role_id, user_id, bill_id, status)

        params: dict[str, Any] = {"role_id": role_id, "user_id": user_id}
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

    # ------------------------------------------------------------------
    # Mock implementations
    # ------------------------------------------------------------------

    def _mock_get_bills(
        self,
        role_id: str,
        user_id: str,
        month: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict[str, Any]:
        logger.info(f"[MOCK] get_bills: role_id={role_id}, user_id={user_id}")
        return {
            "success": True,
            "mapping": {
                "bit_status": {
                    "2": "應到帳",
                    "16": "已到帳",
                    "64": "逾期",
                },
                "invoice_status": {
                    "0": "未開立",
                    "1": "已開立",
                    "2": "已作廢",
                },
            },
            "data": [
                {
                    "id": 12345,
                    "contract_id": 678,
                    "estate_id": 456,
                    "bit_status": 2,
                    "title": "2026年4月租金",
                    "currency": "TWD",
                    "total": 25000.00,
                    "date_expire": 20260405,
                    "invoice_status": 0,
                    "invoice_number": None,
                    "pay_at": None,
                    "complete_at": None,
                    "created_at": "2026-03-25 10:30:00",
                    "updated_at": "2026-04-01 00:00:00",
                },
                {
                    "id": 12340,
                    "contract_id": 678,
                    "estate_id": 456,
                    "bit_status": 16,
                    "title": "2026年3月租金",
                    "currency": "TWD",
                    "total": 25000.00,
                    "date_expire": 20260305,
                    "invoice_status": 1,
                    "invoice_number": "AZ00000120",
                    "pay_at": "2026-03-03 14:00:00",
                    "complete_at": "2026-03-03 15:00:00",
                    "created_at": "2026-02-25 10:30:00",
                    "updated_at": "2026-03-03 15:00:00",
                },
                {
                    "id": 12350,
                    "contract_id": 678,
                    "estate_id": 456,
                    "bit_status": 64,
                    "title": "2025年12月租金",
                    "currency": "TWD",
                    "total": 25000.00,
                    "date_expire": 20251205,
                    "invoice_status": 0,
                    "invoice_number": None,
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
        logger.info(f"[MOCK] get_invoices: role_id={role_id}, user_id={user_id}")
        return {
            "success": True,
            "mapping": {
                "status": {"1": "已開立", "2": "已作廢"},
                "category": {"B2C": "一般消費者發票", "B2B": "營業人發票"},
            },
            "data": [
                {
                    "id": 5001,
                    "bill_id": 12345,
                    "number": "AZ00000123",
                    "status": 1,
                    "category": "B2C",
                    "amount": 25000,
                    "created_at": "2026-04-01 10:00:00",
                    "invalid_at": None,
                },
                {
                    "id": 5002,
                    "bill_id": 12340,
                    "number": "AZ00000120",
                    "status": 2,
                    "category": "B2C",
                    "amount": 25000,
                    "created_at": "2026-03-01 10:00:00",
                    "invalid_at": "2026-03-15 10:00:00",
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
        logger.info(f"[MOCK] get_contracts: role_id={role_id}, user_id={user_id}")
        return {
            "success": True,
            "mapping": {
                "bit_status_flags": {
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
        logger.info(
            f"[MOCK] get_contract_checkin_eligibility: "
            f"role_id={role_id}, user_id={user_id}, contract_id={contract_id}"
        )
        return {
            "success": True,
            "data": {
                "contract_id": contract_id,
                "eligible": True,
                "contract_status": "執行中",
                "first_bill_paid": True,
                "deposit_required": 50000.00,
                "deposit_paid": 50000.00,
                "blockers": [],
            },
        }

    def _mock_get_payments(
        self,
        role_id: str,
        user_id: str,
        month: Optional[str] = None,
    ) -> dict[str, Any]:
        logger.info(f"[MOCK] get_payments: role_id={role_id}, user_id={user_id}")
        return {
            "success": True,
            "mapping": {
                "status": {"0": "待處理", "2": "已完成"},
                "payment_method": {
                    "credit_card": "信用卡",
                    "atm": "ATM 轉帳",
                    "barcode": "超商條碼",
                },
            },
            "data": [
                {
                    "id": 9876,
                    "bill_id": 12345,
                    "status": 2,
                    "manufacturer": "newebpay",
                    "payment_method": "credit_card",
                    "currency": "TWD",
                    "amount": 25000.00,
                    "paid_at": "2026-04-01 15:30:00",
                    "created_at": "2026-04-01 14:00:00",
                },
                {
                    "id": 9870,
                    "bill_id": 12340,
                    "status": 0,
                    "manufacturer": "newebpay",
                    "payment_method": "atm",
                    "currency": "TWD",
                    "amount": 25000.00,
                    "paid_at": None,
                    "created_at": "2026-03-01 14:00:00",
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
        logger.info(f"[MOCK] get_repairs: role_id={role_id}, user_id={user_id}")
        return {
            "success": True,
            "mapping": {
                "status": {"1": "已申請", "2": "處理中", "16": "已完成"},
            },
            "data": [
                {
                    "id": 3001,
                    "estate_name": "信義區套房A",
                    "status": 16,
                    "category_name": "水電類",
                    "item_name": "水管漏水",
                    "is_emergency": False,
                    "assigned_vendor": "信義水電行",
                    "scheduled_date": "2026-04-12",
                    "completed_at": "2026-04-12 14:00:00",
                    "cost": 3500.00,
                    "created_at": "2026-04-05 09:00:00",
                },
                {
                    "id": 3002,
                    "estate_name": "信義區套房A",
                    "status": 1,
                    "category_name": "設備類",
                    "item_name": "冷氣不冷",
                    "is_emergency": True,
                    "assigned_vendor": None,
                    "scheduled_date": None,
                    "completed_at": None,
                    "cost": None,
                    "created_at": "2026-04-15 14:00:00",
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
        logger.info(
            f"[MOCK] get_tenant_summary: role_id={role_id}, user_id={user_id}"
        )
        return {
            "success": True,
            "data": {
                "tenant_info": {
                    "name": "王小明",
                    "email": "tenant@example.com",
                    "phone": "0912345678",
                    "is_registered": True,
                    "is_email_verified": True,
                },
                "contract_summary": {
                    "active_count": 1,
                    "history_count": 2,
                },
                "bill_summary": {
                    "unpaid_count": 1,
                    "total_count": 24,
                    "on_time_ratio": 87,
                },
                "repair_summary": {
                    "total_count": 5,
                    "in_progress_count": 1,
                },
            },
        }
