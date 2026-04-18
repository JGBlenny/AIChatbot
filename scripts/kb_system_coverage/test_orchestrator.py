"""
test_orchestrator.py — Orchestrator 多階段 pipeline 編排腳本測試

測試涵蓋：
- CLI 參數解析（--vendor-id, --skip-phases, --batch-size）
- 各階段的 skip 邏輯
- Phase 順序與資料傳遞
- P4/P5 平行執行
- P6 暫停邏輯（等待人工審核後才進入 P7）
- 錯誤處理與中斷安全
"""

from __future__ import annotations

import asyncio
import json
import sys
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 確保 project root 在 sys.path
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.kb_system_coverage.models import (
    CoverageReport,
    Feature,
    GapItem,
    Module,
    ModuleCoverage,
    RoleCoverage,
    SimilarItem,
    SystemQuestion,
)


# ===========================================================================
# Fixtures — 共用測試資料
# ===========================================================================

@pytest.fixture
def sample_modules():
    """範例模組清單"""
    return [
        Module(
            module_id="billing",
            module_name="帳務管理",
            description="帳單與繳費管理",
            features=[
                Feature(
                    feature_id="billing_001",
                    feature_name="租金帳單查詢",
                    roles=["tenant"],
                    entry_point="app",
                ),
            ],
        ),
    ]


@pytest.fixture
def sample_questions():
    """範例問題清單"""
    return [
        SystemQuestion(
            topic_id="帳務_001",
            module_id="billing",
            question="怎麼在 APP 查看帳單明細",
            roles=["tenant"],
            entry_point="app",
            priority="p0",
            query_type="static",
            question_category="basic_operation",
            keywords=["帳單", "明細", "APP"],
        ),
        SystemQuestion(
            topic_id="帳務_002",
            module_id="billing",
            question="帳單為什麼沒產生發票",
            roles=["tenant"],
            entry_point="app",
            priority="p0",
            query_type="dynamic",
            question_category="common_question",
            keywords=["帳單", "發票"],
        ),
    ]


@pytest.fixture
def sample_coverage_report():
    """範例覆蓋率報告"""
    return CoverageReport(
        total_questions=2,
        covered_by_kb=0,
        covered_by_sop=0,
        uncovered=2,
        partial_covered=0,
        needs_improvement=0,
        coverage_by_module={
            "billing": ModuleCoverage(
                module_id="billing",
                module_name="帳務管理",
                total=2,
                uncovered=2,
            ),
        },
        coverage_by_role={
            "tenant": RoleCoverage(role="tenant", total=2, uncovered=2),
        },
        gaps=[
            GapItem(
                topic_id="帳務_001",
                question="怎麼在 APP 查看帳單明細",
                gap_type="uncovered",
                recommendation="add_kb",
                query_type="static",
                priority="p0",
            ),
            GapItem(
                topic_id="帳務_002",
                question="帳單為什麼沒產生發票",
                gap_type="uncovered",
                recommendation="add_kb",
                query_type="dynamic",
                priority="p0",
            ),
        ],
    )


# ===========================================================================
# Test: CLI 參數解析
# ===========================================================================

class TestParseArgs:
    """CLI 參數解析測試"""

    def test_required_vendor_id(self):
        """--vendor-id 為必填參數"""
        from scripts.kb_system_coverage.orchestrator import parse_args
        with pytest.raises(SystemExit):
            parse_args([])

    def test_vendor_id_parsed(self):
        """--vendor-id 正確解析"""
        from scripts.kb_system_coverage.orchestrator import parse_args
        args = parse_args(["--vendor-id", "1"])
        assert args.vendor_id == 1

    def test_skip_phases_parsed(self):
        """--skip-phases 正確解析為逗號分隔"""
        from scripts.kb_system_coverage.orchestrator import parse_args
        args = parse_args(["--vendor-id", "1", "--skip-phases", "mapping,questions"])
        assert args.skip_phases == "mapping,questions"

    def test_batch_size_default(self):
        """--batch-size 預設為 5"""
        from scripts.kb_system_coverage.orchestrator import parse_args
        args = parse_args(["--vendor-id", "1"])
        assert args.batch_size == 5

    def test_batch_size_custom(self):
        """--batch-size 可自訂"""
        from scripts.kb_system_coverage.orchestrator import parse_args
        args = parse_args(["--vendor-id", "1", "--batch-size", "10"])
        assert args.batch_size == 10


