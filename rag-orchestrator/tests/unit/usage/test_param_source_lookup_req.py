"""unit：參數來源分工（使用者裁決 2026-07-06）——通用參數預設讀 vendor_configs；
VENDOR_PARAMS_FROM_LOOKUP=true 才切 lookup（保留切換能力）。案場級資料歸 lookup 錨點。
"""
import json
import pytest
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.unit


def _resolver_with(rows, monkeypatch, flag="true"):
    monkeypatch.setenv("VENDOR_PARAMS_FROM_LOOKUP", flag)
    from services.vendor_parameter_resolver import VendorParameterResolver
    r = VendorParameterResolver.__new__(VendorParameterResolver)
    r._cache = {}
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    cursor.execute = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value = cursor
    r._get_db_connection = MagicMock(return_value=conn)
    return r, cursor


def test_flag_on_reads_lookup_tables(monkeypatch):
    rows = [{"param_key": "late_fee", "param_value": "300",
             "data_type": "number", "unit": "元", "display_name": "逾期手續費",
             "description": None}]
    r, cursor = _resolver_with(rows, monkeypatch, flag="true")
    params = r.get_vendor_parameters(2, use_cache=False)
    sql = cursor.execute.call_args[0][0]
    assert "lookup_tables" in sql
    assert "category IN" in sql                       # 只撈參數四分類，不掃物件級資料
    assert params["late_fee"]["value"] == "300"
    assert params["late_fee"]["unit"] == "元"


def test_default_reads_vendor_configs(monkeypatch):
    rows = [{"param_key": "late_fee", "param_value": "200",
             "data_type": "number", "unit": "元", "display_name": "逾期手續費",
             "description": None}]
    r, cursor = _resolver_with(rows, monkeypatch, flag="unset-默認")
    params = r.get_vendor_parameters(2, use_cache=False)
    assert "vendor_configs" in cursor.execute.call_args[0][0]
    assert params["late_fee"]["value"] == "200"
