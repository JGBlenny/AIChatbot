# 實作落差分析：routing-disambiguation

> 建立 2026-08-23｜語言 zh-TW
> 需求：[requirements.md](./requirements.md)（APPROVED，9 需求／35 子需求）
> ⚠️ `.kiro/settings/rules/gap-analysis.md` 不存在；本文件以
> **Req.2.1 的六項證據欄位 ＋ Req.2.6 的三值 disposition** 為框架。

## ⚠️ 本版狀態：**pre-freeze structural inventory**

需求的依賴鏈明訂 `Req.3.5 凍結量尺 → Req.2 六層評估`，而本盤查**先於 3.5 完成**。
不重做的理由：本版工作全屬「讀 production code／盤現有 signal／查資料模型／
引用前案既有實測／找 consumption point」——**不涉及在看到方案結果後修改 robustness 尺**。

> **本版可作為候選層現況盤查，但 SHALL NOT 作為方案 robustness acceptance evidence。**
> Req.3.5 完成後，任何新的 L4／L3 實測及**最終 disposition 收斂**均須使用凍結量尺。

## 停止線（本階段刻意不做）

```text
只做：六層 production seam 盤查｜各層實際可見 signals｜現行缺失 signals
     ｜feasibility／cost／blast radius｜disposition｜falsifier／negative control
不做：不選 implementation｜不寫 migration｜不改 routing code｜不新增 instance marker
     ｜不調 prompt／threshold／top_k／anchor｜不進 spec-design
```

⚠️ **`SUPPORTED` 在本階段的意義**是「此層存在**值得進 design 驗證**的能力／訊號」，
**不是**「此層已被選為最終方案」。出現兩三個 `SUPPORTED` 完全合理，trade-off 由 design 負責；
六層全為 `REJECTED`／`INSUFFICIENT_EVIDENCE` 亦為合法結論（Req.2.4），
**不得為了進下一 phase 強選 winner**。

---

## ⭐ 結構性 exposure surface：144 筆（**不是** 144 筆已證實缺陷）

| 事實 | 數量 | 證據等級 |
|---|---|---|
| 啟用中的**空答案錨點** | 98（其中 63 掛面向分類）| 實查 |
| **內容型 KB（answer 非空）同時掛面向分類** | **144** | 實查（**結構條件**）|
| 前案 case-level 判真的 `REGRESSION` | **3** | evidence packet 逐案 |

> **前案確認的 defect 雖只有少數 case，但相同的
> 「content evidence 與 Routing Hint 共居一筆 KB」結構，在 production 有 144 筆 exposure surface。**

⚠️ **這 144 筆是 potential blast radius／exposure surface，不是 confirmed defect。**
本盤查證明的是它們**同時具備**兩個屬性（`answer` 非空 ＝ Knowledge Evidence；
掛面向分類 ＝ Routing Hint），因而**具有本案同型 overreach 的可能性**；
**未證明**其中任何一筆已實際發生錯路由。實際缺陷率與可推廣性仍受 Req.9.3 的 ≥30 規則約束。

**144 改變的是「風險範圍與研究價值」，不是已證實 defect 數。** 它應影響兩件事：

| 影響 | 內容 |
|---|---|
| **Req.2.5 scope** | 不得再無證據假設病灶只存在帳單域 |
| **Req.9 結論分級** | 若要宣稱方案能處理「content KB ＋ Routing Hint 共存」這個**通用結構**，SHALL 自 144 筆 exposure population 取得 **≥30 個可判定的 holdout／validation 案例** |

**兩級 scope（供 Req.2.5 宣告時參考，本階段不選）**：

```text
Level A  billing-domain verified   → 可修本案四筆 known-red
Level B  cross-face generalized    → 需 ≥30 跨域可判定案例，
                                     方得宣稱適用 144 筆 exposure surface
```

⚠️ **不得讓 144 迫使本案一開始就膨脹為全面重構。**

---

## L1 · lexical／structural instance signal

