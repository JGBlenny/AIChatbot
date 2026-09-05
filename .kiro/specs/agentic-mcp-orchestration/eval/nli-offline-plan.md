# 5.8 NLI 接地檢查——離線量測計畫（v1，2026-09-05；業主「好同意」，DSP-031）

> ⛔ 不接線上、不動 Verifier；與 DSP-029 並行。判準在看到任何分數之前凍結於本檔。

## 1. 輸入
- **前提（premise）**：DSP-029 解析出的來源句（`resolved` 片段；029 落地前可用 R4 `--dump-texts` 的回答句對大綱以字元交集取最相近單句作暫代，標 `proxy=true`）。
- **假設（hypothesis）**：回答句片段（Verifier `split_sentences` 切法）。
- **標籤**：獨立代理逐句對大綱原文判「有據／無據」（029 驗收④的 20 筆抽審共用）＋R4 三個已知捏造句（無據）＋大綱原句改寫的有據句（正對照）。目標 ≥ 60 對，無據 ≥ 15。
- 兩種輸入形式各跑一次：繁中原文、OpenCC 轉簡（t2s）。

## 2. 模型
- 主：`MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`（讀 `id2label`；`max_length` 依 config）。
- 副：`IDEA-CCNL/Erlangshen-Roberta-110M-NLI`。
- 對照下限：DSP-030 純規則變體（novel_chars k∈{2,3,4}、bigram 覆蓋率）在同一組對上的表現。

## 3. 量尺（凍結）
| 尺 | 定義 | 門檻（達標才立接線提案） |
|---|---|---|
| 捏造抓到率 | 無據對中判「非蘊涵」（entailment 機率 < τ）的比例 | > DSP-030 最佳純規則變體 |
| 有據誤殺率 | 有據對中判非蘊涵的比例 | ≤ 該純規則變體 |
| τ 選法 | 在 holdout 上以誤殺率 ≤ 10% 為約束取最大抓到率；τ 凍結後不得依線上結果調 | — |
| 延遲 | 目標機器（本機 docker CPU）每句對 p95 | ≤ 100 ms |
| 尺自證 | 三個已知捏造句必須全被抓到，否則此尺不採用 | 3/3 |

## 4. 環境
scratch 容器（`python:3.11-slim` ＋ `transformers`、`torch` CPU、`opencc-python-reimplemented`），⛔ 不進 `rag-orchestrator/requirements.txt`；模型檔快取在 scratchpad。

## 5. 產出
`eval/nli-offline-<date>.md`：對數、兩模型×兩輸入的四尺、τ、混淆矔陣、失敗例（只記索引與類型，⛔ 不記原文）；結論三選一：接線提案（DSP）／留作抽審輔助／不採用。

## 6. 不做
不改 Verifier；不在線上路徑載入模型；不用 LLM 當判官補標籤（標籤來自獨立代理對原文的人工級判讀）。
