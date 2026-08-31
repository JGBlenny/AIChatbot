# SEC-C2 —— Remediation Ledger（活帳，可續填）

> 本檔與 `sec-c1-audit.md` 分工明確：
>
> ```text
> sec-c1-audit.md   immutable forensic evidence   「當時掃到什麼」   ⛔ 一字不動
> sec-c2-ledger.md  mutable remediation ledger    「後來做了什麼、還差什麼」
> ```
>
> ⛔ 本檔同樣**不儲存任何 secret 值**：僅記狀態、判定、SHA-256 指紋引用。
> 指紋一律引用 C1 §4 的封存值，⛔ 不在此重列、⛔ 不回填明文。

```text
ledger_opened   2026-08-31
repo            /Users/lenny/jgb/AIChatbot
branch          fix/retrieval-routing-stability
C1 checkpoint   commit 8e922c0 ／ evidence sha256 c01b317761cbe3bd55d2446c6a7d503186170c362aef2dc33199722bb5bbbe49
全域凍結中       ⛔ 不 rotate（除 SEC-01 授權項）／⛔ 不 history rewrite／⛔ 不 push
```

---

## 不變量

### SEC-C2-L1 —— ACTION ≠ EVIDENCE

```text
planned              已規劃，尚未執行
CONSOLE_REPORTED     外部主控台顯示已完成 —— 這是**操作紀錄**，不是驗證
LOCALLY_VERIFIED     本機以決定性方式實測（雜湊比對、容器內讀值）
EXTERNALLY_VERIFIED  對外部權威系統實測（API 回應碼、STS 認證）

⛔ 不得因為「操作已做」就把對應命題直接寫成 CONFIRMED。
⛔ CONSOLE_REPORTED 永遠不可單獨升級為 EXTERNALLY_VERIFIED。
每一條 pending 轉為 evidence 時，必須標明它屬於上述哪一級。
```

### SEC-C2-L2 —— 否定結論需正對照

```text
任何回報「已失效／查無／不存在」的檢查，必須同時跑一個已知必然成立的對照項；
對照落空即判工具或路徑故障，⛔ 該否定結論作廢。
（沿用 C1 的四道正對照慣例。）
```

### SEC-C2-L3 —— ⛔ 不為取證而製造新的 secret artifact

```text
為了實測「舊 key 已撤銷」而把舊 secret 另存成檔案 = 禁止。
獨立 401 是**加強證據**，不是 closure 的必要條件。
可用的替代路徑：撤銷後、容器 recreate 之前，執行中的容器 environment
仍持有舊值（該值即將被銷毀，非新建 artifact），可在單一 process 內取用驗證。
若時機已過，直接接受 NOT_AVAILABLE，⛔ 不得回頭重建。
```

---

## SEC-01 —— OpenAI transcript exposure

```text
status = OPEN
action = ROTATE_NOW            （唯一必做、最高優先）
history rewrite = NO           （C1 已證現行 exact value 在 Git 內 0 hit）
```

### evidence

```text
[LOCALLY_VERIFIED]    current host key matches C1 baseline        = CONFIRMED
                      （.env 之 SHA-256 == C1 §4 封存值）
[LOCALLY_VERIFIED]    container currently matches host            = CONFIRMED
                      （aichatbot-rag-orchestrator 容器內同一指紋）
[LOCALLY_VERIFIED]    comparator can detect difference            = CONFIRMED
                      （比對器對合成不同值判為不同，非恆真）
[EXTERNALLY_VERIFIED] orphan historical keys = INVALID / HISTORICAL_ONLY
                      orphan-1 blob 639715e1e15b… → /v1/me 401 ＋ /v1/models 401
                      orphan-2 blob 474e58c7b692… → /v1/me 401 ＋ /v1/models 401
                      正對照（SEC-C2-L2）：現行 key 對同兩端點回 200 ⇒ 401 可信
                      ⇒ ⛔ 無需 revoke、⛔ 無需為它們清 ODB
[EXTERNALLY_VERIFIED] current key is ACTIVE                       = CONFIRMED（/v1/me 200）
[LOCALLY_VERIFIED]    committed-history exposure of current exact value = NOT_FOUND
                      （C1：全 ODB 14897 物件／1.37e9 bytes，可達與 orphan 皆 0 hit）
```

