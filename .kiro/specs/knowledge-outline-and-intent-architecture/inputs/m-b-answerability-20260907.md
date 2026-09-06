# M-b 2.4b 步 4 可答性報告：55 格・子代理判者・正本細目為候選（2026-09-07）

> **結論先講：一致率 52／55＝0.945 ≥ 門檻 0.80（design D.1.4），`needs_rubric_revision=false`，出口＝通過，進 2.6 reweigh（腳本未寫）與步 6 diff。** 三格 label 分歧由第 3 判者裁定；另有兩格 label 同、fine_id 不同（不計入門檻）。finalize 通過、journal 已寫。

## 1. 數字

| 項目 | 值 | 查證 |
|---|---|---|
| 格數／同意數／一致率 | 55／52／**0.945** | `python3 -c "import json;r=json.load(open('.claude/skills/outline-curation/raw/answerability-20260907/result.json'));print(r['total'],r['agree'],r['agreementRate'])"` |
| label 分歧（走第 3 判者） | 3：C24、C30、C46 | `raw/answerability-20260907/prompts/third.prompt.md`、`verdicts/third.json` |
| fine_id 分歧（label 同；不進門檻） | 2：C02、C23 | 比對 `verdicts/G01-s1.json`／`G01-s2.json`、`G05-s1`／`G05-s2` |
| 丟棄格 | 0 | `result.json.droppedCells` |
| 判者數 | 23＝11 組 × 2 ＋ 第 3 判者 1 | `result.json.usage.agents` |
| token（harness 計） | G02–G11＋third 共 21 個實測 1,248,948；G01 兩個在前一視窗未記，以 ≈60k／個估 ⇒ 全程 ≈1.37M | 各子代理完成通知 `subagent_tokens`；`finalize` 的 `cost.usd=0` 是因為未帶 token 參數，⛔ 不是免費 |
| 候選 sha（正本審查版） | `da786d73407b…` | `result.json.inputsSha.canon`＝`inputs/prospect.draft.review-20260907.md` 的 sha256 |
| rubric sha | `3d1137476b7f…`（0.2.0 approved） | `result.json.rubricSha` |
| 標籤分佈 | answerable 28／partial 11／no_source 11／deliberate_no 5 | `python3 -c "import json,collections;r=json.load(open('.claude/skills/outline-curation/raw/answerability-20260907/result.json'));print(collections.Counter(x['label'] for x in r['labels']))"` |
| finalize 產物 | `runs/2026-09-06T00-00-00Z/answerability-canon.json`（40,751 bytes）、`journal/answerability-canon-20260907.json` | `ls -la` 兩檔 |

## 2. 五格分歧與裁決

| 格 | 問句 | s1 | s2 | 第 3 判者 | 終判 | 備註 |
|---|---|---|---|---|---|---|
| C24 | 電子發票可以自動開嗎 | no_source | partial（billing-overview） | no_source | **no_source** | 2:1 |
| C30 | 帳單代收代付的運作方式 | no_source | partial（owner-report-collection-remit） | partial（**billing-overview**） | **partial／owner-report-collection-remit** | ⚠️ 第 3 判者 label 同 s2 但 fine_id 不同；Reconcile 只以 label 多數決、fine_id 沿用同 label 的首位判者。M-a 試作此格也分歧（見 §4），是唯一兩輪都分歧的格 |
| C46 | 有多語系介面嗎？外籍租客能用嗎 | answerable | partial（皆 why-choose-jgb） | answerable | **answerable** | 業主原列「可見性待決」（附錄 H P6），判者認為正本 `why-choose-jgb` 第 1 句已答；請業主核該句是否真的回答多語系 |
| C02 | 收租常常忘記，你們適合我嗎 | answerable／overdue-reminder-late-fee | answerable／billing-overview | — | overdue-reminder-late-fee | 兩細目都能答 ⇒ 重疊訊號，進 2.6／步 6 當 see_also 候選 |
| C23 | 帳單可以自動產生嗎 | answerable／billing-overview | answerable／bill-contents-extra-fees | — | billing-overview | 同上 |

