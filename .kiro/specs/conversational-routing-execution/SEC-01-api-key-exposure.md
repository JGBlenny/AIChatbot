# SEC-01 — API_KEY_EXPOSURE（2026-08-30，OPEN）

## 事故

盤查 embedding provider model id 時，我對容器執行了 `env | grep -i "model\|openai"`，
該 grep 同時命中 `OPENAI_API_KEY`，且我加的 redact 未生效 ⇒ **金鑰明文進入本次 session transcript**。

```text
定性       視為 **compromised**
根因       我自己踩了既有紀律「查詢／派工不得整包 dump env」；redact 只是形式、未驗證
⚠️ 這不是代理造成的——是主 session 自己下的指令。
```

## 業主裁定：SEC-01 為與 C2 **正交**的 push blocker

```text
required_before_any_push:
  - exposed key revoked
  - replacement key installed where required
  - repository / committed history checked for accidental secret persistence

does_not:
  - invalidate C2-SCORE evidence
  - require rollback of canonical embeddings
  - alter R10／C2 product verdicts
```

⇒ **⛔ 不因本事故停掉本地 C2 實作**；撤銷金鑰是 **push 前的硬閘**。

## 處置建議（業主指出，⛔ 我不代執行）

```text
1. 到該 key 所屬 Project／Organization 的 API key 設定**撤銷**外洩 key，再建立替代 key
2. 若該 key 只用於建 embedding ⇒ 替代 key 考慮 **restricted permissions**（限制 endpoint 權限），
   ⛔ 不要繼續給不必要的全權限
3. 檢查 repo／已 commit 的 history 是否有 secret 殘留
```

⚠️ 線上操作一律由業主自己執行；本 session ⛔ 不代跑撤銷／輪替指令。

## 本地已完成的相關檢查

```text
· 本次 C2 artifact 的建置 request body 只有 `{"text": ...}`——⛔ 未攜帶任何金鑰參數
· manifest semantics correction 未重新呼叫 API（⛔ 未再使用該 key）
· 待業主確認：committed history 的 secret 掃描（⛔ 我未代掃 repo 全史）
```
