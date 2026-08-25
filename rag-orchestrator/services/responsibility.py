"""Responsibility evaluation context ／ decision — **單一權威建構點**。

spec `face-exit-before-grounding` 的實作 slice 1。

## 為什麼要有這個模組

實測（`.kiro/specs/face-exit-before-grounding/research.md` §8.3）發現：
同一個面向，**進場前**與**進場後**拿到的 system context **不是同一份**——

```text
pre-entry   get_system_context(db, cfg.key)                  → 常落回 base
in-session  get_system_context(db, _domain_key(config))      → 該領域的脈絡
billing_anomaly 兩者 digest 不同（d1f88c90… vs 2158ebdc…）
```

⚠️ 後果：進場前做的 responsibility 判定**不是**進場後會做的那個判定，
於是「把判斷提前」這句話在 production 上不成立。本模組把兩邊收斂到同一條路徑。

## 權威鍵的定義（唯一真實來源）

```text
當輪面向（state.face）優先 → 否則 topic_scope.category（診斷面向）→ 否則 persona_role（角色級面向）
```
"""

import hashlib
from dataclasses import dataclass
import os
from typing import Any, Optional


def responsibility_context_key(config: Any, face: Optional[str] = None) -> Optional[str]:
    """responsibility 評估所用的**權威 context 鍵**。

    ⚠️ 這是唯一定義點：`conversational_engine._domain_key` 與 pre-entry 皆委派至此，
    不得任何一方自行以 `cfg.key` 之類的替代鍵取脈絡。
    """
    if face:
        return face
    ts = getattr(config, "topic_scope", None) or {}
    if ts.get("mode") == "category" and ts.get("category"):
        return ts.get("category")
    return getattr(config, "persona_role", None)


def _digest(text: Optional[str]) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class ResponsibilityContext:
    """一次 responsibility 評估所需的全部輸入（**pre-entry 與 in-session 共用**）。"""

    config_key: Optional[str]
    context_key: Optional[str]
    rules_text: str
    system_md: str

    @property
    def rules_digest(self) -> str:
        return _digest(self.rules_text)

    @property
    def context_digest(self) -> str:
        return _digest(self.system_md)

    def as_evidence(self) -> "dict[str, Any]":
        """可直接入 evidence／log 的識別資料（不含全文）。"""
        return {"config_key": self.config_key, "context_key": self.context_key,
                "rules_digest": self.rules_digest, "context_digest": self.context_digest}


def _scope_salvage_enabled() -> bool:
    """`FACET_SCOPE_SALVAGE`（預設 off）——語義見 `routers/chat.py` 的同名函式（任務 8.3）。"""
    return os.getenv("FACET_SCOPE_SALVAGE", "false").lower() == "true"


async def build_responsibility_context(
    db_pool: Any, config: Any, *, face: Optional[str] = None,
) -> Optional[ResponsibilityContext]:
    """組出 responsibility 評估上下文；**規則取不到回 None**（呼叫端須誠實降級）。

    ⚠️ 規則缺失回 None 是刻意的：引擎在 `rules_text` 為空時本來就會降級，
    pre-entry 若自行編一份空規則去問模型，等於用一個 production 不存在的語境做判定。
    """
    from services.conversational_rules import load_rules
    from services.system_context import get_system_context

    rules_text = await load_rules(db_pool, getattr(config, "persona_role", None))
    if not rules_text:
        return None
    context_key = responsibility_context_key(config, face)
    system_md = await get_system_context(db_pool, context_key) or ""
    return ResponsibilityContext(
        config_key=getattr(config, "key", None), context_key=context_key,
        rules_text=rules_text, system_md=system_md)


# ── delegation 白名單（slice 2）────────────────────────────────────────────────

