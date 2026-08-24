# Round 1 failure analysis：結果

> 2026-08-24｜語言 zh-TW｜依 `round1-failure-analysis-charter.md`（凍結）執行
> 分析對象：`round1-experiment-a.json`（frozen inputs：cohort `543d3e97b0a6afe6`｜labels `a3cf08354f180960`｜
> D1 spec `ebb5f542f14d5c09`｜D3 contract `9b1c12e154b0c85a`｜model `gpt-4o-mini`）
> ⚠️ 本文件是**診斷**，不重新宣告 member/family disposition（沿用 `round1-experiment-a-result.md`：
> D1-member-1／D3-member-1 皆 REJECTED for R1；D1/D3 family 皆 INSUFFICIENT_EVIDENCE）。

## 停止條件判定：**A 與 B 同時達成**（未觸發 D）

```text
A（evaluator/calibration 主導）  → D1-member-1：強證據
B（source information 不足）      → D3-member-1：強證據
C（shared abstraction 抹平 provenance） → 本輪證據轉弱（見下方「對 ③ 的修正」）
D（多因並存無法分離）              → 未觸發：A、B 各自有可分離、可歸因的證據
```

兩個 member 的失敗**不是同一種病**：D1 的病灶在「evaluator 沒有正確使用它自己已經拿到的證據」，
D3 的病灶在「contract 條列的 handles 清單本身不夠完整」。這比 Experiment A 結果文件當時給出的
單一「evaluator 主導」假說更精細，且部分**修正**了原文件的推論強度（見下）。

---

## D1-member-1：**F1 evaluator/calibration 主導**（16/17 = 94%）

判準：D1 spec 的核心準則是「query 是否指涉一個既存實體實例」。17 筆 false reject 中，
**16 筆的原始 query 文字本身含有明確指示詞**（這張／這筆／8月那張／9/15那張／剛剛那筆），
但 `d1_raw.reason` **明白宣稱該指示詞不存在**（例：「並未指涉特定的既存實體實例」）。
同一個 evaluator、同一次執行，在配對的 true accept 上又正確辨識了幾乎相同的指示詞結構。
這不是「軸線太細、判不準」的邊界模糊，而是**對已呈現在輸入裡的證據做出與輸入矛盾的陳述**。

### 三組配對舉證（同 Face、同語義操作、指示詞結構相同，一邊 accept 一邊 reject）

| Face | TP（accepted） | FN（rejected，reasoning 否認指示詞存在） |
|---|---|---|
| billing_flow | `bf-06-b`「**這張**租客多匯了一千，系統還顯示沒繳清」→ reason 正確引用「這張」 | `bf-08-b`「租客**這筆**分兩次匯，結果只認到第一筆」→ reason：「並未指涉特定的既存實體實例，而是描述了一個通則性的問題」 |
| billing_anomaly | `ba-10-a`「**這筆的**收據金額顯示 0，明明有收到錢」→ reason 正確引用「這筆的」 | `ba-06-a`「**這筆的**期間寫 7/1-7/31，但明明應該是八月份的」→ reason：「涉及到期間的正確性，而不是特定實體的現況」 |
| bill_diagnosis | `bd-01-a`「**這張帳單**我按收回都沒反應，是卡在哪」→ reason 正確引用「這張帳單」 | `bd-04-b`「**這張的**發送鈕是灰的，點不下去」→ reason：「並未指涉特定的既存實體實例」 |

唯一不含明確指示詞的一筆是 `ba-08-a`「同一個租客同一個月冒出兩張一樣的帳單」——這筆較適合歸為
F4（見下）：靠上下文（同租客＋同月）隱含指涉，而非指示詞詞彙表面特徵，屬於 D1 demand model
未覆蓋的辨識維度，不是 evaluator 誤讀。

**歸因**：D1-member-1 的失敗以 **F1** 為主（16/17），**F4** 補充解釋剩下 1 筆。

---

## D3-member-1：**F2 source 不足主導**，夾雜 F1 與 F4

D3 的 17 筆 false reject 與 D1 有 13 筆重疊，但**理由文字系統性不同**——D1 否認指示詞存在，
D3 幾乎全部引用**主題／責任範圍**（does_not_handle 或「未列於 handles」）。逐筆對照
`d3-face-responsibility-contract-v1.json` 的 handles／does_not_handle／self_scope_rule：

