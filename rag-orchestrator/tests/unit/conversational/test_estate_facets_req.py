"""unit:物件面向底座（estate-conversational-facets 任務 1.1–1.3 / R4, R8.1）。

get_estate_status wrapper（拉頁＋token 過濾＋sentinel——引擎 0-row 短路對策）＋
get_estate_detail（空 id 優雅降級）＋ build_estate_status_facts（status 轉譯／
建約決策樹／sentinel 口徑／個資紅線）。口徑以 research.md 定案 9 項為準。
⚠️ jgb_estates 為修繕報修表單現役鍵——本面向用新鍵 jgb_estate_status，舊鍵零改動。
"""
import pytest
from unittest.mock import AsyncMock

pytestmark = pytest.mark.unit


def _estate(**over):
    e = {"id": 8801, "serial_id": "E-8801", "title": "新莊富貴500-14B05",
         "status": 2, "use_for": "residential",
         "address": "新北市新莊區富貴路500號14樓B05室",
         "full_address": "新北市新莊區富貴路500號14樓B05室",
         "display_address": "新北市新莊區富貴路", "full_display_address": "新北市新莊區富貴路",
         "latitude": 25.035, "longitude": 121.435,
         "rent": 15800, "currency": "TWD"}
    e.update(over)
    return e


def _api_with_rows(rows):
    from services.jgb_system_api import JGBSystemAPI
    api = JGBSystemAPI()
    api.use_mock = False
    api._request = AsyncMock(return_value={
        "success": True, "data": rows, "pagination": {"total": len(rows)}})
    return api


# ════════ 1.1 get_estate_status wrapper（R4.1/R8.1）════════

async def test_estate_status_keyword_token_filter_title():
    rows = [_estate(id=8801, title="新莊富貴500-14B05"),
            _estate(id=8802, title="基隆海大套房A1")]
    api = _api_with_rows(rows)
    r = await api.get_estate_status(role_id="37305", keyword="新莊富貴500的14B05")
    assert r["success"] and [e["id"] for e in r["data"]] == [8801]


async def test_estate_status_keyword_matches_display_address():
    rows = [_estate(id=8801, title="14B05", display_address="新北市新莊區富貴路"),
            _estate(id=8802, title="A1", display_address="基隆市中正區北寧路")]
    api = _api_with_rows(rows)
    r = await api.get_estate_status(role_id="37305", keyword="新莊 富貴路")
    assert [e["id"] for e in r["data"]] == [8801]


async def test_estate_status_pure_digit_keyword_matches_id_first():
    rows = [_estate(id=8801, title="500號物件"), _estate(id=8802, title="B2")]
    api = _api_with_rows(rows)
    r = await api.get_estate_status(role_id="37305", keyword="8802")
    assert [e["id"] for e in r["data"]] == [8802]


async def test_estate_status_int_keyword_tolerated():
    rows = [_estate(id=8801), _estate(id=8802)]
    api = _api_with_rows(rows)
    r = await api.get_estate_status(role_id="37305", keyword=8801)  # int（候選 refine 先例）
    assert [e["id"] for e in r["data"]] == [8801]


async def test_estate_status_empty_result_returns_sentinel():
    """引擎 0-row 短路對策（design Issue 1）：過濾後空集回單元素 sentinel。"""
    rows = [_estate(id=8801, title="基隆海大套房A1")]
    api = _api_with_rows(rows)
    r = await api.get_estate_status(role_id="37305", keyword="不存在的物件名")
    assert r["success"] is True
    assert len(r["data"]) == 1
    s = r["data"][0]
    assert s.get("found") is False and s.get("keyword") == "不存在的物件名"


async def test_estate_status_api_empty_also_sentinel():
    api = _api_with_rows([])
    r = await api.get_estate_status(role_id="37305", keyword="任何")
    assert r["success"] and r["data"][0].get("found") is False


async def test_estate_status_rows_carry_status_zh_label_field():
    """label_fields 用 status_zh 轉譯欄（wrapper 附掛，候選標籤帶狀態）。"""
    rows = [_estate(id=8801, status=2), _estate(id=8802, status=4)]
    api = _api_with_rows(rows)
    r = await api.get_estate_status(role_id="37305")
    zh = {e["id"]: e.get("status_zh") for e in r["data"]}
    assert zh[8801] == "刊登中" and "洽談中" in zh[8802]


async def test_estate_status_api_failure_degrades():
    from services.jgb_system_api import JGBSystemAPI
    api = JGBSystemAPI()
    api.use_mock = False
    api._request = AsyncMock(return_value={"success": False})
    r = await api.get_estate_status(role_id="37305", keyword="x")
    assert r.get("success") is False


# ════════ 1.1 get_estate_detail（sentinel 無 id → 優雅降級）════════

async def test_estate_detail_empty_id_degrades():
    from services.jgb_system_api import JGBSystemAPI
    api = JGBSystemAPI()
    api.use_mock = False
    for bad in (None, "", "None"):
        r = await api.get_estate_detail(estate_id=bad)
        assert r.get("success") is False, f"id={bad!r} 應優雅降級"


