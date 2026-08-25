"""物件 fixture 表（transport-migration-inventory §8 第 4 項：estates 端點盤查）。

**保真度：已對照 jgb2 原始碼**（2026-08-25）——
`jgb2/app/Http/Controllers/External/EstateApiController.php` 的
`formatEstate()` 逐鍵、`index()` 的恆定 where、`applyFilters()` 的參數語義。
資料值沿用原方法級 mock `_mock_get_estates`，使遷移對既有呼叫點為行為保持，
但**移除了投影外欄位** `estate_room_number`（那是 `/repairs` 的欄位，
`RepairApiController.php:323`，`/estates` 從來不回它）。

⚠️ 全部為合成資料，不含任何真實個資。
"""

from typing import Any, Optional

# ⚠️ **值的形狀由三層決定，控制器只是最後一層**：
#    ① DDL（型別／nullable／預設）② Eloquent $casts ③ Model accessor。
#    `formatEstate()` 多數欄位是 `$estate->x` 直通，故 accessor 會改寫真正輸出：
#      · `getFacilitiesAttribute`／`getFeesAttribute`（Estate.php:325／:339）
#        **空值回 `[]`，永遠不是 null** → 本表兩欄用 `[]`（首版誤用 None）
#      · `getRentAttribute`（:506）空值回 0；設了 trans_currency_to 時回**千分位字串**
#      · `getCountryAttribute`（:224）回 `Address::getCountryKey(country_id)` 而非原欄位值
#      · `gallery`／`floor_plan` 由 controller `formatGallery()` 收尾，**空值回 null**（:429-432）
#    ⚠️ 仍未證：DDL 層（型別、nullable、預設）與 `Address` 對照表——見 estates-source-audit.md
#: External 投影（`formatEstate()` 逐鍵；`include_relations=False` 的列表形狀）
EXTERNAL_ESTATE_FIELDS: "frozenset[str]" = frozenset({
    "id", "url", "user_id", "role_id", "role_id_comment", "team_id", "team_id_comment",
    "team_name", "team_name_comment", "serial_id", "title", "status",
    "country", "country_id", "city", "city_id", "district", "district_id",
    "address", "full_address", "display_address", "full_display_address",
    "latitude", "longitude",
    "use_for", "space_type", "building", "room_count", "size", "size_data",
    "direction", "floor", "total_floor",
    "rent", "currency", "deposit", "deposit_type", "deposit_amount",
    "fees", "management_fee", "facilities", "labels_fees",
    "avatar", "gallery", "floor_plan", "vr_url",
    "community_id", "community_name", "property_purpose_key", "bit_status",
    "created_at", "updated_at",
})

#: **只有單筆詳情**（`show` → `formatEstate($estate, true)`）才會多出來的鍵
DETAIL_ONLY_FIELDS: "frozenset[str]" = frozenset({
    "description", "traffic", "nearby", "notes", "contract_required_fields",
})

#: **內部欄位**：`index()`／`show()` 恆定 where 用得到（`active=1`、`is_open=1`），
#: 但 `formatEstate()` **不投影**——與 contracts 的 `to_user_id` 同款。
INTERNAL_ESTATE_FIELDS: "frozenset[str]" = frozenset({"active", "is_open"})

#: `applyFilters()` 的排序白名單（:60-66）；不在其中一律回退 `updated_at`
ALLOWED_SORT_FIELDS: "frozenset[str]" = frozenset({
    "id", "created_at", "updated_at", "rent", "size",
})

DEFAULT_PER_PAGE = 50      # EstateApiController::DEFAULT_PER_PAGE
MAX_PER_PAGE = 200         # EstateApiController::MAX_PER_PAGE


class ForeignEstateFieldError(ValueError):
    """fixture 出現投影不存在的欄位（契約保真失效）。"""


def assert_estate_projection(record: "dict[str, Any]") -> None:
    foreign = (set(record) - EXTERNAL_ESTATE_FIELDS
               - INTERNAL_ESTATE_FIELDS - DETAIL_ONLY_FIELDS)
    if foreign:
        raise ForeignEstateFieldError(f"物件 fixture 含投影外欄位：{sorted(foreign)}")


