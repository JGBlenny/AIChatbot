# runtime replica of sealed R10P artifacts

⛔ **本目錄不是 authority。** authority 在
`.kiro/specs/conversational-routing-execution/r10p/`（registry-v2.json 為 responsibility
identity 的唯一權威來源）。

本目錄存在的唯一理由：`docker-compose.prod.yml` 的 build context 是 `./rag-orchestrator`，
`COPY . .` 搆不到 repo 根層的 `.kiro/`。改用根層 context 不可行（排除 .git 後仍 2.4 GB，
且四個服務皆採 per-service context 慣例）。

⚠️ 因此這是 **replica**，⛔ 不是第二個 authority：
- 內容必須與 `.kiro/.../r10p/` 對應檔**逐位元相同**；
- 由 `scripts/audit` 的 `R10P_ARTIFACT_REPLICA_DRIFT` 不變量把關；
- ⛔ 不得只改本目錄；要更新一律先改 `.kiro` 正本再同步過來。

⚠️ 歷史教訓：2026-08-30 曾以 `docker cp` 把 artifacts 放進容器 `/spec`，到 2026-09-01
已與正本 drift（embeddings 與 manifest 皆不符，且 manifest 缺 `embeddings_file_digest`）。
⛔ `docker cp` 不得作為 runtime prerequisite。
