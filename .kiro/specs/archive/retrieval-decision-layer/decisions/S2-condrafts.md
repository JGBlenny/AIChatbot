# S2 條文修訂草稿｜逐條 before → after（呈業主核准，核准後直接套進正文）

> 2026-08-19｜**這不是又一份修訂稿**——是任務 0.5 要寫進 requirements.md／design.md 的
> **實際文字**。核准後我把 after 欄貼進正文、`spec.json` 核准打回重走，本檔轉為決策紀錄。
> 涵蓋 D-04～D-08、D-11、D-14、D-16、D-17。**不含 D-01（R7.1）**——那條等 EXP-7 pilot。

---

## 修訂 1｜名詞定義「路由類別」（D-04）

**before**
> - **路由類別（routing class）**：一輪回應的行為歸類——直答知識（ANSWER）／面向索取識別（ASK_ID）／面向查無（FACET_EMPTY）／表單（FORM）／fallback（FALLBACK）。

**after**
> - **路由類別（routing verdict）**：一輪回應的**決策層判定去向**，由決策層產出並落決策快照，
>   **不得由答案文字反推**。值域為單一枚舉（C1 與 C3 共用，不得各自定義）：
>   `direct_answer`／`enter_facet`／`stay_facet_ask`／`stay_facet_answer`／`exit_facet`／
>   `degrade_knowledge`／`degrade_honest`／`form`／`fallback`。
>   - `stay_facet` 依「本輪是否在索取識別資訊」細分為 `_ask`／`_answer` 兩值——
>     **不細分則面向黏著（#07 型：使用者換主題、面向不放手）在此尺上前後皆為 stay，
>     判為一致，主病灶量不到**（D-24 教訓）。
>   - 舊五類名稱（ANSWER/ASK_ID/FACET_EMPTY/FORM/FALLBACK）僅保留於本 spec 立案前產生、
>     無決策快照的舊檔重判，須標 `legacy_text_classifier` 與版本戳，
>     且 **SHALL NOT 與 verdict 尺混計於同一統計**。

**理由**：C1 宣告六值 verdict、C6 卻用五值且從文字反推——同一份設計兩套詞彙。
五類無法表達「同類別但知識接地翻轉」（實測漏計 36% 不穩定輪）與面向內續留。

---

## 修訂 2｜R1.3（D-04、D-05）

**before**
> 3. THE 評測流程 SHALL 對每輪回應自動判定路由類別（ANSWER／ASK_ID／FACET_EMPTY／FORM／FALLBACK），且判定規則 SHALL 版本化以供跨輪比較。

**after**
> 3. THE 評測流程 SHALL 以決策層落於 `usage_events.decision_snapshot.routing_verdict`
>    為路由類別的唯一來源；SHALL NOT 以回應文字反推類別作為正式量測。
> 3.1 THE 評測流程 SHALL 對每輪同時記錄 `grounded`（答案是否有知識來源支撐）與
>    `answer_verdict`（答案真偽，值域 correct／incorrect／unsupported／unjudged）；
>    路由穩定性與等價比較 SHALL 以 **`(routing_verdict, grounded, answer_verdict)` 複合鍵**
>    為單位。WHERE 兩輪 verdict 相同但 grounded 不同，SHALL 計為不一致
>    （該情形代表知識命中退化為無據生成，後果重於類別翻動）。
> 3.2 THE 評測流程 SHALL 對「決策層 verdict 值域」與「評測所用值域」設自動一致性檢查，
>    枚舉不一致即失敗。
> 3.3 **換尺驗收（鐵則）**：WHEN 更換或修訂量尺，THE 新尺 SHALL 先於已知病灶案例上重判，
>    且 SHALL 判出既有的不一致——具體為歸因報告的翻動案 #07 T4／#10 T3／#21 T3 的初翻點
>    必須被計為不一致。**新尺看不見已知病灶者，判定為不合格，退回重設計。**
> 3.4 WHERE 舊檔無決策快照需重判，MAY 用文字判定，但 SHALL 標 `legacy_text_classifier`
>    並 SHALL NOT 與 verdict 尺混計。

