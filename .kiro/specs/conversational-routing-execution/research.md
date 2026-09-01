# 研究記錄：conversational-routing-execution

> 建立 2026-08-23｜語言 zh-TW
> 目的：記錄 2026-08-22~23 檢索盤查的實測、架構推演與決策依據。
> ⚠️ **本檔記錄的是「調查結果與目標形態」，不是現況正本。**
> 現況正本為 [COMPLETE_CONVERSATION_ARCHITECTURE.md](../../../docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md)
> （停留於 2026-07-11，本輪發現尚未回寫）；參數的唯一真實來源為
> [參數台帳](../../../docs/retrieval-parameters.md)。

## 摘要

### 調查範圍
起點問題：業者問的問題，正確知識就在庫裡，但檢索沒排上來——是召回還是精排？
調查過程中範圍擴大為：檢索管線正確性、面向路由、對話引擎閉環、測試基礎設施。

### 關鍵發現
- **原語料量不出檢索**：25 筆中 14 筆的「正解知識」是照著這些回報事後補寫的。
- **本輪工作只是完整架構中的一個接縫**（Knowledge Path 內的「檢索後如何處理」），
  不取代 SOP 編排、既有會話續跑、Form／API 等既有主幹。
- **測試基礎設施結構性失效**：`make test-integration` 回報 183 skipped，
  實際為 166 passed / **5 failed** / 12 skipped——失敗被 skip 遮住。
- **判定類 LLM 呼叫點都跑在最弱模型上**：三處寫死 `gpt-3.5-turbo` fallback，
  同一段 prompt 換成 gpt-4o-mini 差 12 分（8/25 → 20/25）。
- **離線重建 pipeline 失敗三次**，每次讓結論作廢。**驅動真實 API，不要重建。**

---

## 命題狀態表（先讀本表）

> ⛔ **本表是 2026-08-23 的快照，⛔ 不是現況。**
> 2026-09-01 逐條查證 16 項：**9 條仍成立、5 條已過時、2 條紀錄有誤**。
> 現況一律跑 `python3 scripts/status.py` 與 `make audit`，⛔ 不從本表取值。
>
> **已過時（4 條是被本 spec 自己的任務修掉的——這是好事，不是缺陷）**
> ```text
> run-tests.sh 未傳 RUN_INTEGRATION/RUN_E2E      → 已修（任務 1.1／1.8）
> make test-integration 遮蔽 5 failed             → 已修（任務 1.3／1.8／1.10）
> harness drift：_route 自行重演進場鏈            → 已修（任務 3.1）
> mock 短路在 bill_ref adapter 之前               → 已改（任務 4.6，改由 _send 依 use_mock 派發）
> 三處寫死 gpt-3.5-turbo                          → 2 處已改跟隨 OPENAI_MODEL；
>                                                   ⚠️ 第 3 處連參數台帳自己都標「未盤查完」
> ```
>
> **⛔ 紀錄有誤（寫下時或現在為假）**
> ```text
> 「修繕報修 目前 0 個知識進場點」
>   ⛔ 2026-09-01 實查為 **5 筆**（4416/4418/4420/4421/4422，created 07-11、updated 08-04）
>   ⚠️ 但「不變量 4 對修繕報修 WARN」**今天仍成立**——兩條講的是不同東西，別混
> 「本地與 CI 同一支入口已不成立」被寫成 drift
>   ⛔ `scripts/run-tests.sh` 註解明文寫這是**刻意設計**，不是失效；
>      照本表去「修」它會修錯東西
> ```
>
> 防止本輪最常發生的兩種滑動：
> **「配置存在」被說成「能力已證實」**、**「候選解法」被說成「必要解法」**。

