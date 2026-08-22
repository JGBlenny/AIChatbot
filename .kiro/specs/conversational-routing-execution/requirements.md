# 需求規格：conversational-routing-execution

> 建立 2026-08-23｜語言 zh-TW
> 來源：2026-08-22~23 檢索盤查（[盤查報告](../../../docs/retrieval-recall-audit-20260822.md)、
> [參數台帳](../../../docs/retrieval-parameters.md)、[驗收契約](../../../docs/routing-gate-acceptance.md)）
> ⚠️ `.kiro/settings/rules/ears-format.md` 與 `templates/specs/requirements.md` 不存在，
> 本文件採 WHEN/THEN/SHALL 內建結構，並以數字 ID 編號。

## 架構定位（本 spec 的作用域）

> ⚠️ **本 spec 不是在重建「完整對話架構」，而是改善其中一個接縫。**
> 母圖為 [COMPLETE_CONVERSATION_ARCHITECTURE.md](../../../docs/architecture/COMPLETE_CONVERSATION_ARCHITECTURE.md) §1；
> 定位推導見 [research.md 主題 1](./research.md)。

真實系統的主幹（本 spec **未觸及**的部分）：

```text
Step 0    表單會話檢查（既有會話優先續跑，優先權最高）
Step 0.4  trigger_facet_key 直達 Face
Step 0.5  損傷圖改道交易 Face
Step 1-3  基礎處理 → cache → 意圖分類
            ↓
        【並行檢索】SOP ‖ Knowledge
            ↓
        【智能決策】仲裁（SOP／KB 分數、門檻、score gap、是否帶 next_action）
            ↓
     SOP 勝出 ／ 知識庫勝出 ／ 都不達標 fallback
```

**本 spec 的作用域＝知識庫勝出之後的那一段**：

```text
Knowledge Path
  Vector → Rerank → categories 觸發 Face？
                    │  現況：rule-based commit（門檻＋查表）
                    │  **非獨立 Decision Engine**
                    ├─ Face
                    ├─ Clarification 【研究項，未實作】
                    └─ Direct → Answerability Gate → 直答／誠實 fallback
```

> ⚠️ 「Proposal／Decision」為**責任模型**，**不代表目前存在獨立的 decision service**，
> 亦**不要求**新建一個。pre-entry routability gate 實測錯路由攔截率 1/13，
> 已證明現階段沒有理由新增中央 selector。

**範圍聲明**：本 spec 僅處理 **Knowledge retrieval 勝出後的 Face routing／Direct answer 接縫，
以及 Face execution 的可驗證性**。
既有 Form Session 優先序、**SOP vs Knowledge arbitration**、SOP trigger modes、
Form Engine、API Engine、交易面向引擎——**均不在本次改造範圍**。
不處理澄清分岔——實測 brain 對 **Route-R3** 全數判 `stay`，不具 ambiguity 偵測能力，列研究項。

---

## Requirement 1：測試基礎設施必須可執行（最高優先）

**背景**：`.kiro/steering/testing-code.md` 明訂「integration 預設略過，`RUN_INTEGRATION=1` 才跑」，
但 `scripts/run-tests.sh` 以 `docker compose run --rm` 啟動且**未傳遞任何測試旗標**，
亦未提供 DB 連線設定 → `make test-integration` 回報 **183 skipped**，
實際繞過後為 **166 passed / 5 failed / 12 skipped**。
**文件寫的意圖，工具結構上做不到；5 個失敗被 skip 遮住。**

- 1.1 WHEN 執行 `make test-integration`，THEN 系統 SHALL 實際執行 integration 層測試，
  而非因旗標未傳遞而全數略過。
- 1.2 WHEN 測試容器啟動，THEN 系統 SHALL 提供可連線的 DB 設定
  （目前預設 `localhost:5432`，與實際 DB 服務不同網路）。
- 1.3 WHEN 測試因環境不足而略過，THEN 系統 SHALL 於摘要明確區分
  「因環境略過」與「因標記未啟用略過」，不得讓兩者在輸出上無法分辨。
