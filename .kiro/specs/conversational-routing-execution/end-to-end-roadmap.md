# 從現在到結案的完整順序（對話邏輯主線）

> 2026-08-26｜語言 zh-TW｜業主指示：「可以先修保真度，但我要知道整個順序，
> **不要修完就當作結案**。」本檔就是那份順序，也是結案的定義。

## 〇、結案不等於測試綠

```text
❌ 結案 ≠ unit/integration 全綠      （那只證明程式沒炸）
❌ 結案 ≠ 替身與 production 契約一致  （那只證明「如果打得到，形狀會對」）
✅ 結案 = 真 brain 回歸過 ＋ Stage-1 上線 ＋ telemetry 看得到效果 ＋ 業主放行
```

## 一、五個階段，依賴是單向的

```text
P0  資料保真（現在做，免費，不需授權）
     └─ 為什麼在最前面：三個「線上靜默失效」證明**答錯話的根因在資料層**，
        不修完，P1 的真 brain 會在錯的輸入上取證，等於白花錢。
     完成條件：T2 消費端契約全掃無 P0 殘留；T3 情境分支有覆蓋或具名 GAP。
     ⚠️ **不含** T1／T4／T5／T8——那些是驗證能力的債，不擋 P1，降為背景。

P1  M3：真 brain v6 回歸（**需授權，付費**）
     內容：真 brain ＋ migrated test DB ＋ scoped gate ＋ JGBMockTransport ＋ v6 尺
     規模：4 案 ×3 次、硬上限 30 次呼叫；brain gpt-4o@0.4、合成 gpt-4o-mini@0.2
     成本：以公開費率量級估算為**個位數美元**
     ⚠️ v6 只是 regression，**不得回寫 v5**；v5 的 machine verdict 永久保留
     完成條件：v6 尺三項（正確 instance 進答案／沒串到別筆／沒退化成通用答案）全過

P2  R：上線（**需授權，逐條指令由業主自跑**）
     順序：staging migration → real API smoke → production migration →
           Stage-1 scoped rollout → 觀察 telemetry
     Stage-1 值：PREENTRY_ROUTABILITY_GATE=true
                 PREENTRY_ROUTABILITY_FACETS=bill_diagnosis,billing_anomaly,contract_closeout
     ⚠️ 只開 GATE 不設 FACETS ＝ fail-safe 停用，等於沒上
     完成條件：Stage-1 面向在線上跑滿一個觀察窗，且 telemetry 有逐跳結構可讀

P3  觀測（**目前 BLOCKED_BY_OBSERVABILITY**）
     實況：turn_number 與 decision_snapshot.user_turns **全表 0 列**；
           chat_history／conversation_logs／unclear_questions 皆 0 列；
           scope=switch 退出**不發 facet_event**
     ⇒ 沒有這一層，P2 上線後**無法回答「有沒有變好」**。
     缺口已登記 OBS-1／OBS-2／OBS-3。補法屬另開的 observability 線，不塞進本線。

P4  routing-authority-model（**BLOCKED_BY_EXTERNAL_DECISION**，與 P1-P3 平行）
     等 responsibility-governance-decision-record 的四項產品裁定。
     ⚠️ 工程端不得代填、代猜。四題若答「沒有固定規則」→ 那本身就是結論。
```

## 二、模型選擇是**產品組態**，不是測試選項

```text
現行：production brain = PRESALES_SYNTH_MODEL，預設 **gpt-4o**
      （docker-compose.prod.yml:134；程式讀取點 llm_answer_optimizer.py:961／:1088）
      其餘角色各自不同：OPENAI_MODEL 預設 gpt-4o-mini、QUERY_REWRITE_MODEL mini、
      IMAGE_RECOGNITION_MODEL／DOCUMENT_CONVERTER_MODEL gpt-4o
為什麼 M3 用 gpt-4o：C4b 凍結參數要求**在 production 實際跑的 brain 上取證**
      （c4b-run-parameters-frozen.md ①）。dev compose 曾漏宣告該變數，
      測試容器會靜默落回 mini —— 本專案**已三次因 runner 保真度不足而結論作廢**。
```

**分岔（需要業主決定，會改變 P1 的時機）**

```text
A 維持 gpt-4o → 直接跑 M3。得到的是「現行 production 組態」的回歸證據。
B 想升級 brain 模型 → **先換再跑 M3**，否則量的是一個即將被丟掉的組態。
  換模型是產品決策，代價是所有面向的答話都會位移，需要自己的回歸預算。
⚠️ 不論 A/B，M3 都必須跑在**與 production 同一個模型**上，否則證據無效。
```

## 三、每個階段的停止條件（防止「做完就當結案」）

```text
P0 完成 → **不得**宣稱對話邏輯已改善，只能說「答錯話的資料層根因已清」
P1 完成 → **不得**宣稱可上線，只能說「執行鏈在真 brain 下未回歸」
P2 完成 → **不得**宣稱有效，因為 P3 尚未成立，「有沒有變好」量不出來
P3 完成 → 才有資格談效果；此時才回頭決定 P4 是否仍是阻擋
```

## 四、現在的位置

```text
P0  進行中（20/22 端點已稽核；T2 未開始 ← 下一步）
P1  等授權（成本個位數美元）
P2  等授權
P3  BLOCKED_BY_OBSERVABILITY
P4  BLOCKED_BY_EXTERNAL_DECISION
```