| 命題 | 狀態 | 依據／缺口 |
|---|---|---|
| 原語料（25 筆）已被知識補寫污染 | ✅ **已驗** | 14 筆正解 KB 建立於 07-31／08-03，晚於全部回報 |
| B2B always-on rewrite 無最終收益 | ✅ **已驗** | A/B 10 情境×3 次，行為 10/10 相同 |
| `related ≠ answerable` | ✅ **已驗** | kb3968 對 #18 final 0.9931 卻答非所問 |
| `related ≠ routable` | ✅ **已驗** | 「停用租客帳號」對退租面向 final 0.941 |
| pre-entry gate ROI 不成立 | ✅ **已驗** | 上游凍結後錯路由攔截 1/13 |
| **15 個 Face 配有 API grounding** | ✅ **配置已查** | ⚠️ 是**配置**，不等於**能力已證實** |
| API-grounded Face C1 多輪狀態／C2 API 呼叫 | ✅ **已驗** | session 實查 + mock 回傳進入候選 |
| API-grounded Face C3 grounding 傳遞 | ✅ **已驗** | 既有測試斷言 `bit_status=47 in grounding` 且通過 |
| **API-grounded Face C4 最終答案引用真實資料** | ⏳ **待驗** | mock 不依任何參數過濾、恆回 3 筆，無法收斂單筆（主題 7）|
| 真 API 有 `bill_ref` 參數 | ❌ **已否定** | External 只有 `bill_id`／`contract_id` 等；`bill_ref` 是 rag 端 adapter |
| External 與 Internal 是兩套不同投影的 API | ✅ **已驗** | 欄位／過濾／權限圈定皆不同；`api_registry` 全指向 External |
| External 欄位足以支撐帳單診斷 | ❓ **假說** | `late_fee_info`／`invoice_info`／`data` 僅 Internal 有 |
| Route-R3 是 routing failure | ❌ **已否定** | brain 判 `stay` 是對的——問題確實屬於該 Face |
| Route-R3 最終造成 answer failure | ⏳ **待驗** | 需 knowledge-grounded Face 的 end-to-end outcome |
| knowledge Face 需要 face-scoped retrieval | ❓ **假說** | 最直接的候選解法，非唯一解 |
| Clarification branch 可行 | ❓ **研究項** | brain 對 Route-R3 全數判 `stay`，不具 ambiguity 偵測能力 |
| 面向降級率 9%，且降級皆為正確拒絕 | ✅ **已驗** | 22 題實測，2 筆降級都是錯路由被正確攔下 |
| `repair_create` 零觸發點 | ✅ **已驗** | 無任何知識掛 `修繕報修`；`make audit` 不變量 4 長期 WARN |
| Handling Decision 現況為 rule-based commit | ✅ **已驗** | 讀碼：門檻 + `config_for_category` 查表，無判定步驟 |
| 測試基礎設施結構性失效 | ✅ **已驗** | `make test-integration` 183 skipped；繞過後 166/5/12 |
| 離線重建 pipeline 會失真 | ✅ **已驗** | 三次翻盤：錨點濾除／面向分岔／rewrite 擴充候選 |
| `run-tests.sh` 未傳 `RUN_INTEGRATION`／`RUN_E2E` | ✅ **已驗（讀碼）** | 全檔無該二字串；`docker compose run` 不帶 `-e` |
| 測試容器與 DB 分屬兩個 docker network | ✅ **已驗（實查）** | `aichatbot-test_default` vs `aichatbot_default`，dev compose 無 external network |
| 「本地與 CI 同一支入口」已不成立 | ✅ **已驗（讀碼）** | CI 直接跑 pytest＋`RUN_INTEGRATION=1`／`DB_HOST=localhost`，未經 `run-tests.sh` |
| **Req.2 存在第三種失敗型態：harness drift** | ✅ **已驗（讀碼）** | `test_facet_entry_routing_req.py::_route` 自行重演進場鏈，未呼叫 `_diagnosis_config_for_knowledge` |
| mock 短路位置在 `bill_ref` adapter **之前** | ✅ **已驗（讀碼）** | `jgb_system_api.py` `get_bills`：`if self.use_mock: return self._mock_get_bills(...)` 早於 adapter 解析 |
| **`skip_refine` 與 Req.4 mock 缺陷同根** | ⏳ **待驗（讀碼推得）** | `skip_refine` 語義＝跳過「補識別」輪，非跳過重查；重查為插點 A 既有正確設計 |
| 既有 C3 測試把 `api_handler` 整個替換 | ✅ **已驗（讀碼）** | 該測試以 `MagicMock` 注入手寫單列，未經 `APICallHandler`／`jgb_system_api` |
| `修繕報修` 目前 0 個知識進場點 | ✅ **已驗（實查 DB）** | `categories @> '修繕報修'` 且非「對話規則」＝ 0 筆 |
| **kb3365／kb4249 與 `repair_create` 語義／角色皆不符** | ✅ **已驗（實查 DB）** | 面向 `target_user=tenant`／`mode=b2c`；3365＝進度查詢（`property_manager,tenant`）、4249＝業者受理（`property_manager`）|
| `config_for_category` 不做 `target_user`／`mode` 過濾 | ✅ **已驗（讀碼）** | 純 `by_category` 查表，無角色比對 |
| 3365／1558 的 WARN 在**不變量 1**（非不變量 4）| ✅ **已驗（讀碼）** | 不變量 1＝動作知識必有面向接管（掛帳清單）；不變量 4＝面向 category 必有系統脈絡知識 |
| **Req.5.2 預設組態下的使用者可見 delta 極小** | ⏳ **待驗（讀碼推得）** | `step is None` 與 `scope=switch` 於 chat.py 續輪皆走「關會話＋重路由」；真正 delta 在 pre-entry gate 由 fail-open 轉為實擋 |

---

## 主題 1：本輪工作在完整架構中的**定位**

> ⚠️ **本輪研究的不是「完整對話架構」，而是其中一個接縫。**
> 母圖為 [COMPLETE_CONVERSATION_ARCHITECTURE.md](../../../docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md) §1，
> 該圖已完整涵蓋真實系統。**後續應以母圖為準，只修改本輪真正影響到的節點，
> 不得另畫一套平行架構。**

