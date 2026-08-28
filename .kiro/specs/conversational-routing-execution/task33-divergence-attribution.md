# 任務 3.3：divergence 歸因（**只歸因，不修**）

- 日期：2026-08-28｜環境：`aichatbot_test` ＋ frozen corpus，dev compose（`env_file: .env`）
- 證據：`evidence/task33-divergence-evidence-packet.json`（9 案 × 兩側 × 逐節點）
- 方法：逐節點並排「舊 harness（`97449f4^` 的 `_route`）」與「production seam」，
  依 3.3-b 的節點順序找**第一個**分歧點。

## 先排除已被點名的兩個候選（**實測，非照抄**）

```text
測試容器實際解析值：
  env KB_SIMILARITY_THRESHOLD = 0.65  → 舊 harness 0.65 ／ production kb_threshold 0.65
  env FORM_TRIGGER_THRESHOLD  = 0.75  → production form_trigger 0.75
⇒ 門檻兩側同值，確認非現行分歧。`top_k` 兩側皆 5。
```

⚠️ probe 第一版有保真度缺陷並已修正：production 側原本回報**提名分類**，
而真 harness 回報的是 **resolver 收斂後面向**的 `topic_scope.category`。
未修正前所有案例都顯示「無分歧」——**resolver 造成的分歧會整個看不見**。

## 結果（9 案）

| 問句 | 期望 | 舊 harness | production seam | 第一個分歧節點 |
|---|---|---|---|---|
| 點退的前置條件是什麼 | 單發 | single | single | **無** |
| 合約快到期了，系統會自動提醒我嗎？ | 單發 | single | single | **無** |
| 我的合約狀態怪怪的 | 進對話 | dialog／狀態判斷 | dialog／狀態判斷 | **無** |
| 點退帳單的金額是怎麼算的 | 單發 | dialog／條件診斷：帳單 | **single** | applicability(resolver) |
| 系統怎麼算點退帳單的金額 | 單發 | dialog／條件診斷：帳單 | **single** | applicability(resolver) |
| 點退做完後，帳單會自動出來嗎？ | 單發 | dialog／條件診斷：帳單 | dialog／條件診斷：帳單 | **無** |
| 收據 PDF 在哪裡下載 | 單發 | dialog／條件診斷：帳單 | dialog／**帳單異常** | applicability(resolver) |
| 幫我查點退帳單金額 | 條件診斷：帳單 | dialog／條件診斷：帳單 | dialog／**退租收尾** | applicability(resolver) |
| 我的這張點退帳單金額怎麼算出來的 | 條件診斷：帳單 | dialog／條件診斷：帳單 | dialog／**帳單異常** | applicability(resolver) |

## 判定

### A. 3.3 表列「舊紅 → seam 綠」三筆 → `NO_LONGER_DIVERGENT`

```text
三筆逐節點**完全一致**，且三筆都符合凍結期望。
⇒ 無法判 HARNESS_DRIFT——3.3-c 要求「必須指名第一個分歧節點」，
   而這裡**沒有分歧可指名**；也不需要修。
⚠️ 這推翻 3.3 記載的前提（「三筆轉綠為 candidate HARNESS_DRIFT」）：
   該分歧在今天的 corpus 與程式上**不再可觀測**。
   ⛔ 不得回頭引用那三筆當 harness drift 的證據。
```

### B. 舊／新一致但仍不符期望（點退做完後）→ **不是** harness drift

兩側都進對話，期望單發。這是 production 行為與凍結期望的衝突，
候選判型為 `REGRESSION` 或 `EXPECTATION_DRIFT`（見下方待裁定）。

### C. 分歧節點＝`applicability(resolver)` 四筆 → 節點已指名

舊 harness **完全沒有**適用性節點（3.3-b 表格自己就寫「—（舊 harness 無）」），
production seam 有 instance gate ＋ responsibility resolver。
就「舊 vs 新」這一對而言，這是**可指名節點的 HARNESS_DRIFT**。

⚠️ 但那只解釋「舊 harness 為什麼不同」，**不解釋** production 為何不符期望。

## 根因（B、C 共通，這才是實質發現）

```text
① instance-reference gate **未啟用**：
   gate_active() = gate_requested() ∧ gate_authorized()
     gate_requested()  env 旗標，預設 false
     gate_authorized() 需現行規則集通過 matching holdout
   實測九案的 instance_gate 全為 None ⇒ 設計上用來擋「規則型問句」的
   **決定性**機制目前是關的。
② 於是規則型問句擋不擋，實際由 **LLM resolver** 決定，而它對**語義等價**的問句
   給出不一致判定：
     「點退帳單的金額是怎麼算的」  → resolver no_face          → 單發 ✅
     「系統怎麼算點退帳單的金額」  → resolver no_face          → 單發 ✅
     「點退做完後，帳單會自動出來嗎？」→ authoritative commit    → 進對話 ❌
     「收據 PDF 在哪裡下載」      → authoritative commit(billing_anomaly) → 進對話 ❌
```

⇒ 這同時解釋了先前量到的 integration 噪音（同碼同 selection 連跑三次 7／6／5）：
**失敗數的擺動來自 resolver 的 LLM 判定，不是測試環境不穩。**

## 待裁定（依規約，歸因後遇到產品語義問題即停）

```text
Q1 規則型問句該由誰擋？
   (a) 先讓 instance-reference gate 通過 matching holdout 並啟用（決定性、可測）
   (b) 維持由 resolver 判（現況；語義等價問句會不一致，且回歸測試恆有噪音）
   ⇒ 選 (a) 才可能讓 3.4「全部案例通過」是穩定的。

Q2 「幫我查點退帳單金額」凍結期望是進「條件診斷：帳單」，
   但 resolver 依契約白名單委派到 contract_closeout／billing_anomaly。
   裁定 001／001-A（2026-08-27）已賦予 responsibility resolver commit authority，
   時間**晚於**本表凍結（2026-08-23）。
   ⇒ 這是否構成 `EXPECTATION_DRIFT` 的書面依據，可改寫凍結期望？
   ⚠️ 3.3-c 明訂依據**不得為「測試沒過」本身**——需要你判定裁定 001 是否即為該依據。
```

**在 Q1／Q2 裁定前，3.4 不得開始**——否則只能靠改斷言收尾，那正是 3.3-c 禁止的預設處置。
