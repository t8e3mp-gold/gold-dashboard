import React, { useCallback, useEffect, useState } from 'react';
import { BarChart, Callout, Caption, Closing, Facts, FileCard, Group, Header, LineChart, Link, NavLink, RangeChart, Route, Routes, Row, Rows } from '@instinct/files';

import { VolumeProfile } from './vp';
import { Radar } from './radar';
import { Signal } from './signal';
import { Research } from './research';
import { Studio } from './studio';
import { TVNote, History, Journal, Ideas, Rules, Paper, Lab } from './pages';
const API = 'https://data-api.binance.vision/api/v3/klines';
const ASSETS = [
    { path: 'xaut', sym: 'XAUTUSDT', name: 'الذهب (XAUT)', note: 'توكن ذهب، السعر بالدولار USDT' },
    { path: 'bnb', sym: 'BNBUSDT', name: 'BNB', note: '' },
    { path: 'eth', sym: 'ETHUSDT', name: 'ETH', note: '' },
    { path: 'sol', sym: 'SOLUSDT', name: 'SOL', note: '' },
];

type Candle = { t: number; o: number; h: number; l: number; c: number; v: number };
type Info = {
    sym: string; name: string; note: string; price: number; chg: number; lo: number; hi: number; poc: number;
    path: string; sup: number[]; res: number[]; h24: number; l24: number; qv: number; rsi: number; ema10: number; ema30: number; w: Candle[]; prof: number[]; step: number; lo0: number; recent: Candle[]; atr: number; vol24: number; closes: number[]; days: string[]; rets: number[];
};

