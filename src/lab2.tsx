import React, { useEffect, useState } from 'react';
import { Callout, Caption, Facts, Group, Row, Rows } from '@instinct/files';
import labData from './data/lab.json';

const f = (v: number) => v >= 1000 ? v.toLocaleString('en-US', { maximumFractionDigits: 0 }) : v >= 100 ? v.toFixed(1) : v.toFixed(2);
const nm = (x: string) => x === 'XAUTUSDT' ? 'الذهب XAUT' : x.replace('USDT', '');

export function VpNow({ coin }: { coin: string }) {
    const n = (labData as any).coins[coin].now;
    const p = n.px as number;
    const pos = p > n.vah ? 'فوق منطقة القيمة' : p < n.val ? 'تحت منطقة القيمة' : 'داخل منطقة القيمة';
    const hv: number[] = n.hvn, lv: number[] = n.lvn;
    const hvB = hv.filter(x => x <= p).slice(-1)[0], hvA = hv.find(x => x > p);
    const lvB = lv.filter(x => x <= p).slice(-1)[0], lvA = lv.find(x => x > p);
    const up = n.vfi > n.vfi_prev, neg = n.vfi < 0;
    const flow = `${neg ? 'تحت الصفر' : 'فوق الصفر'} ${up ? 'ويرتفع' : 'وينخفض'} (قيمة ${n.vfi.toFixed(3)})`;
    const read: string[] = [`السعر ${f(p)} ${pos} (VAL ${f(n.val)}، POC ${f(n.poc)}، VAH ${f(n.vah)}).`];
    if (p < n.val) read.push(`السعر بعيد عن POC بمقدار ${(((n.poc / p) - 1) * 100).toFixed(1)} بالمئة. هذا ما تفترضه استراتيجية الارتداد، لكنها خسرت في الاختبار.`);
    read.push(`تدفق الحجم ${flow}. ${neg ? 'لم تظهر إشارة شراء VFI بعد (تحتاج عبورا فوق الصفر).' : 'الإشارة الشرائية لـ VFI قائمة.'}`);
    return <Group label={`التحليل الحالي: بروفايل الحجم وتدفق الحجم لـ ${nm(coin)}`} heading>
        <Facts items={[
            { label: 'السعر (آخر شمعة ساعة)', value: f(p) },
            { label: 'أعلى حجم POC', value: f(n.poc) },
            { label: 'منطقة القيمة VAL إلى VAH', value: `${f(n.val)} إلى ${f(n.vah)}` },
            { label: 'عقدة حجم عالٍ HVN أقرب تحت السعر', value: hvB ? f(hvB) : 'لا يوجد' },
            { label: 'HVN أقرب فوق السعر', value: hvA ? f(hvA) : 'لا يوجد' },
            { label: 'فجوة حجم LVN أقرب تحت', value: lvB ? f(lvB) : 'لا يوجد' },
            { label: 'LVN أقرب فوق', value: lvA ? f(lvA) : 'لا يوجد' },
            { label: 'تدفق الحجم VFI', value: flow },
        ]} />
        <Callout title="قراءة وصفية" tone="note">{read.join(' ')} هذا وصف للبيانات وليس توقعا. بروفايل آخر 30 يوما من شموع الساعة. {n.vfi_days < 200 ? `VFI محسوب على ${n.vfi_days} يوما فقط.` : ''}</Callout>
        <Caption>HVN: مناطق ازدحام يُتوقع أن تتفاعل معها الأسعار (دعم أو مقاومة محتملة). LVN: مناطق حجم قليل يمر السعر فيها بسرعة عادة. التفاعل ليس مضمونا.</Caption>
    </Group>;
}

