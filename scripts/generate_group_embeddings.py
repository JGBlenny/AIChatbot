"""
生成vendor_sop_groups的group_embedding

为所有Group的group_name生成embedding并存储
"""

import sys
import os
import asyncio

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../rag-orchestrator'))

from services.embedding_utils import get_embedding_client
import psycopg2
import psycopg2.extras


def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(
        host='localhost',
        port=5432,
        user='aichatbot',
        password='aichatbot_password',
        database='aichatbot_admin'
    )


async def generate_group_embedding(group_id, group_name, embedding_client):
    """
    为单个Group生成embedding

    Args:
        group_id: Group ID
        group_name: Group名称
        embedding_client: Embedding客户端

    Returns:
        bool: 是否成功
    """
    try:
        # 生成embedding
        embedding = await embedding_client.get_embedding(group_name)

        if not embedding:
            print(f"❌ [Group {group_id}] Embedding生成失败")
            return False

        # 转换为pgvector格式
        vector_str = embedding_client.to_pgvector_format(embedding)

        # 更新数据库
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE vendor_sop_groups
            SET group_embedding = %s::vector
            WHERE id = %s
        """, (vector_str, group_id))

        conn.commit()
        cursor.close()
        conn.close()

        print(f"✅ [Group {group_id}] {group_name[:50]}...")
        return True

    except Exception as e:
        print(f"❌ [Group {group_id}] 生成失败: {e}")
        return False


async def generate_all_group_embeddings(vendor_id=None, batch_size=5):
    """
    批量生成所有Group的embeddings

    Args:
        vendor_id: 指定vendor_id（可选，None表示所有）
        batch_size: 批次大小
    """
    print("=" * 100)
    print("🚀 开始生成Group Embeddings")
    print("=" * 100)

    # 获取所有Group
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if vendor_id:
        cursor.execute("""
            SELECT id, vendor_id, group_name
            FROM vendor_sop_groups
            WHERE vendor_id = %s AND is_active = TRUE
            ORDER BY id
        """, (vendor_id,))
    else:
        cursor.execute("""
            SELECT id, vendor_id, group_name
            FROM vendor_sop_groups
            WHERE is_active = TRUE
            ORDER BY id
        """)

    groups = cursor.fetchall()
    cursor.close()
    conn.close()

    print(f"\n📊 找到 {len(groups)} 个Group需要生成embedding")

    if not groups:
        print("❌ 没有找到任何Group")
        return

    # 初始化embedding客户端
    embedding_client = get_embedding_client()

    # 统计
    success_count = 0
    failed_count = 0

    # 分批处理
    for i in range(0, len(groups), batch_size):
        batch = groups[i:i + batch_size]

        print(f"\n🔄 处理批次 {i // batch_size + 1} ({i + 1}-{min(i + batch_size, len(groups))}/{len(groups)})")

        # 并发处理当前批次
        tasks = [
            generate_group_embedding(group['id'], group['group_name'], embedding_client)
            for group in batch
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
            elif result:
                success_count += 1
            else:
                failed_count += 1

        # 批次间短暂延迟
        if i + batch_size < len(groups):
            await asyncio.sleep(0.5)

    # 最终统计
    print("\n" + "=" * 100)
    print("📊 生成完成统计")
    print("=" * 100)
    print(f"✅ 成功: {success_count}/{len(groups)}")
    print(f"❌ 失败: {failed_count}/{len(groups)}")

    # 验证
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(group_embedding) as with_embedding
        FROM vendor_sop_groups
        WHERE is_active = TRUE
    """)

    stats = cursor.fetchone()
    cursor.close()
    conn.close()

    print(f"\n📈 数据库验证:")
    print(f"   总Group数: {stats[0]}")
    print(f"   有embedding: {stats[1]}")
    print(f"   覆盖率: {stats[1] / stats[0] * 100:.1f}%")


async def regenerate_group_embedding(group_id):
    """
    重新生成单个Group的embedding

    Args:
        group_id: Group ID
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT id, group_name
        FROM vendor_sop_groups
        WHERE id = %s
    """, (group_id,))

    group = cursor.fetchone()
    cursor.close()
    conn.close()

    if not group:
        print(f"❌ Group {group_id} 不存在")
        return False

    print(f"🔄 重新生成 Group {group_id} 的embedding...")

    embedding_client = get_embedding_client()
    result = await generate_group_embedding(group['id'], group['group_name'], embedding_client)

    if result:
        print(f"✅ 成功重新生成 Group {group_id} 的embedding")
    else:
        print(f"❌ 重新生成失败")

    return result


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='生成Group Embeddings')
    parser.add_argument('--vendor-id', type=int, help='指定vendor_id')
    parser.add_argument('--group-id', type=int, help='重新生成单个Group')
    parser.add_argument('--batch-size', type=int, default=5, help='批次大小')

    args = parser.parse_args()

    if args.group_id:
        # 重新生成单个Group
        await regenerate_group_embedding(args.group_id)
    else:
        # 批量生成
        await generate_all_group_embeddings(
            vendor_id=args.vendor_id,
            batch_size=args.batch_size
        )


if __name__ == "__main__":
    asyncio.run(main())
