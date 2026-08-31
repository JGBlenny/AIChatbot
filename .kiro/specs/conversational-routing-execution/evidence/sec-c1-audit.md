# SEC-C1 —— Committed History Secret Audit（證據封存）

> ⛔ **本檔絕不儲存任何 secret 值。** 所有憑證一律只記 type / length / entropy /
> classification / object / ref / path / SHA-256 fingerprint。
> 需要辨認「是否同一把 key」時使用 fingerprint 比對，**不得回填明文**。
> 本檔為 **immutable forensic checkpoint**：C2 remediation 會改變環境狀態，
> 事後重掃結果與本檔不同屬正常，⛔ 不得回頭改寫本檔。

---

## 1. Audit scope / date / HEAD

```text
audit_id        SEC-C1
date            2026-08-31
repo            /Users/lenny/jgb/AIChatbot
branch          fix/retrieval-routing-stability
HEAD            0850fcd
worktree        clean
remote          git@github.com:JGBlenny/AIChatbot.git

SCOPE（已凍結，執行未偏離）
  掃：HEAD ancestry ／ 所有本地 branches + tags ／ tracked file history
      ／ commit patch contents ／ 全 ODB（含 unreachable / orphan 物件）
  找：已知 exposed key exact value（只在本機比對，⛔ 不輸出）
      ／ OpenAI pattern ／ AWS 與常見 credential pattern
      ／ .env / backup / debug 類敏感檔是否曾被 commit
  不做：不 push ／ 不 history rewrite ／ 不 rotate ／ 不 revoke
        ／ 不印 secret ／ 不把完整匹配行貼進 transcript
        —— 以上五項本輪**全部遵守**，未執行任何 Git 寫入或狀態變更操作

refs inventory
  local branches 5   archive/conversation-retrieval-resilience-failed 6dccc5b
                     docs/sop-index-link-repair 37419b4
                     fix/retrieval-routing-stability 0850fcd
                     main 7d895ce
                     spec/retrieval-decision-layer d4c9cfe
  tags 1             rdl-20260822-halt d4c9cfe
  remote refs 3      origin/HEAD e20324d ／ origin/main e20324d
                     origin/feat/form-chaining c805c0e
  commits            reachable(all refs)=1058 ／ HEAD ancestry=1007
  未 push            origin/main..HEAD = 444 commits
```

## 2. Positive controls（否定結論的前提）

三道正對照全部命中；任一未中即 **非 0 退出**，且本輪確實觸發過一次大聲失敗。

```text
PC-1 matcher self-test        10 個 pattern ＋ exact matcher 對合成樣本
                              = PASS
     ⚠️ 首次執行 FAIL（jwt_like 合成樣本過短）→ 腳本 exit 2 中止，
        修正**控制樣本**（非放寬 pattern）後重跑通過。
PC-2 "OPENAI_API_KEY" 字面     = 427 objects HIT
     用途：證明 ODB 串流讀得到內容；若為 0 則所有 NOT_FOUND 不可信
PC-3 .env.example 在 committed path 清單 = HIT
     用途：證明路徑史掃描有效；據此「裸 .env 從未被 commit」才是可信的否定結論
PC-4 word-boundary self-test  真 project-key 樣本必中、"task-"/"risk-" 必不中
                              = PASS
```

## 3. Object counts / bytes scanned

```text
OBJECTS_SCANNED   14897      （blob 6584 ／ commit 1162 ／ tree 7151）
BLOBS             6584
BYTES             1366905173  （約 1.27 GiB，逐 byte 掃描，未跳過大檔）
掃描面            git cat-file --batch-all-objects  ⇒ 含 unreachable / orphan
REACHABLE_OBJECTS_ALL_REFS   11919
REACHABLE_FROM_REMOTE         8149
```

## 4. Exact-value scan result

