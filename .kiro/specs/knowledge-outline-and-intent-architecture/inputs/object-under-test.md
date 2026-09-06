# 受測物定義清單——`tools/canon/index_eval.py` 全跑前置（元件 10 步 1）

> 依 Plan `inputs/plan-3.4-index-eval-20260907.md` §1／§4／§7；本檔核可欄非空後才准全跑（打 embedding、
> 寫 session 狀態）。`--dry-run` 已跑過、三項全等（見下）。

## 1. 材料 sha（`--dry-run` 實測，2026-09-07）

| 材料 | sha256 |
|---|---|
| 知識正本 `rag-orchestrator/canon/prospect.md` | `240e1a502a85621799bdd5f850c41ce6cb90784a2911ccc3f12a76decba2763c` |
| koyu 問法正本 `coverage-map/sources/koyu-v2-phrasings.json` | `1fc5bccd33726c9283d1b6d5daeeee97dec01818afa80a6d097c9e15bce8b25d` |
| 422 抽樣規則檔 `inputs/phrasing-selection-rule-20260906.json` | `5fcb52b78ce29fa220c7d473a71160e7a9d94406c9430ccde060b31b16ef7d61` |
| 凍結 54 句來源 `coverage-map/topics-v2.json` | `f78344d65ebcdc7b9901c77b7bdf5a6b23b2548e2dea3729feba36ccb8868570` |
| gold 映射（本次 dry-run 產出）`inputs/koyu-article-map.json` | `ec8adeba3470726b21ebf482478b94b29c79aa234088c6e80c5ec349eb1f91d0` |
| 幫助中心目錄摘要 `phrasing_map.dir_digest` | `8a040b783281f0eedf43fe1eb805d0f6e77b9b2396a5d9499fc8a4a43735661c` |

規則檔宣告 `sha256`＝`b771a6e5c6c139d434e21c54f5a5c4fcade934aca6c50c104f2aaf7f4379a747`；原計法（哪支腳本、
以什麼輸入算出這個值）在 `raw/phrasing-20260906/` 與 commit `eabb2c2b` 均查無——**sha 原計法未留**。
凍結證據改採 plan-verifier 第 1 輪建議的「三項全等」（見下）。

## 2. 凍結證據（三項全等，`--dry-run` 實測）

| 項 | 規則檔宣告 | 本次重生 | 相等？ |
|---|---|---|---|
| `n` | 422 | 422 | ✅ |
| `by_type` | 直接85／口語85／情境84／俗稱85／邊界83 | 同左 | ✅ |
| `excluded_frozen` | 48 | 48（重算） | ✅ |

`frozen_set_size`＝54（`topics-v2.json` 全部 `q`，含 2 句字面重複）。

## 3. gold 映射現況（實查）

- koyu `articles` 85 篇；`<slug>_zh-Hant.html` 直接對得到檔案：82 篇；對不到（`unresolved`）：3 鍵
  `TOFILL-beike`／`TOFILL-repair`／`property（原`。
- §7.1 業主核准別名（三個都視為同一篇）：`TOFILL-beike→beike`、`TOFILL-repair→repair`、
  `property（原→property`。套用後 `unresolved_after_alias=[]`（3 個檔案都存在）。
- 正本 24 個細目的 `sources` 引用 39 個相異 helpcenter slug（含重複跨細目引用）；
  套別名後與 koyu 85 個可解析文章鍵交集、且該細目集合非空 ⇒ `articles_with_gold=31`
  （不含別名時為 30；`repair` 別名讓 `repair-system` 細目多算入 1 篇，`articles_with_gold`
  30→31；`beike`／`property` 兩鍵雖套別名後檔案存在，但**沒有任何細目的 `sources` 引用
  `helpcenter:beike` 或 `helpcenter:property`**——Plan §1 原預期 property 合併會再 +1（引 32），
  ⛔ 實查不成立，記在此供業主核對，不自行假定 Plan 的預期數字對）。
- 每型可對映句數（實查）：直接 31／85、口語 31／85、情境 30/84、俗稱 31/85、邊界 30/83——
  五型皆 **≥30，`limited_types=[]`**，dry-run 未觸發 exit 3 硬停（與 Plan §2 現況事實一節「claim
  ceiling 很可能整片 limited」的預期不同，實測剛好卡在門檻之上；業主可自行核對 §7.3 是否仍要走
  備案）。

## 4. 材料能證什麼／證不了什麼

**能證**：
- 三臂（標題／標題+講法／標題+講法+內文）在 31 篇有 gold 的文章、共 422 句真實問法（koyu 抽樣）
  上的 recall@1/3/5 相對高低——足以看出「內文要不要加進匹配鍵」這個問題的**方向**。
- LOO 兩模式下的分數，用來排除「湊巧命中自己」（`exact`）與「同文章污染」（`article`）造成的
  虛高分數。
- 55 格代表問句（第二份材料）上的同一組三臂 recall，作交叉對照。

**證不了什麼**：
- 82 篇 koyu 文章裡只有 31 篇有正本細目對映；其餘 51 篇（含 `beike`／`property` 全部句子）不進
  任何 recall 分母——**這片材料不代表全部 koyu 內容的檢索表現，只代表「正本目前已覆蓋的那 31
  篇」**。
- $0 本機 embedding，非線上流量；不代表真實使用者問法分佈。
- 55 格代表問句的 gold 來自 v3 判者的**單一標記**（`answerability-canon-v3.json`），非人工覆核共識。
- ⛔ 本片不下「該用哪一臂」的結論（Plan §4.4）——3.6 才定案。

## 5. 假設表

| 命題 | 最小材料 | 尺 | 推翻條件 | 費用 |
|---|---|---|---|---|
| 標題+講法+內文臂的 recall@5 顯著高於只標題臂（≥10 點差） | 31 篇 gold、422 句、5 型 | recall@5（gold∩top5非空） | 臂間差 <10 點，或某型差距反向 | $0 |
| LOO article 模式下 recall 明顯低於 LOO exact（同源污染存在） | 同上 | 兩模式 recall@1/3/5 差 | 兩模式數字接近（差 <5 點） | $0 |
| 55 格代表問句與 422 句 koyu 抽樣的臂間排序一致 | 55 格＋v3 gold | 兩份材料各自的臂序 | 排序不一致 | $0 |

## 6. 核可

核可：owner 2026-09-07（業主回「核可」，主 session 代填）
