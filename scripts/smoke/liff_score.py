# -*- coding: utf-8 -*-
import json,re,sys
def load(f): return [json.loads(l) for l in open(f) if l.strip() and '"turn"' in l]
leak=re.compile(r'estate_ref|estate_id|emergency_status|confirmation token|confirm\.response|（1）|（2）|＝1|＝2|=1\b|=2\b|設為 ?[12]|急迫值|結束鈕')
photo=re.compile(r'照片|上傳')
def score(rows,label):
    cards=[(r['session'],r['turn']) for r in rows if re.search(r'confirm_submit:[0-9a-f]{16}',json.dumps(r.get('quick_replies') or ''))]
    built=[(r['session'],re.search(r'單號 ?(\d+)',r['answer']).group(1)) for r in rows if re.search(r'單號 ?\d+',r.get('answer') or '')]
    lk=[(r['session'],r['turn'],leak.search(r['answer']).group()) for r in rows if leak.search(r.get('answer') or '')]
    ph=[(r['session'],r['turn']) for r in rows if photo.search(r.get('answer') or '')]
    ho=[r['session'] for r in rows if r.get('handoff')]
    lat=sorted(r.get('latency_s') or 0 for r in rows)
    l3s={r['session'] for r in rows if r['session'].startswith('L3')}
    print(f"{label}: turns {len(rows)} | L3 sessions w/ card {len({s for s,_ in cards if s.startswith('L3')})}/{len(l3s)} | cards {len(cards)} | builds {len(built)} {built} | leaks {len(lk)} {lk} | photo {len(ph)} {ph} | handoff {ho} | p50 {lat[len(lat)//2]:.1f} p95 {lat[int(len(lat)*0.95)-1]:.1f}")
old=load(sys.argv[1]); new=load(sys.argv[2])
score(old,'OLD'); score(new,'NEW')
print('--- NEW turns')
for r in new:
    c='card' if re.search(r'confirm_submit:[0-9a-f]{16}',json.dumps(r.get('quick_replies') or '')) else '    '
    print(r['session'],r['turn'],c,'|',(r.get('answer') or '')[:120].replace('\n',' '))
