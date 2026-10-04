import json, sys
S=".kiro/specs/knowledge-outline-and-intent-architecture/verification/"
d=json.load(open("rag-orchestrator/canon/jgb.json"))
done=set()
for n in ("20261004-p923-write.json","20261004-p924-write.json","20261004-p925-write.json"):
    done|={x["id"] for x in json.load(open(S+n))["fines"]}
MAXS=int(sys.argv[1]) if len(sys.argv)>1 else 70
batches=[];cur=[];cs=0;shelf=None
for c in d["coarses"]:
    fs=[f for f in c["fines"] if f["id"] not in done and (f.get("reviewed_by") or "").strip()]
    if not fs: continue
    n=sum(len(f["content_units"]) for f in fs)
    sh=c["id"][0]
    # 粗目不拆；超過上限的單一粗目自成一批
    if cur and (cs+n>MAXS):
        batches.append(cur);cur=[];cs=0
    cur.append((c["id"],[f["id"] for f in fs],n));cs+=n;shelf=sh
if cur: batches.append(cur)
out=[]
for i,b in enumerate(batches,1):
    ids=[x for _,fs,_ in b for x in fs]
    out.append({"batch":f"B{i:02d}","coarses":[c for c,_,_ in b],"fines":ids,"sentences":sum(n for *_,n in b)})
json.dump(out,open(sys.argv[2],"w"),ensure_ascii=False,indent=1)
print(len(out),"批")
for b in out: print(b["batch"],len(b["fines"]),"條",b["sentences"],"句",",".join(b["coarses"]))
print("合計",sum(len(b["fines"]) for b in out),sum(b["sentences"] for b in out))
