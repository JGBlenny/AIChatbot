# JGB 領域地圖（由 jgb2 程式導出；v2 2026-09-14，三代理反證後重寫）

> **用途**：知識大綱粗目（脊椎）的依據。⛔ 不是從我們自己的工具六域反推，是從 jgb2 自己怎麼組織產品導出。
> **查證基準**：`/Users/chenqinghuang/dev/work/jgb2/dev2`（`preview`，HEAD `556d2c651f`，2026-09-10，工作樹乾淨）。幫助中心 92 頁：`/Users/chenqinghuang/dev/work/docs/幫助中心/JGB幫助中心_HTML_交付_20260818/*_zh-Hant.html`。
> ⚠️ 本檔的 jgb2 查證指令要在 dev2 目錄下跑（`cd /Users/chenqinghuang/dev/work/jgb2/dev2`）。
> 🔴 **v1（同日上午）宣稱「四路證據一致、12 領域直接抄」——經三個獨立代理反證，該句不成立**：四路只在五個領域的交集上一致；12 個裡 3 個是硬拆、1 個限單一身分、社宅分支只在三域。v1 的路由查證正則 `[a-z_-]+` 抓不到 `entrustedContracts`，計數也有一半錯。以下全部重算。

## 0. 先講最重要的：粗目對檢索**零影響**，真正在傷召回的是另外兩件事

`FineIndex._key_plan` 只走 `doc.fines()`——**檢索鍵只建在細目**（標題／`approved` 講法／內文句）；`build_canon_toc` 是一張平表、無分組；`kb.get("outline:*")` 只認 `toc` 與完整 `fine.id`。改粗目：分數不變、可見性不變；**同分時拆序用 `fine_id` 字典序，粗目字母在其中 ⇒ K=5 邊界成員可能換**（prospect 現有 15 組同分）。會變的只有 `fine.id` 中段字母 ⇒ `canon_sha256` ⇒ **`.json` 必須重導出否則啟動紅**、索引重建、TOC 行序。

查證：`grep -n "def _key_plan" -A 18 rag-orchestrator/services/agent/canon/fine_index.py`；`grep -n "def build_canon_toc" -A 20 rag-orchestrator/services/agent/canon/canon_assembler.py`。

**🔴 P0-1：pm 正本 68 條講法全部 `proposed`，0 條 `approved`** ⇒ `INDEXED_PHRASING_STATUS = "approved"` ⇒ **一條都沒進索引**。pm 現在只靠 39 個標題＋57 句內文在檢索。（正對照：prospect 189 條全 approved。）
查證：`grep -oE "status: [a-z]+" docs/archive/2026-09/canon-pre-library/property_manager.md | sort | uniq -c`
（⚠️ 2026-09-15 DSP-058 起兩份受眾正本已合併成 `rag-orchestrator/canon/jgb/` 並封存原檔；
本節的數字是**合併前的快照**，故查證指令指向封存版，⛔ 不是現況正本）。

**🔴 P0-2：prospect 有 15 組講法文字逐字掛在 ≥2 個細目下（37/189 條）**。文字同 ⇒ 向量同 ⇒ 餘弦同 ⇒ `scored.sort(key=(-score, fine_id))` 靠字典序拆同分 ⇒ **同一件事的三種切法一起進 top-5，吃掉 K=5 的三格**。最嚴重：`合約範本`／`建立合約`／`簽約邀請`／`線上電子簽約`等六條同時掛 `C/contract-esign-flow`、`C/contract-modify-after-sign`、`C/contract-templates`；`合約能不能匯`等六條同時掛 `B/data-migration`、`G/migration-limits`。（正對照：同腳本在 pm 抓到 0 組。）
查證：見 §7 腳本。

**這兩條與粗目無關，且優先於粗目。**

## 1. jgb2 怎麼組織自己——四路證據，只在交集一致

| 路 | 來源 | 頂層數 | 查證 |
|---|---|---|---|
| A 業者端主選單 | `app/Role.php::roleHasAction` | ~14 頂層（權限決定顯示） | `grep -n "function roleHasAction" app/Role.php` |
| B 方案功能矩陣 | `ApiController.php` `groupList[].fieldLabel` | **6 群**（⛔ 沒有修繕；把「一般匯款」「自動催繳通知」放在帳務群） | `grep -n "'fieldLabel' =>" app/Http/Controllers/ApiController.php` |
| C web 路由 | `routes/web.php` route name 第一段 | ~30 namespace（`admin.*` 205 最大） | `grep -oE "name\('[a-zA-Z_-]+\." routes/web.php \| sort \| uniq -c \| sort -rn` |
| D 幫助中心房東教學 | 92 頁 `<title>` | 9 單元（社宅與物件／合約／帳務同層） | `grep -ohE "<title>[^<]*" *_zh-Hant.html` |

