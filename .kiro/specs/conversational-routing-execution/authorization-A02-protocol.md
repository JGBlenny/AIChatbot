# A02 synthetic semantic authorization —— **協議已凍結**（2026-08-29）

⚠️ 本檔於 **corpus 生成之前**凍結。
⛔ 凍結後無論哪一 row 表現差，都不得合併 strata、擴 oracle 或補題。

## 0. Claim ceiling（業主原文，先寫死）

> **A02 tests semantic correctness and routing behavior under an isolated
> synthetic, scope-matched corpus. It does not estimate production frequency,
> recall, or traffic distribution.**

## 1. 已凍結的受測物

```text
implementation SHA          f89861250d9cd01f4585fc9624a629b75bbcc7d5
Level-A population digest   57413ee8a4068f73bc4e0c2c0512967e
face requirement digest     bde00b206c9c8b7d4b1328e7440d754f
gate                        OFF（評估時以真實接縫 `_applicability_suppressed` 走 gate-on 之姿）
```

### frozen Level-A truth table（10 rows）

```text
general   3402 點退帳單 自動產生 費用結算        （reviewed）
          3406 帳單收據 繳費證明 PDF 下載        （reviewed）
          3519 點退帳單金額計算 押金結算          （reviewed）
instance  3495 帳單為什麼發不出去                （deterministic）
          3496 帳單為什麼取消不了                （deterministic）
          3498 為什麼被收逾期費（延遲金）         （deterministic）
          3499 帳單手動到帳或標記已收款失敗       （deterministic）
          4640 帳單收據金額 收據多少錢            （reviewed）
          4656 查帳單 帳單編號查詢                （reviewed）
          4657 合約的點退帳單金額 查點退金額       （reviewed）
```

## 2. Corpus 規格（事前固定，⛔ 不補題）

```text
**10 strata × 20 = 200**（general 60／instance 140）
```

⚠️ 這個不平衡**不是問題**——A02 ⛔ 不估 prevalence／production distribution。
⛔ **不得**為了做成 100/100 而額外製造 general 題：那是**為了統計外觀改 semantic scope**。

| Stratum | 任務 |
|---|---|
| G1 | 點退帳單是否／何時自動產生、費用結算流程 |
| G2 | 收據／繳費證明 PDF 如何取得 |
| G3 | 點退帳單金額計算規則 |
| I1 | 查自己的某張收據實際金額 |
| I2 | 查自己的某筆帳單目前狀態／找到某筆帳單 |
| I3 | 查自己某份合約的點退帳單實際金額 |
| I4 | 自己某筆帳單為什麼發不出去 |
| I5 | 自己某筆帳單為什麼取消不了 |
| I6 | 自己某筆帳單為什麼被收逾期費 |
| I7 | 自己某筆帳單手動到帳為什麼失敗 |

⚠️ **I2 措辭已收緊**：⛔ 不含「為什麼發不出去／取消不了／被收逾期費／手動到帳失敗」
——那四種**各自獨立為 I4–I7**。

## 3. `allowed_top1_ids`（**oracle 定義——必須在生成前凍結**）

**全部維持單一 row oracle**——10 個 semantic task 與 10 個 frozen Level-A rows **一對一**。
⚠️ 這比允許多 row 的 oracle **更強**，且讓失敗歸因非常乾淨。

```text
G1 → {3402}   G2 → {3406}   G3 → {3519}
I1 → {4640}   I2 → {4656}   I3 → {4657}
I4 → {3495}   I5 → {3496}   I6 → {3498}   I7 → {3499}
```

Layer A 單題 PASS 的定義（業主裁定）：

```text
query judgeable AND top1 ∈ allowed_top1_ids[its_stratum]
⛔ **不是** top1 truth class == query truth class（那會假綠：
   「收據 PDF 怎麼下載」命中「點退帳單怎麼算」兩者都 general，但 retrieval 顯然錯了）
```

### 業主裁定（2026-08-29，**corpus 生成前最後一次 scope／oracle 修訂**）

```text
【確認 1】I2 = {4656}，**維持窄定義** ✅
  ⛔ 不採 {4656,3495,3496,3498,3499}——那會把「帳單個別查詢」與「四種不同故障診斷」
     揉成一個 oracle，80% alignment 極易因 oracle 過寬而**假綠**。
  ⚠️ 若作者偏離 I2 任務、寫成故障診斷而 top1 命中 3495–3499
     → **就應算 I2 misalignment**。
     這是在測 authoring／retrieval 是否忠於 preregistered semantic stratum，
     ⛔ 不是測「系統有沒有找到某個差不多的 instance row」。

【確認 2】**現在**新增 I4–I7 ✅
  corpus 未生成、oracle 未凍結 ⇒ 合法 preregistration；⛔ 看到結果再補才是 adaptive。
  不補的話 A02 最多只能授權「6 of 10 Level-A rows」，
  ⛔ 不能升格成整個 bill_diagnosis Level-A scope 的 synthetic semantic authorization。
  而下一關是 gate authorization，⛔ 不是只驗其中六個漂亮案例。
```

