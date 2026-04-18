"""
單元測試：chat.py role_id 支援

驗證：
- VendorChatRequest model 接受 role_id 欄位（Optional[str]）
- session_data 組裝包含 role_id

對應任務：kb-jgb-system-coverage-completion task 1.2
對應需求：requirements.md Requirement 7, criteria 7.3, 7.4
"""
import os
import sys

# Ensure rag-orchestrator is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from routers.chat import VendorChatRequest


class TestVendorChatRequestRoleId:
    """VendorChatRequest role_id 欄位驗證"""

    def test_role_id_accepted(self):
        """role_id 字串值應被正確接受"""
        r = VendorChatRequest(message='test', vendor_id=1, role_id='5678')
        assert r.role_id == '5678'

    def test_role_id_defaults_to_none(self):
        """未提供 role_id 時應預設為 None"""
        r = VendorChatRequest(message='test', vendor_id=1)
        assert r.role_id is None

    def test_role_id_is_optional(self):
        """role_id 欄位應為非必填"""
        field = VendorChatRequest.model_fields['role_id']
        assert not field.is_required()

    def test_role_id_independent_of_target_user(self):
        """role_id 與 target_user 應為獨立欄位"""
        r = VendorChatRequest(
            message='test', vendor_id=1,
            role_id='5678', target_user='tenant'
        )
        assert r.role_id == '5678'
        assert r.target_user == 'tenant'


class TestSessionDataRoleId:
    """session_data 組裝中 role_id 的存在性驗證（靜態檢查）"""

    def test_session_data_contains_role_id(self):
        """_handle_api_call 中 session_data dict 應包含 role_id key"""
        path = os.path.join(
            os.path.dirname(__file__), '..', 'routers', 'chat.py'
        )
        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()

        # Find the session_data block in _handle_api_call
        assert "'role_id': request.role_id" in src, (
            "session_data should contain 'role_id': request.role_id"
        )
