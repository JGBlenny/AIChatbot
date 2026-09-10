# 第四批（line-bot 第二輪劇本 scenarios_lb2.json）自動計分；用法：python3 b4_score.py lb2_r1.jsonl [...]
import json, re, sys, datetime

TODAY = datetime.date.today()
PLUS3 = (TODAY + datetime.timedelta(days=3)).strftime("%Y/%m/%d")
ASK_TARGET = "想處理哪一件事？講名稱或編號就可以。"

def load(p):
    rows = {}
    for line in open(p, encoding="utf-8"):
        d = json.loads(line)
        if "turn" in d:
            rows[(d["session"], d["turn"])] = d
    return rows

A = lambda d: d.get("answer") or ""
card = lambda d: bool(d.get("quick_replies"))
nh = lambda d: d.get("kind") != "handoff"

def score(rows):
    g = lambda s, t: rows.get((s, t), {})
    r = {}
    d = g("lb2-repair", 2); r["V4 物件名單獨一句被認作物件（不問哪一戶、不舉 A棟）"] = bool(d) and "A棟" not in A(d) and not re.search(r"哪一戶", A(d))
    d = g("lb2-repair", 6); r["V1 這戶還有沒有別的單 ⇒ 含 8591"] = bool(d) and "8591" in A(d)
    d = g("lb2-repair", 7); r["H4 改描述 ⇒ 已送出＋指路"] = bool(d) and re.search(r"已送出|無法.*修改", A(d)) is not None and re.search(r"JGB|頁面", A(d)) is not None
    d = g("lb2-bill", 1); r["逾期題講出已逾期天數、不夾工程語"] = bool(d) and "已逾期" in A(d) and not re.search(r"收回|標記到帳", A(d))
    d = g("lb2-bill", 2); r["H5 不回聲確認"] = bool(d) and not re.search(r"是要我|要我.*嗎", A(d))
    d = g("lb2-bill", 3); r[f"V3 延三天 ⇒ 出卡、新到期日={PLUS3}、起算日"] = bool(d) and card(d) and PLUS3 in A(d) and "起算日" in A(d)
    d = g("lb2-bill", 5); r["H5 其他未繳一次答"] = bool(d) and not re.search(r"要我.*嗎", A(d))
    d = g("lb2-bill", 6); r["V2 上次報修修好了沒 ⇒ 不退回開場白"] = bool(d) and nh(d) and ASK_TARGET not in A(d)
    d = g("lb2-conv", 2); r["租客看不看得到 ⇒ 直接答"] = bool(d) and not re.search(r"是要確認|要我.*嗎", A(d))
    d = g("lb2-conv", 3); r["V2 要不要打電話 ⇒ 不退回開場白"] = bool(d) and nh(d) and ASK_TARGET not in A(d)
    d = g("lb2-restart", 1); r["V4 restart 我剛剛問了什麼 ⇒ 沒說過話、不把開場白當使用者"] = bool(d) and re.search(r"還沒有說過|還沒說過|沒有先前|尚未|還沒", A(d)) is not None and not re.search(r"(你|您)剛剛問的是「?想看哪一戶", A(d))
    d = g("lb2-restart", 3); r["V2 有前文要不要打電話 ⇒ 不退回開場白"] = bool(d) and nh(d) and ASK_TARGET not in A(d)
    hand = sum(1 for d in rows.values() if d.get("kind") == "handoff")
    r["0 轉人"] = hand == 0
    return r

for p in sys.argv[1:]:
    rows = load(p); r = score(rows)
    ok = sum(1 for v in r.values() if v)
    print(f"== {p.split('/')[-1]}: {ok}/{len(r)} turns={len(rows)}")
    for k, v in r.items(): print(f"  {'✓' if v else '✗'} {k}")