| 欄位 | 內容 |
|---|---|
| **可觀測 signal** | 引擎內已有成熟表層抽取：`_looks_like_identifier`（純數字 2–15 位）、id-like token（4–15 位，排除日期分隔符相鄰）、`_parse_ordinal`（純數字／中文數字／第 X 筆／最後一筆）。`services/conversational_engine.py:88,113,118,137,241` |
| **新增什麼資訊** | 「句中有無識別值」——與相似度**正交**。但**只覆蓋帶編號的問法**；「我這張／我的」等所有格無現成抽取器 |
| **可行性** | 高（既有函式可複用），但目前**只在進入面向之後**使用（插點 A 確定性填槽），**不在進場判定**中 |
| **代價** | 上移至進場判定＝新增全域 routing 訊號，觸及前案 Req.8 排除項，須在本案內明示評估 |
| **否決／保留理由** | 保留——唯一與相似度正交且已存在於 production 的訊號 |
| **可反證條件** | 對本案 instance 案例集實測，若帶所有格但無編號者（「我的這張點退帳單金額怎麼算出來的」）無法被任何表層規則穩定辨識 → 本層不足以單獨承擔判別 |

**Disposition：`SUPPORTED`**（值得進 design 驗證；覆蓋率待量）
**Negative control**：對 rule 案例集跑同一抽取器，若「點退帳單的金額是怎麼算的」也被判為含識別值，則訊號無鑑別力。

---

## L2 · routing-specific metadata／trigger representation

| 欄位 | 內容 |
|---|---|
| **可觀測 signal** | `knowledge_base` 現有：`categories`、`category`、`action_type`、`form_id`、`trigger_mode`、`trigger_keywords`、`keywords`、`priority` |
| **新增什麼資訊** | **目前為零**——`categories` 同時承擔「知識主題」與「Face entry point」兩種語義，正是 overreach 成因（前案 Req.6 已把三層責任寫成文件，但**未落到資料表示**）|
| **可行性** | 中——需把 Routing Hint 與 knowledge evidence 分離表示（新欄位或新關聯），影響 144 筆 |
| **代價** | schema 變更 ＋ 144 筆 metadata 重新判定 ＋ 21 面向進場回歸 |
| **否決／保留理由** | 保留——直接對應根因；但**單靠分離表示不解決判別**：分離後仍需某層決定「這個問句走哪一種」 |
| **可反證條件** | 若能展示「分離表示後判別仍落回相似度競爭」，則本層只是搬移問題 |

**Disposition：`SUPPORTED`**（對應根因，但可能需與其他層合用）
**Negative control**：假想已分離表示，重跑 3.4 的兩個反例——若仍是 0.003／0.004 邊際決定，本層無效。

---

## L3 · intent stage

| 欄位 | 內容 |
|---|---|
| **可觀測 signal** | `intents` 表已有 `api_required`／`api_endpoint`／`api_action`；`intent_classifier.classify()` 輸出含 `requires_api` |
| **新增什麼資訊** | 概念上正是本案要的訊號（「這個意圖需不需要查實值」）|
| ⚠️ **現行缺失** | **主檢索路徑的意圖分類是固定 stub**——`routers/chat.py:1084-1100` `handle_retrieval` 檔頭明寫「intent_result 用固定 stub（意圖在計分零權重）」，Step 3 已註解掉（「省 ~1.5s」）。真分類器僅在**既有表單會話續跑**時呼叫（`chat.py:542`）。且 `requires_api`／`api_required` 於 `routers/`＋`services/`（除 `intent_manager` 的 CRUD 外）**無任何消費點** |
| **可行性** | 低—中——等於重新啟用一個被刻意關閉的階段，並承擔其延遲與成本 |
| **代價** | ~1.5s／請求（當初關閉理由）＋ 54 筆 intent 的 `api_required` 需重新判定 ＋ 分類器準確度未量 |
| **否決／保留理由** | **證據不足**——訊號在資料模型上存在，但在 production 路徑上**從未被驗證過** |
| **可反證條件** | 對本案雙邊案例集實跑真分類器，若 `requires_api` 對 rule／instance 兩組無鑑別力 → 否決 |

**Disposition：`INSUFFICIENT_EVIDENCE`**（本階段**不升級**）
**Negative control**：真分類器對 rule 案例若也回 `requires_api=true`，訊號無效。

⚠️ 本層是**唯一在資料模型上已宣告該語義**者，也是**唯一在主路徑上完全未啟用**者——兩件事必須一起講。

⚠️ **防一個概念偷換**：`requires_api` **不必然等於** `instance-specific`。
通則問題也可能需要 API（例如查系統設定值）；instance 問題也可能由既有 session state 回答。
兩者是**相關但不同**的維度。

