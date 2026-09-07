"""帳單 fixture 表（spec conversational-routing-execution 任務 4.4，R4.1／R4.2）。

**定位**：建立 deterministic synthetic API state，**不是**「方便讓測試過」的 response dictionary。
故欄位一律為 External API 的**實際投影**，資料差異一律**足以咬到後續過濾**。

契約基準：jgb2 `app/Http/Controllers/External/BillApiController.php:130-167`（`formatBill`）——
該方法的輸出鍵即 External 白名單投影。
⚠️ **不得新增真 API 不存在的欄位**；jgb2 演進導致不符時，**先重盤 research.md 主題 7 再改本檔**。

⚠️ 全部為合成資料，**不含任何真實個資**（見 design.md「安全性設計」）。
"""

from typing import Any, Optional, TypedDict

from services.jgb.fixture_store import demo_rows, demo_visibility

#: External 白名單投影（`formatBill` 逐鍵，33 欄）。
#: ⚠️ `archive_at` **不在**投影內——真 API 輸出的是衍生的 `is_archived`（:163）。
EXTERNAL_BILL_FIELDS: "frozenset[str]" = frozenset({
    "id", "contract_id", "estate_id", "type", "category", "status", "bit_status",
    "title", "sub_title", "currency", "total", "final_total", "rate",
    "date_start", "date_end", "date_expire", "date_expire_note", "cycle", "days",
    "is_auto_pay", "is_paid_on_time", "online_payment_method", "online_payment_action",
    "payment_id", "invoice_status", "invoice_number",
    "ready_at", "pay_at", "complete_at", "is_archived", "archive_ymd",
    "created_at", "updated_at",
})


class BillFixture(TypedDict, total=False):
    """單筆帳單的測試事實；鍵為 `EXTERNAL_BILL_FIELDS` 的子集。"""
    id: int
    contract_id: int
    estate_id: int
    type: int
    category: int
    status: int
    bit_status: int
    title: str
    sub_title: str
    currency: str
    total: float
    final_total: float
    rate: float
    date_start: int
    date_end: int
    date_expire: int          # YYYYMMDD 整數
    date_expire_note: Optional[str]
    cycle: Optional[int]
    days: Optional[int]
    is_auto_pay: bool
    is_paid_on_time: Optional[int]
    online_payment_method: Optional[str]
    online_payment_action: Optional[str]
    payment_id: Optional[int]
    invoice_status: int
    invoice_number: Optional[str]
    ready_at: Optional[str]
    pay_at: Optional[str]
    complete_at: Optional[str]
    is_archived: bool
    archive_ymd: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]


class ForeignFixtureFieldError(ValueError):
    """fixture 出現 External 投影不存在的欄位。

    ⚠️ 這是**契約保真失效**：mock 若能回傳真 API 沒有的欄位，
    上層就能在測試中依賴一個 production 永遠拿不到的值。
    """


def assert_external_projection(record: "dict[str, Any]") -> None:
    """機器檢查：`record` 的鍵必須是 External 白名單投影的子集。

    ⚠️ 刻意寫成可被測試直接呼叫的函式——白名單若只靠 code review 肉眼確認，
    就會變成「whitelist exists ≠ whitelist can bite」。
    """
    foreign = set(record) - EXTERNAL_BILL_FIELDS
    if foreign:
        raise ForeignFixtureFieldError(
            f"fixture 含 External 投影不存在的欄位：{sorted(foreign)}"
        )


def _bill(**overrides: Any) -> BillFixture:
    """以 External 投影的完整鍵集建一筆，再套 overrides（避免各筆漏鍵不一致）。"""
    base: "dict[str, Any]" = {
        "id": 0, "contract_id": 0, "estate_id": 0, "type": 1, "category": 3,
        "status": 1, "bit_status": 1, "title": "", "sub_title": "",
        "currency": "TWD", "total": 0.0, "final_total": 0.0, "rate": 1.0,
        "date_start": 20260801, "date_end": 20260831, "date_expire": 20260815,
        "date_expire_note": None, "cycle": 1, "days": 31,
        "is_auto_pay": False, "is_paid_on_time": None,
        "online_payment_method": None, "online_payment_action": None,
        "payment_id": None, "invoice_status": 0, "invoice_number": None,
        "ready_at": None, "pay_at": None, "complete_at": None,
        "is_archived": False, "archive_ymd": None,
        "created_at": "2026-08-01 09:00:00", "updated_at": "2026-08-01 09:00:00",
    }
    base.update(overrides)
    assert_external_projection(base)
    return base  # type: ignore[return-value]