def delegate_specs(config: Any) -> "tuple[tuple[str, Optional[str]], ...]":
    """本面向 contract 宣告的可轉交目標及其**語義條件**：`(target, when)`。

    ⚠️ **白名單是 contract 給的，不是模型給的**：`billing_anomaly → contract_closeout`
    這條 edge 原本只存在於 persona 的自然語言裡（實測要讀 LLM 輸出才發現），
    routing 無法使用。本函式讓它成為結構化資料。

    ⚠️ `when` 的身分（2026-08-25 業主定界）：
    **responsibility delegation semantics——供 evaluator 判斷何時可選該白名單 target，
    不是 resolver 自己拿去做 keyword routing 的條件。** 程式**不得**出現
    `if "帳單金額" in query: delegate_to(...)` 這種比對；authority 仍在 evaluator，
    `target` 只是合法 destination，`when` 只補足它的語義。

    背景：第一次 gated validation 3/3 都停在第一跳——模型判了 switch 卻沒填 delegate，
    因為白名單只給英文面向鍵，而規則講的是中文分類名，兩者之間沒有對應。
    """
    spec = getattr(config, "responsibility", None) or {}
    out: "list[tuple[str, Optional[str]]]" = []
    seen: "set[str]" = set()
    for item in spec.get("delegates") or []:
        if isinstance(item, dict):
            target, when = item.get("target"), item.get("when")
        else:
            target, when = item, None
        if isinstance(target, str) and target and target not in seen:
            seen.add(target)
            out.append((target, when if isinstance(when, str) and when else None))
    return tuple(out)


def allowed_delegates(config: Any) -> "tuple[str, ...]":
    """白名單的**鍵**（驗證用）——`when` 一律不參與合法性判定。"""
    return tuple(t for t, _ in delegate_specs(config))


# ── responsibility decision ／ pre-commit resolver（slice 3）────────────────────

#: 一條 delegation chain 最多跳幾次（決定性上界，防無限轉交）
MAX_DELEGATION_HOPS = 3


@dataclass(frozen=True)
class ResponsibilityDecision:
    """一個候選面向對本輪 query 的責任判定。

    ⚠️ 刻意**不是** boolean：舊的 `_preentry_routable` 只回 true/false，
    資訊少到無法據以續走 delegation——「不適用」與「該給誰」是兩件事。
    """

    facet_key: Optional[str]
    verdict: str                      # "stay" ｜ "switch"
    delegate_to: Optional[str] = None
    reason: str = ""                  # 判定來源（含 fail-open 種類）
    evidence: "dict[str, Any]" = None  # type: ignore[assignment]

    @property
    def stay(self) -> bool:
        return self.verdict == "stay"


@dataclass(frozen=True)
class EntryResolution:
    """pre-commit 解析結果。`committed` 為 None ＝ 不進任何面向（走既有 fallback）。"""

    committed_key: Optional[str]
    committed_config: Any = None
    chain: "list[dict[str, Any]]" = None   # type: ignore[assignment]
    stop_reason: str = ""


