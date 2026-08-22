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

### 四個平面（理解完整系統的正確切法）

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

**錯路由攔截率 1/13。** R3 全數漏放且是結構性的——那些問題 topic 上確實屬於該面向，
錯的是「觸發它的那篇知識答不了這題」，**是 answerability 的病，gate 治不了**。
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

**結論：不要離線重建 pipeline，驅動真實 API。**

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
| 2 | knowledge-grounded Face 是否需 face-scoped retrieval | R3 那 11 筆的唯一出路，未驗 |
| 3 | D 澄清分岔的 ambiguity 偵測 | brain 對 R3 全數判 `stay`，不具此能力 |
| 4 | production holdout | S3 客服回報自 2026-07-29 零新增 |
