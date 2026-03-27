"""
測試知識缺口分類器

使用 OpenAI 對 Loop 45 的 46 個知識缺口進行分類
"""

import asyncio
import os
import sys
import psycopg2
import psycopg2.extras
import json

# 添加路徑
sys.path.insert(0, '/app')

from gap_classifier import GapClassifier


async def main():
    """主函數"""

    print("=" * 80)
    print("知識缺口分類測試")
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

    # 2. 查詢知識缺口
    print("📊 查詢知識缺口...")
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

    # 3. 初始化分類器
    print("\n🤖 初始化 OpenAI 分類器...")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not openai_api_key:
        print("⚠️  未設定 OPENAI_API_KEY，使用 Stub 模式")

    classifier = GapClassifier(
        openai_api_key=openai_api_key,
        model="gpt-4o-mini"  # 使用 gpt-4o-mini 更經濟
    )

    # 4. 執行分類
    print("\n🔍 開始分類...")
    print(f"   模型: {classifier.model}")
    print(f"   問題數量: {len(gaps)}")

    classification_result = await classifier.classify_gaps(gaps)

    # 5. 顯示結果
    print("\n" + "=" * 80)
    print("分類結果摘要")
    print("=" * 80)

    summary = classification_result["summary"]
    print(f"\n總問題數: {summary['total_questions']}")
    print(f"  - SOP 知識: {summary['sop_knowledge_count']} 題")
    print(f"  - API 查詢: {summary['api_query_count']} 題")
    print(f"  - 表單填寫: {summary['form_fill_count']} 題")
    print(f"  - 系統配置: {summary['system_config_count']} 題")
    print(f"\n應生成知識: {summary['should_generate_count']} 題")
    print(f"建議聚類數: {summary.get('recommended_clusters', 0)} 個")

    # 6. 顯示分類詳情（前 20 題）
    print("\n" + "=" * 80)
    print("分類詳情（前 20 題）")
    print("=" * 80)

    classifications = classification_result["classifications"]
    for i, classification in enumerate(classifications[:20]):
        icon = "✅" if classification["should_generate_knowledge"] else "❌"
        print(f"\n{i+1}. {icon} [{classification['category']}] {classification['question']}")
        print(f"   理由: {classification['reasoning'][:80]}...")

        if classification.get("similar_to"):
            similar_indices = classification["similar_to"]
            print(f"   相似問題: {similar_indices}")

    # 7. 顯示聚類結果
    clusters = classification_result.get("clusters", [])
    if clusters:
        print("\n" + "=" * 80)
        print(f"聚類結果（共 {len(clusters)} 個聚類）")
        print("=" * 80)

        for cluster in clusters[:10]:  # 只顯示前 10 個
            print(f"\n聚類 #{cluster['cluster_id']} [{cluster['category']}]")
            print(f"  包含問題: {len(cluster['question_indices'])} 題")
            print(f"  代表問題: {cluster['representative_question']}")
            print(f"  合併答案: {cluster['combined_answer_needed']}")
            print(f"  理由: {cluster['reasoning'][:80]}...")

    # 8. 過濾出需要生成知識的缺口
    print("\n" + "=" * 80)
    print("知識生成建議")
    print("=" * 80)

    filtered_gaps = classifier.filter_gaps_for_generation(gaps, classification_result)
    print(f"\n過濾後需要生成知識: {len(filtered_gaps)} 題")

    # 如果有聚類，顯示聚類後的代表性問題
    if clusters:
        clustered_gaps = classifier.get_clusters_for_generation(gaps, classification_result)
        print(f"聚類後代表性問題: {len(clustered_gaps)} 題")

        print("\n代表性問題列表:")
        for i, gap in enumerate(clustered_gaps[:15], 1):
            cluster_info = f" (代表 {gap.get('cluster_size', 1)} 題)" if gap.get('cluster_size', 1) > 1 else ""
            print(f"  {i}. {gap['question']}{cluster_info}")

    # 9. 保存結果到檔案
    output_file = "/tmp/gap_classification_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(classification_result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 完整結果已保存到: {output_file}")

    # 10. 統計建議
    print("\n" + "=" * 80)
    print("💡 處理建議")
    print("=" * 80)

    api_count = summary['api_query_count']
    sop_count = summary['sop_knowledge_count']
    form_count = summary['form_fill_count']

    print(f"\n1. API 查詢類 ({api_count} 題)")
    print(f"   - 不生成靜態知識")
    print(f"   - 建議：整合房源/合約資料庫查詢功能")

    print(f"\n2. SOP 知識類 ({sop_count} 題)")
    print(f"   - 生成知識文檔")
    print(f"   - 建議：請產品/客服團隊提供標準流程")

    print(f"\n3. 表單填寫類 ({form_count} 題)")
    print(f"   - 生成引導知識")
    print(f"   - 建議：建立表單庫並整合表單填寫流程")

    print(f"\n預估最終生成知識數量: {summary['should_generate_count']} 題")
    if clusters:
        print(f"如果採用聚類: 約 {len([c for c in clusters if c['category'] != 'api_query'])} 題")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
