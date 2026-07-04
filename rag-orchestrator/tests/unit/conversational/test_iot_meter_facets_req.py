"""unit:IoT 電表面向底座（iot-conversational-facets 任務 1.1–1.3 / R2, R5, R8, R9.1）。

get_meters wrapper（client 端 keyword 過濾——端點無此參數）＋
build_meter_facts 四分支矩陣（後續任務 1.2/1.3 擴充）。
機制口徑以 research.md 主題 1–3 為準；J-I1 防護（離線不引用 is_poweron）。
"""
import pytest
from unittest.mock import AsyncMock

pytestmark = pytest.mark.unit


def _meter(**over):
    m = {"id": 501, "estate_id": 9001, "estate_name": "海大質感獨立套房",
         "name": "3F 分電表", "manufacturer": "DAE", "meter_type": "cloud",
         "is_online": True, "is_topup": True, "enable_topup": True,
         "balance": 350.0, "available_meter": 87.5, "current_reading": 1234.5,
         "is_poweron": True, "is_low_battery": False,
         "synced_at": "2026-07-04 10:35:00"}
    m.update(over)
    return m


def _api_with_rows(rows):
    """真 client＋stub _request（回傳固定 rows，並記錄參數供斷言）。"""
    from services.jgb_system_api import JGBSystemAPI
    api = JGBSystemAPI()
    api.use_mock = False
    api._request = AsyncMock(return_value={
        "success": True, "data": rows,
        "pagination": {"total": len(rows)}})
    return api


# ════════ 1.1 get_meters wrapper：client 端過濾三路（R2.1/R8.1）════════

async def test_meters_missing_role_id_degrades():
    from services.jgb_system_api import JGBSystemAPI
    api = JGBSystemAPI()
    r = await api.get_meters(role_id="")
    assert r.get("success") is False


async def test_meters_keyword_filters_by_estate_name():
    rows = [_meter(id=501, estate_name="海大質感獨立套房"),
            _meter(id=502, estate_name="基隆溫馨一人宅", name="主電表")]
    api = _api_with_rows(rows)
    r = await api.get_meters(role_id="37305", keyword="海大")
    assert r["success"] and [m["id"] for m in r["data"]] == [501]


async def test_meters_keyword_filters_by_meter_name():
    rows = [_meter(id=501, name="3F 分電表"), _meter(id=502, name="1F 主電表")]
    api = _api_with_rows(rows)
    r = await api.get_meters(role_id="37305", keyword="主電表")
    assert [m["id"] for m in r["data"]] == [502]


async def test_meters_keyword_no_match_returns_empty_not_raise():
    api = _api_with_rows([_meter()])
    r = await api.get_meters(role_id="37305", keyword="不存在的物件")
    assert r["success"] and r["data"] == []


async def test_meters_no_keyword_returns_all():
    api = _api_with_rows([_meter(id=1), _meter(id=2)])
    r = await api.get_meters(role_id="37305")
    assert len(r["data"]) == 2


async def test_meters_requests_full_page_and_passes_estate_id():
    api = _api_with_rows([])
    await api.get_meters(role_id="37305", estate_id="9001")
    path, params = api._request.call_args.args
    assert path.endswith("/meters")
    assert params["role_id"] == "37305"
    assert params["per_page"] == 200                       # 全列拉取（≤200）
    assert params["estate_id"] == "9001"                   # 端點原生參數透傳


async def test_meters_upstream_failure_degrades_to_empty():
    from services.jgb_system_api import JGBSystemAPI
    api = JGBSystemAPI()
    api.use_mock = False
    api._request = AsyncMock(return_value={"success": False})
    r = await api.get_meters(role_id="37305", keyword="海大")
    assert r["success"] is False and r["data"] == []


def test_meters_registered_in_api_registry():
    from services.api_call_handler import APICallHandler
    handler = APICallHandler(db_pool=None)
    assert "jgb_meters" in handler.api_registry


# ════════ 1.2/1.3 build_meter_facts：四分支×廠商×synced_at 矩陣（R2.2–2.5, R5.1）════════