⚠️ 保留 C1 的限制，⛔ 引用時不得省略：
```text
CURRENT_ENV_KEY == TRANSCRIPT_EXPOSED_KEY
  = ASSUMED_FROM_HANDOFF_HISTORY
  = NOT_INDEPENDENTLY_PROVEN
（惟兩種情況下皆應輪換，故此假設不影響 ROTATE_NOW 之決定。）
```

### pending

```text
[ ] old key revoked
      REVOKED_CONSOLE_REPORTED        = ____ （YES／NO）
      REVOKED_INDEPENDENTLY_VERIFIED  = ____ （YES／NOT_AVAILABLE）
      ⚠️ 拆兩欄係刻意：Console 顯示已撤銷屬 CONSOLE_REPORTED，⛔ 不可自動升級。
      ⚠️ 依 SEC-C2-L3，若無法在不新建 artifact 的前提下取得舊值，
         直接記 NOT_AVAILABLE，⛔ 不得為此另存 secret。
[ ] replacement created                       （使用者於 Console 執行）
[ ] .env updated                              （⛔ 不同步寫入 .env.bak-20260822）
[ ] container recreated
      docker compose -f docker-compose.prod.yml up -d --force-recreate rag-orchestrator
      ⚠️ docker restart 無效：compose 以 environment: ${OPENAI_API_KEY} 插值，
         值在 container 建立時固定
[ ] container_key_changed = YES               （容器內 SHA-256 ≠ C1 §4 baseline）
[ ] replacement /v1/me = 200
[ ] old key /v1/me = 401  OR  NOT_INDEPENDENTLY_VERIFIED
[ ] .env.bak-20260822 秘密值 redact 為 <REDACTED_SEC_C2>
      ⚠️ 不可逆本機改寫，僅在 revoke 完成後執行
[ ] post-remediation exact/pattern rescan clean（含四道正對照）
```

### closure 條件

```text
以上 pending 全數完成且 rescan clean ⇒ SEC-01 eligible to CLOSE
⛔ SEC-02 的 AWS rotation **不是** SEC-01 的 closure prerequisite（兩條事件分開）
```

### 目前卡點

```text
BLOCKED_ON_USER_ACCOUNT_ACTION
  OpenAI Console 的 revoke 與 create 需使用者本人登入其帳戶執行；
  此處無法代為登入或執行帳戶動作。
  使用者完成後回報，本檔續填其餘欄位。
```

---

## SEC-02 —— AWS Access Key ID in public history

```text
status  = OPEN
finding = REMOTE_HISTORY_CREDENTIAL_IDENTIFIER_EXPOSURE
action  = ROTATE               （defense-in-depth，優先度低於 SEC-01）
history rewrite = NOT_REQUIRED
```

### confirmed

```text
[EXTERNALLY_VERIFIED] repo public
                      gh repo view → visibility=PUBLIC ／ 匿名 HTTPS 探測 200
[LOCALLY_VERIFIED]    access key id present in pushed history
                      blob 4f3a9ba9210f… ／ docs/archive/2025-Q4/deployment/
                      PRODUCTION_DEPLOYMENT_CHECKLIST.md line 33
                      in_origin_main=TRUE；指紋比對確認即現行 .env 那把
[LOCALLY_VERIFIED]    paired secret not found in pushed history
                      現行 secret 僅見於 orphan blob ccd34afb11b3…（不可達、不可 push）
[EXTERNALLY_VERIFIED] current credential authenticates via STS
                      以 .env 憑證、阻斷 profile 回退後 get-caller-identity rc=0
                      ⇒ ACTIVE_LONG_TERM_CREDENTIAL = CONFIRMED

定性（⛔ 不得放寬）
  REMOTE_HISTORY_CREDENTIAL_IDENTIFIER_EXPOSURE = CONFIRMED
  FULL_CREDENTIAL_EXPOSURE                      = NOT_SUPPORTED
  ⛔ 不得表述為 "AWS credential compromised"
  理由：Access Key ID 單獨不能登入 AWS；輪換理由是「仍 active 的長期憑證，
        其 identifier 已永久進入 public Git history」，屬 defense-in-depth。

未取得
  IAM key metadata = UNAVAILABLE
    .env 憑證與 default profile（經證實為同一 AWS 帳號）皆回 AccessDenied
    ⇒ Status 由 STS 成功反推為 Active（Inactive key 無法通過 STS）
    ⇒ last_used = Unknown，⛔ 不得記為 Never
```