**理由**：見修訂 1；3.3 是 D-24 的教訓——我在修訂過程中曾用一把對主病灶同樣全盲的新尺
取代舊尺，若無此條，換尺只是換一把瞎尺。

---

## 修訂 3｜R5.4「0 胡編」的量測機制（D-06）

**before**
> 4. 驗收基準：30 題變形評測集（登錄簿 20260803 節）命中 SHALL 較基準（80%）持平或提升，……0 胡編 0 錯誤資訊下限 SHALL 維持。

**after**
> 4. 驗收基準：30 題變形評測集命中 SHALL 較基準持平或提升（基準須標明組態，見 R2.4）；
>    ……**「0 胡編 0 錯誤資訊」SHALL 以期望答案表量測**：
> 4.1 THE 評測流程 SHALL 維護**期望答案表**（凍結語料中客服提供標準答案者＋30 題集），
>    逐輪列輪 ID 與期望答案；該表 SHALL 納入 R2.5 的量測前凍結範圍。
> 4.2 `answer_verdict` 的判定母體＝**期望答案表涵蓋的輪**。母體內任一輪為 `unjudged`
>    即 FAIL（禁止以「沒判＝沒問題」通過）；**母體外的輪不計 FAIL，但 SHALL 於報告揭露
>    其筆數與佔比**（不得讓分母悄悄縮小）。

**理由**：原條文以「0 胡編」為驗收但全 spec 無任何量測機制；`grounded` 只證明有來源、
不證明答對。母體限定是為了避免「107 輪多數無標準答案 → 照字面恆 FAIL」。

---

## 修訂 4｜R1.7 快取雙軌改容差式（D-11）

**before**
> 7. ……快取開啟下的路由行為 SHALL 與快取關閉下同語料的路由類別一致。

**after**
> 7. ……**快取開啟與關閉兩軌的路由不一致率 SHALL NOT 高於同軌重跑的不一致率**
>    （兩者以同一把尺、同一母體量測）。
> 7.1 **主判準（決定性斷言）**：WHEN 快取啟用，面向進場輪的二次相同請求 SHALL 仍建立
>    面向會話——此條為 R1.7 的主要驗收，不受統計噪音影響。

**理由**：原「一致」為絕對相等要求，套在自陳 13% 非決定性的系統上：要嘛恆 FAIL、
要嘛被寬鬆判讀恆 PASS，而快取真正造成的缺陷（面向會話未建立）反藏在噪音裡。

---

## 修訂 5｜新增 R2.4（流程鐵則）：引用實驗數據須帶量測條件（D-14、D-17）

**after（新增）**
> 4. WHEN requirements／design／tasks 引用 research 的量化結果，SHALL 同時載明
>    量測條件（樣本、代理方式、適用範圍）與該值屬**點估計／上界／下界**。
>    上界值 SHALL NOT 直接作為生產常數或不可逆約束；
>    **否定性結果（證偽）SHALL NOT 計為該機制「已通過藥效門」**。
> 4.1 引用任何量化基準時 SHALL 標明所用的尺；**不同尺之間 SHALL NOT 直接比較**。
>    現有需引用者：E-5 現況值（人工判讀尺 14/107）SHALL 改為「以核定尺重測後填入」。

**理由**：K_MAX=5 標「EXP-4 定」而該實驗未量過 k=5 且自陳量的是上界；
門檻解耦以 EXP-1/1b 的證偽當作已過藥效門；30 題 80% 基準的量測組態與驗收組態不同。

---

## 修訂 6｜新增 R2.5（流程鐵則）：量測前凍結四件事（D-16）

**after（新增）**
> 5. WHEN 任一驗收量測開跑前，THE 流程 SHALL 凍結並記錄：①判準與及格線
>    ②統計母體與分母定義 ③雜訊標記（noise_manifest）④尺的版本。
>    四者的雜湊 SHALL 入 `make audit`；量測後任一項變更 SHALL **重跑前後兩側**，
>    不得只重算一側。
> 5.1 R7.2／R8.2 的上限值 SHALL 由業主在「**已看到歸因報告、尚未看到修正後結果**」的
>    時點核定，核定即凍結；該核定 SHALL 為關卡條件（未核定不得進下一階段）。