### 母圖的真實主幹（本輪一度忽略的兩條）

```text
Step 0    表單會話檢查            ← 既有會話優先續跑，優先權最高
Step 0.4  trigger_facet_key      ← 直達指定 Face
Step 0.5  損傷圖 is_damage        ← 特殊訊號改道交易 Face
Step 1-3  基礎處理 → cache → 意圖分類
            ↓
        【並行檢索】SOP ‖ Knowledge     ← 不是先 Knowledge 再決定
            ↓
        【智能決策】仲裁（SOP 分數／KB 分數／門檻／score gap／是否帶 next_action）
            ↓
     SOP 勝出 ／ 知識庫勝出 ／ 都不達標 fallback
```

### 本輪工作的位置

```text
完整系統
├─ Existing Form Session      ← 本輪未觸及
├─ Direct Facet Entry         ← 本輪未觸及
├─ SOP System                 ← 本輪未觸及
├─ Knowledge System ──────────┐
│                             │  ★ 本輪全部工作在此
│                    Vector → Rerank
│                             ↓
│                    categories 觸發 Face？
│                       ↙          ↘
│                    Face          Direct
│                                    ↓
│                            Answerability Gate
├─ Form Engine                ← 本輪未觸及
├─ API Engine                 ← 本輪未觸及
└─ Conversational / Transaction Face Engine  ← 僅驗證，未改
```

**本輪所有結論（b2b 停用 rewrite、`related ≠ answerable`、`related ≠ routable`、
strict direct-answer gate、R3 的 trigger evidence ≠ answer evidence、
API-grounded Face 待驗）全部掛在這個接縫下**，
**不取代** SOP、Form、API、Context、交易面向等既有架構。

### ⚠️ 撤回一個過度統一的抽象

本輪一度把 Direct／Form／Conversation／API 統稱為 **Capability Proposal**。
**看過母圖後撤回**——這四者不在同一層，壓成一類會把已分好的責任重新混在一起：

| 東西 | 實際是什麼 |
|---|---|
| SOP、Knowledge | **內容來源／編排來源** |
| `direct_answer`、`form_fill`、`api_call` | **Action** |
| Face | **有狀態的多輪 Orchestrator** |
| Form | 另一個**獨立狀態機** |
| API | **執行／grounding 能力** |
| `categories` | 目前 Knowledge → Face 的一種**入口關聯** |

### 四個平面（**責任分析模型**）

> ⚠️ **四個平面是責任分析模型，不代表系統存在四個獨立 service，
> 也不要求依此重構程式。** 現有實際流程為：表單會話先行 → 特殊 Face 直達 →
> cache → intent → SOP／Knowledge 並行仲裁；交易面向另有自己的
> prefill → brain → confirm → execute 流程。

| 平面 | 負責 |
|---|---|
| **A. Entry / Session** | 是否已有流程要續跑；是否有直達入口（表單會話優先權最高）|
| **B. Retrieval / Arbitration** | 意圖 → SOP ‖ Knowledge 並行 → 分數仲裁 |
| **C. Execution** | Direct／Form／API／SOP continuation／Conversational Face／Transaction Face，**各用既有引擎，不應硬統一** |
| **D. Grounding / State** | Redis context、Form state、Face state、API result、transaction slots；SOP Context 與 Knowledge Context 本即分開保存 |

### 仍然成立的接縫原則（本輪實測）
1. **semantic similarity ≠ answerability**——kb3968 對「續約後找不到帳單」final **0.9931**，答非所問。
2. **semantic similarity ≠ routability**——「停用租客帳號」對退租面向 final **0.941**。
3. **routing evidence ≠ answer evidence**——觸發面向的 KB 不應自動成為回答依據（R3 那 11 筆）。
4. **uncertainty ≠ automatically ask user**——只有「使用者回答後決策會改變」才反問；
   系統自己找不到知識時應誠實 fallback。

### 三種不確定必須分開
| 型態 | 例 | 正確處置 |
|---|---|---|
| 缺**執行欄位** | 「這張帳單為什麼沒入帳？」缺 `bill_ref` | 進 Face 後反問 |
| 缺 **intent** | 「我想增加一個物件」（新增／刊登／建約？）| **先澄清再 routing**（未實作）|
| 系統**沒有答案** | 「免費方案最多能建幾個物件？」KB 查無 | **fallback，不得反問** |

### 母圖的已知過時處（待本輪驗證後回寫）
正本標示 2026-07-11／v2.1，以下與現況不符：
`QUERY_REWRITE_MODEL`（已改 gpt-4o-mini）、`KNOWLEDGE_MIN_THRESHOLD`（實際 `KB_SIMILARITY_THRESHOLD=0.65`）、
`LLM_SYNTHESIS_TEMP`（實際 0.1）；且未涵蓋 `FORM_TRIGGER_THRESHOLD`、`RELEVANCE_GATE_*`、
`ENABLE_QUERY_REWRITE_B2B`、`PREENTRY_ROUTABILITY_GATE`。
**參數的唯一真實來源為 [參數台帳](../../../docs/retrieval-parameters.md)。**

