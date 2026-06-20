"""
Unit tests for VendorKnowledgeRetrieverV2 b2b target_user 過濾重啟 + 角色正規化。
Feature: presales-retrieval-routing（最小實作）

- _effective_target_user：非可信角色（None/空/未知）→ tenant；可信角色原樣保留。
- b2b 路徑 SQL 重新帶入 target_user 過濾（寬鬆，NULL 放行）；b2c 維持不套用。
"""

import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2  # noqa: E402


@pytest.mark.parametrize("inp,expected", [
    (None, "tenant"),
    ("", "tenant"),
    ("garbage_role", "tenant"),
    ("property_manager", "property_manager"),
    ("system_admin", "system_admin"),
    ("tenant", "tenant"),
    ("landlord", "landlord"),
    ("prospect", "prospect"),
    (["property_manager"], "property_manager"),
    ([], "tenant"),
])
def test_effective_target_user_normalization(inp, expected):
    assert VendorKnowledgeRetrieverV2._effective_target_user(inp) == expected


def _vector_src():
    return inspect.getsource(VendorKnowledgeRetrieverV2._vector_search)


def _keyword_src():
    return inspect.getsource(VendorKnowledgeRetrieverV2._keyword_search)


def test_b2b_branch_applies_target_user_filter():
    """b2b 分支帶入 target_user 過濾（寬鬆，NULL 放行）。"""
    for src in (_vector_src(), _keyword_src()):
        assert "kb.target_user IS NULL OR kb.target_user && %s::text[]" in src


def test_b2c_branch_leaves_target_user_filter_empty():
    """b2c 分支 target_user_filter_sql 為空字串（不套用過濾，維持既有行為）。"""
    for src in (_vector_src(), _keyword_src()):
        assert 'target_user_filter_sql = ""' in src


def test_filter_param_uses_effective_target_user():
    """過濾參數使用正規化後的 effective target_user。"""
    for src in (_vector_src(), _keyword_src()):
        assert "self._effective_target_user(target_user)" in src
