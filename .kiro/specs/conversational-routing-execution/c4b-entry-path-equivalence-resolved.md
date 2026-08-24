# C4b 供裝前置：直達進場等價性——**已解除**

> 2026-08-25｜語言 zh-TW｜**零 OpenAI 成本**（讀碼 ＋ DB 查值 ＋ 重跑既有測試）。
> 解除的是 `c4b-phase-inventory.md`（fdb75fe）末段「一個尚未解除的供裝前置條件」。

## 結論（先講）

`trigger_facet_key` 直達進場與分類路由出口，在 **C4b 的驗證標的**（grounding → 真 brain → answer）
上**等價**——但等價**只對 `bill_diagnosis`／`billing_anomaly` 成立**，且**依賴一個配置前提**：
這兩個面向的 `grounding_scope` **未宣告** `enabled_gate` 與 `prefill_api`。

⚠️ 盤點當時把此題記為「未確認」，是**盤點的帳面落後**，非事實未查：
任務 2.5／2.4 早已各留一支測試鎖住兩側前提（見下），本次只是**查證它們仍然成立**。

## 證據

### E1｜程式側：兩條路徑收斂到**同一個呼叫**

```text
分類路由出口   routers/chat.py:1201-1206
               宣告 enabled_gate 或 prefill_api → _seed_repair_facet
               否則                            → _conversational_respond(start_if_absent=True, config=cfg)
直達進場       routers/chat.py:1009-1027（Step 0.4，chat.py:4158-4165 派發）
               一律 → _seed_repair_facet(request, req, config)
```

對「兩鍵皆未宣告」的面向，`_seed_repair_facet`（chat.py:976-1006）三個前置全為 no-op：

| 前置 | 判定點 | 未宣告時 |
|---|---|---|
| gate | `_repair_gate_open` → `_gate_switch_key` | `switch_key` 為 None → **恆 True**，不讀 vendor_configs |
| Vision | `_recognize_repair_image` | 無 `image_urls` → **None**，不打 Vision |
| prefill | `_run_repair_prefill` | 無 `prefill_api` → **None**（早退，不碰 jgb_api） |

`prefill` 為 None → 不進降級分支 → 落到
`_conversational_respond(request, req, start_if_absent=True, config=config, prefill=None)`，
與分類路由出口**逐參數相同**（後者 `prefill` 取預設值 None，簽章見 chat.py:1358）。

### E2｜配置側：DB 實查兩個面向的宣告

2026-08-25 於測試庫 `aichatbot_test` 查 `knowledge_base` 中 `category='對話規則'` 全 12 列：

```text
bill_diagnosis   (id 4252) grounding_scope: select=api / endpoint=jgb_bills /
                 secondary_call=jgb_bill_detail / requires_instance_reference=true
                 → **無 enabled_gate、無 prefill_api**
billing_anomaly  (id 3916) grounding_scope: select=api / endpoint=jgb_bills
                 → **無 enabled_gate、無 prefill_api**
repair_create    (id 4415) → **兩鍵皆宣告**（enabled_gate=repair_enabled /
                 prefill_api=get_tenant_contracts）→ **不等價，本結論不得外推**
```

兩者 `enabled` 皆為 True 且 `key` 即 registry 鍵 → `config_for_key()`（by_key）命中，
直達進場的 registry 查找可達（`services/conversational_config.py`：`config_for_key` → `get_config` → `_cache["by_key"]`）。

### E3｜既有測試重跑（本次實跑，非引述）

```text
scripts/run-tests.sh unit tests/unit/conversational/test_facet_entry_path_equivalence_req.py
  → passed=3  failed=0  gate_skipped=0  env_skipped=0     （程式側前提）
scripts/run-tests.sh integration tests/integration/conversational/test_facet_entry_equivalence_config_req.py
  → passed=4  failed=0  gate_skipped=0  env_skipped=0     （配置側前提，真連 DB）
```

⚠️ 兩檔的 `skipped=0` 是重點：**不是 skip 出來的綠**。
配置側那支同時鎖住「by_key 與 by_category 解析到**同一個物件**」——
兩路若拿到不同 config 實例，即使欄位同值也可能因快取時機分歧。

## 直達進場**不會**做的四件事（等價的邊界，必須寫進 C4b 的 claim ceiling）

```text
① 檢索 ＋ top-1 門檻 ＋ 分類命中     ← 這正是要省掉的（供裝降級的來源），
                                       故 C4b **不得**主張任何 routing 結論
② _instance_gate_decision／_preentry_routable
   （bill_diagnosis 宣告 requires_instance_reference=true）→ 直達完全繞過此閘
③ 進場埋點：_meter_decision(routing_verdict="enter_facet")／usage_metering set_facet/set_path
   → 直達路徑不產生這些觀測；C4b 的尺**不得**斷言 decision snapshot
④ 有圖時的 Vision（直達會打、分類路由對非交易面向不打）
   → C4b 案例**一律不帶 image_urls**，此差異即不存在
```

①②③④ 皆**不改變** `_conversational_respond` 之後的行為，故不影響 C4b 的驗證標的。

## 供裝結論（本題的目的）

**可由「完整 KB ＋ embedding」降為：**

```text
必須                面向設定列（對話規則 id 4252／3916，已在測試庫）
                    per-領域系統脈絡（services/system_context，鍵＝topic_scope.category：
                      「條件診斷：帳單」／「帳單異常」；C4a 已實證可載入）
                    面向的 answer_rules／cta_rules（隨設定列走）
                    JGBMockTransport 的 fixture（900001/900002/900003，4.4 已凍結）
不再必須            KB 語料達進場門檻、以及為此所需的 embedding 重建
```

⚠️ **`kb_search` 工具不會掛上**（2026-08-25 讀碼確認，這使供裝降級比原先估計更乾淨）：
`conversational_engine.py:672-676` 明文「kb_search 僅注入交易面向（`_tx`）」，
而 `_is_transaction_scope()` 的定義是 `grounding_scope` 宣告 `execute_endpoint`
（同檔 :306-308）。`bill_diagnosis`／`billing_anomaly` **皆未宣告** `execute_endpoint`
（見 E2 的 DB 實查）→ 兩者的 brain **拿不到** `kb_search` 工具，
故 C4b 的整條路徑**不會**觸發 `retrieve_knowledge_hybrid`，也就不需要 embedding。

⚠️ **但仍有一項非 KB 的必要供裝**：`prepare()` 會載入該 persona 的對話規則
（`_load_rules(db_pool, config.persona_role)`，:668-670）；**取不到即回 None 降級**，
整輪對話不會發生。故 `pm_bill_diagnosis`／`pm_billing_anomaly` 的規則文字必須在庫內
（即上表兩列 `對話規則` 知識的 `answer` 欄）。

## 失效條件（寫死在測試裡，不靠人記得）

`tests/integration/conversational/test_facet_entry_equivalence_config_req.py`：
任何人只要替這兩個面向補上 `enabled_gate` 或 `prefill_api`（**即使程式完全沒動**），
該檔立刻紅，並明言「C4b 不得再以 trigger_facet_key 進場，須改回分類路由並重估供裝深度」。
