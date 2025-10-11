#!/usr/bin/env python3
"""
RAG 評分品質測試系統
驗證意圖加成機制是否真正提升答案品質

測試維度：
1. 相關性 (Relevance): 答案是否回答問題
2. 完整性 (Completeness): 答案是否完整
3. 意圖匹配 (Intent Match): 意圖是否正確
4. 排序質量 (Ranking Quality): 最佳答案是否排在前面

測試場景：
- 多意圖問題（主要 + 次要）
- 單意圖問題
- 邊界情況（低相似度高意圖 vs 高相似度低意圖）
- 錯誤分類情況
"""

import sys
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from openai import OpenAI

# 添加路徑
sys.path.insert(0, '/Users/lenny/jgb/AIChatbot/rag-orchestrator')

from services.intent_classifier import IntentClassifier
from services.vendor_knowledge_retriever import VendorKnowledgeRetriever


class ScoringQualityTester:
    """評分品質測試器"""

    def __init__(self):
        self.intent_classifier = IntentClassifier(use_database=True)
        self.knowledge_retriever = VendorKnowledgeRetriever()
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.test_results = []

    def print_section(self, title: str):
        """打印區塊標題"""
        print("\n" + "=" * 80)
        print(f"  {title}")
        print("=" * 80)

    def print_subsection(self, title: str):
        """打印子標題"""
        print(f"\n{'─' * 80}")
        print(f"📋 {title}")
        print(f"{'─' * 80}")

    async def retrieve_with_different_boosts(
        self,
        query: str,
        intent_id: int,
        all_intent_ids: List[int],
        vendor_id: int = 1,
        top_k: int = 5
    ) -> Dict[str, List[Dict]]:
        """
        使用不同的加成倍數檢索，比較效果

        Returns:
            {
                'baseline': [...],      # 無加成 (1.0x)
                'current': [...],       # 當前 (1.5x/1.2x)
                'aggressive': [...],    # 激進 (2.0x/1.5x)
                'conservative': [...]   # 保守 (1.3x/1.1x)
            }
        """
        results = {}

        # 測試配置
        boost_configs = {
            'baseline': (1.0, 1.0),
            'current': (1.5, 1.2),
            'aggressive': (2.0, 1.5),
            'conservative': (1.3, 1.1)
        }

        print(f"\n🔍 測試不同加成倍數對問題的影響：")
        print(f"   問題: {query}")
        print(f"   主要意圖 ID: {intent_id}")
        print(f"   所有意圖 IDs: {all_intent_ids}")

        for config_name, (primary_boost, secondary_boost) in boost_configs.items():
            print(f"\n   ⚙️  配置: {config_name} (主要: {primary_boost}x, 次要: {secondary_boost}x)")

            # 這裡需要修改 retriever 以支持自定義 boost
            # 暫時使用當前實現
            knowledge_list = await self.knowledge_retriever.retrieve_knowledge_hybrid(
                query=query,
                intent_id=intent_id,
                vendor_id=vendor_id,
                top_k=top_k,
                similarity_threshold=0.5,  # 降低閾值以觀察更多結果
                resolve_templates=False,
                all_intent_ids=all_intent_ids
            )

            results[config_name] = knowledge_list
            print(f"      找到 {len(knowledge_list)} 筆結果")

        return results

    async def evaluate_answer_quality_with_llm(
        self,
        question: str,
        answer: str,
        expected_intent: str
    ) -> Dict:
        """
        使用 LLM 評估答案品質

        Returns:
            {
                'relevance': 1-5,
                'completeness': 1-5,
                'accuracy': 1-5,
                'intent_match': 1-5,
                'overall': 1-5,
                'reasoning': str
            }
        """
        prompt = f"""請評估以下問答的品質（1-5分，5分最佳）：

問題：{question}
預期意圖：{expected_intent}
答案：{answer}

請從以下維度評分：
1. 相關性 (Relevance): 答案是否直接回答問題？
2. 完整性 (Completeness): 答案是否完整涵蓋問題所問？
3. 準確性 (Accuracy): 答案內容是否準確可靠？
4. 意圖匹配 (Intent Match): 答案是否符合預期意圖？

請以 JSON 格式回覆：
{{
    "relevance": <1-5>,
    "completeness": <1-5>,
    "accuracy": <1-5>,
    "intent_match": <1-5>,
    "overall": <1-5>,
    "reasoning": "簡短說明評分理由"
}}"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            print(f"⚠️  LLM 評估失敗: {e}")
            return {
                'relevance': 0,
                'completeness': 0,
                'accuracy': 0,
                'intent_match': 0,
                'overall': 0,
                'reasoning': f"評估失敗: {str(e)}"
            }

    def calculate_ndcg(
        self,
        retrieved_results: List[Dict],
        relevance_scores: List[float],
        k: int = 5
    ) -> float:
        """
        計算 NDCG@K (Normalized Discounted Cumulative Gain)
        衡量排序質量

        Args:
            retrieved_results: 檢索結果列表
            relevance_scores: 對應的相關性分數列表
            k: 計算前 K 個結果

        Returns:
            NDCG 分數 (0-1)
        """
        import math

        if not relevance_scores or len(relevance_scores) == 0:
            return 0.0

        # DCG: Discounted Cumulative Gain
        dcg = 0.0
        for i, score in enumerate(relevance_scores[:k], 1):
            dcg += (2 ** score - 1) / math.log2(i + 1)

        # IDCG: Ideal DCG (最佳排序)
        ideal_scores = sorted(relevance_scores, reverse=True)[:k]
        idcg = 0.0
        for i, score in enumerate(ideal_scores, 1):
            idcg += (2 ** score - 1) / math.log2(i + 1)

        # NDCG
        if idcg == 0:
            return 0.0
        return dcg / idcg

    async def test_case_with_quality_assessment(
        self,
        test_num: int,
        test_name: str,
        question: str,
        expected_intent: str,
        expected_best_answers: List[str],
        vendor_id: int = 1
    ) -> Dict:
        """
        執行單個測試並評估答案品質

        Args:
            expected_best_answers: 預期的最佳答案（knowledge ID 或 question_summary）
        """
        self.print_subsection(f"測試 {test_num}: {test_name}")

        result = {
            'test_num': test_num,
            'test_name': test_name,
            'question': question,
            'expected_intent': expected_intent,
            'expected_best_answers': expected_best_answers,
            'passed': True,
            'issues': [],
            'quality_scores': {},
            'ndcg_scores': {}
        }

        try:
            # 1. 意圖分類
            print(f"\n🔍 問題: {question}")
            intent_result = self.intent_classifier.classify(question)
            print(f"   分類結果: {intent_result['intent_name']} (信心度: {intent_result['confidence']:.2f})")

            primary_intent_id = intent_result.get('intent_ids', [None])[0]
            all_intent_ids = intent_result.get('intent_ids', [])

            if not primary_intent_id:
                result['passed'] = False
                result['issues'].append("意圖分類失敗")
                return result

            # 2. 檢索知識（當前配置）
            print(f"\n📚 檢索知識 (使用當前配置):")
            knowledge_list = await self.knowledge_retriever.retrieve_knowledge_hybrid(
                query=question,
                intent_id=primary_intent_id,
                vendor_id=vendor_id,
                top_k=5,
                similarity_threshold=0.5,
                resolve_templates=False,
                all_intent_ids=all_intent_ids
            )

            if not knowledge_list:
                result['issues'].append("未檢索到任何知識")
                print("   ⚠️  未檢索到任何知識")
            else:
                print(f"   找到 {len(knowledge_list)} 筆結果")

                # 3. 使用 LLM 評估每個答案的品質
                print(f"\n🤖 使用 LLM 評估答案品質:")
                quality_scores = []

                for i, kb in enumerate(knowledge_list[:3], 1):  # 只評估前 3 個
                    print(f"\n   評估答案 {i}: ID {kb.get('id')}, 相似度 {kb.get('similarity', 0):.3f}")

                    quality = await self.evaluate_answer_quality_with_llm(
                        question=question,
                        answer=kb.get('answer', ''),
                        expected_intent=expected_intent
                    )

                    quality_scores.append(quality)

                    print(f"      相關性: {quality['relevance']}/5")
                    print(f"      完整性: {quality['completeness']}/5")
                    print(f"      準確性: {quality['accuracy']}/5")
                    print(f"      意圖匹配: {quality['intent_match']}/5")
                    print(f"      綜合評分: {quality['overall']}/5")
                    print(f"      理由: {quality['reasoning']}")

                result['quality_scores'] = quality_scores

                # 4. 計算 NDCG（使用相關性分數）
                if quality_scores:
                    relevance_scores = [q['relevance'] for q in quality_scores]
                    ndcg = self.calculate_ndcg(
                        knowledge_list[:3],
                        relevance_scores,
                        k=3
                    )
                    result['ndcg_scores']['current'] = ndcg
                    print(f"\n   📊 NDCG@3: {ndcg:.3f}")

                # 5. 檢查最佳答案是否在前 3
                top_3_summaries = [kb.get('question_summary', '') for kb in knowledge_list[:3]]
                found_best = False
                for expected in expected_best_answers:
                    if any(expected in summary for summary in top_3_summaries):
                        found_best = True
                        break

                if found_best:
                    print(f"\n   ✅ 預期的最佳答案在 Top-3 中")
                else:
                    print(f"\n   ⚠️  預期的最佳答案不在 Top-3 中")
                    result['issues'].append("預期最佳答案未在前 3 名")

                # 6. 分析評分與相似度的關係
                print(f"\n   📈 評分與相似度相關性分析:")
                if quality_scores and len(knowledge_list) >= 3:
                    similarities = [kb.get('similarity', 0) for kb in knowledge_list[:3]]
                    overall_scores = [q['overall'] for q in quality_scores]

                    # 簡單相關性檢查
                    for i in range(3):
                        print(f"      結果 {i+1}: 相似度 {similarities[i]:.3f}, 品質 {overall_scores[i]}/5")

                    # 檢查是否相似度高的答案品質也高
                    if similarities[0] > similarities[1] and overall_scores[0] < overall_scores[1]:
                        result['issues'].append("排序問題：相似度最高的答案品質反而較低")

        except Exception as e:
            result['passed'] = False
            result['issues'].append(f"測試執行失敗: {str(e)}")
            print(f"\n❌ 錯誤: {e}")
            import traceback
            traceback.print_exc()

        # 保存結果
        self.test_results.append(result)

        # 打印測試結果
        status = "✅ 通過" if result['passed'] and len(result['issues']) == 0 else "⚠️  需注意"
        print(f"\n{'─' * 80}")
        print(f"{status}: {test_name}")
        if result['issues']:
            print("發現的問題:")
            for issue in result['issues']:
                print(f"   - {issue}")
        print(f"{'─' * 80}")

        return result

    async def run_all_tests(self):
        """執行所有評分品質測試"""

        self.print_section("🧪 RAG 評分品質完整測試")

        # 測試案例集
        test_cases = [
            {
                'test_num': 1,
                'test_name': '多意圖問題 - 退租押金',
                'question': '退租時押金要怎麼退還？',
                'expected_intent': '退租流程',
                'expected_best_answers': ['退租押金如何退還', '押金']
            },
            {
                'test_num': 2,
                'test_name': '多意圖問題 - 解除合約',
                'question': '如何解除合約並重新簽約？',
                'expected_intent': '退租流程',
                'expected_best_answers': ['解除合約', '重新簽約']
            },
            {
                'test_num': 3,
                'test_name': '單意圖問題 - 租金計算',
                'question': '租金如何計算？逾期會罰款嗎？',
                'expected_intent': '合約規定',
                'expected_best_answers': ['租金', '逾期', '罰款']
            },
            {
                'test_num': 4,
                'test_name': '邊界情況 - 一般性問題',
                'question': '我想了解租約的詳細內容',
                'expected_intent': '合約規定',
                'expected_best_answers': ['租約', '合約']
            }
        ]

        # 執行測試
        for test_case in test_cases:
            await self.test_case_with_quality_assessment(**test_case)
            await asyncio.sleep(2)  # 避免 API 請求過於密集

        # 打印總結
        self.print_summary()

    def print_summary(self):
        """打印測試總結"""

        self.print_section("📊 評分品質測試總結")

        total_tests = len(self.test_results)
        tests_with_issues = sum(1 for r in self.test_results if len(r['issues']) > 0)

        print(f"\n總測試數: {total_tests}")
        print(f"發現問題: {tests_with_issues} 個測試")

        # 統計平均 NDCG
        ndcg_scores = [r['ndcg_scores'].get('current', 0) for r in self.test_results if r['ndcg_scores']]
        if ndcg_scores:
            avg_ndcg = sum(ndcg_scores) / len(ndcg_scores)
            print(f"\n平均 NDCG@3: {avg_ndcg:.3f}")
            print(f"   (1.0 = 完美排序, 0.0 = 完全錯誤)")

        # 統計平均品質分數
        all_quality_scores = []
        for r in self.test_results:
            if r.get('quality_scores'):
                all_quality_scores.extend(r['quality_scores'])

        if all_quality_scores:
            avg_relevance = sum(q['relevance'] for q in all_quality_scores) / len(all_quality_scores)
            avg_completeness = sum(q['completeness'] for q in all_quality_scores) / len(all_quality_scores)
            avg_accuracy = sum(q['accuracy'] for q in all_quality_scores) / len(all_quality_scores)
            avg_intent_match = sum(q['intent_match'] for q in all_quality_scores) / len(all_quality_scores)
            avg_overall = sum(q['overall'] for q in all_quality_scores) / len(all_quality_scores)

            print(f"\n平均答案品質分數 (5分制):")
            print(f"   相關性: {avg_relevance:.2f}")
            print(f"   完整性: {avg_completeness:.2f}")
            print(f"   準確性: {avg_accuracy:.2f}")
            print(f"   意圖匹配: {avg_intent_match:.2f}")
            print(f"   綜合評分: {avg_overall:.2f}")

        # 顯示所有問題
        if tests_with_issues > 0:
            print(f"\n⚠️  發現的問題總結:")
            issue_counts = {}
            for result in self.test_results:
                for issue in result['issues']:
                    issue_counts[issue] = issue_counts.get(issue, 0) + 1

            for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"   - {issue} ({count} 次)")

        # 保存結果到文件
        output_file = f"/Users/lenny/jgb/AIChatbot/output/scoring_quality_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'tests_with_issues': tests_with_issues,
                    'avg_ndcg': avg_ndcg if ndcg_scores else 0,
                    'avg_quality': {
                        'relevance': avg_relevance if all_quality_scores else 0,
                        'completeness': avg_completeness if all_quality_scores else 0,
                        'accuracy': avg_accuracy if all_quality_scores else 0,
                        'intent_match': avg_intent_match if all_quality_scores else 0,
                        'overall': avg_overall if all_quality_scores else 0,
                    } if all_quality_scores else {}
                },
                'test_results': self.test_results
            }, f, ensure_ascii=False, indent=2)

        print(f"\n💾 詳細結果已保存到: {output_file}")

        # 提供改善建議
        self.print_recommendations()

    def print_recommendations(self):
        """根據測試結果提供改善建議"""

        self.print_section("💡 改善建議")

        # 分析 NDCG 分數
        ndcg_scores = [r['ndcg_scores'].get('current', 0) for r in self.test_results if r['ndcg_scores']]
        if ndcg_scores:
            avg_ndcg = sum(ndcg_scores) / len(ndcg_scores)

            if avg_ndcg < 0.7:
                print("\n⚠️  NDCG 分數較低 (<0.7)，建議:")
                print("   1. 調整意圖加成倍數 (當前 1.5x/1.2x)")
                print("   2. 降低相似度閾值 (當前 0.6)")
                print("   3. 檢查 Scope 權重 (1000/500/100)")
            elif avg_ndcg < 0.85:
                print("\n✅ NDCG 分數中等 (0.7-0.85)，可考慮微調:")
                print("   1. 對主要意圖可能給予更高加成 (如 1.6x)")
                print("   2. 考慮引入意圖信心度作為額外權重")
            else:
                print("\n🎉 NDCG 分數優秀 (>0.85)，排序品質良好！")

        # 分析品質分數
        all_quality_scores = []
        for r in self.test_results:
            if r.get('quality_scores'):
                all_quality_scores.extend(r['quality_scores'])

        if all_quality_scores:
            avg_overall = sum(q['overall'] for q in all_quality_scores) / len(all_quality_scores)

            if avg_overall < 3.5:
                print("\n⚠️  答案品質分數較低 (<3.5/5)，建議:")
                print("   1. 檢查知識庫內容品質")
                print("   2. 提高相似度閾值以過濾低質量答案")
                print("   3. 加強意圖分類準確性")
            elif avg_overall < 4.0:
                print("\n✅ 答案品質分數中等 (3.5-4.0/5):")
                print("   1. 繼續優化知識庫內容")
                print("   2. 考慮引入重排序機制")
            else:
                print("\n🎉 答案品質分數優秀 (>4.0/5)！")

        # 常見問題建議
        issue_counts = {}
        for result in self.test_results:
            for issue in result['issues']:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1

        if "預期最佳答案未在前 3 名" in issue_counts:
            count = issue_counts["預期最佳答案未在前 3 名"]
            print(f"\n⚠️  有 {count} 個測試的最佳答案未在前 3:")
            print("   建議:")
            print("   1. 增加意圖加成倍數")
            print("   2. 調整 Scope 權重")
            print("   3. 檢查 embedding 質量")

        if "排序問題：相似度最高的答案品質反而較低" in issue_counts:
            print(f"\n⚠️  存在排序品質問題:")
            print("   建議:")
            print("   1. 引入答案長度/完整性因子")
            print("   2. 考慮使用重排序 (Reranking) 模型")
            print("   3. 結合人工標註優化排序")


async def main():
    """主函數"""
    tester = ScoringQualityTester()

    try:
        await tester.run_all_tests()
        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n⚠️ 測試被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 測試執行失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    # 載入環境變數
    env_file = '/Users/lenny/jgb/AIChatbot/.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key != 'EMBEDDING_API_URL':
                        os.environ[key] = value

    # 設置環境變數
    os.environ['DB_HOST'] = os.getenv('DB_HOST', 'localhost')
    os.environ['DB_PORT'] = os.getenv('DB_PORT', '5432')
    os.environ['DB_USER'] = os.getenv('DB_USER', 'aichatbot')
    os.environ['DB_PASSWORD'] = os.getenv('DB_PASSWORD', 'aichatbot_password')
    os.environ['DB_NAME'] = os.getenv('DB_NAME', 'aichatbot_admin')
    os.environ['EMBEDDING_API_URL'] = 'http://localhost:5001/api/v1/embeddings'

    # 執行測試
    asyncio.run(main())