⚠️ **L3 offline discriminative measurement 的停止線**：該量測只能回答

```text
現有 intent signal 對 rule／instance 兩組有沒有辨識力？
```

**不能**直接推導

```text
所以重新啟用 Step 3 就是方案。
```

有辨識力只是**必要的第一步證據**；重啟一個被刻意關閉的階段（~1.5s／請求）
是另一個獨立的成本／設計決策，屬 design 階段。

---

## L4 · applicability gate（`_preentry_routable` 延伸）

| 欄位 | 內容 |
|---|---|
| **可觀測 signal** | `routers/chat.py:737-782` 已實作、`PREENTRY_ROUTABILITY_GATE` 預設 `false`；把面向 brain 的 `scope: stay\|switch` 判斷提前到進場前 |
| **新增什麼資訊** | LLM 對「這題適不適用本面向」的判斷——與相似度正交 |
| ⚠️ **現行缺失** | 前案實測：上游凍結後 replay 72 筆 → **錯路由攔截率 1/13**；對 Route-R3（方向對、證據錯）**全數漏放**。本案三筆正屬「主題相關但問法不對」，與 R3 同型 |
| **可行性** | 高（程式已在，開 flag 即可）|
| **代價** | 每次進場多一次 LLM 呼叫；且 `conversational_step` validator 缺陷使其 fail-open（前案 Req.5.2 的 `FACET_SCOPE_SALVAGE` 尚未開啟）|
| **否決／保留理由** | **否決**——前案已用 72 筆母體實測其對本型問題無效，且理由是機制性的：它判 routability（主題屬不屬於本面向），本案問的是 answerability shape（規則 vs 我的那一筆），brain 對兩者都判 `stay` |
| **可反證條件** | 對本案 rule 案例集實跑（`PREENTRY_ROUTABILITY_GATE=true` ＋ `FACET_SCOPE_SALVAGE=true`），若 gate 能穩定判出「規則問句不適用本面向」→ 推翻本否決 |

### ⚠️ Disposition 必須拆兩層（否則推論跨太遠）

用「現有 gate 很弱」推論「applicability gate 這個責任層不可能適合」是**兩個不同命題**：

| 命題 | 現況 | Disposition |
|---|---|---|
| **A. 現行 `_preentry_routable` 實作**有沒有足夠能力？ | 可測——production 程式已在，開 flag 即可 | **`REJECTED`**（前案 72 筆：攔截 1/13、Route-R3 全漏；本輪以 protocol v1 再驗一次）|
| **B. applicability-gate 這個「層級」**若增加新訊號（如 `FACET_SCOPE_SALVAGE`），能否取得足夠資訊？ | **尚無 production implementation** | **`INSUFFICIENT_EVIDENCE`** |

⚠️ **`FACET_SCOPE_SALVAGE` 目前只存在於前案的設計文件，程式未動。**
本階段**刻意不實作它**——先造出新能力再用它推翻「現有 L4 不足」，等於：

```text
先創造新的 L4 能力 → 再用它推翻「現有 L4 不足」
```

那會混掉命題 A 與 B。它應進 `/kiro:spec-design` 作為**可被比較的 L4 design candidate**，
且 design 須先回答：**它到底取得了什麼 L1／L2／retrieval ranking 沒有的新資訊？**
若答案仍只是「再看一次 top-k、再算一次相似度、再用另一個 threshold」，
即使能讓 8/8 過也會撞 Req.2.3／Req.3。

### 本輪 falsifier 的正確命名與範圍

**`L4-current-mechanism falsifier`**（**不是** `L4 layer falsifier`）：
以 frozen protocol v1 跑現行 `_preentry_routable`（fail-open 狀態），
可正式得到的結論是「**現行機制在 protocol v1 下被反證不足**」，
**不是**「applicability gate 這一層永遠不可行」。

⚠️ **不得因為 falsifier 便宜就降低標準**：驗收 SHALL **雙邊同看**——
不只看四筆 RULE 是否被救回 `single`，**還要看 INSTANCE 是否仍進正確 facet**。
只驗一邊就會回到「修一邊、另一邊沒進驗收集合」的老路（前案最大教訓）。