- 1.4 WHEN 任一層測試存在失敗，THEN 該失敗 SHALL NOT 被 skip 統計遮蔽。
- 1.5 `make test-e2e` SHALL 適用同樣條件（`RUN_E2E=1` 目前同樣無法傳遞）。

**驗收**：`make test-integration` 的 passed/failed/skipped 三個數字與繞過 runner 直跑一致。

---

## Requirement 2：面向進場路由的既有回歸必須恢復綠燈

**背景**：Requirement 1 修復後浮現 5 個失敗，全在 `test_facet_entry_routing_req.py`，
全是「該不該進面向」的斷言：

| 測試案例 | 期望 |
|---|---|
| 點退帳單的金額是怎麼算的 | 維持單發直答 |
| 點退的前置條件是什麼 | 維持單發直答 |
| 合約快到期了，系統會自動提醒我嗎？ | 維持單發直答 |
| 點退做完後，帳單會自動出來嗎？ | 維持單發直答 |
| 我的合約狀態怪怪的 | 應進對話 |

- 2.1 WHEN 執行面向進場路由測試，THEN 全部案例 SHALL 通過。
- 2.2 WHEN 任一案例無法通過，THEN 系統 SHALL 明確區分是
  **產品行為已合理改變（需更新斷言）** 或 **真實回歸（需修程式）**，
  並記錄判定依據；**不得以「更新斷言」作為預設處置**。
- 2.3 修復 SHALL NOT 依賴調整 `FORM_TRIGGER_THRESHOLD`——
  實測 6 筆資訊型問題以 final ≥0.945 進面向，任何門檻皆擋不到。

---

## Requirement 3：API-grounded Face 端到端閉環必須被證實

> **Dependency：Requirement 1、Requirement 4。**
> Req.4（mock 契約）是本需求可驗的前提——mock 不依 `bill_ref` 過濾即無法收斂單筆，
> C4 便無從驗證。**不得依編號順序先做 Req.3。**

**背景**：15/21 面向為 API-grounded，是面向機制的核心價值主張。
四檢查點現況：**C1 多輪狀態已證實**（session 實查 `collected_fields.bill_ref=12345`、
`pending_candidates` 三筆完整）；**C2 API 呼叫已證實**；
**C3 grounding 傳遞已有測試守著且通過**
（`test_single_row_converges_with_hybrid_three_level_context` 斷言 `bit_status=47 in grounding`）；
**C4 最終答案引用真實資料尚未證實**。

**兩種證據不得混為一談**：

| 證據 | 方法 | 證明什麼 |
|---|---|---|
| **A. Deterministic control-flow E2E** | contract-faithful **mock** | 系統控制流**真的閉環** |
| **B. Real API contract smoke** | 少量打 staging／真 API | **mock 假設與現實 contract 沒漂移** |

3.1–3.3 屬 **A**（走 mock）；**B 由 Req.4.4 負責，不作為主要控制流驗收**。

- 3.1 系統 SHALL 有一條可重複執行的 **deterministic control-flow E2E** 測試，涵蓋
  「問題 → 進面向 → 反問必要欄位 → 收齊 → 呼叫 API handler → mock response
  → grounding → 最終回答」完整鏈路。
- 3.2 WHEN 該鏈路收斂至單筆資料，THEN 最終回答 SHALL 引用該筆的實際狀態值，
  且 SHALL NOT 退回泛用 KB 答案。
- 3.3 該測試 SHALL 至少涵蓋**兩個不同的 API-grounded 面向**
  （例如 `bill_diagnosis` 與 `contract_diag`），以證明非單一面向特例。
- 3.4 IF 閉環無法證實，THEN 所有 routing 相關工作 SHALL 降級為 P1 以下，
  「Face → state → API → grounding → answer」執行鏈修復 SHALL 升為 **P0**。
- 3.5 ⚠️ 完整系統另有 SOP 直接 API、Form→API 等多種 API 路徑；
  本需求的「API invocation」SHALL 僅指 **Face grounding** 那一條，不得與其他路徑混稱。

---

## Requirement 4：Mock 保真度必須與測試綁定並具契約

