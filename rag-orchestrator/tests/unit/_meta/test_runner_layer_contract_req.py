"""unit：runner 層級契約（spec conversational-routing-execution 任務 1.11｜R1.1/1.4/1.5）。

守的是一條鏈的**成套對應**：

    LAYER → pytest selection → REQUESTED_TEST_LAYERS → RUN_* flags

`tests/conftest.py` 的空跑守門靠兩個來源交叉校驗（runner 宣告 vs pytest 實際 selection），
但那兩者都由 `scripts/run-tests.sh` 的同一個 `case` 區塊注入。本檔是**第三層**：
直接對 runner 與 CI 的注入內容下斷言，防「整組注入被一起改壞」——
那正是共因失效的來源，兩來源交叉守門本身擋不住。

⚠️ 本檔刻意用**純文字解析**而非執行 `run-tests.sh`（後者會啟動容器，不屬 unit 層）。
"""
import os
import re

import pytest

pytestmark = pytest.mark.unit

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))          # → repo/rag-orchestrator
_REPO = os.path.dirname(_ROOT)
_RUNNER = os.path.join(_REPO, "scripts", "run-tests.sh")
_WORKFLOW = os.path.join(_REPO, ".github", "workflows", "tests.yml")

#: LAYER → (必須注入的 RUN_* 旗標集合, REQUESTED_TEST_LAYERS 的值)
EXPECTED_CONTRACT = {
    "unit":        (set(), None),                       # 離線：兩者皆不注入
    "integration": ({"RUN_INTEGRATION"}, "integration"),
    "e2e":         ({"RUN_E2E"}, "e2e"),
    "all":         ({"RUN_INTEGRATION", "RUN_E2E"}, "integration,e2e"),
}


def _env_args_block() -> str:
    """抽出 run-tests.sh 內組 ENV_ARGS 的 case 區塊。"""
    src = open(_RUNNER, encoding="utf-8").read()
    m = re.search(r"ENV_ARGS=\(\)\s*\ncase \"\$LAYER\" in\n(.*?)\nesac", src, re.S)
    assert m, "run-tests.sh 找不到 ENV_ARGS 的 case 區塊（結構已改變，契約測試需同步更新）"
    return m.group(1)


def _injected_for(layer: str, block: str) -> "tuple[set, str | None]":
    """從 case 區塊解析某 LAYER 實際注入了什麼。"""
    m = re.search(rf"^\s*{re.escape(layer)}\)(.*?);;", block, re.S | re.M)
    if not m:
        return set(), None
    body = m.group(1)
    flags = set(re.findall(r"-e\s+(RUN_INTEGRATION|RUN_E2E)=1", body))
    req = re.search(r"-e\s+REQUESTED_TEST_LAYERS=([^\s)]+)", body)
    return flags, (req.group(1) if req else None)


@pytest.mark.req("conversational-routing-execution:1.1")
@pytest.mark.parametrize("layer", sorted(EXPECTED_CONTRACT))
def test_runner_injects_matching_flags_and_declaration(layer):
    """四種 LAYER 的旗標與宣告必須成套對應——缺一即為共因失效的入口。"""
    exp_flags, exp_req = EXPECTED_CONTRACT[layer]
    flags, req = _injected_for(layer, _env_args_block())
    assert flags == exp_flags, (
        f"LAYER={layer} 的 RUN_* 旗標注入不符：預期 {sorted(exp_flags)}，實際 {sorted(flags)}")
    assert req == exp_req, (
        f"LAYER={layer} 的 REQUESTED_TEST_LAYERS 不符：預期 {exp_req!r}，實際 {req!r}")


@pytest.mark.req("conversational-routing-execution:1.4")
def test_unit_layer_stays_offline():
    """unit 層不得注入任何 gated 旗標或宣告（維持離線、不受空跑守門管轄）。"""
    flags, req = _injected_for("unit", _env_args_block())
    assert not flags and req is None, f"unit 層不該有注入，實際 flags={flags} req={req!r}"


@pytest.mark.req("conversational-routing-execution:1.4")
def test_ci_integration_job_declares_matching_pair():
    """CI 的 integration job 必須同時帶 RUN_INTEGRATION=1 與 REQUESTED_TEST_LAYERS=integration。"""
    yaml = pytest.importorskip("yaml")
    spec = yaml.safe_load(open(_WORKFLOW, encoding="utf-8").read())
    env = (spec["jobs"]["integration"].get("env") or {})
    assert str(env.get("RUN_INTEGRATION")) == "1", f"CI 缺 RUN_INTEGRATION=1：{env}"
    assert env.get("REQUESTED_TEST_LAYERS") == "integration", \
        f"CI 缺 REQUESTED_TEST_LAYERS=integration：{env}"


@pytest.mark.req("conversational-routing-execution:1.4")
def test_ci_integration_job_has_no_job_level_swallow():
    """job 級 continue-on-error 會吞掉結構性失效的 exit 1，不得復活。"""
    yaml = pytest.importorskip("yaml")
    spec = yaml.safe_load(open(_WORKFLOW, encoding="utf-8").read())
    job = spec["jobs"]["integration"]
    assert "continue-on-error" not in job, \
        "integration job 出現 job 級 continue-on-error——會使結構性失效在 CI 無訊號"
