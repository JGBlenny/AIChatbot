# V0 反證盤查｜原始發現留檔（D 編號的證據源）

> 2026-08-19｜三隻反證代理（立場設為推翻，非確認）＋兩隻計畫審查＋一隻全 spec 掃描。
> **本檔為 `decisions/DECISIONS.md` 各 D 項的證據源**，台帳只留濃縮結論。
> 業主質疑任一 D 項的證據強度時，回溯到這裡。

## 盤查編制

| 代理 | 任務 | 結果 |
|---|---|---|
| A | 攻擊等價證據的名實相符 | **攻不破**（3 攻擊點全 CONFIRMED）＋3 則 advisory |
| B | 攻擊量尺與雜訊標記是否為好看而裁剪 | **打穿**（分類器 REFUTED；雜訊標記 CONFIRMED 無超收） |
| C | 攻擊埋點與不變量的實際效力 | **打穿**（3 主張中 2 個 REFUTED、1 個部分） |
| D | 審查修訂稿 01 | REVISE，4 阻斷 |
| E | 全 spec 同型缺陷盤查 | 16 項（1 P1、9 P2），判定系統性 |
| F | 審查修訂稿 02（fresh） | REVISE，8 阻斷（2 P1） |

## 代理 A｜等價證據（攻不破）

- **參考實作忠實性**：代理不採信我方測試，自 `git show bfc504d~1` 取搬移前原文另寫一份參考
  實作，於容器內對 **380,192 格**（分數 0–1 步進 0.01＋門檻/gap 邊界 ±1e-6、has_sop×2、
  四旗標 16 組）與 `decide_arbitration` 對拍：`checked 380192 mismatch 0`。
  逐分支核對分支順序、`>=` vs `>`、gap 計算式、reason 字串全一致。
  **方法可重跑**：取 `bfc504d~1` 的 chat.py Step 3 逐字複製為參考函式，
  對上述網格與 `services/decision_layer.decide_arbitration` 逐格比對四元組
  `(type, reason, decision_case, gap)`。
- **多數決是否掩蓋漂移**：跨組（before×after）9 配對平均不一致 **5.56 輪**，
  組內 6 配對平均 **6.00 輪**——**跨組低於組內**。permutation 檢定（10 種切法）
  真實切法落在分佈最小值，p=1.00。類別分佈的 ASK_ID +5 經逐 run 拆解證明是 a2 單輪離群。
- **發現的真實差異（P4）**：搬移後 `(sop_result.get('trigger_result') or {})` vs
  原 `.get('trigger_result', {})`——該鍵存在但值為 `None` 時，原碼 500、新碼續走。
  嚴格不更壞，但技術上非零差異。**處置：保留新版（不重新引入崩潰），於此留檔。**
- **檢定力 advisory（P3）**：組內配對噪音 2–9 輪，三輪/側的設計對「小於約 5 輪/107 的
  真實漂移」無分辨力——「不一致 1/107」實為「≤ 噪音」。要提高分辨力需每側 ≥5 輪。

## 代理 B｜量尺（打穿 → D-04、D-05）

- **`ask_id_max_len:120` 是過擬合徵兆且為冗餘參數**：全語料 1291 輪中，含「請提供」＋識別詞者
  長度分佈為 17–77（272 輪，全 sources=0）與 122（9 輪，全 sources=1，皆 #36 同一段 KB 答案），
  **78–121 完全無資料**。門檻取 120＝貼著唯一反例往上頂、餘裕 2 字。
  改成 80 或無限大、或關掉 `requires_no_sources`，**1291 輪皆 0 筆變動**。
- **自造 9 個語料外變體，誤判 8 個**（V1 較長索取句→ANSWER、V3/V4 查無另一措辭→ANSWER、
  V6「麻煩告訴我帳單編號」→ANSWER、V7 run1 真實表單 UI→ASK_ID、V9 索取帶來源→ANSWER）。
- **⭐ 最重的發現（P2）**：`ANSWER` 併吞「知識接地直答」與「無據 LLM 自由發揮」。
  對 6 個以上 run 跑過的 107 輪逐輪比對：rc-v1 判「類別有翻動」16 輪；
  **類別完全穩定但知識接地翻動另有 9 輪**（#08T9、#09T9、#09T10、#09T12、#10T9、
  #11T9、#11T10、#11T12、#33T1）→ **漏計 16→25 中的 36%**。
  實例：run2 的 #09/#10 T10「我可以擁有多少個物件？」帶 sources 直答「一物件多合約
  **上限 10 份**」，run3 同輪無 sources、LLM 自由發揮成「**並沒有上限**」——與知識庫直接
  矛盾的幻覺，rc-v1 兩邊都記 `ANSWER`。偏差方向對主張者有利。
- **FORM 是死類別**：全 17 個 run、1291 輪 `form_triggered=True` **0 次**（含 13 個有記錄
  該欄位的新 run）；run1 有 5 輪明顯表單 UI（含 📝／「取消」）全被判 ASK_ID。
  且 `ask()` 只記 `form_triggered` 不記 `current_field`，而 repo 自己的 e2e
  判定表單用的是 `form_triggered or current_field`。
