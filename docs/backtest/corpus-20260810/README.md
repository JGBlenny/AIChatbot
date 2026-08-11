# 20260810 真實對話重播語料（凍結）——本體在 S3

37 份 S3 客服回報逐字稿的使用者發言，原樣、依序、同 session 重播（107 輪/輪次）。
harness 形狀比照 jgb2 `HelpAssistantController@chat` 實送 payload。詳見登錄簿「批次 20260810」節。

## 存放（2026-08-11 業主定案：語料本體走 S3，repo 只留指標與工具）

- **S3**：`s3://jgb2-production-upload/aichatbot/eval-corpus/corpus-20260810/corpus-20260810.tar.gz`
- **SHA-256**：`b9c690cf63a2474f5fbab061e8d996e3fc445610678663de70c5841f3bb93495`
- **取回**（解到本目錄，路徑與所有文件引用一致）：

```bash
cd docs/backtest
aws s3 cp s3://jgb2-production-upload/aichatbot/eval-corpus/corpus-20260810/corpus-20260810.tar.gz /tmp/
shasum -a 256 -c <(echo "b9c690cf63a2474f5fbab061e8d996e3fc445610678663de70c5841f3bb93495  /tmp/corpus-20260810.tar.gz")
tar -xzf /tmp/corpus-20260810.tar.gz   # 展出 corpus-20260810/run1-stale-image|run2-head|run3-head
```

- run 目錄已列 .gitignore——**不進 git、不重新上傳**；S3 物件即凍結正本，取回後只讀。
- 評測工具（任務 1.1 的 decision_replay）開跑前必驗 SHA-256，不符即 abort。

## 內容

| 目錄 | image | 用途 |
|---|---|---|
| `run1-stale-image/` | 舊 image（韌性 spec 撤案還原後未重建） | **已作廢**，僅留作容器污染對照 |
| `run2-head/` | HEAD（cca0146＋P1-a 修正）重建後 | 有效基準（等價搬移的對照組） |
| `run3-head/` | 同 run2 | 重跑變異量測（14/107 輪路由類別不同） |

- 每檔＝一份回報：原逐字稿（`turns`）＋重播結果（`replay`，含 answer/intent/耗時）。
- 原始逐字稿正本在 `s3://jgb2-production-upload/assistant-reports/`，此處不重複存。
- `replay_harness.py`＝重播工具（repo 內版控；跑法：`OUTDIR=out WORKERS=5 python3 replay_harness.py <tag>`，需先把 S3 逐字稿抓到 `reports/`）。
- **此語料為 retrieval-decision-layer spec 的凍結評測集**：語料先於設計凍結（撤案教訓），spec 期間只准引用、不准增刪改。
- 判讀注意：語料含雜訊（測試案/跨案殘留輪次/客服轉述句），分類見登錄簿 20260810 節；`noise_manifest.json`（任務 1.1 產出）落地後以機器可讀版為準。

## 佚失紀錄（誠實註記）

三支實驗原始輸出（exp1/exp1b/exp4 raw json）於反證覆核完成**之後**因 scratchpad session 清理佚失——複算結論已記錄於 spec research.md 反證覆核節（C1 全數對上）；如需 raw 可依 research.md 協定重跑（實驗只依賴本語料＋kb 向量＋reranker，與管線碼無關，可重現）。教訓：實驗產物應在產出當下即歸檔，不停留 scratchpad。
