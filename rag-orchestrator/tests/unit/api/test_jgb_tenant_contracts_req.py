"""TDD：get_tenant_contracts mock 方法（spec conversational-repair 任務 1.3，R2.1/R2.2）。

驗證契約：
- 雙證（role_id + user_id）缺一 → 降級回應（success: False）
- role_id="R001", user_id="U001" → 1 筆（典型單租約租客）
- role_id="R002", user_id="U002" → N 筆（多租約）
- role_id="R003", user_id="U003" → 0 筆（無有效租約）
- 每筆資料含五欄位：contract_id / estate_id / estate_title / display_address / room
"""
import pytest
import asyncio

pytestmark = pytest.mark.unit


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def api():
    import os
    os.environ["USE_MOCK_JGB_API"] = "true"
    from services.jgb_system_api import JGBSystemAPI
    return JGBSystemAPI()


# ---------------------------------------------------------------------------
# 雙證缺一 → 降級
# ---------------------------------------------------------------------------

@pytest.mark.req("conversational-repair:2.1")
def test_missing_role_id_returns_degraded(api):
    result = _run(api.get_tenant_contracts(role_id=None, user_id="U001"))
    assert result["success"] is False


@pytest.mark.req("conversational-repair:2.1")
def test_missing_user_id_returns_degraded(api):
    result = _run(api.get_tenant_contracts(role_id="R001", user_id=None))
    assert result["success"] is False


@pytest.mark.req("conversational-repair:2.1")
def test_empty_role_id_returns_degraded(api):
    result = _run(api.get_tenant_contracts(role_id="", user_id="U001"))
    assert result["success"] is False


@pytest.mark.req("conversational-repair:2.1")
def test_empty_user_id_returns_degraded(api):
    result = _run(api.get_tenant_contracts(role_id="R001", user_id=""))
    assert result["success"] is False


# ---------------------------------------------------------------------------
# 1 筆形狀（典型租客）
# ---------------------------------------------------------------------------

@pytest.mark.req("conversational-repair:2.2")
def test_single_contract_shape(api):
    result = _run(api.get_tenant_contracts(role_id="R001", user_id="U001"))
    assert result["success"] is True
    assert isinstance(result["data"], list)
    assert len(result["data"]) == 1


@pytest.mark.req("conversational-repair:2.2")
def test_single_contract_has_all_fields(api):
    result = _run(api.get_tenant_contracts(role_id="R001", user_id="U001"))
    row = result["data"][0]
    assert "contract_id" in row
    assert "estate_id" in row
    assert "estate_title" in row
    assert "display_address" in row
    assert "room" in row


# ---------------------------------------------------------------------------
# N 筆形狀（多租約）
# ---------------------------------------------------------------------------

@pytest.mark.req("conversational-repair:2.2")
def test_multiple_contracts_shape(api):
    result = _run(api.get_tenant_contracts(role_id="R002", user_id="U002"))
    assert result["success"] is True
    assert isinstance(result["data"], list)
    assert len(result["data"]) >= 2


@pytest.mark.req("conversational-repair:2.2")
def test_multiple_contracts_all_have_required_fields(api):
    result = _run(api.get_tenant_contracts(role_id="R002", user_id="U002"))
    required = {"contract_id", "estate_id", "estate_title", "display_address", "room"}
    for row in result["data"]:
        assert required.issubset(row.keys()), f"缺少欄位：{required - row.keys()}"


# ---------------------------------------------------------------------------
# 0 筆形狀（無有效租約）
# ---------------------------------------------------------------------------

@pytest.mark.req("conversational-repair:2.2")
def test_zero_contracts_shape(api):
    result = _run(api.get_tenant_contracts(role_id="R003", user_id="U003"))
    assert result["success"] is True
    assert isinstance(result["data"], list)
    assert len(result["data"]) == 0
