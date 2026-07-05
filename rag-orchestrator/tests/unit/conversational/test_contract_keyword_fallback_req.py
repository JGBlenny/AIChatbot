"""unit:合約 keyword 查無 token 化 fallback（多輪回測 run295/296 逼出）。

真相：合約 title 格式不一致——「重慶北137-503」（無前綴）與「台北大同-重慶北5-304」
（帶前綴）並存；業者最自然的問法是物件全名「台北大同-重慶北137-503」→ server LIKE
恆查無。修法沿 get_meters/get_estate_status 先例：首查透傳；查無且 keyword 可拆
→ 以最長 token 重查 server（放寬命中面）＋client 端全 token 去分隔符 AND 過濾。
"""
import pytest
from unittest.mock import AsyncMock

pytestmark = pytest.mark.unit


def _contract(id, title):
    return {"id": id, "title": title, "status": 8}


def _api(responses):
    """依呼叫順序回覆的 _request 序列。"""
    from services.jgb_system_api import JGBSystemAPI
    api = JGBSystemAPI()
    api.use_mock = False
    api._request = AsyncMock(side_effect=[{"success": True, "data": d} for d in responses])
    return api


async def test_exact_keyword_hit_no_fallback():
    api = _api([[_contract(1, "重慶北137-503")]])
    r = await api.get_contracts(role_id="37305", keyword="重慶北137-503")
    assert [c["id"] for c in r["data"]] == [1]
    assert api._request.call_count == 1                       # 命中不重查


async def test_full_estate_name_falls_back_to_token_search():
    """物件全名（帶城市-區前綴）→ 首查空 → 最長 token 重查＋client 過濾。"""
    api = _api([
        [],                                                    # 首查「台北大同-重慶北137-503」空
        [_contract(1, "重慶北137-503"), _contract(2, "重慶北137-202"),
         _contract(3, "台北大同-重慶北5-304")],                # token 重查（放寬）
    ])
    r = await api.get_contracts(role_id="37305", keyword="台北大同-重慶北137-503")
    assert [c["id"] for c in r["data"]] == [1]                # 全 token AND 過濾唯一命中
    assert api._request.call_count == 2


async def test_fallback_matches_prefixed_title_too():
    """合約 title 帶前綴的也要能被無前綴問法配中（格式不一致雙向容錯）。"""
    api = _api([
        [],
        [_contract(3, "台北大同-重慶北5-304")],
    ])
    r = await api.get_contracts(role_id="37305", keyword="重慶北5-304")
    assert [c["id"] for c in r["data"]] == [3]


async def test_fallback_no_match_returns_empty():
    api = _api([[], [_contract(9, "完全無關物件")]])
    r = await api.get_contracts(role_id="37305", keyword="台北大同-重慶北137-503")
    assert r["data"] == []                                     # 過濾後空 → 引擎照舊追問


async def test_short_unsplittable_keyword_no_fallback():
    """無分隔符的短 keyword（如純編號/單詞）查無不重查——避免亂放寬。"""
    api = _api([[]])
    r = await api.get_contracts(role_id="37305", keyword="ABC123")
    assert r["data"] == [] and api._request.call_count == 1
