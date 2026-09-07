"""TDD：`demo_vendor4.json` 真資料子集不含真實個資（任務契約 2026-09-08）。

本組驗的是「真實值不再出現」，**不是**「輸出裡沒有像電話/email 的字串」——
遮罩後的合成佔位值（如 `0901-000-001`／`user1@example.com`）本來就長得像
電話／email，一般 regex 掃描會誤把它們當「命中」。真正該驗的是：從**原始擷取檔**
抽出的電話／email／經緯度候選值，逐字不再出現於最終的 `demo_vendor4.json`。

正對照組：擷取檔裡至少有一個已知真實電話字面值（`0909558137`，見
`repairs` 8591/7628 的 `user_phone`）——證明掃描規則本身沒壞，
而不是「規則寫錯導致什麼都掃不到」。
"""
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_FIXTURE_PATH = (Path(__file__).resolve().parents[3]
                 / "services" / "jgb" / "fixture_data" / "demo_vendor4.json")

#: 與 `scripts/fixtures/build_demo_fixture_from_capture.py` 的 extract_pii_candidates()
#: 同一組規則（獨立重寫，不 import 建置腳本——避免「掃描器抄自己」失去獨立驗證意義）。
_PHONE_RE = re.compile(r"09\d{8}|09\d{2}-\d{3}-\d{3}|0\d{1,2}-\d{4}-\d{4}")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_TWID_RE = re.compile(r"\b[A-Z][12]\d{8}\b")

#: 本次真資料擷取（role_id=20151/user_id=12291）已知會出現的真實個資字面值——
#: 這些值在遮罩前的原始擷取檔裡真的存在（人工核對），遮罩後的 demo_vendor4.json
#: 裡不應再出現任何一個。
_KNOWN_REAL_VALUES = {
    "0909558137",          # repairs 8591／7628 的真實 user_phone（遮罩前）
    "demo@jgbsmart.com",   # repairs 8591／7628 的真實 user_email（遮罩前）
    "25.03767380",         # 45728 的真實緯度（遮罩前，非 0.00000000 佔位）
    "121.50743890",        # 45728 的真實經度（遮罩前）
}

#: 既有合成 fixture 刻意保留的個資陷阱（見 `demo_vendor4.json` 的 `_comment` 與
#: `test_jgb_mock_full_coverage_req.py::_ALLOWED_CONTACTS`）——非本次任務注入，
#: 契約明訂勿清除，故本測試的「掃描全文找像電話/email的字串」步驟需排除它們，
#: 只在「已知真實值集合」這條主張上聚焦。
_LEGACY_ALLOWED = {
    "0912345678", "0923456789", "tenant@example.com", "tenant2@example.com",
    "0911-111-111", "0912-345-678", "02-2345-6789",
    "owner@example.com", "viewer@example.com", "nochar@example.com",
    "manager@example.com", "sales12291@example.com",
}


def _fixture_text() -> str:
    return _FIXTURE_PATH.read_text(encoding="utf-8")


def test_positive_control_phone_pattern_is_detectable():
    """正對照組：掃描規則本身要抓得到電話格式，否則後面的「0 命中」毫無意義。"""
    assert _PHONE_RE.search("0909558137"), "正對照組未命中——電話掃描規則本身可能壞了"
    assert _EMAIL_RE.search("demo@jgbsmart.com"), "正對照組未命中——email 掃描規則本身可能壞了"


def test_known_real_contact_values_are_absent_from_fixture():
    """真資料子集遮罩後：本次擷取裡已知的真實電話／email／經緯度，一個都不該留在檔案裡。"""
    text = _fixture_text()
    leaked = sorted(v for v in _KNOWN_REAL_VALUES if v in text)
    assert not leaked, f"以下真實個資值仍出現於 demo_vendor4.json：{leaked}"


def test_new_estate_rows_have_no_gps_or_gallery():
    """真資料子集的物件列：經緯度／gallery／avatar／floor_plan／vr_url 一律清空。"""
    import json
    data = json.loads(_fixture_text())
    real_subset_ids = {68926, 67649, 67651, 67652, 45728}
    rows = [e for e in data["estates"] if e["id"] in real_subset_ids]
    assert len(rows) == len(real_subset_ids), "真資料子集物件列缺筆——先確認 fixture 已跑過建置腳本"
    for e in rows:
        assert e["latitude"] in (None, ""), e["id"]
        assert e["longitude"] in (None, ""), e["id"]
        assert e["avatar"] is None, e["id"]
        assert e["gallery"] is None, e["id"]
        assert e["floor_plan"] is None, e["id"]
        assert e["vr_url"] is None, e["id"]


def test_new_repair_rows_have_no_broken_photos_and_masked_contacts():
    """真資料子集的修繕列：broken_photos 清空；電話／email 已非原始真實值。"""
    import json
    data = json.loads(_fixture_text())
    rows = [r for r in data["repairs"] if r["id"] in (8591, 7628)]
    assert len(rows) == 2, "真資料子集修繕列缺筆——先確認 fixture 已跑過建置腳本"
    for r in rows:
        assert r["broken_photos"] == []
        assert r["user_phone"] != "0909558137"
        assert r["user_email"] != "demo@jgbsmart.com"


def test_undeclared_contact_strings_limited_to_legacy_allowlist_or_new_masked_scheme():
    """全文掃描電話／email：命中的字串只能是既有陷阱，或本次遮罩產生的合成值
    （`09NN-000-0NN` / `userN@example.com` 格式）——不能是任何其他未預期的明文聯絡方式。
    """
    text = _fixture_text()
    phones = set(_PHONE_RE.findall(text))
    emails = set(_EMAIL_RE.findall(text))
    twids = set(_TWID_RE.findall(text))

    _new_phone_re = re.compile(r"^09\d{2}-000-0\d{2}$")
    _new_email_re = re.compile(r"^user\d+@example\.com$")

    def _unexpected(values, new_re):
        return sorted(v for v in values
                       if v not in _LEGACY_ALLOWED and not new_re.match(v))

    assert not _unexpected(phones, _new_phone_re), \
        f"出現未預期的電話字串：{_unexpected(phones, _new_phone_re)}"
    assert not _unexpected(emails, _new_email_re), \
        f"出現未預期的 email 字串：{_unexpected(emails, _new_email_re)}"
    assert not twids, f"出現身分證／統編格式字串：{sorted(twids)}"
