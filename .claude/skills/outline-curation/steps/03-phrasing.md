# 步 3：phrasing

**輸入**：`structure-proposal.json`、講法來源（question_summary／幫助中心／問法正本）、凍結題 manifest。
**輸出 schema**：`../schemas/phrasing-map.json`。
**形態**：腳本＋人審（相似細目只出待審清單，⛔ 不自動合併）。
**出口條件**：`phrasings[]` 每筆狀態為 `proposed`；`similar_pairs[]` 待人審裁決前不得視為已解決；
`unassigned[]` 每筆要有去向（掛哪個細目／不要）才進步 4。

## CLI

```bash
python3 .claude/skills/outline-curation/scripts/phrasing_map.py \
  --structure   .claude/skills/outline-curation/runs/<run>/structure-proposal.json \
  --kb-rows     .kiro/specs/knowledge-outline-and-intent-architecture/inputs/prospect-kb-rows-<date>.json \
  --helpcenter-dir "<幫助中心 HTML 扁平目錄>" \
  --koyu        .kiro/specs/presales-grounding-gate/coverage-map/sources/koyu-v2-phrasings.json \
  --frozen-manifest .kiro/specs/agentic-mcp-orchestration/eval/samples-manifest.json \
  --raw-dir     .claude/skills/outline-curation/raw/phrasing-<YYYYMMDD> \
  --frozen-at   <ISO 時間戳> \
  --out         .claude/skills/outline-curation/runs/<run>/phrasing-map.json \
  [--min-score 0.12] [--cap 12]

python3 .claude/skills/outline-curation/scripts/similar_items.py \
  --structure   .claude/skills/outline-curation/runs/<run>/structure-proposal.json \
  --phrasing-map .claude/skills/outline-curation/runs/<run>/phrasing-map.json \
  --out         .claude/skills/outline-curation/runs/<run>/similar-items.json \
  [--threshold 0.30] [--no-merge]

# 90 天保存期限（先乾跑看清單，確認後才 --apply）
python3 .claude/skills/outline-curation/scripts/raw_purge.py \
  --raw-dir .claude/skills/outline-curation/raw --today <YYYY-MM-DD> [--days 90] [--apply]
```

⛔ `--frozen-at`／`--today` 一律由呼叫端傳入：三支腳本內都沒有 `datetime.now()`，同輸入兩次執行逐位元相同。

## 來源與掛載

| 來源 | `source` 格式 | 掛載方式 |
|---|---|---|
| kb 列的 `question_summary`（關鍵字串，空白切詞、每詞 2–20 字） | `question_summary:<kb_id>` | 細目 `merge_of` 含 `tmp:kb:<kb_id>` ⇒ 直接掛（⛔ 不算分） |
| 幫助中心 `<title>`（缺則 `<h1>`） | `helpcenter:<slug>`（slug＝檔名去 `_zh-Hant.html`） | 字元 bigram Jaccard 對細目 profile 取 top-1，≥ `--min-score` 才掛 |
| 問法正本 `koyu-v2-phrasings.json` | `koyu:<slug>#<n>` | 同上 |

- 細目 profile＝細目標題＋該細目 `merge_of` 所含 kb 列的 question_summary 詞。
- 分數低於門檻者進 `payload.unassigned[]` 交人審，⛔ 不硬掛到最接近的細目。
- 問法正本**只取 直接／口語／情境／俗稱**；⛔ 不取 **操作**（找按鈕路徑，屬業者操作受眾）與
  **邊界**（＝該文章本來就沒寫的延伸問題，掛上去等於承諾沒有的內容）。
- 與凍結題（`samples-manifest.json` 各 available set 的 `q`）NFKC＋去空白後相同者一律丟棄並計數，
  ⛔ 不得進索引（去識別前後各比對一次）。
- 每細目上限 12 筆（分數高者留），NFKC＋去空白後去重。

## 去識別（⛔ 在任何 agent 呼叫、任何字元寫進 `runs/` 之前執行）

原句（未去識別）只落 `--raw-dir`（`.claude/skills/outline-curation/raw/`，已在 `.gitignore`；
查證：`git check-ignore -v .claude/skills/outline-curation/raw/x.json`），90 天後由 `raw_purge.py` 依**檔名日期**刪除。

十類（各以固定佔位符整段取代；命中數記進 `payload.redaction_counts`）：

| 類別 | 定義 | 佔位符 |
|---|---|---|
| 人名 | 常見單姓＋0–3 個中文字＋稱謂（先生／小姐／太太／女士／老師／經理／專員／主任／董事長／總經理／課長／店長） | `〈人名〉` |
| 地址 | 縣市（＋可選 區／鄉／鎮）＋路／街／巷／弄＋門牌片段 | `〈地址〉` |
| 合約號・帳單號 | ≥4 位數字與 合約／帳單／編號／號 相鄰（數字在前或標籤在前皆算） | `〈編號〉` |
| 電話 | 市話與行動電話號碼 | `〈電話〉` |
| email | 電子郵件位址 | `〈EMAIL〉` |
| LINE id | `@` 起頭的帳號字串 | `〈LINEID〉` |
| 統編 | 獨立的 8 位數字；⛔ 排除可解讀為日期者（19xx／20xx＋合法月日） | `〈統編〉` |
| 房號戶名 | 棟／樓／室／號房＋數字，或「戶名：<中文>」 | `〈房號〉` |
| 社區與物件名 | 專名＋社區／大樓／華廈／大廈／花園／山莊 | `〈社區名〉` |
| 車牌 | 車輛牌照號碼 | `〈車牌〉` |
| 金額＋日期 | 金額與日期同時出現且相鄰的組合 | `〈金額日期〉` |

- 去識別後只剩佔位符的講法整筆丟棄（`counts.dropped_deidentified_empty`）。
- email／電話／LINE id／統編／車牌／編號／金額＋日期的 regex **直接 import `.claude/hooks/outline_gate.py`**，
  ⛔ 不在 skill 內另寫一份——skill 與 hook 必須是同一把尺。人名／地址／房號戶名／社區與物件名 hook 沒有，在腳本內補齊。
- 判準取捨（刻意，⛔ 勿改回）：**單獨的「數字＋戶」是計數量詞**（如「約10戶」＝規模），不算房號；
  **專名往回收字遇動詞字（建／創／設…）即止**（否則「先建社區」「創建社區」會被整段當專名遮掉）。

## 相似細目

`similar_items.py` 只出 `similar_pairs[] = {a, b, score, method}` 待審清單，**⛔ 永不合併、⛔ 不改任何 id**。
後端：環境變數 `EMBEDDING_API_URL` 有設時走向量（`POST` body `{"text": ...}`、回應 `{"embedding": [...]}`，
形狀取自 `rag-orchestrator/services/embedding_utils.py`），沒設時走決定性字面後備；`method` 記在 payload。
⛔ 不印 URL、⛔ 不印環境變數。
