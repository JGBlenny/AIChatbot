"""integration：multi-category 情境下 `block` 的**作用域**契約
（spec routing-disambiguation 任務 1.3｜R1.2, R1.3；robustness-protocol **v2** 之 N4）。

守的是**產品效果**，不是某個迴圈實作：

```text
rule 問句 ＋ top-1 KB 掛兩個以上可導向 Face 的 categories
  → 第一個 instance-requiring Face 被 block
  → SHALL NOT 因 continue 到第二個同型 Routing Hint 而進另一個 Face
  → final route SHALL 仍為 single
```

⚠️ **為何必須雙邊**：只鎖 rule 側，最省事的實作是把整列 categories 全封掉——
rule 救回來、instance 一起陪葬，正是前案「修一邊傷另一邊」的形態。
故同一個 multi-category KB shape 的 instance 問句 SHALL 仍進 `bill_diagnosis`。

⚠️ **為何用合成 KB row**：2026-08-23 實查 `aichatbot_test`——
**categories 解析後掛到兩個以上 Face 的 KB 為 0 筆**。
（74 筆 categories≥2 中，配對的另一分類多為主題分類；3497／3503 那型看似 multi-face，
實則「條件診斷：付款」「條件診斷：發票」**沒有 Face 設定**，只解析到一個 Face。）
新增語料會變更 corpus digest、破壞 v1 凍結，故改以合成 row 驅動 **production seam**：
決策邏輯全走 production（真 config registry、真 Face 設定），**僅 KB row 為輸入**。

⚠️ 本檔測試的紅綠**不是全紅**，逐條標示於各測試 docstring：
  - rule 側（2 筆）：**紅**——契約要逼出的未決設計問題（見 v2 `open_conflict_for_task_4_1`）
  - instance 側／旗標關閉／shape 守門／凍結對帳（4 筆）：**綠**，且 SHALL 保持綠
    （preservation 與 rollout-safety 斷言，不是「已經修好」的證據）
"""
import json
import os

import pytest

pytestmark = pytest.mark.integration

VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))

#: 本控制凍結於 protocol **v2**（v1 不動、digest 不變）
#: ⚠️ `791e84c38ae813fd` 為 **superseded_before_use**：補上 v2 自描述 metadata
#:    （acceptance_role／replaces_v1／final_acceptance／parent digest）後重算。
#:    僅補 metadata，未動任何案例、expected route、metric 或 threshold；
#:    修改時尚無 candidate implementation、亦未以 v2 量測過任何方案。
PROTOCOL_V2_DIGEST = "26a6199116f738ec"

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
_V2_PATH = os.path.join(
    _REPO, ".kiro", "specs", "routing-disambiguation", "robustness-protocol-v2.json")

#: design 元件 3 的原始舉例；兩者皆為實際 Face 且 required_slots 皆為 ["bill_ref"]
MULTI_CATEGORY = ["條件診斷：帳單", "帳單異常"]
TARGET_FACE_KEY = "bill_diagnosis"
RULE_CASE = "點退帳單的金額是怎麼算的"
INSTANCE_CASE = "我的這張點退帳單金額怎麼算出來的"


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.fixture
async def pool():
    import asyncpg
    from services import conversational_config as cc
    try:
        p = await asyncpg.create_pool(**_conn_kwargs(), min_size=1, max_size=2)
    except Exception as e:
        pytest.skip(f"無法連 DB：{e}")
        return
    cc.reset_cache()
    yield p
    cc.reset_cache()
    await p.close()


@pytest.fixture(autouse=True)
def deterministic_flags(monkeypatch):
    """⚠️ 明確關閉 `PREENTRY_ROUTABILITY_GATE`——它會呼叫 LLM。

    不關的話，本檔的紅綠會隨環境旗標與 LLM 回應漂移，
    而漂移的方向**看起來都很合理**，最難察覺。
    """
    monkeypatch.setenv("PREENTRY_ROUTABILITY_GATE", "false")


def _synthetic_knowledge(config, categories):
    """合成 top-1：只需通過 `facet_entry_eligible`（similarity ≥ form_trigger_threshold）。

    門檻**取自 production 唯一讀值點**，不在本檔硬寫數字。
    """
    return {
        "id": -1,
        "question_summary": "（合成）multi-category negative control",
        "answer": "（合成）",
        "categories": list(categories),
        "category": categories[0],
        "similarity": config.form_trigger_threshold + 0.05,
        "action_type": "direct_answer",
    }


async def _seam(pool, categories, question):
    """驅動 **production** 進場決策；回 (route, facet_key)。"""
    from routers.chat import _diagnosis_config_for_knowledge
    from services.decision_layer import DecisionConfig

    config = DecisionConfig.load()
    cfg = await _diagnosis_config_for_knowledge(
        pool, _synthetic_knowledge(config, categories), config, user_message=question)
    return ("single", None) if cfg is None else ("dialog", getattr(cfg, "key", "?"))


# ── 紅：契約要逼出的未決設計問題 ─────────────────────────────
@pytest.mark.req("routing-disambiguation:1.2")
@pytest.mark.parametrize("categories", [MULTI_CATEGORY, list(reversed(MULTI_CATEGORY))],
                         ids=["diagnosis_first", "anomaly_first"])
async def test_multi_category_rule_query_stays_single(pool, monkeypatch, categories):
    """**目前應為紅**（Level A 白名單只涵蓋一個 Face，rule 問句仍會 continue 進 `billing_anomaly`）。

    ⚠️ 兩種順序都測：只修第一順位等於沒修——`continue` 的語義問題與順序無關。
    """
    monkeypatch.setenv("INSTANCE_REFERENCE_GATE", "true")
    route, facet = await _seam(pool, categories, RULE_CASE)
    assert route == "single", (
        f"rule 問句在 categories={categories} 下進了「{facet}」——"
        "第一個同型 Face 被 block 之後 continue 到第二個，rule 問句依然進了 Face")


