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

                test_scenarios.append({
                    'test_id': idx,
                    'test_question': question,
                    'difficulty': 'medium',
                    'notes': f'來自知識庫 ID: {kb_id}, 意圖: {intent_name}, 對象: {audience}'
                })

        # 如果沒有足夠的數據，添加示例測試場景
        if len(test_scenarios) < 5:
            print("⚠️ 知識庫數據不足，添加示例測試場景...")
            example_scenarios = [
                {
                    'test_id': len(test_scenarios) + 1,
                    'test_question': '租金如何計算？',
                    'difficulty': 'easy',
                    'notes': '示例測試 - 租金計算問題'
                },
                {
                    'test_id': len(test_scenarios) + 2,
                    'test_question': '如何申請退租？',
                    'difficulty': 'medium',
                    'notes': '示例測試 - 退租流程問題'
                },
                {
                    'test_id': len(test_scenarios) + 3,
                    'test_question': '水電費誰負責？',
                    'difficulty': 'easy',
                    'notes': '示例測試 - 費用責任問題'
                },
                {
                    'test_id': len(test_scenarios) + 4,
                    'test_question': '合約到期後怎麼辦？',
                    'difficulty': 'medium',
                    'notes': '示例測試 - 合約到期問題'
                },
                {
                    'test_id': len(test_scenarios) + 5,
                    'test_question': '房屋設備損壞如何報修？',
                    'difficulty': 'medium',
                    'notes': '示例測試 - 設備報修問題'
                },
                {
                    'test_id': len(test_scenarios) + 6,
                    'test_question': '如何聯繫管理師？',
                    'difficulty': 'easy',
                    'notes': '示例測試 - 聯繫管理師問題'
                },
                {
                    'test_id': len(test_scenarios) + 7,
                    'test_question': '忘記密碼怎麼辦？',
                    'difficulty': 'easy',
                    'notes': '示例測試 - 密碼重設問題'
                },
                {
                    'test_id': len(test_scenarios) + 8,
                    'test_question': 'IOT 設備如何使用？',
                    'difficulty': 'medium',
                    'notes': '示例測試 - IOT 設備使用問題'
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
            print(f"  難度: {row['difficulty']}")
            if row.get('notes'):
                print(f"  備註: {row['notes']}")

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
