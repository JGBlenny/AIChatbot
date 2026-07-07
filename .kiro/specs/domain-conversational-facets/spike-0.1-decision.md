# Task 0.1 spike 決策記錄：混合 grounding 走 system_md（選項 A/B）

> 建立：2026-07-01｜對應：tasks.md 0.1｜需求：R3｜設計：design.md D3（預算閘）
> 目的：把合約基底架構壓成 append，量測「base + append 是否壓得進 system_md 預算且仍夠 LLM 判斷」，據此決定走**選項 A**（system_md 常駐注入）或 **fallback 選項 B**（knowledge_ref 收斂時載）。

## 一、預算量測（實測）

| 項目 | 字元數 | 依據 |
|---|---|---|
| 通用 base（`系統脈絡`，id 3622，`target_user IS NULL`） | 1377 | design.md D2/元件1（既有共用底座） |
| 分隔符 `\n\n` | 2 | 疊加串接 |
| **合約 append（本 spike 精簡版，注入本文）** | **1368** | `knowledge-contract-base.append.md`「---」之後 |
| **疊加後 system_md 合計** | **2747** | base + sep + append |
| 硬上限 `MAX_CHARS_WARN`（`system_context.py:12`） | 4500 | 既有告警門檻 |
| 對 ~3900 設計目標 | **PASS**（餘裕 1153） | design.md D3 |
| 對 4500 硬上限餘裕 | **1753** | 僅用 61% |

> 修訂（2026-07-01，後續檢視）：**違約金／滯納金「金額試算框架」已從注入本文移除**（目前不支援金額試算；且經查合約 formatter 未把 `late_fee_percent`/`penalty_type` 等客製欄位攤進 grounding → 常駐框架＋範例數字反致幻覺）。改以一句 guardrail：實際金額一律以 API 現值為準，被問試算而現值缺→導專人、不自算。故 append 由 1593→**1368** 字。未來要支援金額試算時，連同「formatter 攤出客製欄位」（Fix B）一起加回框架。

> 註：注入僅計 append 檔「---」分隔線之後之本文；前置備註（用途/性質/落地）不入注入。base=1377 沿用 design.md D2 對現有 id 3622 之量測。

## 二、判斷力覆蓋檢查（append 是否仍夠 LLM 判斷）

spike 精簡後仍完整保留 R3/R5.1 判斷所需之全部要素：

- ✅ **status vs bit_status** 兩欄位語義區分 + `bit_status` 須逐位元拆解（非單一整數查表）。
- ✅ **12 里程碑 × 4 階段** 對照表（值/里程碑/階段/白話俱全）。
- ✅ **各階段下一步 / 能做什麼** + 可否動作前提（點交/點退/提前解約）——「判斷」核心。
- ✅ 用詞校正：**點交＝交屋、點退＝退租**（對齊真碼，糾正舊 mock）。
- ⏸️ **違約金／滯納金金額試算框架**：目前不支援，故不放常駐脈絡（僅留 guardrail：以現值為準、缺值導專人）。見上方修訂。
- ✅ **續約父子鏈 + 同名多份**處置（`father_id`、title 重複、列候選）。
- ✅ **關鍵欄位詞彙表**。

精簡手法：去除草稿的教學語氣與重複散文、合併條列、表格白話欄壓縮；**未刪任何一條事實或規則**，僅改寫更緊湊。完整草稿保留於 `knowledge-contract-base.md` 供業務覆核。

## 三、決策

**採用選項 A：合約基底架構走 per-領域 system_md（append），常駐注入。**

- 疊加後 2747 字，遠低於 4500 硬上限、亦低於 ~3900 設計目標，餘裕充足（後續其他領域 append 亦有空間）。
- 判斷力要素全數保留，符合 R3「LLM 有領域框架可判斷而非複述」。
- 混合 grounding 自然發生於 `synthesize(grounding=API 現值, system_md=base+合約架構)`，`_ground_by_api` **零改**（design.md D3）。

**Fallback 選項 B（knowledge_ref 收斂時載）觸發條件＝append > ~2500 仍需完整 → 未觸發，不啟用。**

## 四、對後續任務的影響

- **task 1.x（per-領域 system_md 疊加載入）**：照設計元件1 實作（走 A）。
- **task 2.1 / 2.2 / 2.4**：混合走 system_md，如常實作。
- **task 2.3（`grounding_scope.knowledge_ref` escape hatch）**：標為 `- [ ]*` 可延後；因走 A 而**本案不需實作**（escape hatch 之接口仍可保留為向後相容選項，但不作為合約首案交付路徑）。
- **task 4.2（合約系統脈絡種子）**：以 `knowledge-contract-base.append.md`「---」後之本文落成 `category='系統脈絡'`、`target_user=[property_manager]` 之列。

## 五、產出

1. `knowledge-contract-base.append.md`——精簡 append 版（注入本文 1368 字）。
2. 本決策記錄。
