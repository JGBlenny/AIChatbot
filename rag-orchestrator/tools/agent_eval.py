#!/usr/bin/env python3
"""離線評估 `tools/agent_eval.py`（spec agentic-mcp-orchestration・任務 4.2）。

三組凍結樣本（topics／scenarios／traffic，見同目錄
`.kiro/specs/agentic-mcp-orchestration/eval/samples-manifest.json`）對舊鏈
（`POST /api/v1/message`）與 agent 鏈（`services.agent.bootstrap.build_runtime`
直呼 `run_turn`）跑，逐題輸出 JSONL 對照＋彙總 `report.md`。

⛔ 本任務只做工具骨架＋假 provider 測試：不呼叫真 OpenAI（`--provider openai`
直接拒絕）、不打真正 `:8100`（old 鏈用可注入的 httpx transport，unit 測試
一律假 transport）。收案數字（D2）由這支工具產出對照，⛔ 由業主裁；本工具
本身不判定 D2 是否過關，只算三項硬線（見 manifest `hardlines`）。

樣本紀律（design 元件 7・R8.2/8.3、任務 4.2 brief）：跑之前先對 manifest 記錄
的 sha256 重新計算比對，不符 ⇒ 退出碼 3，⛔ 不得在看過結果後回頭改樣本或改
線——這支工具本身不提供「更新 manifest」的功能，manifest 由人工另外維護。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

# `tools/agent_eval.py` → parents[0]=tools, [1]=rag-orchestrator
_RAG_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _RAG_ROOT.parents[0]
if str(_RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(_RAG_ROOT))

DEFAULT_MANIFEST_PATH = (
    _REPO_ROOT / ".kiro" / "specs" / "agentic-mcp-orchestration" / "eval" / "samples-manifest.json"
)

_SAMPLES_CHANGED_MSG = (
    "樣本已變動，⛔ 不得在看過結果後改樣本或改線"
    "（manifest sha256 與實際檔案不符，見下方逐項比對）"
)

EXIT_OK = 0
EXIT_SAMPLES_CHANGED = 3
EXIT_SAMPLE_UNAVAILABLE = 4


# ---------------------------------------------------------------------------
# manifest／sha256
# ---------------------------------------------------------------------------


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(manifest_path: Path) -> dict:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


@dataclass
class ManifestCheck:
    ok: bool
    mismatches: list[dict] = field(default_factory=list)


def verify_manifest(manifest: dict, set_name: str, *, root: Path) -> ManifestCheck:
    """比對 `manifest["sets"][set_name]` 記錄的 sha256 與實際檔案。

    `available=false`（尚未凍結的樣本，例如 `traffic`）視為「不可跑」而非
    「sha 不符」——呼叫端應先用 `sample_available()` 判斷，這裡仍會在
    mismatches 記一條說明，供 CLI 統一走 UNAVAILABLE 分支。
    """
    entry = manifest.get("sets", {}).get(set_name)
    if entry is None:
        return ManifestCheck(ok=False, mismatches=[{"set": set_name, "reason": "manifest 未登記此 set"}])
    if not entry.get("available", False):
        return ManifestCheck(
            ok=False,
            mismatches=[{"set": set_name, "reason": entry.get("note", "尚未凍結（available=false）")}],
        )
    path = root / entry["path"]
    if not path.is_file():
        return ManifestCheck(ok=False, mismatches=[{"set": set_name, "path": str(path), "reason": "檔案不存在"}])
    actual = sha256_of(path)
    expected = entry.get("sha256")
    if actual != expected:
        return ManifestCheck(
            ok=False,
            mismatches=[{"set": set_name, "path": str(path), "expected": expected, "actual": actual}],
        )
    return ManifestCheck(ok=True)


def sample_available(manifest: dict, set_name: str) -> bool:
    return bool(manifest.get("sets", {}).get(set_name, {}).get("available", False))


# ---------------------------------------------------------------------------
# 樣本載入 → 統一形狀：list[Scenario]，Scenario.turns: list[Turn]
# ---------------------------------------------------------------------------


@dataclass
class Turn:
    turn: int
    q: str
    expect_kind: Optional[str] = None   # "answer" | "ask" | "handoff" | "recommend" | None（不判）
    must_not_contain: list[str] = field(default_factory=list)
    sensitive: bool = False
    knowledge_gap_unfilled: bool = False


@dataclass
class Scenario:
    idx: str
    turns: list[Turn]


def _gap_batches_imported(manifest: dict) -> bool:
    """3.4 未做時，逐題要標「知識缺口未補」——manifest 若未來補上
    `sets.*.gap_batches_imported` 就讀它；未登記則預設 False（保守：視為
    未補，⛔ 不得因為欄位缺席就假設已補）。
    """
    return bool(manifest.get("gap_batches_imported", False))


def load_topics_scenarios(path: Path, manifest: dict, *, limit: Optional[int] = None) -> list[Scenario]:
    data = json.loads(path.read_text(encoding="utf-8"))
    gap_unfilled = not _gap_batches_imported(manifest)
    scenarios: list[Scenario] = []
    for topic in data.get("topics", []):
        forbid_map = topic.get("forbid", {})
        star_forbid = list(forbid_map.get("*", []))
        for i, item in enumerate(topic.get("phrasings", [])):
            sub = item.get("sub", "")
            forbid = list(forbid_map.get(sub, [])) + star_forbid
            scenarios.append(
                Scenario(
                    idx=f"{topic['id']}:phrasing:{i}",
                    turns=[
                        Turn(
                            turn=0,
                            q=item["q"],
                            expect_kind=None,
                            must_not_contain=forbid,
                            sensitive=False,
                            knowledge_gap_unfilled=gap_unfilled,
                        )
                    ],
                )
            )
        for i, item in enumerate(topic.get("boundary", [])):
            sub = item.get("sub", "")
            forbid = list(forbid_map.get(sub, [])) + star_forbid
            scenarios.append(
                Scenario(
                    idx=f"{topic['id']}:boundary:{i}",
                    turns=[
                        Turn(
                            turn=0,
                            q=item["q"],
                            expect_kind="handoff",
                            must_not_contain=forbid,
                            sensitive=False,
                            knowledge_gap_unfilled=gap_unfilled,
                        )
                    ],
                )
            )
    if limit is not None:
        scenarios = scenarios[:limit]
    return scenarios


def load_scenarios_v1(path: Path, manifest: dict, *, limit: Optional[int] = None) -> list[Scenario]:
    data = json.loads(path.read_text(encoding="utf-8"))
    gap_unfilled = not _gap_batches_imported(manifest)
    scenarios: list[Scenario] = []
    for sc in data.get("scenarios", []):
        turns = [
            Turn(
                turn=t["turn"],
                q=t["q"],
                expect_kind=t.get("expect_kind"),
                must_not_contain=list(t.get("must_not_contain") or []),
                sensitive=bool(t.get("sensitive", False)),
                knowledge_gap_unfilled=gap_unfilled,
            )
            for t in sc.get("turns", [])
        ]
        scenarios.append(Scenario(idx=sc["id"], turns=turns))
    if limit is not None:
        scenarios = scenarios[:limit]
    return scenarios


def load_samples(set_name: str, manifest: dict, *, root: Path, limit: Optional[int] = None) -> list[Scenario]:
    entry = manifest["sets"][set_name]
    path = root / entry["path"]
    if set_name == "topics":
        return load_topics_scenarios(path, manifest, limit=limit)
    if set_name == "scenarios":
        return load_scenarios_v1(path, manifest, limit=limit)
    raise ValueError(f"未知 set：{set_name}")


# ---------------------------------------------------------------------------
# 逐題輸出記錄（⛔ 不落原文——answer 只留 sha256 與長度）
# ---------------------------------------------------------------------------

_NO_VERBATIM_KEYS = frozenset({"answer", "quote", "text", "user_message", "q"})


def _text_digest(text: str) -> dict:
    text = text or ""
    return {"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "len": len(text)}


@dataclass
class EvalRecord:
    set: str
    idx: str
    turn: int
    chain: str
    kind: str
    answered: bool
    handoff_reason: Optional[str]
    sensitive_expected: bool
    sensitive_leak: bool
    boundary_ok: Optional[bool]
    forbid_hit: bool
    verifier_rejects: int
    latency_ms: int
    cost_usd: float
    knowledge_gap_unfilled: bool
    answer_digest: dict

    def to_jsonl_dict(self) -> dict:
        d = {
            "set": self.set,
            "idx": self.idx,
            "turn": self.turn,
            "chain": self.chain,
            "kind": self.kind,
            "answered": self.answered,
            "handoff_reason": self.handoff_reason,
            "sensitive_expected": self.sensitive_expected,
            "sensitive_leak": self.sensitive_leak,
            "boundary_ok": self.boundary_ok,
            "forbid_hit": self.forbid_hit,
            "verifier_rejects": self.verifier_rejects,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "knowledge_gap_unfilled": self.knowledge_gap_unfilled,
            "answer_sha256": self.answer_digest["sha256"],
            "answer_len": self.answer_digest["len"],
        }
        assert not (_NO_VERBATIM_KEYS & set(d.keys())), "JSONL 洩了原文鍵——見模組 docstring 紀律"
        return d


HANDOFF_KINDS = {"handoff"}


def _forbid_hit(answer: str, must_not_contain: Iterable[str]) -> bool:
    return any(term and term in (answer or "") for term in must_not_contain)


def _boundary_ok(kind: str, answer: str, handoff_reason: Optional[str], forbid_hit: bool) -> Optional[bool]:
    if forbid_hit:
        return False
    if kind in HANDOFF_KINDS or handoff_reason:
        return True
    return any(w in (answer or "") for w in ("沒有資料", "專人", "找真人", "找不到"))


def _sensitive_leak(kind: str, handoff_reason: Optional[str], answer: str, forbid_hit: bool) -> bool:
    """敏感題「漏」＝沒有轉人／固定句收場，卻給出實質斷言。"""
    if kind in HANDOFF_KINDS or handoff_reason:
        return False
    return bool((answer or "").strip()) or forbid_hit


# ---------------------------------------------------------------------------
# 舊鏈（httpx，可注入 transport 供測試）
# ---------------------------------------------------------------------------


def old_chain_session_id(set_name: str, scenario_idx: str) -> str:
    """⛔ 前綴必須是 `backtest_session_`（見 scripts/backtest/run_batch.py 的
    `_REQUIRED_PREFIX` 紀律，兩個豁免前綴都要吃到）。"""
    safe_idx = scenario_idx.replace(":", "_").replace(" ", "_")
    return f"backtest_session_eval_{set_name}_{safe_idx}"


def run_old_chain(
    scenarios: list[Scenario],
    *,
    set_name: str,
    base_url: str,
    api_key: Optional[str],
    client: Any,
    vendor_id: int = 0,
    role_id: Optional[str] = None,
) -> list[EvalRecord]:
    """`client` 是一個具 `.post(url, json=..., headers=...) -> response` 的物件
    （生產用 `httpx.Client(base_url=...)`；測試注入假 transport）。
    ⛔ `api_key` 只放進 header，永遠不放進 URL／log／args。
    """
    records: list[EvalRecord] = []
    for sc in scenarios:
        session_id = old_chain_session_id(set_name, sc.idx)
        for t in sc.turns:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["X-API-Key"] = api_key
            body = {
                "vendor_id": vendor_id,
                "mode": "b2c",
                "target_user": "prospect",
                "role_id": role_id,
                "session_id": session_id,
                "user_id": session_id,
                "message": t.q,
            }
            t0 = time.monotonic()
            resp = client.post(f"{base_url}/api/v1/message", json=body, headers=headers)
            latency_ms = int((time.monotonic() - t0) * 1000)
            data = resp.json() if hasattr(resp, "json") else {}
            answer = data.get("answer") or ""
            handoff = data.get("handoff")
            handoff_reason = None
            if isinstance(handoff, dict):
                handoff_reason = handoff.get("reason")
            kind = "handoff" if handoff else ("answer" if answer else "ask")
            forbid_hit = _forbid_hit(answer, t.must_not_contain)
            records.append(
                EvalRecord(
                    set=set_name,
                    idx=sc.idx,
                    turn=t.turn,
                    chain="old",
                    kind=kind,
                    answered=bool(answer) and not handoff,
                    handoff_reason=handoff_reason,
                    sensitive_expected=t.sensitive,
                    sensitive_leak=_sensitive_leak(kind, handoff_reason, answer, forbid_hit) if t.sensitive else False,
                    boundary_ok=_boundary_ok(kind, answer, handoff_reason, forbid_hit)
                    if t.expect_kind == "handoff"
                    else None,
                    forbid_hit=forbid_hit,
                    verifier_rejects=0,  # 舊鏈無 verifier
                    latency_ms=latency_ms,
                    cost_usd=0.0,  # 舊鏈成本另由 usage_events 併回（3.4／contract_enrich 路徑），本工具不重算
                    knowledge_gap_unfilled=t.knowledge_gap_unfilled,
                    answer_digest=_text_digest(answer),
                )
            )
    return records


# ---------------------------------------------------------------------------
# agent 鏈（build_runtime 直呼 run_turn；`--provider fake` 用可腳本化假 provider）
# ---------------------------------------------------------------------------


class _FakeMessage:
    def __init__(self, content):
        self.content = content
        self.tool_calls = None


class _FakeChoice:
    def __init__(self, message):
        self.message = message


class _FakeUsage:
    def __init__(self, prompt_tokens=0, completion_tokens=0):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _FakeResponse:
    def __init__(self, payload: dict, *, prompt_tokens=20, completion_tokens=10):
        self.choices = [_FakeChoice(_FakeMessage(json.dumps(payload, ensure_ascii=False)))]
        self.usage = _FakeUsage(prompt_tokens, completion_tokens)


def _fixed_agent_output_for(turn: "Turn") -> dict:
    """決定性、無隨機——同輸入必同輸出（design 元件 7 契約）。

    腳本規則（單純、可預期，不追求逼真）：
    - `sensitive=True` ⇒ `kind="handoff"`（模擬模型正確判斷敏感題應轉人）。
    - 否則依 `expect_kind` 回對應 kind；缺省一律 `answer`。
    - `answer` 內容固定為一句不含任何已知禁詞的安全文字，⛔ 不含使用者原句
      （避免巧合觸發 forbid_hit，讓假 provider 分支保持可預期）。
    """
    if turn.sensitive:
        kind = "handoff"
    else:
        kind = turn.expect_kind or "answer"
    answer = "" if kind == "handoff" else f"[fake-agent-answer:{kind}]"
    return {
        "kind": kind,
        "answer": answer,
        "citations": [],
        "sentence_map": [],
        "fact_class": "other",
        "handoff_reason": "no_grounding" if kind == "handoff" else None,
    }


class ScriptedFakeCompletions:
    def __init__(self, turns: list["Turn"]):
        self._turns = list(turns)
        self._i = 0

    async def create(self, **kwargs):  # noqa: D401 — 簽名比照真 openai client
        if self._i >= len(self._turns):
            # 重寫迴圈（拒後再問模型）可能多打一次；重播上一題的固定輸出，
            # 保持決定性（⛔ 不 raise，raise 會讓 Runtime 的重寫路徑無法測）。
            turn = self._turns[-1]
        else:
            turn = self._turns[self._i]
            self._i += 1
        return _FakeResponse(_fixed_agent_output_for(turn))


class ScriptedFakeProvider:
    """`provider.async_client.chat.completions.create(...)`（比照
    `tests/unit/agent/test_runtime_req.py::FakeProvider` 既有慣例）。"""

    def __init__(self, turns: list["Turn"]):
        from types import SimpleNamespace

        completions = ScriptedFakeCompletions(turns)
        self.async_client = SimpleNamespace(chat=SimpleNamespace(completions=completions))


def build_fake_registry():
    """真的 `ToolRegistry`（空白名單、無工具註冊）——比 `SimpleNamespace` 更貼近
    生產組裝路徑（`build_runtime` 會呼叫 `to_openai_tools`），且不需要假造
    `ToolRegistry` 的完整介面。"""
    from services.agent.tools.registry import ToolRegistry

    return ToolRegistry()


def make_agent_identity(*, session_id: str):
    from services.agent.identity import Identity

    return Identity(
        vendor_id=0,
        target_user="prospect",
        mode="b2c",
        session_id=session_id,
        audience="prospect",
    )


async def _run_turn_for(runtime, identity, q: str) -> Any:
    state: dict = {}
    return await runtime.run_turn(identity, q, state)


def run_agent_chain(
    scenarios: list[Scenario],
    *,
    set_name: str,
    provider_kind: str,
) -> list[EvalRecord]:
    if provider_kind == "openai":
        raise SystemExit(
            "provider=openai 未在任務 4.2 實作範圍內（⛔ 本任務不呼叫真 OpenAI）；"
            "真線路評估屬任務 4.3。"
        )
    if provider_kind != "fake":
        raise SystemExit(f"未知 --provider {provider_kind!r}")

    import asyncio

    from services.agent.bootstrap import build_runtime

    records: list[EvalRecord] = []
    for sc in scenarios:
        provider = ScriptedFakeProvider(sc.turns)
        registry = build_fake_registry()
        runtime = build_runtime(db_pool=None, provider=provider, registry=registry)
        identity = make_agent_identity(session_id=old_chain_session_id(set_name, sc.idx))
        for t in sc.turns:
            t0 = time.monotonic()
            result = asyncio.run(_run_turn_for(runtime, identity, t.q))
            latency_ms = int((time.monotonic() - t0) * 1000)
            answer = result.answer or ""
            handoff = result.handoff
            handoff_reason = (handoff or {}).get("reason") if isinstance(handoff, dict) else None
            kind = result.kind
            verifier_rejects = sum(1 for v in result.trace.verifier if not v.ok)
            forbid_hit = _forbid_hit(answer, t.must_not_contain)
            records.append(
                EvalRecord(
                    set=set_name,
                    idx=sc.idx,
                    turn=t.turn,
                    chain="agent",
                    kind=kind,
                    answered=bool(answer) and kind not in HANDOFF_KINDS,
                    handoff_reason=handoff_reason,
                    sensitive_expected=t.sensitive,
                    sensitive_leak=_sensitive_leak(kind, handoff_reason, answer, forbid_hit) if t.sensitive else False,
                    boundary_ok=_boundary_ok(kind, answer, handoff_reason, forbid_hit)
                    if t.expect_kind == "handoff"
                    else None,
                    forbid_hit=forbid_hit,
                    verifier_rejects=verifier_rejects,
                    latency_ms=latency_ms,
                    cost_usd=0.0,  # fake provider 無真實 token 定價；--provider openai（另案）才計費
                    knowledge_gap_unfilled=t.knowledge_gap_unfilled,
                    answer_digest=_text_digest(answer),
                )
            )
    return records


# ---------------------------------------------------------------------------
# 三項硬線 + report.md
# ---------------------------------------------------------------------------


def compute_hardlines(records: list[EvalRecord], manifest: dict) -> dict:
    by_chain: dict[str, list[EvalRecord]] = {}
    for r in records:
        by_chain.setdefault(r.chain, []).append(r)

    result: dict[str, Any] = {}
    for chain, rs in by_chain.items():
        sensitive_rs = [r for r in rs if r.sensitive_expected]
        leaks = sum(1 for r in sensitive_rs if r.sensitive_leak)
        sensitive_pass = leaks == 0

        if chain == "agent":
            fabrication_hits = sum(1 for r in rs if r.verifier_rejects > 0 and r.kind == "answer")
        else:
            fabrication_hits = sum(1 for r in rs if r.forbid_hit)
        fabrication_pass = fabrication_hits == 0

        total = len(rs) or 1
        fixed = sum(1 for r in rs if r.kind == "handoff")
        fixed_rate = fixed / total
        baseline = (manifest.get("baseline", {}).get("fixed_rate", {}) or {}).get("value")
        if baseline is None:
            fixed_rate_verdict = "UNSET"
        else:
            fixed_rate_verdict = "PASS" if fixed_rate <= baseline else "FAIL"

        result[chain] = {
            "sensitive_zero_leak": {"pass": sensitive_pass, "leaks": leaks, "n_sensitive": len(sensitive_rs)},
            "no_fabrication": {"pass": fabrication_pass, "hits": fabrication_hits, "n": len(rs)},
            "fixed_rate": {
                "value": round(fixed_rate, 4),
                "baseline": baseline,
                "verdict": fixed_rate_verdict,
            },
        }
    return result


def render_report_md(
    *,
    records: list[EvalRecord],
    hardlines: dict,
    samples_sha: dict,
    rules_sha: str,
    outline_sha: str,
    git_head: str,
) -> str:
    lines = ["# agent_eval report", ""]
    lines.append(f"- samples_sha: `{json.dumps(samples_sha, ensure_ascii=False)}`")
    lines.append(f"- rules_sha: `{rules_sha}`")
    lines.append(f"- outline_sha: `{outline_sha}`")
    lines.append(f"- git HEAD: `{git_head}`")
    lines.append("")
    lines.append("## 三項硬線（D2 未裁前僅供對照，⛔ 其餘欄只列數字不判）")
    lines.append("")
    for chain, h in hardlines.items():
        lines.append(f"### {chain}")
        sl = h["sensitive_zero_leak"]
        nf = h["no_fabrication"]
        fr = h["fixed_rate"]
        lines.append(f"- 敏感五類 0 漏：{'PASS' if sl['pass'] else 'FAIL'}（漏 {sl['leaks']}/{sl['n_sensitive']}）")
        lines.append(f"- 無捏造：{'PASS' if nf['pass'] else 'FAIL'}（命中 {nf['hits']}/{nf['n']}）")
        lines.append(f"- 固定句率 ≤ 基準：{fr['verdict']}（{fr['value']} vs baseline={fr['baseline']}）")
        lines.append("")
    lines.append("## 逐鏈統計（僅列數字，不判 D2）")
    by_chain: dict[str, list[EvalRecord]] = {}
    for r in records:
        by_chain.setdefault(r.chain, []).append(r)
    for chain, rs in by_chain.items():
        n = len(rs) or 1
        answered_rate = sum(1 for r in rs if r.answered) / n
        avg_latency = sum(r.latency_ms for r in rs) / n
        avg_cost = sum(r.cost_usd for r in rs) / n
        gap_unfilled_n = sum(1 for r in rs if r.knowledge_gap_unfilled)
        lines.append(
            f"- **{chain}**：n={len(rs)}、answered_rate={answered_rate:.2%}、"
            f"avg_latency_ms={avg_latency:.0f}、avg_cost_usd={avg_cost:.6f}、"
            f"knowledge_gap_unfilled={gap_unfilled_n}/{len(rs)}"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _git_head(root: Path) -> str:
    import subprocess

    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=5
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:  # noqa: BLE001 — git 缺席不擋報表產出
        return ""


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--set", required=True, choices=["topics", "scenarios", "traffic"])
    p.add_argument("--chain", required=True, choices=["old", "agent", "both"])
    p.add_argument("--out", required=True, help="輸出目錄（JSONL + report.md）")
    p.add_argument("--provider", default="fake", choices=["fake", "openai"])
    p.add_argument("--old-base-url", default="http://localhost:8100")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH), help="samples-manifest.json 路徑（測試用可覆寫）")
    p.add_argument("--root", default=str(_REPO_ROOT), help="樣本相對路徑的根目錄（測試用可覆寫）")
    return p


def main(argv: Optional[list[str]] = None, *, http_client: Any = None) -> int:
    args = build_arg_parser().parse_args(argv)
    root = Path(args.root)
    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)

    if not sample_available(manifest, args.set):
        entry = manifest.get("sets", {}).get(args.set, {})
        print(f"樣本尚未就緒（available=false）：{entry.get('note', '')}", file=sys.stderr)
        return EXIT_SAMPLE_UNAVAILABLE

    check = verify_manifest(manifest, args.set, root=root)
    if not check.ok:
        print(_SAMPLES_CHANGED_MSG, file=sys.stderr)
        for m in check.mismatches:
            print(f"  - {json.dumps(m, ensure_ascii=False)}", file=sys.stderr)
        return EXIT_SAMPLES_CHANGED

    scenarios = load_samples(args.set, manifest, root=root, limit=args.limit)

    records: list[EvalRecord] = []
    chains = ["old", "agent"] if args.chain == "both" else [args.chain]

    for chain in chains:
        if chain == "old":
            client = http_client
            if client is None:
                import httpx

                client = httpx.Client(timeout=180.0)
            api_key = os.environ.get("RAG_ADMIN_API_KEY")  # ⛔ 不進 argv
            records.extend(
                run_old_chain(
                    scenarios,
                    set_name=args.set,
                    base_url=args.old_base_url,
                    api_key=api_key,
                    client=client,
                )
            )
        else:
            records.extend(run_agent_chain(scenarios, set_name=args.set, provider_kind=args.provider))

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / f"{args.set}.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.to_jsonl_dict(), ensure_ascii=False) + "\n")

    hardlines = compute_hardlines(records, manifest)

    rules_sha = ""
    outline_sha = ""
    try:
        from services.agent.output_schema import VerifierRules

        rules_sha = VerifierRules.load(_RAG_ROOT / "config" / "agent_verifier_rules.json").sha256
    except Exception:  # noqa: BLE001 — 報表不因規則檔缺席而整支失敗
        rules_sha = ""

    samples_sha = {
        name: manifest["sets"][name]["sha256"]
        for name in manifest.get("sets", {})
        if manifest["sets"][name].get("available")
    }

    report = render_report_md(
        records=records,
        hardlines=hardlines,
        samples_sha=samples_sha,
        rules_sha=rules_sha,
        outline_sha=outline_sha,
        git_head=_git_head(root),
    )
    (out_dir / "report.md").write_text(report, encoding="utf-8")

    print(f"wrote {jsonl_path}")
    print(f"wrote {out_dir / 'report.md'}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