class BillFixtureTable:
    """多筆、可依 `bill_id` 收斂到唯一列的**可變**資料集（R4.2；transport-extension-full-coverage 起可寫）。

    資料來源：`services/jgb/fixture_data/demo_vendor4.json`（唯一來源，見 `fixture_store`）——
    本類**不再**硬編碼列值，只負責投影守衛、identity 存取與寫入語義。

    **差異矩陣**（fixture 檔刻意設計，使複合過濾可觀測）：

    ==========  ============  ============  ================  ============
    bill_id     contract_id   bit_status    invoice_status    date_expire
    ==========  ============  ============  ================  ============
    900001      678           3             0                 20260815
    900002      678           19            1                 20260915
    900003      600           3             1                 20260915
    ==========  ============  ============  ================  ============

    ⚠️ `contract_id` **跨域連貫修正（2026-09-08）後**指向既有 `ContractFixtureTable`
    的真實 id（678／600，非孤立合成值）——使帳單／合約／物件三個 fixture 宇宙相連
    （見 `fixture_data/demo_vendor4.json` 頂端註解）。

    ⚠️ **每一對只共用一個維度**：900001／900002 同 contract、900001／900003 同 bit_status、
    900002／900003 同 invoice_status 與同月。
    因此**任何單一過濾條件都無法複製另一條件的結果集**——
    若 4.5 的 `contract_id`／`status`／`invoice`／`month` 任一寫錯，集合就會不同。
    （若三筆只有 id 不同，過濾寫錯也會剛好得到相同集合，那種 fixture 驗不出東西。）

    ⚠️ **identity 靠 `bill_id`，不靠 list position**——
    `by_id()` 是唯一的取用方式，日後加第四筆不會改變既有測試的語義。

    ⚠️ **每個實例各自持有一份可變列表**（`self._rows`）：`by_id()` 回傳的是該實例內部的
    dict 參照，就地修改（PATCH 用）會被後續 `rows()`／`by_id()` 看見——這是刻意設計，
    使「寫入後的讀反映」不需要額外的同步機制；但也代表**不得**跨實例共用同一個
    `BillFixtureTable`，否則一個 transport 的寫入會外溢到另一個。
    """

    def __init__(self) -> None:
        self._rows: "list[BillFixture]" = [
            _bill(**row) for row in demo_rows("bills")
        ]
        #: `{str(bill_id): [user_id, ...]}`——缺 key＝未宣告，見 `visible_to()`。
        self._visibility: "dict[str, list[int]]" = demo_visibility("bill")

    def rows(self) -> "list[BillFixture]":
        return list(self._rows)

    def by_id(self, bill_id: int) -> Optional[BillFixture]:
        for row in self._rows:
            if row["id"] == bill_id:
                return row
        return None

    def visible_to(self, bill_id: int) -> Optional["list[int]"]:
        """回傳這筆帳單宣告的可見 user_id 清單；**未宣告**回 `None`（非空清單）。

        呼叫端必須能區分「未宣告」（`None`，替身不可信地回答可見性）與
        「宣告為空清單」（`[]`，明確宣告誰都看不到）——兩者是不同事實。
        """
        return self._visibility.get(str(bill_id))

    def create(self, overrides: "dict[str, Any]") -> BillFixture:
        """寫入路徑（`POST /agent/v1/bills`）：以 `_bill()` 補滿預設欄位後附加一筆。

        回傳的是**存入 `self._rows` 的同一個 dict 參照**，供呼叫端立刻取用新列
        （例如 receipt 需要的 `created_at`），且該參照的後續就地修改
        （PATCH）仍會反映在 `rows()`／`by_id()`。
        """
        row = _bill(**overrides)
        self._rows.append(row)
        return row
