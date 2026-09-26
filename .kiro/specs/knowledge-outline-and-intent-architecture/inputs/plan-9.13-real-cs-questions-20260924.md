# Plan 9.13：用真實客服紀錄驗「口語對到細目」這一層（量尺＋架構比較）— 2026-09-24 第 3 稿

> 業主 2026-09-24：提供 `5.3.4_客服_ QA, FB, 來電.xlsx`（「看看這份有沒有幫助」）→ 盤點後「好」（照建議寫計畫）→ 資安審查 P0／P1 後「照建議」：**題目文字不進 git**（決定一 (a)）。
> 起因：Plan 9.11 撤 A、9.12 量尺天花板（hit@5 0.979，題目由內文改寫）、講法入索引實驗救回 1/5；2026-09-07 業主問法正本量測講法臂僅 +3.9 點 ⇒「口語由檢索層吃（講法多向量）」這個設計假設未被證明（`../HANDOFF-20260923.md` §9–§10）。
> ⛔ 本 Plan 不動 runtime／selector／正本內容；產物是真實題集（題目文字在 repo 外）、各組比較數字與架構建議。⛔ 核可前不抽取、不派代理、不外送、不花錢。
> 第 2 稿＝第 1 稿＋security-reviewer（2026-09-24）P0×1／P1×3／P2×6／P3×3 全數處置（§9）。第 3 稿＝plan-verifier 第 1 輪 REVISE 5 條 P2 全 FIX（§10）。

## 0. 受測物與命題

- **受測物**：`CandidateSelector.select`（K=5）在新三層正本（`canon/jgb`，sha `9b67e763…`）的全審暫存副本上（`tools/canon/ruler_eval.py` 以 tempfile 自建）；比較組只在暫存副本或量測程序內變動。
- **命題**
  - P1（現況）：真實「該由知識回答」的客服提問，前 5 名命中率；答不出的有多少是**正本沒有**（覆蓋）、多少是**有但找不到**（檢索）。
  - P2（原架構假設）：以真實說法寫成的講法進索引，能讓留出集命中率明顯上升。
  - P3（替代層 a）：embedding 取前 40 名、由既有 reranker（`aichatbot-semantic-model` `/rerank`）重排取前 5。
  - P4（替代層 b）：一次程式側小模型呼叫，讀提問＋57 粗目目錄選 ≤3 粗目，候選限於這些粗目。
- **證得了**：真實業者操作提問上的覆蓋率與命中率；各組相對差異；依「原話／客服摘要」分層。
- **證不了**：回答品質；兩半近似題造成的 A2 高估（以 §4 近似分層控制，只在「無近似素材層」下結論）；租客（正本無租客細目）；售前（樣本少，只報描述）；線上流量頻率（客服紀錄是**有來問的**）；also_ok 未窮盡 ⇒ 命中率偏低（同 9.12 §0 ⑤）。

## 1. 材料（原檔 ⛔ 不進 repo）

- 來源：`~/Downloads/5.3.4_客服_ QA, FB, 來電.xlsx`，sha256 `d969d3bb4dbc2fe55db30f2d9c08bf38e40198d95ac1595c8d6412f86be58e20`。
- 納入（依分頁欄位決定性篩；**只讀白名單欄位**）：
  | 分頁 | 條件 | 讀取欄（提問／替換字典） | 文字形態 |
  |---|---|---|---|
  | A.客戶回饋&建議 2.0 | `結論 = C.使用者操作釐清` | 遇到問題、分類／商家客戶、user、回報人 | 客服摘要 |
  | A.客戶回饋&建議 | `結論 ∈ {客戶操作問題, C.使用者操作釐清}` | 遇到問題、分類／商家客戶、user、回報人 | 客服摘要 |
  | C-4.QA list | 全部 | 遇到問題、大分類／商家客戶、user、回報人 | 原話為主 |
  | QA-old | 全部 | Q、使用者身份／姓名 | 原話為主 |
  | C.社群 | 分類 `a.產品&潛在客戶`／`d.陌生訪客`／`e.個人屋主…` | 遇到問題／user、回報人 | 客服摘要 |
  - 「替換字典」欄的值只在記憶體中用來遮蔽，⛔ 不寫入任何檔案、⛔ 不印出。
