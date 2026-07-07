# 實作任務：iot-conversational-facets（智慧設備領域對話面向擴充）

> 建立時間：2026-07-04
> 需求：requirements.md（R1–R9）｜設計：design.md（v1.0）｜落差：gap-analysis.md｜研究：research.md（主題 1 未給電決策樹 主題 2 離線/度數 主題 3 識別鏈 主題 4 recharge 定性 主題 5 J/G 主題 6 e2e 前置 主題 7 舊案過濾）
> 標記：`(P)` = 可與同層其他 `(P)` 平行；`- [ ]*` = 可延後（外部條件 gated）
> 鐵律：TDD（先紅後綠）；面向字面只准出現在資料列與 `services/jgb/` 領域檔；合約 6＋帳務 5＋帳號 4 面向/售前/form_fill/diagnose_iot 零回歸；機制數字（每小時 :35 同步/儲值帳單效期 4 天/對帳每小時）以 research 為準寫死、LLM 不得自創；度數與金額只引用存值禁重算；**斷電/復電措辭歸電表端（廠商行為），不稱系統行為**；不代執行遠端控制；離線時不引用 is_poweron 下結論（J-I1 防護）

## 1. get_meters wrapper＋iot.py builder 底座（先做）

- [x] 1.1 `jgb_system_api.get_meters` client wrapper（TDD）：role_id 必填＋keyword（client 端對 estate_name/name 過濾——端點無此參數）＋estate_id 透傳＋分頁處理（≤200）；查無回空列不拋；mock 版；registry 掛 `jgb_meters`。
  - 需求：2.1, 8.1, 8.4
- [x] 1.2 `services/jgb/iot.py` 擴充：`METER_FACE_BUILDERS` 註冊表＋`build_meter_facts`——決定性四分支（research 主題 1 語義）：①is_online=false → 離線分支優先（「截至 {synced_at} 最後同步」措辭；Miezo 無 synced_at 降級；DAE 帳密失效/未開 API 服務高頻真因→引導 IoT 裝置頁重新驗證；仍離線導廠商附設備資訊；**離線不引用 is_poweron**）；②online＋poweron=false＋enable_topup＋balance 低 → 儲值耗盡（「電表端自動斷電；儲值入帳後電表端自動復電」）；③online＋poweron=false（非儲值/餘額足）→ 供電關閉（IoT 裝置頁模式切換路徑；無斷電原因紀錄不臆測）；④online＋poweron=true → 供電正常轉硬體/確認是否問對表。設備狀況查詢直出解碼（線上/供電/餘額/度數/最後同步）；度數餘額單價引用存值。`jgb_response_formatter` 加 `jgb_meters` face 分發（同 jgb_team_members 模式）；face=None/未命中 → 原路恆等（diagnose_iot 零回歸）。
  - 需求：2.2, 2.3, 2.4, 2.5, 5.1, 5.2, 9.1
- [x] 1.3 單元測試（先紅後綠）：builder 四分支×廠商（DAE/Miezo）×synced_at 有無矩陣；J-I1 防護斷言（離線態輸出不含供電結論）；儲值耗盡分支含「自動復電」token、供電關閉分支不臆測原因；face=None 恆等（既有 diagnose_iot 測試不改一字全綠，mutation 證明）；wrapper 過濾三路（keyword 命中/查無/estate_id）。
  - 需求：5.1, 5.3, 9.1

## 2. 面向資料四件套（migrations）

- [x] 2.1 (P) `add_iot_facet_categories.sql`：category_config 母 `智慧設備`＋2 子分類（`電表排障`/`IoT設定引導`，冪等）；整合驗證 `_domain_faces` 含兩面向。
  - 需求：1.1
- [x] 2.2 (P) `seed_iot_facet_system_context.sql`：系統脈絡 3 列——母薄層 ~150 字（雲端電表 vs 手動抄表、儲值模式、台科電=DAE 名詞對照，不含分支細節）；2 子各 300–600 字依 research 主題 1/2 撰寫（電表排障：未給電四分支決策樹＋每小時 :35 同步一次＋DAE 帳號失效整批停同步＋儲值 webhook 對帳口徑「帳單付了電還沒來→系統每小時自動對帳補認，仍未到聯繫客服」；設定引導：串接啟用/儲值單價（DAE 端設定 JGB 鏡像）/門鎖預設密碼/連結起始日分流框架＋儲值金流入帳屬帳務提示）；長度預算自檢 ≤4500。
  - 需求：1.3, 1.5, 2.6, 3.3
- [x] 2.3 (P) `seed_iot_facet_configs.sql`：對話 config 2 筆（persona_role `pm_iot_meter`/`pm_iot_setup` 專屬鍵）——`電表排障` select='api' endpoint=jgb_meters＋required_slots=[meter_ref]＋**deterministic_id:false**（識別多為物件名/房號文字）＋search_params keyword＋result_mapping（label：name/estate_name/meter_type，candidate_cap 8）；`IoT設定引導` select='category'＋**明填 target_user='property_manager'**（account 坑防呆）；persona：電表排障現象分流（沒電？離線？度數怪？）＋機制數字紅線＋**不代操作紅線**（復電/重啟/模式切換只指路）；設定引導兩輪分流＋涉特定設備現況 switch 電表排障＋儲值錢入帳沒 switch 帳務。
  - 需求：1.2, 1.6, 2.1, 3.1, 3.2, 3.3, 3.4, 5.5, 6.1, 6.2
