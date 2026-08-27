---
name: config-governance-review
description: 設定治理的語義審查：讀 knowledge_base／persona 規則／conversational config，找出「結構上不一定錯、但語義上互相矛盾」的設定（category 與 responsibility 脫節、跨角色進場路徑、面向職責與知識歸屬不符），逐條產出 proposed patch ＋ reason ＋ evidence 交人裁決。**只提案，絕不寫 DB**。用於定期治理健檢、或懷疑某面向的知識歸屬有問題時。
user_invocable: true
arguments:
  - name: scope
    required: false
    description: 限定範圍（面向 key、category 名、或 kb id 清單）；省略＝全庫
  - name: flags
    required: false
    description: "--l3-only 只列語義歸屬提案；--json 機器可讀輸出"
---

# 設定治理語義審查（knowledge-config-governance Task 5）

## 這個 skill 的邊界——先讀這段

```text
✅ 讀設定、找語義矛盾、產出 proposal ＋ reason ＋ evidence
❌ **絕不寫 DB**（不 UPDATE、不 INSERT、不 DELETE、不呼叫 fix_config.py --apply）
❌ 不決定「這個 query 應該由誰擁有」——那是產品語義，只能提案
```

變更的正當路徑固定是：

```text
本 skill 提案 → 人裁決 → migration／admin action 寫入 → make audit-config 機械複驗
```

⚠️ 為什麼禁止自己寫：替某筆知識加一個面向標籤**看起來**像資料清理，
實際是在回答「這個 query 應該由誰負責」。`routing-authority-model` 整條線
就是卡在「誰有資格說 Face X 負責」而 BLOCKED——skill 不得繞過那個未決問題。

## 執行順序

### 第 0 步：先跑機械掃描，不要重做它的工作

```bash
make audit-config
```

L1／L2 由掃描器負責（schema、缺欄位、指向不存在的目標）。
**本 skill 只處理它報不出來的那一層**：規則寫得出來就該進掃描器，寫不出來才輪到人看。
⚠️ 若 audit-config 有未清的 L1，先請人處理完再做語義審查——
在結構還壞著的資料上談語義，結論不可信。

### 第 1 步：讀三份事實（唯讀）

```sql
-- ① 面向設定（含職責宣告）
SELECT id, generation_metadata->'conversational_config'
FROM knowledge_base WHERE category = '對話規則' AND is_active;

-- ② 知識的歸屬標記
SELECT id, question_summary, categories, target_user, action_type, api_config
FROM knowledge_base WHERE category IS DISTINCT FROM '對話規則' AND is_active;

-- ③ 契約（機器可讀的規則來源）
--    rag-orchestrator/database/config_contracts.yaml
```

### 第 2 步：找這四類語義矛盾

```text
S1 category 與 responsibility 脫節
   知識掛在面向 A 的 category，但該問句的實際職責由面向 B 的 persona 規則宣告
   （例：「點退帳單」掛在「條件診斷：帳單」，而點退的職責寫在「退租收尾」）

S2 跨角色進場路徑
   知識的 target_user 與面向的角色不相容（b2b 業者問句進 b2c 租客面向）
   ⚠️ config_for_category **不比對 target_user／mode**——結構上不會擋，只能靠語義看出來

S3 面向職責宣告與 delegates 不一致
   persona 規則的自然語言說「X 交給 Y」，但 responsibility.delegates 沒有那條邊（或相反）

S4 同義知識分屬不同面向
   語義幾乎相同的兩筆知識掛在不同 category ⇒ 使用者問法微調就換面向、答案不一致
```

### 第 3 步：每條提案的固定格式

```text
[S?] <一句話說矛盾在哪>
  等級      L1／L2／L3（**L3 必須明寫「這是產品語義決定」**）
  證據      kb id、category、target_user、persona 規則原文（**逐字引用，不轉述**）
  提案      具體要改什麼（欄位＋新舊值）
  代價      改了會影響哪些進場路徑；不改會怎樣
  反對意見  這條提案可能錯在哪（**必填**——寫不出來代表證據不足）
```

⚠️ `反對意見` 是硬性欄位。這條線已經三次因為「看起來合理」而做出後來被推翻的判斷；
提案若說不出自己可能錯在哪，就是還沒查夠。

## 不得做的事

```text
❌ 由 git 作者／實作者／文件撰寫者推論誰該負責
❌ 把「查無證據」寫成「不存在」——沒有正對照的否定結論一律不採
❌ 以相似度／category 重編碼冒充責任判定（routing-authority-model 已 REFUTED 三次）
❌ 一次提案超過 10 條——超過代表沒有分優先序，人會直接略過整份
```

## 產出

一份 markdown 提案清單，落在 `.kiro/specs/knowledge-config-governance/proposals/`，
檔名帶日期。**不修改任何既有檔案、不動 DB。**
