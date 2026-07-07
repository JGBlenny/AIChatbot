# 面向化系統脈絡架構（domain-conversational-facets · 後續演進定案）

> 建立：2026-07-01。本檔記錄「per-領域系統脈絡」在實作審視後演進到「**面向化（facet）三層疊加**」的完整邏輯與資料佈局，取代 design.md 元件1/D2 的兩層版本（design.md 變更歷史已標注）。

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

- `services/system_context.py`：
  - `_fetch_base`：`target_user IS NULL AND categories 空`（真通用，避免誤取面向列）。
  - `_fetch_category_chain`：`category_config` 遞迴父鏈（母在前、子在後）。
  - `_fetch_appends`：角色級鍵走 target_user 單層；面向鍵沿父鏈逐層取 categories 列，多層。
  - `get_system_context`：`base ＋ "\n\n".join(appends)`，per-key 快取。
- `services/conversational_engine.py::_domain_key(config)`：`topic_scope.mode=='category'` → `topic_scope.category`；否則 `persona_role`。prepare 兩處呼叫傳它。
- `config_for_category`（chat.py 路由）：**無需改**——config 宣告子面向 `狀態判斷`、知識也掛 `狀態判斷`，精確命中。（若未來知識只掛更細子分類，再補子→母展開。）

## 五、部署順序（migrations）

```bash
# 1) 拆售前出 base（內容保全、冪等、自檢）
psql "$DATABASE_URL" -f database/migrations/split_base_system_context_extract_presales.sql
# 2) 建面向分類骨架（系統合約母 / 狀態判斷子）
psql "$DATABASE_URL" -f database/migrations/add_contract_facet_categories.sql
# 3) 合約系統脈絡兩列（母共用 + 子面向）
psql "$DATABASE_URL" -f database/migrations/seed_domain_contract_system_context.sql
# 4) 合約診斷 config（topic_scope.category=狀態判斷）
psql "$DATABASE_URL" -f database/migrations/seed_conversational_diagnosis_contract_rule.sql
# 5) 合約查詢知識補標 狀態判斷
psql "$DATABASE_URL" -f database/migrations/backfill_contract_knowledge_diagnosis_category.sql
# 套用後清快取（重啟服務，或後台 /conversational-config 任一儲存）
```

## 六、擴一個新面向 / 新領域（零改程式）

- **合約加面向（違約金試算…）**：category_config 加 `違約金`(parent=系統合約)；系統脈絡加一列 `categories=['違約金']`；相關知識掛 `違約金`。問違約金→載 base＋系統合約母＋違約金子。
- **新領域（帳單…）**：category_config 加 `系統帳單`(母)＋子面向；系統脈絡加母/子列；診斷 config topic_scope.category＝該子面向；知識掛該子面向。與合約完全平行，程式不動。
