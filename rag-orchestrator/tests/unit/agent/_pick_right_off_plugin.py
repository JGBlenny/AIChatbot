"""pytest 外掛：整個行程以 `AGENT_PICK_RIGHT=off` 跑（「選對紀錄」片驗收：開關 off ⇒ A-2a 行為逐字相同）。

`scripts/run-tests.sh` 走 `docker compose run`，不轉傳主機環境變數，故以外掛在匯入時設定。用法：

    scripts/run-tests.sh unit -p tests.unit.agent._pick_right_off_plugin tests/unit/agent

檔名不以 `test_` 開頭 ⇒ 一般測試收集不會載入它。⚠️ 個別測試以 `monkeypatch.delenv` 明設 on 的（如
`test_pick_right_record_req.py` 的 autouse）仍跑 on——off-run 的比對對象是其餘測試。
"""
import os

os.environ["AGENT_PICK_RIGHT"] = "off"


def pytest_report_header(config):
    return f"pick-right off-run: AGENT_PICK_RIGHT={os.environ.get('AGENT_PICK_RIGHT')!r}"


def pytest_sessionfinish(session, exitstatus):
    # 正對照：跑完仍是 off（沒有被某個 fixture 永久蓋掉）
    print(f"\n[pick-right-off-plugin] AGENT_PICK_RIGHT at session end = "
          f"{os.environ.get('AGENT_PICK_RIGHT')!r}")
