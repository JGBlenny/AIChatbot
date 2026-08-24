# face-exit-before-grounding — Research（evidence baseline ＋ 初步 control-flow tracing）

> 2026-08-25｜語言 zh-TW｜**未呼叫任何 OpenAI API**（本檔全部為讀碼與 DB 讀取）
> 本檔是 R1–R4 的工作底稿；**不含 R5 裁決**。下列 F-x 為**初步發現**，不是結論。

## 1. Evidence baseline（自 C4b 移轉，provenance-only）

```text
案例       c4b-diag-01：「幫我查點退帳單金額」→「900003」（fixture 900003，total 7500）
觀測       🎯 trigger_facet_key 'bill_diagnosis' 命中 → 直達面向
           🔀 brain 判定離題(scope=switch) → 關會話、重路由當前訊息
           （落回檢索 → 分類路由再進一次面向）
           🔀 brain 判定離題(scope=switch) → 引擎降級
           → 通用兜底文案（intent_type=None、action_type=direct_answer）
正式分類   face_exit_before_grounding（`conversational-routing-execution` 6.3 diagnostic taxonomy）
原始證據   ../conversational-routing-execution/evidence/c4b-diag01-diagnostic-replay-stdout.log
           ../conversational-routing-execution/evidence/c4b-diag01-diagnostic-replay.json
```

```text
SUPPORTED       brain 的 scope／stay-switch 行為是直接 mechanism
SUPPORTED       trigger_facet_key 不是充分原因——分類路由進場同樣被退出
NOT ESTABLISHED 為什麼 brain 會判 switch     ← 本 spec 的工作面
```

## 2. R2 初步 tracing：producer → inputs → consumer

### 2.1 producer：`scope` 由 **LLM 產生**，不是程式判定

```text
services/llm_answer_optimizer.py  conversational_step()
  system_prompt = f"{system_context_md}\n\n{rules_text}{faces_note}{schema_note}{tool_note}"
  user_prompt   = 【已知欄位】/【asked_count】/【已給過推薦】/
                  【已鎖定資料】(grounding_note)/【最近對話】/【使用者最新訊息】
  model=PRESALES_SYNTH_MODEL(gpt-4o)  temperature=ADVISOR_TEMP(0.4)  max_tokens=400
  response_format=json_object
  → 正規化：data['scope'] = 'switch' if data.get('scope') == 'switch' else 'stay'
```

⇒ **`scope` 的語義完全由 `rules_text`（persona 規則）指示**；程式只做越界正規化。

### 2.2 inputs：`rules_text` 來自 DB 的「對話規則」列

```text
services/conversational_engine.py  prepare()
  rules_text = await self._load_rules(db_pool, config.persona_role)   # 取不到 → return None 降級
  system_md  = await self._get_system_context(db_pool, state.face or _domain_key(config))
  faces      = _domain_faces(db_pool, config)
```

### 2.3 consumer：引擎**直接關會話**

```text
services/conversational_engine.py
  if step.get("scope") == "switch":
      print("🔀 [conversational] brain 判定離題(scope=switch) → 關會話、重路由當前訊息")
      await self._close(session_id)
      return None
```

⇒ consumer 對 `switch` **沒有任何條件**：不看是否為進場輪、不看 entry 是誰決定的、
不看是否已有 grounding。回 `None` 後由 `chat.py` 落回一般流程重路由。

---

## F-1（初步）：producer 的 inputs 裡**沒有** entry 這件事

`conversational_step()` 的 system／user prompt 皆**不含**任何「本會話是被明確指定進入
某 Face」的敘述——沒有 entry 來源、沒有 entry authority、沒有「這是進場第一輪」。
brain 在 `asked_count=0`、`collected={}`、無 dialog、無 grounding_note 的空狀態下，
**只憑 query 對 persona 規則**做 stay/switch 判定。

⚠️ 這是 R3 contract map 的關鍵一格：**entry 的存在本身不在 scope 判定的輸入集合裡**。

