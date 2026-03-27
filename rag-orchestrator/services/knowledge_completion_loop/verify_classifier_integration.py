"""
驗證 GapClassifier 整合是否成功

使用 Loop 45 的知識缺口資料測試分類功能
"""

import asyncio
import os
import sys
import psycopg2
import psycopg2.extras

sys.path.insert(0, '/app')

from gap_classifier import GapClassifier


async def main():
    """主函數"""

    print("=" * 80)
    print("驗證 GapClassifier 整合")
    print("=" * 80)

    # 1. 連接資料庫
    print("\n🔌 連接資料庫...")
    conn = psycopg2.connect(
        host='postgres',
        port=5432,
        database='aichatbot_admin',
        user='aichatbot',
        password='aichatbot_password'
    )

    # 2. 查詢 Loop 45 的知識缺口
    print("📊 查詢 Loop 45 的知識缺口...")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT
            id as gap_id,
            question,
            failure_reason,
            priority,
            intent_name
        FROM knowledge_gap_analysis
        WHERE loop_id = 45
        ORDER BY id
    """)

    gaps = [dict(row) for row in cur.fetchall()]
    conn.close()

    print(f"   找到 {len(gaps)} 個知識缺口")

    if not gaps:
        print("❌ 沒有找到知識缺口資料")
        return

    # 3. 初始化分類器（使用 OpenAI）
    print("\n🤖 初始化 GapClassifier...")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        print("⚠️  未設定 OPENAI_API_KEY，使用 Stub 模式")

    classifier = GapClassifier(
        openai_api_key=openai_api_key,
        model="gpt-4o-mini"
    )

    # 4. 執行分類
    print(f"\n🔍 開始分類 {len(gaps)} 個知識缺口...")
    classification_result = await classifier.classify_gaps(gaps)

    # 5. 顯示結果
    print("\n" + "=" * 80)
    print("分類結果")
    print("=" * 80)

    summary = classification_result.get("summary", {})
    print(f"\n總問題數: {summary.get('total_questions', 0)}")
    print(f"  - SOP 知識: {summary.get('sop_knowledge_count', 0)} 題")
    print(f"  - API 查詢: {summary.get('api_query_count', 0)} 題（不生成靜態知識）")
    print(f"  - 表單填寫: {summary.get('form_fill_count', 0)} 題")
    print(f"  - 系統配置: {summary.get('system_config_count', 0)} 題")
    print(f"\n應生成知識: {summary.get('should_generate_count', 0)} 題")

    # 6. 過濾缺口
    print("\n🔍 過濾出需要生成知識的缺口...")
    filtered_gaps = classifier.filter_gaps_for_generation(gaps, classification_result)

    print(f"\n✅ 過濾結果：{len(gaps)} 題 → {len(filtered_gaps)} 題需要生成知識")
    print(f"   減少比例：{(1 - len(filtered_gaps) / len(gaps)) * 100:.1f}%")

    # 7. 顯示前 10 個分類範例
    print("\n" + "=" * 80)
    print("分類範例（前 10 題）")
    print("=" * 80)

    classifications = classification_result.get("classifications", [])
    for i, classification in enumerate(classifications[:10]):
        icon = "✅" if classification["should_generate_knowledge"] else "❌"
        category = classification["category"]
        question = classification["question"]

        print(f"\n{i+1}. {icon} [{category}] {question}")
        print(f"   理由: {classification['reasoning'][:80]}...")

    # 8. 總結
    print("\n" + "=" * 80)
    print("✅ GapClassifier 整合驗證完成！")
    print("=" * 80)

    print(f"\n💡 效益：")
    print(f"   - 原本需生成：{len(gaps)} 筆知識")
    print(f"   - 過濾後需生成：{len(filtered_gaps)} 筆知識")
    print(f"   - 減少生成量：{len(gaps) - len(filtered_gaps)} 筆")
    print(f"   - 節省比例：{(1 - len(filtered_gaps) / len(gaps)) * 100:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