def project_estate(record: "dict[str, Any]") -> "dict[str, Any]":
    """輸出投影：剝掉內部欄位，使回應與 `formatEstate()` 的鍵集一致。"""
    return {k: v for k, v in record.items() if k not in INTERNAL_ESTATE_FIELDS}


#: `formatContractRequiredFields()` 的欄位順序與標籤（:299-345）——
#: basicFields ＋ addressFields ＋ displayAddressFields（有城市層級的國家版本）
CONTRACT_REQUIRED_FIELD_LABELS: "tuple[tuple[str, str], ...]" = (
    ("use_for", "用途"), ("space_type", "格局"), ("building", "建築類型"),
    ("floor", "所在樓層"), ("floor_all", "總樓層"), ("title", "物件標題"),
    ("size", "面積"), ("rent", "租金"),
    ("country_id", "國家"), ("city_id", "城市"), ("district_id", "區域"),
    ("address", "地址"),
    ("display_country_id", "顯示國家"), ("display_city_id", "顯示城市"),
    ("display_district_id", "顯示區域"), ("display_address", "顯示地址"),
)


def build_contract_required_fields(
    fail_fields: "tuple[str, ...]" = (),
) -> "dict[str, Any]":
    """照抄 `formatContractRequiredFields()` 的輸出形狀。

    ⚠️ production **一律列出全部 16 個欄位**（`all_filled` 為真時亦然），
    `all_filled = empty(fail_fields)`。舊 mock 回 `{"all_filled": True, "fields": []}`
    ——那個空 `fields` 是 production 產不出來的形狀。
    """
    return {
        "all_filled": not fail_fields,
        "fields": [
            {"field": f, "label": label, "is_filled": f not in fail_fields}
            for f, label in CONTRACT_REQUIRED_FIELD_LABELS
        ],
    }


