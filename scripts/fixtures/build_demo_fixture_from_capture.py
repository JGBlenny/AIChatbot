#!/usr/bin/env python3
"""從一次真實 jgb2 API 擷取（role_id=20151／user_id=12291）建立可用於 demo 的
「真資料子集」，遮罩 PII 後合併進 ``services/jgb/fixture_data/demo_vendor4.json``。

**設計原則**（見任務契約，2026-09-08）：
* 既有合成列（bills 900001-900003／contracts 678,600／estates 456,400／
  meters 601／repairs 3001,3002／team_members 等）原樣保留，**值與 id 都不動**——
  13 個凍結回歸測試引用它們。
* 這些合成列對 demo 使用者 12291 改為不可見（從 *_visibility 拿掉 12291，
  保留既有的 100／9001／9002 等宣告）。
* 真資料子集以另一組 id（皆為真實擷取值）附加進同一批列表，可見性只含 12291。

**選取的連貫子集**（人工核對，見 SOURCE_NOTES）：
* 4 個物件為軸（各有合約＋帳單）：68926／67649／67651／67652（皆基隆/信義區真實物件），
  67652 另有一張真實「處理中」修繕單（8591）。
* 第 5 個物件 45728（台北中正-小南門）不掛合約／帳單，只承載真實電錶（1061，有餘額）
  與真實「完成修繕」修繕單（7628）——真實 API 擷取中，電錶／修繕的物件集合與
  帳單／合約的物件集合彼此不相交（兩支端點各自分頁擷取，樣本未重疊），
  這是本次擷取的真實限制，不是遮罩造成的。
* contracts（89481／85894／84921／88247）**在擷取樣本中查無同 id 的合約列**
  （bills 端點回的 contract_id 不在 contracts 端點回的 50 筆合約樣本裡，兩支端點
  分頁擷取、樣本不相交）——故合約列由「真實 estate 欄位（title／地址／rent／
  deposit）＋合理預設值」建構，非逐鍵真實合約記錄；來源標記見 SOURCE_NOTES。
  其中 89481（68926）的 date_end 刻意落在今天起 90–150 天內，滿足受測情境需求。

**遮罩規則**：
* 電話 → 同一原始值一致對應 ``09NN-000-0NN``（依首次出現順序編號）。
* email → 同一原始值一致對應 ``user{N}@example.com``。
* 姓名欄（``to_user_name``／``agent_name``／``user_name``…）→ 合成中文名，同一原始值一致。
* 地址：保留縣市＋區，門牌／樓層改為同一原始地址一致的合成值。
* 緯度／經度／avatar／gallery／floor_plan／vr_url／broken_photos → 刪除或清空。
* 身分證／統一編號 → 本次擷取的 bills／contracts／estates／meters／repairs 皆無此欄位，
  無需遮罩（若未來擷取含此欄位，需在此腳本補規則後才可使用）。

**PII 驗證**：遮罩前先用同一組規則從「原始擷取檔」抽出電話／email／經緯度候選值，
寫檔前確認這些候選值**逐字**不再出現於最終合併檔的文字中，0 命中才寫檔——
不是「輸出裡沒有像電話的字串」（我們自己合成的佔位值本來就長得像電話／email），
而是「原始真實值不再出現」。

用法：
    python3 scripts/fixtures/build_demo_fixture_from_capture.py \\
        --capture /path/to/raw_20151_12291.json \\
        --fixture rag-orchestrator/services/jgb/fixture_data/demo_vendor4.json \\
        [--dry-run]
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any


# ── 選取的真實 id（人工核對，見模組 docstring）───────────────────────────────

AXIS_ESTATE_IDS = [68926, 67649, 67651, 67652]
METER_ONLY_ESTATE_ID = 45728
ALL_ESTATE_IDS = AXIS_ESTATE_IDS + [METER_ONLY_ESTATE_ID]

# estate_id -> 建構合約 id（真實 bills 的 contract_id，但合約端點樣本未擷到同 id 列）
ESTATE_TO_CONTRACT_ID = {
    68926: 89481,
    67649: 85894,
    67651: 84921,
    67652: 88247,
}

SELECTED_BILL_IDS = [
    769258, 769246, 769249,   # 68926／contract 89481：未到期待發送、已繳費、近期待發送
    756248, 756242,           # 67649／contract 85894：逾期待繳費、已繳費
    727606,                   # 67651／contract 84921：已繳費（點退結算）
    750524,                   # 67652／contract 88247：未到期待發送
]

SELECTED_REPAIR_IDS = [8591, 7628]   # 67652 處理中／45728 完成修繕
SELECTED_METER_IDS = [1061]          # 45728：有餘額

VENDOR_ROLE_ID = 20151
DEMO_USER_ID = 12291

# 合約 89481 的到期日：刻意落在「今天」起 90–150 天內（受測情境要求）。
CONTRACT_DATE_END_IN_WINDOW = 20261215


# ── PII 遮罩：一致性對應表 ───────────────────────────────────────────────────

_PHONE_RE = re.compile(r"09\d{8}|09\d{2}-\d{3}-\d{3}|0\d{1,2}-\d{4}-\d{4}")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_TWID_RE = re.compile(r"\b[A-Z][12]\d{8}\b")

_SURNAMES = ["陳", "林", "黃", "張", "李", "王", "吳", "劉", "蔡", "楊"]
_GIVEN = ["志明", "淑芬", "怡君", "俊傑", "美玲", "建宏", "雅婷", "冠宇", "佳蓉", "彥廷"]


class _ConsistentMasker:
    """依「原始值」一致對應到同一個合成值（同一輪腳本執行內、依首次出現順序編號）。"""

    def __init__(self, template: "callable[[int], str]") -> None:
        self._template = template
        self._map: "dict[str, str]" = {}

    def mask(self, original: "str | None") -> "str | None":
        if not original:
            return original
        if original not in self._map:
            self._map[original] = self._template(len(self._map) + 1)
        return self._map[original]


_phone_masker = _ConsistentMasker(lambda n: f"09{n:02d}-000-0{n:02d}")
_email_masker = _ConsistentMasker(lambda n: f"user{n}@example.com")
_name_masker = _ConsistentMasker(
    lambda n: _SURNAMES[(n - 1) % len(_SURNAMES)] + _GIVEN[(n - 1) % len(_GIVEN)]
)


def _split_city_district(full_address: "str | None") -> "tuple[str, str, str]":
    """從真實 full_address（如「TW基隆市中正區中正一路256號」）拆出 (縣市, 區, 其餘門牌)。"""
    s = (full_address or "").lstrip("TW")
    m = re.match(r"(.{2,3}[市縣])(.{1,3}[區鄉鎮市])(.*)", s)
    if not m:
        return "台北市", "信義區", s
    return m.group(1), m.group(2), m.group(3)


_addr_door_masker = _ConsistentMasker(lambda n: f"合成路{n}段{n * 10}號")
_addr_floor_masker = _ConsistentMasker(lambda n: f"{n}樓")


def mask_address(full_address: "str | None") -> "dict[str, str]":
    """保留縣市＋區，門牌／樓層改為同一原始地址一致的合成值。"""
    city, district, _rest = _split_city_district(full_address)
    key = f"{city}{district}"  # 同一縣市區視為同一棟樓 → 合成同一門牌
    door = _addr_door_masker.mask(key)
    floor = _addr_floor_masker.mask(key)
    return {
        "city": city, "district": district,
        "address": door, "full_address": f"{city}{district}{door}",
        "display_address": door, "full_display_address": f"{city}{district}{door}",
        "floor": floor,
    }


#: 地址門牌 token（巷／弄／號／樓／之）——標題、備註、地址欄裡的門牌都要遮。
_DOOR_TOKEN_RE = re.compile(r"(?:\d+巷)?(?:\d+弄)?\d+(?:-\d+)?號(?:\d+樓)?(?:之\d+)?(?:[A-Za-z0-9]+室)?")
#: 「路名＋門牌」整段（個資閘用：原始值逐字不得再出現）。
_ADDR_SPAN_RE = re.compile(r"[\u4e00-\u9fff]{1,8}(?:路|街|大道|巷|弄)[\u4e00-\u9fff0-9]{0,12}?\d+(?:-\d+)?號(?:\d+樓)?(?:之\d+)?")


def redact_door_tokens(text: "str | None") -> "str | None":
    """把字串裡的門牌 token（123號4樓之2 …）換成一致的合成門牌（同一 token 同一值）。
    用於標題（物件名常含門牌）與備註；縣市／路名保留，只動門牌。"""
    if not text:
        return text
    return _DOOR_TOKEN_RE.sub(lambda m: _addr_door_masker.mask(m.group(0)), text)


def extract_pii_candidates(raw_text: str) -> "set[str]":
    """從原始擷取檔文字抽出電話／email／身分證候選值、非零經緯度字面值，
    以及**地址門牌段**（路名＋門牌；verifier 2026-09-08 F1：舊閘沒有地址類，
    修繕列的 `estate_full_address` 與合約列的 `address` 原值逐字出檔而閘仍綠）。"""
    candidates: "set[str]" = set(_PHONE_RE.findall(raw_text))
    candidates |= set(_ADDR_SPAN_RE.findall(raw_text))
    candidates |= set(_EMAIL_RE.findall(raw_text))
    candidates |= set(_TWID_RE.findall(raw_text))
    # 非零經緯度（"25.03767380" 這種字面值）——排除 "0.00000000" 這種未設值佔位。
    for m in re.finditer(r'"latitude":\s*"([^"0][^"]*)"', raw_text):
        candidates.add(m.group(1))
    for m in re.finditer(r'"longitude":\s*"([^"0][^"]*)"', raw_text):
        candidates.add(m.group(1))
    return candidates


# ── 從擷取檔建構各領域列 ─────────────────────────────────────────────────────

def _index_by_id(section: "dict[str, Any]") -> "dict[int, dict[str, Any]]":
    return {row["id"]: row for row in section["data"]}


def build_bills(capture: "dict[str, Any]") -> "list[dict[str, Any]]":
    bills_by_id = _index_by_id(capture["bills"])
    estates_by_id = _index_by_id(capture["estates"])
    out = []
    for bid in SELECTED_BILL_IDS:
        row = copy.deepcopy(bills_by_id[bid])
        # bills 投影無任何個資欄位（僅 title/sub_title 為物件標題與地址片語）；
        # sub_title 是 "TW"+full_address，換成遮罩後地址以維持一致（同一物件同一合成門牌）。
        masked_addr = mask_address(estates_by_id[row["estate_id"]]["full_address"])
        row["sub_title"] = "TW" + masked_addr["full_address"]
        out.append(row)
    return out


def build_contracts(capture: "dict[str, Any]") -> "list[dict[str, Any]]":
    estates_by_id = _index_by_id(capture["estates"])
    out = []
    for estate_id, contract_id in ESTATE_TO_CONTRACT_ID.items():
        e = estates_by_id[estate_id]
        masked = mask_address(e["full_address"])
        rent = e.get("rent") or 0
        deposit_months = e.get("deposit") or 1
        date_end = (CONTRACT_DATE_END_IN_WINDOW if contract_id == 89481 else 20270228)
        out.append({
            "id": contract_id,
            "status": 32, "bit_status": 63,        # 生效中（租客同意點交）——見模組說明
            "active": 1, "is_history": 0, "is_history_done": 0,
            "estate_id": estate_id,
            "title": e["title"],
            "city": masked["city"], "district": masked["district"],
            "address": masked["address"],
            "currency": e.get("currency", "TWD"),
            "rent": rent,
            "deposit_amount": rent * deposit_months,   # 推導值：估算，非真實合約欄位
            "date_start": 20260101, "date_end": date_end,
            "allow_early_termination": False, "early_termination_days": None,
            "is_auto_generate_invoice": 1,
            "to_user_connect": True, "is_tenant_registered": True,
            "to_user_phone": "", "to_user_email": "",   # 無真實合約列可查，不捏造聯絡方式
            "property_purpose_key": e.get("property_purpose_key", 1),
            "father_id": contract_id,
            "early_termination_wish_date_end": None,
            "enable_late_fee": 0, "calc_late_fee_buffer_days": 0, "late_fee_percent": 0.0,
            "early_termination_penalty_type": None, "early_termination_penalty": 0.0,
            "early_termination_penalty_amount": 0.0, "early_termination_notice_date": None,
            "contract_inviting_at": None, "contract_inviting_expire_at": None,
            "contract_inviting_sign_at": None, "contract_finish_sign_at": None,
            "to_user_login_email": None, "is_newest": 1,
            "created_at": "2026-01-01 09:00:00", "updated_at": "2026-08-01 09:00:00",
        })
    return out


def build_estates(capture: "dict[str, Any]") -> "list[dict[str, Any]]":
    by_id = _index_by_id(capture["estates"])
    out = []
    for eid in ALL_ESTATE_IDS:
        row = copy.deepcopy(by_id[eid])
        masked = mask_address(row.get("full_address"))
        row.update({
            "city": masked["city"], "district": masked["district"],
            "address": masked["address"], "full_address": masked["full_address"],
            "display_address": masked["address"],
            "full_display_address": masked["full_address"],
            "floor": masked["floor"],
            "latitude": "", "longitude": "",
            "avatar": None, "gallery": None, "floor_plan": None, "vr_url": None,
            # active/is_open：真實投影不含這兩個內部欄位，招租中假設，供 EstateFixtureTable
            # 的恆定 where（active=1 且 is_open=1）判可見。
            "active": 1, "is_open": 1,
        })
        out.append(row)
    return out


def build_meters(capture: "dict[str, Any]") -> "list[dict[str, Any]]":
    by_id = _index_by_id(capture["meters"])
    return [copy.deepcopy(by_id[mid]) for mid in SELECTED_METER_IDS]


def build_repairs(capture: "dict[str, Any]") -> "list[dict[str, Any]]":
    by_id = _index_by_id(capture["repairs"])
    estates_by_id = _index_by_id(capture["estates"])
    out = []
    for rid in SELECTED_REPAIR_IDS:
        row = copy.deepcopy(by_id[rid])
        masked = mask_address(estates_by_id[row["estate_id"]]["full_address"])
        row["estate_full_address"] = masked["full_address"]
        for phone_key in ("manufacturer_phone", "user_phone", "to_user_phone"):
            row[phone_key] = _phone_masker.mask(row.get(phone_key))
        for email_key in ("user_email", "to_user_email"):
            row[email_key] = _email_masker.mask(row.get(email_key))
        for name_key in ("user_name", "to_user_name", "agent_name", "manufacturer_name"):
            if row.get(name_key):
                row[name_key] = _name_masker.mask(row[name_key])
        row["broken_photos"] = []
        out.append(row)
    return out


def build_repair_categories(capture: "dict[str, Any]") -> "list[dict[str, Any]]":
    return copy.deepcopy(capture["repair_categories"]["data"])


# ── `--mode all`：整批真資料重建（2026-09-08「清掉測試資料」定案）───────────────
#
# 與上面「軸心＋合成鏈共存」的舊模式（`merge()`）不同：本模式**捨棄舊 fixture
# 全部內容**，只用這次擷取的每一筆真資料重建整份 JSON——不留任何合成列
# （bills 900001-3／contracts 678,600／estates 456,400,54126,54200,54305／
# meters 501,502,503,601／repairs 3001,3002／team_members 100,292,305／
# 0912345678／tenant@example.com 陷阱值），因為業主裁示「demo 用關鍵字查詢
# 會撈到同 role 的合成合約，狀態碼還是不合法的 5」——舊模式的「對 12291 隱藏
# 但仍在同一 role 資料集裡」不夠，必須整批不存在。
#
# 測試套件已改吃凍結的 `tests/fixtures/jgb/regression_vendor4.json`
# （`tests/conftest.py` 設 `JGB_MOCK_FIXTURE`），本檔的合成列搬過去，
# 故 demo 檔可以整份替換而不影響回歸測試。

#: `services/jgb/estate_fixtures.py::EXTERNAL_ESTATE_FIELDS ∪ INTERNAL_ESTATE_FIELDS`
#: 的本地副本（避免建置腳本 import `services.*` 造成 sys.path 依賴）——
#: 兩邊改動需同步，見該模組頂端的保真度聲明。
_ALL_ESTATE_FIELDS: "frozenset[str]" = frozenset({
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
    "active", "is_open",   # 內部欄位（`visible_rows()` 的恆定 where 用得到）
})

#: 已知合成鏈（舊 demo 檔／`regression_vendor4.json` 的凍結列）——`--mode all`
#: 重建後必須整批不在輸出裡，見上方模組說明。
_SYNTHETIC_TRAP_IDS: "dict[str, set[int]]" = {
    "bills": {900001, 900002, 900003},
    "contracts": {678, 600},
    "estates": {456, 400, 54126, 54200, 54305},
    "meters": {501, 502, 503, 601},
    "repairs": {3001, 3002},
}
_SYNTHETIC_TRAP_MEMBER_IDS: "set[int]" = {100, 292, 305}
_SYNTHETIC_TRAP_VALUES: "set[str]" = {"0912345678", "tenant@example.com"}


def build_all_bills(capture: "dict[str, Any]") -> "list[dict[str, Any]]":
    """全部 61 筆帳單，`sub_title` 依對應物件（真 46 筆或退回帳單自帶位址）遮罩。

    ⚠️ `--mode all` 的擷取檔頂層形狀與 `--mode legacy` 不同——`bills`／`estates`／
    `repairs`／`contracts_by_ids` 本身即為 list（非 `{"success","data"}` 外殼），
    故本組 `build_all_*` 函式一律直接對 list 取值，**不**沿用 `_index_by_id()`
    （那是為 legacy 擷取檔的 `{"data":[...]}` 外殼寫的）。"""
    estates_by_id = {e["id"]: e for e in capture["estates"]}
    out = []
    for row in copy.deepcopy(capture["bills"]):
        estate = estates_by_id.get(row.get("estate_id"))
        raw_addr = estate["full_address"] if estate else row.get("sub_title")
        masked_addr = mask_address(raw_addr)
        row["sub_title"] = "TW" + masked_addr["full_address"]
        out.append(row)
    return out


def build_all_contracts(capture: "dict[str, Any]") -> "list[dict[str, Any]]":
    """`contracts_by_ids` 的真實合約列（2026-09-09 起＝`status-overview` 以 `user_id` 圈定後、
    `estate_id` 落在本 role 物件集的列；8 → 27）——只遮罩 `to_user_*` 三個個資欄，
    其餘（含 `status`／`bit_status`／`date_start`／`date_end`／`estate_id`／
    `title`／`address`）原樣保留真實值。"""
    out = []
    for row in copy.deepcopy(capture["contracts_by_ids"]):
        row["to_user_phone"] = _phone_masker.mask(row.get("to_user_phone"))
        row["to_user_email"] = _email_masker.mask(row.get("to_user_email"))
        row["to_user_login_email"] = _email_masker.mask(row.get("to_user_login_email"))
        # 地址：保留縣市＋區、門牌合成（verifier F1：合約列 `address` 原值曾逐字出檔）
        masked = mask_address(row.get("address"))
        row["address"] = masked["full_address"]
        if "city" in row:
            row["city"] = masked["city"]
        if "district" in row:
            row["district"] = masked["district"]
        for key in ("title", "estate_title"):
            if row.get(key):
                row[key] = redact_door_tokens(row[key])
        out.append(row)
    return out


def build_all_estates(capture: "dict[str, Any]") -> "list[dict[str, Any]]":
    """46 筆真實物件（遮罩地址／清空經緯度與媒體欄）＋37 筆「僅被引用」最小列
    （bills／repairs／meters／contracts 提到、但擷取樣本裡查無同 id 物件列的
    estate_id——兩支端點各自分頁擷取，樣本未重疊，見模組 docstring）。

    最小列補滿 `_ALL_ESTATE_FIELDS` 全部鍵（多數為 `None`），使
    `EstateFixtureTable`／`project_estate()` 的投影守衛與下游存取都拿得到
    預期鍵；`status=2`／`bit_status=2`、`active=1`／`is_open=1` 對齊
    `build_estate_status_facts()` 的「刊登中」判斷（`status==2`）與
    `visible_rows()` 的恆定 where，使這些物件在替身裡可查得到、且判定為刊登中。
    """
    real_rows = []
    for row in copy.deepcopy(capture["estates"]):
        for key in ("title", "community_name", "building", "room_number"):
            if isinstance(row.get(key), str):
                row[key] = redact_door_tokens(row[key])   # 物件名可能含門牌（同 meters F3）
        masked = mask_address(row.get("full_address"))
        row.update({
            "city": masked["city"], "district": masked["district"],
            "address": masked["address"], "full_address": masked["full_address"],
            "display_address": masked["address"],
            "full_display_address": masked["full_address"],
            "floor": masked["floor"],
            "latitude": "", "longitude": "",
            "avatar": None, "gallery": None, "floor_plan": None, "vr_url": None,
            "active": 1, "is_open": 1,
        })
        real_rows.append(row)

    real_ids = {r["id"] for r in real_rows}
    bills_by_estate = {b["estate_id"]: b for b in capture["bills"]}
    repairs_by_estate: "dict[int, dict[str, Any]]" = {}
    for r in capture["repairs"]:
        eid = r.get("estate_id")
        if eid is not None and eid not in repairs_by_estate:
            repairs_by_estate[eid] = r
    meters_by_estate = {m["estate_id"]: m for m in capture["meters"]["data"]
                        if m.get("estate_id") is not None}
    referenced_ids = (set(bills_by_estate) | set(repairs_by_estate)
                      | set(meters_by_estate)
                      | {c["estate_id"] for c in capture["contracts_by_ids"]
                         if c.get("estate_id") is not None})
    missing_ids = sorted(referenced_ids - real_ids)

    stub_rows = []
    for eid in missing_ids:
        title = f"物件 {eid}"
        city = district = address = full_address = None
        if eid in bills_by_estate:
            b = bills_by_estate[eid]
            title = b.get("title") or title
            masked = mask_address(b.get("sub_title"))
            city, district = masked["city"], masked["district"]
            address, full_address = masked["address"], masked["full_address"]
        elif eid in repairs_by_estate:
            title = repairs_by_estate[eid].get("estate_title") or title
        elif eid in meters_by_estate:
            title = meters_by_estate[eid].get("estate_name") or title

        stub: "dict[str, Any]" = {k: None for k in sorted(_ALL_ESTATE_FIELDS)}   # 固定鍵序：重產可逐位元比對（verifier A1）
        stub.update({
            "id": eid, "title": redact_door_tokens(title),
            "role_id": VENDOR_ROLE_ID, "user_id": DEMO_USER_ID,
            "status": 2, "bit_status": 2, "currency": "TWD",
            "city": city, "district": district,
            "address": address, "full_address": full_address,
            "display_address": address, "full_display_address": full_address,
            "active": 1, "is_open": 1,
        })
        stub_rows.append(stub)

    return real_rows + stub_rows


def build_all_meters(capture: "dict[str, Any]") -> "list[dict[str, Any]]":
    """全部 7 顆電錶——無電話／email／座標欄，但**名稱欄可帶門牌**（verifier r2 F3：
    `estate_name` 出現「…/N號房」），所以名稱／地址類字串欄一律過 `redact_door_tokens`。"""
    out = []
    for row in copy.deepcopy(capture["meters"]["data"]):
        for key in ("estate_name", "name", "title", "address", "full_address", "room_number"):
            if isinstance(row.get(key), str):
                row[key] = redact_door_tokens(row[key])
        out.append(row)
    return out


def _redact_embedded_contacts(text: "str | None") -> "str | None":
    """自由文字欄位（如 `broken_note`）裡使用者自己打進去的電話／email——
    不是結構化欄位無法逐值一致遮罩，直接以字面樣式取代成占位字串。

    ⚠️ 本次擷取實測命中一筆（修繕單 6699 的 `broken_note` 含手打電話），
    這是 production 使用者行為，不是遮罩規則的假設之外——`build_repairs()`
    （軸心真資料子集）沒踩到純屬樣本沒抽到，非「自由文字不需要掃」的證據。
    """
    if not text:
        return text
    # ⚠️ 取代字串刻意**不**長得像電話／email（不用 09xx-xxx-xxx／user@example.com
    # 這種格式），否則會被下游「掃描全文找聯絡方式格式」的測試／稽核誤判成
    # 又一個需要對照白名單的命中，混淆真正的遮罩佔位值。
    text = _PHONE_RE.sub("（電話已遮罩）", text)
    text = _EMAIL_RE.sub("（email已遮罩）", text)
    return text


def build_all_repairs(capture: "dict[str, Any]") -> "list[dict[str, Any]]":
    """全部 119 張修繕單，遮罩規則與 `build_repairs()` 相同，
    另加自由文字欄位的埋藏聯絡方式清除（見 `_redact_embedded_contacts()`）。"""
    out = []
    for row in copy.deepcopy(capture["repairs"]):
        for phone_key in ("manufacturer_phone", "user_phone", "to_user_phone"):
            row[phone_key] = _phone_masker.mask(row.get(phone_key))
        for email_key in ("user_email", "to_user_email"):
            row[email_key] = _email_masker.mask(row.get(email_key))
        for name_key in ("user_name", "to_user_name", "agent_name", "manufacturer_name"):
            if row.get(name_key):
                row[name_key] = _name_masker.mask(row[name_key])
        for free_text_key in ("broken_note", "broken_reason", "user_note", "to_user_note"):
            row[free_text_key] = redact_door_tokens(_redact_embedded_contacts(row.get(free_text_key)))
        # 地址（verifier F1：119 列 `estate_full_address` 原值曾逐字出檔）
        masked = mask_address(row.get("estate_full_address"))
        row["estate_full_address"] = masked["full_address"]
        for key in ("estate_title", "estate_room_number"):
            if row.get(key):
                row[key] = redact_door_tokens(row[key])
        row["broken_photos"] = []
        out.append(row)
    return out


def build_all_team_members(capture: "dict[str, Any]") -> "list[dict[str, Any]]":
    """`member_permissions` 只回單一成員（12291 自己）——沒有其他真實成員可列，
    ⛔ 不補造。`email`／`name` 是內部展示欄，這支端點不回這兩鍵的真實值，
    無值可遮罩，留 `None`（非捏造）。"""
    rows = (capture.get("member_permissions") or {}).get("data") or []
    out = []
    for m in rows:
        character = m.get("character") or {}
        out.append({
            "member_user_id": m.get("user_id"),
            "character_id": character.get("id"),
            "character_name": character.get("name"),
            "is_owner": bool(m.get("is_owner")),
            "email": None,
            "name": None,
        })
    return out


def build_all_fixture(capture: "dict[str, Any]") -> "dict[str, Any]":
    """`--mode all`：整份真資料重建（不合併舊列，見模組說明）。"""
    bills = build_all_bills(capture)
    contracts = build_all_contracts(capture)
    estates = build_all_estates(capture)
    meters = build_all_meters(capture)
    repairs = build_all_repairs(capture)
    team_members = build_all_team_members(capture)
    repair_categories = build_repair_categories(capture)

    stub_count = len(estates) - len(capture["estates"])
    captured_ids = {e["id"] for e in capture["estates"]}
    estate_stubs = sorted(e["id"] for e in estates if e["id"] not in captured_ids)
    comment = (
        "vendor4 demo fixture（real-data-only，2026-09-08 重建，業主裁示「清掉測試資料 "
        "並 慢慢地抓取此團隊的資料」）——全部列皆為 role_id=20151/user_id=12291 團隊的"
        f"真實資料（擷取於 {capture.get('_meta', {}).get('captured_at', '?')}），PII 遮罩後、"
        "對 12291 全數可見；⛔ 不含任何合成/測試列（合成鏈已搬到 "
        "tests/fixtures/jgb/regression_vendor4.json，測試改吃那份，不吃本檔）。"
        f"counts：bills={len(bills)}／contracts={len(contracts)}／"
        f"estates={len(estates)}（其中 {stub_count} 筆為僅被 bills/repairs/meters 引用、"
        f"擷取樣本查無同 id 列的最小 stub）／meters={len(meters)}／repairs={len(repairs)}／"
        f"team_members={len(team_members)}。遮罩規則：電話→09NN-000-0NN、"
        "email→user{n}@example.com、姓名→合成中文姓名（同一原始值一致對應）；"
        "地址保留縣市/區，門牌/樓層改合成值；經緯度/avatar/gallery/floor_plan/vr_url/"
        "broken_photos 一律清空。"
    )

    return {
        "_comment": comment,
        "bills": bills,
        "bill_visibility": {str(b["id"]): [DEMO_USER_ID] for b in bills},
        "contracts": contracts,
        "contract_visibility": {str(c["id"]): [DEMO_USER_ID] for c in contracts},
        "estate_stubs": estate_stubs,   # 僅被 bills/repairs/meters 引用、擷取樣本查無同 id 列（列本身在嚴格投影內，標記放頂層）
        "estates": estates,
        "estate_visibility": {str(e["id"]): [DEMO_USER_ID] for e in estates},
        "meters": meters,
        "team_members": team_members,
        "repairs": repairs,
        "repair_categories": repair_categories,
    }


def assert_no_synthetic_rows(fixture: "dict[str, Any]") -> None:
    """`--mode all` 專用防線：確認舊合成鏈整批不在輸出裡（見模組說明）。"""
    for domain, trap_ids in _SYNTHETIC_TRAP_IDS.items():
        present_ids = {row["id"] for row in fixture[domain]}
        hit = present_ids & trap_ids
        if hit:
            raise SystemExit(f"[FATAL] {domain} 仍含合成 id：{sorted(hit)}")
    member_ids = {row.get("member_user_id") for row in fixture["team_members"]}
    hit_members = member_ids & _SYNTHETIC_TRAP_MEMBER_IDS
    if hit_members:
        raise SystemExit(f"[FATAL] team_members 仍含合成 id：{sorted(hit_members)}")
    text = json.dumps(fixture, ensure_ascii=False)
    hit_values = sorted(v for v in _SYNTHETIC_TRAP_VALUES if v in text)
    if hit_values:
        raise SystemExit(f"[FATAL] 仍含合成陷阱值：{hit_values}")


# ── 合併進 demo_vendor4.json（`--mode legacy`）──────────────────────────────

def merge(fixture: "dict[str, Any]", capture: "dict[str, Any]") -> "dict[str, Any]":
    out = copy.deepcopy(fixture)

    # 1) 既有合成列對 12291 不可見：從 *_visibility 移除 12291，其餘宣告原樣保留。
    for vis_key in ("bill_visibility", "contract_visibility", "estate_visibility"):
        for row_id, viewers in out[vis_key].items():
            if DEMO_USER_ID in viewers:
                viewers.remove(DEMO_USER_ID)

    # 2) 附加真資料子集（原樣保留既有列，⛔ 不動既有列的值/id）。
    new_bills = build_bills(capture)
    new_contracts = build_contracts(capture)
    new_estates = build_estates(capture)
    new_meters = build_meters(capture)
    new_repairs = build_repairs(capture)

    out["bills"].extend(new_bills)
    out["contracts"].extend(new_contracts)
    out["estates"].extend(new_estates)
    out["meters"].extend(new_meters)
    out["repairs"].extend(new_repairs)
    out["repair_categories"] = build_repair_categories(capture)

    # 3) 可見性宣告只含 12291。
    for b in new_bills:
        out["bill_visibility"][str(b["id"])] = [DEMO_USER_ID]
    for c in new_contracts:
        out["contract_visibility"][str(c["id"])] = [DEMO_USER_ID]
    for e in new_estates:
        out["estate_visibility"][str(e["id"])] = [DEMO_USER_ID]

    out["_comment"] = (
        fixture["_comment"]
        + " ｜真資料子集（role_id=20151/user_id=12291 擷取，遮罩後）："
        f"estates {ALL_ESTATE_IDS}、bills {SELECTED_BILL_IDS}、"
        f"contracts {sorted(ESTATE_TO_CONTRACT_ID.values())}（建構，非逐鍵真實）、"
        f"meters {SELECTED_METER_IDS}、repairs {SELECTED_REPAIR_IDS}；"
        "對 12291 可見，既有合成列對 12291 改不可見。"
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--capture", required=True, type=Path,
                     help="原始擷取 JSON（role_id=20151/user_id=12291）路徑")
    ap.add_argument("--fixture", required=True, type=Path,
                     help="demo_vendor4.json 路徑（就地更新／`--mode all` 整份覆寫）")
    ap.add_argument("--mode", choices=("legacy", "all"), default="legacy",
                     help="legacy＝軸心真資料合併進既有合成鏈（預設，向後相容）；"
                          "all＝整份真資料重建、不留任何合成列（2026-09-08 定案）")
    ap.add_argument("--dry-run", action="store_true",
                     help="只驗證與印摘要，不寫檔")
    args = ap.parse_args()

    if not args.capture.is_file():
        print(f"[FATAL] 擷取檔不存在：{args.capture}", file=sys.stderr)
        return 2
    if args.mode == "legacy" and not args.fixture.is_file():
        print(f"[FATAL] fixture 檔不存在：{args.fixture}", file=sys.stderr)
        return 2

    raw_text = args.capture.read_text(encoding="utf-8")
    capture = json.loads(raw_text)

    pii_candidates = extract_pii_candidates(raw_text)
    if not pii_candidates:
        print("[FATAL] 正對照組落空：從擷取檔本身抽不到任何電話／email／經緯度候選值，"
              "掃描規則可能壞了（或擷取檔內容有變）——拒絕繼續。", file=sys.stderr)
        return 2

    if args.mode == "all":
        output = build_all_fixture(capture)
    else:
        fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
        output = merge(fixture, capture)
    output_text = json.dumps(output, ensure_ascii=False, indent=1)

    leaked = sorted(v for v in pii_candidates if v in output_text)
    if leaked:
        print(f"[FATAL] PII 掃描命中 {len(leaked)} 筆原始真實值仍出現於輸出："
              f"{leaked[:20]}{'...' if len(leaked) > 20 else ''}", file=sys.stderr)
        return 1

    if args.mode == "all":
        assert_no_synthetic_rows(output)

    print(f"[OK] 正對照組候選值 {len(pii_candidates)} 筆（含真實電話/經緯度），"
          f"輸出檔掃描 0 命中。")
    if args.mode == "all":
        print(f"[OK] 整份重建 bills={len(output['bills'])} "
              f"contracts={len(output['contracts'])} estates={len(output['estates'])} "
              f"meters={len(output['meters'])} repairs={len(output['repairs'])} "
              f"team_members={len(output['team_members'])} "
              f"repair_categories={len(output['repair_categories'])}；"
              "合成鏈掃描 0 命中。")
    else:
        print(f"[OK] 新增 estates={len(ALL_ESTATE_IDS)} bills={len(SELECTED_BILL_IDS)} "
              f"contracts={len(ESTATE_TO_CONTRACT_ID)} meters={len(SELECTED_METER_IDS)} "
              f"repairs={len(SELECTED_REPAIR_IDS)} repair_categories="
              f"{len(output['repair_categories'])}")

    if args.dry_run:
        print("[dry-run] 未寫檔。")
        return 0

    args.fixture.write_text(output_text + "\n", encoding="utf-8")
    print(f"[OK] 已寫入 {args.fixture}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
