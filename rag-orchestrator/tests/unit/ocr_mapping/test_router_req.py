"""unit 層：端點守門（design.md 元件 1／routers/ocr_mapping.py）。需求 1.2、1.3、1.5、1.6。

以最小 FastAPI app 只掛本 router（無 DB、無 lifespan）用 TestClient 打——仍屬 unit（純進程內）。
"""
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.ocr_mapping import router
from services.api_key_auth import is_exempt
from services.ocr_mapping.models import CONTRACT_FIELDS

pytestmark = pytest.mark.unit
FIX = Path(__file__).parent / "fixtures"
IDENTITY = {"vendor_id": 1, "role_id": "20151", "user_id": "12291", "mode": "b2c",
            "target_user": "landlord", "session_id": "backtest_session_ocr_router"}


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _payload(name: str, **override) -> dict:
    data = json.loads((FIX / name).read_text(encoding="utf-8"))
    data = {k: v for k, v in data.items() if not k.startswith("_")}
    data.update(IDENTITY); data.update(override)
    return data


@pytest.mark.req("documind-ocr-mapping:1.1")
def test_happy_path_returns_mapping_result(client):
    r = client.post("/api/v1/ocr-mapping/contract", json=_payload("documind_contract_sample.json"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "draft" and set(body["fields"]) == set(CONTRACT_FIELDS)
    assert body["provenance"]["mapping_version"]


@pytest.mark.req("documind-ocr-mapping:1.2")
def test_path_body_document_type_mismatch_is_400(client):
    r = client.post("/api/v1/ocr-mapping/transcript", json=_payload("documind_contract_sample.json"))
    assert r.status_code == 400 and r.json()["error_code"] == "DOCUMENT_TYPE_MISMATCH"


@pytest.mark.req("documind-ocr-mapping:1.3")
def test_unsupported_document_type_is_400(client):
    r = client.post("/api/v1/ocr-mapping/bill", json=_payload("documind_contract_sample.json", document_type="bill"))
    assert r.status_code == 400 and r.json()["error_code"] == "UNSUPPORTED_DOCUMENT_TYPE"


@pytest.mark.req("documind-ocr-mapping:1.5")
def test_body_over_limit_is_413(client, monkeypatch):
    monkeypatch.setenv("OCR_MAPPING_MAX_BODY_MB", "0.000001")          # ≈1 byte
    r = client.post("/api/v1/ocr-mapping/contract", json=_payload("documind_contract_sample.json"))
    assert r.status_code == 413 and r.json()["error_code"] == "BODY_TOO_LARGE"


@pytest.mark.req("documind-ocr-mapping:1.1")
def test_invalid_documind_payload_is_422_with_error_code(client):
    bad = _payload("documind_contract_sample.json"); bad.pop("pages")
    r = client.post("/api/v1/ocr-mapping/contract", json=bad)
    assert r.status_code == 422 and r.json()["error_code"] == "INVALID_DOCUMIND_PAYLOAD"


@pytest.mark.req("documind-ocr-mapping:1.4")
def test_empty_pages_is_200_draft_not_500(client):
    r = client.post("/api/v1/ocr-mapping/contract", json=_payload("documind_contract_sample.json", pages=[], total_pages=0))
    assert r.status_code == 200 and r.json()["status"] == "draft"


@pytest.mark.req("documind-ocr-mapping:1.6")
def test_endpoint_is_not_exempt_from_api_key_auth():
    assert is_exempt("/api/v1/ocr-mapping/contract") is False
    assert is_exempt("/api/v1/health") is True                          # 正對照：豁免清單本身讀得到


@pytest.mark.req("documind-ocr-mapping:1.6")
def test_router_is_wired_into_app():
    src = (Path(__file__).parents[3] / "app.py").read_text(encoding="utf-8")
    assert "ocr_mapping.router" in src
