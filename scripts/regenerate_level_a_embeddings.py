#!/usr/bin/env python3
"""**唯一被批准的 Level-A embedding 重生路徑**（業主定案 2026-08-29）。

## 為什麼需要一支專用腳本，而不是「跑 regenerate」

本專案有 **5 個** embedding surface 產生點，其中兩條是**全庫**重生且彼此矛盾：

```text
scripts/regenerate_all_embeddings.py           → 全庫；legacy surface = question_summary
knowledge-admin app.py::regenerate_all_embeddings → 全庫 backfill；
                                                  legacy surface = (summary or answer[:200]) + 關鍵字
```
⇒ 「跑 regenerate」是**有歧義**的指令：跑哪一條，整庫 surface 就變成哪一種，
   而且事後**無法從資料回推**當初跑的是哪條 ⇒ **證據失去 provenance**。

⚠️ 因此 Level-A 遷移**只准**走本腳本：

```text
✅ 射程鎖死：只處理 LEVEL_A_ROWS，且**只處理已有 approved declaration 的列**
✅ surface 唯一：一律呼叫 services/retrieval_representation.scoring_surface()
✅ 拒絕半套：任一目標列的 provenance 不是 reviewed ⇒ **整批中止**，不做部分寫入
✅ 預設 dry-run：要真的寫入必須明示 --apply
```

## ⚠️ 與「重建 semantic-model」是**同一個 migration step**

```text
只重建容器不重生 embedding ＝ reranker 吃新宣告、vector 吃舊 summary
                            ＝ 形式上接線、前半段仍是舊 semantic surface 的**假完成**
```

用法：
    python3 scripts/regenerate_level_a_embeddings.py            # dry-run（預設）
    python3 scripts/regenerate_level_a_embeddings.py --apply    # 實際寫入
"""
import asyncio
import os
import sys

import asyncpg

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if os.path.exists('/.dockerenv'):
    sys.path.insert(0, '/app')
else:
    sys.path.append(os.path.join(project_root, 'rag-orchestrator'))

#: 凍結的 Level-A scope（與不變量 13 同一組）
LEVEL_A_ROWS = [3402, 3406, 3495, 3496, 3498, 3499, 3519, 4640, 4656, 4657]


def get_db_config():
    is_docker = os.path.exists('/.dockerenv')
    return {
        'host': os.getenv('DB_HOST', 'db' if is_docker else 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'aichatbot_admin'),
        'user': os.getenv('DB_USER', 'aichatbot'),
        'password': os.getenv('DB_PASSWORD', 'aichatbot_password'),
    }


async def run(apply: bool) -> int:
    from services.embedding_utils import get_embedding_client
    # D2：scoring surface 的唯一實作點（⛔ 不得在此自寫優先序）
    from services.retrieval_representation import (
        SURFACE_SOURCE_DECLARED,
        scoring_surface,
    )

    pool = await asyncpg.create_pool(**get_db_config(), min_size=1, max_size=2)
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, question_summary,
                       generation_metadata->>'retrieval_representation'
                           AS retrieval_representation,
                       generation_metadata->'retrieval_representation_provenance'->>'source'
                           AS retrieval_representation_source
                FROM knowledge_base
                WHERE id = ANY($1::int[])
                ORDER BY id
                """,
                LEVEL_A_ROWS,
            )
        if len(rows) != len(LEVEL_A_ROWS):
            print(f"❌ 中止：Level-A 母體應為 {len(LEVEL_A_ROWS)} 筆，實得 {len(rows)} 筆")
            return 1

        targets, skipped = [], []
        for r in rows:
            text, source = scoring_surface(dict(r))
            if source == SURFACE_SOURCE_DECLARED:
                targets.append((r['id'], text))
            else:
                skipped.append((r['id'], source))

        print(f"Level-A {len(LEVEL_A_ROWS)} 筆：已宣告 {len(targets)}、未宣告 {len(skipped)}")
        for kb_id, source in skipped:
            print(f"  ⏭️  {kb_id}：{source}（⛔ 本腳本不碰未宣告的列——"
                  f"它們的 surface 仍由 legacy 路徑決定）")
        if not targets:
            print("❌ 中止：沒有任何已宣告的列。"
                  "⚠️ 這代表 population 尚未完成，⛔ 現在重生 embedding 沒有意義。")
            return 1

        client = get_embedding_client()
        for kb_id, text in targets:
            print(f"  {'✍️ ' if apply else '🔍'} {kb_id}：surface ← reviewed declaration"
                  f"（{len(text)} 字）")
            if not apply:
                continue
            emb = await client.get_embedding(text)
            if not emb:
                print(f"  ❌ 中止：{kb_id} 取不到 embedding——⛔ 不做部分寫入")
                return 1
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE knowledge_base SET embedding = $1::vector, updated_at = NOW() "
                    "WHERE id = $2",
                    client.to_pgvector_format(emb), kb_id,
                )
        if not apply:
            print("\n🔍 dry-run：未寫入任何資料。要實際執行請加 --apply")
        else:
            print(f"\n✅ 已重生 {len(targets)} 筆 Level-A embedding（surface＝reviewed declaration）")
            print("⚠️ 下一步必須驗：retriever transport ／ vector ／ reranker "
                  "三處實際使用的是同一份 reviewed text。")
        return 0
    finally:
        await pool.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(run("--apply" in sys.argv)))
