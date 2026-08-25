"""resolver hop 的 **raw output attribution**（測試側，零 production 變更）。

## 為什麼需要

gated validation v1／v2 兩輪都得到同一個正規化後的結果：

```text
scope = switch      delegate_to = None
```

但這一個 `None` 底下至少壓著三種**完全不同**的問題：

```text
A missing           模型根本沒輸出 delegate 欄位   → prompt／output contract 不足
B wrong_key         輸出了，但鍵名不同             → schema／parser contract mismatch
C not_allowed       有 delegation intent，但值被白名單／正規化丟掉
```

不先分開，下一輪付費執行只會再看到一次 `None`。

⚠️ **本模組只讀證據、不改行為**：分類依據是 provider 的原始 JSON ＋ 白名單 ＋
`conversational_step` 正規化後的輸出，三者並列比對。**不得**用來替代 production 的正規化邏輯。
"""

import json
from typing import Any, Optional, Sequence

#: 可能被模型誤用來放轉交目標的鍵（`face` 是 schema 既有欄位，故只在**值命中白名單**時才算誤放）
#  ⚠️ 不放裸的 "next"——`next_question` 是 schema 既有欄位，會誤報。
_DELEGATE_ISH = ("delegate", "face", "facet", "target", "handoff", "hand_off",
                 "transfer", "route", "switch_to", "next_face", "next_facet")

#: `normalization_drop_reason` 的值域（事前定死，不臨場擴充）
DROP_REASONS = ("kept", "missing", "wrong_key", "not_string", "not_allowed", "scope_not_switch")


def _as_payload(raw: Any) -> "dict[str, Any]":
    """provider 原始回傳 → dict（無法解析回空 dict）。"""
    if isinstance(raw, dict) and "content" in raw:
        raw = raw.get("content")
    if isinstance(raw, str):
        try:
            return json.loads(raw or "{}")
        except Exception:
            return {}
    return raw if isinstance(raw, dict) else {}


def delegate_related_keys(payload: "dict[str, Any]") -> "list[str]":
    """原始 payload 中所有**可能承載轉交目標**的鍵（含 delegate_facet_key 本身）。"""
    return [k for k in payload
            if k == "delegate_facet_key" or any(m in k.lower() for m in _DELEGATE_ISH)]


def classify_delegate_drop(
    raw: Any, allowed: Sequence[str], normalized: Optional["dict[str, Any]"] = None,
) -> "dict[str, Any]":
    """把「為什麼 normalized 沒有 delegate」歸因到單一原因。

    判定順序（**不得改**，否則歸因會漂）：
      ① normalized 已保留 → kept
      ② 有 `delegate_facet_key` → not_string ／ scope_not_switch ／ not_allowed
      ③ 沒有該鍵，但**別的鍵的值命中白名單** → wrong_key（模型放錯欄位）
      ④ 其餘 → missing
    """
    payload = _as_payload(raw)
    allowed_set = {a for a in (allowed or [])}
    norm = normalized or {}
    raw_scope = payload.get("scope")
    normalized_scope = norm.get("scope")

    evidence = {
        "raw_model_payload": payload,
        "raw_scope": raw_scope,
        "raw_delegate_related_keys": delegate_related_keys(payload),
        "normalized_scope": normalized_scope,
        "normalized_delegate_facet_key": norm.get("delegate_facet_key"),
        "allowed_delegates": list(allowed or []),
    }

    if norm.get("delegate_facet_key"):
        evidence["normalization_drop_reason"] = "kept"
        return evidence

    if "delegate_facet_key" in payload:
        value = payload["delegate_facet_key"]
        if not isinstance(value, str):
            reason = "not_string"
        elif (normalized_scope or raw_scope) != "switch":
            reason = "scope_not_switch"
        else:
            # 白名單外＝正規化丟掉；白名單內卻沒留下＝parser 疑點，兩者都記 not_allowed，
            # 但 dropped_value 與 allowed_delegates 並列，人工一眼可辨。
            reason = "not_allowed"
        evidence["normalization_drop_reason"] = reason
        evidence["dropped_value"] = value
        return evidence

    misplaced = [(k, v) for k, v in payload.items()
                 if k != "delegate_facet_key" and isinstance(v, str) and v in allowed_set]
    if misplaced:
        evidence["normalization_drop_reason"] = "wrong_key"
        evidence["misplaced_in"] = [k for k, _ in misplaced]
        evidence["dropped_value"] = misplaced[0][1]
        return evidence

    evidence["normalization_drop_reason"] = "missing"
    return evidence


def build_hop_evidence(candidate_face: str, raw: Any, allowed: Sequence[str],
                       normalized: Optional["dict[str, Any]"] = None) -> "dict[str, Any]":
    """一跳的完整 attribution 紀錄（八欄，供 evidence 檔逐跳保留）。"""
    return {"candidate_face": candidate_face,
            **classify_delegate_drop(raw, allowed, normalized)}