## 4. 判準（業主裁定，四項）

```text
Label quality        L1 exact agreement >= 90%；Cohen's kappa >= 0.70
                     κ 因零變異無法定義 → LABELING_INCONCLUSIVE
                     ⚠️ 措辭：沿用**同一套事前 label-process quality criterion**，
                        ⛔ 不主張它對所有來源天然適用

Corpus sufficiency   **每個 stratum**（含新增 I4–I7）judgeable >= 15／20
                     否則 CORPUS_INSUFFICIENT
                     「有效」＝ authoring integrity 通過 AND 兩位標註者一致
                       AND label ∈ {instance, general}
                     ⛔ 不得以 general 合併 45 掩蓋某 stratum 只剩 8

Layer A              **每個 stratum**（10 個）alignment >= 80%
（retrieval support） 任一 stratum < 80% → **RETRIEVAL_INSUFFICIENT**，⛔ 不得怪 gate

Layer B              只在 Layer-A-aligned 案例上判；**accuracy = 100%**
（authority）         任一筆錯 → **AUTHORITY_POLICY_FAIL**
                     ⚠️ ⛔ 不給誤差額度的理由：query truth 已確認、top1 對齊已通過、
                        knowledge 宣告與 Face requirement 皆凍結
                        ⇒ 此處是 **deterministic policy**：
                          instance × REQUIRED → ELIGIBLE／general × REQUIRED → INELIGIBLE
                        **語義噪音歸 Layer A；policy wiring 不給額度。**
```

## 5. Controls（業主修正後）

```text
① row-local declaration mutation（⚠️ **不是** stratum 整組翻轉——原寫法太強且可能錯，
   因為同一 stratum 的 20 句不保證 top1 都是同一 row）
     選一個 frozen Level-A row R → 取出 A02 中 top1 == R 的所有 aligned queries
     翻轉 R.instance_applicability（general ↔ instance）
     期待：這些 query 的 authority result **全數翻轉**；
          其他 top1 != R 的 query **不得**因此翻轉
     ⇒ 直接證明 **row truth 是實際 causal input**
     **最低要求**：一個 general row ＋ 一個 instance row 即足以證明 causal wiring
     ⚠️ A02 本體成功後可機械跑 **10-row mutation census**：對每個 row R，
        只看 top1 == R 的 aligned queries，翻轉 R 宣告 → 該集合全數翻轉、
        top1 != R 全數不受影響 ⇒ deterministic control，
        ⛔ 不增加 synthetic authorization claim，也不需再生成題目

② non-Level-A negative control
     用 A01 **burned** corpus 中 top1 ∉ Level-A 的案例（burned 僅供失敗分析，此用途合法）
     期待：P1f applicability Level-A policy **不得介入**
     ⛔ 這些案例不進 120 題、不進 Layer A 分母、不進 Layer B accuracy、
        ⛔ 不得用來墊高 A02 的 PASS 數字
     它只回答：**non-Level-A scope lock 還活著嗎？**
```

## 6. 作者隔離

```text
✅ 可知：§2 的六個任務（＝驗證標的定義，非洩題）
⛔ 不得看到：10 個 knowledge rows／question_summary／categories／
   §3 的 allowed_top1_ids／embedding 或 ranking／Face 名稱／gate／
   instance-general metadata／lexical extractor／任何測試／「哪些措辭容易命中」
要求：自然產生多種表述（口語、簡略、含錯字、不同角色語氣），⛔ 不得對 KB 文案改寫
```

## 7. 執行順序（⛔ 不可調換）

```text
1. §3 兩項確認 → **協議凍結**（allowed_top1_ids 必須在生成前凍結）
2. isolated synthetic author 生成 120 句
3. corpus 固定 ＋ digest
4. 兩位隔離標註者做 query 層 truth
5. integrity ＋ label quality ＋ corpus sufficiency
6. labels 凍結 ＋ digest
7. 才跑 frozen implementation
8. **先判 Layer A**，再判 Layer B，最後跑 controls
```

## 8. PASS 時只能宣稱（業主原文）

> **P1f passed synthetic semantic authorization for the frozen Level-A
> bill_diagnosis scope across the ten preregistered task strata
> (all 10 frozen Level-A rows exercised, one dedicated stratum each).**

```text
✅ 支持：scope-matched semantic retrieval；
        knowledge truth → Face requirement → authority policy 的接線；
        general suppression／instance retention 的語義方向
⛔ 不得說：production recall 已驗證｜production traffic 命中率｜
        其他 15 個 REQUIRED Faces 已授權｜可以擴 PREENTRY_ROUTABILITY_FACETS
```

## 9. 未變動

```text
⏸ 3.4｜⏸ gate enable｜⏸ 擴 scope｜⏸ release
A01 = CLOSED／BURNED；⛔ 不得用 A02 補救 A01
```