**交集一致的只有五個：物件／合約／帳務／人員團隊／設備。** 其餘每一路各自不同。

路由去重計數（正確版）：bills 50／users 35／contracts 30／estates 29／iots 13／payments 10／communities 9／entrustedContracts 5／repairs 3。

## 2. 脊椎（9 個粗目＋3 條橫切軸）

| # | 粗目 | 證據 | v1 怎麼錯 |
|---|---|---|---|
| 1 | **帳號與身分** | `users.*` 35；`config/role.php` 四身分 | — |
| 2 | **團隊、人員與大房東** | 選單「人員管理」「團隊管理」「大房東管理」三個**都是頂層**；`character.php` 46 個權限 action | v1 把大房東塞進團隊 |
| 3 | **社區與物件**（含刊登／銷售） | `Community` hasMany `Estate`，同一選單群；`estates.open/close/sell-*/istaging` | v1 漏了刊登與銷售 |
| 4 | **委託約**（⚠️ 僅法人房東） | 選單 `allow_role_key => [RULE_KEY_LANDLORD_CORPORATE]`（正對照：物件管理三身分全開）；B 0 項、D 0 頁、路由 5 條；434 條材料裡唯一歸位**只有 1 條** | v1 當通用領域 |
| 5 | **租約** | `contracts.*` 30；`Contract` 12 狀態；D 20+ 頁；歸位測試 **52 條唯一**、最厚 | — |
| 6 | **帳務**（吸收發票、繳費／收款流程、抄表） | `bills.*` 50——**發票 6 條路由全在 `bills.*` 下**、`Invoice` 只 `belongsTo` Bill／Payment；`payments.*` 10 條**全是金流商 callback**、業者面收款設定是 `users.*` 子項；抄表 `bills.current_meter/prev_meter/save_meter` | v1 拆成 6／7／8 三個 |
| 7 | **修繕** | `repairs.*` 3、選單頂層、D 教學07（⛔ B 矩陣 0 命中，門鎖 3 命中正對照） | — |
| 8 | **裝置（IoT）** | `iots.*` 13（門鎖／密碼／廠商／狀態；⛔ 抄表不在這） | — |
| 9 | **幫助中心** | 選單頂層項、`users.help*`、`src/pages/help-center/` | v1 只當材料沒當區塊 |

**降級／移出**：
- **方案與訂閱** → 1 或 2 的細目（選單只是「其他設定／團隊管理」子項；D 0 頁；無 `src/pages`）
- **通知與訊息** → **橫切屬性**：`Notification` 的型別常數就是 `_ESTATE/_CONTRACT/_BILL/_REPAIR/_IOT`——通知自己的分類就是其他領域；歸位測試唯一歸位 1 條、參與多義 20 次
- **差額發票**、**簽核管理**：同為 `FeatureConfigService` flag 閘控——判準一致，都當細目不當粗目
- **控制台**：env `CONTROL_PANEL_ROLE_IDS` 名單閘控；**活動列表**：nthurc 客製——⛔ 不進

**三條橫切軸（細目屬性，⛔ 不是粗目）**：
- **身分**：四身分（租客／個人房東／法人房東／社宅）＋大房東＋團隊成員權限。⚠️ 我們這側 `KNOWN_TARGET_USERS` 四值**沒有「大房東」「社宅」**（正對照：`property_manager` 在）。
- **社會住宅**：身分軸上的一個值＋限地區垂直線（`config/role.php` 唯一有 locale／currency／country 限制的身分）；分支**只在 estates 4／contracts 4／bills 1**，其餘 0（v1 寫「每個領域都有」是錯的）。⚠️ 我們這側**沒有欄位可裝**：`categories` 存在但 `canon_visible` 不讀它。
- **客製客戶**（joerich／nthurc／tonesang）：⛔ 不進通用正本，與 `canon_assembler` 「正本無 vendor 軸」的刻意設計一致。

## 3. 歸位測試（434 條：77 細目標題＋257 講法＋92 幫助中心 title＋8 情境句）

| 材料 | 唯一 | 多義 | 不歸位 | 歧義率 |
|---|---|---|---|---|
| 合計 434（對 v1 的 12 領域） | 203 | 90 | 141 | **30.7%** |