- **雜訊標記查無超收（CONFIRMED）**：逐條核對登錄簿原文並以 `parse_report` 還原 37 份逐字稿，
  carryover/probe 標記逐句屬實；#19 依原文本可順手標掉卻**未標**（對自己不利、分母變大）；
  #10 T13 同時是 signal 依 `signal_overrides_noise` 保留（又一反向選擇）；
  母體 50／104 獨立重算一致。**分母沒有被灌水縮小。**

## 代理 C｜埋點與不變量（打穿 → D-19、D-20、D-21、D-22）

- **快照覆蓋 176/321＝54.8%**，按 `facet_event` 拆解：`enter` 91 輪 100% 有快照、
  `(null)` 230 輪僅 85 有 → **扣除進場輪後其餘僅 37%**。缺口 145 輪全部
  `is_internal=t / internal_kind=backtest / status=success`、`processing_path` 與
  `answer_source` 皆 NULL——**即面向內續輪**。
  程式根因：`_meter_decision` 全 repo 僅三個呼叫點（面向進場、b2b 短路、仲裁回傳），
  而面向續輪走 `handle_conversational` → `_conversational_respond` 直接 return，
  **永不經過任何 `_meter_decision`**。`decision_layer.py` 檔頭「從此每輪」與實作不符。
  `backtest_a1_07` 8 輪只有 3 輪有快照、`a1_08` 10 輪只有 5 輪。
  附帶：`escape_kind`／`facet_key`／`turn_number` 三欄 321 筆全 NULL。
- **不變量 8 實測 8 種寫法只擋 1 種**：`os.environ[...]`、`os.environ.get`、
  `from os import getenv`、`os.getenv("KB_" + "SIMILARITY_THRESHOLD")`、變數間接、
  **`os.getenv(  "KB_..."`（多一個空格）** 全部漏網。常數檢查對 `_SOP_MIN = 0.6`、
  型別註記、dict 形式、內聯 `if s > 0.6:` 全無感。掃描範圍未含 tools/scripts/knowledge-admin。
  **公平陳述：全 repo grep 後目前確實無洩漏——任務 1.3 的收斂是真的，
  假的是「不變量 8 鎖死了它」這句話。**
- **快取軌別閘門 CONFIRMED**：實測 `--cache-mode on`（容器 false）→ abort、exit 1、
  輸出目錄未建（`os.makedirs` 在三閘之後）。設計紮實。
- **`--skip-audit` 無下游約束**：`_run_meta.json` 寫了「不具回歸效力」，
  但 `grep -rn "_run_meta"` 排除自身後**零命中**——無任何消費者。
- **語料閘門自簽自證**：只比對 manifest 內由同一支程式算出的樹雜湊；
  `grep -rn "tarball_sha256|tarball_s3" --include=*.py --include=*.sh` **零命中**——
  程式從未讀 tarball 雜湊、從未觸及 S3，而 corpus README 明寫「開跑前必驗 SHA-256」。
  三個 run 目錄受 gitignore，竄改不留版控痕跡。

## 代理 E｜全 spec 掃描（16 項 → F↔D 對照見 DECISIONS 附一）

三條系統性模式（P-1 概念沒落成資料／P-2 證據強度與引用強度不匹配／P-3 及格線與分母
在被驗證方手上）詳見 `decisions/DECISIONS.md` 附三。最重一項為 F1（P1）：
R7.1「校準後信心值」在 design C1 無對應欄位，只剩由絕對分數算出的 `gray_zone: bool`。

## 代理 D／F｜兩份修訂稿審查（12 項阻斷）

修訂稿 01：4 阻斷（核心＝誤以為快照 verdict 即 C1 六值，實為仲裁的 sop/knowledge/none）。
修訂稿 02：8 阻斷含 2 P1：
- **P1-1**：「分數平移時 confidence 排序不變」的驗收**對任何分數單調函數恆成立**
  → 「絕對分數改名」最容易通過。且 A4 重寫 signals 時未移除 `gray_zone`。
  **最小修法（已納入 D-01(a) 驗收②）：拿「confidence = 絕對分數」的假實作跑全套驗收，
  必須 FAIL。**
- **P1-2**：改用 `routing_verdict` 尺後，面向內續輪前後皆 `stay_facet` → **#07 黏著
  在新尺上判為一致**，主病灶量不到。**驗收檢查（已納入 D-04）：歸因報告 5 個翻動案
  在新尺上重判，#07/#10/#21 的初翻點必須被計為不一致。**

## 教訓（已入長期記憶 `feedback_independent_verification` 第 8–10 點）

1. 反證代理要打的是**量尺**，不只是結論——本次結論全守住、量測工具被打穿。
2. **換量尺前先驗「新尺看得見已知病灶」**，否則只是換一把瞎尺。
3. 審查連續兩次 REVISE 就停止加大範圍——兩次都在修訂稿裡重犯自己指控的錯。