type Lvl = [string, string];
export function Book({ coin }: { coin: string }) {
    const [d, setD] = useState<any>(null);
    const [err, setErr] = useState('');
    useEffect(() => {
        let on = true;
        const load = () => fetch(`https://data-api.binance.vision/api/v3/depth?symbol=${coin}&limit=500`).then(r => r.json()).then(j => { if (on) { setD(j); setErr(''); setT(new Date()); } }).catch(() => on && setErr('تعذر جلب دفتر الأوامر'));
        setD(null); load();
        const id = setInterval(load, 30000);
        return () => { on = false; clearInterval(id); };
    }, [coin]);
    const [t, setT] = useState<Date | null>(null);
    if (err && !d) return <Callout title="دفتر الأوامر" tone="note">{err}</Callout>;
    if (!d) return <Caption>جار تحميل دفتر الأوامر...</Caption>;
    const bids: [number, number][] = (d.bids as Lvl[]).map(([p, q]) => [+p, +q]);
    const asks: [number, number][] = (d.asks as Lvl[]).map(([p, q]) => [+p, +q]);
    const bb = bids[0][0], ba = asks[0][0], mid = (bb + ba) / 2;
    const spread = ba - bb, bps = spread / mid * 1e4;
    const nt = (a: [number, number][]) => a.reduce((s, x) => s + x[0] * x[1], 0);
    const win = (pct: number) => { const B = nt(bids.filter(x => x[0] >= mid * (1 - pct))), A = nt(asks.filter(x => x[0] <= mid * (1 + pct))); return { B, A, im: B + A ? (B - A) / (B + A) : 0 }; };
    const top = (a: [number, number][]) => { const B = nt(a.slice(0, 20)); return B; };
    const w5 = win(0.005), w1 = win(0.001), wall = (a: [number, number][]) => a.reduce((m, x) => x[0] * x[1] > m[0] * m[1] ? x : m, a[0]);
    const bw = wall(bids), aw = wall(asks);
    const med = (a: [number, number][]) => { const v = a.map(x => x[0] * x[1]).sort((x, y) => x - y); return v[Math.floor(v.length / 2)] || 1; };
    const bwr = bw[0] * bw[1] / med(bids), awr = aw[0] * aw[1] / med(asks);
    const im20 = (top(bids) - top(asks)) / (top(bids) + top(asks));
    const lean = w5.im > 0.25 ? 'ميل شراء في الدفتر' : w5.im < -0.25 ? 'ميل بيع في الدفتر' : 'دفتر متوازن';
    const pct = (x: number) => `${(x * 100).toFixed(0)} بالمئة`;
    const m = (x: number) => x >= 1e6 ? `${(x / 1e6).toFixed(2)} مليون` : x >= 1e3 ? `${(x / 1e3).toFixed(0)} ألف` : x.toFixed(0);
    return <Group label={`دفتر الأوامر الحي لـ ${nm(coin)} (بحث حي فقط)`} heading>
        <Callout title={`القراءة الآن: ${lean}`} tone="note">اختلال السيولة ضمن 0.5 بالمئة من السعر: {pct(w5.im)} (موجب يعني سيولة الشراء أكبر). هذه لقطة لحظية. الدفتر يتغير بسرعة وقد تكون الجدران وهمية وتُسحب قبل التنفيذ، ولا يمكن اختبارها على التاريخ لأن بينانس لا تحفظ عمق الدفتر.</Callout>
        <Facts items={[
            { label: 'أفضل شراء / بيع', value: `${f(bb)} / ${f(ba)}` },
            { label: 'السبريد', value: `${spread.toFixed(spread < 1 ? 3 : 2)} (${bps.toFixed(1)} نقطة أساس)` },
            { label: 'سيولة الشراء / البيع ضمن 0.1 بالمئة', value: `${m(w1.B)} / ${m(w1.A)} USDT` },
            { label: 'سيولة الشراء / البيع ضمن 0.5 بالمئة', value: `${m(w5.B)} / ${m(w5.A)} USDT` },
            { label: 'الاختلال لأفضل 20 مستوى', value: pct(im20) },
            { label: 'أكبر جدار شراء', value: `${f(bw[0])} بحجم ${m(bw[0] * bw[1])} USDT، ${((1 - bw[0] / mid) * 100).toFixed(2)} بالمئة تحت السعر${bwr >= 5 ? ' (بارز)' : ''}` },
            { label: 'أكبر جدار بيع', value: `${f(aw[0])} بحجم ${m(aw[0] * aw[1])} USDT، ${((aw[0] / mid - 1) * 100).toFixed(2)} بالمئة فوق السعر${awr >= 5 ? ' (بارز)' : ''}` },
        ]} />
        <Rows>{[
            ['قاعدة الاستراتيجية (غير مختبرة)', 'ميل شراء إذا كان اختلال 0.5 بالمئة أكبر من +25 بالمئة، وميل بيع إذا أقل من -25 بالمئة، وإلا توازن. الجدار يُعد بارزا إذا زاد حجمه على 5 أضعاف متوسط المستويات.'],
            ['لماذا لا اختبار تاريخي', 'بينانس تعطي الدفتر الحالي فقط. للاختبار لازم تسجيل لقطات الدفتر عبر الوقت، وهذا يحتاج مهمة مراقبة منفصلة وأقترحه كخطوة قادمة.'],
        ].map(([a, b], i) => <Row key={a} number={i + 1} name={a} detail={b} />)}</Rows>
        <Caption>آخر تحديث {t ? t.toLocaleTimeString('ar-EG') : ''}، يتجدد كل 30 ثانية. مصدر عمق بينانس سبوت العام.</Caption>
    </Group>;
}
