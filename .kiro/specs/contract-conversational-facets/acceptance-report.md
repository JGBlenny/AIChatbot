# 驗收報告：contract-conversational-facets

> 驗收日期：2026-07-03　範圍：R1–R11 全需求　結果：**21/22 任務收案，可部署**（6.3 部署由使用者執行；7.4 G5 選配 gated）
> 測試環境：本機容器（真 DB＋真 embedding＋真 reranker＋真 jgb2 preview＋真 LLM）

## 一、需求逐項驗收

| 需求 | 驗收標準摘要 | 結果 | 證據 |
|---|---|---|---|
| R1 資料驅動底座 | 5 子分類＋脈絡＋config 純資料成立、零引擎修改；三層疊加 ≤4500 | ✅ | `test_contract_facet_seeds_req`（11 案）＋`test_contract_facets_seed_integration_req`（5 案，真 DB）；migration 內建長度自檢（實測 <2600） |
| R2 合約異動＋申請書 | 三出口 status 決定性分流；申請書槽位收集→可抄錄產出＋提交指引；權限/狀態分流；轉歷史共用出口 | ✅ | unit 全 status 矩陣 15 案；`test_contract_change_tree_integration_req` 5 案；e2e 申請書 token 實測（`service@jgbsmart.com`/異動前/異動後/合約 ID 全中） |
| R3 退租收尾 | bit 旗標判步驟；點交點退互不相依；G3 封存個人化/通用降級；逾期未轉導客服；回簽效期 30 天 | ✅ | unit 旗標矩陣 10 案＋secondary_call 14 案；e2e 真資料（84908 實盤 5 筆未封存個人化指名） |
| R4 續約 | 剩餘天數＋可否系統續約＋免註冊不重簽＋G4 已被續約＋配額真因 | ✅ | unit 13 案（含 G4 有無欄位）；e2e 84981 真跑；配額真因知識依 research 修正 |
| R5 建約引導 | 兩輪分流；藍字提醒；轉異動/續約 scope=switch；共同承租/條款 QA 掛面向；特殊個案導客服 | ✅ | config seed 驗證＋整合 switch 重路由案＋e2e 進場分流實測；共同承租知識（C-1 週頻）已入庫 |
| R6 簽署排障 | 還差誰簽/通道/綁定；G1 效期＋過期清資料；G2 錯配遮罩；自助排查導客服 | ✅ | unit 13 案（G1/G2 矩陣＋密文防護）；e2e 84927 真資料（效期至+比對一致）；錯配遮罩單元覆蓋（preview 無錯配樣本） |
| R7 決定性計算 | facts 由 formatter 算、LLM 只轉述；API 現值為準；0/N 筆降級；缺欄位不虛構 | ✅ | FACE_BUILDERS 純函式全矩陣；face=None 恆等 52 案（突變證明殺傷力）；e2e G 缺欄位降級不阻斷 |
| R8 面向路由切換 | 6 面向互轉＋脈絡切換；鎖定合約保留；口語錨點進場；既有保證不回歸 | ✅ | 整合 face 切換保留識別＋face 傳抵 handler；**進場路由回歸 24 案**（13 進對話保護＋11 單發紅名單，誤進場 4 案已收斂，routing-tuning.md） |
| R9 知識產製 | 官方素材為主幹；短關鍵字/先述情境；衝突以 research 為準；審核流程 | ✅ | help 48 篇全文素材；批次 1（修正 1＋35＋錨點 12，審核通過）＋批次 2 快照 5 筆＋調校 1 筆＝**淨增 58 筆**；3331 效期錯誤修正（2天→72小時） |
| R10 外部 API 契約 | G1–G4 存在性驅動、兩端獨立部署 | ✅ | 契約文件已交付；G1/G3/G4 上線驗畢；**G2 密文缺陷由本驗收揪出→jgb2 修復→複驗通過**；G5 選配未做（7.4 gated） |
| R11 回歸保護 | 既有測試全綠；檢索基準不回歸；e2e 走正常管線；會話銜接；reranker 重建入部署 | ✅* | unit 464/int 58/e2e 17 全綠（狀態判斷矩陣一字未改）；檢索：非合約對照組 69.5% 無異常＋路由回歸 24 案（*80% 舊基準查明為失效 harness，Run 285–288 盤查，兩段式基準另案）；reranker 重建在部署清單 |

## 二、交付物清單

**程式**（5 commits，未 push）：`017df2f` face 貫穿＋四 builder／`01e2365` 資料四件套／`df67657` backfill／`5940509` 整合+e2e+日期識別 guard／`b4a484f` secondary_call+G 驗證／`(HEAD)` 路由回歸 harness。
**Migrations ×7**：categories_v2、system_context、configs、backfill（3388 修訂版）、closeout_secondary_call、update_closeout_archive_answer_rule（封存主詞雙釘）＋前置 3 支既有種子。
**知識**：淨增 58 筆（含 12 錨點）已入本機庫含 embedding；prod 重放＝import 工具 ×2 批次＋tune_routing.py（spec 目錄，冪等）。
**文件**：g1-g4-api-contract.md（含驗證狀態）、facet-backfill-review.md、knowledge-batch-review.md、routing-tuning.md、research.md §九（快照盤查）。

## 三、驗收過程揪出並修復的缺陷（真跑價值）

1. `_extract_identifier` 日期誤抽識別（e2e 真資料揪出，2026/12/30→誤切多筆）→ regex 結構性 guard。
2. jgb2 G2 回加密密文 → 假錯配風險 → 消費端防護＋jgb2 修復＋複驗。
3. `get_bills` 不支援 per-contract → secondary_call 靜默降級 → 補授權形態。
4. 既有知識 3331 邀請效期錯誤（2 天 → 72 小時，與官方文章及程式一致）。
5. 誤進場 4 案（含自己 4.2 補標過頭的 3388）→ 資料側收斂＋回歸測試釘死。
6. 封存主詞轉述漂移（多輪實測 1/3 → answer_rules＋脈絡雙釘 → 0/3）。
7. 回測 harness 三重失效（target_user/分數欄位/role_id）→ 22.9% 假警報定性，避免誤判產品回歸。

## 四、遺留事項

- **6.3 部署**（使用者執行）：migrations→知識重放→reranker 重建→清快取→煙囪。
- **7.4 G5**（選配 gated）；條款法律 QA 三題待官方素材；「換承租人後原約處理」營運 SOP 話術待業務定案。
- **另案立項**：兩段式回測基準（行為標注＋retrieval-only runner＋harness 修復進版控）。
