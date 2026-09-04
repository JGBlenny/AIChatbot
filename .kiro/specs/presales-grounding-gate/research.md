# 研究記錄：presales-grounding-gate

> 建立時間：2026-09-04
> 目的：記錄設計階段的技術調查、架構決策與相依性分析
> 發現流程：**light**（擴充既有售前對話路徑、無新第三方依賴）；整合點多數已於 `validation_gap.md` 逐符號對碼，本檔補三項實測與決策落定。

## 摘要

### 調查範圍
售前對話 brain 路徑（`handle_conversational_entry` → `ConversationalEngine.prepare/handle/stream_answer` → `_converge_grounding` → `synthesize_presales_answer`）與無 session 路徑（`_handle_no_knowledge_found`）的知識 grounding、無佐證出口、回應契約與計量落點；以本機 `:8100`（2026-09-04 00:43 image）容器內實測門檻。

### 關鍵發現
- **門檻參數是死的**：`vendor_knowledge_retriever_v2._vector_search` 只 `LIMIT 20`、不比 threshold；真正過濾在 `BaseRetriever.retrieve()` application 端（比 final `similarity`）。現行 `_converge_grounding` 的 `similarity_threshold=0.0` 改任何值都無效。
- **實測 12 題 prospect 池**：`retrieve()` 的 final similarity 把「有知識」與「沒知識」分得很開——真命中 0.53～0.99（免費試用 0.992、競品 0.914、電子發票 0.534），無知識的題 top-1 全在 0.05～0.29；**0.55／0.6／0.65 三個門檻結果完全相同**（3/12 題有 grounding）⇒ D2 取 `DecisionConfig.kb_threshold`（0.55）即可，不必新發明數字。
- **`retrieve()` 與 `_vector_search` 的候選集不同**（reranker 重排）：例如「收租組可以看不到財務數字嗎」vector top 是 3584，`retrieve()` top 是 3601。換路等於換 grounding 來源，屬預期的行為變化，限 prospect。
- **門檻擋不住語義錯配**：「房東對帳單格式可以自己設定嗎？」讓 3596（個人房東 10 戶方案）拿到 0.759——會被當成有佐證去答。這是知識品質問題，⛔ 不是門檻能修的；記為已知限制。
- `usage_events.escape_kind／entry_tier` 兩欄**無任何寫入者**；`set_decision()` 的 `decision_snapshot`（JSONB）是零 migration 的落點。
- 規則文字活值在 DB 3645（覆蓋 code fallback，僅差 markdown 粗體）；改話術要動四處＋DB 一處，且兩列都不在不變量 10／17 母體。

## 研究主題

### 主題 1：售前 grounding 門檻值（D2）

**調查問題**：沿用 0.55（決策層）還是 0.65（檢索候選門檻）？售前池只有 20 筆，門檻會不會把僅有的知識也砍掉？

**研究方法**：
- [x] 現有程式碼分析（`DecisionConfig.load()`、`BaseRetriever.retrieve()`、`_converge_grounding`）
- [x] 效能基準測試：容器內對 12 題（盤查 4 題＋知識池主題 8 題）跑 `retrieve(query, vendor_id=0, top_k=5, similarity_threshold=0.0, target_user='prospect', mode='b2b', return_unfiltered=True)` 取 top-3 final similarity

**發現**（top-1 final similarity）：

```text
有知識的題：可以免費試用嗎 0.992｜你們跟 Bananas 差在哪 0.914｜房東對帳單格式 0.759（⚠️ 命中 3596 個人房東方案，語義錯配）｜電子發票自動開 0.534
沒知識的題：600 戶客戶 0.29｜Excel 匯出 0.259｜舊系統匯入 0.217（top 竟是 3605 修繕；3357 物件批次匯入只有 0.129）｜收租組看不到財務 0.214｜180 間費用 0.183｜水電費 0.07｜資安認證 0.057
追問「那物件跟合約呢？」單句 0.5（3596）——併入上一輪問句後會變，R5 再量
門檻 0.55／0.6／0.65 ⇒ 皆 3/12 題有 grounding（同一組）
```

