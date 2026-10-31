import json,statistics
from pathlib import Path
r=Path(__file__).parent/'results'
a=json.loads((r/'benchmark-1000000.json').read_text());b=json.loads((r/'benchmark-10000000.json').read_text())
def cells(d):
 res={}
 for x in d['requests']:
  role='hot' if x['tenant']==1 else 'second' if x['tenant']==2 else 'small' if x['tenant']==(10 if d['scale']==1000000 else 100) else 'middle'
  key=':'.join([role,x['family'],x['grain'],x['range'],x['mode']]);res.setdefault(key,[]).append(x['ms'])
 return res
ca,cb=cells(a),cells(b);out=[]
for key in ca:
 if key not in cb:continue
 av,bv=sorted(ca[key]),sorted(cb[key]);p=lambda x:x[min(len(x)-1,int(.95*len(x)))]
 ratios={'p50':statistics.median(bv)/statistics.median(av),'p95':p(bv)/p(av),'max':max(bv)/max(av)}
 out.append({'case':key,'latency_1m_p50':statistics.median(av),'latency_10m_p50':statistics.median(bv),'ratio':ratios,'status':'PASS' if max(ratios.values())<2 else 'FAIL'})
d={'status':'PASS' if all(x['status']=='PASS' for x in out) else 'FAIL','cases':out,'worst_ratio':max(max(x['ratio'].values()) for x in out),'conditions':'Same seeded distribution algorithm, 1M/10 tenants vs 10M/100 tenants; largest tenant grows 10x; small tenant maps 10 to100; warmed HTTP at same 1/4 client concurrency and limits. Per-case p50/p95/max compared; short trials do not establish statistical confidence.'}
(r/'growth.json').write_text(json.dumps(d,indent=2));print('Growth',d['status'],'worst',d['worst_ratio'])
