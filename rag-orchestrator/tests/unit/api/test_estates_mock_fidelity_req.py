"""`/estates` 替身逐條對照 `EstateApiController`（inventory §8 第 4 項的稽核產出）。

M2 在 contracts 上抓到的三類偏差，estates 全中：投影外欄位、過度寬鬆的比對、
恆定 where 漏條件。本檔把修好的行為具名鎖住——每一條都對得上 production 的一行。

⚠️ 仍未涵蓋（mock 結構上證不到，只有真 API 會現形）：
   API key 的 applyAccessibleEstateScope 圈定、show 的 403／404 之分、
   5 分鐘 Cache::remember 造成的陳舊、mapping 的 countries 三表組裝、真實標題分佈。
"""
import asyncio

import pytest

from services.jgb.estate_fixtures import (
    EXTERNAL_ESTATE_FIELDS,
    INTERNAL_ESTATE_FIELDS,
    EstateFixtureTable,
    ForeignEstateFieldError,
    assert_estate_projection,
    build_contract_required_fields,
)

pytestmark = pytest.mark.unit

ROLE = "20151"          # fixture 列的 role_id
#: 跨域連貫修正（transport-agent-mcp-orchestration 收案修正 4）後新增 456／400——
#: 兩戶分別是 contract 678／600 與 repairs 3001/3002 對齊的物件，見 fixture_data
#: `demo_vendor4.json` 頂端註解。
OPEN_IDS = [400, 456, 54126, 54200]
#: 真資料子集（role_id=20151/user_id=12291 擷取）新增的已刊登物件——
#: 與 OPEN_IDS 同樣 active=1／is_open=1／role_id=20151，一併會出現在
#: 未帶篩選條件的查詢結果裡；不併入 OPEN_IDS 是為了保留「合成矩陣」原意可獨立辨識。
REAL_OPEN_IDS = [45728, 67649, 67651, 67652, 68926]
CLOSED_ID = 54305       # is_open=0


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    from services.jgb_system_api import JGBSystemAPI
    return JGBSystemAPI()


# ── 恆定 where：active=1 且 is_open=1（:52-53、:121-124）──────────────────

@pytest.mark.req("face-exit-before-grounding:1")
def test_only_published_estates_are_visible(api):
    """⚠️ 真資料子集併入後不再是封閉四筆——改驗合成／真實兩批已刊登物件皆在內、
    已下架物件（54305）不在內。"""
    r = _run(api.get_estates(role_id=ROLE))
    ids = {e["id"] for e in r["data"]}
    assert set(OPEN_IDS) <= ids
    assert set(REAL_OPEN_IDS) <= ids
    assert CLOSED_ID not in ids


@pytest.mark.req("face-exit-before-grounding:1")
def test_unpublished_estate_detail_is_not_found(api):
    """`show()` 同樣過濾 is_open=1 → 非刊登中即 404（我方折疊為 success:False）。"""
    assert _run(api.get_estate_detail(estate_id=CLOSED_ID))["success"] is False
    assert _run(api.get_estate_detail(estate_id=OPEN_IDS[0]))["success"] is True


# ── applyFilters 的參數語義 ──────────────────────────────────────────────

@pytest.mark.req("face-exit-before-grounding:1")
def test_keyword_matches_title_only_not_address(api):
    """production：`where('title','like',...)`（:189-192）。

    舊替身連 `full_address` 一起比＝**過度寬鬆**：用地址關鍵字在替身查得到、
    在 production 查不到。
    """
    by_title = _run(api.get_estates(role_id=ROLE, keyword="信義區精緻套房"))
    assert [e["id"] for e in by_title["data"]] == [54126]
    by_address = _run(api.get_estates(role_id=ROLE, keyword="信義路五段7號"))
    assert by_address["data"] == []


@pytest.mark.req("face-exit-before-grounding:1")
def test_role_id_is_a_filter_not_an_echo(api):
    """舊替身把傳入的 role_id 寫進每一列 → 任何 role 都命中。"""
    assert _run(api.get_estates(role_id="99999"))["data"] == []