class EstateFixtureTable:
    """可依 **request 參數**收斂的物件資料集。

    差異矩陣（刻意）：三列的 `id`／`title`／`district`／`rent`／`size`／
    `updated_at` 皆不同；且 **54305 的 `is_open=0`**——
    production 的 `index()`／`show()` 都硬過濾 `is_open=1`，
    故它**查不到**。少了這一列，「查無＝非刊登中」那條 sentinel 口徑
    在替身上永遠不會被走到。
    """

    _ROWS: "tuple[dict[str, Any], ...]" = (
        {
            "id": 54126,
            "active": 1,
            "is_open": 1,
            "url": "https://www.jgbsmart.com/house/AABBCC?living=1",
            "user_id": 1001,
            "role_id": 20151,
            "role_id_comment": "房東編號",
            "team_id": 20151,
            "team_id_comment": "團隊編號（同 role_id）",
            "team_name": "好租管理",
            "team_name_comment": "物件歸屬",
            "serial_id": None,
            "title": "信義區精緻套房",
            "status": 2,
            "country": "TW",
            "country_id": 1,
            "city": "台北市",
            "city_id": 2,
            "district": "信義區",
            "district_id": 10,
            "address": "信義路五段7號",
            "full_address": "台北市信義區信義路五段7號3樓",
            "display_address": "信義路五段7號",
            "full_display_address": "台北市信義區信義路五段7號3樓",
            "latitude": "25.03360000",
            "longitude": "121.56480000",
            "use_for": "residential",
            "space_type": "flat",
            "building": "condo",
            "room_count": 1,
            "size": 15,
            "size_data": {"size": {"m2": 15, "sqm": 4.54, "sq_ft": 161.46}},
            "direction": "south",
            "floor": "3",
            "total_floor": "12",
            "rent": 25000,
            "currency": "TWD",
            "deposit": 2,
            "deposit_type": 0,
            "deposit_amount": 50000,
            "fees": [],
            "management_fee": 0,
            "facilities": [],
            "labels_fees": None,
            "avatar": None,
            "gallery": None,
            "floor_plan": None,
            "vr_url": None,
            "community_id": None,
            "community_name": None,
            "property_purpose_key": 1,
            "bit_status": 1026,
            "created_at": "2025-01-15 10:30:00",
            "updated_at": "2025-03-20 14:25:00",
        },
        {
            "id": 54200,
            "active": 1,
            "is_open": 1,
            "url": "https://www.jgbsmart.com/house/DDEEFF?living=1",
            "user_id": 1001,
            "role_id": 20151,
            "role_id_comment": "房東編號",
            "team_id": 20151,
            "team_id_comment": "團隊編號（同 role_id）",
            "team_name": "好租管理",
            "team_name_comment": "物件歸屬",
            "serial_id": None,
            "title": "中山區溫馨雅房",
            "status": 2,
            "country": "TW",
            "country_id": 1,
            "city": "台北市",
            "city_id": 2,
            "district": "中山區",
            "district_id": 4,
            "address": "中山北路二段10號",
            "full_address": "台北市中山區中山北路二段10號5樓",
            "display_address": "中山北路二段10號",
            "full_display_address": "台北市中山區中山北路二段10號5樓",
            "latitude": "25.06120000",
            "longitude": "121.52250000",
            "use_for": "residential",
            "space_type": "flat",
            "building": "apartment",
            "room_count": 1,
            "size": 8,
            "size_data": {"size": {"m2": 8, "sqm": 2.42, "sq_ft": 86.11}},
            "direction": "east",
            "floor": "5",
            "total_floor": "7",
            "rent": 12000,
            "currency": "TWD",
            "deposit": 2,
            "deposit_type": 0,
            "deposit_amount": 24000,
            "fees": [],
            "management_fee": 0,
            "facilities": [],
            "labels_fees": None,
            "avatar": None,
            "gallery": None,
            "floor_plan": None,
            "vr_url": None,
            "community_id": None,
            "community_name": None,
            "property_purpose_key": 1,
            "bit_status": 1026,
            "created_at": "2025-02-01 09:00:00",
            "updated_at": "2025-04-10 11:00:00",
        },
        {
            "id": 54305,
            "active": 1,
            "is_open": 0,
            "url": "https://www.jgbsmart.com/house/GGHHII?living=1",
            "user_id": 1001,
            "role_id": 20151,
            "role_id_comment": "房東編號",
            "team_id": 20151,
            "team_id_comment": "團隊編號（同 role_id）",
            "team_name": "好租管理",
            "team_name_comment": "物件歸屬",
            "serial_id": None,
            "title": "大安區景觀兩房",
            "status": 2,
            "country": "TW",
            "country_id": 1,
            "city": "台北市",
            "city_id": 2,
            "district": "大安區",
            "district_id": 6,
            "address": "敦化南路一段100號",
            "full_address": "台北市大安區敦化南路一段100號12樓",
            "display_address": "敦化南路一段100號",
            "full_display_address": "台北市大安區敦化南路一段100號12樓",
            "latitude": "25.04210000",
            "longitude": "121.54920000",
            "use_for": "residential",
            "space_type": "flat",
            "building": "condo",
            "room_count": 2,
            "size": 25,
            "size_data": {"size": {"m2": 25, "sqm": 7.56, "sq_ft": 269.1}},
            "direction": "west",
            "floor": "12",
            "total_floor": "15",
            "rent": 35000,
            "currency": "TWD",
            "deposit": 2,
            "deposit_type": 0,
            "deposit_amount": 70000,
            "fees": [],
            "management_fee": 2000,
            "facilities": [],
            "labels_fees": None,
            "avatar": None,
            "gallery": None,
            "floor_plan": None,
            "vr_url": None,
            "community_id": None,
            "community_name": None,
            "property_purpose_key": 1,
            "bit_status": 1026,
            "created_at": "2025-03-10 14:00:00",
            "updated_at": "2025-05-01 16:30:00",
        },
    )

    def __init__(self) -> None:
        for row in self._ROWS:
            assert_estate_projection(row)

    def rows(self) -> "list[dict[str, Any]]":
        return [dict(r) for r in self._ROWS]

    def visible_rows(self) -> "list[dict[str, Any]]":
        """`index()`／`show()` 的恆定 where：`active=1` 且 `is_open=1`（:52-53、:121-124）。"""
        return [r for r in self.rows() if r.get("active") == 1 and r.get("is_open") == 1]

    def by_id(self, estate_id: int) -> Optional["dict[str, Any]"]:
        """`show()` 語義：不在 `active=1 且 is_open=1` 之內就是 404。"""
        for row in self.visible_rows():
            if row["id"] == estate_id:
                return row
        return None
