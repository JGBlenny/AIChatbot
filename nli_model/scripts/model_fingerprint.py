#!/usr/bin/env python3
"""模型目錄指紋（DSP-033 r18 F-7）。

**為什麼指紋量的是整個目錄而不是權重檔**：`config.json` 決定 `id2label`
（ENTAILMENT 是第幾格）、`vocab.txt` 決定切詞——這兩個檔任一被換掉，
同一份 `pytorch_model.bin` 會算出**完全不同**的 p_ent，而 τ=0.40 是在
特定切詞與特定標籤順序上校準出來的。只釘權重檔等於守住了鎖、卻讓門框可以換。

指紋定義（⛔ 不得改，改了所有既有映像的期望值一次作廢）：
    對「納入集合」內的檔案按**相對路徑字典序**排序，逐檔把
        f"{相對路徑}\\n{該檔內容的 sha256 十六進位}\\n"
    串起來，再對整串 UTF-8 位元組取 sha256。

「納入集合」＝ `INCLUDED_FILES`：`config.json`／`vocab.txt`／`pytorch_model.bin`。
⛔ 刻意不含 `README.md`／`.gitattributes`：那兩個檔在 HF 上會被無關的
文件修訂動到，把它們納入會讓指紋因為「作者改了說明文字」而失效，
於是每次都得重算期望值——一個天天在喊狼來了的警報等於沒有警報。
⚠️ 反過來說，`snapshot_download` 也必須用同一份 `allow_patterns`，
否則目錄裡多出來的檔案雖然不進指紋，卻會讓「目錄＝指紋所描述的東西」
這句話不再成立。兩處清單由 `INCLUDED_FILES` 這一個常數同時供應。

用法：
    python3 model_fingerprint.py <模型目錄>            # 印出指紋
    python3 model_fingerprint.py <模型目錄> <期望值>    # 不符即 exit 1
"""
from __future__ import annotations

import hashlib
import os
import sys

#: 進指紋、也進 `snapshot_download(allow_patterns=...)` 的檔案清單（唯一來源）。
INCLUDED_FILES = ("config.json", "pytorch_model.bin", "vocab.txt")

#: 指紋值寫進模型目錄的這個檔，供 `api_server.py` 啟動時免重算即可回報 `model_sha`。
#: ⚠️ 它是**快取**不是憑據——`api_server` 仍會實算一次跟它比對（見 `load_state`）。
DIGEST_FILENAME = ".dir_sha256"

_CHUNK = 1024 * 1024


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def directory_fingerprint(model_dir: str) -> str:
    """回傳模型目錄指紋。

    🔴 納入集合裡任一檔案**不存在**一律 raise，⛔ 不跳過——
    「少一個檔」與「檔案內容不同」都必須改變結論，而跳過會讓少檔的目錄
    算出一個看起來很正常的指紋（在 `_file_sha256` 讀不到就回空字串的
    寫法下，甚至會讓兩個都缺檔的目錄互相「相符」）。
    """
    parts = []
    for name in sorted(INCLUDED_FILES):
        path = os.path.join(model_dir, name)
        if not os.path.isfile(path):
            raise FileNotFoundError(
                f"模型目錄缺少 {name}（{path}）——指紋無法計算，⛔ 不得以部分檔案算出指紋")
        parts.append(f"{name}\n{_file_sha256(path)}\n")
    return hashlib.sha256("".join(parts).encode("utf-8")).hexdigest()


def main(argv: list) -> int:
    if len(argv) < 2:
        print("用法：model_fingerprint.py <模型目錄> [期望的 sha256]", file=sys.stderr)
        return 2
    model_dir = argv[1]
    actual = directory_fingerprint(model_dir)
    expected = argv[2].strip() if len(argv) > 2 else ""
    if not expected:
        # 首次建置的 bootstrap 路徑：印出實得值後**失敗**，⛔ 不預設放行。
        # 沒有期望值就建得起來，等於這條檢查在 CI 上永遠是綠的裝飾品。
        print(f"NLI_MODEL_DIR_SHA256={actual}")
        print(
            "🔴 未提供 NLI_MODEL_SHA256 建置參數：請以上面這個值重跑\n"
            "   docker build --build-arg NLI_MODEL_SHA256=<值> ...\n"
            "   並把它寫回 nli_model/Dockerfile 的 ARG 預設值（進版控＝已審核）。",
            file=sys.stderr,
        )
        return 1
    if actual != expected:
        print(
            f"🔴 模型目錄指紋不符：期望 {expected}，實得 {actual}——"
            "權重／設定／詞表至少一項不是預期的那份，⛔ 不得繼續建置。",
            file=sys.stderr,
        )
        return 1
    with open(os.path.join(model_dir, DIGEST_FILENAME), "w", encoding="utf-8") as fh:
        fh.write(actual)
    print(f"✅ 模型目錄指紋相符：{actual}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
