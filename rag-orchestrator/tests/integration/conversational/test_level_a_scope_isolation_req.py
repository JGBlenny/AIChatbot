"""integration：**Level A 作用域隔離**契約
（spec routing-disambiguation 任務 1.4｜R2.5, R5.2）。

守的是一句話：**旗標開啟時，Level A 以外的 Face 行為完全不變。**
⚠️ 防的是「帳單 8/8 但偷偷改了 21 個 Faces」——**局部量表全綠，全域行為已經位移**。

本檔分三塊，紅綠定性不同（逐條標於 docstring）：

  A. **Level A 成員資格**（🔴 紅，實作不存在）
     `is_instance_requiring_face()` 的**判準**不得等價於 `bool(required_slots)`。
     實查 22 個 Face 中 **13 個** required_slots 非空（contract_ref×6／bill_ref×4／
     estate_ref／meter_ref／member_ref／repair 五槽），該等價會一次納管 13 個 Face。

  B. **作用域隔離**（🟢 綠，且 SHALL 保持綠）
     同一批非 Level A 問句，旗標 ON／OFF 的 (route, facet) SHALL 完全相同。

  C. **B 的 negative control**（🟢 綠——證明 B 咬得動）
     把同一支判定式餵給一個**過寬**的 stub gate（旗標開啟即封所有 Face），
     它 SHALL 判出漂移；再餵一個**正確**的 stub（只封 Level A），
     它 SHALL 判為無漂移。**只會回「無漂移」的隔離檢查等於沒有檢查。**

⚠️ **本檔刻意不預選 `open_conflict_for_task_4_1` 的解法**：
`billing_anomaly`／`billing_invoice`／`billing_flow`／`billing_late_fee`
的歸屬待 design erratum 裁定（1.5 之後、任何 candidate implementation 之前），
故它們**既不入正向斷言、也不入隔離宣稱**，僅實測記錄。
在裁定前就把它們寫進任一側，就是拿「技術上需要它」當「產品上它屬於 scope」。
"""
import os

import pytest

pytestmark = pytest.mark.integration

VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))
PRODUCTION_TOP_K = 5
TARGET_USER = "property_manager"
MODE = "b2b"

#: Level A 白名單本尊（tasks 4.1）
LEVEL_A_FACE = "bill_diagnosis"

#: ⚠️ **歸屬待 design erratum 裁定**——不入正向斷言，也不入隔離宣稱
PENDING_ERRATUM_FACES = {"billing_anomaly", "billing_invoice", "billing_flow", "billing_late_fee"}

#: 任何 erratum 結果下都**確定**在 Level A 之外（非帳務域；Req.2.5 宣告 Level A ＝帳單域）
#: ——且**全部 required_slots 非空**，故同時是「判準 ≠ bool(required_slots)」的證據
OUT_OF_SCOPE_WITH_SLOTS = {
    "contract_diag": ["contract_ref"],
    "contract_change": ["contract_ref"],
    "contract_sign": ["contract_ref"],
    "estate_diag": ["estate_ref"],
    "iot_meter": ["meter_ref"],
    "account_team": ["member_ref"],
    "account_login": ["contract_ref"],
}

#: required_slots 為空 → 本就非 instance-requiring
OUT_OF_SCOPE_WITHOUT_SLOTS = ["billing_setup_guide", "estate_guide", "iot_setup",
                              "contract_create_guide", "account_register"]

#: 非 Level A 代表問句（四個非帳務域 ＋ 兩筆單發）；
#: 末兩筆為帳務域但**非** Level A：僅實測記錄，隔離宣稱自動排除待裁定 Face
NON_LEVEL_A_QUESTIONS = [
    "我想改合約 內容要修改",
    "租客要退租了 接下來怎麼做",
    "物件要怎麼刊登 上架流程",
    "租客說他登不進去系統",
    "電表一直離線 度數不動",
    "進階搜尋怎麼用 有哪些條件",
    "門鎖可以用悠遊卡嗎",
    "滯納金怎麼收這麼多",
]

