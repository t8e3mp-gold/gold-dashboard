import React, { useState } from 'react';
import { Callout, Caption, Facts, Group, Row, Rows } from '@instinct/files';
import hist from './data/history.json';
import labData from './data/lab.json';

const H: Record<string, number[][]> = hist as any;
const fx = (v: number) => v >= 1000 ? v.toLocaleString('en-US', { maximumFractionDigits: 0 }) : v >= 100 ? v.toFixed(1) : v.toFixed(2);
type C = { t: number; o: number; h: number; l: number; c: number };

function daily(x: any): C[] {
    const d: C[] = H[x.sym].map(r => ({ t: r[0], o: r[1], h: r[2], l: r[3], c: r[4] }));
    const day0 = Math.floor(Date.now() / 864e5) * 864e5;
    const lastT = d[d.length - 1].t;
    const td = (x.w as any[]).filter(k => k.t >= day0);
    if (td.length && day0 > lastT) d.push({ t: day0, o: td[0].o, h: Math.max(...td.map(k => k.h)), l: Math.min(...td.map(k => k.l)), c: td[td.length - 1].c });
    return d;
}
const ema = (c: number[], n: number) => { const k = 2 / (n + 1); return c.reduce((e, v, i) => i ? v * k + e * (1 - k) : v, c[0]); };
function rsi14(c: number[]) { let g = 0, l = 0; for (let i = c.length - 14; i < c.length; i++) { const d = c[i] - c[i - 1]; if (d > 0) g += d; else l -= d; } return l === 0 ? 100 : 100 - 100 / (1 + g / l); }
function atr14(d: C[]) { let s = 0; for (let i = d.length - 14; i < d.length; i++) s += Math.max(d[i].h - d[i].l, Math.abs(d[i].h - d[i - 1].c), Math.abs(d[i].l - d[i - 1].c)); return s / 14; }

export function analyse(x: any) {
    const d = daily(x), c = d.map(k => k.c), p = x.price as number;
    const now = (labData as any).coins[x.sym].now;
    const atr = atr14(d), e10 = ema(c, 10), e30 = ema(c, 30), r = rsi14(c);
    const ch7 = (p / c[c.length - 8] - 1) * 100;
    let score = 0; const why: string[] = [];
    if (e10 < e30) { score -= 1; why.push(`المتوسط 10 يوم (${fx(e10)}) تحت المتوسط 30 يوم (${fx(e30)}): الاتجاه هابط.`); } else { score += 1; why.push(`المتوسط 10 يوم (${fx(e10)}) فوق 30 يوم (${fx(e30)}): الاتجاه صاعد.`); }
    if (ch7 < 0) { score -= 1; why.push(`السعر تغير ${ch7.toFixed(1)} بالمئة في 7 أيام: الزخم سلبي.`); } else { score += 1; why.push(`السعر تغير +${ch7.toFixed(1)} بالمئة في 7 أيام: الزخم إيجابي.`); }
    if (now.vfi < 0) { score -= 1; why.push('تدفق الحجم VFI تحت الصفر: الحجم لا يدعم الصعود بعد.'); } else { score += 1; why.push('تدفق الحجم VFI فوق الصفر: الحجم يدعم الصعود.'); }
    if (p < now.val) { score -= 0.5; why.push(`السعر تحت منطقة القيمة (VAL ${fx(now.val)}): السوق يقبل أسعارا أقل من متوسط آخر 30 يوما.`); }
    else if (p > now.vah) { score += 0.5; why.push(`السعر فوق منطقة القيمة (VAH ${fx(now.vah)}): قبول أسعار أعلى.`); }
    else why.push(`السعر داخل منطقة القيمة (${fx(now.val)} إلى ${fx(now.vah)}).`);
    if (r < 30) why.push(`RSI اليومي ${r.toFixed(0)} (تشبع بيعي): احتمال ارتداد فني، لكنه ليس إشارة انعكاس بحد ذاته.`);
    else if (r > 70) why.push(`RSI اليومي ${r.toFixed(0)} (تشبع شرائي): احتمال تراجع فني.`);
    else why.push(`RSI اليومي ${r.toFixed(0)} (محايد).`);
    // أسلوب المستخدم: سبوت فقط، شراء عند الهبوط وبيع عند الصعود، دفعات تدريجية
    const supports = [...(x.sup as number[])].sort((u, v) => v - u);
    const s1 = supports[0] ?? p - atr, s2 = supports[1] ?? s1 - atr, s3 = supports[2] ?? s2 - atr;
    const eLo = s1 - 0.25 * atr, eHi = s1 + 0.25 * atr;
    const tranches = [{ n: 'الدفعة 1', at: s1 }, { n: 'الدفعة 2', at: Math.min(s2, s1 - 0.5 * atr) }, { n: 'الدفعة 3', at: Math.min(s3, s1 - 1 * atr) }];
    const avgCost = tranches.reduce((u, t) => u + t.at, 0) / 3;
    const levels = [...new Set([...(x.res as number[]), ...now.hvn, now.poc, now.val, now.vah, ...now.lvn].map((v: number) => Math.round(v * 100) / 100))].filter(v => v > s1 + 0.5 * atr).sort((u, v) => u - v);
    const t1 = levels[0] ?? s1 + atr, t2 = levels.find(v => v > t1 + 0.5 * atr) ?? t1 + atr;
    const inv = tranches[2].at - 0.5 * atr;
    const rr = (t1 - avgCost) / (avgCost - inv);
    const down = score <= -2;
    let state: 'buy' | 'near' | 'wait' | 'sell';
    if (p >= t1 - 0.25 * atr) state = 'sell'; else if (p <= eHi) state = 'buy'; else if (p <= eHi + 1.5 * atr) state = 'near'; else state = 'wait';
    const verdict = state === 'buy' ? (down ? 'منطقة تجميع الآن، بحذر (الاتجاه هابط)' : 'منطقة تجميع تدريجي الآن') : state === 'near' ? 'اقترب من منطقة التجميع، راقب' : state === 'sell' ? 'منطقة جني أرباح جزئي' : 'انتظار: السعر فوق مناطق التجميع';
    const tone = state === 'buy' ? (down ? 'warning' : 'note') : state === 'sell' ? 'note' : 'warning';
    const risk = down ? 'أعلى (الاتجاه هابط، والشراء على الهبوط قد يستمر في النزول، لذلك دفعات صغيرة)' : score <= 0.5 ? 'متوسطة' : 'أقل (الاتجاه صاعد)';
    return { d, p, atr, e10, e30, r, ch7, score, why, verdict, tone, state, risk, tranches, avgCost, s1, eLo, eHi, brk: 0, brkHi: 0, t1, t2, inv, rr, now };
}

