# 需求規格：brain-kb-grounding（Brain 知識庫落地）

> 建立時間：2026-07-20　階段：requirements-generated　語言：zh-TW
> 定位：agent 模式評估（2026-07-20）拍板的 B 區最小增量——在面向對話 Brain 掛載 `search_kb` 工具，讓岔題即答從「憑規則文字與模型印象」升級為「知識庫背書」。同時作為「agent 吃知識庫」的最小實證，成效數據供 A 區（進場路由 agent 化）後續評估參考。
> 對碼前提（已於評估階段查實）：`conversational_step`（`rag-orchestrator/services/llm_answer_optimizer.py:825-909`）為單次 structured-output LLM 呼叫，未掛任何工具；`inline_answer` 岔題即答機制已存在（conversational-repair R3.1），但答案僅來自 rules_text 與模型自身知識，無知識庫查詢。

## 目標形態（本 spec 的北極星）

```
租客（修繕面向、槽位收集中）：「堵塞。對了，這個修理要收費嗎？」
系統：（Brain 判斷岔題 → 呼叫 search_kb 查費用歸屬知識 → 以檢索結果組話）
     「費用部分：若屬自然損壞由房東負擔，人為損壞由租客負擔，實際依維修結果判定。
      那繼續幫您登記：堵塞是浴室的馬桶嗎？」
```

設計判斷：**查了再答**（岔題的事實性回答須知識庫背書）、**查不到就誠實**（回退規則文字指引或告知無法確認，不憑空補答）、**降級即現狀**（工具鏈任何失敗回到今日行為，不會更差）、**寫入 gate 不碰**（工具僅唯讀查詢）。

## 已拍板決策（2026-07-20 評估階段）

1. 工具僅 `search_kb` 一個；SOP 檢索、lookup、API 查詢工具皆範圍外（避免一次開太大）。
2. 工具迴圈上限：每輪 Brain 至多 1 次 `search_kb` 呼叫＋1 次最終生成（至多 2 次 LLM 往返）。
3. 檢索管線（pgvector＋關鍵字＋reranker）零改動，只新增一個內部呼叫方。
4. 不依賴回測現代化：以既有 e2e＋岔題實測集收案（A 區才 gate 於回測現代化）。

## 名詞定義

- **Brain**：`conversational_step` 這次 LLM 呼叫——面向對話的決策核心，輸出 action（ask/converge/confirm）、extracted_fields、next_question、inline_answer。
- **岔題即答（inline_answer）**：面向進行中使用者岔出知識性問題（費用/時程/規定），Brain 在 `inline_answer` 欄位先答、`next_question` 接回槽位收集。
- **search_kb 工具**：掛在 Brain LLM 呼叫上的 function tool；模型判斷需要查詢時發出 tool call，系統以既有知識庫檢索服務執行後將結果回填，模型再產出最終 JSON。
- **工具迴圈**：LLM 回傳 tool call（而非最終 JSON）→ 系統執行檢索 → 結果併回 messages → 再次呼叫 LLM 取得最終 JSON 的過程。
- **安全降級**：工具定義未掛、模型未呼叫、檢索失敗/超時、二次呼叫失敗——任一情況下該輪行為與現行完全一致。

## 範圍

### 範圍內
- Brain LLM 呼叫掛載 `search_kb` function 定義與工具迴圈處理。
- `search_kb` 接上既有知識庫檢索服務，帶會話脈絡過濾（vendor、target_user/persona、business_types）。
- 檢索結果注入後的 inline_answer 落地規則（有命中據實組話、無命中誠實回退）。
- 工具圈計量埋點（token、呼叫率、命中率）。
- 岔題三態（有命中/無命中/檢索失敗）e2e 與岔題實測集。

### 範圍外
- A 區：進場路由 agent 化（gate 於回測現代化，另案）。
- 多工具擴充：SOP 檢索、lookup_tables、API 查詢工具。
- 知識內容補建（岔題常見主題缺知識屬知識營運，走既有迴圈/審核機制）。
- Brain 輸出 schema 變更、引擎 gate 邏輯變更、檢索管線與 embedding 流程變更。
- 回測現代化（另案候選）。

## 需求

### Requirement 1：工具掛載與 Brain 呼叫

**使用者故事**：作為租客，我在報修對話中順口問的費用、規定問題，系統要查過知識庫再回答我，而不是憑印象編一個聽起來合理的答案。

#### 驗收標準（EARS）
1. WHEN Brain 判斷使用者訊息含知識性岔題（費用/時程/規定等事實性問題），THE SYSTEM SHALL 允許 Brain 在產出最終 JSON 前發出 `search_kb` 工具呼叫，查詢詞由模型依岔題內容擬定。
2. THE SYSTEM SHALL 限制單輪工具迴圈至多 1 次 `search_kb` 呼叫；模型連續要求超出上限時 SHALL 以已有資訊強制收斂產出最終 JSON。
3. WHEN Brain 未發出工具呼叫，THE SYSTEM SHALL 維持與現行完全一致的單次呼叫行為與輸出。
4. THE SYSTEM SHALL 維持 Brain 最終輸出 JSON schema 不變（action=ask/converge/confirm、extracted_fields、next_question、inline_answer 及既有驗證規則），工具圈不新增輸出欄位。

### Requirement 2：檢索整合與脈絡過濾