#: Level A 本尊：放進觀測集是為了讓 C 能分辨「只改 Level A」與「什麼都改」
LEVEL_A_QUESTION = "我的這張點退帳單金額怎麼算出來的"


def _conn_kwargs():
    return dict(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "aichatbot"), password=os.getenv("DB_PASSWORD", "aichatbot_password"),
        database=os.getenv("DB_NAME", "aichatbot_admin"),
    )


@pytest.fixture(scope="module")
def retriever():
    from services.vendor_knowledge_retriever_v2 import VendorKnowledgeRetrieverV2
    return VendorKnowledgeRetrieverV2()


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
    """⚠️ 明確關閉 `PREENTRY_ROUTABILITY_GATE`——它會呼叫 LLM，會讓 ON／OFF 比較無法歸因。"""
    monkeypatch.setenv("PREENTRY_ROUTABILITY_GATE", "false")


async def _best_knowledge(retriever, question):
    from services.decision_layer import DecisionConfig
    cfg = DecisionConfig.load()
    rows = await retriever.retrieve_knowledge_hybrid(
        query=question, vendor_id=VENDOR_ID, top_k=PRODUCTION_TOP_K,
        similarity_threshold=cfg.kb_threshold, target_user=TARGET_USER, mode=MODE)
    return rows[0] if rows else None


async def _production_seam(pool, best, question):
    from routers.chat import _diagnosis_config_for_knowledge
    from services.decision_layer import DecisionConfig
    return await _diagnosis_config_for_knowledge(
        pool, best, DecisionConfig.load(), user_message=question)


def _overbroad_stub(blocked_keys=None):
    """stub gate：旗標開啟時封鎖 `blocked_keys`（None ＝**全部**）。

    ⚠️ 存在理由：在真 gate 尚未實作時，證明 `_isolation_drift()` **咬得動**。
    """
    async def _seam(pool, best, question):
        cfg = await _production_seam(pool, best, question)
        if cfg is None or os.getenv("INSTANCE_REFERENCE_GATE", "false").lower() != "true":
            return cfg
        if blocked_keys is None or getattr(cfg, "key", None) in blocked_keys:
            return None
        return cfg
    return _seam


async def _observe(pool, retriever, seam, monkeypatch, *, flag_on, cache):
    """回 {question: (route, facet_key)}；檢索只做一次並快取——旗標不影響檢索。"""
    monkeypatch.setenv("INSTANCE_REFERENCE_GATE", "true" if flag_on else "false")
    out = {}
    for q in NON_LEVEL_A_QUESTIONS + [LEVEL_A_QUESTION]:
        if q not in cache:
            cache[q] = await _best_knowledge(retriever, q)
        best = cache[q]
        if best is None:
            out[q] = ("single", None)
            continue
        cfg = await seam(pool, best, q)
        out[q] = ("single", None) if cfg is None else ("dialog", getattr(cfg, "key", "?"))
    return out


def _isolation_drift(off, on):
    """判定式：**Level A 與待裁定 Face 之外**，ON／OFF 有任何差異即為漂移。

    ⚠️ 以 **OFF 側**的落點決定一題是否在宣稱範圍內——用 ON 側決定的話，
    「gate 把某題踢出 Level A」會讓那題自動退出宣稱，漂移永遠測不到。
    """
    excluded = {LEVEL_A_FACE} | PENDING_ERRATUM_FACES
    drift = []
    for q, before in off.items():
        if before[0] == "dialog" and before[1] in excluded:
            continue
        if on.get(q) != before:
            drift.append((q, before, on.get(q)))
    return drift