async function candles(sym: string, interval: string, limit: number): Promise<Candle[]> {
    const r = await fetch(`${API}?symbol=${sym}&interval=${interval}&limit=${limit}`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const rows: any[][] = await r.json();
    return rows.map(k => ({ t: +k[0], o: +k[1], h: +k[2], l: +k[3], c: +k[4], v: +k[5] }));
}

function analyse(a: typeof ASSETS[number], d: Candle[], h: Candle[]): Info {
    const last = d[d.length - 1];
    const price = last.c;
    const prev = d[d.length - 2];
    const chg = (price / prev.c - 1) * 100;
    const win = d.slice(-30);
    const lo = Math.min(...win.map(x => x.l));
    const hi = Math.max(...win.map(x => x.h));
    const sup = [...new Set(win.map(x => x.l).filter(x => x < price))].sort((x, y) => y - x).slice(0, 3);
    const res = [...new Set(win.map(x => x.h).filter(x => x > price))].sort((x, y) => x - y).slice(0, 3);
    const tr = d.slice(-14).map((x, i, arr) => {
        const pc = (d[d.length - 14 + i - 1] ?? x).c;
        return Math.max(x.h - x.l, Math.abs(x.h - pc), Math.abs(x.l - pc));
    });
    const atr = tr.reduce((s, x) => s + x, 0) / tr.length;
    const hr = h.slice(-24).map((x, i, arr) => i === 0 ? 0 : Math.log(x.c / arr[i - 1].c)).slice(1);
    const m = hr.reduce((s, x) => s + x, 0) / hr.length;
    const vol24 = Math.sqrt(hr.reduce((s, x) => s + (x - m) ** 2, 0) / (hr.length - 1)) * Math.sqrt(24) * 100;
    const bins = 40, step = (hi - lo) / bins || 1;
    const prof = new Array(bins).fill(0);
    h.slice(-720).forEach(x => { const tp = (x.h + x.l + x.c) / 3; prof[Math.min(bins - 1, Math.max(0, Math.floor((tp - lo) / step)))] += x.v; });
    const poc = lo + (prof.indexOf(Math.max(...prof)) + 0.5) * step;
    const closes = win.map(x => x.c);
    const days = win.map(x => new Date(x.t).toLocaleDateString('ar-EG', { day: 'numeric', month: 'short' }));
    const rets = closes.slice(1).map((x, i) => x / closes[i] - 1);
    const ema = (n: number) => { const k = 2 / (n + 1); return closes.slice(1).reduce((e, x) => x * k + e * (1 - k), closes[0]); };
    const hc = h.slice(-15).map(x => x.c); let g = 0, ls = 0;
    for (let i = 1; i < hc.length; i++) { const df = hc[i] - hc[i - 1]; if (df > 0) g += df; else ls -= df; }
    const rsi = ls === 0 ? 100 : 100 - 100 / (1 + g / ls);
    const l24 = Math.min(...h.slice(-24).map(x => x.l)), h24 = Math.max(...h.slice(-24).map(x => x.h));
    const qv = h.slice(-24).reduce((s2, x) => s2 + x.v * x.c, 0);
    return { path: a.path, h24, l24, qv, rsi, ema10: ema(10), ema30: ema(30), w: h.slice(-720), prof, step, lo0: lo, recent: d.slice(-8, -1).reverse(), sym: a.sym, name: a.name, note: a.note, price, chg, lo, hi, poc, sup, res, atr, vol24, closes, days, rets };
}

function corr(a: number[], b: number[]) {
    const n = Math.min(a.length, b.length);
    const x = a.slice(-n), y = b.slice(-n);
    const mx = x.reduce((s, v) => s + v, 0) / n, my = y.reduce((s, v) => s + v, 0) / n;
    let sxy = 0, sxx = 0, syy = 0;
    for (let i = 0; i < n; i++) { sxy += (x[i] - mx) * (y[i] - my); sxx += (x[i] - mx) ** 2; syy += (y[i] - my) ** 2; }
    return sxy / Math.sqrt(sxx * syy);
}

const fmt = (v: number) => v >= 1000 ? v.toLocaleString('en-US', { maximumFractionDigits: 0 }) : v >= 100 ? v.toFixed(1) : v.toFixed(2);
const list = (xs: number[]) => xs.length ? xs.map(fmt).join(' / ') : 'لا يوجد';


function Spark({ v, up }: { v: number[]; up: boolean }) {
    const lo = Math.min(...v), hi = Math.max(...v), W = 200, H = 56;
    const pts = v.map((y, i) => `${(i / (v.length - 1) * W).toFixed(1)},${(H - 4 - (y - lo) / ((hi - lo) || 1) * (H - 8)).toFixed(1)}`);
    const col = up ? '#3ecf8e' : '#e0707a';
    return <svg className="gd-spark" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden="true">
        <polygon points={`0,${H} ${pts.join(' ')} ${W},${H}`} fill={col} opacity="0.14" />
        <polyline points={pts.join(' ')} fill="none" stroke={col} strokeWidth="2.2" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
    </svg>;
}
function Pill({ v }: { v: number }) { return <span className={`gd-pill ${v >= 0 ? 'gd-up' : 'gd-down'}`}>{v >= 0 ? '▲' : '▼'} {Math.abs(v).toFixed(2)}%</span>; }
function RangeBar({ lo, hi, now, ticks, loL, hiL }: { lo: number; hi: number; now: number; ticks?: number[]; loL: string; hiL: string }) {
    const pc = (x: number) => Math.min(100, Math.max(0, (x - lo) / ((hi - lo) || 1) * 100));
    return <div><div className="gd-bar">{(ticks ?? []).map(t => <b key={t} style={{ left: `${pc(t)}%` }} />)}<i style={{ left: `${pc(now)}%` }} /></div>
        <div className="gd-bar-l"><span>{loL} {fmt(lo)}</span><span>{hiL} {fmt(hi)}</span></div></div>;
}
function Gauge({ value, label, text }: { value: number; label: string; text: string }) {
    const a = Math.PI * (1 - Math.min(100, Math.max(0, value)) / 100);
    const x = 60 + 48 * Math.cos(a), y = 62 - 48 * Math.sin(a);
    const col = value > 70 ? '#e0707a' : value < 30 ? '#6a9be0' : '#3ecf8e';
    return <div className="gd-gauge"><svg viewBox="0 0 120 70" aria-hidden="true">
        <path d="M12 62 A48 48 0 0 1 108 62" fill="none" stroke="#2a2410" strokeWidth="10" strokeLinecap="round" />
        <path d={`M12 62 A48 48 0 0 1 ${x.toFixed(1)} ${y.toFixed(1)}`} fill="none" stroke={col} strokeWidth="10" strokeLinecap="round" />
    </svg><div className="gd-big">{value.toFixed(0)}</div><div className="gd-sub">{label}</div><div className="gd-sub"><b>{text}</b></div></div>;
}

const GREEN = "#19c37d", RED = "#f23645";
function lean(w: Candle[], n: number) {
    const seg = w.slice(-n);
    const rs = w.slice(1).map((c, i) => Math.log(c.c / w[i].c));
    const m = rs.reduce((a, b) => a + b, 0) / rs.length;
    const sd = Math.sqrt(rs.reduce((a, b) => a + (b - m) ** 2, 0) / (rs.length - 1));
    const ret = Math.log(seg[seg.length - 1].c / seg[0].c);
    const z = ret / (sd * Math.sqrt(seg.length - 1));
    const sc = Math.max(-1, Math.min(1, z / 1.5));
    const kind = sc >= 0.67 ? 'up' : sc <= -0.67 ? 'down' : 'side';
    return { sc, kind, green: Math.round((sc + 1) / 2 * 100), ret: ret * 100 };
}
function Arrow({ sc, kind, green, size = 48, id }: { sc: number; kind: string; green: number; size?: number; id: string }) {
    const label = kind === 'up' ? 'اتجاه صاعد' : kind === 'down' ? 'اتجاه هابط' : `عرضي، ${green} بالمئة أخضر و${100 - green} بالمئة أحمر`;
    return <svg width={size} height={size} viewBox="0 0 32 32" role="img" aria-label={label}>
        {kind === 'side' && <defs><linearGradient id={id} x1="0" x2="1" y1="0" y2="0"><stop offset={`${100 - green}%`} stopColor={RED} /><stop offset={`${100 - green}%`} stopColor={GREEN} /></linearGradient></defs>}
        {kind === 'up' && <path d="M16 4 L28 18 H20 V28 H12 V18 H4 Z" fill={GREEN} stroke="#fff" strokeWidth="1.2" strokeLinejoin="round" />}
        {kind === 'down' && <path d="M16 28 L4 14 H12 V4 H20 V14 H28 Z" fill={RED} stroke="#fff" strokeWidth="1.2" strokeLinejoin="round" />}
        {kind === 'side' && <path d="M2 16 L11 7 V13 H21 V7 L30 16 L21 25 V19 H11 V25 Z" fill={`url(#${id})`} stroke="#fff" strokeWidth="1.2" strokeLinejoin="round" />}
    </svg>;
}
function TrendTag({ w, n, id }: { w: Candle[]; n: number; id: string }) {
    const l = lean(w, n);
    const t = l.kind === 'up' ? 'صاعد' : l.kind === 'down' ? 'هابط' : l.sc > 0.1 ? 'عرضي مائل للصعود' : l.sc < -0.1 ? 'عرضي مائل للهبوط' : 'عرضي متوازن';
    return <span className="gd-trend"><Arrow {...l} id={id} /><span>{t}</span></span>;
}

const RANGES = [{ k: '24س', n: 24, t: 'آخر 24 ساعة' }, { k: '7 أيام', n: 168, t: 'آخر 7 أيام' }, { k: '30 يوم', n: 720, t: 'آخر 30 يوم' }];
function CoinChart({ x, r, setR }: { x: Info; r: number; setR: (n: number) => void }) {
    const rg = RANGES[r];
    const w = x.w.slice(-rg.n);
    const ch = (w[w.length - 1].c / w[0].c - 1) * 100;
    return <>
        <div className="gd-nav" role="group" aria-label="المدى الزمني">
            {RANGES.map((q, i) => <button key={q.k} type="button" className="file-button is-compact" data-variant={i === r ? 'primary' : 'secondary'} aria-pressed={i === r} onClick={() => setR(i)}>{q.k}</button>)}
        </div>
        <LineChart label={`الإغلاق بالساعة، ${rg.t}`} summary={`التغير في المدى ${ch >= 0 ? '+' : ''}${ch.toFixed(2)} بالمئة. المس الشارت أو اسحب عليه لقراءة أي نقطة.`} xName="الوقت" data={w.map((c, i) => ({ x: i, label: new Date(c.t).toLocaleString('ar-EG', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }), value: c.c, valueLabel: fmt(c.c) }))} />
    </>;
}

