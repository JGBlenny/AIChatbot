"""unit：protocol v1 量尺的 **wrong facet ≠ success** negative control
（spec routing-disambiguation 任務 1.2｜R1.4；robustness-protocol.json 之 N3）。

守的是一句話：**instance 問句進入「條件診斷：帳單」以外的任何 dialog，量尺 SHALL 判為失敗。**

⚠️ 為什麼這一條要獨立於 integration 的正向斷言存在：
前案 3.4 驗證期間，「我的收據在哪」被記為 instance 通過，實測它進的是
**帳單異常（3936）**而非「條件診斷：帳單」——判定式只看 `route == "dialog"`，
於是**跑錯面向被算成成功**。同型錯誤前案發生兩次。
正向斷言（integration `test_billing_instance_questions_enter_diagnosis_facet`）
只能證明「對的時候會綠」；**它不能證明「錯的時候會紅」**——
量尺自身可能是瞎的，那正是本檔要排除的失敗形態（Req.6.5 的 negative control 紀律）。

被測對象是**量尺**（`scripts.routing.protocol_v1`），不是 production routing：
餵它一筆**已知為錯**的觀測結果，證明它確實判 fail。

⚠️ 量尺的期望值 SHALL 取自**已凍結**的 `robustness-protocol.json`（digest
`4690a258f502d98d`），不得在量尺內另寫一份——兩份期望值會各自漂移，
而漂移的那一份通常是比較寬鬆的那一份。

⚠️ 本檔於任務 1.2 建立時**應為紅**（量尺尚不存在）——那是它有效的證明。
   import 置於各測試內，使各條路徑**各自**以清楚訊息失敗，
   而非整檔於收集階段 error 而看不出個別攔截（沿任務 1.1 慣例）。
"""
import json
import os

import pytest

pytestmark = pytest.mark.unit

#: protocol v1 的 digest（Req.3.5 已凍結；與任務 1.1 的 ACTIVE_PROTOCOL_DIGEST 同源）
ACTIVE_PROTOCOL_DIGEST = "4690a258f502d98d"

#: instance 問法唯一正確的落點
CORRECT = "條件診斷：帳單"

#: 「錯的 dialog」代表集合——**含 3936「帳單異常」，即前案真正跑錯的那一個面向**
WRONG_FACETS = [
    "帳單異常",          # ⚠️ 前案 3.4 實際跑進的面向，被誤記為通過
    "發票",
    "滯納金",
    "繳費金流排障",
    "狀態判斷",          # 跨域：連域都錯，更不得算通過
]

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
_PROTOCOL_PATH = os.path.join(
    _REPO, ".kiro", "specs", "routing-disambiguation", "robustness-protocol.json")


def _mod():
    """延後匯入：量尺尚不存在時，讓每個測試各自紅在自己的斷言上。"""
    from scripts.routing import protocol_v1 as m  # noqa: PLC0415
    return m


def _frozen():
    with open(_PROTOCOL_PATH, encoding="utf-8") as f:
        return json.load(f)


def _run(instance_facet, *, rule_kind="single"):
    """組一輪完整觀測：RULE 4 筆 ＋ INSTANCE 4 筆（分母 8，Req.1.3 雙邊）。"""
    p = _frozen()["case_sets"]
    rows = [{"case_set": "RULE", "question": q, "kind": rule_kind, "facet": None}
            for q in p["RULE"]["cases"]]
    rows += [{"case_set": "INSTANCE", "question": q, "kind": "dialog", "facet": instance_facet}
             for q in p["INSTANCE"]["cases"]]
    return rows


# ── 核心：錯面向不得算通過（N3）─────────────────────────────
@pytest.mark.req("routing-disambiguation:1.4")
@pytest.mark.parametrize("facet", WRONG_FACETS)
def test_wrong_facet_is_not_success(facet):
    m = _mod()
    verdict = m.score_case("INSTANCE", observed_kind="dialog", observed_facet=facet)
    assert verdict == "fail", (
        f"instance 問法進入「{facet}」被判為 {verdict!r}——"
        "跑錯面向算成成功，正是前案兩度發生的假綠")


@pytest.mark.req("routing-disambiguation:1.4")
def test_correct_facet_is_the_only_pass():
    """反向：對的面向必須綠——否則這把尺只是恆紅，同樣測不出東西。"""
    m = _mod()
    assert m.score_case("INSTANCE", observed_kind="dialog", observed_facet=CORRECT) == "pass"


@pytest.mark.req("routing-disambiguation:1.4")
def test_dialog_without_facet_is_never_pass():
    """⚠️ 只知道『進了某個對話』而不知道是哪一個 → **不得**判 pass。

    這正是前案判定式的形狀（`route == "dialog"` 即算過）。量尺若在缺面向資訊時
    預設放行，錯面向只要不報面向就能矇混過關。
    """
    m = _mod()
    assert m.score_case("INSTANCE", observed_kind="dialog", observed_facet=None) != "pass"


@pytest.mark.req("routing-disambiguation:1.4")
def test_single_shot_on_instance_is_failure():
    """落回單發＝使用者拿到通則說明而非自己那筆的資料（T-1 要保住的能力）。"""
    m = _mod()
    assert m.score_case("INSTANCE", observed_kind="single", observed_facet=None) == "fail"


# ── 聚合層：錯面向不得被 8/8 吸收 ───────────────────────────
@pytest.mark.req("routing-disambiguation:1.4")
def test_bilateral_pass_rejects_run_where_instances_landed_in_wrong_facet():
    """⚠️ 逐筆判對還不夠——前案的假綠出現在**彙總**：
    RULE 四筆全 single（規則側看起來修好了）＋ INSTANCE 四筆全進錯面向，
    若彙總只數「有沒有進對話」就會報 8/8。此處要求它報不通過。
    """
    m = _mod()
    assert m.bilateral_pass(_run("帳單異常")) is False, \
        "RULE 全綠但 instance 全部跑錯面向，卻仍判 bilateral_pass——單邊假綠又回來了"


@pytest.mark.req("routing-disambiguation:1.3")
def test_bilateral_pass_requires_both_sides():
    """雙邊缺一不可（Req.1.3）：instance 側全對、rule 側全錯，同樣不得通過。"""
    m = _mod()
    assert m.bilateral_pass(_run(CORRECT, rule_kind="dialog")) is False
    assert m.bilateral_pass(_run(CORRECT)) is True, \
        "雙邊皆符合凍結期望卻不判通過——這把尺恆紅，測不出任何改善"


# ── 期望值來源：凍結檔，不得在量尺內另寫一份 ──────────────────
@pytest.mark.req("routing-disambiguation:1.4")
def test_expected_facet_comes_from_the_frozen_protocol():
    m = _mod()
    frozen = _frozen()
    assert frozen["protocol_digest"] == ACTIVE_PROTOCOL_DIGEST
    assert m.PROTOCOL_DIGEST == ACTIVE_PROTOCOL_DIGEST, "量尺未釘在 protocol v1"
    assert m.expected_for("INSTANCE") == frozen["case_sets"]["INSTANCE"]["expected"] \
        == f"dialog:{CORRECT}"


@pytest.mark.req("routing-disambiguation:1.4")
def test_undecided_cases_are_unscored_not_pass():
    """Req.4.2 兩筆歸屬未定案：僅記錄實際 route，**不計入通過率**。

    ⚠️ 把 `expected: null` 當成「怎樣都算過」，等同拿跑錯面向替 T-1 背書。
    """
    m = _mod()
    for facet in (CORRECT, "帳單異常", None):
        assert m.score_case("UNDECIDED", observed_kind="dialog", observed_facet=facet) == "unscored"