# ===========================================================================
# Test: ALL_PHASES 常數
# ===========================================================================

class TestAllPhases:
    """ALL_PHASES 常數驗證"""

    def test_all_phases_has_7_phases(self):
        """Pipeline 應有 7 個階段"""
        from scripts.kb_system_coverage.orchestrator import ALL_PHASES
        assert len(ALL_PHASES) == 7

    def test_phase_names(self):
        """階段名稱正確"""
        from scripts.kb_system_coverage.orchestrator import ALL_PHASES
        expected = [
            "mapping", "questions", "coverage",
            "generate_kb", "build_api_kb", "pause", "backtest",
        ]
        assert ALL_PHASES == expected


# ===========================================================================
# Test: Phase skip 邏輯
# ===========================================================================

class TestPhaseSkip:
    """各階段的 skip 邏輯"""

    @pytest.mark.asyncio
    async def test_skip_mapping_phase(self, sample_modules):
        """跳過 Phase 1 時不呼叫 build_module_inventory"""
        with patch(
            "scripts.kb_system_coverage.orchestrator.build_module_inventory"
        ) as mock_mapper, patch(
            "scripts.kb_system_coverage.orchestrator.load_inventory"
        ) as mock_load:
            mock_load.return_value = sample_modules

            from scripts.kb_system_coverage.orchestrator import run_pipeline
            result = await run_pipeline(
                vendor_id=1,
                skip_phases=["mapping", "questions", "coverage", "generate_kb",
                             "build_api_kb", "pause", "backtest"],
            )
            mock_mapper.assert_not_called()

    @pytest.mark.asyncio
    async def test_skip_all_returns_completed(self):
        """跳過所有階段仍應正常返回 completed"""
        from scripts.kb_system_coverage.orchestrator import run_pipeline
        result = await run_pipeline(
            vendor_id=1,
            skip_phases=["mapping", "questions", "coverage", "generate_kb",
                         "build_api_kb", "pause", "backtest"],
        )
        assert result["status"] == "completed"


# ===========================================================================
# Test: Phase 1 — Module Mapping
# ===========================================================================

class TestPhase1:
    """Phase 1: Module Mapping"""

    @pytest.mark.asyncio
    async def test_phase1_calls_build_module_inventory(self, sample_modules):
        """P1 呼叫 build_module_inventory 並保存結果"""
        with patch(
            "scripts.kb_system_coverage.orchestrator.build_module_inventory",
            return_value=sample_modules,
        ) as mock_mapper:
            from scripts.kb_system_coverage.orchestrator import run_pipeline
            result = await run_pipeline(
                vendor_id=1,
                skip_phases=["questions", "coverage", "generate_kb",
                             "build_api_kb", "pause", "backtest"],
            )
            mock_mapper.assert_called_once()
            assert result["module_count"] == 1


# ===========================================================================
# Test: Phase 2 — Question Generation
# ===========================================================================

class TestPhase2:
    """Phase 2: Question Generation"""

    @pytest.mark.asyncio
    async def test_phase2_calls_generate_questions(
        self, sample_modules, sample_questions
    ):
        """P2 呼叫 generate_questions 並保存結果"""
        with patch(
            "scripts.kb_system_coverage.orchestrator.build_module_inventory",
            return_value=sample_modules,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.generate_questions",
            new_callable=AsyncMock,
            return_value=sample_questions,
        ) as mock_gen, patch(
            "scripts.kb_system_coverage.orchestrator.save_output",
        ):
            from scripts.kb_system_coverage.orchestrator import run_pipeline
            result = await run_pipeline(
                vendor_id=1,
                skip_phases=["coverage", "generate_kb",
                             "build_api_kb", "pause", "backtest"],
            )
            mock_gen.assert_called_once()
            assert result["question_count"] == 2


# ===========================================================================
# Test: Phase 3 — Coverage Analysis
# ===========================================================================

