"""
三面向知識清單生成腳本

產出三份 JSON 清單：
  - checklist_general.json   — 一般知識（scope=global, category=general）
  - checklist_industry.json  — 產業知識（scope=global, category=industry）
  - checklist_vendor_template.json — 業者專屬知識範本（scope=vendor, is_template=true）

使用方式：
  python3 scripts/kb_coverage/generate_checklist.py --skeleton
  python3 scripts/kb_coverage/generate_checklist.py --skeleton --output-dir /tmp/output
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, TypedDict


# ---------------------------------------------------------------------------
# ChecklistItem 資料結構
# ---------------------------------------------------------------------------
class ChecklistItem(TypedDict):
    id: str                          # "general-01-01"
    dimension: str                   # "general" | "industry" | "vendor"
    category: str                    # 大類名稱
    sub_topic: str                   # 子題名稱
    question: str                    # 對應的獨立可回答問題
    target_user: List[str]           # ["tenant", "landlord", ...]
    business_types: List[str]        # ["system_provider", "full_service", ...]
    suggest_api: Optional[str]       # 建議未來串接的 API 用途描述（僅標記，不關聯）


# ---------------------------------------------------------------------------
# VendorTemplateField — 業者專屬知識範本欄位定義
# ---------------------------------------------------------------------------
class VendorTemplateField(TypedDict):
    field_name: str                  # 欄位名稱（如「聯絡電話」）
    field_key: str                   # 模板變數 key（如「contact_phone」）
    description: str                 # 欄位說明
    required: bool                   # 是否必填


# ---------------------------------------------------------------------------
# 一般知識 11 大類
# ---------------------------------------------------------------------------
GENERAL_CATEGORIES: List[Dict[str, str]] = [
    {"id": "01", "name": "租賃契約與法規"},
    {"id": "02", "name": "租金與費用常識"},
    {"id": "03", "name": "押金（保證金）規定"},
    {"id": "04", "name": "入住與退租常識"},
    {"id": "05", "name": "提前解約與違約"},
    {"id": "06", "name": "修繕與維護責任歸屬"},
    {"id": "07", "name": "居住使用規範"},
    {"id": "08", "name": "安全與保險"},
    {"id": "09", "name": "稅務相關"},
    {"id": "10", "name": "租客權益與爭議處理"},
    {"id": "11", "name": "戶籍與居住證明"},
]

# ---------------------------------------------------------------------------
# 產業知識 8 大類
# ---------------------------------------------------------------------------
INDUSTRY_CATEGORIES: List[Dict[str, str]] = [
    {"id": "01", "name": "包租業 vs 代管業差異"},
    {"id": "02", "name": "管理費收費規則"},
    {"id": "03", "name": "委託管理合約"},
    {"id": "04", "name": "社會住宅制度"},
    {"id": "05", "name": "業者服務範圍"},
    {"id": "06", "name": "點交規範與責任"},
    {"id": "07", "name": "租金代收制度"},
    {"id": "08", "name": "設備管理責任"},
]

# ---------------------------------------------------------------------------
# 業者專屬知識 — 通用欄位範本
# ---------------------------------------------------------------------------
VENDOR_TEMPLATE_FIELDS: List[VendorTemplateField] = [
    {
        "field_name": "聯絡電話",
        "field_key": "contact_phone",
        "description": "業者客服或服務電話",
        "required": True,
    },
    {
        "field_name": "Email",
        "field_key": "contact_email",
        "description": "業者聯絡信箱",
        "required": True,
    },
    {
        "field_name": "地址",
        "field_key": "office_address",
        "description": "業者辦公室或服務據點地址",
        "required": False,
    },
    {
        "field_name": "營業時間",
        "field_key": "business_hours",
        "description": "業者營業或服務時段",
        "required": True,
    },
    {
        "field_name": "服務範圍",
        "field_key": "service_area",
        "description": "業者服務的地理區域或物件類型",
        "required": False,
    },
    {
        "field_name": "收費標準",
        "field_key": "pricing_info",
        "description": "業者管理費或服務費收費方式與金額",
        "required": True,
    },
    {
        "field_name": "緊急聯絡方式",
        "field_key": "emergency_contact",
        "description": "非營業時間的緊急聯絡管道",
        "required": True,
    },
]


def _build_skeleton_item(
    dimension: str,
    category_id: str,
    category_name: str,
    sub_index: int = 0,
) -> ChecklistItem:
    """建立一個空白的 ChecklistItem 骨架（skeleton 模式用）。"""
    item_id = f"{dimension}-{category_id}-{sub_index:02d}"
    return ChecklistItem(
        id=item_id,
        dimension=dimension,
        category=category_name,
        sub_topic="",
        question="",
        target_user=[],
        business_types=[],
        suggest_api=None,
    )


def build_general_skeleton() -> Dict[str, Any]:
    """產出一般知識的 JSON 骨架結構。"""
    categories = [{"id": c["id"], "name": c["name"]} for c in GENERAL_CATEGORIES]
    return {
        "status": "draft",
        "dimension": "general",
        "categories": categories,
        "items": [],
    }


def build_industry_skeleton() -> Dict[str, Any]:
    """產出產業知識的 JSON 骨架結構。"""
    categories = [{"id": c["id"], "name": c["name"]} for c in INDUSTRY_CATEGORIES]
    return {
        "status": "draft",
        "dimension": "industry",
        "categories": categories,
        "items": [],
    }


def build_vendor_template_skeleton() -> Dict[str, Any]:
    """產出業者專屬知識範本的 JSON 骨架結構。"""
    return {
        "status": "draft",
        "dimension": "vendor",
        "is_template": True,
        "template_fields": [dict(f) for f in VENDOR_TEMPLATE_FIELDS],
        "categories": [{"id": "01", "name": "業者專屬資訊"}],
        "items": [],
    }


def write_checklist_files(output_dir: str) -> List[str]:
    """
    產出三份 JSON 清單檔案。

    Parameters
    ----------
    output_dir : str
        輸出目錄路徑

    Returns
    -------
    List[str]
        成功寫入的檔案路徑清單
    """
    os.makedirs(output_dir, exist_ok=True)

    files_written: List[str] = []

    outputs = [
        ("checklist_general.json", build_general_skeleton()),
        ("checklist_industry.json", build_industry_skeleton()),
        ("checklist_vendor_template.json", build_vendor_template_skeleton()),
    ]

    for filename, data in outputs:
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        files_written.append(filepath)
        print(f"  寫入: {filepath}")

    return files_written


def validate_checklist_structure(data: Dict[str, Any], dimension: str) -> List[str]:
    """
    驗證清單 JSON 結構是否正確。

    Returns
    -------
    List[str]
        錯誤訊息清單；空表示通過
    """
    errors: List[str] = []

    # 共用必要欄位
    for key in ("status", "dimension", "categories", "items"):
        if key not in data:
            errors.append(f"缺少必要欄位: {key}")

    if data.get("dimension") != dimension:
        errors.append(f"dimension 應為 '{dimension}'，實際為 '{data.get('dimension')}'")

    if data.get("status") != "draft":
        errors.append(f"status 應為 'draft'，實際為 '{data.get('status')}'")

    if not isinstance(data.get("categories"), list):
        errors.append("categories 應為 list")

    if not isinstance(data.get("items"), list):
        errors.append("items 應為 list")

    # vendor 專屬欄位
    if dimension == "vendor":
        if not data.get("is_template"):
            errors.append("vendor 維度應有 is_template=true")
        if "template_fields" not in data:
            errors.append("vendor 維度應有 template_fields")

    # 驗證 items 中每筆 ChecklistItem 的結構
    checklist_keys = {"id", "dimension", "category", "sub_topic", "question",
                      "target_user", "business_types", "suggest_api"}
    for i, item in enumerate(data.get("items", [])):
        missing = checklist_keys - set(item.keys())
        if missing:
            errors.append(f"items[{i}] 缺少欄位: {missing}")

    return errors


def main():
    parser = argparse.ArgumentParser(
        description="三面向知識清單生成腳本"
    )
    parser.add_argument(
        "--skeleton",
        action="store_true",
        help="產出空白 JSON 骨架（不展開子題）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="輸出目錄（預設：腳本所在目錄）",
    )
    args = parser.parse_args()

    if not args.skeleton:
        print("目前僅支援 --skeleton 模式（子題展開功能待 Task 2.2 實作）")
        sys.exit(1)

    # 決定輸出目錄
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"[generate_checklist] 產出 JSON 骨架到: {output_dir}")
    files = write_checklist_files(output_dir)
    print(f"[generate_checklist] 完成，共產出 {len(files)} 份檔案")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # 如果有 CLI 引數（--skeleton 等）→ 執行 main()
    # 否則（無引數）→ 執行 self-test
    if len(sys.argv) > 1:
        main()
        sys.exit(0)

    import tempfile

    print("=" * 60)
    print("generate_checklist.py — self-test")
    print("=" * 60)

    # ----------------------------------------------------------
    # Test 1: ChecklistItem 結構完整性
    # ----------------------------------------------------------
    sample_item = ChecklistItem(
        id="general-01-01",
        dimension="general",
        category="租賃契約與法規",
        sub_topic="定期契約定義",
        question="什麼是定期租賃契約？",
        target_user=["tenant"],
        business_types=["system_provider", "full_service"],
        suggest_api=None,
    )
    expected_keys = {"id", "dimension", "category", "sub_topic", "question",
                     "target_user", "business_types", "suggest_api"}
    assert set(sample_item.keys()) == expected_keys, \
        f"ChecklistItem 欄位不符: {set(sample_item.keys())} != {expected_keys}"
    print("  [PASS] ChecklistItem 資料結構正確")

    # ----------------------------------------------------------
    # Test 2: 一般知識大類數量 = 11
    # ----------------------------------------------------------
    assert len(GENERAL_CATEGORIES) == 11, \
        f"一般知識應有 11 大類，實際 {len(GENERAL_CATEGORIES)}"
    print("  [PASS] GENERAL_CATEGORIES = 11 大類")

    # ----------------------------------------------------------
    # Test 3: 產業知識大類數量 = 8
    # ----------------------------------------------------------
    assert len(INDUSTRY_CATEGORIES) == 8, \
        f"產業知識應有 8 大類，實際 {len(INDUSTRY_CATEGORIES)}"
    print("  [PASS] INDUSTRY_CATEGORIES = 8 大類")

    # ----------------------------------------------------------
    # Test 4: 業者範本欄位數量 >= 7
    # ----------------------------------------------------------
    assert len(VENDOR_TEMPLATE_FIELDS) >= 7, \
        f"業者範本欄位應至少 7 個，實際 {len(VENDOR_TEMPLATE_FIELDS)}"
    print(f"  [PASS] VENDOR_TEMPLATE_FIELDS = {len(VENDOR_TEMPLATE_FIELDS)} 個欄位")

    # ----------------------------------------------------------
    # Test 5: skeleton 輸出結構驗證
    # ----------------------------------------------------------
    general = build_general_skeleton()
    industry = build_industry_skeleton()
    vendor = build_vendor_template_skeleton()

    for label, data, dim in [
        ("general", general, "general"),
        ("industry", industry, "industry"),
        ("vendor", vendor, "vendor"),
    ]:
        errs = validate_checklist_structure(data, dim)
        assert not errs, f"{label} 結構驗證失敗: {errs}"
    print("  [PASS] 三份骨架結構驗證通過")

    # ----------------------------------------------------------
    # Test 6: 寫檔並讀回驗證
    # ----------------------------------------------------------
    with tempfile.TemporaryDirectory() as tmpdir:
        files = write_checklist_files(tmpdir)
        assert len(files) == 3, f"應產出 3 份檔案，實際 {len(files)}"

        for filepath in files:
            assert os.path.exists(filepath), f"檔案不存在: {filepath}"
            with open(filepath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded["status"] == "draft", f"{filepath} status 應為 draft"
            assert "dimension" in loaded, f"{filepath} 缺少 dimension"
            assert "categories" in loaded, f"{filepath} 缺少 categories"
            assert "items" in loaded, f"{filepath} 缺少 items"
            assert isinstance(loaded["items"], list), f"{filepath} items 應為 list"

        # 驗證 vendor 檔案有 is_template
        vendor_path = os.path.join(tmpdir, "checklist_vendor_template.json")
        with open(vendor_path, "r", encoding="utf-8") as f:
            vendor_data = json.load(f)
        assert vendor_data.get("is_template") is True, \
            "vendor 檔案應有 is_template=true"
        assert "template_fields" in vendor_data, \
            "vendor 檔案應有 template_fields"

    print("  [PASS] 寫檔 + 讀回驗證通過（3 份 JSON）")

    # ----------------------------------------------------------
    # Test 7: _build_skeleton_item 產出格式正確
    # ----------------------------------------------------------
    item = _build_skeleton_item("general", "01", "租賃契約與法規", 0)
    assert item["id"] == "general-01-00"
    assert item["dimension"] == "general"
    assert item["category"] == "租賃契約與法規"
    assert item["sub_topic"] == ""
    assert item["question"] == ""
    assert item["target_user"] == []
    assert item["business_types"] == []
    assert item["suggest_api"] is None
    print("  [PASS] _build_skeleton_item 格式正確")

    # ----------------------------------------------------------
    # Test 8: validate_checklist_structure 拒絕不完整結構
    # ----------------------------------------------------------
    bad_data: Dict[str, Any] = {"status": "draft"}
    errs = validate_checklist_structure(bad_data, "general")
    assert len(errs) > 0, "不完整結構應回報錯誤"
    print("  [PASS] validate_checklist_structure 可偵測不完整結構")

    # ----------------------------------------------------------
    # Test 9: 大類 id 唯一性
    # ----------------------------------------------------------
    gen_ids = [c["id"] for c in GENERAL_CATEGORIES]
    assert len(gen_ids) == len(set(gen_ids)), "GENERAL_CATEGORIES id 應唯一"
    ind_ids = [c["id"] for c in INDUSTRY_CATEGORIES]
    assert len(ind_ids) == len(set(ind_ids)), "INDUSTRY_CATEGORIES id 應唯一"
    print("  [PASS] 大類 id 唯一性驗證通過")

    # ----------------------------------------------------------
    # Test 10: VendorTemplateField 結構正確
    # ----------------------------------------------------------
    vtf_keys = {"field_name", "field_key", "description", "required"}
    for i, field in enumerate(VENDOR_TEMPLATE_FIELDS):
        missing = vtf_keys - set(field.keys())
        assert not missing, f"VENDOR_TEMPLATE_FIELDS[{i}] 缺少: {missing}"
    print("  [PASS] VendorTemplateField 結構驗證通過")

    print("=" * 60)
    print("All generate_checklist.py self-tests passed!")
    print("=" * 60)
