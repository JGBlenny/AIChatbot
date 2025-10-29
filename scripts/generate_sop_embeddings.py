#!/usr/bin/env python3
"""
生成 SOP 項目的雙 Embedding
- Primary:  group_name + item_name  (策略 C: 精準匹配)
- Fallback: content                 (策略 A: 細節查詢)

使用方式：
    python3 scripts/generate_sop_embeddings.py

選項：
    --batch-size N   每批處理 N 個 SOP（預設 10）
    --start-id N     從指定 ID 開始（預設從 1 開始）
    --dry-run        測試模式，不寫入資料庫
"""
import asyncio
import psycopg2
import psycopg2.extras
import os
import sys
import argparse
from dotenv import load_dotenv

# 添加路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'rag-orchestrator'))
from services.embedding_utils import get_embedding_client

load_dotenv()


def get_db_connection():
    """建立資料庫連接"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'aichatbot_admin'),
        user=os.getenv('DB_USER', 'aichatbot'),
        password=os.getenv('DB_PASSWORD', 'aichatbot_password')
    )


async def generate_embeddings(
    batch_size: int = 10,
    start_id: int = 1,
    dry_run: bool = False
):
    """
    生成 SOP 雙 Embedding

    Args:
        batch_size: 每批處理的 SOP 數量
        start_id: 從哪個 ID 開始處理
        dry_run: 測試模式，不寫入資料庫
    """
    print("=" * 100)
    print("🚀 生成 SOP 雙 Embedding")
    print("=" * 100)
    print(f"\n配置:")
    print(f"  批次大小: {batch_size}")
    print(f"  起始 ID: {start_id}")
    print(f"  測試模式: {'是' if dry_run else '否'}")

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 查詢所有需要處理的 SOP
    cursor.execute("""
        SELECT
            si.id,
            sg.group_name,
            si.item_name,
            si.content,
            si.primary_embedding IS NOT NULL as has_primary,
            si.fallback_embedding IS NOT NULL as has_fallback
        FROM vendor_sop_items si
        LEFT JOIN vendor_sop_groups sg ON si.group_id = sg.id
        WHERE
            si.is_active = true
            AND si.id >= %s
        ORDER BY si.id
    """, (start_id,))

    all_sops = cursor.fetchall()
    total = len(all_sops)

    # 統計
    need_update = [s for s in all_sops if not (s['has_primary'] and s['has_fallback'])]
    already_done = len(all_sops) - len(need_update)

    print(f"\n📊 統計:")
    print(f"  總共: {total} 個 SOP")
    print(f"  已完成: {already_done}")
    print(f"  需處理: {len(need_update)}")

    if not need_update:
        print("\n✅ 所有 SOP 都已經有 embedding，無需處理！")
        cursor.close()
        conn.close()
        return

    print(f"\n開始處理 {len(need_update)} 個 SOP...")

    embedding_client = get_embedding_client()

    success = 0
    failed = 0
    skipped = 0

    # 批次處理
    for i in range(0, len(need_update), batch_size):
        batch = need_update[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(need_update) + batch_size - 1) // batch_size

        print(f"\n{'=' * 100}")
        print(f"批次 {batch_num}/{total_batches} ({len(batch)} 個 SOP)")
        print(f"{'=' * 100}")

        for idx, sop in enumerate(batch, 1):
            sop_id = sop['id']
            group_name = sop['group_name'] or ''
            item_name = sop['item_name']
            content = sop['content']

            global_idx = i + idx
            print(f"\n[{global_idx}/{len(need_update)}] 處理 SOP ID={sop_id}")
            print(f"  群組: {group_name[:50]}{'...' if len(group_name) > 50 else ''}")
            print(f"  項目: {item_name}")

            try:
                # 檢查是否需要生成
                need_primary = not sop['has_primary']
                need_fallback = not sop['has_fallback']

                primary_embedding = None
                fallback_embedding = None

                # 生成 primary_embedding (group_name + item_name)
                if need_primary:
                    # 使用冒號分隔格式（例如："租賃申請流程：申請步驟"）
                    if group_name:
                        primary_text = f"{group_name}：{item_name}"
                    else:
                        primary_text = item_name
                    print(f"  生成 Primary: {primary_text[:60]}...")
                    primary_embedding = await embedding_client.get_embedding(primary_text)

                    if not primary_embedding:
                        raise Exception("Primary embedding 生成失敗")
                else:
                    print(f"  跳過 Primary (已存在)")

                # 生成 fallback_embedding (content)
                if need_fallback:
                    print(f"  生成 Fallback: {content[:60]}...")
                    fallback_embedding = await embedding_client.get_embedding(content)

                    if not fallback_embedding:
                        raise Exception("Fallback embedding 生成失敗")
                else:
                    print(f"  跳過 Fallback (已存在)")

                # 更新資料庫
                if not dry_run and (primary_embedding or fallback_embedding):
                    update_parts = []
                    update_values = []

                    if primary_embedding:
                        primary_vector = embedding_client.to_pgvector_format(primary_embedding)
                        update_parts.append("primary_embedding = %s::vector")
                        update_values.append(primary_vector)

                    if fallback_embedding:
                        fallback_vector = embedding_client.to_pgvector_format(fallback_embedding)
                        update_parts.append("fallback_embedding = %s::vector")
                        update_values.append(fallback_vector)

                    # 更新元數據
                    if primary_embedding:
                        embedding_text_value = primary_text if group_name else item_name
                        update_parts.append("embedding_text = %s")
                        update_values.append(embedding_text_value)

                    update_parts.append("embedding_updated_at = NOW()")
                    update_parts.append("embedding_status = %s")
                    update_values.append('completed')

                    update_values.append(sop_id)

                    cursor.execute(f"""
                        UPDATE vendor_sop_items
                        SET {', '.join(update_parts)}
                        WHERE id = %s
                    """, tuple(update_values))

                    conn.commit()
                    success += 1
                    print(f"  ✅ 成功更新資料庫")
                elif dry_run:
                    print(f"  🔍 測試模式: 跳過寫入")
                    success += 1
                else:
                    skipped += 1
                    print(f"  ⏭️  跳過 (無需更新)")

            except Exception as e:
                failed += 1
                print(f"  ❌ 錯誤: {e}")
                conn.rollback()

                # 詳細錯誤日誌
                import traceback
                print(f"\n詳細錯誤:")
                traceback.print_exc()

        # 批次間休息（避免 API rate limit）
        if i + batch_size < len(need_update):
            print(f"\n⏸️  休息 2 秒後繼續下一批...")
            await asyncio.sleep(2)

    cursor.close()
    conn.close()

    print("\n" + "=" * 100)
    print(f"✅ 處理完成！")
    print(f"   成功: {success}")
    print(f"   失敗: {failed}")
    print(f"   跳過: {skipped}")
    print("=" * 100)

    if failed > 0:
        print(f"\n⚠️  有 {failed} 個 SOP 處理失敗，請檢查上方錯誤日誌")

    if dry_run:
        print(f"\n🔍 測試模式完成，未實際寫入資料庫")


async def verify_embeddings():
    """驗證 embeddings 生成狀況"""
    print("\n" + "=" * 100)
    print("🔍 驗證 Embeddings 生成狀況")
    print("=" * 100)

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(primary_embedding) as has_primary,
            COUNT(fallback_embedding) as has_fallback,
            COUNT(*) FILTER (
                WHERE primary_embedding IS NOT NULL
                AND fallback_embedding IS NOT NULL
            ) as has_both,
            COUNT(*) FILTER (
                WHERE primary_embedding IS NULL
                OR fallback_embedding IS NULL
            ) as missing
        FROM vendor_sop_items
        WHERE is_active = true
    """)

    stats = cursor.fetchone()

    print(f"\n統計結果:")
    print(f"  總 SOP 數: {stats['total']}")
    print(f"  有 Primary: {stats['has_primary']} ({stats['has_primary']/stats['total']*100:.1f}%)")
    print(f"  有 Fallback: {stats['has_fallback']} ({stats['has_fallback']/stats['total']*100:.1f}%)")
    print(f"  兩者皆有: {stats['has_both']} ({stats['has_both']/stats['total']*100:.1f}%)")
    print(f"  缺少任一: {stats['missing']}")

    if stats['missing'] > 0:
        print(f"\n⚠️  還有 {stats['missing']} 個 SOP 缺少 embedding")
    else:
        print(f"\n✅ 所有活躍 SOP 都已生成 embeddings！")

    cursor.close()
    conn.close()


def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description="生成 SOP 雙 Embedding（Primary + Fallback）"
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='每批處理的 SOP 數量（預設 10）'
    )
    parser.add_argument(
        '--start-id',
        type=int,
        default=1,
        help='從哪個 SOP ID 開始處理（預設 1）'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='測試模式，不寫入資料庫'
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='僅驗證現有 embeddings，不生成新的'
    )

    args = parser.parse_args()

    if args.verify_only:
        asyncio.run(verify_embeddings())
    else:
        asyncio.run(generate_embeddings(
            batch_size=args.batch_size,
            start_id=args.start_id,
            dry_run=args.dry_run
        ))

        # 生成完後驗證
        asyncio.run(verify_embeddings())


if __name__ == "__main__":
    main()
