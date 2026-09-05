#!/usr/bin/env python3
"""建置期下載 NLI 權重（DSP-033 P2-10／r18 F-7）。

⛔ **執行期不拉**：權重隨映像走，容器啟動時只讀本地檔（`local_files_only=True`）。
理由與 F-16（semantic-model 執行期下載）記在 BACKLOG 的是同一件事——執行期
下載會讓「這台機器現在跑的是哪一份權重」變成一個要去問網路的問題，而
`model_sha` 的整套稽核前提是它答得出來。

`revision` 綁**commit sha**（⛔ 不綁 `main`）：分支會前進，tag 會被移動，
只有 commit sha 是不可變的。這一層與目錄指紋是兩道獨立的檢查——
revision 管「跟 HF 要的是哪一版」，指紋管「拿到的真的是那一版」。
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model_fingerprint import INCLUDED_FILES  # noqa: E402

#: IDEA-CCNL/Erlangshen-Roberta-110M-NLI，2026-09-05 由 HF API 取得的現行 main commit。
#: 查證：`curl -s https://huggingface.co/api/models/IDEA-CCNL/Erlangshen-Roberta-110M-NLI | jq -r .sha`
DEFAULT_REPO_ID = "IDEA-CCNL/Erlangshen-Roberta-110M-NLI"
DEFAULT_REVISION = "864d25be3ce5e90d9193cb49d9fbd52722cdc6b0"


def main() -> int:
    repo_id = os.getenv("NLI_MODEL_REPO", DEFAULT_REPO_ID)
    revision = os.getenv("NLI_MODEL_REVISION", DEFAULT_REVISION)
    target = os.getenv("NLI_MODEL_DIR", "/models/erlangshen-110m-nli")

    # ⚠️ 輸入檢查在**任何 import 與任何 I/O 之前**：revision 不合格時這支要能在
    # 沒有 huggingface_hub 的環境（例如 rag-orchestrator 測試容器）也答得出來，
    # 否則這條檢查只在會下載的那個映像裡跑得到，也就等於沒有被測過。
    if len(revision) != 40 or not all(c in "0123456789abcdef" for c in revision.lower()):
        print(
            f"🔴 NLI_MODEL_REVISION={revision!r} 不是 40 位 commit sha——"
            "⛔ 不接受分支名或 tag（兩者都會移動）。",
            file=sys.stderr,
        )
        return 1

    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=repo_id,
        revision=revision,
        local_dir=target,
        local_dir_use_symlinks=False,
        # ⚠️ 與 `model_fingerprint.INCLUDED_FILES` 同一份清單：指紋描述的目錄
        # 與實際下載下來的目錄必須是同一個集合，⛔ 不得各列各的。
        allow_patterns=list(INCLUDED_FILES),
    )
    print(f"✅ 已下載 {repo_id}@{revision[:12]} → {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
