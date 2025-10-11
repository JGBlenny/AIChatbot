"""
測試題庫資料遷移腳本

功能：
1. 讀取 Excel 測試題庫（test_scenarios_smoke.xlsx, test_scenarios_full.xlsx）
2. 遷移到資料庫 test_scenarios 表
3. 自動建立集合關聯
4. 驗證遷移完整性

使用方式：
    python3 database/migrations/migrate_excel_to_db.py
"""

import os
import sys
import pandas as pd
import psycopg2
import psycopg2.extras
from datetime import datetime
from typing import List, Dict, Tuple

# 配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'user': os.getenv('DB_USER', 'aichatbot'),
    'password': os.getenv('DB_PASSWORD', 'aichatbot_password'),
    'database': os.getenv('DB_NAME', 'aichatbot_admin')
}

PROJECT_ROOT = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# 測試題庫檔案
TEST_FILES = {
    'smoke': os.path.join(PROJECT_ROOT, "test_scenarios_smoke.xlsx"),
    'full': os.path.join(PROJECT_ROOT, "test_scenarios_full.xlsx")
}


class TestScenarioMigrator:
    """測試情境遷移器"""

    def __init__(self, db_config: Dict, dry_run: bool = False):
        self.db_config = db_config
        self.dry_run = dry_run
        self.conn = None
        self.stats = {
            'total_read': 0,
            'total_inserted': 0,
            'total_skipped': 0,
            'errors': []
        }

    def connect(self):
        """連接資料庫"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.conn.autocommit = False  # 使用事務
            print(f"✅ 資料庫連接成功: {self.db_config['database']}")
            return True
        except Exception as e:
            print(f"❌ 資料庫連接失敗: {e}")
            return False

    def get_collection_id(self, collection_name: str) -> int:
        """獲取集合 ID"""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id FROM test_collections WHERE name = %s",
            (collection_name,)
        )
        result = cur.fetchone()
        cur.close()

        if result:
            return result[0]
        else:
            raise ValueError(f"Collection not found: {collection_name}")

    def get_intent_id(self, intent_name: str) -> int:
        """獲取意圖 ID（模糊匹配）"""
        cur = self.conn.cursor()

        # 先嘗試精確匹配
        cur.execute(
            "SELECT id FROM intents WHERE name = %s AND is_enabled = true",
            (intent_name,)
        )
        result = cur.fetchone()

        if result:
            cur.close()
            return result[0]

        # 模糊匹配：部分包含
        cur.execute(
            """
            SELECT id FROM intents
            WHERE is_enabled = true
              AND (name LIKE %s OR %s LIKE name)
            LIMIT 1
            """,
            (f"%{intent_name}%", f"%{intent_name}%")
        )
        result = cur.fetchone()
        cur.close()

        if result:
            return result[0]
        else:
            print(f"   ⚠️  找不到意圖: {intent_name}，將設為 NULL")
            return None

    def read_excel(self, file_path: str) -> List[Dict]:
        """讀取 Excel 測試題庫"""
        if not os.path.exists(file_path):
            print(f"   ⚠️  檔案不存在: {file_path}")
            return []

        try:
            df = pd.read_excel(file_path, engine='openpyxl')
            scenarios = df.to_dict('records')
            print(f"   ✅ 讀取 {len(scenarios)} 個測試情境")
            return scenarios
        except Exception as e:
            print(f"   ❌ 讀取失敗: {e}")
            self.stats['errors'].append(f"Read error ({file_path}): {e}")
            return []

    def migrate_scenario(
        self,
        scenario: Dict,
        collection_name: str,
        collection_id: int
    ) -> Tuple[bool, str]:
        """遷移單個測試情境"""

        try:
            # 提取數據
            test_question = scenario.get('test_question', '').strip()
            if not test_question:
                return False, "Empty test_question"

            expected_category = scenario.get('expected_category', '').strip()
            expected_keywords = scenario.get('expected_keywords', '')
            difficulty = scenario.get('difficulty', 'medium').lower()
            notes = scenario.get('notes', '')

            # 處理關鍵字（可能是字串或列表）
            if isinstance(expected_keywords, str):
                keywords = [k.strip() for k in expected_keywords.split(',') if k.strip()]
            elif isinstance(expected_keywords, list):
                keywords = expected_keywords
            else:
                keywords = []

            # 獲取意圖 ID
            intent_id = None
            if expected_category:
                intent_id = self.get_intent_id(expected_category)

            # 檢查是否已存在（避免重複）
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT id FROM test_scenarios
                WHERE test_question = %s
                """,
                (test_question,)
            )
            existing = cur.fetchone()

            if existing:
                cur.close()
                return False, f"Already exists (ID: {existing[0]})"

            if self.dry_run:
                cur.close()
                return True, "DRY RUN - would insert"

            # 插入測試情境
            cur.execute(
                """
                INSERT INTO test_scenarios (
                    test_question,
                    expected_category,
                    expected_intent_id,
                    expected_keywords,
                    difficulty,
                    status,
                    source,
                    is_active,
                    notes,
                    created_by
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
                """,
                (
                    test_question,
                    expected_category if expected_category else None,
                    intent_id,
                    keywords if keywords else None,
                    difficulty,
                    'approved',  # 從 Excel 遷移的視為已審核
                    'imported',  # 來源：匯入
                    True,  # 啟用
                    notes if notes else f'從 {collection_name} 集合遷移',
                    'migration_script'
                )
            )

            scenario_id = cur.fetchone()[0]

            # 建立集合關聯
            cur.execute(
                """
                INSERT INTO test_scenario_collections (
                    scenario_id,
                    collection_id,
                    display_order,
                    added_by
                ) VALUES (
                    %s, %s, %s, %s
                )
                """,
                (scenario_id, collection_id, scenario.get('test_id', 0), 'migration_script')
            )

            cur.close()
            return True, f"Inserted (ID: {scenario_id})"

        except Exception as e:
            return False, f"Error: {e}"

    def migrate_collection(self, collection_name: str, file_path: str):
        """遷移一個測試集合"""

        print(f"\n📦 遷移集合: {collection_name}")
        print(f"   檔案: {file_path}")

        # 讀取 Excel
        scenarios = self.read_excel(file_path)
        if not scenarios:
            print(f"   ⚠️  無資料可遷移")
            return

        self.stats['total_read'] += len(scenarios)

        # 獲取集合 ID
        try:
            collection_id = self.get_collection_id(collection_name)
            print(f"   ✅ 集合 ID: {collection_id}")
        except ValueError as e:
            print(f"   ❌ {e}")
            self.stats['errors'].append(f"Collection error: {e}")
            return

        # 遷移每個測試情境
        for idx, scenario in enumerate(scenarios, 1):
            success, message = self.migrate_scenario(scenario, collection_name, collection_id)

            if success:
                self.stats['total_inserted'] += 1
                print(f"   ✅ [{idx}/{len(scenarios)}] {message}")
            else:
                self.stats['total_skipped'] += 1
                print(f"   ⏭️  [{idx}/{len(scenarios)}] {message}")
                if "Error" in message:
                    self.stats['errors'].append(f"{collection_name}#{idx}: {message}")

    def run(self):
        """執行遷移"""

        print("="*60)
        print("測試題庫資料遷移")
        print("="*60)

        if self.dry_run:
            print("🧪 DRY RUN 模式（不會實際寫入資料庫）")
            print()

        # 連接資料庫
        if not self.connect():
            return False

        try:
            # 遷移每個測試集合
            for collection_name, file_path in TEST_FILES.items():
                self.migrate_collection(collection_name, file_path)

            # 驗證結果
            print(f"\n{'='*60}")
            print("遷移摘要")
            print(f"{'='*60}")
            print(f"讀取總數：{self.stats['total_read']}")
            print(f"插入成功：{self.stats['total_inserted']}")
            print(f"跳過數量：{self.stats['total_skipped']}")
            print(f"錯誤數量：{len(self.stats['errors'])}")

            if self.stats['errors']:
                print(f"\n❌ 錯誤列表：")
                for error in self.stats['errors'][:10]:  # 只顯示前 10 個
                    print(f"   - {error}")

            # 提交或回滾
            if not self.dry_run:
                if len(self.stats['errors']) == 0 and self.stats['total_inserted'] > 0:
                    self.conn.commit()
                    print(f"\n✅ 遷移成功！已提交 {self.stats['total_inserted']} 筆資料")
                    return True
                else:
                    self.conn.rollback()
                    print(f"\n❌ 遷移失敗，已回滾所有變更")
                    return False
            else:
                print(f"\n🧪 DRY RUN 完成，未提交資料")
                return True

        except Exception as e:
            print(f"\n❌ 遷移過程發生錯誤: {e}")
            if self.conn:
                self.conn.rollback()
            return False

        finally:
            if self.conn:
                self.conn.close()
                print("\n資料庫連接已關閉")


def main():
    """主程式"""

    import argparse

    parser = argparse.ArgumentParser(description='測試題庫資料遷移')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run 模式（不實際寫入資料庫）'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='強制執行（跳過確認）'
    )

    args = parser.parse_args()

    # 確認提示
    if not args.force and not args.dry_run:
        print("⚠️  警告：此操作將從 Excel 檔案遷移資料到資料庫")
        print("確認要繼續嗎？(y/N): ", end='')
        confirm = input().strip().lower()
        if confirm != 'y':
            print("❌ 已取消")
            return

    # 執行遷移
    migrator = TestScenarioMigrator(DB_CONFIG, dry_run=args.dry_run)
    success = migrator.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