### pending

```text
[ ] replacement credential created            （Console 建立，⛔ 不用 CLI create-access-key，
                                                 其 stdout 會完整輸出 SecretAccessKey）
[ ] services recreated                        （⚠️ 不只 rag-orchestrator，
                                                 所有吃 ${AWS_*} 的服務都要 recreate）
[ ] replacement functionality confirmed       （S3 影片／assistant-reports 讀寫）
[ ] old credential inactive                   （aws iam update-access-key --status Inactive）
[ ] observation window completed              （建議 24–48h）
[ ] old credential deleted / retained-with-reason
⚠️ 順序不可顛倒：先建新、確認服務、再停舊、觀察、最後刪除。
```

---

## C2-D —— PUBLIC_DEFAULT_CREDENTIAL_REUSE

```text
status = OPEN
```

### confirmed

```text
[LOCALLY_VERIFIED] current .env DB_PASSWORD == public .env.example value
                   PUBLICLY_KNOWN_CREDENTIAL = CONFIRMED
                   （repo 為 public ⇒ 該值任何人可讀）
```

### 尚未確立

```text
ENVIRONMENT_SCOPE = NOT_ESTABLISHED
RISK_DISPOSITION  = NOT_YET_JUDGEABLE

⛔ 不得以「它一直就在 .env.example」當作無風險論據。
   該事實只能證明「這不是一次新的 secret leak」，
   ⛔ 不能證明它適合作為真實環境的 credential。
```

### pending

```text
[ ] enumerate environments using same DB_PASSWORD
[ ] determine network reachability
[ ] classify each as local / test / staging / prod
[ ] decide disposition，判準：
      只有本機隔離的 test/admin DB 且外部不可達 → RISK_ACCEPTED_LOCAL_DEFAULT
      任何 staging／production／remotely reachable DB 沿用 → 必須 rotate/change
      ⛔ 後者不得 risk-accept 成「普通預設值」
```

---

## PUB-01 —— PUBLIC_REPOSITORY_ARTIFACT_DISCLOSURE

```text
status = OPEN（產品／資訊揭露決策，⛔ 非安全掃描問題）
```

### confirmed

```text
[EXTERNALLY_VERIFIED] target repository = PUBLIC
[LOCALLY_VERIFIED]    secret scan = CLEAN
                      445 commits 待 push 差異（CONTROL: diff 8,081,862 bytes = HIT）
                        openai 樣式 0 ／ 私鑰區塊 0 ／ 敏感檔名新增 無
                        AKIA 3 hits → 全為 sec-c1-audit.md 內的 AWS 官方公開範例值
                      .env ／ .env.bak-20260822：tracked=no ／ ignored=YES
```

### 命題邊界

```text
SECRET-SAFE ≠ PUBLICATION-SAFE
PUSH_CONTENT_READINESS = CLEAN 只回答「沒有 credential secret」。
它**完全沒有回答**：.kiro/specs/、HANDOFF、security evidence、內部架構、
缺陷名稱、endpoint／資料模型資訊，是否本來就打算對外公開。
```

### pending

```text
[ ] PUBLIC_DISCLOSURE_APPROVED = YES
    或
[ ] exclusion / removal of non-public artifacts
⛔ 在其一完成前不得 push。
```

---

## 續填規約

```text
1. 每次續填只改本檔，⛔ 不動 sec-c1-audit.md。
2. 每一條由 pending 轉 evidence 時，必須標註 SEC-C2-L1 的級別
   （CONSOLE_REPORTED／LOCALLY_VERIFIED／EXTERNALLY_VERIFIED）。
3. 任何否定結論必須附正對照（SEC-C2-L2）。
4. ⛔ 不得為取證而新建 secret artifact（SEC-C2-L3）。
5. 事件關閉需在該區塊明記 closure 依據與日期；⛔ 不得只把 status 改成 CLOSED。
```
