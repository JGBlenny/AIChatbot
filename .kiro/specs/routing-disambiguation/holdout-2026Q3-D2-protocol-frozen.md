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

## 3. 語料來源（**已改為真實口語文件，非代理自產**）

> 2026-08-28 業主裁定：改用 `JGB_口語化問法_v2.pages`（基於 JGB 幫助中心產出）。
> 理由：來自實際 JGB 幫助中心語境，優於代理想像的問法。

### 3.1 來源凍結

```text
file    ~/jgb/JGB_口語化問法_v2.pages
sha256  579e9fa27f4321abea1a49816c21420c3243867e5cad311e256deb410775792c
size    2817455 bytes｜mtime 2026-08-28T23:26:13
凍結副本已留存；日後原檔若再編輯，**不影響**本次授權所用語料。
```

### 3.2 污染查核（**執行抽取前完成**）

```text
D1 holdout 50 句        交集 = 0
KB question_summary（921）交集 = 0
既有 routing tests       交集 = 2 → 機械排除
repo 全文搜「口語化問法」 → 查無任何引用
ruleset 自述來源＝research.md 主題 1 的 20 筆樣本（非本文件）
⚠️ 無法由工程端證明「當初寫特徵表的人未曾看過本文件」——該點由業主確認。
```

### 3.2b 來源鏈時序查核（2026-08-28 追加，**把 provenance gate 收到證據能到的極限**）

```text
① 規則集寫入時間  916c63e8  2026-08-23 23:29:39
   git log -S"COUNTER_PATTERNS" -- services/instance_evidence.py
   → **只有這一筆**，此後 patterns 從未變更 ⇒ 規則集自 08-23 起凍結
② 本文件在本機的 birth time  2026-08-28 23:26:12（晚五天）
③ 規則集自述來源＝protocol v1 凍結案例集的 20 筆（repo 內建物）
   該案例集（robustness-protocol.json／evidence/protocol-v1-baseline.json）
   與本文件的交集 = **1 句**「帳單有哪幾種狀態」
   → 該句已被污染過濾機械排除：**不在 sealed pool、不在 D2 sample**
④ D1 holdout ∩ 文件 = 0｜KB question_summary ∩ 文件 = 0
```

### 3.2c ✅ **provenance gate 已關閉**（2026-08-28 業主確認）

> 業主確認：**這份文件是今天才提供，先前未曾給過。**
> ⇒ 撰寫 `instance-evidence` 特徵表時（2026-08-23）不可能參考它。
> 下方「殘留缺口」自此解除，保留原文僅供追溯當時的推理狀態。

**（已解除）殘留的唯一缺口**（證據到不了，需業主確認）：

```text
檔名為 v2 ⇒ 可能存在更早的 v1（不在 ~/jgb）。
birth time 只證明「這個檔案何時出現在本機」，不證明內容何時被撰寫。
⇒ 若 v1 於 2026-08-23 之前存在且被特徵表作者參考過，本批語料仍屬污染。
   除此之外，時序與來源鏈皆支持「未被參考」。
```

### 3.3 機械抽取規則（**先凍結，執行後不回頭調**）

```text
INCLUDE  6 ≤ len ≤ 40 ∧ 含中日韓文字
         ∧ 疑問樣態：句尾 ？/?/嗎/呢 或含
           怎麼|如何|哪|什麼|可不可以|能不能|要不要|是不是|有沒有|會不會
EXCLUDE  原文|建議先用|我不能|標記為|一律|^表格|^可以，|^不行|^是的|^沒有，
         |請洽|請聯繫|如下|以上|範例|欄位|頁面|系統會|若你|你可以
         （客服回答／後設評論／版面殘留）
＋ 機械排除三份污染清單｜＋ 去重（去空白後比對）
PARTITION  sha256(去空白問句) 前 8 hex % 4 == 0 → 密封；其餘釋出
```

⚠️ 規則以**結構與句型**定義，**不含**任何依內容挑選的判斷——
選句不經工程端的主觀判斷，這是本次抽取可信的唯一理由。

### 3.4 執行結果

```text
原始候選行 11376 → 長度不符 118｜非疑問 8978｜排除樣態 130｜污染 2｜重複 1
kept = 2147
  sealed（授權候選池）  n=576   digest=1b85edb1d7e58b95
  released（可補 KB）   n=1571  digest=ccaef1f7a28531a2
  互斥檢查：交集 = 0 ✅
D2 sample（預先登記的抽樣規則）：
  sealed 池內依 sha256 升冪取前 80 句  n=80  digest=c57a8eac6b03cd51
  （80 句留給不可判定的耗損，確保 judgeable ≥ 30）
  池內其餘 496 句為**保留**，供未來輪次；本輪不得動用
```

### 3.5 禁令

```text
⛔ sealed pool（576 句）在 D2 授權執行前，禁止進入 KB／prompt／classifier 調整
⛔ 不得用它挑題：sample 由預先登記的 hash 排序決定，非人工挑選
✅ released（1571 句）即刻可用於知識工程
```

---

## 3B. 若日後改回代理產題——前次已驗證的隔離紀律（保留備用）

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
