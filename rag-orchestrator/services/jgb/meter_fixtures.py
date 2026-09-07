"""電表 fixture 表（transport-extension-full-coverage：meters 遷入 `JGBMockTransport`）。

資料來源：`services/jgb/fixture_data/demo_vendor4.json`（唯一來源）——
三列刻意涵蓋 production 的兩個衍生規則（`MeterApiController:152-172`）：

* `meter_type` = manufacturer ∈ {Miezo, DAE, SkyWatch} ? cloud : manual；
* `is_poweron` 三態：-1（從未連線）→ **null**，0/1 → false/true——
  501/502/503 分別覆蓋 true／null／false 三態。

⚠️ 全部為合成資料，不含任何真實個資。
"""

from typing import Any, Optional

from services.jgb.fixture_store import demo_rows

#: `formatMeter()` 逐鍵 15 欄（`MeterApiController:152-172`）。
EXTERNAL_METER_FIELDS: "frozenset[str]" = frozenset({
    "id", "estate_id", "estate_name", "name", "manufacturer", "meter_type",
    "is_online", "is_topup", "enable_topup", "balance", "available_meter",
    "current_reading", "is_poweron", "is_low_battery", "synced_at",
})


class ForeignMeterFieldError(ValueError):
    """fixture 出現投影不存在的欄位（契約保真失效）。"""


def assert_meter_projection(record: "dict[str, Any]") -> None:
    foreign = set(record) - EXTERNAL_METER_FIELDS
    if foreign:
        raise ForeignMeterFieldError(f"電表 fixture 含投影外欄位：{sorted(foreign)}")


class MeterFixtureTable:
    """可依 `estate_id`／`keyword` 收斂的電表資料集。"""

    def __init__(self) -> None:
        self._rows: "list[dict[str, Any]]" = list(demo_rows("meters"))
        for row in self._rows:
            assert_meter_projection(row)

    def rows(self) -> "list[dict[str, Any]]":
        return [dict(r) for r in self._rows]

    def by_id(self, meter_id: int) -> Optional["dict[str, Any]"]:
        for row in self._rows:
            if row["id"] == meter_id:
                return dict(row)
        return None
