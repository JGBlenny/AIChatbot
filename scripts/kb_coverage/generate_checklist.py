"""
三面向知識清單生成腳本

產出三份 JSON 清單：
  - checklist_general.json   — 一般知識（scope=global, category=general）
  - checklist_industry.json  — 產業知識（scope=global, category=industry）
  - checklist_vendor_template.json — 業者專屬知識範本（scope=vendor, is_template=true）

使用方式：
  python3 scripts/kb_coverage/generate_checklist.py --skeleton
  python3 scripts/kb_coverage/generate_checklist.py --skeleton --output-dir /tmp/output
  python3 scripts/kb_coverage/generate_checklist.py --expand --output-dir /tmp/output
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, TypedDict

logger = logging.getLogger(__name__)


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


# ---------------------------------------------------------------------------
# LLM 輔助子題展開
# ---------------------------------------------------------------------------

# 一般知識各大類的 context hints（幫助 LLM 生成更精準的子題）
_GENERAL_CATEGORY_HINTS: Dict[str, str] = {
    "租賃契約與法規": "定期 vs 不定期契約、契約必備條款、契約審閱期、應記載與不得記載事項",
    "租金與費用常識": "租金行情參考、管理費定義、公共費用分攤原則、水電瓦斯費",
    "押金（保證金）規定": "法定上限、返還時限、扣除條件、收據",
    "入住與退租常識": "點交注意事項、原狀回復義務、傢俱清點",
    "提前解約與違約": "法定解約條件、違約金上限、通知期限",
    "修繕與維護責任歸屬": "房東 vs 租客責任劃分、緊急修繕權利、修繕通知義務",
    "居住使用規範": "轉租限制、寵物規定、噪音管理、公共區域使用",
    "安全與保險": "火災保險、居家安全、住宅火災及地震基本保險",
    "稅務相關": "租賃所得申報、租金扣繳、公益出租人減稅",
    "租客權益與爭議處理": "消保法適用、調解管道、租賃糾紛申訴",
    "戶籍與居住證明": "租屋遷戶籍規定、居住事實證明",
}

# 產業知識各大類的 context hints
_INDUSTRY_CATEGORY_HINTS: Dict[str, str] = {
    "包租業 vs 代管業差異": "法律定義、服務模式、收費結構差異",
    "管理費收費規則": "包租業代收轉付 vs 代管業服務費比例的規則說明",
    "委託管理合約": "委託期限、服務範圍、提前終止條件",
    "社會住宅制度": "社宅申請資格、租金補貼條件、與一般租約的差異說明",
    "業者服務範圍": "標準服務項目、加值服務、服務時段",
    "點交規範與責任": "點交項目清單、損壞賠償標準、照片留存要求",
    "租金代收制度": "公司代收 vs 房東直收的制度差異說明",
    "設備管理責任": "公共設備 vs 租客設備的維護責任歸屬",
}

# 產業知識中可能需要 suggest_api 的關鍵字
_API_SUGGEST_KEYWORDS: List[str] = [
    "金額", "帳單", "明細", "餘額", "費用查詢", "繳費狀態",
    "收費標準", "管理費金額", "租金金額", "欠款", "應繳",
]


def _call_llm_expand(
    category_name: str,
    dimension: str,
    hints: str,
    min_items: int = 5,
    max_items: int = 15,
) -> List[Dict[str, Any]]:
    """
    使用 LLM 展開某大類的子題。

    Returns
    -------
    List[Dict] — 每筆包含 sub_topic, question, target_user, business_types, suggest_api
    """
    import openai
    from tenacity import retry, stop_after_attempt, wait_exponential

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    if dimension == "industry":
        system_prompt = (
            "你是台灣租賃管理產業的知識專家。"
            "你要為 AI 客服的知識庫（KB）展開子題。"
            "KB 只收解答性知識（回答「是什麼」「為什麼」「有哪些」），不收操作流程（那歸 SOP）。"
            "如果子題涉及業者特定數據查詢（例如：某業者的管理費金額、帳單明細、繳費狀態），"
            "請在 suggest_api 欄位填寫建議的 API 用途描述（例如「管理費金額查詢」）；"
            "若不涉及業者特定數據查詢，suggest_api 填 null。"
        )
    else:
        system_prompt = (
            "你是台灣租賃法規與租屋常識的知識專家。"
            "你要為 AI 客服的知識庫（KB）展開子題。"
            "KB 只收解答性知識（回答「是什麼」「為什麼」「有哪些」），不收操作流程（那歸 SOP）。"
            "suggest_api 一律填 null（一般知識不需要 API）。"
        )

    user_prompt = f"""請為「{category_name}」大類展開 {min_items}~{max_items} 個子題。

