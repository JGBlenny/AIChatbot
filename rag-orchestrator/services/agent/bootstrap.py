"""`build_runtime`（spec agentic-mcp-orchestration・任務 2.5）。

啟動期把 `VerifierRules` → `OutputVerifier`（含自證）→ `PromptAssembler` →
`AgentRuntime` 兜起來的**唯一**組裝點，⛔ 判斷邏輯不在這裡（那是
`verifier.py`／`runtime.py` 的事）。任何一步失敗一律 `raise`（啟動紅）——
帶著一把沒驗證過的尺（Verifier）上線，比啟動失敗更糟。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

from services.agent.agent_rules import persona_provider, policy_provider
from services.agent.budget import Budget
from services.agent.output_schema import VerifierRules
from services.agent.prompt_assembler import PromptAssembler
from services.agent.runtime import AgentRuntime
from services.agent.tools.registry import ToolRegistry
from services.agent.verifier import OutputVerifier

#: `services/agent/bootstrap.py` → parents[0]=agent, [1]=services, [2]=rag-orchestrator。
_RAG_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULES_PATH = _RAG_ROOT / "config" / "agent_verifier_rules.json"
DEFAULT_FIXTURES_DIR = _RAG_ROOT / "tests" / "fixtures" / "agent"


def build_runtime(
    db_pool: Any,
    provider: Any,
    registry: ToolRegistry,
    *,
    outline_doc: Optional[Any] = None,
    budget: Optional[Budget] = None,
    rules_path: Union[Path, str] = DEFAULT_RULES_PATH,
    fixtures_dir: Union[Path, str] = DEFAULT_FIXTURES_DIR,
    **runtime_kwargs: Any,
) -> AgentRuntime:
    """組裝順序固定，⛔ 不得跳步（design 元件 6、任務 2.5 brief）：

    1. `VerifierRules.load(rules_path)`——`sha256` 由檔案位元組算；檔案不存在
       或格式不符 ⇒ 直接 raise。
    2. `OutputVerifier(rules)`。
    3. `verifier.self_test(fixtures_dir)`——對 `known_fabrications.json` 全拒、
       `known_good.json` 全放，任一案例不符即 `RuntimeError`（⛔ 不吞例外續跑，
       這裡刻意不 try/except，讓呼叫端的啟動流程直接失敗）。
    4. `PromptAssembler(persona_provider, policy_provider)`——persona／政策文字
       來源見 `services/agent/agent_rules.py`（程式常數、進版控＝已審核）。
    5. `AgentRuntime(provider, registry, verifier, assembler, budget, **runtime_kwargs)`。

    回傳的 `AgentRuntime` 額外掛上 `rules_sha`／`outline_sha` 屬性（design
    附錄／任務 brief「並暴露 rules_sha／outline_sha 給 health」）——這兩個屬性
    不是 `AgentRuntime.__init__` 的正式參數，是本函式組裝完成後外掛的唯讀
    快照值，供健康檢查或其他觀測端讀取；`AgentRuntime` 本體邏輯不依賴它們。

    `db_pool` 目前未被任何組裝步驟消費——`OutlineAssembler`（任務 3.2）尚未
    接線，大綱／目錄的 DB 讀取還沒有落地。保留這個參數是讓呼叫端一次把
    未來要接的依賴準備好，⛔ 不是這裡偷偷用了卻沒說。
    """
    rules = VerifierRules.load(rules_path)
    verifier = OutputVerifier(rules)
    verifier.self_test(fixtures_dir)

    assembler = PromptAssembler(persona_provider, policy_provider)

    runtime = AgentRuntime(
        provider,
        registry,
        verifier,
        assembler,
        budget or Budget(),
        **runtime_kwargs,
    )
    runtime.rules_sha = rules.sha256
    runtime.outline_sha = str(getattr(outline_doc, "sha256", "") or "") if outline_doc is not None else ""
    return runtime


__all__ = ["build_runtime", "DEFAULT_RULES_PATH", "DEFAULT_FIXTURES_DIR"]
