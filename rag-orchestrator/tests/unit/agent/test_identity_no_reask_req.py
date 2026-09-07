"""unit：身分反問句型表這把尺（Plan
`.kiro/specs/knowledge-outline-and-intent-architecture/inputs/plan-m-d-runtime-wiring-20260907.md`
§4.1-7／-8、§4.3-6｜knowledge-outline-and-intent-architecture:4.2）。

**主張範圍＝「agent 路徑內不重問」**（業主 2026-09-07 收窄）：

1. **非空守門**：五個欄位各 6 條、且逐列等於業主核可的草稿——任一欄位空掉，
   「不得命中」這種否定斷言就恆真（＝一把瞎尺）。
2. **正例**（R4.3）：`identity_source=anonymous` 的回合模型問身分，量得到；
   把表清空 ⇒ 這條正例**必紅**（清空必紅的正對照）。
3. **entry 的否定斷言只套「身分」＋「槽位已知的欄位」**：問一個**未知**欄位
   （pain／scale…）是售前規則允許的「一次一題」補問，⛔ 不得判違規；
   `unit_count` 已知時再問戶數才是重問。
4. **不進 prompt**：`IDENTITY_REASK_PATTERNS`／`reask_hits` ⛔ 不得被
   `agent_rules.py`／`prompt_assembler.py`／`outline.py`／`runtime.py` 引用
   （`presales_gate.SENSITIVE` 被 `agent_rules._SENSITIVE_LINE` 反射進政策文的
   先例是刻意保留的，本檔拿它當掃描器的正對照，⛔ 不動那條先例）。
5. **兩側都 NFKC**。

⚠️ **已知債 F-10**（業主 2026-09-07 記錄在案、本片 ⛔ 不解）：主張只到 agent 路徑。
`fallback_old_chain` 之後**舊鏈讀的是 `collected_fields`、⛔ 不讀 `slots`**，
因此舊鏈仍會重問——那條路這張表管不到。

⚠️ 單元層一律**假模型**：這裡證的是**尺**（正例命中、清空必紅、entry 依已知欄位過濾）
與「不進 prompt」；真模型「一次一題、已知不重問」的行為留 4.4b 對真輸出量。
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from types import MappingProxyType

import pytest

from services import presales_gate as PG
from services.agent.identity import derive_identity_source
from tests.unit.agent.test_runtime_req import (
    FakeAssembler,
    FakeProvider,
    FakeRegistry,
    FakeVerifier,
    _final_response,
    _identity,
    _runtime,
)

pytestmark = [
    pytest.mark.unit,
    pytest.mark.req("knowledge-outline-and-intent-architecture:4.2"),
]

REPO_ROOT = Path(__file__).resolve().parents[3]              # 容器內＝/app
AGENT_DIR = REPO_ROOT / "services" / "agent"
#: 業主核可的句型表正本（容器把 repo 根的 `.kiro` 唯讀掛在 `/.kiro`）。
DRAFT_PATH = (
    REPO_ROOT.parent / ".kiro" / "specs" / "knowledge-outline-and-intent-architecture"
    / "inputs" / "identity-reask-patterns-draft-20260907.md"
)

#: 五個欄位（＝草稿 §3 的五節）。
FIELDS = ("identity", "scale", "team", "pain", "interested")

#: **本回合欄位選取**用的槽位鍵 → 句型表欄位映射（`SlotKey` 十值裡對得上五欄位的五個；
#: `contract_ref`／`bill_ref`／`estate_ref`／`repair_ref`／`business_type` 不是售前五欄位，
#: ⛔ 不硬湊）。⚠️ 這支**刻意留在測試檔**：它是「這一回合該用哪幾欄的尺」的判準，
#: 屬本主張的一部分，⛔ 不進 `presales_gate.py`——產品程式碼不需要它，多一個公開符號
#: 就多一條被 prompt 組裝路徑引用的路。
SLOT_KEY_TO_FIELD = {
    "unit_count": "scale",
    "team": "team",
    "pain": "pain",
    "interested": "interested",
    "identity_detail": "identity",
}


def reask_fields_for(identity_source: str, known_slot_keys) -> frozenset:
    """這一回合「⛔ 不得再問」的欄位集合。

    - `identity_source == "entry"` ⇒ 身分由入口決定 ⇒ 加 `identity`（Plan §4.1-5 政策句）。
    - 任一**已知槽位**對應的欄位一律加入（售前規則「已知或可推斷的欄位絕不再問」）。
    - 其餘欄位（未知）**不入集合**：一次一題的補問是規則允許的，⛔ 不得判違規。

    ⛔ 未知的 `identity_source` 一律 `ValueError`（值域＝`derive_identity_source` 的兩值；
    打錯字會讓否定斷言恆真）。
    """
    if identity_source not in ("entry", "anonymous"):
        raise ValueError(f"未知的 identity_source：{identity_source!r}")
    fields = {SLOT_KEY_TO_FIELD[k] for k in known_slot_keys if k in SLOT_KEY_TO_FIELD}
    if identity_source == "entry":
        fields.add("identity")
    return frozenset(fields)


# ---------------------------------------------------------------------------
# 共用：斷言小工具（`pytest.raises` 的控制組要拿得到「同一條斷言」）
# ---------------------------------------------------------------------------
def _assert_asks_identity(text: str) -> None:
    """正例用：這句**必須**被判成在問身分。"""
    assert PG.reask_hits(text, ["identity"]), "句型表對這句沒有任何命中——尺看不見已知病灶"


def _assert_no_reask(text: str, fields) -> None:
    """否定斷言：這一回合不得再問 `fields` 這幾欄。"""
    hits = PG.reask_hits(text, sorted(fields))
    assert not hits, f"這一回合不得再問 {sorted(hits)}（已由入口決定或槽位已知）"


def _turn(answer_text: str, state=None):
    """跑一回合假模型，回 (result, assembler)。⛔ 不接真 provider／DB。"""
    assembler = FakeAssembler()
    runtime = _runtime(
        provider=FakeProvider([_final_response(answer=answer_text)]),
        registry=FakeRegistry(),
        verifier=FakeVerifier(),
        assembler=assembler,
    )
    return runtime, assembler, (state if state is not None else {})


async def _run(answer_text: str, identity, state=None):
    runtime, assembler, st = _turn(answer_text, state)
    result = await runtime.run_turn(identity, "你好我有需求", st)
    return result, assembler, st


def _anonymous_identity():
    """prospect、無 `role_id`／`user_id` ⇒ `anonymous`（REST／MCP 兩入口的售前形狀）。"""
    return _identity(vendor_id=1, target_user="prospect", mode="b2b", role_id=None, user_id=None)


def _entry_identity():
    """pm 帶 `role_id`＋`user_id` ⇒ `entry`。⚠️ `AGENT_TURN_SPEC` stage 今天只開 prospect，
    `entry` 分支無活流量，故契約測試以 pm 身分構造（Plan §4.1-2）。"""
    return _identity(vendor_id=1, target_user="property_manager", mode="b2b",
                     role_id="20151", user_id="u-1")


#: 假模型輸出（測試詞彙；句型片段本身是業主核可的表內字串）
_ANON_ASKS_IDENTITY = "好的。為了給您對的說明，請容我確認：您是自己收租，還是有委託代管呢？"
_ENTRY_ASKS_UNKNOWN_PAIN = "這部分系統支援自動對帳。想多了解一下，目前最困擾您的是哪個環節呢？"
_ENTRY_REASKS_KNOWN_SCALE = "了解。想再確認一次，您目前管理多少戶呢？"
_ENTRY_CLEAN = "這部分系統可以自動對帳，我再補充說明給您聽。"


# ---------------------------------------------------------------------------
# (a) 非空守門＋逐列對帳（空表 ⇒ 否定斷言恆真，F-11）
# ---------------------------------------------------------------------------
def _parse_draft(text: str) -> dict:
    """從草稿 §3 的五張表抓「句型」欄（第 2 格），回 {欄位: (句型…)}。"""
    field, table = None, {}
    for line in text.splitlines():
        stripped = line.strip()
        heading = re.match(r"^###\s+3\.\d+\s+([A-Za-z_]+)", stripped)
        if heading:
            field = heading.group(1)
            table.setdefault(field, [])
            continue
        if stripped.startswith("## "):
            field = None
            continue
        if field and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) >= 2 and cells[0].isdigit():
                table[field].append(cells[1])
    return {k: tuple(v) for k, v in table.items()}


def test_table_is_row_for_row_the_approved_draft():
    """句型表＝業主 2026-09-07 核可的草稿三十列逐字（⛔ 不得就地改字）。"""
    assert DRAFT_PATH.is_file(), (
        f"讀不到核可的句型表草稿 {DRAFT_PATH}——這是查證條件壞了（容器需唯讀掛 .kiro），"
        "⛔ 不是「表沒問題」"
    )
    parsed = _parse_draft(DRAFT_PATH.read_text(encoding="utf-8"))
    # 正對照：解析器真的抓到 5×6 列（抓不到就會讓下面那條比對變成 0 對 30 而紅）
    assert {f: len(v) for f, v in parsed.items()} == {f: 6 for f in FIELDS}, (
        f"草稿解析器只抓到 {[(f, len(v)) for f, v in parsed.items()]}——解析器壞了"
    )
    assert parsed == dict(PG.IDENTITY_REASK_PATTERNS)


def test_every_field_is_non_empty_with_exactly_six_patterns():
    """非空守門（F-11）：任一欄位空掉 ⇒ 該欄位的否定斷言恆真。"""
    assert sorted(PG.IDENTITY_REASK_PATTERNS) == sorted(FIELDS)
    assert {f: len(PG.IDENTITY_REASK_PATTERNS[f]) for f in FIELDS} == {f: 6 for f in FIELDS}
    for field in FIELDS:
        assert PG.IDENTITY_REASK_PATTERNS[field], f"{field} 欄位被清空了"
        assert all(p.strip() for p in PG.IDENTITY_REASK_PATTERNS[field])


def test_reask_hits_finds_a_known_pattern_positive_control():
    """正對照：含表內句型的句子一定量得到，且回的就是那一條。"""
    hits = PG.reask_hits("請問您的身分是哪一種呢？", ["identity"])
    assert hits == {"identity": ("請問您的身分",)}


def test_reask_hits_is_silent_on_a_sentence_without_any_pattern():
    """反面：不含任何句型的句子 ⇒ 空 dict（尺不會亂咬）。"""
    assert PG.reask_hits(_ENTRY_CLEAN, FIELDS) == {}


def test_reask_hits_rejects_an_unknown_field():
    """⛔ 打錯欄位名一律 raise：靜默回空會讓否定斷言恆真。"""
    with pytest.raises(ValueError):
        PG.reask_hits("隨便一句", ["identity", "scaleX"])


# ---------------------------------------------------------------------------
# (b) 正例（R4.3）：anonymous 回合問身分 ⇒ 命中；清空表 ⇒ 這條正例必紅
# ---------------------------------------------------------------------------
async def test_anonymous_turn_that_asks_identity_is_a_hit():
    identity = _anonymous_identity()
    assert derive_identity_source(identity) == "anonymous"

    result, assembler, _ = await _run(_ANON_ASKS_IDENTITY, identity)

    assert result.kind == "answer"
    # 這一回合真的是匿名入口（派生槽位是 run_turn 現算後餵進 prompt 的）
    assert assembler.calls[-1]["slots"]["identity_source"] == "anonymous"
    _assert_asks_identity(result.answer)
    assert PG.reask_hits(result.answer, ["identity"]) == {"identity": ("您是自己收租",)}


async def test_emptied_table_makes_the_positive_case_vacuous(monkeypatch):
    """清空必紅：把表換成全空 tuple ⇒ 上一條正例的**同一條斷言**必須失敗。"""
    identity = _anonymous_identity()
    result, _, _ = await _run(_ANON_ASKS_IDENTITY, identity)
    _assert_asks_identity(result.answer)                       # 清空前：命中

    monkeypatch.setattr(
        PG, "IDENTITY_REASK_PATTERNS", MappingProxyType({f: () for f in FIELDS})
    )
    with pytest.raises(AssertionError):
        _assert_asks_identity(result.answer)                   # 清空後：必紅


# ---------------------------------------------------------------------------
# (c) entry 的否定斷言（收窄）：只禁身分＋已知欄位
# ---------------------------------------------------------------------------
async def test_entry_turn_asking_an_unknown_field_is_allowed():
    """entry 回合問一個**未知**欄位（pain）⇒ 不算重問；但尺看得見它在問 pain。"""
    identity = _entry_identity()
    assert derive_identity_source(identity) == "entry"

    state = {"slots": {}}
    result, assembler, _ = await _run(_ENTRY_ASKS_UNKNOWN_PAIN, identity, state)
    assert assembler.calls[-1]["slots"]["identity_source"] == "entry"

    fields = reask_fields_for("entry", state["slots"])
    assert fields == frozenset({"identity"})
    _assert_no_reask(result.answer, fields)                    # 身分沒被再問 ⇒ 放行
    # 正對照（證明放行不是因為尺瞎了）：pain 欄位的句型**確實**命中
    assert PG.reask_hits(result.answer, ["pain"]) == {"pain": ("最困擾您的",)}


async def test_entry_turn_reasking_a_known_slot_is_a_hit():
    """`unit_count` 已知 ⇒ 檢查欄位變成 {identity, scale}；再問戶數＝重問（否定斷言必紅）。"""
    identity = _entry_identity()
    state = {"slots": {"unit_count": {"value": "600", "source": "tool", "confirmed": False}}}
    result, assembler, _ = await _run(_ENTRY_REASKS_KNOWN_SCALE, identity, state)
    assert assembler.calls[-1]["slots"]["unit_count"] == "600"   # 正對照：槽位真的攤平進了 prompt

    fields = reask_fields_for("entry", state["slots"])
    assert fields == frozenset({"identity", "scale"})
    with pytest.raises(AssertionError):
        _assert_no_reask(result.answer, fields)
    # 命中的是 scale，⛔ 不是 identity（尺沒有把整段話都算成問身分）
    assert PG.reask_hits(result.answer, sorted(fields)) == {"scale": ("管理多少戶",)}


async def test_entry_turn_with_clean_output_has_no_hit():
    """同一組欄位下，乾淨輸出 ⇒ 不命中（證明上一條的紅不是恆紅）。"""
    identity = _entry_identity()
    state = {"slots": {"unit_count": {"value": "600", "source": "tool", "confirmed": False}}}
    result, _, _ = await _run(_ENTRY_CLEAN, identity, state)

    fields = reask_fields_for("entry", state["slots"])
    assert fields == frozenset({"identity", "scale"}), "檢查欄位是空的 ⇒ 這條否定斷言恆真"
    _assert_no_reask(result.answer, fields)
    assert PG.reask_hits(result.answer, sorted(fields)) == {}


def test_reask_fields_for_rejects_an_unknown_identity_source():
    with pytest.raises(ValueError):
        reask_fields_for("entryish", {})


def test_reask_fields_for_maps_every_known_slot_key():
    """五個對得上的槽位鍵各自映到欄位；`anonymous` ⛔ 不加 identity（匿名可以問身分）。"""
    known = {"unit_count", "team", "pain", "interested", "identity_detail", "bill_ref"}
    assert reask_fields_for("anonymous", known) == frozenset(FIELDS)
    assert reask_fields_for("anonymous", {"bill_ref"}) == frozenset()
    assert reask_fields_for("entry", {"bill_ref"}) == frozenset({"identity"})


# ---------------------------------------------------------------------------
# (d) 不進 prompt：句型表 ⛔ 不得被 prompt 組裝路徑引用
# ---------------------------------------------------------------------------
PROMPT_PATH_FILES = ("agent_rules.py", "prompt_assembler.py", "outline.py", "runtime.py")
BANNED_SYMBOLS = ("IDENTITY_REASK_PATTERNS", "reask_hits")


def _referenced_names(source: str) -> set:
    """原始碼引用到的識別字（Name／Attribute／import 別名）。"""
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.alias):
            names.add(node.name.split(".")[-1])
            if node.asname:
                names.add(node.asname)
    return names


@pytest.mark.parametrize("filename", PROMPT_PATH_FILES)
def test_prompt_path_modules_do_not_reference_the_pattern_table(filename):
    path = AGENT_DIR / filename
    assert path.is_file(), f"正對照失敗：{path} 不存在——掃描目標本身錯了，不是「查無引用」"
    source = path.read_text(encoding="utf-8")
    names = _referenced_names(source)
    for symbol in BANNED_SYMBOLS:
        assert symbol not in names, f"{filename} 引用了 {symbol}——句型表 ⛔ 不得進 prompt 組裝路徑"
        # 字面掃描：連 `getattr(presales_gate, "…")` 與註解／docstring 提及都不放行
        assert symbol not in source, f"{filename} 出現了 {symbol} 字面——句型表 ⛔ 不得進 prompt 組裝路徑"


def test_scan_sees_sensitive_referenced_in_agent_rules_positive_control():
    """正對照：同一支掃描器看得見 `agent_rules` 反射 `presales_gate.SENSITIVE` 的既有先例
    （⛔ 不改那條先例——這裡只拿它證明掃描器不是形同虛設）。"""
    names = _referenced_names((AGENT_DIR / "agent_rules.py").read_text(encoding="utf-8"))
    assert "SENSITIVE" in names


def test_scan_catches_a_planted_reference_positive_control():
    planted = (
        "from services.presales_gate import IDENTITY_REASK_PATTERNS\n"
        "def f():\n"
        "    return IDENTITY_REASK_PATTERNS['identity']\n"
    )
    assert "IDENTITY_REASK_PATTERNS" in _referenced_names(planted)


# ---------------------------------------------------------------------------
# (e) 兩側都 NFKC
# ---------------------------------------------------------------------------
#: NFKC 才會併回去的相容字：U+FABB ⇒「請」、U+2F9D（康熙部首）⇒「身」。
#: ⚠️ 這兩個字在原始碼裡看起來就是「請」「身」，但**碼位不同**——
#: 下面那條「沒 NFKC 就比不到」的正對照就是在證這件事。
_COMPAT_TEXT = "請問您的⾝分是哪一種呢？"          # 全形問號亦一併正規化


def test_matching_normalizes_the_text_side():
    # 正對照：**沒有** NFKC 的話這句根本比不到（否則這條測試等於沒測）
    assert "請問您的身分" not in _COMPAT_TEXT
    assert PG.reask_hits(_COMPAT_TEXT, ["identity"]) == {"identity": ("請問您的身分",)}


def test_matching_normalizes_the_pattern_side(monkeypatch):
    """句型那側若被寫成非 NFKC 形式，對半形／標準字形的輸出照樣比得到。"""
    patched = dict(PG.IDENTITY_REASK_PATTERNS)
    patched["identity"] = ("請問您的⾝分",)
    monkeypatch.setattr(PG, "IDENTITY_REASK_PATTERNS", MappingProxyType(patched))
    assert PG.reask_hits("請問您的身分是哪一種呢", ["identity"])


def test_punctuation_does_not_break_matching():
    """句型不含標點 ⇒ 全形問號／半形問號都不影響命中（草稿 §2-4 的理由）。"""
    assert PG.reask_hits("您是個人房東？", ["identity"]) == {"identity": ("您是個人房東",)}
    assert PG.reask_hits("您是個人房東?", ["identity"]) == {"identity": ("您是個人房東",)}
