#!/usr/bin/env python3
"""可答性判者——直打 Messages API（取代 Workflow 判者；業主 2026-09-06 裁：Workflow 留參考、skill 用 API）。

設計（與 outline-curation.js 等價，差別只在執行形態）：
- 判者互不可見：每個判者＝一個獨立請求，⛔ 不把 v1 傳給 judge2、不把 v1/v2 傳給 judge3。
- schema 強制：`output_config.format = json_schema`（VERDICT_SCHEMA 與 JS 同；`fine_id` enum＝候選 id＋null）。
- 兩種版面（--layout）：
  * `workflow`：system＝promptHead、user＝cellBlock+candidatesBlock+cellTail，**system+user 逐位元等於 `build_judge_prompt`**（unit 守著）
    ⇒ 與 1.5 Workflow 判者看到的字完全相同、可直接和那 44 格合併；代價＝候選每格重送（無共用前綴），11 格約 30 請求 × 7k token。
  * `cached`（預設）：system＝promptHead+candidatesBlock 掛 `cache_control`（rubric＋候選共用前綴）、user＝cellBlock+cellTail；
    內容同、段落順序不同（候選在問句前）⇒ 是**另一版 prompt**，⛔ 不與 workflow 版面的結果混算一致率。
- 續跑：journal jsonl 以 `sha256(system+user)[:16]:<slot>` 為 key，已有 verdict 的判者不再打；中斷重跑只補缺的。
- 成本：逐請求 `usage` 累加；usd 依 `--price-json`（預設 claude-sonnet-5 牌價，來源見 DEFAULT_PRICE）。
- 憑證：`anthropic.Anthropic()` 零參數由 SDK 自行解析（環境變數／ant 登入設定檔）；本腳本 ⛔ 不讀 .env、不印任何環境變數、不把金鑰放進 argv。

輸出 JSON 與 Workflow Reconcile 回傳同形（step/frozenAt/rubricSha/inputsSha/total/agree/agreementRate/
needs_rubric_revision/agentsUsed/labels[]），外加 usage 與 usd，可直接餵 finalize_answerability.py／merge_answerability_batches.py。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

AGREEMENT_THRESHOLD = 0.80  # 2026-09-06 業主裁（原 0.90）；與 outline-curation.js／merge_answerability_batches.py 同值
LABELS = ["answerable", "partial", "no_source", "deliberate_no"]

# claude-api skill 快取表（2026-06-24）：claude-sonnet-5 input $2／output $10 per MTok；cache read 0.1×、cache write 1.25×（5m TTL）
DEFAULT_PRICE = {"model": "claude-sonnet-5", "input": 2.0, "output": 10.0, "cache_read": 0.2, "cache_write_5m": 2.5, "cache_write_1h": 4.0}


def verdict_schema(fine_id_enum: list) -> dict:
    return {
        "type": "object",
        "properties": {
            "cell_id": {"type": "string"},
            "label": {"type": "string", "enum": LABELS},
            "fine_id": {"type": ["string", "null"], "enum": list(fine_id_enum) + [None]},
            "evidence_unit": {"type": ["integer", "null"]},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "provisional": {"type": "boolean", "enum": [True]},
        },
        "required": ["cell_id", "label", "fine_id", "evidence_unit", "confidence", "provisional"],
        "additionalProperties": False,
    }


LAYOUTS = ("cached", "workflow")


def split_prompt(args: dict, cell: dict, layout: str = "cached") -> tuple[str, str]:
    """回 (system_text, user_text)。cached：system 共用可快取；workflow：拼回 build_judge_prompt 的原順序（逐位元相同）。"""
    if layout == "workflow":
        return args["promptHead"], cell["cellBlock"] + args["candidatesBlock"] + cell["cellTail"]
    if layout != "cached":
        raise ValueError(f"未知 layout：{layout}")
    return args["promptHead"] + args["candidatesBlock"], cell["cellBlock"] + cell["cellTail"]


def judge_key(system_text: str, user_text: str, slot: int) -> str:
    return hashlib.sha256((system_text + user_text).encode("utf-8")).hexdigest()[:16] + f":{slot}"


def build_request(model: str, system_text: str, user_text: str, schema: dict, layout: str = "cached") -> dict:
    system_block = {"type": "text", "text": system_text}
    if layout == "cached":
        system_block["cache_control"] = {"type": "ephemeral"}
    return {
        "model": model,
        "max_tokens": 1024,
        "system": [system_block],
        "messages": [{"role": "user", "content": user_text}],
        "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": schema}},
    }


def _usage_dict(usage) -> dict:
    g = lambda k: int(getattr(usage, k, 0) or 0)  # noqa: E731
    cc = getattr(usage, "cache_creation", None)
    w5 = int(getattr(cc, "ephemeral_5m_input_tokens", 0) or 0) if cc is not None else g("cache_creation_input_tokens")
    w1 = int(getattr(cc, "ephemeral_1h_input_tokens", 0) or 0) if cc is not None else 0
    return {"input": g("input_tokens"), "output": g("output_tokens"), "cache_read": g("cache_read_input_tokens"),
            "cache_write_5m": w5, "cache_write_1h": w1}


def usd_of(usage: dict, price: dict) -> float:
    return (usage["input"] * price["input"] + usage["output"] * price["output"] + usage["cache_read"] * price["cache_read"]
            + usage["cache_write_5m"] * price["cache_write_5m"] + usage["cache_write_1h"] * price["cache_write_1h"]) / 1e6  # 不四捨五入：呼叫端決定


class Journal:
    """jsonl：一行一判者。載入時把已有 verdict 的 key 收進 done；append 執行緒安全。"""

    def __init__(self, path: str | None):
        self.path = path
        self.done: dict[str, dict] = {}
        self._lock = threading.Lock()
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    if rec.get("verdict") is not None:
                        self.done[rec["key"]] = rec

    def append(self, rec: dict) -> None:
        with self._lock:
            if self.path:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if rec.get("verdict") is not None:
                self.done[rec["key"]] = rec


def call_judge(client, request: dict) -> tuple[dict | None, dict]:
    """打一次 API；回 (verdict|None, usage)。refusal／非 JSON ⇒ None（no silent caps：由呼叫端記 dropped）。"""
    resp = client.messages.create(**request)
    usage = _usage_dict(getattr(resp, "usage", None))
    if getattr(resp, "stop_reason", None) == "refusal":
        return None, usage
    blocks = getattr(resp, "content", None) or []
    text = next((getattr(b, "text", None) for b in blocks if getattr(b, "type", "text") == "text"), None)
    if not text:
        return None, usage
    try:
        verdict = json.loads(text)
    except json.JSONDecodeError:
        return None, usage
    return verdict, usage


def judge_cell(client, args: dict, cell: dict, model: str, schema: dict, journal: Journal, log, layout: str = "cached") -> dict:
    """judge1、judge2，不一致才 judge3；每個判者獨立請求、prompt 逐位元相同（slot 只進 journal key，不進 prompt）。"""
    system_text, user_text = split_prompt(args, cell, layout)
    request = build_request(model, system_text, user_text, schema, layout)
    verdicts: list = []
    usage_total = {"input": 0, "output": 0, "cache_read": 0, "cache_write_5m": 0, "cache_write_1h": 0}
    calls = 0

    def one(slot: int):
        nonlocal calls
        key = judge_key(system_text, user_text, slot)
        if key in journal.done:
            return journal.done[key]["verdict"]
        v, u = call_judge(client, request)
        calls += 1
        for k in usage_total:
            usage_total[k] += u.get(k, 0)
        journal.append({"key": key, "cell_id": cell["cellId"], "slot": slot, "model": model, "layout": layout, "verdict": v, "usage": u})
        return v

    v1 = one(1)
    v2 = one(2)
    verdicts = [v for v in (v1, v2) if v]
    v3 = None
    if not (v1 and v2 and v1["label"] == v2["label"]):
        v3 = one(3)
        if v3:
            verdicts.append(v3)
    log(f"{cell['cellId']} judges={len(verdicts)} calls={calls}")
    return {"c": cell, "v1": v1, "v2": v2, "v3": v3, "verdicts": verdicts, "usage": usage_total, "calls": calls}


def reconcile(results: list, args: dict, log) -> dict:
    """與 outline-curation.js Reconcile 逐條等價。"""
    agree = 0
    agents_used = 0
    dropped = 0
    labels = []
    for r in results:
        if not r:
            dropped += 1
            continue
        c, v1, v2, v3 = r["c"], r["v1"], r["v2"], r["v3"]
        verdicts = r["verdicts"]
        agents_used += len(verdicts)
        if not v1 or not v2:
            dropped += 1
            log(f"{c['cellId']} skipped（判者結果缺失，no silent caps）")
            continue
        is_agree = v1["label"] == v2["label"]
        if is_agree:
            agree += 1
            final = v1["label"]
            unresolved = False
        elif v3 and v3["label"] in (v1["label"], v2["label"]):
            final = v3["label"]
            unresolved = False
        else:
            final = "no_source"
            unresolved = True
        winner = next((v for v in verdicts if v["label"] == final), v1)
        entry = {"cell_id": c["cellId"], "label": final, "fine_id": winner["fine_id"], "evidence_unit": winner["evidence_unit"],
                 "confidence": winner["confidence"], "provisional": True, "verdicts": verdicts}
        if unresolved:
            entry["unresolved"] = True
        labels.append(entry)
    if dropped:
        log(f"{dropped} 格因判者結果缺失被跳過（no silent caps）")
    total = len(labels)
    rate = agree / total if total else 0.0
    return {"step": "answerability", "frozenAt": args["frozenAt"], "rubricSha": args["rubricSha"], "inputsSha": args["inputsSha"],
            "total": total, "agree": agree, "agreementRate": rate, "needs_rubric_revision": rate < AGREEMENT_THRESHOLD,
            "agentsUsed": agents_used, "labels": labels, "droppedCells": dropped}


def run(args: dict, client, *, model: str, journal: Journal, concurrency: int = 4, price: dict = DEFAULT_PRICE,
        cell_ids: set | None = None, layout: str = "cached", log=print) -> dict:
    schema = verdict_schema(args["fineIdEnum"])
    cells = [c for c in args["cells"] if not cell_ids or c["cellId"] in cell_ids]
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        results = list(pool.map(lambda c: judge_cell(client, args, c, model, schema, journal, log, layout), cells))
    out = reconcile(results, args, log)
    usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write_5m": 0, "cache_write_1h": 0}
    calls = 0
    for r in results:
        if r:
            calls += r["calls"]
            for k in usage:
                usage[k] += r["usage"][k]
    out["usage"] = {**usage, "calls": calls, "model": model, "layout": layout}
    out["usd"] = usd_of(usage, price)
    out["price"] = price
    return out


def _make_client():
    try:
        import anthropic  # noqa: WPS433 — 延遲匯入：unit 測試不需要 SDK
    except ImportError:
        print("[answerability_judge] 缺 anthropic SDK：pip install anthropic（venv；宿主 3.9 不支援 SDK 1.x）", file=sys.stderr)
        raise SystemExit(2)
    try:
        return anthropic.Anthropic()  # 零參數：SDK 自行解析憑證；⛔ 本腳本不碰金鑰
    except Exception as exc:  # noqa: BLE001
        print(f"[answerability_judge] 建立 client 失敗（{type(exc).__name__}）：請在你的 shell 設定 Anthropic 憑證後重跑；本腳本不讀 .env", file=sys.stderr)
        raise SystemExit(2)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--args", required=True, help="answerability_args.py --slim 產出（含 promptHead/candidatesBlock/cells）")
    p.add_argument("--out", required=True, help="結果 JSON（與 Workflow Reconcile 同形）")
    p.add_argument("--journal", required=True, help="判者 jsonl（續跑用；已有 verdict 的 key 不再打）")
    p.add_argument("--model", default=DEFAULT_PRICE["model"])
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--cell-ids", default=None, help="逗號分隔子集")
    p.add_argument("--layout", choices=LAYOUTS, default="cached", help="workflow＝與 1.5 Workflow 判者 prompt 逐位元相同（無共用快取，可與 44 格合併）；cached＝共用快取前綴（另一版 prompt）")
    p.add_argument("--price-json", default=None, help="覆寫牌價 {input,output,cache_read,cache_write_5m,cache_write_1h}（USD/MTok）")
    a = p.parse_args()
    args = json.load(open(a.args, encoding="utf-8"))
    for k in ("promptHead", "candidatesBlock", "cells", "fineIdEnum"):
        if k not in args:
            print(f"[answerability_judge] args 缺 {k}：請用 answerability_args.py --slim 產出", file=sys.stderr)
            return 2
    price = dict(DEFAULT_PRICE)
    if a.price_json:
        price.update(json.load(open(a.price_json, encoding="utf-8")))
    if a.model != price.get("model") and not a.price_json:
        print(f"[answerability_judge] 模型 {a.model} 沒有牌價：請給 --price-json（usd 否則不可信）", file=sys.stderr)
        return 2
    journal = Journal(a.journal)
    if journal.done:
        print(f"[answerability_judge] 續跑：journal 已有 {len(journal.done)} 個判者")
    cell_ids = set(a.cell_ids.split(",")) if a.cell_ids else None
    client = _make_client()
    out = run(args, client, model=a.model, journal=journal, concurrency=a.concurrency, price=price, cell_ids=cell_ids, layout=a.layout)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(f"[answerability_judge] total={out['total']} agree={out['agree']} rate={out['agreementRate']:.3f} "
          f"agents={out['agentsUsed']} calls={out['usage']['calls']} usd={out['usd']} needs_rubric_revision={out['needs_rubric_revision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
