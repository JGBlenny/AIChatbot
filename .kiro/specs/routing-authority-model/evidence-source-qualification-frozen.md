# Evidence-source qualification（E1–E6）：**凍結於挑選任何 candidate 之前**

> 2026-08-24｜語言 zh-TW｜業主裁定：D1／D3 **均維持 member-shape discovery**；
> 下一步是**跨 D1/D3 的 runtime-binding applicability evidence inventory**，
> **不是**直接設計下一版 member。
> 前置：`g1-audit-result.md`（G1 **FAIL**，B／C 退場，`6242d62`）
> **裁定：APPROVE WITH 1 MUST-FIX（已補）**——F-1～F-5（搜尋空間／程序／記錄／停止規則／分開統計）
> 已凍結於執行之前；第四種結局措辭已收窄；E5 補上「qualified ≠ routing authority」對稱條款。

## 這一輪問的問題（與上一輪根本不同）

```text
上一輪（B／C，已死）
  先描述「所有什麼樣的 query 屬於 Face X」
  → 需要 closed semantic ontology
  → G1 FAIL

這一輪
  對眼前這個 candidate Face X，
  有沒有某個 **runtime-binding fact** 可以證明／反證這次 entry 的正當性？
```

> **本輪 NOT REQUIRED：totality。**
> 這是與 G1 最大的差別。我們不再要求「列出所有 operation」；
> 可以接受「這個 query 明確帶了一個實際存在、可解析的 bill identifier」——
> 即使世界上還有很多其他 query shape，**這個 fact 本身仍然成立**。

⚠️ 因此本輪**允許 Face 集合本身是 open-world**。

## G1 到底殺掉了什麼（定性，避免下一輪誤用）

```text
被殺掉的是：先建立一套**全域、有限、封閉**的 responsibility dimensions，
            再把所有 Face applicability 投影進這套代數。

失敗不在「三維選錯」，而在更上游：
  problem_state      沒有全集 authority
  operation_class    runtime 邊界本身不是封閉 registry
  Face set           DB 可新增，open-world
```

**因此明令禁止**：

```text
❌ + target ／ + lifecycle_stage ／ + payment_method ／ + actor …
   —— 直接違反 G1 已得到的答案。B／C 維持退場。
```

⚠️ **但「Face 是 open-world」不等於「Face contract 做不了」**。
它排除的是**需要事先知道全部 Faces／全部責任類型才能成立的 global closed taxonomy**。
未來仍可能存在：

```text
每個新 Face → 自己攜帶一份可執行的、**局部的** applicability proof mechanism
```

那不需要全世界 Face 集合封閉。
⚠️ **但這種 local proof 是否存在、能否取得新資訊，目前完全沒有證據**——故本輪只做 inventory，不寫 member。

## 為何不是轉去 D2、也不是重開 D1

```text
D2  仍有未解問題：目前真正證實有資訊價值的是 query × KB ／ query × Face applicability，
    **尚無證據**說 query-alone semantics 足以承擔 routing authority。
    從 D3 失敗跳到「那就做 intent model」**沒有因果依據**。

D1  re-entry condition 未滿足：必須先提出**不同於 text specification ＋ generic evaluator**
    的 routing-owned information shape，目前還沒有。
```

---

## ⚠️ Prior-exposure declaration（**本輪不能宣稱 blind**）

G1 的協議可以誠實宣稱「撰寫時尚未讀取任何 source 內容」。**本輪不行**，必須據實揭露：

> 執行 G1 期間，我已讀過下列 production 內容。本協議在**已知這些事實**的情況下撰寫。

```text
jgb2（master 5eaebb7f0a）
  app/Bill.php 的類別常數區、app/BillActivityLog.php、
  routes/web.php 的 bill 區段、BillController::batch 的 switch 分派、
  bill_activity_logs 建表 migration
AIChatbot（rag-orchestrator）
  services/conversational_config.py 的設定層 docstring 與 CONFIG_CATEGORY
  services/conversational_engine.py 的 entity_noun 使用點
  services/jgb_system_api.py 的方法清單（僅方法名層級）
另見 incidental-observations.md OBS-1
```

**因此本協議加一條防護**：

```text
上述已曝光項目 **MUST NOT** 因為「已經看過、印象深刻」而取得 candidate 的優先地位。
它們與任何其他 source 一樣，**必須逐條通過 E1–E6**，且其 disposition
MUST 記錄「本項屬 prior-exposure 清單」，供事後判斷是否有選擇偏誤。
```

⚠️ 我**不能**假裝這輪是 blind 的。能做的是把污染面攤開、並讓它可被檢查。

---

## E1–E6：合法 evidence source 的資格條件（業主指定，**凍結**）

### E1｜Runtime binding