- 排除：Bug、異動單、需求／建議、租客分類、其餘分頁；QA-old `使用者身份＝租客` 列。
- **受眾指派（決定性）**：A 系列、C-4、QA-old（非租客）⇒ `property_manager`；C.社群 a／d／e ⇒ `prospect`。
- 去重：遮蔽後 NFKC 逐字相同 ⇒ 留最早；字元 bigram Jaccard ≥ 0.8 ⇒ 同題留最早。
- 形態標記：以分頁定；判者可把「詢問：」「反映：」式改標摘要，⛔ 不反向。

## 2. 個資與資料流（⚠️ 風險觸發）

**資料流與外送點（業主須一次授權「遮蔽後文字」外送）**：
```
原檔（~/Downloads，只讀）
  └─ 抽取＋遮蔽（同一程序，記憶體內；⛔ 原文不落地、⛔ 不印內容）
       └─ 遮蔽後題目 → ~/jgb-archive/ruler-9.13/（repo 外，權限 600）
            ├─ 獨立寬掃描器（零未裁決命中）→ 業主看全部命中＋隨機 30 題
            │     └─（通過後才准以下外送）
            ├─ Anthropic：判者、審題者代理（只收遮蔽後文字）
            ├─ OpenAI：embedding（A0–A3 每題＋A2 講法素材；`embedding-api`→`text-embedding-3-small`；Redis 以 md5 快取向量 24h，不存原文）
            └─ OpenAI：gpt-5-mini（A4，另行支出授權）
       repo 只收：id、hash_norm(q)、gold、also_ok、audience、形態、分類、split、near（⛔ 無題目文字）
```
- **遮蔽器**：唯一入口 `.claude/skills/outline-curation/scripts/phrasing_map.py::deidentify`（Email、LINE id、金額＋日期、電話、車牌、合約／帳單號、統編、地址、社區／大樓名、人名＋稱謂、房號、`_pre_normalize`）。前置：替換字典（`商家客戶` 值及去「股份有限公司／有限公司／公司」的核心詞、`user`／`回報人`／`姓名` 值）逐字替換。後置補充規則：身分證 `[A-Z][12]\d{8}` 與「身分證／末四碼」片段、無 scheme 網址（`drive.google`／`docs.google`／`line.me`／`lin.ee`／`bit.ly`／`reurl`）、不帶 @ 的 LINE ID（「line id：」「賴：」後接字串）、與人連結的單獨金額（「押金 25000」類）、拆寫 email（「at gmail」）。
- **獨立寬掃描器**（與遮蔽器規則不同源，比它寬）：任何 ≥4 碼數字、`@`、`http|www|\.com|\.tw|drive`、先生／小姐／太太／經理／老闆／姐／哥、路街巷弄號樓、`[A-Z]\d{9}`、替換字典殘留。正對照：塞 `0912345678`、`demo@jgbsmart.com`、`王小姐`、`中山路 1 號` 必命中；缺讀或正對照未中 ⇒ 非 0 退出。**每一筆命中都由業主裁決**（遮蔽或放行），另再隨機抽 30 題；判者回報的疑似個資 ⇒ 回遮蔽器重遮＋重掃。
- **主 session 輸出紀律**：抽取／遮蔽／掃描程式 stdout 只印筆數、sha、不透明 id；例外只印型別名、⛔ 不印 cell；⛔ 不 Read／cat 任何含文字的中間檔（給業主看的抽樣另存 repo 外檔、由業主自己開）。
- **回溯不可能的欄位 ⛔ 不帶**：列號、時間戳、客服人員、原分頁名以外的來源線索；id＝`md5(seed+遮蔽後文字)` 前 12 碼。
- **保存與刪除**：`~/jgb-archive/ruler-9.13/` 保留到本 Plan 結案＋業主裁定；結案時刪除判者輸出、抽樣檔；刪除前後各列一次目錄。代理 transcript（遮蔽後文字）存在 `~/.claude/projects/...`，接受並記錄。
- ⚠️ 本 session 盤點時的預覽已把少量未遮蔽姓名／Email／LINE ID 印進 transcript（2026-09-24，已記錄、無法撤回）；原文抽取檔 `scratchpad/cs/sheets.json` 已刪除。

## 3. 可答性與標準答案（判者看不到檢索輸出）

