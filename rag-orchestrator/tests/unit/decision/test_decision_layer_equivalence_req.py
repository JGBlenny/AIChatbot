"""unit：DecisionLayer 行為等價搬移——第①層嚴格等價（任務 1.3｜R7.4、審查修訂 1）。

驗證方法：**參考實作對拍**。`_reference_arbitration()` 是搬移前 chat.py
`_smart_retrieval_with_comparison` Step 3 決策邏輯的逐字複製（僅把 dict 外殼縮成
type/reason/case/gap 四元組；判定式、比較運算、reason 字串一字未動）。
`decide_arbitration()` 對**全輸入網格**（分數 0～1 步進 ×8 種旗標組合）必須與參考
實作同輸出——任何一格不同＝搬移改了行為＝任務失敗。

門檻值等價另測：DecisionConfig.load() 讀出的值必須與原散落讀值點的 env 鍵/預設一致。
"""
import itertools
import os

import pytest

from services import decision_layer as dl

pytestmark = pytest.mark.unit


# ════════════════════════════════════════════════════════════════════
# 參考實作：chat.py Step 3（搬移前原文逐字複製；勿「順手改善」——它是等價的準繩）
# ════════════════════════════════════════════════════════════════════

def _reference_arbitration(sop_score, knowledge_score, has_sop, sop_cancelled,
                           sop_action_executed, sop_has_response, sop_has_action,
                           sop_next_action):
    SCORE_GAP_THRESHOLD = 0.15  # 差距閾值
    SOP_MIN_THRESHOLD = 0.55
    KNOWLEDGE_MIN_THRESHOLD = 0.6

    # 特殊情況 0A：SOP 被用戶取消（cancelled）
    if has_sop and sop_cancelled:
        return ('sop', '用戶取消 SOP 動作', 'sop_cancelled_by_user',
                abs(sop_score - knowledge_score))

    # 特殊情況 0B：SOP 已觸發並執行後續動作
    if has_sop and sop_action_executed:
        return ('sop', 'SOP 關鍵詞匹配並已執行後續動作',
                'sop_triggered_action_executed', abs(sop_score - knowledge_score))

    # 特殊情況：SOP 等待關鍵詞（response 為 None）
    if has_sop and not sop_has_response:
        gap = abs(knowledge_score - sop_score)
        if knowledge_score >= KNOWLEDGE_MIN_THRESHOLD:
            return ('knowledge', f'SOP 等待關鍵詞，使用知識庫 ({knowledge_score:.3f})',
                    'sop_waiting_for_keyword_use_knowledge', gap)
        else:
            return ('none', 'SOP 等待關鍵詞且知識庫未達標',
                    'sop_waiting_both_below_threshold', gap)

    # Case 1: SOP 顯著更高
    if (sop_score >= SOP_MIN_THRESHOLD and
            sop_score > knowledge_score + SCORE_GAP_THRESHOLD):
        return ('sop', f'SOP 分數顯著更高 ({sop_score:.3f} vs {knowledge_score:.3f})',
                'sop_significantly_higher', sop_score - knowledge_score)

    # Case 2: 知識庫顯著更高
    if (knowledge_score >= KNOWLEDGE_MIN_THRESHOLD and
            knowledge_score > sop_score + SCORE_GAP_THRESHOLD):
        return ('knowledge',
                f'知識庫分數顯著更高 ({knowledge_score:.3f} vs {sop_score:.3f})',
                'knowledge_significantly_higher', knowledge_score - sop_score)

    # Case 3: 分數接近
    if (sop_score >= SOP_MIN_THRESHOLD and
            knowledge_score >= KNOWLEDGE_MIN_THRESHOLD):
        gap = abs(sop_score - knowledge_score)
        if sop_has_action:
            return ('sop', f'SOP 有後續動作 ({sop_next_action})',
                    'close_scores_sop_has_action', gap)
        if sop_score > knowledge_score:
            return ('sop',
                    f'分數接近但 SOP 略高 ({sop_score:.3f} vs {knowledge_score:.3f})',
                    'close_scores_sop_slightly_higher', gap)
        else:
            return ('knowledge',
                    f'分數接近但知識庫略高 ({knowledge_score:.3f} vs {sop_score:.3f})',
                    'close_scores_knowledge_slightly_higher', gap)

    # Case 4: 只有 SOP 達標
    if sop_score >= SOP_MIN_THRESHOLD:
        return ('sop', f'只有 SOP 達標 ({sop_score:.3f})', 'only_sop_qualified',
                abs(sop_score - knowledge_score))

    # Case 5: 只有知識庫達標
    if knowledge_score >= KNOWLEDGE_MIN_THRESHOLD:
        return ('knowledge', f'只有知識庫達標 ({knowledge_score:.3f})',
                'only_knowledge_qualified', abs(knowledge_score - sop_score))

    # Case 6: 都不達標
    return ('none', '都未達到最低閾值', 'both_below_threshold',
            abs(sop_score - knowledge_score))