async def evaluate_responsibility(
    db_pool: Any, config: Any, user_message: str, *, optimizer: Any = None,
) -> ResponsibilityDecision:
    """以**進場前的空狀態**問該面向的責任契約：這輪該不該由你接？

    ⚠️ 空狀態是刻意的、也是保真的：實測捕捉證實**進場輪**送進 brain 的狀態六欄本來就全空
    （collected={}／asked_count=0／recommended=False／無 grounding_note／無 dialog），
    所以把判定提前**不會**因為少了會話狀態而變弱。

    ⚠️ 任何失敗一律 **fail-open（stay）**：規則取不到、brain 失敗、例外——
    維持既有「照舊進場」行為，不因新機制故障而擋掉原本會成立的進場。
    """
    facet_key = getattr(config, "key", None)
    try:
        rctx = await build_responsibility_context(db_pool, config)
        if rctx is None:
            return ResponsibilityDecision(facet_key, "stay",
                                          reason="rules_unavailable_fail_open", evidence={})
        if optimizer is None:
            from services.llm_answer_optimizer import LLMAnswerOptimizer
            optimizer = LLMAnswerOptimizer()
        result = await optimizer.conversational_step_result(
            rctx.rules_text, rctx.system_md,
            {"collected_fields": {}, "asked_count": 0, "recommended": False},
            user_message, delegates=list(delegate_specs(config)) or None)
        if result is None:
            return ResponsibilityDecision(facet_key, "stay",
                                          reason="brain_unavailable_fail_open",
                                          evidence=rctx.as_evidence())
        if result.payload is None:
            # 任務 8.3／需求 5.2：`action` 越界不再連同 `scope` 一起丟。
            # ⚠️ 這條路徑對本模組特別致命——舊碼一律 fail-open 成 stay，
            #    等於**責任委派整條鏈被靜默停用**（delegate 永遠不會發生）。
            if result.scope == "switch" and _scope_salvage_enabled():
                return ResponsibilityDecision(
                    facet_key, "switch", delegate_to=result.delegate_facet_key,
                    reason=f"responsibility_contract_salvaged:{result.reject_reason}",
                    evidence=rctx.as_evidence())
            return ResponsibilityDecision(
                facet_key, "stay",
                reason=f"action_rejected_fail_open:{result.reject_reason}",
                evidence=rctx.as_evidence())
        verdict = "switch" if result.scope == "switch" else "stay"
        return ResponsibilityDecision(
            facet_key, verdict, delegate_to=result.delegate_facet_key,
            reason="responsibility_contract", evidence=rctx.as_evidence())
    except Exception as e:                                     # noqa: BLE001
        print(f"⚠️ [responsibility] 判定失敗，fail-open 照舊進場：{e}")
        return ResponsibilityDecision(facet_key, "stay",
                                      reason=f"error_fail_open:{type(e).__name__}", evidence={})


async def resolve_entry_candidate(
    db_pool: Any, seed_config: Any, user_message: str,
    *, config_lookup: Any = None, optimizer: Any = None,
) -> EntryResolution:
    """沿 delegation chain 解析出**唯一可 commit 的面向**；期間**不建立任何 session**。

    ```text
    seed → responsibility 判定
             ├─ stay          → commit（迴圈結束）
             ├─ switch + 白名單內的 delegate → 換下一個候選，續判
             └─ switch 無可用 delegate       → 不 commit，走既有 fallback
    ```

    決定性護欄：`visited`（同一面向不重評，A→B→A 不成環）與 `MAX_DELEGATION_HOPS`。
    ⚠️ **未知或停用的 delegate 一律 fail closed**（不 commit）——白名單指向不存在的面向
    是設定錯誤，硬進場只會把錯誤藏起來。
    """
    if config_lookup is None:
        from services.conversational_config import config_for_key as config_lookup  # type: ignore

    chain: "list[dict[str, Any]]" = []
    visited: "list[str]" = []
    config = seed_config
    for _hop in range(MAX_DELEGATION_HOPS + 1):
        key = getattr(config, "key", None)
        if key in visited:
            chain.append({"facet_key": key, "verdict": "cycle"})
            return EntryResolution(None, None, chain, "delegation_cycle")
        visited.append(key)

        decision = await evaluate_responsibility(db_pool, config, user_message,
                                                 optimizer=optimizer)
        chain.append({"facet_key": key, "verdict": decision.verdict,
                      "delegate_to": decision.delegate_to, "reason": decision.reason,
                      **(decision.evidence or {})})
        if decision.stay:
            return EntryResolution(key, config, chain, "stay")
        if not decision.delegate_to:
            return EntryResolution(None, None, chain, "switch_without_delegate")

        nxt = await config_lookup(db_pool, decision.delegate_to)
        if nxt is None or not getattr(nxt, "enabled", False):
            chain.append({"facet_key": decision.delegate_to, "verdict": "unavailable"})
            return EntryResolution(None, None, chain, "unknown_or_disabled_delegate")
        config = nxt

    return EntryResolution(None, None, chain, "max_hops_exceeded")
