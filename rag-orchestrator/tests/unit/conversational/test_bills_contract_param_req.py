"""unit：get_bills 合約過濾參數修正（帳單診斷 e2e 逼出）。

真相：jgb2 `/api/external/v1/bills` 的合約過濾參數是 `contract_id`（單數）——
adapter 誤送 `contract_ids`（複數）被上游無視，整個 role 的帳單全回（實測 50 筆
電錶儲值蓋台），bill_ref 識別鏈的「合約→帳單候選」名存實亡；繳費金流排障同傷。
修法：參數名改對＋client 端按列上 contract_id 防衛過濾（上游再無視也擋得住，
沿 get_contracts 雙向包含過濾先例）。
"""
import pytest
from unittest.mock import AsyncMock

pytestmark = pytest.mark.unit


def _api(responses):
    from services.jgb_system_api import JGBSystemAPI
    api = JGBSystemAPI()
    api.use_mock = False
    api._request = AsyncMock(side_effect=[{"success": True, "data": d} for d in responses])
    return api


def _bill(id, contract_id, title="電錶儲值"):
    return {"id": id, "contract_id": contract_id, "title": title, "status": 2}


async def test_contract_filter_uses_singular_param():
    """送給 /bills 的參數必須是 contract_id（單數）——複數會被上游無視。"""
    api = _api([[_bill(1, 62326)]])
    await api.get_bills(role_id="37305", contract_ids="62326")
    _, kwargs_or_params = api._request.call_args[0]
    assert kwargs_or_params.get("contract_id") == "62326"
    assert "contract_ids" not in kwargs_or_params


async def test_client_side_guard_filters_foreign_bills():
    """上游若無視參數回整包 → client 端按列上 contract_id 防衛過濾。"""
    api = _api([[_bill(1, 62326), _bill(2, 99999), _bill(3, 62326)]])
    r = await api.get_bills(role_id="37305", contract_ids="62326")
    assert [b["id"] for b in r["data"]] == [1, 3]


async def test_bill_ref_name_resolves_contract_then_filters():
    """bill_ref=物件名 → 合約解析 → 該合約帳單（含防衛過濾）全鏈。"""
    api = _api([
        [{"id": 62326, "title": "重慶北137-503", "status": 8}],   # get_contracts
        [_bill(10, 62326), _bill(11, 77777)],                     # get_bills
    ])
    r = await api.get_bills(role_id="37305", bill_ref="重慶北137-503")
    assert [b["id"] for b in r["data"]] == [10]


async def test_rows_without_contract_id_not_nuked():
    """防衛過濾只在列上帶 contract_id 時啟動——舊形狀列（無該鍵）不得被清空。"""
    api = _api([[{"id": 5, "title": "房租", "status": 2}]])
    r = await api.get_bills(role_id="37305", contract_ids="62326")
    assert [b["id"] for b in r["data"]] == [5]