@pytest.mark.req("face-exit-before-grounding:1")
def test_use_for_outside_whitelist_is_silently_ignored(api):
    """production 只在三個合法值時才加條件（:149-155）——非法值**不報錯也不過濾**。"""
    kept = _run(api.get_estates(role_id=ROLE, per_page=50, use_for="不存在的用途"))
    kept_ids = {e["id"] for e in kept["data"]}
    assert set(OPEN_IDS) <= kept_ids
    assert set(REAL_OPEN_IDS) <= kept_ids
    narrowed = _run(api.get_estates(role_id=ROLE, per_page=50, use_for="business"))
    assert narrowed["data"] == []


@pytest.mark.req("face-exit-before-grounding:1")
def test_sort_by_outside_whitelist_falls_back_to_updated_at(api):
    """白名單外回退 `updated_at desc`（:60-66），非拒絕。"""
    bogus = _run(api.get_estates(role_id=ROLE, per_page=50, sort_by="rent; DROP TABLE"))
    fallback = _run(api.get_estates(role_id=ROLE, per_page=50, sort_by="updated_at"))
    assert [e["id"] for e in bogus["data"]] == [e["id"] for e in fallback["data"]]
    ascending = _run(api.get_estates(role_id=ROLE, per_page=50,
                                     sort_by="rent", sort_direction="asc"))
    assert [e["rent"] for e in ascending["data"]] == sorted(
        e["rent"] for e in ascending["data"])


# ── 分頁 ────────────────────────────────────────────────────────────────

@pytest.mark.req("face-exit-before-grounding:1")
def test_pagination_bounds_match_production(api):
    """⚠️ `total` 不再斷言固定為合成四筆——改以 `EstateFixtureTable().visible_rows()`
    的實際已刊登筆數推導期望值。"""
    total_open = len(EstateFixtureTable().visible_rows())
    capped = _run(api.get_estates(role_id=ROLE, per_page=9999))
    assert capped["pagination"]["per_page"] == 200          # MAX_PER_PAGE
    one = _run(api.get_estates(role_id=ROLE, per_page=1))
    assert one["pagination"] == {"current_page": 1, "per_page": 1, "total": total_open,
                                 "total_pages": total_open, "has_more": total_open > 1}
    empty = _run(api.get_estates(role_id="99999", per_page=50))
    assert empty["pagination"]["total_pages"] == 0 and empty["pagination"]["has_more"] is False


# ── 投影 ────────────────────────────────────────────────────────────────

@pytest.mark.req("face-exit-before-grounding:1")
def test_no_foreign_field_and_no_internal_leak(api):
    """`estate_room_number` 是 `/repairs` 的欄位（RepairApiController.php:323），
    `/estates` 從來不回它；`active`／`is_open` 是內部欄位，過濾用、不投影。"""
    rows = _run(api.get_estates(role_id=ROLE))["data"]
    for row in rows:
        assert "estate_room_number" not in row
        assert not (set(row) & INTERNAL_ESTATE_FIELDS)
        assert set(row) <= EXTERNAL_ESTATE_FIELDS


@pytest.mark.req("face-exit-before-grounding:1")
def test_projection_guard_bites():
    with pytest.raises(ForeignEstateFieldError):
        assert_estate_projection({"id": 1, "estate_room_number": "3F-1"})


@pytest.mark.req("face-exit-before-grounding:1")
def test_contract_required_fields_shape_matches_production(api):
    """production 一律列 16 欄（`all_filled` 為真時亦然）；舊 mock 的 `fields: []` 產不出來。"""
    crf = _run(api.get_estate_detail(estate_id=OPEN_IDS[0]))["data"][0]["contract_required_fields"]
    assert crf["all_filled"] is True and len(crf["fields"]) == 16
    assert set(crf["fields"][0]) == {"field", "label", "is_filled"}
    missing = build_contract_required_fields(("rent", "size"))
    assert missing["all_filled"] is False
    assert [f["label"] for f in missing["fields"] if not f["is_filled"]] == ["面積", "租金"]


