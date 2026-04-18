"""
從 Excel 資料建立 process_checklist.json
讀取 SOP_1 客戶常見QA 的分類與子題，重新組織為 13 大類
"""
import json
import openpyxl
from collections import defaultdict

# Excel 分類 → 13 大類映射
CATEGORY_MAP = {
    # 租賃契約
    "合約條款／內容": "租賃契約",
    "合約": "租賃契約",
    "其他合約相關": "租賃契約",
    "租約變更／轉租": "租賃契約",
    # 租金與費用
    "帳務": "租金與費用",
    "租金繳納": "租金與費用",
    "租金金額調整": "租金與費用",
    "其他租金相關": "租金與費用",
    "收據問題": "租金與費用",
    "電費查詢": "租金與費用",
    "電表度數/抄表": "租金與費用",
    "其他電費問題": "租金與費用",
    "儲值電/預付電": "租金與費用",
    # 押金
    "押金/退款": "押金",
    # 入住與退租
    "租期／到期": "入住與退租",
    "退租": "入住與退租",
    "退租／解約流程": "提前解約與違約",
    # 修繕與維護
    "水電": "修繕與維護",
    "冷氣": "修繕與維護",
    "電器設備": "修繕與維護",
    "其他設備問題": "修繕與維護",
    "家具/裝潢": "修繕與維護",
    # 居住使用規範
    "噪音問題": "居住使用規範",
    "鄰居": "居住使用規範",
    "室友": "居住使用規範",
    "網路/第四台": "居住使用規範",
    # 社區管理與設施
    "鑰匙": "社區管理與設施",
    "垃圾回收": "社區管理與設施",
    "廢棄物代收": "社區管理與設施",
    # 爭議處理與客訴
    "激動客訴問題": "爭議處理與客訴",
}

# 13 大類定義（含未被 Excel 覆蓋的類別）
ALL_CATEGORIES = [
    {"category_name": "租賃契約", "description": "租約條款、契約變更、轉租、續約等合約相關問題"},
    {"category_name": "租金與費用", "description": "租金繳納、金額調整、電費、水費、管理費、收據等費用問題"},
    {"category_name": "押金", "description": "押金繳納、退還、扣款、爭議等保證金問題"},
    {"category_name": "入住與退租", "description": "入住點交、退租流程、租期到期、續約等租期問題"},
    {"category_name": "提前解約與違約", "description": "提前退租、違約金、解約流程、點交等解約問題"},
    {"category_name": "修繕與維護", "description": "水電、冷氣、電器、家具、裝潢等設備維修問題"},
    {"category_name": "居住使用規範", "description": "噪音、鄰居、室友、網路、寵物、裝潢規定等居住規範"},
    {"category_name": "社區管理與設施", "description": "鑰匙門禁、垃圾回收、公設使用、停車位等社區管理"},
    {"category_name": "安全與保險", "description": "居家安全、火災保險、天災處理、用電安全等"},
    {"category_name": "稅務相關", "description": "房屋稅、租金扣除額、租金補貼、稅賦優惠等"},
    {"category_name": "爭議處理與客訴", "description": "租賃糾紛、客訴處理、調處管道、法律資源等"},
    {"category_name": "制度與法規", "description": "包租代管制度、租賃專法、定型化契約、政府補貼等"},
    {"category_name": "戶籍與居住證明", "description": "戶籍遷入、居住證明、就學設籍等"},
]

def load_excel_subtopics():
    """從 Excel 載入子題"""
    wb = openpyxl.load_workbook(
        'data/20250305 租管業 SOP_1 客戶常見QA.xlsx',
        read_only=True
    )
    ws = wb['工作表1']

    subtopics_by_cat = defaultdict(set)
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i < 2:
            continue
        cat = row[4] if row[4] else ''
        subcat = row[5] if row[5] else ''
        if not cat or not subcat:
            continue
        if cat in ('分類別 (可自訂分類)',):
            continue
        mapped = CATEGORY_MAP.get(cat)
        if mapped:
            subtopics_by_cat[mapped].add(subcat)
        else:
            print(f"[WARN] 未映射分類: {cat} | {subcat}")

    return subtopics_by_cat


def add_manual_subtopics():
    """補充 Excel 未覆蓋的類別子題（來自領域研究）"""
    return {
        "安全與保險": [
            "熱水器安裝位置與一氧化碳安全",
            "煙霧偵測器與滅火器配置",
            "住宅火災保險說明",
            "地震或颱風後的損壞處理",
            "用電安全與高功率電器規範",
        ],
        "稅務相關": [
            "房屋稅與地價稅負擔歸屬",
            "租金支出報稅扣除額說明",
            "申請政府租金補貼的資格與流程",
            "包租代管稅賦優惠說明",
        ],
        "制度與法規": [
            "包租業與代管業的定義與差異",
            "租賃專法重點說明",
            "定型化契約應記載與不得記載事項",
            "社會住宅包租代管計畫簡介",
            "契約審閱期規定",
            "公證費補助申請",
        ],
        "戶籍與居住證明": [
            "租屋處辦理戶籍遷入的權利",
            "居住事實證明文件取得",
            "就學設籍需求的處理方式",
        ],
    }


def build_checklist():
    excel_subtopics = load_excel_subtopics()
    manual_subtopics = add_manual_subtopics()

    # 合併
    all_subtopics = defaultdict(list)
    for cat, subs in excel_subtopics.items():
        all_subtopics[cat].extend(sorted(subs))
    for cat, subs in manual_subtopics.items():
        all_subtopics[cat].extend(subs)

    # 建立 checklist
    checklist = []
    topic_counter = 0
    for cat_def in ALL_CATEGORIES:
        cat_name = cat_def["category_name"]
        subs = all_subtopics.get(cat_name, [])

        subtopics = []
        for sub in subs:
            topic_counter += 1
            topic_id = f"{cat_name[:2]}_{topic_counter:03d}"
            subtopics.append({
                "topic_id": topic_id,
                "question": sub,
                "business_type": "both",
                "keywords": [],  # SOPGenerator 會用 LLM 生成
                "cashflow_relevant": any(
                    kw in sub for kw in ["租金", "押金", "費用", "繳", "退款", "電費", "管理費"]
                ),
                "priority": "p0" if cat_name in ["租賃契約", "租金與費用", "押金", "修繕與維護"] else "p1",
            })

        checklist.append({
            "category_name": cat_name,
            "description": cat_def["description"],
            "subtopics": subtopics,
        })

    return checklist


if __name__ == "__main__":
    checklist = build_checklist()

    total = sum(len(c["subtopics"]) for c in checklist)
    print(f"=== Process Checklist ===")
    for cat in checklist:
        print(f"  {cat['category_name']}: {len(cat['subtopics'])} 筆")
    print(f"  Total: {total} 筆")

    with open("scripts/sop_coverage/process_checklist.json", "w", encoding="utf-8") as f:
        json.dump(checklist, f, ensure_ascii=False, indent=2)

    print(f"\nWritten to scripts/sop_coverage/process_checklist.json")
