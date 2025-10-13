"""
資料庫工具模組
統一處理所有資料庫配置相關功能，避免代碼重複
"""
import os
import psycopg2
import psycopg2.extras
from typing import Dict, Optional
from contextlib import contextmanager


def get_db_config() -> Dict[str, any]:
    """
    獲取資料庫配置

    從環境變數讀取資料庫連接參數

    Returns:
        資料庫配置字典，包含 host, port, user, password, database
    """
    return {
        'host': os.getenv('DB_HOST', 'postgres'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'user': os.getenv('DB_USER', 'aichatbot'),
        'password': os.getenv('DB_PASSWORD', 'aichatbot_password'),
        'database': os.getenv('DB_NAME', 'aichatbot_admin')
    }


@contextmanager
def get_db_connection(dict_cursor: bool = False):
    """
    獲取資料庫連接（Context Manager）

    使用方式：
    ```python
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM table")
        ...
    ```

    Args:
        dict_cursor: 是否使用 DictCursor（返回字典格式結果）

    Yields:
        psycopg2 連接物件
    """
    config = get_db_config()
    conn = psycopg2.connect(**config)

    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_db_cursor(dict_cursor: bool = False):
    """
    獲取資料庫游標（Context Manager）

    自動管理連接和游標的生命週期

    使用方式：
    ```python
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("SELECT * FROM table")
        results = cursor.fetchall()
    ```

    Args:
        dict_cursor: 是否使用 DictCursor（返回字典格式結果）

    Yields:
        psycopg2 cursor 物件
    """
    config = get_db_config()
    conn = psycopg2.connect(**config)

    try:
        if dict_cursor:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cursor = conn.cursor()

        try:
            yield cursor
            conn.commit()  # 自動提交
        finally:
            cursor.close()
    finally:
        conn.close()


def execute_query(
    query: str,
    params: Optional[tuple] = None,
    dict_cursor: bool = False,
    fetch: str = "all"
) -> any:
    """
    執行查詢並返回結果（便利函數）

    Args:
        query: SQL 查詢語句
        params: 查詢參數
        dict_cursor: 是否使用 DictCursor
        fetch: 返回方式 ('all', 'one', 'none')

    Returns:
        查詢結果（根據 fetch 參數決定）

    Example:
        ```python
        # 查詢多行
        results = execute_query(
            "SELECT * FROM intents WHERE is_enabled = %s",
            (True,),
            dict_cursor=True,
            fetch="all"
        )

        # 查詢單行
        result = execute_query(
            "SELECT id FROM intents WHERE name = %s",
            ("rent_payment",),
            fetch="one"
        )

        # 執行更新（不返回結果）
        execute_query(
            "UPDATE intents SET usage_count = usage_count + 1 WHERE name = %s",
            ("rent_payment",),
            fetch="none"
        )
        ```
    """
    with get_db_cursor(dict_cursor=dict_cursor) as cursor:
        cursor.execute(query, params)

        if fetch == "all":
            return cursor.fetchall()
        elif fetch == "one":
            return cursor.fetchone()
        elif fetch == "none":
            return None
        else:
            raise ValueError(f"Invalid fetch mode: {fetch}")


# ============================================================
# 使用範例與測試
# ============================================================

if __name__ == "__main__":
    # 測試資料庫配置
    print("=" * 60)
    print("測試 DB Utils")
    print("=" * 60)

    # 測試 1: 獲取配置
    print("\n📝 測試 1: 獲取資料庫配置")
    config = get_db_config()
    print(f"   Host: {config['host']}")
    print(f"   Port: {config['port']}")
    print(f"   Database: {config['database']}")
    print(f"   User: {config['user']}")

    # 測試 2: 使用 Context Manager 連接
    print("\n📝 測試 2: 使用 get_db_connection")
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM intents")
            count = cursor.fetchone()[0]
            cursor.close()
            print(f"   ✅ 意圖總數: {count}")
    except Exception as e:
        print(f"   ❌ 錯誤: {e}")

    # 測試 3: 使用便利的 cursor context manager
    print("\n📝 測試 3: 使用 get_db_cursor (dict_cursor=True)")
    try:
        with get_db_cursor(dict_cursor=True) as cursor:
            cursor.execute("""
                SELECT name, type, is_enabled
                FROM intents
                LIMIT 3
            """)
            results = cursor.fetchall()
            for row in results:
                print(f"   - {row['name']}: {row['type']} (啟用: {row['is_enabled']})")
    except Exception as e:
        print(f"   ❌ 錯誤: {e}")

    # 測試 4: 使用便利函數
    print("\n📝 測試 4: 使用 execute_query 便利函數")
    try:
        results = execute_query(
            "SELECT name FROM intents WHERE is_enabled = %s LIMIT 3",
            (True,),
            dict_cursor=True,
            fetch="all"
        )
        print(f"   ✅ 查詢到 {len(results)} 個啟用的意圖")
        for row in results:
            print(f"      - {row['name']}")
    except Exception as e:
        print(f"   ❌ 錯誤: {e}")

    print("\n" + "=" * 60)
    print("測試完成！")
    print("=" * 60)