**背景**：`_mock_get_bills` 忽略 `bill_ref` 恆回 3 筆，導致選定候選後重查仍為多筆、
永遠收斂不到單筆——C4 因此無法在 mock 下驗證。
但 mock 的正當性建立在「不得造假通過」，故其行為必須有契約可稽核。

- 4.1 WHEN mock 模擬一個具備過濾語意的參數（如 `bill_ref`），
  THEN mock SHALL 依該參數過濾，與真 API 的文件契約一致。
- 4.2 Mock 的期望回傳 SHALL 於測試中明示為斷言基準，
  使「通過」可回溯至具體資料值，而非僅「有回答」。
- 4.3 Mock 的啟用 SHALL 由測試自身控制（現況 `monkeypatch.setenv` 已符合），
  SHALL NOT 依賴常駐容器的環境設定。
- 4.4 **Real API contract smoke**：真 API SHALL 僅用於確認
  「mock 假設與現實 contract 是否漂移」（params → endpoint → response schema），
  SHALL NOT 作為驗證控制流的起點，亦 SHALL NOT 作為 Req.3 的主要驗收證據。

---

## Requirement 5：已知缺陷修復（各自獨立驗收）

- 5.1 **`skip_refine` 語義不符**：`bill_diagnosis` 設定 `result_mapping.skip_refine=true`，
  但實測選定候選後仍重查 API。WHEN 設定宣告 `skip_refine`，
  THEN 系統行為 SHALL 與宣告一致；不一致者 SHALL 修正其一並記錄哪一邊是正確語義。
- 5.2 **validator 丟棄正確 scope**：`llm_answer_optimizer.conversational_step` 的
  `action` 驗證早於 `scope` 正規化，`action` 越界即整包丟棄
  （實測 brain 5/5 正確輸出 `scope=switch` 全遭丟棄，line 表現為「引擎降級」）。
  WHEN brain 輸出可用的 `scope` 而 `action` 越界，
  THEN 系統 SHALL NOT 連同 `scope` 一併丟棄。
  ⚠️ 此修復 SHALL 獨立驗收——它會啟用一條 **mid-session switch** 能力，
  其 blast radius 未量，**不得與其他改動同批上線**。
- 5.3 **`repair_create` 零觸發點**：該面向無任何知識掛 `修繕報修`，完全無法進場
  （`make audit` 不變量 4 長期 WARN）。
  WHEN 解 freeze 補上 kb3365／kb4249 的 routing metadata，THEN SHALL：
  ① 明確記錄其新增的 **Face entry points**；
  ② 以**現行 production routing 規則**執行回歸；
  ③ 驗證新增 trigger **不造成已知資訊型問題誤進 `repair_create`**；
  ④ 通過後始得上線。
  ⚠️ **不等待任何尚不存在的 Handling Decision**——
  直接驗證這兩筆 executable metadata change 的 **runtime effect**。

---

## Requirement 6：Routing Hint、Action Declaration 與 Execution Configuration 必須分層

**背景**：先前把 `categories`／`form_id`／API capability 統稱「Capability Proposal」——
**這個抽象不準，已撤回**。三者處於**三個不同層級**，壓成一類會把系統已分好的責任重新混在一起。

```text
Knowledge Evidence（內容本身）
│
├─ Routing Hint ──────── categories → 可能的 Face
│                        （Knowledge 與 Face 的入口關聯）
│
├─ Action Declaration ── action_type / form_id / trigger_mode
│                        （direct_answer｜form_fill｜api_call｜form_then_api；
│                          form_fill 後再由 trigger_mode 分 manual／immediate／auto）
│
└─ Face 被選定之後
     └─ Execution Configuration ── grounding_scope / required_slots
                                   / execute_endpoint / execute_params
                                   （不是「要不要選 API」，而是選定後怎麼執行）
```

| 層級 | 是什麼 | 現況數量 |
|---|---|---|
| **Routing Hint** | `categories` → 可能的 Face | 21 組面向 |
| **Action Declaration** | `action_type`／`form_id`／`trigger_mode` | 336 direct_answer／37 form_fill |
| **Execution Configuration** | `grounding_scope`／`required_slots`／`execute_*` | 15/21 面向為 API-grounded |

- 6.1 系統文件 SHALL 以上述三層描述 KB 攜帶的資訊，
  SHALL NOT 將三者統稱為單一種「capability」。
