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
