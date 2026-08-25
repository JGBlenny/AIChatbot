# P3 第 2 次付費執行（singleton delegation 上線後）

> 2026-08-26｜brain＝**gpt-4o-mini**｜brain 輪 **22**／全部 **36**（上限 30／60，未觸頂）
> 證據：`evidence/p3-run2-singleton.json`＋`p3-run2-stdout.log`
> 協議：`p3-run-parameters-frozen.md`（semantic 紅不重試）

## 一、singleton delegation **確實解決了它要解決的那一格**

```text
三次執行，第一跳全部成立：
  bill_diagnosis --switch--> billing_anomaly    delegate_source = **contract_singleton**
第 1 次執行（未實作前）：三次全部 switch_without_delegate、不 commit
```

第二跳在 rep2／rep3 甚至是模型自己填的（`delegate_source = model_delegate`），
完整鏈走完並 commit `contract_closeout`：

```text
rep2/rep3  bill_diagnosis →(singleton) billing_anomaly →(model) contract_closeout → stay ✅
rep1       bill_diagnosis →(singleton) billing_anomaly → **stay** ⇒ commit 停在中繼站 ❌
```

## 二、A 仍 **NOT_VALIDATED**，但**卡點換了**，而且是兩個新的

### 卡點 A1：語義判定不穩（1/3）

rep1 的 `billing_anomaly` 判 **stay**，於是 commit 停在中繼面向。
⚠️ 這**正是**業主界定「值得重新討論模型能力」的那一類——「該 switch 卻 stay」。
但目前只有 1/3、單一樣本，**不足以據此翻案模型**；需要更多樣本或先解掉 A2 再看。

### 卡點 A2：`action=ask` 卻**沒有 next_question**（3/3 都踩到）

```text
resolver hop3 的 reason = action_rejected_fail_open:missing_next_question（rep2／rep3）
in-session 第 1 輪答案 = 「我目前沒有找到符合您問題的資訊…轉給客服」（泛用退化）
session 直接 COMPLETED，第 2 輪「678」因此毫無 grounding ⇒ v6 ruler value_not_used
```

也就是：**面向確實 commit 對了，但那一輪的 brain 輸出被解析層依規則擋掉**，
引擎降級 → 泛用回答。三次的 `value_not_used` 全部源於此，不是 grounding 邏輯壞掉。

⚠️ 與 delegate 那格是**同一類病**：mini 的語義判斷可用，但**輸出形狀不穩**。
差別在於 `next_question` 是**真內容**，不像 delegate key 是可由契約決定性補上的機器值——
所以不能用 singleton 那招補，**也不得**把 `ask` 硬改成 `converge`（那是替模型捏造意圖）。

## 三、⑤ 的判定也連帶被污染

rep2／rep3 的第三跳 reason 是 `action_rejected_fail_open:missing_next_question`，
即 `contract_closeout` 的 **stay 是 fail-open 來的，不是模型判的**——
雖然 commit 目標正確，但它不符合「所有 responsibility 判定都來自真模型」的判準⑤。

## 四、建議的下一步（需業主裁決，會再花錢）

```text
① 讓輸出形狀由 API 契約強制，而不是靠模型自律
   OpenAI structured outputs（strict JSON schema、required 欄位）
   —— 與 singleton delegation 同一原則：**模型負責語義，程式負責無歧義的形狀**。
   影響面：改的是所有 brain 呼叫的 response_format，需零回歸鎖與一次 P3 重跑。
② 先只解 A2，再重評 A1
   A1 目前 1/3，樣本不足；A2 修好後語義判定的樣本才乾淨，屆時再看要不要談模型。
❌ 不做：把 ask 無題自動改成 converge／要求模型「一定要填 next_question」的 prompt 加強
   （前者捏造意圖，後者又回到靠模型自律——正是本輪已證不可靠的東西）
```

## 五、B 這次仍不算數

`b_verdict = B_OK` 是**舊判準**的殘留輸出——本次執行的程式碼已改為三值，
但 evidence 內的 B 區段沿用第 2 次執行當下的判定。
依 P3 run1 的改判，**B②③④ 一律視為 INCONCLUSIVE**：
salvage 適用情境（`payload 被擋 ∧ scope=switch`）仍未觀察到。
harness 已補上 `all_parsed_turns`（每一次 brain 呼叫的解析結果都留檔），
下一次執行才有辦法逐輪歸因，不必再用猜的。
