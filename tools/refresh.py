import json,urllib.request,time,datetime,sys
D='/downloads/golddash/src/data/'
old=json.load(open(D+'lab.json'))
def get(sym):
    out=[];end=int(time.time()*1000)
    while len(out)<365:
        u=f'https://data-api.binance.vision/api/v3/klines?symbol={sym}&interval=1d&limit=1000&endTime={end}'
        r=json.load(urllib.request.urlopen(u,timeout=30))
        if not r:break
        out=r+out;end=r[0][0]-1
        if len(r)<1000:break
    now=int(time.time()*1000)
    out=[k for k in out if k[6]<now]  # drop forming candle
    return [[k[0],float(k[1]),float(k[2]),float(k[3]),float(k[4]),float(k[5])] for k in out][-365:]
H={s:get(s) for s in ['XAUTUSDT','BNBUSDT','ETHUSDT','SOLUSDT']}
H['_saved']=datetime.datetime.utcnow().isoformat()+'Z'
json.dump(H,open(D+'history.json','w'))
def ema(c,n):
    a=2/(n+1);e=[c[0]]
    for x in c[1:]:e.append(a*x+(1-a)*e[-1])
    return e
def rsi(c,n=14):
    r=[50]*len(c);g=l=0
    for i in range(1,len(c)):
        d=c[i]-c[i-1];u,dn=max(d,0),max(-d,0)
        if i<=n:
            g+=u/n;l+=dn/n
            if i==n:r[i]=100 if l==0 else 100-100/(1+g/l)
        else:
            g=(g*(n-1)+u)/n;l=(l*(n-1)+dn)/n;r[i]=100 if l==0 else 100-100/(1+g/l)
    return r
def run(c,pos):
    fee=old['fee'];eq=1;peak=1;dd=0;trades=[];inp=False;entry=0;expo=0
    for i in range(1,len(c)):
        # position decided at close i-1, held over bar i
        if pos[i-1] and not inp:inp=True;entry=c[i-1]*(1+fee);eq*=(1-fee)
        if not pos[i-1] and inp:
            inp=False;ex=c[i-1]*(1-fee);trades.append(ex/entry-1);eq*=(1-fee)
        if inp:eq*=c[i]/c[i-1];expo+=1
        peak=max(peak,eq);dd=min(dd,eq/peak-1)
    if inp:trades.append(c[-1]*(1-fee)/entry-1)
    w=[t for t in trades if t>0];lo=[t for t in trades if t<=0]
    return dict(ret=(eq-1)*100,trades=len(trades),win=100*len(w)/len(trades) if trades else 0,dd=dd*100,
      pf=(sum(w)/-sum(lo) if lo and sum(lo)<0 else None),avgw=100*sum(w)/len(w) if w else None,avgl=100*sum(lo)/len(lo) if lo else None,expo=100*expo/(len(c)-1))
res={}
for s,d in H.items():
    if s.startswith('_'):continue
    c=[k[4] for k in d];hi=[k[2] for k in d];lw=[k[3] for k in d];n=len(c)
    e1,e2=ema(c,10),ema(c,30);ema_p=[e1[i]>e2[i] for i in range(n)]
    r=rsi(c);rp=[];p=False
    for i in range(n):
        if r[i]<30:p=True
        elif r[i]>50:p=False
        rp.append(p)
    bp=[];p=False
    for i in range(n):
        if i>=20 and c[i]>max(hi[i-20:i]):p=True
        elif i>=10 and c[i]<min(lw[i-10:i]):p=False
        bp.append(p)
    res[s]=dict(days=n,start=d[0][0],end=d[-1][0],res=dict(ema=run(c,ema_p),rsi=run(c,rp),brk=run(c,bp),hold=run(c,[True]*n)))
json.dump(dict(fee=old['fee'],coins=res,generated=H['_saved']),open(D+'lab.json','w'))
for s in res:print(s,res[s]['days'],{k:round(v['ret'],2) for k,v in res[s]['res'].items()},'old',{k:round(v['ret'],2) for k,v in old['coins'][s]['res'].items()})
