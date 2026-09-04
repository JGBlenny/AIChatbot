"""unit：`Identity` 擴充＋`audience_of` 三判準（spec agentic-mcp-orchestration 任務 1.3｜R1.3, R2.2）。

`audience_of(mode, target_user, role_id)` 是決定性純函式，⛔ 不看 role_id
（僅 target_user=='prospect' 判 prospect）；⛔ 不看 user 自述。判準與兩處
既有程式同源：
- prospect ⇔ `routers/chat.py:CONVERSATIONAL_ENABLED_ROLES == {'prospect'}`
- property_manager ⇔ `vendor_knowledge_retriever_v2.build_visibility_predicate`
  的 `is_b2b_mode = target_user in ['property_manager','system_admin'] or mode=='b2b'`

同時鎖住 `Identity` 擴充的向後相容性：既有三欄（vendor_id/target_user/mode）
名稱、預設值、關鍵字建構方式不得因新增欄位而破——
`tests/unit/retrieval/test_visibility_predicate_req.py` 與
`services/vendor_knowledge_retriever_v2.py` 皆用這個既有建構式。
"""
import pytest

from services.agent.identity import Identity, audience_of

pytestmark = pytest.mark.unit


class TestAudienceOfThreeCriteria:
    """`audience_of` 三判準（prospect／property_manager／tenant）。"""

    def test_prospect_by_target_user_only(self):
        assert audience_of(mode="b2c", target_user="prospect", role_id=None) == "prospect"

    def test_prospect_with_role_id_still_prospect(self):
        """⛔ role_id 不影響 prospect 判定——即使帶了 role_id 仍是 prospect。"""
        assert (
            audience_of(mode="b2c", target_user="prospect", role_id="R123")
            == "prospect"
        )

    def test_system_admin_is_property_manager(self):
        assert (
            audience_of(mode="b2c", target_user="system_admin", role_id=None)
            == "property_manager"
        )

    def test_property_manager_target_user_is_property_manager(self):
        assert (
            audience_of(mode="b2c", target_user="property_manager", role_id=None)
            == "property_manager"
        )

    def test_mode_b2b_with_tenant_target_user_is_property_manager(self):
        """`mode=='b2b'` 與 `target_user` 兩條件 OR——即使 target_user=tenant，
        mode=b2b 仍判 property_manager（與 retriever `is_b2b_mode` 同式）。"""
        assert audience_of(mode="b2b", target_user="tenant", role_id=None) == "property_manager"

    def test_target_user_none_is_tenant(self):
        assert audience_of(mode="b2c", target_user=None, role_id=None) == "tenant"

    def test_target_user_landlord_is_tenant(self):
        """既非 prospect 也非 pm/system_admin/b2b ⇒ 落 tenant（其餘一律 tenant）。"""
        assert audience_of(mode="b2c", target_user="landlord", role_id=None) == "tenant"

    def test_role_id_alone_never_changes_non_prospect_outcome(self):
        """role_id 對 property_manager／tenant 判定同樣不參與。"""
        with_role = audience_of(mode="b2c", target_user="tenant", role_id="R1")
        without_role = audience_of(mode="b2c", target_user="tenant", role_id=None)
        assert with_role == without_role == "tenant"

    def test_deterministic_pure_function(self):
        """同輸入必同輸出（決定性、純函式，可重複呼叫多次）。"""
        args = ("b2b", "tenant", None)
        results = {audience_of(*args) for _ in range(5)}
        assert results == {"property_manager"}


class TestIdentityBackwardCompatibility:
    """既有三欄的向後相容性——1.3 擴充不得破壞 1.1 的建構方式。"""

    def test_existing_three_field_positional_construction_still_works(self):
        identity = Identity(1, "tenant", "b2c")
        assert identity.vendor_id == 1
        assert identity.target_user == "tenant"
        assert identity.mode == "b2c"

    def test_existing_three_field_keyword_construction_still_works(self):
        identity = Identity(vendor_id=7, target_user="property_manager", mode="b2b")
        assert identity.vendor_id == 7
        assert identity.target_user == "property_manager"
        assert identity.mode == "b2b"

    def test_target_user_default_is_tenant(self):
        assert Identity(vendor_id=None).target_user == "tenant"

    def test_mode_default_is_b2c(self):
        assert Identity(vendor_id=None).mode == "b2c"

    def test_vendor_id_may_be_none(self):
        """既有測試（visibility predicate 池外案例）以 `vendor_id=99999`／`None`
        建構，新增欄位不得要求 vendor_id 一定非 None。"""
        identity = Identity(vendor_id=None)
        assert identity.vendor_id is None

    def test_is_frozen_dataclass(self):
        identity = Identity(vendor_id=1)
        with pytest.raises(Exception):
            identity.vendor_id = 2  # type: ignore[misc]


class TestIdentityNewFieldsHaveDefaults:
    """1.3 新增欄位一律有預設值——不傳也能建構。"""

    def test_new_fields_default_values(self):
        identity = Identity(vendor_id=1)
        assert identity.role_id is None
        assert identity.user_id is None
        assert identity.session_id == ""
        assert identity.api_key_id is None
        assert identity.audience is None

    def test_new_fields_can_be_set(self):
        identity = Identity(
            vendor_id=1,
            role_id="R1",
            user_id="U1",
            session_id="sess-1",
            api_key_id=42,
        )
        assert identity.role_id == "R1"
        assert identity.user_id == "U1"
        assert identity.session_id == "sess-1"
        assert identity.api_key_id == 42


class TestResolvedAudience:
    """`resolved_audience()`：有預算好的 `audience` 就直接用，否則即時推導。"""

    def test_uses_explicit_audience_when_set(self):
        identity = Identity(vendor_id=1, target_user="tenant", audience="prospect")
        assert identity.resolved_audience() == "prospect"

    def test_derives_from_audience_of_when_none(self):
        identity = Identity(vendor_id=1, target_user="prospect", mode="b2c")
        assert identity.audience is None
        assert identity.resolved_audience() == "prospect"

    def test_derives_property_manager_case(self):
        identity = Identity(vendor_id=1, target_user="tenant", mode="b2b")
        assert identity.resolved_audience() == "property_manager"
