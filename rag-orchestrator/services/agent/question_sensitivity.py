"""問句側敏感判定（Plan `inputs/plan-walkthrough-fixes-batch3-20260909.md` §3 U2）。

**為什麼要有這個檔**：`fact_class` 由模型自填（`output_schema.AgentOutput.fact_class`），
Verifier 只驗「敏感類配敏感原因」，⛔ 不驗「模型說敏感是不是真敏感」。第二批回測抓到
模型可以把任何一題（例：「要不要催他」）自報成 `sensitive_no_grounding`，藉此躲過
`_apply_handoff_without_lookup`／`_apply_handoff_data_exits` 兩道降級閘、直接轉人。
這裡提供**程式側**的第二意見：只判「使用者問的那一句本身是不是敏感題」。

紀律（Plan §3、feedback「禁止特例修改」）：
- ⛔ 不寫字串特例：樣式一律放在 `config/agent_verifier_rules.json` 的
  `question_sensitive_patterns`（`presales_gate.SENSITIVE` 五類各一組正則），
  程式這一側只做「正規化 → 逐條 search」。改判定＝改規則檔，⛔ 不改這支程式。
- ⛔ 不改寫 `out.fact_class`、⛔ 不動模型輸出：本函式**沒有副作用**，只回 bool。
  答案側的 `SENSITIVE_TOPIC` 掃描維持原樣（縱深防禦）。
- 樣式以**我們自己的產品／服務**為錨（抽成、SLA、資安、法遵、客戶案例），⛔ 不錨在
  物管領域本來就會出現的詞（租金、滯納金、合約到期、續約）——那些是租客／管理者的
  資料題，不是售前敏感題。誤判成敏感的代價＝這一題維持轉人（＝現狀，無新風險），
  誤判成非敏感的代價＝敏感題被降級成固定句，故詞表寧可窄。
"""
from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover - 僅為型別，⛔ 不在執行期建立循環相依
    from services.agent.output_schema import VerifierRules


def _nfkc(text: Optional[str]) -> str:
    return unicodedata.normalize("NFKC", text or "")


def question_sensitive(message: str, rules: "VerifierRules") -> bool:
    """使用者這一句是不是敏感題（封閉樣式表）。純函式、⛔ 無副作用。

    `rules.question_sensitive_patterns` 為空（未配置）⇒ 一律 `False`：這一側的
    `False` 只被拿去當「模型自報敏感但程式看不出敏感」的**准入條件之一**，
    而准入之後走的是兩出口固定句，⛔ 不會吐出任何敏感內容。
    """
    if not isinstance(message, str) or not message:
        return False
    patterns = getattr(rules, "question_sensitive_patterns", None) or []
    text = _nfkc(message)
    for pattern in patterns:
        try:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True
        except re.error:  # 壞樣式 ⛔ 不讓整回合掛掉；當作這一條沒命中
            continue
    return False


__all__ = ["question_sensitive"]