## F-2（初步）：兩個 Face 的規則**都**把本 query 判給對方

實查測試庫 `knowledge_base`（`category='對話規則'`）：

```text
pm_bill_diagnosis（id 4252）
  【本輪範疇 scope】是帳單操作可否/原因相關、或在回答你剛問的問題 → scope="stay"。
  **帳單金額組成**/看不到帳單（帳單異常）、繳費入帳（繳費金流排障）、
  其他領域完整新問題 → scope="switch"。不確定 → stay 並澄清。

pm_billing_anomaly（id 3916）
  【本輪範疇 scope】是帳單內容/顯示相關、或在回答你剛問的 → stay。
  **封存/點退帳單處理**、其他領域完整新問題 → scope="switch"。不確定 → stay 並澄清。
```

query「幫我查**點退**帳單**金額**」同時命中兩條 switch 條款：

```text
對 bill_diagnosis   → 「金額組成」→ switch（規則要它交給帳單異常）
對 billing_anomaly  → 「點退帳單處理」→ switch（規則要它交出去）
```

⇒ **brain 沒有違反規則；它嚴格照著 authoritative rules 走。**
⇒ 目前證據指向的不是「brain 判錯」，而是**責任歸屬在規則層面存在缺口**：
   兩個 Face 的規則各自把這句話推給對方。

## F-3（初步）：core question 的前提需要重新查證

Core question 假定該 query「產品上屬於 `bill_diagnosis`」。目前唯一把它綁到
`bill_diagnosis` 的 artifact 是 C4a case set 的 `execution_face` 標籤，
而該檔**自己明文**：

> `execution_face` 是 **test execution context**，不是 routing ownership label；
> **C4a case inclusion SHALL NOT be cited as evidence of query→Face routing ownership.**

⇒ 前提「產品上屬於該 Face」**尚未由任何 production artifact 支持**。
⇒ 這不推翻 F-2 的觀測，但會改變 R5 分流的形狀（見下）。

---

## 3. 對 R5 分流的影響（**提請業主裁示，本檔不自行擴充分類**）

R5 目前只允許四種結論。若 F-2／F-3 在後續查證後成立，實際形狀可能是：

```text
兩套 contract **並非**各自主張 ownership 然後衝突，
而是**兩者都主動棄權**——responsibility gap，不是 authority conflict。
```

此形狀與四種既有結論的對應並不乾淨：

```text
IMPLEMENTATION_DEFECT_CONFIRMED   ✗ 規則載對、brain 照做、consumer 照契約關會話
CONTRACT_DEFECT_CONFIRMED         ？ 端看「兩份規則互推」算不算 contract 之間不一致；
                                     但**不得**用它偷渡「應該改成哪一套產品規則」（R5 窄定義）
AUTHORITY_CONFLICT_CONFIRMED      ？ 字面是「相反決定」；此處是「兩邊都說不是我」
INSUFFICIENT_EVIDENCE             ✓ 目前尚未完成 R1／R3／R4，仍為誠實的當前狀態
```

⚠️ **本檔不自行新增第五類**。是否需要（例如 `RESPONSIBILITY_GAP_CONFIRMED`）由業主裁示。

## 4. 尚未做的（R1／R3／R4 的缺口）

```text
R1  最小 reproduction 尚未建立（目前僅有 C4b 的 e2e 重現）
R2  已完成 producer→inputs→consumer 主幹；尚未列全 system_context 與 faces 清單的實際內容
R3  contract map 尚未成表（entry producer/evidence/authority 那三格尚未逐項填）
R4  六個 deterministic defect candidate 中，
    「載錯 rules」與「responsibility context 未傳入」已有初步證據（F-1／F-2），
    其餘四項（context 截斷／Face identity·state 不一致／reroute 殘留／
    producer-consumer contract mismatch）**尚未證偽**
```

⚠️ 依 R7，「讓 `diag-01` 不再退出」不是本 spec 的 acceptance criterion；
上列缺口補齊、證據足以歸因，才是。