- 6.2 **Routing Hint SHALL 被視為提議**：`categories` 命中面向
  SHALL NOT 於文件中被描述為「命中即決定」。
- 6.3 **Action Declaration 不等於立即執行**：帶 `form_id` SHALL NOT 被理解為
  「有 form_id 就直接開表單」——`trigger_mode`（manual／immediate／auto）另有分支。
- 6.4 **Execution Configuration 僅在 Face／Action 選定之後生效**，
  SHALL NOT 被描述為 routing 階段的選項。
- 6.5 系統文件 SHALL 明確區分
  `knowledge_categories`（描述知識主題）與 `routing_faces`（允許提出哪些 Face）。
- 6.6 WHEN 新增或修改任何具 routing／action 意義的 metadata，
  THEN 該變更 SHALL 經與程式碼變更同等的審查與回歸驗證——
  補 34 筆 `categories` ≠ 資料完整性修復，而是**新增 34 個 Face entry point**。
- 6.7 ⚠️ 本層級模型為**責任描述**，**不要求**新建任何 decision component。
  現況為 rule-based commit；pre-entry routability gate 實測錯路由攔截率 1/13，
  **已證明現階段沒有理由新造中央 selector**。
- 6.8 本 spec **不要求**立即變更 DB schema；語義分層先落於文件與審查流程。

## Requirement 7：測試成本控制

**背景**：`.kiro/steering/testing.md` 已有「控制成本：避免大規模執行產生過高 API 成本」原則。
現況 integration 層的 brain 與合成 LLM 已腳本化（183 測試 36 秒、零 OpenAI 呼叫）。

- 7.1 unit 與 integration 層 SHALL 維持零外部 LLM 呼叫。
- 7.2 WHEN e2e 層需真實 LLM，THEN 其規模 SHALL 受控並於文件標明預期成本量級。
- 7.3 分析與標註工作 SHALL 優先由人／協作代理直接判斷，
  SHALL NOT 為了省事而外包給大量 API 呼叫產生不可靠標註
  （本輪已有前例：43 案 × 6 次的 LLM 判定，事後複核發現誤判）。

---

## Requirement 8：範圍邊界（明確不做）

以下項目 SHALL NOT 納入本 spec 實作，各有實測依據：

| 項目 | 不做的依據 |
|---|---|
| always-on query rewrite（b2b）| A/B 10 情境×3 次 **10/10 行為完全相同**；成本 600–800ms／次；已停用 |
| 新的全域 routing selector | 既有 brain 前移即有能力，不需新造判斷模型 |
| pre-entry routability gate 上線 | 上游凍結後實測錯路由攔截 **1/13**，作用面不成比例；程式保留、flag 預設關 |
| KB event/object/condition 全面結構化 | selector 實測不需要結構化欄位；現有四欄尚未填滿 |
| 為架構完整性硬加 hybrid recall | 21 筆中召回可救約 1 筆；且詞面通道已部分存在 |
| B 澄清分岔 | brain 對 **Route-R3** 全數判 `stay`，不具 ambiguity 偵測能力，列研究項 |

---

## Requirement 9：結論分級與驗收基準限制

**背景**：目前**無 production holdout**（S3 客服回報自 2026-07-29 零新增）。
現有兩層基準：`test_scenarios` b2b 未污染集 241 筆（`created_by=backtest_user`，來歷未確證）、
72 筆 routing cohort（有 **Route-R1–R5** 人工標註，67 筆仍會提出面向 routing）。

- 9.1 WHEN 僅通過現有基準，THEN 結論 SHALL 僅聲稱「技術可行／regression-safe」。
- 9.2 「routing 品質確實提升」SHALL 僅在通過 production holdout 後聲稱。
- 9.3 任何關於**整體品質提升、precision／recall 改善、元件優劣或泛化效果**的
  比較性結論 SHALL 以 **≥30 個可判定案例**為基礎
  （本輪三次「擴大樣本即翻盤」：25 筆語料污染／72 筆標註失真／8 題改寫比較）。
  **不受此限**：deterministic contract 驗證、單一 bug 重現、已知 case 的回歸——
  這些不是統計性結論，不需湊題數。
