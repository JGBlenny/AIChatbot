# 任務 8 落實紀錄：`conversational_step` 契約分層（需求 5.2）

> 2026-08-26｜語言 zh-TW｜零 OpenAI 呼叫、未碰 staging／production
> **8.1–8.4 完成；8.5 的實作完成但上線受 6.3 的 CLOSED gate 約束（gate 擋 deploy，不擋 development）。**

## 一、修的是什麼

舊碼在 `llm_answer_optimizer.conversational_step` 內的順序是：

```python
if data.get('action') not in ('ask', 'converge', 'confirm'):
    return None          # ← 同一包裡正確的 scope=switch 一起被丟掉
...
data['scope'] = 'switch' if data.get('scope') == 'switch' else 'stay'   # 永遠走不到
```

實測：問「停用租客帳號」時 brain **5/5 正確輸出 `scope=switch`**，
但因為它把 `"switch"` 也填進了 `action`，整包被丟棄。呼叫端只看得到「引擎降級」，
看不到「使用者其實已離題、該換面向」。

⚠️ 對 `services/responsibility.py` 特別致命：該模組在 `data` 為 None 時 fail-open 成 `stay`
⇒ **責任委派鏈整條被靜默停用**，delegate 永遠不會發生。face-exit 那條線要啟用的能力，
在這個 validator 上就先斷了。

## 二、怎麼修（8.1／8.2）

```text
新增 StepResult（frozen dataclass）
  payload             action 合法時的完整輸出；否則 None
  scope               'stay' | 'switch'，**永遠有值**
  face／delegate_facet_key／reject_reason

_parse_conversational_step(data, delegates) → Optional[StepResult]
  ① scope 正規化 → ② face 帶出 → ③ delegate 白名單過濾 → ④ **最後**才驗 action
```

不變量（測試逐條鎖住）：

```text
· 回傳非 None ⇒ scope ∈ {'stay','switch'}
· payload 非 None ⇒ payload['action'] ∈ VALID_ACTIONS
· payload 內**永不**出現 action=None 或越界值（不製造半合法狀態）
· 硬失敗（非 dict）→ 回 **None**（非 StepResult）：語義是「模型連可解析內容都沒給」
```

介面分層：`conversational_step_result()` 為主要介面；
`conversational_step()` 降為相容層（`return result.payload if result else None`），
**簽章與回傳形狀逐位一致**，現有 caller 零感知。

## 三、呼叫端遷移（8.3）

```text
routers/chat.py::_preentry_routable        GATE ＋ SALVAGE 二重保護
services/conversational_engine.py          payload None ＋ scope switch → 依 switch 語義關會話重路由
services/responsibility.py                 payload None ＋ scope switch → verdict switch（帶 delegate）
```

`FACET_SCOPE_SALVAGE`（**預設 off**）只控制**呼叫端要不要行動**——
解析層一律照新順序執行，**回退時不需回退解析層**。

歸因（attribution）改善，即使旗標關著也生效：

```text
舊：reason="brain_unavailable_fail_open"（分不出「模型沒回」與「action 越界」）
新：reason="action_rejected_fail_open:action_out_of_range"
    旗標開啟時：reason="responsibility_contract_salvaged:action_out_of_range"
```

## 四、測試（8.4）

`tests/unit/conversational/test_step_contract_layers_req.py`（**16 passed**）：
三條不變量、delegate 三種情形、相容層逐位一致、旗標兩態、
以及 `_preentry_routable` 的 GATE×SALVAGE 四象限。

替身遷移：新增 `tests/support/brain_stub.py`，把 15 個測試檔的 brain 替身**同時**接上
新舊兩個介面（斷言逐位不變），並將 18 處 `conversational_step.assert_*`
改指向 `conversational_step_result`。

基線：unit **1389 passed / 13 failed**（13 筆全為既有 `_meta` known-red）。

## 五、8.5：上線狀態

```text
實作         ✅ 完成
獨立驗收     ⏸ 需在 FACET_SCOPE_SALVAGE=true 下跑一次面向 e2e（付費，未執行）
上線         ⛔ 受 6.3 的 production-facing gate **CLOSED** 約束
兩項待確認 delta（需求 5.2 明列）：
  · decision_snapshot 歸因由 facet_engine_degraded 改為 switch 語義
  · _preentry_routable 由 fail-open 轉為實際擋下進場
     （受 PREENTRY_ROUTABILITY_GATE 與 FACET_SCOPE_SALVAGE 二重保護）
```

⚠️ **本修復須獨立上線，不得與其他改動同批**（需求 5.2 明文）。
