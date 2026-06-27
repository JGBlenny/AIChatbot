"""T2 主幹確定性：target_user 正規化（檢索角色路由的安全預設）。

純函式、不碰 DB/LLM → unit。對應 testing-traceability R5.3（target_user 路由）。
"""
import pytest

from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2 as KB

pytestmark = pytest.mark.unit


@pytest.mark.req("testing-traceability:5.3")
@pytest.mark.parametrize("inp,expected", [
    ("prospect", "prospect"),                 # 可信角色原樣
    ("property_manager", "property_manager"),
    ("tenant", "tenant"),
    ("亂打", "tenant"),                        # 未知 → tenant（最小權限安全預設）
    (None, "tenant"),                          # None → tenant
    ("", "tenant"),                            # 空字串 → tenant
    (["prospect"], "prospect"),                # list 取第一個
    (["未知角色"], "tenant"),                   # list 內未知 → tenant
    ([], "tenant"),                            # 空 list → tenant
])
def test_effective_target_user_normalization(inp, expected):
    assert KB._effective_target_user(inp) == expected