function Candles({ a, n }: { a: ReturnType<typeof analyse>; n: number }) {
    const d = a.d.slice(-n), W = 360, Hh = 250, L = 46, R = 6, T = 8, B = 18;
    const ys = [...d.flatMap(k => [k.h, k.l]), a.inv, a.t2];
    const lo = Math.min(...ys), hi = Math.max(...ys), pad = (hi - lo) * 0.04;
    const y = (v: number) => T + (Hh - T - B) * (1 - (v - (lo - pad)) / (hi - lo + 2 * pad));
    const bw = (W - L - R) / d.length, x = (i: number) => L + bw * (i + 0.5);
    const ticks = [0, 1, 2, 3, 4].map(i => lo + (hi - lo) * i / 4);
    const band = (a1: number, a2: number, col: string) => <rect x={L} width={W - L - R} y={y(a2)} height={Math.max(1.5, y(a1) - y(a2))} fill={col} opacity="0.22" />;
    return <svg viewBox={`0 0 ${W} ${Hh}`} width="100%" role="img" aria-label="شارت الشموع اليابانية اليومية" style={{ direction: 'ltr', display: 'block' }}>
        {ticks.map(v => <g key={v}><line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="#d4af37" opacity="0.12" /><text x={L - 4} y={y(v) + 3} fontSize="9" textAnchor="end" fill="#d4af37">{fx(v)}</text></g>)}
        {a.tranches.map(t => <g key={t.n}>{band(t.at - 0.25 * a.atr, t.at + 0.25 * a.atr, '#19c37d')}</g>)}{band(a.t1, a.t2, '#d4af37')}
        <line x1={L} x2={W - R} y1={y(a.inv)} y2={y(a.inv)} stroke="#f23645" strokeDasharray="4 3" />
        <line x1={L} x2={W - R} y1={y(a.now.poc)} y2={y(a.now.poc)} stroke="#d4af37" opacity="0.5" strokeDasharray="2 3" />
        {d.map((k, i) => { const up = k.c >= k.o, col = up ? '#19c37d' : '#f23645'; return <g key={k.t}><line x1={x(i)} x2={x(i)} y1={y(k.h)} y2={y(k.l)} stroke={col} strokeWidth="1" /><rect x={x(i) - bw * 0.35} width={bw * 0.7} y={y(Math.max(k.o, k.c))} height={Math.max(1, Math.abs(y(k.o) - y(k.c)))} fill={col} /></g>; })}
        <line x1={L} x2={W - R} y1={y(a.p)} y2={y(a.p)} stroke="#fff" strokeWidth="0.8" strokeDasharray="1 2" />
        <rect x={W - R - 40} y={y(a.p) - 7} width="40" height="14" rx="3" fill="#fff" /><text x={W - R - 20} y={y(a.p) + 3} fontSize="9" textAnchor="middle" fill="#000" fontWeight="700">{fx(a.p)}</text>
        <text x={L + 2} y={Hh - 4} fontSize="9" fill="#d4af37">{new Date(d[0].t).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}</text>
        <text x={W - R} y={Hh - 4} fontSize="9" textAnchor="end" fill="#d4af37">{new Date(d[d.length - 1].t).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}</text>
    </svg>;
}

