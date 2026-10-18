# 答案品質評估與先探測 Steering

> 由 spec **dev-workflow-hardening** D1 沉澱（2026-10-18）。本軌道評估「站內幫手回答品質」，與 `testing-code.md`（程式碼行為正確性）分開。

## 一、先探測（spike）

**觸發**：設計依賴模型行為（「模型會填這個欄位」「模型會呼叫這個工具」「模型會照這句政策文說」）時，實作前的第 0 步。

**做法**（照 Extreme Programming 的 spike，原文存 `~/jgb-archive/devflow-20261018/sources/xp-spike.txt`：「A spike solution is a very simple program to explore potential solutions. Build the spike to only addresses the problem under examination and ignore all other concerns. Most spikes are not good enough to keep, so expect to throw it away.」）：

1. **只回答那一個問題**：寫明要確認的模型行為與判定方式。
2. **做完即丟**：探測腳本不進正式程式。
3. **有時限**：數回合、數分鐘級；結果寫進計畫第 0 步紀錄再動手。

事例：W1 假設「strict 必填模型就不會略過」未探測，實作後才發現 gpt-oss 一律填 null（多兩輪實作與審查）；W1c 先探測數分鐘即順利。

## 二、評估一律用 eval-harness

位置：`~/jgb-archive/eval-harness/`（⛔ 進 repo：題目與回答原文不進 git，見記憶「內部評估個資」）。用法見 `run.py` 檔頭；單元測試 `python3 -m unittest discover -s tests`。

它把下列量尺錯誤變成預設防線（不靠記得）：

| 防線 | 事件 |
|---|---|
| 每回合存完整 answer、模型輸出全文、`decision_snapshot`；原始請求／回應存每模型前 5 筆＋所有錯誤 | R3 shim 只存 400 字，#2 有一回合判不出 |
| 停容器前收 shim 紀錄，收不到非 0 退出 | W1 停容器後紀錄遺失只能重跑 |
| 共用解析 `harness/parse.extract_json` | 舊解析法 63 筆判失敗 35 筆，差點誤判 gpt-oss 做不到 |
| 盲判批次 `judge-build`／`judge-check`：每批 6 誘餌（知識題 `v2/decoys.json`；探針題 `decoys/probe.json` 各標籤 2）、≥5/6 才採用、分母不符非 0 | 誘餌被打散 1/4/1；探針批誘餌與清單不符 |
| 題庫有答案檢查 `bank`：每題 `target_fine` 存在且已審 | v1 題庫混正本沒答案的題目 |
| 報告頭印 HEAD／diff 雜湊，基準與改後差異不只受測檔即警告 | R3 現值量在已撤回的版本上 |

## 三、環境坑（照做即可）

- 評估容器的 openai SDK 不收 `reasoning_effort` 參數 ⇒ 用 `extra_body={"reasoning_effort": ...}`。
- dev 映像沒有 pytest ⇒ 程式測試一律 `scripts/run-tests.sh`。
- 評估容器以 `--rm` 起，停掉即消失 ⇒ 只用 harness 起停。
- **收尾稽核固定三步**（D3-2；業主 2026-10-18 選「維持每次由你手跑」）：本機 `aichatbot-rag-orchestrator` 由 `docker-compose.prod.yml` 起、程式包在映像裡，`make audit` 不變量 3 會比對容器檔與工作樹 ⇒ 改了 `rag-orchestrator/` 後：
  1. 請業主在提示列跑 `! cd /Users/chenqinghuang/dev/work/AIChatbot && docker compose -f docker-compose.prod.yml up -d --build rag-orchestrator`（權限分類器判這行為「[Production Deploy]」，⛔ 代理自行重建或繞過）。**本機接 Bedrock gpt-oss 時**改用 `! cd /Users/chenqinghuang/dev/work/AIChatbot && docker compose -f docker-compose.prod.yml -f docker-compose.bedrock-local.yml up -d --build rag-orchestrator`——不帶覆寫檔重建會回到 OpenAI，且 `USE_MOCK_JGB_API` 改依 `.env`（非 mock）；量測打常駐服務用 eval-harness `run.py turns B … --target resident`（開頭自動 mock 檢查）。
  2. 健康檢查：`curl -s -o /dev/null -w '%{http_code}' localhost:8100/api/v1/health` 回 200。
  3. `make audit`，以 `OVERALL: PASS` 為準；容器未重建前的 audit 結果不採用。
