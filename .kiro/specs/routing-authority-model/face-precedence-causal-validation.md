# 刀 A causal validation：注入技術故障，走真控制流

- 日期：2026-08-28｜依據：裁定 001-B（刀 A APPROVED）後的必要 causal validation
- 標的 commit：`b2990af`
- 性質：**本機**故障注入。⛔ 不碰 production 資料，也**不**冒充 P2.5 完整 acceptance。

## 驗收命題（事前鎖死，不事後放寬）

```text
前提：真 handle_retrieval／真入口／真 retrieval／真 responsibility resolver control flow
      只把 evaluator 技術性弄壞；不改 routing code、不改 fixture、不改 assertion
第 3 列：technical_fail_open ＋ 有 direct-answer Knowledge → **Knowledge 勝出，Face 不得 commit**
第 4 列：technical_fail_open ＋ 無 Knowledge            → 相容性 Face 仍可進場，
                                                          但 responsibility_confirmed=false
```

## 故障注入怎麼做（**靶找錯過一次，記錄下來**）

```text
❌ 第一次：把 OPENAI_MODEL 指向不存在的模型 → **evaluator 沒壞**，resolver 照樣給真 verdict。
   原因：`conversational_step_result` 讀的是 `PRESALES_SYNTH_MODEL`（fallback 才到 config["model"]），
         不是 OPENAI_MODEL。⇒ 只讀 env 名稱猜靶會猜錯，必須追到實際取值那一行。
✅ 第二次：PRESALES_SYNTH_MODEL=<不存在的模型>，其餘保持健康。
   Knowledge 直答走 `PRESALES_ANSWER_MODEL`（`cta_mode != "force"`），故直答與 gate 不受影響。
⚠️ compose 原本未透傳 RELEVANCE_GATE_MODEL／PRESALES_ANSWER_MODEL（程式讀得到、compose 沒給），
   為了外科式注入曾**暫時**加上，驗完已還原。
```

`before → inject → 兩個 case → restore → **container runtime readback**`。
最後一步不可省：曾被「host 設定 ≠ container 實際設定」咬過。還原後 `diff` 基線讀值＝**無差異**。

## 結果

### 第 3 列 ✅ CONFIRMED（完整 causal chain）

query：`收據 PDF 在哪裡下載`（b2b／property_manager／role 20151）

```text
🧭 [responsibility resolver] bill_diagnosis[stay] → commit bill_diagnosis
                             **但無 authority**（technical_fail_open）→ 延後
⏸️ [face-precedence] bill_diagnosis 無 authority（compat_fail_open）→ 延後，Knowledge path 先走
🛡️ [錨點防呆] 濾除 2 筆空答案錨點
✅ [face-precedence] Knowledge candidate 存續 → Knowledge 勝出，bill_diagnosis 不進場
                     （技術故障不得取得 routing authority）
```

telemetry（`usage_events.decision_snapshot`）：

```text
commit_source=technical_fail_open｜has_commit_authority=false｜fail_open=true
hops[0].decision_source=technical_fail_open
routing_verdict=direct_answer｜processing_path=param_answer
回應：action_type=direct_answer、source_count=3、真實知識答案
```

**對照組**（同一句注入前，evaluator 健康）：`commit_source=model`／`has_commit_authority=true`／
`routing_verdict=enter_facet` ⇒ 差異確實由 authority 造成，不是問句本身變了。

### 第 4 列 ⚠️ PARTIAL——分支選對、進場有嘗試，但**走不完**

query：`這張帳單的收據金額多少`（Knowledge 被錨點防呆＋gate 清空）

```text
⏸️ [face-precedence] 延後 → Knowledge path 先走
⚠️ [face-precedence] 相容性 Face 進場亦降級 → 落回既有處理
telemetry：commit_source=technical_fail_open｜has_commit_authority=false
           routing_verdict=direct_answer｜processing_path=no_knowledge_found
```

已證：Knowledge 消失後**確實**選了 `compat_face` 並嘗試進場——刀 A **沒有**把相容性候選丟掉
（這正是 M5 在 unit 層守的那件事）。

未證：相容性 Face **成功完成**進場。原因是**注入手法的限制**，不是刀 A 的缺陷——
pre-entry evaluator 與 in-session 引擎共用同一個模型設定，弄壞前者必然一起弄壞後者，
於是進場後立刻降級。要驗完整第 4 列，需要能只弄壞 pre-entry 的注入點（目前不存在）。

## 這次證據把刀 A 升到哪裡

```text
✅ VALIDATED on real entry/control-flow under injected technical failure：
   除 deterministic unit／mutation 外，第 3 列（技術故障不得取得 Knowledge precedence）
   已取得 causal runtime evidence。
⚠️ 第 4 列僅取得「分支選擇＋進場嘗試」的 runtime evidence，完成路徑仍只有 unit（M5）覆蓋。
❌ 仍不得宣稱：P2.5 完整 PASS／integration deterministic／routing regression fixed。
```

## 仍未完成（另案）

```text
P2.5 full acceptance：Face 進場後 → 識別碼 → real grounding → grounded answer。
⚠️ `p2-4-production-smoke-result.md` 明訂不得直接對 production 跑，該限制未解除。
```
