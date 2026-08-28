# 下一輪 holdout 來源可行性盤查：assistant-reports

- 日期：2026-08-29｜性質：**唯讀盤查**。不改 classifier、不改 gate、不動 3.4、不抽語料
- 要回答的唯一問題：**真實對話來源能否提供足量、未污染的 instance-side 語料，讓下一輪有資格測 B 層？**

## 結論

> **不能。37 份逐字稿（107 輪 user turns）已於 2026-08-10 批次「全量重播」，
> 全部燒毀，無一可作為未見 authorization 語料。**

⚠️ 這是**直接證據**（登錄簿逐項記載用途），不是「查不到反例」。

## 一、規模與分布（由 S3 key 取得，未讀內容）

```text
Total Objects  37｜Total Size 58,397 bytes
月份分布       2026-07 × 36（1 筆 key 不符命名樣式）
時間範圍       20260709 → 20260729（三週）
role 數        7，且高度偏斜：role 93920 佔 18/36（50%）
⚠️ S3 自 2026-07-29 16:55 起**無新回報**——等自然累積不是近期可行路徑
```

## 二、污染：三種用途全部命中

```text
docs/backtest/assistant-report-regression.md 的「處理批次」表：
  20260724  30 筆 → 已彙整《完整對話逐字稿》＋《知識缺口清單 xlsx》
                    ⇒ 這 30 筆用於**知識工程**，KB 已對它們調整過
  20260731   7 筆 → 逐筆登錄為回測案例 R-31 起（含問句、正確期望、修法）
                    ⇒ 已成為**回歸測試案例**
  20260803  30 筆 → 重跑稽核 20260724 批
  20260810  **37 筆 → 真實多輪對話全量重播（107 輪）**
                    ⇒ **全部**逐字稿都已對系統重播過
```

⇒ 三個排除條件（進過 KB／進過測試案例／進過 classifier 設計）**至少命中一項**，
且第四批直接覆蓋全部 37 份。

## 三、即使未污染，量也在邊緣

```text
107 輪 user turns（全部 role 合計）
其中 instance-side 的比例**未知**（需盲標才知道）
下一輪 B 層門檻：gate opportunity ≥ 10，judgeable ≥ 30
⇒ 就算全數可用，也只是勉強達標；扣掉 undecidable 與非 opportunity 後很可能不足
```

## 四、這輪 D2 的兩件 evidence（**不得互相洗掉**）

```text
B 層  instance-side = 0｜gate opportunity = 1 → INCONCLUSIVE
      ⇒ 明確是**來源 coverage 不足**，不得據此判 gate 好或壞
A 層  rule-side 72：block 39／abstain 30／allow 3
      ⇒ classifier coverage 與 false-allow 訊號**仍然存在**，
        不因 B 層沒樣本而一起消失
⚠️ 那 3 筆 false allow 已燒毀：可進 failure analysis，
   ⛔ 但不得用它們設計新 pattern 後再以同批宣稱改善。
```

## 五、可能的來源方向（**僅列出，未評估、未選定**）

```text
① 等新回報          S3 已一個月無新增，近期不可行
② 產線前瞻性採集    ⚠️ usage-metering 明訂**不存原文**（R7），
                    現行 telemetry 沒有 user message text；要走這條得先做隱私與 schema 決定
③ 其他真實來源      jgb2 平台端是否另存 help-assistant 對話紀錄——**本次未查**
④ 隔離作者合成      D1 前例；但那正是本次改用真實語料想避開的弱點
```

⚠️ **下一輪的 source-design protocol 必須在看到候選語料之前凍結**，
且 strata 定義只能用**來源 metadata／conversation context**，
⛔ 不得用問句文字或 classifier feature 挑選——那會把 holdout 變成針對 classifier 的試卷。
