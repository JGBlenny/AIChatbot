"""pytest 外掛：整個行程以 `AGENT_WRITE_CANDIDATES=off` 跑（A-2a 驗收：開關 off ⇒ B 片行為逐字相同）。

`scripts/run-tests.sh` 走 `docker compose run`，不轉傳主機環境變數，故以外掛在匯入時設定。用法：

    scripts/run-tests.sh unit -p tests.unit.agent._a2a_candidates_off_plugin \\
        tests/unit/agent/test_b_write_replies_program_req.py tests/unit/agent/test_pipeline_golden_req.py

檔名不以 `test_` 開頭 ⇒ 一般測試收集不會載入它。
"""
import os

os.environ["AGENT_WRITE_CANDIDATES"] = "off"


def pytest_report_header(config):
    return f"A-2a off-run: AGENT_WRITE_CANDIDATES={os.environ.get('AGENT_WRITE_CANDIDATES')!r}"


def pytest_sessionfinish(session, exitstatus):
    # 正對照：跑完仍是 off（沒有被某個 fixture 永久蓋掉）
    print(f"\n[a2a-off-plugin] AGENT_WRITE_CANDIDATES at session end = "
          f"{os.environ.get('AGENT_WRITE_CANDIDATES')!r}")
