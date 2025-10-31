"""
業者參數遷移腳本
從 emergency_repair_hours 遷移到 repair_response_time
"""
import sys
import os
import re
from typing import List, Dict, Any

# 加入路徑以便導入 db_utils
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
rag_orchestrator_path = os.path.join(project_root, 'rag-orchestrator')

if os.path.exists(rag_orchestrator_path):
    sys.path.insert(0, rag_orchestrator_path)
else:
    # 在容器中，直接從 /app 路徑導入
    sys.path.insert(0, '/app')

from services.db_utils import get_db_cursor, execute_query


def print_section(title: str):
    """打印章節標題"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subsection(title: str):
    """打印子章節標題"""
    print(f"\n{title}")
    print("-" * 80)


class VendorParamMigration:
    """業者參數遷移類"""

    def __init__(self):
        self.old_params = []
        self.new_params = []
        self.knowledge_entries = []
        self.migration_sql = []

    def step1_check_old_params(self):
        """步驟 1: 盤點所有業者的舊參數"""
        print_section("📊 步驟 1: 盤點所有業者的舊參數")

        # 查詢所有舊參數
        query = """
        SELECT vendor_id, category, param_key, param_value, data_type, created_at
        FROM vendor_configs
        WHERE param_key = 'emergency_repair_hours'
        ORDER BY vendor_id;
        """

        self.old_params = execute_query(query, dict_cursor=True, fetch="all")

        print(f"\n找到 {len(self.old_params)} 個業者使用舊參數:")
        for param in self.old_params:
            print(f"  - 業者 {param['vendor_id']}: emergency_repair_hours = \"{param['param_value']}\"")

        # 檢查是否已有新參數
        query_new = """
        SELECT vendor_id, category, param_key, param_value, data_type
        FROM vendor_configs
        WHERE param_key = 'repair_response_time'
        ORDER BY vendor_id;
        """

        self.new_params = execute_query(query_new, dict_cursor=True, fetch="all")

        if self.new_params:
            print(f"\n⚠️  警告：已有 {len(self.new_params)} 個業者設定了新參數:")
            for param in self.new_params:
                print(f"  - 業者 {param['vendor_id']}: repair_response_time = {param['param_value']}")
        else:
            print("\n✅ 確認：目前沒有業者設定 repair_response_time")

        return len(self.old_params) > 0

    def step2_check_system_definition(self):
        """步驟 2: 檢查 system_param_definitions"""
        print_section("📋 步驟 2: 檢查系統參數定義")

        query = """
        SELECT param_key, display_name, data_type, unit, default_value,
               description, category, is_required, placeholder, display_order
        FROM system_param_definitions
        WHERE param_key IN ('emergency_repair_hours', 'repair_response_time')
        ORDER BY param_key;
        """

        definitions = execute_query(query, dict_cursor=True, fetch="all")

        for definition in definitions:
            print(f"\n參數: {definition['param_key']}")
            print(f"  顯示名稱: {definition['display_name']}")
            print(f"  資料類型: {definition['data_type']}")
            print(f"  單位: {definition['unit']}")
            print(f"  預設值: {definition['default_value']}")
            print(f"  分類: {definition['category']}")
            print(f"  必填: {definition['is_required']}")
            print(f"  說明: {definition['description']}")
            print(f"  占位符: {definition['placeholder']}")
            print(f"  顯示順序: {definition['display_order']}")

        # 檢查是否存在新參數定義
        has_new_def = any(d['param_key'] == 'repair_response_time' for d in definitions)

        if not has_new_def:
            print("\n⚠️  警告：未找到 repair_response_time 的系統定義")
            print("   建議先在 system_param_definitions 中新增定義")
        else:
            print("\n✅ 確認：repair_response_time 已有系統定義")

        return has_new_def

    def step3_check_knowledge_usage(self):
        """步驟 3: 檢查知識庫使用情況"""
        print_section("📚 步驟 3: 檢查知識庫使用情況")

        # 搜尋提到維修時效的知識
        query = """
        SELECT id, vendor_id, question_summary, answer, is_template, template_vars
        FROM knowledge_base
        WHERE (question_summary LIKE '%緊急報修%' OR question_summary LIKE '%維修時效%' OR
               answer LIKE '%緊急報修%' OR answer LIKE '%維修時效%' OR
               answer LIKE '%小時%' OR answer LIKE '%工作天%')
        AND is_active = true
        ORDER BY vendor_id, id;
        """

        self.knowledge_entries = execute_query(query, dict_cursor=True, fetch="all")

        print(f"\n找到 {len(self.knowledge_entries)} 個相關知識條目:")

        for entry in self.knowledge_entries:
            print(f"\n  ID {entry['id']} (業者 {entry['vendor_id']}):")
            question_text = entry['question_summary'][:60] if entry['question_summary'] else "(無)"
            print(f"    問題: {question_text}...")
            print(f"    回答: {entry['answer'][:100]}...")
            print(f"    是否模板: {entry['is_template']}")
            if entry['template_vars']:
                print(f"    模板變數: {entry['template_vars']}")

        return len(self.knowledge_entries)

    def step4_check_code_dependencies(self):
        """步驟 4: 檢查程式碼依賴（透過檔案搜尋）"""
        print_section("🔍 步驟 4: 程式碼依賴檢查")

        print("\n提示：請手動執行以下命令檢查程式碼依賴：")
        print("\n  grep -r \"emergency_repair_hours\" rag-orchestrator/ knowledge-admin/ --include=\"*.py\" --include=\"*.js\" --include=\"*.vue\"")
        print("\n如果找到任何引用，請先更新程式碼再執行遷移。")

    def step5_generate_conversion_rules(self):
        """步驟 5: 生成數值轉換規則"""
        print_section("🔧 步驟 5: 數值轉換規則")

        print("\n轉換規則:")
        print("  \"24小時\" → 24")
        print("  \"2小時內回應\" → 2")
        print("  \"XX小時\" → XX")
        print("  \"X個工作天\" → X * 24")

        conversion_map = {}

        for param in self.old_params:
            old_value = param['param_value']
            vendor_id = param['vendor_id']

            # 嘗試提取數字
            match = re.search(r'(\d+)', old_value)
            if match:
                number = int(match.group(1))

                # 判斷是否為工作天
                if '工作天' in old_value or '日' in old_value:
                    new_value = number * 24
                else:
                    new_value = number

                conversion_map[vendor_id] = {
                    'old_value': old_value,
                    'new_value': new_value
                }

                print(f"  業者 {vendor_id}: \"{old_value}\" → {new_value} 小時")
            else:
                print(f"  ⚠️  業者 {vendor_id}: 無法解析 \"{old_value}\"，請手動處理")

        return conversion_map

    def step6_generate_migration_sql(self, conversion_map: Dict[int, Dict[str, Any]]):
        """步驟 6: 生成遷移 SQL"""
        print_section("📝 步驟 6: 生成遷移 SQL")

        sql_statements = []

        # 開始事務
        sql_statements.append("-- ============================================")
        sql_statements.append("-- 業者參數遷移 SQL")
        sql_statements.append("-- 從 emergency_repair_hours 遷移到 repair_response_time")
        sql_statements.append("-- ============================================")
        sql_statements.append("")
        sql_statements.append("BEGIN;")
        sql_statements.append("")

        # 步驟 1: 插入新參數
        sql_statements.append("-- 步驟 1: 插入新參數 repair_response_time")
        sql_statements.append("")

        for vendor_id, conversion in conversion_map.items():
            # 需要找到該業者的 category
            category = next((p['category'] for p in self.old_params if p['vendor_id'] == vendor_id), 'service_settings')

            sql = f"""INSERT INTO vendor_configs (vendor_id, category, param_key, param_value, data_type, created_at, updated_at)
