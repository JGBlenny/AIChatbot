import json,sys
src,dst=sys.argv[1],sys.argv[2]
def texts(o):
    m=o.get("message",{})
    if m.get("role")!="assistant":return
    cs=m.get("content")
    if isinstance(cs,str):yield cs;return
    for c in cs or []:
        if c.get("type")=="text":yield c.get("text","")
        elif c.get("type")=="tool_use":
            for v in (c.get("input") or {}).values():
                if isinstance(v,str):yield v
last=None
for line in open(src,encoding="utf-8"):
    try:o=json.loads(line)
    except Exception:continue
    for t in texts(o):
        n=sum(1 for l in t.splitlines() if l.strip().startswith("jgb/") and "｜" in l)
        if n>0: last=(t,n)
if last is None: raise SystemExit("❌ no verdict message with id lines found")
open(dst,"w",encoding="utf-8").write(last[0])
print("wrote",dst,"id-lines",last[1])
