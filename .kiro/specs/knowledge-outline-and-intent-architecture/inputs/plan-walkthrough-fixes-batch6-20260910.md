# Plan 第六批：line-bot 2026-09-10 回報 #2／#4／#5／#6／#8／#10／#11（業主直接「派」，快速路線）

> 來源：line-bot 第四輪回報（修繕分類 #1 已於 `5ee1a861` 上線）。業主 2026-09-10 裁：先派六條程式層＋#11 環境量測；#9（物件級總覽前置查詢）、#7（排版契約）待點頭；#3 真掛附件需 jgb2 開帳單附件 API（external 目前只有 `GET /bills/{id}`），承諾句納入 #6 禁用。
> 紀律：通用修改不特規、定義不寫例子、程式一筆／文件一筆、不 push；每單元獨佔檔案、fresh verifier 收案；快速路線省略 plan-verifier（業主裁）。

## 單元與獨佔檔案

| 單元 | 內容 | 獨佔檔案 | 波 |
|---|---|---|---|
| A（security-executor） | #2 `bill_due_extend` 缺 `bill_id` 時以物件名稱＋期別（這期／YYYY-MM／幾月／未繳）**決定性**對到帳單：唯一 ⇒ 填 `bill_id` 出卡；多筆 ⇒ 候選 quick_replies（`select:bill:<id>`）；零筆 ⇒ 固定句。工具描述改定義（缺編號時給 `estate_name`＋`period`，⛔ 不反問編號） | `services/agent/tools/confirm.py`、`tools/action.py`（規格描述）、新 `services/agent/bill_period.py`（純函式解析期別→日期區間／未繳）、`tests/unit/agent/test_bill_period_resolve_req.py` | 1 |
| C（executor） | #5 擷取 schema 每欄加「原文片段」（`evidence`：文件上逐字可見的片段，≤40 字）；程式端：片段空／不含該值的關鍵字元 ⇒ 該欄 null（不猜）；`uncertain` 照舊 | `services/agent/document_extract.py`、`tests/unit/agent/test_document_extract_evidence_req.py` | 1 |
| E（security-executor） | #6／#3 承諾：規則檔 1.6.0 加 `document_turn_forbid_terms`（封閉詞表：已掛／已存／已建立／已匯入／要我…匯入／建單 等寫入類動詞與提議句式，按「一類」維護），`verify(..., document_turn: bool=False)`；文件回合命中 ⇒ `FORBIDDEN_TERM`（enforce 與 grounding_observe 皆擋——它屬機敏類）；fixtures 正反 | `services/agent/verifier.py`、`config/agent_verifier_rules.json`、`services/agent/output_schema.py`（`VerifierRules` 欄位）、fixtures、`tests/unit/agent/test_document_turn_forbid_req.py`、`test_verifier_req.py`（版本釘） | 1 |
| B（security-executor） | #4 追問對象加 `photo`／`document`，`outcome.expects` 加 `image`／`file`（`ask_target` 對映）；#8 `attachment_purpose=document` 且無附件 ⇒ 視同一般回合（不套文件回合閘、不注入 G？——G 是正本細目由大綱選；程式只管閘）；#10 會話記「最近解析成功／提到的物件」（`estate_carry`：來源＝查詢工具回傳唯一物件、確認卡物件、pre-lookup 物件名），`repair_create`／`bill_due_extend` payload 缺 `estate_name` 由程式補、照片回合資料段加一句「本對話最近提到的物件：X」（citable=False）；接 E 的 `verify(document_turn=)`；契約表補 expects 新值 | `services/agent/runtime.py`、`services/agent/mcp_facade.py`、`services/agent/output_schema.py`（`ASK_TARGETS`）、`inputs/line-bot-integration-sheet-20260908.md`、`tests/unit/agent/test_estate_carry_req.py`、`test_ask_expects_req.py` | 2（A、E 併回後） |
| 主線 | #11：runbook §20-2 加 `OPENAI_TIMEOUT_S=25`（SDK 逾時＋預設重試）；量 `AGENT_MODEL=gpt-5.6-luna` 走 lb2 劇本一輪比對延遲與分數，相同即切線上 | `docs/deployment-runbook.md`、線上 `.env` | 1 |

## 驗收
- 各單元單元測試正反對照；整合後 agent+audit 全綠；lb2＋線③ 回歸不退步；文件情境①–④重跑（C／E）；#2／#10 用 lb2-bill／lb2-repair 劇本加兩句（「基隆獨立共生公寓雅房九月的房租晚三天繳」「這期的，還沒繳的那張」；照片前先講物件）；fresh verifier。
