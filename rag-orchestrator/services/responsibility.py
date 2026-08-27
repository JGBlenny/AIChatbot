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


# ── decision source（裁定 001 ④：technical fail-open ≠ model stay）─────────────
#
# 正本：`.kiro/specs/routing-authority-model/responsibility-governance-decision-record.md`
#
# ```text
# responsibility_contract ／ model stay  → **有** commit authority
# technical_fail_open（brain 例外／schema 或 API 失敗／timeout）
#                                        → compatibility fallback，
#                                          **不得**藉此壓過已成立的 direct-answer candidate
# ```
#
# ⚠️ 為什麼不能只看 `verdict == "stay"`：兩者的 verdict 都是 `stay`，
#    布林值分不出「模型判這輪該由我接」與「評估器壞掉、照舊放行」。
#    若讓後者也能搶走 Knowledge path，等於**技術故障取得 routing authority**。

#: 模型真的判了——`conversational_step_result` 回了可用 payload，verdict 出自模型。
DECISION_SOURCE_MODEL = "model"
#: 技術故障造成的相容性 fallback：規則取不到／brain 無回應／`action` 越界／例外。
#: ⚠️ 這種 `stay` **沒有** commit authority（見 `has_commit_authority`）。
DECISION_SOURCE_TECHNICAL_FAIL_OPEN = "technical_fail_open"
#: `action` 越界但 `scope` 仍可信時的救援（`FACET_SCOPE_SALVAGE`）。
#: 只會產生 `switch`，永遠不會產生 `stay`，因此不涉及 commit authority。
DECISION_SOURCE_CONTRACT_SALVAGE = "contract_salvage"
#: 決定性護欄造成的終止（delegation cycle／未知或停用的 delegate）。
#: ⚠️ **不是** fail-open：這些是設定或圖形問題，硬歸進技術故障率會把設定錯誤洗掉。
DECISION_SOURCE_GUARD = "guard"


@dataclass(frozen=True)
class ResponsibilityDecision:
    """一個候選面向對本輪 query 的責任判定。

    ⚠️ 刻意**不是** boolean：舊的 `_preentry_routable` 只回 true/false，
    資訊少到無法據以續走 delegation——「不適用」與「該給誰」是兩件事。
    """

    facet_key: Optional[str]
    verdict: str                      # "stay" ｜ "switch"
    delegate_to: Optional[str] = None
    reason: str = ""                  # 判定來源的**細節字串**（含 fail-open 種類）
    evidence: "dict[str, Any]" = None  # type: ignore[assignment]
    #: **轉交目標由誰決定**——telemetry 必須分得開，否則看不出模型到底有沒有在做這件事。
    #:   model_delegate      模型自己填了合法目標
    #:   contract_singleton  模型沒填，且契約白名單**只有一個**合法目標 → 決定性補上
    #:   None                沒有轉交（stay，或 switch 但無法解析目標）
    delegate_source: Optional[str] = None
    #: **verdict 出自誰**——`DECISION_SOURCE_*` 之一。
    #: ⚠️ 預設刻意是 `technical_fail_open`：漏填時**失去** commit authority（可回復的錯），
    #:    而不是憑空取得（不可回復的越權）。任何新建構點都必須明寫本欄。
    decision_source: str = DECISION_SOURCE_TECHNICAL_FAIL_OPEN

    @property
    def stay(self) -> bool:
        """**行為述詞**：這條 delegation chain 是否停在本面向。

        ⚠️ **不是 authority 述詞**。fail-open 也會回 True（刻意的：新機制故障
        不得擋掉原本會成立的進場）。要判「能不能搶走 Knowledge path」請用
        `has_commit_authority`，**不得**用本布林值（裁定 001 ④）。
        """
        return self.verdict == "stay"

    @property
    def is_technical_fail_open(self) -> bool:
        """verdict 是技術故障頂上去的，不是模型判的。"""
        return self.decision_source == DECISION_SOURCE_TECHNICAL_FAIL_OPEN

    @property
    def has_commit_authority(self) -> bool:
        """**真實 responsibility stay**——唯一能搶走 Knowledge direct-answer path 的東西。

        裁定 001 ③：`category exists`／`candidate generated`／`scope=switch`／
        fail-open **一律不算**。這裡把那條規則寫成一個述詞，讓呼叫端沒有偷懶的餘地。
        """
        return self.verdict == "stay" and self.decision_source == DECISION_SOURCE_MODEL


