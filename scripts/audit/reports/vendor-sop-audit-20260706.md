# 業者設定與 SOP 邏輯盤查（2026-07-06）

方法：資料盤點（vendors/vendor_configs/vendor_sop_items）＋邏輯對碼（chat.py b2b 分流/比分）＋行為抽驗（b2c 雙 vendor probe）。

## 邏輯面驗證（健康 ✓）
- **b2b 分流**：chat.py:1743 `is_b2b → 只走 JGB 知識、SOP=None`——與 SOP 受眾隔離撤案結論一致 ✓
- **vendor 隔離**：同句「租客遲付租金」vendor 2 → 自家 #1373、vendor 3 → 自家 #46（0.992）——SOP 不跨業者 ✓
- **比分邏輯運作中**：vendor 2 案 SOP 0.904 仍由知識勝出（comparison_metadata 在 debug 可查）

## 疑慮（依嚴重度）
1. **P0：vendor_configs 參數真實性**——vendor 1/2/3 各 12 筆（繳費日/逾期費/押金/客服專線/地址）全為 2025-11 種子資料，會經 param_answer 注入對租客的回答（vendor 2 寫 late_fee 300、專線 02-8765-4321、仁愛路地址）。與真實業者規約不符＝對外給錯資訊。→ 需業者逐筆核實；未核實前建議停用（is_active=false 該筆即回 fallback）。
2. **P1：vendor 1（心巢）active 但零 SOP**——租客問句無 SOP 可答。定位不明：未建置 or 已棄用？棄用應停 vendor。
3. **P1：vendor 3 僅 4 筆 SOP**——b2c 覆蓋極薄，幾乎全靠 fallback。
4. **P1：embedding_status 欄說謊**——11 筆 active 標 pending 但向量存在且實際可被檢索（probe 實證）。狀態鏈（誰寫 completed）已斷。→ 資料修：對齊 completed；根本修：以「向量存在」為唯一真相或修 generator 寫回。
5. **P2：vendor.settings 幾乎全空**——僅 vendor 4 有 jgb_role_id；vendor 2 為 {}。role_id 現全靠請求帶，vendor 層無兜底。
6. **P2：contact_email 3/4 空**——quota 警示信收不到（已知，重申）。
7. **P2：vendor 4 有 75 SOP＋jgb_role_id 但零 vendor_configs**——若 b2c 營運中，參數題 fallback。定位待確認。

## 優化機會
- **稽核不變量 7（業者健康）**：active vendor 必有 SOP 或標記 b2b-only；embedding_status 與向量一致；（核實機制建立後）param 必帶核實標記。
- **參數核實欄位**：vendor_configs 加 verified_at/verified_by，param_answer 只用已核實參數。
- **SOP 覆蓋雷達**：b2c NOFOUND/fallback 日誌按 vendor 分列（usage_events 已有 processing_path——現成可查），薄覆蓋 vendor 一目了然。
- **comparison 可觀測**：SOP vs 知識勝負已在 debug_info，可考慮進 usage_events.answer_source 常態化（現欄位已存在，補寫入即可）。

## 補充盤查：參數雙軌真相（2026-07-06 使用者提示「Lookup 統一匯入」後追查）

**證實：參數體系雙軌並存**（半遷移家族 +1）：

| 體系 | 資料 | 消費端 |
|---|---|---|
| `vendor_configs`（舊） | 12 筆/vendor，**2025-11-05 同秒種子**（繳費日/逾期費/專線/地址） | `vendor_parameter_resolver` → param_answer 注入回答（現役） |
| `lookup_tables`（新） | **142 筆，2026-03-12 統一匯入**，13 分類（管理費/押金/水電×3/包裹/停車/繳費方式/客服/廠商/設施/服務時間），按物件地址結構化 | 僅 **5 筆遠古知識錨點**（1403-1408：客服專線/LINE/推薦廠商×3）經 api_call lookup 端點取用 |

