import React, { useState } from 'react';
import { Callout, Caption, Facts, Group, Row, Rows } from '@instinct/files';
import hist from './data/history.json';

export type C = { t: number; o: number; h: number; l: number; c: number; v: number };
const H: Record<string, number[][]> = hist as any;
const fx = (v: number) => v >= 1000 ? v.toLocaleString('en-US', { maximumFractionDigits: 0 }) : v >= 100 ? v.toFixed(1) : v.toFixed(2);
const dd = (t: number) => new Date(t).toLocaleDateString('ar-EG', { day: 'numeric', month: 'short' });

type P = { lo: number; step: number; vols: number[]; poc: number; vah: number; val: number; total: number; n: number; from: number; to: number; hvn: number[]; lvn: number[] };
export function profile(cs: C[], bins = 48, tpo = false): P | null {
    if (cs.length < 2) return null;
    const lo = Math.min(...cs.map(x => x.l)), hi = Math.max(...cs.map(x => x.h));
    const step = (hi - lo) / bins || 1;
    const vols = new Array(bins).fill(0);
    for (const x of cs) {
        const a = Math.min(bins - 1, Math.floor((x.l - lo) / step)), b = Math.min(bins - 1, Math.floor((x.h - lo) / step));
        const k = b - a + 1;
        for (let i = a; i <= b; i++) vols[i] += tpo ? 1 : x.v / k;
    }
    const total = vols.reduce((s, v) => s + v, 0);
    let pi = vols.indexOf(Math.max(...vols));
    let lowI = pi, highI = pi, acc = vols[pi];
    while (acc < total * 0.7 && (lowI > 0 || highI < bins - 1)) {
        const dn = lowI > 0 ? vols[lowI - 1] : -1, up = highI < bins - 1 ? vols[highI + 1] : -1;
        if (up >= dn) { highI++; acc += vols[highI]; } else { lowI--; acc += vols[lowI]; }
    }
    const avg = total / bins;
    const peaks: number[] = [], valleys: number[] = [];
    for (let i = 1; i < bins - 1; i++) {
        if (vols[i] > vols[i - 1] && vols[i] >= vols[i + 1] && vols[i] > avg * 1.15 && i !== pi) peaks.push(i);
        if (vols[i] < vols[i - 1] && vols[i] <= vols[i + 1] && vols[i] < avg * 0.6) valleys.push(i);
    }
    const px = (i: number) => lo + (i + 0.5) * step;
    peaks.sort((a, b) => vols[b] - vols[a]); valleys.sort((a, b) => vols[a] - vols[b]);
    return { lo, step, vols, poc: px(pi), vah: lo + (highI + 1) * step, val: lo + lowI * step, total, n: cs.length, from: cs[0].t, to: cs[cs.length - 1].t, hvn: peaks.slice(0, 3).map(px), lvn: valleys.slice(0, 3).map(px) };
}

function Bars({ p, price }: { p: P; price: number }) {
    const rows = p.vols.length, per = 1;
    const agg = Array.from({ length: rows }, (_, r) => { let s = 0; for (let i = Math.round(r * per); i < Math.round((r + 1) * per); i++) s += p.vols[i]; return s; });
    const mx = Math.max(...agg);
    const lo = (r: number) => p.lo + Math.round(r * per) * p.step, hi = (r: number) => p.lo + Math.round((r + 1) * per) * p.step;
    return <div className="gd-vp" dir="ltr" role="img" aria-label="توزيع الحجم على الأسعار">
        {agg.map((_, r) => { const i = rows - 1 - r; const v = agg[i]; const a = lo(i), b = hi(i); const inVA = b > p.val && a < p.vah; const hasPoc = p.poc >= a && p.poc < b + 1e-9; const hasPx = price >= a && price < b + 1e-9;
            return <div key={i} className={`gd-vp-r${hasPx ? ' is-px' : ''}`}>
                <span className="gd-vp-p">{fx((a + b) / 2)}</span>
                <span className="gd-vp-t"><span className={`gd-vp-b${inVA ? ' is-va' : ''}${hasPoc ? ' is-poc' : ''}`} style={{ width: `${Math.max(1, v / mx * 100)}%` }} /></span>
                <span className="gd-vp-m">{hasPoc ? 'POC' : hasPx ? 'السعر' : ''}</span>
            </div>; })}
    </div>;
}