export function App() {
    const [data, setData] = useState<Info[] | null>(null);
    const [err, setErr] = useState('');
    const [busy, setBusy] = useState(false);
    const [at, setAt] = useState<Date | null>(null);

    const load = useCallback(async () => {
        setBusy(true); setErr('');
        try {
            const out = await Promise.all(ASSETS.map(async a => analyse(a, await candles(a.sym, '1d', 40), await candles(a.sym, '1h', 720))));
            setData(out); setAt(new Date());
        } catch (e) { setErr('تعذر تحميل البيانات من بينانس. جرب التحديث بعد قليل.'); }
        setBusy(false);
    }, []);
    const [left, setLeft] = useState(60);
    const [rr, setRr] = useState(1);
    useEffect(() => { void load(); }, [load]);
    useEffect(() => { const t = setInterval(() => setLeft(l => { if (l <= 1) { void load(); return 60; } return l - 1; }), 1000); return () => clearInterval(t); }, [load]);
    useEffect(() => { if (!busy) setLeft(60); }, [at, busy]);

    const pairs = data ? data.slice(1).map(x => ({ name: x.name, value: corr(data[0].rets, x.rets) }))
        .concat([[1, 2], [1, 3], [2, 3]].map(([i, j]) => ({ name: `${data[i].name} و${data[j].name}`, value: corr(data[i].rets, data[j].rets) }))) : [];
    const time = at ? at.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' }) : '';

    const head = <Header title="لوحة الذهب والكريبتو" fact={at ? `آخر تحديث ${time}` : 'جار التحميل'} intro="أسعار ومستويات الذهب (XAUT) وBNB وETH وSOL من بينانس سبوت، تتحدث عند فتح الصفحة. للبحث فقط، لا شراء ولا بيع من هنا." />;
    const refresh = <div><span className="gd-live"><span className="gd-dot" />مباشر، تحديث تلقائي بعد {left} ث</span> <button type="button" className="file-button is-compact" data-variant="secondary" disabled={busy} onClick={() => { void load(); setLeft(60); }}>{busy ? 'جار التحديث…' : 'تحديث الآن'}</button></div>;
    const home = <>
        {data && <>
            <Group label="نظرة سريعة" heading>
                <div className="gd-grid">{data.map(x => <Link key={x.sym} to={`/${x.path}`} className="gd-card">
                    <div className="gd-card-top"><span className="gd-name">{x.name}</span><Pill v={x.chg} /></div>
                    <div className="gd-price">{fmt(x.price)}</div>
                    <TrendTag w={x.w} n={168} id={`h-${x.sym}`} />
                    <RangeBar lo={x.lo} hi={x.hi} now={x.price} loL="أدنى" hiL="أعلى" />
                    <Spark v={x.closes} up={x.chg >= 0} />
                    <div className="gd-sub">اضغط لفتح لوحة {x.name}</div>
                </Link>)}</div>
                <Caption>الأسعار بالدولار USDT. سعر XAUT هو سعر توكن الذهب على بينانس وليس سعر الذهب الفوري.</Caption>
            </Group>
            <Group label="موقع السعر داخل نطاق 30 يوم" heading>
                <RangeChart label="أدنى 30 يوم، السعر الآن، أعلى 30 يوم" rows={data.map(x => ({ label: x.name, low: 0, now: Math.round((x.price - x.lo) / (x.hi - x.lo) * 100), high: 100, highlight: x.sym === 'XAUTUSDT' }))} range={[0, 100]} scaleLabels={['الأدنى', 'المنتصف', 'الأعلى']} />
            </Group>
            <Group label="لوحة كل عملة" heading>
                <nav className="gd-nav" aria-label="العملات">{data.map(x => <Link key={x.path} className="file-button is-compact" data-variant="secondary" to={`/${x.path}`}>{x.name}</Link>)}</nav>
            </Group>
            <Group label="الارتباط خلال 30 يوم" heading>
                <Rows>{pairs.map((p, i) => <Row key={p.name} number={i + 1} name={p.name} value={p.value.toFixed(2)} valueKnown />)}</Rows>
                <Callout title="كيف تقرأها" tone="note">قريب من 1 يعني يتحركان معا. حول 0.4 يعني استقلال نسبي. الكريبتو الثلاثة غالبا كتلة واحدة والذهب أكثر استقلالا.</Callout>
            </Group>
        </>}
        </>;
    const coin = (x: Info, r: number, setR: (n: number) => void) => <>
        <Header title={x.name} intro="الأسعار بالدولار USDT على بينانس سبوت." />
        <div className="gd-hero">
            <div className="gd-card-top"><span className="gd-name">{x.name}</span><Pill v={x.chg} /></div>
            <div className="gd-price">{fmt(x.price)}</div>
            <div className="gd-sub">مدى 24 ساعة</div>
            <RangeBar lo={x.l24} hi={x.h24} now={x.price} loL="أدنى" hiL="أعلى" />
        </div>
        <Signal x={x} />
        <Group label="الاتجاه" heading>
            <div className="gd-trends">{[{ n: 24, t: '24 ساعة' }, { n: 168, t: '7 أيام' }, { n: 720, t: '30 يوم' }].map(f => { const l = lean(x.w, f.n); return <div key={f.n} className="gd-tr"><span className="gd-sub">{f.t}</span><Arrow {...l} size={60} id={`c-${x.sym}-${f.n}`} /><TrendTag w={x.w} n={f.n} id={`t-${x.sym}-${f.n}`} /><span className={`gd-sub ${l.ret >= 0 ? "gd-upt" : "gd-downt"}`} dir="ltr">{l.ret >= 0 ? '+' : ''}{l.ret.toFixed(1)}%</span></div>; })}</div>
            <Caption>السهم الأخضر صاعد والأحمر هابط. إذا كان الاتجاه عرضيا يظهر السهم بلونين، وتزيد مساحة اللون الغالب حسب ميل الحركة. المقياس هو حركة المدى مقارنة بالتذبذب المعتاد للعملة، وصف وليس توقعا.</Caption>
        </Group>
        {refresh}
        <Link className="file-button is-compact" data-variant="secondary" to="/">كل العملات</Link>
        <Callout title="قراءة سريعة" tone="note">{`RSI ${x.rsi.toFixed(0)} (${x.rsi > 70 ? 'تشبع شراء' : x.rsi < 30 ? 'تشبع بيع' : 'منطقة محايدة'})، والمتوسط القصير ${x.ema10 > x.ema30 ? 'فوق' : 'تحت'} الطويل، والسعر ${x.price > x.poc ? 'فوق' : 'تحت'} منطقة أعلى حجم. وصف للوضع الحالي وليس توقعا.`}</Callout>
        <Group label="الميزان" heading>
            <div className="gd-gauges">
                <Gauge value={x.rsi} label="RSI ساعة" text={x.rsi > 70 ? 'تشبع شراء' : x.rsi < 30 ? 'تشبع بيع' : 'محايد'} />
                <Gauge value={Math.min(100, Math.max(0, (x.price - x.lo) / (x.hi - x.lo) * 100))} label="موقعك في نطاق 30 يوم" text={x.price > x.poc ? 'فوق أعلى حجم' : 'تحت أعلى حجم'} />
            </div>
            <span className="gd-chip">{x.ema10 > x.ema30 ? 'الاتجاه القصير فوق الطويل' : 'الاتجاه القصير تحت الطويل'}</span>
            <span className="gd-chip">تذبذب {x.vol24.toFixed(2)}%</span>
            <div className="gd-sub" style={{ marginTop: 14 }}>نطاق 30 يوم، والعلامات الرمادية هي الدعم والمقاومة</div>
            <RangeBar lo={x.lo} hi={x.hi} now={x.price} ticks={[...x.sup, ...x.res]} loL="أدنى" hiL="أعلى" />
        </Group>
        <Group label="آخر 24 ساعة" heading>
            <Facts items={[
                { label: 'أعلى سعر', value: fmt(x.h24) }, { label: 'أدنى سعر', value: fmt(x.l24) },
                { label: 'قيمة التداول', value: `${Math.round(x.qv).toLocaleString('en-US')} USDT` },
                { label: 'تذبذب 24 ساعة', value: `${x.vol24.toFixed(2)} بالمئة` },
            ]} />
        </Group>
        <Group label="الشارت" heading>
            <CoinChart x={x} r={r} setR={setR} />
        </Group>
        <Group label="المستويات" heading>
            <Facts items={[
                { label: 'أدنى 30 يوم', value: fmt(x.lo) }, { label: 'أعلى 30 يوم', value: fmt(x.hi) },
                { label: 'البعد عن الأعلى', value: `${((x.price / x.hi - 1) * 100).toFixed(1)} بالمئة` },
                { label: 'البعد عن الأدنى', value: `+${((x.price / x.lo - 1) * 100).toFixed(1)} بالمئة` },
                { label: 'دعم', value: list(x.sup) }, { label: 'مقاومة', value: list(x.res) },
                { label: 'أعلى حجم تداول (POC)', value: fmt(x.poc) },
            ]} />
        </Group>
        <Group label="المؤشرات" heading>
            <Facts items={[
                { label: 'متوسط المدى اليومي (ATR 14)', value: fmt(x.atr) },
                { label: 'RSI على الساعة (14)', value: x.rsi.toFixed(0) },
                { label: 'المتوسط 10 يوم مقابل 30 يوم', value: x.ema10 > x.ema30 ? 'قصير فوق طويل' : 'قصير تحت طويل' },
            ]} />
            <Caption>RSI فوق 70 يعني تشبع شراء وتحت 30 تشبع بيع. المتوسطات من الإغلاق اليومي. كلها قراءة وصفية وليست توقعا.</Caption>
        </Group>
        <VolumeProfile sym={x.sym} w={x.w} price={x.price} rangeN={RANGES[r].n} rangeName={RANGES[r].t} />
        <TVNote sym={x.sym} />
        <History sym={x.sym} name={x.name} />
        <Group label="آخر 7 أيام" heading>
            <Rows>{x.recent.map((c, i) => <Row key={c.t} number={i + 1} name={new Date(c.t).toLocaleDateString('ar-EG', { weekday: 'long', day: 'numeric', month: 'short' })} detail={`أعلى ${fmt(c.h)} وأدنى ${fmt(c.l)}`} value={<span className={(c.c >= c.o ? 'gd-upt' : 'gd-downt')}>{`${((c.c / c.o - 1) * 100).toFixed(2)} بالمئة`}</span>} />)}</Rows>
        </Group>
        {x.note && <Caption>{x.note}</Caption>}
        <Group label="عملات أخرى" heading>
            <nav className="gd-nav">{data!.filter(y => y.sym !== x.sym).map(y => <Link key={y.path} className="file-button is-compact" data-variant="secondary" to={`/${y.path}`}>{y.name}</Link>)}</nav>
        </Group>
    </>;
    const closing = <Closing>مستويات بسيطة من أعلى وأدنى أسعار 30 يوم وليست توقعات. بيانات عامة من بينانس، بحث فقط وليست نصيحة مالية.</Closing>;
    return <FileCard lang="ar" dir="rtl">
        {err && <Callout title="خطأ" tone="danger">{err}</Callout>}
        <nav className="gd-tabs" aria-label="الصفحات">
            <NavLink to="/" end>الرئيسية</NavLink>
            {ASSETS.map(a => <NavLink key={a.path} to={`/${a.path}`}>{a.name.split(' ')[0] === 'الذهب' ? 'الذهب' : a.name}</NavLink>)}
            <NavLink to="/radar">الأخبار</NavLink><NavLink to="/journal">السجل</NavLink><NavLink to="/lab">المعمل</NavLink><NavLink to="/paper">التداول</NavLink><NavLink to="/studio">المحلل</NavLink><NavLink to="/research">المخزن</NavLink><NavLink to="/ideas">الأفكار</NavLink><NavLink to="/rules">القواعد</NavLink>
        </nav>
        <Routes>
            <Route path="/" element={<>{head}{refresh}{data && home}</>} />
            <Route path="/radar" element={<Radar />} />
            <Route path="/journal" element={<Journal />} />
            <Route path="/ideas" element={<Ideas />} />
            <Route path="/rules" element={<Rules />} />
            <Route path="/paper" element={<Paper />} />
            <Route path="/research" element={<Research />} />
            <Route path="/studio" element={<Studio />} />
            <Route path="/lab" element={<Lab />} />
            {ASSETS.map(a => <Route key={a.path} path={`/${a.path}`} element={data ? coin(data.find(d => d.sym === a.sym)!, rr, setRr) : <Header title={a.name} fact="جار التحميل" />} />)}
        </Routes>
        {closing}
    </FileCard>;
                                                                                                                                              }