> **protocol v1 已凍結的附帶好處**：現在測現行 gate 的失敗不是浪費——
> 它成為日後所有 L4 新設計的合法 baseline（`CURRENT L4 → X/8` vs `候選 → Y/8` 同尺比較），
> 而非「先做 salvage 再決定怎麼測它」。那正是 Req.3.5 要防的事。

---

## L5 · clarification

| 欄位 | 內容 |
|---|---|
| **可觀測 signal** | **無**——`chat.py`／`conversational_engine.py` grep `clarif`／`澄清` 零命中 |
| **新增什麼資訊** | 反問「您是想了解規則，還是要查您的某一筆？」可直接取得意圖，**完全不依賴相似度** |
| ⚠️ **現行缺失** | 未實作；前案實測 brain 對 Route-R3 **全數判 `stay`**，即**不具 ambiguity 偵測能力**——沒有偵測就不知何時該澄清 |
| **可行性** | 低——需先有 ambiguity 偵測，而那本身可能又落回相似度或 LLM 判斷 |
| **代價** | 每次歧義多一輪（dialogue steering 目標 P50≤4／P90≤6）；且對「點退帳單的金額是怎麼算的」這種**其實不歧義**的問句反問，是體驗倒退 |
| **否決／保留理由** | **證據不足**——機制上最徹底（不靠分數），但**觸發條件無解** |
| **可反證條件** | 出現不依賴相似度的 ambiguity 偵測，且對本案 rule 案例**不觸發**、對真歧義案例觸發 → 轉 `SUPPORTED` |

**Disposition：`INSUFFICIENT_EVIDENCE`**
⚠️ 前案 Req.8 已把「B 澄清分岔」列為不做，理由同上；本案若要重啟須在本案內明示評估。

---

## L6 · KB responsibility 拆分

| 欄位 | 內容 |
|---|---|
| **可觀測 signal** | corpus **已存在該分工**：98 筆空答案錨點（63 掛面向分類）承擔進場，內容 KB 承擔 evidence。20260731 §3 正是**破壞**了這條分工 |
| **新增什麼資訊** | 使「一筆 KB 只承載一種使用者意圖」，Routing Hint 與 evidence 不再共用同一列 |
| ⚠️ **現行缺失** | **144 筆內容 KB 仍同時掛面向分類**——不是 3 筆清理，是全庫級責任重劃 |
| **可行性** | 中——機制已存在（錨點慣例），但需逐筆產品判定（Req.4.2／5.2 依據標準）|
| **代價** | 144 筆 × 產品判定 ＋ 新錨點 embedding 生成 ＋ 全面向進場回歸 |
| ⚠️ **關鍵疑慮** | **3.4 已實測反證**：即使拆成「錨點帶 Hint、內容 KB 不帶」，兩者在 embedding space 仍高度重疊，判別回到 0.003～0.005 邊際。**拆責任不等於拆得開語義** |
| **否決／保留理由** | 保留為**結構性 hygiene／可作組合元件**；3.4 已證實**單獨不充分** |
| **可反證條件** | 找到一組錨點措辭，使 rule／instance 分數差**穩定大於 3.3 定義的門檻**（非個案調參）→ 可單獨成立 |

**Disposition：`SUPPORTED`（結構性 hygiene／可作組合元件；已證實單獨不充分）**

⚠️ **不得寫成「必要非充分」**。3.4 的 revert 證明的是
「拆 responsibility／新增獨立 trigger representation ＋ 仍靠 embedding competition → 不充分」，
**未證明「任何成功方案都必須先做 L6」**。反例：若 L3 intent stage 能可靠區分，
同一筆 KB 仍可存在，Routing Hint 是否生效改由 intent 決定——此時 L6 非邏輯必要條件。

**Negative control**：3.4 的 revert 即為本層單獨使用的失敗實例，已在案。

---

## 逐層 disposition 總表（Req.2.6）

