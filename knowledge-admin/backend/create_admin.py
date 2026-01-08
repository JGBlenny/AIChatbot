"""
創建系統管理員腳本
用於部署時初始化第一個管理員帳號

使用方式：
  python create_admin.py --username admin --password your_password --email admin@example.com

或者交互式輸入：
  python create_admin.py
"""
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
from datetime import datetime
import argparse
import getpass

# 數據庫配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "aichatbot_admin")
DB_USER = os.getenv("DB_USER", "aichatbot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "aichatbot_password")


def get_db_connection():
    """建立資料庫連線"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor
    )


def hash_password(password: str) -> str:
    """使用 bcrypt 加密密碼"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def check_admin_exists(conn, username: str) -> bool:
    """檢查管理員是否已存在"""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM admins WHERE username = %s", (username,))
        return cur.fetchone() is not None


def get_super_admin_role(conn):
    """獲取超級管理員角色 ID"""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM roles WHERE name = 'super_admin'")
        result = cur.fetchone()
        return result['id'] if result else None


def create_admin(username: str, password: str, email: str, full_name: str = None):
    """創建管理員帳號並分配超級管理員角色"""
    conn = None
    try:
        conn = get_db_connection()

        # 檢查帳號是否已存在
        if check_admin_exists(conn, username):
            print(f"❌ 錯誤：帳號 '{username}' 已存在")
            return False

        # 獲取超級管理員角色
        super_admin_role_id = get_super_admin_role(conn)
        if not super_admin_role_id:
            print(f"❌ 錯誤：找不到 super_admin 角色，請先初始化權限系統")
            return False

        # 加密密碼
        hashed_password = hash_password(password)
        now = datetime.now()

        # 插入管理員
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO admins (username, password_hash, email, full_name, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (username, hashed_password, email, full_name, True, now, now))

            admin_id = cur.fetchone()['id']

            # 分配超級管理員角色
            cur.execute("""
                INSERT INTO admin_roles (admin_id, role_id, created_at)
                VALUES (%s, %s, %s)
            """, (admin_id, super_admin_role_id, now))

            print(f"✅ 成功創建管理員帳號")
            print(f"   帳號：{username}")
            print(f"   Email：{email}")
            print(f"   角色：超級管理員（擁有所有權限）")

        conn.commit()
        return True

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"❌ 數據庫錯誤：{e}")
        return False
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 錯誤：{e}")
        return False
    finally:
        if conn:
            conn.close()


def main():
    parser = argparse.ArgumentParser(description='創建系統管理員帳號')
    parser.add_argument('--username', help='管理員帳號')
    parser.add_argument('--password', help='管理員密碼')
    parser.add_argument('--email', help='管理員 Email')
    parser.add_argument('--full-name', help='管理員姓名（可選）')

    args = parser.parse_args()

    # 如果沒有提供參數，則交互式輸入
    if not args.username:
        print("=== 創建系統管理員 ===\n")
        username = input("請輸入帳號: ").strip()
        if not username:
            print("❌ 帳號不能為空")
            sys.exit(1)
    else:
        username = args.username

    if not args.password:
        password = getpass.getpass("請輸入密碼: ")
        password_confirm = getpass.getpass("請再次輸入密碼: ")
        if password != password_confirm:
            print("❌ 兩次密碼不一致")
            sys.exit(1)
        if len(password) < 6:
            print("❌ 密碼長度至少 6 個字符")
            sys.exit(1)
    else:
        password = args.password

    if not args.email:
        email = input("請輸入 Email: ").strip()
        if not email:
            print("❌ Email 不能為空")
            sys.exit(1)
    else:
        email = args.email

    full_name = args.full_name or input("請輸入姓名（可選，直接回車跳過）: ").strip() or None

    # 確認創建
    print("\n=== 確認信息 ===")
    print(f"帳號：{username}")
    print(f"Email：{email}")
    print(f"姓名：{full_name or '(未設置)'}")
    print(f"權限：所有權限")

    if not args.password:  # 交互式模式才需要確認
        confirm = input("\n確認創建？(y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ 已取消")
            sys.exit(0)

    # 創建管理員
    success = create_admin(username, password, email, full_name)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
