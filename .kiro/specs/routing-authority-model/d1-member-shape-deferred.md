# D1：next-member DEFERRED（業主裁定 2026-08-24）

> 語言 zh-TW｜依據：`round1-failure-analysis-result.md`（F1 歸因 16/17）
> ⚠️ **DEFERRED ≠ 放棄**。本檔的作用是**鎖住 re-entry condition**，
> 使未來重開 D1 時不能只是「換 prompt 再重跑」。

## 狀態（2026-08-24 更新：由 DEFERRED 改記為 **PARTIALLY SATISFIED**）

```text
D1 family          INSUFFICIENT_EVIDENCE     （M1：不得由 member 失敗外推 family）
D1-member-1        REJECTED for R1           （paired discrimination 12/29；單向過度拒絕 17）

D1 re-entry status **PARTIALLY SATISFIED**
  ✅ 已找到新的 admissible demand-side information source：
     N1／N2 runtime instance-binding facts（`evidence-source-inventory.md`）
     —— 不再是 text specification ＋ generic evaluator；runtime-binding；與 similarity/category 正交
  ❌ 仍缺：facet-specific responsibility authority（**R-e**）
```

⚠️ **不得**因 re-entry condition 的一半已滿足就開 D1-member-2：
`candidate Face = Hint 給的 X ＋ N1／N2 = 這是某一筆真實帳單 → allow X`
只是把「這是 instance」偷換成「所以 Hint 提的 Face X 是對的」——**重演 v1 的核心錯誤**。
N1／N2 是**必要**輸入，**尚非充分**輸入。R-e 見 `re-mapping-discovery-frozen.md`。

## D3 對照狀態（同日更新，兩者走到**同一個缺口**前）

```text
D3 family          INSUFFICIENT_EVIDENCE
D3-member-1        REJECTED for R1
B／C representation RETIRED（G1 FAIL）

D3 re-entry status **PARTIALLY SATISFIED**
  ✅ 已找到 runtime executable prerequisite facts（N1／N2／N3）
  ❌ 仍缺：從那些 facts 到 Face responsibility 的 **authoritative binding**（同為 R-e）
```

⚠️ 這是本輪 inventory 的意外收斂：**D1 與 D3 缺的是同一條箭頭。**

## 為什麼是 DEFERRED 而不是「改 representation 就好」

D3 的失敗（F2 枚舉缺口）是**局部且可驗證的 representation 缺陷**——換表示法即是明確的下一步。
D1 的失敗（F1）不是：16/17 筆 false reject 的 query **明含指示詞**（這張／這筆／8月那張／
9/15 那張／剛剛那筆），而 evaluator 的 `reason` 明白宣稱該指示詞不存在，同時在配對的
true accept 上又正確辨識了幾乎相同的結構。

```text
D1 spec 本身沒有枚舉缺口——它的判準（是否指涉既存實體實例）已經涵蓋了那 16 筆。
失效的是**執行**：evaluator 對自己輸入裡已有的證據做出與輸入矛盾的陳述。
→ 因此「把 spec 寫得更好」不對症；「文本 ＋ generic evaluator」這個 shape 本身退場。
```

## Re-entry condition（重開 D1 前必須先回答）

> **若不再使用「text specification ＋ generic evaluator」，
> D1 的 routing-owned demand evidence 到底用什麼 shape 承載？**

具體要求：

```text
MUST 提出一個 routing-owned applicability representation，
     且該 representation 不依賴已退場的「文本規格 ＋ 通用 evaluator」形態。

MUST 說明新 shape 如何避免 F1：
     即「輸入裡已存在的指涉證據被判定為不存在」這個失效模式，
     在新 shape 下為何不可能發生（或如何被機械檢出）。

MUST NOT 以「換 prompt／換 model／調 temperature 後重跑同一 shape」作為 re-entry 理由
     ——那不是新 member shape，且會落回同一個混淆變數。
```

## 現在不做的理由（因果可歸因性）

同時開 D1 與 D3 兩條 member 設計分支，會讓後續任何改善無法歸因到單一變更。
D3 已有被 failure analysis 支持的、局部的、可驗證的修正方向；D1 沒有。
故本輪只推進 D3（見 `d3-representation-proposal.md`），D1 保持 DEFERRED。

## 不得因本檔而發生的推論

```text
❌ 「D1 shape 退場」→「candidate-specific adjudication 這條路不可行」（M1 不允許）
❌ 「D3 先做」→「D3 family 比 D1 family 有前景」（provenance 防線①：本輪不得作 D1 vs D3 比較）
❌ 把 F1 的診斷當成 D1 family 的反證——F1 反證的是 evaluator／calibration，不是 family
```