@dataclass(frozen=True)
class EntryResolution:
    """pre-commit 解析結果。`committed` 為 None ＝ 不進任何面向（走既有 fallback）。"""

    committed_key: Optional[str]
    committed_config: Any = None
    chain: "list[dict[str, Any]]" = None   # type: ignore[assignment]
    stop_reason: str = ""
    #: **這個 commit 出自誰**——`DECISION_SOURCE_*` 之一；沒 commit 時為 None。
    #: ⚠️ 預設 None 而非 model：漏填要往「失去 authority」的方向錯。
    commit_source: Optional[str] = None

    @property
    def has_commit_authority(self) -> bool:
        """committed 的面向是否由**真實 model stay** 取得（裁定 001 ③④）。

        ⚠️ `committed_key is not None` **不等於**有 authority：fail-open 也會 commit
        （相容性照舊進場），但那不足以壓過已成立的 direct-answer candidate。
        """
        return bool(self.committed_key) and self.commit_source == DECISION_SOURCE_MODEL


def _resolve_delegate(config: Any, verdict: str, result: Any) -> "tuple[Optional[str], Optional[str]]":
    """決定轉交目標：**模型負責語義，程式負責無歧義的 machine decision**。

    P3 第 1 次付費執行（2026-08-26，gpt-4o-mini）實測 3/3：
    模型穩定判對 `scope=switch`，卻把 `delegate_facet_key` 回成**空字串**——
    也就是「知道不該由我接」，但沒有把**唯一合法的 machine key 再複述一次**。
    要模型重複一個決定性映射沒有必要；那一格改由契約解。

    **規則刻意很窄**（業主 2026-08-26 裁定）——三個條件同時成立才補：

    ```text
    verdict == 'switch'
    ∧ 模型**沒填**（delegate_drop_reason == 'missing'：缺鍵／None／空字串／全空白）
    ∧ 契約白名單**恰好一個**合法目標
    ```

    ⚠️ 以下情形**一律不補**，且必須保留各自語義：
      · 白名單有多個 → 不得「隨便選第一個」（那是替模型做選擇）
      · 模型填了**不合法**的 target（`not_allowed`）→ 不得自動改成唯一值
        （那是替模型的錯誤決定背書；它與「沒填」是兩件不同的事）
      · `verdict == 'stay'` → 不轉交
    """
    delegate = getattr(result, "delegate_facet_key", None)
    if delegate:
        return delegate, "model_delegate"
    if verdict != "switch":
        return None, None
    if getattr(result, "delegate_drop_reason", None) != "missing":
        return None, None                      # not_allowed／scope_not_switch：不補
    allowed = allowed_delegates(config)
    if len(allowed) == 1:
        return allowed[0], "contract_singleton"
    return None, None                          # 0 個或多個 → switch_without_delegate


