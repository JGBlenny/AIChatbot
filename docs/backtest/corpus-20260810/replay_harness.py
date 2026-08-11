#!/usr/bin/env python3
"""把 S3 客服回報逐字稿的「真實多輪對話」原樣重播到本機 rag-orchestrator。

harness 形狀比照 jgb2 HelpAssistantController@chat 實際送出的 payload：
mode=b2b、target_user=property_manager、帶 role_id/user_id、不帶 vendor_id。
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(BASE, "reports")
OUT = os.path.join(BASE, os.environ.get("OUTDIR", "replay_out"))
API = "http://localhost:8100/api/v1/message"
RUN_TAG = sys.argv[1] if len(sys.argv) > 1 else "bt0810"

os.makedirs(OUT, exist_ok=True)


def parse(path):
    text = open(path, encoding="utf-8").read()

    def field(label):
        m = re.search(r"- %s：(.*)" % label, text)
        return m.group(1).strip() if m else ""

    role = re.search(r"role_id:\s*([0-9-]+)", text)
    desc = ""
    m = re.search(r"## 問題描述\n+(.*?)\n+## ", text, re.S)
    if m:
        desc = m.group(1).strip()

    turns = []
    body = text.split("## 對話逐字稿", 1)[1] if "## 對話逐字稿" in text else ""
    # 逐字稿由 **使用者：** / **智能助手：** 交錯分段
    parts = re.split(r"\*\*(使用者|智能助手)：\*\*", body)
    i = 1
    while i + 1 < len(parts) + 1 and i < len(parts):
        speaker = parts[i]
        content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        turns.append({"speaker": speaker, "text": content})
        i += 2

    return {
        "file": os.path.basename(path),
        "time": field("回報時間"),
        "user_id": field("回報人 user_id"),
        "role_name": field("團隊/角色"),
        "role_id": role.group(1) if role else None,
        "page": field("頁面"),
        "orig_session": field("session_id"),
        "desc": desc,
        "turns": turns,
    }


def ask(message, session_id, role_id, user_id):
    payload = {
        "message": message,
        "mode": "b2b",
        "target_user": "property_manager",
        "session_id": session_id,
    }
    if role_id and role_id != "-":
        payload["role_id"] = str(role_id)
    if user_id:
        payload["user_id"] = str(user_id)
    req = urllib.request.Request(
        API,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": "HTTP %s" % e.code, "body": e.read().decode()[:500],
                "elapsed": round(time.time() - t0, 1)}
    except Exception as e:
        return {"error": repr(e), "elapsed": round(time.time() - t0, 1)}
    return {
        "answer": data.get("answer") or data.get("message") or "",
        "intent": data.get("intent_name"),
        "confidence": data.get("confidence"),
        "sources": [s.get("question_summary") or s.get("question")
                    for s in (data.get("sources") or [])][:3],
        "elapsed": round(time.time() - t0, 1),
    }


def replay(case):
    idx, rec = case
    user_turns = [t["text"] for t in rec["turns"] if t["speaker"] == "使用者"]
    sid = "%s_%02d_%s" % (RUN_TAG, idx, rec["file"][:15])
    out = dict(rec)
    out["replay_session"] = sid
    out["replay"] = []
    for n, msg in enumerate(user_turns, 1):
        res = ask(msg, sid, rec["role_id"], rec["user_id"])
        out["replay"].append({"turn": n, "user": msg, **res})
        print("  [%02d/T%d] %s -> %s" % (idx, n, msg[:28].replace("\n", " "),
                                         (res.get("answer") or res.get("error", ""))[:60].replace("\n", " ")),
              flush=True)
    with open(os.path.join(OUT, "%02d_%s.json" % (idx, rec["file"][:-3])), "w",
              encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


def main():
    files = []
    for root, _, names in os.walk(REPORTS):
        for n in sorted(names):
            if n.endswith(".md"):
                files.append(os.path.join(root, n))
    files.sort(key=os.path.basename)
    recs = [parse(p) for p in files]
    cases = [(i, r) for i, r in enumerate(recs, 1)]
    only = os.environ.get("ONLY")
    if only:
        want = {int(x) for x in only.split(",")}
        cases = [c for c in cases if c[0] in want]
    print("replaying %d cases (%d user turns)" % (
        len(cases), sum(len([t for t in r['turns'] if t['speaker'] == '使用者']) for _, r in cases)))
    with ThreadPoolExecutor(max_workers=int(os.environ.get("WORKERS", "4"))) as ex:
        list(ex.map(replay, cases))
    print("done ->", OUT)


if __name__ == "__main__":
    main()