# 分數網格：0～1 步進 0.05（21 點）＋門檻邊界±ε 關鍵點——涵蓋 >、>=、+gap 的每個翻轉面
_EDGE = [0.549, 0.55, 0.551, 0.599, 0.6, 0.601, 0.699, 0.7, 0.701,
         0.749, 0.75, 0.751]
_SCORES = sorted({round(x * 0.05, 2) for x in range(21)} | set(_EDGE))
_FLAGS = list(itertools.product([False, True], repeat=4))  # cancelled/executed/response/action


@pytest.mark.req("retrieval-decision-layer:7.4")
def test_arbitration_strict_equivalence_full_grid():
    """全網格對拍：35×35 分數 × 2 has_sop × 16 旗標組合 ≈ 39k 格，全部嚴格同輸出。"""
    config = dl.DecisionConfig()          # 預設值＝原硬編碼
    checked = 0
    for sop_score, knowledge_score in itertools.product(_SCORES, _SCORES):
        for has_sop in (False, True):
            for cancelled, executed, has_resp, has_action in _FLAGS:
                got = dl.decide_arbitration(
                    sop_score=sop_score, knowledge_score=knowledge_score,
                    has_sop=has_sop, sop_cancelled=cancelled,
                    sop_action_executed=executed, sop_has_response=has_resp,
                    sop_has_action=has_action, sop_next_action="form_fill",
                    config=config)
                want = _reference_arbitration(
                    sop_score, knowledge_score, has_sop, cancelled,
                    executed, has_resp, has_action, "form_fill")
                assert (got["type"], got["reason"], got["decision_case"],
                        got["gap"]) == want, (
                    f"不等價 @ sop={sop_score} kb={knowledge_score} has_sop={has_sop} "
                    f"flags={cancelled,executed,has_resp,has_action}")
                checked += 1
    assert checked > 25000                # 網格真的跑完，不是空迴圈（29²×2×16=26,912）


@pytest.mark.req("retrieval-decision-layer:7.4")
def test_arbitration_next_action_string_passthrough():
    """3.1 的 reason 帶 next_action 原文（api_call/form_then_api 也逐字）。"""
    config = dl.DecisionConfig()
    for na in ("form_fill", "api_call", "form_then_api", None):
        got = dl.decide_arbitration(
            sop_score=0.7, knowledge_score=0.65, has_sop=True, sop_cancelled=False,
            sop_action_executed=False, sop_has_response=True, sop_has_action=True,
            sop_next_action=na, config=config)
        assert got["decision_case"] == "close_scores_sop_has_action"
        assert got["reason"] == f'SOP 有後續動作 ({na})'


# ════════════════════════════════════════════════════════════════════
# 快照（R8.3）：每次仲裁必產出、內容足以歸因
# ════════════════════════════════════════════════════════════════════

@pytest.mark.req("retrieval-decision-layer:8.3")
def test_arbitration_snapshot_content():
    config = dl.DecisionConfig()
    got = dl.decide_arbitration(
        sop_score=0.58, knowledge_score=0.61, has_sop=True, sop_cancelled=False,
        sop_action_executed=False, sop_has_response=True, sop_has_action=False,
        sop_next_action=None, config=config)
    snap = got["snapshot"]
    assert snap["rule_version"] == dl.DECISION_RULE_VERSION
    assert snap["config_hash"] == config.config_hash()
    assert snap["sop_top1_final"] == 0.58 and snap["kb_top1_final"] == 0.61
    assert snap["sop_min"] == 0.55 and snap["knowledge_min"] == 0.6
    assert snap["verdict"] == got["type"]
    assert snap["decision_case"] == got["decision_case"]


# ════════════════════════════════════════════════════════════════════
# DecisionConfig：env 鍵與預設值等價（R7.4）
# ════════════════════════════════════════════════════════════════════