def _build(**over):
    from services.jgb.iot import build_meter_facts
    return build_meter_facts(_meter(**over), "租客說沒電")


# ── 分支①：離線優先（J-I1 防護：不引用 is_poweron 下供電結論）──

def test_offline_dae_snapshot_wording_and_account_cause():
    out = _build(is_online=False, is_poweron=True, manufacturer="DAE")
    assert "離線" in out
    assert "2026-07-04 10:35" in out                        # 截至最後同步（synced_at 原樣）
    assert "帳號" in out and ("密碼" in out or "驗證" in out)  # DAE 高頻真因：帳密失效
    assert "台科電" in out or "廠商" in out                  # 仍離線導廠商
    for verdict in ("供電正常", "供電目前為關閉", "自動復電"):
        assert verdict not in out                            # 離線不下供電結論（J-I1）


def test_offline_miezo_no_synced_at_degrades_wording():
    out = _build(is_online=False, manufacturer="Miezo", meter_type="cloud",
                 synced_at=None, enable_topup=False, is_topup=False)
    assert "離線" in out
    assert "None" not in out                                 # 無 synced_at 措辭降級
    assert "帳號" not in out                                 # DAE 帳密真因不套用 Miezo


# ── 分支②：儲值耗盡（電表端自動斷/復電——廠商行為措辭）──

def test_online_topup_exhausted_gives_auto_repower():
    out = _build(is_online=True, is_poweron=False, enable_topup=True,
                 balance=0.0, available_meter=0.0)
    assert "餘額" in out and "0" in out                       # 存值原樣
    assert "自動復電" in out                                  # 儲值入帳後電表端自動復電
    assert "儲值" in out
    assert "電表端" in out                                    # 措辭歸廠商行為


# ── 分支③：供電關閉（不臆測誰關）──

def test_online_poweroff_non_topup_points_to_mode_switch():
    out = _build(is_online=True, is_poweron=False, enable_topup=False,
                 is_topup=False)
    assert "關閉" in out
    assert "IoT 裝置" in out or "供電模式" in out             # 模式切換路徑
    assert "自動復電" not in out                              # 非儲值不談復電
    assert "原因" in out                                      # 明示無斷電原因紀錄


def test_online_poweroff_topup_with_sufficient_balance_is_switch_not_exhausted():
    out = _build(is_online=True, is_poweron=False, enable_topup=True,
                 balance=350.0, available_meter=87.5)
    assert "關閉" in out
    assert "耗盡" not in out                                  # 餘額足→非耗盡分支


# ── 分支④：供電正常 → 轉硬體/確認問對表 ──

def test_online_poweron_normal_turns_to_hardware():
    out = _build(is_online=True, is_poweron=True)
    assert "供電" in out and "正常" in out
    assert "廠商" in out or "台科電" in out                    # 硬體/迴路轉向
    assert "這顆" in out or "確認" in out                      # 是否問對表


# ── 設備狀況解碼＋度數存值（R2.5/R5.2）──

def test_status_decode_carries_reading_verbatim():
    out = _build()
    assert "1234.5" in out                                    # current_reading 存值原樣
    assert "海大質感獨立套房" in out                           # 物件識別


# ── 註冊表＋formatter 分發＋face=None 恆等（R9.1）──

def test_meter_face_builders_registry():
    from services.jgb.iot import METER_FACE_BUILDERS, build_meter_facts
    assert set(METER_FACE_BUILDERS.keys()) == {"電表排障"}
    assert METER_FACE_BUILDERS["電表排障"] is build_meter_facts


def test_formatter_dispatches_jgb_meters_by_face():
    from services.jgb_response_formatter import format_jgb_response
    from services.jgb.iot import build_meter_facts
    m = _meter(is_online=False)
    api_result = {"success": True, "data": [m]}
    faced = format_jgb_response(api_result, endpoint="jgb_meters",
                                user_question="沒電", face="電表排障")
    assert faced == build_meter_facts(m, "沒電")
    none_case = format_jgb_response(api_result, endpoint="jgb_meters",
                                    user_question="沒電", face=None)
    assert none_case != faced                                 # face=None 走原路（恆等/mutation）