| 層 | Disposition | 支持／否決的 production evidence | 推翻本判定的觀察 |
|---|---|---|---|
| L1 lexical／structural | `SUPPORTED` | 引擎既有 id-like／ordinal 抽取，與相似度正交 | 所有格但無編號的 instance 問法無法穩定辨識 |
| L2 routing metadata | `SUPPORTED` | `categories` 雙重語義即根因；前案 Req.6 三層模型已成文未落地 | 分離表示後判別仍落回相似度競爭 |
| L3 intent stage | `INSUFFICIENT_EVIDENCE` | `api_required`／`requires_api` 已在資料模型；但主路徑 intent 為 stub、零權重、無消費點 | 真分類器對 rule／instance 兩組無鑑別力 |
| L4-a **現行 `_preentry_routable` 實作** | **`REJECTED`** | 前案 72 筆實測：攔截 1/13、Route-R3 全漏；本輪 protocol v1 再驗 | 現行 gate 在 protocol v1 下雙邊同時達標 |
| L4-b **applicability-gate 層級潛力** | `INSUFFICIENT_EVIDENCE` | `FACET_SCOPE_SALVAGE` 尚不存在於 production，未實測 | 該層能提供不同於 retrieval similarity 的新資訊來源 |
| L5 clarification | `INSUFFICIENT_EVIDENCE` | 未實作；brain 對 R3 全判 `stay`＝無 ambiguity 偵測 | 出現不依賴相似度且不誤觸的偵測機制 |
| L6 KB responsibility | `SUPPORTED`（hygiene／組合元件；單獨不充分）| corpus 已有錨點／內容分工；144 筆 exposure surface 仍共居 | 錨點措辭能使分數差穩定大於門檻 |

**三個 `SUPPORTED` 皆為「值得進 design 驗證」，非選定。** L1／L2／L6 有互補跡象
（L6 清資料、L2 分表示、L1 供正交訊號），但**組合是否成立由 design 評估**，本階段不判。
⚠️ 亦**不得推論任一層為其他層的前置條件**——現有證據只支持「某層單獨不充分」，
不支持「某層為必要」。

---

## 缺口摘要：現行缺什麼訊號

| 缺口 | 影響 |
|---|---|
| **無「使用者是否指涉自己的某一筆」的顯式訊號進入進場判定** | 判別只能靠相似度，而兩類問句語義高度重疊 |
| **`categories` 一欄承擔兩種語義** | Routing Hint 無法獨立於 knowledge evidence 調整 |
| **主路徑意圖分類為 stub** | 資料模型已宣告的 `api_required` 語義從未被啟用或驗證 |
| **無 ambiguity 偵測** | 澄清路線的觸發條件無著落 |
| **144 筆內容 KB 帶 Routing Hint** | 任何 metadata 方案的影響面遠大於前案的 3 筆 |

## 待 design 階段研究（本階段不決定）

1. L1／L2／L6 的組合是否足夠——各自不足，合用是否互補？
2. L3 的 `api_required` 若要驗證，成本多大？（重啟 stub 階段 vs 離線對案例集跑分類器）
3. L4 的否決值得先跑一次反證實測（成本低：開兩個 flag ＋ 現有 rule 案例集）
4. Req.2.5 的適用範圍：帳單域 vs 21 面向——受 144 筆分布影響
5. Req.3.5 的量尺凍結必須在上述任何實作或調整之前完成

---

## 建議的下一步順序

```text
Req.3.5 凍結穩健性量尺（尚未做，且必須最先）
   ↓
L4 反證實測（成本最低、可能推翻一個 REJECTED）
   ↓
L3 離線鑑別力量測（不重啟 stub，先看訊號有無鑑別力）
   ↓
/kiro:spec-design routing-disambiguation
```

⚠️ 本文件**未選定 implementation、未寫 migration、未改任何 routing code**。


---

# Post-freeze 實測（protocol v1，digest `4690a258f502d98d`）

> 原始結果：`evidence/l4_off.json`、`l4_on{,_2,_3}.json`、`l3.json`
> 語料 digest `918b69ce70fbb8f1660819c3774eb24b`；正規入口 `docker compose run`。

## 實測 1 · `L4-current-mechanism falsifier`

**只測現行 production 機制**（`_preentry_routable`）；`FACET_SCOPE_SALVAGE` 未實作，
故 `conversational_step` 輸出被丟棄時 gate **fail-open**——這是現況，非缺陷模擬。