async def evaluate_responsibility(
    db_pool: Any, config: Any, user_message: str, *, optimizer: Any = None,
) -> ResponsibilityDecision:
    """以**進場前的空狀態**問該面向的責任契約：這輪該不該由你接？

    ⚠️ 空狀態是刻意的、也是保真的：實測捕捉證實**進場輪**送進 brain 的狀態六欄本來就全空
    （collected={}／asked_count=0／recommended=False／無 grounding_note／無 dialog），
    所以把判定提前**不會**因為少了會話狀態而變弱。

    ⚠️ 任何失敗一律 **fail-open（stay）**：規則取不到、brain 失敗、例外——
    維持既有「照舊進場」行為，不因新機制故障而擋掉原本會成立的進場。

    ⚠️ 但那種 stay 一律標 `decision_source=technical_fail_open`，
    **沒有** commit authority（裁定 001 ④）：照舊進場是相容性行為，
    不等於「這個面向贏得了這輪的責任」。兩者由 `has_commit_authority` 分開。
    """
    facet_key = getattr(config, "key", None)
    try:
        rctx = await build_responsibility_context(db_pool, config)
        if rctx is None:
            return ResponsibilityDecision(
                facet_key, "stay", reason="rules_unavailable_fail_open", evidence={},
                decision_source=DECISION_SOURCE_TECHNICAL_FAIL_OPEN)
        if optimizer is None:
            from services.llm_answer_optimizer import LLMAnswerOptimizer
            optimizer = LLMAnswerOptimizer()
        result = await optimizer.conversational_step_result(
            rctx.rules_text, rctx.system_md,
            {"collected_fields": {}, "asked_count": 0, "recommended": False},
            user_message, delegates=list(delegate_specs(config)) or None)
        if result is None:
            return ResponsibilityDecision(
                facet_key, "stay", reason="brain_unavailable_fail_open",
                evidence=rctx.as_evidence(),
                decision_source=DECISION_SOURCE_TECHNICAL_FAIL_OPEN)
        if result.payload is None:
            # 任務 8.3／需求 5.2：`action` 越界不再連同 `scope` 一起丟。
            # ⚠️ 這條路徑對本模組特別致命——舊碼一律 fail-open 成 stay，
            #    等於**責任委派整條鏈被靜默停用**（delegate 永遠不會發生）。
            if result.scope == "switch" and _scope_salvage_enabled():
                _d, _src = _resolve_delegate(config, "switch", result)
                return ResponsibilityDecision(
                    facet_key, "switch", delegate_to=_d, delegate_source=_src,
                    reason=f"responsibility_contract_salvaged:{result.reject_reason}",
                    evidence=rctx.as_evidence(),
                    decision_source=DECISION_SOURCE_CONTRACT_SALVAGE)
            return ResponsibilityDecision(
                facet_key, "stay",
                reason=f"action_rejected_fail_open:{result.reject_reason}",
                evidence=rctx.as_evidence(),
                decision_source=DECISION_SOURCE_TECHNICAL_FAIL_OPEN)
        verdict = "switch" if result.scope == "switch" else "stay"
        delegate, source = _resolve_delegate(config, verdict, result)
        return ResponsibilityDecision(
            facet_key, verdict, delegate_to=delegate, delegate_source=source,
            reason="responsibility_contract", evidence=rctx.as_evidence(),
            decision_source=DECISION_SOURCE_MODEL)
    except Exception as e:                                     # noqa: BLE001
        print(f"⚠️ [responsibility] 判定失敗，fail-open 照舊進場：{e}")
        return ResponsibilityDecision(
            facet_key, "stay", reason=f"error_fail_open:{type(e).__name__}", evidence={},
            decision_source=DECISION_SOURCE_TECHNICAL_FAIL_OPEN)


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

    ⚠️ commit 了**不等於**贏得責任：fail-open 的 stay 一樣會 commit（相容性照舊進場），
    但 `commit_source=technical_fail_open`、`has_commit_authority` 為 False。
    要用這個結果去壓過 Knowledge direct answer 的呼叫端，必須讀 `has_commit_authority`。

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
            chain.append({"facet_key": key, "verdict": "cycle",
                          "decision_source": DECISION_SOURCE_GUARD})
            return EntryResolution(None, None, chain, "delegation_cycle")
        visited.append(key)

        decision = await evaluate_responsibility(db_pool, config, user_message,
                                                 optimizer=optimizer)
        chain.append({# ⚠️ evidence 先展開，決策欄位後寫：evidence 是外來 dict，
                      #    不得覆蓋掉 authority 相關的欄位。
                      **(decision.evidence or {}),
                      "facet_key": key, "verdict": decision.verdict,
                      "delegate_to": decision.delegate_to,
                      "delegate_source": decision.delegate_source,
                      "reason": decision.reason,
                      # ⚠️ 結構化欄位，**不是** `reason` 的複述：telemetry 與
                      #    authority 判定都讀這格，不得回頭用字串前綴嗅探 `reason`。
                      "decision_source": decision.decision_source})
        if decision.stay:
            return EntryResolution(key, config, chain, "stay",
                                   commit_source=decision.decision_source)
        if not decision.delegate_to:
            return EntryResolution(None, None, chain, "switch_without_delegate")

        nxt = await config_lookup(db_pool, decision.delegate_to)
        if nxt is None or not getattr(nxt, "enabled", False):
            chain.append({"facet_key": decision.delegate_to, "verdict": "unavailable",
                          "decision_source": DECISION_SOURCE_GUARD})
            return EntryResolution(None, None, chain, "unknown_or_disabled_delegate")
        config = nxt

    return EntryResolution(None, None, chain, "max_hops_exceeded")
