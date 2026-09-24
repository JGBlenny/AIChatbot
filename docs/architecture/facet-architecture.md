# 面向化系統脈絡架構（domain-conversational-facets · 後續演進定案）

> 建立：2026-07-01。本檔記錄「per-領域系統脈絡」在實作審視後演進到「**面向化（facet）三層疊加**」的完整邏輯與資料佈局，取代 design.md 元件1/D2 的兩層版本（design.md 變更歷史已標注）。

> 🔴 **2026-09-12 對碼更正（前一版檔頭的核心斷言是錯的）**：前一版寫「`category_config`、
> `conversational_config`、`grounding_scope`、`persona_role`、`topic_scope` 仍在用——
> 新線繼續讀這幾張表與這幾個鍵」。**逐鍵掃 `services/agent/**`（排除測試）的實測是：**
>
> | 鍵 | `services/agent/` 內 | 實際讀者 |
> |---|---|---|
> | `grounding_scope` | ⛔ **0** | `services/instance_applicability.py`（不變量 10）、`tools/audit_config.py`（稽核） |
> | `persona_role` | ⛔ **0** | `conversational_config._config_from_row` 解析後無下游；另 `tools/audit_config.py`（稽核） |
> | `topic_scope` | ⛔ **0** | 同上 |
> | `answer_rules`／`cta_rules` | ⛔ **0** | 同上 |
> | `required_slots` | ⛔ **0** | **全 repo 非測試程式 0 支** |
> | `category_config` | ⛔ **0** | 面向父子骨架無消費者 |
> | `conversational_config`（模組） | ✅ 5 支 | **但只 import `effective_handoff_channel`／`effective_handoff_message`／`config_for_target_user`**——⛔ 不是本檔講的那些配置鍵 |
>
> （查證法：`ast`／字串掃 `rag-orchestrator/**/*.py` 去掉 `tests/`；正對照
> `effective_handoff_message` 在 agent 內 5 支命中 ⇒ 掃描器可用。）
>
> ⇒ **本檔描述的面向骨架已無消費者。** 仍有價值的是**資料佈局規則與踩坑記錄**
> （§三、半形/全形冒號、`target_user` 必須＝`persona_role` 的理由），
> ⛔ 不是「照著設定就會生效」。下文引用的
> **舊鏈執行程式**（`services/conversational_engine.py`、`services/system_context.py`、
> `routers/chat.py`、`services/jgb/repair_prefill.py`）已隨舊 REST 對話鏈於
> 2026-09-11 整批砍除（commit `7c905408`／`10116570`，見 `.claude/DECISIONS.md`
> DSP-046）。逐段標記見下；`get_system_context` 一類的系統脈絡組裝邏輯，新線
> 對應位置在 `services/agent/outline.py`／`services/agent/prompt_assembler.py`
> （具體對應關係未逐行核對，僅供下一步查找起點）；`repair_prefill.py` 的
> API 預填機制**沒有**新線對應物——agent 路徑改由模型呼叫工具即時取值，
> 不再有程式先行預填槽位這一步，這是能力形態的改變而非搬家。

## 〇、三層責任分層（與母圖 §0 對齊，2026-08-25）

本檔其餘章節談的是**面向怎麼組裝與執行**；先把它與另外兩層分開，否則「進場」很容易
被讀成「這個面向已經對這句話負責」。

```text
① Entry / Routing Hint    誰**被提出**——檢索知識的 categories ＋ 門檻，或 trigger_facet_key 直達
② Face Responsibility     這個面向**該不該承擔本輪 query**——persona 的【本輪範疇 scope】契約
③ Execution               進場後**怎麼做**——本檔第二～七章的內容
```

```text
**Face entry ≠ responsibility ownership。**
`scope=stay/switch` 屬**第②層的責任判定**，不是 entry evidence，也不能反推 entry 是否正確。
進場成立只代表「有人／有檢索證據提出了這個面向」。
```

⚠️ 已證實：**第①層不消費第②層的契約**——entry nomination 不讀 responsibility contract，
兩者唯一的間接耦合是 knowledge-row 上人工維護的 `categories`
（見母圖 §0.3 與 `.kiro/specs/face-exit-before-grounding/`）。
**本檔刻意不畫「應有的 bridge」**——那屬 governance 尚未做的 normative decision。

⚠️ `PREENTRY_ROUTABILITY_GATE`（現行 `false`）把第②層的判定提前到進場之前，但**不是**
「同一判定提前」：它以 `cfg.key` 取 system context，而 in-session 用的是
`_domain_key(config)`（`topic_scope.category`）——**evaluation context 不同源**（實測 digest 不同）。

---

## 一、問題與演進

初版設計把系統脈絡做成「base（target_user NULL）＋ 領域 append（target_user）」兩層，領域鍵＝`persona_role`（=target_user）。實作審視發現三個問題，逐一修正：

