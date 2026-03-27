"""
Test suite for migration 1.1: knowledge_completion_loops table enhancements
Feature: backtest-knowledge-refinement
Task: 1.1 - Supplement knowledge_completion_loops table fields

This test verifies that all required columns and indexes were added correctly.
"""

import pytest
import asyncpg
import os


@pytest.fixture
async def db_pool():
    """Create a database connection pool for testing."""
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
        min_size=1,
        max_size=2
    )
    yield pool
    await pool.close()


@pytest.mark.asyncio
async def test_parent_loop_id_column_exists(db_pool):
    """Test that parent_loop_id column exists with correct type and constraints."""
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'knowledge_completion_loops'
            AND column_name = 'parent_loop_id'
        """)

        assert result is not None, "parent_loop_id column does not exist"
        assert result['data_type'] == 'integer', f"Expected integer, got {result['data_type']}"
        assert result['is_nullable'] == 'YES', "parent_loop_id should be nullable"


@pytest.mark.asyncio
async def test_max_iterations_column_exists(db_pool):
    """Test that max_iterations column exists with correct default value."""
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT column_name, data_type, column_default, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'knowledge_completion_loops'
            AND column_name = 'max_iterations'
        """)

        assert result is not None, "max_iterations column does not exist"
        assert result['data_type'] == 'integer', f"Expected integer, got {result['data_type']}"
        assert result['column_default'] == '10', f"Expected default 10, got {result['column_default']}"
        assert result['is_nullable'] == 'YES', "max_iterations should be nullable"


@pytest.mark.asyncio
async def test_scenario_ids_column_exists(db_pool):
    """Test that scenario_ids column exists as integer array."""
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'knowledge_completion_loops'
            AND column_name = 'scenario_ids'
        """)

        assert result is not None, "scenario_ids column does not exist"
        assert result['data_type'] == 'ARRAY', f"Expected ARRAY, got {result['data_type']}"
        assert result['is_nullable'] == 'YES', "scenario_ids should be nullable"


@pytest.mark.asyncio
async def test_selection_strategy_column_exists(db_pool):
    """Test that selection_strategy column exists with correct type."""
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT column_name, data_type, is_nullable, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'knowledge_completion_loops'
            AND column_name = 'selection_strategy'
        """)

        assert result is not None, "selection_strategy column does not exist"
        assert result['data_type'] == 'character varying', f"Expected varchar, got {result['data_type']}"
        assert result['character_maximum_length'] == 50, f"Expected length 50, got {result['character_maximum_length']}"
        assert result['is_nullable'] == 'YES', "selection_strategy should be nullable"


@pytest.mark.asyncio
async def test_difficulty_distribution_column_exists(db_pool):
    """Test that difficulty_distribution column exists as JSONB."""
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'knowledge_completion_loops'
            AND column_name = 'difficulty_distribution'
        """)

        assert result is not None, "difficulty_distribution column does not exist"
        assert result['data_type'] == 'jsonb', f"Expected jsonb, got {result['data_type']}"
        assert result['is_nullable'] == 'YES', "difficulty_distribution should be nullable"


@pytest.mark.asyncio
async def test_scenario_ids_gin_index_exists(db_pool):
    """Test that GIN index on scenario_ids exists (requirement 4.5)."""
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'knowledge_completion_loops'
            AND indexname = 'idx_loops_scenario_ids'
        """)

        assert result is not None, "idx_loops_scenario_ids index does not exist"
        assert 'USING gin' in result['indexdef'].lower(), "Index should be GIN type"
        assert 'scenario_ids' in result['indexdef'], "Index should be on scenario_ids column"


