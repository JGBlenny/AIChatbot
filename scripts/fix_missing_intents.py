#!/usr/bin/env python3
"""
從 Excel 檔案修復遺失意圖的知識項目

原理：
1. 讀取 Excel 檔案的問題和分類
2. 在資料庫中找到匹配的知識（by question_summary）
3. 根據 Excel 的分類設定對應的 intent_id
4. 不需要 OpenAI API！

使用情境：
- 部署時忘記先執行 add_rental_qa_intents.sql
- 導致從 Excel 匯入的知識沒有意圖分類
"""

import os
import sys
import psycopg2
import pandas as pd
from typing import List, Dict, Tuple
from datetime import datetime
from difflib import SequenceMatcher

# 設定
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "aichatbot_admin"),
    "user": os.getenv("DB_USER", "aichatbot"),
    "password": os.getenv("DB_PASSWORD", "aichatbot_password")
}

# Excel 檔案路徑
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
EXCEL_FILE = os.getenv(
    "EXCEL_FILE",
    os.path.join(PROJECT_ROOT, "data", "20250305 租管業 SOP_1 客戶常見QA.xlsx")
)

# 顏色輸出
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.BLUE}{'=' * 80}")
    print(f"{text}")
    print(f"{'=' * 80}{Colors.NC}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.NC}")

def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.NC}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.NC}")

def print_info(text: str):
    print(f"   {text}")

def connect_db():
    """連接數據庫"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print_error(f"無法連接數據庫: {e}")
        sys.exit(1)

def read_excel_data():
    """讀取 Excel 數據"""
    print_header("步驟 1：讀取 Excel 檔案")

    try:
        # 讀取 Excel（從第2行開始，第1行是標題）
        df = pd.read_excel(EXCEL_FILE, header=1)

        # 篩選有問題的行
        df_with_q = df[df['租客常問Q'].notna()].copy()

        # 清理數據
        df_with_q['租客常問Q'] = df_with_q['租客常問Q'].str.strip()
        df_with_q['分類別 (可自訂分類)'] = df_with_q['分類別 (可自訂分類)'].str.strip()

        print_success(f"讀取 Excel 檔案成功")
        print_info(f"檔案路徑：{EXCEL_FILE}")
        print_info(f"問答總數：{len(df_with_q)}")

        # 統計分類
        categories = df_with_q['分類別 (可自訂分類)'].value_counts()
        print_info(f"分類總數：{len(categories)}")
        print()

        return df_with_q

    except FileNotFoundError:
        print_error(f"找不到 Excel 檔案: {EXCEL_FILE}")
        return None
    except Exception as e:
        print_error(f"讀取 Excel 失敗: {e}")
        return None

def get_intent_mapping(conn):
    """獲取意圖名稱到 ID 的映射"""
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name
        FROM intents
        WHERE type = 'knowledge'
        ORDER BY name
    """)

    rows = cur.fetchall()
    cur.close()

    intent_map = {}
    for row in rows:
        intent_map[row[1]] = row[0]  # name -> id

    return intent_map

