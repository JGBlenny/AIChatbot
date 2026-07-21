# 業務版流程圖——逐條對碼驗證證據

> 目的：業務版流程圖（conversation-flow-business.md / .mmd）上的每條斷言都有實碼出處，不憑文件拼接。
> 驗證日：2026-07-16。方法：四路獨立 scout 對 rag-orchestrator 實碼逐條查證（46 條）＋ jgb2 前台通路實查＋ dev DB 實查。
> 結果：42 ✅ 屬實、4 ⚠️ 偏差（已據實修圖或列入文件漂移待辦）。

## 一、入口與管線（10 條，chat.py）

| 斷言 | 判定 | 證據 |
|---|---|---|
| 進行中會話攔截最優先；對話偽會話優先於表單會話 | ✅ | chat.py:4040-4060 |
| trigger_facet_key 直達；未命中照常不報錯 | ✅ | chat.py:839-858 |
| 損傷圖辨識改道修繕；repair_enabled gate 缺值 true；降級文案 | ✅ | chat.py:514-618, 731, 816-833 |
| prospect engine-first 在快取前 | ✅ | chat.py:621-627, 4083 |
| 快取排除動作類/串流/debug | ✅ | chat.py:630-660, 103-105 |
| query rewrite 開關＋多意圖 | ⚠️ | rewrite chat.py:2007-2018 屬實；主 1.3x/次 1.1x 倍率未在 chat.py 證實（檢索層待查）——業務版未引用數字，不受影響 |
| b2b 只檢索知識庫、不跑 SOP | ✅ | chat.py:1976-1995 |
| SOP∥知識並行；接近時 SOP 有動作優先；fallback＝參數答案→LLM 兜底 | ✅ | chat.py:2043-2046, 2215-2235, 2854-2928 |
| action_type 分派；form_fill≥0.75；分類路由≥0.75 進面向 | ✅ | chat.py:976-998, 3078-3303 |
| SSE 逐 token 串流 | ✅ | chat.py:1296-1458, 377-385 |

## 二、SOP 與表單（12 條）

| 斷言 | 判定 | 證據 |
|---|---|---|
| trigger_mode none/manual/immediate 三行為 | ✅ | sop_trigger_handler.py:171-305 |
| immediate 否定詞/問句/>10 字不算同意 | ✅ | sop_orchestrator.py:221-278 |
| next_action form_fill/api_call/form_then_api | ⚠️ | sop_trigger_handler.py:37-42——實為四種（另有 none＝無動作）；業務圖「純說明不接服務」已涵蓋 |
| 等待期新問題相似度≥0.7→重新檢索 | ✅ | sop_orchestrator.py:124, 509-538 |
| 表單狀態機 | ⚠️ | form_manager.py:34-43——實際 7 狀態，**無 CONFIRMING**（immediate 待確認用 context 存，非狀態機）→ 技術文件 §7 漂移待辦 |
| 離題三型處理 | ⚠️ | digression_detector.py:15-20、form_manager.py:1026-1032——question 型**先答、需用戶說「繼續」才回表單**，非自動拉回 → **業務圖已修正** |
| PAUSED 可續填；30 分逾時取消 | ✅ | form_manager.py:2710-2756, 2975-3003 |
| REVIEWING 摘要／修改N→EDITING／確認才提交 | ✅ | form_manager.py:2778-2971 |
| on_complete_action 三路 | ✅ | form_manager.py:2406-2708 |
| API 錯誤重試上限 2、達限自動取消 | ✅ | form_manager.py:2435-2491 |
| chaining/option-routing、深度上限 3 | ✅ | form_manager.py:59, 678-828 |
| 欄位驗證 text/phone/email/date/number/select | ✅ | form_manager.py:1422-1425＋form_validator.py |

## 三、對話引擎與交易（14 條，全數 ✅）

| 斷言 | 證據 |
|---|---|
| 面向＝DB 配置（category='對話規則'），加面向零改碼 | conversational_config.py:7-13, 113-138 |
| 三層系統脈絡疊加 | system_context.py:36-120 |
| Brain ask/converge/confirm＋inline_answer 岔題即答（自動接回） | llm_answer_optimizer.py:825-912、conversational_engine.py:659-706 |
| API grounding 三態（1 筆答/0 筆追問/N 筆候選）＋向量/分類/ids 選材 | conversational_engine.py:63-67, 802-920, 1056-1091 |
| face 切換／scope switch 重路由 | conversational_engine.py:637-650, 177-208 |
| 交易判定＝execute_endpoint | conversational_engine.py:305-307, 530 |
| prefill 雙證查租約＋Vision 併槽、已知不重問 | repair_prefill.py:178-311 |
| confirm 後引擎保底驗 required_slots | conversational_engine.py:664-679 |
| 同意判定引擎層決定性（按鈕值/同意詞）；模糊不送出 | conversational_engine.py:53-61, 1005-1054 |
| executed 冪等不重複建單 | conversational_engine.py:1017-1041 |
| 失敗誠實＋重試；brain 失敗絕不建單 | conversational_engine.py:632-635, 1039-1049 |
| 取消關會話、槽位丟棄 | conversational_engine.py:444-450, 1021-1024 |
| 續跑補圖只填空槽 | conversational_engine.py:452-491 |
| 售前不報價/不碰個資/競品中立 | conversational_config.py:50-59、conversational_rules.py:19-64 |