@pytest.mark.req("retrieval-decision-layer:7.4")
def test_config_defaults_match_legacy_values(monkeypatch):
    """未設 env 時＝原散落讀值點的預設：KB 0.55、FORM 0.75、六 case 0.55/0.6/0.15。"""
    monkeypatch.delenv("KB_SIMILARITY_THRESHOLD", raising=False)
    monkeypatch.delenv("FORM_TRIGGER_THRESHOLD", raising=False)
    c = dl.DecisionConfig.load()
    assert c.kb_threshold == 0.55
    assert c.form_trigger_threshold == 0.75
    assert (c.sop_min, c.knowledge_min, c.score_gap) == (0.55, 0.6, 0.15)


@pytest.mark.req("retrieval-decision-layer:7.4")
def test_config_env_override_same_keys(monkeypatch):
    """env 鍵名不變（KB_SIMILARITY_THRESHOLD／FORM_TRIGGER_THRESHOLD）；
    設了就生效——與原 os.getenv 每請求即時讀同語義。"""
    monkeypatch.setenv("KB_SIMILARITY_THRESHOLD", "0.62")
    monkeypatch.setenv("FORM_TRIGGER_THRESHOLD", "0.8")
    c = dl.DecisionConfig.load()
    assert c.kb_threshold == 0.62
    assert c.form_trigger_threshold == 0.8
    # 六 case 常數無 env 旋鈕（原碼即硬編碼；調參屬 P1 任務 2.4）
    assert (c.sop_min, c.knowledge_min, c.score_gap) == (0.55, 0.6, 0.15)


@pytest.mark.req("retrieval-decision-layer:8.3")
def test_config_hash_reflects_values(monkeypatch):
    monkeypatch.delenv("KB_SIMILARITY_THRESHOLD", raising=False)
    monkeypatch.delenv("FORM_TRIGGER_THRESHOLD", raising=False)
    h0 = dl.DecisionConfig.load().config_hash()
    assert h0 == dl.DecisionConfig.load().config_hash()      # 同值同雜湊
    monkeypatch.setenv("FORM_TRIGGER_THRESHOLD", "0.8")
    assert dl.DecisionConfig.load().config_hash() != h0      # 改值必變


# ════════════════════════════════════════════════════════════════════
# gate 函式：與原 inline 判定嚴格等價
# ════════════════════════════════════════════════════════════════════

@pytest.mark.req("retrieval-decision-layer:7.4")
@pytest.mark.parametrize("bk,expected", [
    (None, False),                                        # 無知識
    ({}, False),                                          # 空 dict（原碼 falsy → None）
    ({"similarity": 0.749}, False),                       # 差一線
    ({"similarity": 0.75}, True),                         # 恰達標（>=）
    ({"similarity": 0.9}, True),
    ({"id": 1}, False),                                   # 缺 similarity → get 預設 0
])
def test_facet_entry_eligible_matrix(bk, expected):
    assert dl.facet_entry_eligible(bk, dl.DecisionConfig()) is expected


@pytest.mark.req("retrieval-decision-layer:7.4")
@pytest.mark.parametrize("bk,expected", [
    (None, False),
    ({"action_type": "direct_answer", "similarity": 0.9}, False),   # 非表單
    ({"action_type": "form_fill", "similarity": 0.75}, True),       # 表單恰達標
    ({"action_type": "form_fill", "similarity": 0.749}, False),     # 表單差一線
    ({"form_id": "repair", "similarity": 0.8}, True),               # 帶 form_id 即表單
    ({"form_id": None, "similarity": 0.8}, False),
    ({"action_type": "api_call", "form_id": "f1", "similarity": 0.8}, True),
    ({"action_type": "form_fill"}, False),                          # 缺 similarity
])
def test_form_trigger_eligible_matrix(bk, expected):
    assert dl.form_trigger_eligible(bk, dl.DecisionConfig()) is expected


@pytest.mark.req("retrieval-decision-layer:7.4")
def test_gates_honor_env_threshold(monkeypatch):
    """gate 讀的是 config 值，不是寫死 0.75——env 調 0.8 後 0.78 不再過。"""
    monkeypatch.setenv("FORM_TRIGGER_THRESHOLD", "0.8")
    c = dl.DecisionConfig.load()
    assert dl.facet_entry_eligible({"similarity": 0.78}, c) is False
    assert dl.form_trigger_eligible({"form_id": "x", "similarity": 0.78}, c) is False
    assert dl.facet_entry_eligible({"similarity": 0.8}, c) is True
