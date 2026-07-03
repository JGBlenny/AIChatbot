"""integration:面向進場路由回歸（contract-conversational-facets 收尾／R8.3, R11.2）。

忠實重演 chat.py 進場決策鏈（決定性、零 LLM）：
  retrieve_knowledge_hybrid(top1) → similarity ≥ FORM_TRIGGER_THRESHOLD(0.75)
  → 知識 categories → config_for_category 命中 → 進對話；否則單發。
（真 DB＋真 embedding＋真 reranker；不含 SOP 比分——SOP 勝出時不進對話，本測試聚焦知識路徑。）

期望準則（設計定案）：
  - 模糊起手/需 ground 的問句 → 進對話（錨點句本尊＋高頻口語＋既有狀態判斷保證句）；
  - 具體操作教學/制度 QA → 單發直答，不得被面向錨點吸走（Run 288 誤進場紅名單）。
本檔同時是「誤進場調校」的 TDD harness：調錨點/priority/標注後跑此檔驗證，
既防修壞單發、也防把該進對話的修掉。
"""
import os

import pytest

pytestmark = pytest.mark.integration

VENDOR_ID = int(os.getenv("TEST_VENDOR_ID", "2"))
ENTRY_THRESHOLD = float(os.getenv("FORM_TRIGGER_THRESHOLD", "0.75"))
KB_THRESHOLD = float(os.getenv("KB_SIMILARITY_THRESHOLD", "0.65"))
FACES = {"狀態判斷", "合約異動", "退租收尾", "續約", "建約引導", "簽署排障"}
BILLING_FACES = {"繳費金流排障", "帳單異常", "發票", "滯納金", "帳單設定引導"}


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


async def _route(retriever, pool, question):
    """重演進場決策：回 ('dialog', 面向, top1) 或 ('single', 原因, top1)。"""
    from services.conversational_config import config_for_category
    rows = await retriever.retrieve_knowledge_hybrid(
        query=question, vendor_id=VENDOR_ID, top_k=5,
        similarity_threshold=KB_THRESHOLD,
        target_user="property_manager", mode="b2b")
    best = rows[0] if rows else None
    if not best:
        return ("single", "no-hit", None)
    if best.get("similarity", 0) < ENTRY_THRESHOLD:
        return ("single", f"below-threshold({best.get('similarity', 0):.3f})", best)
    cats = [c for c in (best.get("categories") or []) if c] or \
           ([best.get("category")] if best.get("category") else [])
    for cat in cats:
        cfg = await config_for_category(pool, cat)
        if cfg is not None:
            return ("dialog", cat, best)
    return ("single", "no-facet-config", best)


def _fmt(best):
    if not best:
        return "（無命中）"
    return (f"top1={best.get('question_summary', '')[:24]}｜sim={best.get('similarity', 0):.3f}"
            f"｜cats={best.get('categories')}")


# ── 應進對話：錨點本尊＋高頻口語＋既有保證句（R8.3）──
DIALOG_CASES = [
    "我想改合約 內容要修改",
    "簽出去的合約還能改嗎 改得了嗎",
    "我想改 83315 這份合約的租期",
    "租客要退租了 接下來怎麼做",
    "提前解約之後 還要處理什麼",
    "合約快到期 要續約怎麼辦",
    "合約快到期了要怎麼續約",      # e2e 實跑進場句（調校保護）
    "要簽新合約 怎麼開始建",
    "租客簽不了約 一直簽不成",
    "租客說沒收到合約 找不到約",
    "我的合約狀態怪怪的",          # 既有狀態判斷保證
    "我想查合約狀態",              # 既有回歸句
    "這份合約怎麼還沒生效",        # 既有口語錨點
]

# ── 應單發：具體操作教學/制度 QA（Run 288 誤進場紅名單＋既有單發代表）──
SINGLE_CASES = [
    "我該怎麼把點交清單發給租客呢？",
    "點退的前置條件是什麼",
    "可以複製舊合約來建新的嗎",
    "批次續約要怎麼做啊？",
    "合約帳單的統計報表在哪看",
    "委託合約跟一般出租合約差在哪",
    "租客確認點交之後我這邊要做什麼",
    "合約快到期了，系統會自動提醒我嗎？",
    "「待發送」「待租客簽回」「待房東簽名」這些狀態怎麼分的",
    "點退做完後，帳單會自動出來嗎？",
    "合約備註只能寫 50 行嗎",
]


# ── 帳務：應進對話（billing-conversational-facets 任務 5.4 / R8.3, R11.2）──
BILLING_DIALOG_CASES = [
    "租客說繳了 錢還沒進來",
    "帳單卡在待對帳 狀態一直沒跳",
    "已付款但帳單狀態沒有更新",          # form_fill 升級（3497）
    "租客繳不了費 一直失敗",
    "帳單金額怪怪的 跟預期不一樣",
    "這期帳單怎麼還沒出來",
    "租客說看不到帳單 找不到",
    "發票怎麼還沒開 沒收到發票",
    "發票為什麼沒有開出來",              # form_fill 升級（3503）
    "滯納金怎麼收這麼多",
    "要開始收租 帳單要怎麼設定",
    "收款帳戶怎麼綁 金流怎麼申請",
]