**結論與建議**：D2 採 **`DecisionConfig.kb_threshold`（env `KB_SIMILARITY_THRESHOLD`，預設 0.55）**，另給 `PRESALES_GROUNDING_THRESHOLD` 覆寫；三個門檻在此池上不可區分，選最低者避免日後知識增加時誤砍。⚠️ 「舊系統資料能匯進來嗎」在門檻下會走 handoff（3357 只有 0.129），與盤查 P1-2 的期待不同——但 DSP-008 未裁前這正是安全行為。

### 主題 2：`retrieve()` 取代 `_vector_search` 的候選差異

**調查問題**：換成 `retrieve()` 後，prospect 的 grounding 來源會不會變？

**發現**：12 題中 5 題 top-3 順序或成員不同（reranker 0.9 權重主導 final）；例：收租組（3584→3601）、Excel 匯出（3597→3335）、資安（3599→3353）。差異只影響 prospect（`CONVERSATIONAL_ENABLED_ROLES={'prospect'}`），一般 b2b 檢索本來就走 `retrieve()`。

**結論與建議**：接受此變化，列入 R6 回歸的「限 prospect」註記；⛔ 不得為了保留舊候選集而自製第二套門檻（validation_gap 缺口 1 選項 B）。

### 主題 3：無佐證出口的落點（brain 路徑 vs 無 session 路徑）

**發現**：brain 路徑在 `handle()`／`stream_answer()` 一律呼叫 optimizer；無 session 路徑在 `_handle_no_knowledge_found` 的 prospect 分支呼叫 optimizer。兩處都要改；串流要比照 `ask` 分支整句一次 yield。決策見 design 決策 2。

### 主題 4：`fact_class` 進 strict schema

**發現**：`CONVERSATIONAL_STEP_SCHEMA` 為 `strict: True`＋`additionalProperties: False`＋`required` 全列 ⇒ 新欄位必進 `required`；`BRAIN_STRICT_SCHEMA` 關閉時走 `json_object`，欄位可能缺。`_parse_conversational_step` 是唯一正規化點。gpt-4o-mini 對 strict enum 的遵從率**未量**（開放問題 Q1）。

### 主題 5：`handoff` 訊號的透傳與前端消費

**發現**：後端兩條透傳路已有先例（`quick_replies`）；jgb2 `HelpAssistantController@chat` 原樣透傳 body；前端 `useChat.ts` 只讀 `answer／quick_replies／form_triggered`（非串流）與 SSE `metadata` 同三鍵 ⇒ `handoff` 會到前端但沒人讀，按鈕是切片 2 的工。

## 技術選型

### 選型 1：門檻過濾在哪一層

| 方案 | 優點 | 缺點 |
|------|------|------|
| A `retrieve()`（application 端過濾 final similarity） | 與全系統同一把尺；含 reranker；`_make_kb_search` 已示範 | 多 keyword fallback／boost／reranker 延遲；候選集會變（主題 2） |
| B `_vector_search`＋自己比 `vector_similarity` | 候選集不變 | 發明第二套門檻語義（純向量分 vs final）；tech.md 明定 `KB_SIMILARITY_THRESHOLD` 比 final |

**最終選擇**：A。

### 選型 2：計量落點（R7）

| 方案 | 優點 | 缺點 |
|------|------|------|
| a `set_decision({"presales": {...}})` → `decision_snapshot` JSONB | 零 migration、零新欄位、可放多鍵 | 查詢要 `->>`；與決策層快照同欄（淺層合併，鍵名要獨立） |
| b 補 `escape_kind` setter | 欄位已在、語義貼近 | 該欄原意在封存 spec 內（D-003 ⛔ 不得列為前置必讀）；補 setter 等於重新定義它 |
| c `set_comparison(decision_case="presales_handoff:<fc>")` | 可直接 GROUP BY | 覆蓋既有 `decision_case`（一般檢索路徑寫 `b2b_knowledge_only` 等）——brain 路徑目前不寫，但語義混用 |

