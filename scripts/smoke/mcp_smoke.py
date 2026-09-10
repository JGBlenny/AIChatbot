# 本機煙霧＋劇本測試：pm 身分經 /mcp 打 agent.turn，多回合、逐回合抓 trace（一次性，⛔ 不進 repo）。
# 用法：cat key.txt mcp_smoke.py | docker compose … run --rm -T -e SMOKE_SCENARIOS_JSON="$(cat scenarios.json)" rag-orchestrator \
#        python3 -c "import sys; k=sys.stdin.readline().strip(); exec(compile(sys.stdin.read(),'smoke','exec'))"
# key 只從 stdin 第一行進變數 k，⛔ 不進 argv／env／log。輸出每回合一行 JSON（stdout），由呼叫端存檔。
import asyncio, json, os, sys, inspect, time, httpx

BASE = os.environ.get("SMOKE_BASE", "http://smoke-rag:8100")
URL = BASE + "/mcp"
import base64 as _b64
SCEN = json.loads((_b64.b64decode(os.environ["SMOKE_SCEN_B64"]).decode("utf-8")) if os.environ.get("SMOKE_SCEN_B64") else (os.environ.get("SMOKE_SCENARIOS_JSON") or "[]"))
if os.environ.get("SMOKE_Q"):
    SCEN = [{"session": "adhoc", "title": "adhoc", "turns": [{"q": os.environ["SMOKE_Q"], "expect": ""}]}]

def ident(session_id):
    return json.dumps({"mode": "b2b", "target_user": "property_manager", "vendor_id": 4,
                       "role_id": "20151", "user_id": "12291", "session_id": session_id})

from mcp import ClientSession
from mcp.client import streamable_http as sh

def _open(headers):
    sig = inspect.signature(sh.streamable_http_client).parameters
    if "headers" in sig:
        return sh.streamable_http_client(URL, headers=headers)
    if "http_client" in sig:
        return sh.streamable_http_client(URL, http_client=httpx.AsyncClient(headers=headers, timeout=120))
    raise SystemExit(f"unknown streamable_http_client signature: {list(sig)}")

def _text(res):
    return "\n".join(getattr(c, "text", "") for c in (getattr(res, "content", None) or []) if getattr(c, "text", None))

async def fetch_trace(headers, trace_id):
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{BASE}/api/v1/agent/trace/{trace_id}", headers=headers)
            if r.status_code != 200:
                return {"trace_http": r.status_code}
            t = r.json()
            keep = {}
            for key in ("kind", "handoff_reason", "miss_kind", "candidate_ids", "tool_calls", "cited", "verifier_rejects",
                        "verifier_reasons", "outline_sha", "llm_calls", "attempts", "tools_called", "refs"):
                if key in t: keep[key] = t[key]
            if not keep: keep = {"trace_keys": sorted(t.keys())[:25]}
            return keep
    except Exception as e:  # noqa: BLE001
        return {"trace_error": type(e).__name__}

async def run_session(sc):
    sid = f"smoke-{sc['session']}-{int(time.time())%100000}"
    headers = {"X-API-Key": k, "X-JGB-Identity": ident(sid)}  # noqa: F821
    async with _open(headers) as ctx:
        async with ClientSession(ctx[0], ctx[1]) as s:
            await s.initialize()
            tools = await s.list_tools(); names = sorted(t.name for t in tools.tools)
            print(json.dumps({"session": sc["session"], "event": "tools", "n": len(names), "names": names,
                              "has_agent_turn": "agent.turn" in names}, ensure_ascii=True), flush=True)
            if "agent.turn" not in names:
                return
            last_qr = []
            for i, turn in enumerate(sc["turns"], 1):
                t0 = time.time()
                if "reply" in turn:  # 機器值回覆：從上一回合 quick_replies 挑前綴相符的 value（形狀由 W3 定，這裡容錯多種鍵名）
                    cands = [(q.get("value") or q.get("data") or q.get("text") or q) if isinstance(q, dict) else q for q in (last_qr or [])]
                    hit = [c for c in cands if isinstance(c, str) and c.startswith(turn["reply"])]
                    turn = dict(turn, q=hit[0] if hit else turn["reply"])
                try:
                    _args = {"message": turn["q"]}
                    _el = turn.get("context") or (sc.get("context") if turn is sc["turns"][0] else None)
                    if _el: _args["context"] = _el
                    for _k in ("image_urls", "file_urls", "attachment_purpose"):
                        if turn.get(_k) is not None: _args[_k] = turn[_k]
                    res = await s.call_tool("agent.turn", _args)
                    txt = _text(res); rec = {"is_error": bool(getattr(res, "isError", False))}
                    try:
                        d = json.loads(txt)
                        rec.update({"answer": d.get("answer"), "kind": d.get("kind"), "handoff": d.get("handoff"),
                                    "quick_replies": d.get("quick_replies"), "outcome": d.get("outcome"), "session_expired": d.get("session_expired"), "trace_id": d.get("trace_id")})
                        last_qr = d.get("quick_replies") or []
                    except Exception:
                        rec["raw"] = txt[:800]
                except Exception as e:  # noqa: BLE001
                    rec = {"exception": f"{type(e).__name__}: {str(e)[:300]}"}
                rec.update({"session": sc["session"], "turn": i, "q": turn["q"], "expect": turn.get("expect", ""),
                            "latency_s": round(time.time() - t0, 1)})
                if rec.get("trace_id"):
                    rec["trace"] = await fetch_trace(headers, rec["trace_id"])
                print(json.dumps(rec, ensure_ascii=True), flush=True)

async def main():
    for sc in SCEN:
        try:
            await run_session(sc)
        except Exception as e:  # noqa: BLE001
            import traceback as _tb; _tb.print_exc()
            print(json.dumps({"session": sc["session"], "session_error": f"{type(e).__name__}: {str(e)[:400]}"}, ensure_ascii=True), flush=True)

asyncio.run(main())