## 四、業者層與資料（10 條）

| 斷言 | 判定 | 證據 |
|---|---|---|
| 檢索過濾：業者/角色/業態/is_active | ✅ | vendor_knowledge_retriever_v2.py:70-114 |
| 優先級加成 +0.15@≥0.70 | ⚠️ | base_retriever.py:394-395 實為關鍵字加成（1.0–1.3x）；priority 用於排序（:121）→ 技術文件 §3 漂移待辦；業務版未畫此項 |
| 業者參數注入＝正則決定性替換、無 LLM | ✅ | vendor_parameter_resolver.py:124-267 |
| lookup 決定性查詢、無 LLM | ✅ | lookup.py:53-100 |
| 每則訊息計量 usage_events | ✅ | usage_metering.py:1-116（額度警示寄信在另檔／middleware，quota spec 已收案，prod 待設 SMTP） |
| 知識觸發欄位透傳（P0 修後） | ✅ | vendor_knowledge_retriever_v2.py:106-108, 338-340 |
| JGB API 雙證＋formatter 決定性解碼（五領域 FACE_BUILDERS） | ✅ | jgb_system_api.py:48-50、jgb_response_formatter.py:176-217 |
| api_call_handler 註冊表＋params_from_form | ✅ | api_call_handler.py:49-143 |
| 查詢數字不經 LLM 改寫 | ✅ | jgb_response_formatter.py:297-372、chat.py:3586-3624 |
| USE_MOCK_JGB_API 開關 | ✅ | jgb_system_api.py:35, 134 |

## 五、通路與資料現況（實查）

| 事實 | 證據 |
|---|---|
| jgb2 唯一聊天端點只收 message/session_id/mode/target_user，**無 image_urls** | jgb2 HelpAssistantController.php:492-514、routes/web.php:922 |
| jgb2 codebase 無任何 b2c → 租客/房東進線未串接；現行進線＝業者員工（後台 SSO＋白名單）＋prospect 匿名 | jgb2 全庫 grep（2026-07-16） |
| 照片上傳後端兩路皆備：開場改道（chat.py:514-618）＋會話中補圖（conversational_engine.py:452-491）；前台放哪待拍板 | 同上 |
| 知識庫 1015 筆僅 2 筆綁業者，其餘平台共通（含 JGB 系統操作知識），靠 target_user/business_types 隔離 | dev DB 實查 2026-07-16 |
| SOP 嚴格業者維度：vendor 2 啟用 250、vendor 3 有 4、vendor 4 修繕 75 停用（M2） | dev DB 實查 2026-07-16 |

## 六、技術文件漂移（2026-07-16 已修正於 COMPLETE_CONVERSATION_ARCHITECTURE.md）

1. §7 `CONFIRMING`：FormState 有定義（form_manager.py:41）但全庫零使用（死狀態），immediate 待確認由 SOP context 管理——文件已移除該轉換並加註。
2. §3「優先級加成 +0.15@≥0.70」無實裝：priority 只用於排序（v2:121），加成實為關鍵字加成 1.0–1.3x（base_retriever.py:357-403）——文件已修。
3. §2「主 1.3x/次 1.1x 意圖加成」無實裝：意圖僅 JOIN 帶出（v2:219-221）——文件已修。

## 七、反向盤查（實碼→圖，2026-07-16）

從實碼枚舉約 48 個用戶可感知分支對照圖面，涵蓋率約 90%，7 個缺口全數補進兩份業務版：

| 發現 | 實碼證據 | 圖上處置 |
|---|---|---|
| 「30 分自動取消」清理函式無生產呼叫端（未接線） | form_manager.py:2975-3001，唯一引用 :3001（自身） | 改註「已寫成、尚未啟用」 |
| 知識觸發表單有三模式（auto/immediate/manual） | chat.py:3197-3250、sop_trigger_handler.py:258-304 | KTYPE 邊標三分岔 |
| API 查詢缺參數有專屬回覆 | chat.py:3553-3570 | QUERY 補「明說缺什麼才能查」 |
| 表單重試耗盡依錯誤原因給不同結束語 | form_manager.py:2440-2524 | AFTERFORM 邊補「試滿依原因說明後結束」 |
| 圖片認不出／非損壞有引導出口 | chat.py:593-613 | VISION 補旁支 |
| 對話中補圖自動併入 | chat.py:450-461 | ASKMISS 補一行 |
| 候選選不出來會重列反問（支援口語序數） | conversational_engine.py:240-296 | DIAG 補「選不出來會再問一次」 |
