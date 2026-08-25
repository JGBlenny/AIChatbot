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