背景提示：{hints}

請以 JSON 格式回傳，格式如下（注意是一個 JSON 陣列）：
[
  {{
    "sub_topic": "子題名稱（簡短）",
    "question": "對應的獨立可回答問題（完整問句，繁體中文）",
    "target_user": ["tenant", "landlord", "property_manager 中適用的角色"],
    "business_types": ["system_provider", "full_service", "property_management 中適用的業態"],
    "suggest_api": null 或 "API 用途描述"
  }}
]

規則：
1. 每個 question 必須是獨立可回答的完整問句
2. 不要包含操作流程類的子題（例如「如何申請...」「...的步驟」）
3. target_user 可多選：tenant（租客）、landlord（房東）、property_manager（管理師）
4. business_types 可多選：system_provider（系統商）、full_service（全方位服務）、property_management（物管）
5. 只回傳 JSON 陣列，不要其他文字"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
    )
    def _do_call() -> List[Dict[str, Any]]:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(raw)
        # Handle both {"items": [...]} and [...] formats
        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict):
            items = None
            # Try common keys
            for key in ("items", "subtopics", "sub_topics", "data", "result"):
                if key in parsed and isinstance(parsed[key], list):
                    items = parsed[key]
                    break
            # If dict has the item fields directly, wrap it
            if items is None and "sub_topic" in parsed and "question" in parsed:
                items = [parsed]
            if items is None:
                raise ValueError(f"LLM 回傳格式無法解析: keys={list(parsed.keys())}")
        else:
            raise ValueError(f"LLM 回傳格式無法解析: {type(parsed)}")

        # Validate each item has required fields
        valid_items = []
        for item in items:
            if isinstance(item, dict) and "sub_topic" in item and "question" in item:
                valid_items.append(item)
            else:
                logger.warning(f"  跳過格式不正確的項目: {type(item)}")
        return valid_items

    return _do_call()


