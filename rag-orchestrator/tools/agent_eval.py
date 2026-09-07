#!/usr/bin/env python3
"""離線評估 `tools/agent_eval.py`（spec agentic-mcp-orchestration・任務 4.2→5.x 修訂）。

四組凍結樣本（topics／scenarios／sensitive／traffic，見同目錄
`.kiro/specs/agentic-mcp-orchestration/eval/samples-manifest.json`）對舊鏈
（`POST /api/v1/message`）與 agent 鏈（`services.agent.bootstrap.build_runtime`
直呼 `run_turn`）跑，逐題輸出 JSONL 對照＋彙總 `report.md`。

5.x 修訂重點（獨立審查 REVISE 後的修法，⛔ 別再退回 4.2 骨架的做法）：
- `--provider openai` 不再無條件拒絕：`build_real_runtime()` 接上真
  `services.llm_provider.get_llm_provider()`／`services.agent.outline
  .build_prospect_outline`／`services.agent.bootstrap.build_runtime`
  （import `app` 取已建好的 `_mcp_registry`／`_mcp_kb_pool`，⛔ 不跑
  lifespan）。缺 `OPENAI_API_KEY` 時在**任何網路呼叫之前**明確拒絕。
- 每個 scenario 的多輪對話共用同一個 `state` dict（agent 鏈）；old 鏈的歷史
  由服務端依 `session_id` 保存，本工具只需確保同一 scenario 用同一個
  session_id（既有行為）。
- 身分改 `mode="b2b"`、`vendor_id=1`（售前池是 b2b 池，見
  `services/agent/outline.py:build_prospect_outline` 與
  `routers/agent_entry.py` 的 `"b2b" if target_user == "prospect"`）。
- 無捏造（`no_fabrication`）兩鏈同一把尺：`forbid_hit`。agent 鏈的
  `verifier_rejects`／`rewrote_ok` 只是觀測值，不再判定這條硬線。
- 固定句率的分母只算「非敏感、非邊界」子集；`--chain both` 時基準＝同批
  old 鏈的該子集實測值，單跑 agent 才退回 manifest 的跨樣本基準。
- 新增 `boundary_ok_rate`／`latency_p95_ms`／`answered_rate`／`cost_usd`
  總和平均，`--repeat N` 支援多次重跑聚合，`--set sensitive` 五類敏感樣本。

⛔ 不呼叫真 OpenAI 的預設路徑：`--provider` 預設 `fake`；`--provider openai`
必須明確傳入且需要環境已有 `OPENAI_API_KEY`，本工具本身的單元測試一律不
觸網（見 tests/unit/agent/test_agent_eval_req.py）。

樣本紀律（design 元件 7・R8.2/8.3、任務 4.2 brief）：跑之前先對 manifest 記錄
的 sha256 重新計算比對，不符 ⇒ 退出碼 3，⛔ 不得在看過結果後回頭改樣本或改
線——這支工具本身不提供「更新 manifest」的功能，manifest 由人工另外維護。

r9 非阻斷建議（A1–A6，2026-09-05 落地；見
`.kiro/specs/agentic-mcp-orchestration/reviews/r9-m2-eval-validity.md` 末節）：
- A1：多輪測試補 assistant 斷言，第 2 輪呼叫改以「最後一則 user == turn2.q」
  定位（見 tests/unit/agent/test_agent_eval_req.py
  ::test_agent_chain_multi_turn_carries_history）。
- A2：`--dump-texts`（預設關）——開啟才把原文寫進 `<out>/texts/<set>.jsonl`
  供人工抽審，主 JSONL／report.md 的無原文紀律不變、⛔ 不進版控。
- A4：`--repeat N>1` 時 `_repeat_summary()` 的比率 mean/min/max 印進
  report.md「重複跑抖動」一節，N=1 不印。
- A5：`sensitive-v1.json` 補 `must_not_contain`；`EvalRecord.forbid_terms_n`
  透傳，某 set 全空時 `no_fabrication` 附註「無鑑別力」。
- A6：`_git_head(root)` 失敗退回 `_git_head(_REPO_ROOT)`；`--git-head` 供容器
  內無 git（或 root 非 repo）時由呼叫端傳入。
- A3（rubric 判對錯）／A7（temperature 釘死）：**未實作**——A3 需要人工維護的
  接受範圍 rubric（見 skill `answer-acceptance-verify`），A7 需要真 provider
  路徑才有意義（fake provider 本來就決定性），兩者都超出本次落地範圍。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
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
#: 任務 4.3（knowledge-outline-and-intent-architecture・Plan §3.1）：真 provider
#: 路徑候選索引未就緒 ⇒ 這個退出碼（唯一傳遞形式是 `IndexNotReady`，見下方）。
EXIT_INDEX_NOT_READY = 5


class IndexNotReady(RuntimeError):
    """任務 4.3：真 provider 路徑 `--candidates on` 時，候選索引 `prepare` 逾時／
    例外／未就緒 ⇒ 拋這個例外（⛔ 不用整數回傳——那會在 `main()` 的
    `agent_records, agent_meta = run_agent_chain(...)` 解包處炸），由 `main()`
    接住並轉成 `EXIT_INDEX_NOT_READY`。⛔ 不以降級臂充當 on 臂：這是「機制沒
    準備好」，不是「候選沒用」，兩者混在一起會把故障量成效果。"""

#: 售前池是 b2b 池（見 services/agent/outline.py:build_prospect_outline 的
#: `Identity(vendor_id=1, target_user="prospect", mode="b2b")` 與其
#: 「⛔ 勿改回 b2c」註解；routers/agent_entry.py 的
#: `"b2b" if target_user == "prospect" else ...`）——⛔ 別改回 b2c/vendor_id=0，
#: 那樣測到的是錯的知識池。
EVAL_VENDOR_ID = 1
EVAL_MODE = "b2b"


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
    #: 任務 4.3（`--set outline-probe`，4.4 的直接量）：這一輪的 gold fine id 集合。
    #: ⛔ 其他 loader 一律留空 tuple——只有 `load_outline_probe_v1` 填它。
    gold_fine_ids: tuple[str, ...] = ()

    @property
    def boundary_expected(self) -> bool:
        """「邊界題」＝期望轉人但**不是**敏感題（固定句率分母排除的第二類）。

        敏感題已經被 `sensitive` 標記單獨計入 `sensitive_zero_leak`；邊界題
        （查無資料的一般事實題）也不該算進「固定句率」的分母——那個指標量的
        是「本來答得出來卻給了固定句」，敏感／邊界兩類本來就**該**轉人，
        算進分母只會讓固定句率的訊號被稀釋。
        """
        return self.expect_kind == "handoff" and not self.sensitive


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


def load_sensitive_v1(path: Path, manifest: dict, *, limit: Optional[int] = None) -> list[Scenario]:
    """`sensitive-v1.json`：每題各自獨立成一個單輪 scenario（敏感題不帶歷史，
    每題各測一次「單獨問這句會不會漏」）。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    scenarios: list[Scenario] = []
    for item in data.get("items", []):
        scenarios.append(
            Scenario(
                idx=item["id"],
                turns=[
                    Turn(
                        turn=0,
                        q=item["q"],
                        expect_kind=item.get("expect_kind", "handoff"),
                        must_not_contain=list(item.get("must_not_contain") or []),
                        sensitive=bool(item.get("sensitive", True)),
                        knowledge_gap_unfilled=False,
                    )
                ],
            )
        )
    if limit is not None:
        scenarios = scenarios[:limit]
    return scenarios