> 它是**系統真的 enforce** 的事實，不是 observed list／docstring／naming convention。

⚠️ 直接沿用 G1 學到的教訓：class constant 不是 enforcement；
「文件寫了」不是 enforcement；「目前搜到這些」不是 enforcement。

### E2｜Pre-entry availability

> 它 MUST 在 **Face irreversible entry ／ early-return 之前**就能取得。

⚠️ 取不到就不是 applicability evidence，是事後解釋。

### E3｜Candidate relevance

> 它 MUST 真的對 **Face X 的 applicability** 有語義，
> 不是只有「系統裡存在這個東西」。

### E4｜Information independence

> 它 MUST NOT 只是 **similarity／category 的重新編碼**（R1 §1.2 已實測 REFUTED 過該形態）。

### E5｜No false closed-world inference

> source 沒有證據時，只能得出 **unknown ／ abstain**。
> **除非該 source 本身具 totality**，否則**不得**推論「不存在」。

⚠️ 本條是 G1 §5 的延續，也是本輪避免重製 precision-first collapse 的關鍵。

### E6｜Provenance

> MUST 說清楚：**誰產生這個 fact、誰擁有它、它的 runtime semantics 是什麼**。

---

## 研究方向：**positive proof**，不只是下一個 veto

已連續三次觀察到同一形態的 **precision-first collapse**：

```text
v1 lexical candidate     大量 abstain
Q2 relevance gate        0 false allow ／ 高 false reject（44% 誤殺）
Round 1 D1／D3           0 false allow ／ 17 false reject
```

這足以讓本輪至少**問一個不同的問題**：

> 我們是否一直試圖證明「不該進」，
> 而 production 更容易提供的其實是「為什麼這次確實該進」的**正向**證據？

概念形態（**尚未成立**）：

```text
candidate Face ＋ 某個 machine-bound entity／action／state evidence
→ positive applicability proof
```

**關鍵語義規則**（避免重造 collapse）：

```text
沒有 proof  ≠  not_applicable
沒有 proof  =  unknown
```

⚠️ 「我沒看懂 → 所以不准進」正是前三輪的病灶。本輪**不得**把 abstain 當成拒絕。

⚠️ **另一邊同樣要守住**：**positive proof 本身不自動取得 routing authority。**

```text
E1–E6 全過  →  最多得到：QUALIFIED applicability evidence source
             ✗ 不等於：Face SHALL enter
```

後者仍須回到 **R2 ／ authority design** 回答，不在本輪。

⚠️ **這只是研究方向**：本檔**不宣稱** positive-proof architecture 已成立。

---

## ⚠️ 補凍結（業主 must-fix）：搜尋空間、程序、記錄與停止規則

E1–E6 只回答「某個**已找到**的 source 合不合格」，回答不了
「**你憑什麼說該找的已經找完？**」。在已有 prior exposure 的情況下，缺這一節會使
最終的負面結論證據力不足，或使正面結論停在第一個好看的 candidate 上。

### F-1｜AUDITED SCOPE（**凍結於執行之前**）

本輪搜索範圍＝**一次 Face routing decision 發生時，其前後可觸及的 production authority surface**：

```text
L1 對話入口 seam        rag-orchestrator/routers/（請求進入、路由分歧、early-return 點）
L2 檢索與決策層          services/decision_layer.py、檢索管線、面向進場判斷
L3 面向設定／註冊        services/conversational_config.py、面向設定的**儲存結構**
                        （knowledge_base 的欄位／約束層級，**非**知識內容）
L4 對話引擎狀態          services/conversational_engine.py、session／state 的持久化結構
L5 平台 API client 面    services/jgb_system_api.py、services/jgb/*
L6 平台 authority 面     jgb2：routes/api.php 的 External API 契約、request validation、
                        DB migration 的 constraint／欄位型別、model 的 cast／狀態機
L7 身分與呼叫端斷言      role_id／user_id／mode／target_user 的取得與驗證路徑、API 金鑰驗證
L8 chatbot 自身持久層    rag-orchestrator 的 migration／schema constraint
```

**明確在 scope 外**（列出以免被誤讀為已查）：

```text
✗ 知識內容本身（KB rows 的文字）——那是 S5 型，非 runtime binding
✗ 前端／後台 UI 程式碼
✗ 尚未上線的分支功能（preview-only 未進 master 者，若遇到須標記為 out-of-scope）
✗ 第三方金流／發票供應商內部
```

⚠️ **scope 覆蓋範圍的限度必須誠實承認**：本 scope **未**證明自己覆蓋了
「整個 relevant production authority surface」。因此第四種結局的措辭依業主裁定收窄（見下）。

### F-2｜DISCOVERY PROCEDURE（**系統性尋找，不靠記憶**）

