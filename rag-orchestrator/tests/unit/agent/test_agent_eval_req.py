"""unit：`tools/agent_eval.py`（spec agentic-mcp-orchestration・任務 4.2）。

全部離線：manifest sha 校驗、fake provider 的 agent 鏈、old 鏈用假 httpx
transport（不打真 `:8100`）。⛔ 不呼叫真 OpenAI，`--provider openai` 直接拒絕。

覆蓋（任務 brief「測試」節）：
- manifest sha 不符 ⇒ 退出碼 3。
- fake provider 跑 topics 前 3 題 ⇒ JSONL 欄位形狀、⛔ 無原文鍵。
- 硬線判定三態（PASS／FAIL／UNSET）。
- `knowledge_gap_unfilled` 透傳（manifest `gap_batches_imported` 開／關）。
- old 鏈：假 httpx transport 驗 session_id 前綴、header 帶 key 但 log／json
  body 不含 key 字面。
"""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_RAG_ROOT = Path(__file__).resolve().parents[3]
if str(_RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(_RAG_ROOT))
_TOOLS_DIR = _RAG_ROOT / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

agent_eval = importlib.import_module("agent_eval")

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 樣本檔＋manifest 夾具
# ---------------------------------------------------------------------------


def _write_topics(tmp_path: Path) -> Path:
    doc = {
        "_meta": {"version": "test"},
        "topics": [
            {
                "id": "T-x",
                "forbid": {"*": ["一律可以"], "s1": ["禁詞A"]},
                "phrasings": [
                    {"q": "問題一", "sub": "s1", "type": "直接", "src": "t"},
                    {"q": "問題二", "sub": "s1", "type": "口語", "src": "t"},
                    {"q": "問題三", "sub": "s1", "type": "俗稱", "src": "t"},
                ],
                "boundary": [
                    {"q": "邊界一", "sub": "s1", "type": "邊界", "src": "t"},
                ],
            }
        ],
    }
    p = tmp_path / "topics-v2.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


def _write_scenarios(tmp_path: Path) -> Path:
    doc = {
        "scenarios": [
            {
                "id": "S-x",
                "turns": [
                    {"turn": 1, "q": "有沒有 600 戶", "expect_kind": "handoff",
                     "must_not_contain": ["可以支援"], "sensitive": True},
                    {"turn": 2, "q": "可不可以線上簽約", "expect_kind": "answer",
                     "must_not_contain": ["一律可以"], "sensitive": False},
                ],
            }
        ]
    }
    p = tmp_path / "scenarios-v1.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_manifest(tmp_path: Path, topics_path: Path, scenarios_path: Path, *,
                     gap_batches_imported: bool = False, baseline_fixed_rate=None) -> Path:
    manifest = {
        "gap_batches_imported": gap_batches_imported,
        "sets": {
            "topics": {
                "available": True,
                "path": str(topics_path.relative_to(tmp_path)),
                "sha256": _sha(topics_path),
            },
            "scenarios": {
                "available": True,
                "path": str(scenarios_path.relative_to(tmp_path)),
                "sha256": _sha(scenarios_path),
            },
            "traffic": {"available": False, "path": None, "sha256": None, "note": "尚未凍結"},
        },
        "baseline": {"fixed_rate": {"value": baseline_fixed_rate}},
    }
    p = tmp_path / "samples-manifest.json"
    p.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.fixture()
def sample_root(tmp_path):
    topics = _write_topics(tmp_path)
    scenarios = _write_scenarios(tmp_path)
    manifest = _write_manifest(tmp_path, topics, scenarios)
    return tmp_path, manifest


# ---------------------------------------------------------------------------
# 1) manifest sha 不符 ⇒ 退出碼 3
# ---------------------------------------------------------------------------