```text
EXACT_VALUE_SCAN = EXECUTED       （⛔ 非 NOT_EXECUTABLE）
比對值來源       本機 .env ／ .env.bak-20260822（.example 類已排除）
候選變數         7 個（名稱含 KEY/SECRET/TOKEN/PASSWORD/... 且長度 ≥16）
輸出限制         只印 present / length，⛔ 未印值、前綴、後綴

結果（objects = 含該 exact 值的物件數）
  OPENAI_API_KEY          0     ← 可達與 orphan 皆 0
  JGB_API_KEY             0
  RAG_ADMIN_API_KEY       0
  AWS_ACCESS_KEY_ID       2     ← 1 筆在 **pushed** blob、1 筆 orphan（見 §7）
  AWS_SECRET_ACCESS_KEY   1     ← 僅 orphan，**不在** pushed history
  DB_PASSWORD           656     ← 與 .env.example 同值，見 §8
  INTENT_SUGGESTION_MAX_TOKENS  2  ← 變數名含 "TOKENS" 的誤收候選，非憑證
```

**Fingerprints（SHA-256，供 C2 之後 correlation 用；⛔ 不可回填明文）**

```text
CURRENT_ENV.OPENAI_API_KEY         len=164  5e89e8866549ef0b998bba6792b41b82bb984ca42ee9014bc08831f664328cc3
CURRENT_ENV.AWS_ACCESS_KEY_ID      len=20   93e67538460db6f443120436bf11e067350e0394884f79c0cee4c74da8c5a3e0
CURRENT_ENV.AWS_SECRET_ACCESS_KEY  len=40   ccbc228e9f13cacbcfe5da825afa5d7675426c7575f96dd1bb413f57851863d5
CURRENT_ENV.JGB_API_KEY            len=36   8d2539d0ffabcfe75135419c833b64fd50fcef70ed8588e1448395ada3f5d47f
CURRENT_ENV.RAG_ADMIN_API_KEY      len=47   784c04c8811c3e24a8b266d5640e569c9d1222c3926849a9876273b98db0c74f
CURRENT_ENV.DB_PASSWORD            len=18   a4deae55669af20505132b16409c58e0a440b6e3e590e0a7297189225080b85b

ORPHAN_OPENAI_KEY_A                len=164  5bf1ac0b88b707d90eec214d076be62937844166ada98dce934ed4875fdf0a7f
ORPHAN_OPENAI_KEY_B                len=160  46e5a63344189702c423024fd21a810dbc1e8c0671736b1cfa83c56df216ef43
AWS_DOC_EXAMPLE_SECRET             len=40   78314b11be2e581549ac1c4f616563fad3fdf0c3b71678f6e2299182080e0598
```

⚠️ `ORPHAN_OPENAI_KEY_A/B` 與 `CURRENT_ENV.OPENAI_API_KEY` 指紋**互不相同** ⇒ 為三把不同的 key。

## 5. Reachable vs orphan（本次審查的關鍵區分）

```text
REACHABLE   可從 refs/heads、refs/tags 或 refs/remotes 走到 ⇒ **會被 push**
ORPHAN      僅存在於本機 ODB（曾 staged、被 amend/reset 丟棄、或 stash 殘留）
            ⇒ git push **永遠不會**傳送；git gc --prune 會回收

命中物件中的 dangling 統計
  dangling_hit_objects   56
    ORPHAN_ODB_ONLY      52
    REFLOG_REACHABLE      4   （reflog 為本機物件，同樣不可 push）
  reflog_commits       1096
  stash_entries           4

⛔ 判定鐵則：orphan 物件的命中**不構成 committed history exposure**，
   但**仍是本機殘留憑證**，必須進 C2 的 inventory 與清理決策。
```

## 6. SEC-01 —— OpenAI transcript exposure

