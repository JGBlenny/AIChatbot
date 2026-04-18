"""
ApiKBBuilder — 動態查詢 KB 條目建立

讀取 coverage_report.json 中 query_type=dynamic 的缺口，
參照 JGB API 規格建立 action_type='api_call' 的 KB 條目，
並同步產出 api_endpoints 表設定。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from scripts.kb_system_coverage.models import GapItem


# ---------------------------------------------------------------------------
# topic_id 中文前綴 → module 映射（對照 question_generator.py MODULE_ABBR）
# ---------------------------------------------------------------------------
_TOPIC_PREFIX_TO_MODULE: Dict[str, str] = {
    "帳務": "billing",
    "發票": "invoice",
    "合約": "contract",
    "支付": "payment",
    "修繕": "repair",
    "租客": "tenant",
    "物件": "estate",
    "設備": "iot",
    "社區": "community",
    "大房東": "big_landlord",
    "委託": "entrusted_contract",
    "差額發票": "balance_invoice",
    "簽章": "esign",
    "帳號": "user_account",
    "通知": "notification",
    "訂閱": "subscription",
    "虛帳": "recharge_account",
    "刊登": "listing",
    "簽核": "approval",
    "住都": "nthurc",
    "押息": "deposit_interest",
    "後台": "admin_tools",
    "LINE": "line_integration",
    "API": "external_api",
}

# 點交/入住相關關鍵字
_CHECKIN_KEYWORDS = ["點交", "入住", "checkin", "check-in", "move_in", "搬入"]


def _extract_module_from_topic(topic_id: str) -> Optional[str]:
    """從 topic_id（如 '帳務_001'）擷取模組 ID。"""
    prefix = topic_id.rsplit("_", 1)[0] if "_" in topic_id else topic_id
    return _TOPIC_PREFIX_TO_MODULE.get(prefix)


class ApiKBBuilder:
    """Build knowledge_base entries for dynamic query questions (action_type=api_call)."""

    def __init__(self) -> None:
        self.endpoint_configs: Dict[str, dict] = {
            "jgb_bills": {
                "url_path": "/api/external/v1/bills",
                "params": {
                    "role_id": "{session.role_id}",
                    "user_id": "{session.user_id}",
                    "month": "{form.month_select}",
                },
                "response_template": (
                    "您好！查詢到您 {month} 月的帳單資訊如下：\n\n"
                    "📋 帳單狀態：{status_text}\n"
                    "💰 金額：NT$ {amount}\n"
                    "📅 繳費期限：{due_date}\n"
                    "🧾 發票狀態：{invoice_status_text}\n\n"
                    "{diagnosis_message}"
                ),
                "fallback_message": "目前無法查詢帳單資訊，請稍後再試或聯繫您的管理師。",
            },
            "jgb_invoices": {
                "url_path": "/api/external/v1/invoices",
                "params": {
                    "role_id": "{session.role_id}",
                    "user_id": "{session.user_id}",
                    "bill_id": "{form.bill_id}",
                },
                "response_template": (
                    "您好！以下是您的發票資訊：\n\n"
                    "🧾 發票號碼：{invoice_number}\n"
                    "📋 發票狀態：{status_text}\n"
                    "📁 發票類別：{category}\n"
                    "💰 金額：NT$ {amount}\n"
                    "📝 課稅別：{tax_type}"
                ),
                "fallback_message": "目前無法查詢發票資訊，請稍後再試或聯繫您的管理師。",
            },
            "jgb_contracts": {
                "url_path": "/api/external/v1/contracts",
                "params": {
                    "role_id": "{session.role_id}",
                    "user_id": "{session.user_id}",
                },
                "response_template": (
                    "您好！以下是您的合約資訊：\n\n"
                    "📋 合約編號：{contract_id}\n"
                    "🏠 物件名稱：{estate_name}\n"
                    "📌 合約狀態：{status_text}\n"
                    "📅 合約期間：{start_date} ~ {end_date}\n"
                    "💰 月租金：NT$ {rent}"
                ),
                "fallback_message": "目前無法查詢合約資訊，請稍後再試或聯繫您的管理師。",
            },
            "jgb_contract_checkin": {
                "url_path": "/api/external/v1/contracts/{contract_id}/checkin-eligibility",
                "params": {
                    "role_id": "{session.role_id}",
                    "user_id": "{session.user_id}",
                    "contract_id": "{form.contract_id}",
                },
                "response_template": (
                    "您的合約點交資格查詢結果如下：\n\n"
                    "📋 合約編號：{contract_id}\n"
                    "✅ 是否可點交：{eligible_text}\n\n"
                    "{reasons_text}\n\n"
                    "{guidance_message}"
                ),
                "fallback_message": "目前無法查詢點交資格，請稍後再試或聯繫您的管理師。",
            },
            "jgb_payments": {
                "url_path": "/api/external/v1/payments",
                "params": {
                    "role_id": "{session.role_id}",
                    "user_id": "{session.user_id}",
                    "month": "{form.month_select}",
                },
                "response_template": (
                    "您好！以下是您的繳費紀錄：\n\n"
                    "💰 金額：NT$ {amount}\n"
                    "💳 付款方式：{method}\n"
                    "📋 付款狀態：{status_text}\n"
                    "📅 付款時間：{paid_at}"
                ),
                "fallback_message": "目前無法查詢繳費紀錄，請稍後再試或聯繫您的管理師。",
            },
            "jgb_repairs": {
                "url_path": "/api/external/v1/repairs",
                "params": {
                    "role_id": "{session.role_id}",
                    "user_id": "{session.user_id}",
                },
                "response_template": (
                    "您好！以下是您的修繕進度：\n\n"
                    "🔧 修繕單號：{repair_id}\n"
                    "📝 問題描述：{description}\n"
                    "📋 處理狀態：{status_text}\n"
                    "👷 負責廠商：{assigned_to}\n"
                    "📅 申請時間：{created_at}"
                ),
                "fallback_message": "目前無法查詢修繕進度，請稍後再試或聯繫您的管理師。",
            },
            "jgb_tenant_summary": {
                "url_path": "/api/external/v1/tenants/{user_id}/summary",
                "params": {
                    "role_id": "{session.role_id}",
                    "user_id": "{session.user_id}",
                },
                "response_template": (
                    "您好！以下是您的租賃摘要：\n\n"
                    "📋 合約數量：{contracts_count}\n"
                    "🏠 目前物件：{active_estate}\n"
                    "💰 待繳帳單：{unpaid_bills_count} 張"
                ),
                "fallback_message": "目前無法查詢租賃摘要，請稍後再試或聯繫您的管理師。",
            },
        }

        # module → default endpoint mapping
        self._module_to_endpoint: Dict[str, str] = {
            "billing": "jgb_bills",
            "invoice": "jgb_invoices",
            "contract": "jgb_contracts",
            "payment": "jgb_payments",
            "repair": "jgb_repairs",
            "tenant": "jgb_tenant_summary",
            "lessee": "jgb_tenant_summary",
        }

        # Category mapping for KB entries
        self._endpoint_to_category: Dict[str, str] = {
            "jgb_bills": "帳務管理",
            "jgb_invoices": "帳務管理",
            "jgb_contracts": "合約管理",
            "jgb_contract_checkin": "合約管理",
            "jgb_payments": "繳費管理",
            "jgb_repairs": "修繕系統",
            "jgb_tenant_summary": "租客管理",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, gaps: List[GapItem]) -> Tuple[List[dict], List[dict]]:
        """
        Build KB entries and api_endpoint records for dynamic gaps.

        Returns:
            (kb_entries, api_endpoint_entries)
        """
        dynamic_gaps = self._filter_dynamic_gaps(gaps)

        kb_entries: List[dict] = []
        seen_endpoints: Dict[str, dict] = {}

        for gap in dynamic_gaps:
            endpoint_key = self._map_to_endpoint(gap)
            if endpoint_key is None:
                continue

            kb_entries.append(self._build_kb_entry(gap, endpoint_key))

            if endpoint_key not in seen_endpoints:
                seen_endpoints[endpoint_key] = self._build_api_endpoint_entry(
                    endpoint_key
                )

        api_entries = list(seen_endpoints.values())
        return kb_entries, api_entries

    def export(
        self,
        kb_entries: List[dict],
        api_entries: List[dict],
        output_path: Path,
    ) -> None:
        """Export KB entries and API endpoint entries to a JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "kb_entries": kb_entries,
            "api_endpoint_entries": api_entries,
        }
        output_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _filter_dynamic_gaps(self, gaps: List[GapItem]) -> List[GapItem]:
        """Filter gaps to only query_type=dynamic."""
        return [g for g in gaps if g.query_type == "dynamic"]

    def _map_to_endpoint(self, gap: GapItem) -> Optional[str]:
        """Map a gap item to a JGB API endpoint key based on topic_id prefix and keywords."""
        module = _extract_module_from_topic(gap.topic_id)
        if module is None:
            return None

        # Check for checkin-specific keywords in question (contract module only)
        if module == "contract":
            question_lower = gap.question.lower()
            if any(kw in question_lower for kw in _CHECKIN_KEYWORDS):
                return "jgb_contract_checkin"

        return self._module_to_endpoint.get(module)

    def _build_kb_entry(self, gap: GapItem, endpoint_key: str) -> dict:
        """Build a KB entry dict with action_type=api_call and api_config."""
        config = self.endpoint_configs[endpoint_key]
        return {
            "topic_id": gap.topic_id,
            "question_summary": gap.question,
            "action_type": "api_call",
            "scope": "global",
            "category": self._endpoint_to_category.get(endpoint_key, "系統查詢"),
            "priority": gap.priority,
            "api_config": {
                "endpoint": endpoint_key,
                "params": dict(config["params"]),
                "response_template": config["response_template"],
                "fallback_message": config["fallback_message"],
                "combine_with_knowledge": True,
            },
        }

    def _build_api_endpoint_entry(self, endpoint_key: str) -> dict:
        """Build an api_endpoints table entry for a JGB endpoint."""
        config = self.endpoint_configs[endpoint_key]
        return {
            "endpoint_name": endpoint_key,
            "url_path": config["url_path"],
            "method": "GET",
            "required_params": ["role_id", "user_id"],
            "auth_type": "api_key",
            "auth_header": "X-API-Key",
        }
