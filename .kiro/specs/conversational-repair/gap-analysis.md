# 差距分析：conversational-repair

> 產生時間：2026-07-11　方法：三路對碼盤查（引擎交易擴充點／照片辨識與 Step 0.5／預填 API・配置・進場・埋點）
> 總判：**重用面遠大於預期**——推斷原料（Vision 建議）、執行通道（grounding→execute_api_call）、多選機制（插點 A）、寫入型 formatter 處理全部現成；真缺口集中在三處：租客物件 API（外部依賴）、引擎 image 通道、確認 gate 語義。

## 1. 重用資產（對碼證實，不用新建）

| 需求 | 現成資產 | 位置 |
|---|---|---|
| 照片→分類推斷（R2.3） | **Vision 辨識已輸出 `suggested_category/item/reason/emergency`**（GPT-4o、修繕分類樹已注入 prompt、信心度、8 類損壞型別）——現行表單流程只存 metadata 不預選（既有智慧閒置） | image_recognition_service.py:22-275、form_manager.py:1517-1648 |
| 執行通道（R4.2） | `_ground_by_api` 設定驅動 endpoint→`execute_api_call`；**formatter 對寫入型端點已有「不合併知識、直返結果」分支**（jgb_create_repair 在 api_registry） | conversational_engine.py:563-730 |
| 多租約選擇（R2.2） | 插點 A `pending_candidates`＋`_match_candidate` 三級確定性比對（序號/id/label），零硬編 | conversational_engine.py:229-253 |
| 槽位檢查 | `grounding_scope.required_slots` 設定驅動、缺一不打 API | conversational_engine.py:484-492 |
| 半交易防護（R3.4） | 引擎失敗一律回 None 降級、無部分提交路徑；required_slots 齊才呼叫 | 盤查證實 |
| 面向進場（R1.1） | 分類路由可複用：知識錨點掛分類→`by_category` 索引→`config_for_category` | chat.py:646-657、conversational_config.py:162-197 |
| 配置擴充（確認文案/execute endpoint/prefill 規則） | `generation_metadata.conversational_config` jsonb 任意擴鍵；建議塞 `grounding_scope` 子鍵避免 dataclass 膨脹 | conversational_config.py:26-123 |
| 取消（R3.3） | chat.py 續跑 hook 已有顯式取消→`engine._close` | chat.py:434 |
| Step 0.5 停 SOP 安全性 | 修繕 SOP 全停後 `has_sop=False`→回 None→**安全降級文字流程，不爆錯** | chat.py:497-586、vendor_sop_retriever_v2.py:107-110 |

## 2. 真缺口

### G1（外部依賴，最大風險）：租客物件查詢無現成 API
「以租客身份（role_id＋user_id）→ 他的租約物件清單」**沒有直達端點**：`get_estates(role_id, keyword)` 回業者全物件無租客過濾；`get_contracts` 同；`get_tenant_summary(role_id, user_id)` 是統計摘要非清單（jgb_system_api.py:208/325/343）。這是「租客視角 API 缺口」的具體實例。
**選項**：(A) 確認 `get_contracts` 真實 API 是否支援 user_id 過濾（查 client-guide／問 jgb2）(B) 複合查詢（summary＋逐筆驗證，低效不建議）(C) 請 jgb2 開租客租約端點。**處置**：列 E 級依賴與 J 清單；設計期以 mock 契約先定介面形狀（雙證進、租約物件清單出），與 E1 真 API 對接一併談。

### G2：引擎無 image 通道
`image_urls` 進不了引擎（引擎無 image 參數、brain 輸入無圖）；且管線順序 Step 0（會話攔截）先於 Step 0.5（圖片）——**面向會話進行中傳圖，續跑路徑收不到圖**。需：續跑 hook 把 image_urls 傳入引擎＋引擎把辨識結果（Vision suggested_*）併入 extracted_fields。

### G3：確認 gate 語義（新建，但擴充點明確）
brain 輸出 schema 現為 `action: ask|converge`——加 `confirm` 語義：brain 判定收齊→confirm（出摘要）→使用者同意→execute（呼 `_ground_by_api` 既有通道）。冪等（R4.4）需會話層 `executed` 標記防重複建單。盤查確認這是**最小新建集**：brain 規則範本＋prepare 新分支＋配置新鍵，其餘重用。

### G4：Step 0.5 改道
停 SOP 後 Step 0.5 降級安全，但目標形態要它**進面向**（損傷照片＝報修意圖的最強訊號）：改為辨識後攜帶 suggested_* 進入修繕面向（而非觸發 SOP）。

### G5：進場的兩條腿
- 自由輸入：分類路由複用（意圖錨點知識掛修繕分類、≥0.75）——與 P0 已知的門檻議題共存，錨點品質＋分數埋點實測把關
- 按鈕直達（R1.3）：**無現成「直達面向」參數**（engine-first 白名單不可用——會吸整角色流量）。需新增輕量直達參數（如 `trigger_facet_key`），語義同 trigger_form_id 的面向版〔設計定案〕

### G6：輪數埋點（R7）
usage_events 無 per-turn 欄；引擎 `asked_count` 只計引擎提問非使用者訊息數。需：加欄（P0 的 `ADD COLUMN IF NOT EXISTS`＋set_path 模式前例）＋呼叫端從引擎 state 傳入〔輪數定義按 requirements 名詞定義：使用者訊息數〕。

## 3. 實作路線（單一合理路線，無重大選項分歧）

全案走 **extend**：引擎加 confirm/execute 語義（新分支）＋面向配置新鍵＋接線（image/預填/埋點）＋2 個 migration（表單升 NULL、停 2/4 修繕 SOP）＋2-3 筆知識（意圖錨點/查進度）。唯一架構級新件是「直達面向參數」（G5，小）。

## 4. 設計階段待決清單

1. G1 介面形狀（mock 契約）與 jgb2 溝通路徑
2. confirm 的呈現形式（純文字摘要 vs quick_replies 確認鈕）
3. 推斷信心門檻（Vision confidence ≥? 採納為確認型槽位；表單流程既有 0.7 前例可沿用）
4. 直達面向參數命名與驗證（trigger_facet_key）
5. 輪數欄位定義（turn_number vs 會話總輪數落在收斂事件）
6. Step 0.5 改道後，非修繕損傷圖（如公共區域）的行為

## 5. 風險登記

| 風險 | 影響 | 緩解 |
|---|---|---|
| G1 jgb2 不給租客租約端點 | 高（物件預填做不到→退化為問一輪） | mock 先行＋退化路徑本來就要有（多租約選擇機制同款）；J 清單提前談 |
| Vision 推斷準確率不足 | 中（確認型槽位變詢問型，輪數↑） | 信心門檻＋R2.4 退化候選；輪數埋點量測後調 |
| 修繕面向與既有診斷面向的進場分類衝突 | 低 | 修繕掛獨立分類，config by_category 1:1 |
| 停 SOP 後 vendor 2 舊用戶體驗突變 | 中（拍板接受，棄灰度） | e2e 驗收矩陣＋SOP 停用可逆（migration 附回復） |
