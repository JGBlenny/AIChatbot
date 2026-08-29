#!/usr/bin/env python3
"""
重新生成所有 Embeddings（不包含 Keywords）
用於部署時確保 embeddings 使用統一架構 V2 的策略
Date: 2026-02-11

根據測試結果：
- 0 個關鍵字的 embedding 表現最佳
- 關鍵字透過獨立機制處理，避免稀釋效應
"""

import asyncio
import asyncpg
import os
import sys
import time
from typing import Optional

# 添加服務路徑
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
rag_orchestrator_path = os.path.join(project_root, 'rag-orchestrator')

# 如果在 Docker 容器內，直接使用 /app
if os.path.exists('/.dockerenv'):
    sys.path.insert(0, '/app')
else:
    sys.path.append(rag_orchestrator_path)


def get_db_config():
    """獲取資料庫配置"""
    # 在 Docker 內使用 'db' 作為 host
    is_docker = os.path.exists('/.dockerenv')

    return {
        'host': os.getenv('DB_HOST', 'db' if is_docker else 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'aichatbot_admin'),
        'user': os.getenv('DB_USER', 'aichatbot'),
        'password': os.getenv('DB_PASSWORD', 'aichatbot_password')
    }


async def regenerate_sop_embeddings(pool: asyncpg.Pool, dry_run: bool = False) -> dict:
    """
    重新生成 SOP embeddings（不包含 keywords）

    Args:
        pool: 資料庫連接池
        dry_run: 是否為預覽模式

    Returns:
        執行結果統計
    """
    print("\n" + "=" * 60)
    print("SOP Embeddings 重新生成")
    print("=" * 60)

    from services.sop_embedding_generator import generate_sop_embeddings_async

    async with pool.acquire() as conn:
        # 查詢需要更新的 SOP
        rows = await conn.fetch("""
            SELECT id, item_name, keywords,
                   primary_embedding IS NOT NULL as has_embedding
            FROM vendor_sop_items
            WHERE is_active = TRUE
            ORDER BY id
        """)

        if not rows:
            print("⚠️  沒有找到任何 SOP")
            return {'total': 0, 'success': 0, 'failed': 0}

        # 分類統計
        with_keywords = [r for r in rows if r['keywords'] and len(r['keywords']) > 0]
        has_embedding = [r for r in rows if r['has_embedding']]

        print(f"📊 SOP 統計：")
        print(f"  總數: {len(rows)}")
        print(f"  有 keywords: {len(with_keywords)}")
        print(f"  有 embedding: {len(has_embedding)}")

        if dry_run:
            print("\n🔍 預覽模式 - 將會處理以下 SOP:")
            for row in rows[:10]:  # 只顯示前 10 個
                kw_status = "✓" if row['keywords'] else "✗"
                emb_status = "✓" if row['has_embedding'] else "✗"
                print(f"  ID {row['id']:3d}: {row['item_name'][:30]:30} [Keywords: {kw_status}] [Embedding: {emb_status}]")

            if len(rows) > 10:
                print(f"  ... 還有 {len(rows) - 10} 個")

            return {'total': len(rows), 'would_process': len(rows)}

        # 實際處理
        print(f"\n開始處理 {len(rows)} 個 SOP...")
        success = 0
        failed = 0

        for i, row in enumerate(rows, 1):
            sop_id = row['id']
            item_name = row['item_name']
            keywords = row['keywords']

            if i % 10 == 1 or i == 1:
                print(f"\n進度: {i}/{len(rows)}")

            try:
                result = await generate_sop_embeddings_async(pool, sop_id)
                if result:
                    success += 1
                    print(f"  ✅ ID {sop_id}: {item_name[:30]}")
                else:
                    failed += 1
                    print(f"  ❌ ID {sop_id}: {item_name[:30]}")

                # 避免太快
                await asyncio.sleep(0.05)

            except Exception as e:
                failed += 1
                print(f"  ❌ ID {sop_id}: {str(e)}")

        return {'total': len(rows), 'success': success, 'failed': failed}


