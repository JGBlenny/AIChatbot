"""
Integration tests for JGB API: handler routing, response templates, and mock data format.

Covers:
1. APICallHandler registry has all 7 jgb_* keys mapped to callable methods
2. Response template variable substitution for bills, contracts, repairs, etc.
3. Mock data format validation against jgb_external_api_spec.md field structure
"""

import os
import re
import pytest

# Ensure mock mode is active for tests
os.environ["USE_MOCK_JGB_API"] = "true"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def jgb_api():
    """Create a JGBSystemAPI instance in mock mode."""
    from services.jgb_system_api import JGBSystemAPI
    return JGBSystemAPI()


@pytest.fixture
def handler():
    """Create an APICallHandler without db_pool (custom-code endpoints only)."""
    from services.api_call_handler import APICallHandler
    return APICallHandler(db_pool=None)


ROLE_ID = "200"
USER_ID = "100"

# All 7 JGB endpoint keys expected in the registry
JGB_ENDPOINT_KEYS = [
    "jgb_bills",
    "jgb_invoices",
    "jgb_contracts",
    "jgb_contract_checkin",
    "jgb_payments",
    "jgb_repairs",
    "jgb_tenant_summary",
]


# ===========================================================================
# 1. APICallHandler Routing Tests
# ===========================================================================

class TestAPICallHandlerRegistry:
    """Verify that APICallHandler has all 7 jgb_* keys in its registry."""

    def test_all_jgb_keys_registered(self, handler):
        """All 7 jgb_* endpoint keys must exist in api_registry."""
        for key in JGB_ENDPOINT_KEYS:
            assert key in handler.api_registry, (
                f"Missing registry key: {key}"
            )

    def test_registry_values_are_callable(self, handler):
        """Each registered value must be callable (async method reference)."""
        for key in JGB_ENDPOINT_KEYS:
            func = handler.api_registry[key]
            assert callable(func), f"Registry value for {key} is not callable"

    def test_registry_maps_to_jgb_api_methods(self, handler):
        """Each jgb_* key should map to a method on the JGBSystemAPI instance."""
        expected_method_names = {
            "jgb_bills": "get_bills",
            "jgb_invoices": "get_invoices",
            "jgb_contracts": "get_contracts",
            "jgb_contract_checkin": "get_contract_checkin_eligibility",
            "jgb_payments": "get_payments",
            "jgb_repairs": "get_repairs",
            "jgb_tenant_summary": "get_tenant_summary",
        }
        for key, method_name in expected_method_names.items():
            func = handler.api_registry[key]
            assert func.__name__ == method_name, (
                f"Registry {key} maps to {func.__name__}, expected {method_name}"
            )

    def test_jgb_api_instance_exists_on_handler(self, handler):
        """Handler must hold a jgb_api attribute of type JGBSystemAPI."""
        from services.jgb_system_api import JGBSystemAPI
        assert hasattr(handler, "jgb_api")
        assert isinstance(handler.jgb_api, JGBSystemAPI)

    def test_unknown_endpoint_not_in_registry(self, handler):
        """Non-existent key should not be in registry."""
        assert "jgb_nonexistent" not in handler.api_registry