| 案例 | gate OFF | gate ON（三輪）|
|---|---|---|
| RULE 點退帳單的金額是怎麼算的 | ❌ dialog | ✅ ✅ ✅ single |
| RULE 點退做完後，帳單會自動出來嗎？ | ❌ dialog | ❌ ❌ ❌ dialog |
| RULE 收據 PDF 在哪裡下載 | ❌ dialog | ✅ ✅ ✅ single |
| RULE 系統怎麼算點退帳單的金額 | ❌ dialog | ✅ ✅ ✅ single |
| INSTANCE 我的這張點退帳單金額怎麼算出來的 | ✅ | ✅ ✅ ✅ |
| INSTANCE 我這筆點退帳單怎麼會是這個數字 | ✅ | ✅ ✅ ✅ |
| **INSTANCE 幫我查點退帳單金額** | ✅ | **❌ ✅ ❌ ⚠️ 三輪翻面** |
| INSTANCE 這張帳單的收據金額多少 | ✅ | ✅ ✅ ✅ |
| UNDECIDED（僅觀察）| 兩筆皆 `帳單異常` | 兩筆皆 `帳單異常`（未受影響）|

```text
bilateral_pass（門檻 8/8）   OFF 4/8   →   ON 6/8 ／ 7/8 ／ 6/8    ← 從未達標
RULE      0/4 → 3/4     ← gate 確實有訊號
INSTANCE  4/4 → 3/4     ← 但錯攔一筆
flip（無擾動、僅重跑）  1/8 在三輪間翻面
```

### 判定：`L4-a` **`REJECTED`（protocol v1 下再度確認）**

三項依據：
① **bilateral_pass 三輪皆未達 8/8**；
② **為了攔 rule 而傷到 instance**——正是雙邊同看才看得到的失敗（只看 RULE 會判它「大有可為」）；
③ **無擾動即翻面**——LLM gate 在判別邊界上非決定性，`flip_rate` 在 P1–P3 尚未施加前就已違反。

> ⚠️ 本輪比前案（72 筆／攔截 1/13）**更細緻**：現行 gate 對本型問題**並非全無訊號**
> （3/4 RULE 穩定攔下），失敗在**精度**與**決定性**，不在「完全看不見」。
> 這句話**只描述現行實作**，不上調 L4-b。

### `L4-b` 維持 **`INSUFFICIENT_EVIDENCE`**（新增一個正向指標，但不升級）

本輪首次出現「applicability 判斷能穩定攔下 3 筆相似度攔不住的 rule 問句」的證據，
顯示**該層可能帶有不同於 retrieval similarity 的資訊**。但：

- `FACET_SCOPE_SALVAGE` 仍未實作 → 該層的完整能力未測；
- 現行實作的**非決定性**是否為該層固有（LLM 判斷）或可設計掉，未知。

⚠️ **不得以「現行 gate 有部分訊號」推論該層可行**——那與「用現行 gate 很弱推論整層不可行」
是同一種跨越，只是方向相反。

---

## 實測 2 · `L3 offline discriminative measurement`

**未重啟 Step 3、未改任何 production 路徑**——離線直呼 `IntentClassifier.classify()`。

| 案例 | intent_name | intent_type | requires_api |
|---|---|---|---|
| RULE ×3（點退金額／自動出來／系統怎麼算）| 帳務查詢 | `data_query` | `False` |
| RULE 收據 PDF 在哪裡下載 | 收據問題 | `knowledge` | `False` |
| INSTANCE ×4（全部）| 帳務查詢 | `data_query` | `False` |

**實查 `intents` 表（54 筆）：`api_required = true` 者 0 筆。**

### 判定：`L3-a`（現行 intent 訊號**如其被供裝的樣子**）**`REJECTED`**

三個**互相獨立**的缺口，任一即足以使其無法承擔判別：

| # | 缺口 | 證據 |
|---|---|---|
| 1 | **訊號從未被供裝** | `api_required=true` 於 54 筆 intent 中為 **0 筆**——不是「對本案無鑑別力」，是**資料上不存在** |
| 2 | **訊號從未被消費** | `requires_api`／`api_required` 於 `routers/`＋`services/`（除 `intent_manager` CRUD 外）零命中 |
| 3 | **主路徑該階段為 stub** | `chat.py:1084-1100`，Step 3 已註解、零權重 |

### ⭐ 更根本的結構發現：rule／instance 與 intent taxonomy **正交**

八筆案例中 **7/8 映到同一個 intent（帳務查詢）**，rule 與 instance 的分界
**切在該 intent 內部**。故：