async def regenerate_knowledge_embeddings(pool: asyncpg.Pool, dry_run: bool = False) -> dict:
    """
    重新生成知識庫 embeddings（不包含 keywords）

    Args:
        pool: 資料庫連接池
        dry_run: 是否為預覽模式

    Returns:
        執行結果統計
    """
    print("\n" + "=" * 60)
    print("知識庫 Embeddings 重新生成")
    print("=" * 60)

    from services.embedding_utils import get_embedding_client
    # D2：scoring surface 的唯一實作點（⛔ 不得在此自寫 summary/answer 優先序）
    from services.retrieval_representation import scoring_surface
    embedding_client = get_embedding_client()

    async with pool.acquire() as conn:
        # 查詢需要更新的知識
        rows = await conn.fetch("""
            SELECT id, question_summary, answer, keywords,
                   embedding IS NOT NULL as has_embedding,
                   -- ⚠️ 本腳本跑**全庫**，必然會掃到已宣告 retrieval_representation 的列。
                   --    不取這兩欄就會把它們的 embedding **靜默改回** legacy surface，
                   --    造成「reranker 吃新宣告、vector 吃舊 summary」的半遷移狀態。
                   generation_metadata->>'retrieval_representation'
                       AS retrieval_representation,
                   generation_metadata->'retrieval_representation_provenance'->>'source'
                       AS retrieval_representation_source
            FROM knowledge_base
            WHERE question_summary IS NOT NULL
            ORDER BY id
        """)

        if not rows:
            print("⚠️  沒有找到任何知識")
            return {'total': 0, 'success': 0, 'failed': 0}

        # 分類統計
        with_keywords = [r for r in rows if r['keywords'] and len(r['keywords']) > 0]
        has_embedding = [r for r in rows if r['has_embedding']]

        print(f"📊 知識庫統計：")
        print(f"  總數: {len(rows)}")
        print(f"  有 keywords: {len(with_keywords)}")
        print(f"  有 embedding: {len(has_embedding)}")

        if dry_run:
            print("\n🔍 預覽模式 - 將會處理以下知識:")
            for row in rows[:10]:  # 只顯示前 10 個
                kw_status = "✓" if row['keywords'] else "✗"
                emb_status = "✓" if row['has_embedding'] else "✗"
                print(f"  ID {row['id']:3d}: {row['question_summary'][:30]:30} [Keywords: {kw_status}] [Embedding: {emb_status}]")

            if len(rows) > 10:
                print(f"  ... 還有 {len(rows) - 10} 個")

            return {'total': len(rows), 'would_process': len(rows)}

        # 實際處理
        print(f"\n開始處理 {len(rows)} 個知識...")
        success = 0
        failed = 0

        for i, row in enumerate(rows, 1):
            kb_id = row['id']
            question = row['question_summary']

            if i % 10 == 1 or i == 1:
                print(f"\n進度: {i}/{len(rows)}")

            try:
                # ⚠️ 已宣告且經審查者以宣告為 surface（與 reranker 同一份契約函式，D2）；
                #    未宣告者維持原行為：只使用 question_summary 生成 embedding。
                # 根據實測：加入 answer 會降低 9.2% 的檢索匹配度（30 題測試，86.7% 受負面影響）
                # 原因：answer 包含的格式化內容、操作步驟會稀釋語意
                text, surface_source = scoring_surface(dict(row))
                embedding = await embedding_client.get_embedding(text)

                if embedding:
                    # 轉換為 pgvector 格式
                    embedding_str = embedding_client.to_pgvector_format(embedding)

                    # 更新資料庫
                    await conn.execute("""
                        UPDATE knowledge_base
                        SET embedding = $1::vector, updated_at = NOW()
                        WHERE id = $2
                    """, embedding_str, kb_id)

                    success += 1
                    print(f"  ✅ ID {kb_id}: {question[:30]}")
                else:
                    failed += 1
                    print(f"  ❌ ID {kb_id}: 生成失敗")

                # 避免太快
                await asyncio.sleep(0.05)

            except Exception as e:
                failed += 1
                print(f"  ❌ ID {kb_id}: {str(e)}")

        return {'total': len(rows), 'success': success, 'failed': failed}


async def main(dry_run: bool = False, target: Optional[str] = None):
    """
    主函式

    Args:
        dry_run: 是否為預覽模式
        target: 處理目標 ('sop', 'knowledge', 或 None 表示全部)
    """
    print("=" * 60)
    print("Embeddings 重新生成工具（統一架構 V2）")
    print("=" * 60)
    print("\n策略：Embeddings 不包含 Keywords")
    print("原因：根據實測，純 embedding 表現最佳，避免關鍵字稀釋效應")

    if dry_run:
        print("\n🔍 預覽模式 - 不會實際修改資料")

    # 建立資料庫連接池
    db_config = get_db_config()
    print(f"\n連接資料庫: {db_config['host']}:{db_config['port']}/{db_config['database']}")

    try:
        pool = await asyncpg.create_pool(**db_config, min_size=1, max_size=5)
    except Exception as e:
        print(f"❌ 資料庫連接失敗: {e}")
        return 1

    results = {}
    start_time = time.time()

    try:
        # 處理 SOP
        if target in [None, 'sop']:
            sop_result = await regenerate_sop_embeddings(pool, dry_run)
            results['sop'] = sop_result

        # 處理知識庫
        if target in [None, 'knowledge']:
            kb_result = await regenerate_knowledge_embeddings(pool, dry_run)
            results['knowledge'] = kb_result

        # 總結
        elapsed = time.time() - start_time
        print("\n" + "=" * 60)
        print("執行總結")
        print("=" * 60)

        if dry_run:
            print("預覽結果：")
            if 'sop' in results:
                print(f"  SOP: 將處理 {results['sop'].get('would_process', 0)} 個")
            if 'knowledge' in results:
                print(f"  知識庫: 將處理 {results['knowledge'].get('would_process', 0)} 個")
        else:
            print("處理結果：")
            if 'sop' in results:
                r = results['sop']
                print(f"  SOP: 成功 {r['success']}/{r['total']}, 失敗 {r['failed']}")
            if 'knowledge' in results:
                r = results['knowledge']
                print(f"  知識庫: 成功 {r['success']}/{r['total']}, 失敗 {r['failed']}")

        print(f"\n執行時間: {elapsed:.1f} 秒")

        # 返回狀態碼
        total_failed = sum(r.get('failed', 0) for r in results.values())
        return 0 if total_failed == 0 else 1

    finally:
        await pool.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='重新生成 Embeddings（統一架構 V2）')
    parser.add_argument('--dry-run', action='store_true', help='預覽模式，不實際修改')
    parser.add_argument('--target', choices=['sop', 'knowledge'], help='指定處理目標')
    parser.add_argument('--yes', '-y', action='store_true', help='跳過確認提示')

    args = parser.parse_args()

    # 確認執行
    if not args.dry_run and not args.yes:
        target_msg = args.target if args.target else "SOP 和 知識庫"
        print(f"\n⚠️  即將重新生成 {target_msg} 的所有 embeddings")
        print("這將會：")
        print("  1. 覆寫現有的 embeddings")
        print("  2. 使用純文字生成（不包含 keywords）")
        print("  3. 可能需要幾分鐘時間")

        confirm = input("\n確認繼續？(y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ 已取消")
            sys.exit(0)

    # 執行
    exit_code = asyncio.run(main(args.dry_run, args.target))
    sys.exit(exit_code)