| 類型 | 筆數（約） | 代表案例 | 判定依據 |
|---|---|---|---|
| **contract 枚舉缺口**（該 topic 概念上該收，但 handles 清單沒列出這個變體措辭） | 7 | `ba-06-a` 帳單「期間」錯誤（handles 只列金額不對／沒出現／看不到，沒有「期間」）；`bf-05-a`「待對帳」（handles 只列「帳單狀態沒動」，沒把「對帳中」視為同一狀態的措辭變體）；`bf-08-b` 分次匯款只認一筆（同上，狀態措辭變體）；`ba-08-a` 同月重複帳單；`ba-09-b` 帳單姓名錯置；`bd-09-a` 到帳日順延；`bd-10-a` 明細存檔失敗 | contract 沒錯，但**列舉式** handles 對同義措辭沒有泛化能力 |
| **evaluator 誤判已存在的 entity 指涉**（與 D1 同型錯誤） | 3 | `bd-04-b`「這張的發送鈕是灰的」——「發不出去」明確在 handles，「這張的」明確存在，卻以 `entity_reference_required` 未滿足為由拒絕；`bd-06-a`「9/15 那張我想再重發一次」——同型；`bd-10-a` 同時具備缺口與誤判兩種特徵 | evaluator 沒有正確套用自己的 `entity_reference_required` 判準 |
| **contract 與 ground-truth 標籤本身有真實的跨 Face 邊界張力**（非 evaluator 或 contract 缺陷，是設計層級的界線問題） | 2 | `bd-02-b`「8月那張水電費現在還改得動嗎」——bill_diagnosis 的 `self_scope_rule` 明寫「金額組成…→switch」，「改不改得動金額」按字面就該轉去 billing_anomaly，但 ground-truth 標成 bill_diagnosis applicable；`bf-09-a`「入帳比帳單金額少，是被扣手續費了嗎」——同樣落在 billing_flow 的 does_not_handle「金額組成」 | **F4**：ground-truth label 與 D3 自己寫的 `self_scope_rule` 對同一句話給出不同的歸屬 Face |

**歸因**：D3-member-1 的失敗以 **F2**（contract 枚舉缺口，約 7/17）為主，
**F1**（evaluator 誤判既有 entity 指涉，約 3/17，與 D1 同型）與
**F4**（label 與 contract 自身 self_scope_rule 衝突，2/17）為輔。

---

## 對「85% 重合 → evaluator 主導」的修正（③，見 `round1-experiment-a-result.md`）

Experiment A 結果文件當時只看到**結果層級**的重合（D1/D3 分數完全相同、85% 逐句判定相同），
據此建立「evaluator 主導、provenance 影響有限」的強假說。本輪讀了 `d1_raw`／`d3_raw` 的
**理由文字**後，這個假說**部分不成立**：

```text
13 筆 D1／D3 同判 reject 的重疊項目中，理由文字系統性不同——
D1 一律訴諸「不指涉既存實體」（且經常與輸入矛盾），
D3 一律訴諸「不在該面向責任範圍」（且多數可對照 contract 條文找到依據或缺口）。
```

若真是「同一 evaluator class 主導、provenance 文本影響有限」，理由文字應該也高度重合——但沒有。
**修正後的表述**：outcome-level 重合（85%）主要來自**兩個獨立的失敗機制恰好落在多數重疊的題目
上**（D1 的指示詞誤判＋D3 的枚舉缺口，經常同時發生在同一批「措辭較不典型」的句子上），
而不是單一 evaluator 決策邏輯把兩份 provenance 文本壓成同一件事。
**不得**仍然引用 Experiment A 結果文件的③作為「evaluator 主導、provenance 無效」的完整結論；
應改引用本文件作為更新依據。

---

## 依充章「預先綁定」方向（本輪即生效，不等下一輪再議）

```text
D1（F1 主導，觸發 A）→ 下一輪不再做「文本 ＋ generic evaluator」形態的 D1-shaped member；
                       若要延續 candidate-specific adjudication 路線，
                       evaluator 必須先能在本 cohort 的 D1 exhibits 上穩定辨識指示詞，
                       否則不得視為已解決 F1。
D3（F2 主導，觸發 B）→ 仍留在 D3／Face-owned contract family，
                       但**列舉式 handles／does_not_handle 需換成可泛化的判準表示**
                       （而非窮舉措辭），不換 family。
                       F4 的 2 筆（bd-02-b／bf-09-a）留給 N3／design-discovery 處理，
                       屬於「contract 邊界定義」問題，不是本輪 member 品質問題。
```

## 未做、且依充章不得做的事

```text
❌ 未宣告 D1-member-2 / D3-member-2 PASS —— 本文件只做因果診斷，未重跑 cohort
❌ 未更新 family disposition —— D1／D3 family 仍為 INSUFFICIENT_EVIDENCE
❌ 未把 F1/F2 的診斷結果拿去主動找新的 misrouting 案例（N3 升格另案處理）
❌ 未動 production Face config／matching ruler／manifest
```
