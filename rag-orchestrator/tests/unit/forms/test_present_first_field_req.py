"""重建：FormManager._present_first_field 首欄呈現契約（spec unit-coverage-rebuild・任務 2・R4.1/4.2）。

純函式、不碰 DB → unit。鎖定首欄呈現的對外契約（prompt 組裝、欄位中介資料、quick_replies）。
"""
import pytest

from form_manager import FormManager

pytestmark = pytest.mark.unit


@pytest.fixture
def manager():
    return FormManager()


@pytest.mark.req("unit-coverage-rebuild:4.1")
def test_present_first_field_prompt_and_field_meta(manager):
    """prompt 含 form_name／首欄 prompt／取消提示；current_field 與 type 正確。"""
    schema = {
        "form_id": "f",
        "form_name": "租金繳納設定",
        "default_intro": "好的，我們來設定。",
        "fields": [
            {"field_name": "method", "field_type": "select", "prompt": "請選擇繳納方式",
             "options": [{"label": "轉帳", "value": "transfer"}]},
        ],
    }
    out = manager._present_first_field(schema)
    assert "租金繳納設定" in out["prompt"]
    assert "請選擇繳納方式" in out["prompt"]
    assert "取消" in out["prompt"]
    assert out["current_field"] == "method"
    assert out["current_field_type"] == "select"


@pytest.mark.req("unit-coverage-rebuild:4.1")
def test_present_first_field_defaults_field_type_text(manager):
    """首欄未標 field_type → current_field_type 預設 'text'。"""
    schema = {
        "form_id": "f",
        "form_name": "意見回饋",
        "fields": [
            {"field_name": "content", "prompt": "請輸入內容"},
        ],
    }
    out = manager._present_first_field(schema)
    assert out["current_field_type"] == "text"


@pytest.mark.req("unit-coverage-rebuild:4.2")
def test_present_first_field_select_builds_quick_replies(manager):
    """首欄為 select → quick_replies 為對應選項按鈕 list。"""
    schema = {
        "form_id": "f",
        "form_name": "身分確認",
        "fields": [
            {"field_name": "identity", "field_type": "select", "prompt": "您是？",
             "options": [
                 {"label": "個人房東", "value": "individual"},
                 {"label": "包租代管業", "value": "agency"},
             ]},
        ],
    }
    out = manager._present_first_field(schema)
    qr = out["quick_replies"]
    assert isinstance(qr, list) and len(qr) == 2
    assert {r["text"] for r in qr} == {"個人房東", "包租代管業"}
    assert {r["value"] for r in qr} == {"individual", "agency"}


@pytest.mark.req("unit-coverage-rebuild:4.2")
def test_present_first_field_non_select_quick_replies_none(manager):
    """首欄非 select → quick_replies 為 None。"""
    schema = {
        "form_id": "f",
        "form_name": "聯絡資料",
        "fields": [
            {"field_name": "phone", "field_type": "text", "prompt": "請輸入電話"},
        ],
    }
    out = manager._present_first_field(schema)
    assert out["quick_replies"] is None