---

## 主題 2：語料污染（為何 25 筆量不出檢索）

25 筆回報全在 2026-07-09~07-29；正解知識 kb4637／4642–4655 建立於 **07-31 與 08-03**，
`question_summary` 與案主題一對一。今天跑這些題，量的是「知識補了沒」，不是檢索。

三分類（21 筆知識題，剔除 4 筆查實值題）：

| | 今日 KB | 回報當時（KB < 07-30）|
|---|---|---|
| top-1 命中 | 16（14 筆命中事後補寫那批）| **1** |
| 進了被壓下去 | 3 | 3 |
| 沒進候選 | 2 | 2 |
| 庫裡沒有 | 0 | **15** |

---

## 主題 3：面向機制實測

- **21 組啟用面向**，15 為 API-grounded（`jgb_bills`／`jgb_contracts`／`jgb_meters`／
  `jgb_team_members`／`jgb_estate_status`），5 為 knowledge-grounded，1 為交易型。
- **55 筆空答案錨點**存在目的即面向進場觸發點。
- **進場判定順序**：面向判定用**濾錨點之前**的 top-1，錨點濾除在其後，
  適用性把關再其後——**面向繞過把關**。
- **降級率 9%**（22 題中 2 筆），且降級的都是**正確拒絕**——保護機制正常運作。
- `repair_create` **0 個觸發點**，完全打不開（`make audit` 不變量 4 長期 WARN）。

### Pre-entry routability gate（已實作、未上線）
上游凍結後 replay（72 筆母體 → 67 仍會路由）：

| 標註 | 仍路由 | 被擋 |
|---|---|---|
| R1／R2 正確 | 48 | 1（誤殺 2%）|
| **R3 方向對、證據錯** | **11** | **0** |
| **R4 明確錯路由** | **2** | **1** |

**錯路由攔截率 1/13。** Route-R3 全數漏放，且 brain 判 `stay` 是**對的**——
那些問題 topic 上確實屬於該面向。

> **Route-R3 不是 routability failure，而是 trigger-evidence mismatch**：
> 問題確實屬於該 Face，但**觸發 Face 的那篇 KB 本身不足以回答原問題**。
> ⏳ **是否進一步構成 answerability failure，須以 knowledge-grounded Face 的
> end-to-end outcome 驗證**——本輪未跑完，不得先行宣判。

無論如何，pre-entry gate 治不了 Route-R3（它判的是 routability，不是 evidence 充分性）。
→ 不上線，程式保留、flag 預設關。

---

## 主題 4：對話邏輯缺陷（進對面向之後）

| # | 實測 | 病灶 |
|---|---|---|
| 1 | 「續約 12 個月後在帳單頁找不到帳單」→ 反問「以便查詢**租客帳號狀態**」| 進對面向、**問錯問題** |
| 2 | 「合約**已經簽約了**但我想修改」→ 反問「想修改哪個項目？」| **繞過已陳述的前提**；對照組「還在簽署中可以改嗎」得到幾乎相同回應 |

→ 形成 R10（對話邏輯品質必須可量測）。

---

## 主題 5：測試基礎設施

`steering/testing-code.md` 明訂「`RUN_INTEGRATION=1` 才跑」，
但 `scripts/run-tests.sh` 以 `docker compose run` 啟動、**無任何機制傳遞該旗標**，
亦無 DB 連線設定。

| 執行方式 | 結果 |
|---|---|
| `make test-integration` | **183 skipped** |
| 繞過 runner（帶旗標＋接上網路）| **166 passed / 5 failed / 12 skipped** |

5 個失敗全在 `test_facet_entry_routing_req.py`，全是「該不該進面向」的斷言。
**C3 grounding 傳遞其實已有測試守著且通過**
（`test_single_row_converges_with_hybrid_three_level_context` 斷言 `bit_status=47 in grounding`）。

---

## 主題 6：量測紀律（本輪的代價）

### 離線重建 pipeline 失敗三次
| # | 漏掉 | 後果 |
|---|---|---|
| 1 | 錨點濾除（55 筆空答案列）| top-1 算錯 |
| 2 | 面向分岔（截走約 30% 流量）| 直答/查無比例整組偏移 |
| 3 | query rewrite 擴充候選（+10–23 筆）＋關鍵字備選 | 候選集約為線上一半，三題結論相反 |

**結論（精確版）：不得自行重建 production retrieval／routing pipeline 作為比較基準。**

- 量測 SHALL 優先驅動 **production code path**。
- 若使用**離線 replay**，輸入 SHALL 取自真實管線**凍結後的中間產物**
  （本輪成功案例：72 筆 cohort 先以 Gate OFF 跑真 API 取得 routing proposal 再凍結）。
- **Mock 僅替換外部依賴**（如 jgb2 API），SHALL NOT 重寫 routing／retrieval 邏輯。

