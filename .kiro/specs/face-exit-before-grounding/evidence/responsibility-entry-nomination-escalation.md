# Escalation artifact：responsibility ownership 與 entry nomination 之間沒有橋

> 2026-08-25｜語言 zh-TW｜**來源工作線：`face-exit-before-grounding`（descriptive discovery = COMPLETE）**
> 收件對象：`routing-authority-model` / **Responsibility Governance Decision Record**
> 身分：**decision input**，不是研究結論包裝成的方案。
> ⚠️ 本檔**不改動** `routing-authority-model` 的 snapshot／status／outcome，
> 也**不代填** Responsibility Governance Decision Record 的任何答案。

## 0. 開場：本線最終查到的不是原本要查的東西

> **本線原先調查「為何 Face 進場後在 grounding 前退出」，最終證實退出本身並非主要缺陷：
> 已存在且穩定接受該 query 的 responsibility owner，沒有被現行 entry nomination 所提出；
> 兩層之間不存在由 responsibility contract 驅動的 nomination bridge。**

```text
outcome                        OWNER_EXISTS_BUT_NOT_PROPOSED
RESPONSIBILITY_GAP_CONFIRMED   REFUTED
```

---

## 1. 已證實的 descriptive findings

受測 query（逐字）：**「幫我查點退帳單金額」**（sha1/16 `c0d220cc3f1d47cb`）

```text
bill_diagnosis                          stable reject   （6/6 switch，§8.1）
billing_anomaly                         stable reject   （3/3 switch，in-session context，§10）
contract_closeout                       **stable accept**（3/3 stay，in-session context，§11）

observed production entry nomination    **bill_diagnosis only**（9/9 次，§8.1＋§10.1）
entry nomination inputs                 檢索 top-1 的 knowledge `categories` ＋ 相似度門檻（0.75）
responsibility contract 參與 nomination  **none**
```

⚠️ **不得誇大成 architecture claim**：

> `contract_closeout` **並非 globally unreachable**：它存在於 `by_category['退租收尾']`，
> 該分類鍵有 11 筆 active 知識，其他適當 query 可以被提名。
> 因此本線只裁 **`OWNER_EXISTS_BUT_NOT_PROPOSED`**，
> **不裁** `OWNER_UNREACHABLE_BY_CURRENT_ENTRY_CONTRACT`。

## 2. 已排除的替代解釋（**請勿重新調查**）

```text
context truncation                 FALSIFIED       （§7.1，runtime value-flow 捕捉）
Face identity／state mismatch       FALSIFIED       （§7.2，session lineage ＋ prompt 同一性）
producer／consumer mismatch         FALSIFIED       （§7.3，正規化與消費端逐位對位）
reroute residual                   FALSIFIED       （§8.1，兩次 brain 呼叫七欄逐位元等價）
responsibility gap                 **REFUTED**     （§11，owner 確實存在且穩定接受）
ranking-only explanation           **REFUTED**     （§12.3，能提名它的證據不在候選集內，
                                                    換排序也提不出來）
metadata defect                    **NOT ESTABLISHED**
```

> `metadata defect` 維持未成立：「與本 query 同義的知識**應不應該**掛『退租收尾』」
> 本身就是待治理決定的 **responsibility allocation**，不是本線可裁的事實問題。

## 3. 確切的架構落差（目前證據能支持的**最強** claim）

> **現行 entry nomination contract 不消費 Face responsibility evidence。
> Face ownership 與 entry candidate generation 之間，
> 只有 knowledge-row 的 category annotation 這個人工維護的間接連結。**

```text
responsibility layer   persona responsibility contract（對話規則的【本輪範疇 scope】）
                       → contract_closeout accepts query
entry nomination layer retrieval top-1 → knowledge categories → category→Face index
                       → bill_diagnosis
bridge between them    **none**
唯一靜態耦合            人工寫在 knowledge row 上的 `categories`
```

⚠️ 本節**不主張**「categories 標錯了」，也**不主張**「contract_closeout 應優先」。

## 4. 升級的 normative 問題（**本線不回答**）

> **當 responsibility owner 已存在且會接受 query，但現行 entry-routing authority
> 未將其納入／選為候選時，entry nomination 應如何取得 responsibility evidence，
> 以及哪個 authority 有權決定候選集合？**

### decision boundary（明確劃出）

```text
本 artifact **不主張** entry authority 應服從 responsibility authority；
本 artifact **不主張** categories、persona rules 或 retrieval 應如何修改。
以上均屬 Responsibility Governance Decision Record 的 **normative decision**。
```

---

## 5. 可追溯性

```text
spec        .kiro/specs/face-exit-before-grounding/（requirements.md／research.md）
協議        r1-protocol-frozen.md ／ r1b-prime-protocol-frozen.md ／ r1b2-protocol-frozen.md
            （三份皆**先於各自執行** commit）
evidence    r1-first-execution.json ／ r1b-prime-execution.json ／ r1b2-execution.json
            （各附 stdout log）
上游        conversational-routing-execution 的 C4b（6.3 簽核：C4b NOT PASSED、gate CLOSED）
            ——本線的起點證據，provenance-only
```

## 6. 最終 discovery correction（本線對外的唯一版本）

> **問題已從「責任沒有 owner」修正為
> 「owner 存在，但現行 entry nomination 不讀 responsibility contract；
> 兩者僅透過 knowledge categories 間接耦合，因此本 query 的 owner 未被提出」。**
