# 業主 position：entry nomination 與 responsibility applicability 的權責配置

```text
Status: OWNER NORMATIVE INPUT
Not a Decision Record
Does not change routing-authority-model status
Does not authorize implementation
```

> 2026-08-25｜語言 zh-TW｜提出者：業主
> 收件對象：**Responsibility Governance Decision Record**（產品決策方）
> 佐證來源：`face-exit-before-grounding`（descriptive discovery = COMPLETE）
> ＋ `conversational-routing-execution`（C4b／任務 11 telemetry inventory）
> ⚠️ 本檔為**可被逐條接受、拒絕或修改的提案**，不是研究結論，也不是已批准的 architecture。

---

## 0. 提案的一句話

> **Retrieval 只有「提名權」；Responsibility applicability 才有「進場核准權」。
> 而候選集合不能只由 retrieval categories 產生。**

現制與提案的差別：

```text
現制   Query → retrieval top-1 → categories → Face → **建 session** → scope 判斷 → 不適合再退出
提案   Query →（retrieval evidence ＋ responsibility evidence）→ candidate set
             → applicability adjudication →（適合才 commit ／ 多個 → arbitration ／ 皆不適合 → knowledge・fallback）
             → Execution
```

---

## G1. Retrieval／knowledge categories 僅具 candidate nomination 權

> **Retrieval／knowledge `categories` 僅具有 candidate nomination 權，
> 不構成 responsibility ownership evidence。**

**Evidence（本條最硬）**

```text
entry 的證據語言   檢索 top-1 的 categories ＋ 相似度門檻（0.75）
responsibility 的證據語言  persona 的【本輪範疇 scope】契約
兩者在現行系統中**沒有交集**：entry 從不讀 responsibility wording；scope 不知道 entry 發生過
實證：本 query 的 owner（contract_closeout）穩定接受 3/3，entry 卻 9/9 只提出會拒絕的 Face
```

→ 來源：`research.md` §5（contract map）、§8／§10／§11、§12（entry nomination chain）

**Prerequisite**：無。此條不依賴任何尚未完成的工作。

---

## G2. Session commit 前應取得 candidate-specific applicability evidence

> **Normal conversational Face 應在 session commit 前取得 candidate-specific
> responsibility applicability evidence；但採用此設計前，pre-entry evaluation context
> 必須與 in-session responsibility evaluation 的 authoritative context 同源。**

**Evidence（支持「提前判定不損失資訊」）**

```text
進場輪的狀態是空的：collected={}／asked_count=0／recommended=False／無 grounding_note／無 dialog
實測捕捉的 prompt 證實**只餵原始問句**（research.md §7）
⇒ 把 applicability 判定提前到 commit 之前，**不會**因為少了會話狀態而變弱
```

**⚠️ Blocker（必須先解，否則「提前的判定」不是「原本那個判定」）**

```text
Observed:
  pre-entry context source  = cfg.key
  in-session context source = _domain_key(topic_scope.category)

  billing_anomaly digests differ
    pre-entry  d1f88c90a2e0c9d2（落回 base）
    in-session 2158ebdc2d8fe7e6（帳單異常領域脈絡）
→ production-equivalence not established
```

（`_preentry_routable` 現行三處宣告皆 `false`：`.env:164`、prod:224、dev:81。）

**⚠️ Decision cost（architecture decision constraint，不是 implementation footnote）**

```text
現行 candidate-specific applicability ＝ **每候選一次 gpt-4o 呼叫**（temp 0.4／max_tokens 400／json_object）
若 candidate set 擴為多來源 union，naive implementation 可能造成**每 request 多次前置 LLM invocation**
——以本提案示意的 union（responsibility 2–4 ＋ retrieval 1–3）為例，naive 上界約 4–7 次，
  相對現況每輪 1 次 brain 呼叫，是**數量級的 latency／cost topology 變化**
```

⚠️ 上述數字是「naive union ＋ 現行 adjudicator」的**成本上界形狀**，
**不是** G2 的必然實作要求（見 §「本 position 不決定什麼」）。

---

## G3. 現有 machine-readable declaration 不足以表達完整 responsibility semantics

> **Candidate generation 不得只依賴 knowledge categories；
> 但問題不是「沒有 responsibility source」，而是現有宣告不足以表達 responsibility 語義。**

