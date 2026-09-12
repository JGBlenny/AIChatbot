# tests/unit/decision/

**維護級**：對應 spec 已封存（D-003，見 `.claude/DECISIONS.md`）。只保綠、不擴充。

`decision_layer.py` 於 2026-09-12 縮成只剩 `DecisionConfig`——`decide_arbitration`／
`facet_entry_eligible`／`form_trigger_eligible` 三個判定函式產品側已無呼叫端，
連同對拍它們的測試一併刪除（對拍的「原版」是 `routers/chat.py` 的逐字複製，
該檔已刪 ⇒ 等於拿測試自己抄的那份比自己）。

**保留的是門檻契約**：`DecisionConfig` 的 env 鍵名與預設值仍被
`services/agent/tools/kb.py` 與 `services/presales_gate.py` 讀取，⛔ 不得悄悄改。
