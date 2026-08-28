"""unit：Face vs Knowledge 的 precedence（裁定 001-A ②）。

要鎖的命題：

> **技術故障不得取得 routing authority——已成立的 Knowledge direct answer
>   不得被 `technical_fail_open + stay` 擠掉。**

對照實測病灶：`_resolve_pre_commit_candidate` 過去對三種完全不同的情況回同一個
`cfg`（resolver 沒跑／model 判 stay／技術故障 fail-open），呼叫端只看得到
「有沒有面向」，於是 evaluator 壞掉時 Face 照樣搶走 Knowledge path。

⚠️ 本檔**刻意不測** `.stay`：那格布林對 model stay 與 fail-open 都是 True，
   正是它分不出來才需要這一層。
"""
import ast
import io
from pathlib import Path

import pytest

from services.responsibility import (
    FACE_AUTHORITATIVE,
    FACE_COMPAT_FAIL_OPEN,
    FACE_NONE,
    FACE_UNEVALUATED,
    face_precedence,
)

pytestmark = pytest.mark.unit


# ── 裁定 001-A 的四列表（deterministic causal grid）─────────────────────────
#
#   Face authority        Knowledge   期望
#   authoritative         YES         face
#   authoritative         NO          face
#   technical fail-open   YES         **knowledge**（Face 不得 commit）
#   technical fail-open   NO          compat_face（相容性，非 responsibility-confirmed）
#
# ⚠️ 第 3 格是**唯一**會因為偷懶實作而翻掉的那格；前兩格在舊碼下也會過，
#    單獨拿它們當通過條件等於沒有鑑別力。

@pytest.mark.req("routing-authority-model:ruling-001A-2")
@pytest.mark.parametrize("authority,knowledge,expected", [
    (FACE_AUTHORITATIVE,   True,  "face"),          # ①
    (FACE_AUTHORITATIVE,   False, "face"),          # ②
    (FACE_COMPAT_FAIL_OPEN, True,  "knowledge"),    # ③ ★ 核心
    (FACE_COMPAT_FAIL_OPEN, False, "compat_face"),  # ④
])
def test_precedence_grid(authority, knowledge, expected):
    assert face_precedence(authority, knowledge_present=knowledge) == expected


@pytest.mark.req("routing-authority-model:ruling-001A-2")
def test_fail_open_never_beats_an_existing_knowledge_candidate():
    """③ 的獨立敘述版：技術故障 + 有 Knowledge ⇒ Knowledge，一個字都不能鬆。"""
    assert face_precedence(FACE_COMPAT_FAIL_OPEN, knowledge_present=True) == "knowledge"


@pytest.mark.req("routing-authority-model:ruling-001A-2")
def test_authoritative_stay_wins_regardless_of_the_direct_answer_gate():
    """對照組：真實 model stay **必須**贏，不論 gate 判 YES 或 NO。
    少了這條，本檔就退化成「一律否決 Face」，鑑別力為零。"""
    assert face_precedence(FACE_AUTHORITATIVE, knowledge_present=True) == "face"
    assert face_precedence(FACE_AUTHORITATIVE, knowledge_present=False) == "face"


@pytest.mark.req("routing-authority-model:ruling-001A-2")
def test_unevaluated_keeps_existing_behaviour():
    """resolver **沒跑**（旗標關／不在 allowlist）≠ fail-open。

    ⚠️ 若把它也當成無 authority，allowlist 外的**所有**面向會被一次改掉語義
    （scoped rollout 的設計意圖就是只在 allowlist 內生效）。
    """
    assert face_precedence(FACE_UNEVALUATED, knowledge_present=True) == "face"
    assert face_precedence(FACE_UNEVALUATED, knowledge_present=False) == "face"


@pytest.mark.req("routing-authority-model:ruling-001A-2")
def test_no_face_falls_through_to_knowledge_then_fallback():
    assert face_precedence(FACE_NONE, knowledge_present=True) == "knowledge"
    assert face_precedence(FACE_NONE, knowledge_present=False) == "fallback"


@pytest.mark.req("routing-authority-model:ruling-001A-2")
def test_switch_salvage_guard_are_never_laundered_into_a_face_stay():
    """裁定 001 ③：`scope=switch`／salvage／guard **一律不算** Face 贏得責任。

    它們在 resolver 層就不會產生 committed_key，因此到不了 precedence；
    這條測試鎖的是「萬一有人把它們映射成 authoritative」——
    映射得再像，值也不會等於 FACE_AUTHORITATIVE。
    """
    from services.responsibility import (DECISION_SOURCE_CONTRACT_SALVAGE,
                                         DECISION_SOURCE_GUARD,
                                         DECISION_SOURCE_TECHNICAL_FAIL_OPEN)
    for src in (DECISION_SOURCE_CONTRACT_SALVAGE, DECISION_SOURCE_GUARD,
                DECISION_SOURCE_TECHNICAL_FAIL_OPEN):
        assert src != FACE_AUTHORITATIVE
        # 非 authoritative 的任何值，在有 Knowledge 時都不得回 face
        assert face_precedence(src, knowledge_present=True) != "face"


# ── guard：authority-sensitive 仲裁不得讀 `.stay`（業主 2026-08-28 裁定）──────
#
# `.stay` 本身不刪（compatibility control flow 仍需要它），但**產線路由層**
# 一旦讀它，就等於把「fail-open 冒充 model stay」那條路徑再開回來。
# 改名 stay → stops_chain_here 被判 DEFER，因此改用這條機器規則守。

@pytest.mark.req("routing-authority-model:ruling-001A-guard")
def test_router_never_reads_dot_stay_for_precedence():
    src = Path(__file__).resolve().parents[3] / "routers" / "chat.py"
    tree = ast.parse(io.open(src, encoding="utf-8").read())
    hits = [n.lineno for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and n.attr == "stay"]
    assert not hits, (
        f"routers/chat.py 有 {len(hits)} 處讀 `.stay`（行 {hits}）——"
        "authority-sensitive 仲裁必須讀 has_commit_authority／face_precedence。"
        "`.stay` 對 model stay 與 technical fail-open 都是 True，分不出來。")


@pytest.mark.req("routing-authority-model:ruling-001A-guard")
def test_guard_itself_can_see_a_planted_violation():
    """⚠️ 正對照組：上面那條回「沒有違規」是否定結論，必須證明它咬得動。

    餵一段**含** `.stay` 的合成程式，掃描器必須抓到；抓不到就是掃描器壞了，
    不是 chat.py 乾淨。
    """
    planted = "def f(res):\n    if res.stay:\n        return 1\n"
    tree = ast.parse(planted)
    hits = [n for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and n.attr == "stay"]
    assert len(hits) == 1, "掃描器看不見植入的 `.stay` → 它對 chat.py 的 PASS 不可信"
