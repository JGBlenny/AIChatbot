#!/usr/bin/env python3
"""
完整對話流程效能測試

⚠️ 警告：此測試使用已廢棄的 /api/v1/chat 端點
   - 此端點將在 2026-01-01 移除
   - 建議遷移到 /api/v1/message 或 /api/v1/chat/stream
   - 詳見: docs/api/CHAT_API_MIGRATION_GUIDE.md

測試範圍：
1. 意圖分類
2. 知識檢索（RAG）
3. LLM 答案生成
4. 信心度評估
5. 未釐清問題記錄
6. 端到端總時間

測試情境：
- 高信心度問題（有明確知識）
- 中等信心度問題（部分相關知識）
- 低信心度問題（無相關知識）
- 複雜問題（需要 SOP + 參數注入）

TODO: 將測試遷移到 /api/v1/message 端點
"""
import asyncio
import httpx
import time
import statistics
from typing import List, Dict
from datetime import datetime
import json

# API 配置
RAG_API_BASE = "http://localhost:8100"
VENDOR_ID = 1  # 測試用業者 ID

# 測試問題集合
TEST_QUESTIONS = {
    "high_confidence": [
        "租金每個月幾號要繳？",
        "我想養寵物可以嗎？",
        "退租需要提前多久告知？",
        "房租包含哪些費用？",
        "租約到期如何續約？"
    ],
    "medium_confidence": [
        "電費是怎麼算的？",
        "冷氣壞了怎麼辦？",
        "可以提前解約嗎？",
        "房間可以釘釘子嗎？",
        "停車位怎麼收費？"
    ],
    "low_confidence": [
        "附近有什麼好吃的餐廳？",
        "這個社區安全嗎？",
        "我的鄰居很吵怎麼辦？",
        "今天天氣如何？",
        "你能幫我訂披薩嗎？"
    ],
    "complex": [
        "我的租金明細是什麼？",  # 需要 API 整合
        "幫我查詢我的繳費記錄",  # 需要參數注入
        "我的合約什麼時候到期？",  # 需要租客識別
    ]
}