export function Signal({ x }: { x: any }) {
    const [n, setN] = useState(60);
    const a = analyse(x);
    return <>
        <Group label="شارت الشموع اليابانية" heading>
            <div className="gd-nav" role="group" aria-label="المدى">{[30, 60, 90, 180].map(m => <button key={m} type="button" className="file-button is-compact" data-variant={m === n ? 'primary' : 'secondary'} aria-pressed={m === n} onClick={() => setN(m)}>{m} يوم</button>)}</div>
            <Candles a={a} n={Math.min(n, a.d.length)} />
            <Caption>كل شمعة تمثل يوما: الجسم من الافتتاح إلى الإغلاق والخط من أعلى سعر إلى أدنى سعر. أخضر يعني أغلق فوق الافتتاح وأحمر يعني أغلق تحته. النطاقات الخضراء مناطق التجميع (ثلاث دفعات)، والذهبي منطقة أهداف، والخط الأحمر المتقطع مستوى إعادة التقييم، والخط الذهبي المنقط أعلى حجم POC. الشمعة الأخيرة هي اليوم الجاري.</Caption>
        </Group>
        <Group label="التوصية المبدئية (قراءة بحثية، سبوت فقط)" heading>
            <Callout title={`الخلاصة: ${a.verdict}`} tone={a.tone as any}>أسلوبك: شراء الأصل نفسه عند الهبوط وبيعه عند الصعود، دفعات تدريجية، بلا رافعة ولا عقود ولا فوائد ولا بيع على المكشوف. هذه قراءة بحثية أولية وليست نصيحة مالية ولا أمرا بالتداول. الخدمة لا تنفذ أي صفقة، والقرار لك.</Callout>
            <Facts items={[
                { label: 'مستوى المخاطرة الحالي', value: a.risk },
                ...a.tranches.map(t => ({ label: `${t.n}: منطقة التجميع`, value: `${fx(t.at - 0.25 * a.atr)} إلى ${fx(t.at + 0.25 * a.atr)}` })),
                { label: 'متوسط تكلفة الدفعات الثلاث (تقريبي)', value: fx(a.avgCost) },
                { label: 'جني الأرباح: بيع جزء عند الهدف الأول', value: fx(a.t1) },
                { label: 'بيع جزء عند الهدف الثاني', value: fx(a.t2) },
                { label: 'مستوى إعادة التقييم (تحته توقف التجميع وراجع الفكرة)', value: fx(a.inv) },
                { label: 'العائد إلى المخاطرة للهدف الأول', value: a.rr.toFixed(1) },
                { label: 'ATR اليومي (مقياس التذبذب)', value: fx(a.atr) },
            ]} />
            <Rows>{a.why.map((w, i) => <Row key={i} number={i + 1} name={w} />)}</Rows>
            <Callout title="كيف تقرأ المناطق" tone="note">مناطق التجميع هي أقرب ثلاثة دعوم من أدنى 30 يوما (± ربع ATR)، بحيث تتوزع الشراءات على دفعات بدل دفعة واحدة. الأهداف هي أقرب مقاومة أو عقدة حجم عالٍ أو حافة منطقة القيمة فوقها، وتُباع عندها أجزاء. مستوى إعادة التقييم ليس أمر وقف، بل نقطة تتوقف عندها عن الإضافة وتراجع الفكرة لأنك تملك الأصل ولا تبيع بالخسارة تلقائيا. حجم الدفعات وما يناسب رأس مالك قرارك.</Callout>
            <Callout title="حدود هذه التوصية" tone="warning">اختبارات المعمل: شراء الهبوط على دفعات خسر أقل من الاحتفاظ لكنه ظل خاسرا في هذه الفترة الهابطة، والعينات صغيرة. السعر قد يواصل النزول بعد كل دفعة، خاصة وقت الأخبار. الحكم الشرعي على كل أصل يرجع لك أو لمرجعك، وهنا بيانات فقط.</Callout>
        </Group>
    </>;
}
