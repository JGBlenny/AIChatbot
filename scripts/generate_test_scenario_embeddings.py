#!/usr/bin/env python3
"""
生成測試情境的向量嵌入
用途：為 test_scenarios 表中缺少 question_embedding 的記錄生成向量
"""
import os
import sys
import asyncio
import asyncpg
from openai import AsyncOpenAI

# 配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'user': os.getenv('DB_USER', 'aichatbot'),
    'password': os.getenv('DB_PASSWORD', 'aichatbot_password'),
    'database': os.getenv('DB_NAME', 'aichatbot_admin')
}

EMBEDDING_MODEL = "text-embedding-3-small"


async def generate_embeddings_for_test_scenarios():
    """為測試情境生成向量嵌入"""
    print("🔮 開始為測試情境生成向量嵌入...")
    print(f"   資料庫: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print(f"   模型: {EMBEDDING_MODEL}\n")

    # 檢查 API 金鑰
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 錯誤：未設定 OPENAI_API_KEY 環境變數")
        sys.exit(1)

    # 連接資料庫
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        print("✅ 資料庫連接成功\n")
    except Exception as e:
        print(f"❌ 資料庫連接失敗: {e}")
        sys.exit(1)

    # 初始化 OpenAI 客戶端
    client = AsyncOpenAI(api_key=api_key)

    try:
        # 取得所有沒有 embedding 的測試情境
        scenarios = await conn.fetch("""
            SELECT id, test_question
            FROM test_scenarios
            WHERE question_embedding IS NULL
            ORDER BY id
        """)

        total = len(scenarios)
        print(f"📊 找到 {total} 個需要生成 embedding 的測試情境\n")

        if total == 0:
            print("✅ 所有測試情境都已有 embedding，無需處理")
            return

        # 逐個生成 embedding
        success_count = 0
        error_count = 0

        for idx, scenario in enumerate(scenarios, 1):
            scenario_id = scenario['id']
            question = scenario['test_question']

            try:
                print(f"[{idx}/{total}] 處理測試情境 #{scenario_id}")
                print(f"   問題: {question[:80]}{'...' if len(question) > 80 else ''}")

                # 生成 embedding
                response = await client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=question
                )

                embedding = response.data[0].embedding

                # 轉換為 PostgreSQL vector 格式
                vector_str = '[' + ','.join(str(x) for x in embedding) + ']'

                # 更新資料庫
                await conn.execute("""
                    UPDATE test_scenarios
                    SET question_embedding = $1::vector,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = $2
                """, vector_str, scenario_id)

                print(f"   ✅ Embedding 已生成並儲存 (維度: {len(embedding)})\n")
                success_count += 1

                # 避免 rate limit
                if idx < total:
                    await asyncio.sleep(0.1)

            except Exception as e:
                print(f"   ❌ 錯誤: {e}\n")
                error_count += 1
                continue

        # 顯示統計
        print("=" * 60)
        print("📈 執行統計:")
        print(f"   總數: {total}")
        print(f"   成功: {success_count}")
        print(f"   失敗: {error_count}")
        print("=" * 60)

        if success_count > 0:
            print("\n✅ 向量生成完成！")
            print(f"   {success_count} 個測試情境已成功生成 embedding")

    except Exception as e:
        print(f"\n❌ 處理過程發生錯誤: {e}")
        sys.exit(1)

    finally:
        await conn.close()
        print("\n👋 資料庫連接已關閉")


if __name__ == "__main__":
    asyncio.run(generate_embeddings_for_test_scenarios())
