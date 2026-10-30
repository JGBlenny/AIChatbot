"""unit：替身寫入紀錄 `JGB_MOCK_WRITE_LOG`（plan-assistant-11-items-20261014 §3f「檔案擁有」條；
就緒審查 r1 B3）。

被測物：`JGBMockTransport.send` 在寫入端點（`WRITE_ENDPOINTS`，含 jgb2-req#19～#22）呼叫後
追加一行 JSON：`endpoint_key`、守門後的 request body、回應狀態碼、建立或更新後的那一列、
四域列數。命題：
  1. 未設 env ⇒ 完全不寫（正對照：同一操作設了 env 就有一行）；
  2. 設了 env ⇒ 每次寫入一行，欄位逐一正確；冪等鍵遮罩（token ⛔ 落檔）；
  3. 寫入失敗（422／404）也記一行、`row` 為 null、四域列數不變；同 token 重送記一行但列數不變；
  4. 讀端點 ⛔ 記；
  5. 只在 mock transport 內——`RealHttpTransport` 不認得這個 env。
"""
from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path

import pytest

from services import jgb_system_api as api_mod
from services.jgb import fixture_store
from services.jgb.transport import MOCK_WRITE_LOG_ENV, RealHttpTransport

pytestmark = pytest.mark.unit

FIXTURE = (Path(__file__).resolve().parents[3]
           / "services" / "jgb" / "fixture_data" / "assistant_demo_vendor4.json")
ROLE, OWNER = "20151", "12291"
ESTATE_BODY = {"title": "紀錄測試物件", "city": "台北市", "district": "信義區",
               "address": "松仁路1號", "use_for": "residential", "rent": 12000}


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def api(monkeypatch):
    monkeypatch.setenv("USE_MOCK_JGB_API", "true")
    monkeypatch.delenv("MOCK_FAIL_NEXT_WRITE", raising=False)
    monkeypatch.delenv(MOCK_WRITE_LOG_ENV, raising=False)
    monkeypatch.setattr(fixture_store, "_DATA", fixture_store._DATA)
    fixture_store.load_from(FIXTURE)
    return api_mod.JGBSystemAPI()


def _lines(path: Path) -> list:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _counts(api) -> dict:
    m = api._mock_transport
    return {"estates": len(m.estate_fixtures.rows()), "contracts": len(m.contract_fixtures.rows()),
            "bills": len(m.fixtures.rows()), "repairs": len(m.repair_fixtures.rows())}


def test_env_name_is_the_documented_one():
    assert MOCK_WRITE_LOG_ENV == "JGB_MOCK_WRITE_LOG"


def test_unset_env_writes_nothing(api, tmp_path, monkeypatch):
    """未設 env ⇒ transport 模組在寫入過程中**任何路徑**都不開檔（以 `open` 探針證明，
    ⛔ 只看 tmp_path——寫到別處的預設路徑也要抓得到）。"""
    import builtins
    from services.jgb import transport as tr

    opened: list = []

    def _spy_open(*args, **kwargs):
        opened.append(args[0] if args else kwargs.get("file"))
        return builtins.open(*args, **kwargs)

    monkeypatch.setattr(tr, "open", _spy_open, raising=False)
    log = tmp_path / "writes.jsonl"
    resp = _run(api.assistant_create_estate(ROLE, OWNER, dict(ESTATE_BODY), idempotency_key="k1"))
    assert resp["success"], resp                        # 前提：寫入真的發生
    assert opened == [] and list(tmp_path.iterdir()) == []
    # 正對照：同一組裝置設了 env ⇒ 探針看得到開檔、且有一行（否則上面的「沒開檔」可能只是探針壞了）
    monkeypatch.setenv(MOCK_WRITE_LOG_ENV, str(log))
    _run(api.assistant_create_estate(ROLE, OWNER, dict(ESTATE_BODY), idempotency_key="k2"))
    assert opened == [str(log)]
    assert len(_lines(log)) == 1


