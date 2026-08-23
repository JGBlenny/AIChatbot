# Q2：既有 applicability signal 盤點（code-level contract audit）

> 2026-08-24｜語言 zh-TW｜discovery Q2 第一輪｜**唯讀讀碼，未取 production 數據**

## ⚠️ 先更正 Q1 的一個框架問題

`_top1_relevance_gate` 的 docstring（`routers/chat.py:1089–1091`）**逐字寫著**：

> 「⚠️ 本閘門只守「直答」路徑。面向進場在 handle_retrieval 更前面（分類路由…），
> **不經過這裡**——**替知識補 categories 等於把它移進一條繞過本閘門的路徑**，
> 補標時須一併考量。」

**Q1 的「發現」有一半是 rediscovery**：這條繞道在 gate 寫下時就被記錄，並附了警告。
⚠️ 而 v1 的根因（`20260731` §3 替 3402／3406／3519 **補掛面向分類**）
**正是這段警告所描述的動作**。

```text
新增事實：bypass 不是未被察覺的缺陷，而是**已記錄的已知後果**；
          真正失效的是「補標時須一併考量」這道**流程約束**——它沒有機制保證。
```

---

## Signal 1：`_top1_relevance_gate`（query × Knowledge applicability）

| 欄 | 實查結果 |
|---|---|
| 執行條件 | `handle_retrieval` 的 knowledge 分支；**面向進場成功即 early-return，不會執行到** |
| skip | 表單／API 觸發列不判；`RELEVANCE_GATE_SKIP_VEC` **預設未設＝不跳過**（註記：拿高語意相似當免判理由「自相矛盾」）；`RELEVANCE_GATE_ENABLED=false` 可整道關閉 |
| input | `問題` ＋ `知識標題(question_summary)` ＋ `知識內容節錄(answer[:180])`｜**不含** session／Face／slot |
| 判準 | **適用性不是相關性**（2026-08-22 業主定案，precision-first）。prompt 逐字：「相關不等於足夠…寧可判 NO 讓系統回覆查無」；「只是主題相同、症狀相似」一律 NO |
| 語義 | YES→該列晉為 top1 候選；NO→次筆晉位（最多 `max_checks=2`）；全 NO→空列走誠實 fallback |
| 失敗 | **b2b fail-closed**（視同不適用）／b2c fail-open |
| 決定性 | ❌ LLM（模型敏感度已實測：3.5-turbo 8/25 vs 4o-mini 20/25）|
| Pre-entry 可取得 | ✅ 輸入只需 query ＋ KB row，**面向進場前即可算** |

## Signal 2：`scope = stay | switch`（query × **某一個** Face 的 applicability）

| 欄 | 實查結果 |
|---|---|
| input | `rules_text`(persona 規則)、`system_context_md`(**該 Face** 的系統脈絡)、`state`、`user_message`、`faces` 清單、`kb_search` callback |
| output 契約 | **A 類（適用／不適用）**，非單純話題切換——engine 消費端逐字：「brain 判定**這句明顯不屬本 config 職責** → 關會話、回 None，由 chat.py 落回一般流程對當前訊息**重路由**」。正規化：缺省／越界 → `stay`（fail-safe 向 stay）|
| consumer | ① `conversational_engine:687`（**session 內**）→ `_close(session)` ＋ 重路由；② `_preentry_routable`（`chat.py:778`，**進場前**）→ 不進場。②的旗標 `PREENTRY_ROUTABILITY_GATE` **預設 false** |
| timing | **進場前可算**——`_preentry_routable` 實際以空狀態呼叫（`collected_fields={}`／`asked_count=0`／`recommended=False`），v1 design 已註記「六個狀態欄位在進場那一輪全是空的」 |
| **prerequisites** | ⚠️ **需要一個「候選 Face」才能判**：`rules_text` 依 persona_role、`system_md` 依 face key。**沒有候選 Face 就沒有可判對象。** |
| 決定性 | ❌ LLM；且 v1 已實測其 `action` 驗證會整包丟棄（`data is None` → fail-open）|

### ⭐ scope 的 falsifier 判定結果

業主設的 falsifier：**「若 scope 的正確判斷依賴進入 Face 後才成立的 state，就不能稱為 pre-entry authority。」**

```text
判定：**通過**（不依賴進場後 state）——`_preentry_routable` 以全空狀態呼叫即為實證。
但**另一個限制成立**：它是 **per-candidate-Face 的二元測試**，不是全域路由器。
→ 它能回答「這句適不適用於 **Face X**」，回答不了「這句該去哪」，
  更回答不了「這句該不該進**任何** Face」。
```

## Signal inventory（服務 Q2）

| Signal | 判斷對象 | Query-aware | Face-aware | Pre-entry 可取得 | Deterministic | 現行消費者 | 可跨 entry source？ |
|---|---|---|---|---|---|---|---|
| `_top1_relevance_gate` | query × KB row | ✓ | ✗ | ✓ | ✗ | **direct-answer only** | **待判**（它不知 Face，無法判「該不該進場」）|
| `scope=stay/switch` | query × **單一** Face | ✓ | ✓ | ✓ | ✗ | Face brain（session 內）／`_preentry_routable`（預設關）| **待判**（需候選 Face；N 個 Face → N 次 LLM）|
| session 存在 | session state | ✗ | ✓ | ✓ | ✓ | 續談直入 | ✗ |
| `trigger_facet_key` | **呼叫端斷言** | ✗ | ✓ | ✓ | ✓ | 直達進場 | ✗ |
| vision confidence | **圖片** × Face | ✗ | ✓ | ✓ | ✗ | 損傷改道 | ✗ |
| `facet_entry_eligible` | similarity 門檻 | ✗ | ✗ | ✓ | ✓ | 分類路由 | ✗（與 P7 同源）|
| KB `categories` | KB row | ✗ | ✓ | ✓ | ✓ | 分類路由 | ✗（P7：非新 authority）|

## 本輪可下的結論（**不越界**）

```text
CONFIRMED
- production 已存在**兩類局部 applicability evidence**：
  query×KB（只服務 direct-answer）與 query×單一Face（只在 session 內生效／進場前旗標預設關）
- 兩者**皆非決定性**（皆 LLM），且**皆不覆蓋** trigger_facet_key／vision／session 三種 entry
- bypass 是**已記錄的已知後果**，失效的是流程約束而非認知缺口

INSUFFICIENT EVIDENCE
- `_top1_relevance_gate` 的**實效**（攔截率／誤殺率）：
  `usage_events` **不寫 gate 判定**（欄位僅 processing_path／answer_source 等），
  故 **rejection rate 無法自 telemetry 取得**，correctness 更不可能
  → **不得**以觸發率或現行 route 代替 correctness
```

⚠️ **明確不做的推論**：兩類 evidence 存在 **≠**「把兩個整合起來就是 v2」。
五種 entry source 中的 `trigger_facet_key`（呼叫端斷言）、vision（判圖片）、
existing session（判狀態）**都不由 query applicability 決定**，
其等價 authority 由誰提供，本輪**尚未回答**。

## 下一步的取數選項（待業主裁示）

```text
(1) production 日誌：gate 會 print「🛡️ [適用性把關] …」→ 需線上撈 log（我不代跑）
(2) 離線重放：以凍結語料在本機跑該函式，量**已知案例上**的攔截與誤殺
    → 可控可重複，但**不是 production 頻率**，且需先有 case-level ground truth
(3) 加觀測欄位 → **implementation，discovery 階段不做**
```
