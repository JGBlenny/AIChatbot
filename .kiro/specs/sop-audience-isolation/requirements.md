# ⚠️ 本 spec 已撤銷（2026-07-05，使用者裁定）

撤銷原因：核心前提被兩次質疑推翻——①SOP 內容體系全為租客服務流程（零 JGB 系統內容）；②生產隔離本已存在：jgb2 後台呼叫帶 mode='b2b'（useChat.ts:62），chat.py:1633 b2b 模式不走 SOP。4 實彈與「房間沒電」皆為測試 harness 未帶 mode（預設 b2c）的 artifact。

轉出項：P0 錨點單發防呆（真 bug）、e2e harness 補 mode='b2b'、memory/runbook 改判更正、b2b 知識補強（A7 工作流/電費六模式——與 SOP 無關的真缺口）、縱深防禦（b2c+property_manager 矛盾組合警示）記 G 掛帳。jgb2 真相三題研究成果保留於 research.md 供知識產製。

---

# 需求規格：sop-audience-isolation（SOP 檢索受眾隔離）

> 建立時間：2026-07-04
> 階段：requirements-generated
> 語言：zh-TW
> 背景：`vendor_sop_items` 無 target_user 欄，SOP 檢索兩條路徑（chat.py `_retrieve_sop`／sop_orchestrator）皆零受眾意識——租客向 SOP 攔截業者問句給受眾錯位回答。
> 實彈證據：五域大抽驗（2026-07-04）20 題中 4 題中招（SOP 1256 信用卡繳租／1193 退租結算／1285 包電方案／1268 統編收據，全以「您的管理師」口吻回覆業者）；第一案為 IoT e2e「房間沒電」被修繕 SOP 1166 攔截。
> 資料現況（實測）：全庫 407 筆、3 vendor（vendor 2 佔 328）；370 筆（91%）帶租客向口吻特徵——SOP 本質即「租客問業者」的標準回覆，故回填策略為「預設 tenant、白名單挑例外」。

## 簡介

在不重寫 SOP 內容、不動管理後台 UI 的前提下，為 SOP 體系補上受眾維度：schema 加欄、407 筆回填（人工閘門）、檢索兩路徑按請求角色過濾、業者向補位知識接住被過濾的問句。過渡安全原則：**未標注（NULL）視為通用**，租客側行為零回歸。

## 名詞定義

- **target_user（請求側）**：chat API 請求的角色參數，現行值域 `tenant`／`property_manager`／`prospect`（沿 knowledge_base 慣例）。
- **tenant-only SOP**：target_user=['tenant'] 的 SOP——只服務租客問句，業者/售前請求不得命中。
- **通用 SOP**：target_user 為 NULL 或含多值——所有角色可命中（過渡期預設語義，避免未回填先破壞）。
- **受眾錯位**：SOP 內容的預設聽者（如租客）與實際提問者（如業者）不一致，導致口吻與指引對象錯誤（「您的管理師」對業者說）。
- **補位知識（定位修正 2026-07-05）**：⚠️ 非「SOP 的業者版」——SOP 為租客服務域，業者問句本來就不在其範圍。這 4 題是 **knowledge_base 一直欠著的 b2b 知識缺口**（收款方式支援範圍/電費設定/統編開立本該存在），SOP 越界只是用錯的答案把「查無」遮住了；過濾修好後缺口裸露，故知識須先於過濾部署。知識歸屬走既有領域分類（帳務/合約），不造「SOP 補位」新概念。
- **SOP vs 知識比分**：chat.py 現行機制——SOP 與知識同時檢索後比相似度分數決定誰接手；本 spec 的過濾必須發生在比分**之前**。

## 範圍

### 範圍內
- `vendor_sop_items` schema 加 target_user 欄（冪等 migration）。
- 407 筆回填：規則預判（口吻特徵）＋人工閘門審白名單例外（~37 筆無特徵者逐筆）＋回填 migration。
- SOP 檢索兩條路徑（chat.py `_retrieve_sop`→`retrieve_sop_hybrid`、`sop_orchestrator`→`retrieve_sop_by_query`）的受眾過濾。
- 業者向補位知識 4 筆起（收款方式支援範圍／退租結算業者側／電費收法設定／代開統編發票），其中電費收法與統編開立鏈需先盤 jgb2 真相。
- 回歸三組（4 實彈改判／租客側抽樣零回歸／「房間沒電」改判）＋五域全套零回歸。
- 部署步驟併入統一部署 runbook。

### 範圍外
- SOP 管理後台 UI（新增/編輯表單的 target_user 欄位輸入——治理註記交後台團隊，另案）。
- SOP 內容口吻改寫（tenant-only 判定後內容照舊）。
- `platform_sop_templates` 體系（若盤查確認同構缺口，記入 gap 分析與掛帳，不在本 spec 修）。
- 不改五域面向/售前/form_fill 任何行為。

## 需求

