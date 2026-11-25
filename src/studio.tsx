import React, { useEffect, useMemo, useState } from 'react';
import { Callout, Caption, Facts, Group, Header, LineChart } from '@instinct/files';
import { Src } from './trust';

const API = 'https://data-api.binance.vision/api/v3/klines';
const COINS = ['XAUTUSDT', 'BNBUSDT', 'ETHUSDT', 'SOLUSDT'];
const TFS = ['5m', '15m', '1h', '4h', '1d'];
type K = { t: number; o: number; h: number; l: number; c: number };

function rsi(c: number[], n = 14) {
    const r: number[] = new Array(c.length).fill(NaN);
    let g = 0, l = 0;
    for (let i = 1; i < c.length; i++) {
        const d = c[i] - c[i - 1], up = Math.max(d, 0), dn = Math.max(-d, 0);
        if (i <= n) { g += up; l += dn; if (i === n) { g /= n; l /= n; r[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l); } }
        else { g = (g * (n - 1) + up) / n; l = (l * (n - 1) + dn) / n; r[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l); }
    }
    return r;
}
function lowerBB(c: number[], n = 20, m = 2) {
    return c.map((_, i) => {
        if (i < n - 1) return NaN;
        const s = c.slice(i - n + 1, i + 1), a = s.reduce((x, y) => x + y, 0) / n;
        const sd = Math.sqrt(s.reduce((x, y) => x + (y - a) ** 2, 0) / n);
        return a - m * sd;
    });
}
type P = { rsiIn: number; rsiOut: number; tp: number; sl: number; maxBars: number; fee: number; useBB: boolean };
function backtest(k: K[], p: P) {
    const c = k.map(x => x.c), R = rsi(c), B = lowerBB(c);
    const trades: { i: number; j: number; pct: number; why: string }[] = [];
    let i = 15;
    while (i < k.length - 2) {
        if (R[i] < p.rsiIn && (!p.useBB || c[i] <= B[i])) {
            const e = k[i + 1].o; let j = i + 1, why = 'وقت', x = k[Math.min(k.length - 1, i + 1 + p.maxBars)].c;
            const last = Math.min(k.length - 1, i + 1 + p.maxBars);
            let done = false;
            for (j = i + 1; j <= last; j++) {
                if (p.sl > 0 && k[j].l <= e * (1 - p.sl / 100)) { x = e * (1 - p.sl / 100); why = 'وقف'; done = true; break; }
                if (p.tp > 0 && k[j].h >= e * (1 + p.tp / 100)) { x = e * (1 + p.tp / 100); why = 'هدف'; done = true; break; }
                if (p.rsiOut > 0 && R[j] > p.rsiOut) { x = k[j].c; why = 'RSI'; done = true; break; }
            }
            if (!done) { j = last; x = k[last].c; }
            trades.push({ i: i + 1, j, pct: ((x / e - 1) * 100) - 2 * p.fee, why });
            i = j + 1;
        } else i++;
    }
    return trades;
}
const f2 = (x: number) => (x >= 0 ? '+' : '') + x.toFixed(2);