async def test_estate_detail_single_object_normalized_to_list():
    from services.jgb_system_api import JGBSystemAPI
    api = JGBSystemAPI()
    api.use_mock = False
    api._request = AsyncMock(return_value={
        "success": True,
        "data": _estate(id=8801, description="近捷運",
                        contract_required_fields={"all_filled": True, "fields": []})})
    r = await api.get_estate_detail(estate_id=8801)
    assert r["success"] and isinstance(r["data"], list) and len(r["data"]) == 1
    assert r["data"][0]["contract_required_fields"]["all_filled"] is True


# ════════ 1.2 build_estate_status_facts（R4.2/R4.3）════════

def _facts(estate, detail=None, q="這個物件現在什麼狀態"):
    from services.jgb.estates import build_estate_status_facts
    return build_estate_status_facts(estate, detail, q)


def test_facts_sentinel_wording_red_lines():
    """sentinel：併含「確認名稱」與「非刊登中」雙情境；不得斷言已刪除。"""
    txt = _facts({"found": False, "keyword": "富貴500"})
    assert "富貴500" in txt and "非刊登中" in txt and "名稱" in txt
    assert "已刪除" not in txt and "不存在" not in txt


@pytest.mark.parametrize("status,token", [
    (1, "未刊登"), (2, "刊登中"), (4, "洽談中"), (8, "租約中")])
def test_facts_status_translation(status, token):
    txt = _facts(_estate(status=status))
    assert token in txt


def test_facts_unknown_status_annotated_raw():
    txt = _facts(_estate(status=6))
    assert "6" in txt  # 未知位元值原樣標注（互斥性防護）


def test_facts_contract_ready_when_filled_and_published():
    detail = {"contract_required_fields": {"all_filled": True, "fields": []}}
    txt = _facts(_estate(status=2), detail)
    assert "可建立合約" in txt or "可建約" in txt


def test_facts_missing_fields_listed():
    detail = {"contract_required_fields": {"all_filled": False, "fields": [
        {"field": "size", "label": "面積", "is_filled": False},
        {"field": "rent", "label": "每月租金", "is_filled": False},
        {"field": "title", "label": "物件名稱", "is_filled": True}]}}
    txt = _facts(_estate(status=2), detail)
    assert "面積" in txt and "每月租金" in txt
    assert "物件名稱" not in txt.split("尚缺")[-1][:40] if "尚缺" in txt else True


def test_facts_not_published_states_contract_precondition():
    """status≠2：建約前提為刊登中（EstateController.php:279-283 口徑）。"""
    txt = _facts(_estate(status=1))
    assert "刊登中" in txt  # 前提說明必然帶到


def test_facts_detail_absent_degrades_gracefully():
    txt = _facts(_estate(status=2), None)
    assert "刊登中" in txt  # 無 detail 仍有狀態 facts，不拋錯


def test_facts_pii_red_line():
    """個資紅線：完整地址與經緯度值不得出現在 facts。"""
    e = _estate(status=2)
    txt = _facts(e, {"contract_required_fields": {"all_filled": True, "fields": []}})
    assert "富貴路500號14樓B05室" not in txt      # full/address 值
    assert "25.035" not in txt and "121.435" not in txt
    assert e["title"] in txt                       # 識別靠 title
    # display_address（對外遮蔽版）允許出現——不強制斷言存在，只確保完整版不漏


# ════════ 1.2 face 分發恆等（零回歸慣例）════════

def test_face_none_returns_none():
    from services.jgb.estates import face_estate_response
    assert face_estate_response([_estate()], "問題", None) is None


def test_face_unknown_returns_none():
    from services.jgb.estates import face_estate_response
    assert face_estate_response([_estate()], "問題", "不存在的面向") is None


def test_face_diagnosis_dispatches():
    from services.jgb.estates import face_estate_response
    out = face_estate_response([_estate(status=2)], "這物件什麼狀態", "物件現況診斷")
    assert out and "刊登中" in out


def test_formatter_routes_estate_status_endpoint():
    from services.jgb_response_formatter import format_jgb_response
    out = format_jgb_response(
        {"success": True, "data": [_estate(status=4)]},
        endpoint="jgb_estate_status", user_question="狀態?", face="物件現況診斷")
    assert "洽談中" in out


def test_registry_has_new_keys_and_old_key_untouched():
    """jgb_estate_status/jgb_estate_detail 新鍵註冊；jgb_estates 舊鍵仍指舊方法。"""
    from services.api_call_handler import APICallHandler
    h = APICallHandler.__new__(APICallHandler)
    import services.api_call_handler as m
    import inspect
    src = inspect.getsource(m)
    assert "'jgb_estate_status'" in src and "'jgb_estate_detail'" in src
    assert "'jgb_estates': self.jgb_api.get_estates" in src  # 修繕表單現役鍵不動
