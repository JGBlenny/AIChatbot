"""句末標點正規化（Plan `plan-walkthrough-fixes-batch2-20260909.md` §5 T4）。

⛔ 只做這一件事：連續的句尾終結標點收斂成第一個。不做其他任何文字改寫——
不補標點、不刪除非終結標點、不動內文其他字元。

封閉規則（Plan 逐字）：
1. 連續的全形終結標點（`。？！` 這個封閉集合，長度 ≥ 2）收斂成第一個字元
   （例：「嗎？。」→「嗎？」；「。。」→「。」；「？！」→「？」）。
2. 半形 `?`／`!` 後面緊接一個以上全形 `。`，視為同一種情況，收斂成該半形字元本身
   （例：「單身狗?。」→「單身狗?」）。
"""
from __future__ import annotations

import re

#: 規則 1：全形終結標點的封閉集合，連續 2 個以上收斂成第一個。
_FULLWIDTH_RUN_RE = re.compile(r"[。？！]{2,}")

#: 規則 2：半形問號／驚嘆號後面緊接的全形句號一律去掉，只留半形字元本身。
_ASCII_FOLLOWED_BY_FULLWIDTH_PERIOD_RE = re.compile(r"([?!])。+")


def normalize_terminal_punctuation(text: str) -> str:
    """把連續的句尾終結標點收斂成第一個字元；其餘文字原樣返回。

    先套規則 2（半形＋全形句號），再套規則 1（純全形的連續終結標點）——
    兩條規則彼此不重疊字元類別，套用順序不影響結果。
    """
    if not text:
        return text
    text = _ASCII_FOLLOWED_BY_FULLWIDTH_PERIOD_RE.sub(lambda m: m.group(1), text)
    text = _FULLWIDTH_RUN_RE.sub(lambda m: m.group(0)[0], text)
    return text


__all__ = ["normalize_terminal_punctuation"]