### Requirement 1：SOP 受眾標注（schema＋回填）

**使用者故事**：作為維護者，我要每筆 SOP 都有受眾標注，讓檢索能區分「這是講給誰聽的」。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 於 `vendor_sop_items` 提供 target_user 多值欄位（與 knowledge_base 同型別語義），migration 冪等可重跑。
2. THE SYSTEM（回填流程）SHALL 以「預設 tenant」為基準策略，僅無租客向口吻特徵者（實測 ~37 筆）進人工逐筆審表，判定為 tenant／property_manager／通用。
3. THE SYSTEM SHALL 於回填執行前經人工閘門確認審表（含 4 實彈 SOP 與修繕 1166 的判定結果明列）。
4. THE SYSTEM SHALL 使回填不修改任何 SOP 的內容與 embedding（只動 target_user 欄）。
5. WHERE SOP 未標注（NULL），THE SYSTEM SHALL 視為通用（所有角色可命中）——保證未回填的 vendor 行為不變。

### Requirement 2：檢索受眾過濾

**使用者故事**：作為業者，我問系統問題時，不要收到寫給租客看的標準回覆。

#### 驗收標準（EARS）
1. WHEN 請求 target_user 為 property_manager 或 prospect，THE SYSTEM SHALL 於 SOP 檢索時排除 tenant-only SOP；通用 SOP 不受影響。
2. WHEN 請求 target_user 為 tenant，THE SYSTEM SHALL 維持現行命中集合（零回歸——過濾語義為「排除不相容」而非「僅取同角色」）。
3. THE SYSTEM SHALL 於 SOP vs 知識比分之前完成過濾——被過濾的 SOP 不得參與比分（否則高分 SOP 仍會壓過知識）。
4. THE SYSTEM SHALL 於兩條檢索路徑（chat.py 直接檢索與 sop_orchestrator）套用同一過濾語義，單一實作點不重複邏輯。
5. WHERE 請求未帶 target_user，THE SYSTEM SHALL 維持現行行為（不過濾）——向下相容。

### Requirement 3：業者向補位知識

**使用者故事**：作為業者，被過濾掉租客向 SOP 後，我的問題應由正確受眾的知識回答，而不是變成「查無資料」。

#### 驗收標準（EARS）
1. THE SYSTEM（產製流程）SHALL 產出補位知識至少 4 筆：業者收款方式支援範圍、退租結算業者側口徑、電費收法設定、代開統編發票流程——target_user=property_manager、business_types=system_provider。
2. THE SYSTEM SHALL 於產製前以 jgb2 真碼盤定兩題真相：金流支援的支付方式集合（信用卡是否在列）、電費計收模式設定位置與發票統編開立鏈〔以 file:line 為準，客服口徑錯誤處修正〕。
3. THE SYSTEM SHALL 使補位知識經人工閘門後入庫（沿知識工程慣例：理解情境、短關鍵字 question、answer 先述情境）。
4. WHERE 過濾後某業者問句仍無知識可接，THE SYSTEM SHALL 走既有誠實 fallback（導客服），不虛構——此為可接受的過渡態並記入缺口清單。

### Requirement 4：回歸與零回歸

**使用者故事**：作為維護者，我要證明錯位修好了、而租客側一分未壞。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 通過 4 實彈改判回歸：業者問「信用卡繳租／押金退還／電費收法／統編發票」不得再命中租客向 SOP，且由補位知識或誠實 fallback 接手。
2. THE SYSTEM SHALL 通過租客側零回歸：抽樣既有租客向 SOP 命中案（含 4 實彈同題租客版），tenant 請求命中集合與過濾前一致。
3. THE SYSTEM SHALL 通過「房間沒電」改判驗證：property_manager 請求不再被修繕 SOP 1166 攔截（由電表排障錨點接手或誠實 fallback）。
4. THE SYSTEM SHALL 通過五域面向/售前/form_fill 全套測試零回歸（unit＋integration＋e2e）。
5. THE SYSTEM SHALL 具備 seed/單元層防呆：過濾語義（tenant-only 排除、NULL 通用、tenant 請求不縮集）以測試釘死。

### Requirement 5：治理與部署

**使用者故事**：作為維護者，我要新增 SOP 時受眾標注不再缺席，且部署與其他五 spec 一批走。

#### 驗收標準（EARS）
1. THE SYSTEM SHALL 於部署文件記載治理註記：後台新增 SOP 時應標注 target_user（UI 欄位另案；未標注前新 SOP 落 NULL=通用，不會錯攔但也不隔離）。
2. THE SYSTEM SHALL 將 migration＋回填＋補位知識匯入併入統一部署 runbook（依序、冪等、含煙囪驗證句：4 實彈之一＋租客對照句）。
3. WHERE `platform_sop_templates` 盤查確認同構缺口，THE SYSTEM SHALL 記入掛帳清單（不在本 spec 修）。
