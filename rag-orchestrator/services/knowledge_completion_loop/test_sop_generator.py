"""
測試 SOP 生成器

使用 vendor 2 的資料進行測試
"""

import asyncio
import os
import sys
import psycopg2
import psycopg2.pool
import psycopg2.extras

# 確保可以 import 模組
sys.path.insert(0, '/app')

from sop_generator import SOPGenerator


async def main():
    """主函數"""
    print("="*80)
    print("測試 SOP 生成器")
    print("="*80)

    # 環境變數
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ 未設定 OPENAI_API_KEY")
        return

    print(f"✅ OpenAI API Key: {openai_api_key[:10]}...")

    # 建立資料庫連接池
    db_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=5,
        host='postgres',
        port=5432,
        database='aichatbot_admin',
        user='aichatbot',
        password='aichatbot_password'
    )

    print("✅ 資料庫連接池建立成功")

    # 創建測試用的知識缺口資料
    test_gaps = [
        {
            'gap_id': 1,
            'question': '如何續約',
            'failure_reason': 'no_match',
            'priority': 'p0',
            'gap_type': 'sop_knowledge'
        },
        {
            'gap_id': 2,
            'question': '如何退租',
            'failure_reason': 'no_match',
            'priority': 'p0',
            'gap_type': 'sop_knowledge'
        },
        {
            'gap_id': 3,
            'question': '我想找房',
            'failure_reason': 'no_match',
            'priority': 'p1',
            'gap_type': 'form_fill'
        }
    ]

    print(f"\n測試資料：{len(test_gaps)} 個知識缺口")
    for gap in test_gaps:
        print(f"   - {gap['question']} ({gap['gap_type']})")

    # 初始化 SOP 生成器
    sop_generator = SOPGenerator(
        db_pool=db_pool,
        openai_api_key=openai_api_key,
        model="gpt-4o-mini"
    )

    print("\n✅ SOP 生成器初始化完成")

    # 生成 SOP
    print("\n" + "="*80)
    print("開始生成 SOP...")
    print("="*80)

    generated_sops = await sop_generator.generate_sop_items(
        loop_id=99999,  # 測試用的 loop_id
        vendor_id=2,
        gaps=test_gaps,
        iteration=1,
        batch_size=3
    )

    # 顯示結果
    print("\n" + "="*80)
    print("生成結果")
    print("="*80)

    if generated_sops:
        print(f"\n✅ 成功生成 {len(generated_sops)} 筆 SOP\n")

        for i, sop in enumerate(generated_sops, 1):
            print(f"SOP #{i}:")
            print(f"   ID: {sop.get('id')}")
            print(f"   名稱: {sop.get('item_name')}")
            print(f"   問題: {sop.get('question')}")
            print(f"   內容預覽: {sop.get('content', '')[:100]}...")
            print(f"   觸發模式: {sop.get('trigger_mode')}")
            print(f"   下一步動作: {sop.get('next_action')}")
            if sop.get('trigger_keywords'):
                print(f"   觸發關鍵字: {', '.join(sop.get('trigger_keywords', []))}")
            print()

        # 檢查資料庫
        print("\n" + "="*80)
        print("檢查資料庫中的 SOP")
        print("="*80)

        conn = db_pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # 查詢剛生成的 SOP
            sop_ids = [sop['id'] for sop in generated_sops]
            cur.execute("""
                SELECT
                    id,
                    vendor_id,
                    item_name,
                    LEFT(content, 60) as content_preview,
                    trigger_mode,
                    next_action,
                    is_active
                FROM vendor_sop_items
                WHERE id = ANY(%s)
                ORDER BY id
            """, (sop_ids,))

            db_sops = cur.fetchall()

            if db_sops:
                print(f"\n✅ 資料庫中找到 {len(db_sops)} 筆 SOP：\n")
                for sop in db_sops:
                    print(f"ID {sop['id']}:")
                    print(f"   名稱: {sop['item_name']}")
                    print(f"   內容: {sop['content_preview']}...")
                    print(f"   觸發模式: {sop['trigger_mode']}")
                    print(f"   下一步: {sop['next_action']}")
                    print(f"   啟用: {sop['is_active']}")
                    print()
            else:
                print("❌ 資料庫中沒有找到生成的 SOP")

        finally:
            cur.close()
            db_pool.putconn(conn)

    else:
        print("❌ 沒有成功生成任何 SOP")

    # 關閉資料庫連接池
    db_pool.closeall()

    print("\n" + "="*80)
    print("測試完成")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
