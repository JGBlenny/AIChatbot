# P3 第 1 次付費執行結果（**A：NOT_VALIDATED；B：改判 INCONCLUSIVE**）

> 2026-08-26｜語言 zh-TW｜協議 `p3-run-parameters-frozen.md`
> brain＝**gpt-4o-mini**（容器內實測 `PRESALES_SYNTH_MODEL=gpt-4o-mini`）
> 呼叫量：brain 輪 **7**／全部 provider **30**（上限 30／60，未觸頂）
> 證據：`evidence/p3-run1-true-brain.json`＋`evidence/p3-run1-stdout.log`

## 一、A（pre-commit delegation）：**NOT_VALIDATED**，3/3 同一病灶

```text
期望鏈  bill_diagnosis --switch--> billing_anomaly --switch--> contract_closeout --stay-->
實得    bill_diagnosis --switch--> **None** ⇒ 不 commit ⇒ 無 grounding ⇒ 泛用回答
逐項    ① chain 不符｜② committed=None、session rows=[]｜③④ v6 ruler value_not_used
```

### 根因（決定性，不需再花錢就能歸因）

`resolver_capture` 的逐跳歸因三次一致：

```text
normalization_drop_reason = **not_allowed**
raw_scope = switch          normalized_scope = switch
raw payload 有 delegate_facet_key 這個鍵，但值是 **空字串 ''**
allowed_delegates = ['billing_anomaly']
```

⇒ **模型判對了「該轉交」，卻沒有填轉交目標**（回空字串，3/3）。
白名單正規化把空字串丟掉（正確行為），resolver 因此 `switch_without_delegate`、不 commit。

⚠️ **這是模型能力落差，不是程式缺陷**：同一條鏈在 gpt-4o 下（v5，2026-08-25）
三跳都走得完。統一 mini 的代價在這裡第一次被量到。

### 這一格**不重跑**

協議 §四明訂 semantic／assertion 紅**一律不重試**。3/3 同一原因、歸因決定性，
再跑只會再買一次同樣的答案。

## 二、B（mid-session scope salvage）：harness 給了假綠，**改判 INCONCLUSIVE**

實測觀察（真模型、兩次獨立會話）：

```text
SALVAGE=off  turn3 scope=switch（payload 正常）→ 會話殘留 COLLECTING
SALVAGE=on   turn3 scope=switch（payload 正常）
             turn4 payload 被擋：reject=**missing_next_question**、scope=**stay**
             → 會話未殘留
```

第一版判準只看 `payload_is_none` 就認定「越界情境出現」，於是把
**scope=stay 的拒絕**當成 salvage 證據，再拿兩次**獨立會話**的控制流差異當「salvage 生效」。
兩者都不成立：

```text
· salvage 分支的前提是 scope=='switch'；scope=stay 的拒絕根本不會走到它
· 跨會話比對控制流＝拿模型隨機性當證據
```

已修正判準（本次一併 commit）：必須是「payload 被擋 **∧** scope=switch」才算適用情境；
未出現時 **不比對** on/off 控制流，直接記 INCONCLUSIVE。

### B 目前能誠實宣稱的只有這一條

```text
✅ B①：真模型在中途岔題輪確實輸出 raw scope=switch（兩次執行皆有）
⏸ B②③④：**salvage 適用情境（越界 ∧ switch）未觀察到** ⇒ 無結論
   該分支由 unit `test_step_contract_layers_req.py`（16 passed）覆蓋，
   **不以決定性注入或跨會話雜訊冒充真模型證據**
```

## 三、下一步的三個選項（需業主裁決）

```text
① 維持 mini，改讓委派目標不依賴模型自由填寫
   （例：白名單只有一個候選時由 resolver 直接採用；或改為單選枚舉輸出）
   —— 修的是 output contract，不是模型；改完可再跑一次 P3-A。
② brain 單獨保留 gpt-4o（其餘維持 mini），承認委派鏈需要較強模型
   —— 與「統一 mini」的裁定相衝，需要你重新裁。
③ 接受 delegation 在 mini 下不成立，先只上 Stage-1 的非委派面向
   —— 範圍縮小，但 face-exit 這條線的主張就沒被證實。

B 的取證另需一次設計：讓「越界 ∧ switch」可被觀察，
建議做法是**捕捉真模型的原始 payload 後決定性重放**（標明為 replay，不冒充 live）。
```