class PerformanceTester:
    """效能測試器"""

    def __init__(self):
        self.results = []
        self.client = None

    async def __aenter__(self):
        """進入上下文時創建 HTTP 客戶端"""
        self.client = httpx.AsyncClient(timeout=60.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文時關閉客戶端"""
        if self.client:
            await self.client.close()

    async def test_single_question(
        self,
        question: str,
        category: str,
        repeat: int = 1
    ) -> Dict:
        """測試單個問題"""
        times = []
        responses = []

        for i in range(repeat):
            start_time = time.time()

            try:
                response = await self.client.post(
                    f"{RAG_API_BASE}/api/v1/chat",
                    json={
                        "question": question,
                        "vendor_id": VENDOR_ID,
                        "user_role": "customer",
                        "user_id": f"perf_test_{i}"
                    }
                )

                elapsed = (time.time() - start_time) * 1000  # 轉換為毫秒

                if response.status_code == 200:
                    data = response.json()
                    times.append(elapsed)
                    responses.append(data)
                else:
                    print(f"   ❌ 請求失敗: {response.status_code}")
                    times.append(elapsed)
                    responses.append(None)

            except Exception as e:
                elapsed = (time.time() - start_time) * 1000
                print(f"   ❌ 異常: {e}")
                times.append(elapsed)
                responses.append(None)

        # 計算統計數據
        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            median_time = statistics.median(times)
            stdev_time = statistics.stdev(times) if len(times) > 1 else 0
        else:
            avg_time = min_time = max_time = median_time = stdev_time = 0

        # 從響應中提取詳細時間分解（如果可用）
        breakdown = None
        if responses and responses[0]:
            last_response = responses[0]
            breakdown = {
                "processing_time_ms": last_response.get("processing_time_ms", 0),
                "confidence_score": last_response.get("confidence_score", 0),
                "confidence_level": last_response.get("confidence_level", "unknown"),
                "requires_human": last_response.get("requires_human", False),
                "intent_type": last_response.get("intent", {}).get("intent_type", "unknown"),
                "retrieved_docs_count": len(last_response.get("retrieved_docs", []))
            }

        result = {
            "question": question,
            "category": category,
            "repeat_count": repeat,
            "avg_time_ms": round(avg_time, 2),
            "min_time_ms": round(min_time, 2),
            "max_time_ms": round(max_time, 2),
            "median_time_ms": round(median_time, 2),
            "stdev_ms": round(stdev_time, 2),
            "breakdown": breakdown,
            "success_rate": sum(1 for r in responses if r) / len(responses) * 100
        }

        self.results.append(result)
        return result

    async def run_tests(self, repeat_per_question: int = 3):
        """執行所有測試"""
        print("=" * 80)
        print("RAG 對話流程完整效能測試")
        print("=" * 80)
        print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"API 端點: {RAG_API_BASE}")
        print(f"業者 ID: {VENDOR_ID}")
        print(f"每個問題重複次數: {repeat_per_question}")
        print("=" * 80)

        total_tests = sum(len(questions) for questions in TEST_QUESTIONS.values())
        current_test = 0

        for category, questions in TEST_QUESTIONS.items():
            print(f"\n📂 測試類別: {category.upper()}")
            print("-" * 80)

            for question in questions:
                current_test += 1
                print(f"\n[{current_test}/{total_tests}] 測試問題: {question}")

                result = await self.test_single_question(
                    question,
                    category,
                    repeat=repeat_per_question
                )

                # 顯示即時結果
                print(f"   平均時間: {result['avg_time_ms']:.2f} ms")
                print(f"   範圍: {result['min_time_ms']:.2f} - {result['max_time_ms']:.2f} ms")

                if result['breakdown']:
                    bd = result['breakdown']
                    print(f"   信心度: {bd['confidence_score']:.2f} ({bd['confidence_level']})")
                    print(f"   意圖類型: {bd['intent_type']}")
                    print(f"   檢索文檔數: {bd['retrieved_docs_count']}")
                    print(f"   需要人工: {'是' if bd['requires_human'] else '否'}")

                # 避免過快請求
                await asyncio.sleep(0.5)

    def generate_report(self) -> Dict:
        """生成效能報告"""
        if not self.results:
            return {"error": "沒有測試結果"}

        # 按類別分組統計
        category_stats = {}
        for category in TEST_QUESTIONS.keys():
            category_results = [r for r in self.results if r['category'] == category]

            if category_results:
                avg_times = [r['avg_time_ms'] for r in category_results]
                category_stats[category] = {
                    "count": len(category_results),
                    "avg_time_ms": round(statistics.mean(avg_times), 2),
                    "min_time_ms": round(min(avg_times), 2),
                    "max_time_ms": round(max(avg_times), 2),
                    "median_time_ms": round(statistics.median(avg_times), 2),
                    "success_rate": round(
                        statistics.mean([r['success_rate'] for r in category_results]), 2
                    )
                }

        # 全局統計
        all_avg_times = [r['avg_time_ms'] for r in self.results]
        global_stats = {
            "total_tests": len(self.results),
            "overall_avg_ms": round(statistics.mean(all_avg_times), 2),
            "overall_min_ms": round(min(all_avg_times), 2),
            "overall_max_ms": round(max(all_avg_times), 2),
            "overall_median_ms": round(statistics.median(all_avg_times), 2),
            "overall_stdev_ms": round(statistics.stdev(all_avg_times), 2),
            "success_rate": round(
                statistics.mean([r['success_rate'] for r in self.results]), 2
            )
        }

        # 信心度分布
        confidence_distribution = {}
        for result in self.results:
            if result['breakdown']:
                level = result['breakdown']['confidence_level']
                confidence_distribution[level] = confidence_distribution.get(level, 0) + 1

        # 識別慢查詢（大於 P95）
        p95_time = sorted(all_avg_times)[int(len(all_avg_times) * 0.95)]
        slow_queries = [
            {
                "question": r['question'],
                "avg_time_ms": r['avg_time_ms'],
                "category": r['category']
            }
            for r in self.results
            if r['avg_time_ms'] > p95_time
        ]

        return {
            "test_summary": {
                "test_time": datetime.now().isoformat(),
                "api_endpoint": RAG_API_BASE,
                "vendor_id": VENDOR_ID
            },
            "global_stats": global_stats,
            "category_stats": category_stats,
            "confidence_distribution": confidence_distribution,
            "slow_queries": {
                "p95_threshold_ms": round(p95_time, 2),
                "count": len(slow_queries),
                "queries": slow_queries
            },
            "detailed_results": self.results
        }

    def print_report(self, report: Dict):
        """打印報告"""
        print("\n" + "=" * 80)
        print("📊 效能測試報告")
        print("=" * 80)

        # 全局統計
        print("\n🌐 全局統計")
        print("-" * 80)
        gs = report['global_stats']
        print(f"總測試數: {gs['total_tests']}")
        print(f"成功率: {gs['success_rate']}%")
        print(f"平均響應時間: {gs['overall_avg_ms']:.2f} ms")
        print(f"中位數時間: {gs['overall_median_ms']:.2f} ms")
        print(f"最小時間: {gs['overall_min_ms']:.2f} ms")
        print(f"最大時間: {gs['overall_max_ms']:.2f} ms")
        print(f"標準差: {gs['overall_stdev_ms']:.2f} ms")

        # 類別統計
        print("\n📂 各類別統計")
        print("-" * 80)
        for category, stats in report['category_stats'].items():
            print(f"\n{category.upper()}:")
            print(f"  測試數: {stats['count']}")
            print(f"  平均時間: {stats['avg_time_ms']:.2f} ms")
            print(f"  範圍: {stats['min_time_ms']:.2f} - {stats['max_time_ms']:.2f} ms")
            print(f"  成功率: {stats['success_rate']}%")

        # 信心度分布
        print("\n🎯 信心度分布")
        print("-" * 80)
        for level, count in report['confidence_distribution'].items():
            percentage = (count / gs['total_tests']) * 100
            print(f"{level}: {count} ({percentage:.1f}%)")

        # 慢查詢
        print("\n⚠️  慢查詢 (P95)")
        print("-" * 80)
        print(f"P95 閾值: {report['slow_queries']['p95_threshold_ms']:.2f} ms")
        print(f"慢查詢數量: {report['slow_queries']['count']}")
        for sq in report['slow_queries']['queries']:
            print(f"  - [{sq['category']}] {sq['question']}: {sq['avg_time_ms']:.2f} ms")

        # 效能評級
        print("\n⭐ 效能評級")
        print("-" * 80)
        avg_ms = gs['overall_avg_ms']
        if avg_ms < 1000:
            grade = "A (優秀)"
            emoji = "🟢"
        elif avg_ms < 2000:
            grade = "B (良好)"
            emoji = "🟡"
        elif avg_ms < 3000:
            grade = "C (尚可)"
            emoji = "🟠"
        else:
            grade = "D (需改進)"
            emoji = "🔴"

        print(f"{emoji} 平均響應時間 {avg_ms:.2f} ms - 評級: {grade}")

        # 建議
        print("\n💡 優化建議")
        print("-" * 80)
        if avg_ms > 2000:
            print("  - 平均響應時間較長，建議檢查 LLM API 延遲")
        if gs['overall_stdev_ms'] > 500:
            print("  - 響應時間波動較大，建議檢查服務穩定性")
        if report['slow_queries']['count'] > 0:
            print(f"  - 發現 {report['slow_queries']['count']} 個慢查詢，建議針對性優化")

        print("\n" + "=" * 80)


async def main():
    """主函數"""
    async with PerformanceTester() as tester:
        # 執行測試
        await tester.run_tests(repeat_per_question=3)

        # 生成報告
        report = tester.generate_report()

        # 打印報告
        tester.print_report(report)

        # 保存報告到文件
        output_file = f"/tmp/chat_performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📄 詳細報告已保存至: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
