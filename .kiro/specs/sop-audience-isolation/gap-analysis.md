# 落差分析：sop-audience-isolation

> 分析日期：2026-07-04　基準：requirements.md（R1–R5）＋現行 codebase 實測
> 定位：提供資訊與選項，不做最終決定；〔研究〕標記者入設計階段研究清單。

## 一、現況元件盤點（全部實測，file:line）

| 元件 | 現況 | 對本 spec 的意義 |
|---|---|---|
| **檢索漏斗單點** | 兩條路徑（chat.py `_retrieve_sop:1572`→`retrieve_sop_hybrid`(chat_shared:64)；`sop_orchestrator:145/158`→`retrieve_sop_by_query`(:308)）**全部匯進 `VendorSOPRetrieverV2.retrieve()`**（BaseRetriever 模式） | R2.4 單一實作點天然成立——過濾放 retriever 層一處生效 |
| SQL 兩塊 | `_vector_search` 向量塊（vendor_sop_retriever_v2.py:104-118 WHERE vendor/is_active）＋關鍵字備選塊（:184-192） | 過濾謂詞要加**兩處**（同檔同語義） |
| **比分點位置** | `_smart_retrieval_with_comparison`（chat.py:1591+）在 `_retrieve_sop` **之後**拿結果比分 | SQL 層過濾 ⇒ **R2.3「比分前」免費滿足**，被濾 SOP 根本不出現 |
| 參數穿線 | `retrieve_sop_hybrid`／`retrieve_sop_by_query`／`retrieve()` 三層簽名**皆無 target_user** | 需穿線：chat.py 有 `request.target_user` 現成；sop_orchestrator 呼叫端可得性〔研究 ①〕 |
| KB 過濾先例 | `vendor_knowledge_retriever_v2._effective_target_user`（:27-31）：KNOWN_TARGET_USERS 正規化、**None→tenant** | 語義模板現成；但 None→tenant 與 R2.5「未帶不過濾」衝突〔研究 ②：實際流量是否恆帶 target_user〕 |
| 資料分佈 | 407 筆＝vendor 2:328／3:4／4:75；**無租客口吻特徵 37 筆**（審表規模證實可行） | R1.2 回填策略成立 |
| 匯入路徑 | sop_utils.py：平台範本匯入（:128）＋業者 Excel 匯入（:129）——皆不設 target_user | 新匯入落 NULL=通用（R5.1 治理註記對象）；匯入器可順手支援選填欄〔設計定案〕 |
| platform_sop_templates | 獨立 admin 體系（routers/platform_sop.py）；是否複製進 vendor_sop_items〔研究 ③〕 | R5.3 同構缺口掛帳判定依據 |
| 測試 harness | 4 實彈問句已有真管線腳本先例；integration 可直測 retriever SQL；e2e TestClient 慣例現成 | R4 直接開工 |

## 二、逐需求落差

- **R1 schema＋回填**：migration 一支（`ALTER TABLE ... ADD COLUMN IF NOT EXISTS target_user text[]`，407 筆小表免索引）；回填工序＝一次性腳本（不 commit）按口吻規則產**審表**（370 筆預判 tenant＋37 筆逐筆欄）→ 人工閘門 → backfill migration（明列 4 實彈＋1166 判定）。無程式落差。
- **R2 檢索過濾**：落差＝SQL 謂詞 ×2＋簽名穿線 ×3＋orchestrator 端 target_user 取得〔研究 ①〕。謂詞語義（沿 KB 慣例）：`(si.target_user IS NULL OR %s = ANY(si.target_user))`——排除語義（含我即可過），tenant 請求在「絕大多數列=['tenant']」的回填後命中集合不變（R2.2 零回歸的資料面保證）。
- **R3 補位知識**：落差＝jgb2 真相盤查兩題（金流支付方式集合——SOP 1256 宣稱信用卡可用需驗證；電費計收模式設定＋發票統編開立鏈）〔研究 ④，agent 平行盤〕→ 知識 4 筆＋閘門。
- **R4 回歸**：integration 直測 retriever（插測試 SOP 列驗過濾三態：tenant-only 排除／NULL 通過／tenant 請求不縮集）＋e2e 4 實彈改判＋租客對照＋「房間沒電」改判；五域全套重跑。
- **R5 治理部署**：runbook 併第六 spec；platform 掛帳依研究 ③ 定案。

## 三、實作策略選項

| 決策點 | 選項 A（傾向） | 選項 B | 權衡 |
|---|---|---|---|
| 過濾位置 | **SQL 謂詞（retriever 層）** | application 端 post-filter | A 比分前天然滿足＋單點；B 要兩路徑重複、且 threshold/top_k 在過濾前計算會失真（先取 5 筆再濾可能全滅） |
| 未帶 target_user | **不過濾（照 R2.5 向下相容）** | 沿 KB None→tenant | A 保守零意外；B 跨體系語義一致但改變未帶行為——依研究 ② 實際流量定案 |
| 匯入器 | 順手支援 target_user 選填欄（Excel 加欄向下相容） | 完全不動（NULL=通用） | A 治理缺口即刻收斂；B 最小改動——規模小可 A |
| 回填載體 | backfill migration（id 清單式，冪等） | 管理後台手動 | A 可重跑可部署；B 不可追溯 |

## 四、設計階段研究清單

1. sop_orchestrator 呼叫端（:145/158）的 target_user 可得性——其 context/request 有沒有現成角色參數。
2. 未帶 target_user 的實際流量：chat request 的 target_user 是否必填/恆帶——決定 NULL 請求語義選 A 或 B。
3. platform_sop_templates 是否複製進 vendor_sop_items（vendors.py 初始化路徑）——同構缺口掛帳範圍。
4. jgb2 真相兩題（agent 平行）：①對外/對內金流支援的支付方式集合（信用卡真偽——SOP 1256 口徑驗證）；②電費計收模式設定位置＋發票統編開立鏈（file:line）。

## 五、風險

| 風險 | 緩解 |
|---|---|
| 回填誤標（業者向被標 tenant）→ 業者問句誤失 SOP | 37 筆逐筆人工審＋370 筆預判抽樣複核（閘門審表含抽樣欄）；誤標後果=落知識/fallback（誠實不錯位，可逆） |
| tenant 請求命中集合意外變動 | 謂詞用排除語義＋integration 三態釘死＋e2e 租客對照句 |
| 補位知識趕不上過濾上線 | R3.4 已定過渡態（誠實 fallback 可接受）；部署順序知識先於過濾（runbook 註記） |
| SOP 1256「信用卡可繳租」若為錯誤口徑 | 研究 ④ 盤 jgb2 定真相；錯誤則該 SOP 內容修正另案交 vendor，本 spec 補位知識寫真相 |