```text
Git committed history
  NOT_FOUND for currently scanned exact value
    scope：全 ODB 14897 物件、1.37e9 bytes，可達與 orphan 皆 0 hit

history rewrite
  NOT_REQUIRED_BY_CURRENT_EVIDENCE

credential remediation
  STILL_REQUIRED
    - revoke / rotate 目前被視為 exposed 的現行 key
      （fingerprint 5e89e886…；⚠️ 現行 key 仍寫在本機 .env 與 .env.bak-20260822）
    - 另兩把僅存在於 orphan ODB 的歷史 OpenAI key，若仍 active 亦須 revoke
      ORPHAN_OPENAI_KEY_A  len=164 entropy=5.75  blobs 639715e1e15b / ccd34afb11b3
      ORPHAN_OPENAI_KEY_B  len=160 entropy=5.71  blob  474e58c7b692
      三者皆 in_origin_main=FALSE ／ in_any_remote=FALSE ／ 不可達任何 ref

⚠️⚠️ 限制（⛔ 不得在引用本檔時省略）
  CURRENT_ENV_KEY == TRANSCRIPT_EXPOSED_KEY
    = ASSUMED_FROM_HANDOFF_HISTORY
    = NOT_INDEPENDENTLY_PROVEN
  ⇒ 本檔**僅**斷言：「目前被視為該 exposed key 的現行值，exact scan 在 Git 內 0 hit」。
  ⛔ 不得改寫成「the exact transcript key is definitely absent from Git」。
  ⇒ 本機 ODB 內另存在兩把不同的真長度 OpenAI key，這本身即說明 key 曾經更替，
    因此上述等同假設**不是自動成立的**。
```

## 7. SEC-02 —— REMOTE_HISTORY_CREDENTIAL_IDENTIFIER_EXPOSURE

```text
AWS_ACCESS_KEY_ID exposed in pushed Git history        = CONFIRMED
AWS_SECRET_ACCESS_KEY paired with that ID (in pushed)  = NOT_FOUND
⛔ 因此**不得**表述為 "full AWS credential compromised"
   —— Access Key ID 本身不是能單獨登入 AWS 的秘密。

命中細節
  file           docs/archive/2025-Q4/deployment/PRODUCTION_DEPLOYMENT_CHECKLIST.md  (line 33)
  blob           4f3a9ba9210f0993305204c0d165e795aef17813
  token          AKIA + 16，len=20，entropy=4.02，格式完整
  redaction      該行無遮蔽標記、無截斷符 ⇒ 判定為完整值而非示例
  非官方範例      ≠ AKIAIOSFODNN7EXAMPLE / ASIAIOSFODNN7EXAMPLE
  in_origin_main TRUE        in_any_remote TRUE
  present_at_HEAD / origin/main tip = FALSE
                 （2026-05-18 commit 915e9562 刪除 docs/archive/，但歷史仍在）
  路徑史          引入 fd0a5ca4 (2026-02-14) → 刪除 915e9562 (2026-05-18)，5 commits
  contained_in   全部 5 條本地分支 ＋ origin/main ＋ origin/feat/form-chaining

⚠️ **身分比對（此為本輪最重要的更正）**
  該 pushed token 的 sha256 = 93e67538…
  CURRENT_ENV.AWS_ACCESS_KEY_ID 的 sha256 = 93e67538…
  ⇒ **兩者為同一把**：進入遠端歷史的不是舊 key，而是**目前 .env 仍配置在用的那把 Access Key ID**。
  （初判曾誤述為「另一把舊 key」，係逐路徑清單被截斷所致；以本節為準。）

配對 secret 的位置
  CURRENT_ENV.AWS_SECRET_ACCESS_KEY (ccbc228e…) 僅出現於 orphan blob ccd34afb11b3
  該 blob 同時含 access key id 與 secret ⇒ 疑為 .env 的孤兒副本
  in_origin_main=FALSE ／ in_any_remote=FALSE ⇒ **未進遠端**

同名檔內另一組 AWS 憑證（無風險）
  docs/guides/deployment/AWS_S3_VIDEO_SETUP.md
  = AWS 官方文件範例組（AKIAIOSFODNN7EXAMPLE ＋ 78314b11… 之 EXAMPLE 尾綴 secret）
  classification = AWS_DOC_EXAMPLE，非真實憑證

C2-B 待確認（本輪未查，⛔ 不代執行線上操作）
  該 Access Key ID 目前狀態：active? inactive? deleted? 屬於現行帳號? 或歷史憑證?
  若仍 active → 建議停用／輪換
  若早已 deleted → SEC-02 remediation 可落在記錄與風險接受，⛔ 不需強制 history rewrite
```

