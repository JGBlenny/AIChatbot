"""`AgentOutput`／`VerifierRules`／`VerifierVerdict` 資料模型（spec agentic-mcp-orchestration・任務 2.3，design.md 元件 6）。

⛔ 只放資料模型，判斷邏輯在 `services/agent/verifier.py`。pydantic v2（見 requirements.txt `pydantic>=2.13,<3`）。

**`AgentOutput.fact_class` 刻意型別為 `Optional[str]`，不是 `FactClass` 列舉**（設計取捨，見任務回報）：
design 元件 6 要求 verifier 對「`fact_class` 缺／不合法」做 fail-closed 判斷——如果這個欄位型別是
`FactClass`，pydantic 在**建構 `AgentOutput` 這一步**就會因為非法值直接 raise，verifier 永遠看不到
「非法值」這個狀態，也就測不到 fail-closed 分支。生產路徑上，OpenAI `response_format` 的
`json_schema strict` 仍會把 schema 送成封閉 enum；這裡放寬只是讓 verifier 自己能做「缺／非法」
與「合法值但屬 SENSITIVE」的兩段式判斷（`services/agent/verifier.py::_classify_fact_class`）。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


#: T1（Plan `inputs/plan-walkthrough-fixes-batch2-20260909.md` §2）：`kind=ask` 時
#: **追問對象**的封閉值域。⚠️ 值是**機器值**（英文），⛔ 不是給使用者看的字——
#: 使用者看到的措辭由既有面向決定，兩者分開才不會為了改一句話而動到契約。
#: ⚠️ 它同時是三個地方的唯一值域來源：`AgentOutput.ask_target` 的 schema 覆寫
#: （`runtime._agent_output_response_format`）、Verifier 的 `ask_target_invalid`、
#: 以及出口閘 `runtime._apply_ask_target_gate`。⛔ 不得在任一處另抄一份字面表。
ASK_TARGETS: tuple[str, ...] = (
    "estate",
    "community",
    "address",
    "bill_id",
    "repair_id",
    "contract_id",
    "meter",
    "date",
    "description",
    "urgency",
    "confirm_intent",
    "choice",
    # 售前線（prospect）補問對象——與 `_POLICY_TEXT` 的可補問欄位同名（identity／scale／team／pain／interested）；
    # schema 與 Verifier 是各受眾共用的，值域必須是各受眾的聯集（2026-09-09 T1 執行代理 P1 裁定）。
    "identity",
    "scale",
    "team",
    "pain",
    "interested",
)


class Sentence(BaseModel):
    """模型逐句輸出的**一筆**：文字、分類與依據標記同筆攜帶（DSP-028／DSP-029a）。

    `text` 要含句尾標點；⛔ 一筆不放兩句（放兩句時 Verifier 會把它切成片段逐一複核，
    片段只**繼承** `kind`／`refs` 標籤、⛔ 不繼承驗證結果）。

    **DSP-029a：`refs` 是標記字串本身，⛔ 不再是任何陣列的索引。**
    起因見 `.claude/DECISIONS.md` DSP-029a：舊契約要模型自己對齊
    `tool_call_id`／`source`／`unit` 三個定址欄位，R5 實測 162 回合裡 119 次錯在
    三欄互混。標記已經整串印在資料段那一行的行首，照抄一個字串是模型做得到的動作，
    對齊三個欄位不是。解析在 `services.agent.provenance_units.resolve_refs`，
    ⛔ 解析結果不寫回本模型任何欄位（r13 F-A：掛上去就會跟著
    `decision_snapshot`／trace 外流）。
    """
    text: str
    kind: Literal["fact", "question", "greeting", "routing"]
    refs: list[str] = Field(
        default_factory=list,
        description=(
            "事實句填其依據所在那一行開頭的標記，原樣照抄。"
        ),
    )


class AgentOutput(BaseModel):
    """模型一輪回覆的結構化輸出（`response_format` json_schema strict）。

    **DSP-028：⛔ 模型不再輸出 `answer` 欄，也不再輸出另一張逐句對照表**——舊契約要模型自己保證
    「句數等於標籤數、順序對得上」，句數不等時程式只能猜哪筆標籤配哪一句，猜錯的
    方向是放行。改成文字與標籤同筆攜帶後，「拼接後等於送出的字串」變成定義而不是
    要靠檢查維持的巧合。

    **DSP-029a：⛔ 不再有 `citations` 陣列**——引用就是 `Sentence.refs` 裡的標記字串，
    句子與依據之間不再隔一層索引（索引本身是另一個會對錯的東西）。
    """
    kind: Literal["answer", "ask", "recommend", "handoff"] = Field(
        description=(
            "本輪回覆的型別：answer 直接回答、ask 反問澄清、recommend 建議下一步、"
            "handoff 轉真人（轉人時 sentences 可留空）。"
        )
    )
    sentences: list[Sentence] = Field(
        default_factory=list,
        description=(
            "回覆逐句一筆 {text, kind, refs}；text 含句尾標點、⛔ 一筆不放兩句。"
            "系統把各筆 text 原樣接起來就是使用者看到的整段話，⛔ 不另外給 answer 欄位。"
        ),
    )
    fact_class: Optional[str] = None  # 見檔案頂端說明：刻意不是 FactClass 型別
    handoff_reason: Optional[str] = None
    #: T1：追問對象。**刻意型別為 `Optional[str]`、⛔ 不是 `Literal[ASK_TARGETS]`**
    #: ——理由同 `fact_class`（見檔案頂端）：型別若收成封閉列舉，非法值在建構
    #: `AgentOutput` 這一步就 raise，Verifier 永遠看不到「填錯」這個狀態，
    #: `ask_target_invalid` 這條 fail-closed 分支也就測不到。給模型的 strict
    #: schema 仍是封閉列舉（`runtime._agent_output_response_format` 的覆寫）。
    ask_target: Optional[str] = Field(
        default=None,
        description=(
            "kind=ask 時必填，且必須是值域內的一項；其他 kind 一律填 null。"
        ),
    )

    @property
    def answer(self) -> str:
        """使用者實際會看到的整段文字＝逐筆 `text` 直接拼接（⛔ 不補空白、不補標點）。

        **刻意用純 `@property`、⛔ 不用 pydantic `computed_field`**（r11 安全審 F-4）：
        `computed_field` 會讓 `model_json_schema()` 把 `answer` 列進 properties，而
        `services/agent/runtime.py:strict_json_schema` 把每一層的 `required` 設成
        「全部 properties」⇒ OpenAI strict schema 會**回頭要求模型輸出 `answer`**，
        等於把剛拆掉的雙軌契約原封不動裝回去。純 property 不進 schema，也不進
        `model_dump()`，`answer` 因此只有一個導出點——步①⑤⑥⑦掃的字串就是送出的字串。
        """
        return "".join(s.text for s in self.sentences)


#: 11 個結構化拒因（design 元件 6 全文）。
VerdictReason = Literal[
    "SENSITIVE_TOPIC",
    "UNCITED_ASSERTION",
    "QUOTE_NOT_VERBATIM",
    "QUOTE_TOO_SHORT",
    "QUOTE_NOT_COVERING",
    "POLARITY_MISMATCH",
    "SOURCE_NOT_CITABLE",
    "ROUTE_NOT_ALLOWED",
    "FORBIDDEN_TERM",
    "HANDOFF_WORD_NO_HANDOFF",
    "SCHEMA",
]


#: `term_id` 的唯一合法形式（2.6 前置 security review P2）：`rule#<規則集內索引>`。
#: ⛔ **不得填字面詞／regex 本身**——verdict 會落進
#: `usage_events.decision_snapshot.agent`，也會被 2.7 的 trace 端點印出來，
#: 填字面值等於把敏感樣式表／禁詞表／否定詞表逐字外洩。
#: 產生點是 `services/agent/verifier.py:_rule_id()`；這裡用 pydantic `pattern`
#: 把契約釘在型別上，任何想塞字面詞的呼叫端會在建構當下就炸。
TERM_ID_PATTERN = r"^rule#\d+$"


class VerifierVerdict(BaseModel):
    """結構化拒因。⛔ 不放原文（`sent`／`term_id`／`quote_len` 是索引與長度，不是內容）。

    `term_id` 只認 `rule#<n>`：`reason` 決定查哪一張規則表
    （`SENSITIVE_TOPIC`→`sensitive_patterns`、`FORBIDDEN_TERM`→`forbid_terms`、
    `POLARITY_MISMATCH`→`negation_terms`），`n` 是該表內 0-based 索引，
    再配 trace 的 `rules_sha` 才對得回具體規則集版本。
    """
    ok: bool
    reason: Optional[VerdictReason] = None
    #: W6-b3（`AGENT_VERIFIER_MODE=grounding_observe`）：本回合**被觀察而未擋**的違規類別，
    #: 形狀 `"<reason>"` 或 `"SCHEMA:<schema_cause>"`（去重、依命中順序）。
    #: ⛔ 只放列舉值，**不攜帶任何模型文字或來源原文**——與 `schema_cause` 同一條紀律
    #: （它會落 `usage_events.decision_snapshot.agent`，也會被 trace 端點印出來）。
    #: ⚠️ `observed` 非空 **≠ 這回合被拒**：`ok=True` 且 `observed` 非空是觀察模式的
    #: 正常輸出，呼叫端 ⛔ 不得據此遞增 `counters.rewrites`（見 `runtime.py` 的
    #: `if not verdict.ok` 分支）。
    observed: list[str] = Field(default_factory=list)
    #: `POLARITY_MISMATCH` 的來源表（W6-b3 誤殺量測後分流）：`term`＝裸否定詞表 `negation_terms`
    #: （對稱整段比對，引文側含否定詞即誤殺——`grounding_observe` 下降為觀察類）；
    #: `pair`＝主題錨定 `negation_status_pairs`（狀態詞兩側都在才算，照擋）。其他拒因為 None。
    polarity_source: Optional[Literal["term", "pair"]] = None
    #: DSP-028：**筆索引**（`AgentOutput.sentences` 的 index），⛔ 不是切片段後的片段序號——
    #: 一筆裡若含多個片段，任一片段違規都記在該筆的索引上（`trace_view` 顯示為「筆次」）。
    sent: Optional[int] = None
    term_id: Optional[str] = Field(default=None, pattern=TERM_ID_PATTERN)
    quote_len: Optional[int] = None
    #: DSP-029 r13 #7：`SCHEMA` 的**子成因**（封閉列舉）。原本只回 `SCHEMA` 三個字，
    #: 模型與稽核都看不出是哪一種；引用改成標記字串後，「標記本身不合格式／不是
    #: 本回合的」與「標記合格式但指不到東西」是不同的病，不分流等於把它們混進同一格。
    #: DSP-029a：`cite_out_of_range` 退場（`cite` 索引已不存在），改為
    #: `ref_invalid`（格式不合或 nonce 非本回合）／`ref_source_not_found`／`ref_ambiguous`。
    #: ⛔ 只放列舉值，**不攜帶任何模型文字或來源原文**——它會落
    #: `usage_events.decision_snapshot.agent`，也會被 trace 端點印出來。
    schema_cause: Optional[
        Literal[
            "empty_sentences",
            "empty_text",
            "ref_invalid",
            "ref_source_not_found",
            "ref_ambiguous",
            "unit_out_of_range",
            "marker_in_answer",
            "handoff_reason_invalid",
            "handoff_reason_mismatch",
            # T1：`kind=ask` 卻沒填／填了值域外的 `ask_target`。
            "ask_target_invalid",
        ]
    ] = None


class VerifierRules(BaseModel):
    """規則集。`load()` 是唯一建構入口——`sha256` 一律由載入時的檔案位元組計算，
    ⛔ 不信任 json 檔內任何 `sha256` 欄位（避免檔案改了但欄位忘記同步，`sha256` 就失去自證意義）。
    """
    version: str
    sha256: str
    sensitive_patterns: list[str]
    #: U3（Plan `inputs/plan-document-summary-demo-20260909.md` §U3／W9-11／W9-12）：
    #: 上面那張 `sensitive_patterns` **對哪些受眾生效**。
    #: * `None`（規則檔沒有這個鍵）＝**全受眾**＝本欄位出現以前的行為，⛔ 不是「不生效」；
    #: * 有清單時，只有清單內的受眾會被這張表掃到。
    #: ⚠️ 缺值方向刻意是**照擋**：這一欄一旦被誤讀成「沒宣告＝關掉」，售前守門會在
    #: 沒有人發現的情況下整張消失。判定在 `verifier.OutputVerifier._sensitive_patterns_apply`，
    #: ⛔ 不在這裡展開語義。
    #: ⚠️ 與 `question_sensitive_patterns`（問句側）無關，⛔ 不共用這張受眾清單。
    #: 預設 `None` 而非 `[]`：pydantic 白名單會**靜默忽略未宣告鍵**，所以這個欄位
    #: 必須宣告，否則規則檔加了鍵也讀不到（載入正對照測試釘住這件事）；而 `[]`
    #: 與「沒宣告」是兩件事——前者是明寫「沒有任何受眾要掃」，後者是舊規則檔。
    sensitive_patterns_audiences: Optional[list[str]] = None
    #: W9 情境①（2026-09-09）：`allowed_routes` 的電話／網址白名單檢查（`ROUTE_NOT_ALLOWED`）
    #: 也是售前 CTA 守門——pm 引資料段的交易序號會被電話正則咬到（`R2026081500042`
    #: 的 `02608150004` 命中 `_PHONE_RE` 第二支）。同 `sensitive_patterns_audiences`
    #: 的語義：缺鍵＝全受眾＝舊行為；缺 audience／未知 ⇒ 照擋。
    route_check_audiences: Optional[list[str]] = None
    negation_terms: list[str]
    #: W6-b3（plan-verifier r3 #1）：**主題錨定**極性詞表——`[{"neg": "尚未", "status": "逾期"}, …]`，
    #: 以否定詞與狀態詞兩個**封閉集合的笛卡兒積**維護（規則檔內逐筆寫出，⛔ 不在程式裡展開，
    #: 那樣 `rules_sha` 就管不到詞表內容）。裸「尚未」「未」⛔ 不進 `negation_terms`：
    #: 整段引文比對會把「句子沒提到該主題、引文另一段落有否定」誤殺（`known_open.json`
    #: 的 `r4_edit_contract_requires_admin_role` 是實例）。
    #: 預設空表——舊規則檔（與只給部分欄位的測試用 `VerifierRules(**dict)`）照樣載得起來，
    #: 效果等同「這條規則沒開」。
    negation_status_pairs: list[dict[str, str]] = Field(default_factory=list)
    forbid_terms: list[str]
    #: 第六批單元 E（line-bot #6／#3）：**文件回合專用**禁用樣式（正則陣列，
    #: NFKC 後比對），兩類——(a) 完成式寫入宣稱（「已掛／已存／已建立／已匯入…」）、
    #: (b) 提議寫入（「要我…匯入嗎」「要不要…建單」）。文件歸納回合 ⛔ 不寫回、
    #: ⛔ 不建單，所以這兩種句子在該回合一律是**承諾做不到的事**。
    #: ⚠️ 與 `forbid_terms` 是**兩張表**，⛔ 不合併：那張是字面子字串、對**所有**
    #: 回合生效；這張是正則、只在 `verify(document_turn=True)` 時生效。合併會讓
    #: 「已掛」這類在正常寫入回合是**正確**的句子被整條線誤殺。
    #: 預設 `None`（規則檔沒有這個鍵）＝**不啟用**——本欄位是新增的閘，缺鍵時
    #: 舊規則檔的行為必須一字不變；⚠️ 這與 `sensitive_patterns_audiences` 的
    #: 「缺鍵＝全受眾＝照擋」方向**相反**，理由是那一欄的缺鍵代表舊行為是「掃」，
    #: 這一欄的缺鍵代表舊行為是「沒有這張表」。判定在
    #: `verifier.OutputVerifier.verify`，⛔ 不在這裡展開語義。
    #: ⚠️ pydantic 白名單會**靜默忽略未宣告鍵**，故此欄位必須宣告，否則規則檔
    #: 加了鍵也讀不到（`test_document_turn_forbid_req.py` 的載入正對照釘住這件事）。
    document_turn_forbid_terms: Optional[list[str]] = None
    allowed_routes: list[str]
    assertion_terms: list[str]
    min_quote_len: int = 6
    min_coverage_chars: int = 4
    #: DSP-029：覆蓋率改**片段側相對值**——被驗的那個片段（模型自己寫的句子）
    #: 有意義字元中，至少這個比例要出現在解析出來的來源片段裡。絕對下限
    #: `min_coverage_chars` 仍在（`max(...)`），兩者是「取嚴的那個」而非二選一。
    min_coverage_ratio: float = 0.5
    #: U2（Plan `plan-walkthrough-fixes-batch3-20260909.md` §3）：**問句側**敏感樣式，
    #: `presales_gate.SENSITIVE` 五類各一組正則（順序＝customer_reference／pricing／
    #: contract_sla／compliance／security）。用途只有一個：
    #: `services/agent/question_sensitivity.question_sensitive()`——判「模型自報的
    #: 敏感類站不站得住」。⚠️ 與答案側的 `sensitive_patterns` 是**兩件事**，⛔ 不合併：
    #: 那一組掃的是模型寫出來的答案（縱深防禦，維持原樣）。
    #: 預設空表＝這一側一律判非敏感（pydantic 白名單會靜默忽略未宣告鍵，故此欄位
    #: 必須宣告，否則規則檔加了鍵也讀不到——載入正對照測試釘住這件事）。
    question_sensitive_patterns: list[str] = []

    @classmethod
    def load(cls, path: str | Path) -> "VerifierRules":
        raw = Path(path).read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        data = json.loads(raw)
        data["sha256"] = sha
        return cls.model_validate(data)


__all__ = ["Sentence", "AgentOutput", "ASK_TARGETS", "VerdictReason", "VerifierVerdict",
           "VerifierRules", "TERM_ID_PATTERN"]
