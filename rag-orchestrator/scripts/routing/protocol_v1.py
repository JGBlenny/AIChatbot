"""protocol v1 的**量尺**（spec routing-disambiguation｜R1.4, R6.1, R3.5）。

責任只有一件事：把一筆**觀測結果**判成 `pass`／`fail`／`unscored`，
以及把一輪觀測判成 `bilateral_pass` 與否。

⚠️ **本模組不重演 routing 語義**——它不檢索、不查 DB、不判該進哪個面向。
   誰進了哪裡由 production seam 決定並餵進來；量尺只負責「這樣算不算過」。

⚠️ **期望值一律取自凍結的 `robustness-protocol.json`**（digest `4690a258f502d98d`），
   量尺內**不另寫一份**。兩份期望值會各自漂移，而漂移的那份通常是比較寬鬆的那份。

⚠️ 為什麼 `dialog` 不夠、非得比到 facet：前案兩度以 `route == "dialog"` 判定成功，
   把「我的收據在哪」進了**帳單異常**（3936）記為 instance 通過。
   故 `observed_facet is None` 一律**不得** pass——訊號不足時不假裝有結論。
"""
import hashlib
import json
import os
from typing import Dict, Iterable, List, Mapping, Optional

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", ".."))
PROTOCOL_PATH = os.path.join(REPO, ".kiro", "specs", "routing-disambiguation",
                             "robustness-protocol.json")

#: 本量尺實作的是 **v1**；換尺即換模組，不在原地改判準（Req.3.5）
PROTOCOL_DIGEST = "4690a258f502d98d"

#: 進入 `bilateral_pass` 分母的兩側（v1 metrics.primary.denominator ＝ 8）
BILATERAL_SETS = ("RULE", "INSTANCE")

_cache: Dict[str, dict] = {}


def _digest(protocol: Mapping) -> str:
    body = {k: v for k, v in protocol.items() if k != "protocol_digest"}
    return hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True, indent=2).encode()).hexdigest()[:16]


def load_protocol() -> dict:
    """讀取凍結檔並**驗 digest**——內容與宣告不符即 abort，不得降級續跑。"""
    if "protocol" not in _cache:
        with open(PROTOCOL_PATH, encoding="utf-8") as f:
            protocol = json.load(f)
        declared = protocol.get("protocol_digest")
        if declared != PROTOCOL_DIGEST or _digest(protocol) != PROTOCOL_DIGEST:
            raise ValueError(
                f"protocol v1 內容與 digest 不符（宣告 {declared}／實算 {_digest(protocol)}／"
                f"本量尺釘死 {PROTOCOL_DIGEST}）——凍結量尺被改動過，結論不具效力")
        _cache["protocol"] = protocol
    return _cache["protocol"]


def expected_for(case_set: str) -> Optional[str]:
    """該案例集的期望結果字串；`None` ＝ 不計入通過率（如 `UNDECIDED`）。"""
    sets = load_protocol()["case_sets"]
    if case_set not in sets:
        raise KeyError(f"未知案例集 {case_set!r}——量尺不對凍結檔以外的案例集發表意見")
    return sets[case_set].get("expected")


def cases_for(case_set: str) -> List[str]:
    return list(load_protocol()["case_sets"][case_set]["cases"])


def observed_str(observed_kind: str, observed_facet: Optional[str]) -> str:
    """把觀測正規化成與凍結期望同格式的字串。

    ⚠️ `dialog` 而無 facet → 回 `"dialog:?"`，**永遠比不上任何期望值**。
    """
    if observed_kind == "dialog":
        return f"dialog:{observed_facet}" if observed_facet else "dialog:?"
    return observed_kind


def score_case(case_set: str, observed_kind: str, observed_facet: Optional[str] = None) -> str:
    """回 `"pass"`／`"fail"`／`"unscored"`。"""
    expected = expected_for(case_set)
    if expected is None:
        return "unscored"
    return "pass" if observed_str(observed_kind, observed_facet) == expected else "fail"


def score_run(results: Iterable[Mapping]) -> List[dict]:
    """逐筆評分；每筆須有 `case_set`／`question`／`kind`，`facet` 可省。"""
    out = []
    for row in results:
        verdict = score_case(row["case_set"], row["kind"], row.get("facet"))
        out.append({**dict(row), "verdict": verdict})
    return out


def bilateral_pass(results: Iterable[Mapping]) -> bool:
    """RULE 與 INSTANCE **兩側**的凍結案例全數 `pass` 才為真（8/8，Req.1.3）。

    ⚠️ 缺席不等於通過：凍結案例集中任何一題**沒有出現在觀測裡**即為不通過。
       否則「只跑規則側」會得到一個看起來很好的 8/8。
    """
    scored = {(r["case_set"], r["question"]): r["verdict"] for r in score_run(results)}
    for case_set in BILATERAL_SETS:
        for question in cases_for(case_set):
            if scored.get((case_set, question)) != "pass":
                return False
    return True
