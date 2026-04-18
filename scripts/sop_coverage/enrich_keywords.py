"""
批量補充 SOP 關鍵字同義詞
用 LLM 為每筆 SOP 生成租客可能的其他說法，補入 keywords 和 trigger_keywords
"""
import asyncio
import json
import os
import sys
from typing import List, Dict

import openai
import asyncpg
from dotenv import load_dotenv

load_dotenv()

ENRICH_PROMPT = """你是包租代管公司的客服主管。

以下是一筆 SOP 的標題和現有關鍵字。請列出「租客可能用來問這個問題的其他說法」，包含：
- 同義詞（如「垃圾分類」↔「資源回收」）
- 口語說法（如「退租」↔「搬走」↔「不租了」）
- 簡稱或縮寫（如「冷氣」↔「空調」↔「AC」）
- 相關動作（如「繳租金」↔「付房租」↔「匯款」）

## SOP 標題
{item_name}

## 現有關鍵字
{keywords}

## 請回答
用 JSON 陣列格式回答（不要加其他文字），列出 5-10 個補充關鍵字：
["關鍵字1", "關鍵字2", ...]"""


async def enrich_one(
    client: openai.AsyncOpenAI,
    item_name: str,
    keywords: List[str],
    model: str = "gpt-4o-mini",
    max_retries: int = 2,
) -> List[str]:
    """為單筆 SOP 生成補充關鍵字"""
    for attempt in range(max_retries + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{
                    "role": "user",
                    "content": ENRICH_PROMPT.format(
                        item_name=item_name,
                        keywords=", ".join(keywords) if keywords else "(無)",
                    ),
                }],
                temperature=0.3,
                max_tokens=200,
            )
            content = (response.choices[0].message.content or "").strip()
            if not content:
                if attempt < max_retries:
                    await asyncio.sleep(1)
                    continue
                return []
            # 嘗試提取 JSON 陣列（可能被 markdown 包裹）
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            result = json.loads(content)
            if isinstance(result, list):
                return [kw for kw in result if isinstance(kw, str) and len(kw) <= 20]
            return []
        except json.JSONDecodeError:
            if attempt < max_retries:
                await asyncio.sleep(1)
                continue
            print(f"  ⚠️ JSON 解析失敗 ({item_name[:20]})")
            return []
        except Exception as e:
            if attempt < max_retries:
                await asyncio.sleep(1)
                continue
            print(f"  ⚠️ 關鍵字生成失敗 ({item_name[:20]}): {e}")
            return []


async def enrich_all_sops(vendor_id: int = 2, batch_size: int = 10, concurrency: int = 5):
    """批量補充所有 active SOP 的關鍵字"""
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
    )
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    semaphore = asyncio.Semaphore(concurrency)

    # 取所有 active SOP
    sops = await pool.fetch('''
        SELECT id, item_name, keywords, trigger_keywords
        FROM vendor_sop_items
        WHERE vendor_id = $1 AND is_active = true
        ORDER BY id
    ''', vendor_id)

    print(f"=== 補充關鍵字：{len(sops)} 筆 SOP ===\n")

    updated = 0
    total_new_kw = 0

    for i in range(0, len(sops), batch_size):
        batch = sops[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(sops) + batch_size - 1) // batch_size
        print(f"批次 {batch_num}/{total_batches}")

        async def process_one(sop):
            nonlocal updated, total_new_kw
            async with semaphore:
                existing_kw = set(sop["keywords"] or [])
                existing_tk = set(sop["trigger_keywords"] or [])
                all_existing = existing_kw | existing_tk

                new_kw = await enrich_one(
                    client,
                    sop["item_name"],
                    list(all_existing),
                )

                # 只加真正新的
                truly_new = [kw for kw in new_kw if kw not in all_existing]
                if not truly_new:
                    return

                merged_kw = list(existing_kw | set(truly_new))
                merged_tk = list(existing_tk | set(truly_new))

                await pool.execute('''
                    UPDATE vendor_sop_items
                    SET keywords = $1, trigger_keywords = $2, updated_at = NOW()
                    WHERE id = $3
                ''', merged_kw, merged_tk, sop["id"])

                updated += 1
                total_new_kw += len(truly_new)
                print(f"  ✅ [{sop['id']}] {sop['item_name'][:25]} +{len(truly_new)} 個: {', '.join(truly_new[:3])}{'...' if len(truly_new) > 3 else ''}")

        await asyncio.gather(*[process_one(s) for s in batch])

    print(f"\n=== 完成 ===")
    print(f"  更新 {updated}/{len(sops)} 筆 SOP")
    print(f"  新增 {total_new_kw} 個關鍵字")

    await pool.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="補充 SOP 關鍵字同義詞")
    parser.add_argument("--vendor-id", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()

    asyncio.run(enrich_all_sops(
        vendor_id=args.vendor_id,
        batch_size=args.batch_size,
        concurrency=args.concurrency,
    ))
