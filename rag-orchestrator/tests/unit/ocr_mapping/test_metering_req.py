"""unit 層：端點內計量與無個資日誌（design.md 決策 1／需求 9.3、9.3a、9.5）。

⛔ 不動 middleware（它只認 /api/v1/message）；本端點自行 begin → set_path → finalize。
以 spy 取代 usage_metering 的三個函式驗呼叫序與參數；is_internal 用真 begin() 驗；日誌用 capsys 驗。
"""
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.ocr_mapping import router
from services import usage_metering as um

pytestmark = pytest.mark.unit
FIX = Path(__file__).parent / "fixtures"
IDENTITY = {"vendor_id": 1, "role_id": "20151", "user_id": "12291", "mode": "b2c", "target_user": "landlord"}


@pytest.fixture()
def client() -> TestClient:
    app = FastAPI(); app.include_router(router); return TestClient(app)


@pytest.fixture()
def spy(monkeypatch):
    calls = {"begin": [], "set_path": [], "finalize": [], "add_llm_usage": []}
    monkeypatch.setattr(um, "begin", lambda fields: calls["begin"].append(dict(fields)))
    monkeypatch.setattr(um, "set_path", lambda processing_path=None, answer_source=None: calls["set_path"].append(processing_path))
    monkeypatch.setattr(um, "finalize", lambda status="success", http_status=200, db_pool=None: calls["finalize"].append((status, http_status)))
    monkeypatch.setattr(um, "add_llm_usage", lambda model, usage: calls["add_llm_usage"].append((model, usage)))
    return calls


def _payload(**override) -> dict:
    data = json.loads((FIX / "documind_contract_sample.json").read_text(encoding="utf-8"))
    data = {k: v for k, v in data.items() if not k.startswith("_")}
    data.update(IDENTITY); data.update(override)
    return data


# ── R9.3 成功路徑：begin 一次、set_path("ocr_mapping")、finalize(success,200) ────
@pytest.mark.req("documind-ocr-mapping:9.3")
def test_success_path_meters_exactly_once(client, spy):
    r = client.post("/api/v1/ocr-mapping/contract", json=_payload(session_id="backtest_session_m1"))
    assert r.status_code == 200
    assert len(spy["begin"]) == 1 and spy["set_path"] == ["ocr_mapping"] and spy["finalize"] == [("success", 200)]
    b = spy["begin"][0]
    assert {b["mode"], b["role_id"], b["target_user"], b["vendor_id"], b["session_id"]} == {"b2c", "20151", "landlord", 1, "backtest_session_m1"}


# ── R9.3 拒絕路徑亦計量：status="rejected"＋對應 http_status ───────────────────
@pytest.mark.req("documind-ocr-mapping:9.3")
@pytest.mark.parametrize("path,override,code", [
    ("/api/v1/ocr-mapping/transcript", {}, 400),                       # mismatch
    ("/api/v1/ocr-mapping/bill", {"document_type": "bill"}, 400),      # unsupported
    ("/api/v1/ocr-mapping/contract", {"pages": None}, 422),            # invalid payload
])
def test_rejections_are_metered_as_rejected(client, spy, path, override, code):
    r = client.post(path, json=_payload(**override))
    assert r.status_code == code
    assert len(spy["begin"]) == 1 and spy["finalize"] == [("rejected", code)]


@pytest.mark.req("documind-ocr-mapping:9.3")
def test_413_is_metered_as_rejected(client, spy, monkeypatch):
    monkeypatch.setenv("OCR_MAPPING_MAX_BODY_MB", "0.000001")
    r = client.post("/api/v1/ocr-mapping/contract", json=_payload())
    assert r.status_code == 413 and spy["finalize"] == [("rejected", 413)]


# ── R9.3a 內部流量：session_id 前綴命中 INTERNAL_RULES ⇒ is_internal；未帶 ⇒ 外部 ──
@pytest.mark.req("documind-ocr-mapping:9.3a")
def test_internal_flag_follows_session_prefix_rules():
    um.begin({**IDENTITY, "session_id": "backtest_session_ocr_x"})
    assert um._ctx.get().is_internal is True and um._ctx.get().internal_kind == "backtest"
    um.begin({**IDENTITY})                                             # 未帶 session_id ⇒ 外部
    assert um._ctx.get().is_internal is False and um._ctx.get().user_type == "landlord"
    um.begin({**IDENTITY, "session_id": "line-6d0d1320"})              # 真實 LINE session ⇒ 外部（正對照）
    assert um._ctx.get().is_internal is False


# ── R9.5 日誌不落個資：只印欄位名／source／confidence ─────────────────────────
@pytest.mark.req("documind-ocr-mapping:9.5")
def test_logs_contain_field_names_but_no_values_or_ocr_text(client, spy, capsys):
    r = client.post("/api/v1/ocr-mapping/contract", json=_payload(session_id="backtest_session_m2"))
    assert r.status_code == 200
    out = capsys.readouterr().out
    assert "[ocr-mapping]" in out and "date_end" in out                # 有摘要行、有欄位名
    for pii in ("壹萬參仟捌佰", "27600", "歐陽小美", "房屋租賃契約書", "信義路五段", "13800"):
        assert pii not in out, f"日誌洩漏個資／欄位值：{pii}"


# ── 雙落點反例：middleware 不得替 ocr-mapping 落計量 ─────────────────────────────
@pytest.mark.req("documind-ocr-mapping:9.3")
def test_middleware_does_not_meter_ocr_mapping():
    """需求 9.3／9.3a 的守門：ocr-mapping **端點內自記**，⛔ middleware 不得雙落點。

    ⚠️ **2026-09-11 舊鏈退役後本斷言加強**：原本驗的是
    `request.url.path == "/api/v1/message"` 仍在（＝middleware 只認那一條）。
    該端點已隨舊 REST 對話鏈刪除，整條 REST 計量分支一併移除
    （它跑在路由之前，會對 404 扣額度並寫 `status='success'` 事件）。
    現在 middleware **只做 `/mcp` 額度短路、完全不 begin／finalize**，
    本需求要守的「不雙落點」因此比原本更強。
    ⛔ 日後若重開 REST 入口，⛔ 不要在 middleware 以路徑字串等值判斷（改路徑會靜默停止計量）。
    """
    src = (Path(__file__).parents[3] / "app.py").read_text(encoding="utf-8")
    body = src.split("def usage_metering_middleware", 1)[1].split("@app.", 1)[0]
    assert "ocr-mapping" not in body                      # 原斷言，逐字保留
    # ⚠️ 比對**判斷式**而非字串出現與否——docstring 裡會提到該路徑以說明為何移除
    assert 'request.url.path == "/api/v1/message"' not in body
    assert "_um.begin(" not in body and "_um.finalize(" not in body   # ⛔ 不得雙落點
    assert 'request.url.path.startswith("/mcp")' in body  # 正對照：/mcp 短路仍在
