# P1e-1 盲標協議（**凍結於語料產出之前**，2026-08-29）

⚠️ 依 `holdout-validation` skill 鐵則①：**順序不可逆**——凍結判準 → 造語料 → 標註 → 才用。
本檔在標註語料產出**之前**寫定，⛔ 標註回來後不得修改 label definition。

## 目的（⚠️ 與授權驗證嚴格分家）

```text
本批 839 筆的用途 ＝ **population corpus**（回填 applicability metadata）
一旦用於回填，它們就是 training/configuration corpus
⛔ 之後**不得**從中抽樣宣稱「gate 對 unseen general/instance 的準確率」
未來的 authorization holdout 必須是**完全 unseen 的另一批**，
且在 implementation ＋ population freeze **之後**才建立。
（不重演 D1–D3：那批就是因為來源與用途混用而失效。）
```

## label 定義（**只有這三個**，⛔ 標註後不得修改）

```text
instance    正確完成這個問題，需要讀取「這個使用者自己的」
            帳號／合約／帳單／物件／訂閱／系統狀態等資料
general     不需要任何該使用者自己的系統資料，
            僅靠制度、流程、產品通則即可完整回答
undecidable 僅從該知識內容不足以確定
```

⛔ **不問**「應不應該進對話面向」、⛔ **不問**「應該去哪個 Face」。

## 標註者可見 / 不可見

```text
可見：knowledge id、question_summary、answer（使用者可見的問題與答案脈絡）
      ＋ 上面三個 label 的定義

⛔ 不給：
   Face／category→Face mapping／gate／requires_instance_reference
   現行 routing／form／API／action_type 等 metadata
   P1b 結果／哪些 row 已被 machine 判 instance
   我們希望 UNKNOWN 下降到多少
```

## 隔離與計數

```text
兩位標註者**互相隔離**，各自獨立看同一批語料

⚠️ **協議修訂（2026-08-29，於任何標註開始之前）**
原訂「0 tool calls」。實作時遇到硬限制：語料共 119KB，**無法可靠地內嵌進代理 prompt**
（連我自己讀該檔都被截斷，無法逐字複製）。⇒ 修訂為：

```text
每位標註者**恰好一次** tool call：Read 自己被指派的語料檔
任何其他 tool call → 該標註者的產出作廢
```

⚠️ 為什麼這不削弱隔離——**隔離改由構造保證，而非靠自律**：
語料檔由 `scripts/analysis/p1e_corpus.py`（已進版控）產出，
每列**只有** `id \t question_summary \t answer` 三欄，
⛔ 不含 Face／mapping／gate／routing／form／API／action_type／P1b 結果。
⇒ 標註者即使讀了檔，也讀不到 withheld 清單上的任何一項。
這比「相信代理沒去查」更強。

⚠️ 本修訂發生在**尚無任何標註結果**之時，⛔ 不是看到結果後調整判準；
   label 定義、合議規則、withheld 清單**一字未改**。
```

## 合議規則（⛔ 不做優先序、不做仲裁）

```text
兩者皆 instance      → proposal = instance
兩者皆 general       → proposal = general
其餘任何組合          → 保持 **UNKNOWN**
（含一方 undecidable、兩方 undecidable、兩方相反）
```

## provenance（⚠️ 必須可追）

```text
34 筆 deterministic  source=deterministic，evidence=E1／E2／E3
                     ⛔ **不交給 labeler 再確認**——它們有 repository machine evidence
839 筆盲標           source=blind_label_consensus，evidence=兩位標註者的 label
⇒ 半年後看到 instance_applicability=instance，必須知道它是引擎契約推出來的、
  還是兩位標註者判的。
```

## 本輪**不做**的事

```text
⛔ 不寫 DB（proposal 先落檔，population 是另一刀）
⛔ 不改 routing、不 enable gate
⛔ 不為了壓低 UNKNOWN 而放寬合議規則
```

## 預先登記的 claim ceiling

```text
✅ 可說：兩位隔離標註者對 N 筆達成一致，proposal 覆蓋率 X%
⛔ 不得說：applicability 標註「正確率」——本批**沒有** ground truth，
   合議只代表兩個獨立判斷相同，不代表判對
⛔ 不得說：任何 production 分布
```
