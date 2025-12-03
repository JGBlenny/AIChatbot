"""
SOP 工具函數
提供 SOP 相關的共用功能，避免代碼重複
"""
import pandas as pd
import io
from typing import Union


def parse_sop_excel(file_input: Union[str, bytes]) -> dict:
    """
    解析 SOP Excel 文件（三層結構）

    此函數用於解析標準格式的 SOP Excel 文件，支援兩種輸入方式：
    1. 檔案路徑（str）：用於命令行腳本
    2. 檔案內容（bytes）：用於 Web API 上傳

    Excel 結構對應：
    - 第1欄（分類）→ vendor_sop_categories.category_name
    - 第2欄（說明）→ vendor_sop_groups.group_name
    - 第3欄（序號）→ vendor_sop_items.item_number
    - 第4欄（項目）→ vendor_sop_items.item_name
    - 第5欄（內容）→ vendor_sop_items.content

    Args:
        file_input: Excel 檔案路徑（str）或檔案內容（bytes）

    Returns:
        {
            'categories': [
                {
                    'name': '租賃流程相關資訊',
                    'groups': [
                        {
                            'name': '租賃申請流程：介紹如何申請租賃...',
                            'items': [
                                {
                                    'number': 1,
                                    'name': '申請步驟：',
                                    'content': '租客首先需要在線提交租賃申請表...'
                                },
                                ...
                            ]
                        },
                        ...
                    ]
                },
                ...
            ]
        }
    """
    # 根據輸入類型選擇讀取方式
    if isinstance(file_input, str):
        # 檔案路徑
        df = pd.read_excel(file_input, sheet_name=0)
    else:
        # bytes 內容
        df = pd.read_excel(io.BytesIO(file_input), sheet_name=0)

    # 清理欄位名稱（根據實際欄位數量動態設定）
    num_cols = len(df.columns)
    base_cols = ['分類', '說明', '序號', '項目', '內容']

    if num_cols >= 5:
        # 至少有 5 個必要欄位
        extra_cols = [f'額外欄位{i}' for i in range(1, num_cols - 4)]
        df.columns = base_cols + extra_cols
    else:
        raise ValueError(f"Excel 欄位數量不足，至少需要 5 個欄位（分類、說明、序號、項目、內容），目前只有 {num_cols} 個")

    categories = []
    current_category = None
    current_group = None

    for idx, row in df.iterrows():
        category_name = row['分類']
        group_name = row['說明']  # 第2欄是 group_name，不是 category description
        item_number = row['序號']
        item_name = row['項目']
        item_content = row['內容']

        # 跳過標題行
        if category_name == '分類':
            continue

        # 遇到新分類
        if pd.notna(category_name):
            # 清理分類名稱：移除換行符、多餘空格
            clean_name = str(category_name).replace('\n', '').replace('\r', '').strip()

            current_category = {
                'name': clean_name,
                'groups': []  # 三層結構：分類 → 群組 → 項目
            }
            categories.append(current_category)
            current_group = None  # 重置當前群組

        # 遇到新群組（說明欄位）
        if current_category and pd.notna(group_name) and str(group_name).strip():
            clean_group_name = str(group_name).replace('\n', ' ').replace('\r', ' ').strip()

            current_group = {
                'name': clean_group_name,
                'items': []
            }
            current_category['groups'].append(current_group)

        # 添加項目
        if current_group and pd.notna(item_name):
            item_data = {
                'number': int(item_number) if pd.notna(item_number) else None,
                'name': str(item_name).strip(),
                'content': str(item_content).strip() if pd.notna(item_content) else ''
            }
            current_group['items'].append(item_data)

    return {'categories': categories}


def identify_cashflow_sensitive_items(item_name: str, content: str) -> dict:
    """
    識別是否需要金流模式判斷

    此函數用於判斷 SOP 項目是否涉及金流相關內容，
    並根據不同的金流模式生成對應的內容版本。

    使用場景：
    1. 平台範本匯入時（platform_sop_templates）
    2. 業者從 Excel 匯入時（vendor_sop_items）

    Args:
        item_name: 項目名稱
        content: 項目內容

    Returns:
        {
            'requires_cashflow': bool,
            'through_company': str or None,
            'direct_to_landlord': str or None
        }
    """
    # 金流敏感關鍵字
    cashflow_keywords = ['租金支付', '繳費', '收據', '發票', '遲付', '押金', '帳戶', '匯款']

    requires_cashflow = any(kw in item_name or kw in content for kw in cashflow_keywords)

    if not requires_cashflow:
        return {
            'requires_cashflow': False,
            'through_company': None,
            'direct_to_landlord': None
        }

    # 根據項目類型生成不同版本的內容
    versions = {}

    if '租金支付方式' in item_name:
        versions['through_company'] = "登入JGB系統查看公司收款帳號，可通過銀行轉帳、信用卡支付或超商代碼繳款。"
        versions['direct_to_landlord'] = "請向房東索取收款帳號，建議使用銀行轉帳並留存交易記錄。"

    elif '租金提醒通知' in item_name:
        versions['through_company'] = "JGB系統會根據租金帳單的截止日，提前透過email、LINE等發送繳租提醒，並在收款後主動通知您。"
        versions['direct_to_landlord'] = "JGB系統會根據租金帳單的截止日，提前透過email、LINE等發送繳租提醒。請您自行與房東確認收款狀態。"

    elif '收據或發票' in item_name:
        versions['through_company'] = "支付後，JGB系統會自動生成收據或電子發票，並通過郵件發送給您。您也可以登入管理系統查閱。"
        versions['direct_to_landlord'] = "請向房東索取收據，JGB系統僅保存繳款提醒記錄供您參考。"

    elif '遲付租金' in item_name or '遲付' in item_name:
        versions['through_company'] = "JGB系統會自動發送催繳通知並依約收取滯納金，請儘速完成繳款。"
        versions['direct_to_landlord'] = "房東會處理遲付事宜，JGB系統僅協助發送提醒通知。請您主動聯繫房東說明情況。"

    elif '押金' in item_name:
        versions['through_company'] = "押金由公司收取並專戶保管，租約結束後會根據房屋狀況於7個工作天內退還。"
        versions['direct_to_landlord'] = "押金由房東收取，租約結束後請與房東確認退還時間與方式。"

    elif '提前終止' in item_name:
        versions['through_company'] = "若需提前終止租約，請向公司提出申請，我們會依據合約計算賠償金額並協助辦理退租手續。"
        versions['direct_to_landlord'] = "若需提前終止租約，請與房東協商，JGB可提供合約條款參考與退租檢核表協助您完成程序。"

    else:
        # 其他項目：保持原內容
        versions['through_company'] = content
        versions['direct_to_landlord'] = content

    return {
        'requires_cashflow': True,
        'through_company': versions.get('through_company', content),
        'direct_to_landlord': versions.get('direct_to_landlord', content)
    }