def _filter_kb_items(
    items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    使用 boundary_classifier 過濾掉被分類為 SOP 的子題。
    """
    from boundary_classifier import classify_knowledge_type

    filtered = []
    for item in items:
        sub_topic = item.get("sub_topic", "")
        question = item.get("question", "")
        # 防禦：LLM 可能回傳非字串值
        if not isinstance(sub_topic, str):
            sub_topic = str(sub_topic)
        if not isinstance(question, str):
            question = str(question)
        topic_text = sub_topic + " " + question
        if classify_knowledge_type(topic_text) == "kb":
            filtered.append(item)
        else:
            logger.info(f"  過濾 SOP 子題: {sub_topic}")
    return filtered


def _check_suggest_api(item: Dict[str, Any]) -> Optional[str]:
    """
    檢查產業知識子題是否涉及業者特定數據查詢，
    若 LLM 已填則保留，若未填但含關鍵字則補標。
    """
    if item.get("suggest_api"):
        return item["suggest_api"]

    text = item.get("sub_topic", "") + " " + item.get("question", "")
    for kw in _API_SUGGEST_KEYWORDS:
        if kw in text:
            return f"{item.get('sub_topic', '')}查詢"
    return None


def _normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """確保每筆 item 的欄位符合 ChecklistItem 結構。"""
    # Normalize sub_topic and question to str
    sub_topic = item.get("sub_topic", "")
    if not isinstance(sub_topic, str):
        sub_topic = str(sub_topic) if sub_topic else ""
    question = item.get("question", "")
    if not isinstance(question, str):
        question = str(question) if question else ""

    # Normalize target_user
    valid_users = {"tenant", "landlord", "property_manager"}
    target_user = item.get("target_user", [])
    if isinstance(target_user, str):
        target_user = [target_user]
    if not isinstance(target_user, list):
        target_user = []
    target_user = [u for u in target_user if isinstance(u, str) and u in valid_users]
    if not target_user:
        target_user = ["tenant"]

    # Normalize business_types
    valid_types = {"system_provider", "full_service", "property_management"}
    business_types = item.get("business_types", [])
    if isinstance(business_types, str):
        business_types = [business_types]
    if not isinstance(business_types, list):
        business_types = []
    business_types = [b for b in business_types if isinstance(b, str) and b in valid_types]
    if not business_types:
        business_types = ["system_provider", "full_service"]

    # Normalize suggest_api — must be str or None
    suggest_api = item.get("suggest_api")
    if suggest_api is not None:
        if isinstance(suggest_api, (list, dict)):
            suggest_api = None  # LLM 誤回傳結構化資料，丟棄
        elif not isinstance(suggest_api, str):
            suggest_api = str(suggest_api) if suggest_api else None

    return {
        "sub_topic": sub_topic,
        "question": question,
        "target_user": target_user,
        "business_types": business_types,
        "suggest_api": suggest_api,
    }


def expand_general_checklist() -> Dict[str, Any]:
    """
    使用 LLM 展開一般知識 11 大類的子題，並用 boundary_classifier 過濾。
    """
    all_items: List[ChecklistItem] = []

    for cat in GENERAL_CATEGORIES:
        cat_id = cat["id"]
        cat_name = cat["name"]
        hints = _GENERAL_CATEGORY_HINTS.get(cat_name, cat_name)

        logger.info(f"展開一般知識: {cat_name} ...")
        try:
            raw_items = _call_llm_expand(cat_name, "general", hints)
            filtered = _filter_kb_items(raw_items)

            for idx, item in enumerate(filtered, start=1):
                normed = _normalize_item(item)
                checklist_item = ChecklistItem(
                    id=f"general-{cat_id}-{idx:02d}",
                    dimension="general",
                    category=cat_name,
                    sub_topic=normed["sub_topic"],
                    question=normed["question"],
                    target_user=normed["target_user"],
                    business_types=normed["business_types"],
                    suggest_api=None,  # 一般知識不需要 API
                )
                all_items.append(checklist_item)

            logger.info(f"  {cat_name}: {len(filtered)} 個子題（原始 {len(raw_items)}）")

        except Exception as e:
            logger.error(f"  {cat_name} 展開失敗: {e}")

    categories = [{"id": c["id"], "name": c["name"]} for c in GENERAL_CATEGORIES]
    return {
        "status": "draft",
        "dimension": "general",
        "categories": categories,
        "items": [dict(item) for item in all_items],
    }


def expand_industry_checklist() -> Dict[str, Any]:
    """
    使用 LLM 展開產業知識 8 大類的子題，標註 suggest_api。
    """
    all_items: List[ChecklistItem] = []

    for cat in INDUSTRY_CATEGORIES:
        cat_id = cat["id"]
        cat_name = cat["name"]
        hints = _INDUSTRY_CATEGORY_HINTS.get(cat_name, cat_name)

        logger.info(f"展開產業知識: {cat_name} ...")
        try:
            raw_items = _call_llm_expand(cat_name, "industry", hints)
            filtered = _filter_kb_items(raw_items)

            for idx, item in enumerate(filtered, start=1):
                normed = _normalize_item(item)
                # 檢查並標註 suggest_api
                normed["suggest_api"] = _check_suggest_api(normed)

                checklist_item = ChecklistItem(
                    id=f"industry-{cat_id}-{idx:02d}",
                    dimension="industry",
                    category=cat_name,
                    sub_topic=normed["sub_topic"],
                    question=normed["question"],
                    target_user=normed["target_user"],
                    business_types=normed["business_types"],
                    suggest_api=normed["suggest_api"],
                )
                all_items.append(checklist_item)

            logger.info(f"  {cat_name}: {len(filtered)} 個子題（原始 {len(raw_items)}）")

        except Exception as e:
            logger.error(f"  {cat_name} 展開失敗: {e}")

    categories = [{"id": c["id"], "name": c["name"]} for c in INDUSTRY_CATEGORIES]
    return {
        "status": "draft",
        "dimension": "industry",
        "categories": categories,
        "items": [dict(item) for item in all_items],
    }


def write_expanded_checklist_files(output_dir: str) -> List[str]:
    """
    使用 LLM 展開子題，產出三份完整 JSON 清單。

    一般知識與產業知識由 LLM 展開，業者專屬知識使用既有範本（不需 LLM 展開）。
    """
    os.makedirs(output_dir, exist_ok=True)

    files_written: List[str] = []

    print("[generate_checklist] 展開一般知識子題...")
    general = expand_general_checklist()
    print(f"  一般知識: {len(general['items'])} 個子題")

    print("[generate_checklist] 展開產業知識子題...")
    industry = expand_industry_checklist()
    print(f"  產業知識: {len(industry['items'])} 個子題")

    # 業者專屬知識用 skeleton（不需 LLM 展開）
    vendor = build_vendor_template_skeleton()

    outputs = [
        ("checklist_general.json", general),
        ("checklist_industry.json", industry),
        ("checklist_vendor_template.json", vendor),
    ]

    for filename, data in outputs:
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        files_written.append(filepath)
        print(f"  寫入: {filepath}")

    return files_written


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
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--skeleton",
        action="store_true",
        help="產出空白 JSON 骨架（不展開子題）",
    )
    mode_group.add_argument(
        "--expand",
        action="store_true",
        help="使用 LLM 輔助展開子題（需 OPENAI_API_KEY）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="輸出目錄（預設：腳本所在目錄）",
    )
    args = parser.parse_args()

    # 決定輸出目錄
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = os.path.dirname(os.path.abspath(__file__))

    if args.skeleton:
        print(f"[generate_checklist] 產出 JSON 骨架到: {output_dir}")
        files = write_checklist_files(output_dir)
        print(f"[generate_checklist] 完成，共產出 {len(files)} 份檔案")
    elif args.expand:
        if not os.getenv("OPENAI_API_KEY"):
            print("錯誤：需要設定 OPENAI_API_KEY 環境變數")
            sys.exit(1)
        logging.basicConfig(level=logging.INFO, format="%(message)s")
        print(f"[generate_checklist] 使用 LLM 展開子題到: {output_dir}")
        files = write_expanded_checklist_files(output_dir)
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

    # ----------------------------------------------------------
    # Test 11: _GENERAL_CATEGORY_HINTS 涵蓋所有 11 大類
    # ----------------------------------------------------------
    for cat in GENERAL_CATEGORIES:
        assert cat["name"] in _GENERAL_CATEGORY_HINTS, \
            f"_GENERAL_CATEGORY_HINTS 缺少: {cat['name']}"
    print("  [PASS] _GENERAL_CATEGORY_HINTS 涵蓋所有 11 大類")

    # ----------------------------------------------------------
    # Test 12: _INDUSTRY_CATEGORY_HINTS 涵蓋所有 8 大類
    # ----------------------------------------------------------
    for cat in INDUSTRY_CATEGORIES:
        assert cat["name"] in _INDUSTRY_CATEGORY_HINTS, \
            f"_INDUSTRY_CATEGORY_HINTS 缺少: {cat['name']}"
    print("  [PASS] _INDUSTRY_CATEGORY_HINTS 涵蓋所有 8 大類")

    # ----------------------------------------------------------
    # Test 13: _normalize_item 欄位正規化
    # ----------------------------------------------------------
    raw_item = {
        "sub_topic": "測試子題",
        "question": "測試問題？",
        "target_user": "tenant",       # 字串 → 應轉為 list
        "business_types": "full_service",  # 字串 → 應轉為 list
        "suggest_api": None,
    }
    normed = _normalize_item(raw_item)
    assert isinstance(normed["target_user"], list), "target_user 應為 list"
    assert isinstance(normed["business_types"], list), "business_types 應為 list"
    assert normed["target_user"] == ["tenant"]
    assert normed["business_types"] == ["full_service"]
    print("  [PASS] _normalize_item 欄位正規化（字串→list）")

    # ----------------------------------------------------------
    # Test 14: _normalize_item 過濾無效值
    # ----------------------------------------------------------
    bad_item = {
        "sub_topic": "測試",
        "question": "測試？",
        "target_user": ["tenant", "invalid_role"],
        "business_types": ["invalid_type"],
        "suggest_api": None,
    }
    normed2 = _normalize_item(bad_item)
    assert normed2["target_user"] == ["tenant"], "應過濾無效 target_user"
    assert normed2["business_types"] == ["system_provider", "full_service"], \
        "無有效 business_types 時應給預設值"
    print("  [PASS] _normalize_item 過濾無效值 + 預設值")

    # ----------------------------------------------------------
    # Test 15: _normalize_item 空值處理
    # ----------------------------------------------------------
    empty_item: Dict[str, Any] = {}
    normed3 = _normalize_item(empty_item)
    assert normed3["sub_topic"] == ""
    assert normed3["question"] == ""
    assert len(normed3["target_user"]) > 0, "target_user 不應為空"
    assert len(normed3["business_types"]) > 0, "business_types 不應為空"
    print("  [PASS] _normalize_item 空值處理")

    # ----------------------------------------------------------
    # Test 16: _check_suggest_api 關鍵字偵測
    # ----------------------------------------------------------
    api_item = {"sub_topic": "管理費金額查詢", "question": "管理費金額是多少？", "suggest_api": None}
    result = _check_suggest_api(api_item)
    assert result is not None, "含 API 關鍵字的子題應標註 suggest_api"
    print(f"  [PASS] _check_suggest_api 偵測到: {result}")

    # ----------------------------------------------------------
    # Test 17: _check_suggest_api 保留 LLM 已填的值
    # ----------------------------------------------------------
    prefilled = {"sub_topic": "帳單", "question": "帳單？", "suggest_api": "帳單查詢 API"}
    result2 = _check_suggest_api(prefilled)
    assert result2 == "帳單查詢 API", "LLM 已填的 suggest_api 應保留"
    print("  [PASS] _check_suggest_api 保留 LLM 已填值")

    # ----------------------------------------------------------
    # Test 18: _check_suggest_api 不誤標
    # ----------------------------------------------------------
    no_api = {"sub_topic": "押金規定", "question": "押金上限是多少？", "suggest_api": None}
    result3 = _check_suggest_api(no_api)
    assert result3 is None, "不涉及數據查詢的子題不應標註 suggest_api"
    print("  [PASS] _check_suggest_api 不誤標一般子題")

    # ----------------------------------------------------------
    # Test 19: _filter_kb_items 過濾 SOP 子題
    # ----------------------------------------------------------
    test_items = [
        {"sub_topic": "押金規定說明", "question": "押金的法定上限是多少？"},
        {"sub_topic": "報修申請流程", "question": "如何申請報修？"},
        {"sub_topic": "違約金上限", "question": "違約金上限是多少？"},
    ]
    filtered_items = _filter_kb_items(test_items)
    # "報修申請流程" + "如何申請報修" 含 SOP 關鍵字，應被過濾
    sub_topics = [i["sub_topic"] for i in filtered_items]
    assert "報修申請流程" not in sub_topics, "SOP 子題應被過濾"
    assert "押金規定說明" in sub_topics, "KB 子題應保留"
    assert "違約金上限" in sub_topics, "KB 子題應保留"
    print(f"  [PASS] _filter_kb_items 過濾 SOP 子題（{len(test_items)}→{len(filtered_items)}）")

    # ----------------------------------------------------------
    # Test 20: _API_SUGGEST_KEYWORDS 非空
    # ----------------------------------------------------------
    assert len(_API_SUGGEST_KEYWORDS) >= 5, \
        f"_API_SUGGEST_KEYWORDS 應至少 5 個，實際 {len(_API_SUGGEST_KEYWORDS)}"
    print(f"  [PASS] _API_SUGGEST_KEYWORDS = {len(_API_SUGGEST_KEYWORDS)} 個關鍵字")

    # ----------------------------------------------------------
    # Test 21: validate_checklist_structure 驗證含 items 的結構
    # ----------------------------------------------------------
    expanded_data: Dict[str, Any] = {
        "status": "draft",
        "dimension": "general",
        "categories": [{"id": "01", "name": "測試"}],
        "items": [
            {
                "id": "general-01-01",
                "dimension": "general",
                "category": "測試",
                "sub_topic": "子題",
                "question": "問題？",
                "target_user": ["tenant"],
                "business_types": ["full_service"],
                "suggest_api": None,
            }
        ],
    }
    errs = validate_checklist_structure(expanded_data, "general")
    assert not errs, f"含完整 items 的結構應通過驗證: {errs}"
    print("  [PASS] validate_checklist_structure 驗證含 items 的結構")

    print("=" * 60)
    print("All generate_checklist.py self-tests passed!")
    print("=" * 60)