1. **可答性**（封閉集）：`knowledge`（操作／機制）／`data`（要查某筆實際資料）／`bug_or_change`（故障、異動、客製）／`out_of_scope`（非系統、租客、課程）。只有 `knowledge` 進量尺。
2. **標準答案**：同 9.12 跨架方法，但判者只能從 `target_user` 含該題受眾的細目中選；答得了 ⇒ `fine_id`＋`also_ok`；**該受眾可見的正本沒有答案 ⇒ `no_canon`**，進覆蓋缺口清單、⛔ 不進命中率分母。凍結前以程式驗每題 gold 對指派身分可見（全審副本），不可見 ⇒ 退回判者重判該題（⛔ 不讓量測整批中止）。
3. **審題**：審題者抽 ≥ 20% 複核；分歧交業主。
4. **業主抽查**：md5 抽 30 題（遮蔽後文字＋gold 標題，repo 外檔）核可。

## 4. 切分與凍結（題目文字不進 git）

- **唯一正規化**：新增 `scripts/audit/checks/canon_phrasing_frozen_disjoint.py::hash_norm(text)`＝`sha256(NFKC → 去全部空白 → 去句尾標點（同 phrasing_map.norm 的 _TRAILING_PUNCT_RE）)`；產 index、`ruler_eval.py --text-file` 驗證、checker 三處 ⛔ 只准 import 這一個符號。
- `knowledge` 且有 gold 的題，依 `md5("real-9.13-split:" + 遮蔽後文字)` 升冪，形態分層各前 50% ＝**留出集**，其餘＝**講法素材**。留出集 < 150 ⇒ INCONCLUSIVE。
- **近似分層（先定）**：切分後在記憶體內算每題留出題對全部講法素材的最大字元 bigram Jaccard；≥ **0.5** ⇒ `near`、否則 `far`；index 只記標記，⛔ 不記對應題。
- **repo 內**：`inputs/ruler-9.13-index.json`＝`{_meta, items:[{id, q_sha256, fine_id, also_ok, audience, form, category, split, near}]}`（⛔ 無 `q`）；`_meta` 記原檔 sha、repo 外文字檔路徑與 sha、種子、正本 sha、`also_ok_note`。
- **repo 外**：`~/jgb-archive/ruler-9.13/questions.json`＝`{id, q}`（遮蔽後）；`ruler_eval.py` 加 `--text-file`，以 id 併回並逐題驗 `hash_norm(q) == q_sha256`，不符 ⇒ 大聲失敗。
- **容器讀取**：量測一律 `docker compose -f docker-compose.dev.yml run --rm -v ~/jgb-archive/ruler-9.13:/ruler_text:ro …`（唯讀臨時掛載、容器隨 `--rm` 銷毀、⛔ 不 `docker cp`、⛔ 不放 repo 工作樹任何路徑）；量測後 `git status --porcelain` 不得出現含題目文字的新檔。
- **不變量 34 延伸**：manifest 登記 `ruler-9.13`（path＝repo 內 index、shape＝`items[].q_sha256`）；checker 加「hash 集合」比對：正本講法 `hash_norm(text)` ∩ 留出集 `q_sha256` ＝∅；self-test 加三案：不撞 ⇒ PASS、同句 ⇒ FAIL、**講法「X？」或中間有空白 vs 題目 `hash_norm(X)` ⇒ FAIL**。⛔ 不登記成 `available:false`（會被跳過）。

## 5. 比較組（同一留出集、同一量測程式）

| 組 | 內容 | 外送 |
|---|---|---|
| A0 | 現況（標題＋內文句） | OpenAI embedding |
| A1 | ＋代理講法 1,670 條（暫存副本 approved） | 同上 |
| A2 | ＋真實講法：講法素材每題（遮蔽後）掛到其 gold 細目（暫存副本 approved） | 同上＋講法素材 |
| A3 | A0 ＋ reranker 第二層（前 40 → **直接呼叫** `/rerank`（⛔ 不經 `SemanticReranker.rerank`，它失敗會靜默回原順序）→ 前 5；surface＝細目標題＋內文） | embedding；reranker 為本機容器 |
| A4 | A0 ＋ 意圖對應粗目（gpt-5-mini low，一次呼叫，≤3 粗目，候選限其細目、不足補 embedding 前 5） | OpenAI gpt-5-mini；估 < US$0.15，**另行支出授權** |
| A2+A3 | 兩者合用 | 同上 |