1. **base 其實是「售前系統脈絡」**：現有 `target_user IS NULL` 那列（id 3622，`question_summary='售前系統脈絡'`）內容為售前導向（§5b 競品協定、§6 CTA 出口、§7 功能推薦索引）。疊加後合約診斷仍吃到售前銷售脈絡——正是本 spec 要解的缺口 2。
   → **拆分**：把該列切成「真通用 base（§1–5 產品定位/客群/模組/語氣/合規）」＋「售前 append（§5b/6/7，target_user=['prospect']）」。售前疊加＝原文（不回歸）；其他領域不再吃售前。migration：`split_base_system_context_extract_presales.sql`（切在「## 5b」邊界，內容保全自檢）。

2. **領域鍵用 target_user 會撞鍵**：同一角色（property_manager）未來會有多個診斷領域（合約、帳單…），全掛 property_manager → 系統脈絡/persona 互蓋。能唯一區分領域的是**分類（category）**，不是角色。
   → **領域鍵改＝診斷 config 的 `topic_scope.category`（分類值）**。角色級面向（售前 `mode:'all'`）仍用 persona_role/target_user。

3. **合約整份每輪常駐會越長越貴**：合約知識會長（狀態、違約金、續約…），全塞每輪注入浪費 token。
   → **面向化**：把領域知識拆成「母分類共用 ＋ 子分類面向」，**只載入當下問到的面向**。

（另修：半形/全形冒號不一致——config/backfill 用半形 `條件診斷:合約`，category_config 與真知識用全形 `條件診斷：合約`，路由對不上。改採真實資料驅動的分類名。）

## 二、面向模型（三層疊加）

```
通用 base（category='系統脈絡'，無 target_user、無 categories）        —— 每輪必注入
  └ 母分類『系統合約』(categories=['系統合約'])：合約領域共用框架        —— 命中合約任一面向都載
        └ 子面向『狀態判斷』(categories=['狀態判斷'])：各階段下一步/可否操作 —— 只有問狀態才載
              （未來）違約金試算面向、續約面向… 各一列，同理

system_md = base ＋（沿領域鍵在 category_config 的父鏈，母共用在前、子面向在後）
```

- **領域鍵**＝`topic_scope.category`＝子面向值（如 `狀態判斷`）。
- `get_system_context('狀態判斷')` 沿 `category_config` 父鏈（`狀態判斷`→parent `系統合約`）逐層取 `categories` 命中的系統脈絡列，**母共用在前、子面向在後**，疊加於 base 之後。
- **售前**領域鍵＝`prospect`（角色級）→ 走 `target_user`，維持單層（base＋售前 append），內容＝原 3622（不回歸）。

**省 token**：面向一多時每輪只載「base＋母共用＋命中的那個子面向」，不是整個領域。實測合約問狀態＝base560＋母994＋子372≈1930 字，遠低於 4500 上限。

## 三、資料佈局（誰標什麼）

| 資料列 | category | 標記 | 內容 |
|---|---|---|---|
| 通用 base | 系統脈絡 | target_user NULL、categories 空 | 產品定位/客群/模組/語氣/合規（真通用） |
| 售前 append | 系統脈絡 | target_user=['prospect'] | 競品協定/CTA/功能推薦索引（售前專屬） |
| 母『系統合約』 | 系統脈絡 | categories=['系統合約'] | 狀態模型/12 里程碑/續約父子鏈/欄位語義 |
| 子『狀態判斷』 | 系統脈絡 | categories=['狀態判斷'] | 各階段下一步/可否動作前提 |
| 合約診斷 config | 對話規則 | target_user=['property_manager']、metadata.topic_scope.category=`狀態判斷` | persona＋grounding_scope(api) |
| 合約查詢知識 | （原分類） | categories 含 `狀態判斷` | 觸發診斷路由（config_for_category 命中） |
| category_config | — | `系統合約`(母,parent NULL)、`狀態判斷`(子,parent=系統合約) | 面向父子骨架 |

## 四、程式（皆讀設定，與名稱無關）

- `services/system_context.py`（⚠️ 已隨舊鏈於 2026-09-11 退役，見檔頭註記）：
  - `_fetch_base`：`target_user IS NULL AND categories 空`（真通用，避免誤取面向列）。
  - `_fetch_category_chain`：`category_config` 遞迴父鏈（母在前、子在後）。
  - `_fetch_appends`：角色級鍵走 target_user 單層；面向鍵沿父鏈逐層取 categories 列，多層。
  - `get_system_context`：`base ＋ "\n\n".join(appends)`，per-key 快取。
