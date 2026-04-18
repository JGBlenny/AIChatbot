"""
Tests for JGBSystemAPI service (mock mode).

Verifies:
- All 7 endpoints return correct response format in mock mode
- role_id/user_id validation returns degraded response when empty
- Response structure matches JGB External API spec
- Error/timeout handling returns fallback structure
"""

import os
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock

# Ensure mock mode is active for tests
os.environ["USE_MOCK_JGB_API"] = "true"


@pytest.fixture
def api():
    """Create a JGBSystemAPI instance in mock mode."""
    from services.jgb_system_api import JGBSystemAPI
    return JGBSystemAPI()


class TestJGBSystemAPIInit:
    """Test initialization and configuration."""

    def test_mock_mode_enabled_by_default(self, api):
        assert api.use_mock is True

    def test_env_vars_read(self):
        with patch.dict(os.environ, {
            "JGB_API_BASE_URL": "https://test.example.com",
            "JGB_API_KEY": "test-key-123",
            "USE_MOCK_JGB_API": "false",
        }):
            from services.jgb_system_api import JGBSystemAPI
            svc = JGBSystemAPI()
            assert svc.api_base_url == "https://test.example.com"
            assert svc.api_key == "test-key-123"
            assert svc.use_mock is False


class TestRoleIdUserIdValidation:
    """Test that empty role_id or user_id returns degraded response."""

    @pytest.mark.asyncio
    async def test_empty_role_id_returns_degraded(self, api):
        result = await api.get_bills(role_id="", user_id="100")
        assert result["success"] is False
        assert "error" in result
        assert "message" in result

    @pytest.mark.asyncio
    async def test_none_role_id_returns_degraded(self, api):
        result = await api.get_bills(role_id=None, user_id="100")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_empty_user_id_returns_degraded(self, api):
        result = await api.get_invoices(role_id="200", user_id="")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_none_user_id_returns_degraded(self, api):
        result = await api.get_contracts(role_id="200", user_id=None)
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_both_empty_returns_degraded(self, api):
        result = await api.get_payments(role_id="", user_id="")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_degraded_response_for_all_endpoints(self, api):
        """Every endpoint should degrade when role_id/user_id missing."""
        endpoints = [
            api.get_bills("", "100"),
            api.get_invoices("200", ""),
            api.get_contracts(None, "100"),
            api.get_contract_checkin_eligibility("", "100", contract_id=1),
            api.get_payments("200", None),
            api.get_repairs("", ""),
            api.get_tenant_summary(None, None),
        ]
        for coro in endpoints:
            result = await coro
            assert result["success"] is False, f"Expected degraded response, got: {result}"
            assert "message" in result


class TestGetBillsMock:
    """Test get_bills in mock mode."""

    @pytest.mark.asyncio
    async def test_returns_success_structure(self, api):
        result = await api.get_bills(role_id="200", user_id="100")
        assert result["success"] is True
        assert "data" in result
        assert isinstance(result["data"], list)

    @pytest.mark.asyncio
    async def test_bill_record_has_required_fields(self, api):
        result = await api.get_bills(role_id="200", user_id="100")
        bill = result["data"][0]
        required_fields = [
            "id", "contract_id", "type", "bit_status", "title",
            "currency", "total", "final_total",
            "date_start", "date_end", "created_at",
        ]
        for field in required_fields:
            assert field in bill, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_pagination_present(self, api):
        result = await api.get_bills(role_id="200", user_id="100")
        assert "pagination" in result
        pag = result["pagination"]
        assert "current_page" in pag
        assert "per_page" in pag
        assert "total" in pag
        assert "total_pages" in pag
        assert "has_more" in pag


class TestGetInvoicesMock:
    """Test get_invoices in mock mode."""

    @pytest.mark.asyncio
    async def test_returns_success_structure(self, api):
        result = await api.get_invoices(role_id="200", user_id="100")
        assert result["success"] is True
        assert "data" in result
        assert isinstance(result["data"], list)

    @pytest.mark.asyncio
    async def test_invoice_record_has_required_fields(self, api):
        result = await api.get_invoices(role_id="200", user_id="100")
        invoice = result["data"][0]
        required_fields = [
            "id", "bill_id", "number", "status", "category",
            "tax_type", "total_amt",
        ]
        for field in required_fields:
            assert field in invoice, f"Missing field: {field}"


class TestGetContractsMock:
    """Test get_contracts in mock mode."""

    @pytest.mark.asyncio
    async def test_returns_success_structure(self, api):
        result = await api.get_contracts(role_id="200", user_id="100")
        assert result["success"] is True
        assert isinstance(result["data"], list)

    @pytest.mark.asyncio
    async def test_contract_record_has_required_fields(self, api):
        result = await api.get_contracts(role_id="200", user_id="100")
        contract = result["data"][0]
        required_fields = [
            "id", "bit_status", "estate_id", "title",
            "rent", "date_start", "date_end", "currency",
        ]
        for field in required_fields:
            assert field in contract, f"Missing field: {field}"