# ── 綠：preservation，SHALL 保持綠 ───────────────────────────
@pytest.mark.req("routing-disambiguation:1.3")
async def test_multi_category_instance_query_still_enters_bill_diagnosis(pool, monkeypatch):
    """**目前應為綠，且修完 rule 側後仍須為綠**（preservation，非「已修好」的證據）。

    ⚠️ 這條在擋一種具體的省事修法：把整列 categories 全封掉。
    那樣 rule 側會轉綠，而 instance 側**陪葬**——前案 3.4 的形態。
    """
    monkeypatch.setenv("INSTANCE_REFERENCE_GATE", "true")
    route, facet = await _seam(pool, MULTI_CATEGORY, INSTANCE_CASE)
    assert (route, facet) == ("dialog", TARGET_FACE_KEY), \
        f"instance 問句在同一個 multi-category shape 下落到 {route}/{facet}——雙邊只成立了一邊"


@pytest.mark.req("routing-disambiguation:1.2")
async def test_flag_off_leaves_multi_category_behaviour_unchanged(pool, monkeypatch):
    """**目前應為綠**：旗標預設關 → 行為與今日完全一致（rollout-safety，可獨立回退）。

    ⚠️ 本條斷言的是「關閉時不變」，**不是**「今日的 route 是對的」——
    今日 rule 問句進 Face 正是本案要修的缺陷。兩者不可混為一談。
    """
    monkeypatch.setenv("INSTANCE_REFERENCE_GATE", "false")
    route, _ = await _seam(pool, MULTI_CATEGORY, RULE_CASE)
    assert route == "dialog", "旗標關閉卻改變了既有行為——預設關的承諾不成立"


@pytest.mark.req("routing-disambiguation:1.2")
async def test_case_shape_is_genuinely_multi_face(pool):
    """**目前應為綠**：守的是**這個 negative control 本身沒有悄悄失效**。

    ⚠️ 兩個分類若哪天只剩一個解析得到 Face，本檔其餘測試會變成
    **單分類情境**——依然可能全綠，而 multi-category 契約根本沒被測到。
    「條件診斷：付款」「條件診斷：發票」看起來像 Face、實際 `config_for_category` 回 None，
    正是這種形態（實查 2026-08-23）。
    """
    from services.conversational_config import config_for_category
    resolved = {}
    for cat in MULTI_CATEGORY:
        cfg = await config_for_category(pool, cat)
        assert cfg is not None, f"分類「{cat}」已解析不到 Face——本控制已退化為單分類情境"
        gs = getattr(cfg, "grounding_scope", None) or {}
        assert "bill_ref" in (gs.get("required_slots") or []), \
            f"Face {cfg.key} 的 required_slots 不含 bill_ref——已非同型 instance-requiring Face"
        resolved[cat] = cfg.key
    assert len(set(resolved.values())) == 2, f"兩個分類指向同一個 Face：{resolved}"
    assert resolved[MULTI_CATEGORY[0]] == TARGET_FACE_KEY


@pytest.mark.req("routing-disambiguation:3.5")
def test_cases_come_from_frozen_protocol_v2():
    """**目前應為綠**：案例取自凍結的 v2，且 v2 未被事後改成剛好符合實作。

    ⚠️ 一併回證 **v1 未被動過**——本案新增案例的正當性，全繫於「v1 原封不動」。
    """
    import hashlib

    def _digest(obj):
        obj = {k: v for k, v in obj.items() if k != "protocol_digest"}
        return hashlib.sha256(
            json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2).encode()).hexdigest()[:16]

    with open(_V2_PATH, encoding="utf-8") as f:
        v2 = json.load(f)
    assert v2["protocol_digest"] == PROTOCOL_V2_DIGEST == _digest(v2), "v2 內容與 digest 不符"

    v1_path = os.path.join(os.path.dirname(_V2_PATH), "robustness-protocol.json")
    with open(v1_path, encoding="utf-8") as f:
        v1 = json.load(f)
    assert v1["protocol_digest"] == "4690a258f502d98d" == _digest(v1), \
        "v1 被改動了——凍結量尺一旦可事後修改，Req.3.5 的時間因果即失效"
    assert v2["relation_to_v1"]["v1_protocol_digest"] == v1["protocol_digest"]

    # v2 的**制度地位**須能從 v2 自身判讀，不得只寫在 tasks.md（provenance 分裂）
    assert v2["replaces_v1"] is False
    assert v2["acceptance_role"] == "required_additive_contract"
    assert v2["final_acceptance"]["protocol_v1_must_pass"] is True
    assert v2["final_acceptance"]["protocol_v2_must_pass"] is True, \
        "v2 若非最終收案必要條件，N4 就成了旁觀者——design correctness contract 必須最終為綠"
    assert v2["parent_protocol_digest"] == v1["protocol_digest"]
    assert v2["provenance"]["id"] == "design_v1_1_must_4"
    assert v2["provenance"]["created_before_candidate_implementation"] is True
    assert v2["supersedes"]["status"] == "superseded_before_use"

    case = v2["additions"]["case_sets"]["MULTI_CATEGORY"]
    assert case["kb_shape"]["categories"] == MULTI_CATEGORY
    assert case["rule_case"] == RULE_CASE and case["instance_case"] == INSTANCE_CASE
    assert case["expected"] == {"rule": "single", "instance": f"dialog:{MULTI_CATEGORY[0]}"}
