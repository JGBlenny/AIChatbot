"""TDD：`demo_vendor4.json` 整份真資料重建（任務契約 2026-09-08，業主裁示
「清掉測試資料 並 慢慢地抓取此團隊的資料」）。

驗兩件事：
1. 直接讀 `services/jgb/fixture_data/demo_vendor4.json`（**不經** `fixture_store`——
   那支模組被 `tests/conftest.py` 的 `JGB_MOCK_FIXTURE` 導去讀凍結的
   `regression_vendor4.json`，直讀路徑才驗得到 demo 檔本身）：不含任何舊合成
   陷阱 id／值，可見性一律只含 12291，數量與跨域連貫皆對。
2. mock round-trip：把 `fixture_store` 的記憶體狀態換成 demo 檔後，真的
   建構 `JGBSystemAPI`＋`JGBMockTransport` 查一次，證明「檔案內容」與
   「替身實際回應」一致——不是只驗 JSON 檔本身。

正對照組：`tests/fixtures/jgb/regression_vendor4.json`（測試套件實際吃的凍結
合成宇宙）**仍然**含 900001／信義區套房A——證明本檔的掃描規則本身沒壞
（掃得到已知一定在的東西），失敗只可能是 demo 檔真的乾淨了。
"""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytest

import services.jgb.fixture_store as fixture_store
from services.jgb_system_api import JGBSystemAPI
from services.agent.tools import jgb2 as jgb2_tools

pytestmark = pytest.mark.unit

_RAG_ROOT = Path(__file__).resolve().parents[3]
_DEMO_PATH = _RAG_ROOT / "services" / "jgb" / "fixture_data" / "demo_vendor4.json"
_REGRESSION_PATH = _RAG_ROOT / "tests" / "fixtures" / "jgb" / "regression_vendor4.json"

DEMO_USER_ID = 12291

#: 舊合成鏈的 id（見 `scripts/fixtures/build_demo_fixture_from_capture.py` 的
#: `_SYNTHETIC_TRAP_IDS`／`_SYNTHETIC_TRAP_MEMBER_IDS`）——demo 檔重建後必須整批不在。
_SYNTHETIC_BILL_IDS = {900001, 900002, 900003}
_SYNTHETIC_CONTRACT_IDS = {678, 600}
_SYNTHETIC_ESTATE_IDS = {456, 400, 54126, 54200, 54305}
_SYNTHETIC_METER_IDS = {501, 502, 503, 601}
_SYNTHETIC_REPAIR_IDS = {3001, 3002}
_SYNTHETIC_MEMBER_IDS = {100, 292, 305}

_PHONE_RE = re.compile(r"09\d{8}|09\d{2}-\d{3}-\d{3}|0\d{1,2}-\d{4}-\d{4}")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


@pytest.fixture
def demo_fixture() -> dict:
    return json.loads(_DEMO_PATH.read_text(encoding="utf-8"))


# ── 正對照組：regression 檔仍含舊陷阱，證明掃描規則沒壞 ──────────────────────

def test_positive_control_regression_fixture_still_has_legacy_traps():
    text = _REGRESSION_PATH.read_text(encoding="utf-8")
    assert "900001" in text, "正對照組落空——regression fixture 應仍含合成帳單 900001"
    assert "信義區套房A" in text, "正對照組落空——regression fixture 應仍含合成物件標題"


# ── 1. demo 檔本身：不含任何舊合成 id／值 ────────────────────────────────────

def test_demo_fixture_has_no_synthetic_ids(demo_fixture):
    bill_ids = {b["id"] for b in demo_fixture["bills"]}
    contract_ids = {c["id"] for c in demo_fixture["contracts"]}
    estate_ids = {e["id"] for e in demo_fixture["estates"]}
    meter_ids = {m["id"] for m in demo_fixture["meters"]}
    repair_ids = {r["id"] for r in demo_fixture["repairs"]}
    member_ids = {m.get("member_user_id") for m in demo_fixture["team_members"]}

    assert not (bill_ids & _SYNTHETIC_BILL_IDS), bill_ids & _SYNTHETIC_BILL_IDS
    assert not (contract_ids & _SYNTHETIC_CONTRACT_IDS), contract_ids & _SYNTHETIC_CONTRACT_IDS
    assert not (estate_ids & _SYNTHETIC_ESTATE_IDS), estate_ids & _SYNTHETIC_ESTATE_IDS
    assert not (meter_ids & _SYNTHETIC_METER_IDS), meter_ids & _SYNTHETIC_METER_IDS
    assert not (repair_ids & _SYNTHETIC_REPAIR_IDS), repair_ids & _SYNTHETIC_REPAIR_IDS
    assert not (member_ids & _SYNTHETIC_MEMBER_IDS), member_ids & _SYNTHETIC_MEMBER_IDS


def test_demo_fixture_has_no_trap_contact_values(demo_fixture):
    text = json.dumps(demo_fixture, ensure_ascii=False)
    assert "0912345678" not in text
    assert "tenant@example.com" not in text

    emails = set(_EMAIL_RE.findall(text))
    non_example = {e for e in emails if not e.endswith("@example.com")}
    assert not non_example, f"出現非 @example.com 的 email：{non_example}"


