"""
Simple verification script for migration 1.1 (no pytest dependency)
Feature: backtest-knowledge-refinement
Task: 1.1 - Supplement knowledge_completion_loops table fields
"""

import asyncio
import asyncpg
import os
import sys


async def verify_migration():
    """Verify that all migration 1.1 changes were applied successfully."""

    print("=" * 80)
    print("Migration 1.1 Verification")
    print("=" * 80)

    # Connect to database
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"),
        password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin")
    )

    errors = []
    passed = 0

    try:
        # Test 1: Check parent_loop_id column
        print("\n[TEST 1] Checking parent_loop_id column...")
        result = await conn.fetchrow("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'knowledge_completion_loops'
            AND column_name = 'parent_loop_id'
        """)

        if result and result['data_type'] == 'integer' and result['is_nullable'] == 'YES':
            print("✓ PASS: parent_loop_id column exists with correct type")
            passed += 1
        else:
            error = f"✗ FAIL: parent_loop_id column issue: {result}"
            print(error)
            errors.append(error)

        # Test 2: Check max_iterations column
        print("\n[TEST 2] Checking max_iterations column...")
        result = await conn.fetchrow("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'knowledge_completion_loops'
            AND column_name = 'max_iterations'
        """)

        if result and result['data_type'] == 'integer' and result['column_default'] == '10':
            print("✓ PASS: max_iterations column exists with default value 10")
            passed += 1
        else:
            error = f"✗ FAIL: max_iterations column issue: {result}"
            print(error)
            errors.append(error)

        # Test 3: Check scenario_ids column
        print("\n[TEST 3] Checking scenario_ids column...")
        result = await conn.fetchrow("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'knowledge_completion_loops'
            AND column_name = 'scenario_ids'
        """)

        if result and result['data_type'] == 'ARRAY':
            print("✓ PASS: scenario_ids column exists as INTEGER[]")
            passed += 1
        else:
            error = f"✗ FAIL: scenario_ids column issue: {result}"
            print(error)
            errors.append(error)

        # Test 4: Check selection_strategy column
        print("\n[TEST 4] Checking selection_strategy column...")
        result = await conn.fetchrow("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'knowledge_completion_loops'
            AND column_name = 'selection_strategy'
        """)

        if result and result['data_type'] == 'character varying' and result['character_maximum_length'] == 50:
            print("✓ PASS: selection_strategy column exists with VARCHAR(50)")
            passed += 1
        else:
            error = f"✗ FAIL: selection_strategy column issue: {result}"
            print(error)
            errors.append(error)

        # Test 5: Check difficulty_distribution column
        print("\n[TEST 5] Checking difficulty_distribution column...")
        result = await conn.fetchrow("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'knowledge_completion_loops'
            AND column_name = 'difficulty_distribution'
        """)

        if result and result['data_type'] == 'jsonb':
            print("✓ PASS: difficulty_distribution column exists as JSONB")
            passed += 1
        else:
            error = f"✗ FAIL: difficulty_distribution column issue: {result}"
            print(error)
            errors.append(error)

        # Test 6: Check GIN index on scenario_ids
        print("\n[TEST 6] Checking idx_loops_scenario_ids GIN index...")
        result = await conn.fetchrow("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'knowledge_completion_loops'
            AND indexname = 'idx_loops_scenario_ids'
        """)

        if result and 'gin' in result['indexdef'].lower():
            print("✓ PASS: GIN index on scenario_ids exists")
            passed += 1
        else:
            error = f"✗ FAIL: GIN index issue: {result}"
            print(error)
            errors.append(error)

        # Test 7: Check index on parent_loop_id
        print("\n[TEST 7] Checking idx_loops_parent index...")
        result = await conn.fetchrow("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'knowledge_completion_loops'
            AND indexname = 'idx_loops_parent'
        """)

        if result and 'parent_loop_id' in result['indexdef']:
            print("✓ PASS: Index on parent_loop_id exists")
            passed += 1
        else:
            error = f"✗ FAIL: parent_loop_id index issue: {result}"
            print(error)
            errors.append(error)

        # Test 8: Check foreign key constraint
        print("\n[TEST 8] Checking parent_loop_id foreign key constraint...")
        result = await conn.fetchrow("""
            SELECT conname, pg_get_constraintdef(oid) as definition
            FROM pg_constraint
            WHERE conrelid = 'knowledge_completion_loops'::regclass
            AND conname LIKE '%parent_loop_id%'
            AND contype = 'f'
        """)

        if result and 'REFERENCES knowledge_completion_loops(id)' in result['definition']:
            print("✓ PASS: Foreign key constraint exists")
            passed += 1
        else:
            error = f"✗ FAIL: Foreign key constraint issue: {result}"
            print(error)
            errors.append(error)

        # Test 9: Integration test - insert and retrieve data
        print("\n[TEST 9] Integration test - insert loop with new columns...")
        loop_id = await conn.fetchval("""
            INSERT INTO knowledge_completion_loops (
                loop_name, status, vendor_id, config, target_pass_rate,
                max_iterations, scenario_ids, selection_strategy, difficulty_distribution
            ) VALUES (
                'test_migration_verification', 'pending', 999, '{}'::jsonb, 0.85,
                10, ARRAY[1, 2, 3], 'stratified_random', '{"easy": 1, "medium": 1, "hard": 1}'::jsonb
            )
            RETURNING id
        """)

        result = await conn.fetchrow("""
            SELECT scenario_ids, selection_strategy, difficulty_distribution
            FROM knowledge_completion_loops
            WHERE id = $1
        """, loop_id)

        # Cleanup
        await conn.execute("DELETE FROM knowledge_completion_loops WHERE id = $1", loop_id)

        if (result and
            result['scenario_ids'] == [1, 2, 3] and
            result['selection_strategy'] == 'stratified_random'):
            print("✓ PASS: Data insertion and retrieval works correctly")
            passed += 1
        else:
            error = f"✗ FAIL: Integration test failed: {result}"
            print(error)
            errors.append(error)

    finally:
        await conn.close()

    # Print summary
    print("\n" + "=" * 80)
    print(f"SUMMARY: {passed}/9 tests passed")
    print("=" * 80)

    if errors:
        print("\nFailed tests:")
        for error in errors:
            print(f"  {error}")
        sys.exit(1)
    else:
        print("\n✓ All tests passed! Migration 1.1 verified successfully.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(verify_migration())