## 8. False-positive classifications

```text
openai_like  原始 83 objects → 邊界修正後真實 token 僅 6 個
  誤命中主因：pattern 未設左邊界，"task-5-4-…"、"risk-…" 中的 "sk-" 被吃進去
  修正：加 (?<![A-Za-z0-9_-]) lookbehind；⚠️ **尾字元類必須維持 [A-Za-z0-9_-]**，
        一度誤縮為 [A-Za-z0-9] 導致含 "-"/"_" 的真 project key 反被漏掉（已回正並自測）
  6 個真 token
    PLACEHOLDER len=32  29 objects  README.md / QUICKSTART.md / docs/guides/*
    PLACEHOLDER len=25  24 objects  .env.example / docs/guides/ENVIRONMENT_VARIABLES.md
    PLACEHOLDER len=23   5 objects  .env.example
    REDACTED    len=28   1 object   PRODUCTION_DEPLOYMENT_CHECKLIST.md line 32
                                    （該行含遮蔽標記且緊接截斷符；長度亦不足真 key）
    LOOKS_REAL  len=164  2 objects  ORPHAN ONLY
    LOOKS_REAL  len=160  1 object   ORPHAN ONLY

aws_access_key_id 5 objects → 3 官方範例值 ／ 1 orphan ／ 1 真命中（§7）
aws_secret_ctx    4 objects → 3 官方範例值(pushed) ／ 1 orphan（現行 secret）
db_url_with_pw   13 objects → 值即 DB_PASSWORD
  ⚠️ DB_PASSWORD 的 IDENTICAL_TO_EXAMPLE = **TRUE**
     ⇒ 現行 .env 密碼與已公開的 .env.example 樣板值相同，
       656 個命中物件**不是洩漏事件**（該值從來就不是秘密），
       但**是一項弱憑證缺陷**：若任何非本機環境沿用此值，屬 C2 之外的獨立議題。
jwt_like          2 objects → docs/archive/auth_testing/AUTH_FINAL_TEST_GUIDE.md
                  claims exp=1767154710 → 2025-12-31T04:18:30Z ⇒ **已過期**
anthropic_like / google_api_key / slack_token / github_token / private_key_block
                  全部 0 objects
```

## 9. Sensitive filename history

```text
POSITIVE_CONTROL(.env.example 出現在 committed paths) = HIT ⇒ 本節否定結論可信
sensitive_path_matches = 10

  [TEMPLATE] .env.example
  [TEMPLATE] backend/.env.example
  [REVIEW]   backend/.env.docker
             → OPENAI_API_KEY = PLACEHOLDER(len 20)、SECRET_KEY = PLACEHOLDER(len 41)
  [REVIEW]   knowledge-admin/frontend/.env.development   → 無 KEY/SECRET/TOKEN/PASSWORD 賦值
  [REVIEW]   database/init/12-create-ai-knowledge-system.sql.backup → 無
  [REVIEW]   knowledge-admin/frontend/src/views/.backup                → 無
  [REVIEW]   rag-orchestrator/routers/.backup                          → 無
  [REVIEW]   rag-orchestrator/routers/.backup/audience_config.py.backup → 無
  [REVIEW]   rag-orchestrator/routers/api_endpoints.py.bak             → 無
  [REVIEW]   rag-orchestrator/services/business_scope_utils.py.backup  → 無

⭕ 裸 `.env` 與 `.env.bak-20260822` **從未進入版控**（依 PC-3 此否定結論成立）
```

## 10. Known limitations

