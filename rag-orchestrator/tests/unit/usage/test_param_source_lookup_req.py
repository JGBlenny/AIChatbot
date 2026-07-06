"""unit：參數雙軌收斂——resolver 切讀 lookup_tables（盤查 20260706 步驟②）。

契約：VENDOR_PARAMS_FROM_LOOKUP=true（預設）→ 讀 lookup_tables（param 四分類），
型別/單位/顯示名自 metadata 還原；=false → 回退 vendor_configs（原行為，可秒切回）。
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


def test_lookup_source_reads_lookup_tables(monkeypatch):
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


def test_flag_off_falls_back_to_configs(monkeypatch):
    rows = [{"param_key": "late_fee", "param_value": "200",
             "data_type": "number", "unit": "元", "display_name": "逾期手續費",
             "description": None}]
    r, cursor = _resolver_with(rows, monkeypatch, flag="false")
    params = r.get_vendor_parameters(2, use_cache=False)
    assert "vendor_configs" in cursor.execute.call_args[0][0]
    assert params["late_fee"]["value"] == "200"