class TestGetContractCheckinEligibilityMock:
    """Test get_contract_checkin_eligibility in mock mode."""

    @pytest.mark.asyncio
    async def test_returns_success_structure(self, api):
        result = await api.get_contract_checkin_eligibility(
            role_id="200", user_id="100", contract_id=678
        )
        assert result["success"] is True
        assert "data" in result

    @pytest.mark.asyncio
    async def test_eligibility_data_fields(self, api):
        result = await api.get_contract_checkin_eligibility(
            role_id="200", user_id="100", contract_id=678
        )
        data = result["data"]
        assert "contract_id" in data
        assert "eligible" in data
        assert "contract_status" in data
        assert "first_bill_status" in data
        assert "deposit_status" in data
        assert "checkin_blockers" in data


class TestGetPaymentsMock:
    """Test get_payments in mock mode."""

    @pytest.mark.asyncio
    async def test_returns_success_structure(self, api):
        result = await api.get_payments(role_id="200", user_id="100")
        assert result["success"] is True
        assert isinstance(result["data"], list)

    @pytest.mark.asyncio
    async def test_payment_record_has_required_fields(self, api):
        result = await api.get_payments(role_id="200", user_id="100")
        payment = result["data"][0]
        required_fields = [
            "id", "no", "status", "manufacturer", "payment",
            "currency", "price", "final_price",
        ]
        for field in required_fields:
            assert field in payment, f"Missing field: {field}"


class TestGetRepairsMock:
    """Test get_repairs in mock mode."""

    @pytest.mark.asyncio
    async def test_returns_success_structure(self, api):
        result = await api.get_repairs(role_id="200", user_id="100")
        assert result["success"] is True
        assert isinstance(result["data"], list)

    @pytest.mark.asyncio
    async def test_repair_record_has_required_fields(self, api):
        result = await api.get_repairs(role_id="200", user_id="100")
        repair = result["data"][0]
        required_fields = [
            "id", "estate_id", "contract_id", "status",
            "emergency_status", "category_name", "item_name",
        ]
        for field in required_fields:
            assert field in repair, f"Missing field: {field}"


class TestGetTenantSummaryMock:
    """Test get_tenant_summary in mock mode."""

    @pytest.mark.asyncio
    async def test_returns_success_structure(self, api):
        result = await api.get_tenant_summary(role_id="200", user_id="100")
        assert result["success"] is True
        assert "data" in result

    @pytest.mark.asyncio
    async def test_summary_has_required_sections(self, api):
        result = await api.get_tenant_summary(role_id="200", user_id="100")
        data = result["data"]
        assert "tenant_info" in data
        assert "contract_summary" in data
        assert "bill_summary" in data
        assert "repair_summary" in data


class TestErrorHandling:
    """Test API error and timeout handling (real mode)."""

    @pytest.mark.asyncio
    async def test_http_error_returns_fallback(self):
        """When real API returns error, should return fallback structure."""
        with patch.dict(os.environ, {"USE_MOCK_JGB_API": "false"}):
            from services.jgb_system_api import JGBSystemAPI
            svc = JGBSystemAPI()

        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await svc.get_bills(role_id="200", user_id="100")
            assert result["success"] is False
            assert "error" in result
            assert "message" in result

    @pytest.mark.asyncio
    async def test_timeout_returns_fallback(self):
        """When real API times out, should return fallback structure."""
        with patch.dict(os.environ, {"USE_MOCK_JGB_API": "false"}):
            from services.jgb_system_api import JGBSystemAPI
            svc = JGBSystemAPI()

        import httpx
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(
                side_effect=httpx.TimeoutException("Connection timed out")
            )
            mock_client_cls.return_value = mock_client

            result = await svc.get_bills(role_id="200", user_id="100")
            assert result["success"] is False
            assert "message" in result


class TestMockDataVariety:
    """Test that mock data includes various status combinations."""

    @pytest.mark.asyncio
    async def test_bills_have_different_statuses(self, api):
        result = await api.get_bills(role_id="200", user_id="100")
        statuses = {bill["bit_status"] for bill in result["data"]}
        # Should have at least 2 different statuses
        assert len(statuses) >= 2, f"Expected variety in statuses, got: {statuses}"

    @pytest.mark.asyncio
    async def test_repairs_have_different_statuses(self, api):
        result = await api.get_repairs(role_id="200", user_id="100")
        statuses = {r["status"] for r in result["data"]}
        assert len(statuses) >= 2, f"Expected variety in statuses, got: {statuses}"
