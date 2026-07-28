#!/usr/bin/env python3
"""補缺 embedding（targeted 缺嵌補算）：只為 embedding 為 NULL 的 active 知識列生成向量。

- 冪等：只碰 `embedding IS NULL` 的列，已有 embedding 的完全不動（不覆寫）。
- 非互動：無確認提示，可安全放進部署流程／runner。
- 遵守 embedding 完整性鐵則：question_summary 直進 embedding-api，不加前綴、不混 keywords。

在容器內跑（有 asyncpg＋DB/embedding 環境，免手動密碼）：
  # 檔已在 image 內（重建後）：
  docker exec aichatbot-rag-orchestrator python3 tools/embed_missing.py [--dry-run]
  # 檔還沒進 image（用主機的檔餵進容器）：
  docker exec -i aichatbot-rag-orchestrator python3 - < rag-orchestrator/tools/embed_missing.py
"""
import asyncio
import json
import os
import sys
import urllib.request

DRY = "--dry-run" in sys.argv
EMB_URL = os.getenv("EMBEDDING_API_URL", "http://localhost:5001/api/v1/embeddings")


def get_embedding(text: str) -> str:
    req = urllib.request.Request(
        EMB_URL, data=json.dumps({"text": text}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        emb = json.loads(r.read())["embedding"]
    assert len(emb) == 1536, f"embedding 維度異常：{len(emb)}"
    return "[" + ",".join(f"{v:.8f}" for v in emb) + "]"


async def main() -> None:
    import asyncpg
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"), min_size=1, max_size=2)
    n = 0
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, question_summary FROM knowledge_base "
            "WHERE is_active AND embedding IS NULL AND question_summary IS NOT NULL "
            # 排除「系統脈絡／對話規則」：注入/設定列（勿檢索），系統本就不給 embedding。
            # 用 question_summary 前綴判定——category 欄不可靠（有的系統脈絡列 category 掛面向名
            # 如 '條件診斷：帳單' 會漏網；但前綴命名一致）。只補真正走向量檢索的知識/錨點。
            "AND question_summary NOT LIKE '%系統脈絡%' "
            "AND question_summary NOT LIKE '%對話規則%' "
            "ORDER BY id")
        print(f"缺 embedding 的列：{len(rows)} 筆")
        for row in rows:
            print(f"  {'(dry)' if DRY else '▶'} id={row['id']}：{(row['question_summary'] or '')[:40]}")
            if not DRY:
                emb = get_embedding(row["question_summary"])
                await conn.execute(
                    "UPDATE knowledge_base SET embedding=$1::vector WHERE id=$2",
                    emb, row["id"])
                n += 1
    await pool.close()
    print(f"完成：補了 {n} 筆 embedding" + ("（dry-run，未寫入）" if DRY else ""))


if __name__ == "__main__":
    asyncio.run(main())
