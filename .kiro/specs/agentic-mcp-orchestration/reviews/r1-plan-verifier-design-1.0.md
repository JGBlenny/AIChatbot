# r1 plan-verifier — design 1.0（2026-09-04）

REVISE

[P1] `jgb2.query.<domain>` 契約引用的 `services/jgb/<domain>.build_<domain>_facts(row, user_question)` 在程式中不存在——實際是 12 個以中文面向名為鍵的 builder，分散在 5 個模組的獨立註冊表 — 證據：`rag-orchestrator/services/jgb/contracts.py:FACE_BUILDERS`、`bills.py:BILL_FACE_BUILDERS`、`accounts.py:ACCOUNT_FACE_BUILDERS`、`iot.py:METER_FACE_BUILDERS`、`estates.py:ESTATE_FACE_BUILDERS`；正對照組：`grep "def build_late_fee_facts"` 命中、`grep "def build_bills_facts\|def build_contracts_facts"` 全無 — 修法建議：映射改成 `(domain, face) → builder`，列出五張既有註冊表與其鍵。
[P1] `jgb2.query` 少了「誰挑 face」：現行 face 來自 `categories` 面向提名，R12.1 明列退休，design 未給替代 — 證據：requirements R12 §1；`bills.py:face_bill_response` — 修法建議：face 提升為封閉 enum 參數。
[P1] `kb.get` 宣稱 import 謂詞組件，但該檔沒有可 import 的謂詞——隔離 SQL 內嵌在 `_vector_search`／`_keyword_search` 的 f-string — 修法建議：抽出 `build_visibility_predicate()` 三方共用。
[P1] R7.3（回答含專人／真人／客服／沒有資料須附 handoff）無承接元件 — 證據：`presales_gate.py:HANDOFF_WORDS`／`scan_handoff_mentions` 存在 — 修法建議：Verifier 出口加後置掃描。
[P1] R3.4「citable=false 不接受為引用」無承接 — 修法建議：Verifier 加 citable 判定與拒因。
[P1] R12.1 退休清單全無承接 — 證據：`routers/chat.py`／`services/decision_layer.py` 兩符號存在 — 修法建議：列 agent 路徑不呼叫的舊鏈符號與檢查方式。
[P2] R6.4「程式端數字／機構名檢查」無規則來源。
[P2] quote 比對目標兩說（`text_for_model` vs `Provenance.text`）。
[P2] 預算計數規則未定；session 級回退與單回合重寫關係未定義。
[P2] `ToolSpec.audiences` 值域未定；R5.2 prospect 不呼叫 `kb.search` 與無條件註冊未對齊。
[P2] M1／M2／M3／M5 無 done 條件；`stage` 只含 M0／M4。
[P2] D2／D3／D5 無處置紀錄。
[P2] 決策 7「不讀 retrieval_representation」與 `kb.search` 走 `retrieve()`（含 reranker `scoring_surface`）矛盾；G11 未裁。
[P2] `audience` 與 `target_user`／`mode`／`role_id` 無映射規則。
[P3] `DOMAIN_BUILDERS` vs `FACE_BUILDERS` 名稱不一；`PRESALES_HANDOFF_MESSAGE` 實在 `conversational_config.py`；API 節 `GET /mcp` 方法不符。

## 已確認成立（對碼吻合）
`app.py` lifespan 存在（`Mount` 需新增 import）；`chat.py` 四符號存在；`retrieve` 在 `base_retriever.py`，`target_user`／`mode` 走 `**kwargs`；`JGBSystemAPI` 23 支 `get_*`；builder 皆 `(row, user_question="")`，例外 `estates.build_estate_status_facts(estate, detail=None, user_question="")`；`payments.py`／`invoices.py`／`repairs.py`／`subscription.py` 無 `build_*_facts`；`OpenAIProvider.async_client` 存在；`presales_gate` 四符號、`conversational_config` 兩符號存在；`_QR_SUBMIT` 存在；`form_sessions.collected_data`／`usage_events.decision_snapshot` 使用中；`help_center_pages` 查無（與新表一致）；`system_context.get_system_context` 存在；`DecisionConfig`／`_top1_relevance_gate` 存在；需求 ID 反向檢查無懸空。