```text
L1  等同假設未證實 —— 見 §6：CURRENT_ENV_KEY == TRANSCRIPT_EXPOSED_KEY 為
    ASSUMED_FROM_HANDOFF_HISTORY，NOT_INDEPENDENTLY_PROVEN。
L2  exact-value scan 只能證明「掃描當下取得的值」不在 history；
    任何**已被替換掉且未留副本**的舊值，本輪無法比對（僅能靠 pattern 面覆蓋）。
L3  pattern 覆蓋非完備：只涵蓋 10 類。自訂格式、無前綴的高熵字串、
    加密或編碼後的憑證不在偵測範圍。
L4  掃描僅涵蓋 **Git 物件**。未掃 CI 設定、部署主機、容器 image、
    S3 物件、Monday/Slack 等外部系統中的憑證複本。
L5  jgb2 等其他 repo 未在本次 scope 內。
L6  「該 AWS Access Key ID 是否仍 active」為線上狀態，本輪**未查**（屬 C2-B）。
L7  orphan 物件會被未來的 git gc --prune 回收；本檔記錄的 blob id 屆時可能不再存在，
    此為預期行為，⛔ 不得視為本檔失效。
```

## 11. Remediation decisions pending

```text
C2-A OpenAI          revoke/rotate 現行 key ＋ 盤查兩把 orphan 歷史 key 是否仍 active
C2-B AWS             盤查 Access Key ID 狀態（active/inactive/deleted/歸屬）→ 決定停用或輪換
                     paired secret exposure = NOT_FOUND（pushed 面）
C2-C Git             remediation 後重掃 ／ orphan ODB 清理（optional）
                     ／ history rewrite 決策 ／ push readiness 重評

HISTORY_REWRITE = DEFERRED_RISK_DECISION      ⛔ 不是必做 remediation
  理由：pushed 面實際暴露物僅 AWS Access Key ID（identifier，非可單獨使用之秘密）；
        pushed 面**未**發現配對 AWS secret，亦**未**發現現行 OpenAI key。
        rewrite 的 blast radius = origin/main ancestry ＋ 5 條本地分支
        ＋ origin/feat/form-chaining ＋ 所有協作者的 clone／branch 同步，
        與暴露物的實際 credential power 不成比例。
  ⛔ 在 C2-A/B 完成並重掃之前，**不得執行 git filter-repo 或任何歷史改寫**。

SEC-01 / SEC-02 能否關閉、以及 push blocker 能否解除
  ⇒ 一律等 C2 完成並重新掃描後再裁，⛔ 本檔不得作為關案依據。
```

## 12. Explicit rule —— secret values never stored in evidence

```text
本檔與本次審查的所有輸出，對任何憑證僅記錄：
    type ／ length ／ entropy ／ classification ／ object id ／ ref ／ path
    ／ SHA-256 fingerprint（僅在需要 correlation 時）
⛔ 不記錄完整值、⛔ 不記錄前綴或後綴、⛔ 不記錄完整匹配行、
⛔ 不記錄任何足以重建該值的片段（連 sk-…xxxx 形式亦禁止）。
日後若需辨認「是否同一把 key」，一律以 §4 的 SHA-256 比對，⛔ 不得回填明文。

若需在本機取回某個值以執行 C2（例如到 AWS 主控台查該 Access Key ID 狀態），
於本機終端自行讀取，⛔ 不得貼進任何對話、issue、工單或本檔。
```

---

## 附：可重現性

```text
掃描腳本（一次性工具，⛔ 不進產品程式碼）
  sec_c1_scan.py      全 ODB 串流掃描 ＋ PC-1/PC-2
  sec_c1_resolve.py   命中物件 → path / reachable / pushed 對映
  sec_c1_classify.py  placeholder vs real 分類 ＋ orphan provenance ＋ PC-3
  sec_c1_final.py     word-boundary 修正 ＋ ref 對映 ＋ JWT claims ＋ 敏感檔內容
所有腳本為唯讀：僅使用 git rev-list / cat-file / log / branch / merge-base，
未執行任何 Git 寫入、未 push、未改寫歷史、未觸碰 production。
```
