# A01 authorization 執行結果（2026-08-29）——**INCONCLUSIVE / SOURCE_INSUFFICIENT**

## 判定

```text
coverage precondition = **INCONCLUSIVE**
  C1 judgeable 且 top1 ∈ Level-A 10 rows =  **7**（門檻 >= 30）❌
  C2 truth = instance                    =  **0**（門檻 >= 10）❌
  C3 truth = general                     =  **7**（門檻 >= 10）❌

⇒ 依凍結協議：⛔ 不計 authorization PASS／FAIL
              ⛔ 不追加 corpus、不改 sampling、不放寬 top1→topK、不回頭補題
⚠️ **一致率未計算**——門檻須由業主在看到結果之前補登，而 coverage 未過即不進該步。
   本檔**不含**任何系統判定與 truth 的比對數字。
```

## 執行完整性（先驗，全數通過）

```text
456/456｜序號 1..456 齊全｜⛔ 無重複｜⛔ 無執行例外
單一乾淨執行（先前兩個競爭進程已終止並清除舊產物）
implementation SHA f89861250d9cd01f4585fc9624a629b75bbcc7d5
corpus digest 628e3ca51679ba43｜labels digest 41743b7219f0f224
```

## 為什麼失敗——是**結構性**的，不是抽樣運氣

```text
Level-A top1 命中率       8/456 = **1.8%**
judgeable instance 占比  38/456 = 8.3%
兩者若獨立，期望 instance ∩ Level-A ≈ **0.7 句** ⇒ 實得 0 **屬預期，非異常**

Level-A scope 是 873 筆情境知識中的 10 筆（1.1%）
⇒ 用一般性自然語料去驗一個 1.1% 的 scope，命中率必然極低
```

### 同型來源要達標所需的語料量

```text
C1 = 30  → 約 **1,710 句**
C2 = 10  → 約 **6,840 句**
```

⚠️ 而整個 sealed pool 只有 576 句（已全數消耗）。
⇒ **這個 authorization 設計（一般性自然語料 × 極窄 scope）在此規模下不可能成立。**

## Corpus 狀態

```text
authorization-2026Q3-A01（n=456）→ **BURNED**
⛔ 不得再作任何 holdout；僅可用於失敗分析
sealed pool 576 句至此全數消耗（D2 80 ＋ D3 40 ＋ A01 456）
```

## 這一輪**確實買到**的東西（⛔ 不是白跑）

```text
✅ label-quality precondition 首次通過：L1=95.4%、κ=0.902（判準凍結於標註之前）
   ⇒ query 層 applicability 的盲標**是可靠的**——與 P1e-1 從 KB 答案盲標的失敗形成對照
✅ 證明了失敗屬 **SOURCE_INSUFFICIENT**，而非 gate 判錯：
   coverage 在**看任何一致率之前**就判定，⛔ 沒有任何 adaptive criterion 的空間
✅ 取得可據以決策的量化基準（1.8% 命中率、1710／6840 句需求）
```

## 待業主裁定的三條路（⛔ 我不預選）

```text
【A】擴大 Level-A scope
    命中率隨 scope 成正比上升；但擴 scope 本身需要它自己的授權決定
【B】改用 targeted corpus
    ⚠️ 依主題挑題＝人為選題 ⇒ 立即污染，⛔ 與本輪紀律衝突
【C】isolated synthetic authoring（業主已預先核准為 fallback）
    作者不知 Level-A 內容／gate／labels／keywords，只收產品任務分布要求
    ⚠️ claim ceiling 必須降為 **synthetic semantic authorization**，
       ⛔ 不得冒充 production distribution
```

## 未變動

```text
⏸ gate 仍 OFF｜⏸ 3.4 仍 PAUSED｜LEVEL_A_INSTANCE_GATE_SCOPE 未變
Level-A population 與 implementation 皆維持凍結，⛔ 未因本結果調整
```