**多義集中在三對，它們各自撐得起粗目，缺的是寫下來的分界線**：

| 領域對 | 次數 | 建議判準 |
|---|---|---|
| 帳務 ↔ 收款金流 | 19 | **錢怎麼算＝帳務；錢怎麼進來＝金流**（「信用卡能不能繳」→金流子題；「帳單裡有什麼」→帳務） |
| 租約 ↔ 帳務 | 15 | **合約條款決定的＝租約；帳單列上的＝帳務**（押金條件→租約；找補金額→帳務） |
| 物件 ↔ 租約 | 14 | **物件本身的屬性＝物件；由合約驅動的狀態＝租約**（標籤／刊登→物件；洽談中／已出租→租約） |

發票、委託約、通知相關的 27 個多義對在 §2 合併／降級後消失；剩餘歧義率約 22%——**這是領域軸的天花板**。同一批材料用「意圖類型」8 類當軸歧義率 7.1%，但意圖軸對這套機制的召回效果同樣是零；它的用處是**篩子**（一次挑出 22 條對話規則＋10 條工作清單）和未來的細目屬性，⛔ 不當粗目。

**141 條不歸位的去向**：

| 這些 | 條數 | 去哪 |
|---|---|---|
| pm F 的內部標籤（`對話規則:X`／`系統脈絡:Y`）＋10 條待裁 | 47 | **移出正本**。🔴 現況 10/10 有 `reviewed`、可見、`citable=True`——內部工作項今天就可被當事實引用 |
| 語氣／禁止項／拒答／數字來源／會話過期（pm D／E） | 15 | `agent_rules.py`——`_POLICY_TEXT_NON_PROSPECT` 已含同題定義句，兩處成文無仲裁；搬進去 +524 字（≈+27%），撞 DSP-028「越長越先轉人」 |
| 銷售話術／適配／競品／導流（prospect A／B／E／F） | 12 | **保留為漏斗粗目**，⛔ 不硬塞進領域——粗目層只能有一條軸，售前的軸是漏斗 |
| 法律／產業文章 | 13 | 不進大綱 |
| 泛詞、操作指令、槽位值 | 26 | 不是知識 |

## 4. 我們現在的東西對上去

⚠️ **現況（2026-09-15 起）**：本節「pm 正本」「prospect 正本」與底下 §5 的舊 id（如
`prospect/C/contract-esign-flow`、`pm/A/repair-ticket-photo-count-limit`）是**當時兩份單檔正本**的
歸位盤查快照——DSP-058／計畫 9.6 後正本已併成一份圖書館形態 `rag-orchestrator/canon/jgb/`
（一目錄＋九架，id 規則 `jgb/<粗目碼>/<slug>`，`canon_parser.parse_canon_dir` 解析），受眾差異
改落在每個細目的 `target_user`。本節的粗目歸位分析結論不受影響（脊椎九碼未變），⛔ 但引用細目 id
字面時請對照 `canon/jgb/CATALOG.md` 找現行 id，不要直接照抄本節的舊字面。

**資料側六域**：`bills`＝帳務（正確，含發票金流）；`contracts`＝租約；`accounts`＝帳號＋團隊；`repairs`／`iot`／`estates`。**缺**：委託約（限法人，低優先）、大房東、幫助中心（`help.read` 工具已有，不是 face）。

**pm 正本 39 細目（A11 B3 C7 D2 E4 F10 G2）→ 9 粗目**：修繕 12（A×11＋C 緊急修繕）、帳務 4（B×3＋C 逾期）、租約 1（C 合約到期）、裝置 1（C 電錶）＝18 知識槽；帳號／團隊／社區物件／委託約／幫助中心 **0**；另 3 條會話規則（C 邊界／查無／收尾）＋D／E 6 條規則移 `agent_rules`；F 10 條移出；**G 2 條文件歸納無粗目可歸**（待裁）。合計 18＋3＋6＋10＋2＝39。
**prospect 38 細目**：C「六大模組」21 條可按 §2 落點；A／B／E／F 留漏斗粗目；D 一半漏斗（定價／試用）一半領域（額度／續約→帳號）；G「現有不足」改用細目 `policy: not_available` 欄（parser 已有，**兩份正本 0 使用**）。

## 5. 「細目＝一個可回答命題」檢驗：77 個裡 33 個違反（42.9%）

