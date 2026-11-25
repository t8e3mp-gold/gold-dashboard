import json
D='/downloads/golddash/src/data/'
H=json.load(open(D+'history.json'));lab=json.load(open(D+'lab.json'));FEE=lab['fee']
def run_exp(c,e,cycles):
    eq=1;peak=1;dd=0;expo=0
    for i in range(1,len(c)):
        de=abs(e[i-1]-(e[i-2] if i>=2 else 0));eq*=(1-FEE*de)
        eq*=1+e[i-1]*(c[i]/c[i-1]-1);expo+=e[i-1]
        peak=max(peak,eq);dd=min(dd,eq/peak-1)
    w=[t for t in cycles if t>0];l=[t for t in cycles if t<=0]
    return dict(ret=(eq-1)*100,trades=len(cycles),win=100*len(w)/len(cycles) if cycles else 0,dd=dd*100,
      pf=(sum(w)/-sum(l) if l and sum(l)<0 else None),avgw=100*sum(w)/len(w) if w else None,avgl=100*sum(l)/len(l) if l else None,expo=100*expo/(len(c)-1))
def dip(d):
    c=[k[4] for k in d];lo=[k[3] for k in d];n=len(c);e=[0]*n;inn=False;ent=0;cyc=[]
    for i in range(n):
        if not inn:
            if i>=30 and c[i]<=1.01*min(lo[i-30:i]):inn=True;ent=c[i]
        else:
            if c[i]>=ent*1.05:inn=False;cyc.append(c[i]/ent-1)
        e[i]=1 if inn else 0
    if inn:cyc.append(c[-1]/ent-1)
    return run_exp(c,e,cyc)
def ladder(d):
    c=[k[4] for k in d];n=len(c);e=[0.0]*n;f=0.0;cost=0.0;cyc=[];start=0
    for i in range(n):
        if i>=20:
            h20=max(c[i-20:i]);tgt=0
            for th,fr in((0.97,1/3),(0.94,2/3),(0.91,1.0)):
                if c[i]<=th*h20:tgt=fr
            if tgt>f+1e-9:
                if f==0:start=i
                cost=(cost*f+c[i]*(tgt-f))/tgt;f=tgt
            elif f>0 and c[i]>=cost*1.04:
                cyc.append(c[i]/cost-1);f=0;cost=0
        e[i]=f
    if f>0:cyc.append(c[-1]/cost-1)
    return run_exp(c,e,cyc)
for s,d in H.items():
    if s.startswith('_'):continue
    r=lab['coins'][s]['res'];r['dip']=dip(d);r['ladder']=ladder(d)
    print(s,{k:(round(r[k]['ret'],1),r[k]['trades'],round(r[k]['dd'],1)) for k in('dip','ladder','hold')})
json.dump(lab,open(D+'lab.json','w'))
