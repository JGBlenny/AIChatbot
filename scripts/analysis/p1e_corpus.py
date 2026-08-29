#!/usr/bin/env python3
"""P1e-1 盲標語料產生器——**隔離由構造保證**（協議見 p1e-labeling-protocol.md）。

⚠️ 每列只輸出 `id \t question_summary \t answer`，⛔ **不含**：
   Face／category→Face mapping／gate／requires_instance_reference／
   現行 routing／form_id／api_config／action_type／P1b 結果／
   哪些 row 已被 machine 判 instance。
⇒ 標註者即使讀了語料檔，也讀不到 withheld 清單上的任何一項——
  這比「相信代理沒有去查」更強。

母體＝P1b census 判 UNKNOWN 的 839 筆（34 筆 deterministic ⛔ 不交給 labeler 再確認）。
"""
import json
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
BATCHES = 3


def main(out_dir):
    census = json.load(open(os.path.join(REPO, "scripts/analysis/p1b_census.json"), encoding="utf-8"))
    ids = [r["knowledge_id"] for r in census if r["verdict"] == "UNKNOWN"]
    sql = ("SELECT COALESCE(json_agg(json_build_object('id',id,'q',question_summary,"
           "'a',left(COALESCE(answer,''),420))),'[]')::text FROM knowledge_base WHERE id IN (%s)"
           % ",".join(map(str, ids)))
    out = subprocess.run(["docker", "exec", "aichatbot-postgres", "psql", "-U", "aichatbot",
                          "-d", "aichatbot_admin", "-t", "-A", "-c", sql],
                         capture_output=True, text=True, timeout=120)
    rows = sorted(json.loads(out.stdout.strip()), key=lambda d: d["id"])
    if len(rows) != len(ids):
        print(f"❌ 取回 {len(rows)} 筆 ≠ 預期 {len(ids)} 筆——大聲失敗")
        return 1
    os.makedirs(out_dir, exist_ok=True)
    size = len(rows) // BATCHES + 1
    for i in range(BATCHES):
        chunk = rows[i * size:(i + 1) * size]
        path = os.path.join(out_dir, f"batch{i + 1}.txt")
        with open(path, "w", encoding="utf-8") as fh:
            for d in chunk:
                fh.write(f"{d['id']}\t{d['q']}\t{(d['a'] or '').replace(chr(10), ' ')}\n")
        print(f"batch{i+1}: {len(chunk)} 筆 → {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "build/p1e")))