def test_sha_mismatch_exits_3(sample_root, tmp_path, capsys):
    root, manifest_path = sample_root
    # 竄改樣本內容（模擬「看過結果後改樣本」）
    topics_path = root / "topics-v2.json"
    doc = json.loads(topics_path.read_text(encoding="utf-8"))
    doc["topics"][0]["phrasings"].append({"q": "額外題", "sub": "s1", "type": "直接", "src": "t"})
    topics_path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    out_dir = tmp_path / "out"
    code = agent_eval.main(
        [
            "--set", "topics", "--chain", "agent", "--out", str(out_dir),
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_SAMPLES_CHANGED
    captured = capsys.readouterr()
    assert "樣本已變動" in captured.err
    assert "不得在看過結果後改樣本" in captured.err


def test_sha_ok_passes_check(sample_root):
    root, manifest_path = sample_root
    manifest = agent_eval.load_manifest(manifest_path)
    check = agent_eval.verify_manifest(manifest, "topics", root=root)
    assert check.ok is True

    # 正對照組（CANON 否定結論紀律）：manifest 記錄的 sha 若也連「已知一致」
    # 的案例都判不一致，代表比對邏輯本身壞了，不是樣本真的變了。
    assert check.mismatches == []


def test_traffic_unavailable_exits_4(sample_root, tmp_path):
    root, manifest_path = sample_root
    out_dir = tmp_path / "out2"
    code = agent_eval.main(
        [
            "--set", "traffic", "--chain", "agent", "--out", str(out_dir),
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_SAMPLE_UNAVAILABLE


# ---------------------------------------------------------------------------
# 2) fake provider 跑 topics 前 3 題 ⇒ JSONL 欄位形狀、無原文鍵
# ---------------------------------------------------------------------------


_EXPECTED_JSONL_KEYS = {
    "set", "idx", "turn", "chain", "kind", "answered", "handoff_reason",
    "sensitive_expected", "sensitive_leak", "boundary_ok", "forbid_hit",
    "verifier_rejects", "latency_ms", "cost_usd", "knowledge_gap_unfilled",
    "answer_sha256", "answer_len",
}


def test_agent_chain_fake_provider_topics_shape(sample_root, tmp_path):
    root, manifest_path = sample_root
    out_dir = tmp_path / "out3"
    code = agent_eval.main(
        [
            "--set", "topics", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake", "--limit", "3",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_OK

    jsonl_path = out_dir / "topics.jsonl"
    lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3

    for line in lines:
        row = json.loads(line)
        assert set(row.keys()) == _EXPECTED_JSONL_KEYS
        # ⛔ 不落原文：沒有任何鍵叫 answer/quote/text/user_message/q
        assert not (agent_eval._NO_VERBATIM_KEYS & set(row.keys()))
        assert row["chain"] == "agent"
        assert row["set"] == "topics"
        assert isinstance(row["answer_sha256"], str) and len(row["answer_sha256"]) == 64

    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "agent_eval report" in report
    assert "三項硬線" in report


def test_agent_chain_is_deterministic(sample_root, tmp_path):
    root, manifest_path = sample_root
    out1, out2 = tmp_path / "run1", tmp_path / "run2"
    for out_dir in (out1, out2):
        code = agent_eval.main(
            [
                "--set", "scenarios", "--chain", "agent", "--out", str(out_dir),
                "--provider", "fake",
                "--manifest", str(manifest_path), "--root", str(root),
            ]
        )
        assert code == agent_eval.EXIT_OK
    a = (out1 / "scenarios.jsonl").read_text(encoding="utf-8")
    b = (out2 / "scenarios.jsonl").read_text(encoding="utf-8")
    # latency_ms 會抖動，去掉它再比對其餘欄位的決定性
    def _strip_latency(text):
        rows = [json.loads(l) for l in text.strip().splitlines()]
        for r in rows:
            r.pop("latency_ms", None)
        return rows

    assert _strip_latency(a) == _strip_latency(b)


def test_provider_openai_refused(sample_root, tmp_path):
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_openai"
    with pytest.raises(SystemExit, match="不呼叫真 OpenAI"):
        agent_eval.main(
            [
                "--set", "topics", "--chain", "agent", "--out", str(out_dir),
                "--provider", "openai",
                "--manifest", str(manifest_path), "--root", str(root),
            ]
        )


# ---------------------------------------------------------------------------
# 3) 硬線判定三態
# ---------------------------------------------------------------------------


def _rec(**kwargs) -> agent_eval.EvalRecord:
    base = dict(
        set="s", idx="i", turn=0, chain="agent", kind="answer", answered=True,
        handoff_reason=None, sensitive_expected=False, sensitive_leak=False,
        boundary_ok=None, forbid_hit=False, verifier_rejects=0, latency_ms=1,
        cost_usd=0.0, knowledge_gap_unfilled=False, answer_digest={"sha256": "x", "len": 1},
    )
    base.update(kwargs)
    return agent_eval.EvalRecord(**base)


def test_hardlines_pass():
    records = [
        _rec(kind="handoff", sensitive_expected=True, sensitive_leak=False, handoff_reason="sensitive_no_grounding"),
        _rec(kind="answer"),
    ]
    manifest = {"baseline": {"fixed_rate": {"value": 0.9}}}
    h = agent_eval.compute_hardlines(records, manifest)
    assert h["agent"]["sensitive_zero_leak"]["pass"] is True
    assert h["agent"]["no_fabrication"]["pass"] is True
    assert h["agent"]["fixed_rate"]["verdict"] == "PASS"


def test_hardlines_fail_on_leak_and_fabrication():
    records = [
        _rec(kind="handoff", sensitive_expected=True, sensitive_leak=True),
        _rec(kind="answer", verifier_rejects=1),
    ]
    manifest = {"baseline": {"fixed_rate": {"value": 0.0}}}
    h = agent_eval.compute_hardlines(records, manifest)
    assert h["agent"]["sensitive_zero_leak"]["pass"] is False
    assert h["agent"]["sensitive_zero_leak"]["leaks"] == 1
    assert h["agent"]["no_fabrication"]["pass"] is False
    assert h["agent"]["fixed_rate"]["verdict"] == "FAIL"


def test_hardlines_unset_without_baseline():
    records = [_rec(kind="handoff", sensitive_expected=True)]
    manifest = {"baseline": {"fixed_rate": {"value": None}}}
    h = agent_eval.compute_hardlines(records, manifest)
    assert h["agent"]["fixed_rate"]["verdict"] == "UNSET"


# ---------------------------------------------------------------------------
# 4) knowledge_gap_unfilled 透傳
# ---------------------------------------------------------------------------


def test_knowledge_gap_unfilled_true_when_batches_not_imported(sample_root, tmp_path):
    root, _ = sample_root
    topics_path = root / "topics-v2.json"
    scenarios_path = root / "scenarios-v1.json"
    manifest_off = _write_manifest(root, topics_path, scenarios_path, gap_batches_imported=False)
    manifest = agent_eval.load_manifest(manifest_off)
    scenarios = agent_eval.load_samples("topics", manifest, root=root)
    assert all(t.knowledge_gap_unfilled for sc in scenarios for t in sc.turns)


def test_knowledge_gap_unfilled_false_when_batches_imported(sample_root, tmp_path):
    root, _ = sample_root
    topics_path = root / "topics-v2.json"
    scenarios_path = root / "scenarios-v1.json"
    manifest_on = _write_manifest(root, topics_path, scenarios_path, gap_batches_imported=True)
    manifest = agent_eval.load_manifest(manifest_on)
    scenarios = agent_eval.load_samples("topics", manifest, root=root)
    assert all(not t.knowledge_gap_unfilled for sc in scenarios for t in sc.turns)


def test_knowledge_gap_unfilled_field_present_in_jsonl(sample_root, tmp_path):
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_gap"
    agent_eval.main(
        [
            "--set", "topics", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake", "--limit", "1",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    row = json.loads((out_dir / "topics.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["knowledge_gap_unfilled"] is True  # manifest 夾具預設 gap_batches_imported=False


# ---------------------------------------------------------------------------
# 5) old 鏈：假 httpx transport 驗 session 前綴、header 帶 key 但不外洩字面
# ---------------------------------------------------------------------------


class _FakeHttpResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _RecordingClient:
    """比照真 `httpx.Client` 最小介面：`.post(url, json=..., headers=...)`。"""

    def __init__(self):
        self.requests: list[dict] = []

    def post(self, url, *, json, headers):
        self.requests.append({"url": url, "json": json, "headers": dict(headers)})
        return _FakeHttpResponse({"answer": "測試回答", "handoff": None})


def test_old_chain_session_prefix_and_key_not_leaked(monkeypatch, sample_root, tmp_path):
    root, manifest_path = sample_root
    monkeypatch.setenv("RAG_ADMIN_API_KEY", "sk-super-secret-do-not-leak")
    out_dir = tmp_path / "out_old"
    client = _RecordingClient()

    code = agent_eval.main(
        [
            "--set", "topics", "--chain", "old", "--out", str(out_dir),
            "--limit", "2",
            "--manifest", str(manifest_path), "--root", str(root),
        ],
        http_client=client,
    )
    assert code == agent_eval.EXIT_OK
    assert len(client.requests) == 2
    for req in client.requests:
        assert req["json"]["session_id"].startswith("backtest_session_")
        # X-API-Key 走 header，⛔ 不落 json body 或 url
        assert "sk-super-secret-do-not-leak" not in json.dumps(req["json"])
        assert "sk-super-secret-do-not-leak" not in req["url"]
        assert req["headers"]["X-API-Key"] == "sk-super-secret-do-not-leak"

    jsonl_rows = [
        json.loads(l)
        for l in (out_dir / "topics.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    dumped = json.dumps(jsonl_rows, ensure_ascii=False)
    assert "sk-super-secret-do-not-leak" not in dumped


def test_old_chain_without_env_key_omits_header(monkeypatch, sample_root, tmp_path):
    root, manifest_path = sample_root
    monkeypatch.delenv("RAG_ADMIN_API_KEY", raising=False)
    out_dir = tmp_path / "out_old_nokey"
    client = _RecordingClient()

    agent_eval.main(
        [
            "--set", "topics", "--chain", "old", "--out", str(out_dir),
            "--limit", "1",
            "--manifest", str(manifest_path), "--root", str(root),
        ],
        http_client=client,
    )
    assert "X-API-Key" not in client.requests[0]["headers"]