**最終選擇**：a，鍵名 `presales`（獨立命名空間）。

### 選型 3：固定句與 channel 的來源（D1）

| 方案 | 優點 | 缺點 |
|------|------|------|
| code 常數 | 決定性、可測 | 改文案要 rebuild |
| `ConversationalConfig` 新欄位 `handoff_message`／`handoff_channel`（DB metadata 供給、code 保底） | 後台可編，沿用 `answer_rules` 的外移慣例 | 多兩個設定鍵 |

**最終選擇**：DB 供給＋code 保底（與 `answer_rules／cta_rules` 同款）。

## 相依性分析

### 外部 API 與服務
| 服務名稱 | 用途 | 注意事項 |
|---------|------|---------|
| OpenAI gpt-4o-mini（既有 `llm_provider`） | brain 判定（strict schema）、有 grounding 時合成 | 無佐證路徑**不呼叫**；strict enum 遵從率待量 |
| jgb2 `/api2/assistant/chat` 代理 | 透傳 | 原樣透傳 body，無需改 |

### 函式庫與套件
無新增。

## 現有程式碼分析

**檔案位置與符號**：
- `routers/chat.py`：`handle_conversational_entry`、`_maybe_conversational_freetext`、`_conversational_respond`、`_conversational_to_response`、`_conversational_sse`、`_handle_no_knowledge_found`、`VendorChatResponse`
- `services/conversational_engine.py`：`prepare`、`handle`、`stream_answer`、`_converge_grounding`、`_finalize_converge`、`_note_turn`、`_synth_context`、`_make_kb_search`
- `services/llm_answer_optimizer.py`：`CONVERSATIONAL_STEP_SCHEMA`（模組層）、`conversational_step_result`、`_parse_conversational_step`、`_build_presales_synth`、`synthesize_presales_answer(_stream)`
- `services/conversational_config.py`：`ConversationalConfig`、`PRESALES_ANSWER_RULES`、`PRESALES_CTA_RULES`、`PRESALES_CONFIG`
- `services/conversational_rules.py`：`CONVERSATIONAL_RULES_BY_ROLE['prospect']`、`load_rules`
- `services/decision_layer.py`：`DecisionConfig.load().kb_threshold`
- `services/usage_metering.py`：`set_decision`、`_meter_path`
- 測試先例：`tests/unit/conversational/test_presales_grounding_req.py`、`test_brain_strict_schema_req.py`（`_opt(llm_json)`）、`test_presales_compliance_req.py`

**整合點**：
1. `_converge_grounding` vector 路改 `self.retriever.retrieve(...)`，回傳多 `empty／hits`。
2. `prepare` 的 converge decision 加 `fact_class／grounding_empty／prev_turn`。
3. `handle`／`stream_answer` 加 handoff 分支（不進 optimizer）。
4. `_handle_no_knowledge_found` prospect 分支改固定句＋handoff。
5. `VendorChatResponse.handoff`、`_conversational_to_response`、`_conversational_sse` metadata。
6. `CONVERSATIONAL_STEP_SCHEMA` 加 `fact_class`；`_parse_conversational_step` 正規化。
7. 規則文字四處＋DB 3645／3798（業主 SQL）。

## 效能考量

| 指標 | 目標值 | 測試方法 | 備註 |
|------|--------|---------|------|
| 無佐證路徑 P95 | 低於現行事實題（現行含一次 LLM 合成） | :8100 連打 5 次計時 | 省掉合成呼叫；brain 判定仍在 |
| 有 grounding 路徑 | 不多於現行＋`retrieve()` 差額 | 同上 | reranker 若靜默停用（`project_retrieval_ranking_findings`）final 會退回 vector 分，門檻語義變——列風險 |

