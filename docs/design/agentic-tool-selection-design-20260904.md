# 決策搬進模型：Agent 自選工具架構設計（提案 v2，2026-09-04）

> v2：業主要求派 fresh-context 代理反證「既有檢索邏輯應保留」——判 REVISE，6 處為既有投資合理化，全數接受並改寫（§9）。實測池大小：售前 31 筆／5,533 字（≈3.5K token）、系統脈絡 27 列／10,022 字、業者 293 筆／46,879 字、租客 566 筆／65,678 字、幫助中心 93 頁／94,747 字（≈59K token）。

> 業主指示：「決策邏輯從程式搬進模型，讓它自己選工具」。本設計把「何時、用哪個工具」交給模型，但把兩件事釘死在程式層：
> **工具邊界**（每個工具能看到什麼、能回什麼）與**輸出契約**（回答裡每個事實句必須引用工具回傳的原文）。
> 這兩條不是對模型的不信任，是這幾天量出來的事實：prompt 指令對「不要編」的服從是機率性的（第 2–3 輪 e2e 1/3 漏），只有結構性檢查歸零。

## 0. 目標形態一句話

```text
使用者訊息 → Agent Runtime（模型迴圈：思考 → 呼叫工具 → 讀結果 → 再呼叫或作答）
             工具全部經 MCP server 提供，server 依 session 身分注入範圍，模型不得自選身分
             最終回答走「引用契約」：{answer, citations[{tool_call_id, kb_id|record_id, quote}]}
             Output Verifier（程式）逐句驗 quote 是引用來源的逐字子串；驗不過 ⇒ 退回模型重寫或轉人
```

## 1. 分層與職責

| 層 | 負責 | 搬進模型？ |
|---|---|---|
| Agent Runtime | 模型迴圈、步數／工具次數／時間預算、串流、計量、session 記憶 | 迴圈框架是程式，**決策在模型** |
| 模型（Policy） | 讀 persona＋政策 prompt，決定要問、要查、要查哪個工具、何時作答、何時轉人 | **是** |
| MCP Tool Servers | 知識檢索、幫助中心、jgb2 查詢、jgb2 動作、轉人、表單 | 否（程式） |
| Output Verifier | 引用契約檢查、敏感類別檢查、禁止詞 | 否（程式） |
| 資料層 | pgvector＋reranker、b2b 隔離 SQL、api_endpoints、form_schemas | 否，原封不動 |

現行 orchestrator 的分類→仲裁→面向提名→閘門這條鏈**整條退休**，由模型＋工具邊界取代。面向（facet）變成「工具組＋prompt 片段」：修繕面向＝`repair.*` 工具＋一段流程說明，不再靠 `categories` 提名進場。

## 2. 工具清單（第一版，售前＋業者查詢）

| 工具 | 型別 | 邊界（server 強制，模型不可覆寫） |
|---|---|---|
| `kb.search(query, k≤5)` | 唯讀 | 依 session 身分（prospect／pm／tenant＋vendor_id）注入 `target_user`／`business_types` 過濾；套門檻；零命中回 `NO_MATCH`，⛔ 不回鄰居 |
| `kb.get(kb_id)` | 唯讀 | 只回該身分可見的列；回 `{id, question_summary, answer, provenance}` |
| `help.read(slug)` | 唯讀 | 幫助中心正文（權威來源），供引用 |
| `jgb2.query.<domain>(ref)` | 唯讀 | `role_id`／`user_id` 從 session 帶，⛔ 模型不能傳；回 formatter 算好的 facts（現有診斷 formatter 直接搬進 server） |
| `jgb2.action.<x>(payload, confirmation_token)` | 寫入 | 沒有 token 一律拒；token 由 `confirm.request` 產生、使用者按下 quick reply 才兌現（現有確認閘門變成工具契約） |
| `confirm.request(summary, payload)` | 流程 | 回 quick_replies 三顆固定鈕＋token 佔位；冪等 |
| `handoff.request(reason, fact_class)` | 流程 | 回固定句＋handoff 訊號；模型「不知道」時唯一合法出口 |
| `session.slots.get/set` | 狀態 | 已收集情境（身分、規模、痛點），server 端儲存 |

