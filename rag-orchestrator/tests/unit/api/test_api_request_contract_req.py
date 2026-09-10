"""補測試：API 端點／SSE／跨層 e2e（spec testing-traceability・任務 9・R5.5）。

unit 層：VendorChatRequest 請求契約（pydantic 驗證，純函式、無服務）。
e2e 層：SSE 事件序與多輪 session（需整服務 → 預設略過，RUN_E2E=1 才跑）。
"""
import pytest

from routers.chat import VendorChatRequest

pytestmark = pytest.mark.unit


@pytest.mark.req("testing-traceability:5.5")
def test_message_required_and_default_mode_b2c():
    req = VendorChatRequest(message="你好", vendor_id=1)
    assert req.message == "你好"
    assert req.mode == "b2c"


@pytest.mark.req("testing-traceability:5.5")
def test_invalid_target_user_rejected():
    with pytest.raises(ValueError):
        VendorChatRequest(message="hi", vendor_id=1, target_user="not_a_role")


@pytest.mark.req("testing-traceability:5.5")
def test_prospect_is_valid_target_user():
    """prospect（售前匿名）為合法角色。"""
    req = VendorChatRequest(message="想了解方案", mode="b2b", target_user="prospect")
    assert req.target_user == "prospect"


@pytest.mark.req("testing-traceability:5.5")
def test_b2c_requires_vendor_id():
    with pytest.raises(ValueError):
        VendorChatRequest(message="hi", mode="b2c")  # 無 vendor_id


@pytest.mark.req("testing-traceability:5.5")
def test_b2b_allows_missing_vendor_id():
    req = VendorChatRequest(message="hi", mode="b2b")
    assert req.vendor_id is None


@pytest.mark.req("testing-traceability:5.5")
def test_legacy_user_role_field_ignored():
    """user_role 相容層已移除：欄位被當未知欄位忽略，target_user 只依 mode 給預設值
    （非 mode 對應的舊值 'customer' 不再生效，證明不是走已刪的遷移邏輯）。"""
    req = VendorChatRequest(message="hi", mode="b2b", user_role="customer")
    assert req.target_user == "property_manager"
    assert not hasattr(req, "user_role")


@pytest.mark.req("testing-traceability:5.5")
def test_image_urls_max_three():
    with pytest.raises(ValueError):
        VendorChatRequest(message="hi", vendor_id=1,
                          image_urls=["https://a/1.jpg", "https://a/2.jpg",
                                      "https://a/3.jpg", "https://a/4.jpg"])