```text
Existing   topic_scope.category
           → machine-readable，支撐 by_category 索引與粗粒度 nomination

Missing    accepts ／ excludes ／ delegates（或等價的 responsibility semantics）
```

**Evidence**

```text
`billing_anomaly → contract_closeout` 這條 delegation edge **只有 natural-language persona
contract 能表達**——它是靠讀 LLM 的 runtime 輸出才被發現的
（「點退帳單屬合約退租收尾範疇…轉由合約領域接手」，evidence/r1b-prime-execution.json）
現有 structured routing data **無此 edge**
```

⚠️ Persona 可繼續負責回答行為；本條主張的是 **routing 需要自己可機器使用的 responsibility 契約**。

---

## G4. Enter-then-switch 不應作為正常的 candidate exploration 機制

> **若採此原則，必須有足夠的 lifecycle telemetry 驗證
> pre-entry rejection、committed entry、scope exit 與 reroute。**

**Evidence**

```text
現制的 enter-then-switch 是**正常且靜默**的 control flow：
  同一次請求內，direct entry 與分類路由各進場一次、各被判 switch 一次，最後落到通用兜底
```

**⚠️ Observability prerequisite**

```text
Current limitation:
  scope=switch does not emit a distinct facet lifecycle event
  （現有 exit 事件只有 exit_degraded 84／exit_user_cancel 1）
→ OBS-2（conversational-routing-execution／task11-data-availability-audit.md）
→ governance rule may be **unobservable after implementation**
```

⇒ 即使 G4 被採納，**現行 telemetry 無法驗證它有沒有被遵守**。

---

## Open Governance Question：explicit trigger 的 bypass authority

**不併入 G1–G4**——它是另一個 authority source，且各 source 的語義未必相同
（session continuation／damage image／transaction direct entry／classification）。

**Production fact（已實測）**

```text
trigger_facet_key
→ registry exists + enabled
→ direct Face entry
→ **no query applicability check**
```

（C4b、B′、B″ 用的正是這條路徑。）

> **Explicit product trigger 是否具有 bypass responsibility applicability 的 authority？
> 若有，哪些 trigger source 有此權限，契約如何明示？**

---

## 本 position **不決定**什麼

```text
This position does NOT decide:

- contract_closeout owns the observed query
- knowledge rows 3519 / 4657 should add 退租收尾
- responsibility authority always overrides entry authority
- all Faces must be evaluated by LLM
- candidate set must be retrieval ∪ all responsibility Faces
- trigger_facet_key must lose bypass authority
- which arbitration algorithm should be used
```

⚠️ 特別是 **all Faces must be evaluated by LLM**：本提案的方向是
**responsibility-aware candidate generation**，**不是** 21 Faces × 1 LLM call。
G2 列出的 4–7 次是 naive union 的成本上界形狀，**不得**被讀成 G2 的實作要求。

---

## Decision Record 真正需要決策的四題

```text
D1. Candidate nomination authority
    哪些 evidence 有資格把 Face 放進 candidate set？

D2. Responsibility applicability authority
    session commit 前是否必須通過 responsibility applicability？

D3. Responsibility representation
    現有 topic_scope/category 是否足夠？
    若不足，是否建立 machine-readable accepts/excludes/delegates 或等價契約？

D4. Source-specific bypass authority
    trigger／session／vision／classification 等 entry source
    哪些可以 bypass applicability，哪些不可以？
```

⇒ **D1–D4 定下來之後**，arbitration 演算法、cost optimization、pre-entry implementation
才是工程設計題。在那之前，它們都不是可以先做的實作。

---

## 可追溯性

```text
descriptive evidence   .kiro/specs/face-exit-before-grounding/research.md（§5／§7–§12）
                       evidence/r1-first-execution.json ／ r1b-prime-execution.json ／
                       r1b2-execution.json（各附 stdout log）
escalation artifact    evidence/responsibility-entry-nomination-escalation.md
observability gaps     ../conversational-routing-execution/task11-data-availability-audit.md
                       （OBS-1／OBS-2／OBS-3）
上游                   conversational-routing-execution 的 C4b（6.3 簽核：gate CLOSED）
```
