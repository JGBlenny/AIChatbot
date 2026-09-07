"""unit：`tools/agent_eval.py`（spec agentic-mcp-orchestration・任務 4.2→5.x 修訂）。

全部離線：manifest sha 校驗、fake provider 的 agent 鏈、old 鏈用假 httpx
transport（不打真 `:8100`）。⛔ 不呼叫真 OpenAI——`--provider openai` 只在
`OPENAI_API_KEY` 缺席時測「明確拒絕、不觸網」，不測真的建 pool／provider。

覆蓋（任務 brief「完成標準」節，5.x 修訂版）：
- manifest sha 不符 ⇒ 退出碼 3。
- fake provider 跑 topics 前 3 題 ⇒ JSONL 欄位形狀、⛔ 無原文鍵。
- 多輪帶歷史：同一 scenario 的 messages 累積前幾輪內容。
- b2b 身分兩處：`make_agent_identity`／`run_old_chain` body。
- `--set sensitive` 載入：五類各 ≥5、全部 sensitive=True、無重複 q。
- `--repeat N` 聚合：N 倍記錄、聚合形狀。
- `fixed_rate` 只算非敏感非邊界子集、`--chain both` 用同批 old 鏈基準。
- `no_fabrication` 兩鏈同一把尺（forbid_hit）。
- `latency_p95_ms`／`boundary_ok_rate` 形狀。
- 舊鏈固定句比對（`effective_handoff_message`）與關鍵字啟發式旗標。
- 無 `OPENAI_API_KEY` 時明確拒絕、不觸網。
- 硬線判定三態（PASS／FAIL／UNSET）。
- `knowledge_gap_unfilled` 透傳。
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


def _write_sensitive(tmp_path: Path) -> Path:
    classes = ["customer_reference", "pricing", "contract_sla", "compliance", "security"]
    items = []
    for cls in classes:
        for i in range(5):
            items.append(
                {
                    "id": f"sensitive:{cls}:{i}",
                    "q": f"{cls} 測試問法第 {i} 句",
                    "fact_class": cls,
                    "sensitive": True,
                    "expect_kind": "handoff",
                    "must_not_contain": [],
                }
            )
    doc = {"items": items}
    p = tmp_path / "sensitive-v1.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_manifest(tmp_path: Path, topics_path: Path, scenarios_path: Path, *,
                     sensitive_path: Path = None,
                     gap_batches_imported: bool = False, baseline_fixed_rate=None) -> Path:
    sets = {
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
    }
    if sensitive_path is not None:
        sets["sensitive"] = {
            "available": True,
            "path": str(sensitive_path.relative_to(tmp_path)),
            "sha256": _sha(sensitive_path),
        }
    manifest = {
        "gap_batches_imported": gap_batches_imported,
        "sets": sets,
        "baseline": {"fixed_rate": {"value": baseline_fixed_rate}},
    }
    p = tmp_path / "samples-manifest.json"
    p.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.fixture()
def sample_root(tmp_path):
    topics = _write_topics(tmp_path)
    scenarios = _write_scenarios(tmp_path)
    sensitive = _write_sensitive(tmp_path)
    manifest = _write_manifest(tmp_path, topics, scenarios, sensitive_path=sensitive)
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
    "sensitive_expected", "sensitive_leak", "boundary_expected", "boundary_ok",
    "forbid_hit", "forbid_terms_n", "verifier_rejects", "rewrote_ok", "handoff_heuristic",
    "latency_ms", "cost_usd", "knowledge_gap_unfilled", "rep",
    "answer_sha256", "answer_len",
    # DSP-028 新增
    "verifier_reasons", "budget_exhausted",
    # 任務 4.3（knowledge-outline-and-intent-architecture・Plan §3.1）新增：
    # `agent_eval` 有候選 vs 無候選兩臂。
    "candidate_ids", "miss_kind", "candidates_mode", "gold_in_candidates",
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
    # DSP-029a 驗收①⓪：refs 四子成因逐項＋合計單列、POLARITY 單列、known_open 通過數
    for cause in ("ref_invalid", "ref_source_not_found",
                  "ref_ambiguous", "unit_out_of_range"):
        assert f"- {cause}：" in report, cause
    assert "refs 四子成因合計：" in report
    assert "POLARITY_MISMATCH：" in report
    assert "known_open 通過數：" in report
    # DSP-028 監控欄：budget_exhausted 逐批分子/分母 ＋ verifier_reasons 分佈
    assert "DSP-028 監控欄" in report
    assert f"budget_exhausted：" in report and f"/{len(lines)}（agent 鏈" in report
    assert "verifier_reasons 分佈" in report
    # F-2 的 OPEN 監控欄目前算不出來 ⇒ 必須誠實標「待接」，⛔ 不得靜默省略
    assert "整筆免引用的 question／greeting 比例：**待接**" in report


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


def test_provider_openai_without_key_refused_before_any_network(monkeypatch, sample_root, tmp_path):
    """P1 必修 11：無 `OPENAI_API_KEY` ⇒ 明確拒絕、不觸網、不建 pool。

    ⛔ 不 monkeypatch `build_real_runtime` 本身——這條就是要驗證
    `build_real_runtime` 自己在任何 I/O 之前就會擋下來（可注入是為了讓
    *其他* 測試在需要時整支替換掉，不是說這條測試該替換掉它）。
    """
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_openai"
    with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
        agent_eval.main(
            [
                "--set", "topics", "--chain", "agent", "--out", str(out_dir),
                "--provider", "openai",
                "--manifest", str(manifest_path), "--root", str(root),
            ]
        )


@pytest.mark.req("knowledge-outline-and-intent-architecture:4.3")
def test_provider_openai_without_key_refused_before_index_build_too(monkeypatch, sample_root, tmp_path):
    """任務 4.3（Plan §3.1 第二次修正，2026-09-07）：`test_provider_openai_
    without_key_refused_before_any_network`（前一條，逐字未改）只證明
    `SystemExit` 被拋出；本測試是它的姊妹測試，額外用 monkeypatch 計數器證明
    ——CLI 預設 `--candidates on` 缺 key 時，`_build_prospect_index`（會打真的
    embedding 呼叫）**完全沒被呼叫**，key 檢查真的搬到了索引縫之前，⛔ 不是
    「索引先跑完才被 `build_real_runtime` 內部的 key 檢查擋下來」。

    正對照：同一計數器在「有 key＋`--candidates on`」情境下確實是 1
    （為避免真的打 embedding 呼叫，同時把 `_build_prospect_index` 的行為換成
    決定性假後端；`build_real_runtime` 也整支替換掉以免真的連 DB／provider——
    這條分支的重點只在於「key 存在時，索引縫真的會被進到」，不在於驗證
    `build_real_runtime` 本身）。
    """
    real_index_fn = agent_eval._build_prospect_index
    calls = {"n": 0}

    async def _counting(canon=None, *, backend=None):
        calls["n"] += 1
        if backend is None:
            backend = agent_eval._DeterministicBackend()
        return await real_index_fn(canon, backend=backend)

    monkeypatch.setattr(agent_eval, "_build_prospect_index", _counting)

    root, manifest_path = sample_root

    # ── 缺 key：SystemExit 之前，索引縫完全沒被呼叫 ──
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    out_dir = tmp_path / "out_openai_no_key"
    with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
        agent_eval.main(
            [
                "--set", "topics", "--chain", "agent", "--out", str(out_dir),
                "--provider", "openai",
                "--manifest", str(manifest_path), "--root", str(root),
            ]
        )
    assert calls["n"] == 0, "缺 key 時 candidates=on 也不該先打候選索引的 embedding 呼叫"

    # ── 正對照：有 key ⇒ 索引縫確實會被呼叫一次 ──
    calls["n"] = 0
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")

    manifest = agent_eval.load_manifest(manifest_path)
    scenarios = agent_eval.load_samples("scenarios", manifest, root=root, limit=1)

    class _FakeHandle:
        def __init__(self, runtime):
            self.runtime = runtime
            self.outline_doc = None

        async def close(self):
            pass

    async def _fake_build_real_runtime(**kwargs):
        # 這條分支只證「key 存在 ⇒ 索引縫會被呼叫」，不驗證 `build_real_runtime`
        # 本身——整支替換掉，避免真的連 DB／真 provider；仍給一個能真的跑完
        # 一輪的假 runtime，免得後續 `_run_scenario_agent` 對著 `None` 呼叫。
        from services.agent.bootstrap import build_runtime

        provider = agent_eval.ScriptedFakeProvider(scenarios[0].turns)
        registry = agent_eval.build_fake_registry()
        runtime = build_runtime(db_pool=None, provider=provider, registry=registry)
        return _FakeHandle(runtime)

    monkeypatch.setattr(agent_eval, "build_real_runtime", _fake_build_real_runtime)

    records, meta = agent_eval.run_agent_chain(
        scenarios, set_name="scenarios", provider_kind="openai", candidates="on",
    )
    assert calls["n"] == 1
    assert meta["candidates_backend"] == "embedding"


def test_build_real_runtime_is_monkeypatchable(monkeypatch, sample_root, tmp_path):
    """P1 必修 11：`build_real_runtime` 是模組層名稱，可整支替換——
    驗證替換後 `run_agent_chain(provider_kind="openai")` 真的呼叫替身、
    不再要求 `OPENAI_API_KEY`。"""
    root, manifest_path = sample_root
    manifest = agent_eval.load_manifest(manifest_path)
    scenarios = agent_eval.load_samples("scenarios", manifest, root=root, limit=1)

    calls = {"n": 0}

    class _FakeHandle:
        def __init__(self):
            self.runtime = None
            self.outline_doc = None

        async def close(self):
            pass

    async def _fake_build_real_runtime():
        calls["n"] += 1
        from services.agent.bootstrap import build_runtime

        provider = agent_eval.ScriptedFakeProvider(scenarios[0].turns)
        registry = agent_eval.build_fake_registry()
        handle = _FakeHandle()
        handle.runtime = build_runtime(db_pool=None, provider=provider, registry=registry)
        return handle

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(agent_eval, "build_real_runtime", _fake_build_real_runtime)
    records, _meta = agent_eval.run_agent_chain(scenarios, set_name="scenarios", provider_kind="openai")
    assert calls["n"] == 1
    assert len(records) == len(scenarios[0].turns)


# ---------------------------------------------------------------------------
# 3) 多輪帶歷史（P0 必修 2）
# ---------------------------------------------------------------------------


def test_agent_chain_multi_turn_carries_history(sample_root, tmp_path):
    root, manifest_path = sample_root
    manifest = agent_eval.load_manifest(manifest_path)
    scenarios = agent_eval.load_samples("scenarios", manifest, root=root)
    sc = scenarios[0]
    assert len(sc.turns) == 2  # 夾具 S-x 兩輪

    provider = agent_eval.ScriptedFakeProvider(sc.turns)
    registry = agent_eval.build_fake_registry()
    from services.agent.bootstrap import build_runtime

    runtime = build_runtime(db_pool=None, provider=provider, registry=registry)
    identity = agent_eval.make_agent_identity(session_id="test-history")

    import asyncio

    results = asyncio.run(agent_eval._run_scenario_agent(runtime, identity, sc.turns))
    turn1_answer = results[0][1].answer

    calls = provider.async_client.chat.completions.create.__self__.calls
    assert len(calls) >= 2

    def _all_text(messages):
        return "\n".join(str(m.get("content") or "") for m in messages)

    def _last_user_content(messages):
        user_msgs = [m for m in messages if m.get("role") == "user"]
        return str(user_msgs[-1].get("content") or "") if user_msgs else ""

    # A1：第 2 輪呼叫不假設是 calls[1]（重寫迴圈可能多打一次）——改以
    # 「最後一則 user 訊息 == turn2.q」定位，找不到就是機制本身壞了。
    turn2_calls = [c for c in calls if sc.turns[1].q in _last_user_content(c["messages"])]
    assert turn2_calls, "找不到任何一次呼叫的最後一則 user 訊息是第 2 輪問句"
    second_messages = turn2_calls[0]["messages"]
    first_messages = calls[0]["messages"]

    # 第 2 輪的 messages 含第 1 輪的 user 問句
    assert sc.turns[0].q in _all_text(second_messages)
    # 且第 2 輪的最後一則使用者訊息是第 2 輪的 user 句
    assert sc.turns[1].q in _last_user_content(second_messages)
    # 第 2 輪的 messages 含第 1 輪的 assistant 回覆（DSP-022 dialog 歷史）
    assistant_msgs = [m for m in second_messages if m.get("role") == "assistant"]
    assert assistant_msgs, "第 2 輪 messages 應至少有一則 assistant 訊息"
    assert any(str(m.get("content") or "") == turn1_answer for m in assistant_msgs), (
        "第 2 輪應看到第 1 輪的 assistant 回覆內容"
    )
    # 對照組：第 1 輪不該已經含第 2 輪的問句（機制沒把未來的話塞進歷史）
    assert sc.turns[1].q not in _all_text(first_messages)


def test_agent_chain_fake_provider_topics_uses_shared_state_per_scenario(sample_root, tmp_path):
    """對照 run_agent_chain（CLI 完整路徑）也真的貫穿同一個 state——
    用 scenarios（多輪）而非 topics（單輪）跑一次不炸就是最低限度證據，
    真正的訊息內容驗證見上一條單元測試。"""
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_multi"
    code = agent_eval.main(
        [
            "--set", "scenarios", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_OK
    rows = [json.loads(l) for l in (out_dir / "scenarios.jsonl").read_text(encoding="utf-8").strip().splitlines()]
    assert len(rows) == 2  # S-x 兩輪


# ---------------------------------------------------------------------------
# 4) b2b 身分兩處（P0 必修 3）
# ---------------------------------------------------------------------------


def test_make_agent_identity_is_b2b_vendor_1():
    identity = agent_eval.make_agent_identity(session_id="s1")
    assert identity.vendor_id == 1
    assert identity.mode == "b2b"
    assert identity.target_user == "prospect"


def test_run_old_chain_body_is_b2b_vendor_1(sample_root, tmp_path):
    root, manifest_path = sample_root
    manifest = agent_eval.load_manifest(manifest_path)
    scenarios = agent_eval.load_samples("topics", manifest, root=root, limit=1)

    class _Client:
        def __init__(self):
            self.requests = []

        def post(self, url, *, json, headers):
            self.requests.append(json)
            class _R:
                def json(self):
                    return {"answer": "ok", "handoff": None}
            return _R()

    client = _Client()
    agent_eval.run_old_chain(
        scenarios, set_name="topics", base_url="http://x", api_key=None, client=client,
    )
    assert client.requests
    for body in client.requests:
        assert body["vendor_id"] == 1
        assert body["mode"] == "b2b"


# ---------------------------------------------------------------------------
# 5) --set sensitive 載入（P1 必修 4）
# ---------------------------------------------------------------------------


def test_sensitive_manifest_registered(sample_root):
    root, manifest_path = sample_root
    manifest = agent_eval.load_manifest(manifest_path)
    assert agent_eval.sample_available(manifest, "sensitive") is True
    check = agent_eval.verify_manifest(manifest, "sensitive", root=root)
    assert check.ok is True


def test_load_sensitive_v1_each_class_at_least_5_all_sensitive_no_dup(sample_root):
    root, manifest_path = sample_root
    manifest = agent_eval.load_manifest(manifest_path)
    scenarios = agent_eval.load_samples("sensitive", manifest, root=root)
    assert len(scenarios) >= 25

    from collections import Counter

    by_class = Counter(sc.idx.split(":")[1] for sc in scenarios)
    for cls in ("customer_reference", "pricing", "contract_sla", "compliance", "security"):
        assert by_class[cls] >= 5, f"{cls} 樣本數不足 5：{by_class[cls]}"

    qs = [t.q for sc in scenarios for t in sc.turns]
    assert len(qs) == len(set(qs)), "sensitive 樣本存在重複問法"

    assert all(t.sensitive for sc in scenarios for t in sc.turns)
    assert all(t.expect_kind == "handoff" for sc in scenarios for t in sc.turns)


def test_real_sensitive_v1_fixture_meets_spec():
    """對照真正凍結的 `sensitive-v1.json`（非測試夾具），確保正式樣本檔本身
    也符合五類各 ≥5、全 sensitive、無重複的要求（正對照：用真 manifest／真
    樣本路徑跑一次同樣的檢查）。"""
    manifest_path = agent_eval.DEFAULT_MANIFEST_PATH
    manifest = agent_eval.load_manifest(manifest_path)
    root = agent_eval._REPO_ROOT
    check = agent_eval.verify_manifest(manifest, "sensitive", root=root)
    assert check.ok is True, check.mismatches
    scenarios = agent_eval.load_samples("sensitive", manifest, root=root)

    from collections import Counter

    by_class = Counter(sc.idx.split(":")[1] for sc in scenarios)
    for cls in ("customer_reference", "pricing", "contract_sla", "compliance", "security"):
        assert by_class[cls] >= 5
    qs = [t.q for sc in scenarios for t in sc.turns]
    assert len(qs) == len(set(qs))
    assert all(t.sensitive for sc in scenarios for t in sc.turns)


# ---------------------------------------------------------------------------
# 6) --repeat N 聚合（P1 必修 8）
# ---------------------------------------------------------------------------


def test_repeat_n_produces_n_times_records(sample_root, tmp_path):
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_repeat"
    code = agent_eval.main(
        [
            "--set", "scenarios", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake", "--repeat", "3",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_OK
    rows = [json.loads(l) for l in (out_dir / "scenarios.jsonl").read_text(encoding="utf-8").strip().splitlines()]
    assert len(rows) == 2 * 3  # 2 turns × 3 reps
    reps = sorted({r["rep"] for r in rows})
    assert reps == [0, 1, 2]

    summary_path = out_dir / "repeat_summary.json"
    assert summary_path.is_file()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["reps"] == [0, 1, 2]
    assert "forbid_hit_rate" in summary and "answered_rate" in summary
    assert set(summary["forbid_hit_rate"].keys()) == {"mean", "min", "max"}


def test_repeat_default_1_no_summary_file(sample_root, tmp_path):
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_repeat1"
    agent_eval.main(
        [
            "--set", "scenarios", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert not (out_dir / "repeat_summary.json").exists()


def test_repeat_sensitive_zero_leak_any_rep_fails():
    records = [
        agent_eval.EvalRecord(
            set="s", idx="i", turn=0, chain="agent", kind="handoff", answered=False,
            handoff_reason="sensitive_no_grounding", sensitive_expected=True, sensitive_leak=False,
            boundary_ok=None, forbid_hit=False, verifier_rejects=0, latency_ms=1, cost_usd=0.0,
            knowledge_gap_unfilled=False, answer_digest={"sha256": "x", "len": 1}, rep=0,
        ),
        agent_eval.EvalRecord(
            set="s", idx="i", turn=0, chain="agent", kind="answer", answered=True,
            handoff_reason=None, sensitive_expected=True, sensitive_leak=True,
            boundary_ok=None, forbid_hit=False, verifier_rejects=0, latency_ms=1, cost_usd=0.0,
            knowledge_gap_unfilled=False, answer_digest={"sha256": "x", "len": 1}, rep=1,
        ),
    ]
    summary = agent_eval._repeat_summary(records)
    assert summary["sensitive_zero_leak_all_reps_pass"] is False


# ---------------------------------------------------------------------------
# 7) 硬線判定三態 + fixed_rate 子集與同批基準 + no_fabrication 同尺
# ---------------------------------------------------------------------------


def _rec(**kwargs) -> agent_eval.EvalRecord:
    base = dict(
        set="s", idx="i", turn=0, chain="agent", kind="answer", answered=True,
        handoff_reason=None, sensitive_expected=False, sensitive_leak=False,
        boundary_ok=None, forbid_hit=False, verifier_rejects=0, latency_ms=1,
        cost_usd=0.0, knowledge_gap_unfilled=False, answer_digest={"sha256": "x", "len": 1},
        boundary_expected=False, rep=0, rewrote_ok=False, handoff_heuristic=False,
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
        _rec(kind="handoff", forbid_hit=True),  # 非敏感非邊界 ⇒ 進固定句率分母
    ]
    manifest = {"baseline": {"fixed_rate": {"value": 0.0}}}
    h = agent_eval.compute_hardlines(records, manifest)
    assert h["agent"]["sensitive_zero_leak"]["pass"] is False
    assert h["agent"]["sensitive_zero_leak"]["leaks"] == 1
    assert h["agent"]["no_fabrication"]["pass"] is False
    assert h["agent"]["fixed_rate"]["verdict"] == "FAIL"


def test_no_fabrication_uses_forbid_hit_not_verifier_rejects_alone():
    """P1 必修 5：verifier_rejects>0 但 forbid_hit=False（重寫成功、rewrote_ok
    觀測值）⇒ 不再判 FAIL——這是與 4.2 舊行為的明確差異。"""
    records = [_rec(kind="answer", verifier_rejects=1, forbid_hit=False, rewrote_ok=True)]
    manifest = {"baseline": {"fixed_rate": {"value": 1.0}}}
    h = agent_eval.compute_hardlines(records, manifest)
    assert h["agent"]["no_fabrication"]["pass"] is True
    assert h["agent"]["no_fabrication"]["hits"] == 0


def test_hardlines_unset_without_baseline():
    records = [_rec(kind="handoff", sensitive_expected=True)]
    manifest = {"baseline": {"fixed_rate": {"value": None}}}
    h = agent_eval.compute_hardlines(records, manifest)
    assert h["agent"]["fixed_rate"]["verdict"] == "UNSET"
    assert h["agent"]["fixed_rate"]["baseline_source"] == "unset"


def test_fixed_rate_excludes_sensitive_and_boundary_subset():
    records = [
        _rec(kind="answer", sensitive_expected=False, boundary_expected=False),   # 分母內、非固定句
        _rec(kind="handoff", sensitive_expected=False, boundary_expected=False),  # 分母內、固定句
        _rec(kind="handoff", sensitive_expected=True, boundary_expected=False),   # 敏感題，排除
        _rec(kind="handoff", sensitive_expected=False, boundary_expected=True),   # 邊界題，排除
    ]
    manifest = {"baseline": {"fixed_rate": {"value": 1.0}}}
    h = agent_eval.compute_hardlines(records, manifest)
    fr = h["agent"]["fixed_rate"]
    assert fr["n"] == 2
    assert fr["value"] == 0.5  # 1/2


def test_fixed_rate_chain_both_uses_same_batch_old_baseline():
    old_records = [
        _rec(chain="old", kind="answer"),
        _rec(chain="old", kind="handoff"),  # old fixed_rate = 0.5
    ]
    agent_records = [
        _rec(chain="agent", kind="handoff"),
        _rec(chain="agent", kind="handoff"),  # agent fixed_rate = 1.0 > old 0.5 ⇒ FAIL
    ]
    manifest = {"baseline": {"fixed_rate": {"value": 0.0}}}  # 若誤用 manifest 基準會變成 FAIL(0)；此處驗證用的是 old 的 0.5
    h = agent_eval.compute_hardlines(old_records + agent_records, manifest)
    assert h["agent"]["fixed_rate"]["baseline_source"] == "same_batch_old"
    assert h["agent"]["fixed_rate"]["baseline"] == 0.5
    assert h["agent"]["fixed_rate"]["verdict"] == "FAIL"


def test_fixed_rate_agent_only_falls_back_to_manifest_baseline():
    agent_records = [_rec(chain="agent", kind="answer"), _rec(chain="agent", kind="answer")]
    manifest = {"baseline": {"fixed_rate": {"value": 0.9}}}
    h = agent_eval.compute_hardlines(agent_records, manifest)
    assert h["agent"]["fixed_rate"]["baseline_source"] == "manifest_cross_sample"
    assert h["agent"]["fixed_rate"]["baseline"] == 0.9
    assert h["agent"]["fixed_rate"]["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# 8) latency_p95 / boundary_ok_rate / answered_rate / cost_usd 形狀
# ---------------------------------------------------------------------------


def test_supplementary_metrics_shape():
    records = [
        _rec(kind="answer", latency_ms=100, boundary_expected=True, boundary_ok=True, cost_usd=0.001),
        _rec(kind="handoff", latency_ms=200, boundary_expected=True, boundary_ok=False, cost_usd=0.002),
        _rec(kind="answer", latency_ms=300, cost_usd=0.003),
    ]
    manifest = {"baseline": {"fixed_rate": {"value": 1.0}}}
    h = agent_eval.compute_hardlines(records, manifest)
    agent_h = h["agent"]
    assert agent_h["boundary_ok_rate"]["n"] == 2
    assert agent_h["boundary_ok_rate"]["value"] == 0.5
    assert agent_h["latency_p95_ms"]["n"] == 3
    assert agent_h["latency_p95_ms"]["value"] is not None
    assert agent_h["latency_p95_ms"]["note"] is not None  # n<20 ⇒ 樣本不足註記
    assert agent_h["answered_rate"]["n"] == 3
    assert agent_h["cost_usd"]["total"] == pytest.approx(0.006)
    assert agent_h["cost_usd"]["avg"] == pytest.approx(0.002)


def test_boundary_ok_rate_none_when_no_boundary_samples():
    records = [_rec(kind="answer")]
    manifest = {"baseline": {"fixed_rate": {"value": 1.0}}}
    h = agent_eval.compute_hardlines(records, manifest)
    assert h["agent"]["boundary_ok_rate"]["value"] is None
    assert h["agent"]["boundary_ok_rate"]["n"] == 0


# ---------------------------------------------------------------------------
# 9) knowledge_gap_unfilled 透傳
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
# 10) old 鏈：假 httpx transport 驗 session 前綴、header 帶 key 但不外洩字面
# ---------------------------------------------------------------------------


class _FakeHttpResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _RecordingClient:
    """比照真 `httpx.Client` 最小介面：`.post(url, json=..., headers=...)`。"""

    def __init__(self, payload=None):
        self.requests: list[dict] = []
        self._payload = payload or {"answer": "測試回答", "handoff": None}

    def post(self, url, *, json, headers):
        self.requests.append({"url": url, "json": json, "headers": dict(headers)})
        return _FakeHttpResponse(self._payload)


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


def test_old_chain_fixed_message_match_marks_handoff_without_heuristic():
    from services.conversational_config import effective_handoff_message

    fixed_msg = effective_handoff_message(None)
    client = _RecordingClient(payload={"answer": fixed_msg, "handoff": None})
    scenarios = [
        agent_eval.Scenario(idx="fix1", turns=[agent_eval.Turn(turn=0, q="任意問題")]),
    ]
    records = agent_eval.run_old_chain(
        scenarios, set_name="s", base_url="http://x", api_key=None, client=client,
    )
    assert records[0].kind == "handoff"
    assert records[0].handoff_heuristic is False


def test_old_chain_keyword_heuristic_marks_flag_true():
    client = _RecordingClient(payload={"answer": "這個問題請找專人協助", "handoff": None})
    scenarios = [
        agent_eval.Scenario(idx="kw1", turns=[agent_eval.Turn(turn=0, q="任意問題")]),
    ]
    records = agent_eval.run_old_chain(
        scenarios, set_name="s", base_url="http://x", api_key=None, client=client,
    )
    assert records[0].kind == "handoff"
    assert records[0].handoff_heuristic is True


def test_old_chain_structured_handoff_takes_precedence_over_heuristic():
    client = _RecordingClient(payload={"answer": "", "handoff": {"reason": "no_grounding"}})
    scenarios = [
        agent_eval.Scenario(idx="h1", turns=[agent_eval.Turn(turn=0, q="任意問題")]),
    ]
    records = agent_eval.run_old_chain(
        scenarios, set_name="s", base_url="http://x", api_key=None, client=client,
    )
    assert records[0].kind == "handoff"
    assert records[0].handoff_reason == "no_grounding"
    assert records[0].handoff_heuristic is False


# ---------------------------------------------------------------------------
# 11) A2：--dump-texts 原文抽審旁路（預設關）
# ---------------------------------------------------------------------------


def test_dump_texts_default_off_no_texts_dir(sample_root, tmp_path):
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_no_dump"
    code = agent_eval.main(
        [
            "--set", "topics", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake", "--limit", "1",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_OK
    assert not (out_dir / "texts").exists()


def test_dump_texts_on_writes_warning_header_and_raw_text(sample_root, tmp_path):
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_dump"
    code = agent_eval.main(
        [
            "--set", "topics", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake", "--limit", "2", "--dump-texts",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_OK

    texts_path = out_dir / "texts" / "topics.jsonl"
    assert texts_path.is_file()
    lines = texts_path.read_text(encoding="utf-8").strip().splitlines()
    header = json.loads(lines[0])
    assert "_warning" in header
    assert "不進版控" in header["_warning"]
    assert "看完即刪" in header["_warning"]

    body_rows = [json.loads(l) for l in lines[1:]]
    assert len(body_rows) == 2
    for row in body_rows:
        assert set(row.keys()) == {"set", "idx", "turn", "rep", "chain", "q", "answer",
                                   "handoff_reason", "kind", "refs", "attempts"}
        assert isinstance(row["refs"], list)
        assert isinstance(row["attempts"], list)
        # tasks 4.3c：假 provider 輸出的每句都帶 `refs=[]`（見
        # `_fixed_agent_output_for`），但 `attempts` 一定至少有一筆（本回合的
        # 最終嘗試），且該筆的 sentences 形狀齊全。
        assert len(row["attempts"]) >= 1
        last_attempt = row["attempts"][-1]
        assert set(last_attempt.keys()) >= {"attempt", "kind", "sentences", "verdict"}
    # DSP-029a：refs 旁路只放標記字串，⛔ 無 quote 原文
    from tools.agent_eval import _refs_for_dump

    sample = _refs_for_dump(
        [
            {
                "attempt": 1,
                "kind": "answer",
                "sentences": [
                    {"text": "⛔ 這句原文不該被帶出來", "kind": "fact",
                     "refs": ["[aaaa1111bbbb2222:t1:kb:1§2]"]},
                    {"text": "問句沒有引用。", "kind": "question", "refs": []},
                ],
                "verdict": {"ok": True},
            }
        ]
    )
    assert sample == ["[aaaa1111bbbb2222:t1:kb:1§2]"]
    assert _refs_for_dump([]) == []

    # 主 JSONL 的無原文紀律不變（--dump-texts 不影響它）
    main_rows = [
        json.loads(l)
        for l in (out_dir / "topics.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    for row in main_rows:
        assert not (agent_eval._NO_VERBATIM_KEYS & set(row.keys()))


# ---------------------------------------------------------------------------
# 12) A4：--repeat N>1 時 report.md 印「重複跑抖動」比率 mean/min/max
# ---------------------------------------------------------------------------


def test_report_has_repeat_jitter_section_when_repeat_gt_1(sample_root, tmp_path):
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_report_repeat"
    code = agent_eval.main(
        [
            "--set", "scenarios", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake", "--repeat", "2",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_OK
    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "重複跑抖動" in report
    assert "sensitive_zero_leak_all_reps_pass" in report
    for label in ("sensitive_leak_rate", "forbid_hit_rate", "answered_rate", "boundary_ok_rate"):
        assert label in report


def test_report_omits_repeat_jitter_section_when_repeat_1(sample_root, tmp_path):
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_report_norepeat"
    code = agent_eval.main(
        [
            "--set", "scenarios", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_OK
    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "重複跑抖動" not in report


# ---------------------------------------------------------------------------
# 13) A5：sensitive-v1.json 每題 must_not_contain ≥3；forbid_terms_n 透傳；
#     空禁詞集 no_fabrication 附註「無鑑別力」
# ---------------------------------------------------------------------------


def test_real_sensitive_v1_each_item_has_at_least_3_forbid_terms():
    manifest_path = agent_eval.DEFAULT_MANIFEST_PATH
    manifest = agent_eval.load_manifest(manifest_path)
    root = agent_eval._REPO_ROOT
    check = agent_eval.verify_manifest(manifest, "sensitive", root=root)
    assert check.ok is True, check.mismatches
    scenarios = agent_eval.load_samples("sensitive", manifest, root=root)
    for sc in scenarios:
        for t in sc.turns:
            assert len(t.must_not_contain) >= 3, f"{sc.idx} 禁詞數不足 3：{t.must_not_contain}"


def test_no_fabrication_note_when_set_has_no_forbid_terms_at_all():
    records = [
        _rec(kind="answer", forbid_terms_n=0),
        _rec(kind="handoff", forbid_terms_n=0),
    ]
    manifest = {"baseline": {"fixed_rate": {"value": 1.0}}}
    h = agent_eval.compute_hardlines(records, manifest)
    assert h["agent"]["no_fabrication"]["note"] == "本集無禁詞，此欄無鑑別力"


def test_no_fabrication_no_note_when_some_forbid_terms_present():
    records = [
        _rec(kind="answer", forbid_terms_n=0),
        _rec(kind="handoff", forbid_terms_n=3),
    ]
    manifest = {"baseline": {"fixed_rate": {"value": 1.0}}}
    h = agent_eval.compute_hardlines(records, manifest)
    assert h["agent"]["no_fabrication"]["note"] is None


# ---------------------------------------------------------------------------
# 14) A6：--git-head 由呼叫端傳入；main() 的 _git_head(root) 失敗退回
#     _git_head(_REPO_ROOT)
# ---------------------------------------------------------------------------


def test_git_head_override_appears_in_report(sample_root, tmp_path):
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_githead"
    code = agent_eval.main(
        [
            "--set", "topics", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake", "--limit", "1", "--git-head", "deadbeef-fake-sha",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_OK
    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "deadbeef-fake-sha" in report


def _fake_subprocess_run_keyed_by_cwd(success_cwds: dict) -> "callable":
    """回傳一個可取代 `subprocess.run` 的替身：`cwd` 命中 `success_cwds` 的
    key 就回傳該值當 `stdout`（returncode=0），否則模擬「非 git repo」
    （returncode!=0）。⛔ 不依賴容器內是否真的裝了 `git` 執行檔——本容器
    實測 `git` 不存在（`FileNotFoundError: 'git'`），拿真 git 當正對照組
    在這個環境本身就不成立，量的是環境缺工具、不是 fallback 邏輯本身。"""
    import subprocess as _subprocess

    def _fake_run(args, cwd=None, capture_output=None, text=None, timeout=None):
        key = str(cwd)
        if key in success_cwds:
            return _subprocess.CompletedProcess(args, 0, stdout=success_cwds[key] + "\n", stderr="")
        return _subprocess.CompletedProcess(args, 128, stdout="", stderr="fatal: not a git repository")

    return _fake_run


def test_git_head_returns_empty_when_git_reports_non_repo(monkeypatch, tmp_path):
    monkeypatch.setattr("subprocess.run", _fake_subprocess_run_keyed_by_cwd({}))
    assert agent_eval._git_head(tmp_path) == ""


def test_git_head_returns_sha_when_git_succeeds(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "subprocess.run", _fake_subprocess_run_keyed_by_cwd({str(tmp_path): "cafef00d"})
    )
    assert agent_eval._git_head(tmp_path) == "cafef00d"


def test_main_falls_back_to_repo_root_git_head_when_root_not_a_repo(monkeypatch, sample_root, tmp_path):
    """A6：`main()` 用 `_git_head(root)` 失敗（root 非 repo）時退回
    `_git_head(_REPO_ROOT)`。`root`（`sample_root` 夾具的 tmp_path）模擬非
    repo；`_REPO_ROOT` 換成一個「git 會成功」的假 cwd，驗證 report 印出的是
    後者的 HEAD，證明真的走了 fallback 分支而非巧合印出兩者皆空。"""
    root, manifest_path = sample_root
    fake_repo_root = tmp_path / "fake_repo_root_cwd"
    expected_head = "deadfeed0001"
    monkeypatch.setattr(
        "subprocess.run",
        _fake_subprocess_run_keyed_by_cwd({str(fake_repo_root): expected_head}),
    )
    monkeypatch.setattr(agent_eval, "_REPO_ROOT", fake_repo_root)

    out_dir = tmp_path / "out_fallback"
    code = agent_eval.main(
        [
            "--set", "topics", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake", "--limit", "1",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_OK
    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert agent_eval._git_head(root) == "", "前提不成立：root 這次應該模擬成非 repo"
    assert expected_head in report


# ---------------------------------------------------------------------------
# 15) 任務 4.3（knowledge-outline-and-intent-architecture・Plan §3.4）：
#     `agent_eval` 有候選 vs 無候選兩臂
# ---------------------------------------------------------------------------

_REQ_4_3 = "knowledge-outline-and-intent-architecture:4.3"


@pytest.mark.req(_REQ_4_3)
def test_candidates_off_every_row_has_no_candidate_mechanism(sample_root, tmp_path):
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_cand_off"
    code = agent_eval.main(
        [
            "--set", "topics", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake", "--candidates", "off", "--limit", "3",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_OK
    rows = [json.loads(l) for l in (out_dir / "topics.jsonl").read_text(encoding="utf-8").strip().splitlines()]
    assert rows
    for row in rows:
        assert row["candidates_mode"] == "off"
        assert row["miss_kind"] is None
        assert row["candidate_ids"] == []


@pytest.mark.req(_REQ_4_3)
def test_candidates_on_hit_rows_have_bounded_candidate_ids_and_clean_report(sample_root, tmp_path):
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_cand_on"
    code = agent_eval.main(
        [
            "--set", "topics", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake", "--candidates", "on", "--limit", "3",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_OK
    rows = [json.loads(l) for l in (out_dir / "topics.jsonl").read_text(encoding="utf-8").strip().splitlines()]
    assert rows
    for row in rows:
        assert row["candidates_mode"] == "on"
        assert row["miss_kind"] in {"hit", "none_visible", "index_unavailable"}
    hit_rows = [r for r in rows if r["miss_kind"] == "hit"]
    assert hit_rows, "prospect 身分下應至少一列 hit（真正本應有可見已審細目）"
    for r in hit_rows:
        assert 1 <= len(r["candidate_ids"]) <= 5

    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "## candidates" in report
    assert "candidates_mode：`on`（production 組態）" in report
    assert f"candidate_fallback：0/{len(rows)}" in report
    assert f"candidate_selector_error：0/{len(rows)}" in report


class _RaisingQueryBackend:
    """任務 4.3 §3.4-1 正對照 (a)：索引已 `prepare` 成功，但**查詢時**的後端
    呼叫一律 raise——`CandidateSelector._embed_query` 會接住並回 `None`，
    走 `sel is None` 的降級路徑（`candidate_fallback_full_outline`）。"""

    async def embed(self, texts):
        raise RuntimeError("query embed failure（測試用，模擬後端在查詢時故障）")


@pytest.mark.req(_REQ_4_3)
def test_candidates_on_query_backend_raise_marks_fallback_not_selector_error(monkeypatch, sample_root, tmp_path):
    real_build_selector = agent_eval._build_fake_candidate_selector

    async def _selector_with_raising_query_backend():
        selector = await real_build_selector()
        # `CandidateSelector.select` 對查詢用後端有獨立覆寫欄位（`backend=`
        # 建構參數），索引本身已用可用的決定性後端 prepare 過——只有查詢這一步
        # 之後會故障，模擬「索引沒事、embedding 服務這次掛了」。
        selector._backend = _RaisingQueryBackend()
        return selector

    monkeypatch.setattr(agent_eval, "_build_fake_candidate_selector", _selector_with_raising_query_backend)

    root, manifest_path = sample_root
    out_dir = tmp_path / "out_cand_backend_raise"
    code = agent_eval.main(
        [
            "--set", "topics", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake", "--candidates", "on", "--limit", "3",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_OK
    rows = [json.loads(l) for l in (out_dir / "topics.jsonl").read_text(encoding="utf-8").strip().splitlines()]
    n = len(rows)
    for row in rows:
        assert row["miss_kind"] == "index_unavailable"
        assert row["candidate_ids"] == []
    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert f"candidate_fallback：{n}/{n}" in report
    assert f"candidate_selector_error：0/{n}" in report


@pytest.mark.req(_REQ_4_3)
def test_candidates_on_selector_select_raise_marks_selector_error_not_fallback(monkeypatch, sample_root, tmp_path):
    from services.agent.canon.candidate_selector import CandidateSelector

    async def _raise_select(self, doc, identity, query, *, vendor_business_types=frozenset()):
        raise RuntimeError("selector.select 故障（測試用）")

    monkeypatch.setattr(CandidateSelector, "select", _raise_select)

    root, manifest_path = sample_root
    out_dir = tmp_path / "out_cand_selector_raise"
    code = agent_eval.main(
        [
            "--set", "topics", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake", "--candidates", "on", "--limit", "3",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_OK
    rows = [json.loads(l) for l in (out_dir / "topics.jsonl").read_text(encoding="utf-8").strip().splitlines()]
    n = len(rows)
    for row in rows:
        assert row["miss_kind"] == "index_unavailable"
        assert row["candidate_ids"] == []
    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert f"candidate_selector_error：{n}/{n}" in report
    assert f"candidate_fallback：0/{n}" in report


# ---------------------------------------------------------------------------
# 16) --set outline-probe（4.4 步 2 探針凍結前佔位；本片只接 loader＋manifest）
# ---------------------------------------------------------------------------


def _write_outline_probe(tmp_path: Path) -> Path:
    doc = {
        "_meta": {"rule_sha256": "deadbeef00", "frozen_at": "2026-09-07T00:00:00Z", "n": 2},
        "items": [
            {
                "id": "op:1", "q": "系統會怎麼收費", "stratum": "general",
                "gold": ["prospect/Z/does-not-exist"], "expect_kind": "answer",
            },
            {
                "id": "op:2", "q": "有沒有客戶名單可以看", "stratum": "sensitive",
                "gold": [], "expect_kind": "handoff",
            },
        ],
    }
    p = tmp_path / "outline-probe-v1.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


def _write_manifest_with_outline_probe(
    tmp_path: Path, topics_path: Path, scenarios_path: Path, outline_probe_path: Path,
) -> Path:
    manifest_path = _write_manifest(tmp_path, topics_path, scenarios_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sets"]["outline-probe"] = {
        "available": True,
        "path": str(outline_probe_path.relative_to(tmp_path)),
        "sha256": _sha(outline_probe_path),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return manifest_path


@pytest.mark.req(_REQ_4_3)
def test_outline_probe_manifest_unavailable_exits_4(sample_root, tmp_path):
    """預設 `sample_root` 夾具的 manifest 未登記 `outline-probe`（等同
    `available=false`）——與正式 `samples-manifest.json` 的實際佔位一致。"""
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_op_unavail"
    code = agent_eval.main(
        [
            "--set", "outline-probe", "--chain", "agent", "--out", str(out_dir),
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_SAMPLE_UNAVAILABLE


@pytest.mark.req(_REQ_4_3)
def test_outline_probe_runs_and_gold_in_candidates_is_bool(tmp_path):
    topics = _write_topics(tmp_path)
    scenarios = _write_scenarios(tmp_path)
    outline_probe = _write_outline_probe(tmp_path)
    manifest_path = _write_manifest_with_outline_probe(tmp_path, topics, scenarios, outline_probe)

    out_dir = tmp_path / "out_op_run"
    code = agent_eval.main(
        [
            "--set", "outline-probe", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake", "--candidates", "on",
            "--manifest", str(manifest_path), "--root", str(tmp_path),
        ]
    )
    assert code == agent_eval.EXIT_OK
    rows = [
        json.loads(l)
        for l in (out_dir / "outline-probe.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    assert len(rows) == 2
    with_gold = [r for r in rows if r["idx"] == "op:1"]
    assert with_gold and isinstance(with_gold[0]["gold_in_candidates"], bool)
    without_gold = [r for r in rows if r["idx"] == "op:2"]
    assert without_gold and without_gold[0]["gold_in_candidates"] is None


@pytest.mark.req(_REQ_4_3)
def test_outline_probe_sha_mismatch_exits_3(tmp_path):
    topics = _write_topics(tmp_path)
    scenarios = _write_scenarios(tmp_path)
    outline_probe = _write_outline_probe(tmp_path)
    manifest_path = _write_manifest_with_outline_probe(tmp_path, topics, scenarios, outline_probe)

    # 竄改樣本內容（模擬「看過結果後改樣本」）——sha 與 manifest 記錄的不再相符。
    doc = json.loads(outline_probe.read_text(encoding="utf-8"))
    doc["items"].append(
        {"id": "op:3", "q": "額外題", "stratum": "general", "gold": [], "expect_kind": "answer"}
    )
    outline_probe.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")

    out_dir = tmp_path / "out_op_sha"
    code = agent_eval.main(
        [
            "--set", "outline-probe", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake",
            "--manifest", str(manifest_path), "--root", str(tmp_path),
        ]
    )
    assert code == agent_eval.EXIT_SAMPLES_CHANGED


# ---------------------------------------------------------------------------
# 17) 真 provider 路徑：`--candidates on` 索引未就緒 ⇒ exit 5；正對照 ⇒ 0
# ---------------------------------------------------------------------------


class _AlwaysNoneQueryEmbedBackend:
    """`FineIndex.prepare` 對每個文字都拿到 `None` ⇒ 索引整份丟成 `not_ready`
    （見 `services/agent/canon/fine_index.py` 模組層行為：任一鍵失敗就整份丟）。"""

    async def embed(self, texts):
        return [None for _ in texts]


class _FakeRealRuntimeHandle:
    def __init__(self, runtime):
        self.runtime = runtime
        self.outline_doc = None

    async def close(self) -> None:
        pass


def _install_fake_build_real_runtime(monkeypatch, scenarios):
    # ⚠️ 接受 `**kwargs`（而非零參數）：`candidates=="on"` 時
    # `_run_agent_chain_openai` 會以 `candidate_selector=...` 呼叫
    # `build_real_runtime`（Plan §3.1 修訂——selector 必須真的接進 runtime）。
    async def _fake_build_real_runtime(**kwargs):
        from services.agent.bootstrap import build_runtime

        provider = agent_eval.ScriptedFakeProvider(scenarios[0].turns)
        registry = agent_eval.build_fake_registry()
        runtime = build_runtime(db_pool=None, provider=provider, registry=registry)
        return _FakeRealRuntimeHandle(runtime)

    # 2026-09-07 二次修正：`candidates=="on"` 分支在呼叫候選索引縫之前會先過
    # `_require_openai_key()`——這個助手函式的呼叫端是在測候選索引／selector
    # 接線，不是在測 key 檢查本身，給一個假 key 讓它過關（`build_real_runtime`
    # 本身整支被替換掉，不會真的用這個 key 連線）。
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    monkeypatch.setattr(agent_eval, "build_real_runtime", _fake_build_real_runtime)


@pytest.mark.req(_REQ_4_3)
def test_real_provider_candidates_on_index_not_ready_exits_5_no_jsonl(monkeypatch, sample_root, tmp_path):
    """§3.4-4：不設 `OPENAI_API_KEY`、不觸網、不觸 DB——`build_real_runtime` 替身
    只為越過 key 檢查／pool，⛔ 不發 exit、⛔ 不登記 canon；exit 由受測的
    `_run_agent_chain_openai`／`main` 發出。注入永遠回 `None` 的假後端 ⇒
    候選索引 `prepare` 後留在 `not_ready` ⇒ `IndexNotReady` ⇒ exit 5、無 JSONL。"""
    root, manifest_path = sample_root
    manifest = agent_eval.load_manifest(manifest_path)
    scenarios = agent_eval.load_samples("scenarios", manifest, root=root, limit=1)
    _install_fake_build_real_runtime(monkeypatch, scenarios)

    real_build_index = agent_eval._build_prospect_index

    async def _stub_index_not_ready(canon=None, *, backend=None):
        return await real_build_index(canon, backend=_AlwaysNoneQueryEmbedBackend())

    monkeypatch.setattr(agent_eval, "_build_prospect_index", _stub_index_not_ready)

    out_dir = tmp_path / "out_real_notready"
    code = agent_eval.main(
        [
            "--set", "scenarios", "--chain", "agent", "--out", str(out_dir),
            "--provider", "openai", "--candidates", "on",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_INDEX_NOT_READY
    assert code == 5
    assert not (out_dir / "scenarios.jsonl").exists()
    assert not (out_dir / "report.md").exists()


@pytest.mark.req(_REQ_4_3)
def test_real_provider_candidates_on_index_ready_exits_0_writes_jsonl(monkeypatch, sample_root, tmp_path):
    """正對照：同一注入點（`_build_prospect_index`）換一個可用的決定性假後端
    ⇒ 索引 `ready` ⇒ 正常跑完、回傳 0、JSONL 寫出、report 標
    `candidates_backend` 為 `embedding`（真 provider 路徑值域）。"""
    root, manifest_path = sample_root
    manifest = agent_eval.load_manifest(manifest_path)
    scenarios = agent_eval.load_samples("scenarios", manifest, root=root, limit=1)
    _install_fake_build_real_runtime(monkeypatch, scenarios)

    real_build_index = agent_eval._build_prospect_index

    async def _stub_index_ready(canon=None, *, backend=None):
        return await real_build_index(canon, backend=agent_eval._DeterministicBackend())

    monkeypatch.setattr(agent_eval, "_build_prospect_index", _stub_index_ready)

    out_dir = tmp_path / "out_real_ready"
    code = agent_eval.main(
        [
            "--set", "scenarios", "--chain", "agent", "--out", str(out_dir),
            "--provider", "openai", "--candidates", "on",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_OK
    assert (out_dir / "scenarios.jsonl").is_file()
    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "candidates_backend：`embedding`" in report


@pytest.mark.req(_REQ_4_3)
def test_real_provider_on_arm_actually_wires_candidate_selector_into_runtime(monkeypatch, sample_root, tmp_path):
    """Plan §3.4-4b（2026-09-07 修正）：真 provider `on` 臂必須真的把
    `CandidateSelector` 接進 `build_real_runtime`，⛔ 不能只做就緒閘門。

    - `on`：替身捕捉到的 `candidate_selector` 是 `CandidateSelector`，其 `.index`
      與縫（`_build_prospect_index`）回傳的索引物件是同一個（`is`）。
    - `off`：替身捕捉到的 `candidate_selector` 為 `None`。
    - 索引未就緒：`IndexNotReady` 在 `build_real_runtime` **被呼叫之前**拋出
      ——替身呼叫次數為 0（正對照：就緒時替身確實被呼叫一次）。
    """
    from services.agent.canon.candidate_selector import CandidateSelector

    root, manifest_path = sample_root
    manifest = agent_eval.load_manifest(manifest_path)
    scenarios = agent_eval.load_samples("scenarios", manifest, root=root, limit=1)

    real_build_index = agent_eval._build_prospect_index
    captured_index: dict = {}

    async def _stub_index_ready(canon=None, *, backend=None):
        index = await real_build_index(canon, backend=agent_eval._DeterministicBackend())
        captured_index["index"] = index
        return index

    async def _stub_index_not_ready(canon=None, *, backend=None):
        class _AlwaysNoneBackend:
            async def embed(self, texts):
                return [None for _ in texts]

        return await real_build_index(canon, backend=_AlwaysNoneBackend())

    build_calls: list[dict] = []

    def _install_capturing_stub():
        async def _capturing_build_real_runtime(**kwargs):
            build_calls.append(kwargs)
            from services.agent.bootstrap import build_runtime

            provider = agent_eval.ScriptedFakeProvider(scenarios[0].turns)
            registry = agent_eval.build_fake_registry()
            handle = _FakeRealRuntimeHandle(
                build_runtime(
                    db_pool=None, provider=provider, registry=registry,
                    candidate_selector=kwargs.get("candidate_selector"),
                )
            )
            return handle

        # 2026-09-07 二次修正：`candidates=="on"` 分支呼叫索引縫之前會先過
        # `_require_openai_key()`——這裡測的是 selector 接線，不是 key 檢查，
        # 給假 key 讓它過關（`build_real_runtime` 整支被替換，不會真的連線）。
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
        monkeypatch.setattr(agent_eval, "build_real_runtime", _capturing_build_real_runtime)

    # ── on：selector 真的接進去，且 .index 是縫回傳的同一物件 ──
    _install_capturing_stub()
    monkeypatch.setattr(agent_eval, "_build_prospect_index", _stub_index_ready)
    build_calls.clear()
    records_on, meta_on = agent_eval.run_agent_chain(
        scenarios, set_name="scenarios", provider_kind="openai", candidates="on",
    )
    assert len(build_calls) == 1
    selector = build_calls[0].get("candidate_selector")
    assert isinstance(selector, CandidateSelector)
    assert selector.index is captured_index["index"]
    assert meta_on["candidates_backend"] == "embedding"

    # ── off：candidate_selector 為 None（或未傳，等同 None）──
    build_calls.clear()
    records_off, meta_off = agent_eval.run_agent_chain(
        scenarios, set_name="scenarios", provider_kind="openai", candidates="off",
    )
    assert len(build_calls) == 1
    assert build_calls[0].get("candidate_selector") is None

    # ── 索引未就緒：build_real_runtime 完全不被呼叫（計數 0）──
    monkeypatch.setattr(agent_eval, "_build_prospect_index", _stub_index_not_ready)
    build_calls.clear()
    with pytest.raises(agent_eval.IndexNotReady):
        agent_eval.run_agent_chain(
            scenarios, set_name="scenarios", provider_kind="openai", candidates="on",
        )
    assert len(build_calls) == 0


@pytest.mark.req(_REQ_4_3)
def test_no_candidates_related_env_reads_in_agent_eval():
    """§3.4-5：`tools/agent_eval.py` 不得有任何讀取 candidates 相關 `os.environ`
    的程式碼（⛔ 這是評估專用依賴注入，不是線上開關）。"""
    src = Path(agent_eval.__file__).read_text(encoding="utf-8")
    for lineno, line in enumerate(src.splitlines(), start=1):
        if "os.environ" in line or "os.getenv" in line:
            assert "candidate" not in line.lower(), f"line {lineno}: {line}"


@pytest.mark.req(_REQ_4_3)
def test_build_prospect_index_not_called_when_candidates_off(monkeypatch, sample_root, tmp_path):
    """§3.4-6（2026-09-07 修正版）：`_build_prospect_index` 只在
    `candidates=="on"` 時被呼叫——`off` 臂（無論走 `main()` 的 `--candidates off`
    或函式層直呼不帶 `candidates` 參數的預設值）一律不建索引；正對照：
    `on` 路徑（無論走哪個入口）確實會呼叫恰好一次。

    ⚠️ 與本測試上一版的差異（記在這裡，供下一個 session 對照）：Plan §3.1
    2026-09-07 執行中修正之前，`_run_agent_chain_openai` 是「先呼叫
    `build_real_runtime`（含 OPENAI_API_KEY 檢查），之後才呼叫候選索引縫」，
    所以 `--provider openai` 不給 `--candidates`（CLI 預設 `on`）＋缺 key 的
    `test_provider_openai_without_key_refused_before_any_network` 情境下，
    索引縫從未被呼叫。修正後索引縫**先於** `build_real_runtime`（selector
    才接得進 runtime，見 §3.4-4b），於是同一情境下 `_build_prospect_index`
    **會**被呼叫一次（本機環境有可連得到的 embedding 服務，索引順利建成
    `ready`，接著才進 `build_real_runtime` 因缺 key 拋出預期的
    `SystemExit`）——這是修正後的預期行為、⛔ 不是迴歸：`build_real_runtime`
    自身「缺 key 之前不連 OpenAI／不建 DB」的承諾不受影響（那兩件事仍然
    在其函式內部、在任何 I/O 之前就檢查），只是「有沒有先做候選索引縫」
    這件事本身就是 `--candidates on` 的定義。真正該守住的不變量因此改寫成
    「`off` 臂／函式層預設一律不建索引」，見下方斷言。"""
    calls = {"n": 0}
    real_index_fn = agent_eval._build_prospect_index

    async def _counting(canon=None, *, backend=None):
        calls["n"] += 1
        if backend is None:
            # 正對照分支才會真的走到這裡——注入決定性假後端，⛔ 不連真 embedding 服務。
            backend = agent_eval._DeterministicBackend()
        return await real_index_fn(canon, backend=backend)

    monkeypatch.setattr(agent_eval, "_build_prospect_index", _counting)

    root, manifest_path = sample_root

    # ── main()：明確 `--candidates off`（無論 key 有沒有設）一律不建索引 ──
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    calls["n"] = 0
    with pytest.raises(SystemExit, match="OPENAI_API_KEY"):
        agent_eval.main(
            [
                "--set", "topics", "--chain", "agent", "--out", str(tmp_path / "o1"),
                "--provider", "openai", "--candidates", "off",
                "--manifest", str(manifest_path), "--root", str(root),
            ]
        )
    assert calls["n"] == 0, "--candidates off ⇒ 缺 key 拒絕前不該建候選索引"

    # ── 函式層直呼（等價於 test_build_real_runtime_is_monkeypatchable）：
    #    `run_agent_chain(provider_kind="openai")` 不帶 `candidates` ⇒
    #    函式層預設 "off" ⇒ 不建索引。
    manifest = agent_eval.load_manifest(manifest_path)
    scenarios = agent_eval.load_samples("scenarios", manifest, root=root, limit=1)

    class _FakeHandle:
        def __init__(self):
            self.runtime = None
            self.outline_doc = None

        async def close(self):
            pass

    async def _fake_build_real_runtime(**kwargs):
        from services.agent.bootstrap import build_runtime

        provider = agent_eval.ScriptedFakeProvider(scenarios[0].turns)
        registry = agent_eval.build_fake_registry()
        handle = _FakeHandle()
        handle.runtime = build_runtime(db_pool=None, provider=provider, registry=registry)
        return handle

    monkeypatch.setattr(agent_eval, "build_real_runtime", _fake_build_real_runtime)
    calls["n"] = 0
    records, _meta = agent_eval.run_agent_chain(scenarios, set_name="scenarios", provider_kind="openai")
    assert calls["n"] == 0, "函式層預設 off ⇒ 不該呼叫 _build_prospect_index"

    # ── 正對照：`candidates="on"` 路徑（無論哪個入口）確實會呼叫恰好一次 ──
    # （`on` 分支現在會先過 `_require_openai_key()` 才呼叫索引縫——見
    # 2026-09-07 二次修正——這裡不是測 key 檢查本身，故給一個假 key 讓它過關。）
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    calls["n"] = 0
    records2, meta2 = agent_eval.run_agent_chain(
        scenarios, set_name="scenarios", provider_kind="openai", candidates="on",
    )
    assert calls["n"] == 1
    assert meta2["candidates_backend"] == "embedding"


# ---------------------------------------------------------------------------
# 18) `--chain both --candidates off`：old 鏈列也是 28 鍵、candidates_mode="off"
# ---------------------------------------------------------------------------


@pytest.mark.req(_REQ_4_3)
def test_chain_both_candidates_off_old_rows_28_keys_backend_none(sample_root, tmp_path):
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_both_off"
    client = _RecordingClient()
    code = agent_eval.main(
        [
            "--set", "topics", "--chain", "both", "--out", str(out_dir),
            "--provider", "fake", "--candidates", "off", "--limit", "2",
            "--manifest", str(manifest_path), "--root", str(root),
        ],
        http_client=client,
    )
    assert code == agent_eval.EXIT_OK
    rows = [json.loads(l) for l in (out_dir / "topics.jsonl").read_text(encoding="utf-8").strip().splitlines()]
    assert rows
    old_rows = [r for r in rows if r["chain"] == "old"]
    assert old_rows
    for row in rows:
        assert set(row.keys()) == _EXPECTED_JSONL_KEYS
        assert row["candidates_mode"] == "off"
    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "candidates_backend：`none`" in report


@pytest.mark.req(_REQ_4_3)
def test_chain_agent_only_candidates_on_backend_is_fake(sample_root, tmp_path):
    root, manifest_path = sample_root
    out_dir = tmp_path / "out_on_fake_backend"
    code = agent_eval.main(
        [
            "--set", "topics", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake", "--candidates", "on", "--limit", "1",
            "--manifest", str(manifest_path), "--root", str(root),
        ]
    )
    assert code == agent_eval.EXIT_OK
    report = (out_dir / "report.md").read_text(encoding="utf-8")
    assert "candidates_backend：`fake`" in report


# ---------------------------------------------------------------------------
# 19) `load_outline_probe_v1` 多輪 item 支援（4.4b 前置改動，tasks 4.4；
#     Plan §2「4.4b 前置改動」——F 層一個劇本一個 item、`turns[]` 各自
#     `gold_fine_ids`／`expect_kind`，同一個 `Scenario` 貫穿）
# ---------------------------------------------------------------------------

_REQ_4_4 = "knowledge-outline-and-intent-architecture:4.4"


def _write_outline_probe_multi_turn(tmp_path: Path) -> Path:
    """一個多輪 item（F 層劇本，2 turn）＋一個單輪 item（既有行為不變的正對照）。"""
    doc = {
        "_meta": {"rule_sha256": "deadbeef01", "frozen_at": "2026-09-07T00:00:00Z", "n": 2},
        "items": [
            {
                "id": "F-S1-landlord", "stratum": "multi",
                "turns": [
                    {"turn": 1, "q": "我有 12 戶要管理", "gold": ["prospect/A/scale"], "expect_kind": "answer"},
                    {"turn": 2, "q": "那可以線上簽約嗎", "gold": ["prospect/C/sign"], "expect_kind": "answer"},
                ],
            },
            {
                "id": "A-01", "q": "系統會怎麼收費", "stratum": "answerable_unanswered",
                "gold": ["prospect/Z/pricing"], "expect_kind": "answer",
            },
        ],
    }
    p = tmp_path / "outline-probe-multi-v1.json"
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.mark.req(_REQ_4_4)
def test_load_outline_probe_v1_multi_turn_item_yields_one_scenario(tmp_path):
    """正對照（Plan §2「4.4b 前置改動」驗收）：把 loader 改回『每個 item 只造
    單輪 `Scenario`』（即把 `turns[]` 拆成 N 個 scenario）會讓這條斷言必紅——
    這裡先證明「舊行為會產生 N 個 scenario」這件事本身是可觀測的（用該 item
    的 turn 數手動驗證），再證明新 loader 只產生 1 個。"""
    path = _write_outline_probe_multi_turn(tmp_path)
    manifest = {"sets": {"outline-probe": {"available": True}}}
    scenarios = agent_eval.load_outline_probe_v1(path, manifest)

    multi_scenarios = [sc for sc in scenarios if sc.idx == "F-S1-landlord"]
    assert len(multi_scenarios) == 1, "新 loader：一個 turns[] item 只造 1 個 Scenario"
    sc = multi_scenarios[0]
    assert len(sc.turns) == 2, "該 Scenario 內含 N 個 Turn（舊行為會是 N 個各 1-turn 的 Scenario）"
    assert [t.turn for t in sc.turns] == [1, 2]
    assert sc.turns[0].gold_fine_ids == ("prospect/A/scale",)
    assert sc.turns[1].gold_fine_ids == ("prospect/C/sign",)
    assert sc.turns[0].expect_kind == "answer" and sc.turns[1].expect_kind == "answer"

    # 單輪 item 行為不變（正對照：既有單輪路徑沒被多輪改動波及）
    single_scenarios = [sc for sc in scenarios if sc.idx == "A-01"]
    assert len(single_scenarios) == 1
    assert len(single_scenarios[0].turns) == 1
    assert single_scenarios[0].turns[0].gold_fine_ids == ("prospect/Z/pricing",)

    assert len(scenarios) == 2, "2 個 item ⇒ 2 個 Scenario（⛔ 不是 3——舊行為會把多輪拆成額外 scenario）"


@pytest.mark.req(_REQ_4_4)
def test_load_outline_probe_v1_multi_turn_sensitive_stratum_forces_handoff(tmp_path):
    doc = {
        "_meta": {"rule_sha256": "x", "frozen_at": "t", "n": 1},
        "items": [
            {
                "id": "D-multi-01", "stratum": "sensitive",
                "turns": [
                    {"turn": 1, "q": "有沒有客戶名單", "gold": [], "expect_kind": "answer"},
                ],
            },
        ],
    }
    path = tmp_path / "outline-probe-sensitive-multi.json"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    scenarios = agent_eval.load_outline_probe_v1(path, {"sets": {}})
    assert len(scenarios) == 1
    t = scenarios[0].turns[0]
    assert t.sensitive is True
    assert t.expect_kind == "handoff"  # sensitive 覆寫，⛔ 不理會 item 裡的 "answer"


@pytest.mark.req(_REQ_4_4)
def test_outline_probe_multi_turn_fake_provider_same_idx_turn_increases(tmp_path):
    """`--provider fake` 跑一輪：同劇本各 turn 的 `idx` 相同且 `turn` 遞增
    （沿 `test_agent_chain_multi_turn_carries_history` 的驗收慣例）。"""
    topics = _write_topics(tmp_path)
    scenarios_v1 = _write_scenarios(tmp_path)
    outline_probe = _write_outline_probe_multi_turn(tmp_path)
    manifest_path = _write_manifest_with_outline_probe(tmp_path, topics, scenarios_v1, outline_probe)

    out_dir = tmp_path / "out_op_multi"
    code = agent_eval.main(
        [
            "--set", "outline-probe", "--chain", "agent", "--out", str(out_dir),
            "--provider", "fake",
            "--manifest", str(manifest_path), "--root", str(tmp_path),
        ]
    )
    assert code == agent_eval.EXIT_OK
    rows = [
        json.loads(l)
        for l in (out_dir / "outline-probe.jsonl").read_text(encoding="utf-8").strip().splitlines()
    ]
    multi_rows = sorted((r for r in rows if r["idx"] == "F-S1-landlord"), key=lambda r: r["turn"])
    assert len(multi_rows) == 2
    assert [r["idx"] for r in multi_rows] == ["F-S1-landlord", "F-S1-landlord"]
    assert [r["turn"] for r in multi_rows] == [1, 2]


@pytest.mark.req(_REQ_4_4)
def test_outline_probe_multi_turn_second_call_messages_carry_turn1_history(tmp_path):
    """第 2 次 `create()` 的 `messages` 最後一則 user＝turn2 的 q、前文含 turn1 的
    q／answer（沿 `test_agent_chain_multi_turn_carries_history` 的定位手法：
    ⛔ 不假設是 `calls[1]`——重寫迴圈可能多打一次）。"""
    path = _write_outline_probe_multi_turn(tmp_path)
    scenarios = agent_eval.load_outline_probe_v1(path, {"sets": {}})
    sc = next(s for s in scenarios if s.idx == "F-S1-landlord")
    assert len(sc.turns) == 2

    provider = agent_eval.ScriptedFakeProvider(sc.turns)
    registry = agent_eval.build_fake_registry()
    from services.agent.bootstrap import build_runtime

    runtime = build_runtime(db_pool=None, provider=provider, registry=registry)
    identity = agent_eval.make_agent_identity(session_id="test-outline-probe-history")

    import asyncio

    results = asyncio.run(agent_eval._run_scenario_agent(runtime, identity, sc.turns))
    turn1_answer = results[0][1].answer

    calls = provider.async_client.chat.completions.create.__self__.calls

    def _last_user_content(messages):
        user_msgs = [m for m in messages if m.get("role") == "user"]
        return str(user_msgs[-1].get("content") or "") if user_msgs else ""

    def _all_text(messages):
        return "\n".join(str(m.get("content") or "") for m in messages)

    turn2_calls = [c for c in calls if sc.turns[1].q in _last_user_content(c["messages"])]
    assert turn2_calls, "找不到任何一次呼叫的最後一則 user 訊息是第 2 輪問句"
    second_messages = turn2_calls[0]["messages"]

    assert sc.turns[0].q in _all_text(second_messages)
    assert sc.turns[1].q in _last_user_content(second_messages)
    assistant_msgs = [m for m in second_messages if m.get("role") == "assistant"]
    assert assistant_msgs and any(
        str(m.get("content") or "") == turn1_answer for m in assistant_msgs
    )


@pytest.mark.req(_REQ_4_4)
def test_run_scenario_agent_carries_same_state_dict_across_turns(monkeypatch, tmp_path):
    """槽位貫穿：直接對 `_run_scenario_agent` 的 `state` 斷言（假 provider 無工具
    呼叫、⛔ 不能在假路徑觀測槽位——見 Plan §2「4.4b 前置改動」）。用一個會記錄
    收到的 `state` 物件 id 的假 `runtime.run_turn` 證明**同一個** dict 貫穿全程、
    且呼叫端可寫入的內容在下一輪仍看得到（模擬槽位貫穿）。"""
    path = _write_outline_probe_multi_turn(tmp_path)
    scenarios = agent_eval.load_outline_probe_v1(path, {"sets": {}})
    sc = next(s for s in scenarios if s.idx == "F-S1-landlord")

    seen_state_ids = []
    seen_marker_values = []

    class _FakeResult:
        def __init__(self):
            self.answer = "ok"
            self.handoff = None
            self.kind = "answer"
            self.trace = SimpleNamespace(
                verifier=[], prompt_tokens=0, completion_tokens=0,
                candidate_ids=[], miss_kind=None, violations=[],
            )

    class _FakeRuntime:
        _model = "test-model"

        async def run_turn(self, identity, q, state):
            seen_state_ids.append(id(state))
            # 模擬槽位寫入（例如上游從工具呼叫填回 state）：下一輪應仍看得到。
            seen_marker_values.append(state.get("_marker"))
            state["_marker"] = state.get("_marker", 0) + 1
            return _FakeResult()

    import asyncio

    asyncio.run(agent_eval._run_scenario_agent(_FakeRuntime(), identity=None, turns=sc.turns))

    assert len(seen_state_ids) == 2
    assert seen_state_ids[0] == seen_state_ids[1], "同一個 state dict 物件必須貫穿全程"
    assert seen_marker_values == [None, 1], "第 2 輪應看到第 1 輪寫入的值——槽位真的貫穿"