**翻案線索**：先前裁定「範疇外」的 12 題中，「管理費金額與包含項目」「包裹代收/位置/時間」「停車費」「社區設施」其實 **lookup_tables 有業者上傳的真資料**——NOFOUND 不是沒真相，是**缺知識錨點串接**（管理費/押金/包裹等 8 個分類的 lookup 資料無任何錨點）。維持範疇外的只剩：法規稅務、加租/賠償規則、鄰居糾紛（lookup 也答不了的）。

**新增疑慮**：
- P1：lookup_tables 混入「範例：」開頭的模板列（vendor 2 實測可見）——會被當真資料端給租客；匯入驗證缺防呆。
- P1：雙軌收斂待決——param_answer 讀舊表、Lookup 讀新表，同類資訊（客服專線/服務時間/繳費方式）兩處各一份，值可能互相矛盾（vendor_configs 專線 02-8765-4321 vs lookup customer_service 分類）。
- 待確認：lookup 142 筆是真業者上傳還是功能 demo 匯入（地址樣態偏 demo）。

**優化路線（若資料屬實）**：為 8 個未接分類補知識錨點（api_call lookup 端點現成、5 筆先例可抄）＝「管理費/包裹/停車/設施」類 b2c 問句從 NOFOUND 變真答案；同時廢 vendor_configs 併入 lookup（單源），param resolver 改讀 lookup 或反向——擇一收斂。


## 執行紀錄（步驟②③，2026-07-06 使用者核准）

- **搬家**：`migrate_vendor_configs_to_lookup.sql`——37 參數（含 vendor 3 demo 殘渣照搬保行為）＋3 筆客服專線 alias 入 lookup（40 筆，冪等）。
- **切讀**：`vendor_parameter_resolver` 預設讀 lookup（param 四分類過濾，不掃物件級資料）；`VENDOR_PARAMS_FROM_LOOKUP=false` 秒切回。unit 2 案先紅後綠。
- **錨點修復**：1403 客服專線因 alias 復活（活體 02-8765-4321 直出）；1405-1408 key 對位確認無需改。
- **匯入防呆**：lookup import 拒收「範例：」開頭列。
- **8+3 分類錨點**：33 筆（11 分類主錨點＋自然問句變體；handler 放行 key 空＋key2=全部 的整分類查詢）。活體：vendor 1（零 SOP）「管理員會代收包裹嗎」NOFOUND→列 6 筆代收明細 ✓。
- **修正認知**：先前 b2b 回測的「範疇外 NOFOUND」在 b2c 側多有 SOP/知識覆蓋（vendor 2 SOP #1323 管理費 1.0 完勝）——錨點價值在零/薄 SOP 業者（vendor 1/3）與未來擴充分類。
- 殘留掛帳：管理費類 generic 知識（#3117 等）排名壓過 lookup 錨點——內容不錯但非 per-vendor 實值；擇期評估以 lookup 值增潤或退役。SYNC_FILES +3 檔；稽核/709 unit 全綠。


## 分工定案與反轉（2026-07-06 使用者裁決）

**裁決**：通用資料（公司電話/LINE/營業時間等 vendor 級單值）＝`vendor_configs`；案場級與額外資料（管理費/電費/包裹等）＝`lookup_tables`。推翻先前「統一 lookup」方向。

**執行**：搬家 40 筆自 lookup 撤除、migrate migration 撤檔（prod 未跑過，無痕）；resolver 預設回 configs（flag 保留）；知識 1403 客服專線改 configs 模板直答（`{{service_hotline}}`——比 lookup alias 更正確，各 vendor 出自家值）；案場級 33 錨點不動。三路活體驗證通過。

**取捨與已知債**：
1. lookup 內原生「通用類」殘留（customer_service 的 LINE/服務中心、service_hours 7 筆、payment_methods 8 筆）依新分工屬 configs 範疇，但為業者上傳原生資料且部分比 configs 豐富——重匯時歸位（移 configs 或刪除），service_hours/payment_methods 錨點暫仍讀之（保留豐富覆蓋）。
2. configs 升格為通用唯一源後，其 2025-11 種子值的真實性核實（原 P0 疑慮）更形關鍵。
3. vendor 2 污染/vendor 3 demo 值：不變，待重匯。
