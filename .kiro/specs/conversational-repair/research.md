# 研究記錄：conversational-repair

> 建立時間：2026-07-11
> 發現流程：整合導向（三路對碼盤查已於 gap-analysis.md 完成——引擎交易擴充點／照片辨識與 Step 0.5／預填 API・配置・進場・埋點）。本文件收斂六個設計待決事項。

## 摘要

### 關鍵發現（承自 gap-analysis，對碼證實）
- Vision 辨識已輸出 `suggested_category/item/reason/emergency`（含信心度、分類樹注入 prompt）——推斷＝接線非新建
- 執行通道現成：`_ground_by_api`→`execute_api_call`，formatter 有寫入型端點專屬分支；半交易風險零
- 插點 A（pending_candidates＋三級比對）可直接承載多租約選擇與推斷退化候選
- 面向配置 jsonb 任意擴鍵；分類路由進場可複用
- 真缺口：租客租約物件無直達 API（G1）、引擎無 image 通道（G2）、confirm 語義（G3）、直達參數（G5）

## 六項設計決策（本階段定案）

### 決策 1：G1 租客物件介面形狀——新 mock 方法先定契約
**選項**：A 等 jgb2 端點；B 複合查詢（summary＋逐筆驗證）；C **新增 `get_tenant_contracts(role_id, user_id)` mock 方法定契約，真端點列 E 級依賴/J 清單（選定）**。
**契約**：`{success, data:[{contract_id, estate_id, estate_title, display_address, room}]}`——雙證進、租約物件清單出。0 筆→誠實降級（「請與管理師確認租約狀態」）；1 筆→estate 為推斷槽位；N 筆→插點 A 候選。
**理由**：mock 先行是本 repo 既定模式（E1 同款）；介面形狀由使用場景決定後拿去跟 jgb2 談，避免被動等待。

### 決策 2：confirm 呈現＝文字摘要＋quick_replies
摘要（物件/設備/狀況/急迫性逐行）＋三顆 quick reply：「✅ 確認送出」「✏️ 我要修改」「❌ 取消」。同意判定＝quick reply value **或** brain 判定的明確肯定（「好」「送出」）；修改與取消同理雙路。
**理由**：quick_replies 是既有回應契約欄位、Web 前端已渲染、LINE 未來直接映射；純文字判定單靠 brain 有誤判風險，按鈕給確定性路徑（與觸發語彙「越明確越決定性」原則一致）。

### 決策 3：推斷信心門檻＝沿用 0.7 前例
Vision `confidence ≥ 0.7` → 推斷槽位（確認型，出現在摘要）；`< 0.7` → 退化為 2-3 候選選一輪（R2.4，重用插點 A）。門檻進面向配置（`grounding_scope.inference_confidence`，預設 0.7）可調不改碼。
**理由**：form_manager `_match_category_suggestion` 既有 0.7 門檻（form_manager.py:1649），沿用避免兩套標準。

### 決策 4：直達面向參數＝`trigger_facet_key`
chat API 新選填參數；驗證＝必須命中 conversational config registry 且 enabled 且通過 repair_enabled gate；命中→跳過意圖辨識直接 seed 面向會話（帶本次訊息與 image 一併處理）。未命中→照常走管線（不報錯，防呆）。
**理由**：engine-first 白名單會吸整角色流量（盤查證實不可用）；語義對齊 trigger_form_id（G9 同族，LINE rich menu 未來同用）。

### 決策 5：輪數與面向埋點＝usage_events 加兩欄
`facet_key VARCHAR(60)`＋`turn_number SMALLINT`（該面向會話中的使用者訊息序號，引擎 state 新增 `user_turns` 計數、每輪 +1、經計量 hook 寫入——`set_facet(facet_key, turn_number)` 比照 set_path/set_comparison 房式）。P50/P90＝按 session_id＋facet_key 分組取 MAX(turn_number) 聚合。加性 migration、欄位偵測降級沿用 P0 機制。
**理由**：per-turn 事件已存在（一訊息一事件），只缺標注；會話層聚合交給 SQL 不建新表。

### 決策 6：Step 0.5 改道＝損傷圖一律進修繕面向
`is_damage=true`（信心足）→ 不再打 SOP 檢索，改 seed 修繕面向並攜帶 suggested_*；`is_damage=false` 或信心不足 → 現行降級提示不變。公共區域等非租約標的的損傷：仍進面向，由對話處理（estate 槽位對不上租約時引導說明位置、必要時走客服管道文案）——不另設分支。
**理由**：損傷照片是報修意圖最強訊號；SOP 停用後原路徑本來就會空轉；例外情境交給對話本身（這正是對話形態的優勢）。

## 風險登記（承自 gap §5，補處置）

| 風險 | 處置 |
|---|---|
| G1 jgb2 端點談不下 | 退化路徑內建（0 筆降級／問一輪），面向仍可用只是少預填 |
| Vision 準確率不足 | 門檻配置化＋退化候選＋輪數埋點量測後調 |
| brain confirm 判定誤差 | quick reply 給決定性路徑；冪等標記防重複建單 |
| 停 SOP 體驗突變（拍板接受） | e2e 驗收矩陣＋可逆 migration |

## 時間軸

| 日期 | 活動 | 結果 |
|---|---|---|
| 2026-07-11 | 三路 gap 盤查 | 重用資產表＋六缺口（gap-analysis.md） |
| 2026-07-11 | 設計決策收斂 | 六項全定案（本文件） |
