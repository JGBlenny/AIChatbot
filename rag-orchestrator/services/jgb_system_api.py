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
            "error": "missing_identity",
            "message": DEGRADED_MESSAGE,
        }

    @staticmethod
    def _fallback_response(error_detail: str) -> dict[str, Any]:
        return {
            "success": False,
            "error": error_detail,
            "message": FALLBACK_MESSAGE,
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
        user_id: str,
        status: Optional[str] = None,
    ) -> dict[str, Any]:
        """查詢合約列表"""
        if not self._validate_identity(role_id, user_id):
            return self._degraded_response()

        if self.use_mock:
            return self._mock_get_contracts(role_id, user_id, status)

        params: dict[str, Any] = {"role_id": role_id, "user_id": user_id}
        if status:
            params["status"] = status
        return await self._request("/api/external/v1/contracts", params)

    async def get_contract_checkin_eligibility(
        self,
        role_id: str,
        user_id: str,
        contract_id: int,
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
                    "rate": 1.00,
                    "date_start": 20260401,
                    "date_end": 20260430,
                    "date_expire": 20260405,
                    "date_expire_note": ["繳費期限：2026/04/05"],
                    "cycle": 1,
                    "days": 30,
                    "is_auto_pay": False,
                    "is_paid_on_time": None,
                    "online_payment_method": "newebpay",
                    "online_payment_action": "credit_card",
                    "payment_id": 9876,
                    "invoice_status": 0,
                    "invoice_number": None,
                    "ready_at": "2026-04-01T00:00:00+08:00",
                    "pay_at": None,
                    "complete_at": None,
                    "created_at": "2026-03-25T10:30:00+08:00",
                    "updated_at": "2026-04-01T00:00:00+08:00",
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
                    "rate": 1.00,
                    "date_start": 20260301,
                    "date_end": 20260331,
                    "date_expire": 20260305,
                    "date_expire_note": ["繳費期限：2026/03/05"],
                    "cycle": 1,
                    "days": 31,
                    "is_auto_pay": False,
                    "is_paid_on_time": True,
                    "online_payment_method": "newebpay",
                    "online_payment_action": "credit_card",
                    "payment_id": 9870,
                    "invoice_status": 1,
                    "invoice_number": "AZ00000120",
                    "ready_at": "2026-03-01T00:00:00+08:00",
                    "pay_at": "2026-03-03T14:00:00+08:00",
                    "complete_at": "2026-03-03T15:00:00+08:00",
                    "created_at": "2026-02-25T10:30:00+08:00",
                    "updated_at": "2026-03-03T15:00:00+08:00",
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
                    "rate": 1.00,
                    "date_start": 20251201,
                    "date_end": 20251231,
                    "date_expire": 20251205,
                    "date_expire_note": ["繳費期限：2025/12/05"],
                    "cycle": 1,
                    "days": 31,
                    "is_auto_pay": False,
                    "is_paid_on_time": None,
                    "online_payment_method": "newebpay",
                    "online_payment_action": "credit_card",
                    "payment_id": None,
                    "invoice_status": 0,
                    "invoice_number": None,
                    "ready_at": "2025-12-01T00:00:00+08:00",
                    "pay_at": None,
                    "complete_at": None,
                    "created_at": "2025-11-25T10:30:00+08:00",
                    "updated_at": "2025-12-06T00:00:00+08:00",
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
            "data": [
                {
                    "id": 5001,
                    "bill_id": 12345,
                    "payment_id": 9876,
                    "payment_no": "P202604010001",
                    "manufacturer": "ezpay",
                    "year": 2026,
                    "month": 4,
                    "number": "AZ00000123",
                    "random_num": "1234",
                    "status": 1,
                    "upload_status": 1,
                    "category": "B2C",
                    "buyer_name": "王小明",
                    "buyer_ubn": None,
                    "buyer_address": None,
                    "buyer_email": "tenant@example.com",
                    "carrier_type": 0,
                    "carrier_number": "/ABC+123",
                    "love_code": None,
                    "print_flag": 0,
                    "tax_type": 1,
                    "tax_rate": 0.05,
                    "tax_amt": 1190,
                    "amt": 23810,
                    "total_amt": 25000,
                    "item_data": [
                        {
                            "item_name": "2026年4月租金",
                            "item_count": 1,
                            "item_unit": "月",
                            "item_price": 25000,
                            "item_amount": 25000,
                        }
                    ],
                    "bar_code": "10604AZ000001231234",
                    "url": "https://inv.ezpay.com.tw/...",
                    "added_at": "2026-04-01T10:00:00+08:00",
                    "invalid_at": None,
                    "allowanced_at": None,
                },
                {
                    "id": 5002,
                    "bill_id": 12340,
                    "payment_id": 9870,
                    "payment_no": "P202603010001",
                    "manufacturer": "ezpay",
                    "year": 2026,
                    "month": 3,
                    "number": "AZ00000120",
                    "random_num": "5678",
                    "status": 2,
                    "upload_status": 1,
                    "category": "B2C",
                    "buyer_name": "王小明",
                    "buyer_ubn": None,
                    "buyer_address": None,
                    "buyer_email": "tenant@example.com",
                    "carrier_type": 0,
                    "carrier_number": "/ABC+123",
                    "love_code": None,
                    "print_flag": 0,
                    "tax_type": 1,
                    "tax_rate": 0.05,
                    "tax_amt": 1190,
                    "amt": 23810,
                    "total_amt": 25000,
                    "item_data": [
                        {
                            "item_name": "2026年3月租金",
                            "item_count": 1,
                            "item_unit": "月",
                            "item_price": 25000,
                            "item_amount": 25000,
                        }
                    ],
                    "bar_code": "10603AZ000001205678",
                    "url": "https://inv.ezpay.com.tw/...",
                    "added_at": "2026-03-01T10:00:00+08:00",
                    "invalid_at": "2026-03-15T10:00:00+08:00",
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
        logger.info(f"[MOCK] get_contracts: role_id={role_id}, user_id={user_id}")
        return {
            "success": True,
            "data": [
                {
                    "id": 678,
                    "father_id": None,
                    "is_newest": 1,
                    "property_purpose_key": 1,
                    "contract_type": "general",
                    "contract_is_existing": False,
                    "bit_status": 8,
                    "estate_id": 456,
                    "title": "信義區套房A",
                    "country": "TW",
                    "city": "台北市",
                    "district": "信義區",
                    "address": "信義路五段7號",
                    "room_number": "A01",
                    "currency": "TWD",
                    "rent": 25000.00,
                    "deposit_type": 0,
                    "deposit": 2.0,
                    "deposit_amount": 50000.00,
                    "cycle": 1,
                    "cycle_type": 2,
                    "cycle_date": 1,
                    "date_start": 20260101,
                    "date_end": 20261231,
                    "is_auto_pay": False,
                    "online_payment_method": "newebpay",
                    "online_payment_action": "credit_card",
                    "fees": {
                        "電費": 0,
                        "水費": 0,
                        "瓦斯費": 0,
                        "網路費": 0,
                        "管理費": 1500,
                    },
                    "allow_early_termination": True,
                    "early_termination_days": 30,
                    "enable_late_fee": 0,
                    "sales_tax_type": 0,
                    "is_auto_generate_invoice": 0,
                    "contract_inviting_at": "2025-12-15T10:00:00+08:00",
                    "contract_finish_sign_at": "2025-12-20T14:30:00+08:00",
                    "created_at": "2025-12-10T09:00:00+08:00",
                    "updated_at": "2026-01-01T00:00:00+08:00",
                },
                {
                    "id": 600,
                    "father_id": None,
                    "is_newest": 1,
                    "property_purpose_key": 1,
                    "contract_type": "general",
                    "contract_is_existing": False,
                    "bit_status": 1024,
                    "estate_id": 400,
                    "title": "中山區雅房B",
                    "country": "TW",
                    "city": "台北市",
                    "district": "中山區",
                    "address": "中山北路二段10號",
                    "room_number": "B02",
                    "currency": "TWD",
                    "rent": 18000.00,
                    "deposit_type": 0,
                    "deposit": 2.0,
                    "deposit_amount": 36000.00,
                    "cycle": 1,
                    "cycle_type": 2,
                    "cycle_date": 1,
                    "date_start": 20250101,
                    "date_end": 20251231,
                    "is_auto_pay": False,
                    "online_payment_method": "newebpay",
                    "online_payment_action": "atm",
                    "fees": {
                        "電費": 0,
                        "水費": 0,
                        "管理費": 1000,
                    },
                    "allow_early_termination": False,
                    "early_termination_days": 0,
                    "enable_late_fee": 1,
                    "sales_tax_type": 0,
                    "is_auto_generate_invoice": 0,
                    "contract_inviting_at": "2024-12-10T10:00:00+08:00",
                    "contract_finish_sign_at": "2024-12-15T14:30:00+08:00",
                    "created_at": "2024-12-05T09:00:00+08:00",
                    "updated_at": "2025-12-31T23:59:59+08:00",
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
                "contract_status": {
                    "bit_status": 8,
                    "label": "執行中合約",
                    "is_signed": True,
                },
                "first_bill_status": {
                    "bill_id": 12340,
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
        logger.info(f"[MOCK] get_payments: role_id={role_id}, user_id={user_id}")
        return {
            "success": True,
            "data": [
                {
                    "id": 9876,
                    "no": "P202604010001",
                    "transaction_id": "TXN20260401123456",
                    "user_id": 100,
                    "role_id": 200,
                    "creditor_user_id": 50,
                    "creditor_role_id": 300,
                    "type": "bill",
                    "status": 2,
                    "manufacturer": "newebpay",
                    "payment": "credit_card",
                    "currency": "TWD",
                    "orig_currency": "TWD",
                    "orig_price": 25000.00,
                    "price": 25000.00,
                    "final_currency": "TWD",
                    "final_price": 25000.00,
                    "discount_cash": 0.00,
                    "discount_price": 0.00,
                    "payment_times": 1,
                    "data": "末四碼 1234",
                    "note": "2026年4月租金",
                    "items": [{"name": "租金", "amount": 25000}],
                    "invoice_status": 1,
                    "invoice_number": "AZ00000123",
                    "ymd": 20260401,
                    "payment_completed_ymd": 20260401,
                    "payment_completed_at": "2026-04-01T15:30:00+08:00",
                    "created_at": "2026-04-01T14:00:00+08:00",
                    "updated_at": "2026-04-01T15:30:00+08:00",
                },
                {
                    "id": 9870,
                    "no": "P202603010001",
                    "transaction_id": "TXN20260301654321",
                    "user_id": 100,
                    "role_id": 200,
                    "creditor_user_id": 50,
                    "creditor_role_id": 300,
                    "type": "bill",
                    "status": 0,
                    "manufacturer": "newebpay",
                    "payment": "atm",
                    "currency": "TWD",
                    "orig_currency": "TWD",
                    "orig_price": 25000.00,
                    "price": 25000.00,
                    "final_currency": "TWD",
                    "final_price": 25000.00,
                    "discount_cash": 0.00,
                    "discount_price": 0.00,
                    "payment_times": 1,
                    "data": None,
                    "note": "2026年3月租金",
                    "items": [{"name": "租金", "amount": 25000}],
                    "invoice_status": 0,
                    "invoice_number": None,
                    "ymd": 20260301,
                    "payment_completed_ymd": None,
                    "payment_completed_at": None,
                    "created_at": "2026-03-01T14:00:00+08:00",
                    "updated_at": "2026-03-01T14:00:00+08:00",
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
            "data": [
                {
                    "id": 3001,
                    "estate_id": 456,
                    "contract_id": 678,
                    "role_id": 200,
                    "user_id": 50,
                    "to_user_id": 100,
                    "to_role_id": 201,
                    "status": 16,
                    "emergency_status": 1,
                    "estate_title": "信義區套房A",
                    "estate_full_address": "台北市信義區信義路五段7號",
                    "estate_room_number": "A01",
                    "category_id": 1,
                    "category_name": "水電類",
                    "item_id": 3,
                    "item_name": "水管漏水",
                    "broken_reason": "管線老化",
                    "broken_note": "浴室水管持續滴水",
                    "broken_photos": ["photo1.jpg", "photo2.jpg"],
                    "manufacturer_id": 10,
                    "manufacturer_name": "信義水電行",
                    "manufacturer_phone": "02-12345678",
                    "currency": "TWD",
                    "total": 3500.00,
                    "apply_role_key": 3,
                    "apply_role_id": 201,
                    "pre_assign_data": [
                        {"date": "2026-04-10", "time_slot": "上午"}
                    ],
                    "assign_data": [
                        {
                            "date": "2026-04-12",
                            "time": "10:00",
                            "manufacturer_id": 10,
                            "manufacturer_name": "信義水電行",
                        }
                    ],
                    "user_note": "已完成修繕，更換新水管",
                    "to_user_note": "謝謝，已確認修繕完成",
                    "apply_at": "2026-04-05T09:00:00+08:00",
                    "assign_at": "2026-04-06T11:00:00+08:00",
                    "complete_at": "2026-04-12T14:00:00+08:00",
                    "finish_at": "2026-04-13T10:00:00+08:00",
                    "archive_at": None,
                    "created_at": "2026-04-05T09:00:00+08:00",
                    "updated_at": "2026-04-13T10:00:00+08:00",
                },
                {
                    "id": 3002,
                    "estate_id": 456,
                    "contract_id": 678,
                    "role_id": 200,
                    "user_id": 50,
                    "to_user_id": 100,
                    "to_role_id": 201,
                    "status": 1,
                    "emergency_status": 2,
                    "estate_title": "信義區套房A",
                    "estate_full_address": "台北市信義區信義路五段7號",
                    "estate_room_number": "A01",
                    "category_id": 2,
                    "category_name": "設備類",
                    "item_id": 5,
                    "item_name": "冷氣不冷",
                    "broken_reason": "冷媒不足",
                    "broken_note": "客廳冷氣吹出的風不冷",
                    "broken_photos": ["photo3.jpg"],
                    "manufacturer_id": None,
                    "manufacturer_name": None,
                    "manufacturer_phone": None,
                    "currency": "TWD",
                    "total": None,
                    "apply_role_key": 3,
                    "apply_role_id": 201,
                    "pre_assign_data": [],
                    "assign_data": [],
                    "user_note": None,
                    "to_user_note": None,
                    "apply_at": "2026-04-15T14:00:00+08:00",
                    "assign_at": None,
                    "complete_at": None,
                    "finish_at": None,
                    "archive_at": None,
                    "created_at": "2026-04-15T14:00:00+08:00",
                    "updated_at": "2026-04-15T14:00:00+08:00",
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
                    "id": 5001,
                    "lessee_user_id": 100,
                    "lessee_role_id": 201,
                    "lessor_role_id": 200,
                    "lessee_name": "王小明",
                    "lessee_email": "tenant@example.com",
                    "lessee_registered_phone": "0912345678",
                    "lessee_registered_phone_country": "TW",
                    "is_lessee_user_registered": 1,
                    "lessee_nationality": "TW",
                    "lessee_birthday": "1990-01-15",
                    "lessee_primary_contact": "phone",
                    "lessee_emergency_contact_name": "王大明",
                    "lessee_emergency_contact_phone": "0923456789",
                    "lessee_emergency_contact_relationship": "父親",
                    "active": 1,
                },
                "contract_summary": {
                    "registered_contract_count": 3,
                    "registered_contract_inviting_count": 0,
                    "registered_contract_inviting_next_count": 0,
                    "registered_contract_signed_count": 1,
                    "registered_contract_history_count": 2,
                    "exempt_register_contract_count": 0,
                    "exempt_register_contract_signed_count": 0,
                    "exempt_register_contract_history_count": 0,
                },
                "bill_summary": {
                    "income_bill_count": 24,
                    "income_bill_ready_count": 1,
                    "income_bill_ready_overdue_count": 0,
                    "income_bill_paid_count": 0,
                    "income_bill_complete_count": 23,
                    "income_bill_complete_on_time_count": 20,
                    "income_bill_complete_late_count": 3,
                    "income_bill_paid_on_time_ratio": 87,
                    "payment_bill_count": 0,
                    "payment_bill_ready_count": 0,
                    "payment_bill_paid_count": 0,
                    "payment_bill_complete_count": 0,
                },
                "repair_summary": {
                    "repair_count": 5,
                    "repair_apply_count": 0,
                    "repair_assign_count": 0,
                    "repair_complete_count": 1,
                    "repair_finish_count": 4,
                },
            },
        }
