"""`AgentSession`——`state["agent"]` 的生命週期封裝（Plan R R3｜
`inputs/plan-structural-refactor-20260910.md` §0 R3 列）。

**本檔是純封裝，⛔ 不改任何鍵的生命週期數值**（FIFO 5／20／50、一次性、
釘住不寫）：`AgentSession` 包住同一個 `state["agent"]` dict（`AgentSession(state
["agent"])`，⛔ 不複製、不改鍵名），提供 `begin_turn`／`end_turn` 兩個回合邊界
方法當**唯一寫點**（取代原本散在 `exit_gates.finalize`／
`runtime._finish_confirm_turn`／`turn_segments` 的 `handoff_cache` 重播三處各自
的欄位寫入），`prompt_segments()` 當範圍釘住判斷的**唯一讀點**（收斂
`recent_refs`／`estate_carry` 兩段各自的 `if scope_estate_id is None`），
`scope_exit()` 清掉全部 `until_scope_exit` 鍵。

## 為什麼是純字面常數，不 import 其他 agent 模組
`turn_context.py`／`completed_actions.py`／`state_store.py` 各自持有自己那個鍵
的「權威定義＋既有測試的 import 路徑」（例：`tests/unit/agent/
test_outline_citation_seed_req.py` 直接 `from services.agent.runtime import
DIALOG_MAX_MESSAGES`）。本檔若去 import 那些模組的常數，會在
`runtime.py`／`completed_actions.py`／`state_store.py` 三者都要「反過來 import
`agent_session`」時繞出一個環（它們也需要 `AgentSession` 類別本身）。故本檔的
11 個鍵名與上限**各自重複宣告一份純字面值**，`tests/unit/agent/
test_agent_session_req.py` 另有一條「與各檔既有常數逐一相等」的正對照守著
不讓兩邊漂移，⛔ 不是「重複了就沒事」。

## 11 個鍵與六種生命週期（KEY_SPECS，封閉表）
`turn`（每回合覆寫或回合內暫存）／`once`（一次性，用掉即清）／
`until_scope_exit`（黏到 `scope_exit()`）／`fifo(n)`（FIFO 上限 n）／
`stamp`（時間戳）／`session`（整個 session 累加，不受回合或範圍影響）。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class Lifetime(Enum):
    """六種封閉生命週期（Plan R R3；⛔ 不得新增第七種——新鍵先回頭裁這一支
    表打不打得進既有六種，打不進去是設計要重談，不是加一種例外）。"""

    TURN = "turn"
    ONCE = "once"
    UNTIL_SCOPE_EXIT = "until_scope_exit"
    FIFO = "fifo"
    STAMP = "stamp"
    SESSION = "session"


@dataclass(frozen=True)
class KeySpec:
    key: str
    lifetime: Lifetime
    fifo_limit: Optional[int] = None


# ---------------------------------------------------------------------------
# 鍵名（⛔ 字面值必須與各自的權威定義逐字相同——見模組 docstring；
# `test_agent_session_req.py` 有逐一相等的正對照）。
# ---------------------------------------------------------------------------
DIALOG_KEY = "dialog"
OUTLINE_KEY = "outline"
HANDOFF_CACHE_KEY = "handoff_cache"
FIXED_STREAK_KEY = "fixed_streak"
PENDING_CONFIRM_KEY = "pending_confirm"
SELECT_SCOPE_KEY = "select_scope"
LAST_ASK_TARGET_KEY = "last_ask_target"
COMPLETED_ACTIONS_KEY = "completed_actions"
IMAGE_SUGGESTION_KEY = "image_suggestion"
ESTATE_CARRY_KEY = "estate_carry"
LAST_TURN_AT_KEY = "last_turn_at"

#: DSP-022：`dialog` 保留的訊息數上限（user＋assistant 各一則算 2；10 輪對話）。
DIALOG_MAX_MESSAGES = 20
#: 2.6 前置 security review P3：`handoff_cache` 每 session 的筆數上限。
HANDOFF_CACHE_MAX = 50
#: DSP-038／W3：`pending_confirm` 每 session 保留的待確認筆數上限。
PENDING_CONFIRM_MAX = 20
#: S2｜Plan batch3 §3、H3：`completed_actions` 的 FIFO 上限。
COMPLETED_ACTIONS_MAX = 5

KEY_SPECS: dict[str, KeySpec] = {
    DIALOG_KEY: KeySpec(DIALOG_KEY, Lifetime.FIFO, DIALOG_MAX_MESSAGES),
    OUTLINE_KEY: KeySpec(OUTLINE_KEY, Lifetime.TURN),
    HANDOFF_CACHE_KEY: KeySpec(HANDOFF_CACHE_KEY, Lifetime.FIFO, HANDOFF_CACHE_MAX),
    FIXED_STREAK_KEY: KeySpec(FIXED_STREAK_KEY, Lifetime.SESSION),
    PENDING_CONFIRM_KEY: KeySpec(PENDING_CONFIRM_KEY, Lifetime.FIFO, PENDING_CONFIRM_MAX),
    SELECT_SCOPE_KEY: KeySpec(SELECT_SCOPE_KEY, Lifetime.TURN),
    LAST_ASK_TARGET_KEY: KeySpec(LAST_ASK_TARGET_KEY, Lifetime.TURN),
    COMPLETED_ACTIONS_KEY: KeySpec(COMPLETED_ACTIONS_KEY, Lifetime.FIFO, COMPLETED_ACTIONS_MAX),
    IMAGE_SUGGESTION_KEY: KeySpec(IMAGE_SUGGESTION_KEY, Lifetime.ONCE),
    ESTATE_CARRY_KEY: KeySpec(ESTATE_CARRY_KEY, Lifetime.UNTIL_SCOPE_EXIT),
    LAST_TURN_AT_KEY: KeySpec(LAST_TURN_AT_KEY, Lifetime.STAMP),
}

assert len(KEY_SPECS) == 11, "KEY_SPECS 是封閉表——11 個鍵，多一個少一個都要回頭對帳"


class AgentSession:
    """把 `state["agent"]` 包成一個實體：`self._state is agent_state`（同一個
    物件，⛔ 不複製）。所有方法只是**落地與 FIFO 修剪**，⛔ 不做任何業務判定
    ——判定仍在各呼叫端（`exit_gates`／`runtime`／`turn_segments`）完成，逐字
    保留原順序與條件；本類別只是把「寫進哪裡、修到多短」收攏成一份。
    """

    __slots__ = ("_state",)

    def __init__(self, agent_state: dict) -> None:
        self._state = agent_state

    @property
    def raw(self) -> dict:
        """底下那個原始 dict——⛔ 僅供過渡期呼叫端相容用，新程式不應該繞過
        本類別的方法直接讀寫它。"""
        return self._state

    # -- FIFO 修剪（集中於此；dict／list 皆保序，先進先出） -----------------
    @staticmethod
    def _trim_fifo_dict(d: dict, limit: int) -> None:
        while len(d) > limit:
            d.pop(next(iter(d)))

    @staticmethod
    def _trim_fifo_list(lst: list, limit: int) -> None:
        if len(lst) > limit:
            del lst[: len(lst) - limit]

    # ── dialog（FIFO 20，訊息計；每回合收尾各出口共用） ──────────────────
    @property
    def dialog(self) -> list:
        return self._state.get(DIALOG_KEY, [])

    def append_dialog(self, user_message: str, answer: str) -> None:
        """DSP-022：回合收尾把「使用者這句＋助理回覆」寫回 `dialog`。"""
        dialog = self._state.setdefault(DIALOG_KEY, [])
        dialog.append({"role": "user", "content": user_message})
        dialog.append({"role": "assistant", "content": answer})
        self._trim_fifo_list(dialog, DIALOG_MAX_MESSAGES)

    # ── outline（回合內暫存；由呼叫端門面寫入前塞、存檔前 pop，R3b 待辦
    #    ——`mcp_facade.py` 不在 R3 擁有的檔案清單內，這裡只提供讀點）────────
    @property
    def outline(self) -> Any:
        return self._state.get(OUTLINE_KEY)

    # ── handoff_cache（FIFO 50；鍵＝同題重問的 cache_key） ──────────────────
    def handoff_cache(self) -> dict:
        """回同一個 `dict`（⛔ 不是副本）——`turn_segments.run_program_segments`
        的重播比對與 `end_turn` 的寫入要看到同一個物件。"""
        return self._state.setdefault(HANDOFF_CACHE_KEY, {})

    def write_handoff_cache(self, cache_key: str, entry: dict) -> None:
        cache = self.handoff_cache()
        cache[cache_key] = entry
        self._trim_fifo_dict(cache, HANDOFF_CACHE_MAX)

    # ── fixed_streak（session 累加；連續固定句計數，⛔ 不受 FIFO／回合覆寫）──
    @property
    def fixed_streak(self) -> int:
        return self._state.get(FIXED_STREAK_KEY, 0)

    def bump_fixed_streak(self, is_fixed: bool) -> None:
        """`is_fixed` ⇒ 累加一；否則歸零（逐字＝原 `_finalize` 的算法）。"""
        self._state[FIXED_STREAK_KEY] = (self.fixed_streak + 1) if is_fixed else 0

    # ── pending_confirm（FIFO 20；鍵＝pending_id） ──────────────────────────
    def pending_confirm(self) -> dict:
        pending_all = self._state.setdefault(PENDING_CONFIRM_KEY, {})
        if not isinstance(pending_all, dict):
            pending_all = {}
            self._state[PENDING_CONFIRM_KEY] = pending_all
        return pending_all

    def get_pending_confirm(self) -> Optional[dict]:
        return self._state.get(PENDING_CONFIRM_KEY)

    def write_pending_confirm(self, pending_id: str, entry: dict) -> None:
        pending_all = self.pending_confirm()
        pending_all[pending_id] = entry
        self._trim_fifo_dict(pending_all, PENDING_CONFIRM_MAX)

    # ── select_scope（每回合覆寫，含失敗回合寫 None：L15-05） ──────────────
    @property
    def select_scope(self) -> Optional[dict]:
        return self._state.get(SELECT_SCOPE_KEY)

    def write_select_scope(self, value: Optional[dict]) -> None:
        self._state[SELECT_SCOPE_KEY] = value

    # ── last_ask_target（每一個回合出口都要寫；turn-scoped） ────────────────
    @property
    def last_ask_target(self) -> Optional[str]:
        return self._state.get(LAST_ASK_TARGET_KEY)

    def write_last_ask_target(self, value: Optional[str]) -> None:
        self._state[LAST_ASK_TARGET_KEY] = value

    # ── completed_actions（FIFO 5；實際寫入判定在
    #    `completed_actions.record_completed_action`，本方法只管落地與修剪）──
    def get_completed_actions(self) -> Optional[list]:
        return self._state.get(COMPLETED_ACTIONS_KEY)

    def write_completed_actions(self, items: list) -> None:
        self._trim_fifo_list(items, COMPLETED_ACTIONS_MAX)
        self._state[COMPLETED_ACTIONS_KEY] = items

    # ── image_suggestion（一次性：任何 confirm.request 呼叫即清，新照片覆寫）──
    def get_image_suggestion(self) -> Optional[dict]:
        return self._state.get(IMAGE_SUGGESTION_KEY)

    def write_image_suggestion(self, value: Optional[dict]) -> None:
        self._state[IMAGE_SUGGESTION_KEY] = value

    def consume_image_suggestion(self) -> None:
        self._state.pop(IMAGE_SUGGESTION_KEY, None)

    # ── estate_carry（黏到 `scope_exit()`；釘住範圍時不寫，寫點在呼叫端判斷）──
    def get_estate_carry(self) -> Optional[dict]:
        return self._state.get(ESTATE_CARRY_KEY)

    def write_estate_carry(self, value: dict) -> None:
        self._state[ESTATE_CARRY_KEY] = value

    def scope_exit(self) -> None:
        """範圍退出：清掉全部 `until_scope_exit` 鍵（目前只有 `estate_carry`
        一個；多一個 `until_scope_exit` 鍵時這裡自動涵蓋，⛔ 不必回頭改這支
        方法）。"""
        for key, spec in KEY_SPECS.items():
            if spec.lifetime is Lifetime.UNTIL_SCOPE_EXIT:
                self._state.pop(key, None)

    # ── last_turn_at（時間戳；W8 (5)／DSP-042 的過期閘用它） ────────────────
    @property
    def last_turn_at(self) -> Optional[float]:
        return self._state.get(LAST_TURN_AT_KEY)

    def write_last_turn_at(self, ts: float) -> None:
        self._state[LAST_TURN_AT_KEY] = ts

    # ------------------------------------------------------------------
    # 回合邊界：`begin_turn`／`end_turn` 是回合狀態鍵的唯一寫點
    # （取代 `exit_gates.finalize`／`runtime._finish_confirm_turn`／
    #  `turn_segments` 的 `handoff_cache` 重播三處各自的欄位寫入）。
    # ------------------------------------------------------------------

    def begin_turn(self, nonce: str, outline: Any) -> None:  # noqa: ARG002
        """回合開始的記號（Plan R R3｜與 `end_turn` 成對，符號完整性用）。

        ⚠️ **本方法刻意不寫 `agent_state`**：`outline` 這個鍵的回合內暫存生命
        週期目前由呼叫端門面（`mcp_facade._agent_turn`：進場前塞、存檔前
        pop）管理——`mcp_facade.py` 不在 R3 的擁有檔案清單內（⛔ 不碰），把
        它的寫點搬進這裡會導致「這一行到底歸誰改」的雙重擁有權。R3b 待辦：
        門面改叫 `session.begin_turn(nonce, outline)` 時，這裡才真的接手寫入
        （見 `R3_PROGRESS.md`／commit message 的取捨節）。
        """
        return None

    def end_turn(
        self,
        *,
        user_message: str,
        dialog_text: str,
        ask_target: Optional[str],
        is_fixed: Optional[bool] = None,
        cache: Optional[dict] = None,
        cache_key: Optional[str] = None,
        cache_entry: Optional[dict] = None,
    ) -> None:
        """回合收尾的唯一寫點。

        呼叫端（`exit_gates.finalize`／`runtime._finish_confirm_turn`／
        `turn_segments` 的 `handoff_cache` 重播）各自把自己已經判定好的值傳
        進來，本方法只負責**落地與 FIFO 修剪**：

        - `ask_target`：呼叫端已把值收斂到「落在 `ASK_TARGETS` 值域內才給值，
          否則傳 `None`」——本方法不重驗值域（那是 `output_schema.ASK_TARGETS`
          的事，⛔ 不在這裡重複一份值域判斷）。
        - `is_fixed`：`None` ⇒ 不碰 `fixed_streak`（cache 重播路徑本來就不寫
          這個鍵）；非 `None` ⇒ `bump_fixed_streak`（`False` 等效於原
          `_finish_confirm_turn` 的「一律歸零」）。
        - `cache`／`cache_key`／`cache_entry`：三者都給 ⇒ 寫一筆並修剪。
          ⚠️ **`cache` 是呼叫端傳進來的那一個 dict**（⛔ 不假設它是
          `self._state[HANDOFF_CACHE_KEY]`——`exit_gates.finalize` 本身的
          `cache` 參數是外部注入的依賴，既有測試直接餵一個獨立 dict 而不經
          `agent_state`；生產路徑上它剛好與
          `agent_state["handoff_cache"]` 是同一個物件，因為
          `turn_segments.run_program_segments` 用 `AgentSession.handoff_cache()`
          / `setdefault` 建出那個 dict 之後原樣往下傳）。缺任一 ⇒ 不寫
          （`_finish_confirm_turn` 這條路徑 ⛔ 不進 `handoff_cache`——確認／
          兌現是一次性狀態轉移，見 `runtime._finish_confirm_turn` docstring）。
        - `dialog_text`：與 `TurnResult.answer` 可能不同（W8：清單點選／出卡
          回合 dialog 只寫程式摘要或卡文字）——呼叫端已經算好要寫哪一份。
        """
        self.write_last_ask_target(ask_target)
        if cache is not None and cache_key is not None and cache_entry is not None:
            cache[cache_key] = cache_entry
            self._trim_fifo_dict(cache, HANDOFF_CACHE_MAX)
        if is_fixed is not None:
            self.bump_fixed_streak(is_fixed)
        self.append_dialog(user_message, dialog_text)

    # ------------------------------------------------------------------
    # prompt_segments：範圍釘住判斷的唯一讀點
    # ------------------------------------------------------------------

    def prompt_segments(
        self,
        scope_estate_id: Optional[str],
        *,
        recent_refs_ids: list,
        estate_carry: Optional[dict],
    ) -> dict:
        """收斂 `recent_refs`／`estate_carry` 兩段各自的
        `if scope_estate_id is None` 判斷成**唯一一處**（L15／V2／第六批 #10
        三處紀律共用同一條：釘住範圍時的對話 ⛔ 不讓另一戶的物件跨進來）。

        ⚠️ 兩段的**實際計算**（`runtime._recent_ref_ids`／`_estate_carry_of`）
        仍留在 `runtime.py`——搬進本檔會需要 import `runtime`，而 `runtime.py`
        本身要 import `AgentSession`，兩邊互相 import 會成環。呼叫端一律**先
        算好**未過濾的值（兩支都是純函式、無副作用，`_estate_carry_of` 本身
        內部也已經在讀 `select_scope`），本方法只做**唯一**的範圍門檻判斷；
        釘住範圍時回傳的兩段皆為空／`None`，未釘住時原樣放行。
        """
        if scope_estate_id is not None:
            return {"recent_refs_ids": [], "estate_carry": None}
        return {"recent_refs_ids": list(recent_refs_ids), "estate_carry": estate_carry}


__all__ = [
    "Lifetime",
    "KeySpec",
    "KEY_SPECS",
    "AgentSession",
    "DIALOG_KEY",
    "OUTLINE_KEY",
    "HANDOFF_CACHE_KEY",
    "FIXED_STREAK_KEY",
    "PENDING_CONFIRM_KEY",
    "SELECT_SCOPE_KEY",
    "LAST_ASK_TARGET_KEY",
    "COMPLETED_ACTIONS_KEY",
    "IMAGE_SUGGESTION_KEY",
    "ESTATE_CARRY_KEY",
    "LAST_TURN_AT_KEY",
    "DIALOG_MAX_MESSAGES",
    "HANDOFF_CACHE_MAX",
    "PENDING_CONFIRM_MAX",
    "COMPLETED_ACTIONS_MAX",
]