> **現行 intent 分類法在建構上就無法分辨兩者**——不是分類器不準，
> 而是它的**維度不同**。要用 L3，必須先讓 taxonomy 長出「規則 vs 我的那一筆」這個新維度。

（唯一的例外「收據 PDF 在哪裡下載」→ `knowledge` 型別正確，但另三筆 rule 仍為 `data_query`，
故 `intent_type` 亦不足；1/4 命中不構成鑑別力。）

### `L3-b`（intent stage 作為**層級**）維持 **`INSUFFICIENT_EVIDENCE`**

若 taxonomy 增加該維度，本層是否足夠——未測。
⚠️ 停止線不變：**有無鑑別力 ≠ 重啟 Step 3 就是方案**；重啟一個被刻意關閉的 ~1.5s 階段
是獨立的成本／設計決策。

---

## 更新後的六層 disposition（protocol v1 實測後）

| 層 | Disposition | 本輪新增依據 |
|---|---|---|
| L1 lexical／structural | `SUPPORTED` | 未變（覆蓋率仍待量）|
| L2 routing metadata | `SUPPORTED` | 未變 |
| **L3-a** 現行 intent 訊號 | **`REJECTED`** ⬅ 由 `INSUFFICIENT_EVIDENCE` 改判 | `api_required` 0/54 未供裝；7/8 同 intent＝維度正交 |
| **L3-b** intent stage 層級 | `INSUFFICIENT_EVIDENCE` | taxonomy 增維後未測 |
| **L4-a** 現行 `_preentry_routable` | **`REJECTED`**（再確認）| bilateral 6-7/8 未達標；錯攔 instance；無擾動即翻面 |
| **L4-b** applicability-gate 層級 | `INSUFFICIENT_EVIDENCE` | ⬆ 新增正向指標：3/4 rule 穩定攔下（**不升級**）|
| L5 clarification | `INSUFFICIENT_EVIDENCE` | 未變 |
| L6 KB responsibility | `SUPPORTED`（hygiene／組合元件；單獨不充分）| 未變 |

**現存 `SUPPORTED`：L1、L2、L6。** 三者皆為「值得進 design 驗證」，非選定；
**無 winner，亦不強選**（Req.2.4）。

### 🔁 可重複使用的判準（本輪由 L3／L4 拆層逼出）

> **「現行實作失敗」不能直接推出「這個責任層不可行」；
> 反過來，「現行實作顯示部分訊號」也不能直接推出「這個責任層可行」。**

故凡有 production implementation 的候選層，disposition SHALL 拆為
`-a` 現行實作 與 `-b` 責任層潛力 兩筆（本輪：L3-a／L3-b、L4-a／L4-b）。

### ⭐ 兩個結構發現（正式表述，供 design 起手）

> **發現 1｜現行 intent taxonomy 與 rule／instance distinction 正交。**
> 7/8 落在同一「帳務查詢」intent，表示**若選 L3，設計必須新增可表達此 distinction 的資訊，
> 而不是單純恢復既有 classifier**。

> **發現 2｜現行 applicability 判斷確實觀察到 retrieval similarity 沒有完全提供的訊號，
> 但其 precision 與 determinism 不足。**（3/4 rule 穩定攔下；1 筆 instance 誤殺；無擾動即翻面。）

這兩句比「所以選 L3／L4」強得多——它們描述**證據**，不預判**方案**。

⭐ **原摘要**（保留）：
> 1. **applicability 判斷帶有相似度沒有的訊號**（3/4 rule 穩定攔下），
>    但現行實作在精度與決定性上不足；
> 2. **rule／instance 的分界與 intent taxonomy 正交**——同一 intent 內部的分歧，
>    現行分類法在建構上分不開。
>
> 兩者共同指向（**措辭已收斂**）：
>
> > **「問句是否指涉特定個體」目前沒有被 production 以
> > 可供 routing 穩定消費的第一級訊號顯式表示。**
>
> ⚠️ 刻意**不寫**「任何一層都沒有這個資訊」——那句過頭了：
> L1 已能看到「我的／這筆」等表層證據，L4 實測也顯示部分辨識力。
> **真正缺的是被明確建模、具有契約、且能穩定消費的 representation**，
> 不是「完全看不到訊號」。