此原則同時容納：真 Chat API 驅動、frozen proposal replay、API mock、unit／integration test。
**不是「所有離線測試都不可信」**——是「自行重建管線很容易失真」。

### 五次「小樣本或未驗因果就下結論」
25 筆語料／72 筆標註／8 題改寫比較／「改寫造成路由抖動」未驗因果／
「面向降級率 75%」由單一查詢外推。
→ **比較性結論一律 ≥30 題；單一案例只能提假說。**

### Mock 的正當性與風險
mock 可驗 C1／C3／C4（控制流），**真 API 只用於確認 schema 與現實的偏差**。
風險是「造假資料假裝通過」——防線是：mock 由專案自帶而非臨時撰寫、
期望值於執行前明示為斷言基準、且結論須可回溯至具體資料值。

---

## 主題 7：`jgb_bills` API 契約盤查（jgb2 原始碼，2026-08-23）

> 來源 `/Users/lenny/jgb/project/jgb/jgb2`，附 file:line。
> 目的：作為 **Req.4（Mock 契約）的斷言基準**——mock 期望值不得由推測產生。
> ⚠️ jgb2 持續演進；本節為「當時盤查」快照，行為不符時**先重盤再改斷言**。
>
> **與既有盤查的分工**：[billing-conversational-facets/research.md](../billing-conversational-facets/research.md)
> 已盤**帳務語義**（`status`／`bit_status` 雙欄位、超商條碼撥付逢 5/15/25、
> 金額不符卡待對帳、國泰 ATM 無失效時限）。本節盤的是 **API 契約**
> （端點／參數／回傳形狀），**互補不重複，勿重盤語義**。

### ⭐ 對外與對內是兩套 API，rag 打的是對外

| | **External** `/api/external/v1/bills` | **Internal** `/api/internal/v1/bills` |
|---|---|---|
| 控制器 | `External\BillApiController` | `Internal\BillQueryController` |
| 保護 | `X-API-Key` ＋權限＋限流＋稽核 log | **雙重**：`internal_api_ip`（IP 白名單）**＋** 上述全套（`routes/api.php:179-183`）|
| 欄位 | **白名單 SELECT ~30 欄** | `Bill::query()` **全欄**，含 10 個 JSON 欄（`data`／`pay_info`／`big_landlords`／`invoice_info`／`late_fee_info`…）|
| 過濾 | `user_id`／`contract_id`／`bill_id`／`status`／`type`／`month` | ＋`estate_id`／`role_id`／`owner_role_id`／`creditor_role_id`／`category`＋三組日期區間 |
| 權限圈定 | **強制** `owner_role_id` 或 viewer scope | **無**——`owner_role_id` 只是可選過濾 |

**`api_registry` 目前全部指向 External。** 這代表面向拿得到的是**受限投影**。

> ⚠️ **這是 C4 失敗的第三種可能，本輪原本會漏掉**：
> | 失敗型態 | 修法 |
> |---|---|
> | (a) 鏈路沒跑通 | 修 Face → state → API → grounding 鏈 |
> | (b) mock 不夠保真 | 修 mock 契約（Req.4）|
> | **(c) External 欄位投影不足** | **擴 External 欄位或改打 Internal——與修鏈路完全不同的工作** |
>
> 「這張帳單為什麼發不出去」需要診斷理由，但 External 只給
> `status`／`bit_status`／`invoice_status` 等**結果狀態**；
> `late_fee_info`／`invoice_info`／`data` 這些可能承載原因的 JSON 欄位**只有 Internal 有**。

### 端點與路由

| 契約鍵 | 路由 | 控制器 |
|---|---|---|
| `jgb_bills` | `GET /api/external/v1/bills` | `BillApiController@index`（`routes/api.php:83`）|
| `jgb_bill_detail` | `GET /api/external/v1/bills/{bill_id}` | `BillApiController@show`（`routes/api.php:155`）|

### ⭐ 真 API **沒有 `bill_ref` 參數**

`index` 支援的過濾（`BillApiController.php:49-85`）：
`role_id`（**必填**，缺則 400）／`user_id`／`contract_id`（單數）／`bill_id`／
`status`／`type`／`month`（`YYYY-MM`，比對 `date_expire` 整數區間）／
`sort_by`／`sort_direction`／`page`／`per_page`。

`bill_ref` 是 **rag 端的識別語意 adapter**（`jgb_system_api.get_bills`）：
純數字 → 先 `get_bill_detail` 直查（單筆包成列）；查無 → 當合約 id；非數字 → 當 keyword 查合約。

> ⚠️ **本輪一度打算「修 mock 讓它依 `bill_ref` 過濾」——那會憑空造出真 API 不存在的行為。**
> 盤查即時擋下。**Req.4.1 的「依文件契約過濾」應理解為：對齊 adapter 的解析結果
> （`bill_id` 單筆／`contract_id` 多筆），而非虛構 `bill_ref` 過濾。**