class TestPhase3:
    """Phase 3: Coverage Analysis"""

    @pytest.mark.asyncio
    async def test_phase3_calls_analyzer(
        self, sample_modules, sample_questions, sample_coverage_report
    ):
        """P3 呼叫 CoverageAnalyzer.analyze 並保存結果"""
        mock_analyzer_instance = MagicMock()
        mock_analyzer_instance.analyze = AsyncMock(
            return_value=sample_coverage_report
        )
        mock_analyzer_instance.export_report = MagicMock()

        with patch(
            "scripts.kb_system_coverage.orchestrator.build_module_inventory",
            return_value=sample_modules,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.generate_questions",
            new_callable=AsyncMock,
            return_value=sample_questions,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.save_output",
        ), patch(
            "scripts.kb_system_coverage.orchestrator.CoverageAnalyzer",
            return_value=mock_analyzer_instance,
        ), patch(
            "scripts.kb_system_coverage.orchestrator._fetch_kb_items",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "scripts.kb_system_coverage.orchestrator._fetch_sop_items",
            new_callable=AsyncMock,
            return_value=[],
        ):
            from scripts.kb_system_coverage.orchestrator import run_pipeline
            result = await run_pipeline(
                vendor_id=1,
                skip_phases=["generate_kb", "build_api_kb", "pause", "backtest"],
            )
            mock_analyzer_instance.analyze.assert_called_once()
            assert result["total_questions"] == 2
            assert result["uncovered"] == 2


# ===========================================================================
# Test: Phase 4+5 — 平行執行
# ===========================================================================

class TestPhase4And5:
    """Phase 4 & 5 平行執行（靜態 KB 生成 + 動態 KB 建立）"""

    @pytest.mark.asyncio
    async def test_phase4_calls_system_kb_generator(
        self, sample_modules, sample_questions, sample_coverage_report
    ):
        """P4 呼叫 SystemKBGenerator.generate_batch"""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze = AsyncMock(return_value=sample_coverage_report)
        mock_analyzer.export_report = MagicMock()

        mock_generator = MagicMock()
        mock_generator.generate_batch = AsyncMock(return_value=[{"topic_id": "帳務_001"}])
        mock_generator.export_candidates = MagicMock()

        mock_api_builder = MagicMock()
        mock_api_builder.build = MagicMock(return_value=([], []))
        mock_api_builder.export = MagicMock()

        with patch(
            "scripts.kb_system_coverage.orchestrator.build_module_inventory",
            return_value=sample_modules,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.generate_questions",
            new_callable=AsyncMock,
            return_value=sample_questions,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.save_output",
        ), patch(
            "scripts.kb_system_coverage.orchestrator.CoverageAnalyzer",
            return_value=mock_analyzer,
        ), patch(
            "scripts.kb_system_coverage.orchestrator._fetch_kb_items",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "scripts.kb_system_coverage.orchestrator._fetch_sop_items",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "scripts.kb_system_coverage.orchestrator.SystemKBGenerator",
            return_value=mock_generator,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.ApiKBBuilder",
            return_value=mock_api_builder,
        ):
            from scripts.kb_system_coverage.orchestrator import run_pipeline
            result = await run_pipeline(
                vendor_id=1,
                skip_phases=["pause", "backtest"],
            )
            mock_generator.generate_batch.assert_called_once()
            mock_api_builder.build.assert_called_once()
            assert result["static_kb_count"] == 1

    @pytest.mark.asyncio
    async def test_phase5_calls_api_kb_builder(
        self, sample_modules, sample_questions, sample_coverage_report
    ):
        """P5 呼叫 ApiKBBuilder.build"""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze = AsyncMock(return_value=sample_coverage_report)
        mock_analyzer.export_report = MagicMock()

        mock_generator = MagicMock()
        mock_generator.generate_batch = AsyncMock(return_value=[])
        mock_generator.export_candidates = MagicMock()

        mock_api_builder = MagicMock()
        mock_api_builder.build = MagicMock(
            return_value=(
                [{"endpoint": "jgb_bills"}],
                [{"endpoint_name": "jgb_bills"}],
            )
        )
        mock_api_builder.export = MagicMock()

        with patch(
            "scripts.kb_system_coverage.orchestrator.build_module_inventory",
            return_value=sample_modules,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.generate_questions",
            new_callable=AsyncMock,
            return_value=sample_questions,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.save_output",
        ), patch(
            "scripts.kb_system_coverage.orchestrator.CoverageAnalyzer",
            return_value=mock_analyzer,
        ), patch(
            "scripts.kb_system_coverage.orchestrator._fetch_kb_items",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "scripts.kb_system_coverage.orchestrator._fetch_sop_items",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "scripts.kb_system_coverage.orchestrator.SystemKBGenerator",
            return_value=mock_generator,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.ApiKBBuilder",
            return_value=mock_api_builder,
        ):
            from scripts.kb_system_coverage.orchestrator import run_pipeline
            result = await run_pipeline(
                vendor_id=1,
                skip_phases=["pause", "backtest"],
            )
            mock_api_builder.build.assert_called_once()
            assert result["api_kb_count"] == 1