**理由**：「低於預先聲明的上限」而該數值全 spec 從未出現，實務上由實作方量測後提出
（已實際發生：提 ≤3/104 後因換尺自行作廢），直接違反 R2.3。
基線與 noise_manifest 由被驗證方產生且可重算——**基線量得越吵，及格門越寬**。

---

## 修訂 7｜design C1 契約補足（D-07、D-08）

**after（`RoutingSignals` 新增欄位）**
```python
class RoutingSignals(TypedDict):
    # ── 既有 ──
    kb_top1_final: float | None; sop_top1_final: float | None; kb_top1_vector: float | None
    gray_zone: bool                    # ⚠ 觀測欄位；是否仍為判定輸入待 D-01 裁決
    identifier: IdentifierSignal
    session: SessionFeatures
    top1_categories: list[str]
    # ── 新增（D-08：C3 的再進場抑制判準需要，原契約算不出宣告的行為）──
    user_text: str                     # 當輪原句
    topic_terms: list[str]             # 主題詞（決定性抽取）
    escape: EscapeState                # 逃生門狀態（含 exited_facets）

class SessionFeatures(TypedDict):      # 原全 spec 無定義（D-08）
    turn_index: int
    current_facet: str | None
    zero_row_count: int
    escape_events: list[str]           # 欄位名統一（原註解誤寫 escape_count）
```
- `question_type` 為正式欄位名，`tasks.md` 的 `query_type` 同步改。
- **快照必要欄位**：`routing_verdict`、`grounded`、`rule_version`、`config_hash`、
  `decision_case`、`path`、`query_hash`＋`topic_terms`（依隱私鐵則「不存問題原文」，
  存雜湊與主題詞而非原句，同時滿足 C7 查詢聚類 R10.1）。
  缺任一即視為不完整快照（最小快照除外，須帶 `path` 與 `incomplete: true`）。

---

## 修訂 8｜design C1／C3 共用單一枚舉（D-07）

`EscapeVerdict.action` 併入 `routing_verdict` 單一枚舉（值域見修訂 1）：
`stay` → `stay_facet_ask`／`stay_facet_answer`；`exit_requery` → `exit_facet`；
`degrade_knowledge`／`degrade_honest` 直接為 verdict 值。
**C1 與 C3 不得各自定義**；一致性由 R1.3-3.2 的自動檢查釘死。

---

## 修訂 9｜design C6 EvalHarness 重寫（D-04）

```python
class TurnResult(TypedDict):
    case_id: str; turn: int
    routing_verdict: str               # 值域同修訂 1；來源＝決策快照
    grounded: bool | None
    answer_verdict: Literal["correct","incorrect","unsupported","unjudged"]
    source: Literal["snapshot","legacy_text"]   # 混計即為缺陷
    classifier_version: str | None     # 僅 legacy_text 有值
    noise_tags: list[str]

def collect_verdicts(run_tag: str) -> dict[tuple[str,int], TurnResult]: ...
    # 重播後自 usage_events 依 session_id＋輪序取回快照對齊；**不改請求 payload**
    # （維持與凍結語料逐欄可比）
```
- FORM 自此由 verdict `form` 直接可見，不再依賴 `form_triggered` 欄位
  （該欄實測全語料 1291 輪成立 0 次）。

---

## 影響與後續

| 項 | 內容 |
|---|---|
| 套用動作 | 貼進 requirements.md／design.md 正文；`spec.json` 的 requirements/design 核准打回重走 |
| 連帶作廢 | 以舊尺產生的所有數字（V0 的 1/107、基線 5/107、E-5 上限提案）——已於各檔加橫幅 |
| 不含 | **D-01（R7.1 形態）**——等 EXP-7 pilot 結果，帶證據再裁 |
| 下一步 | 核准後執行任務 0.6（量尺實作）＋0.7（期望答案表），再 0.8 重測基線並核定上限 |