def test_successful_create_logs_body_status_row_and_counts(api, tmp_path, monkeypatch):
    log = tmp_path / "writes.jsonl"
    monkeypatch.setenv(MOCK_WRITE_LOG_ENV, str(log))
    before = _counts(api)
    resp = _run(api.assistant_create_estate(ROLE, OWNER, dict(ESTATE_BODY),
                                            idempotency_key="secret-token-value"))
    assert resp["success"], resp
    (line,) = _lines(log)
    assert line["endpoint_key"] == "assistant_create_estate"
    assert line["path"] == "/api/external/v1/estates"
    assert line["status"] == 200
    assert line["body"] == {**ESTATE_BODY, "role_id": ROLE, "viewer_user_id": OWNER,
                            "idempotency_key": "<redacted>"}
    assert "secret-token-value" not in log.read_text(encoding="utf-8")
    assert line["row"]["id"] == resp["data"]["id"]
    assert line["row"]["title"] == ESTATE_BODY["title"] and line["row"]["floor"] is None
    assert line["counts"] == {**before, "estates": before["estates"] + 1}
    assert _counts(api) == line["counts"]


def test_failures_and_replays_log_without_changing_counts(api, tmp_path, monkeypatch):
    log = tmp_path / "writes.jsonl"
    monkeypatch.setenv(MOCK_WRITE_LOG_ENV, str(log))
    before = _counts(api)
    bad = _run(api.assistant_create_estate(ROLE, OWNER, {**ESTATE_BODY, "team_id": 1}))
    assert bad["success"] is False
    foreign = _run(api.assistant_create_contract(ROLE, "990002", {
        "estate_id": 53973, "date_start": "2026-11-01", "date_end": "2027-10-31",
        "rent": 1000, "to_user_phone": "0912345678"}))
    assert foreign["success"] is False
    first = _run(api.assistant_create_bill(ROLE, OWNER, {
        "contract_id": 89481, "title": "清潔費", "total": 1500, "date_expire": "2026-10-31"},
        idempotency_key="same"))
    replay = _run(api.assistant_create_bill(ROLE, OWNER, {
        "contract_id": 89481, "title": "清潔費", "total": 1500, "date_expire": "2026-10-31"},
        idempotency_key="same"))
    assert first == replay and first["success"]
    lines = _lines(log)
    assert [(x["endpoint_key"], x["status"]) for x in lines] == [
        ("assistant_create_estate", 422), ("assistant_create_contract", 404),
        ("assistant_create_bill", 200), ("assistant_create_bill", 200)]
    assert lines[0]["row"] is None and lines[1]["row"] is None
    assert lines[0]["counts"] == lines[1]["counts"] == before
    assert lines[2]["counts"] == lines[3]["counts"] == {**before, "bills": before["bills"] + 1}
    assert lines[2]["row"] == lines[3]["row"] and lines[2]["row"]["contract_id"] == 89481


def test_repair_write_is_logged_and_reads_are_not(api, tmp_path, monkeypatch):
    log = tmp_path / "writes.jsonl"
    monkeypatch.setenv(MOCK_WRITE_LOG_ENV, str(log))
    _run(api.get_contracts(ROLE, viewer_user_id=OWNER))
    _run(api.get_repairs(ROLE, OWNER, viewer_user_id=OWNER))
    assert not log.exists()                             # 讀端點 ⛔ 記
    resp = _run(api.create_repair(role_id=ROLE, estate_id=68926, category_id=None, item_id=None,
                                  broken_reason="冷氣不冷", user_id=OWNER))
    assert resp["success"], resp
    (line,) = _lines(log)
    assert line["endpoint_key"] == "create_repair" and line["status"] == 200
    assert line["body"]["viewer_user_id"] == OWNER and line["row"]["id"] == resp["data"]["id"]


def test_real_http_transport_has_no_write_log():
    """⛔ 碰真 HTTP 路徑：紀錄只在 mock transport 內。"""
    assert MOCK_WRITE_LOG_ENV not in inspect.getsource(RealHttpTransport)
    assert "_append_write_log" not in inspect.getsource(RealHttpTransport)
