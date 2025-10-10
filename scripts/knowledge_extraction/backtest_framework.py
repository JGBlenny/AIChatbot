"""
知識庫回測框架
測試 RAG 系統對測試問題的回答準確度
"""

import os
import sys
import time
from typing import List, Dict
from datetime import datetime
import pandas as pd
import requests
import json

class BacktestFramework:
    """回測框架"""

    def __init__(self, base_url: str = "http://localhost:8100", vendor_id: int = 1):
        self.base_url = base_url
        self.vendor_id = vendor_id
        self.results = []

    def load_test_scenarios(self, excel_path: str) -> List[Dict]:
        """載入測試情境"""
        print(f"📖 載入測試情境: {excel_path}")

        df = pd.read_excel(excel_path, engine='openpyxl')
        scenarios = df.to_dict('records')

        print(f"   ✅ 載入 {len(scenarios)} 個測試情境")
        return scenarios

    def query_rag_system(self, question: str) -> Dict:
        """查詢 RAG 系統"""
        url = f"{self.base_url}/api/v1/message"

        payload = {
            "message": question,
            "vendor_id": self.vendor_id,
            "mode": "tenant",
            "include_sources": True
        }

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

            # 評估答案
            evaluation = self.evaluate_answer(scenario, system_response)

            # 記錄結果
            result = {
                'test_id': i,
                'test_question': question,
                'expected_category': scenario.get('expected_category', ''),
                'actual_intent': system_response.get('intent_name', '') if system_response else '',
                'system_answer': system_response.get('answer', '')[:200] if system_response else '',
                'confidence': system_response.get('confidence', 0) if system_response else 0,
                'score': evaluation['score'],
                'passed': evaluation['passed'],
                'evaluation': json.dumps(evaluation['checks'], ensure_ascii=False),
                'optimization_tips': '\n'.join(evaluation.get('optimization_tips', [])) if isinstance(evaluation.get('optimization_tips'), list) else evaluation.get('optimization_tips', ''),
                'difficulty': scenario.get('difficulty', 'medium'),
                'notes': scenario.get('notes', ''),
                'timestamp': datetime.now().isoformat()
            }

            results.append(result)

            # 顯示結果
            status = "✅ PASS" if evaluation['passed'] else "❌ FAIL"
            print(f"   {status} (分數: {evaluation['score']:.2f})")

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
            f.write(f"業者 ID：{self.vendor_id}\n\n")

            f.write("="*60 + "\n")
            f.write("整體統計\n")
            f.write("="*60 + "\n")
            f.write(f"總測試數：{total_tests}\n")
            f.write(f"通過數：{passed_tests}\n")
            f.write(f"失敗數：{total_tests - passed_tests}\n")
            f.write(f"通過率：{pass_rate:.2f}%\n")
            f.write(f"平均分數：{avg_score:.2f}\n")
            f.write(f"平均信心度：{avg_confidence:.2f}\n\n")

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
                    f.write("-" * 60 + "\n")
            else:
                f.write("\n無失敗案例 🎉\n")

        print(f"   ✅ 摘要報告已儲存: {summary_path}")

        # 列印摘要到控制台
        print(f"\n{'='*60}")
        print("回測摘要")
        print(f"{'='*60}")
        print(f"通過率：{pass_rate:.2f}% ({passed_tests}/{total_tests})")
        print(f"平均分數：{avg_score:.2f}")
        print(f"平均信心度：{avg_confidence:.2f}")
        print(f"{'='*60}\n")

        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'pass_rate': pass_rate,
            'avg_score': avg_score,
            'avg_confidence': avg_confidence
        }


def main():
    """主程式"""
    print("="*60)
    print("知識庫回測框架")
    print("="*60)

    # 配置
    base_url = os.getenv("RAG_API_URL", "http://localhost:8100")
    vendor_id = int(os.getenv("VENDOR_ID", "1"))

    # 取得專案根目錄
    project_root = os.getenv("PROJECT_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

    # 支援選擇不同的測試檔案（smoke tests 或 full tests）
    test_type = os.getenv("BACKTEST_TYPE", "smoke")  # smoke, full, or custom
    if test_type == "smoke":
        test_scenarios_path = os.path.join(project_root, "test_scenarios_smoke.xlsx")
    elif test_type == "full":
        test_scenarios_path = os.path.join(project_root, "test_scenarios_full.xlsx")
    else:
        # custom: 使用環境變數指定的路徑
        test_scenarios_path = os.getenv("BACKTEST_SCENARIOS_PATH", os.path.join(project_root, "test_scenarios.xlsx"))

    output_path = os.path.join(project_root, "output/backtest/backtest_results.xlsx")

    # 檢查文件
    if not os.path.exists(test_scenarios_path):
        print(f"❌ 測試情境文件不存在: {test_scenarios_path}")
        print("請先執行 extract_knowledge_and_tests.py 提取測試情境")
        return

    # 建立回測框架
    backtest = BacktestFramework(base_url, vendor_id)

    # 載入測試情境
    scenarios = backtest.load_test_scenarios(test_scenarios_path)

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
    backtest.generate_report(results, output_path)

    print("✅ 回測完成！")


if __name__ == "__main__":
    main()