- [x] 2.4 整合測試：兩面向 config_for_category 進場；三層脈絡疊加正確（母薄層＋命中子；不含前三域層與售前）；電表排障 identify→client 過濾→多顆候選列選→單顆 ground 四分支 facts；設定引導 category 收斂（grounding 有資料——target_user 明填生效驗證）；面向互轉（設定→排障）保留識別；跨域 switch 雙向（→帳務、→帳號）；全程零引擎修改驗證。
  - 需求：1.2, 1.3, 1.4, 2.1, 2.2, 5.4, 6.1, 6.2

## 3. 知識工程（2 完成後可與 4 交錯；含人工確認閘門）

- [x] 3.1 (P) 素材整備：help 中心 IoT 素材抓取（fetch 工具改 IoT 關鍵字：電表/儲值/門鎖/IoT/串接/度數，一次性腳本不 commit）＋**20 舊案逐案存廢表**（對 research 真碼過濾：已被改版解決者剔除、口徑過時者改寫、現行有效者轉製——本域特有工序）。
  - 需求：7.1
- [x] 3.2 (P) 既有知識盤點＋補標：IoT 智慧設備 5 筆逐筆歸屬主面向（互斥）或維持單發 → 人工確認清單 → backfill migration。
  - 需求：7.2
- [x] 3.3 各面向知識產製：現行痛點機制知識為主軸（未給電三態、儲值後電未來 webhook 對帳口徑、度數落差每小時同步、DAE 帳號失效整批停同步、離線排查）＋存廢表過濾後轉製＋**門鎖硬體單發知識包**（悠遊卡/磁扣/電池/音量/QRCode——廠商功能面口徑＋導廠商附設備資訊清單，不掛面向）；question 短關鍵字、answer 先述情境；個案資訊剝除；口徑與真碼衝突以 research 為準修正；全部進審核流程。
  - 需求：4.1, 4.2, 7.1, 7.3, 7.4
- [x] 3.4 錨點知識＋進場路由回歸擴充：每面向口語起手句 1–2 筆（**target_user=['property_manager'] only**；語彙分工：IoT 用「沒電/未給電/離線/度數」，避「入帳/金流」與「看不到」）；`test_facet_entry_routing_req.py` 擴 IoT 案例——錨點進對話＋門鎖硬體/教學句單發＋**三組誤吸邊界點名**（「儲值的錢進來了沒」歸帳務、「租客看不到電表」歸帳號域登入排障、門鎖問句不吸進電表排障）；紅→調→綠。
  - 需求：4.3, 6.3, 6.4, 9.2

## 4. 全流程＋端到端

- [x] 4.1 整合測試（真 DB＋stub jgb2 參數感知）：電表排障全流程（現象起手→追問物件/房號→client 過濾（多顆候選/單顆直中）→四分支 facts 各一案）；離線態措辭斷言（「最後同步」＋不含供電結論）；設定引導兩輪分流→category 收斂含機制 facts；跨域 switch 雙向。
  - 需求：2.1, 2.2, 2.3, 2.4, 3.1, 6.2
- [x] 4.2 e2e（preview 真服務＋真 LLM＋真 jgb2）：兩面向口語第一句進場（正常管線含 reranker）；**機制 token 斷言**（「每小時」「自動復電」「最後同步」不被改寫）；不代操作斷言（回答不含代執行承諾）；進對話 vs 單發各一例；跨域 switch 至少一例。**真電表多輪 gated**：〔等 **J-I0 修復**（/meters type 過濾 bug 致恆回空，見 iot-api-contract.md）——修復後以 role 37305 重驗；未修復前以降級態＋整合 stub 覆蓋並誠實標注〕。
  - 需求：2.5, 5.2, 6.2, 9.3

## 5. 回歸＋部署

- [x] 5.1 回歸：合約 6／帳務 5／帳號 4 面向、售前、既有 form_fill 與 diagnose_iot 全綠（unit＋integration＋e2e 全套重跑）；進場路由全案例（四域）綠。
  - 需求：9.1, 9.2
- [ ] 5.2 部署執行（併入統一部署 runbook）：migrations 3 支追加 → 知識匯入（審核後）＋補標 → reranker semantic model 重建 → 清快取 → 煙囪驗證（2 面向各一句＋門鎖單發對照）。
  - 需求：9.4
- [x] 5.3 (P) J/G 契約文件交付 jgb2（提前完成 2026-07-04，`iot-api-contract.md`）：**J-I0 阻塞級新增**——/meters type 過濾錯型別（`where('iots.type', 3)` vs 實際存值 `'power_meter'`，MeterApiController.php:37 vs DaeJob.php:455）致端點對所有 role 恆回空（37305/20151 實測交叉印證）；＋J-I1~I3＋觀察級＋G 選配＋測試 role 請求（37305 修復後重驗）。
  - 需求：8.2, 8.3

## 6. 外部條件 gated（可延後）

- [x] 6.1 J-I0 修復驗證（2026-07-04 jgb2 已部署）：37305 回 50 顆真台科電電表；真資料多輪 e2e 收案（物件口語→一屋雙表候選→選定→現值分支），並逼出兩缺陷已修：wrapper token 化過濾（口語多詞/分隔符省略）＋int keyword 型別容錯（get_meters/get_team_members 同款）。
  - 需求：9.3