def test_demo_fixture_visibility_is_12291_only(demo_fixture):
    for vis_key in ("bill_visibility", "contract_visibility", "estate_visibility"):
        table = demo_fixture[vis_key]
        assert table, f"{vis_key} 空表——先確認 fixture 已跑過 --mode all 建置"
        for row_id, viewers in table.items():
            assert viewers == [DEMO_USER_ID], f"{vis_key}[{row_id}] = {viewers}"


def test_demo_fixture_counts(demo_fixture):
    assert len(demo_fixture["bills"]) == 61
    assert len(demo_fixture["repairs"]) == 119
    # 2026-09-09：status-overview 以 user_id 圈定後取 27 筆（原 8 筆＝帳單引用）
    assert len(demo_fixture["contracts"]) == 27
    assert len(demo_fixture["estates"]) >= 46
    assert len(demo_fixture["meters"]) == 7


def test_demo_fixture_cross_domain_estate_ids_resolve(demo_fixture):
    estate_ids = {e["id"] for e in demo_fixture["estates"]}
    for b in demo_fixture["bills"]:
        assert b["estate_id"] in estate_ids, f"bill {b['id']} 的 estate_id 查無物件列"
    for r in demo_fixture["repairs"]:
        if r.get("estate_id") is not None:
            assert r["estate_id"] in estate_ids, f"repair {r['id']} 的 estate_id 查無物件列"
    for c in demo_fixture["contracts"]:
        assert c["estate_id"] in estate_ids, f"contract {c['id']} 的 estate_id 查無物件列"


# ── 2. mock round-trip：把 fixture_store 指到 demo 檔後真的查一次 ──────────────

def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def api_on_demo_fixture(monkeypatch):
    """把行程內的 `fixture_store._DATA` 換成 demo 檔，建一個吃它的 `JGBSystemAPI`。

    ⚠️ 用 `monkeypatch` 存回舊值，測試結束後其他測試繼續吃
    `regression_vendor4.json`（`tests/conftest.py` 設的 `JGB_MOCK_FIXTURE`）。
    """
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    original = fixture_store._DATA
    fixture_store.load_from(_DEMO_PATH)
    try:
        instance = JGBSystemAPI()
        monkeypatch.setattr(jgb2_tools, "_api_singleton", instance, raising=False)
        yield instance
    finally:
        fixture_store._DATA = original


def test_mock_round_trip_get_bills_sees_all_61_real_bills(api_on_demo_fixture):
    resp = _run(api_on_demo_fixture.get_bills(
        role_id="20151", user_id="12291", viewer_user_id="12291",
    ))
    assert resp["success"] is True
    # ⚠️ `get_bills()` 不轉發 `per_page`（見 `services/jgb_system_api.py::get_bills`），
    # 預設頁面大小 50 < 61，故 `data` 只回第一頁；`pagination.total` 才是
    # 「這個 viewer 圈定下查得到幾筆」的忠實數字——61 筆真實帳單全數可見
    # （bill_visibility 一律 [12291]），才是本測試要證的事。
    assert resp["pagination"]["total"] == 61, resp["pagination"]
    assert len(resp["data"]) <= 61


def test_mock_round_trip_get_contracts_no_longer_finds_synthetic_estate(api_on_demo_fixture):
    """合成物件「信義區套房A」（連同其合約）已整批不在——keyword 精準比對它的
    完整標題查無列；⚠️ 不能用「信義」子字串當負向關鍵字：這次真資料擷取裡
    剛好有一份真合約標題含「信義」（台北信義-市政府...），子字串會誤判為
    仍殘留合成資料。正對照組改用另一個真實命中的子字串證明搜尋機制本身能用。
    """
    gone = _run(api_on_demo_fixture.get_contracts(
        role_id="20151", keyword="信義區套房A",
    ))
    assert gone["success"] is True
    assert gone["data"] == []

    found = _run(api_on_demo_fixture.get_contracts(
        role_id="20151", keyword="信義",
    ))
    assert found["success"] is True
    assert len(found["data"]) >= 1


def test_demo_fixture_has_no_raw_door_tokens_outside_synthetic_placeholder():
    """verifier 2026-09-08 r2 F3／r3 A2：門牌 token（123號4樓之2…）只准以合成佔位
    `合成路N段M號` 的形式出現；任何其他 `\d+號…` 都是遮罩漏網。逐欄位走訪六個域。
    正對照：凍結回歸宇宙（合成鏈）本來就含非佔位門牌，同一掃描器對它必須命中。"""
    import json, re
    from pathlib import Path
    root = Path(__file__).resolve().parents[3]
    door = re.compile(r"\d+(?:-\d+)?號(?:\d+樓)?(?:之\d+)?")
    placeholder = re.compile(r"合成路\d+段\d+號")

    def offending_fields(doc):
        hits = []
        for domain in ("bills", "contracts", "estates", "meters", "repairs", "team_members"):
            for row in doc.get(domain) or []:
                for key, val in row.items():
                    if isinstance(val, str) and door.search(placeholder.sub("", val)):
                        hits.append(f"{domain}.{key}")
        return hits

    demo = json.load(open(root / "services" / "jgb" / "fixture_data" / "demo_vendor4.json", encoding="utf-8"))
    assert offending_fields(demo) == [], "demo 替身有未遮罩門牌"
    regression = json.load(open(root / "tests" / "fixtures" / "jgb" / "regression_vendor4.json", encoding="utf-8"))
    assert offending_fields(regression), "正對照失效：回歸宇宙應含非佔位門牌，掃描器沒看見"