## 安全性考量

- 不新增外呼；無佐證路徑不把使用者原句送 LLM。
- `handoff.message` 為固定句，⛔ 不含使用者輸入回顯（避免 prompt 注入回流）。
- 日誌只記 `fact_class／hits／threshold／reason`。

## 風險登記

| 風險 | 類型 | 影響 | 機率 | 緩解策略 | 狀態 |
|------|------|------|------|---------|------|
| reranker 靜默停用 ⇒ final 退回純向量分，0.55 門檻語義漂移 | 技術 | 中 | 中 | 記錄 `score_source` 進 `presales` 快照；不變量稽核已有 reranker 健檢項可對照 | 開放 |
| strict schema 加 enum 讓 brain 失敗率上升 ⇒ 整輪降級落一般檢索 | 技術 | 高 | 中 | 20 題量降級率；失敗時 `fact_class=other` 不阻斷 | 開放（Q1） |
| 語義錯配仍過門檻（3596 對「對帳單格式」0.759） | 資料 | 中 | 中 | 記為已知限制；靠知識層補條目與 `question_summary` 品質 | 開放 |
| 「舊系統資料能匯」變 handoff，與盤查 P1-2 期待相反 | 產品 | 中 | 高 | DSP-008 裁決後補知識；未裁前 handoff 是正確行為 | 開放 |
| 規則文字改動破壞既有測試釘字 | 技術 | 低 | 高 | 保留「轉專人」「不報價」「不杜撰」字樣 | 已緩解（設計） |

## 開放問題

### Q1 gpt-4o-mini 在 strict schema 加 `fact_class` enum 後的遵從率與降級率
**影響範圍**：R3、整體可用性。**決策狀態**：✅ 已量（`perf-20260904.md` §3）——20 題降級 0/20，敏感五類各 1 題全判對。

### Q3 門檻 0.55 擋掉「電子發票」（final 0.534）——D2 要不要調 0.5
**影響範圍**：R1.2、盤查正面項 3。**資料**：無知識題 top-1 ≤0.337、有知識題 ≥0.534；0.5 多救回 1 題、邊距 0.16。⚠️ 線上實際生效值是 compose env `KB_SIMILARITY_THRESHOLD=0.65`（非程式預設 0.55；verifier A1），0.55～0.65 對 20 題結果相同。**決策狀態**：待業主（`PRESALES_GROUNDING_THRESHOLD` env 覆寫即可）。

### Q4 延遲 NFR 未達：無佐證路徑安靜 median 8.31 s vs 改前 6.35 s
**影響範圍**：非功能約束「無佐證路徑 P95 低於現行」。**根因**：`retrieve()` 的 keyword fallback＋reranker 比 `_vector_search` 多 1.5–2 s，抵銷省下的合成 LLM。**選項**：`enable_keyword_fallback=False`／接受／查 reranker 冷啟。**決策狀態**：待業主。

### Q2 jgb2 切片 2 的 `channel` 實際值與按鈕呈現時機
**影響範圍**：D1、R4.5。**決策狀態**：待 jgb2。

## 時間軸

| 日期 | 活動 | 結果 | 後續行動 |
|------|------|------|---------|
| 2026-09-04 | 根因對碼（22 份 canon-audit）、gap 分析、容器內 12 題門檻掃描 | 門檻參數是死的；0.55～0.65 不可區分；`retrieve()` 候選集會變 | 業主核 design；實作 R1→R2→R4→R3→R5 |

## 參考資源

- 根因：`docs/presales-assistant-rootcause-20260904.md`；盤查：`docs/presales-assistant-quality-audit-20260902.md`
- 落差：`validation_gap.md`；需求：`requirements.md`（v2）
- steering：`tech.md`「Retriever Pipeline 分數欄位」「閾值對應欄位」；`dialogue.md`；`testing-code.md`