export function Studio() {
    const [sym, setSym] = useState('XAUTUSDT'), [tf, setTf] = useState('15m');
    const [k, setK] = useState<K[]>([]), [err, setErr] = useState(''), [load, setLoad] = useState(false);
    const [p, setP] = useState<P>({ rsiIn: 35, rsiOut: 60, tp: 0.35, sl: 0, maxBars: 200, fee: 0.1, useBB: true });
    const [bud, setBud] = useState(1000);
    const [at, setAt] = useState('');
    useEffect(() => {
        let ok = true; setLoad(true); setErr('');
        fetch(`${API}?symbol=${sym}&interval=${tf}&limit=1000`).then(r => r.json()).then((a: any[]) => {
            if (!ok) return; setAt(new Date().toLocaleTimeString('ar-EG')); setK(a.slice(0, -1).map(r => ({ t: r[0], o: +r[1], h: +r[2], l: +r[3], c: +r[4] }))); setLoad(false);
        }).catch(() => { if (ok) { setErr('تعذر جلب بيانات Binance الآن'); setLoad(false); } });
        return () => { ok = false; };
    }, [sym, tf]);
    const T = useMemo(() => k.length ? backtest(k, p) : [], [k, p]);
    const W = T.filter(t => t.pct > 0), L = T.filter(t => t.pct <= 0);
    let eq = 0, peak = 0, dd = 0; const curve = T.map((t, n) => { eq += t.pct; peak = Math.max(peak, eq); dd = Math.min(dd, eq - peak); return { x: n, label: `صفقة ${n + 1}`, value: +eq.toFixed(2), valueLabel: f2(eq) + '%' }; });
    const hold = k.length ? (k[k.length - 1].c / k[0].o - 1) * 100 : 0;
    const days = k.length ? ((k[k.length - 1].t - k[0].t) / 86400000) : 0;
    const gw = W.reduce((x, t) => x + t.pct, 0), gl = -L.reduce((x, t) => x + t.pct, 0);
    const num = (key: keyof P, label: string, step = 1) => <label className="sl"><span>{label}: <b>{(p as any)[key]}</b></span><input type="range" min={key === 'fee' ? 0 : key === 'maxBars' ? 5 : 0} max={key === 'rsiIn' ? 50 : key === 'rsiOut' ? 90 : key === 'tp' ? 5 : key === 'sl' ? 5 : key === 'fee' ? 0.5 : 500} step={step} value={(p as any)[key]} onChange={e => setP({ ...p, [key]: +e.target.value })} /></label>;
    const px = k.length ? k[k.length - 1].c : 0;
    const tr = [0.97, 0.94, 0.91].map(m => px * m);
    const per = bud / 3, qty = tr.map(t => per / t), avg = bud / qty.reduce((a, b) => a + b, 0);
    return <>
        <Header title="المحلل التفاعلي" fact={load ? 'جاري التحميل' : `${k.length} شمعة`} intro="يحسب في متصفحك من بيانات Binance العامة: غيّر العملة والإطار والأرقام، وشاهد نتيجة استراتيجية شراء الهبوط فورا. سبوت وشراء فقط، حساب نظري، بلا أموال حقيقية." />
        <Group label="الاختيار" heading>
            <div className="chips">{COINS.map(c => <button key={c} className={'chip' + (c === sym ? ' on' : '')} onClick={() => setSym(c)}>{c.replace('USDT', '')}</button>)}</div>
            <div className="chips">{TFS.map(c => <button key={c} className={'chip' + (c === tf ? ' on' : '')} onClick={() => setTf(c)}>{c}</button>)}</div>
            {err && <Callout title="خطأ" tone="warning">{err}</Callout>}
        </Group>
        <Group label="شروط الاستراتيجية" heading>
            {num('rsiIn', 'دخول: RSI أقل من')}
            <label className="sl"><span>شرط الحد السفلي لبولينجر: <b>{p.useBB ? 'مفعل' : 'متوقف'}</b></span><input type="checkbox" checked={p.useBB} onChange={e => setP({ ...p, useBB: e.target.checked })} /></label>
            {num('rsiOut', 'خروج: RSI أعلى من (0 = بدون)')}
            {num('tp', 'هدف ربح بالمئة (0 = بدون)', 0.05)}
            {num('sl', 'وقف بالمئة (0 = بدون، أي خسارة تُحتمل)', 0.05)}
            {num('maxBars', 'أقصى مدة بالشموع', 5)}
            {num('fee', 'الرسوم لكل جهة بالمئة', 0.05)}
        </Group>
        <Group label="النتيجة (محاكاة على آخر ألف شمعة)" heading>
            <Facts items={[
                { label: 'الفترة', value: `${days.toFixed(1)} يوم` },
                { label: 'الصفقات', value: String(T.length) },
                { label: 'نسبة النجاح', value: T.length ? `${Math.round(100 * W.length / T.length)} بالمئة (${W.length} رابحة، ${L.length} خاسرة)` : 'لا صفقات' },
                { label: 'متوسط الرابحة / الخاسرة', value: T.length ? `${f2(W.length ? gw / W.length : 0)} / ${f2(L.length ? -gl / L.length : 0)} بالمئة` : '-' },
                { label: 'صافي بعد الرسوم', value: `${f2(eq)} بالمئة (مجموع الصفقات)` },
                { label: 'أقصى تراجع', value: `${dd.toFixed(2)} بالمئة` },
                { label: 'الاحتفاظ بنفس الفترة', value: `${f2(hold)} بالمئة` },
            ]} />
            {curve.length > 1 && <LineChart label="الرصيد التراكمي بالنسبة المئوية، صفقة بصفقة" xName="الصفقة" data={curve} />}
            <Src s={`Binance klines ${sym} ${tf} (آخر 1000 شمعة، تحسب في متصفحك)`} t={at} kind="محاكاة" />
            {T.length < 30 && <Callout title="عينة صغيرة" tone="warning">أقل من 30 صفقة لا تثبت شيئا. التنفيذ يتم عند فتح الشمعة التالية، وإذا لمست شمعة الوقف والهدف معا يُحسب الوقف أولا. لا انزلاق سعري. تغيير الأرقام حتى تظهر نتيجة جيدة هو ملاءمة للماضي وليس دليلا.</Callout>}
        </Group>
        <Group label="حاسبة دفعات التجميع (3 دفعات متساوية)" heading>
            <label className="sl"><span>الميزانية بـ USDT: <b>{bud}</b></span><input type="range" min={30} max={5000} step={10} value={bud} onChange={e => setBud(+e.target.value)} /></label>
            <Facts items={tr.map((t, i) => ({ label: `الدفعة ${i + 1} عند ${(i + 1) * 3} بالمئة تحت السعر الحالي`, value: `${t.toFixed(2)} (${(qty[i]).toFixed(5)} وحدة)` })).concat([{ label: 'متوسط التكلفة لو اكتملت', value: avg.toFixed(2) }, { label: 'السعر الحالي', value: px.toFixed(2) }])} />
            <Caption>أمثلة حسابية وليست توصية. سبوت فقط. القرار والحكم الشرعي لك.</Caption>
        </Group>
    </>;
}
