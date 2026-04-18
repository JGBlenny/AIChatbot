"""
ApiKBBuilder 單元測試

測試覆蓋：
- 動態缺口過濾（只處理 query_type=dynamic）
- 端點映射（topic_id 前綴 + question 關鍵字 → JGB API endpoint）
- KB 條目建構（action_type=api_call, api_config 結構正確）
- api_endpoints 條目建構
- 批量建構流程
- JSON 匯出
- 靜態問題排除
- 未知模組降級
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# 確保 project root 在 sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.kb_system_coverage.models import GapItem
from scripts.kb_system_coverage.api_kb_builder import ApiKBBuilder


# ---------------------------------------------------------------------------
# Fixtures — topic_id 前綴對照 MODULE_ABBR（question_generator.py）
#   帳務 → billing, 發票 → invoice, 合約 → contract
#   支付 → payment, 修繕 → repair, 租客 → lessee/tenant
# ---------------------------------------------------------------------------

def _make_gap(
    topic_id: str = "帳務_001",
    question: str = "我的帳單為什麼沒有發票？",
    gap_type: str = "uncovered",
    recommendation: str = "add_kb",
    query_type: str = "dynamic",
    priority: str = "p0",
) -> GapItem:
    return GapItem(
        topic_id=topic_id,
        question=question,
        gap_type=gap_type,
        recommendation=recommendation,
        query_type=query_type,
        priority=priority,
        similar_existing=[],
    )


def _billing_gap() -> GapItem:
    return _make_gap(
        topic_id="帳務_001",
        question="我的帳單為什麼沒有發票？",
    )


def _invoice_gap() -> GapItem:
    return _make_gap(
        topic_id="發票_010",
        question="我的發票開了嗎？狀態是什麼？",
    )


def _contract_gap() -> GapItem:
    return _make_gap(
        topic_id="合約_005",
        question="我的合約目前是什麼狀態？",
    )


def _checkin_gap() -> GapItem:
    return _make_gap(
        topic_id="合約_010",
        question="我的合約可以點交了嗎？",
    )


def _payment_gap() -> GapItem:
    return _make_gap(
        topic_id="支付_003",
        question="我上個月的繳費紀錄在哪裡查？",
    )


def _repair_gap() -> GapItem:
    return _make_gap(
        topic_id="修繕_002",
        question="我報修的進度到哪了？",
    )


def _tenant_summary_gap() -> GapItem:
    return _make_gap(
        topic_id="租客_001",
        question="我目前有幾個合約、待繳帳單有幾張？",
    )


def _static_gap() -> GapItem:
    return _make_gap(
        topic_id="帳務_099",
        question="怎麼在 APP 查看帳單？",
        query_type="static",
    )


# ---------------------------------------------------------------------------
# Tests: _filter_dynamic_gaps
# ---------------------------------------------------------------------------

class TestFilterDynamicGaps:
    def test_filters_only_dynamic(self):
        builder = ApiKBBuilder()
        gaps = [_billing_gap(), _static_gap(), _contract_gap()]
        result = builder._filter_dynamic_gaps(gaps)
        assert len(result) == 2
        assert all(g.query_type == "dynamic" for g in result)

    def test_empty_list(self):
        builder = ApiKBBuilder()
        result = builder._filter_dynamic_gaps([])
        assert result == []

    def test_all_static_returns_empty(self):
        builder = ApiKBBuilder()
        result = builder._filter_dynamic_gaps([_static_gap()])
        assert result == []


# ---------------------------------------------------------------------------
# Tests: _map_to_endpoint
# ---------------------------------------------------------------------------

class TestMapToEndpoint:
    def test_billing_topic_maps_to_jgb_bills(self):
        builder = ApiKBBuilder()
        gap = _billing_gap()
        endpoint = builder._map_to_endpoint(gap)
        assert endpoint == "jgb_bills"

    def test_invoice_topic_maps_to_jgb_invoices(self):
        builder = ApiKBBuilder()
        gap = _invoice_gap()
        endpoint = builder._map_to_endpoint(gap)
        assert endpoint == "jgb_invoices"

    def test_contract_topic_maps_to_jgb_contracts(self):
        builder = ApiKBBuilder()
        gap = _contract_gap()
        endpoint = builder._map_to_endpoint(gap)
        assert endpoint == "jgb_contracts"

    def test_checkin_keyword_maps_to_jgb_contract_checkin(self):
        builder = ApiKBBuilder()
        gap = _checkin_gap()
        endpoint = builder._map_to_endpoint(gap)
        assert endpoint == "jgb_contract_checkin"

    def test_payment_topic_maps_to_jgb_payments(self):
        builder = ApiKBBuilder()
        gap = _payment_gap()
        endpoint = builder._map_to_endpoint(gap)
        assert endpoint == "jgb_payments"

    def test_repair_topic_maps_to_jgb_repairs(self):
        builder = ApiKBBuilder()
        gap = _repair_gap()
        endpoint = builder._map_to_endpoint(gap)
        assert endpoint == "jgb_repairs"

    def test_tenant_topic_maps_to_jgb_tenant_summary(self):
        builder = ApiKBBuilder()
        gap = _tenant_summary_gap()
        endpoint = builder._map_to_endpoint(gap)
        assert endpoint == "jgb_tenant_summary"

    def test_unknown_topic_returns_none(self):
        builder = ApiKBBuilder()
        gap = _make_gap(topic_id="未知_001", question="不知道的問題")
        endpoint = builder._map_to_endpoint(gap)
        assert endpoint is None


# ---------------------------------------------------------------------------
# Tests: _build_kb_entry
# ---------------------------------------------------------------------------

class TestBuildKBEntry:
    def test_has_action_type_api_call(self):
        builder = ApiKBBuilder()
        entry = builder._build_kb_entry(_billing_gap(), "jgb_bills")
        assert entry["action_type"] == "api_call"

    def test_has_api_config_with_endpoint(self):
        builder = ApiKBBuilder()
        entry = builder._build_kb_entry(_billing_gap(), "jgb_bills")
        assert entry["api_config"]["endpoint"] == "jgb_bills"

    def test_api_config_has_session_params(self):
        builder = ApiKBBuilder()
        entry = builder._build_kb_entry(_billing_gap(), "jgb_bills")
        params = entry["api_config"]["params"]
        assert params["role_id"] == "{session.role_id}"
        assert params["user_id"] == "{session.user_id}"

    def test_api_config_has_response_template(self):
        builder = ApiKBBuilder()
        entry = builder._build_kb_entry(_billing_gap(), "jgb_bills")
        assert len(entry["api_config"]["response_template"]) > 0

    def test_api_config_has_fallback_message(self):
        builder = ApiKBBuilder()
        entry = builder._build_kb_entry(_billing_gap(), "jgb_bills")
        assert len(entry["api_config"]["fallback_message"]) > 0

    def test_api_config_has_combine_with_knowledge(self):
        builder = ApiKBBuilder()
        entry = builder._build_kb_entry(_billing_gap(), "jgb_bills")
        assert entry["api_config"]["combine_with_knowledge"] is True

    def test_has_question_summary(self):
        builder = ApiKBBuilder()
        gap = _billing_gap()
        entry = builder._build_kb_entry(gap, "jgb_bills")
        assert entry["question_summary"] == gap.question

    def test_has_scope_global(self):
        builder = ApiKBBuilder()
        entry = builder._build_kb_entry(_billing_gap(), "jgb_bills")
        assert entry["scope"] == "global"

    def test_has_topic_id(self):
        builder = ApiKBBuilder()
        gap = _billing_gap()
        entry = builder._build_kb_entry(gap, "jgb_bills")
        assert entry["topic_id"] == gap.topic_id

    def test_response_template_in_traditional_chinese(self):
        builder = ApiKBBuilder()
        entry = builder._build_kb_entry(_billing_gap(), "jgb_bills")
        template = entry["api_config"]["response_template"]
        assert any("\u4e00" <= ch <= "\u9fff" for ch in template)

    def test_fallback_message_in_traditional_chinese(self):
        builder = ApiKBBuilder()
        entry = builder._build_kb_entry(_billing_gap(), "jgb_bills")
        fallback = entry["api_config"]["fallback_message"]
        assert any("\u4e00" <= ch <= "\u9fff" for ch in fallback)


# ---------------------------------------------------------------------------
# Tests: _build_api_endpoint_entry
# ---------------------------------------------------------------------------

class TestBuildApiEndpointEntry:
    def test_has_endpoint_name(self):
        builder = ApiKBBuilder()
        entry = builder._build_api_endpoint_entry("jgb_bills")
        assert entry["endpoint_name"] == "jgb_bills"

    def test_has_url_path(self):
        builder = ApiKBBuilder()
        entry = builder._build_api_endpoint_entry("jgb_bills")
        assert "/api/external/v1/" in entry["url_path"]

    def test_has_method_get(self):
        builder = ApiKBBuilder()
        entry = builder._build_api_endpoint_entry("jgb_bills")
        assert entry["method"] == "GET"

    def test_has_required_params(self):
        builder = ApiKBBuilder()
        entry = builder._build_api_endpoint_entry("jgb_bills")
        assert "role_id" in entry["required_params"]
        assert "user_id" in entry["required_params"]

    def test_all_endpoints_have_entries(self):
        builder = ApiKBBuilder()
        for key in builder.endpoint_configs:
            entry = builder._build_api_endpoint_entry(key)
            assert entry["endpoint_name"] == key
            assert "url_path" in entry

    def test_contract_checkin_url_path(self):
        builder = ApiKBBuilder()
        entry = builder._build_api_endpoint_entry("jgb_contract_checkin")
        assert "checkin" in entry["url_path"] or "check" in entry["url_path"]

    def test_tenant_summary_url_path(self):
        builder = ApiKBBuilder()
        entry = builder._build_api_endpoint_entry("jgb_tenant_summary")
        assert "tenant" in entry["url_path"] or "summary" in entry["url_path"]


# ---------------------------------------------------------------------------
# Tests: build (integration)
# ---------------------------------------------------------------------------

class TestBuild:
    def test_returns_tuple_of_two_lists(self):
        builder = ApiKBBuilder()
        kb_entries, api_entries = builder.build([_billing_gap(), _contract_gap()])
        assert isinstance(kb_entries, list)
        assert isinstance(api_entries, list)

    def test_kb_entries_count_matches_dynamic_gaps(self):
        builder = ApiKBBuilder()
        gaps = [_billing_gap(), _contract_gap(), _static_gap()]
        kb_entries, _ = builder.build(gaps)
        assert len(kb_entries) == 2

    def test_api_entries_are_deduplicated(self):
        builder = ApiKBBuilder()
        gap1 = _billing_gap()
        gap2 = _make_gap(
            topic_id="帳務_002",
            question="我的帳單金額怎麼算的？",
        )
        kb_entries, api_entries = builder.build([gap1, gap2])
        assert len(kb_entries) == 2
        endpoint_names = [e["endpoint_name"] for e in api_entries]
        assert len(endpoint_names) == len(set(endpoint_names))

    def test_skips_unmappable_gaps(self):
        builder = ApiKBBuilder()
        unknown = _make_gap(topic_id="未知_001", question="不知道的問題")
        kb_entries, api_entries = builder.build([unknown])
        assert len(kb_entries) == 0
        assert len(api_entries) == 0

    def test_all_kb_entries_have_action_type_api_call(self):
        builder = ApiKBBuilder()
        gaps = [_billing_gap(), _contract_gap(), _payment_gap(), _repair_gap()]
        kb_entries, _ = builder.build(gaps)
        for entry in kb_entries:
            assert entry["action_type"] == "api_call"

    def test_mixed_gaps_produce_correct_counts(self):
        builder = ApiKBBuilder()
        gaps = [
            _billing_gap(),
            _invoice_gap(),
            _contract_gap(),
            _checkin_gap(),
            _payment_gap(),
            _repair_gap(),
            _tenant_summary_gap(),
            _static_gap(),
        ]
        kb_entries, api_entries = builder.build(gaps)
        assert len(kb_entries) == 7  # 7 dynamic, 1 static filtered
        assert len(api_entries) == 7  # 7 unique endpoints


# ---------------------------------------------------------------------------
# Tests: export
# ---------------------------------------------------------------------------

class TestExport:
    def test_export_creates_json(self, tmp_path):
        builder = ApiKBBuilder()
        kb_entries, api_entries = builder.build([_billing_gap()])
        output_path = tmp_path / "api_kb_output.json"
        builder.export(kb_entries, api_entries, output_path)
        assert output_path.exists()

        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert "kb_entries" in data
        assert "api_endpoint_entries" in data
        assert len(data["kb_entries"]) == 1

    def test_export_is_valid_json_utf8(self, tmp_path):
        builder = ApiKBBuilder()
        kb_entries, api_entries = builder.build([_billing_gap(), _contract_gap()])
        output_path = tmp_path / "api_kb_output.json"
        builder.export(kb_entries, api_entries, output_path)

        text = output_path.read_text(encoding="utf-8")
        json.loads(text)  # should not raise
        assert any("\u4e00" <= ch <= "\u9fff" for ch in text)


# ---------------------------------------------------------------------------
# Tests: endpoint_configs completeness
# ---------------------------------------------------------------------------

class TestEndpointConfigs:
    def test_all_seven_endpoints_exist(self):
        builder = ApiKBBuilder()
        expected = {
            "jgb_bills", "jgb_invoices", "jgb_contracts",
            "jgb_contract_checkin", "jgb_payments", "jgb_repairs",
            "jgb_tenant_summary",
        }
        assert set(builder.endpoint_configs.keys()) == expected

    def test_each_config_has_response_template(self):
        builder = ApiKBBuilder()
        for key, config in builder.endpoint_configs.items():
            assert "response_template" in config, f"{key} missing response_template"
            assert len(config["response_template"]) > 0

    def test_each_config_has_fallback_message(self):
        builder = ApiKBBuilder()
        for key, config in builder.endpoint_configs.items():
            assert "fallback_message" in config, f"{key} missing fallback_message"
            assert len(config["fallback_message"]) > 0

    def test_each_config_has_url_path(self):
        builder = ApiKBBuilder()
        for key, config in builder.endpoint_configs.items():
            assert "url_path" in config, f"{key} missing url_path"

    def test_each_config_has_params(self):
        builder = ApiKBBuilder()
        for key, config in builder.endpoint_configs.items():
            assert "params" in config, f"{key} missing params"
            assert "role_id" in config["params"]
            assert "user_id" in config["params"]