### 回傳結構

`index`（`:110-124`）：
```jsonc
{ "success": true,
  "mapping": {...},
  "data": [ /* formatBill */ ],
  "pagination": { "current_page","per_page","total","total_pages","has_more" } }
```
分頁常數（`:13-14`）：`DEFAULT_PER_PAGE=50`、`MAX_PER_PAGE=200`。
排序白名單（`:88`）：`date_expire`／`created_at`／`total`／`updated_at`，預設 `created_at desc`。
權限（`:41-47`）：有 `user_data` 則依成員主體圈定，否則 `owner_role_id`；一律 `active=1`。

`show`（`:203-268`）在 `formatBill` 之上另加：
`pay_info`（白名單：`type`／`manufacturer`／`action`／`expire_ymd`／`atm_info`）、
`cvs_info`（超商代碼，來源 `payments.newebpay_cvs_info`）、
`details`（`label`／`unit_price`／`unit_type`／`unit_count`／`measurement_before`／`measurement_after`／`total_price`）。
查詢用 `id`＋`owner_role_id`＋`active=1`，查無回 **404「帳單不存在或無權存取」**。
`getShowMapping()`（`:326-336`）＝ `getMapping()` **再加 `unit_type`**（無單位／度／日／月）——index 沒有這群。

`mapping`（`:173-198`）：`status` 六值／`invoice_status` 三值／`type` 六值。
✅ **mock 的 mapping 與此完全一致，無落差。**

### Mock 與真契約的落差（Req.4 待修清單）

| # | 落差 | 嚴重度 |
|---|---|---|
| 1 | `_mock_get_bills` **缺 `pagination`** | 中——消費端讀 `has_more` 會拿到 None |
| 2 | `_mock_get_bill_detail` **缺 `cvs_info`** | 低——超商代碼情境無法測 |
| 3 | mock 的 `data` 固定三筆、**不依任何參數過濾** | ⚠️ **高** |

**落差 3 的正確修法**：不是「依 `bill_ref` 過濾」（真 API 無此參數），
而是依真 API **實際存在**的參數過濾（至少 `bill_id`、`contract_id`），
如此 adapter 的解析才能在 mock 下收斂到單筆，**Req.3 的 C4 才可驗**。

### 尚未盤查（輪到時再補）
`jgb_contracts`／`jgb_meters`／`jgb_team_members`／`jgb_estate_status`
——本輪只盤 `jgb_bills`，Req.3 的立即阻塞點只在 `bill_diagnosis`。

---

---

## 主題 8：程式碼盤查（2026-08-23，設計階段輕量發現）

> 目的：把 requirements.md 的每條需求對到**具體整合點**，並揭露需求撰寫時尚未掌握的三個結構事實。
> 方法：讀碼 ＋ 對 dev 容器實查 DB／docker network，**未執行任何寫入**。

### 8.1 Req.1｜測試基礎設施：三個獨立缺口，不是一個

| # | 缺口 | 證據 |
|---|---|---|
| 1 | **旗標未傳遞** | `scripts/run-tests.sh` 全檔無 `RUN_INTEGRATION`／`RUN_E2E`；`docker compose run --rm` 未帶 `-e` |
| 2 | **網路不通** | `docker-compose.dev.yml` 宣告 `name: aichatbot-test` 且無 `networks:` 區段 → 網路 `aichatbot-test_default`；DB 在 prod 專案的 `aichatbot_default`。`DB_HOST` 預設 `postgres` 在測試網路內無此名 |
| 3 | **失效不可見** | 183 筆全部被 gate-skip 時 pytest 仍回 exit 0，摘要與「真的跑完且全過」在退出碼上無法分辨 |

補充：`.github/workflows/tests.yml` 的 integration job **不經 `run-tests.sh`**，直接
`python3 -m pytest -m integration`＋`RUN_INTEGRATION=1`＋`DB_HOST=localhost`。
`run-tests.sh` 檔頭宣稱「本地與 CI 同一支」——**該宣稱目前不成立**，修 Req.1 時應一併收斂。

亦查得 `pytest.ini` 的 `addopts` 僅有 `--strict-markers`，**無 `-ra`** → skip 原因不進摘要，
這正是 1.3「兩種略過在輸出上無法分辨」的機制成因。

### 8.2 Req.2｜第三種失敗型態：harness drift

`tests/integration/conversational/test_facet_entry_routing_req.py` 的 `_route()`
**自行重演**進場決策鏈：直接呼叫 `retrieve_knowledge_hybrid` → 自行比門檻 → 自行取
`categories` → 自行呼叫 `config_for_category`。

production 的同一段是 `routers/chat.py::_diagnosis_config_for_knowledge`，其組成為
`decision_layer.facet_entry_eligible`（門檻 gate，讀 `DecisionConfig.load()`）
→ `_knowledge_category`（`categories` 優先、退 `category`）
→ `config_for_category`
→ `_preentry_routable`（gate，預設關）。