- **A3 大聲失敗**：逐題驗 HTTP 200、`results` 長度＝送出筆數、每筆有分數；非 200／逾時／缺分 ⇒ 非 0 退出；正對照＝前 20 題中至少 1 題重排順序 ≠ embedding 順序，否則判 reranker 未生效、停；逐題記延遲（只報、不作判準）。
- **A2 掛講法**：來源標籤 `real-9.13`（⛔ 不用 `traffic:`）；句中引號改全形或剔除以符合 `PHRASING_ITEM_RE`；撞 `_check_phrasing_unique` 的重複句只掛第一個 gold；A2 亦跑 9.12 量尺回歸守門。
- 暫存副本一律 `tempfile`；各組前後比對 repo 正本 sha 不變、`git status --porcelain rag-orchestrator/canon` 為空；副本路徑缺 ⇒ 大聲失敗。
- 指標：留出集 hit@5（gold ∪ also_ok）、粗目命中；依形態、分類拆；9.12 量尺當回歸守門。量測輸出 rows ⛔ 不帶 `q`。

## 6. 判準（先定、看結果不改）

- **P2 成立**：A2 − A0 ≥ **10 點**，**且 `far` 層 A2 − A0 也 ≥ 10 點** ⇒ 建議補「真實說法 → 講法 → 核可 → 索引」閉環（另立 Plan，見 §8）；只有 `near` 層達標 ⇒ 報「重複題效果」，⛔ 不當 P2 成立。各組一律分 `near`／`far` 報。
- **替代層採用**：A3 或 A4 − A0 ≥ **10 點**，且 9.12 量尺掉 ≤ 2 題 ⇒ 建議升格正式一層（另立實作 Plan）。
- 皆 < 10 點 ⇒ 報告交業主，⛔ 不自行擴大實驗。
- `no_canon` 比例 ≥ 20% ⇒ 另報「正本缺口大於檢索」，清單交 81 題類待裁。

## 7. 執行、停止、回滾

- 主 session：抽取／遮蔽／掃描／去重／切分（scratchpad 一次性腳本）、各組量測；代理：可答性＋gold 判者、審題者（不同代理，Hard rules：只收遮蔽文字、只讀指定檔、不跑 git／docker）。
- **停止**：掃描有未裁決命中 ⇒ 停在**第一次派代理／第一次 embedding 之前**；`knowledge` 題 < 300 ⇒ 停、交業主；量測工具非 0 退出 ⇒ 停；A4 未授權 ⇒ 只跑 A0–A3；repo 正本 sha 變動 ⇒ 停；**reranker 降級、逾時或正對照未過 ⇒ 停（A3 不出數字）**；`git status` 出現含題目文字的檔 ⇒ 停。
- **回滾**：manifest 撤 `ruler-9.13`＋checker 的 `hash_norm`／hash 分支與 self-test＋刪 repo 內 index；`ruler_eval.py --text-file` 與 A2／A3／A4 量測分支可獨立留下或一併撤；repo 外目錄依 §2 刪除。題目文字從未進 git ⇒ 無公開撤回問題。

## 8. 範圍外（另案）

- 真實講法進 repo 正本：另立 Plan；講法只經 `deidentify` 產生、以 Edit/Write 寫入觸發 `outline_gate.check_identifiers`、業主逐條核可並優先改寫成一般化說法、與留出集以 §4 hash 檢查不相交、來源欄 ⛔ 不留可回溯資訊。
- 公開 repo 內既有正本講法的去識別程度審查（`fine_index.py` 註記講法源自真流量問句）。
- repo 公開與否：業主權限，本 Plan 不預設。

## 9. security-reviewer（2026-09-24）處置

| # | 審查 | 處置 |
|---|---|---|
| P0 | repo 公開，題集進 repo＝公開發布 | 業主選 (a)：題目文字不進 git，repo 只放 hash／gold（§4） |
| P1-a | A0–A3 也外送 OpenAI（embedding） | §2 資料流列全外送點；業主一次授權遮蔽後文字外送；`ruler_eval.py`／Plan 9.12 的「本機」誤述已更正 |
| P1-b | 掃描關卡擺在進 repo 前 | 前移到第一次外送前（§2、§7） |
| P1-c | 遮蔽清單不足 | 改用 `deidentify`＋替換字典＋補充規則（§2） |
| P2-d/e | 掃描循環驗證、30 題抽樣太弱 | 獨立寬掃描器＋正對照；每筆命中業主裁決＋隨機 30（§2） |
| P2-f | 終端輸出／transcript 外洩 | 輸出紀律（§2）；已發生的預覽洩漏如實記錄 |
| P2-g | A2 暫存副本誤寫正本 | tempfile＋前後 sha＋git status（§5） |
| P2-h | 真實講法進正本需獨立閘門 | §8 另案條件 |
| P2-i | 題集不進 git 時不變量 34 靜默失效 | hash 比對延伸（§4） |
| P3-j/k/l | 保存刪除、可回溯欄位、法遵 | §2 保存／刪除與不帶可回溯欄位；法遵為推測、交業主 |

