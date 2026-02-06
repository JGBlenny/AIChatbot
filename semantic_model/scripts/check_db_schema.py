#!/usr/bin/env python3
"""
檢查資料庫表結構
"""

import psycopg2
import os

def check_schema():
    """檢查 knowledge_base 表的結構"""

    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "aichatbot"),
            user=os.getenv("DB_USER", "aichatbot_user"),
            password=os.getenv("DB_PASSWORD", "aichatbot_password"),
            port=os.getenv("DB_PORT", 5432)
        )

        cursor = conn.cursor()

        # 查詢表的欄位
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'knowledge_base'
            ORDER BY ordinal_position
        """)

        print("knowledge_base 表結構:")
        print("-" * 40)
        columns = cursor.fetchall()
        for col_name, col_type in columns:
            print(f"  {col_name}: {col_type}")

        # 查詢幾筆範例資料
        print("\n範例資料 (前3筆):")
        print("-" * 40)

        # 先獲取所有欄位名稱
        col_names = [col[0] for col in columns]

        # 查詢資料
        cursor.execute("SELECT * FROM knowledge_base LIMIT 3")
        rows = cursor.fetchall()

        for row in rows:
            print("\n記錄:")
            for i, col_name in enumerate(col_names):
                value = str(row[i])[:100] if row[i] else "NULL"  # 限制顯示長度
                print(f"  {col_name}: {value}")

        cursor.close()
        conn.close()

        return col_names

    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return []

if __name__ == "__main__":
    columns = check_schema()

    if columns:
        print("\n" + "="*40)
        print("✅ 找到的欄位:", columns)