# ── get_estate_status 與 get_estates 共用同一份事實 ──────────────────────

@pytest.mark.req("face-exit-before-grounding:1")
def test_estate_status_mock_shares_the_same_visible_set(api):
    """⚠️ 同 `test_only_published_estates_are_visible`：不再斷言封閉集合。"""
    rows = _run(api.get_estate_status(role_id=ROLE))["data"]
    ids = {e["id"] for e in rows}
    assert set(OPEN_IDS) <= ids
    assert set(REAL_OPEN_IDS) <= ids
    assert all("status_zh" in e for e in rows)


@pytest.mark.req("face-exit-before-grounding:1")
def test_estate_status_sentinel_now_reachable_in_mock(api):
    """舊版寫死一列 → 永遠有結果；sentinel（found:False）在替身上測不到。"""
    rows = _run(api.get_estate_status(role_id=ROLE, keyword="不存在的物件"))["data"]
    assert rows == [{"found": False, "keyword": "不存在的物件"}]


@pytest.mark.req("face-exit-before-grounding:1")
def test_accessor_shaped_empty_values(api):
    """空值形狀由 **Model accessor** 決定，不是欄位本身——控制器只是最後一層。

    `getFacilitiesAttribute`／`getFeesAttribute`（Estate.php:325／:339）空值回 `[]`，
    **永遠不是 null**；而 `gallery`／`floor_plan` 由 controller `formatGallery()` 收尾，
    空值回 **null**（:429-432）。兩者方向相反，是這一層最容易抄錯的地方。
    """
    # ⚠️ 真資料子集併入後預設排序（updated_at desc）可能把真實列排到 [0]，
    # 真實列的 facilities/fees 反映實際擷取值（非空）——故改指定合成列（456）驗，
    # 不再取 [0]（原意是「任一同型列皆可」，合成列即該同型代表）。
    rows = _run(api.get_estates(role_id=ROLE))["data"]
    row = next(e for e in rows if e["id"] == 456)
    assert row["facilities"] == [] and row["fees"] == []
    assert row["gallery"] is None and row["floor_plan"] is None


@pytest.mark.req("face-exit-before-grounding:1")
def test_uncast_json_columns_stay_strings(api):
    """沒有 accessor、也不在 `$casts` 裡的 JSON 欄位，API 回的是**原始字串**。

    `size_data`（Estate.php:1803 json_encode 寫入）與 `labels_fees`（:1890）都是這種；
    `$casts`（:120-127）只宣告 mrt／big_landlords／label_ids／agent_user_ids／
    building_registration_transcript。fixture 首版把 size_data 寫成巢狀 dict——
    任何 `row["size_data"]["size"]` 的消費端在 production 都會炸。
    """
    import json as _json
    rows = _run(api.get_estates(role_id=ROLE))["data"]
    row = next(e for e in rows if e["id"] == 54126)      # 預設排序是 updated_at desc，不能取 [0]
    assert isinstance(row["size_data"], str)
    assert _json.loads(row["size_data"])["size"]["m2"] == 15
    assert isinstance(row["labels_fees"], str)


@pytest.mark.req("face-exit-before-grounding:1")
def test_fixture_rows_declare_the_closed_case():
    """⚠️ 真資料子集併入後總筆數不再固定為 5——改驗「已刊登筆數 = 全部筆數 - 1」
    （54305 是唯一 is_open=0 的列，這才是本測試原本要鎖的性質：關閉個案存在且被排除）。
    """
    table = EstateFixtureTable()
    assert len(table.rows()) == len(table.visible_rows()) + 1
    assert table.by_id(CLOSED_ID) is None
    assert set(OPEN_IDS) <= {r["id"] for r in table.visible_rows()}
    assert set(REAL_OPEN_IDS) <= {r["id"] for r in table.visible_rows()}
