"""integration：**F-C23 KNOWLEDGE CONTENT MUST BE SCOPE-CONTAINED**（業主凍結 2026-08-31）。

```text
APPROVED_KNOWLEDGE_CONTENT 要求 reviewed answer：
  ① 完整覆蓋自己的 canonical responsibility
  ② **不得實質回答另一個已存在 responsibility 的核心問題**
```
⚠️ 本檔守 R-26（row 3531）——它曾因 `KNOWLEDGE_CONTENT_SCOPE_OVER_COVERAGE` 被擋，
於 2026-08-31 完成窄收斂。⛔ 若日後有人把「排程滯納金」段落加回去，本 guard 必須變紅。

⚠️ 負控制在 `test_fc23_negative_control_readding_second_mechanism_turns_red`：
⛔ 沒有負控制的 scope guard 無從證明自己不是恆真。
"""
import os

import pytest

pytestmark = pytest.mark.integration

ROW = 3531                      # R-26 的唯一 member
R27_ROW = 3532                  # R-27（跨版本比較）——本檔用來對照「誰才該談比較」

#: R-26 canonical 三要素的可稽核片段（⛔ 不是全文比對，避免文案微調就假紅）
CANONICAL_FRAGMENTS = [
    "實際付款當下若已逾期",                                    # 產生條件
    "滯納金設定已啟用",                                        # 產生條件（前提）
    "租金 ×（實際付款日 − 繳費期限 − 緩衝天數）× 費率",          # 計算方式
    "獨立的延遲金帳單",                                        # 結算規則
    "到期日為產生當日",
    "各自結算、不累加",
    "本身逾期不會再產生滯納金",
]

#: 屬於 **R-27** 或其他機制的標記——出現在 R-26 即為 scope leakage
OUT_OF_SCOPE_MARKERS = ["排程滯納金", "兩種機制", "階梯式", "固定金額", "客製版本", "每日排程"]


def _conn_kwargs():
    return dict(host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
                user=os.getenv("DB_USER", "aichatbot"),
                password=os.getenv("DB_PASSWORD", "aichatbot_password"),
                database=os.getenv("DB_NAME", "aichatbot_test"))


async def _answer(row_id):
    import asyncpg
    conn = await asyncpg.connect(**_conn_kwargs())
    try:
        return await conn.fetchval(
            "SELECT answer FROM knowledge_base WHERE id = $1 AND is_active", row_id)
    finally:
        await conn.close()


def _leaks(text):
    return [m for m in OUT_OF_SCOPE_MARKERS if m in (text or "")]


# ───────────────── ① canonical 三要素仍全部覆蓋 ─────────────────
@pytest.mark.req("FC23_R26:1")
async def test_r26_still_covers_all_canonical_elements():
    a = await _answer(ROW)
    assert a, f"row {ROW} 不存在或非 active ⇒ 前提不成立"
    missing = [f for f in CANONICAL_FRAGMENTS if f not in a]
    assert not missing, f"窄收斂把 canonical 要素也砍掉了：{missing}"


# ───────────────── ② 排程滯納金核心說明已不存在 ─────────────────
@pytest.mark.req("FC23_R26:2")
async def test_r26_no_longer_describes_the_scheduled_mechanism():
    a = await _answer(ROW)
    assert not _leaks(a), f"R-26 仍帶著範圍外內容：{_leaks(a)}"


# ───────────────── ③ 不再實質回答 R-27 的責任 ─────────────────
@pytest.mark.req("FC23_R26:3")
async def test_r26_does_not_answer_r27_cross_version_comparison():
    """⚠️ 正對照：**R-27 自己**必須仍談跨版本比較——否則本 guard 只是在抓一組恰好不存在的詞。"""
    a26, a27 = await _answer(ROW), await _answer(R27_ROW)
    assert a27, f"row {R27_ROW} 不存在 ⇒ 對照組失效"
    r27_markers = [m for m in OUT_OF_SCOPE_MARKERS if m in a27]
    assert len(r27_markers) >= 2, \
        f"R-27 自己也不談跨版本比較（僅 {r27_markers}）⇒ 這組標記無鑑別力，guard 是恆真的"
    assert not [m for m in OUT_OF_SCOPE_MARKERS if m in a26], \
        "R-26 踏進 R-27 的核心問題"


# ───────────────── ④ digest 釘住（⛔ 內容漂移要被看見）─────────────────
@pytest.mark.req("FC23_R26:4")
async def test_r26_answer_digest_is_pinned():
    import hashlib
    a = await _answer(ROW)
    got = hashlib.sha256(a.encode("utf-8")).hexdigest()
    assert got == "b98ec93620c14e5da836218fef96414f5b0dc97ec8acca409017de810cf762c0", (
        f"R-26 的 reviewed answer 已變動（digest={got}）"
        f"——⚠️ 內容變更必須重跑 F-C23 審查，⛔ 不得靜默漂移")


# ───────────────────────── 負控制 ─────────────────────────
@pytest.mark.req("FC23_M1:1")
async def test_fc23_negative_control_readding_second_mechanism_turns_red():
    """⚠️ 把「第二種排程滯納金機制」段落加回去 ⇒ scope-contained guard **必須變紅**。

    ⚠️ 純字串層模擬，⛔ 不寫 DB——本測試 ⛔ 不得污染 baseline。
    """
    a = await _answer(ROW)
    assert not _leaks(a), "前提：目前是乾淨的"
    mutated = a + "（二）排程滯納金（對逾期未付款的帳單開單）：每日排程檢查逾期帳單並依團隊設定開立滯納金帳單。"
    assert _leaks(mutated), "加回第二機制後 guard 仍未變紅 ⇒ scope guard 是裝飾"
    assert "排程滯納金" in _leaks(mutated)
