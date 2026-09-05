#!/usr/bin/env python3
"""`nli-model` 服務：中文 NLI 蘊涵分數（DSP-033）。

Verifier 步③的「這個片段有沒有被它引的來源句支撐」交給一個**固定權重的小型
分類器**回答（⛔ 不是 LLM 判官）：同一對句子在同一份權重下永遠得到同一個分數，
分數本身進 trace，稽核可以拿 `entail_score`＋`nli_model_sha`＋`nli_tau` 把
verdict 重算出來。

## ⛔ 不複製 semantic-model 的形狀
`semantic_model/scripts/api_server.py` 的 `/rerank` 是 `async def` 內直接
`model.predict(...)`——同步 CPU 推論佔住事件迴圈，單 worker 下後面的請求全部
排隊（head-of-line blocking）。DSP-033 P1-3 就是因為這個形狀才裁定 NLI ⛔ 不掛
在 semantic-model。本檔的推論一律走 `asyncio.to_thread`，事件迴圈只負責收送。

## 決定性（P2-5）
`torch.set_num_threads(4)` 是**常數**、**逐對推論（不批次）**、分數四捨五入到
4 位後才與 τ 比較。三者缺一，同一對句子就可能因為批次組成或執行緒數不同而
落在 τ 兩側——那會讓「同樣的輸入得到同樣的判定」這句話不成立。

## 為什麼 torch／transformers 是**函式內** import
本檔要能在**沒有 torch 的環境**被 import（`nli_model/tests/test_api_server.py`
用假模型物件測 canary 與 handler 邏輯，⛔ 不載真模型、⛔ 不觸網）。模組層
import torch 會讓那份測試只能在這個映像裡跑，於是它實際上不會被跑。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("nli_model")

MODEL_DIR = os.getenv("NLI_MODEL_DIR", "/models/erlangshen-110m-nli")
CANARY_PATH = os.getenv("NLI_CANARY_PATH", "/app/canary.json")
#: 建置期由 Dockerfile 以 ENV 烤進映像＝**期望**指紋；啟動時與實算值比對（P2-10）。
EXPECTED_MODEL_SHA = os.getenv("NLI_MODEL_SHA256", "").strip()

#: ⛔ 常數，不吃 env：改任何一個都要重校 τ（r18 F-8）。
MAX_LENGTH = 256
TORCH_THREADS = 4
SCORE_DECIMALS = 4
#: 每對句子的錯誤代碼（client 收到 ⇒ 該對判拒，⛔ 不截斷後硬算）。
ERR_HYPOTHESIS_TOO_LONG = "hypothesis_too_long"

#: 有界佇列：同時只跑一個推論，最多再排 `_MAX_QUEUE` 個；超過即**快速 503**。
#: ⚠️ 排隊排到逾時，對呼叫端而言與服務掛掉沒有差別，卻多花了雙方的時間——
#: client 端逾時＝對數×400 ms，排在第 6 個的請求無論如何都趕不上。
_MAX_INFLIGHT = 1
_MAX_QUEUE = 4


class NliPairIn(BaseModel):
    premise: str
    hypothesis: str


class NliRequest(BaseModel):
    pairs: List[NliPairIn]


app = FastAPI(title="NLI Model API", version="1.0.0")

#: 啟動載入的一切。`ready` 只有在 canary 相符**且**目錄指紋相符時才是 True。
STATE: Dict[str, Any] = {
    "tokenizer": None,
    "model": None,
    "torch": None,
    "entail_idx": None,
    "model_sha": "",
    "sha_ok": False,
    "canary_ok": False,
    "canary_detail": "not_run",
    "tau": 0.4,
    "load_error": "",
}

_inflight = 0


# ---------------------------------------------------------------------------
# 純邏輯（無 torch 相依，供 nli_model/tests 以假物件驗）
# ---------------------------------------------------------------------------

def entailment_index(id2label: Any) -> int:
    """從 `config.json` 的 `id2label` 找出 ENTAILMENT 是第幾格（r18 F-7）。

    🔴 找不到就 raise，⛔ 不預設 2。這個模型現在確實是
    `{0: CONTRADICTION, 1: NEUTRAL, 2: ENTAILMENT}`，但寫死索引的意思是
    「換一個標籤順序不同的權重時，我們會安靜地把『矛盾』的機率當成
    『蘊涵』的機率回報」——那個失敗方向是放行捏造，且沒有任何徵兆。
    """
    if not isinstance(id2label, dict):
        raise ValueError("config.id2label 不是 dict——⛔ 無法判定 ENTAILMENT 索引")
    for key, label in id2label.items():
        if str(label).strip().upper() == "ENTAILMENT":
            return int(key)
    raise ValueError(f"config.id2label 沒有 ENTAILMENT：{id2label!r}")


def hypothesis_too_long(n_hypothesis_tokens: int, n_special_tokens: int) -> bool:
    """hypothesis 光是自己就塞不進 `max_length` ⇒ 該對回錯誤碼（r18 F-8）。

    `truncation='only_first'` 只砍 premise，所以 hypothesis 永遠是完整的——
    但它太長時 tokenizer 會轉而丟例外或把 premise 砍到空。⛔ 不改成
    `longest_first` 來「讓它算得出來」：截掉 hypothesis 等於改動被驗的那句話，
    分數就不再是對那句話的判定。
    """
    return n_hypothesis_tokens + n_special_tokens > MAX_LENGTH


def evaluate_canary(canary: dict, scores: List[Optional[float]]) -> tuple:
    """比對 canary 實得與期望，回 `(ok, detail)`。

    `scores` 的順序＝`canary_pairs(canary)` 的順序（fabrications 在前）。
    🔴 任一對算不出分數（None）一律**不通過**，⛔ 不跳過——「這一對沒算到」
    與「這一對符合期望」是兩件事，用同一個結論表示就是假綠。
    """
    fabs = canary.get("fabrications") or []
    grounded = canary.get("grounded") or []
    tau = float(canary.get("tau", 0.4))
    expect = canary.get("expect") or {}
    if len(scores) != len(fabs) + len(grounded):
        return False, f"score_count_mismatch:{len(scores)}!={len(fabs)}+{len(grounded)}"
    if any(s is None for s in scores):
        return False, "score_missing"
    fab_scores = scores[: len(fabs)]
    grounded_scores = scores[len(fabs):]
    fab_below = sum(1 for s in fab_scores if round(float(s), SCORE_DECIMALS) < tau)
    grounded_below = sum(1 for s in grounded_scores if round(float(s), SCORE_DECIMALS) < tau)
    want_fab = int(expect.get("fabrications_below_tau", 0))
    want_grounded = int(expect.get("grounded_below_tau", 0))
    ok = fab_below == want_fab and grounded_below == want_grounded
    detail = (f"fab_below={fab_below}/{len(fabs)}(want {want_fab}) "
              f"grounded_below={grounded_below}/{len(grounded)}(want {want_grounded})")
    return ok, detail


def canary_pairs(canary: dict) -> List[tuple]:
    """`(premise, hypothesis)` 串，順序＝`evaluate_canary` 假設的順序。"""
    pairs = []
    for item in (canary.get("fabrications") or []):
        pairs.append((item["premise"], item["hypothesis"]))
    for item in (canary.get("grounded") or []):
        pairs.append((item["premise"], item["hypothesis"]))
    return pairs


# ---------------------------------------------------------------------------
# 模型載入與推論
# ---------------------------------------------------------------------------

def _load_model() -> None:
    """啟動期載入。任一步失敗只記進 `STATE['load_error']`＋`ready=False`，
    ⛔ 不讓行程直接死掉——`/health` 要能被問到「為什麼不 ready」。
    orchestrator 端看到 `nli_ready=false` 會走降級尺（DSP-033 fail-safe），
    行程死掉則只剩「連不上」這一種無資訊的症狀。"""
    import torch  # noqa: PLC0415 — 見模組 docstring：⛔ 不在模組層 import
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    torch.set_num_threads(TORCH_THREADS)
    STATE["torch"] = torch

    # ⛔ `trust_remote_code=False`（r18 F-7）：這個 repo 沒有自訂程式碼，
    # 開著等於允許權重來源在我們的容器裡執行任意 python。
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_DIR, local_files_only=True, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_DIR, local_files_only=True, trust_remote_code=False)
    model.eval()

    STATE["tokenizer"] = tokenizer
    STATE["model"] = model
    STATE["entail_idx"] = entailment_index(model.config.id2label)


def _verify_fingerprint() -> None:
    """實算目錄指紋並與烤進映像的期望值比對（P2-10）。"""
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from model_fingerprint import directory_fingerprint

    actual = directory_fingerprint(MODEL_DIR)
    STATE["model_sha"] = actual
    # 🔴 期望值沒烤進來 ⇒ **不通過**（⛔ 不視為「沒設定所以跳過」）：
    # 那樣做的話，忘記傳 build-arg 的映像會是綠的，而它正是我們要擋的那一種。
    STATE["sha_ok"] = bool(EXPECTED_MODEL_SHA) and actual == EXPECTED_MODEL_SHA
    if not STATE["sha_ok"]:
        logger.error("nli_model_sha_mismatch expected=%s actual=%s",
                     EXPECTED_MODEL_SHA or "(unset)", actual)


def _score_pair_sync(premise: str, hypothesis: str):
    """單一句對 ⇒ `(score, error)`，兩者恰有一個為 None。⛔ 不批次（P2-5）。"""
    torch = STATE["torch"]
    tokenizer = STATE["tokenizer"]
    model = STATE["model"]
    entail_idx = STATE["entail_idx"]

    n_special = tokenizer.num_special_tokens_to_add(pair=True)
    n_hyp = len(tokenizer.encode(hypothesis, add_special_tokens=False))
    if hypothesis_too_long(n_hyp, n_special):
        return None, ERR_HYPOTHESIS_TOO_LONG

    enc = tokenizer(
        premise,
        hypothesis,
        truncation="only_first",      # r18 F-8：只砍 premise，⛔ 不動 hypothesis
        max_length=MAX_LENGTH,
        return_tensors="pt",
    )
    with torch.no_grad():
        logits = model(**enc).logits
    probs = torch.softmax(logits, dim=-1)[0]
    return round(float(probs[entail_idx].item()), SCORE_DECIMALS), None


def _score_all_sync(pairs: List[tuple]) -> List[Any]:
    """逐對推論；每格是 float 或 `{"error": ...}`。"""
    out: List[Any] = []
    for premise, hypothesis in pairs:
        try:
            score, err = _score_pair_sync(premise, hypothesis)
        except Exception as exc:  # noqa: BLE001 — 單對失敗 ⛔ 不拖垮整批
            # ⛔ **不用 `logger.exception`**（r18 F-12 的同一條紀律）：traceback 與
            # 例外訊息會把送進來的句子印出來——tokenizer 的錯誤訊息就常帶原字串，
            # 而那正是知識庫原文與要給使用者看的句子。只留型別名。
            logger.error("nli_score_pair_failed type=%s", type(exc).__name__)
            out.append({"error": "score_failed"})
            continue
        out.append({"error": err} if err else score)
    return out


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def _startup() -> None:
    try:
        canary = json.loads(open(CANARY_PATH, encoding="utf-8").read())
        STATE["tau"] = float(canary.get("tau", 0.4))
    except Exception as exc:  # noqa: BLE001
        STATE["load_error"] = f"canary_load_failed:{type(exc).__name__}"
        logger.error("nli_canary_load_failed: %s", type(exc).__name__)
        return

    try:
        _verify_fingerprint()
    except Exception as exc:  # noqa: BLE001
        STATE["load_error"] = f"fingerprint_failed:{type(exc).__name__}"
        logger.error("nli_fingerprint_failed: %s", type(exc).__name__)
        return

    try:
        _load_model()
    except Exception as exc:  # noqa: BLE001
        STATE["load_error"] = f"model_load_failed:{type(exc).__name__}"
        logger.error("nli_model_load_failed: %s", type(exc).__name__)
        return

    scores_raw = await asyncio.to_thread(_score_all_sync, canary_pairs(canary))
    scores = [s if isinstance(s, (int, float)) else None for s in scores_raw]
    ok, detail = evaluate_canary(canary, scores)
    STATE["canary_ok"] = ok
    STATE["canary_detail"] = detail
    logger.info("nli_canary ok=%s %s model_sha=%s sha_ok=%s",
                ok, detail, STATE["model_sha"][:12], STATE["sha_ok"])


def _ready() -> bool:
    return bool(STATE["canary_ok"]) and bool(STATE["sha_ok"])


@app.get("/health")
async def health() -> dict:
    """⛔ 只回三個欄位（DSP-033）：`nli_ready` 為假時，`canary_ok` 為真即代表
    是指紋那一關沒過——診斷得出來，卻不必多開一個欄位。"""
    return {
        "nli_ready": _ready(),
        "model_sha": STATE["model_sha"],
        "canary_ok": bool(STATE["canary_ok"]),
    }


@app.post("/nli")
async def nli(request: NliRequest) -> dict:
    global _inflight
    if not _ready():
        return JSONResponse(status_code=503, content={"error": "not_ready"})
    if _inflight >= _MAX_INFLIGHT + _MAX_QUEUE:
        # 快速 503：⛔ 不排隊等死（client 逾時＝對數×400 ms，排不到就是排不到）
        return JSONResponse(status_code=503, content={"error": "busy"})

    pairs = [(p.premise, p.hypothesis) for p in request.pairs]
    _inflight += 1
    try:
        scores = await asyncio.to_thread(_score_all_sync, pairs)
    finally:
        _inflight -= 1
    return {
        "scores": scores,
        "model_sha": STATE["model_sha"],
        # ⚠️ **hint**：權威 τ 在 orchestrator 的 `config/agent_verifier_rules.json`
        # （`nli_tau`，隨 `rules_sha` 版本化）。這裡回的是映像自己 canary 用的值，
        # 供部署時核對兩邊有沒有走岔，⛔ 不是 Verifier 的判定門檻。
        "tau_hint": STATE["tau"],
    }


@app.exception_handler(RequestValidationError)
async def _on_validation_error(request: Request, exc: RequestValidationError):
    """⛔ 只回代碼（r18 F-12）：pydantic 的預設 422 body 會把**送進來的欄位值**
    原樣回吐，而送進來的正是使用者的問句與知識庫原文。"""
    return JSONResponse(status_code=422, content={"error": "invalid_request"})


@app.exception_handler(Exception)
async def _on_unhandled(request: Request, exc: Exception):
    """同上：例外訊息常含輸入片段（tokenizer 的錯誤訊息會印原字串）。

    ⛔ **不用 `logger.exception`**：回應只回代碼、log 卻把整段 traceback 連同
    輸入印出來的話，這道防護等於只擋了走前門的那一半。只留型別名。
    """
    logger.error("nli_unhandled_error type=%s", type(exc).__name__)
    return JSONResponse(status_code=500, content={"error": "internal_error"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("API_PORT", "8000")),
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