## 10. plan-verifier 第 1 輪（第 2 稿）REVISE 5 條 P2 ⇒ 全 FIX

| # | 審查 | 處置 |
|---|---|---|
| 1 | hash 兩側正規化不同（`phrasing_map.norm` 去句尾標點／checker `_norm` 不去）⇒ 檢查靜默失效 | §4 唯一符號 `hash_norm`，三處只准 import；self-test 加「X？」案 |
| 2 | `SemanticReranker.rerank` 失敗靜默回原順序 ⇒ A3 假否定 | §5 直接呼叫 `/rerank`、逐題驗、正對照；§7 降級即停 |
| 3 | 容器讀不到 repo 外文字檔 | §4 唯讀臨時掛載 `--rm`、⛔ docker cp／repo 路徑；量測後 git status 檢查 |
| 4 | 兩半近似題使 A2 高估 | §4 近似分層（Jaccard 0.5）；§6 P2 須 `far` 層也達標；§0 證不了補混淆 |
| 5 | index 缺 `audience`、指派未定 | §1 決定性指派；§3 判者只從可見細目選、凍結前驗可見性、不可見退回重判；§4 index 加 `audience` |

## 11. 執行紀錄

- 2026-09-24 業主「核可 AUTO」（計畫＋遮蔽後文字外送 Anthropic／OpenAI；A4 未授權 ⇒ 只跑 A0–A3）。
- 抽取＋遮蔽（`deidentify`＋替換字典 878 詞＋補充規則，≥4 碼數字一律遮）：符合 1,102 ⇒ 去重（逐字 144、近似 1）⇒ **957 題**（原話 219／摘要 738；業者 918／售前 39）；檔 `~/jgb-archive/ruler-9.13/masked.json`（600）。
- 獨立掃描：正對照 4/4；命中 59 題（地址樣式 20、字典殘留 18、稱謂 18、`@` 4）。
- **業主 2026-09-25 裁：「有個資也還好吧，盡量就好」** ⇒ 關卡一改為盡力措施：**全部剔除 59 題掃描命中**、免逐筆裁決與隨機 30 題抽查；重掃 898 題 0 命中（`masked_clean.json`）。⚠️ 題目文字不進 git（P0 決定一 (a)）不受此裁影響、照舊。
- 判者三批（898 題）：knowledge 391／bug_or_change 324／data 136／out_of_scope 47；pii_flag 64（凍結時整題剔除）。⚠️ 判者間口徑不一：data 與 bug_or_change 的切分各批差很大（批 2 data 105、批 3 data 18），**非 knowledge 類的細分不得下結論**；knowledge 三批相近（124／135／132）。
- 乾跑合併：knowledge 有 gold **200**、**no_canon 181**（knowledge 且未剔除者的 47.5% ≥ 20% ⇒ 依 §6「正本缺口大於檢索」）、gold 不可見 0；留出集 **101 < 150 ⇒ 依 §4 架構比較記 INCONCLUSIVE**（只報描述）；近似分層 101 題全 `far`。
- 判者違規寫出暫存檔（scratchpad 根目錄 `j*.py`／`questions_*.txt`／`titles_*.txt`／`decisions.py` 等 19 檔，含遮蔽後題目）⇒ 已刪；刪後以 900 個 id 掃 `/private/tmp` 0 命中（正對照：`~/jgb-archive/ruler-9.13` 9 檔命中）。批 3 回報中引用了殘留人名（違反 brief），未轉述。
- 審題複核（45 gold＋40 no_canon，`review_out.json`）：gold_ok 38/45、should_be_nocanon 4、missed_also_ok 4；no_canon 39/40 可信（1 題 `jgb/B/lessee-crud` 其實答得了，同細目在 gold 側也被漏——標題難聯想，屬「說法對不上」）。
- 缺口歸類（`gaps_categorized.json`）：D 68／E 56／C 13／G 13／A 7／I 6／H 4／B 3／NEW 11；歸類者疑判錯 4 題。
- **業主 2026-09-25「a」**：缺口清單優先；架構比較改描述性（A0＋A3，A2 不做）；關卡二＝業主看 `owner_gold30.json`（進行中）。處置預定：被複核 45 題套審題修正、未複核 155 題不重判並標「gold 約 16% 誤差」。
- **關卡二通過（業主 2026-09-25「OK」，`owner_gold30.json` 無判錯）**：套審題者修正（`review_out.json`：4 題 gold→no_canon、4 題補 also_ok、1 題 no_canon→gold；業主判錯者 0）進 `judge_out_{1,2,3}.json`（原檔備份 `judge_out_{b}.orig.json`）。
- **凍結（`freeze913.py --write`）**：knowledge 有 gold **197**（原 200 − 4 + 1）、no_canon **184**（原 181 + 4 − 1，佔比 **48.3%** ≥20% ⇒ 依 §6「正本缺口大於檢索」成立）、gold 不可見 0；holdout **99**（<150 ⇒ 依 §4 架構比較仍記 **INCONCLUSIVE**，material 98；近似分層：holdout 全 `far`）。repo 內 index `inputs/ruler-9.13-index.json`（sha `6b27c06db15ebcad473284229293631bcd6fa05dddf83e1ef1ea3ee2f34f1564`）；manifest 已登記 `ruler-9.13`（`samples-manifest.json`）；checker self-test ⑦ 綠、正對照掃到 197 題。
  - ⚠️ 不變量 34 實跑另抓到 1 個**非留出集**碰撞：`material` 池題 `ce2ce3372c6e`（帳務類）與既有正本講法「房東專屬帳號是什麼」hash 相同——不影響本輪 A0/A3（該題不在 holdout），留供日後 81 題類待裁參考。既有已知紅（`合約範本有哪幾種`，S3 帶入）仍在，非本次新增。
  - **更正（2026-09-25，主 session）**：上面那個碰撞之所以讓 `make audit` 轉紅，是 checker 的實作比 §4 寬——§4 定的是「正本講法 ∩ **留出集** ＝∅」，但 `canon_phrasing_frozen_disjoint.py::_extract_questions` 的 `ruler-9.13` 分支把 material 也一起比。已改為只取 `split=="holdout"`；`split` 缺漏或值域外即大聲失敗；self-test ⑦ 加「撞講法素材池（material）⇒ PASS」。改後凍結題計數 `ruler-9.13` 由 197 變 99，不變量 34 只剩既有的「合約範本有哪幾種」。這是讓實作回到已核可的 §4，⛔ 不是看了結果才放寬門檻。
  - ⚠️ `gaps_categorized.json`（D68/E56/C13/G13/A7/I6/H4/B3/NEW11）是套修正**前**（no_canon 181）產的，與凍結後 184 差 3 題未重新歸類；併入 81 題裁決前需重跑分類，差量小（1.6%）預期不改變分佈結論。
