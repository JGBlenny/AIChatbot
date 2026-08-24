# Authority-Origin Discovery：封口 — **INSUFFICIENT_EVIDENCE**

> 2026-08-24｜語言 zh-TW｜依 `responsibility-truth-source-qualification-frozen.md`（O1–O6，`aa3a4b2`）
> 前置：`authority-origin-repo-side-inventory.md`（repo-side 已凍結，`d5cc0fa`）
> **裁定（業主）：不判 B，也不判 C。以 INSUFFICIENT_EVIDENCE 封口。**

## 判定

```text
結局 A   **已排除**（repo-side：未見 first-class／versioned／可 enrollment 的 normative authority）
結局 B   \
結局 C   /  **無法在現有證據下區分** → **B／C unresolved**

封口理由：**extra-repository governance evidence unavailable**
```

## 兩種「不知道」必須分開（**本檔的核心紀律**）

```text
✅ 已證實
   repo 內**不存在**足以回答 authority origin 的 governance provenance

⬜ 尚未證實
   組織上**不存在** responsibility owner ／ veto ／ approval process
```

**因此**：

```text
❌ 不得寫：沒人能回答 → 沒有治理 → C
✅ 只能寫：repo 外 governance facts unavailable
          → O1／O2／O5 等關鍵資格無法裁定
          → B／C unresolved
```

⚠️ 這與本線一貫的 E5／§5 紀律同源：**`not evidenced` ≠ `does not exist`。**

### 查核已到極限（說明為何不再考古）

```text
repo 側：已完成 governance-artifact inventory（d5cc0fa），
        唯一具 approver 欄位的產物（knowledge_review_queue）不覆蓋責任且被寫入路徑繞過
記憶側：20260731 補標可查到**觸發來源**（客服回報 R-31～R-37）與**實作**（63d5e2d），
        **查不到**誰有資格裁決責任歸屬；且該記錄為本工作線自身筆記，非組織核可記錄
對話側：既有脈絡中**未找到**任何明確陳述足以回答六題任一題

→ 再 grep 更多 repo、翻更多舊 commit，已很難回答「誰有權決定」這種**組織性事實**。
```

---

## O1–O6：**能證多少寫多少**

⚠️ 已凍結的 O1–O6 schema **未定義 disposition 值域**（只要求逐條 disposition）。
故此處採 `INSUFFICIENT ／ PARTIAL`，**刻意不硬算 PASS／FAIL**；此為**明示選擇**，非規避。

| | 條件 | disposition | 依據 |
|---|---|---|---|
| **O1** | Normative legitimacy | **INSUFFICIENT** | 不知道誰有資格制定 responsibility truth；repo 內可查者（B1／B2／B3、seed prose）皆為描述現況 |
| **O2** | Independence from candidate | **INSUFFICIENT** | 無法證明實際裁決者獨立於 Face／實作者；config API 無任何核可痕跡，但 repo 外是否有核可者不明 |
| **O3** | Explicit responsibility semantics | **PARTIAL** | repo 確有 responsibility wording（seed RULES、`facet-backfill-review.md` 的準則與逐筆理由），但 **authority origin 未建立**；且散文需人事後解讀 |
| **O4** | Versionability | **PARTIAL** | git／文件可追**變更**；但「版本化實作」**≠**「版本化權威裁決」——未見責任版本、生效版本、變更核可者 |
| **O5** | Enrollment authority | **INSUFFICIENT** | repo 內無 admission process（`conversational_configs.py` 全檔 approv/review/owner/audit 零命中）；repo 外是否有人工 approval 不明 |
| **O6** | Executable handoff | **技術能力存在，無合法內容可 handoff** | carrier comparison 已證 X-3 三者皆 PASS（擋得住）；但目前**沒有已驗證的 normative truth** 可合法 handoff |

---

## 本輪確實取得的東西：一條可用的 **design dependency**

> **目前這條工作線無法指出一個可被驗證的 normative authority origin，
> 因此任何新的 Responsibility Authority carrier
> MUST NOT 把既有 seed、Face self-declaration、categories、LLM 判斷
> 或實作者決策**冒充成 responsibility truth**。**

即：在 authority origin 被明確識別並留下可驗證的 authority provenance **之前**，
對系統設計而言它就是：

```text
✅ authority_origin = unresolved

❌ authority_origin = engineer
❌ authority_origin = Face seed
❌ authority_origin = categories
❌ authority_origin = LLM verdict
```

⚠️ **這個區分是本輪最實際的產出**：即使組織上其實存在某個 owner，
在它被識別之前，設計上**不得**把任何現成物頂替上去。

### `facet-backfill-review.md` 的正確狀態

```text
confirmation provenance = **unknown**

❌ 不再猜是誰確認
❌ 不得因為它有準則、有逐筆理由、有「已確認」字樣就取得 normative authority
✅ 它仍是有效的 GOVERNANCE_ARTIFACT **形式**證據（有人在做責任裁決），
   但**不構成** authority origin
```

---

## 外部 dependency ／ decision record requirement（**不是 R7**）

> **在任何 responsibility carrier 可被啟用之前，本專案 MUST 識別並記錄：**
>
> ```text
> - authorized responsibility decision owner ／ role
> - approval 或 veto semantics
> - enrollment authority for new Faces
> - versioned normative decision artifact
> ```

⚠️ **這不是在聲稱「過去一定沒有治理」**，而是在說：

```text
未來若要讓 R6 可實際上線，這些 authority facts
MUST 從 **unavailable** 變成 **explicit**。
```

> **歷史治理是否曾存在 → 留作 unresolved fact。**
> **未來制度要求 → 現在就可以誠實地定義。**
> 兩者乾淨分開，前者不阻止後者。

### 為何不新增 R7

R6 已經夠強（MUST 新增 first-class responsibility authority）。
本輪**未**證明「responsibility truth 是 normative product decision 且目前無 governing source」——
該 hypothesis 仍為 hypothesis。故**不得**導出如
「responsibility authority MUST originate from an explicitly authorized,
versioned product-governance source」這類新條文。

⚠️ 上述 decision record requirement 是**外部依賴登記**，
**不是** requirement 層的新條文，也不改動已凍結的 R1–R5／R6。

---

## 下一步的方向轉換（本輪封口時確立）

```text
❌ 停止：考古「誰以前有權」
✅ 轉為：若下一版要成立，必須先建立一個
        **可識別、可版本化、可 enrollment 的 responsibility governance origin**
```

## 本輪**未**做

```text
❌ 未判 B，未判 C（B／C unresolved）
❌ 未由 git 作者／實作者／文件撰寫者推論 authority owner
❌ 未把「沒人回答得出來」當成「沒有治理」
❌ 未新增 R7；未改已凍結的 R1–R5／R6／Contract／ruler／O1–O6
❌ 未設計 governance 流程（本輪只判資格，且判不了）
❌ 未復活任何 carrier；未開 member；D1／D3 family 仍 INSUFFICIENT_EVIDENCE；D2 仍 deferred
❌ 未動 production；未產測資；ruler 0.058928 仍凍結未用
```
