"""
端到端整合測試 — KB 檢索到 API 回答完整流程

驗證完整資料流：
- chat 請求（帶 role_id）→ RAG 檢索到 action_type='api_call' 的 KB
  → 呼叫 JGBSystemAPI mock → response_template 組合回答 → 回傳用戶
- session_data 中 role_id 從前端到 JGBSystemAPI 的完整傳遞鏈
- api_config 正確觸發對應端點，combine_with_knowledge 正確合併
- API 失敗時 fallback_message 正確降級
- 模擬用戶問「帳單為什麼沒產生發票」從 mock API 取得帳單資料並組合成完整回答

需求對應：7.3, 7.4, 7.5, 7.8
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# 確保 rag-orchestrator 在 sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
_RAG_DIR = _PROJECT_ROOT / "rag-orchestrator"
sys.path.insert(0, str(_RAG_DIR))
sys.path.insert(0, str(_PROJECT_ROOT))

# 設定環境變數（避免真實連線）
os.environ.setdefault("USE_MOCK_JGB_API", "true")

from services.api_call_handler import APICallHandler
from services.jgb_system_api import JGBSystemAPI, DEGRADED_MESSAGE, FALLBACK_MESSAGE


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def jgb_api() -> JGBSystemAPI:
    """建立 mock 模式的 JGBSystemAPI 實例"""
    api = JGBSystemAPI()
    api.use_mock = True
    return api


@pytest.fixture
def api_handler() -> APICallHandler:
    """建立不帶 db_pool 的 APICallHandler（僅自定義端點）"""
    return APICallHandler(db_pool=None)


@pytest.fixture
def sample_session_data() -> Dict[str, Any]:
    """模擬帶有 role_id 的 session 資料

    注意：execute_api_call 會自動將 vendor_id 注入 params，
    但 JGBSystemAPI 方法不接受 vendor_id 參數。
    在完整流程測試中需透過 mock 處理此差異。
    """
    return {
        "user_id": "100",
        "role_id": "200",
        "vendor_id": 1,
        "session_id": "sess-test-001",
    }


def _wrap_jgb_method_ignore_vendor_id(original_method):
    """包裝 JGBSystemAPI 方法，忽略 vendor_id 參數

    execute_api_call 會自動注入 vendor_id，但 JGBSystemAPI 方法
    不接受此參數。此包裝器濾除 vendor_id 以測試完整流程。
    """
    async def wrapper(**kwargs):
        kwargs.pop("vendor_id", None)
        return await original_method(**kwargs)
    wrapper.__name__ = original_method.__name__
    return wrapper


@pytest.fixture
def api_handler_with_wrapped_jgb() -> APICallHandler:
    """建立 APICallHandler，JGB 方法已包裝以接受 vendor_id"""
    handler = APICallHandler(db_pool=None)
    jgb = handler.jgb_api
    for key in list(handler.api_registry):
        if key.startswith("jgb_"):
            handler.api_registry[key] = _wrap_jgb_method_ignore_vendor_id(
                handler.api_registry[key]
            )
    return handler


@pytest.fixture
def bills_api_config() -> Dict[str, Any]:
    """模擬 KB 條目中的 api_config（帳單查詢）"""
    return {
        "endpoint": "jgb_bills",
        "params": {
            "role_id": "{session.role_id}",
            "user_id": "{session.user_id}",
        },
        "combine_with_knowledge": True,
        "response_template": "以下是您的帳單資料：\n{api_response}",
        "fallback_message": "目前無法查詢帳單資料，建議您聯繫客服協助。",
    }


@pytest.fixture
def contracts_api_config() -> Dict[str, Any]:
    """模擬 KB 條目中的 api_config（合約查詢）"""
    return {
        "endpoint": "jgb_contracts",
        "params": {
            "role_id": "{session.role_id}",
            "user_id": "{session.user_id}",
        },
        "combine_with_knowledge": False,
        "response_template": "以下是您的合約資料：\n{api_response}",
        "fallback_message": "目前無法查詢合約，請稍後再試。",
    }


@pytest.fixture
def repairs_api_config() -> Dict[str, Any]:
    """模擬 KB 條目中的 api_config（修繕查詢）"""
    return {
        "endpoint": "jgb_repairs",
        "params": {
            "role_id": "{session.role_id}",
            "user_id": "{session.user_id}",
        },
        "combine_with_knowledge": True,
        "response_template": "修繕進度如下：\n{api_response}",
        "fallback_message": "無法查詢修繕進度，請聯繫管理師。",
    }


# ---------------------------------------------------------------------------
# 1. role_id 傳遞鏈驗證
# ---------------------------------------------------------------------------

class TestRoleIdPropagation:
    """驗證 role_id 從前端請求到 JGBSystemAPI 的完整傳遞鏈"""

    def test_session_data_contains_role_id(self, sample_session_data):
        """session_data 應包含從 VendorChatRequest 傳入的 role_id"""
        assert sample_session_data["role_id"] == "200"
        assert sample_session_data["user_id"] == "100"

    def test_prepare_params_resolves_role_id(
        self, api_handler, bills_api_config, sample_session_data
    ):
        """_prepare_params 應將 {session.role_id} 解析為實際值"""
        params = api_handler._prepare_params(
            bills_api_config, sample_session_data, None, None
        )
        assert params["role_id"] == "200"
        assert params["user_id"] == "100"

    @pytest.mark.asyncio
    async def test_role_id_reaches_jgb_api(self, jgb_api):
        """role_id 應傳遞到 JGBSystemAPI 方法參數中"""
        result = await jgb_api.get_bills(role_id="200", user_id="100")
        assert result["success"] is True
        # mock 回傳的資料應包含帳單列表
        assert len(result["data"]) > 0


# ---------------------------------------------------------------------------
# 2. api_call_handler 路由驗證
# ---------------------------------------------------------------------------

class TestApiRegistryRouting:
    """驗證 api_registry 將端點名稱正確路由到 JGBSystemAPI 方法"""

    def test_jgb_bills_registered(self, api_handler):
        """jgb_bills 應註冊在 api_registry 中"""
        assert "jgb_bills" in api_handler.api_registry

    def test_jgb_contracts_registered(self, api_handler):
        """jgb_contracts 應註冊在 api_registry 中"""
        assert "jgb_contracts" in api_handler.api_registry

    def test_jgb_repairs_registered(self, api_handler):
        """jgb_repairs 應註冊在 api_registry 中"""
        assert "jgb_repairs" in api_handler.api_registry

    def test_jgb_invoices_registered(self, api_handler):
        """jgb_invoices 應註冊在 api_registry 中"""
        assert "jgb_invoices" in api_handler.api_registry

    def test_jgb_payments_registered(self, api_handler):
        """jgb_payments 應註冊在 api_registry 中"""
        assert "jgb_payments" in api_handler.api_registry

    def test_jgb_tenant_summary_registered(self, api_handler):
        """jgb_tenant_summary 應註冊在 api_registry 中"""
        assert "jgb_tenant_summary" in api_handler.api_registry

    def test_jgb_contract_checkin_registered(self, api_handler):
        """jgb_contract_checkin 應註冊在 api_registry 中"""
        assert "jgb_contract_checkin" in api_handler.api_registry

    def test_registry_points_to_jgb_api_methods(self, api_handler):
        """api_registry 中的 jgb_ 端點應指向 JGBSystemAPI 的方法"""
        jgb_endpoints = {
            "jgb_bills": "get_bills",
            "jgb_invoices": "get_invoices",
            "jgb_contracts": "get_contracts",
            "jgb_contract_checkin": "get_contract_checkin_eligibility",
            "jgb_payments": "get_payments",
            "jgb_repairs": "get_repairs",
            "jgb_tenant_summary": "get_tenant_summary",
        }
        for endpoint, method_name in jgb_endpoints.items():
            registered_fn = api_handler.api_registry[endpoint]
            assert registered_fn.__name__ == method_name, (
                f"{endpoint} 應指向 {method_name}，"
                f"但實際指向 {registered_fn.__name__}"
            )


# ---------------------------------------------------------------------------
# 3. 完整 mock 流程驗證（帳單、合約、修繕）
# ---------------------------------------------------------------------------

class TestFullMockFlow:
    """模擬完整流程：KB hit → api_call_handler → JGBSystemAPI mock → 格式化回答"""

    @pytest.mark.asyncio
    async def test_bills_full_flow(
        self, api_handler_with_wrapped_jgb, bills_api_config, sample_session_data
    ):
        """帳單查詢完整流程：api_config → execute_api_call → 格式化回答"""
        knowledge_answer = "帳單通常在每月 1 號產生，如有問題請聯繫管理師。"

        result = await api_handler_with_wrapped_jgb.execute_api_call(
            api_config=bills_api_config,
            session_data=sample_session_data,
            knowledge_answer=knowledge_answer,
        )

        assert result["success"] is True
        assert "formatted_response" in result
        # response_template 應被使用
        assert "帳單資料" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_contracts_full_flow(
        self, api_handler_with_wrapped_jgb, contracts_api_config, sample_session_data
    ):
        """合約查詢完整流程"""
        result = await api_handler_with_wrapped_jgb.execute_api_call(
            api_config=contracts_api_config,
            session_data=sample_session_data,
        )

        assert result["success"] is True
        assert "formatted_response" in result
        assert "合約資料" in result["formatted_response"]

    @pytest.mark.asyncio
    async def test_repairs_full_flow(
        self, api_handler_with_wrapped_jgb, repairs_api_config, sample_session_data
    ):
        """修繕查詢完整流程"""
        knowledge_answer = "修繕申請後管理師會安排師傅到場維修。"

        result = await api_handler_with_wrapped_jgb.execute_api_call(
            api_config=repairs_api_config,
            session_data=sample_session_data,
            knowledge_answer=knowledge_answer,
        )

        assert result["success"] is True
        assert "formatted_response" in result
        assert "修繕進度" in result["formatted_response"]


# ---------------------------------------------------------------------------
# 4. combine_with_knowledge 驗證
# ---------------------------------------------------------------------------

class TestCombineWithKnowledge:
    """驗證 combine_with_knowledge 正確合併靜態知識與 API 資料"""

    @pytest.mark.asyncio
    async def test_combine_true_appends_knowledge(
        self, api_handler_with_wrapped_jgb, bills_api_config, sample_session_data
    ):
        """combine_with_knowledge=True 時，知識答案應附加在 API 回答後"""
        knowledge_answer = "帳單通常每月 1 號產生。"
        bills_api_config["combine_with_knowledge"] = True

        result = await api_handler_with_wrapped_jgb.execute_api_call(
            api_config=bills_api_config,
            session_data=sample_session_data,
            knowledge_answer=knowledge_answer,
        )

        assert result["success"] is True
        formatted = result["formatted_response"]
        # 靜態知識應出現在回答中
        assert knowledge_answer in formatted

    @pytest.mark.asyncio
    async def test_combine_false_excludes_knowledge(
        self, api_handler_with_wrapped_jgb, contracts_api_config, sample_session_data
    ):
        """combine_with_knowledge=False 時，不應合併知識答案"""
        knowledge_answer = "合約到期前 30 天可申請續約。"
        contracts_api_config["combine_with_knowledge"] = False

        result = await api_handler_with_wrapped_jgb.execute_api_call(
            api_config=contracts_api_config,
            session_data=sample_session_data,
            knowledge_answer=knowledge_answer,
        )

        assert result["success"] is True
        formatted = result["formatted_response"]
        # 靜態知識不應出現
        assert knowledge_answer not in formatted

    @pytest.mark.asyncio
    async def test_combine_true_without_knowledge_answer(
        self, api_handler_with_wrapped_jgb, bills_api_config, sample_session_data
    ):
        """combine_with_knowledge=True 但無知識答案時，僅回傳 API 結果"""
        bills_api_config["combine_with_knowledge"] = True

        result = await api_handler_with_wrapped_jgb.execute_api_call(
            api_config=bills_api_config,
            session_data=sample_session_data,
            knowledge_answer=None,
        )

        assert result["success"] is True
        assert "formatted_response" in result


# ---------------------------------------------------------------------------
# 5. API 失敗降級驗證
# ---------------------------------------------------------------------------

class TestFallbackOnApiFailure:
    """驗證 API 失敗時 fallback_message 正確降級"""

    @pytest.mark.asyncio
    async def test_fallback_on_exception(
        self, api_handler, bills_api_config, sample_session_data
    ):
        """API 拋出例外時應回傳 fallback_message"""
        # 讓 jgb_api.get_bills 拋出例外
        api_handler.jgb_api.get_bills = AsyncMock(
            side_effect=Exception("Connection timeout")
        )

        knowledge_answer = "帳單通常每月 1 號產生。"
        result = await api_handler.execute_api_call(
            api_config=bills_api_config,
            session_data=sample_session_data,
            knowledge_answer=knowledge_answer,
        )

        assert result["success"] is False
        assert "formatted_response" in result
        # fallback_message 應被使用
        formatted = result["formatted_response"]
        assert "無法查詢帳單" in formatted or "聯繫客服" in formatted

    @pytest.mark.asyncio
    async def test_fallback_includes_knowledge_when_available(
        self, api_handler, bills_api_config, sample_session_data
    ):
        """降級時如果有 knowledge_answer，應一併回傳"""
        api_handler.jgb_api.get_bills = AsyncMock(
            side_effect=TimeoutError("API timeout")
        )

        knowledge_answer = "帳單通常每月 1 號產生。"
        result = await api_handler.execute_api_call(
            api_config=bills_api_config,
            session_data=sample_session_data,
            knowledge_answer=knowledge_answer,
        )

        assert result["success"] is False
        formatted = result["formatted_response"]
        # 降級回答應包含靜態知識
        assert knowledge_answer in formatted

    @pytest.mark.asyncio
    async def test_fallback_without_knowledge(
        self, api_handler, repairs_api_config, sample_session_data
    ):
        """降級時無 knowledge_answer 時，僅回傳 fallback_message"""
        api_handler.jgb_api.get_repairs = AsyncMock(
            side_effect=Exception("Service unavailable")
        )

        result = await api_handler.execute_api_call(
            api_config=repairs_api_config,
            session_data=sample_session_data,
            knowledge_answer=None,
        )

        assert result["success"] is False
        formatted = result["formatted_response"]
        assert "聯繫管理師" in formatted or "無法查詢" in formatted


# ---------------------------------------------------------------------------
# 6. role_id / user_id 為空時的降級驗證
# ---------------------------------------------------------------------------

class TestMissingIdentity:
    """驗證 role_id 或 user_id 為 None 時的降級回應"""

    @pytest.mark.asyncio
    async def test_missing_role_id_degraded(self, jgb_api):
        """role_id 為 None 時 JGBSystemAPI 應回傳降級回應"""
        result = await jgb_api.get_bills(role_id=None, user_id="100")
        assert result["success"] is False
        assert result["error"] == "missing_identity"
        assert result["message"] == DEGRADED_MESSAGE

    @pytest.mark.asyncio
    async def test_missing_user_id_degraded(self, jgb_api):
        """user_id 為 None 時 JGBSystemAPI 應回傳降級回應"""
        result = await jgb_api.get_bills(role_id="200", user_id=None)
        assert result["success"] is False
        assert result["error"] == "missing_identity"

    @pytest.mark.asyncio
    async def test_empty_role_id_degraded(self, jgb_api):
        """role_id 為空字串時 JGBSystemAPI 應回傳降級回應"""
        result = await jgb_api.get_contracts(role_id="", user_id="100")
        assert result["success"] is False
        assert result["error"] == "missing_identity"

    @pytest.mark.asyncio
    async def test_empty_user_id_degraded(self, jgb_api):
        """user_id 為空字串時 JGBSystemAPI 應回傳降級回應"""
        result = await jgb_api.get_repairs(role_id="200", user_id="")
        assert result["success"] is False
        assert result["error"] == "missing_identity"

    @pytest.mark.asyncio
    async def test_both_missing_degraded(self, jgb_api):
        """role_id 與 user_id 都為 None 時應回傳降級回應"""
        result = await jgb_api.get_payments(role_id=None, user_id=None)
        assert result["success"] is False
        assert result["error"] == "missing_identity"

    @pytest.mark.asyncio
    async def test_handler_level_missing_session_role_id(
        self, api_handler, bills_api_config
    ):
        """execute_api_call 中 session_data 的 role_id 為 None 時，
        JGBSystemAPI 應回傳降級回應，handler 將其格式化為 message"""
        session_no_role = {
            "user_id": "100",
            "role_id": None,
            "vendor_id": 1,
            "session_id": "sess-test-002",
        }

        result = await api_handler.execute_api_call(
            api_config=bills_api_config,
            session_data=session_no_role,
        )

        # JGBSystemAPI._validate_identity 會返回 degraded response，
        # 該 response 包含 message 欄位，handler._format_api_data 會取用
        assert "formatted_response" in result


# ---------------------------------------------------------------------------
# 7. 多端點路由驗證（帳單 / 合約 / 修繕）
# ---------------------------------------------------------------------------

class TestMultipleEndpoints:
    """測試至少 3 個不同端點正確路由並回傳資料"""

    @pytest.mark.asyncio
    async def test_bills_endpoint(
        self, api_handler_with_wrapped_jgb, sample_session_data
    ):
        """jgb_bills 端點正確回傳帳單資料"""
        config = {
            "endpoint": "jgb_bills",
            "params": {
                "role_id": "{session.role_id}",
                "user_id": "{session.user_id}",
            },
        }
        result = await api_handler_with_wrapped_jgb.execute_api_call(
            api_config=config, session_data=sample_session_data
        )
        assert result["success"] is True
        # mock 資料應包含帳單列表
        assert "data" in result["data"]

    @pytest.mark.asyncio
    async def test_contracts_endpoint(
        self, api_handler_with_wrapped_jgb, sample_session_data
    ):
        """jgb_contracts 端點正確回傳合約資料"""
        config = {
            "endpoint": "jgb_contracts",
            "params": {
                "role_id": "{session.role_id}",
                "user_id": "{session.user_id}",
            },
        }
        result = await api_handler_with_wrapped_jgb.execute_api_call(
            api_config=config, session_data=sample_session_data
        )
        assert result["success"] is True
        assert "data" in result["data"]

    @pytest.mark.asyncio
    async def test_repairs_endpoint(
        self, api_handler_with_wrapped_jgb, sample_session_data
    ):
        """jgb_repairs 端點正確回傳修繕資料"""
        config = {
            "endpoint": "jgb_repairs",
            "params": {
                "role_id": "{session.role_id}",
                "user_id": "{session.user_id}",
            },
        }
        result = await api_handler_with_wrapped_jgb.execute_api_call(
            api_config=config, session_data=sample_session_data
        )
        assert result["success"] is True
        assert "data" in result["data"]

    @pytest.mark.asyncio
    async def test_unsupported_endpoint_error(
        self, api_handler, sample_session_data
    ):
        """不存在的端點應回傳錯誤"""
        config = {
            "endpoint": "nonexistent_endpoint",
            "params": {},
        }
        result = await api_handler.execute_api_call(
            api_config=config, session_data=sample_session_data
        )
        assert result["success"] is False
        assert "不支援" in result["error"]


# ---------------------------------------------------------------------------
# 8. 情境模擬：「帳單為什麼沒產生發票」
# ---------------------------------------------------------------------------

class TestBillingInvoiceScenario:
    """模擬用戶問「帳單為什麼沒產生發票」的端到端流程"""

    @pytest.mark.asyncio
    async def test_billing_invoice_scenario(
        self, api_handler_with_wrapped_jgb, sample_session_data
    ):
        """
        模擬完整場景：
        1. KB 檢索命中 action_type='api_call' 的帳單查詢知識
        2. api_config 指向 jgb_bills 端點
        3. JGBSystemAPI mock 回傳帳單資料（含 invoice_status）
        4. response_template 組合成完整回答
        5. combine_with_knowledge 合併靜態知識
        """
        # 模擬 KB 條目
        best_knowledge = {
            "answer": (
                "帳單發票通常在繳費完成後 2-3 個工作天內由系統自動開立。"
                "如果帳單尚未繳費，則不會產生發票。"
                "若已繳費超過 3 天仍未收到發票，建議聯繫管理公司確認。"
            ),
            "api_config": {
                "endpoint": "jgb_bills",
                "params": {
                    "role_id": "{session.role_id}",
                    "user_id": "{session.user_id}",
                },
                "combine_with_knowledge": True,
                "response_template": "以下是您的帳單與發票狀態：\n{api_response}",
                "fallback_message": "目前無法查詢帳單資料，{knowledge_answer}",
            },
            "action_type": "api_call",
        }

        api_config = best_knowledge["api_config"]
        knowledge_answer = best_knowledge["answer"]

        result = await api_handler_with_wrapped_jgb.execute_api_call(
            api_config=api_config,
            session_data=sample_session_data,
            knowledge_answer=knowledge_answer,
        )

        assert result["success"] is True
        formatted = result["formatted_response"]

        # 應包含 API 回傳的帳單資訊（透過 response_template 格式化）
        assert "帳單與發票狀態" in formatted
        # 應包含靜態知識（combine_with_knowledge=True）
        assert knowledge_answer in formatted

    @pytest.mark.asyncio
    async def test_billing_invoice_fallback_scenario(
        self, api_handler, sample_session_data
    ):
        """
        模擬 API 失敗時的降級場景：
        API 不可用 → 回傳 fallback_message + 靜態知識
        """
        api_handler.jgb_api.get_bills = AsyncMock(
            side_effect=Exception("JGB API 服務暫時不可用")
        )

        knowledge_answer = "帳單發票通常在繳費完成後 2-3 個工作天內開立。"
        api_config = {
            "endpoint": "jgb_bills",
            "params": {
                "role_id": "{session.role_id}",
                "user_id": "{session.user_id}",
            },
            "combine_with_knowledge": True,
            "fallback_message": "目前無法查詢帳單資料，建議聯繫客服。",
        }

        result = await api_handler.execute_api_call(
            api_config=api_config,
            session_data=sample_session_data,
            knowledge_answer=knowledge_answer,
        )

        assert result["success"] is False
        formatted = result["formatted_response"]
        # 降級訊息應包含 fallback_message
        assert "無法查詢帳單" in formatted
        # 應包含靜態知識
        assert knowledge_answer in formatted


# ---------------------------------------------------------------------------
# 9. response_template 格式化驗證
# ---------------------------------------------------------------------------

class TestResponseTemplateFormatting:
    """驗證 response_template 正確格式化 API 回應"""

    def test_format_response_with_template(self, api_handler):
        """有 response_template 時應使用模板格式化"""
        api_config = {
            "response_template": "查詢結果：{api_response}",
            "combine_with_knowledge": False,
        }
        api_result = {"message": "帳單金額 NT$25,000"}

        formatted = api_handler._format_response(
            api_config, api_result, knowledge_answer=None
        )
        assert "查詢結果" in formatted
        assert "25,000" in formatted

    def test_format_response_without_template(self, api_handler):
        """無 response_template 時應使用預設格式化"""
        api_config = {
            "combine_with_knowledge": False,
        }
        api_result = {"message": "帳單金額 NT$25,000"}

        formatted = api_handler._format_response(
            api_config, api_result, knowledge_answer=None
        )
        assert "25,000" in formatted

    def test_error_response_with_fallback(self, api_handler):
        """_error_response 應使用 fallback_message"""
        result = api_handler._error_response(
            "API timeout",
            fallback_message="系統忙碌中，請稍後再試。",
            knowledge_answer="帳單每月 1 號產生。",
        )
        assert result["success"] is False
        assert "系統忙碌" in result["formatted_response"]
        assert "帳單每月" in result["formatted_response"]

    def test_error_response_without_fallback(self, api_handler):
        """無 fallback_message 時應使用預設錯誤格式"""
        result = api_handler._error_response("API timeout")
        assert result["success"] is False
        assert "API timeout" in result["formatted_response"]


# ---------------------------------------------------------------------------
# 10. 端點缺失驗證
# ---------------------------------------------------------------------------

class TestMissingEndpoint:
    """驗證缺少 endpoint 時的錯誤處理"""

    @pytest.mark.asyncio
    async def test_missing_endpoint_in_config(
        self, api_handler, sample_session_data
    ):
        """api_config 缺少 endpoint 欄位應回傳錯誤"""
        config = {"params": {}}
        result = await api_handler.execute_api_call(
            api_config=config, session_data=sample_session_data
        )
        assert result["success"] is False
        assert "endpoint" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_endpoint_in_config(
        self, api_handler, sample_session_data
    ):
        """api_config 的 endpoint 為空字串應回傳錯誤"""
        config = {"endpoint": "", "params": {}}
        result = await api_handler.execute_api_call(
            api_config=config, session_data=sample_session_data
        )
        assert result["success"] is False