- **量測（A0＋A3，容器內 `arms.py`，`docker-compose.dev.yml`，reranker 走 `aichatbot_default` 網路直打 `aichatbot-semantic-model:8000/rerank`）**：
  | 組 | hit@5 | 粗目層命中 | 備註 |
  |---|---|---|---|
  | A0（現況） | 54.55%（54/99） | 76.77% | 原話 60.0%／摘要 52.17% |
  | A3（A0＋reranker） | 65.66%（65/99） | 80.81% | 原話 66.67%／摘要 65.22%；`rerank_changed_top5=99/99`（正對照遠超門檻）；延遲中位數 **24.5s**（本機記憶體壓力下實測，見下） |
  | **A3−A0** | **+11.11 點** | +3.03 點 | 達 §6 替代層 10 點門檻，但 **holdout 99<150 ⇒ 依 §4 仍記 INCONCLUSIVE，只作描述性參考，不觸發「建議升格正式一層」的正式判定**；未跑 --ruler912 回歸side-check（描述性任務不需要） |
  - **執行環境備註**：跑測當下主機 `PhysMem 23G used／10G compressor`、`load avg 21–30`（已知這台機器資源緊繃時的既有限制，非 reranker 本身或腳本缺陷）⇒ 單題延遲 20–150s 波動、總耗時約 45 分鐘（A0 ~7 分＋A3 ~38 分）；99/99 題全部 HTTP 200、無降級／逾時，未觸發 §7 停止線。24.5s 的延遲數字**不能當生產環境代表值**，僅供「reranker 有沒有用」定性判斷；要production化需另在資源充足環境下重測延遲。
  - 原始紀錄：`~/jgb-archive/ruler-9.13/arms_out.json`（rows 不含題目文字）。