function Summary({ p, price }: { p: P; price: number }) {
    const pos = price > p.vah ? 'فوق منطقة القيمة' : price < p.val ? 'تحت منطقة القيمة' : 'داخل منطقة القيمة';
    return <>
        <Bars p={p} price={price} />
        <Facts items={[
            { label: 'POC أعلى حجم', value: fx(p.poc) },
            { label: 'VAH أعلى منطقة القيمة', value: fx(p.vah) },
            { label: 'VAL أدنى منطقة القيمة', value: fx(p.val) },
            { label: 'السعر الآن', value: `${fx(price)}، ${pos}` },
            { label: 'عقد حجم عالٍ HVN', value: p.hvn.length ? p.hvn.map(fx).join(' / ') : 'لا يوجد' },
            { label: 'فجوات حجم منخفض LVN', value: p.lvn.length ? p.lvn.map(fx).join(' / ') : 'لا يوجد' },
            { label: 'الفترة', value: `${dd(p.from)} إلى ${dd(p.to)}، ${p.n} شمعة` },
        ]} />
    </>;
}

const hourly = (w: C[]) => w;
const daily = (sym: string): C[] => H[sym].map(r => ({ t: r[0], o: r[1], h: r[2], l: r[3], c: r[4], v: r[5] }));
const TYPES = [
    { k: 'session', n: 'الجلسة' }, { k: 'fixed', n: 'نطاق ثابت' }, { k: 'visible', n: 'النطاق المرئي' }, { k: 'periodic', n: 'أسبوعي' }, { k: 'anchored', n: 'مثبّت' }, { k: 'tpo', n: 'TPO' },
];
const FIX = [{ k: '7 أيام', n: 168 }, { k: '14 يوم', n: 336 }, { k: '30 يوم', n: 720 }, { k: '90 يوم', n: -90 }];

