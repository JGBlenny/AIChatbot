"""unit 層：非功能約束（需求 9.4 效能預算、10.5 執行環境）。

⚠️ 9.4 的正式數字以 `.kiro/specs/documind-ocr-mapping/perf-20260903.md` 為準（進程內 20 頁 ×20 次）；
本測試只守「純規則路徑不得退化到接近 2 s 預算」的粗門檻，⛔ 不當基準用。
"""
import copy
import json
import statistics
import sys
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.ocr_mapping import router

pytestmark = pytest.mark.unit
FIX = Path(__file__).parent / "fixtures" / "documind_contract_sample.json"


def _twenty_page_payload() -> dict:
    base = json.loads(FIX.read_text(encoding="utf-8"))
    base = {k: v for k, v in base.items() if not k.startswith("_")}
    pages = base["pages"] + [copy.deepcopy(base["pages"][1 + i % 2]) | {"page_number": 4 + i} for i in range(17)]
    return base | {"pages": pages, "total_pages": len(pages), "vendor_id": 1, "role_id": "20151",
                   "mode": "b2c", "target_user": "landlord", "session_id": "backtest_session_ocr_nfr"}


@pytest.mark.req("documind-ocr-mapping:9.4")
def test_rule_only_path_p95_is_far_below_two_seconds():
    app = FastAPI(); app.include_router(router); c = TestClient(app)
    payload = _twenty_page_payload()
    assert c.post("/api/v1/ocr-mapping/contract", json=payload).status_code == 200   # 暖機
    lat = []
    for _ in range(10):
        t0 = time.perf_counter(); r = c.post("/api/v1/ocr-mapping/contract", json=payload); lat.append((time.perf_counter() - t0) * 1000)
        assert r.status_code == 200
    lat.sort()
    p95 = lat[int(len(lat) * 0.95) - 1]
    assert p95 < 500, f"純規則路徑 P95={p95:.1f}ms，退化到預算（2000ms）的 1/4 以上，請查 clause_splitter／page_merger"
    assert statistics.median(lat) < 200


@pytest.mark.req("documind-ocr-mapping:10.5")
def test_runs_on_python_311_container():
    assert sys.version_info >= (3, 11), "測試須在 Python 3.11 容器內跑（testing-code.md 一）"