# ── A. Level A 成員資格（🔴 目前為紅：實作不存在）──────────────
@pytest.mark.req("routing-disambiguation:2.5")
async def test_level_a_membership_is_not_bool_required_slots(pool):
    """**目前應為紅**（`is_instance_requiring_face` 尚未實作）。

    ⚠️ Must 1 否決 `bool(cfg.grounding_scope.required_slots)`：其語義是
    「執行需要哪些欄位」，非「這題是否指涉某一筆實體」。實查 22 個 Face 中
    **13 個** required_slots 非空——照該等價會一次納管 13 個 Face。
    """
    from services.conversational_config import config_for_key
    from services.instance_reference_gate import is_instance_requiring_face

    target = await config_for_key(pool, LEVEL_A_FACE)
    assert target is not None and is_instance_requiring_face(target) is True

    for key, slots in OUT_OF_SCOPE_WITH_SLOTS.items():
        cfg = await config_for_key(pool, key)
        assert cfg is not None, f"Face {key} 不存在了——本控制的母體已變"
        assert (getattr(cfg, "grounding_scope", None) or {}).get("required_slots") == slots, \
            f"{key} 的 required_slots 已變動，本控制的前提需重驗"
        assert is_instance_requiring_face(cfg) is False, (
            f"{key} 被納管——它的 required_slots={slots} 非空但非 entity reference；"
            "判準若等價 bool(required_slots)，Level A 就不再是 Level A")


@pytest.mark.req("routing-disambiguation:2.5")
async def test_faces_without_required_slots_are_never_members(pool):
    """**目前應為紅**：required_slots 為空者本就不可能是 instance-requiring。"""
    from services.conversational_config import config_for_key
    from services.instance_reference_gate import is_instance_requiring_face

    for key in OUT_OF_SCOPE_WITHOUT_SLOTS:
        cfg = await config_for_key(pool, key)
        if cfg is None:
            continue
        assert is_instance_requiring_face(cfg) is False, f"{key} 無 required_slots 卻被納管"


class _FakeFace:
    """最小替身：一個**已宣告**語義契約、但**不在本次 rollout scope**內的 Face。

    ⚠️ 必須用替身——今日沒有任何 Face 帶 `requires_instance_reference` 宣告，
    而「已宣告但未啟用」正是 D 與 C 分離後**唯一**能區分兩層的情境。
    宣告的載體取 `grounding_scope`（與 `required_slots`／`enabled_gate` 同處，
    沿面向配置鍵契約慣例）。
    """
    key = "future_face_not_in_this_release"
    persona_role = None
    topic_scope = {"mode": "category", "category": "（未來面向）"}
    grounding_scope = {"requires_instance_reference": True, "required_slots": ["bill_ref"]}


@pytest.mark.req("routing-disambiguation:2.5")
async def test_membership_and_rollout_scope_are_two_separate_layers(pool):
    """**目前應為紅**（erratum 01 的兩層契約尚未實作）。

    ⚠️ 擋的是「把兩層摺疊成一層」——摺疊後 Level B 擴張就得回頭改 **membership 定義**，
    語義契約會退化成 rollout 清單，正是本 erratum 否決 A 作為 membership source 的理由。
    """
    from services.instance_reference_gate import (
        gate_applies_to, in_gate_rollout_scope, is_instance_requiring_face)

    fake = _FakeFace()
    assert is_instance_requiring_face(fake) is True, "C 層應讀 Face 自身的宣告"
    assert in_gate_rollout_scope(fake) is False, "D 層不應把未列入本次 release 的 Face 當成已啟用"
    assert gate_applies_to(fake) is False, \
        "已宣告語義契約但不在本次 rollout scope → SHALL NOT 納管（兩層被摺疊了）"


@pytest.mark.req("routing-disambiguation:2.5")
async def test_level_a_face_satisfies_both_layers(pool):
    """**目前應為紅**：`bill_diagnosis` 是唯一兩層皆成立者（erratum 01 逐 Face 裁定）。

    ⚠️ `billing_anomaly`／`billing_invoice`／`billing_flow` **不在本斷言內**——
    逐 Face 裁定未完成前納入，就是把已否決的 family 方案從後門裝回來。
    """
    from services.conversational_config import config_for_key
    from services.instance_reference_gate import gate_applies_to

    cfg = await config_for_key(pool, LEVEL_A_FACE)
    assert cfg is not None and gate_applies_to(cfg) is True