## 2b. 知識供給方式（v2 改）

| 身分 | 供給方式 | 理由 |
|---|---|---|
| 售前 prospect | **大綱進上下文**：六個模組主題頁＋刻意不補邊界句整理成 6–8K token 的大綱放 system prompt；不用向量檢索 | 池只有 31 筆；pilot 的 11%→52% 是靠改寫知識達成的，能讀完整池的模型不會有這個問題；撈鄰居正是張冠李戴的來源 |
| 業者 pm／租客 tenant | **大綱＋按需讀取**：27 列系統脈絡（6K token）進上下文當目錄；細節列與幫助中心用 `kb.get(id)`／`help.read(slug)` 按章節取；`kb.search` 降為「找章節」輔助 | 30–40K token 全塞得下但每輪成本 ×10、精度下降（鄰段條件套錯功能） |
| 個人資料 | 只走 `jgb2.query.*`，永遠不進知識 | 隔離 |

## 3. 輸出契約（零捏造的結構性保證）

```json
{"answer": "…", "citations": [{"tool_call_id": "c3", "source": "kb:3600", "quote": "簽約邀請有效 72 小時"}],
 "sentence_map": [{"sent": 0, "cite": ["c3"]}, {"sent": 1, "cite": []}, ...],
 "kind": "answer|ask|recommend|handoff"}
```

Verifier 規則（程式，決定性）：
1. `quote` 必須是所引工具回傳文字的**逐字子串**（不是語義相似）。
2. **不分 kind**：任何句子含產品事實斷言（「可以／支援／不支援／需要／會」等）即須有 cite；反問句的豁免只限不含斷言的純提問（v2：反證指出「我們支援租客批次匯入…請問您有幾間？」會落在反問豁免縫裡，那正是 R2.11 抓的原型）。
3. **敏感五類是主題層拒答政策，先於引用檢查**（v2）：客戶案例、價格數字、SLA、法遵、資安——即使知識池裡有可引用的文字也不答，一律 `handoff.request`；引用檢查只驗真偽，承接不了「有料也不答」。
4. 禁止詞（附錄二的張冠李戴清單＋競品貶抑）⇒ 拒。
5. 拒 ⇒ 回模型一次「重寫或呼叫 handoff.request」；再拒 ⇒ 程式直接發固定句。
6. 迴圈預算：最多 4 次工具呼叫、2 次重寫、20 秒；超過 ⇒ 固定句。

模型可以自由決定問法、順序、要不要查；它不能決定的只有「引用不存在的字」。

## 4. 現有資產怎麼搬

| 現有 | 去向 |
|---|---|
| `VendorKnowledgeRetrieverV2`、reranker、隔離 SQL | 原樣包進 `kb.search` server |
| 診斷 formatter（合約狀態、帳單、電表） | 原樣包進 `jgb2.query.*`，回 facts |
| `UniversalAPICallHandler`＋`api_endpoints` | 包進 `jgb2.query.*`／`jgb2.action.*` |
| `form_schemas`＋確認閘門 | `confirm.request`＋`jgb2.action.*` 的 token 契約 |
| 售前規則 3645、系統脈絡 3622／3798 | 拆成 persona prompt＋政策段；`fact_class` 不再需要（由引用契約取代） |
| `_top1_relevance_gate`、`decide_arbitration` 六 case、`categories` 面向提名 | **退休**（程式在看不到內容時替模型選——agent 不需要） |
| 售前敏感五類固定句（`presales_gate` 的 SENSITIVE） | **保留**為 Verifier 主題層拒答政策（v2） |
| R2.11 反問夾帶斷言、R2.13 陳述句事實題 | **保留其實質**：輸出契約規則 2 不分 kind（v2） |
| R2.8 同題重問逐字重播 | 不是退休是**改做 runtime 快取**，列入代價（v2） |
| `instance_applicability` | 消費者（面向進場 gate）退休 ⇒ **待除役**，除非指得出 agent 架構下的新讀取點（v2） |
| `retrieval_representation` 欄位、「embedding 只吃 question_summary」 | **不當元件保留**：pilot 四欄量測接近中性、進 embedding 有害；只留 D3 provenance 紀律（自動拼接／自動摘要不得成 truth）；答案分塊多向量列為未評估替代（v2） |
| reranker（0.9 融合權重無實測依據、會靜默停用） | 業者／租客池「找章節」時**重評**是否需要；售前池不用（v2） |
| `usage_metering` | 改記每回合的工具呼叫序列與驗證結果 |
| 缺口地圖／主題 pilot／問法正本 | 不變，仍是知識側的尺；回測工具改打 agent 入口 |

