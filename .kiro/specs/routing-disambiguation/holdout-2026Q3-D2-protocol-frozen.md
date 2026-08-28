# holdout-2026Q3-D2：授權協定（**第一次執行前凍結**）

- 建立：2026-08-28｜依據：裁定 004（相同 implementation 得重新接受 authorization）
- 狀態：**FROZEN — 尚未產生語料，尚未執行**
- ⚠️ 本檔一旦 commit，下列七項即凍結；**執行後不得回頭修改任一項**。

## 0. 為什麼可以用「同一個 implementation」重驗

見裁定 004：舊 `FAILED` 的事實保留，被撤銷的只有「必須先修 classifier」這個推論。
舊 11 個 block **沒有一個**具備「可實際作用」的機會（9 個無 Face nomination、
2 個落在 scope 外），因此 `0/50` 只能證明「那批抽樣上沒有可觀測效果」。

⛔ 這**不是**「測不過就換考卷」：candidate 未被修改，且我們是在**沒有動它**的前提下
先證明舊測量為何無從觀測。

## 1. 凍結項（七項）

| # | 項目 | 值／狀態 |
|---|---|---|
| 1 | query corpus | **待產生**（D1 隔離作者，見 §3） |
| 2 | human labels | **待產生**（D2 盲標者，見 §4） |
| 3 | nomination／applicability 判準 | 本檔 §5 |
| 4 | protocol | `ACTIVE_PROTOCOL_DIGEST = 4690a258f502d98d`（與前次同尺，未換尺） |
| 5 | success／failure criteria | 本檔 §6 |
| 6 | ruleset digest | `80b2f570b10c2e20`（`ie-v1`；positive 3 條／counter 1 條） |
| 7 | code revision | `b9df7ca` |

⚠️ 4 與 6 與前次 holdout **相同**——這是刻意的：本次驗的就是「同一把尺、同一個實作，
換一批真正覆蓋標的情境的未見語料」。

## 2. 已燒毀、**不得**進入本次授權的資料

```text
holdout-2026Q3-D1 的 50 筆   → BURNED（2026-08-24）→ 僅供 failure analysis／diagnostic
2026-08-28 的 4 筆 regression cases
  （收據 PDF 在哪裡下載／點退做完後…／系統怎麼算…／點退帳單的金額是怎麼算的）
                              → BURNED → 僅供 regression corpus
⛔ 兩者皆不得出現在 D2 語料中，也不得作為授權依據。
```

## 3. 語料產生（D1 隔離作者）——沿用前次已驗證的隔離紀律

```text
作者：全新 general-purpose agent，無本案上下文
硬性要求：**0 次工具呼叫**（不得讀檔、不得搜 codebase）——隔離是技術事實，不是口頭要求
交付形式：未標註、順序打散的平面清單（作者不得替自己出的題預先分類）
withheld（不得告知）：
  candidate 存在與否｜機制為 lexical ruleset｜任何特徵名稱
  possessive／explanation_request 等概念｜現行 route｜KB wording
  D1 holdout 的任何內容｜今日 4 筆 regression cases
```

### ⚠️ 本次**新增**的取樣要求（產品層敘述，**不洩漏機制**）

前次失敗的真正原因是抽樣未覆蓋 gate 的標的情境。修正方式是用**產品語言**指定組成，
而不是用機制語言挑句子：

```text
語料須同時涵蓋兩型，且兩型都要落在**帳務／點退**主題內：
  ① 問「我自己那一筆」的說法——想知道某張特定帳單／某份特定合約的實際數字或狀態
  ② 問「制度怎麼運作」的說法——想知道平台的規則、流程、功能有沒有，不指涉特定單據
數量：**≥ 60 句**（預留不可判定與非 judgeable 的耗損，確保 judgeable ≥ 30）
⛔ 不得向作者說明這兩型會被如何使用，也不得提供任何範例句
   （提供範例＝把答案洩漏成模板）
```

## 4. 標註（D2 盲標者）

```text
標註者：另一個全新 general-purpose agent，**0 次工具呼叫**，candidate-blind
可給的輸入：凍結問句｜single／dialog 回應模式的產品定義｜
           帳務相關面向的 key ＋自述範疇（逐字引自 seed 規格）｜label schema
withheld：candidate／extractor／ruleset｜現行 production route｜
         similarity／retrieval 任何數值｜本協定的 criteria
label schema（沿用 D1）：intent_class／intended_route／intended_facet／confidence／evidence
```

## 5. nomination／applicability 判準

```text
intent_class = rule      問的是制度／規則／功能有無 → 不需查任何一筆單據
intent_class = instance  必須查某一筆特定單據／合約才能回答
undecidable              兩者皆不成立或資訊不足 → 退出 judgeable 分母（不得硬判）
gate opportunity         該句經 production 檢索後的 nomination 落在
                         `gate_applies_to = C ∧ D` 為真的 Face 上
                         （C = grounding_scope.requires_instance_reference is True；
                          D = key ∈ LEVEL_A_INSTANCE_GATE_SCOPE）
```

## 6. 判準（**兩層分開，不得混成單一 routing effect**）

### A 層：classifier correctness（全部 judgeable cases）

```text
rule-type     → 期望 verdict = block
instance-type → 期望 verdict = allow
abstain       依本協定判定，**不得事後移動**：
              abstain 計入分母，且**不計為正確**（它代表 ruleset 對該說法無覆蓋）
```

### B 層：routing causal effect（**只在有 gate opportunity 的 case 上問**）

```text
block ＋ gate_applies_to=true → candidate **必須**被 suppress
allow ＋ gate_applies_to=true → candidate **不得**被 suppress
```

⚠️ 兩層的意義不同，**不得互相補分**：
A 問「分類器判得對不對」，B 問「判定真的有沒有控制 routing」。

### 通過門檻（凍結）

```text
judgeable unseen cases ≥ 30                         ← 未達 → 整體 INCONCLUSIVE
A 層：rule-side 與 instance-side **各自**報 accuracy，不合併成單一數字
B 層：有 gate opportunity 的 case **必須 100% 符合**上表
      （這是決定性機制，任何一筆不符即為 implementation defect）
```

### ⚠️ 預先登記的 coverage precondition（**防止第三次白做**）

```text
若 gate opportunity 的 case 數 < 10
  → B 層判 **INCONCLUSIVE**（不是 FAILED），A 層照常判
  → 且該次結果**不得**用來授權 gate
⛔ 不得因為覆蓋不足就回頭重新抽樣**已看過**的語料——那等於挑題。
   覆蓋不足本身即為一項發現，須另取新語料重來。
```

## 7. 失敗時的處置（凍結）

```text
FAIL → 依**第一次** causal failure 歸因，⛔ 不得硬調到綠
     ⛔ 不得補 regex／擴 scope 後重跑同一批語料證明新版泛化
     新版一律另取真正未見的 holdout
PASS → authorized=true → 寫回 manifest → enable gate → 才跑 3.4
```

## 8. claim ceiling

```text
✅ 本協定產出的結論只覆蓋：本次語料、本 ruleset digest、本 protocol digest
❌ 不得宣稱 production block precision（需另行以 production 流量取樣）
❌ n<30 的子群不得做穩定率宣稱
```