C02／C23／C30 三格都指向 `billing-overview` 與鄰居（overdue-reminder-late-fee、bill-contents-extra-fees、owner-report-collection-remit）內容重疊；⛔ 不在本步合併，交 2.6 reweigh 與步 6 diff 標記。

## 3. 附錄 H P6 八格：7 格確認缺、1 格判可答

| 格 | 問句 | 終判 | 兩判者 |
|---|---|---|---|
| C22 | 所以剛剛說的簽約要另外收費嗎 | no_source | 一致 |
| C25 | 差額發票的使用時機是什麼時候 | no_source | 一致 |
| C29 | 儲值金回充帳戶是什麼功能 | no_source | 一致 |
| C39 | 私人門鎖和共用門鎖到底有什麼差別 | no_source | 一致 |
| C52 | 系統管理模組裡有哪些功能？ | no_source | 一致 |
| C53 | 單合約與雙合約差別？ | no_source | 一致 |
| C54 | 手機條碼載具可以用來付費嗎？ | no_source | 一致 |
| C46 | 有多語系介面嗎？外籍租客能用嗎 | **answerable** | 分歧→第 3 判者 |

P6 待業主項（C22／C39／C53 答案、C25／C29／C46／C54 可見性、C52 名稱）現在有判者證據：7 格是真缺口，C46 需業主核。其餘 no_source 4 格：C07 免費方案可建幾個物件、C15 物件自訂標籤用途、C24 電子發票自動開、C31 水電費分算——⛔ 不在 P6 清單，是新缺口，2.6 產 `not_available`／`owner_decision` 去向時要列。

## 4. 與 M-a 試作對照：0.841 → 0.945，七格不一致六格收斂

| | M-a（1.5 試作） | M-b 本輪 |
|---|---|---|
| 候選 | kb 列＋18 筆草稿 | 正本 37 細目（講法不進候選） |
| 判者 | gpt-4o-mini API ×2 | Claude Code 子代理 ×2（＋第 3） |
| 格數 | 44（批 5 未跑） | 55 |
| 一致率 | 37／44＝0.841 | 52／55＝**0.945** |
| 分佈 | answerable 27／partial 4／no_source 12／deliberate_no 1 | 28／11／11／5 |

M-a 七格不一致（C01、C06、C07、C19、C26、C30、C35）本輪：C01 partial、C06 partial、C07 no_source、C19 partial、C26 answerable、C35 partial 皆兩判者一致；只剩 **C30** 仍分歧。M-a 報告建議的 rubric 0.3.0（partial 子問題定義）維持「可選」，本輪數據不要求它。partial 由 4 升到 11 是候選換成正本細目（內容較泛、覆蓋較廣）的效果，不是判者飄。

## 5. 正本覆蓋：37 細目 27 被引用、10 未被任何格引用

未引用：`prospect/A/dashboard-overview`、`A/pain-points`、`B/individual-landlord-scale-fit`、`B/team-company-fit`、`C/contract-modify-after-sign`、`C/property-management-overview`、`C/team-management-overview`、`D/property-quota-limit`、`E/competitor-neutrality`、`G/migration-limits`。未引用≠多餘：需求格只來自 F2 21 列＋缺口地圖 v2.1，A／B 定位類與 G 限制類本來就少有直接問句；2.6 reweigh 標 `no_demand_cell`，⛔ 不刪。

被引用最多：`C/contract-esign-flow` 3、`C/payment-gateway-options` 3。

## 6. 環境事實（給下次跑的人）