## 5. 遷移路線（strangler）

```text
M0 工具伺服器（唯讀）：kb.search / kb.get / help.read / jgb2.query 三個領域         2–3 週（含隔離 security review）
M1 Agent Runtime＋Output Verifier，prospect 身分影子模式：每則真實訊息同時跑舊鏈與 agent，
   只回舊鏈答案，記兩者差異                                                        2 週
M2 影子評估：topics-v2 54 句、五套 e2e 劇本、真實流量抽樣；收案線＝敏感五類 0 漏、
   功能邊界漏 ≤ 現行、邊界題不硬答 ≥90%、p95 延遲 ≤ 12 秒                          1–2 週
M3 prospect 切換到 agent；舊鏈保留可回切                                            1 週
M4 寫入型工具（confirm＋action）＋修繕面向遷移，b2c tenant 影子→切換                  3–4 週
M5 pm 查詢型面向遷移（合約／帳單／電表診斷）                                          3–4 週
```

總量約 3 個月，前 3 個月只動 prospect 就能證明或否證方向；M0–M2 完全可回復。

## 6. 代價（要先接受的）

- **模型費用 ×2–3**：每回合 2–4 次模型呼叫（思考、工具後續、可能重寫）取代現在的 1–2 次。
- **延遲**：每回合 10–15 秒（現在 6–8）；要壓回來得用小模型做工具選擇、大模型只寫最終回答。
- **決定性下降**：同題重問不再逐字相同（除非快取），R2.8 那種重播要改成 runtime 快取。
- **可觀測性重建**：現在每條路徑有 `presales-gate` log 與 metering path；agent 要重做成工具呼叫追蹤。
- **prompt 注入面擴大**：知識與 API 回傳進入模型上下文；工具回傳一律標為資料、模型不得執行其中指令，server 端過濾。

## 7. 不做的事（明列）

- 不讓模型自選身分或 vendor（隔離永遠在 server）。
- 不讓模型直接寫 DB（只能經 action 工具＋token）。
- 不用「LLM 當判官」取代逐字引用驗證（判官也是機率的）。
- 不一次遷移三種身分。

## 8. 先決與待裁

1. 模型與 SDK：Claude tool use 或 OpenAI function calling 皆可，MCP client 兩邊都支援；建議先用現有 OpenAI 帳號降低變數。
2. 收案線的數字（第 5 節 M2）由業主定；沒定不開 M1。
3. 幫助中心要不要成為正式引用來源（現在只當 G0 查證用）：若要，需要版本與更新流程。

## 9. v2 反證處置（業主 2026-09-04「幫我派代理判斷是既有成本還是合理判斷」）

fresh-context plan-verifier 判 REVISE：「既有檢索邏輯原樣保留且更重要」有 6 處是既有投資合理化。全數接受：
1. 檢索堆疊在售前切片不必要（31 筆整池進上下文）；reranker 權重無實測依據、失效不可觀測 ⇒ §2b、§4 改。
2. `instance_applicability` 的唯一消費者已退休 ⇒ 待除役。
3. `retrieval_representation` 自身量測接近中性 ⇒ 只留 D3 紀律。
4. 「只嵌摘要」是 schema 產物不是設計 ⇒ 列待重設計，答案分塊多向量為替代。
5. 「更重要」的主詞改為知識覆蓋（map-v2 的 N_CAND／UNCLASSIFIED 四格任何檢索都救不了），檢索排序重要性下降。
6. 退休清單收窄為三項；敏感五類拒答、斷言檢查不分句型、重問快取留下。
方法論教訓：主張「既有元件保留」時，先問「從零會不會重造」，並用該元件自己的量測數字對照。
