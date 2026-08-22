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
| **API-grounded Face C4 最終答案引用真實資料** | ⏳ **待驗** | mock 忽略 `bill_ref` 恆回 3 筆，無法收斂單筆 |
| Route-R3 是 routing failure | ❌ **已否定** | brain 判 `stay` 是對的——問題確實屬於該 Face |
| Route-R3 最終造成 answer failure | ⏳ **待驗** | 需 knowledge-grounded Face 的 end-to-end outcome |
| knowledge Face 需要 face-scoped retrieval | ❓ **假說** | 最直接的候選解法，非唯一解 |
| Clarification branch 可行 | ❓ **研究項** | brain 對 Route-R3 全數判 `stay`，不具 ambiguity 偵測能力 |
| 面向降級率 9%，且降級皆為正確拒絕 | ✅ **已驗** | 22 題實測，2 筆降級都是錯路由被正確攔下 |
| `repair_create` 零觸發點 | ✅ **已驗** | 無任何知識掛 `修繕報修`；`make audit` 不變量 4 長期 WARN |
| Handling Decision 現況為 rule-based commit | ✅ **已驗** | 讀碼：門檻 + `config_for_category` 查表，無判定步驟 |
| 測試基礎設施結構性失效 | ✅ **已驗** | `make test-integration` 183 skipped；繞過後 166/5/12 |
| 離線重建 pipeline 會失真 | ✅ **已驗** | 三次翻盤：錨點濾除／面向分岔／rewrite 擴充候選 |

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

## 待決事項

| # | 事項 | 卡在哪 |
|---|---|---|
| 1 | C4 最終答案引用真實資料 | mock 忽略 `bill_ref` 恆回 3 筆，無法收斂單筆 |
| 2 | knowledge-grounded Face 是否需 face-scoped retrieval | **若** Route-R3 的 end-to-end 證實最終答案仍受 trigger KB 限制，face-scoped evidence retrieval 是**目前最直接的候選解法**——非唯一解。其他可能：Face 本身規則已足以處理／Face 後續另有知識來源／部分案例本來就能正確處理／應直接退出 Face 回 direct path |
| 3 | D 澄清分岔的 ambiguity 偵測 | brain 對 R3 全數判 `stay`，不具此能力 |
| 4 | production holdout | S3 客服回報自 2026-07-29 零新增 |