- **答兩件事 18 個**：`prospect/C/contract-esign-flow` 標題自列五件事（時效、身分、社宅、批次續約）、`D/subscription-change-renewal` 三件、`pm/A/repair-ticket-photo-count-limit` 兩句答兩個不同問題…
- **兩個細目答同一件事 18 個**：即 §0 P0-2 的 15 組重複講法＋標題層重疊（`A/product-overview`×`A/pain-points`×`A/why-choose-jgb`；pm `D/prohibited-statements`×`E/when-to-decline`×`E/number-data-provenance-rule`）。
- 錯配一條：講法「欠租的房客怎麼找」掛在 `prospect/F/contact-sales-demo`（找真人）下——會把催收查詢拉去命中導流。

## 6. 三種受眾

| 受眾 | 判定 | 要點 |
|---|---|---|
| prospect | 需調整 | 9 領域只能取代 C；A／B／E／F 漏斗粗目必留 |
| property_manager | 需調整（重切） | 29 條搬家可行；D／E 是規則；F 必須先移出 |
| tenant | ⛔ 不照抄 | 團隊／委託約／方案對租客無意義；租客軸是生命週期＋「我的那一筆」（`instance` 型）；且需三處程式改動（`_STATIC_TOC_IDENTITY`、`_AGENT_OUTLINE_AUDIENCES`、`AGENT_TURN_SPEC["stage"]`）＋ front matter 業態重裁——沿用 `business_types: [system_provider]` 實測租客 **0/N 靜默零內容** |

**受眾模型兩條路（⛔ 不選邊）**：A 各自正本（現況，失敗方向＝兩份不一致、git diff 可見）vs B 單一正本＋屬性（失敗方向＝跨受眾外洩、`_no_match()` 刻意不分不可見與不存在 ⇒ **靜默**；要改 4 處刻意設計含不變量 29b）。實測 `canon_visible` 單獨就切得開受眾（prospect 身分對 pm 正本 0/39），機制上 B 的謂詞層做得到，載入層做不到。

## 7. 可重跑

```bash
# P0-2 重複講法
python3 -c "
import re;from collections import defaultdict
ph=defaultdict(set);fid=None
for l in open('docs/archive/2026-09/canon-pre-library/prospect.md',encoding='utf-8'):
    m=re.match(r'^###\s+.+?\s*\{#(\S+)\}\s*$',l)
    if m: fid=m.group(1);continue
    m=re.match(r'^\s+-\s+\{text:\s*\"(.*?)\",',l)
    if m: ph[m.group(1)].add(fid)
d={k:sorted(v) for k,v in ph.items() if len(v)>1};print(len(d),sum(len(v) for v in d.values()))"
# 委託約只開法人（在 dev2）
awk '/委託約管理/{f=1} f&&/allow_role_key/{print; exit}' app/Role.php
# 社宅分支只在三域（在 dev2）
grep -oE "name\('[a-zA-Z0-9_.-]*'" routes/web.php | grep -i social | sed -E "s/name\('//; s/\..*//" | sort | uniq -c
# 通知型別＝其他領域（在 dev2）
grep -oE "const NOTIFICATION_[A-Z_]+" app/Notification.php
```
歸位表原檔（不進 repo）：scratchpad `materials.tsv`／`place.py`／`axes.py`。

## 8. 待裁（業主）——動粗目前必須先定的

1. **粗目軸**：領域 9 個照 §2，售前另留漏斗粗目（A／B／E／F）並列——接受「一份正本兩條軸並列」，還是售前整份走漏斗軸？
2. **pm F 十條**：移出正本／撤 `reviewed`（只剩空標題）／維持（＝接受可被引用）。
3. **pm D／E 六條規則**：搬進 `agent_rules.py`（接受 +524 字與轉人傾向）／留在正本（接受兩處成文）。
4. **受眾模型**：A 各自正本 vs B 單一正本＋屬性。選 B 要連裁 `canon_visible` 加 audience 比對（改不變量 29b）與 `build_outline` 先套可見性再算預算。
5. **社宅**：過濾軸（要改 `canon_visible`、擴 `KNOWN_TARGET_USERS`——它同時是 SQL 謂詞值域）還是只當標籤。
6. **租客線**：開不開；開則 front matter 業態必須重裁。
7. **P0 兩條的執行順序**：先修重複講法＋pm 講法審核，再動粗目——還是一起做（細目 id 反正都要改名、`.json` 都要重導出、索引都要重建，分兩次是付兩次遷移成本）。