export function VolumeProfile({ sym, w, price, rangeN, rangeName }: { sym: string; w: C[]; price: number; rangeN: number; rangeName: string }) {
    const [ty, setTy] = useState('session');
    const [fi, setFi] = useState(2);
    const [sd, setSd] = useState(0);
    const [an, setAn] = useState(0);
    const lastDay = new Date(w[w.length - 1].t).setUTCHours(0, 0, 0, 0);
    const [tp, setTp] = useState(0);
    let body: React.ReactNode = null;
    if (ty === 'session') {
        const day0 = lastDay - sd * 86400000;
        const cs = w.filter(x => x.t >= day0 && x.t < day0 + 86400000);
        const p = profile(cs, 32);
        body = <>
            <div className="gd-nav" role="group" aria-label="اليوم">{['اليوم', 'أمس', 'قبل يومين'].map((n, i) => <button key={n} type="button" className="file-button is-compact" data-variant={i === sd ? 'primary' : 'secondary'} aria-pressed={i === sd} onClick={() => setSd(i)}>{n}</button>)}</div>
            {p ? <Summary p={p} price={price} /> : <Callout title="لا بيانات" tone="note">لا توجد شموع كافية لهذه الجلسة.</Callout>}
            <Caption>جلسة = يوم UTC كامل من شموع الساعة. جلسة اليوم ناقصة حتى آخر اليوم.</Caption>
        </>;
    } else if (ty === 'fixed') {
        const f = FIX[fi];
        const cs = f.n > 0 ? w.slice(-f.n) : daily(sym).slice(f.n);
        const p = profile(cs);
        body = <>
            <div className="gd-nav" role="group" aria-label="النطاق">{FIX.map((q, i) => <button key={q.k} type="button" className="file-button is-compact" data-variant={i === fi ? 'primary' : 'secondary'} aria-pressed={i === fi} onClick={() => setFi(i)}>{q.k}</button>)}</div>
            {p && <Summary p={p} price={price} />}
            <Caption>{f.n > 0 ? 'من شموع الساعة.' : 'من الشموع اليومية المحفوظة، توزيع أقل دقة داخل اليوم.'}</Caption>
        </>;
    } else if (ty === 'visible') {
        const p = profile(w.slice(-rangeN));
        body = <>
            <Callout title="يتبع الشارت" tone="note">هذا هو النطاق المرئي: {rangeName}. غيّره من أزرار المدى فوق الشارت وسيتغير التوزيع.</Callout>
            {p && <Summary p={p} price={price} />}
        </>;
    } else if (ty === 'periodic') {
        const weeks: { s: number; p: P }[] = [];
        const ds = daily(sym);
        const wk = (t: number) => { const d = new Date(t); const day = (d.getUTCDay() + 6) % 7; return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() - day); };
        const map = new Map<number, C[]>();
        for (const x of ds.slice(-56)) { const k = wk(x.t); map.set(k, [...(map.get(k) ?? []), x]); }
        for (const [s, cs] of [...map.entries()].reverse().slice(0, 6)) { const p = profile(cs, 24); if (p && cs.length >= 3) weeks.push({ s, p }); }
        body = <>
            <Rows>{weeks.map(({ s, p }, i) => <Row key={s} number={i + 1} name={`أسبوع ${dd(s)}`} detail={`POC ${fx(p.poc)}، قيمة من ${fx(p.val)} إلى ${fx(p.vah)}`} value={fx(p.poc)} valueKnown />)}</Rows>
            <Caption>ملف حجم لكل أسبوع (اثنين إلى أحد UTC) من الشموع اليومية، لأسابيع فيها 3 أيام أو أكثر. تتبع حركة منطقة القيمة من أسبوع لآخر.</Caption>
        </>;
    } else if (ty === 'tpo') {
        const opts = [{ n: 'اليوم', f: (x: C) => x.t >= lastDay }, { n: 'أمس', f: (x: C) => x.t >= lastDay - 86400000 && x.t < lastDay }, { n: '7 أيام', f: (x: C) => x.t >= lastDay - 6 * 86400000 }, { n: '30 يوم', f: () => true }];
        const cs = w.filter(opts[tp].f);
        const p = profile(cs, 32, true);
        body = <>
            <div className="gd-nav" role="group" aria-label="فترة TPO">{opts.map((q, i) => <button key={q.n} type="button" className="file-button is-compact" data-variant={i === tp ? 'primary' : 'secondary'} aria-pressed={i === tp} onClick={() => setTp(i)}>{q.n}</button>)}</div>
            {p ? <Summary p={p} price={price} /> : <Callout title="لا بيانات" tone="note">لا توجد شموع كافية.</Callout>}
            <Caption>TPO (ملف السوق) يعد الوقت لا الحجم: كل ساعة تضيف نقطة لكل مستوى سعر لمسته. POC هنا هو السعر الذي قضى فيه السوق أطول وقت، وقد يختلف عن POC الحجم.</Caption>
        </>;
    } else {
        const lowI = w.reduce((a, x, i) => x.l < w[a].l ? i : a, 0), highI = w.reduce((a, x, i) => x.h > w[a].h ? i : a, 0);
        const opts = [{ n: 'من أدنى 30 يوم', i: lowI }, { n: 'من أعلى 30 يوم', i: highI }];
        const cs = w.slice(opts[an].i);
        const p = profile(cs);
        body = <>
            <div className="gd-nav" role="group" aria-label="نقطة التثبيت">{opts.map((q, i) => <button key={q.n} type="button" className="file-button is-compact" data-variant={i === an ? 'primary' : 'secondary'} aria-pressed={i === an} onClick={() => setAn(i)}>{q.n}</button>)}</div>
            {p ? <Summary p={p} price={price} /> : <Callout title="شموع قليلة" tone="note">نقطة التثبيت قريبة جدا من الآن.</Callout>}
            <Caption>ملف حجم يبدأ من تلك الشمعة وحتى الآن، ويبين أين تراكم الحجم بعد القاع أو القمة.</Caption>
        </>;
    }
    return <Group label="بروفايل الحجم (Volume Profile)" heading>
        <div className="gd-tabs gd-tabs-s" role="tablist" aria-label="نوع البروفايل">
            {TYPES.map(t => <button key={t.k} type="button" role="tab" aria-selected={ty === t.k} className={ty === t.k ? 'is-on' : ''} onClick={() => setTy(t.k)}>{t.n}</button>)}
        </div>
        {body}
        <Callout title="حدود الدقة" tone="warning">الحجم موزع بالتساوي على مدى سعر كل شمعة، وهو تقدير وليس بيانات صفقات لحظية. شموع الساعة تغطي آخر 30 يوما فقط، وما قبلها من الشموع اليومية. منطقة القيمة تضم 70 بالمئة من الحجم. أدوات وصف وليست توقعا.</Callout>
    </Group>;
}