# ── B. 作用域隔離（🟢 目前為綠，SHALL 保持綠）────────────────
@pytest.mark.req("routing-disambiguation:5.2")
async def test_flag_on_does_not_change_faces_outside_level_a(pool, retriever, monkeypatch):
    """**目前應為綠，實作後仍須為綠**——這是 preservation，不是「已修好」。"""
    cache = {}
    off = await _observe(pool, retriever, _production_seam, monkeypatch, flag_on=False, cache=cache)
    on = await _observe(pool, retriever, _production_seam, monkeypatch, flag_on=True, cache=cache)
    drift = _isolation_drift(off, on)
    assert drift == [], "旗標開啟改動了 Level A 以外的 Face：\n" + "\n".join(
        f"  {q}：{b} → {a}" for q, b, a in drift)


# ── C. B 的 negative control（🟢 綠——證明 B 咬得動）──────────
@pytest.mark.req("routing-disambiguation:5.2")
async def test_isolation_check_catches_an_overbroad_gate(pool, retriever, monkeypatch):
    """**目前應為綠**：過寬的 gate SHALL 被判出漂移。

    ⚠️ 沒有這條，B 可能只是**恆為空**的檢查——那正是本 spec 一路在防的
    「量尺自身是瞎的」。
    """
    cache = {}
    seam = _overbroad_stub(blocked_keys=None)          # 旗標開啟即封所有 Face
    off = await _observe(pool, retriever, seam, monkeypatch, flag_on=False, cache=cache)
    on = await _observe(pool, retriever, seam, monkeypatch, flag_on=True, cache=cache)
    drift = _isolation_drift(off, on)
    assert drift, "過寬 gate 封掉了所有 Face，隔離檢查卻回報無漂移——這支判定式是瞎的"


@pytest.mark.req("routing-disambiguation:5.2")
async def test_isolation_check_does_not_flag_a_correctly_scoped_gate(pool, retriever, monkeypatch):
    """**目前應為綠**：只封 Level A 的 gate SHALL **不**被判出漂移。

    ⚠️ 與上一條成對——只會喊漂移的檢查同樣沒有鑑別力，
    會把正確的實作也一起擋掉（前案「修一邊傷另一邊」的另一種形態）。
    """
    cache = {}
    seam = _overbroad_stub(blocked_keys={LEVEL_A_FACE})
    off = await _observe(pool, retriever, seam, monkeypatch, flag_on=False, cache=cache)
    on = await _observe(pool, retriever, seam, monkeypatch, flag_on=True, cache=cache)
    # ⚠️ 先證明這個 stub **確實改了東西**——否則本條會是空跑的假綠：
    #    什麼都沒變當然沒有漂移，那證明不了判定式懂得區分 in-scope 與越界。
    assert off[LEVEL_A_QUESTION] == ("dialog", LEVEL_A_FACE), \
        f"Level A 代表問句未落在 {LEVEL_A_FACE}（實得 {off[LEVEL_A_QUESTION]}）——本控制失去對照基準"
    assert on[LEVEL_A_QUESTION] == ("single", None), "stub 未真的封住 Level A，本條等於空跑"
    assert _isolation_drift(off, on) == [], \
        "只封 Level A 的 gate 被判為越界——判定式把 in-scope 的變更也算成漂移"


@pytest.mark.req("routing-disambiguation:2.5")
async def test_pending_erratum_faces_are_recorded_not_asserted(pool, retriever, monkeypatch, capsys):
    """**目前應為綠**：待裁定 Face 只**實測記錄**，不入任一側斷言。

    ⚠️ 這條唯一的斷言是「它們確實存在且確實未被納入宣稱」——
    裁定前把它們寫進正向或反向任一側，都是拿技術需要當產品裁示。
    """
    from services.conversational_config import config_for_key
    cache = {}
    off = await _observe(pool, retriever, _production_seam, monkeypatch, flag_on=False, cache=cache)
    for key in sorted(PENDING_ERRATUM_FACES):
        assert await config_for_key(pool, key) is not None, f"待裁定 Face {key} 不存在了"
    assert PENDING_ERRATUM_FACES & {LEVEL_A_FACE} == set()
    print("\n[待 erratum 裁定・僅記錄] 旗標關閉時的落點：")
    for q, r in off.items():
        if r[0] == "dialog" and r[1] in PENDING_ERRATUM_FACES:
            print(f"  {q} → {r[1]}")
