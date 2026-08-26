# 需求規格：knowledge-config-governance

> 2026-08-26 立案｜語言 zh-TW
> 業主定性：這是**橫向治理層**，不是對話流 feature、也不是 mock fidelity——
> 是所有 Face／Knowledge 共用的**資料品質層**。
> 立案理由：DB 裡的 knowledge／conversational config 由不同時期、不同人、不同規則累積，
> 若每碰到一筆就順手修一筆，最後仍是 patch。

## 作用域

```text
在   knowledge_base（含 category='對話規則' 的 conversational config）、
     form_schemas、vendor_sop_items 等**設定資料**的結構與一致性
不在 對話規則的措辭品質、檢索排序、面向的產品語義（誰該負責哪個 query）
```

## 三級分類（**界線就是本 spec 的核心**）

| 等級 | 類型 | 能不能自動修 |
|---|---|---|
| **L1 Structural** | schema、缺欄位、非法 key、orphan、指向不存在的目標 | ✅ 可決定性 autofix |
| **L2 Consistency** | 同類 config 形狀不一致、persona／output contract 不一致 | ✅ **但需明確規則**，規則寫不出來就降 L3 |
| **L3 Semantic ownership** | category／responsibility／delegation **誰應該負責** | ❌ **只能提案，人裁** |

⚠️ L3 不得自動修的理由已由前例證實：替 kb3519 加「退租收尾」看起來像資料清理，
實際是在回答「**這個 query 應該由誰擁有**」——那是產品語義，
而 `routing-authority-model` 整條線就是卡在「誰有資格說 Face X 負責」而 BLOCKED。

## Requirement 1：契約必須是**機器可讀**的單一來源

- 1.1 系統 SHALL 以一份 machine-readable registry 描述設定契約
  （欄位必填性、值域、跨表指向），而非散落在 migration／測試／steering／persona rules。
- 1.2 契約 SHALL 支援**條件式**規則（例：`topic_scope.mode=='category'` 時 category 必填；
  role-routed 的 `presales` 無 topic_scope 屬合法變體）——
  ⚠️ 不得用一條扁平的「全部必填」把合法變體判成錯誤（那會製造誤報，讓人學會忽略稽核）。

## Requirement 2：全庫掃描與報告

- 2.1 `make audit-config` SHALL 掃描全庫並逐條輸出違規，含**表、列 id、契約條款、實際值**。
- 2.2 報告 SHALL 依 L1／L2／L3 分段；**L3 一律標為「提案，待人裁」**，不得混入 FAIL。
- 2.3 掃描 SHALL 為唯讀，且不依賴應用程式啟動。

## Requirement 3：修正必須可預覽、可回退

- 3.1 `make fix-config --dry-run` SHALL 只輸出將要執行的變更，**不寫入**。
- 3.2 實際寫入 SHALL 產生對應的 rollback SQL。
- 3.3 SHALL NOT 自動修 L3；L3 的產出只有 **proposal ＋ reason ＋ evidence**。

## Requirement 4：Skill 是 reviewer，不是 autonomous fixer

- 4.1 Skill SHALL 讀 knowledge／persona／config，找出語義不一致並產生
  **proposed patch ＋ reason ＋ evidence**。
- 4.2 Skill SHALL NOT 直接寫 DB。真正的變更一律走 migration／admin action，
  且先過 validator 的機械檢查。
- 4.3 Skill 的提案 SHALL 標明它屬 L1／L2／L3；L3 提案必須明寫「這是產品語義決定」。

## Requirement 5：稽核疲勞防制

- 5.1 誤報 SHALL 被視為缺陷：一條規則若對合法變體報錯，**修規則，不是叫人忽略**。
- 5.2 豁免 SHALL 帶理由（沿用 `check_invariants.sh` 的維護準則第 2 條）。
- 5.3 WARN 清單只准變短；變長要有立案紀錄。

## 非目標

```text
· 不重建知識內容、不改措辭
· 不決定任何 Face 的責任歸屬（那是 routing-authority-model 的題）
· 不取代 make audit 的既有八條不變量——本層是它的細粒度延伸
```
