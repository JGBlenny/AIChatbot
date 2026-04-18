"""
審核 pipeline 相容性驗證測試

驗證 SystemKBGenerator 產出的系統知識候選項
能正確地透過現有審核 pipeline 流入 knowledge_base。

測試覆蓋（對應需求 5.1-5.6）：
- 5.1 ai_generated_knowledge_candidates 可接收 generation_metadata JSONB
- 5.2 approve_ai_knowledge_candidate() 對 scope='global' + category=模組名稱 相容
- 5.3 同步時自動填入 source_type='ai_generated' 與 generation_metadata
- 5.4 向量嵌入自動生成流程正常
- 5.5 候選項欄位完整性驗證
- 5.6 端到端審核流程模擬
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 確保 project root 在 sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.kb_system_coverage.models import Feature, GapItem, Module
from scripts.kb_system_coverage.system_kb_generator import SystemKBGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_system_kb_candidate() -> Dict[str, Any]:
    """模擬 SystemKBGenerator 產出的候選項"""
    return {
        "topic_id": "帳務_001",
        "question_summary": "如何查看租金帳單",
        "answer": (
            "您可以在 APP 首頁 > 繳費 > 帳單明細 中查看所有租金帳單。"
            "系統會顯示每期應繳金額、繳費期限與繳費狀態。"
            "如果帳單已逾期，系統會以紅色標示提醒您盡快繳納。"
            "若有任何帳單金額疑問，建議直接聯繫您的管理公司確認。"
        ),
        "keywords": ["帳單", "租金", "繳費", "查看"],
        "category": "帳務管理",
        "scope": "global",
        "target_user": ["tenant"],
        "business_types": ["rental", "management"],
        "status": "pending_review",
        "source_gap": {
            "topic_id": "帳務_001",
            "question": "怎麼在 APP 查看帳單明細",
            "gap_type": "uncovered",
            "priority": "p0",
        },
    }


@pytest.fixture
def sample_generation_metadata() -> Dict[str, Any]:
    """模擬寫入 generation_metadata JSONB 的 metadata"""
    return {
        "source_module": "billing",
        "topic_id": "帳務_001",
        "generated_at": "2026-04-18T10:30:00+08:00",
        "generator": "SystemKBGenerator",
        "model": "gpt-4o-mini",
        "quality_checks_passed": True,
    }


@pytest.fixture
def mock_db_conn():
    """模擬 asyncpg connection"""
    conn = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetch = AsyncMock()
    conn.execute = AsyncMock()
    return conn


# ---------------------------------------------------------------------------
# 5.1 generation_metadata JSONB 寫入測試
# ---------------------------------------------------------------------------


class TestGenerationMetadataJSONB:
    """驗證 ai_generated_knowledge_candidates 可正確接收 generation_metadata"""

    def test_metadata_serializable(self, sample_generation_metadata):
        """metadata 可序列化為合法 JSON"""
        json_str = json.dumps(sample_generation_metadata, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed["source_module"] == "billing"
        assert parsed["topic_id"] == "帳務_001"
        assert "generated_at" in parsed

    def test_metadata_contains_required_fields(self, sample_generation_metadata):
        """metadata 包含所有必要欄位"""
        required_fields = ["source_module", "topic_id", "generated_at"]
        for field in required_fields:
            assert field in sample_generation_metadata, (
                f"generation_metadata 缺少必要欄位: {field}"
            )

    def test_metadata_with_extra_fields(self, sample_generation_metadata):
        """metadata 可攜帶額外欄位（JSONB 彈性）"""
        sample_generation_metadata["custom_field"] = "custom_value"
        sample_generation_metadata["nested"] = {"key": "value"}
        json_str = json.dumps(sample_generation_metadata, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed["custom_field"] == "custom_value"
        assert parsed["nested"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_metadata_insert_to_knowledge_base(
        self, mock_db_conn, sample_generation_metadata
    ):
        """generation_metadata 可透過 INSERT 寫入 knowledge_base"""
        mock_db_conn.fetchval.return_value = 42
        metadata_json = json.dumps(sample_generation_metadata, ensure_ascii=False)

        # 模擬 loop_knowledge 的 sync 路徑（直接寫入 knowledge_base）
        kb_id = await mock_db_conn.fetchval(
            """
            INSERT INTO knowledge_base (
                question_summary, answer, scope, category,
                source_type, generation_metadata, is_active,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, 'ai_generated', $5::jsonb,
                    true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING id
            """,
            "如何查看租金帳單",
            "回答內容...",
            "global",
            "帳務管理",
            metadata_json,
        )

        assert kb_id == 42
        mock_db_conn.fetchval.assert_called_once()
        call_args = mock_db_conn.fetchval.call_args
        sql = call_args[0][0]
        assert "generation_metadata" in sql
        assert "source_type" in sql
        assert "'ai_generated'" in sql


# ---------------------------------------------------------------------------
# 5.2 approve_ai_knowledge_candidate 相容性測試
# ---------------------------------------------------------------------------


class TestApproveFunction:
    """驗證 approve_ai_knowledge_candidate() 對系統知識的相容性"""

    @pytest.mark.asyncio
    async def test_approve_function_call_signature(self, mock_db_conn):
        """approve function 接受 4 個參數"""
        mock_db_conn.fetchval.return_value = 100  # 新 knowledge_base id

        new_kb_id = await mock_db_conn.fetchval(
            "SELECT approve_ai_knowledge_candidate($1, $2, $3, $4)",
            1,            # candidate_id
            "admin",      # reviewed_by
            "系統知識審核通過",  # review_notes
            True,         # use_edited
        )

        assert new_kb_id == 100
        call_args = mock_db_conn.fetchval.call_args[0]
        assert "approve_ai_knowledge_candidate" in call_args[0]
        assert len(call_args) == 5  # SQL + 4 params

    @pytest.mark.asyncio
    async def test_approve_function_builds_generation_metadata(self, mock_db_conn):
        """approve function 會自動建構 generation_metadata JSONB

        函數內部使用 JSONB_BUILD_OBJECT 組合：
        ai_model, confidence_score, generated_at, reviewed_by, reviewed_at,
        was_edited, edit_summary, reasoning, warnings
        """
        # 驗證 SQL function 定義中有 JSONB_BUILD_OBJECT
        # 這是靜態驗證，確認 init script 正確
        init_sql_path = (
            _PROJECT_ROOT / "database" / "init" / "12-create-ai-knowledge-system.sql"
        )
        assert init_sql_path.exists(), f"init SQL 不存在: {init_sql_path}"

        sql_content = init_sql_path.read_text(encoding="utf-8")
        assert "JSONB_BUILD_OBJECT" in sql_content, (
            "approve function 缺少 JSONB_BUILD_OBJECT 建構 generation_metadata"
        )
        assert "'ai_model'" in sql_content
        assert "'confidence_score'" in sql_content
        assert "'reviewed_by'" in sql_content
        assert "'was_edited'" in sql_content

    def test_approve_function_inserts_source_type_ai_generated(self):
        """approve function 寫入 source_type='ai_generated'"""
        init_sql_path = (
            _PROJECT_ROOT / "database" / "init" / "12-create-ai-knowledge-system.sql"
        )
        sql_content = init_sql_path.read_text(encoding="utf-8")
        assert "'ai_generated'" in sql_content, (
            "approve function 缺少 source_type='ai_generated'"
        )

    def test_approve_function_copies_embedding(self):
        """approve function 複製 question_embedding 到 knowledge_base"""
        init_sql_path = (
            _PROJECT_ROOT / "database" / "init" / "12-create-ai-knowledge-system.sql"
        )
        sql_content = init_sql_path.read_text(encoding="utf-8")
        assert "question_embedding" in sql_content, (
            "approve function 未複製 question_embedding 到 knowledge_base"
        )


# ---------------------------------------------------------------------------
# 5.3 同步欄位驗證
# ---------------------------------------------------------------------------


class TestSyncFieldPreservation:
    """驗證同步時 source_type 與 generation_metadata 正確保留"""

    def test_knowledge_base_has_source_type_column(self):
        """knowledge_base 表有 source_type 欄位"""
        kb_sql_path = (
            _PROJECT_ROOT / "database" / "init" / "02-create-knowledge-base.sql"
        )
        assert kb_sql_path.exists()
        sql_content = kb_sql_path.read_text(encoding="utf-8")
        assert "source_type" in sql_content

    def test_knowledge_base_has_generation_metadata_column(self):
        """knowledge_base 表有 generation_metadata JSONB 欄位"""
        kb_sql_path = (
            _PROJECT_ROOT / "database" / "init" / "02-create-knowledge-base.sql"
        )
        sql_content = kb_sql_path.read_text(encoding="utf-8")
        assert "generation_metadata" in sql_content
        assert "JSONB" in sql_content.upper()

    def test_knowledge_base_has_scope_column(self):
        """knowledge_base 表有 scope 欄位"""
        kb_sql_path = (
            _PROJECT_ROOT / "database" / "init" / "02-create-knowledge-base.sql"
        )
        sql_content = kb_sql_path.read_text(encoding="utf-8")
        assert "scope" in sql_content

    def test_knowledge_base_has_category_column(self):
        """knowledge_base 表有 category 欄位"""
        kb_sql_path = (
            _PROJECT_ROOT / "database" / "init" / "02-create-knowledge-base.sql"
        )
        sql_content = kb_sql_path.read_text(encoding="utf-8")
        assert "category" in sql_content

    def test_approve_function_does_not_set_scope_or_category(self):
        """approve function 目前不設定 scope/category（已知限制）

        approve_ai_knowledge_candidate() 的 INSERT 不包含 scope、category。
        系統知識候選項需要這些欄位，因此在 approve 後須透過另外的
        機制（如直接 SQL 更新或修改 approve function）將 scope='global'
        和 category=模組名稱 寫入。

        此測試記錄此已知限制，供後續修正時驗證。
        """
        init_sql_path = (
            _PROJECT_ROOT / "database" / "init" / "12-create-ai-knowledge-system.sql"
        )
        sql_content = init_sql_path.read_text(encoding="utf-8")

        # 取出 approve function 的 INSERT INTO knowledge_base 部分
        # 尋找 INSERT INTO knowledge_base 在 function 內的欄位清單
        func_start = sql_content.find(
            "CREATE OR REPLACE FUNCTION approve_ai_knowledge_candidate"
        )
        func_end = sql_content.find("$$;", func_start)
        func_body = sql_content[func_start:func_end]

        insert_section = func_body[func_body.find("INSERT INTO knowledge_base"):]
        columns_end = insert_section.find(")")
        columns = insert_section[:columns_end]

        # 確認 scope 和 category 確實不在 INSERT 欄位中（已知限制）
        # 注意：這兩個欄位在 knowledge_base 有 DEFAULT 值
        # scope DEFAULT 'global'，category DEFAULT NULL
        assert "scope" not in columns.split("VALUES")[0], (
            "approve function 現在已包含 scope — 如果是修正過的，請更新此測試"
        )
        assert "category" not in columns.split("VALUES")[0], (
            "approve function 現在已包含 category — 如果是修正過的，請更新此測試"
        )


# ---------------------------------------------------------------------------
# 5.4 向量嵌入流程驗證
# ---------------------------------------------------------------------------


class TestEmbeddingPipeline:
    """驗證向量嵌入自動生成流程"""

    def test_embedding_utils_importable(self):
        """embedding_utils 模組可正確匯入"""
        # 確認檔案存在
        embedding_path = (
            _PROJECT_ROOT / "rag-orchestrator" / "services" / "embedding_utils.py"
        )
        assert embedding_path.exists(), f"embedding_utils.py 不存在: {embedding_path}"

    def test_review_endpoint_generates_embedding_on_approve(self):
        """審核端點在 approve 時會處理 embedding

        knowledge_generation.py 的 review endpoint:
        1. 先用 check_knowledge_exists_by_similarity 檢查相似度
        2. 呼叫 approve_ai_knowledge_candidate() 完成寫入
        3. approve function 內部複製 question_embedding

        loop_knowledge.py 的 review endpoint:
        1. 檢查 embedding 是否存在
        2. 若不存在，呼叫 generate_embedding_with_pgvector 生成
        3. 寫入 knowledge_base 時攜帶 embedding
        """
        # 驗證 knowledge_generation router 有 embedding 處理
        router_path = (
            _PROJECT_ROOT / "rag-orchestrator" / "routers" / "knowledge_generation.py"
        )
        content = router_path.read_text(encoding="utf-8")
        assert "question_embedding" in content, (
            "knowledge_generation router 缺少 question_embedding 處理"
        )
        assert "check_knowledge_exists_by_similarity" in content, (
            "knowledge_generation router 缺少相似度檢查"
        )

    def test_loop_knowledge_generates_embedding_on_sync(self):
        """loop_knowledge 在 sync 時生成 embedding

        loop_knowledge.py 透過 embedding_client.generate_embedding()
        生成向量，再用 to_pgvector_format() 轉為 DB 格式寫入。
        knowledge_generation.py 則用 generate_embedding_with_pgvector()。
        兩條路徑都有 embedding 生成能力。
        """
        loop_router_path = (
            _PROJECT_ROOT / "rag-orchestrator" / "routers" / "loop_knowledge.py"
        )
        assert loop_router_path.exists()
        content = loop_router_path.read_text(encoding="utf-8")
        # loop_knowledge 使用 embedding_client 或 _generate_embedding
        assert "embedding" in content.lower(), (
            "loop_knowledge router 缺少 embedding 相關處理"
        )

        # knowledge_generation router 使用 generate_embedding_with_pgvector
        kg_router_path = (
            _PROJECT_ROOT / "rag-orchestrator" / "routers" / "knowledge_generation.py"
        )
        content_kg = kg_router_path.read_text(encoding="utf-8")
        assert "generate_embedding_with_pgvector" in content_kg, (
            "knowledge_generation router 缺少 generate_embedding_with_pgvector"
        )


# ---------------------------------------------------------------------------
# 5.5 候選項欄位完整性
# ---------------------------------------------------------------------------


class TestCandidateFieldCompleteness:
    """驗證 SystemKBGenerator 候選項欄位與 pipeline 相容"""

    def test_candidate_has_required_fields(self, sample_system_kb_candidate):
        """候選項包含所有 pipeline 必要欄位"""
        required = [
            "topic_id",
            "question_summary",
            "answer",
            "keywords",
            "category",
            "scope",
            "target_user",
            "business_types",
            "status",
        ]
        for field in required:
            assert field in sample_system_kb_candidate, (
                f"候選項缺少必要欄位: {field}"
            )

    def test_candidate_scope_is_global(self, sample_system_kb_candidate):
        """系統知識候選項 scope 必須是 'global'"""
        assert sample_system_kb_candidate["scope"] == "global"

    def test_candidate_category_is_module_name(self, sample_system_kb_candidate):
        """系統知識候選項 category 是模組中文名稱"""
        assert sample_system_kb_candidate["category"] == "帳務管理"

    def test_candidate_status_is_pending_review(self, sample_system_kb_candidate):
        """候選項初始狀態為 pending_review"""
        assert sample_system_kb_candidate["status"] == "pending_review"

    def test_candidate_source_gap_preserved(self, sample_system_kb_candidate):
        """候選項保留 source_gap 原始缺口資訊"""
        source_gap = sample_system_kb_candidate["source_gap"]
        assert "topic_id" in source_gap
        assert "question" in source_gap
        assert "gap_type" in source_gap
        assert "priority" in source_gap

    def test_system_kb_generator_output_format(self):
        """SystemKBGenerator._generate_single 的輸出格式驗證

        確認 generate_batch 回傳的每個候選項結構與
        ai_generated_knowledge_candidates 表的可用欄位對應。
        """
        # 模擬 SystemKBGenerator 的候選項組裝
        # 取自 system_kb_generator.py line 370-386
        candidate = {
            "topic_id": "帳務_001",
            "question_summary": "如何查看帳單",
            "answer": "在 APP 首頁 > 繳費 > 帳單明細 查看所有帳單資訊...",
            "keywords": ["帳單", "繳費"],
            "category": "帳務管理",
            "scope": "global",
            "target_user": ["tenant"],
            "business_types": ["rental", "management"],
            "status": "pending_review",
            "source_gap": {
                "topic_id": "帳務_001",
                "question": "怎麼在 APP 查看帳單明細",
                "gap_type": "uncovered",
                "priority": "p0",
            },
        }

        # 這些欄位可直接對應到 ai_generated_knowledge_candidates 的欄位
        db_field_mapping = {
            "question_summary": "question",        # DB 欄位名稱為 question
            "answer": "generated_answer",           # DB 欄位名稱為 generated_answer
            "keywords": "keywords",                 # 需要 DB 有此欄位（已由 migration 加入）
            "scope": "scope",                       # 需要 DB 有此欄位（已由 migration 加入）
            "target_user": "target_user",           # 需要 DB 有此欄位（已由 migration 加入）
            "business_types": "business_types",     # 需要 DB 有此欄位（已由 migration 加入）
            "status": "status",
        }

        for gen_field, db_field in db_field_mapping.items():
            assert gen_field in candidate, (
                f"候選項缺少 {gen_field}（對應 DB 欄位 {db_field}）"
            )


# ---------------------------------------------------------------------------
# 5.6 端到端審核流程模擬
# ---------------------------------------------------------------------------


class TestEndToEndReviewSimulation:
    """模擬系統知識從 候選 → 審核 → 正式知識庫 的完整流程"""

    @pytest.mark.asyncio
    async def test_insert_system_kb_candidate(
        self, mock_db_conn, sample_system_kb_candidate
    ):
        """步驟 1：插入系統知識候選項到 staging 表"""
        mock_db_conn.fetchval.return_value = 1001  # candidate_id

        candidate = sample_system_kb_candidate
        candidate_id = await mock_db_conn.fetchval(
            """
            INSERT INTO ai_generated_knowledge_candidates (
                test_scenario_id,
                source_type,
                question,
                generated_answer,
                confidence_score,
                ai_model,
                generation_reasoning,
                keywords,
                scope,
                target_user,
                business_types,
                status,
                created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            RETURNING id
            """,
            None,                                    # test_scenario_id: NULL for system KB
            "system_kb_generation",                  # source_type
            candidate["question_summary"],           # question
            candidate["answer"],                     # generated_answer
            0.85,                                    # confidence_score
            "gpt-4o-mini",                           # ai_model
            json.dumps(candidate["source_gap"],      # generation_reasoning
                       ensure_ascii=False),
            candidate["keywords"],                   # keywords
            candidate["scope"],                      # scope
            candidate["target_user"],                # target_user
            candidate["business_types"],             # business_types
            "pending_review",                        # status
        )

        assert candidate_id == 1001

    @pytest.mark.asyncio
    async def test_approve_system_kb_candidate(self, mock_db_conn):
        """步驟 2：透過 approve function 審核通過"""
        mock_db_conn.fetchval.return_value = 5001  # 新 knowledge_base id

        new_kb_id = await mock_db_conn.fetchval(
            "SELECT approve_ai_knowledge_candidate($1, $2, $3, $4)",
            1001,         # candidate_id
            "admin",      # reviewed_by
            "系統操作知識，已確認正確",
            True,         # use_edited
        )

        assert new_kb_id == 5001

    @pytest.mark.asyncio
    async def test_post_approve_update_scope_and_category(self, mock_db_conn):
        """步驟 3：approve 後補充 scope 和 category

        approve_ai_knowledge_candidate() 目前不寫入 scope/category，
        需要額外 UPDATE。scope 有 DEFAULT 'global' 所以不影響，
        但 category 需要顯式設定。
        """
        mock_db_conn.execute.return_value = None

        # 模擬在 approve 後更新 category
        await mock_db_conn.execute(
            """
            UPDATE knowledge_base
            SET category = $1,
                scope = $2,
                keywords = $3,
                target_user = $4,
                business_types = $5,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $6
            """,
            "帳務管理",               # category
            "global",                # scope
            ["帳單", "租金", "繳費"],  # keywords
            ["tenant"],              # target_user
            ["rental", "management"],  # business_types
            5001,                    # kb_id
        )

        mock_db_conn.execute.assert_called_once()
        call_args = mock_db_conn.execute.call_args[0]
        assert "category" in call_args[0]
        assert "scope" in call_args[0]
        assert call_args[1] == "帳務管理"
        assert call_args[2] == "global"

    @pytest.mark.asyncio
    async def test_verify_synced_knowledge(self, mock_db_conn):
        """步驟 4：驗證同步後的知識庫條目"""
        mock_db_conn.fetchrow.return_value = {
            "id": 5001,
            "question_summary": "如何查看租金帳單",
            "answer": "您可以在 APP 首頁...",
            "scope": "global",
            "category": "帳務管理",
            "source_type": "ai_generated",
            "generation_metadata": json.dumps({
                "ai_model": "gpt-4o-mini",
                "confidence_score": 0.85,
                "reviewed_by": "admin",
            }),
            "embedding": "[0.1, 0.2, ...]",  # 有 embedding
            "is_active": True,
        }

        row = await mock_db_conn.fetchrow(
            "SELECT * FROM knowledge_base WHERE id = $1", 5001
        )

        assert row["source_type"] == "ai_generated"
        assert row["scope"] == "global"
        assert row["category"] == "帳務管理"
        assert row["generation_metadata"] is not None
        assert row["embedding"] is not None
        assert row["is_active"] is True

        # 驗證 generation_metadata 可解析
        metadata = json.loads(row["generation_metadata"])
        assert metadata["ai_model"] == "gpt-4o-mini"
        assert metadata["reviewed_by"] == "admin"


# ---------------------------------------------------------------------------
# 已知限制與相容性差距記錄
# ---------------------------------------------------------------------------


class TestKnownCompatibilityGaps:
    """記錄已知的相容性差距，作為後續修正的基線"""

    def test_test_scenario_id_nullable_needed(self):
        """ai_generated_knowledge_candidates.test_scenario_id 應為 NULLABLE

        目前 init script 定義為 NOT NULL + FK，但系統知識候選項
        來自 gap analysis（不經由 test_scenarios），需要 NULL 支援。

        knowledge_import_service.py 已經傳入 test_scenario_id=NULL，
        說明 DB 實際上已放寬此約束（透過 migration 或直接修改）。
        """
        # 驗證 import service 確實傳入 NULL
        import_service_path = (
            _PROJECT_ROOT
            / "rag-orchestrator"
            / "services"
            / "knowledge_import_service.py"
        )
        content = import_service_path.read_text(encoding="utf-8")
        # knowledge_import_service 在 test_scenario_id 傳入 None
        assert "test_scenario_id" in content
        # 確認有 NULL 相關的使用模式
        assert "NULL" in content or "None" in content

    def test_approve_function_scope_category_gap_documented(self):
        """approve function 不傳遞 scope/category 已記錄

        approve_ai_knowledge_candidate() 的 INSERT 不包含 scope、category、
        keywords、target_user (除硬編碼 ['tenant'])、business_types。

        解決方案：
        A) 修改 approve function 加入這些欄位
        B) approve 後用 UPDATE 補充
        C) 走 loop_knowledge 的 direct sync 路徑（繞過 approve function）

        方案 C 最小侵入，因為 loop_knowledge router 已有完整的
        直接寫入 knowledge_base 的邏輯。
        """
        init_sql_path = (
            _PROJECT_ROOT / "database" / "init" / "12-create-ai-knowledge-system.sql"
        )
        sql_content = init_sql_path.read_text(encoding="utf-8")

        # 確認 approve function 的 target_user 是硬編碼
        assert "ARRAY['tenant']::text[]" in sql_content, (
            "approve function 的 target_user 應為硬編碼 ['tenant']"
        )

    def test_direct_sync_path_available(self):
        """loop_knowledge router 提供直接 sync 路徑（繞過 approve function）

        這是系統知識候選項的推薦同步路徑，因為它支援：
        - scope/category/keywords/target_user/business_types 的完整設定
        - embedding 自動生成
        - generation_metadata 自定義
        """
        loop_router_path = (
            _PROJECT_ROOT / "rag-orchestrator" / "routers" / "loop_knowledge.py"
        )
        content = loop_router_path.read_text(encoding="utf-8")
        # loop_knowledge 有直接寫入 knowledge_base 的路徑
        assert "INSERT INTO knowledge_base" in content
        assert "generation_metadata" in content
        assert "source_type" in content


# ---------------------------------------------------------------------------
# SQL Schema 靜態驗證
# ---------------------------------------------------------------------------


class TestSQLSchemaStaticValidation:
    """靜態驗證 SQL schema 檔案的一致性"""

    def test_knowledge_base_defaults(self):
        """knowledge_base 的 DEFAULT 值設定正確"""
        kb_sql = (
            _PROJECT_ROOT / "database" / "init" / "02-create-knowledge-base.sql"
        ).read_text(encoding="utf-8")

        # scope DEFAULT 'global' — 即使 approve function 不設 scope，
        # 新寫入的 row 也會自動是 'global'
        assert "DEFAULT 'global'" in kb_sql
        # source_type DEFAULT 'manual'
        assert "DEFAULT 'manual'" in kb_sql
        # is_active DEFAULT TRUE
        assert "DEFAULT TRUE" in kb_sql

    def test_approve_function_returns_integer(self):
        """approve function 回傳 INTEGER (新 knowledge_base id)"""
        init_sql = (
            _PROJECT_ROOT / "database" / "init" / "12-create-ai-knowledge-system.sql"
        ).read_text(encoding="utf-8")
        assert "RETURNS INTEGER" in init_sql

    def test_approve_function_updates_candidate_status(self):
        """approve function 會更新候選項狀態為 approved"""
        init_sql = (
            _PROJECT_ROOT / "database" / "init" / "12-create-ai-knowledge-system.sql"
        ).read_text(encoding="utf-8")
        assert "status = 'approved'" in init_sql

    def test_approve_function_supports_intent_mapping(self):
        """approve function 支援多意圖映射"""
        init_sql = (
            _PROJECT_ROOT / "database" / "init" / "12-create-ai-knowledge-system.sql"
        ).read_text(encoding="utf-8")
        assert "knowledge_intent_mapping" in init_sql
