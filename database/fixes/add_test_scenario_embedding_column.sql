-- 【未來優化】為 test_scenarios 添加 question_embedding 欄位
-- 用途：支援測試情境的向量相似度搜尋和去重
-- 執行時機：當需要完整的語意去重功能時執行此腳本

-- ============================================================
-- 1. 添加 question_embedding 欄位
-- ============================================================

ALTER TABLE test_scenarios
ADD COLUMN IF NOT EXISTS question_embedding vector(1536);

-- 添加索引以加速向量搜尋
CREATE INDEX IF NOT EXISTS idx_test_scenarios_question_embedding
ON test_scenarios
USING ivfflat (question_embedding vector_cosine_ops)
WITH (lists = 100);

COMMENT ON COLUMN test_scenarios.question_embedding IS '測試問題的向量嵌入（1536 維度），用於語意相似度搜尋';

-- ============================================================
-- 2. 恢復完整的 find_similar_test_scenario 函數
-- ============================================================

CREATE OR REPLACE FUNCTION find_similar_test_scenario(
    p_question_embedding vector(1536),
    p_similarity_threshold DECIMAL DEFAULT 0.85
)
RETURNS TABLE (
    similar_scenario_id INTEGER,
    similar_question TEXT,
    similarity_score DECIMAL,
    scenario_status VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ts.id AS similar_scenario_id,
        ts.test_question AS similar_question,
        (1 - (ts.question_embedding <=> p_question_embedding))::DECIMAL(5,4) AS similarity_score,
        ts.status AS scenario_status
    FROM test_scenarios ts
    WHERE ts.question_embedding IS NOT NULL
      AND (1 - (ts.question_embedding <=> p_question_embedding)) >= p_similarity_threshold
    ORDER BY ts.question_embedding <=> p_question_embedding
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION find_similar_test_scenario IS
'查詢測試情境中語意相似的問題（使用向量相似度，閾值預設 0.85）';

-- ============================================================
-- 3. 顯示提示訊息
-- ============================================================

DO $$
DECLARE
    v_total_scenarios INTEGER;
    v_scenarios_with_embedding INTEGER;
BEGIN
    SELECT COUNT(*), COUNT(question_embedding)
    INTO v_total_scenarios, v_scenarios_with_embedding
    FROM test_scenarios;

    RAISE NOTICE '✅ 已為 test_scenarios 添加 question_embedding 欄位';
    RAISE NOTICE '   總測試情境數: %', v_total_scenarios;
    RAISE NOTICE '   已有 embedding: %', v_scenarios_with_embedding;
    RAISE NOTICE '   需要生成 embedding: %', v_total_scenarios - v_scenarios_with_embedding;

    IF v_total_scenarios > v_scenarios_with_embedding THEN
        RAISE NOTICE '';
        RAISE NOTICE '⚠️  下一步：為現有的測試情境生成 embedding';
        RAISE NOTICE '   建議使用 Python 腳本批量生成 embedding';
    END IF;
END $$;

-- ============================================================
-- 使用說明
-- ============================================================

/*
執行此腳本後，需要為現有的測試情境生成 embedding：

1. 使用 Python 腳本生成 embedding：

```python
import asyncpg
from openai import AsyncOpenAI

async def generate_embeddings_for_test_scenarios():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='aichatbot',
        password='aichatbot_password',
        database='aichatbot_admin'
    )

    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # 取得所有沒有 embedding 的測試情境
    scenarios = await conn.fetch("""
        SELECT id, test_question
        FROM test_scenarios
        WHERE question_embedding IS NULL
    """)

    for scenario in scenarios:
        # 生成 embedding
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=scenario['test_question']
        )

        embedding = response.data[0].embedding
        vector_str = '[' + ','.join(str(x) for x in embedding) + ']'

        # 更新資料庫
        await conn.execute("""
            UPDATE test_scenarios
            SET question_embedding = $1::vector
            WHERE id = $2
        """, vector_str, scenario['id'])

        print(f"✓ Generated embedding for scenario #{scenario['id']}")

    await conn.close()
```

2. 或者在新增測試情境時自動生成 embedding
*/