VALUES ({vendor_id}, '{category}', 'repair_response_time', '{conversion['new_value']}', 'integer', NOW(), NOW())
ON CONFLICT (vendor_id, category, param_key) DO UPDATE SET
    param_value = EXCLUDED.param_value,
    data_type = EXCLUDED.data_type,
    updated_at = NOW();"""
            sql_statements.append(sql)
            sql_statements.append("")

        # 步驟 2: 驗證插入結果
        sql_statements.append("-- 步驟 2: 驗證插入結果")
        sql_statements.append("")
        sql_statements.append("""SELECT vendor_id, category, param_key, param_value, data_type
FROM vendor_configs
WHERE param_key = 'repair_response_time'
ORDER BY vendor_id;""")
        sql_statements.append("")

        # 步驟 3: 刪除舊參數
        sql_statements.append("-- 步驟 3: 刪除舊參數 emergency_repair_hours")
        sql_statements.append("-- ⚠️  請在確認新參數正確後再執行此步驟")
        sql_statements.append("")
        sql_statements.append("""-- DELETE FROM vendor_configs
-- WHERE param_key = 'emergency_repair_hours';""")
        sql_statements.append("")

        # 步驟 4: 更新知識庫（如果需要）
        if self.knowledge_entries:
            sql_statements.append("-- 步驟 4: 更新知識庫模板變數")
            sql_statements.append("-- 這裡僅作為示例，實際更新需要根據具體內容調整")
            sql_statements.append("")

            for entry in self.knowledge_entries[:5]:  # 只顯示前 5 個作為示例
                question_text = entry['question_summary'][:50] if entry['question_summary'] else "(無問題)"
                sql_statements.append(f"-- ID {entry['id']}: {question_text}...")
                sql_statements.append(f"-- 當前回答: {entry['answer'][:80]}...")
                sql_statements.append("-- 建議手動檢查並更新為模板變數 {{{{repair_response_time}}}}")
                sql_statements.append("")

        # 提交事務
        sql_statements.append("COMMIT;")
        sql_statements.append("")
        sql_statements.append("-- ============================================")
        sql_statements.append("-- 遷移完成！")
        sql_statements.append("-- ============================================")

        self.migration_sql = sql_statements

        print("\n生成的 SQL 腳本:")
        print("\n".join(sql_statements))

        # 儲存到檔案
        if os.path.exists('/app/scripts'):
            output_file = "/app/scripts/migration_output.sql"
        else:
            output_file = os.path.join(script_dir, "migration_output.sql")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(sql_statements))

        print(f"\n✅ SQL 腳本已儲存到: {output_file}")

        return output_file

    def step7_risk_assessment(self):
        """步驟 7: 風險評估"""
        print_section("⚠️  步驟 7: 風險評估")

        print("\n可能的風險:")
        print("  1. 數值轉換錯誤：如果舊參數格式不標準，可能無法正確轉換")
        print("  2. 知識庫不一致：部分知識條目可能硬編碼了舊的時效資訊")
        print("  3. 快取問題：參數變更後需要清除快取才能生效")
        print("  4. 前端顯示：前端可能還在使用舊參數名稱")

        print("\n回滾方案:")
        print("  1. 在執行 DELETE 前保留舊參數")
        print("  2. 可使用以下 SQL 回滾:")
        print("     DELETE FROM vendor_configs WHERE param_key = 'repair_response_time';")

        print("\n備份建議:")
        print("  1. 執行前備份 vendor_configs 表")
        print("     pg_dump -t vendor_configs aichatbot_admin > backup.sql")
        print("  2. 執行前備份 knowledge_base 表")
        print("     pg_dump -t knowledge_base aichatbot_admin > kb_backup.sql")

    def run_full_investigation(self):
        """執行完整調查"""
        print_section("🚀 開始業者參數遷移調查")

        # 步驟 1-4: 調查階段
        has_old_params = self.step1_check_old_params()

        if not has_old_params:
            print("\n✅ 沒有需要遷移的舊參數，結束")
            return False

        has_definition = self.step2_check_system_definition()
        self.step3_check_knowledge_usage()
        self.step4_check_code_dependencies()

        # 步驟 5-6: 遷移計畫
        conversion_map = self.step5_generate_conversion_rules()

        if conversion_map:
            sql_file = self.step6_generate_migration_sql(conversion_map)

        # 步驟 7: 風險評估
        self.step7_risk_assessment()

        return True


def main():
    """主程式"""
    print("\n" + "=" * 80)
    print("  業者參數遷移工具")
    print("  emergency_repair_hours → repair_response_time")
    print("=" * 80)

    try:
        migration = VendorParamMigration()
        success = migration.run_full_investigation()

        if success:
            print_section("✅ 調查完成")
            print("\n下一步:")
            print("  1. 檢查生成的 SQL 腳本: scripts/migration_output.sql")
            print("  2. 確認數值轉換正確")
            print("  3. 執行備份")
            print("  4. 在測試環境執行 SQL")
            print("  5. 驗證 API 端點")
            print("  6. 清除快取")
            print("  7. 在生產環境執行")

    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