每一層 MUST 以**來源類別**逐項掃過，而非「想到什麼查什麼」：

```text
① entry seams              進場／early-return／不可逆點
② API registries           對外契約、路由、client 方法面
③ state machines           狀態常數、轉移條件、生命週期
④ DB constraints           enum／check／NOT NULL／FK／unique／欄位型別
⑤ request schema           validation rule、必填參數、型別強制
⑥ session state            會話持久化的欄位與其寫入點
⑦ caller assertions        呼叫端宣稱的身分／模式／角色及其驗證
⑧ execution bindings       實際綁定到某個實體／動作的執行時事實
```

⚠️ 每一層 × 每一類別 MUST 留下記錄：**查過但無所獲**也要寫，
否則無法區分「沒有」與「沒查」。

### F-3｜RECORD-ALL RULE

進入 qualification 的**每一個** source MUST 留下：

```text
source                 可 grep 的符號／檔案位置
runtime semantics      它在 runtime 實際保證什麼
discovered_from        L? × 類別?（如 L6 × ④ DB constraints）
prior_exposed          true ／ false
E1–E6                  逐條判定
disposition            QUALIFIED ／ REJECTED ／ INSUFFICIENT_EVIDENCE
reason                 REJECT／INSUFFICIENT 須指出是**哪一條**不成立、依據為何
```

### F-4｜STOPPING RULE

```text
MUST 完成 F-1 凍結 scope × F-2 全部來源類別的 inventory 後才可收束。
❌ 找到第一個 QUALIFIED source **不得**提前停止。
❌ 已知位置查完沒過 **不得**直接宣稱「production 沒有」。
```

### F-5｜分開統計（業主指定）

最終報告 MUST 把兩組**分開**呈現：

```text
prior-exposed sources     QUALIFIED ／ REJECTED ／ INSUFFICIENT
newly-discovered sources  QUALIFIED ／ REJECTED ／ INSUFFICIENT
```

⚠️ 目的**不是**比較準確率，而是讓人看得出**結果是否完全由先驗曝光項目主導**。

---

## Disposition（每個 source 逐條給，三值）

```text
QUALIFIED              六條全過，且逐條附證據
REJECTED               任一條明確不成立（須指出是哪一條、依據為何）
INSUFFICIENT_EVIDENCE  無法判定（不得預設倒向 QUALIFIED 或 REJECTED）
```

⚠️ 每條 disposition MUST 附：來源位置（可 grep 的符號／檔案位置）、
E1–E6 逐條判定、是否屬 prior-exposure 清單。

## 本輪的輸出限制（越界即為協議違反）

```text
只輸出：source inventory ＋ 逐條 E1–E6 disposition ＋ provenance

❌ 不設計 member（不論 D1、D3 或組合）
❌ 不宣稱 positive-proof architecture 成立
❌ 不改任何 family disposition（D1／D3 皆維持 INSUFFICIENT_EVIDENCE）
❌ 不重開 B／C，不新增 dimension
❌ 不動 production：不改檔、不進 seam、不動 Face config schema／flag／manifest
❌ 不產新測資、不改 matching ruler（0.058928 仍凍結未用）
❌ 不重跑 Round 1 cohort（burned）
```

## 結果如何決定下一步（**事前綁定，不看到結果再選**）

```text
qualified source 主要在 routing／request 側
  （query 解析出的 binding／caller／request state／structured execution demand）
  → 可能給 **D1** 新 shape

qualified source 主要是 Face 自己可證明的 executable facts
  （Face X 綁定的 API／action、可查的 entity／state、machine-enforced precondition）
  → 可能給 **D3** 新 shape

兩側都有
  → demand proof × offer proof，**可能**產生 D1+D3 組合 member
  → D4（共同 authority envelope）在那之後才有資格進場

**完全沒有 qualified source**
  → 結論措辭**收窄為**（業主裁定）：
    **在事前凍結且已完成的 audited scope（F-1）內，沒有 qualified source。**
  → ⚠️ **不得**寫成「production 沒有」——除非 audited scope 本身能證明
    覆蓋整個 relevant production authority surface，而本輪**不能**如此宣稱。
  → 在該收窄措辭下，它才構成「需要新增 first-class authority source／新產品語義」的證據
```

⚠️ **現在不預選**。

## 這一輪要避免的失敗模式（寫在最前面，不是事後檢討）

```text
❌ G1 FAIL → 想一個更聰明的 schema → 再跑一次
✅ G1 FAIL → 問「系統在一個具體 routing decision 發生時，
             究竟握有哪些**真正被 runtime 約束**、能構成 applicability 證據的事實？」
```

> 若連這批事實都找不到，**那才是**需要新增 first-class authority source 的證據，
> 而不是又靠一份更漂亮的 taxonomy 補洞。