- **判者慢與記憶體爆的根因不在判者**：一筆別窗開的專案層級 canon 盤查（dialogue-logic，22 份來源）沒 `end`，每個子代理 SubagentStop 被 finishgate 擋 3 次；每次 finishgate 跑 `refcheck.verify`，它對 repo 每個檔整檔 `read_text`（含 1 GB `model.safetensors`、44 MB SQL 備份），實測峰值 **2.4 GB／21 s**。判者單次 5–16 分鐘 → 盤查 `end` 後 18–24 秒。
- **已修（全域工具，⛔ 不在本 repo 版控）**：`~/.claude/canon/refcheck.py` 新增 `read_textual`（>4 MB 或開頭 8 KB 含 NUL 跳過），套用於 `_resolve_symbols`、`_symbols_present` 與 `decisions.check_assertions` 的走訪；修後 0.7 s／38 MB、壞引用數不變（0）。修前備份在本 session scratchpad `canon-backup/`（session 級、會消失）；⚠️ `~/.claude/canon/` 無 git，建議納入版控。
- 盤查紀錄按專案存、憑證按 session 存 ⇒ 任何新視窗都會被舊盤查卡住；建議 finishgate 的覆蓋率檢查只對 `main` scope 生效（待業主裁）。
- 閘門解除後一次 4 個判者並行無壓力（free 72%）；有殘留盤查時一次 2 個就進 swap。
- `raw/answerability-20260907/save_verdict.py` 改為 `raw_decode` 只取第一個 JSON 陣列（判者被閘門擋後會在 JSON 外加散文）。
- **P3 待修**：`result.json.agentsUsed`＝113 是「verdict 條數」（55×2＋3）不是代理數，`finalize` 的 `cost.agents` 跟著 113，均攤 usd 時分母錯（`answerability_agents.py` 的 `agents_used += len(verdicts)`）。本輪 usd 為 0 不受影響。
- **PII 全掃誤判已根治（業主裁 B，security-reviewer→security-executor→verifier CONFIRMED）**：`PHONE_RE` 把 finalize 輸出裡 sha256 的 `…cf017929054d…` 當電話；邊界改為排除十六進位字元（不用全英數，因 `phrasing_map.deidentify` 共用此尺遮蔽，英數邊界會漏 `TEL0912…`）。回歸鎖在 `tests/unit/_meta/test_outline_gate_req.py::test_gate4_phone_boundary_excludes_hex_not_all_alnum`。已知取捨（P4，不擋）：號碼緊貼 a–f／A–F 字母者不再遮，含 `0912345678EXT205` 這種無分隔分機；`0912-345678` 舊新版皆不抓是既有缺口，另案。
- 本機 rag-orchestrator image 已重建（不變量 3 曾紅：容器缺 `services/agent/canon/`），`make audit` OVERALL PASS。

## 7. 下一步

1. 2.6 `reweigh.py`（design 元件 1；E6）——未寫；讀 `answerability-canon.json`＋正本＋demand，產 `CellRecord` 去向；`needs_rubric_revision=true` 必 exit 2（正對照 unit）。
2. 步 6 `diff_report.py`——`replacements[]` old kb id → fine id；C02／C23／C30 的重疊標 see_also 候選。
3. 業主：C46 核句；P6 其餘 7 格照附錄 H 走；新缺口 C07／C15／C24／C31 是否進 G「現有不足」。

## 8. 查證指令

```
RAW=.claude/skills/outline-curation/raw/answerability-20260907
ls $RAW/verdicts | wc -l                                   # 23（22 判者＋third）
python3 .claude/skills/outline-curation/scripts/answerability_agents.py collect --args $RAW/args-canon.json --out-dir $RAW --out /tmp/re.json   # collect ok total=55 agree=52 rate=0.945
shasum -a 256 .kiro/specs/knowledge-outline-and-intent-architecture/inputs/prospect.draft.review-20260907.md   # da786d73407b…
python3 -c "import json;print(json.load(open('.claude/skills/outline-curation/runs/2026-09-06T00-00-00Z/answerability-canon.json'))['inputs_sha'])"
```