- 9.4 離線驗證 SHALL 完整複刻**該版本 production 實際啟用**的候選變換與執行順序。
  被 feature flag／mode **關閉**的能力 SHALL NOT 在 runner 額外啟用；
  **降級路徑 SHALL NOT 被誤模擬為並行主路徑**。
  （本輪已三次因 runner 保真度不足而結論作廢。）

  **目前 b2b snapshot（隨 production 變動，以參數台帳為準）**：

  | 項目 | 現況 |
  |---|---|
  | always-on query rewrite | **OFF**（`ENABLE_QUERY_REWRITE_B2B=false`）|
  | vector retrieval | **primary** |
  | keyword search | **embedding failure fallback**（非並行 hybrid）|
  | routing 判定 | 用 **anchor removal 之前**的 top-1 |
  | anchor removal | 在 routing **之後** |

---

## Requirement 10：面向內對話邏輯的品質必須可量測

**背景**：Req.3 只驗面向的**管線**（狀態→API→grounding→答案「有沒有跑通」），
**未驗對話本身好不好**。本輪已實測到兩個缺陷，且兩者都不是路由錯：

| # | 實測 | 病灶 |
|---|---|---|
| 1 | 「續約 12 個月後在帳單頁找不到帳單」→ 進面向 → 反問「請提供合約編號**以便查詢租客帳號狀態**」 | **進對面向、問錯問題**——使用者問續約帳單，面向去查帳號狀態 |
| 2 | 「合約**已經簽約了**但我想修改可以嗎？」→ 反問「想修改哪個項目？」 | **繞過使用者已陳述的前提**——完全沒提「已簽約不能改」。對照組「還在簽署中可以改嗎」得到幾乎相同回應：**兩個相反前提、同一個答案** |

- 10.1 系統 SHALL 能量測面向內對話的下列指標，且量測方式可重複執行：
  **反問對題率**（反問內容是否針對使用者的實際訴求）、
  **前提衝突處理率**（使用者已陳述的事實是否被納入，而非要求重做已完成的事）、
  **輪數分佈**（收斂前的平均／最大反問輪數）、
  **重複詢問率**（是否重問已回答過的欄位）。
- 10.2 WHEN 使用者訊息已陳述可判定的前提（如「已經簽約了」），
  THEN 面向的首輪回應 SHALL 反映該前提，
  SHALL NOT 僅收集槽位而不回應其實際訴求。
- 10.3 WHEN 面向的反問偏離使用者的原始訴求，
  THEN 系統 SHALL 可由量測識別出該情形——**不得僅以「有回應」視為通過**。
- 10.4 `required_slots` 的設計合理性 SHALL 納入評估：
  是否索取了面向實際不需要的欄位、是否遺漏必要欄位。
- 10.5 ⚠️ **先量現況、建立基準，再談優化。**
  本 spec SHALL NOT 在無基準的情況下調整對話規則文字——
  本輪已五次因小樣本或未驗因果而結論翻盤（見 R9.3）。

---

---

## 需求優先序

> ⚠️ **不得依編號順序執行**。Req.4 是 Req.3 可驗的前提。

```
Req.1  測試基礎設施                       ← 所有驗收的前提
   ↓
Req.2  現有面向進場 regression 判定
   ↓
Req.4  Mock contract／fidelity            ← Req.3 的前提
   ↓
Req.3  API-grounded E2E 閉環
   │
   ├─ 失敗 → execution chain 升 P0，routing 工作降級（3.4）
   └─ 通過
        ↓
Req.5  已知缺陷逐項修復（5.2 須獨立上線）
        ↓
Req.6  Routing hint／Action／Execution 責任分層
        ↓
Req.10 Face 對話品質 baseline（依賴 Req.1、Req.3）
```

Req.7／Req.8／Req.9 為橫向約束，適用於全程。

**命名約定**：`Req.N` 指本文件的需求編號；`Route-R1`–`Route-R5`
指 routing cohort 的人工標註類別（正確-錨點／正確-一般KB／方向對但證據錯／
明確錯路由／可議），兩者不得混用。
