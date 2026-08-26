# P2.1 執行結果：**STOP**（guard 生效，7 項中 6 項不符）

> 2026-08-26｜執行位置：`lennydeMacBook-Pro-2.local` 的 `aichatbot-rag-orchestrator`（Up 33 小時）
> 依 runbook §P2.1，任一項不符即停，不得續行 P2.2。

## 一、四個邊界

```text
① RAG runtime ≠ production   ✅ 本機容器，非 production 主機
② RAG DB      ≠ production   ⚠️ **需業主裁定**：DB_NAME=aichatbot_admin（本機 postgres），
                                 但業主已聲明「本地與線上資料相同」——
                                 這代表它雖非 production 執行個體，卻承載**等同 production 的資料**。
                                 P2.2 的 migration 因此不是「在沙盒改東西」。
③ USE_MOCK_JGB_API=false     ❌ 實得 **true** —— 現在驗的是替身，P2 沒有意義
④ JGB_API_BASE_URL=preview   ✅ https://preview.jgbsmart.com
```

## 二、七個旗標（容器內實測）

```text
PREENTRY_ROUTABILITY_GATE      = false        ❌ 應 true
PREENTRY_ROUTABILITY_FACETS    = <UNSET>      ❌ **STOP 條件**：GATE 開了也會 fail-safe 停用
FACET_SCOPE_SALVAGE            = <UNSET>      ❌ 應顯式 false（未宣告 ≠ 已確認）
BRAIN_STRICT_SCHEMA            = <UNSET>      ❌ 應顯式 true（程式預設 on，但同上）
PRESALES_SYNTH_MODEL           = **gpt-4o**   ❌ 應 gpt-4o-mini
USE_MOCK_JGB_API               = true         ❌ 應 false
JGB_API_BASE_URL               = preview      ✅
```

## 三、根因：這個容器**早於今天的 compose 變更**

`Up 33 hours` ⇒ 它是用**舊的** compose 宣告啟動的：
今天補上的三個旗標宣告、以及 `PRESALES_SYNTH_MODEL` 由 gpt-4o 改 mini，
都**還沒進到這個執行中的容器**。

⚠️ 這正是 guard 要抓的東西：`.env`／compose 改了不代表 runtime 生效。
若跳過 P2.1 直接做 P2.4／P2.5，會在 **gpt-4o ＋ 替身** 的組態下驗出「一切正常」，
而那與要上線的組態（mini ＋ 真 API）**不是同一件事**。

## 四、解除條件（指令由業主執行）

```bash
# ① 以新 compose 重建容器（讓今天補的宣告生效）
cd /Users/lenny/jgb/AIChatbot
docker compose -f docker-compose.prod.yml up -d --force-recreate rag-orchestrator

# ② 在該環境的 .env 設定 Stage-1 值
#    PREENTRY_ROUTABILITY_GATE=true
#    PREENTRY_ROUTABILITY_FACETS=bill_diagnosis,billing_anomaly,contract_closeout
#    FACET_SCOPE_SALVAGE=false
#    BRAIN_STRICT_SCHEMA=true
#    PRESALES_SYNTH_MODEL=gpt-4o-mini      ← .env 未設時吃 compose 預設 mini，設了就以 .env 為準
#    USE_MOCK_JGB_API=false                ← ⚠️ 這一項會讓系統開始打真 preview API
#    JGB_API_BASE_URL=https://preview.jgbsmart.com

# ③ 重跑 P2.1-b 逐字比對
```

## 五、續行前必須由業主拍板的一件事

```text
本機這套的 DB **承載等同 production 的資料**（業主自述）。
P2.2 會在其上套 seed_responsibility_delegates_v1.sql（改 knowledge_base 的
對話規則 metadata 與 answer 形狀）。雖然冪等且有 rollback，
但這**不是**在沙盒操作。

因此兩條路，請擇一：
  A. 就在這套上做，接受它等同對「production 等價資料」動刀（有 rollback 腳本）
  B. 另備一份非 production 資料的 DB（dump→restore 到另一個庫名）再做 P2.2-P2.6
```

⚠️ 在此裁定之前，P2.2 不執行。
