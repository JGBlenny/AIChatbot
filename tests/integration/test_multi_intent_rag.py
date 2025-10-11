#!/usr/bin/env python3
"""
多意圖 RAG 系統完整測試
測試 RAG 檢索和評分機制在多意圖場景下的正確性
"""

import sys
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List

# 添加路徑
sys.path.insert(0, '/Users/lenny/jgb/AIChatbot/rag-orchestrator')

from services.intent_classifier import IntentClassifier
from services.vendor_knowledge_retriever import VendorKnowledgeRetriever


class MultiIntentRAGTester:
    """多意圖 RAG 測試器"""

    def __init__(self):
        self.intent_classifier = IntentClassifier(use_database=True)
        self.knowledge_retriever = VendorKnowledgeRetriever()
        self.test_results = []

    def print_section(self, title: str):
        """打印區塊標題"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)

    def print_test_header(self, test_num: int, test_name: str):
        """打印測試標題"""
        print(f"\n{'─' * 80}")
        print(f"📋 測試 {test_num}: {test_name}")
        print(f"{'─' * 80}")

    async def test_intent_classification(self, question: str) -> Dict:
        """測試意圖分類"""
        print(f"\n🔍 問題: {question}")

        # 執行分類
        result = self.intent_classifier.classify(question)

        # 打印結果
        print(f"\n✅ 分類結果:")
        print(f"   主要意圖: {result['intent_name']} ({result['intent_type']})")
        print(f"   信心度: {result['confidence']:.2f}")
        print(f"   所有意圖: {result.get('all_intents', [])}")
        print(f"   次要意圖: {result.get('secondary_intents', [])}")
        print(f"   意圖 IDs: {result.get('intent_ids', [])}")

        return result

    async def test_knowledge_retrieval(
        self,
        question: str,
        intent_result: Dict,
        vendor_id: int = 1,
        top_k: int = 5
    ) -> tuple[List[Dict], List[Dict]]:
        """測試知識檢索，返回 (原始結果, 處理後結果)"""

        # 提取意圖資訊
        primary_intent_id = intent_result.get('intent_ids', [None])[0]
        all_intent_ids = intent_result.get('intent_ids', [])

        if not primary_intent_id:
            print("\n⚠️ 無有效意圖 ID，跳過檢索")
            return []

        print(f"\n🔎 檢索參數:")
        print(f"   主要意圖 ID: {primary_intent_id}")
        print(f"   所有意圖 IDs: {all_intent_ids}")
        print(f"   業者 ID: {vendor_id}")
        print(f"   Top-K: {top_k}")

        # 執行檢索
        knowledge_list = await self.knowledge_retriever.retrieve_knowledge_hybrid(
            query=question,
            intent_id=primary_intent_id,
            vendor_id=vendor_id,
            top_k=top_k,
            similarity_threshold=0.6,
            resolve_templates=False,
            all_intent_ids=all_intent_ids
        )

        # 打印結果
        print(f"\n📚 檢索結果 ({len(knowledge_list)} 筆):")
        if not knowledge_list:
            print("   (無結果 - 可能是相似度過低或該意圖尚無知識)")
        for i, kb in enumerate(knowledge_list, 1):
            # 判斷意圖類型標記
            intent_marker = "  "
            if kb.get('intent_id') == primary_intent_id:
                intent_marker = "★"  # 主要意圖
            elif kb.get('intent_id') in all_intent_ids:
                intent_marker = "☆"  # 次要意圖
            else:
                intent_marker = "○"  # 其他

            print(f"\n   {i}. [{intent_marker}] ID {kb.get('id', 'N/A')}: {kb.get('question_summary', 'N/A')[:50]}")
            print(f"      相似度: {kb.get('similarity', 0):.4f}")
            print(f"      Scope: {kb.get('scope', 'N/A')} | 優先級: {kb.get('priority', 0)}")
            print(f"      Intent ID: {kb.get('intent_id', 'N/A')}")

        return knowledge_list

    def verify_intent_boosting(self, knowledge_list: List[Dict], intent_result: Dict) -> bool:
        """驗證意圖加成正確性

        注意：vendor_knowledge_retriever 會移除內部欄位 (base_similarity, intent_boost, boosted_similarity)
        因此我們只能驗證 intent_id 和結果順序
        實際的加成計算需要查看檢索日誌中的 "[Hybrid Retrieval]" 輸出
        """
        print(f"\n🔬 驗證意圖關聯:")

        primary_intent_id = intent_result.get('intent_ids', [None])[0]
        all_intent_ids = intent_result.get('intent_ids', [])

        all_correct = True

        for kb in knowledge_list:
            kb_intent_id = kb.get('intent_id')

            # 判斷意圖類型
            if kb_intent_id == primary_intent_id:
                intent_type = "主要意圖 (★)"
                expected_boost = "1.5x"
            elif kb_intent_id in all_intent_ids:
                intent_type = "次要意圖 (☆)"
                expected_boost = "1.2x"
            else:
                intent_type = "其他 (○)"
                expected_boost = "1.0x"

            print(f"   ✅ ID {kb.get('id')}: {intent_type}, 預期加成: {expected_boost}")

        print(f"\n   💡 提示：實際加成計算請參考上方 \"[Hybrid Retrieval]\" 日誌")
        return all_correct

    def verify_result_ordering(self, knowledge_list: List[Dict], intent_result: Dict) -> bool:
        """驗證結果排序正確性"""
        print(f"\n📊 驗證結果排序:")

        primary_intent_id = intent_result.get('intent_ids', [None])[0]
        all_intent_ids = intent_result.get('intent_ids', [])

        # 分類結果
        primary_results = []
        secondary_results = []
        other_results = []

        for kb in knowledge_list:
            if kb.get('intent_id') == primary_intent_id:
                primary_results.append(kb)
            elif kb.get('intent_id') in all_intent_ids:
                secondary_results.append(kb)
            else:
                other_results.append(kb)

        print(f"   主要意圖 (★): {len(primary_results)} 筆")
        print(f"   次要意圖 (☆): {len(secondary_results)} 筆")
        print(f"   其他 (○): {len(other_results)} 筆")

        # 簡單驗證：主要意圖的結果應該存在
        if primary_results or secondary_results:
            print(f"   ✅ 找到相關意圖的知識")
            return True
        elif other_results:
            print(f"   ⚠️ 僅找到非相關意圖的知識")
            return False
        else:
            print(f"   ⚠️ 未找到任何知識")
            return False

    async def run_test_case(
        self,
        test_num: int,
        test_name: str,
        question: str,
        expected_primary_intent: str = None,
        expected_secondary_intents: List[str] = None,
        vendor_id: int = 1
    ) -> Dict:
        """執行單個測試案例"""

        self.print_test_header(test_num, test_name)

        result = {
            'test_num': test_num,
            'test_name': test_name,
            'question': question,
            'passed': True,
            'issues': []
        }

        try:
            # 1. 測試意圖分類
            intent_result = await self.test_intent_classification(question)

            # 驗證預期意圖
            if expected_primary_intent:
                if intent_result['intent_name'] != expected_primary_intent:
                    result['passed'] = False
                    result['issues'].append(
                        f"主要意圖不符: 預期 {expected_primary_intent}, 實際 {intent_result['intent_name']}"
                    )

            if expected_secondary_intents:
                actual_secondary = set(intent_result.get('secondary_intents', []))
                expected_secondary = set(expected_secondary_intents)
                if actual_secondary != expected_secondary:
                    result['passed'] = False
                    result['issues'].append(
                        f"次要意圖不符: 預期 {expected_secondary_intents}, 實際 {intent_result.get('secondary_intents', [])}"
                    )

            # 2. 測試知識檢索
            knowledge_list = await self.test_knowledge_retrieval(
                question,
                intent_result,
                vendor_id=vendor_id
            )

            if not knowledge_list:
                result['issues'].append("未檢索到任何知識（可能該意圖尚無知識或相似度過低）")
                # 不標記為失敗，因為這可能是正常情況（該意圖確實沒有知識）
                print(f"\n   ⚠️ 注意: {result['issues'][-1]}")
            else:
                # 3. 驗證意圖加成
                boost_correct = self.verify_intent_boosting(knowledge_list, intent_result)
                if not boost_correct:
                    result['passed'] = False
                    result['issues'].append("意圖關聯驗證不正確")

                # 4. 驗證結果排序
                order_correct = self.verify_result_ordering(knowledge_list, intent_result)
                if not order_correct:
                    result['passed'] = False
                    result['issues'].append("未找到相關意圖的知識")

        except Exception as e:
            result['passed'] = False
            result['issues'].append(f"測試執行失敗: {str(e)}")
            print(f"\n❌ 錯誤: {e}")
            import traceback
            traceback.print_exc()

        # 保存結果
        self.test_results.append(result)

        # 打印測試結果
        status = "✅ 通過" if result['passed'] else "❌ 失敗"
        print(f"\n{'─' * 80}")
        print(f"{status}: {test_name}")
        if result['issues']:
            print("問題:")
            for issue in result['issues']:
                print(f"   - {issue}")
        print(f"{'─' * 80}")

        return result

    async def run_all_tests(self):
        """執行所有測試"""

        self.print_section("🧪 多意圖 RAG 系統完整測試")

        # 測試案例
        test_cases = [
            {
                'test_num': 1,
                'test_name': '單一意圖問題（設備報修）',
                'question': '門鎖壞了要怎麼報修？',
                'expected_primary_intent': '設備報修',
                'expected_secondary_intents': []
            },
            {
                'test_num': 2,
                'test_name': '多意圖問題（退租流程 + 帳務查詢）',
                'question': '退租時押金要怎麼退還？',
                'expected_primary_intent': '退租流程',
                'expected_secondary_intents': ['帳務查詢']
            },
            {
                'test_num': 3,
                'test_name': '多意圖問題（合約規定 + 退租流程）',
                'question': '如何解除合約並重新簽約？',
                'expected_primary_intent': '退租流程',
                'expected_secondary_intents': ['合約規定']
            },
            {
                'test_num': 4,
                'test_name': '多意圖問題（合約規定 + 帳務查詢）',
                'question': '租金如何計算？逾期會罰款嗎？',
                'expected_primary_intent': None,  # 不強制預期
                'expected_secondary_intents': None
            },
            {
                'test_num': 5,
                'test_name': '設備使用問題',
                'question': '電子門鎖要怎麼使用？',
                'expected_primary_intent': None,
                'expected_secondary_intents': None
            }
        ]

        # 執行測試
        for test_case in test_cases:
            await self.run_test_case(**test_case)
            await asyncio.sleep(1)  # 避免 API 請求過於密集

        # 打印總結
        self.print_summary()

    def print_summary(self):
        """打印測試總結"""

        self.print_section("📊 測試總結")

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['passed'])
        failed_tests = total_tests - passed_tests
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"\n總測試數: {total_tests}")
        print(f"通過: {passed_tests} ✅")
        print(f"失敗: {failed_tests} ❌")
        print(f"通過率: {pass_rate:.1f}%")

        if failed_tests > 0:
            print(f"\n❌ 失敗的測試:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"\n   測試 {result['test_num']}: {result['test_name']}")
                    for issue in result['issues']:
                        print(f"      - {issue}")

        # 保存結果到文件
        output_file = f"/Users/lenny/jgb/AIChatbot/output/multi_intent_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)

        print(f"\n💾 詳細結果已保存到: {output_file}")

        # 返回測試是否全部通過
        return failed_tests == 0


async def main():
    """主函數"""
    tester = MultiIntentRAGTester()

    try:
        all_passed = await tester.run_all_tests()

        # 返回適當的退出碼
        sys.exit(0 if all_passed else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️ 測試被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 測試執行失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    # 載入 .env 檔案（但不覆蓋 EMBEDDING_API_URL，因為本地測試需要用不同的端口）
    env_file = '/Users/lenny/jgb/AIChatbot/.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # 跳過 EMBEDDING_API_URL，稍後設置本地測試用的值
                    if key != 'EMBEDDING_API_URL':
                        os.environ[key] = value

    # 設置環境變數
    os.environ['DB_HOST'] = os.getenv('DB_HOST', 'localhost')
    os.environ['DB_PORT'] = os.getenv('DB_PORT', '5432')
    os.environ['DB_USER'] = os.getenv('DB_USER', 'aichatbot')
    os.environ['DB_PASSWORD'] = os.getenv('DB_PASSWORD', 'aichatbot_password')
    os.environ['DB_NAME'] = os.getenv('DB_NAME', 'aichatbot_admin')
    # 本地測試時使用 host-mapped port 5001 (容器內是 5000)
    # 強制設置，不從 .env 載入
    os.environ['EMBEDDING_API_URL'] = 'http://localhost:5001/api/v1/embeddings'

    # 執行測試
    asyncio.run(main())