def get_missing_intent_knowledge(conn):
    """獲取沒有意圖的知識項目"""
    cur = conn.cursor()

    cur.execute("""
        SELECT
            id,
            question_summary,
            vendor_id,
            created_at
        FROM knowledge_base
        WHERE intent_id IS NULL
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    cur.close()

    knowledge_list = []
    for row in rows:
        knowledge_list.append({
            'id': row[0],
            'question': row[1],
            'vendor_id': row[2],
            'created_at': row[3]
        })

    return knowledge_list

def similarity_ratio(str1: str, str2: str) -> float:
    """計算兩個字串的相似度"""
    return SequenceMatcher(None, str1, str2).ratio()

def match_knowledge_with_excel(knowledge_list: List[Dict], excel_df: pd.DataFrame, threshold=0.85):
    """匹配知識和 Excel 數據"""
    matches = []

    for kb in knowledge_list:
        kb_question = kb['question'].strip()

        best_match = None
        best_score = 0.0

        # 在 Excel 中找最相似的問題
        for idx, row in excel_df.iterrows():
            excel_question = row['租客常問Q'].strip()
            score = similarity_ratio(kb_question, excel_question)

            if score > best_score:
                best_score = score
                best_match = {
                    'excel_question': excel_question,
                    'category': row['分類別 (可自訂分類)'],
                    'score': score
                }

        # 如果相似度超過閾值，認為是匹配
        if best_match and best_score >= threshold:
            matches.append({
                'kb_id': kb['id'],
                'kb_question': kb_question,
                'excel_question': best_match['excel_question'],
                'category': best_match['category'],
                'similarity': best_score
            })
        else:
            # 沒有找到匹配
            matches.append({
                'kb_id': kb['id'],
                'kb_question': kb_question,
                'excel_question': None,
                'category': None,
                'similarity': best_score
            })

    return matches

def update_knowledge_intent(conn, knowledge_id: int, intent_id: int, similarity: float):
    """更新知識的意圖（同時更新 knowledge_base 和 knowledge_intent_mapping）"""
    cur = conn.cursor()

    # 1. 更新 knowledge_base 表（向後兼容）
    cur.execute("""
        UPDATE knowledge_base
        SET
            intent_id = %s,
            intent_confidence = %s,
            intent_assigned_by = 'excel_match',
            updated_at = NOW()
        WHERE id = %s
    """, (intent_id, similarity, knowledge_id))

    # 2. 插入到 knowledge_intent_mapping 表（前端顯示）
    # 先刪除舊的關聯（如果存在）
    cur.execute("""
        DELETE FROM knowledge_intent_mapping
        WHERE knowledge_id = %s
    """, (knowledge_id,))

    # 插入新的關聯
    cur.execute("""
        INSERT INTO knowledge_intent_mapping
            (knowledge_id, intent_id, intent_type, confidence, assigned_by)
        VALUES
            (%s, %s, 'primary', %s, 'excel_match')
    """, (knowledge_id, intent_id, similarity))

    conn.commit()
    cur.close()

def fix_missing_intents(conn, excel_df, dry_run=False):
    """修復缺失的意圖"""
    print_header("步驟 2：修復缺失的意圖")

    # 獲取缺失意圖的知識
    knowledge_list = get_missing_intent_knowledge(conn)

    if len(knowledge_list) == 0:
        print_success("沒有需要修復的知識！")
        return {'total': 0, 'success': 0, 'failed': 0}

    print_info(f"找到 {len(knowledge_list)} 筆缺失意圖的知識")
    print()

    # 獲取意圖映射
    intent_map = get_intent_mapping(conn)
    print_info(f"可用意圖數：{len(intent_map)}")
    print()

    # 匹配知識和 Excel
    print_info("正在匹配知識和 Excel 數據...")
    matches = match_knowledge_with_excel(knowledge_list, excel_df, threshold=0.85)
    print()

    if dry_run:
        print_warning("🔍 測試模式（Dry Run）- 不會實際更新數據庫")
    print()

    # 統計
    stats = {'total': len(matches), 'success': 0, 'failed': 0, 'low_similarity': 0}

    # 逐一處理
    for i, match in enumerate(matches, 1):
        print(f"處理 {i}/{len(matches)}: ID={match['kb_id']}")
        print_info(f"問題：{match['kb_question'][:60]}")

        if match['category']:
            # 找到意圖
            intent_id = intent_map.get(match['category'])

            if intent_id:
                print_info(f"匹配分類：{match['category']} (相似度: {match['similarity']:.2f})")

                if match['similarity'] < 0.9:
                    print_warning(f"相似度較低 ({match['similarity']:.2f})")
                    print_info(f"Excel 問題：{match['excel_question'][:60]}")
                    stats['low_similarity'] += 1

                if not dry_run:
                    update_knowledge_intent(conn, match['kb_id'], intent_id, match['similarity'])
                    stats['success'] += 1
                    print_success("已更新")
                else:
                    stats['success'] += 1
                    print_info(f"[測試] 將更新為：{match['category']}")
            else:
                print_error(f"找不到意圖：{match['category']}")
                stats['failed'] += 1
        else:
            print_error(f"無法匹配 Excel 數據（最高相似度: {match['similarity']:.2f}）")
            stats['failed'] += 1

        print()

    return stats

def generate_report(stats: Dict, output_file: str = None):
    """生成修復報告"""
    print_header("修復報告")

    print_info(f"總知識數：{stats['total']}")
    print_success(f"成功修復：{stats['success']}")
    print_error(f"失敗：{stats['failed']}")

    if stats.get('low_similarity', 0) > 0:
        print_warning(f"低相似度匹配（< 0.9）：{stats['low_similarity']}")

    success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
    print_info(f"成功率：{success_rate:.1f}%")

    if output_file:
        report_content = f"""# 意圖修復報告（從 Excel）

**執行時間：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 統計

- 總知識數：{stats['total']}
- 成功修復：{stats['success']}
- 失敗：{stats['failed']}
- 低相似度匹配（< 0.9）：{stats.get('low_similarity', 0)}
- 成功率：{success_rate:.1f}%

## 修復方法

- 從 Excel 檔案讀取問題和分類
- 使用字串相似度匹配（閾值 0.85）
- 分配標記：excel_match

## 建議

- 檢查失敗的知識項目
- 審查低相似度（< 0.9）的匹配
- 必要時手動調整分類
"""

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        print_success(f"報告已保存：{output_file}")

def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description='從 Excel 修復遺失意圖的知識項目')
    parser.add_argument('--dry-run', action='store_true', help='測試模式（不實際更新數據庫）')
    parser.add_argument('--report', type=str, help='報告輸出文件路徑')
    parser.add_argument('--excel', type=str, help='Excel 檔案路徑（可選）')

    args = parser.parse_args()

    # 如果指定了 Excel 檔案
    global EXCEL_FILE
    if args.excel:
        EXCEL_FILE = args.excel

    print_header("🔧 從 Excel 修復遺失意圖的知識項目")

    # 讀取 Excel
    excel_df = read_excel_data()
    if excel_df is None or len(excel_df) == 0:
        print_error("無法讀取 Excel 數據")
        sys.exit(1)

    # 連接數據庫
    conn = connect_db()
    print_success("數據庫連接成功")
    print()

    try:
        # 修復缺失的意圖
        stats = fix_missing_intents(conn, excel_df, dry_run=args.dry_run)

        # 生成報告
        generate_report(stats, output_file=args.report)

        print_header("✅ 修復完成")

    except KeyboardInterrupt:
        print_warning("\n用戶中斷操作")
        sys.exit(1)

    except Exception as e:
        print_error(f"發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        conn.close()

if __name__ == "__main__":
    main()