# ── 帳務：應單發（教學/制度＋保留的 form_fill 精確句）──
BILLING_SINGLE_CASES = [
    "帳單有哪幾種狀態",
    "帳單的收費項目有哪些",
    "怎麼用 Excel 批次匯入帳單",
    "收據 PDF 在哪裡下載",
    "固定虛擬帳號會過期嗎",
    "押金設算息怎麼計算",
    "帳單為什麼發不出去",                # form_fill 保留（3495，混合制）
    "點退帳單的金額是怎麼算的",           # 邊界：含「帳單」但屬合約域教學（3519 單發）
]


# ── 帳號：應進對話（account-conversational-facets 任務 3.4 / R7.3, R10.2）──
ACCOUNT_FACES = {"註冊驗證排障", "登入排障", "帳號綁定異動", "團隊成員權限"}

ACCOUNT_DIALOG_CASES = [
    "租客一直沒辦法註冊 卡住了",
    "租客說他一直無法註冊 換手機也一樣",
    "租客收不到驗證簡訊 驗證過不了",
    "租客說他登不進去系統",
    "租客忘記密碼 登不進去",              # 3436 補標後進對話
    "租客用 LINE 登入變成要重新註冊",
    "手機被綁定過了 要解綁換綁",
    "租客註冊的名字跟證件不一樣 要怎麼改",
    "加了團隊成員 他什麼都看不到",
    "成員只能查看 不能編輯要怎麼調",       # 3545 補標後進對話
]

# ── 帳號：應單發（教學/制度，未補標）──
ACCOUNT_SINGLE_CASES = [
    "帳號要怎麼註冊 流程是什麼",           # 3435 維持單發
    "房東和租客的身分要怎麼切換",           # 3438 維持單發
]

# ── 三組誤吸邊界（gap-analysis R7 點名）：斷言到面向，不只 dialog/single ──
BOUNDARY_CASES = [
    ("租客簽不了約 一直簽不成", "簽署排障"),        # 「簽」→ 合約域，不被登入排障吸走
    ("租客說他登不進去系統", "登入排障"),            # 反向：登入不被簽署排障吸走
    ("租客說看不到帳單 找不到", "帳單異常"),         # 「帳單」→ 帳務域，不被登入排障吸走
]


@pytest.mark.req("account-conversational-facets:7.3")
@pytest.mark.parametrize("question", ACCOUNT_DIALOG_CASES)
async def test_account_openers_enter_dialog(retriever, pool, question):
    kind, detail, best = await _route(retriever, pool, question)
    assert kind == "dialog" and detail in ACCOUNT_FACES, \
        f"應進帳號對話卻為 {detail}：{question}｜{_fmt(best)}"


@pytest.mark.req("account-conversational-facets:10.2")
@pytest.mark.parametrize("question", ACCOUNT_SINGLE_CASES)
async def test_account_teaching_stays_single_shot(retriever, pool, question):
    kind, detail, best = await _route(retriever, pool, question)
    assert kind == "single", \
        f"帳號教學問句被吸進「{detail}」對話：{question}｜{_fmt(best)}"


@pytest.mark.req("account-conversational-facets:10.2")
@pytest.mark.parametrize("question,expected_facet", BOUNDARY_CASES)
async def test_cross_domain_boundary_no_misattraction(retriever, pool, question, expected_facet):
    kind, detail, best = await _route(retriever, pool, question)
    assert kind == "dialog" and detail == expected_facet, \
        f"邊界句應進「{expected_facet}」卻為 {kind}/{detail}：{question}｜{_fmt(best)}"


@pytest.mark.req("billing-conversational-facets:8.3")
@pytest.mark.parametrize("question", BILLING_DIALOG_CASES)
async def test_billing_openers_enter_dialog(retriever, pool, question):
    kind, detail, best = await _route(retriever, pool, question)
    assert kind == "dialog" and detail in BILLING_FACES, \
        f"應進帳務對話卻為 {detail}：{question}｜{_fmt(best)}"


@pytest.mark.req("billing-conversational-facets:11.2")
@pytest.mark.parametrize("question", BILLING_SINGLE_CASES)
async def test_billing_operation_questions_stay_single_shot(retriever, pool, question):
    kind, detail, best = await _route(retriever, pool, question)
    assert kind == "single", \
        f"帳務教學/制度問句被吸進「{detail}」對話：{question}｜{_fmt(best)}"


@pytest.mark.req("contract-conversational-facets:8.3")
@pytest.mark.parametrize("question", DIALOG_CASES)
async def test_vague_openers_enter_dialog(retriever, pool, question):
    kind, detail, best = await _route(retriever, pool, question)
    assert kind == "dialog" and detail in FACES, \
        f"應進對話卻單發（{detail}）：{question}｜{_fmt(best)}"


@pytest.mark.req("contract-conversational-facets:11.2")
@pytest.mark.parametrize("question", SINGLE_CASES)
async def test_operation_questions_stay_single_shot(retriever, pool, question):
    kind, detail, best = await _route(retriever, pool, question)
    assert kind == "single", \
        f"教學/制度問句被吸進「{detail}」對話：{question}｜{_fmt(best)}"
