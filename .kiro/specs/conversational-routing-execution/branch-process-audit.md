# 分支開發流程盤查（fix/retrieval-routing-stability）

> 2026-08-26｜語言 zh-TW｜業主指示：「先盤查這一支分支的開發流程，再完整評估。」
> 全部資料來自 git 與 spec 檔本身，非回憶。

## 一、分支事實

```text
領先 main   200 commits（2026-08-22 ~ 08-26），**未 push**
commit 型別  design 36／test 35／discovery 32／docs 31／spec 30／feat 21／fix 11／其他 4
             ⇒ **文件與探索佔 129／200（65%）**，feat+fix 僅 32（16%）
spec 檔案異動 conversational-routing-execution 84／routing-authority-model 71／
             routing-disambiguation 65／face-exit-before-grounding 45
```

## 二、五天四次轉向（時間軸）

```text
08-22（6 commits）  **檢索層**：query rewrite 決定性、b2b 停用改寫、直答把關改 precision-first、
                    SCORE_SHIFT_PROBE 線上地雷。⇒ 分支開張時處理的是**檢索召回**。
08-23（45）         轉**路由**：pre-entry routability gate 落地，並**開立
                    conversational-routing-execution 需求規格**（09bc1972），
                    當天即擴寫 R6、新增 R10 對話品質。同時 routing-disambiguation 平行開跑。
08-24（91，最高峰）  routing-disambiguation **REFUTED — CLOSED**，
                    後續轉入 routing-authority-model（71 檔異動）→ 最終
                    **BLOCKED_BY_EXTERNAL_DECISION**（等產品方四項治理裁定）。
08-25（55）         face-exit-before-grounding 進 implementation mode（45 檔）＋
                    conversational-routing-execution 的 C4a/C4b 收束。
08-26（3，本日）    **mock 保真度 22 端點全掃**——見下方判定 ②。
```

## 三、任務帳本實況（tasks.md：48 已完成／18 未完成）

### 已完成（實作與證據都在）

```text
1.x   測試基礎設施（層級旗標、空跑守門、runner 契約）
2.x   測試庫隔離（fail-closed 雙驗、DB_ENV）
3.0-3.3 routing regression 與 evidence packet
4.x   transport seam（Protocol／樣板解析／admission gate／bills fixture／移除短路）
5.x   C4a 決定性閉環（10 passed，fresh verifier CONFIRMED）
6.x   C4b 真 brain 量測＋**上線 gate 放行報告（業主已簽署）**
7.x   skip_refine 語義定案（行為正確、不改碼）
10.1-10.3 母圖與 steering 回寫
```

### 未完成，且**沒有被任何 gate 擋住**（可以做卻沒做）

```text
8.1-8.5  ＝ Req.5.2 **validator 早於 scope 正規化，brain 正確的 scope=switch 被整包丟棄**
         已用程式查證仍在：llm_answer_optimizer.py:980 的 action 檢查在 :991 之前。
         這條啟用的是 **mid-session switch**——**對話流本身**。
         8.1-8.4 純程式改動，不需授權；只有 8.5 的「獨立上線」需要。
         ⚠️ **git 全分支查無任何 8.x 的 commit** ——從未被動過。
9.1-9.4  ＝ Req.5.3 **repair_create 零觸發點**（make audit 不變量 4 長期 WARN）
         9.1-9.3 可實作可回歸；只有 9.4 上線被 6.3 gate 擋。
         ⚠️ 同樣**從未被動過**。
12.1-12.2 ＝ Req.4.4 real API contract smoke（漂移偵測）——未開始。
```

### 被擋住（不是沒做，是做不了）

```text
3.4        REFUTED（instance-oriented anchor 修法不足）→ 轉 routing-authority-model
           → **BLOCKED_BY_EXTERNAL_DECISION**（等產品方裁定，工程端不得代填）
11.2-11.6  ＝ Req.10 面向內對話品質基準 → **BLOCKED_BY_OBSERVABILITY**
           turn_number／decision_snapshot.user_turns 全表 0 列；無逐字稿；
           scope=switch 退出不發 facet_event ⇒ judgeable N = 0
10.4       業主裁定 intentionally deferred，不做
```

## 四、三個判定

### ① 對話流優化的**可執行**部分，是任務 8 與 9——而它們一次都沒被碰過

Req.10（品質量測）確實被觀測性擋死，但 Req.5.2／5.3 對應的任務 8、9 **沒有任何 gate**，
而且 8.x 直接改變對話行為（中途換面向）。分支 200 個 commit 裡沒有一個碰它們。
**這是本次盤查最重要的發現**：不是「對話流優化做不了」，是它被排在後面然後沒被排回來。

### ② 今天的 22 端點 mock 全掃，**不在任務清單上**

tasks.md 的 4.4-4.6 只涵蓋 `bills`／`bill_detail`，12.x 是 real API smoke。
「其餘 19 個端點逐一對照原始碼」**不是任何一條任務**——它源自業主的覆蓋率提問，
由我擴成整個 session 的工作。價值真實（挖出三個線上靜默失效），
但它**在帳本外**，所以做完不會讓任何一個任務打勾，也就無法回答「離結案多遠」。

### ③ 缺一份被核准的順序，是失焦的結構成因

`spec.json`：requirements ✅ approved、design ✅ approved、**tasks ❌ approved: false**。
需求與設計都經過業主核准，唯獨**任務順序從未核准**。
再加上我昨天另外發明了一套 T1-T8 編號（與 tasks.md 平行、詞彙不同），
等於同時存在兩份任務清單、兩套編號、零份被核准。

## 五、重新對焦的建議

```text
1. **廢掉 T1-T8 編號**，一律回到 tasks.md 的既有編號（8.x／9.x／11.x／12.x）。
   我昨天寫的 api-fidelity-architecture-and-tasks.md 降級為「保真度背景債務清單」，
   不再充當任務來源。
2. **下一步＝任務 8（Req.5.2）**：8.1-8.4 實作＋零回歸鎖，8.5 獨立驗收後**單獨**上線。
   理由：唯一「不需授權、改了就會改變對話行為」的項目。
3. 任務 9 次之（9.1-9.3 可做，9.4 等 gate）。
4. 22 端點保真度的剩餘部分（tenant_registration／create_repair／fixture 連通／
   transport 遷移）全部降為債務，只在擋住 8／9／12 時才動。
5. **請業主核准一次任務順序**（tasks.approved），否則同樣的漂移會再發生。
```