**使用者故事**：作為平台營運方，Brain 查到的知識必須遵守和 FAQ 主路徑同一套業者與角色隔離，不能因為換了呼叫方就漏看過濾。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 以既有知識庫檢索服務實作 `search_kb`（向量＋關鍵字＋reranker 管線零改動），僅新增呼叫方。
2. WHEN 執行 `search_kb`，THE SYSTEM SHALL 帶入當前會話脈絡過濾：vendor、target_user（依 persona_role 對應）、business_types——隔離規則與 FAQ 主路徑一致。
3. THE SYSTEM SHALL 沿用既有 KB 相似度閾值判定命中，不為工具另設寬鬆閾值。
4. THE SYSTEM SHALL 不觸碰 embedding 完整性（question_summary/embedding 生成與檢索流程零改動）。

### Requirement 3：回答落地品質

**使用者故事**：作為租客，我得到的費用答案要和業者知識庫說的一致；系統不確定時要說不確定，而不是給我一個錯的肯定答案。

#### 驗收標準（EARS）
1. WHEN `search_kb` 有達標命中，THE SYSTEM SHALL 使 inline_answer 以檢索結果為據組話，SHALL NOT 引入檢索結果與規則文字之外的事實性陳述。
2. WHEN `search_kb` 查無達標結果，THE SYSTEM SHALL 回退既有規則文字之指引或誠實告知無法確認並指引客服管道；SHALL NOT 由模型憑印象補答事實性內容。
3. WHEN 岔題已回答（無論命中與否），THE SYSTEM SHALL 於同一回覆接回槽位收集（維持既有先答再接行為，conversational-repair R3.1）。

### Requirement 4：安全降級與不變量

**使用者故事**：作為系統維護者，新掛的工具壞掉時，面向對話要跟今天一樣能走完，而且無論如何不能多建一張單。

#### 驗收標準（EARS）
1. WHEN `search_kb` 執行失敗、超時或回傳異常，THE SYSTEM SHALL 以現行行為完成該輪（等同未掛工具），不中斷面向會話。
2. WHEN 工具迴圈的第二次 LLM 呼叫失敗或輸出無法通過既有 JSON 驗證，THE SYSTEM SHALL 沿用既有 Brain 失敗降級（回 None → 引擎安全降級），SHALL NOT 建單。
3. THE SYSTEM SHALL 使引擎寫入 gate 完全不變：required_slots 保底驗證、確認卡機器值決定性判定、明確同意才 execute、冪等防重複建單。
4. THE SYSTEM SHALL 使 `search_kb` 為純唯讀查詢，SHALL NOT 產生任何資料寫入或狀態變更副作用。

### Requirement 5：效能與計量

**使用者故事**：作為架構決策者，工具圈多花的時間和錢要看得見，B 區的成效數據要能支撐 A 區的後續評估。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 將工具圈的全部 LLM token 納入 usage_events 計量（沿用 fire-and-forget 原則），不漏計第二次呼叫。
2. THE SYSTEM SHALL 於使用事件記錄 `search_kb` 呼叫與命中結果，使「岔題輪工具呼叫率／命中率」可直接以 SQL 查得。
3. WHEN 工具迴圈執行，岔題輪端到端延遲增量 SHALL 以 P90 ≤ 3 秒為目標（含一次檢索＋第二次 LLM 呼叫）；上線後未達標 SHALL 觸發設計覆核而非默默接受。

### Requirement 6：回歸與驗收

**使用者故事**：作為系統維護者，這個增量不能弄壞任何現有能力，而且要留下「查庫前 vs 查庫後」的對照證據，讓 B 區的價值判斷有數據。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 使 FAQ 檢索快路徑、診斷面向、無岔題的交易面向對話、表單流程行為與現狀完全一致（回歸驗證）。
2. WHEN 全部測試執行，既有 unit/integration/e2e SHALL 全綠；新增 e2e SHALL 覆蓋岔題三態（有命中／無命中／檢索失敗降級）。
3. THE SYSTEM SHALL 以費用/規定類岔題實測集收案：查庫後答案與知識庫內容一致、無事實幻覺；並與現行憑印象答案對照留檔，作為 B 區價值判定與 A 區評估依據。
4. THE SYSTEM SHALL 維持既有輪數判準：情境 A 類 e2e ≤3 輪不退步（岔題輪計入 P50/P90、不計入 A 類，定義同 conversational-repair）。

## 依賴與假設

- 依賴既有機制：conversational-repair 的 inline_answer 語義與面向會話狀態、既有知識庫檢索服務與閾值、usage_events 計量、引擎降級路徑。
- 假設：`llm_provider.chat_completion` 抽象層可傳遞 OpenAI `tools` 參數與解析 tool_calls〔design 階段確認現況，不支援則於本案補上抽象層透傳〕。
- 假設：`conversational_step`（同步）可呼叫檢索服務〔design 階段確認同步/非同步邊界與呼叫方式〕。
- 假設：岔題常見主題（費用歸屬/時程/規定）於 knowledge_base 已有可命中知識（修繕域 121+ 筆已建）；實測發現缺口時走既有知識營運流程補建，不 gate 本案程式收案。
- 本案為 agent 模式最小驗證：R5.2/R6.3 產出的呼叫率、命中率、事實一致性數據，供 A 區評估引用；A 區另案且前置於回測現代化。