# ===========================================================================
# Test: Phase 6 — Review Pause
# ===========================================================================

class TestPhase6:
    """Phase 6: 暫停等待人工審核"""

    @pytest.mark.asyncio
    async def test_phase6_pauses_pipeline(self):
        """P6 不被跳過時，pipeline 應暫停並回傳 waiting_for_review"""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze = AsyncMock(
            return_value=CoverageReport(total_questions=0, gaps=[])
        )
        mock_analyzer.export_report = MagicMock()

        mock_generator = MagicMock()
        mock_generator.generate_batch = AsyncMock(return_value=[])
        mock_generator.export_candidates = MagicMock()

        mock_api_builder = MagicMock()
        mock_api_builder.build = MagicMock(return_value=([], []))
        mock_api_builder.export = MagicMock()

        with patch(
            "scripts.kb_system_coverage.orchestrator.build_module_inventory",
            return_value=[],
        ), patch(
            "scripts.kb_system_coverage.orchestrator.generate_questions",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "scripts.kb_system_coverage.orchestrator.save_output",
        ), patch(
            "scripts.kb_system_coverage.orchestrator.CoverageAnalyzer",
            return_value=mock_analyzer,
        ), patch(
            "scripts.kb_system_coverage.orchestrator._fetch_kb_items",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "scripts.kb_system_coverage.orchestrator._fetch_sop_items",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "scripts.kb_system_coverage.orchestrator.SystemKBGenerator",
            return_value=mock_generator,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.ApiKBBuilder",
            return_value=mock_api_builder,
        ):
            from scripts.kb_system_coverage.orchestrator import run_pipeline
            result = await run_pipeline(vendor_id=1, skip_phases=[])
            assert result["status"] == "waiting_for_review"

    @pytest.mark.asyncio
    async def test_skip_pause_continues_to_backtest(self):
        """跳過 P6 時應繼續到 P7（backtest 也跳過時直接完成）"""
        from scripts.kb_system_coverage.orchestrator import run_pipeline
        result = await run_pipeline(
            vendor_id=1,
            skip_phases=["mapping", "questions", "coverage", "generate_kb",
                         "build_api_kb", "pause", "backtest"],
        )
        assert result["status"] == "completed"


# ===========================================================================
# Test: Phase 7 — Backtest (stub，只驗證 skip 邏輯)
# ===========================================================================

class TestPhase7:
    """Phase 7: Backtest Validation"""

    @pytest.mark.asyncio
    async def test_skip_backtest(self):
        """跳過 backtest 時不執行回測"""
        from scripts.kb_system_coverage.orchestrator import run_pipeline
        result = await run_pipeline(
            vendor_id=1,
            skip_phases=["mapping", "questions", "coverage", "generate_kb",
                         "build_api_kb", "pause", "backtest"],
        )
        assert "backtest" not in result


# ===========================================================================
# Test: 完整 pipeline 資料流
# ===========================================================================

