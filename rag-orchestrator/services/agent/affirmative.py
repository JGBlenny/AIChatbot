"""T3 肯定語＝授權（Plan
`inputs/plan-walkthrough-fixes-batch2-20260909.md` §4｜
knowledge-outline-and-intent-architecture:T3）。

`AFFIRMATIVE_WORDS` 是**凍結元組**——逐字等於 Plan §4 那一行，程式不得多不得
少、不得改順序（`is_affirmative` 只認整句等值，⛔ 不做包含比對：「對 查」
「對，列出來」都不算，理由見 Plan §4「⛔ 不代模型執行工具」——把包含比對當
授權訊號等於讓任何一句帶了肯定字的長句都被誤判成「使用者同意送出」）。
"""
from __future__ import annotations

from typing import Any

#: Plan §4 凍結元組——⛔ 程式不得多、不得少、不得改順序。
AFFIRMATIVE_WORDS: tuple[str, ...] = (
    "對", "好", "是", "嗯", "可以", "好的", "好啊", "對啊", "對呀",
    "是的", "沒錯", "請", "ok", "OK", "okay",
)

#: 去除的是**首尾**標點與空白的封閉集合（中英文常見句尾／句首符號），
#: ⛔ 不動句中字元——「對，列出來」的逗號在句中，剝完仍是「對，列出來」，
#: 不等於任何一個肯定詞，因此仍判非肯定（整句等值本身已經擋掉這種句子，
#: 這裡的收斂集合只是讓「對。」「對！」「(對)」這類收尾／包裹符號不誤判成
#: 「不是純肯定語」）。
_STRIP_CHARS = (
    "。，、；：！？…—～·"
    "「」『』（）()[]{}【】<>《》\"'‘’“”"
    ".,!?;:~-_"
    " \t\n\r　"
)


def is_affirmative(message: Any) -> bool:
    """本回合訊息**整句**是否屬於 `AFFIRMATIVE_WORDS`（去除首尾標點與空白後
    的整句等值，⛔ 子字串／包含比對一律不算）。非字串一律 `False`。
    """
    if not isinstance(message, str):
        return False
    stripped = message.strip(_STRIP_CHARS)
    return stripped in AFFIRMATIVE_WORDS


__all__ = ["AFFIRMATIVE_WORDS", "is_affirmative"]