差異至少三處：門檻讀值點不同（測試自行 `os.getenv`，非 `DecisionConfig`）、
`_knowledge_category` 的雙欄位退化規則被複刻而非呼叫、`_preentry_routable` 完全缺席。

> ⚠️ 這與 **R9.4（離線驗證須複刻該版本 production 實際啟用的變換與順序）** 直接衝突。
> 故 Req.2.2 的二分法（產品行為改變／真實回歸）**不足**，須擴為三分：
> `REGRESSION`／`EXPECTATION_DRIFT`／`HARNESS_DRIFT`。

### 8.3 Req.3／4｜C4 未證的機制根因：mock 掛錯層

`services/jgb_system_api.py::get_bills` 的執行順序為：

```text
身分/授權檢查
  ↓
if self.use_mock: return self._mock_get_bills(role_id, user_id, month, status)   ← 短路在此
  ↓  （以下在 mock 模式下永不執行）
bill_ref adapter 解析（純數字→get_bill_detail 單筆／查無→當合約 id／非數字→keyword 查合約）
  ↓
params 組裝（contract_ids → 單數 contract_id）
  ↓
_request('/api/external/v1/bills')
  ↓
client 端防衛過濾（上游無視參數時仍按 contract_id 濾）
```

`_mock_get_bills` 的簽章**不含** `contract_ids`／`bill_ref`，回傳固定三列、無 `pagination`。
因此 mock 模式下被替換掉的不只是「外部依賴」，而是**連同 rag 端的識別解析與防衛過濾一起被略過**
——這正是主題 6「Mock 僅替換外部依賴，SHALL NOT 重寫 routing／retrieval 邏輯」所禁止的形態。

`bill_diagnosis` 的 `grounding_scope` 實查為：
`required_slots=['bill_ref']`、`search_params=[{bill_ref: '{form.bill_ref}'}]`、
`result_mapping.candidate_cap=8`、`skip_refine=true`、
`secondary_call → jgb_bill_detail(bill_id={row.id})`。

C4 在 mock 下的實際軌跡（讀碼推得）：
三列 → 列候選 → 使用者選序號 → 插點 A 填 `bill_ref` → **重查 `get_bills` 仍回三列**
→ 再列候選 → 迴圈，永不進單筆收斂。

### 8.4 Req.5.1｜`skip_refine` 是同一缺陷的第二個症狀

`services/conversational_engine.py` 的 `skip_refine` 只出現在**候選數 > `candidate_cap`**
的分流分支，作用是「跳過『請提供更明確識別』那一輪、直接截斷列候選」。
選定候選後於**插點 A** 呼叫 `_ground_by_api` 重查，是為取得單筆＋`secondary_call` 詳情的**既有正確設計**。

> 推得結論（待以重現測試確認）：Req.5.1 觀測到的「宣告 `skip_refine` 卻仍重查 API」
> **並非行為與宣告不符**，而是 8.3 的 mock 缺陷使重查無法收斂、外觀像是旗標失效。
> 正確語義＝**跳過補識別輪**，非跳過重查。

### 8.5 Req.3｜既有 C3 證據的範圍需要收窄

`test_single_row_converges_with_hybrid_three_level_context` 以
`handler.execute_api_call = AsyncMock(return_value=...)` **整個替換 `APICallHandler`**，
回傳手寫單列與手寫 `formatted_response`。

它證明的是：引擎能把 handler 回傳的 `formatted_response` 組進 `grounding`，且三層 `system_md` 正確注入。
它**不涵蓋** `_ground_by_api → APICallHandler → api_registry → jgb_system_api → 外部 HTTP` 這一段。
C4 之所以至今未證，正因這段從未被端到端跑過——與「mock 不過濾」是同一個結構問題的兩面。

### 8.6 Req.5.2｜blast radius 的實際形狀（比需求預估的小，但不為零）

`llm_answer_optimizer.conversational_step` 的驗證順序：
`action` 白名單檢查（越界即 `return None`）→ …→ `scope` 正規化。故 `action` 越界時 `scope` 陪葬。

三個呼叫點與各自的實際 delta：

| 呼叫點 | 現況（step 被丟棄） | 修復後 | delta |
|---|---|---|---|
| `conversational_engine`（進場輪 `asked_count=0`）| 關會話 → 回 None → chat.py 落回一般流程 | `scope=switch` → 關會話 → 回 None | **無使用者可見差異** |
| `conversational_engine`（續輪）| 回 None → chat.py 記 `facet_engine_degraded`、關會話、重路由 | 同上，但語義為 switch | **歸因改變**（`decision_snapshot` 值域），使用者可見行為相同 |
| `chat._preentry_routable` | `data is None` → **fail-open 照舊進場** | 取得 `scope=switch` → **實際擋下進場** | ⚠️ **真正的行為 delta**，但受 `PREENTRY_ROUTABILITY_GATE`（預設 `false`）保護 |