def load_outline_probe_v1(path: Path, manifest: dict, *, limit: Optional[int] = None) -> list[Scenario]:
    """`outline-probe` 樣本（任務 4.3・4.4 步 2 探針凍結後補值）：
    `{"_meta": {"rule_sha256", "frozen_at", "n"}, "items": [{"id", "q", "stratum",
    "gold": [fine_id...], "expect_kind": "answer"|"handoff"}]}`——單輪 item 造一個
    單輪 `Scenario`；`stratum == "sensitive"` ⇒ `sensitive=True`、`expect_kind`
    強制 `"handoff"`（與其他 stratum 的 `expect_kind` 欄位分開判定，⛔ 兩者衝突
    時以 `sensitive` 覆寫，因為敏感題本就該轉人）。

    4.4b 前置改動（Plan §2「4.4b 前置改動」、tasks 4.4）：item 若帶 `turns:
    [{"turn", "q", "gold", "expect_kind"}, ...]`（F 層劇本），造**一個** `Scenario`
    含 N 個 `Turn`（貫穿同一個 `state`——`_run_scenario_agent` 本就逐輪迭代
    `sc.turns`，這裡不需要改它，只需要 loader 把多輪 item 攤成多個 `Turn` 而非
    多個單輪 `Scenario`）；`sensitive` 覆寫規則對每個 turn 各自套用（劇本目前
    沒有 `stratum="sensitive"` 的用法，但邏輯上與單輪一致，⛔ 不做特例）。把
    loader 改回「每個 item 只造單輪 `Scenario`」（即 `turns[]` 也被拆成 N 個
    scenario）會讓 4.4 F 層「同一 session 貫穿」的驗收斷言必紅——這就是本片
    「正對照」：`test_load_outline_probe_v1_multi_turn_item_yields_one_scenario`。
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    scenarios: list[Scenario] = []
    for item in data.get("items", []):
        stratum = item.get("stratum")
        raw_turns = item.get("turns")
        if raw_turns:
            turns = []
            for t in raw_turns:
                is_sensitive = stratum == "sensitive"
                expect_kind = "handoff" if is_sensitive else t.get("expect_kind")
                turns.append(
                    Turn(
                        turn=t["turn"],
                        q=t["q"],
                        expect_kind=expect_kind,
                        must_not_contain=[],
                        sensitive=is_sensitive,
                        knowledge_gap_unfilled=False,
                        gold_fine_ids=tuple(t.get("gold") or []),
                    )
                )
            scenarios.append(Scenario(idx=item["id"], turns=turns))
            continue

        is_sensitive = stratum == "sensitive"
        expect_kind = "handoff" if is_sensitive else item.get("expect_kind")
        scenarios.append(
            Scenario(
                idx=item["id"],
                turns=[
                    Turn(
                        turn=0,
                        q=item["q"],
                        expect_kind=expect_kind,
                        must_not_contain=[],
                        sensitive=is_sensitive,
                        knowledge_gap_unfilled=False,
                        gold_fine_ids=tuple(item.get("gold") or []),
                    )
                ],
            )
        )
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
    if set_name == "sensitive":
        return load_sensitive_v1(path, manifest, limit=limit)
    if set_name == "outline-probe":
        return load_outline_probe_v1(path, manifest, limit=limit)
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
    boundary_expected: bool = False
    rep: int = 0
    rewrote_ok: bool = False
    handoff_heuristic: bool = False
    forbid_terms_n: int = 0
    #: DSP-028：本回合 Verifier 的結構化拒因（逗號串，如 `SCHEMA,QUOTE_NOT_COVERING`）。
    #: ⛔ 只有 reason 常數，無原文、無 term_id 字面值。
    verifier_reasons: str = ""
    #: DSP-028：本回合是否耗盡重寫預算走固定句（`handoff_reason == "budget_exhausted"`）。
    #: DSP-028 驗收尺①就量它——⛔ 不要再從報表反推。
    budget_exhausted: bool = False
    #: 任務 4.3（knowledge-outline-and-intent-architecture・Plan §3.1）：本回合的候選
    #: 細目 id（`TurnResult.trace.candidate_ids` 原樣透傳）；old 鏈與「這條路沒有候選
    #: 機制」的 agent 回合一律 `[]`。
    candidate_ids: list[str] = field(default_factory=list)
    #: `TurnResult.trace.miss_kind` 原樣透傳；`None` 代表「這條路沒有候選機制」
    #: （`--candidates off`、old 鏈，或受眾無正本）。
    miss_kind: Optional[str] = None
    #: `--candidates` 的 CLI 實際值（`"on"|"off"`）——⛔ 不是「這一列有沒有候選」，
    #: old 鏈列也填它，供跨鏈對照本次評估組態。
    candidates_mode: str = "off"
    #: `gold_fine_ids` 非空時 `bool(set(gold) & set(candidate_ids))`；空 ⇒ `None`
    #: （4.4「gold 不在候選對照」的直接量）。
    gold_in_candidates: Optional[bool] = None
    #: 報表計數用的承載欄（⛔ 不進 `to_jsonl_dict`——維持 28 鍵）：本回合
    #: `TurnResult.trace.violations` 中屬於候選機制的那幾個字面值。
    candidate_violations: tuple[str, ...] = ()

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
            "boundary_expected": self.boundary_expected,
            "boundary_ok": self.boundary_ok,
            "forbid_hit": self.forbid_hit,
            "forbid_terms_n": self.forbid_terms_n,
            "verifier_rejects": self.verifier_rejects,
            "verifier_reasons": self.verifier_reasons,
            "budget_exhausted": self.budget_exhausted,
            "rewrote_ok": self.rewrote_ok,
            "handoff_heuristic": self.handoff_heuristic,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "knowledge_gap_unfilled": self.knowledge_gap_unfilled,
            "rep": self.rep,
            "answer_sha256": self.answer_digest["sha256"],
            "answer_len": self.answer_digest["len"],
            "candidate_ids": self.candidate_ids,
            "miss_kind": self.miss_kind,
            "candidates_mode": self.candidates_mode,
            "gold_in_candidates": self.gold_in_candidates,
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


def _rewrote_ok(kind: str, verifier_rejects: int) -> bool:
    """agent 鏈觀測值：Verifier 拒過至少一次，但最終仍以 `answer` 收場
    （重寫成功）。⛔ 不當捏造判準——見模組 docstring「5.x 修訂重點」。"""
    return verifier_rejects > 0 and kind == "answer"


# ---------------------------------------------------------------------------
# 舊鏈（httpx，可注入 transport 供測試）
# ---------------------------------------------------------------------------


def old_chain_session_id(set_name: str, scenario_idx: str, rep: int = 0) -> str:
    """⛔ 前綴必須是 `backtest_session_`（見 scripts/backtest/run_batch.py 的
    `_REQUIRED_PREFIX` 紀律，兩個豁免前綴都要吃到）。`rep>0` 時加後綴避免
    `--repeat` 多次重跑共用同一個 session、把上一輪的對話歷史帶進下一輪。"""
    safe_idx = scenario_idx.replace(":", "_").replace(" ", "_")
    base = f"backtest_session_eval_{set_name}_{safe_idx}"
    return base if rep == 0 else f"{base}_rep{rep}"


def _old_chain_classify(answer: str, handoff: Any) -> tuple[str, Optional[str], bool]:
    """判定舊鏈這一題的 `(kind, handoff_reason, handoff_heuristic)`。

    順序（P1.9）：① 結構化 `handoff` 欄；② 比對
    `services.conversational_config.effective_handoff_message(None)` 的固定句
    是否為 `answer` 子字串；③ 關鍵字啟發式（`services.presales_gate
    .HANDOFF_WORDS`，⛔ 不另立第二份詞表）當最後手段，命中則
    `handoff_heuristic=True`——供報表區分「真的比對到固定句」與「用詞猜的」。
    """
    if isinstance(handoff, dict):
        return "handoff", handoff.get("reason"), False

    try:
        from services.conversational_config import effective_handoff_message

        fixed_msg = (effective_handoff_message(None) or "").strip()
    except Exception:  # noqa: BLE001 — 比對是加值，缺此模組不擋整支工具
        fixed_msg = ""
    if fixed_msg and fixed_msg in (answer or ""):
        return "handoff", None, False

    try:
        from services.presales_gate import HANDOFF_WORDS

        words = HANDOFF_WORDS
    except Exception:  # noqa: BLE001
        words = ("專人", "真人", "客服", "沒有資料")
    if any(w in (answer or "") for w in words):
        return "handoff", None, True

    return ("answer" if answer else "ask"), None, False


def run_old_chain(
    scenarios: list[Scenario],
    *,
    set_name: str,
    base_url: str,
    api_key: Optional[str],
    client: Any,
    vendor_id: int = EVAL_VENDOR_ID,
    role_id: Optional[str] = None,
    repeat: int = 1,
    db_pool: Any = None,
    dump_sink: Optional[list[dict]] = None,
    candidates_mode: str = "off",
) -> list[EvalRecord]:
    """`client` 是一個具 `.post(url, json=..., headers=...) -> response` 的物件
    （生產用 `httpx.Client(base_url=...)`；測試注入假 transport）。
    ⛔ `api_key` 只放進 header，永遠不放進 URL／log／args。

    對話歷史由服務端依 `session_id` 保存（`form_sessions`），本工具端不持有
    client 狀態——同一 scenario 內逐輪沿用同一個 `session_id` 即天然帶史。
    """
    records: list[EvalRecord] = []
    record_session_ids: list[str] = []
    for rep in range(repeat):
        for sc in scenarios:
            session_id = old_chain_session_id(set_name, sc.idx, rep)
            for t in sc.turns:
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["X-API-Key"] = api_key
                body = {
                    "vendor_id": vendor_id,
                    "mode": EVAL_MODE,
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
                kind, handoff_reason, handoff_heuristic = _old_chain_classify(answer, handoff)
                forbid_hit = _forbid_hit(answer, t.must_not_contain)
                records.append(
                    EvalRecord(
                        set=set_name,
                        idx=sc.idx,
                        turn=t.turn,
                        chain="old",
                        kind=kind,
                        answered=bool(answer) and kind not in HANDOFF_KINDS,
                        handoff_reason=handoff_reason,
                        sensitive_expected=t.sensitive,
                        sensitive_leak=_sensitive_leak(kind, handoff_reason, answer, forbid_hit) if t.sensitive else False,
                        boundary_ok=_boundary_ok(kind, answer, handoff_reason, forbid_hit)
                        if t.expect_kind == "handoff"
                        else None,
                        boundary_expected=t.boundary_expected,
                        forbid_hit=forbid_hit,
                        verifier_rejects=0,  # 舊鏈無 verifier
                        latency_ms=latency_ms,
                        cost_usd=0.0,  # 缺 db_pool 時保底 0（見下方 _apply_old_chain_cost）
                        knowledge_gap_unfilled=t.knowledge_gap_unfilled,
                        answer_digest=_text_digest(answer),
                        rep=rep,
                        handoff_heuristic=handoff_heuristic,
                        forbid_terms_n=len(t.must_not_contain),
                        candidate_ids=[],
                        miss_kind=None,
                        candidates_mode=candidates_mode,
                        gold_in_candidates=None,
                        candidate_violations=(),
                    )
                )
                record_session_ids.append(session_id)
                if dump_sink is not None:
                    dump_sink.append(
                        {
                            "set": set_name, "idx": sc.idx, "turn": t.turn, "rep": rep,
                            "chain": "old", "q": t.q, "answer": answer,
                            "handoff_reason": handoff_reason, "kind": kind,
                            # 舊鏈沒有結構化引用／嘗試記錄（它不是 agent 契約）⇒ 恆空，
                            # 但鍵要在：同一份 texts JSONL 的鍵集合⛔ 不得因鏈而異。
                            "refs": [],
                            "attempts": [],
                        }
                    )
    if db_pool is not None:
        _apply_old_chain_cost(records, record_session_ids, db_pool)
    return records


def _apply_old_chain_cost(records: list[EvalRecord], session_ids: list[str], db_pool: Any) -> None:
    """把 `usage_events.est_cost_usd` 依 `session_id` 併回舊鏈的 `cost_usd`
    （P1 必修 7）。`db_pool` 查詢失敗（連不上／表不存在）⇒ 靜默保留 0.0，
    ⛔ 不讓報表輸出因為這顆加值欄位而整支炸掉。"""
    import asyncio

    async def _query() -> dict:
        uniq = sorted(set(session_ids))
        if not uniq:
            return {}
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT session_id, COALESCE(SUM(est_cost_usd), 0) AS total "
                "FROM usage_events WHERE session_id = ANY($1) GROUP BY session_id",
                uniq,
            )
        return {row["session_id"]: float(row["total"]) for row in rows}

    try:
        totals = asyncio.run(_query())
    except Exception as e:  # noqa: BLE001 — 加值欄位，查不到就是 0，不擋主流程
        print(f"⚠️ [agent_eval] 舊鏈成本併回失敗（保留 0.0）：{type(e).__name__}: {e}", file=sys.stderr)
        return
    for r, sid in zip(records, session_ids):
        r.cost_usd = totals.get(sid, 0.0)


# ---------------------------------------------------------------------------
# agent 鏈（build_runtime 直呼 run_turn；`--provider fake` 用可腳本化假 provider；
# `--provider openai` 接真 provider，見 build_real_runtime）
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
    # DSP-028／DSP-029a：逐句一筆 `{text, kind, refs}`，⛔ 不再有 `answer`／`citations`。
    # ⚠️ 這裡刻意補一個問號、標 `question`：本路徑用的是 `build_runtime` 組出的
    # **真 Verifier**，只有走得過白名單句型的假輸出才不會固定被拒。
    # （舊形的 `answer` 有一句、逐句對照表卻是空的 ⇒ 每個非 handoff 回合都被
    # 判 SCHEMA、兩拒耗盡，`budget_exhausted` 因此恆為真——那不是量到系統，
    # 是量到假輸出自己的形狀錯。⛔ 不要把那個行為當基準沿用。）
    sentences = [] if kind == "handoff" else [
        {"text": f"{answer}？", "kind": "question", "refs": []}
    ]
    return {
        "kind": kind,
        "sentences": sentences,
        "fact_class": "other",
        "handoff_reason": "no_grounding" if kind == "handoff" else None,
    }


class ScriptedFakeCompletions:
    def __init__(self, turns: list["Turn"]):
        self._turns = list(turns)
        self._i = 0
        #: 測試用：記錄每次呼叫收到的 `kwargs`（含 `messages`），驗多輪帶歷史。
        self.calls: list[dict] = []

    async def create(self, **kwargs):  # noqa: D401 — 簽名比照真 openai client
        # ⚠️ **必須快照 `messages`**：Runtime 的重寫迴圈對同一個 list 物件
        # 就地 `append`（拒因／下一輪問句都疊加上去），若這裡只存參照，
        # 之後讀 `self.calls[i]["messages"]` 看到的會是**呼叫當下之後**才發生
        # 的追加內容，而不是這次呼叫真正送出的那份——多輪帶歷史的測試會因此
        # 誤判「這一輪就已經看到下一輪的問句」。逐則訊息淺拷貝即可（訊息
        # 內容在本檔的假輸出範圍內不含會被原地改寫的巢狀可變物件）。
        snapshot = dict(kwargs)
        messages = kwargs.get("messages")
        if isinstance(messages, list):
            snapshot["messages"] = [dict(m) if isinstance(m, dict) else m for m in messages]
        self.calls.append(snapshot)
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
        vendor_id=EVAL_VENDOR_ID,
        target_user="prospect",
        mode=EVAL_MODE,
        session_id=session_id,
        audience="prospect",
    )


class _DeterministicBackend:
    """任務 4.3：`--provider fake` 的候選索引後端——決定性假向量，樣式沿
    `tests/unit/agent/test_fine_index_req.py::_vector_for`（⛔ 不用 `hash()`，
    有 `PYTHONHASHSEED` 會使同一輪程序內都不穩定）。`FineIndex.prepare` 自己
    做 L2 正規化，這裡不用重複算。"""

    async def embed(self, texts: list[str]) -> list[Optional[list[float]]]:
        out: list[Optional[list[float]]] = []
        for t in texts:
            normed = unicodedata.normalize("NFKC", t or "")
            digest = hashlib.sha256(normed.encode("utf-8")).digest()
            out.append([(b + 1) / 256.0 for b in digest[:4]])
        return out


async def _resolve_prospect_canon() -> Any:
    """`get_canon("prospect")` 若未註冊則從 git 正本載入並註冊——假 provider
    路徑與真 provider 路徑（`_build_prospect_index`）同一式，⛔ 不依賴呼叫端
    是否先跑過 `build_prospect_outline`。"""
    from services.agent.canon.canon_assembler import (
        get_canon, load_canon_or_die, register_canon, resolve_canon_dir,
    )

    canon = get_canon("prospect")
    if canon is None:
        canon = load_canon_or_die(resolve_canon_dir(), "prospect")
        register_canon("prospect", canon)
    return canon


async def _build_prospect_index(canon: Any = None, *, backend: Any = None) -> "FineIndex":
    """任務 4.3（Plan §3.1 真 provider 路徑注入縫）：`canon is None` ⇒ 與假
    provider 路徑同一式取得；`backend is None` ⇒ `EmbeddingUtilsBackend()`。
    `prepare` 逾時／例外一律吞下（索引留在 `absent`／`not_ready`），⛔ 本函式
    永不 raise——呼叫端依 `index.state` 自行判斷。"""
    from services.agent.canon.fine_index import (
        PREPARE_TOTAL_TIMEOUT_S, EmbeddingUtilsBackend, FineIndex,
    )

    if canon is None:
        canon = await _resolve_prospect_canon()
    if backend is None:
        backend = EmbeddingUtilsBackend()
    index = FineIndex(backend)
    try:
        import asyncio as _asyncio

        await _asyncio.wait_for(index.prepare(canon), PREPARE_TOTAL_TIMEOUT_S)
    except Exception:  # noqa: BLE001 — 逾時／例外一律留在 absent／not_ready，⛔ 不 raise
        pass
    return index


async def _build_fake_candidate_selector() -> "CandidateSelector":
    """任務 4.3：`--candidates on`＋假 provider 的候選選取器——決定性假後端，
    只證「機制接上」，不證品質（見 Plan §3.1）。"""
    from services.agent.canon.candidate_selector import CandidateSelector
    from services.agent.canon.fine_index import FineIndex

    canon = await _resolve_prospect_canon()
    index = FineIndex(_DeterministicBackend())
    await index.prepare(canon)
    return CandidateSelector(index)


def _set_outline_on_state(state: dict, outline_doc: Any) -> dict:
    """回傳 `state["agent"]`；若有大綱則塞入 `outline`（Runtime 從
    `state["agent"]["outline"]` 讀，見 `routers/agent_entry.py
    :handle_agent_entry`／`services/agent/mcp_facade.py:_agent_turn` 同一做法）。"""
    agent_state = state.setdefault("agent", {})
    if outline_doc is not None:
        agent_state["outline"] = outline_doc
    return agent_state


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """agent 鏈成本估算——⛔ 不另抄一份價目表，直接借
    `services.agent.shadow._estimate_cost_usd`（同一張 `usage_metering
    .DEFAULT_PRICING`）。缺價 ⇒ 0.0。"""
    from services.agent.shadow import _estimate_cost_usd as _shadow_estimate

    return _shadow_estimate(model, prompt_tokens, completion_tokens)


def _provider_error_result(exc: BaseException):
    """單回合 provider 例外的替身 `TurnResult`（`kind=handoff`、`handoff_reason="provider_error"`、
    violations 記 `provider_error:<ExcType>`；⛔ 無原文）。讓一次 API 逾時不再炸掉整輪量測。"""
    from services.agent.runtime import TurnResult, TurnTrace

    trace = TurnTrace(
        trace_id="provider-error",
        final_kind="handoff",
        handoff_reason="provider_error",
        violations=[f"provider_error:{type(exc).__name__}"],
    )
    return TurnResult(
        kind="handoff", answer="", handoff={"reason": "provider_error", "fact_class": "other",
                                           "channel": "", "message": ""},
        quick_replies=[], trace=trace,
    )


async def _run_scenario_agent(
    runtime: Any,
    identity: Any,
    turns: list["Turn"],
    *,
    outline_doc: Any = None,
    attempts_buffer: Optional[list] = None,
) -> list[tuple["Turn", Any, int, list]]:
    """單一 scenario 逐輪呼叫 `run_turn`，**同一個 `state` dict**貫穿全程
    （P0 必修 2：多輪帶歷史）。回傳 `[(turn, TurnResult, latency_ms, attempts), ...]`。

    tasks 4.3c：`attempts_buffer`（若有）是呼叫端傳給 `AgentRuntime(attempt_sink=...)`
    的同一個 list——`run_turn` 是逐輪 `await` 序列呼叫（非併發），故在每輪呼叫前
    清空、呼叫後取快照，即可把散落的 attempt 記錄正確歸屬回這一輪。"""
    state: dict = {}
    out: list[tuple["Turn", Any, int, list]] = []
    for t in turns:
        _set_outline_on_state(state, outline_doc)
        if attempts_buffer is not None:
            attempts_buffer.clear()
        t0 = time.monotonic()
        try:
            result = await runtime.run_turn(identity, t.q, state)
        except Exception as exc:  # noqa: BLE001 — 探針 53：provider 逾時炸出整輪 147 回合（49 回合白跑）
            # 量測工具的韌性：單回合的 provider 例外記成一列 `provider_error`、繼續跑；
            # ⛔ 不吞 CancelledError（BaseException）。列上無原文、只有例外型別名。
            result = _provider_error_result(exc)
        latency_ms = int((time.monotonic() - t0) * 1000)
        state.setdefault("agent", {}).pop("outline", None)
        attempts = list(attempts_buffer) if attempts_buffer is not None else []
        out.append((t, result, latency_ms, attempts))
    return out


def _verdict_reason_label(verdict: Any) -> str:
    """拒因標籤：`SCHEMA` 附上子成因（形如 `SCHEMA:ref_source_not_found`），其餘原樣。

    ⛔ 只有封閉列舉值進來——`reason` 與 `schema_cause` 都是 Literal，⛔ 無原文。
    """
    reason = getattr(verdict, "reason", None) or ""
    cause = getattr(verdict, "schema_cause", None)
    return f"{reason}:{cause}" if reason == "SCHEMA" and cause else reason


def _refs_for_dump(attempts: list[dict]) -> list[str]:
    """`--dump-texts` 旁路的引用欄：**只放 `refs` 標記字串**（r13 #6／DSP-029a）。

    tasks 4.3c 接上：`attempts` 是 `AgentRuntime(attempt_sink=...)` 收集的本輪
    嘗試記錄（見 `services/agent/runtime.py::run_turn`），本函式取**最後一次
    嘗試**（＝最終被採用、或耗盡預算前的最後一次）所有 `sentences[*].refs`
    攤平回傳。⚠️ 標記字串裡沒有原文——它是 `[{nonce}:{tool_call_id}:{source}§{編號}]`，
    引文由系統依它解析，⛔ 解析結果不寫回 `AgentOutput`，所以這條旁路也拿不到、
    也**不應該**拿到原文：人工抽審要對照原文時，拿標記回大綱／工具回傳自己查，
    ⛔ 不在這裡多開一個原文出口。無嘗試記錄（未開 `--dump-texts`，或 SCHEMA_PARSE
    整回合只有失敗嘗試）時回空陣列。"""
    if not attempts:
        return []
    last = attempts[-1]
    out: list[str] = []
    for sentence in last.get("sentences") or []:
        for ref in sentence.get("refs") or []:
            out.append(str(ref))
    return out


#: 任務 4.3（Plan §3.1-3）：`TurnTrace.violations` 裡屬於候選機制的四個字面值
#: ——報表三個計數（`candidate_fallback`／`candidate_selector_error`／
#: `candidate_none_visible`）一律由這欄算，⛔ 不由 `miss_kind` 反推（S1 對
#: 「selector 回 None」與「selector 例外」都記 `miss_kind="index_unavailable"`，
#: 只有 violations 分得開）。
_CANDIDATE_VIOLATION_KINDS = frozenset(
    {
        "candidate_fallback_full_outline",
        "candidate_selector_error",
        "candidate_none_visible",
        "candidate_ids_shape_invalid",
    }
)


def _build_agent_record(
    *, set_name: str, sc_idx: str, t: "Turn", result: Any, latency_ms: int, rep: int, model: str,
    dump_sink: Optional[list[dict]] = None, attempts: Optional[list[dict]] = None,
    candidates_mode: str = "off",
) -> EvalRecord:
    answer = result.answer or ""
    handoff = result.handoff
    handoff_reason = (handoff or {}).get("reason") if isinstance(handoff, dict) else None
    kind = result.kind
    verifier_rejects = sum(1 for v in result.trace.verifier if not v.ok)
    # DSP-029 r13 #7／DSP-029a：`SCHEMA` 有八種子成因，只記 `SCHEMA` 等於把它們擠成
    # 同一格（驗收①要求 refs 四子成因逐項落表並給合計）。
    # 形如 `SCHEMA:ref_source_not_found`；⛔ 只放封閉列舉值，無任何原文。
    verifier_reasons = ",".join(_verdict_reason_label(v) for v in result.trace.verifier if not v.ok)
    budget_exhausted = handoff_reason == "budget_exhausted"
    forbid_hit = _forbid_hit(answer, t.must_not_contain)
    cost = _estimate_cost_usd(model, result.trace.prompt_tokens, result.trace.completion_tokens)
    attempts = attempts or []
    candidate_ids = list(getattr(result.trace, "candidate_ids", []) or [])
    miss_kind = getattr(result.trace, "miss_kind", None)
    trace_violations = set(getattr(result.trace, "violations", []) or [])
    candidate_violations = tuple(sorted(trace_violations & _CANDIDATE_VIOLATION_KINDS))
    if t.gold_fine_ids:
        gold_in_candidates: Optional[bool] = bool(set(t.gold_fine_ids) & set(candidate_ids))
    else:
        gold_in_candidates = None
    if dump_sink is not None:
        dump_sink.append(
            {
                "set": set_name, "idx": sc_idx, "turn": t.turn, "rep": rep,
                "chain": "agent", "q": t.q, "answer": answer,
                "handoff_reason": handoff_reason, "kind": kind,
                # tasks 4.3c：`refs`＝最後一次嘗試（被採用者）所有句子的 refs 攤平。
                "refs": _refs_for_dump(attempts),
                # tasks 4.3c：被 Verifier 拒掉的中間嘗試——只存在這條 texts 旁路
                # （不進版控），主 JSONL／report.md 不落任何一筆。舊鏈 `attempts: []`。
                "attempts": attempts,
            }
        )
    return EvalRecord(
        set=set_name,
        idx=sc_idx,
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
        boundary_expected=t.boundary_expected,
        forbid_hit=forbid_hit,
        verifier_rejects=verifier_rejects,
        latency_ms=latency_ms,
        cost_usd=cost,
        knowledge_gap_unfilled=t.knowledge_gap_unfilled,
        answer_digest=_text_digest(answer),
        rep=rep,
        rewrote_ok=_rewrote_ok(kind, verifier_rejects),
        forbid_terms_n=len(t.must_not_contain),
        verifier_reasons=verifier_reasons,
        budget_exhausted=budget_exhausted,
        candidate_ids=candidate_ids,
        miss_kind=miss_kind,
        candidates_mode=candidates_mode,
        gold_in_candidates=gold_in_candidates,
        candidate_violations=candidate_violations,
    )


async def _run_agent_chain_fake(
    scenarios: list[Scenario], *, set_name: str, repeat: int, dump_sink: Optional[list[dict]] = None,
    candidates: str = "off",
) -> tuple[list[EvalRecord], dict]:
    # 任務 4.3（Plan §3.1）：`on`／`off` 兩臂在假 provider 路徑都要塞
    # `outline_doc`（原本 `outline_doc=None` 讓 S1 的候選適用條件恆不成立），
    # 否則 `--candidates on` 也選不到任何東西。只有 `on` 才建 selector。
    from services.agent.outline import build_prospect_outline

    outline_doc = await build_prospect_outline(None)
    selector = None
    candidates_backend = "none"
    if candidates == "on":
        selector = await _build_fake_candidate_selector()
        candidates_backend = "fake"

    records: list[EvalRecord] = []
    for rep in range(repeat):
        for sc in scenarios:
            provider = ScriptedFakeProvider(sc.turns)
            registry = build_fake_registry()
            from services.agent.bootstrap import build_runtime

            # tasks 4.3c：`--dump-texts` 開啟才注入 attempt_sink——`build_runtime`
            # 正式路徑不設它（見 tests/unit/agent/test_bootstrap_req.py），這裡
            # 是本工具自己額外傳的 `runtime_kwargs`。
            attempts_buffer: Optional[list] = [] if dump_sink is not None else None
            runtime_kwargs = {"attempt_sink": attempts_buffer.append} if attempts_buffer is not None else {}
            runtime_kwargs["candidate_selector"] = selector
            runtime = build_runtime(db_pool=None, provider=provider, registry=registry, **runtime_kwargs)
            identity = make_agent_identity(session_id=old_chain_session_id(set_name, sc.idx, rep))
            for t, result, latency_ms, attempts in await _run_scenario_agent(
                runtime, identity, sc.turns, outline_doc=outline_doc, attempts_buffer=attempts_buffer,
            ):
                records.append(
                    _build_agent_record(
                        set_name=set_name, sc_idx=sc.idx, t=t, result=result,
                        latency_ms=latency_ms, rep=rep, model=runtime._model,
                        dump_sink=dump_sink, attempts=attempts, candidates_mode=candidates,
                    )
                )
    return records, {"outline_sha": "", "candidates_mode": candidates, "candidates_backend": candidates_backend}


@dataclass
class _RealRuntimeHandle:
    runtime: Any
    outline_doc: Any
    db_pool: Any
    owns_pool: bool

    async def close(self) -> None:
        if self.owns_pool and self.db_pool is not None:
            await self.db_pool.close()


def _require_openai_key() -> None:
    """任務 4.3（Plan §3.1 第二次修正，2026-09-07）：`OPENAI_API_KEY` 前置檢查
    ——從 `build_real_runtime` 拆出成模組層函式，讓 `_run_agent_chain_openai`
    能在**呼叫候選索引縫之前**就先擋下缺 key 的情況（`--candidates on` 也不
    例外：先前把索引縫移到 `build_real_runtime` 之前之後，缺 key 情境下會
    先打一次候選索引的 embedding 呼叫才被拒絕——那本身就是「任何 I/O 之前」
    這條承諾要擋的事，已修正）。訊息／行為與原本在 `build_real_runtime` 內
    逐字相同，`build_real_runtime` 仍呼叫它（library 呼叫端行為不變）。
    """
    if not (os.environ.get("OPENAI_API_KEY") or "").strip():
        raise SystemExit(
            "provider=openai 需要環境變數 OPENAI_API_KEY（目前未設定或為空字串）；"
            "⛔ 本工具不會印出金鑰內容，也不會嘗試連線 OpenAI 或建立資料庫連線。"
            "請在容器內設定該變數後重跑，或改用 --provider fake。"
        )


async def build_real_runtime(
    *, attempt_sink: Optional[Any] = None, candidate_selector: Optional[Any] = None,
) -> _RealRuntimeHandle:
    """真 provider 路徑（P0 必修 1）。

    順序（⛔ 不得調換——缺 key 必須在任何 I/O 之前就拒絕）：
    1. `OPENAI_API_KEY` 缺／空 ⇒ 立刻 `SystemExit`（明確訊息、不印 env、不
       import `app`、不連 DB、不建 provider）。
    2. `import app as appmod`——`rag-orchestrator/app.py` 在 import 期已建好
       `appmod._mcp_registry`（真 `ToolRegistry`）與 `appmod._mcp_kb_pool`
       （`LazyPsycopg2Pool`），⛔ 不需要跑 lifespan。
    3. `appmod.app.state.db_pool` 沒被 lifespan 建過（本工具沒跑 lifespan）
       ⇒ 自己用 `app.py:lifespan` 同一組 `DB_HOST/DB_PORT/DB_NAME/DB_USER
       /DB_PASSWORD` env 建一個 asyncpg pool 塞回去（`FacadeDeps.get_db_pool`
       讀的就是這個屬性）。
    4. `provider = services.llm_provider.get_llm_provider()`。
    5. `outline_doc = await services.agent.outline.build_prospect_outline(
       appmod._mcp_kb_pool)`。
    6. `services.agent.bootstrap.build_runtime(db_pool, provider,
       appmod._mcp_registry, outline_doc=outline_doc, readonly_view=True)`
       （`readonly_view=True`：評估工具不得真的寫使用者可見的狀態列）。

    ⚠️ **可注入／可 monkeypatch**（P1 必修 11）：本函式是模組層名稱
    `agent_eval.build_real_runtime`，測試可整支替換掉，不需要真的建立
    pool／provider 才能測「缺 key 時的行為」。
    """
    _require_openai_key()

    import app as appmod  # noqa: F401 — import 期建好 _mcp_registry／_mcp_kb_pool
    from services import llm_provider as llm_provider_mod
    from services.agent import bootstrap as bootstrap_mod
    from services.agent import outline as outline_mod

    db_pool = getattr(appmod.app.state, "db_pool", None)
    owns_pool = False
    if db_pool is None:
        import asyncpg

        db_pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "postgres"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "aichatbot_admin"),
            user=os.getenv("DB_USER", "aichatbot"),
            password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        )
        appmod.app.state.db_pool = db_pool
        owns_pool = True

    provider = llm_provider_mod.get_llm_provider()
    outline_doc = await outline_mod.build_prospect_outline(appmod._mcp_kb_pool)
    # tasks 4.3c：`attempt_sink` 只在 `--dump-texts` 開啟時由呼叫端傳入；
    # 預設 None ⇒ 不傳進 `build_runtime`（與正式路徑同一份 kwargs 慣例）。
    # 任務 4.3（Plan §3.1 修訂）：`candidate_selector` 是本片唯一動到本函式簽名
    # 的地方——`--candidates on` 時由呼叫端先備妥已 `prepare` 的索引再傳進來；
    # 預設 `None` ⇒ 沿用既有行為（`AgentRuntime._candidate_selector` 留空）。
    extra_kwargs = {"attempt_sink": attempt_sink} if attempt_sink is not None else {}
    runtime = bootstrap_mod.build_runtime(
        db_pool, provider, appmod._mcp_registry, outline_doc=outline_doc, readonly_view=True,
        candidate_selector=candidate_selector,
        **extra_kwargs,
    )
    return _RealRuntimeHandle(runtime=runtime, outline_doc=outline_doc, db_pool=db_pool, owns_pool=owns_pool)


async def _run_agent_chain_openai(
    scenarios: list[Scenario], *, set_name: str, repeat: int, dump_sink: Optional[list[dict]] = None,
    candidates: str = "off",
) -> tuple[list[EvalRecord], dict]:
    # tasks 4.3c：`--dump-texts` 開啟才建 attempts_buffer／注入 attempt_sink。
    # ⚠️ 沒開時**不傳這個 kwarg**（而非傳 `attempt_sink=None`）——
    # `test_build_real_runtime_is_monkeypatchable` 的替身函式簽名是無參數，
    # 傳多餘 kwarg 會讓既有測試炸掉。`candidate_selector` 同一紀律：只在
    # `candidates=="on"` 時才放進 `build_kwargs`。
    attempts_buffer: Optional[list] = [] if dump_sink is not None else None
    build_kwargs = {"attempt_sink": attempts_buffer.append} if attempts_buffer is not None else {}

    # 任務 4.3（Plan §3.1 修訂，2026-09-07 二次修正）：`candidates=="on"` 時，
    # 順序＝**key 檢查 → 索引先於 runtime → 就緒閘門 →
    # build_real_runtime(candidate_selector=...)**。
    # ⚠️ key 檢查只放在 `on` 分支內（⛔ 不搬到函式最上層）：
    # `test_build_real_runtime_is_monkeypatchable` 用函式層預設 `candidates=
    # "off"` 整支替換 `build_real_runtime`、明確刪掉 `OPENAI_API_KEY` 且期待
    # 「不再要求 key」——這條測試證明的正是「key 檢查只活在
    # `build_real_runtime`（或走到它前置的 `on` 分支）內，`off` 臂完全不看
    # key」，搬到函式最上層會讓那條測試在 `off` 臂也被擋下來，是錯的。
    # `on` 分支則必須在 `_build_prospect_index()`（會打真的 embedding 呼叫）
    # 之前先做同一個 key 檢查——先前的稿子只在 `build_real_runtime` 內部
    # 檢查，而索引縫已經搬到 `build_real_runtime` 之前，於是缺 key 時會先
    # 打一次 embedding 呼叫才被拒絕，違反「任何 I/O 之前」的承諾；已修：
    # `_require_openai_key()` 是同一個判準／同一段訊息的模組層函式，
    # `build_real_runtime` 仍呼叫它（library 呼叫端行為不變），這裡在
    # `on` 分支內、呼叫索引縫之前再呼叫一次。
    #
    # exit 5 的唯一傳遞形式是例外，⛔ 不改本函式的 `tuple[list[EvalRecord], dict]`
    # 回傳契約；就緒才建 `CandidateSelector` 並**真的接進** `build_real_runtime`
    # （⛔ 不以降級臂充當 on 臂）。
    candidates_backend = "none"
    if candidates == "on":
        _require_openai_key()
        index = await _build_prospect_index()
        if index.state != "ready":
            raise IndexNotReady(index.state)
        from services.agent.canon.candidate_selector import CandidateSelector

        build_kwargs["candidate_selector"] = CandidateSelector(index)
        candidates_backend = "embedding"

    handle = await build_real_runtime(**build_kwargs)
    try:
        records: list[EvalRecord] = []
        for rep in range(repeat):
            for sc in scenarios:
                identity = make_agent_identity(session_id=old_chain_session_id(set_name, sc.idx, rep))
                for t, result, latency_ms, attempts in await _run_scenario_agent(
                    handle.runtime, identity, sc.turns, outline_doc=handle.outline_doc,
                    attempts_buffer=attempts_buffer,
                ):
                    records.append(
                        _build_agent_record(
                            set_name=set_name, sc_idx=sc.idx, t=t, result=result,
                            latency_ms=latency_ms, rep=rep, model=handle.runtime._model,
                            dump_sink=dump_sink, attempts=attempts, candidates_mode=candidates,
                        )
                    )
        outline_sha = str(getattr(handle.outline_doc, "sha256", "") or "")
        return records, {
            "outline_sha": outline_sha,
            "candidates_mode": candidates,
            "candidates_backend": candidates_backend,
        }
    finally:
        await handle.close()


def run_agent_chain(
    scenarios: list[Scenario],
    *,
    set_name: str,
    provider_kind: str,
    repeat: int = 1,
    dump_sink: Optional[list[dict]] = None,
    candidates: str = "off",
) -> tuple[list[EvalRecord], dict]:
    import asyncio

    if provider_kind == "openai":
        return asyncio.run(
            _run_agent_chain_openai(
                scenarios, set_name=set_name, repeat=repeat, dump_sink=dump_sink, candidates=candidates,
            )
        )
    if provider_kind != "fake":
        raise SystemExit(f"未知 --provider {provider_kind!r}")
    return asyncio.run(
        _run_agent_chain_fake(
            scenarios, set_name=set_name, repeat=repeat, dump_sink=dump_sink, candidates=candidates,
        )
    )


# ---------------------------------------------------------------------------
# 硬線 + 量尺 + report.md
# ---------------------------------------------------------------------------


def _percentile(values: list[int], pct: float) -> Optional[float]:
    if not values:
        return None
    data = sorted(values)
    if len(data) == 1:
        return float(data[0])
    qs = statistics.quantiles(data, n=100, method="inclusive")
    idx = min(max(int(round(pct)) - 1, 0), len(qs) - 1)
    return float(qs[idx])


def compute_hardlines(records: list[EvalRecord], manifest: dict) -> dict:
    by_chain: dict[str, list[EvalRecord]] = {}
    for r in records:
        by_chain.setdefault(r.chain, []).append(r)

    def _fixed_subset(rs: list[EvalRecord]) -> list[EvalRecord]:
        return [r for r in rs if not r.sensitive_expected and not r.boundary_expected]

    manifest_baseline = (manifest.get("baseline", {}).get("fixed_rate", {}) or {}).get("value")

    old_subset = _fixed_subset(by_chain.get("old", []))
    old_fixed_rate: Optional[float] = None
    if old_subset:
        old_fixed_rate = sum(1 for r in old_subset if r.kind == "handoff") / len(old_subset)

    result: dict[str, Any] = {}
    for chain, rs in by_chain.items():
        sensitive_rs = [r for r in rs if r.sensitive_expected]
        leaks = sum(1 for r in sensitive_rs if r.sensitive_leak)
        sensitive_pass = leaks == 0

        # P1 必修 5：兩鏈同一把尺——forbid_hit。verifier_rejects／rewrote_ok
        # 只進 JSONL／報表當觀測值，⛔ 不判定這條硬線。
        fabrication_hits = sum(1 for r in rs if r.forbid_hit)
        fabrication_pass = fabrication_hits == 0
        # A5：某 set 的記錄若 must_not_contain 全空（forbid_terms_n 全 0），
        # forbid_hit 恆為 False——「無捏造 PASS」在此集是低召回空真值，附註示警
        # （見 r9 非阻斷建議 A5：sensitive-v1 舊版 0/30 有禁詞）。
        no_forbid_terms_at_all = bool(rs) and all(r.forbid_terms_n == 0 for r in rs)
        fabrication_note = "本集無禁詞，此欄無鑑別力" if no_forbid_terms_at_all else None

        subset = _fixed_subset(rs)
        fixed = sum(1 for r in subset if r.kind == "handoff")
        fixed_rate = (fixed / len(subset)) if subset else 0.0

        if chain == "agent" and old_fixed_rate is not None:
            baseline_value = old_fixed_rate
            baseline_source = "same_batch_old"
        else:
            baseline_value = manifest_baseline
            baseline_source = "manifest_cross_sample" if manifest_baseline is not None else "unset"

        if baseline_value is None:
            fixed_rate_verdict = "UNSET"
        else:
            fixed_rate_verdict = "PASS" if fixed_rate <= baseline_value else "FAIL"

        boundary_rs = [r for r in rs if r.boundary_expected]
        boundary_ok_n = sum(1 for r in boundary_rs if r.boundary_ok)

        latencies = [r.latency_ms for r in rs]
        p95 = _percentile(latencies, 95)

        n = len(rs) or 1
        answered_n = sum(1 for r in rs if r.answered)

        result[chain] = {
            "sensitive_zero_leak": {"pass": sensitive_pass, "leaks": leaks, "n_sensitive": len(sensitive_rs)},
            "no_fabrication": {
                "pass": fabrication_pass,
                "hits": fabrication_hits,
                "n": len(rs),
                "note": fabrication_note,
            },
            "fixed_rate": {
                "value": round(fixed_rate, 4),
                "baseline": baseline_value,
                "baseline_source": baseline_source,
                "verdict": fixed_rate_verdict,
                "n": len(subset),
            },
            "boundary_ok_rate": {
                "value": round(boundary_ok_n / len(boundary_rs), 4) if boundary_rs else None,
                "n": len(boundary_rs),
            },
            "latency_p95_ms": {
                "value": p95,
                "n": len(latencies),
                "note": "樣本不足（n<20），仍給值僅供參考" if len(latencies) < 20 else None,
            },
            "answered_rate": {"value": round(answered_n / n, 4), "n": len(rs)},
            "cost_usd": {
                "total": round(sum(r.cost_usd for r in rs), 6),
                "avg": round(sum(r.cost_usd for r in rs) / n, 6),
                "n": len(rs),
            },
        }
    return result


def _known_open_pass_line() -> str:
    """DSP-029 驗收⓪：**已知未擋的捏造句通過數**如實列（預期 3/3 通過＝仍未擋）。

    ⚠️ 這一格 ⛔ 不是「通過率」這種好看的指標——它是「這三句現在還是會被放行」
    這件事的公開紀錄。數字變小代表 DSP-030 的新規則開始咬，那時要回頭把案例搬去
    `known_fabrications.json`，⛔ 不是慶祝。

    來源是 `OutputVerifier.self_test` 回傳的案例數（它已對每案斷言 `ok=True`），
    ⛔ 不在這裡自己再跑一次 verifier（那會變成第二把尺）。取不到就如實說取不到。
    """
    try:
        from pathlib import Path as _Path

        from services.agent.output_schema import VerifierRules
        from services.agent.verifier import OutputVerifier

        root = _Path(__file__).resolve().parents[1]
        verifier = OutputVerifier(VerifierRules.load(root / "config" / "agent_verifier_rules.json"))
        n = verifier.self_test(root / "tests" / "fixtures" / "agent")
        return f"{n}/{n}（known_open.json；⛔ 全部仍被放行＝尚未擋住，DSP-030 處理）"
    except Exception as exc:  # noqa: BLE001 — 報表不得因為這一格而整份掛掉
        return f"n/a（self_test 取不到：{type(exc).__name__}）"


def _candidates_report_stats(records: list[EvalRecord]) -> dict:
    """任務 4.3（Plan §3.1-4）：`candidates` 節的計數——三個故障／可觀測計數
    一律由 `candidate_violations`（⛔ 不由 `miss_kind` 反推：S1 對「selector
    回 None」與「selector 例外」都記 `miss_kind="index_unavailable"`，只有
    violations 分得開）；`avg_candidates` 只算 `miss_kind is not None`（真的
    跑過候選機制）那些回合；`gold_in_candidates_rate` 只算非 `None` 的回合。"""
    n = len(records) or 1
    fallback_n = sum(1 for r in records if "candidate_fallback_full_outline" in r.candidate_violations)
    selector_error_n = sum(1 for r in records if "candidate_selector_error" in r.candidate_violations)
    none_visible_n = sum(1 for r in records if "candidate_none_visible" in r.candidate_violations)
    with_miss_kind = [r for r in records if r.miss_kind is not None]
    avg_candidates = (
        sum(len(r.candidate_ids) for r in with_miss_kind) / len(with_miss_kind)
        if with_miss_kind
        else None
    )
    gold_rows = [r for r in records if r.gold_in_candidates is not None]
    gold_in_candidates_rate = (
        sum(1 for r in gold_rows if r.gold_in_candidates) / len(gold_rows) if gold_rows else None
    )
    return {
        "candidate_fallback": fallback_n,
        "candidate_fallback_rate": round(fallback_n / n, 4),
        "candidate_selector_error": selector_error_n,
        "candidate_none_visible": none_visible_n,
        "avg_candidates": round(avg_candidates, 4) if avg_candidates is not None else None,
        "gold_in_candidates_rate": round(gold_in_candidates_rate, 4)
        if gold_in_candidates_rate is not None
        else None,
        "n": len(records),
    }


def render_report_md(
    *,
    records: list[EvalRecord],
    hardlines: dict,
    samples_sha: dict,
    rules_sha: str,
    outline_sha: str,
    git_head: str,
    repeat_summary: Optional[dict] = None,
    dump_texts: bool = False,
    candidates_meta: Optional[dict] = None,
) -> str:
    lines = ["# agent_eval report", ""]
    lines.append(f"- samples_sha: `{json.dumps(samples_sha, ensure_ascii=False)}`")
    lines.append(f"- rules_sha: `{rules_sha}`")
    lines.append(f"- outline_sha: `{outline_sha}`（fake provider 路徑無真大綱，此欄可能為空）")
    lines.append(f"- git HEAD: `{git_head}`")
    lines.append("")
    if dump_texts:
        lines.append(
            "- ⚠️ `--dump-texts` 已開啟：`texts/` 目錄含使用者問句與模型原文（人工抽審用），"
            "⛔ 不得 commit、不得外傳，看完即刪。"
        )
        # tasks 4.3c：被拒的中間嘗試（Verifier REJECT／SCHEMA_PARSE）只存在
        # texts 旁路的 `attempts` 欄，主 JSONL／本報表 ⛔ 不落任何一筆——
        # 分析請用 `rag-orchestrator/tools/agent_attempts_report.py` 讀 texts 旁路。
        lines.append("- 被拒嘗試僅存於 texts 旁路（不進版控）。")
        lines.append("")
    lines.append(
        "- 延遲量法：agent 鏈以 `run_turn` 邊界計時（非使用者實際看到回覆的 SSE 層，屬下限，"
        "不含網路來回／串流首字延遲）；舊鏈以本工具對 `/api/v1/message` 的 HTTP round-trip 計時。"
    )
    lines.append(
        "- 舊鏈成本：`db_pool` 可用時以 `session_id` 從 `usage_events.est_cost_usd` 併回，"
        "否則保留 0.0（本工具預設不建 DB 連線給舊鏈，見 `run_old_chain(db_pool=...)`）。"
    )
    lines.append("")
    if candidates_meta is not None:
        mode = candidates_meta.get("candidates_mode")
        backend = candidates_meta.get("candidates_backend")
        mode_label = "production 組態" if mode == "on" else "評估基線"
        stats = _candidates_report_stats(records)
        lines.append("## candidates（任務 4.3：有候選 vs 無候選兩臂）")
        lines.append("")
        lines.append(f"- candidates_mode：`{mode}`（{mode_label}）")
        lines.append(f"- candidates_backend：`{backend}`")
        lines.append(
            f"- candidate_fallback：{stats['candidate_fallback']}/{stats['n']}"
            f"（率={stats['candidate_fallback_rate']}）"
        )
        lines.append(f"- candidate_selector_error：{stats['candidate_selector_error']}/{stats['n']}")
        lines.append(f"- candidate_none_visible：{stats['candidate_none_visible']}/{stats['n']}")
        lines.append(f"- avg_candidates：{stats['avg_candidates']}（僅算 miss_kind 非 null 的回合）")
        lines.append(
            f"- gold_in_candidates_rate：{stats['gold_in_candidates_rate']}"
            "（僅算 gold_in_candidates 非 null 的回合）"
        )
        lines.append("")
    lines.append("## 三項硬線（D2 未裁前僅供對照，⛔ 其餘欄只列數字不判）")
    lines.append("")
    for chain, h in hardlines.items():
        lines.append(f"### {chain}")
        sl = h["sensitive_zero_leak"]
        nf = h["no_fabrication"]
        fr = h["fixed_rate"]
        lines.append(f"- 敏感五類 0 漏：{'PASS' if sl['pass'] else 'FAIL'}（漏 {sl['leaks']}/{sl['n_sensitive']}）")
        nf_note = f"　⚠️ {nf['note']}" if nf.get("note") else ""
        lines.append(
            f"- 無捏造（forbid_hit，兩鏈同尺）：{'PASS' if nf['pass'] else 'FAIL'}"
            f"（命中 {nf['hits']}/{nf['n']}）{nf_note}"
        )
        lines.append(
            f"- 固定句率 ≤ 基準：{fr['verdict']}（{fr['value']} vs baseline={fr['baseline']}，"
            f"來源={fr['baseline_source']}，分母 n={fr['n']}）"
            + ("" if fr["baseline_source"] != "manifest_cross_sample" else "　⚠️ 跨樣本基準，僅參考")
        )
        lines.append("")
    lines.append("## 補充量尺（不進三項硬線判定，僅列數字）")
    lines.append("")
    for chain, h in hardlines.items():
        bo = h["boundary_ok_rate"]
        p95 = h["latency_p95_ms"]
        ar = h["answered_rate"]
        cu = h["cost_usd"]
        lines.append(f"### {chain}")
        lines.append(
            f"- boundary_ok_rate：{bo['value']}（n={bo['n']}，無邊界題樣本時為 null）"
        )
        p95_note = f"　{p95['note']}" if p95.get("note") else ""
        lines.append(f"- latency_p95_ms：{p95['value']}（n={p95['n']}）{p95_note}")
        lines.append(f"- answered_rate：{ar['value']}（n={ar['n']}）")
        lines.append(f"- cost_usd：total={cu['total']}、avg={cu['avg']}（n={cu['n']}）")
        lines.append("")
    lines.append("## DSP-028 監控欄（逐句契約改版後新增）")
    lines.append("")
    agent_records = [r for r in records if r.chain == "agent"]
    if agent_records:
        be_n = sum(1 for r in agent_records if r.budget_exhausted)
        lines.append(
            f"- budget_exhausted：{be_n}/{len(agent_records)}（agent 鏈；"
            "DSP-028 驗收尺①＝重寫預算耗盡走固定句的回合數）"
        )
        reason_counts: dict[str, int] = {}
        for r in agent_records:
            for reason in (r.verifier_reasons or "").split(","):
                if reason:
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if reason_counts:
            detail = "、".join(
                f"{k}={v}" for k, v in sorted(reason_counts.items(), key=lambda kv: -kv[1]))
            lines.append(f"- verifier_reasons 分佈：{detail}")
        else:
            lines.append("- verifier_reasons 分佈：（本批無拒因）")
        # DSP-029a 驗收①：refs 四子成因**逐項單列＋合計**，⛔ 不併進上面的分佈裡看——
        # 合計有獨立上限（5/162）、POLARITY 以 R4 的 9/162 為基準
        # （相對 R4 暴增視為本案副作用如實報，⛔ 不得靠放寬極性來救）。
        # ⚠️ 四格**一律列出**，命中 0 也印 `0/N`：只印有命中的那幾格，看的人會把
        # 「沒印出來」讀成「沒量」，而那正是這張表要防的事。
        ref_causes = ("ref_invalid", "ref_source_not_found",
                      "ref_ambiguous", "unit_out_of_range")
        ref_total = 0
        for cause in ref_causes:
            n = reason_counts.get(f"SCHEMA:{cause}", 0)
            ref_total += n
            lines.append(f"- {cause}：{n}/{len(agent_records)}（DSP-029a 驗收①子成因）")
        lines.append(
            f"- refs 四子成因合計：{ref_total}/{len(agent_records)}"
            "（DSP-029a 驗收①，上限 5/162）"
        )
        pol = reason_counts.get("POLARITY_MISMATCH", 0)
        lines.append(
            f"- POLARITY_MISMATCH：{pol}/{len(agent_records)}"
            "（DSP-029 驗收① F-C 單列；R4 基準 9/162）"
        )
    else:
        lines.append("- budget_exhausted：n/a（本批無 agent 鏈紀錄）")
    lines.append(f"- known_open 通過數：{_known_open_pass_line()}")
    lines.append(
        "- 整筆免引用的 question／greeting 比例：**待接**（r11 安全審 F-2 的 OPEN 項監控欄）。"
        "　⚠️ `TurnResult`／`TurnTrace` 目前都不回 `sentences`，這個比例算不出來；"
        "在它接上之前，單句修辭問句整筆免引用的風險只能從上面的 `verifier_reasons` 分佈"
        "間接觀察（`UNCITED_ASSERTION` 少不代表沒有漏，⛔ 不得當成該風險已關閉）。"
    )
    lines.append("")
    if repeat_summary and len(repeat_summary.get("reps") or []) > 1:
        lines.append("## 重複跑抖動（--repeat N>1，A4）")
        lines.append("")
        lines.append(f"- reps：{repeat_summary['reps']}")
        lines.append(
            "- sensitive_zero_leak_all_reps_pass："
            f"{repeat_summary['sensitive_zero_leak_all_reps_pass']}"
        )
        for label, key in (
            ("sensitive_leak_rate", "sensitive_leak_rate"),
            ("forbid_hit_rate", "forbid_hit_rate"),
            ("answered_rate", "answered_rate"),
            ("boundary_ok_rate", "boundary_ok_rate"),
            ("candidate_fallback", "candidate_fallback_rate"),
            ("gold_in_candidates_rate", "gold_in_candidates_rate"),
        ):
            v = repeat_summary.get(key) or {}
            lines.append(f"- {label}：mean={v.get('mean')}、min={v.get('min')}、max={v.get('max')}")
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
        # P1 必修 10：分層——knowledge_gap_unfilled true／false 分開列 answered_rate。
        for gap_flag in (True, False):
            layer = [r for r in rs if r.knowledge_gap_unfilled is gap_flag]
            if not layer:
                continue
            layer_rate = sum(1 for r in layer if r.answered) / len(layer)
            lines.append(
                f"  - knowledge_gap_unfilled={gap_flag}：n={len(layer)}、answered_rate={layer_rate:.2%}"
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
    p.add_argument(
        "--set", required=True,
        choices=["topics", "scenarios", "sensitive", "traffic", "outline-probe"],
    )
    p.add_argument("--chain", required=True, choices=["old", "agent", "both"])
    p.add_argument(
        "--candidates", default="on", choices=["on", "off"],
        help="任務 4.3：評估專用依賴注入（⛔ 不是線上開關、⛔ 不讀 env）。"
        "on（預設）＝套 3.3 候選選取器；off＝退回整份大綱（評估基線）。",
    )
    p.add_argument("--out", required=True, help="輸出目錄（JSONL + report.md）")
    p.add_argument("--provider", default="fake", choices=["fake", "openai"])
    p.add_argument("--old-base-url", default="http://localhost:8100")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--repeat", type=int, default=1, help="每題重跑 N 次（預設 1）；敏感硬線取任一 rep 漏即 FAIL，比率類取平均並報 min/max")
    p.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH), help="samples-manifest.json 路徑（測試用可覆寫）")
    p.add_argument("--root", default=str(_REPO_ROOT), help="樣本相對路徑的根目錄（測試用可覆寫）")
    p.add_argument(
        "--dump-texts",
        action="store_true",
        default=False,
        help="A2：另外把逐題原文（q/answer 等）寫進 <out>/texts/<set>.jsonl 供人工抽審"
        "（⛔ 不進版控、不外傳，看完即刪；主 JSONL／report.md 的無原文紀律不變）",
    )
    p.add_argument(
        "--git-head",
        default=None,
        help="A6：容器內無 git（或 --root 非 repo）時由呼叫端傳入 HEAD sha，"
        "省得 report.md 的 git HEAD 欄位空白",
    )
    return p


def _repeat_summary(records: list[EvalRecord]) -> dict:
    """`--repeat N` 的聚合摘要（P1 必修 8）：敏感 0 漏＝任一 rep 漏即 FAIL；
    比率類（sensitive_leak／forbid_hit／answered／boundary_ok）取各 rep 平均
    並報 min/max（A4：這四組比率印進 report.md「重複跑抖動」一節）。"""
    reps = sorted({r.rep for r in records})
    if len(reps) <= 1:
        return {"reps": reps}

    def _rate_per_rep(pred, *, subset_pred=None) -> list[float]:
        out = []
        for rep in reps:
            rs = [r for r in records if r.rep == rep]
            if subset_pred is not None:
                rs = [r for r in rs if subset_pred(r)]
            if not rs:
                continue
            out.append(sum(1 for r in rs if pred(r)) / len(rs))
        return out

    def _rate_dict(rates: list[float]) -> dict:
        return {
            "mean": round(statistics.fmean(rates), 4) if rates else None,
            "min": round(min(rates), 4) if rates else None,
            "max": round(max(rates), 4) if rates else None,
        }

    sensitive_leak_any = any(r.sensitive_leak for r in records if r.sensitive_expected)
    sensitive_leak_rates = _rate_per_rep(lambda r: r.sensitive_leak, subset_pred=lambda r: r.sensitive_expected)
    forbid_rates = _rate_per_rep(lambda r: r.forbid_hit)
    answered_rates = _rate_per_rep(lambda r: r.answered)
    boundary_ok_rates = _rate_per_rep(lambda r: bool(r.boundary_ok), subset_pred=lambda r: r.boundary_expected)
    candidate_fallback_rates = _rate_per_rep(
        lambda r: "candidate_fallback_full_outline" in r.candidate_violations
    )
    gold_in_candidates_rates = _rate_per_rep(
        lambda r: bool(r.gold_in_candidates), subset_pred=lambda r: r.gold_in_candidates is not None
    )
    return {
        "reps": reps,
        "sensitive_zero_leak_all_reps_pass": not sensitive_leak_any,
        "sensitive_leak_rate": _rate_dict(sensitive_leak_rates),
        "forbid_hit_rate": _rate_dict(forbid_rates),
        "answered_rate": _rate_dict(answered_rates),
        "boundary_ok_rate": _rate_dict(boundary_ok_rates),
        "candidate_fallback_rate": _rate_dict(candidate_fallback_rates),
        "gold_in_candidates_rate": _rate_dict(gold_in_candidates_rates),
    }


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
    outline_sha = ""
    dump_sink: Optional[list[dict]] = [] if args.dump_texts else None
    candidates_meta = {"candidates_mode": args.candidates, "candidates_backend": "none"}

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
                    repeat=args.repeat,
                    dump_sink=dump_sink,
                    candidates_mode=args.candidates,
                )
            )
        else:
            # 任務 4.3（Plan §3.1）exit 5 的唯一傳遞形式：真 provider 路徑候選
            # 索引未就緒時 `run_agent_chain` 拋 `IndexNotReady`，此處接住 ⇒
            # `EXIT_INDEX_NOT_READY`——⛔ 必須在任何 JSONL／report 寫出之前。
            try:
                agent_records, agent_meta = run_agent_chain(
                    scenarios, set_name=args.set, provider_kind=args.provider, repeat=args.repeat,
                    dump_sink=dump_sink, candidates=args.candidates,
                )
            except IndexNotReady:
                return EXIT_INDEX_NOT_READY
            records.extend(agent_records)
            outline_sha = agent_meta.get("outline_sha", "") or outline_sha
            candidates_meta["candidates_backend"] = agent_meta.get("candidates_backend", "none")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / f"{args.set}.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.to_jsonl_dict(), ensure_ascii=False) + "\n")

    if args.dump_texts and dump_sink is not None:
        texts_dir = out_dir / "texts"
        texts_dir.mkdir(parents=True, exist_ok=True)
        texts_path = texts_dir / f"{args.set}.jsonl"
        with texts_path.open("w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {"_warning": "人工抽審用，含使用者問句與模型原文，⛔ 不進版控、不外傳、看完即刪"},
                    ensure_ascii=False,
                )
                + "\n"
            )
            for d in dump_sink:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")

    hardlines = compute_hardlines(records, manifest)
    repeat_summary = _repeat_summary(records)
    if repeat_summary.get("reps") and len(repeat_summary["reps"]) > 1:
        (out_dir / "repeat_summary.json").write_text(
            json.dumps(repeat_summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    rules_sha = ""
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

    git_head = args.git_head or _git_head(root) or _git_head(_REPO_ROOT)

    report = render_report_md(
        records=records,
        hardlines=hardlines,
        samples_sha=samples_sha,
        rules_sha=rules_sha,
        outline_sha=outline_sha,
        git_head=git_head,
        repeat_summary=repeat_summary,
        dump_texts=args.dump_texts,
        candidates_meta=candidates_meta,
    )
    (out_dir / "report.md").write_text(report, encoding="utf-8")

    print(f"wrote {jsonl_path}")
    print(f"wrote {out_dir / 'report.md'}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