- `services/conversational_engine.py::_domain_key(config)`（⚠️ 已隨舊鏈於 2026-09-11 退役，見檔頭註記）：`topic_scope.mode=='category'` → `topic_scope.category`；否則 `persona_role`。prepare 兩處呼叫傳它。
- `config_for_category`：🔴 **2026-09-12 對碼：函式本體與 `by_category` 索引都還在
  （`services/conversational_config.py`），但呼叫端只剩兩支測試
  （`tests/unit/conversational/test_config_for_category_req.py`、`test_api_config_roundtrip_req.py`），
  `services/**` 零消費。** 前一版寫「**無需改**」會讓人以為它仍在路由——它沒有。
  （正對照：同檔的 `config_for_target_user` 有生產呼叫端 `services/agent/tools/handoff.py`
  ⇒ 不是掃描器壞了。）

> 🔴 **本節主角 `狀態判斷` 不是現行的 face。** 新線的 face 是一個封閉枚舉，值域由六張
> `*_FACE_BUILDERS` 註冊表的鍵**現算**（`mcp_facade._jgb2_spec(domain, sorted(builders.keys()))`），
> 共 **15 個**：帳單異常／條件診斷：帳單／滯納金／發票／繳費金流排障（bills 5）、
> 合約異動／簽署排障／續約／退租收尾（contracts 4）、團隊成員權限／登入排障（accounts 2）、
> 電表排障（meters 1）、物件現況診斷（estates 1）、修繕分類／修繕進度（repairs 2）。
> **`狀態判斷` 不在其中**，且 `tests/unit/conversational/test_face_builders_registry_req.py`
> 明文釘住「『狀態判斷』永不註冊 → 走 fallback」。本檔 §二／§三以它為例，
> 讀作**資料佈局的示範**，⛔ 不是可用的 face 名稱。

## 五、部署順序（migrations）

```bash
# 1) 拆售前出 base（內容保全、冪等、自檢）
psql "$DATABASE_URL" -f rag-orchestrator/database/migrations/split_base_system_context_extract_presales.sql
# 2) 建面向分類骨架（系統合約母 / 狀態判斷子）
psql "$DATABASE_URL" -f rag-orchestrator/database/migrations/add_contract_facet_categories.sql
# 3) 合約系統脈絡兩列（母共用 + 子面向）
psql "$DATABASE_URL" -f rag-orchestrator/database/migrations/seed_domain_contract_system_context.sql
# 4) 合約診斷 config（topic_scope.category=狀態判斷）
psql "$DATABASE_URL" -f rag-orchestrator/database/migrations/seed_conversational_diagnosis_contract_rule.sql
# 5) 合約查詢知識補標 狀態判斷
psql "$DATABASE_URL" -f rag-orchestrator/database/migrations/backfill_contract_knowledge_diagnosis_category.sql
# 套用後清快取（重啟服務，或後台 /conversational-config 任一儲存）
```

## 六、擴一個新面向 / 新領域（🔴 「零改程式」已不成立）

🔴 **2026-09-12：⛔ 不得照本節做。** 本節寫的四件套（`category_config` 加父子、
系統脈絡加列、診斷 config 的 `topic_scope.category`、知識補標）在
`services/agent/**` **全部 0 消費者**——做完四支 migration，**不會有任何程式讀它們**
（逐鍵實測見本檔檔頭的對照表；正對照：同檔 `config_for_target_user` 在
`services/agent/tools/handoff.py` 有生產呼叫端 ⇒ 不是掃描器壞）。

2026-09-12 的對抗性演練裡，一位只讀文件的工程師正是照本節排了**一整天**做那四支 migration。

**現行要加一個 face，實際要動的是**（見 `SYSTEM_ARCHITECTURE.md` §3）：
在 `services/jgb/<domain>.py` 的 `*_FACE_BUILDERS` 加鍵＋寫 builder。
⚠️ 但**加鍵 ⛔ 不等於加能力**——face 只選 builder、⛔ 不選資料源（資料源寫死在
`services/agent/tools/jgb2.py::query_<domain>`），builder 簽名是**單列**（跨列彙總表達不出來），
參數列由測試釘死。⚠️ 且**六個域的隔離不對稱**，挑錯域承載財務資料會外洩——
兩張表都在 `SYSTEM_ARCHITECTURE.md` §3。

以下為**歷史記錄**（舊鏈時代的作法，⛔ 不是現況）：

- **合約加面向（違約金試算…）**：category_config 加 `違約金`(parent=系統合約)；系統脈絡加一列 `categories=['違約金']`；相關知識掛 `違約金`。問違約金→載 base＋系統合約母＋違約金子。
- **新領域（帳單…）**：category_config 加 `系統帳單`(母)＋子面向；系統脈絡加母/子列；診斷 config topic_scope.category＝該子面向；知識掛該子面向。與合約完全平行，程式不動。
