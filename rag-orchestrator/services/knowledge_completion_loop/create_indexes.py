"""
建立缺少的 pgvector 索引 (Task 7.4)
"""

import os
import psycopg2

def create_missing_indexes():
    """建立缺少的索引"""

    print("=" * 60)
    print("建立缺少的 pgvector 索引")
    print("=" * 60)

    # 連接資料庫
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5433')),
        'database': os.getenv('DB_NAME', 'aichatbot_admin'),
        'user': os.getenv('DB_USER', 'aichatbot_admin'),
        'password': os.getenv('DB_PASSWORD', 'aichatbot_admin_password')
    }

    conn = psycopg2.connect(**db_config)
    conn.autocommit = True  # 對於 CREATE INDEX CONCURRENTLY 需要 autocommit

    try:
        cur = conn.cursor()

        # 建立 vendor_sop_items.primary_embedding 索引
        print("\n1. 檢查 vendor_sop_items.primary_embedding 索引")
        print("-" * 60)

        cur.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'vendor_sop_items'
              AND indexdef LIKE '%primary_embedding%'
              AND indexdef LIKE '%ivfflat%'
        """)

        existing = cur.fetchone()
        if existing:
            print(f"⚠️  索引已存在: {existing[0]}")
        else:
            print("建立索引: idx_vendor_sop_items_primary_embedding_ivfflat")
            print("（這可能需要幾分鐘，取決於資料量）")

            try:
                cur.execute("""
                    CREATE INDEX CONCURRENTLY idx_vendor_sop_items_primary_embedding_ivfflat
                    ON vendor_sop_items
                    USING ivfflat (primary_embedding vector_cosine_ops)
                    WITH (lists = 100)
                """)
                print("✅ 索引建立成功！")
            except Exception as e:
                print(f"❌ 索引建立失敗: {e}")

        # 建立 loop_execution_logs 複合索引
        print("\n2. 檢查 loop_execution_logs 複合索引")
        print("-" * 60)

        cur.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'loop_execution_logs'
              AND indexname = 'idx_loop_execution_logs_event_type_loop_id'
        """)

        existing = cur.fetchone()
        if existing:
            print(f"⚠️  索引已存在: {existing[0]}")
        else:
            print("建立索引: idx_loop_execution_logs_event_type_loop_id")

            try:
                cur.execute("""
                    CREATE INDEX CONCURRENTLY idx_loop_execution_logs_event_type_loop_id
                    ON loop_execution_logs (event_type, loop_id)
                """)
                print("✅ 索引建立成功！")
            except Exception as e:
                print(f"❌ 索引建立失敗: {e}")

        # 驗證所有 embedding 索引
        print("\n3. 驗證所有 embedding 索引")
        print("-" * 60)

        cur.execute("""
            SELECT
                tablename,
                indexname,
                LEFT(indexdef, 100) as indexdef_preview
            FROM pg_indexes
            WHERE (indexdef LIKE '%embedding%' OR indexname LIKE '%embedding%')
              AND tablename IN ('knowledge_base', 'vendor_sop_items', 'loop_generated_knowledge')
            ORDER BY tablename, indexname
        """)

        indexes = cur.fetchall()
        for table, idx_name, idx_def in indexes:
            print(f"\n表: {table}")
            print(f"  索引: {idx_name}")
            print(f"  定義: {idx_def}...")

    finally:
        cur.close()
        conn.close()

    print("\n" + "=" * 60)
    print("索引建立完成")
    print("=" * 60)


if __name__ == "__main__":
    create_missing_indexes()