@pytest.mark.asyncio
async def test_parent_loop_id_index_exists(db_pool):
    """Test that index on parent_loop_id exists (requirement 10.4)."""
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'knowledge_completion_loops'
            AND indexname = 'idx_loops_parent'
        """)

        assert result is not None, "idx_loops_parent index does not exist"
        assert 'parent_loop_id' in result['indexdef'], "Index should be on parent_loop_id column"


@pytest.mark.asyncio
async def test_parent_loop_id_foreign_key_exists(db_pool):
    """Test that foreign key constraint on parent_loop_id exists."""
    async with db_pool.acquire() as conn:
        result = await conn.fetchrow("""
            SELECT conname, pg_get_constraintdef(oid) as definition
            FROM pg_constraint
            WHERE conrelid = 'knowledge_completion_loops'::regclass
            AND conname LIKE '%parent_loop_id%'
            AND contype = 'f'
        """)

        assert result is not None, "parent_loop_id foreign key constraint does not exist"
        assert 'REFERENCES knowledge_completion_loops(id)' in result['definition'], \
            "Foreign key should reference knowledge_completion_loops(id)"


@pytest.mark.asyncio
async def test_insert_loop_with_new_columns(db_pool):
    """Integration test: Insert a loop with new columns and verify data integrity."""
    async with db_pool.acquire() as conn:
        # Insert test loop
        loop_id = await conn.fetchval("""
            INSERT INTO knowledge_completion_loops (
                loop_name,
                status,
                vendor_id,
                config,
                target_pass_rate,
                max_iterations,
                scenario_ids,
                selection_strategy,
                difficulty_distribution
            ) VALUES (
                'test_migration_1_1',
                'pending',
                999,
                '{}'::jsonb,
                0.85,
                10,
                ARRAY[1, 2, 3, 5, 10],
                'stratified_random',
                '{"easy": 1, "medium": 3, "hard": 1}'::jsonb
            )
            RETURNING id
        """)

        try:
            # Verify data was inserted correctly
            result = await conn.fetchrow("""
                SELECT
                    max_iterations,
                    scenario_ids,
                    selection_strategy,
                    difficulty_distribution
                FROM knowledge_completion_loops
                WHERE id = $1
            """, loop_id)

            assert result is not None, "Failed to retrieve inserted loop"
            assert result['max_iterations'] == 10
            assert result['scenario_ids'] == [1, 2, 3, 5, 10]
            assert result['selection_strategy'] == 'stratified_random'
            assert result['difficulty_distribution'] == {"easy": 1, "medium": 3, "hard": 1}

        finally:
            # Cleanup test data
            await conn.execute("DELETE FROM knowledge_completion_loops WHERE id = $1", loop_id)


@pytest.mark.asyncio
async def test_parent_loop_id_self_reference(db_pool):
    """Test that parent_loop_id can reference another loop (batch association)."""
    async with db_pool.acquire() as conn:
        # Create parent loop
        parent_id = await conn.fetchval("""
            INSERT INTO knowledge_completion_loops (
                loop_name, status, vendor_id, config, target_pass_rate
            ) VALUES (
                'test_parent_loop', 'completed', 999, '{}'::jsonb, 0.85
            )
            RETURNING id
        """)

        try:
            # Create child loop with parent reference
            child_id = await conn.fetchval("""
                INSERT INTO knowledge_completion_loops (
                    loop_name, status, vendor_id, config, target_pass_rate, parent_loop_id
                ) VALUES (
                    'test_child_loop', 'pending', 999, '{}'::jsonb, 0.85, $1
                )
                RETURNING id
            """, parent_id)

            # Verify parent-child relationship
            result = await conn.fetchrow("""
                SELECT parent_loop_id, loop_name
                FROM knowledge_completion_loops
                WHERE id = $1
            """, child_id)

            assert result['parent_loop_id'] == parent_id
            assert result['loop_name'] == 'test_child_loop'

        finally:
            # Cleanup (child first due to foreign key)
            await conn.execute("DELETE FROM knowledge_completion_loops WHERE id = $1", child_id)
            await conn.execute("DELETE FROM knowledge_completion_loops WHERE id = $1", parent_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
