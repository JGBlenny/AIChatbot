"""
創建測試場景文件
從知識庫中提取數據生成 test_scenarios.xlsx
"""
import pandas as pd
import psycopg2
import os
import sys

def create_test_scenarios():
    """創建測試場景文件"""

    try:
        # 連接資料庫
        print("📡 連接資料庫...")
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'aichatbot_admin'),
            user=os.getenv('DB_USER', 'aichatbot'),
            password=os.getenv('DB_PASSWORD', 'aichatbot_password')
        )

        cursor = conn.cursor()

        # 獲取知識庫數據作為測試場景
        print("🔍 查詢知識庫數據...")
        cursor.execute("""
            SELECT
                kb.id,
                kb.question_summary,
                kb.category,
                kb.audience,
                kb.keywords,
                i.name as intent_name
            FROM knowledge_base kb
            LEFT JOIN intents i ON kb.intent_id = i.id
            WHERE kb.question_summary IS NOT NULL
                AND kb.question_summary != ''
                AND i.name IS NOT NULL
            ORDER BY kb.updated_at DESC
            LIMIT 30
        """)

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        print(f"✅ 找到 {len(results)} 條知識庫數據")

        # 創建測試場景
        test_scenarios = []

        if len(results) > 0:
            for idx, row in enumerate(results, 1):
                kb_id, question, category, audience, keywords, intent_name = row

                # 處理關鍵字
                keyword_str = category
                if keywords:
                    if isinstance(keywords, list):
                        keyword_str = ','.join(keywords[:3])  # 取前3個關鍵字
                    else:
                        keyword_str = str(keywords)

                test_scenarios.append({
                    'test_id': idx,
                    'test_question': question,
                    'expected_category': intent_name,
                    'expected_keywords': keyword_str,
                    'difficulty': 'medium',
                    'notes': f'來自知識庫 ID: {kb_id}, 對象: {audience}'
                })

        # 如果沒有足夠的數據，添加示例測試場景
        if len(test_scenarios) < 5:
            print("⚠️ 知識庫數據不足，添加示例測試場景...")
            example_scenarios = [
                {
                    'test_id': len(test_scenarios) + 1,
                    'test_question': '租金如何計算？',
                    'expected_category': '帳務問題',
                    'expected_keywords': '租金,計算,費用',
                    'difficulty': 'easy',
                    'notes': '示例測試 - 租金計算'
                },
                {
                    'test_id': len(test_scenarios) + 2,
                    'test_question': '如何申請退租？',
                    'expected_category': '合約問題',
                    'expected_keywords': '退租,申請,流程',
                    'difficulty': 'medium',
                    'notes': '示例測試 - 退租流程'
                },
                {
                    'test_id': len(test_scenarios) + 3,
                    'test_question': '水電費誰負責？',
                    'expected_category': '帳務問題',
                    'expected_keywords': '水電費,費用,責任',
                    'difficulty': 'easy',
                    'notes': '示例測試 - 費用問題'
                },
                {
                    'test_id': len(test_scenarios) + 4,
                    'test_question': '合約到期後怎麼辦？',
                    'expected_category': '合約問題',
                    'expected_keywords': '合約,到期,續約',
                    'difficulty': 'medium',
                    'notes': '示例測試 - 合約到期'
                },
                {
                    'test_id': len(test_scenarios) + 5,
                    'test_question': '房屋設備損壞如何報修？',
                    'expected_category': '物件問題',
                    'expected_keywords': '設備,損壞,報修',
                    'difficulty': 'medium',
                    'notes': '示例測試 - 設備報修'
                },
                {
                    'test_id': len(test_scenarios) + 6,
                    'test_question': '如何聯繫管理師？',
                    'expected_category': '操作問題',
                    'expected_keywords': '管理師,聯繫,客服',
                    'difficulty': 'easy',
                    'notes': '示例測試 - 聯繫方式'
                },
                {
                    'test_id': len(test_scenarios) + 7,
                    'test_question': '忘記密碼怎麼辦？',
                    'expected_category': '帳號問題',
                    'expected_keywords': '密碼,忘記,重設',
                    'difficulty': 'easy',
                    'notes': '示例測試 - 密碼重設'
                },
                {
                    'test_id': len(test_scenarios) + 8,
                    'test_question': 'IOT 設備如何使用？',
                    'expected_category': 'IOT設備問題',
                    'expected_keywords': 'IOT,設備,使用',
                    'difficulty': 'medium',
                    'notes': '示例測試 - IOT 使用'
                }
            ]
            test_scenarios.extend(example_scenarios)

        # 創建 DataFrame
        df = pd.DataFrame(test_scenarios)

        # 保存到 Excel
        project_root = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
        output_path = os.path.join(project_root, 'test_scenarios.xlsx')
        df.to_excel(output_path, index=False, engine='openpyxl')

        print(f"\n✅ 成功創建測試場景文件：{output_path}")
        print(f"📊 共 {len(df)} 個測試場景")
        print("\n" + "="*60)
        print("測試場景預覽：")
        print("="*60)
        for _, row in df.head(10).iterrows():
            print(f"\n[測試 {row['test_id']}] {row['test_question']}")
            print(f"  預期分類: {row['expected_category']}")
            print(f"  關鍵字: {row['expected_keywords']}")
            print(f"  難度: {row['difficulty']}")

        if len(df) > 10:
            print(f"\n... 還有 {len(df) - 10} 個測試場景")

        print("\n" + "="*60)
        print("💡 提示：你現在可以在前端界面點擊「執行回測」按鈕來運行測試了！")

        return True

    except Exception as e:
        print(f"\n❌ 創建失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = create_test_scenarios()
    sys.exit(0 if success else 1)
