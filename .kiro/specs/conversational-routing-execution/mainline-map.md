# 主線收束盤點（2026-08-29）

分支 `fix/retrieval-routing-stability`｜領先 `main` **268 筆**｜**從未 push**（遠端含此 commit：0）

---

## 一、已 CLOSED / CONFIRMED

```text
✅ 裁定 001 / 001-A：authority governance
   category = nomination evidence ≠ commit authority
   decision_source 四值｜face_precedence 單一仲裁 oracle｜`.stay` 降為行為述詞＋AST 守衛
   ⇒ technical_fail_open 不再能冒充 authoritative commit

✅ Stage 1 nomination observability ＋ measurement contract
   entry_source 七值／top1/categories/完整候選/epoch digest
   scripts/analysis/stage1_nomination_funnel.sql（Q0–Q4，凍結）
   ⚠️ 「靜態架構事實」與「production 流量分布」**已分開**——
      前者不必等流量（本輪多數發現都來自靜態盤查），後者才需要

✅ 不變量 9：Face preemption 的能力保全
   抓的是**能力**不只端點宣告；三層判定（無能力 FAIL／分流 WARN／端點未涵蓋 WARN）
   自我測試 12 條（五形狀＋row 層彙總＋四組突變控制）

✅ 21 筆 diagnostic ownership census
   結論：面向化遷移漏的**主要不是 mapping，是能力**

✅ billing_invoice ＋ jgb_invoice_logs（能力回補）
✅ billing_flow ＋ jgb_bill_detail（能力回補）
✅ 11.5 repair_create 五槽 wiring：PARTIALLY CONFIRMED → **CONFIRMED**
✅ holdout-validation skill 入 repo
```

---

## 二、已修復，但 acceptance 帶 claim ceiling

```text
◐ subscription capability migration
  ✅ ACCEPTED within tested read-only scope
  ⚪ subscription responsibility authority = **NOT EVALUATED**
     （subscription_diag 不在 PREENTRY_ROUTABILITY_FACETS ⇒ authority=unevaluated，
       現行仍是「檢索提名了誰就 commit 誰」）
  ⚠️ D 分支：三個 entry point 皆 reachable，但**失敗子分支未在線上走到**
     （線上 role 健康：is_subscribed=1、remain=134/200）→ NOT EXERCISED，非 FAIL

◐ 11.5 五槽
  ✅ 五槽對帳完成、[0] index sensitivity 已證、Vision 候選填錯 estate_id 已修
  ⛔ **無真實 POST /repairs acceptance**（會在 production 開單）
     ⇒「payload 抵達 API」由簽名對帳＋sentinel 映射證明，不是線上證據
```

---

## 三、PAUSED / BLOCKED

```text
⏸ instance gate authorization   —— 業主暫停，且已證明現行 scope 下無法有效驗證
⏸ 3.4                            —— 隨 gate 暫停
⚪ subscription authority scope   —— 是否納入 PREENTRY_ROUTABILITY_FACETS
   ⛔ 本輪 smoke **不是**該授權的證據

⚠️ 三者都不因「其他 routing 問題修好了」而自動解凍。
```

---

## 四、已知 debt，不擋主線

```text
ONLINE_FAILURE_STATE_COVERAGE      subscription failure-state 無真實線上樣本
SUBSCRIPTION_PRESENTATION_FIDELITY subscription.py:103 硬編 NT$（忽略 plan_currency='TWD'）、
                                   plan_cycle 原樣輸出 "/year"
INV9_WARN_3366                     「繳費成功 繳費紀錄」表單端點 jgb_payments 未被 billing_flow 涵蓋
                                   （同 3502 型，但無「標題＝engine docstring」那級證據）
INV9_WARN_3548                     payment_gateway_select 分流表單（同 3508／3522 家族，by design）
INV4_WARN_修繕報修                  查無系統脈絡（既有）
MIXED_CATEGORY_GRANULARITY         合約管理 43／帳單管理 26… 同一 category 混載制度與實值
                                   ⇒ category 連當 nomination evidence 可能都太粗（延伸裁定 001）
```

---

## 五、尚未上線 / release 狀態

```text
❌ 不變量 3 現為紅：services/conversational_engine.py 與 services/jgb/repair_prefill.py
   容器與本地不一致 —— ⑧ 的修正在重建**之後**才寫入
   ⇒ source 已驗（1517 unit 全過），**runtime 未同步**
   指令：docker compose -f docker-compose.prod.yml up -d --build rag-orchestrator

📦 268 筆 commit 未 push、未進 main、未部署
📉 Stage 1 telemetry 僅累積 10 筆（本機，多為本輪探測）⇒ funnel **無可分析資料**
```

---

## 六、Release policy（2026-08-29 業主定案，**修正前一版**）

```text
U2 release = **BLOCKED_BY_VALIDATION_COMPLETION**   ⛔ 不是「待裁」

> 這整條 conversational routing／authority／nomination 架構
> 在本地完整驗完以前，一律不 push／不進 main／不部署。

目前全部成果只是 **local candidate implementation**。即使
  unit 1517/0 ・audit 九條全綠 ・runtime container 已同步
  ・capability smoke 通過 ・Stage 1 observability 完成
也**都不構成**「先上去收 production data」的理由。
```

### 連帶：Stage 1 telemetry 重新定位

```text
⛔ 舊定位（錯）：先部署 → 收流量 → 才能繼續
✅ 新定位：**本地驗證與未來上線後監控共用的 observability infrastructure**

現在就可以拿它跑：
  ・專案內全 KB／config census
  ・released 真實語料
  ・已有的未污染 corpus
  ・mechanically generated scenario matrix
  ・deterministic fixtures
  ・isolated synthetic holdout
⚠️ 但這些結果**不得冒充 production distribution**。
```

---

## 七、唯一仍屬主線的命題：U1

```text
【U1】category 是否足以承擔 nomination evidence
```

⚠️ **問題已改寫**——不再是「等流量」，而是：

> **在不靠 production deployment 的條件下，現有專案與可取得語料，
> 是否已足以判定 category 作為 nomination primitive 的資訊量是否足夠。**

```text
U1 的本地證據面
├─ 靜態全量 evidence（全 KB／config census）
├─ 真實但未污染語料（若可取得）
├─ synthetic —— **僅作結構探測**，不得外推覆蓋率
├─ candidate-generation alternatives（若 U1 被 refute 才需要）
└─ deterministic / holdout validation（走 holdout-validation skill）
```

兩種合法結局，⛔ 沒有第三種：

```text
① 本地證據足夠 → 就地裁掉 U1
② 本地證據不足 → 明確標成 **NOT_VALIDATABLE_WITH_CURRENT_LOCAL_EVIDENCE**
⛔ 不得為了收 production data 而提前 release
```

---

## 八、收束順序

```text
U1 本地驗完
→ instance gate authorization
→ 3.4
→ subscription authority scope（若仍屬完整架構驗證範圍）
→ final regression ＋ final audit ＋ clean local runtime acceptance
→ **才談** push / main / deploy
```

### 這一輪反覆出現的同一種失敗模式（保留）

```text
nomination  ≠ authority                （裁定 001）
select=api  ≠ capability equivalence   （不變量 9 端點涵蓋層）
有資料流     ≠ 流到正確的語義槽位        （插點 A 候選填錯 estate_id）
共同形狀：**形式上有接線，不等於語義上接對。**
```
