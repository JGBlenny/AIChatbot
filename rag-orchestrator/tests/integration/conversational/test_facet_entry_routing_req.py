"""integration:面向進場路由回歸（contract-conversational-facets 收尾／R8.3, R11.2）。

**驅動 production 進場決策鏈**（決定性、零 LLM）：
  retrieve_knowledge_hybrid(top1) → `routers.chat._diagnosis_config_for_knowledge`
（真 DB＋真 embedding＋真 reranker；不含 SOP 比分——SOP 勝出時不進對話，本測試聚焦知識路徑。）

⚠️ **本檔曾自行重演該決策鏈**（自行比門檻、自行取 categories、自行查 config），
與 R9.4「離線驗證須完整複刻該版本 production 實際啟用的候選變換與執行順序」相違：
複刻與 production 的分歧（門檻讀值點、雙欄位退化、`_preentry_routable` 缺席、
檢索呼叫參數）會讓紅綠變化無法歸因——**測試沒過究竟是產品壞了，還是複本走偏了？**
spec conversational-routing-execution 任務 3.1 改為呼叫 production seam；
門檻、雙欄位退化、pre-entry gate 一律**不在本檔內複刻**。

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

# ⚠️ **門檻不在本檔讀取**——一律取自 production 唯一讀值點 `DecisionConfig.load()`
#    （任務 3.1）。舊碼在此自行 `os.getenv("FORM_TRIGGER_THRESHOLD"/"KB_SIMILARITY_THRESHOLD")`，
#    連預設值都與 production 不同（KB 門檻：舊碼預設 0.65 vs DecisionConfig 預設 0.55），
#    env 未設的環境會靜默用不同候選集跑，而結果「看起來合理」。
#: 檢索 top_k：對齊 production 請求模型的預設（`VendorChatRequest.top_k` Field(5)）
PRODUCTION_TOP_K = 5
TARGET_USER = "property_manager"
MODE = "b2b"
FACES = {"狀態判斷", "合約異動", "退租收尾", "續約", "建約引導", "簽署排障"}
BILLING_FACES = {"繳費金流排障", "帳單異常", "發票", "滯納金", "帳單設定引導", "條件診斷：帳單"}


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
    """驅動 **production** 進場決策：回 ('dialog', 面向分類, top1) 或 ('single', 原因, top1)。

    本函式只做兩件事，其餘一律交給 production：
      1. 呼叫 production `retrieve_knowledge_hybrid` 取 best_knowledge
         （門檻取自 `DecisionConfig.load().kb_threshold`，top_k 對齊請求模型預設）；
      2. 呼叫 production `routers.chat._diagnosis_config_for_knowledge`。

    ⚠️ 回傳的 `reason`（'no-hit'／'not-routed'）**僅供 pytest 失敗訊息可讀性，
    永不進斷言**。production seam 只回 `cfg | None`，不區分
    below-threshold／no-facet-config／preentry-blocked；若要區分就得事後推導，
    那仍是複刻——只是從主路徑挪進診斷路徑。
    """
    from routers.chat import _diagnosis_config_for_knowledge
    from services.decision_layer import DecisionConfig

    cfg_thresholds = DecisionConfig.load()
    rows = await retriever.retrieve_knowledge_hybrid(
        query=question, vendor_id=VENDOR_ID, top_k=PRODUCTION_TOP_K,
        similarity_threshold=cfg_thresholds.kb_threshold,
        target_user=TARGET_USER, mode=MODE)
    best = rows[0] if rows else None
    if not best:
        return ("single", "no-hit", None)

    cfg = await _diagnosis_config_for_knowledge(
        pool, best, cfg_thresholds, user_message=question)
    if cfg is None:
        return ("single", "not-routed", best)
    # 觸發的分類讀自 config 本身（by_category 索引鍵＝topic_scope.category），非重新推導
    cat = (getattr(cfg, "topic_scope", None) or {}).get("category") or getattr(cfg, "key", "?")
    return ("dialog", cat, best)


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
    "帳單為什麼發不出去",                # 2026-07-06 帳單診斷面向立案後改判進對話（3495 錨點，原 form_fill 保留裁定過時）
]

# ── 帳務：應單發（教學/制度＋保留的 form_fill 精確句）──
BILLING_SINGLE_CASES = [
    "帳單有哪幾種狀態",
    "帳單的收費項目有哪些",
    "怎麼用 Excel 批次匯入帳單",
    "收據 PDF 在哪裡下載",
    "固定虛擬帳號會過期嗎",
    "押金設算息怎麼計算",
    "點退帳單的金額是怎麼算的",           # 邊界：含「帳單」但屬合約域教學（3519 單發）
    "系統怎麼算點退帳單的金額",           # 同上句型變體（3.4 verifier A2 補入）
]


# ── 帳單診斷：instance-specific 應進對話（spec conversational-routing-execution 任務 3.4）──
#
# ⚠️ **本組存在的理由**：20260731 §3（T-1）替三筆內容型 KB 掛面向分類，是為了讓
#    「查我的實值」問法能進面向。但 integration 原本**只守規則側**
#    （BILLING_SINGLE_CASES 7 筆），T-1 想保住的能力**沒有任何測試守著**——
#    於是「三筆 regression 綠了」曾構成假綠：修法只證明了一半。
#    本組把雙邊能力第一次真正寫進驗收集合。
#
# ⚠️ **必須斷言到 facet，不能只驗 dialog**：3.4 驗證期間「我的收據在哪」被誤記為
#    instance 通過，實測它進的是「帳單異常」（3936）而非「條件診斷：帳單」——
#    只看 route=='dialog' 的判定式會把跑錯面向算成成功。
#
# ⚠️ **已知紅**：本組與上方三筆規則案例目前皆為 known-red——
#    3.4 所選的 anchor 修法已被獨立 verifier REFUTED（rule 與 instance 兩側
#    僅靠 0.003～0.005 相似度差分開，corpus 一動即翻面），修復另立
#    routing-disambiguation 設計案。**在該案定案前不得為求綠燈調整本組斷言。**
BILLING_INSTANCE_CASES = [
    "我的這張點退帳單金額怎麼算出來的",
    "我這筆點退帳單怎麼會是這個數字",
    "幫我查點退帳單金額",
    "這張帳單的收據金額多少",
]

# ── facet 歸屬待定：不得拿來替 T-1 背書 ──
# 以下問句實測進的是**其他**帳單診斷面向，而非「條件診斷：帳單」。
# 它們產品上究竟該去哪個面向**尚未定案**，在定案前不列入正向斷言——
# 否則就是拿「跑錯面向」當成能力成立的證據（3.4 驗證期間已犯過一次）。
#   「我的收據在哪」          → 帳單異常（3936 租客說看不到帳單 找不到）
#   「我這筆點退的錢怎麼怪怪的」→ 帳單異常（3934 帳單金額怪怪的 跟預期不一樣）
# 「怎麼怪怪的」本就是帳單異常的句型，故此二筆的正確歸屬需獨立判定。
BILLING_INSTANCE_FACET_UNDECIDED = [
    "我的收據在哪",
    "我這筆點退的錢怎麼怪怪的",
]

#: instance 問法應落在的面向——不得只驗 dialog（見上方說明）
BILLING_INSTANCE_FACET = "條件診斷：帳單"


# ── IoT：應進對話（iot-conversational-facets 任務 3.4 / R6.3, R9.2）──
IOT_FACES = {"電表排障", "IoT設定引導"}

IOT_DIALOG_CASES = [
    "租客說房間沒電 電表沒供電",
    "租客反映房間突然沒電了",
    "電表一直離線 度數不動",
    "電表度數跟現場對不起來",
    "租客儲值了 電還是沒有來",          # 儲值後未復電（電表排障，非帳務）
    "電表要怎麼串接進系統",
    "儲值單價要在哪裡設定",
    "租客要怎麼幫電表儲值",              # 3459 補標後進設定引導（教學收斂，體驗等同單發＋可追問）
]

# ── IoT：應單發（教學/門鎖硬體，未掛面向）──
IOT_SINGLE_CASES = [
    "門鎖可以用悠遊卡嗎",                # 門鎖硬體單發包
]

# ── IoT 誤吸邊界（點名）：儲值金流歸帳務、門鎖不吸電表 ──
IOT_BOUNDARY_CASES = [
    ("租客儲值的錢到底入帳了沒", "not_iot"),     # 金流入帳 → 帳務域（不得進 IoT 面向）
    ("門鎖的電池是不是沒電了", "not_meter"),      # 門鎖硬體 → 不得吸進電表排障
]


@pytest.mark.req("iot-conversational-facets:6.3")
@pytest.mark.parametrize("question", IOT_DIALOG_CASES)
async def test_iot_openers_enter_dialog(retriever, pool, question):
    kind, detail, best = await _route(retriever, pool, question)
    assert kind == "dialog" and detail in IOT_FACES, \
        f"應進 IoT 對話卻為 {detail}：{question}｜{_fmt(best)}"


@pytest.mark.req("iot-conversational-facets:9.2")
@pytest.mark.parametrize("question", IOT_SINGLE_CASES)
async def test_iot_teaching_stays_single_shot(retriever, pool, question):
    kind, detail, best = await _route(retriever, pool, question)
    assert kind == "single", \
        f"IoT 教學/門鎖問句被吸進「{detail}」對話：{question}｜{_fmt(best)}"


@pytest.mark.req("iot-conversational-facets:6.4")
@pytest.mark.parametrize("question,rule", IOT_BOUNDARY_CASES)
async def test_iot_boundary_no_misattraction(retriever, pool, question, rule):
    kind, detail, best = await _route(retriever, pool, question)
    if rule == "not_iot":
        assert not (kind == "dialog" and detail in IOT_FACES), \
            f"金流句被吸進 IoT「{detail}」：{question}｜{_fmt(best)}"
    else:  # not_meter
        assert not (kind == "dialog" and detail == "電表排障"), \
            f"門鎖句被吸進電表排障：{question}｜{_fmt(best)}"


# ── 物件：應進對話（estate-conversational-facets 任務 3.3 / R7.1, R7.2）──
ESTATE_FACES = {"物件操作引導", "物件現況診斷"}

ESTATE_DIALOG_CASES = [
    "物件要怎麼刊登 上架流程",                  # 錨點本尊（引導）
    "改了對外顯示地址 怎麼還是顯示完整地址",      # 錨點本尊（引導）
    "物件為什麼不能建立合約 缺什麼欄位",          # 錨點本尊（診斷）
    "這個物件現在什麼狀態 租客看得到嗎",          # 錨點本尊（診斷）
    "物件刪掉的話 以前的合約會不會不見",          # 刪除三擋知識（引導）
    "為什麼不能新增物件",                        # 3505 改寫掛引導
    "物件突然全部被下架了",                      # 3506 掛引導
    "招租店舖要怎麼進去",                        # 店舖知識（引導）
]

# ── 物件：應單發（未掛面向；批次上傳範圍外由 persona 導客服，不在路由層）──
ESTATE_SINGLE_CASES = [
    "進階搜尋怎麼用 有哪些條件",
    "報表匯出跑很久跑不完",
]

# ── 物件誤吸邊界（點名）：合約域 title 語彙/IoT 綁定/帳號經理人 ──
ESTATE_BOUNDARY_CASES = [
    ("這份合約的物件地址錯了要怎麼改", "not_estate"),   # 合約資料異動 → 不得進物件面向
    ("物件要綁電表要怎麼設定", "not_estate"),           # IoT 域
    ("要把成員設成某個物件的經理人", "not_estate"),      # 帳號域團隊權限
]


@pytest.mark.req("estate-conversational-facets:7.1")
@pytest.mark.parametrize("question", ESTATE_DIALOG_CASES)
async def test_estate_openers_enter_dialog(retriever, pool, question):
    kind, detail, best = await _route(retriever, pool, question)
    assert kind == "dialog" and detail in ESTATE_FACES, \
        f"應進物件對話卻為 {detail}：{question}｜{_fmt(best)}"


@pytest.mark.req("estate-conversational-facets:7.1")
@pytest.mark.parametrize("question", ESTATE_SINGLE_CASES)
async def test_estate_teaching_stays_single_shot(retriever, pool, question):
    kind, detail, best = await _route(retriever, pool, question)
    assert kind == "single", \
        f"物件單發問句被吸進「{detail}」對話：{question}｜{_fmt(best)}"


@pytest.mark.req("estate-conversational-facets:7.2")
@pytest.mark.parametrize("question,rule", ESTATE_BOUNDARY_CASES)
async def test_estate_boundary_no_misattraction(retriever, pool, question, rule):
    kind, detail, best = await _route(retriever, pool, question)
    assert not (kind == "dialog" and detail in ESTATE_FACES), \
        f"邊界句被吸進物件「{detail}」：{question}｜{_fmt(best)}"


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


@pytest.mark.req("conversational-routing-execution:2.1")
@pytest.mark.parametrize("question", BILLING_INSTANCE_CASES)
async def test_billing_instance_questions_enter_diagnosis_facet(retriever, pool, question):
    """instance-specific 問法必須進「條件診斷：帳單」——斷言到 facet，非僅 dialog。"""
    kind, detail, best = await _route(retriever, pool, question)
    assert kind == "dialog" and detail == BILLING_INSTANCE_FACET, (
        f"instance 問法應進「{BILLING_INSTANCE_FACET}」卻為 {kind}/{detail}：{question}｜{_fmt(best)}"
        "\n（此為 T-1 要保住的查實值能力；落回單發＝使用者拿到通則說明而非自己那筆的資料）")


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