class TestPipelineDataFlow:
    """完整 pipeline 的資料傳遞鏈"""

    @pytest.mark.asyncio
    async def test_modules_flow_to_questions(self, sample_modules, sample_questions):
        """P1 的 modules 輸出作為 P2 的輸入"""
        with patch(
            "scripts.kb_system_coverage.orchestrator.build_module_inventory",
            return_value=sample_modules,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.generate_questions",
            new_callable=AsyncMock,
            return_value=sample_questions,
        ) as mock_gen, patch(
            "scripts.kb_system_coverage.orchestrator.save_output",
        ):
            from scripts.kb_system_coverage.orchestrator import run_pipeline
            await run_pipeline(
                vendor_id=1,
                skip_phases=["coverage", "generate_kb",
                             "build_api_kb", "pause", "backtest"],
            )
            # generate_questions 應收到 P1 的 modules
            call_args = mock_gen.call_args
            assert call_args[0][0] == sample_modules or call_args[1].get("modules") == sample_modules

    @pytest.mark.asyncio
    async def test_gaps_flow_to_generators(
        self, sample_modules, sample_questions, sample_coverage_report
    ):
        """P3 的 gaps 輸出作為 P4/P5 的輸入"""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze = AsyncMock(return_value=sample_coverage_report)
        mock_analyzer.export_report = MagicMock()

        mock_generator = MagicMock()
        mock_generator.generate_batch = AsyncMock(return_value=[])
        mock_generator.export_candidates = MagicMock()

        mock_api_builder = MagicMock()
        mock_api_builder.build = MagicMock(return_value=([], []))
        mock_api_builder.export = MagicMock()

        with patch(
            "scripts.kb_system_coverage.orchestrator.build_module_inventory",
            return_value=sample_modules,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.generate_questions",
            new_callable=AsyncMock,
            return_value=sample_questions,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.save_output",
        ), patch(
            "scripts.kb_system_coverage.orchestrator.CoverageAnalyzer",
            return_value=mock_analyzer,
        ), patch(
            "scripts.kb_system_coverage.orchestrator._fetch_kb_items",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "scripts.kb_system_coverage.orchestrator._fetch_sop_items",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "scripts.kb_system_coverage.orchestrator.SystemKBGenerator",
            return_value=mock_generator,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.ApiKBBuilder",
            return_value=mock_api_builder,
        ):
            from scripts.kb_system_coverage.orchestrator import run_pipeline
            await run_pipeline(
                vendor_id=1,
                skip_phases=["pause", "backtest"],
            )
            # P4: generate_batch 接收 gaps + module_inventory
            gen_call = mock_generator.generate_batch.call_args
            assert gen_call[1]["gaps"] == sample_coverage_report.gaps
            assert gen_call[1]["module_inventory"] == sample_modules

            # P5: build 接收 gaps
            build_call = mock_api_builder.build.call_args
            assert build_call[0][0] == sample_coverage_report.gaps


# ===========================================================================
# Test: batch_size 傳遞
# ===========================================================================

class TestBatchSize:
    """batch_size 參數傳遞"""

    @pytest.mark.asyncio
    async def test_batch_size_passed_to_generator(self, sample_modules, sample_questions, sample_coverage_report):
        """batch_size 應傳遞給 SystemKBGenerator"""
        mock_analyzer = MagicMock()
        mock_analyzer.analyze = AsyncMock(return_value=sample_coverage_report)
        mock_analyzer.export_report = MagicMock()

        captured_batch_size = {}

        def capture_init(*args, **kwargs):
            captured_batch_size["value"] = kwargs.get("batch_size", args[0] if args else None)
            mock = MagicMock()
            mock.generate_batch = AsyncMock(return_value=[])
            mock.export_candidates = MagicMock()
            return mock

        mock_api_builder = MagicMock()
        mock_api_builder.build = MagicMock(return_value=([], []))
        mock_api_builder.export = MagicMock()

        with patch(
            "scripts.kb_system_coverage.orchestrator.build_module_inventory",
            return_value=sample_modules,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.generate_questions",
            new_callable=AsyncMock,
            return_value=sample_questions,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.save_output",
        ), patch(
            "scripts.kb_system_coverage.orchestrator.CoverageAnalyzer",
            return_value=mock_analyzer,
        ), patch(
            "scripts.kb_system_coverage.orchestrator._fetch_kb_items",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "scripts.kb_system_coverage.orchestrator._fetch_sop_items",
            new_callable=AsyncMock,
            return_value=[],
        ), patch(
            "scripts.kb_system_coverage.orchestrator.SystemKBGenerator",
            side_effect=capture_init,
        ), patch(
            "scripts.kb_system_coverage.orchestrator.ApiKBBuilder",
            return_value=mock_api_builder,
        ):
            from scripts.kb_system_coverage.orchestrator import run_pipeline
            await run_pipeline(
                vendor_id=1,
                batch_size=10,
                skip_phases=["pause", "backtest"],
            )
            assert captured_batch_size["value"] == 10
