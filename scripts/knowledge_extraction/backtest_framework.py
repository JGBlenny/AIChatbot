"""
知識庫回測框架
測試 RAG 系統對測試問題的回答準確度

支援三種品質評估模式：
- basic: 快速評估（關鍵字、分類、信心度）
- detailed: LLM 深度品質評估
- hybrid: 混合模式（推薦）
"""

import os
import sys
import time
import math
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
import requests
import json
from openai import OpenAI
import psycopg2
from psycopg2.extras import RealDictCursor

class BacktestFramework:
    """回測框架"""

    def __init__(
        self,
        base_url: str = "http://localhost:8100",
        vendor_id: int = 1,
        quality_mode: str = "basic",  # basic, detailed, hybrid
        use_database: bool = True  # 是否使用資料庫（預設 True）
    ):
        self.base_url = base_url
        self.vendor_id = vendor_id
        self.quality_mode = quality_mode
        self.use_database = use_database
        self.results = []
        self.run_started_at = datetime.now()  # 記錄開始時間

        # 資料庫連線配置
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'user': os.getenv('DB_USER', 'aichatbot'),
            'password': os.getenv('DB_PASSWORD', 'aichatbot_password'),
            'database': os.getenv('DB_NAME', 'aichatbot_admin')
        }

        # 如果使用 detailed 或 hybrid 模式，初始化 OpenAI 客戶端
        if quality_mode in ['detailed', 'hybrid']:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("⚠️  警告：未設定 OPENAI_API_KEY，將降級為 basic 模式")
                self.quality_mode = 'basic'
            else:
                self.openai_client = OpenAI(api_key=api_key)
                print(f"✅ 品質評估模式: {quality_mode}")
        else:
            print(f"✅ 品質評估模式: basic（快速模式）")

        # 顯示數據源
        if self.use_database:
            print(f"✅ 測試題庫來源: 資料庫 ({self.db_config['database']})")
        else:
            print(f"✅ 測試題庫來源: Excel 檔案")

    def get_db_connection(self):
        """建立資料庫連線"""
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)

    def load_test_scenarios_from_db(
        self,
        difficulty: str = None,
        limit: int = None,
        min_avg_score: float = None,
        prioritize_failed: bool = True
    ) -> List[Dict]:
        """從資料庫載入測試情境

        Args:
            difficulty: 難度篩選 (easy, medium, hard)
            limit: 限制數量
            min_avg_score: 最低平均分數篩選（優先選擇低分測試）
            prioritize_failed: 優先選擇失敗率高的測試

        Returns:
            測試情境列表
        """
        print(f"📖 從資料庫載入測試情境...")
        if difficulty:
            print(f"   難度: {difficulty}")
        if limit:
            print(f"   限制: {limit} 個")
        if prioritize_failed:
            print(f"   策略: 優先測試低分/失敗案例")

        conn = self.get_db_connection()
        cur = conn.cursor()

        try:
            # 建立查詢
            query = """
                SELECT
                    ts.id,
                    ts.test_question,
                    ts.expected_category,
                    ts.expected_keywords,
                    ts.difficulty,
                    ts.notes,
                    ts.priority,
                    ts.total_runs,
                    ts.pass_count,
                    ts.avg_score,
                    CASE
                        WHEN ts.total_runs > 0
                        THEN 1.0 - (ts.pass_count::float / ts.total_runs)
                        ELSE 0.5
                    END as fail_rate
                FROM test_scenarios ts
                WHERE ts.is_active = TRUE
                  AND ts.status = 'approved'
            """
            params = []

            # 篩選難度
            if difficulty:
                query += " AND ts.difficulty = %s"
                params.append(difficulty)

            # 篩選最低分數
            if min_avg_score is not None:
                query += " AND (ts.avg_score IS NULL OR ts.avg_score <= %s)"
                params.append(min_avg_score)

            # 排序策略
            if prioritize_failed:
                # 優先選擇：失敗率高、平均分低、優先級高的測試
                query += " ORDER BY fail_rate DESC, COALESCE(ts.avg_score, 0) ASC, ts.priority DESC, ts.id"
            else:
                # 預設排序：優先級高的先測試
                query += " ORDER BY ts.priority DESC, ts.id"

            # 限制數量
            if limit:
                query += " LIMIT %s"
                params.append(limit)

            cur.execute(query, params)
            rows = cur.fetchall()

            # 轉換為字典列表
            scenarios = []
            for row in rows:
                scenario = dict(row)
                # 轉換關鍵字陣列為逗號分隔字串（與 Excel 格式一致）
                if scenario.get('expected_keywords') and isinstance(scenario['expected_keywords'], list):
                    scenario['expected_keywords'] = ', '.join(scenario['expected_keywords'])
                scenarios.append(scenario)

            print(f"   ✅ 載入 {len(scenarios)} 個測試情境")
            return scenarios

        finally:
            cur.close()
            conn.close()

    def load_test_scenarios(
        self,
        excel_path: str = None,
        difficulty: str = None,
        limit: int = None,
        prioritize_failed: bool = True
    ) -> List[Dict]:
        """載入測試情境（支援資料庫與 Excel 兩種模式）

        Args:
            excel_path: Excel 檔案路徑（向後相容）
            difficulty: 難度篩選
            limit: 限制數量
            prioritize_failed: 優先選擇失敗率高的測試（僅資料庫模式）

        Returns:
            測試情境列表
        """
        if self.use_database:
            # 使用資料庫模式
            return self.load_test_scenarios_from_db(
                difficulty=difficulty,
                limit=limit,
                prioritize_failed=prioritize_failed
            )
        elif excel_path:
            # 使用 Excel 模式（向後相容）
            print(f"📖 載入測試情境: {excel_path}")
            df = pd.read_excel(excel_path, engine='openpyxl')
            scenarios = df.to_dict('records')
            print(f"   ✅ 載入 {len(scenarios)} 個測試情境")
            return scenarios
        else:
            raise ValueError("必須提供 excel_path 或啟用資料庫模式")

    def query_rag_system(self, question: str) -> Dict:
        """查詢 RAG 系統"""
        url = f"{self.base_url}/api/v1/message"

        payload = {
            "message": question,
            "vendor_id": self.vendor_id,
            "mode": "tenant",
            "include_sources": True
        }

        # ⭐ 回測專用：檢查是否禁用答案合成
        disable_synthesis = os.getenv("BACKTEST_DISABLE_ANSWER_SYNTHESIS", "false").lower() == "true"
        if disable_synthesis:
            payload["disable_answer_synthesis"] = True
            # 只在第一次請求時顯示提示
            if not hasattr(self, '_synthesis_disabled_logged'):
                print("   ⚙️  回測模式：答案合成已禁用（BACKTEST_DISABLE_ANSWER_SYNTHESIS=true）")
                self._synthesis_disabled_logged = True

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"   ❌ API 請求失敗: {e}")
            return None

    def evaluate_answer(
        self,
        test_scenario: Dict,
        system_response: Dict
    ) -> Dict:
        """評估答案品質"""

        if not system_response:
            return {
                "passed": False,
                "score": 0.0,
                "checks": {},
                "reason": "系統無回應",
                "optimization_tips": "系統無法回應，請檢查 RAG API 是否正常運作"
            }

        evaluation = {
            "passed": True,
            "score": 0.0,
            "checks": {},
            "optimization_tips": []
        }

        # 1. 檢查分類是否正確（支援多 Intent）
        expected_category = test_scenario.get('expected_category', '')
        actual_intent = system_response.get('intent_name', '')
        all_intents = system_response.get('all_intents')

        # 確保 all_intents 是列表
        if all_intents is None or not all_intents:
            all_intents = [actual_intent] if actual_intent else []

        if expected_category:
            # 檢查預期分類是否在主要意圖或所有相關意圖中
            # 支援部分匹配（例如「帳務問題」可以匹配「帳務查詢」）
            def fuzzy_match(expected: str, actual: str) -> bool:
                """模糊匹配：檢查是否有共同的關鍵字"""
                # 直接包含關係
                if expected in actual or actual in expected:
                    return True
                # 提取前兩個字做模糊匹配（例如「帳務」）
                if len(expected) >= 2 and len(actual) >= 2:
                    if expected[:2] in actual or actual[:2] in expected:
                        return True
                return False

            category_match = (
                fuzzy_match(expected_category, actual_intent) or
                any(fuzzy_match(expected_category, intent) for intent in all_intents)
            )

            evaluation['checks']['category_match'] = category_match
            evaluation['checks']['matched_intents'] = all_intents if category_match else []

            if category_match:
                evaluation['score'] += 0.3
                # 如果匹配的是次要意圖，給予提示
                if expected_category not in actual_intent and actual_intent not in expected_category:
                    evaluation['optimization_tips'].append(
                        f"✅ 多意圖匹配: 預期「{expected_category}」在次要意圖中找到\n"
                        f"   主要意圖: {actual_intent}，所有意圖: {all_intents}"
                    )
            else:
                # 分類不匹配 - 提供優化建議
                evaluation['optimization_tips'].append(
                    f"意圖分類不匹配: 預期「{expected_category}」但識別為「{actual_intent}」\n"
                    f"   所有意圖: {all_intents}\n"
                    f"💡 建議: 在意圖管理中編輯「{actual_intent}」意圖，添加更多相關關鍵字"
                )

        # 2. 檢查是否包含預期關鍵字
        expected_keywords = test_scenario.get('expected_keywords', [])
        if isinstance(expected_keywords, str):
            expected_keywords = [k.strip() for k in expected_keywords.split(',') if k.strip()]
        elif expected_keywords is None:
            expected_keywords = []

        answer = system_response.get('answer', '')
        keyword_matches = sum(1 for kw in expected_keywords if kw in answer)
        keyword_ratio = keyword_matches / len(expected_keywords) if expected_keywords else 0

        evaluation['checks']['keyword_coverage'] = keyword_ratio
        evaluation['score'] += keyword_ratio * 0.4

        if keyword_ratio < 0.5 and expected_keywords:
            missing_keywords = [kw for kw in expected_keywords if kw not in answer]
            evaluation['optimization_tips'].append(
                f"答案缺少關鍵字: {', '.join(missing_keywords)}\n"
                f"💡 建議: 在知識庫中補充相關內容，或優化知識的關鍵字"
            )

        # 3. 檢查信心度
        confidence = system_response.get('confidence', 0)
        evaluation['checks']['confidence'] = confidence
        if confidence >= 0.7:
            evaluation['score'] += 0.3
        elif confidence < 0.5:
            evaluation['optimization_tips'].append(
                f"信心度過低 ({confidence:.2f})\n"
                f"💡 建議: 系統對答案不確定，可能需要新增更相關的知識"
            )

        # 4. 判定是否通過
        evaluation['passed'] = evaluation['score'] >= 0.6

        # 5. 生成優化建議摘要
        if not evaluation['passed']:
            if not evaluation['optimization_tips']:
                evaluation['optimization_tips'].append(
                    f"整體得分過低 ({evaluation['score']:.2f}/1.0)\n"
                    f"💡 建議: 檢查知識庫是否有相關內容，或優化現有知識的描述"
                )
        else:
            if evaluation['optimization_tips']:
                # 即使通過，如果有優化建議也保留
                evaluation['optimization_tips'].insert(0, "✅ 測試通過，但仍有優化空間:")

        return evaluation

    def llm_evaluate_answer(
        self,
        question: str,
        answer: str,
        expected_intent: str
    ) -> Dict:
        """使用 LLM 評估答案品質

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

    def evaluate_answer_with_quality(
        self,
        test_scenario: Dict,
        system_response: Dict
    ) -> Dict:
        """整合基礎評估和 LLM 品質評估

        Returns:
            {
                'basic_eval': Dict,  # 基礎評估結果
                'quality_eval': Dict,  # LLM 品質評估（如果啟用）
                'overall_score': float,  # 混合評分
                'passed': bool
            }
        """
        # 1. 執行基礎評估（保持向後相容）
        basic_eval = self.evaluate_answer(test_scenario, system_response)

        # 2. 如果是 basic 模式，直接返回
        if self.quality_mode == 'basic':
            return {
                'basic_eval': basic_eval,
                'overall_score': basic_eval['score'],
                'passed': basic_eval['passed']
            }

        # 3. 執行 LLM 評估
        question = test_scenario.get('test_question', '')
        answer = system_response.get('answer', '') if system_response else ''
        expected_intent = test_scenario.get('expected_category', '')

        if not answer:
            # 沒有答案，只使用基礎評估
            return {
                'basic_eval': basic_eval,
                'overall_score': basic_eval['score'],
                'passed': basic_eval['passed']
            }

        quality_eval = self.llm_evaluate_answer(question, answer, expected_intent)

        # 4. 計算混合評分
        overall_score = self._calculate_hybrid_score(basic_eval, quality_eval)

        # 5. 判定是否通過
        passed = self._determine_pass_status(basic_eval, quality_eval, overall_score)

        return {
            'basic_eval': basic_eval,
            'quality_eval': quality_eval,
            'overall_score': overall_score,
            'passed': passed
        }

    def _calculate_hybrid_score(self, basic_eval: Dict, quality_eval: Dict) -> float:
        """計算混合評分

        權重分配：
        - basic 模式：100% 基礎評分
        - hybrid 模式：40% 基礎 + 60% LLM
        - detailed 模式：100% LLM
        """
        basic_score = basic_eval['score']
        quality_score = quality_eval['overall'] / 5.0  # 標準化到 0-1

        if self.quality_mode == 'hybrid':
            return 0.4 * basic_score + 0.6 * quality_score
        elif self.quality_mode == 'detailed':
            return quality_score
        else:
            return basic_score

    def _determine_pass_status(
        self,
        basic_eval: Dict,
        quality_eval: Dict,
        hybrid_score: float
    ) -> bool:
        """判定是否通過"""

        if self.quality_mode == 'hybrid':
            # 混合模式：綜合分數 >= 0.5 且完整性 >= 2.5
            return (
                hybrid_score >= 0.5 and
                quality_eval.get('completeness', 0) >= 2.5
            )
        elif self.quality_mode == 'detailed':
            # 詳細模式：綜合 >= 3 且完整性 >= 3
            return (
                quality_eval.get('overall', 0) >= 3 and
                quality_eval.get('completeness', 0) >= 3
            )
        else:
            # 基礎模式：現有邏輯
            return basic_eval['passed']

    def calculate_ndcg(self, results: List[Dict], k: int = 3) -> Dict:
        """計算所有測試的平均 NDCG@K

        NDCG (Normalized Discounted Cumulative Gain) 衡量排序品質

        Returns:
            {
                'avg_ndcg': float,  # 平均 NDCG
                'count': int  # 計算數量
            }
        """
        def calculate_single_ndcg(relevance_scores: List[float]) -> float:
            """計算單個測試的 NDCG@K"""
            if not relevance_scores or len(relevance_scores) == 0:
                return 0.0

            # DCG (Discounted Cumulative Gain)
            dcg = 0.0
            for i, score in enumerate(relevance_scores[:k], 1):
                dcg += (2 ** score - 1) / math.log2(i + 1)

            # IDCG (Ideal DCG) - 最佳排序
            ideal_scores = sorted(relevance_scores, reverse=True)[:k]
            idcg = 0.0
            for i, score in enumerate(ideal_scores, 1):
                idcg += (2 ** score - 1) / math.log2(i + 1)

            return dcg / idcg if idcg > 0 else 0.0

        # 計算每個測試的 NDCG
        ndcg_scores = []
        for result in results:
            if 'quality_eval' in result and result['quality_eval']:
                # 使用 LLM 評估的相關性分數
                relevance = result['quality_eval'].get('relevance', 0)
                if relevance > 0:
                    # 這裡簡化處理，假設每個測試只有一個答案
                    # 實際應用中可以基於多個知識來源計算 NDCG
                    ndcg_scores.append(relevance / 5.0)  # 標準化到 0-1

        if ndcg_scores:
            avg_ndcg = sum(ndcg_scores) / len(ndcg_scores)
            return {
                'avg_ndcg': avg_ndcg,
                'count': len(ndcg_scores)
            }

        return {'avg_ndcg': 0.0, 'count': 0}

    def run_backtest(
        self,
        test_scenarios: List[Dict],
        sample_size: int = None,
        delay: float = 1.0
    ) -> List[Dict]:
        """執行回測"""

        print(f"\n🧪 開始回測...")
        print(f"   測試情境數：{len(test_scenarios)}")
        if sample_size:
            print(f"   抽樣測試：{sample_size} 個")
            test_scenarios = test_scenarios[:sample_size]

        results = []

        for i, scenario in enumerate(test_scenarios, 1):
            question = scenario.get('test_question', '')
            if not question:
                continue

            print(f"\n[{i}/{len(test_scenarios)}] 測試問題: {question[:50]}...")

            # 查詢系統
            system_response = self.query_rag_system(question)

            # 評估答案（使用增強評估）
            evaluation_result = self.evaluate_answer_with_quality(scenario, system_response)

            # 提取評估資訊（向後相容）
            if 'basic_eval' in evaluation_result:
                evaluation = evaluation_result['basic_eval']
                quality_eval = evaluation_result.get('quality_eval')
                overall_score = evaluation_result.get('overall_score', evaluation['score'])
                passed = evaluation_result.get('passed', evaluation['passed'])
            else:
                # 向後相容（如果只返回基礎評估）
                evaluation = evaluation_result
                quality_eval = None
                overall_score = evaluation['score']
                passed = evaluation['passed']

            # 提取知識來源資訊
            sources = system_response.get('sources', []) if system_response else []
            # 確保 sources 是列表
            if sources is None:
                sources = []
            source_ids = [s.get('id') for s in sources if s.get('id')]
            source_summary = '; '.join([
                f"[{s.get('id', 'N/A')}] {s.get('question_summary', 'N/A')[:40]}"
                for s in sources[:3]  # 只顯示前 3 個
            ]) if sources else '無來源'

            # 生成知識庫管理界面的直接鏈接
            knowledge_urls = []
            if source_ids:
                # 方案1：單個知識的直接鏈接
                for kb_id in source_ids[:3]:  # 只顯示前3個
                    knowledge_urls.append(f"http://localhost:8080/#/knowledge?search={kb_id}")
                # 方案2：批量查詢鏈接（用 IDs 作為搜尋條件）
                ids_param = ','.join(map(str, source_ids))
                batch_url = f"http://localhost:8080/#/knowledge?ids={ids_param}"
            else:
                batch_url = "http://localhost:8080/#/knowledge"

            knowledge_links = '\n'.join(knowledge_urls) if knowledge_urls else '無'

            # 記錄結果
            result = {
                'test_id': i,
                'scenario_id': scenario.get('id'),  # 新增：測試情境 ID（用於資料庫）
                'test_question': question,
                'expected_category': scenario.get('expected_category', ''),
                'actual_intent': system_response.get('intent_name', '') if system_response else '',
                'all_intents': system_response.get('all_intents', []) if system_response else [],
                'system_answer': system_response.get('answer', '')[:200] if system_response else '',
                'confidence': system_response.get('confidence', 0) if system_response else 0,
                'score': evaluation['score'],
                'overall_score': overall_score,  # 新增：混合評分
                'passed': passed,  # 使用混合判定
                'category_match': evaluation['checks'].get('category_match', False),
                'keyword_coverage': evaluation['checks'].get('keyword_coverage', 0.0),
                'evaluation': json.dumps(evaluation['checks'], ensure_ascii=False),
                'optimization_tips': '\n'.join(evaluation.get('optimization_tips', [])) if isinstance(evaluation.get('optimization_tips'), list) else evaluation.get('optimization_tips', ''),
                'knowledge_sources': source_summary,
                'source_ids': ','.join(map(str, source_ids)),
                'source_count': len(sources),
                'knowledge_links': knowledge_links,
                'batch_url': batch_url,
                'difficulty': scenario.get('difficulty', 'medium'),
                'notes': scenario.get('notes', ''),
                'timestamp': datetime.now().isoformat()
            }

            # 如果有 LLM 品質評估，添加到結果中
            if quality_eval:
                result['quality_eval'] = json.dumps(quality_eval, ensure_ascii=False)
                result['relevance'] = quality_eval.get('relevance', 0)
                result['completeness'] = quality_eval.get('completeness', 0)
                result['accuracy'] = quality_eval.get('accuracy', 0)
                result['intent_match'] = quality_eval.get('intent_match', 0)
                result['quality_overall'] = quality_eval.get('overall', 0)
                result['quality_reasoning'] = quality_eval.get('reasoning', '')

            results.append(result)

            # 顯示結果
            status = "✅ PASS" if evaluation['passed'] else "❌ FAIL"
            print(f"   {status} (分數: {evaluation['score']:.2f})")

            # 顯示知識來源
            if sources:
                print(f"   📚 知識來源 ({len(sources)} 個):")
                for idx, src in enumerate(sources[:3], 1):  # 只顯示前3個
                    kb_id = src.get('id', 'N/A')
                    title = src.get('question_summary', 'N/A')[:50]
                    print(f"      {idx}. [ID {kb_id}] {title}")

                # 顯示知識庫直接鏈接
                if knowledge_urls:
                    print(f"   🔗 直接鏈接:")
                    for idx, url in enumerate(knowledge_urls[:3], 1):
                        print(f"      {idx}. {url}")
                    print(f"   📦 批量查詢: {batch_url}")

            # 顯示優化建議
            if evaluation.get('optimization_tips'):
                tips = evaluation['optimization_tips']
                if isinstance(tips, list):
                    for tip in tips:
                        print(f"   {tip}")
                else:
                    print(f"   {tips}")

            # 避免 API rate limit
            time.sleep(delay)

        return results

    def generate_report(self, results: List[Dict], output_path: str):
        """生成回測報告"""

        print(f"\n📊 生成回測報告...")

        # 計算統計
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r['passed'])
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        avg_score = sum(r['score'] for r in results) / total_tests if total_tests > 0 else 0
        avg_confidence = sum(r['confidence'] for r in results) / total_tests if total_tests > 0 else 0

        # 檢查是否有品質評估資料
        has_quality_eval = any('relevance' in r for r in results)

        # 計算品質指標（如果有的話）
        quality_stats = {}
        if has_quality_eval:
            quality_results = [r for r in results if 'relevance' in r]
            if quality_results:
                quality_stats = {
                    'avg_relevance': sum(r['relevance'] for r in quality_results) / len(quality_results),
                    'avg_completeness': sum(r['completeness'] for r in quality_results) / len(quality_results),
                    'avg_accuracy': sum(r['accuracy'] for r in quality_results) / len(quality_results),
                    'avg_intent_match': sum(r['intent_match'] for r in quality_results) / len(quality_results),
                    'avg_quality_overall': sum(r['quality_overall'] for r in quality_results) / len(quality_results),
                    'quality_count': len(quality_results)
                }

                # 計算 NDCG
                ndcg_data = self.calculate_ndcg(quality_results)
                quality_stats['ndcg'] = ndcg_data['avg_ndcg']
                quality_stats['ndcg_count'] = ndcg_data['count']

        # 按難度分組
        by_difficulty = {}
        for r in results:
            diff = r.get('difficulty', 'medium')
            if diff not in by_difficulty:
                by_difficulty[diff] = {'total': 0, 'passed': 0}
            by_difficulty[diff]['total'] += 1
            if r['passed']:
                by_difficulty[diff]['passed'] += 1

        # 建立 DataFrame
        df = pd.DataFrame(results)

        # 儲存詳細結果
        df.to_excel(output_path, index=False, engine='openpyxl')
        print(f"   ✅ 詳細結果已儲存: {output_path}")

        # 生成摘要報告
        summary_path = output_path.replace('.xlsx', '_summary.txt')
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("知識庫回測報告\n")
            f.write("="*60 + "\n\n")

            f.write(f"測試時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"RAG 系統：{self.base_url}\n")
            f.write(f"業者 ID：{self.vendor_id}\n")
            f.write(f"品質評估模式：{self.quality_mode}\n\n")

            f.write("="*60 + "\n")
            f.write("整體統計\n")
            f.write("="*60 + "\n")
            f.write(f"總測試數：{total_tests}\n")
            f.write(f"通過數：{passed_tests}\n")
            f.write(f"失敗數：{total_tests - passed_tests}\n")
            f.write(f"通過率：{pass_rate:.2f}%\n")
            f.write(f"平均分數（基礎）：{avg_score:.2f}\n")
            f.write(f"平均信心度：{avg_confidence:.2f}\n\n")

            # 新增：品質評估統計
            if quality_stats:
                f.write("="*60 + "\n")
                f.write("LLM 品質評估統計\n")
                f.write("="*60 + "\n")
                f.write(f"評估測試數：{quality_stats['quality_count']}\n")
                f.write(f"平均相關性 (Relevance)：{quality_stats['avg_relevance']:.2f}/5.0\n")
                f.write(f"平均完整性 (Completeness)：{quality_stats['avg_completeness']:.2f}/5.0\n")
                f.write(f"平均準確性 (Accuracy)：{quality_stats['avg_accuracy']:.2f}/5.0\n")
                f.write(f"平均意圖匹配 (Intent Match)：{quality_stats['avg_intent_match']:.2f}/5.0\n")
                f.write(f"平均綜合評分 (Overall)：{quality_stats['avg_quality_overall']:.2f}/5.0\n")
                f.write(f"NDCG@3 (排序品質)：{quality_stats['ndcg']:.4f}\n")
                f.write("\n品質評級:\n")

                # 評級邏輯
                def get_rating(score):
                    if score >= 4.0:
                        return "🎉 優秀"
                    elif score >= 3.5:
                        return "✅ 良好"
                    elif score >= 3.0:
                        return "⚠️  中等"
                    else:
                        return "❌ 需改善"

                f.write(f"  相關性：{get_rating(quality_stats['avg_relevance'])}\n")
                f.write(f"  完整性：{get_rating(quality_stats['avg_completeness'])}\n")
                f.write(f"  準確性：{get_rating(quality_stats['avg_accuracy'])}\n")
                f.write(f"  意圖匹配：{get_rating(quality_stats['avg_intent_match'])}\n")
                f.write(f"  綜合評分：{get_rating(quality_stats['avg_quality_overall'])}\n")

                # NDCG 評級
                ndcg_rating = "🎉 優秀" if quality_stats['ndcg'] >= 0.9 else \
                              "✅ 良好" if quality_stats['ndcg'] >= 0.7 else \
                              "⚠️  中等" if quality_stats['ndcg'] >= 0.5 else "❌ 需改善"
                f.write(f"  排序品質：{ndcg_rating}\n\n")

            f.write("="*60 + "\n")
            f.write("按難度統計\n")
            f.write("="*60 + "\n")
            for diff, stats in by_difficulty.items():
                rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                f.write(f"{diff.upper():10s}: {stats['passed']}/{stats['total']} ({rate:.1f}%)\n")

            f.write("\n" + "="*60 + "\n")
            f.write("失敗案例\n")
            f.write("="*60 + "\n")

            failed = [r for r in results if not r['passed']]
            if failed:
                for r in failed[:10]:  # 只顯示前 10 個
                    f.write(f"\n問題：{r['test_question']}\n")
                    f.write(f"預期分類：{r['expected_category']}\n")
                    f.write(f"實際意圖：{r['actual_intent']}\n")
                    f.write(f"分數：{r['score']:.2f}\n")
                    f.write(f"知識來源：{r.get('knowledge_sources', '無')}\n")
                    f.write(f"來源IDs：{r.get('source_ids', '無')}\n")
                    # 新增：知識庫直接鏈接
                    knowledge_links = r.get('knowledge_links', '無')
                    if knowledge_links and knowledge_links != '無':
                        f.write(f"知識庫鏈接：\n{knowledge_links}\n")
                    batch_url = r.get('batch_url', '')
                    if batch_url:
                        f.write(f"批量查詢：{batch_url}\n")
                    f.write(f"優化建議：\n{r.get('optimization_tips', '無')}\n")
                    f.write("-" * 60 + "\n")
            else:
                f.write("\n無失敗案例 🎉\n")

        print(f"   ✅ 摘要報告已儲存: {summary_path}")

        # 列印摘要到控制台
        print(f"\n{'='*60}")
        print("回測摘要")
        print(f"{'='*60}")
        print(f"通過率：{pass_rate:.2f}% ({passed_tests}/{total_tests})")
        print(f"平均分數（基礎）：{avg_score:.2f}")
        print(f"平均信心度：{avg_confidence:.2f}")

        # 顯示品質評估結果
        if quality_stats:
            print(f"\n🎯 LLM 品質評估統計 ({quality_stats['quality_count']} 個測試):")
            print(f"   相關性：{quality_stats['avg_relevance']:.2f}/5.0")
            print(f"   完整性：{quality_stats['avg_completeness']:.2f}/5.0")
            print(f"   準確性：{quality_stats['avg_accuracy']:.2f}/5.0")
            print(f"   意圖匹配：{quality_stats['avg_intent_match']:.2f}/5.0")
            print(f"   綜合評分：{quality_stats['avg_quality_overall']:.2f}/5.0")
            print(f"   NDCG@3：{quality_stats['ndcg']:.4f}")

        print(f"{'='*60}\n")

        # 組裝返回資料
        summary_data = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'pass_rate': pass_rate,
            'avg_score': avg_score,
            'avg_confidence': avg_confidence,
            'quality_mode': self.quality_mode
        }

        # 添加品質統計
        if quality_stats:
            summary_data['quality_stats'] = quality_stats

        return summary_data

    def save_results_to_database(self, results: List[Dict], summary_data: Dict, output_path: str):
        """儲存回測結果到資料庫"""
        print(f"\n💾 儲存回測結果到資料庫...")

        if not self.use_database:
            print("   ⚠️  資料庫模式未啟用，跳過儲存")
            return None

        conn = self.get_db_connection()
        cur = conn.cursor()

        try:
            # 1. 建立 backtest_run 記錄
            completed_at = datetime.now()
            duration_seconds = int((completed_at - self.run_started_at).total_seconds())

            cur.execute("""
                INSERT INTO backtest_runs (
                    quality_mode, test_type, total_scenarios, executed_scenarios,
                    status, rag_api_url, vendor_id,
                    passed_count, failed_count, pass_rate,
                    avg_score, avg_confidence,
                    avg_relevance, avg_completeness, avg_accuracy,
                    avg_intent_match, avg_quality_overall, ndcg_score,
                    started_at, completed_at, duration_seconds,
                    output_file_path, summary_file_path, executed_by
                ) VALUES (
                    %s, %s, %s, %s, 'completed', %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                ) RETURNING id
            """, (
                self.quality_mode,
                os.getenv('BACKTEST_TYPE', 'full'),
                summary_data['total_tests'],
                summary_data['total_tests'],
                self.base_url,
                self.vendor_id,
                summary_data['passed_tests'],
                summary_data['total_tests'] - summary_data['passed_tests'],
                summary_data['pass_rate'],
                summary_data['avg_score'],
                summary_data['avg_confidence'],
                summary_data.get('quality_stats', {}).get('avg_relevance'),
                summary_data.get('quality_stats', {}).get('avg_completeness'),
                summary_data.get('quality_stats', {}).get('avg_accuracy'),
                summary_data.get('quality_stats', {}).get('avg_intent_match'),
                summary_data.get('quality_stats', {}).get('avg_quality_overall'),
                summary_data.get('quality_stats', {}).get('ndcg'),
                self.run_started_at,
                completed_at,
                duration_seconds,
                output_path,
                output_path.replace('.xlsx', '_summary.txt'),
                'backtest_framework'
            ))

            run_id = cur.fetchone()['id']
            print(f"   ✅ 建立回測執行記錄 (Run ID: {run_id})")

            # 2. 插入每個測試結果
            inserted_count = 0
            for result in results:
                # 準備 all_intents 陣列
                all_intents = result.get('all_intents', [])
                if isinstance(all_intents, str):
                    all_intents = [all_intents] if all_intents else []

                cur.execute("""
                    INSERT INTO backtest_results (
                        run_id, scenario_id, test_question, expected_category,
                        actual_intent, all_intents, system_answer, confidence,
                        score, overall_score, passed,
                        category_match, keyword_coverage,
                        relevance, completeness, accuracy, intent_match,
                        quality_overall, quality_reasoning,
                        source_ids, source_count, knowledge_sources, optimization_tips,
                        evaluation
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    run_id,
                    result.get('scenario_id'),
                    result['test_question'],
                    result.get('expected_category'),
                    result.get('actual_intent'),
                    all_intents,
                    result.get('system_answer'),
                    result.get('confidence', 0),
                    result.get('score', 0),
                    result.get('overall_score', result.get('score', 0)),
                    result.get('passed', False),
                    result.get('category_match', False),
                    result.get('keyword_coverage', 0.0),
                    result.get('relevance'),
                    result.get('completeness'),
                    result.get('accuracy'),
                    result.get('intent_match'),
                    result.get('quality_overall'),
                    result.get('quality_reasoning'),
                    result.get('source_ids'),
                    result.get('source_count', 0),
                    result.get('knowledge_sources'),
                    result.get('optimization_tips'),
                    result.get('evaluation')
                ))
                inserted_count += 1

            conn.commit()
            print(f"   ✅ 儲存 {inserted_count} 個測試結果到資料庫")
            print(f"   📊 回測執行 ID: {run_id}")
            print(f"   ⏱️  執行時間: {duration_seconds} 秒")

            return run_id

        except Exception as e:
            conn.rollback()
            print(f"   ❌ 儲存到資料庫失敗: {e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            cur.close()
            conn.close()


def main():
    """主程式"""
    print("="*60)
    print("知識庫回測框架")
    print("="*60)

    # 配置
    base_url = os.getenv("RAG_API_URL", "http://localhost:8100")
    vendor_id = int(os.getenv("VENDOR_ID", "1"))
    quality_mode = os.getenv("BACKTEST_QUALITY_MODE", "basic")  # basic, detailed, hybrid

    # 資料庫模式控制（預設啟用）
    use_database = os.getenv("BACKTEST_USE_DATABASE", "true").lower() == "true"

    # 取得專案根目錄
    project_root = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

    # 支援選擇不同的測試檔案（smoke tests 或 full tests）
    test_type = os.getenv("BACKTEST_TYPE", "smoke")  # smoke, full, or custom

    output_path = os.path.join(project_root, "output/backtest/backtest_results.xlsx")

    # 建立回測框架（帶品質評估模式與資料庫支援）
    backtest = BacktestFramework(base_url, vendor_id, quality_mode, use_database=use_database)

    # 載入測試情境
    if use_database:
        # 資料庫模式：基於評分和難度篩選
        difficulty = os.getenv("BACKTEST_DIFFICULTY")  # easy, medium, hard, or None for all
        prioritize_failed = os.getenv("BACKTEST_PRIORITIZE_FAILED", "true").lower() == "true"

        try:
            scenarios = backtest.load_test_scenarios(
                difficulty=difficulty,
                prioritize_failed=prioritize_failed
            )
        except Exception as e:
            print(f"❌ 從資料庫載入測試情境失敗: {e}")
            print("💡 提示：請確認資料庫連線正常，且已執行測試題庫遷移")
            print("   或設定 BACKTEST_USE_DATABASE=false 使用 Excel 模式")
            return
    else:
        # Excel 模式：使用檔案路徑（向後相容）
        if test_type == "smoke":
            test_scenarios_path = os.path.join(project_root, "test_scenarios_smoke.xlsx")
        elif test_type == "full":
            test_scenarios_path = os.path.join(project_root, "test_scenarios_full.xlsx")
        else:
            # custom: 使用環境變數指定的路徑
            test_scenarios_path = os.getenv("BACKTEST_SCENARIOS_PATH", os.path.join(project_root, "test_scenarios.xlsx"))

        # 檢查文件
        if not os.path.exists(test_scenarios_path):
            print(f"❌ 測試情境文件不存在: {test_scenarios_path}")
            print("請先執行 extract_knowledge_and_tests.py 提取測試情境")
            print("或設定 BACKTEST_USE_DATABASE=true 使用資料庫模式")
            return

        scenarios = backtest.load_test_scenarios(excel_path=test_scenarios_path)

    # 執行回測
    # 支援非交互模式（從環境變數讀取樣本數量）
    non_interactive = os.getenv("BACKTEST_NON_INTERACTIVE", "false").lower() == "true"

    if non_interactive:
        # 非交互模式：直接執行全部測試
        sample_size_str = os.getenv("BACKTEST_SAMPLE_SIZE", "")
        if sample_size_str:
            sample_size = int(sample_size_str)
            print(f"\n🧪 非交互模式：執行 {sample_size} 個測試")
        else:
            sample_size = None
            print(f"\n🧪 非交互模式：執行全部 {len(scenarios)} 個測試")
    else:
        # 交互模式：詢問用戶
        print(f"\n是否要執行完整回測？")
        print(f"總共 {len(scenarios)} 個測試情境")
        sample_size = input("輸入要測試的數量（直接按 Enter 測試全部）: ").strip()

        if sample_size:
            sample_size = int(sample_size)
        else:
            sample_size = None

    results = backtest.run_backtest(scenarios, sample_size=sample_size)

    # 生成報告
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    summary_data = backtest.generate_report(results, output_path)

    # 儲存到資料庫
    backtest.save_results_to_database(results, summary_data, output_path)

    print("✅ 回測完成！")


if __name__ == "__main__":
    main()