> 既有測試 `test_scope_switch_closes_session` 已證 `scope=switch` → 引擎回 None → 會話關閉。
> 故 Req.5.2 的「獨立上線」紀律仍應維持——但理由從「blast radius 未知」
> 修正為「**歸因值域改變 ＋ pre-entry gate 語義由 fail-open 轉為實擋**」，兩者都應單獨可回退。

### 8.7 Req.5.3｜補 metadata 之前必須先判型（新增阻塞點）

實查 DB：

| id | `question_summary` | `action_type` | `form_id` | `target_user` | `categories` |
|---|---|---|---|---|---|
| 3365 | 修繕進度 修繕查詢 | `form_fill` | `jgb_repair_query` | `{property_manager, tenant}` | NULL |
| 4249 | 收到租客修繕申請 怎麼受理處理 | `direct_answer` | — | `{property_manager}` | NULL |
| 1558 | 維修進度查詢 | `api_call` | — | NULL | NULL |

`repair_create` 面向配置（`seed_repair_facet_config.sql`）：
`topic_scope.category='修繕報修'`、`persona_role='tenant_repair'`、
`grounding_scope.target_user='tenant'`、`mode='b2c'`、`execute_endpoint='jgb_create_repair'`。

且 `services/conversational_config.py::config_for_category` 為**純 by_category 查表，
不比對 `target_user`／`mode`**。

> ⚠️ 兩重不符，直接補 `categories=['修繕報修']` 會同時踩到：
> 1. **意圖不符**：3365／1558 是「查進度」，4249 是「業者受理」——皆非「租客建報修單」；
> 2. **角色不符**：4249 只掛 `property_manager`，掛上去等於替 b2b 業者開一條通往
>    b2c 租客面向的進場路徑，而查表層不會擋。
>
> 故 Req.5.3 的「補上 kb3365／kb4249 的 routing metadata」**不可照字面執行**，
> 須先判型（見 design.md 元件 6 的三選項）。

補正：requirements.md 記為「`make audit` 不變量 4 長期 WARN」；實際 3365／1558 的掛帳 WARN
在**不變量 1**（動作知識必有面向接管）。不變量 4 是「每個面向 category 必有系統脈絡知識」，
兩者皆與修繕相關但語義不同，驗收時要對到正確那條。

### 8.8 Req.10｜可直接複用的既有量測基礎

- `usage_events` 已有 `facet_key`／`turn_number`／`facet_event`／`decision_snapshot`
  → **輪數分佈**與**重複詢問率**可由既有埋點以 SQL 聚合，無須新埋點。
- **反問對題率**與**前提衝突處理率**需要對「反問文字 vs 使用者原句」下判定，既有埋點不足。
- `scripts/backtest/freeze_measurement.py`（判準／分母／雜訊標記／尺版本四項量測前凍結）
  與 `decision_replay.py`（容器一致性、語料完整性、快取軌別、規則版本四道閘門）
  是既有且經過教訓沉澱的模式——Req.10 的 baseline 應建在其上，不另起爐灶。

### 8.9 風險登記（輕量發現第 5 階段）

| 風險類別 | 檢查項目 | 結果 |
|---|---|---|
| 資料完整性 | 是否涉及資料遷移？ | **是**（Req.5.3 的 `categories` 變更即 routing 變更，見 R6.6）|
| 效能 | 是否有大量資料處理？ | 否（mock transport 無 IO；量測為離線批次）|
| 安全性 | 是否處理敏感資料？ | **是**（mock fixture 不得含真實個資；`USE_MOCK_JGB_API` 預設 `true`，未設定即走假資料）|
| 相容性 | 是否影響現有 API？ | **是**（`conversational_step` 回傳契約、`get_bills` mock 分支位置）|


## 待決事項

| # | 事項 | 卡在哪 |
|---|---|---|
| 1 | C4 最終答案引用真實資料 | 根因已定位為 **mock 掛錯層**（主題 8.3）——`use_mock` 短路在 `bill_ref` adapter 之前；解法見 design.md 元件 3 |
| 1b | C4 若失敗屬 (a)鏈路／(b)mock／**(c)External 欄位投影不足** 哪一類 | 需先判型再修——三者修法完全不同 |
| 2 | knowledge-grounded Face 是否需 face-scoped retrieval | **若** Route-R3 的 end-to-end 證實最終答案仍受 trigger KB 限制，face-scoped evidence retrieval 是**目前最直接的候選解法**——非唯一解。其他可能：Face 本身規則已足以處理／Face 後續另有知識來源／部分案例本來就能正確處理／應直接退出 Face 回 direct path |
| 3 | D 澄清分岔的 ambiguity 偵測 | brain 對 R3 全數判 `stay`，不具此能力 |
| 4 | production holdout | S3 客服回報自 2026-07-29 零新增 |
| 5 | `repair_create` 該掛哪一筆進場知識 | kb3365／4249 意圖與角色皆不符（主題 8.7）；三選項與推薦見 design.md 元件 6 |
