import json,urllib.request,time,math,statistics
exec(open('refresh.py').read().split("res={}")[0].replace("H={s:get(s)","H0={s:get(s)").replace("json.dump(H,open","0 and json.dump(H,open").replace("H['_saved']","H0['_saved']"))
H=json.load(open(D+'history.json'));lab=json.load(open(D+'lab.json'))
def hourly(sym,start):
    out=[];end=int(time.time()*1000)
    while True:
        r=json.load(urllib.request.urlopen(f'https://data-api.binance.vision/api/v3/klines?symbol={sym}&interval=1h&limit=1000&endTime={end}',timeout=30))
        if not r:break
        out=r+out;end=r[0][0]-1
        if r[0][0]<=start-30*86400000 or len(r)<1000:break
    return [[k[0],float(k[2]),float(k[3]),float(k[4]),float(k[5])] for k in out]
def sma(a,n):return [None if i<n-1 else sum(a[i-n+1:i+1])/n for i in range(len(a))]
def vfi(d,L=130):
    c=[k[4] for k in d];h=[k[2] for k in d];l=[k[3] for k in d];v=[k[5] for k in d];n=len(c)
    tp=[(h[i]+l[i]+c[i])/3 for i in range(n)]
    inter=[0]+[math.log(tp[i])-math.log(tp[i-1]) for i in range(1,n)]
    vint=[None if i<30 else statistics.pstdev(inter[i-29:i+1]) for i in range(n)]
    va=sma(v,L);vave=[None]+va[:-1]
    vcp=[0]*n
    for i in range(1,n):
        if vint[i] is None or vave[i] is None:continue
        cut=0.2*vint[i]*c[i];vc=min(v[i],vave[i]*2.5);mf=tp[i]-tp[i-1]
        vcp[i]=vc if mf>cut else -vc if mf<-cut else 0
    s=sma(vcp,L);raw=[None if s[i] is None or vave[i] is None else s[i]/vave[i] for i in range(n)]
    out=[None]*n;e=None
    for i in range(n):
        if raw[i] is None:continue
        e=raw[i] if e is None else 0.5*raw[i]+0.5*e;out[i]=e
    return out
def nodes(hr,lo,hi_,bins=50):
    step=(hi_-lo)/bins or 1;vol=[0]*bins
    for k in hr:
        b=min(bins-1,int(((k[1]+k[2]+k[3])/3-lo)/step));vol[b]+=k[4]
    m=sum(vol)/bins;hv=[];lv=[]
    for i in range(1,bins-1):
        if vol[i]>=vol[i-1] and vol[i]>=vol[i+1] and vol[i]>=1.2*m:hv.append(lo+(i+.5)*step)
        if vol[i]<=vol[i-1] and vol[i]<=vol[i+1] and vol[i]<=0.5*m:lv.append(lo+(i+.5)*step)
    return hv,lv
def profile(hr,lo,hi_,bins=50):
    step=(hi_-lo)/bins or 1;vol=[0]*bins
    for k in hr:
        b=min(bins-1,int(((k[1]+k[2]+k[3])/3-lo)/step));vol[b]+=k[4]
    poc=max(range(bins),key=lambda i:vol[i]);tot=sum(vol);a=b=poc;acc=vol[poc]
    while acc<0.7*tot and (a>0 or b<bins-1):
        up=vol[b+1] if b<bins-1 else -1;dn=vol[a-1] if a>0 else -1
        if up>=dn:b+=1;acc+=up
        else:a-=1;acc+=dn
    return lo+(poc+.5)*step,lo+(a)*step,lo+(b+1)*step
for s,d in H.items():
    if s.startswith('_'):continue
    hr=hourly(s,d[0][0]);c=[k[4] for k in d];n=len(d)
    v=vfi(d);vp=[];prev=None
    for i in range(n):
        v_=v[i];p=prev;prev=v_
        vp.append(None if v_ is None or p is None else (p<=0<v_,p>=0>v_))
    pos=[];st=False
    for i in range(n):
        if vp[i] and vp[i][0]:st=True
        elif vp[i] and vp[i][1]:st=False
        pos.append(st)
    # volume profile: previous 30 days of hourly bars up to close of day i
    pa=[];pb=[];sa=sb=False;lv=None;ph=[];pl=[];sh=sl=False;hlev=0;llev=0
    for i in range(n):
        end=d[i][0]+86400000;win=[k for k in hr if end-30*86400000<=k[0]<end]
        if len(win)<300:pa.append(False);pb.append(False);ph.append(False);pl.append(False);continue
        poc,val,vah=profile(win,min(k[2] for k in win),max(k[1] for k in win))
        # A: acceptance above value area
        if c[i]>vah:sa=True
        elif c[i]<poc:sa=False
        # B: bounce from below value area back to POC
        if c[i]<val:sb=True
        elif c[i]>=poc:sb=False
        pa.append(sa);pb.append(sb)
        hv,lvn=nodes(win,min(k[2] for k in win),max(k[1] for k in win))
        below=[x for x in hv if x<=c[i]];above=[x for x in hv if x>c[i]]
        if sh:
            if c[i]<hlev*0.99 or (above and False) or any(x<=c[i] and x>hlev*1.01 for x in hv):sh=False
        elif below and i>0 and c[i]>c[i-1]:
            b0=max(below)
            if c[i]<=b0*1.005:sh=True;hlev=b0
        ph.append(sh)
        if sl:
            if c[i]<llev or any(x<=c[i] and x>llev*1.005 for x in hv):sl=False
        elif i>0:
            cr=[x for x in lvn if c[i-1]<x<=c[i]]
            if cr:sl=True;llev=max(cr)
        pl.append(sl)
    now_=hr[-1][0]+3600000;win=[k for k in hr if now_-30*86400000<=k[0]<now_]
    poc,val,vah=profile(win,min(k[2] for k in win),max(k[1] for k in win));hv,lvn=nodes(win,min(k[2] for k in win),max(k[1] for k in win))
    vv=[x for x in v if x is not None];vn=vv[-1];vp_=vv[-2]
    lab['coins'][s]['now']=dict(price=c[-1],poc=poc,val=val,vah=vah,hvn=[round(x,4) for x in hv],lvn=[round(x,4) for x in lvn],vfi=vn,vfi_prev=vp_,vfi_days=len(vv),px=hr[-1][3])
    r=lab['coins'][s]['res'];r['vfi']=run(c,pos);r['vpa']=run(c,pa);r['vpb']=run(c,pb);r['hvn']=run(c,ph);r['lvn']=run(c,pl)
    print(s,len(hr),{k:(round(r[k]['ret'],1),r[k]['trades']) for k in('vfi','vpa','vpb','hvn','lvn','hold')})
import datetime
lab['generated']=datetime.datetime.utcnow().isoformat()+'Z'
json.dump(lab,open(D+'lab.json','w'))