class TestAPICallHandlerRouting:
    """Test that calling through execute_api_call routes to the correct JGB method."""

    @pytest.mark.asyncio
    async def test_route_jgb_bills(self, handler):
        """execute_api_call with endpoint=jgb_bills should route to get_bills."""
        result = await handler.execute_api_call(
            api_config={
                "endpoint": "jgb_bills",
                "params": {"role_id": ROLE_ID, "user_id": USER_ID},
            },
        )
        assert result["success"] is True
        assert "data" in result

    @pytest.mark.asyncio
    async def test_route_jgb_invoices(self, handler):
        result = await handler.execute_api_call(
            api_config={
                "endpoint": "jgb_invoices",
                "params": {"role_id": ROLE_ID, "user_id": USER_ID},
            },
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_route_jgb_contracts(self, handler):
        result = await handler.execute_api_call(
            api_config={
                "endpoint": "jgb_contracts",
                "params": {"role_id": ROLE_ID, "user_id": USER_ID},
            },
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_route_jgb_contract_checkin(self, handler):
        result = await handler.execute_api_call(
            api_config={
                "endpoint": "jgb_contract_checkin",
                "params": {
                    "role_id": ROLE_ID,
                    "user_id": USER_ID,
                    "contract_id": 678,
                },
            },
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_route_jgb_payments(self, handler):
        result = await handler.execute_api_call(
            api_config={
                "endpoint": "jgb_payments",
                "params": {"role_id": ROLE_ID, "user_id": USER_ID},
            },
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_route_jgb_repairs(self, handler):
        result = await handler.execute_api_call(
            api_config={
                "endpoint": "jgb_repairs",
                "params": {"role_id": ROLE_ID, "user_id": USER_ID},
            },
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_route_jgb_tenant_summary(self, handler):
        result = await handler.execute_api_call(
            api_config={
                "endpoint": "jgb_tenant_summary",
                "params": {"role_id": ROLE_ID, "user_id": USER_ID},
            },
        )
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_unknown_endpoint_returns_error(self, handler):
        result = await handler.execute_api_call(
            api_config={"endpoint": "jgb_nonexistent"},
        )
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_missing_endpoint_returns_error(self, handler):
        result = await handler.execute_api_call(api_config={})
        assert result["success"] is False


# ===========================================================================
# 2. Response Template Variable Substitution Tests
# ===========================================================================

class TestResponseTemplateBills:
    """Test response_template substitution for bills endpoint."""

    TEMPLATE = (
        "您好！查詢到您 {month} 月的帳單資訊如下：\n\n"
        "📋 帳單狀態：{status_text}\n"
        "💰 金額：NT$ {amount}\n"
        "📅 繳費期限：{due_date}\n"
        "🧾 發票狀態：{invoice_status_text}\n\n"
        "{diagnosis_message}"
    )

    def test_all_variables_substitute(self):
        values = {
            "month": "4",
            "status_text": "待繳費",
            "amount": "25,000",
            "due_date": "2026/04/05",
            "invoice_status_text": "未開立",
            "diagnosis_message": "請於繳費期限前完成繳費。",
        }
        result = self.TEMPLATE.format(**values)
        assert "4 月" in result
        assert "待繳費" in result
        assert "NT$ 25,000" in result
        assert "2026/04/05" in result
        assert "未開立" in result
        assert "請於繳費期限前完成繳費" in result

    def test_empty_diagnosis_message(self):
        values = {
            "month": "3",
            "status_text": "已繳費",
            "amount": "25,000",
            "due_date": "2026/03/05",
            "invoice_status_text": "已開立",
            "diagnosis_message": "",
        }
        result = self.TEMPLATE.format(**values)
        assert "已繳費" in result
        # No crash when diagnosis_message is empty
        assert result.endswith("\n\n")

    def test_missing_variable_raises_key_error(self):
        """Template with missing key should raise KeyError."""
        with pytest.raises(KeyError):
            self.TEMPLATE.format(month="4")


class TestResponseTemplateContracts:
    """Test response_template for contract-related queries."""

    TEMPLATE_CHECKIN = (
        "您的合約點交資格查詢結果如下：\n\n"
        "📋 合約編號：{contract_id}\n"
        "✅ 是否可點交：{eligible_text}\n\n"
        "{reasons_text}\n\n"
        "{guidance_message}"
    )

    def test_checkin_eligible(self):
        values = {
            "contract_id": "678",
            "eligible_text": "是",
            "reasons_text": "",
            "guidance_message": "您已符合入住條件，請聯繫管理師安排點交。",
        }
        result = self.TEMPLATE_CHECKIN.format(**values)
        assert "678" in result
        assert "是" in result
        assert "安排點交" in result

    def test_checkin_not_eligible(self):
        values = {
            "contract_id": "679",
            "eligible_text": "否",
            "reasons_text": "- 首期租金尚未繳費\n- 押金尚未收齊",
            "guidance_message": "請先完成繳費再申請點交。",
        }
        result = self.TEMPLATE_CHECKIN.format(**values)
        assert "否" in result
        assert "首期租金尚未繳費" in result
        assert "押金尚未收齊" in result

    def test_contract_variables(self):
        """Test contract query template variables."""
        template = (
            "合約資訊：\n"
            "合約編號：{contract_id}\n"
            "物件：{estate_name}\n"
            "狀態：{status_text}\n"
            "期間：{start_date} ~ {end_date}\n"
            "月租：NT$ {rent}"
        )
        values = {
            "contract_id": "678",
            "estate_name": "信義區套房A",
            "status_text": "執行中合約",
            "start_date": "2026/01/01",
            "end_date": "2026/12/31",
            "rent": "25,000",
        }
        result = template.format(**values)
        assert "信義區套房A" in result
        assert "執行中合約" in result
        assert "2026/01/01 ~ 2026/12/31" in result
        assert "NT$ 25,000" in result


class TestResponseTemplateRepairs:
    """Test response_template for repairs endpoint."""

    TEMPLATE = (
        "修繕進度：\n"
        "🔧 修繕單號：{repair_id}\n"
        "📝 項目：{description}\n"
        "📋 狀態：{status_text}\n"
        "👷 負責人：{assigned_to}\n"
        "📅 申請日期：{created_at}"
    )

    def test_repair_variables(self):
        values = {
            "repair_id": "3001",
            "description": "水管漏水",
            "status_text": "完成修繕",
            "assigned_to": "信義水電行",
            "created_at": "2026-04-05",
        }
        result = self.TEMPLATE.format(**values)
        assert "3001" in result
        assert "水管漏水" in result
        assert "完成修繕" in result
        assert "信義水電行" in result

    def test_pending_repair_no_assignee(self):
        values = {
            "repair_id": "3002",
            "description": "冷氣不冷",
            "status_text": "申請中",
            "assigned_to": "尚未指派",
            "created_at": "2026-04-15",
        }
        result = self.TEMPLATE.format(**values)
        assert "尚未指派" in result
        assert "申請中" in result


class TestResponseTemplatePayments:
    """Test response_template for payments endpoint."""

    TEMPLATE = (
        "繳費紀錄：\n"
        "💰 金額：NT$ {amount}\n"
        "💳 付款方式：{method}\n"
        "📋 狀態：{status_text}\n"
        "📅 付款時間：{paid_at}"
    )

    def test_payment_variables(self):
        values = {
            "amount": "25,000",
            "method": "信用卡",
            "status_text": "付款成功",
            "paid_at": "2026-04-01T15:30:00+08:00",
        }
        result = self.TEMPLATE.format(**values)
        assert "NT$ 25,000" in result
        assert "信用卡" in result
        assert "付款成功" in result

    def test_failed_payment(self):
        values = {
            "amount": "25,000",
            "method": "ATM",
            "status_text": "付款失敗",
            "paid_at": "N/A",
        }
        result = self.TEMPLATE.format(**values)
        assert "付款失敗" in result
        assert "N/A" in result


class TestResponseTemplateInvoices:
    """Test response_template for invoices endpoint."""

    def test_invoice_variables(self):
        template = (
            "發票資訊：\n"
            "發票號碼：{invoice_number}\n"
            "狀態：{status_text}\n"
            "種類：{category}\n"
            "金額：NT$ {amount}"
        )
        values = {
            "invoice_number": "AZ00000123",
            "status_text": "已開立",
            "category": "B2C",
            "amount": "25,000",
        }
        result = template.format(**values)
        assert "AZ00000123" in result
        assert "已開立" in result
        assert "B2C" in result


class TestResponseTemplateTenantSummary:
    """Test response_template for tenant summary endpoint."""

    def test_tenant_summary_variables(self):
        template = (
            "租客摘要：\n"
            "合約數：{contracts_count}\n"
            "目前物件：{active_estate}\n"
            "未繳帳單：{unpaid_bills_count}"
        )
        values = {
            "contracts_count": "3",
            "active_estate": "信義區套房A",
            "unpaid_bills_count": "1",
        }
        result = template.format(**values)
        assert "3" in result
        assert "信義區套房A" in result
        assert "1" in result


class TestAPICallHandlerFormatResponse:
    """Test _format_response with response_template through the handler."""

    def test_format_response_with_template(self, handler):
        """response_template with {api_response} placeholder is applied."""
        api_config = {
            "response_template": "查詢結果：{api_response}",
        }
        api_result = {"message": "您的帳單已繳費完成"}
        result = handler._format_response(api_config, api_result, None)
        assert "查詢結果：" in result
        assert "您的帳單已繳費完成" in result

    def test_format_response_without_template(self, handler):
        """Without template, _format_api_data is used directly."""
        api_config = {}
        api_result = {"message": "帳單狀態正常"}
        result = handler._format_response(api_config, api_result, None)
        assert "帳單狀態正常" in result

    def test_format_response_combines_knowledge(self, handler):
        """When combine_with_knowledge=True, knowledge_answer is appended."""
        api_config = {"combine_with_knowledge": True}
        api_result = {"message": "帳單金額 25000"}
        knowledge = "小提醒：您可以設定自動扣款"
        result = handler._format_response(api_config, api_result, knowledge)
        assert "帳單金額 25000" in result
        assert "小提醒" in result


# ===========================================================================
# 3. Mock Data Format Validation Against API Spec
# ===========================================================================

ISO_8601_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$"
)
YYYYMMDD_PATTERN = re.compile(r"^\d{8}$")


def _is_iso8601_or_none(value):
    """Check that value is None or matches ISO 8601 datetime format."""
    if value is None:
        return True
    return bool(ISO_8601_PATTERN.match(str(value)))


def _is_yyyymmdd(value):
    """Check integer date format YYYYMMDD."""
    return isinstance(value, int) and bool(YYYYMMDD_PATTERN.match(str(value)))


class TestMockBillsSpecCompliance:
    """Verify mock bills data matches API spec field structure."""

    REQUIRED_FIELDS = {
        "id": int,
        "contract_id": int,
        "estate_id": int,
        "type": int,
        "category": int,
        "bit_status": int,
        "title": str,
        "currency": str,
        "total": (int, float),
        "final_total": (int, float),
        "rate": (int, float),
        "date_start": int,
        "date_end": int,
        "date_expire": int,
        "cycle": int,
        "days": int,
        "created_at": str,
        "updated_at": str,
    }

    @pytest.mark.asyncio
    async def test_bill_field_types(self, jgb_api):
        result = await jgb_api.get_bills(role_id=ROLE_ID, user_id=USER_ID)
        for bill in result["data"]:
            for field, expected_type in self.REQUIRED_FIELDS.items():
                assert field in bill, f"Bill missing field: {field}"
                assert isinstance(bill[field], expected_type), (
                    f"Bill[{field}] type mismatch: {type(bill[field])} != {expected_type}"
                )

    @pytest.mark.asyncio
    async def test_bill_date_formats(self, jgb_api):
        result = await jgb_api.get_bills(role_id=ROLE_ID, user_id=USER_ID)
        for bill in result["data"]:
            # Integer dates
            assert _is_yyyymmdd(bill["date_start"])
            assert _is_yyyymmdd(bill["date_end"])
            assert _is_yyyymmdd(bill["date_expire"])
            # ISO 8601 timestamps
            assert _is_iso8601_or_none(bill["created_at"])
            assert _is_iso8601_or_none(bill["updated_at"])
            assert _is_iso8601_or_none(bill.get("ready_at"))
            assert _is_iso8601_or_none(bill.get("pay_at"))
            assert _is_iso8601_or_none(bill.get("complete_at"))

    @pytest.mark.asyncio
    async def test_bill_currency_is_iso4217(self, jgb_api):
        result = await jgb_api.get_bills(role_id=ROLE_ID, user_id=USER_ID)
        for bill in result["data"]:
            assert len(bill["currency"]) == 3
            assert bill["currency"].isupper()

    @pytest.mark.asyncio
    async def test_bill_amounts_numeric(self, jgb_api):
        result = await jgb_api.get_bills(role_id=ROLE_ID, user_id=USER_ID)
        for bill in result["data"]:
            assert isinstance(bill["total"], (int, float))
            assert bill["total"] >= 0
            assert isinstance(bill["final_total"], (int, float))


class TestMockInvoicesSpecCompliance:
    """Verify mock invoices match API spec."""

    REQUIRED_FIELDS = [
        "id", "bill_id", "payment_id", "number", "status",
        "category", "tax_type", "tax_rate", "tax_amt",
        "amt", "total_amt", "item_data",
    ]

    @pytest.mark.asyncio
    async def test_invoice_required_fields(self, jgb_api):
        result = await jgb_api.get_invoices(role_id=ROLE_ID, user_id=USER_ID)
        for invoice in result["data"]:
            for field in self.REQUIRED_FIELDS:
                assert field in invoice, f"Invoice missing field: {field}"

    @pytest.mark.asyncio
    async def test_invoice_item_data_structure(self, jgb_api):
        result = await jgb_api.get_invoices(role_id=ROLE_ID, user_id=USER_ID)
        for invoice in result["data"]:
            assert isinstance(invoice["item_data"], list)
            for item in invoice["item_data"]:
                assert "item_name" in item
                assert "item_count" in item
                assert "item_price" in item
                assert "item_amount" in item

    @pytest.mark.asyncio
    async def test_invoice_category_valid(self, jgb_api):
        result = await jgb_api.get_invoices(role_id=ROLE_ID, user_id=USER_ID)
        valid_categories = {"B2B", "B2C"}
        for invoice in result["data"]:
            assert invoice["category"] in valid_categories

    @pytest.mark.asyncio
    async def test_invoice_tax_type_valid(self, jgb_api):
        result = await jgb_api.get_invoices(role_id=ROLE_ID, user_id=USER_ID)
        valid_tax_types = {1, 2, 3, 9}
        for invoice in result["data"]:
            assert invoice["tax_type"] in valid_tax_types


class TestMockContractsSpecCompliance:
    """Verify mock contracts match API spec."""

    REQUIRED_FIELDS = [
        "id", "bit_status", "estate_id", "title",
        "city", "district", "address", "room_number",
        "currency", "rent", "deposit_amount",
        "date_start", "date_end",
        "created_at", "updated_at",
    ]

    @pytest.mark.asyncio
    async def test_contract_required_fields(self, jgb_api):
        result = await jgb_api.get_contracts(role_id=ROLE_ID, user_id=USER_ID)
        for contract in result["data"]:
            for field in self.REQUIRED_FIELDS:
                assert field in contract, f"Contract missing field: {field}"

    @pytest.mark.asyncio
    async def test_contract_date_formats(self, jgb_api):
        result = await jgb_api.get_contracts(role_id=ROLE_ID, user_id=USER_ID)
        for contract in result["data"]:
            assert _is_yyyymmdd(contract["date_start"])
            assert _is_yyyymmdd(contract["date_end"])
            assert _is_iso8601_or_none(contract["created_at"])

    @pytest.mark.asyncio
    async def test_contract_rent_numeric(self, jgb_api):
        result = await jgb_api.get_contracts(role_id=ROLE_ID, user_id=USER_ID)
        for contract in result["data"]:
            assert isinstance(contract["rent"], (int, float))
            assert contract["rent"] > 0

    @pytest.mark.asyncio
    async def test_contract_fees_is_dict(self, jgb_api):
        result = await jgb_api.get_contracts(role_id=ROLE_ID, user_id=USER_ID)
        for contract in result["data"]:
            assert isinstance(contract["fees"], dict)


class TestMockCheckinEligibilitySpecCompliance:
    """Verify mock checkin eligibility matches API spec."""

    @pytest.mark.asyncio
    async def test_eligibility_data_structure(self, jgb_api):
        result = await jgb_api.get_contract_checkin_eligibility(
            role_id=ROLE_ID, user_id=USER_ID, contract_id=678
        )
        data = result["data"]
        assert isinstance(data["contract_id"], int)
        assert isinstance(data["eligible"], bool)
        assert isinstance(data["contract_status"], dict)
        assert isinstance(data["first_bill_status"], dict)
        assert isinstance(data["deposit_status"], dict)
        assert isinstance(data["checkin_blockers"], list)

    @pytest.mark.asyncio
    async def test_contract_status_sub_fields(self, jgb_api):
        result = await jgb_api.get_contract_checkin_eligibility(
            role_id=ROLE_ID, user_id=USER_ID, contract_id=678
        )
        cs = result["data"]["contract_status"]
        assert "bit_status" in cs
        assert "label" in cs
        assert "is_signed" in cs

    @pytest.mark.asyncio
    async def test_deposit_amounts_numeric(self, jgb_api):
        result = await jgb_api.get_contract_checkin_eligibility(
            role_id=ROLE_ID, user_id=USER_ID, contract_id=678
        )
        ds = result["data"]["deposit_status"]
        assert isinstance(ds["required_amount"], (int, float))
        assert isinstance(ds["paid_amount"], (int, float))
        assert isinstance(ds["is_fulfilled"], bool)


class TestMockPaymentsSpecCompliance:
    """Verify mock payments match API spec."""

    REQUIRED_FIELDS = [
        "id", "no", "transaction_id", "user_id", "role_id",
        "type", "status", "manufacturer", "payment",
        "currency", "price", "final_price",
        "created_at", "updated_at",
    ]

    @pytest.mark.asyncio
    async def test_payment_required_fields(self, jgb_api):
        result = await jgb_api.get_payments(role_id=ROLE_ID, user_id=USER_ID)
        for payment in result["data"]:
            for field in self.REQUIRED_FIELDS:
                assert field in payment, f"Payment missing field: {field}"

    @pytest.mark.asyncio
    async def test_payment_amounts_numeric(self, jgb_api):
        result = await jgb_api.get_payments(role_id=ROLE_ID, user_id=USER_ID)
        for payment in result["data"]:
            assert isinstance(payment["price"], (int, float))
            assert isinstance(payment["final_price"], (int, float))

    @pytest.mark.asyncio
    async def test_payment_status_valid(self, jgb_api):
        """Payment status must be one of the spec-defined values."""
        result = await jgb_api.get_payments(role_id=ROLE_ID, user_id=USER_ID)
        valid_statuses = {-3, -2, -1, 0, 1, 2, 99}
        for payment in result["data"]:
            assert payment["status"] in valid_statuses, (
                f"Invalid payment status: {payment['status']}"
            )

    @pytest.mark.asyncio
    async def test_payment_timestamps(self, jgb_api):
        result = await jgb_api.get_payments(role_id=ROLE_ID, user_id=USER_ID)
        for payment in result["data"]:
            assert _is_iso8601_or_none(payment["created_at"])
            assert _is_iso8601_or_none(payment.get("payment_completed_at"))


class TestMockRepairsSpecCompliance:
    """Verify mock repairs match API spec."""

    REQUIRED_FIELDS = [
        "id", "estate_id", "contract_id", "role_id",
        "status", "emergency_status",
        "estate_title", "category_id", "category_name",
        "item_id", "item_name",
        "created_at", "updated_at",
    ]

    @pytest.mark.asyncio
    async def test_repair_required_fields(self, jgb_api):
        result = await jgb_api.get_repairs(role_id=ROLE_ID, user_id=USER_ID)
        for repair in result["data"]:
            for field in self.REQUIRED_FIELDS:
                assert field in repair, f"Repair missing field: {field}"

    @pytest.mark.asyncio
    async def test_repair_status_valid(self, jgb_api):
        result = await jgb_api.get_repairs(role_id=ROLE_ID, user_id=USER_ID)
        valid_statuses = {1, 2, 4, 16, 32, 64}
        for repair in result["data"]:
            assert repair["status"] in valid_statuses, (
                f"Invalid repair status: {repair['status']}"
            )

    @pytest.mark.asyncio
    async def test_repair_emergency_status_valid(self, jgb_api):
        result = await jgb_api.get_repairs(role_id=ROLE_ID, user_id=USER_ID)
        valid_emergency = {1, 2}
        for repair in result["data"]:
            assert repair["emergency_status"] in valid_emergency

    @pytest.mark.asyncio
    async def test_repair_timestamps(self, jgb_api):
        result = await jgb_api.get_repairs(role_id=ROLE_ID, user_id=USER_ID)
        for repair in result["data"]:
            assert _is_iso8601_or_none(repair["created_at"])
            assert _is_iso8601_or_none(repair.get("apply_at"))
            assert _is_iso8601_or_none(repair.get("assign_at"))
            assert _is_iso8601_or_none(repair.get("complete_at"))
            assert _is_iso8601_or_none(repair.get("archive_at"))

    @pytest.mark.asyncio
    async def test_repair_photos_is_list(self, jgb_api):
        result = await jgb_api.get_repairs(role_id=ROLE_ID, user_id=USER_ID)
        for repair in result["data"]:
            assert isinstance(repair["broken_photos"], list)


class TestMockTenantSummarySpecCompliance:
    """Verify mock tenant summary matches API spec."""

    @pytest.mark.asyncio
    async def test_tenant_info_fields(self, jgb_api):
        result = await jgb_api.get_tenant_summary(role_id=ROLE_ID, user_id=USER_ID)
        ti = result["data"]["tenant_info"]
        required = [
            "id", "lessee_user_id", "lessee_role_id", "lessor_role_id",
            "lessee_name", "lessee_email", "lessee_registered_phone",
            "active",
        ]
        for field in required:
            assert field in ti, f"tenant_info missing: {field}"

    @pytest.mark.asyncio
    async def test_contract_summary_fields(self, jgb_api):
        result = await jgb_api.get_tenant_summary(role_id=ROLE_ID, user_id=USER_ID)
        cs = result["data"]["contract_summary"]
        assert isinstance(cs["registered_contract_count"], int)
        assert isinstance(cs["registered_contract_signed_count"], int)
        assert isinstance(cs["registered_contract_history_count"], int)

    @pytest.mark.asyncio
    async def test_bill_summary_fields(self, jgb_api):
        result = await jgb_api.get_tenant_summary(role_id=ROLE_ID, user_id=USER_ID)
        bs = result["data"]["bill_summary"]
        assert isinstance(bs["income_bill_count"], int)
        assert isinstance(bs["income_bill_ready_count"], int)
        assert isinstance(bs["income_bill_complete_count"], int)
        assert isinstance(bs["income_bill_paid_on_time_ratio"], int)

    @pytest.mark.asyncio
    async def test_repair_summary_fields(self, jgb_api):
        result = await jgb_api.get_tenant_summary(role_id=ROLE_ID, user_id=USER_ID)
        rs = result["data"]["repair_summary"]
        assert isinstance(rs["repair_count"], int)
        assert isinstance(rs["repair_finish_count"], int)


# ===========================================================================
# 4. Pagination Structure Validation
# ===========================================================================

class TestPaginationStructure:
    """Verify all list endpoints include correct pagination structure."""

    PAGINATION_FIELDS = ["current_page", "per_page", "total", "total_pages", "has_more"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method_name", [
        "get_bills", "get_invoices", "get_contracts",
        "get_payments", "get_repairs",
    ])
    async def test_pagination_present(self, jgb_api, method_name):
        method = getattr(jgb_api, method_name)
        result = await method(role_id=ROLE_ID, user_id=USER_ID)
        assert "pagination" in result, f"{method_name} missing pagination"
        for field in self.PAGINATION_FIELDS:
            assert field in result["pagination"], (
                f"{method_name} pagination missing: {field}"
            )

    @pytest.mark.asyncio
    async def test_pagination_types(self, jgb_api):
        result = await jgb_api.get_bills(role_id=ROLE_ID, user_id=USER_ID)
        pag = result["pagination"]
        assert isinstance(pag["current_page"], int)
        assert isinstance(pag["per_page"], int)
        assert isinstance(pag["total"], int)
        assert isinstance(pag["total_pages"], int)
        assert isinstance(pag["has_more"], bool)

    @pytest.mark.asyncio
    async def test_tenant_summary_has_no_pagination(self, jgb_api):
        """Tenant summary returns a single object, not a list — no pagination."""
        result = await jgb_api.get_tenant_summary(role_id=ROLE_ID, user_id=USER_ID)
        assert "pagination" not in result

    @pytest.mark.asyncio
    async def test_checkin_eligibility_has_no_pagination(self, jgb_api):
        """Checkin eligibility returns a single object — no pagination."""
        result = await jgb_api.get_contract_checkin_eligibility(
            role_id=ROLE_ID, user_id=USER_ID, contract_id=678
        )
        assert "pagination" not in result
