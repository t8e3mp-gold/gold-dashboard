import React, { useEffect, useState } from 'react';
import { Callout, Caption, Facts, Group, Header, Row, Rows } from '@instinct/files';

type Ev = { at: string; name: string; imp: 'عالي' | 'متوسط' | 'منخفض'; fc: string; prev: string; act?: string; note: string };
// الأوقات بتوقيت القاهرة (UTC+2). المصدر: helious.io/calendar الأسبوع 2026-w48
const EVENTS: Ev[] = [
    { at: '2026-11-25T15:30:00+02:00', name: 'مؤشر PCE الأساسي (شهري)', imp: 'عالي', fc: '0.3', prev: '0.3', act: '0.3', note: 'مقياس التضخم المفضل للفيدرالي. وصفيا: رقم أعلى من المتوقع يعزز الدولار والعوائد وغالبا يضغط على الذهب والعملات الرقمية، والأقل من المتوقع العكس.' },
    { at: '2026-11-25T15:30:00+02:00', name: 'مؤشر PCE الأساسي (سنوي)', imp: 'عالي', fc: '3.2', prev: '3.1', act: '3.3', note: 'نفس منطق التضخم أعلاه.' },
    { at: '2026-11-25T15:30:00+02:00', name: 'الناتج المحلي الأمريكي (سنوي)', imp: 'عالي', fc: '3.4', prev: '3.4', note: 'نمو أقوى من المتوقع يدعم الدولار عادة، وهو أقل ارتباطا بالذهب من التضخم.' },
    { at: '2026-11-25T15:30:00+02:00', name: 'طلبات إعانة البطالة', imp: 'متوسط', fc: '200 ألف', prev: '203 ألف', note: 'سوق العمل يؤثر على توقعات الفائدة.' },
    { at: '2026-11-25T15:30:00+02:00', name: 'طلبيات السلع المعمرة', imp: 'متوسط', fc: '0.4', prev: '1.8', note: 'تأثير محدود عادة.' },
    { at: '2026-11-25T15:30:00+02:00', name: 'PCE الكلي (شهري / سنوي)', imp: 'عالي', fc: 'سنوي 3.8', prev: 'شهري 0.5 / سنوي 3.6', act: 'شهري 0.3 / سنوي 3.8', note: 'المصدر: BEA، الدخل والإنفاق الشخصي أكتوبر 2026. الحقيقي PCE نحو 0.0 بالمئة.' },
    { at: '2026-11-25T15:30:00+02:00', name: 'الدخل والإنفاق الشخصي', imp: 'متوسط', fc: '0.4 لكل منهما', prev: 'الدخل 0.3 والإنفاق 0.6', act: 'الدخل +0.7 والإنفاق +0.3', note: 'يصدر مع PCE فيزيد التذبذب في نفس النافذة.' },
    { at: '2026-11-25T17:00:00+02:00', name: 'مبيعات المنازل الجديدة', imp: 'منخفض', fc: '0.65 مليون', prev: 'غير متاح', note: 'تأثير محدود على العملات.' },
    { at: '2026-11-25T21:00:00+02:00', name: 'الكتاب البيج للفيدرالي', imp: 'متوسط', fc: 'لا يوجد رقم', prev: 'غير متاح', note: 'نص وصفي لحال الاقتصاد. قد يحرك التوقعات عن الفائدة.' },
];
const BEFORE = 60, AFTER = 120; // دقائق: نافذة الحذر حول الأحداث العالية
const fmt = (s: string) => new Date(s).toLocaleString('ar-EG', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Africa/Cairo' });

function status(e: Ev, now: number) {
    const t = new Date(e.at).getTime(), m = (t - now) / 60000;
    if (m > 0) return { s: 'قادم', mins: m };
    return { s: 'صدر', mins: m };
}
function caution(now: number) {
    const hi = EVENTS.filter(e => e.imp === 'عالي').map(e => (new Date(e.at).getTime() - now) / 60000);
    const next = hi.filter(m => m > 0).sort((a, b) => a - b)[0];
    const last = hi.filter(m => m <= 0).sort((a, b) => b - a)[0];
    if (next !== undefined && next <= BEFORE) return { tone: 'warning' as const, t: 'قبل خبر عالي التأثير', x: `بعد ${Math.round(next)} دقيقة صدور عالي التأثير. السيولة والفروقات قد تتغير بسرعة.` };
    if (last !== undefined && last > -AFTER) return { tone: 'warning' as const, t: last > -15 ? 'لحظة الخبر' : 'بعد الخبر', x: `مر ${Math.round(-last)} دقيقة على صدور عالي التأثير. الحركة بعد الأخبار غالبا متقلبة وقد تنعكس.` };
    return { tone: 'note' as const, t: 'لا نافذة حذر الآن', x: next !== undefined ? `أقرب خبر عالي التأثير بعد ${Math.round(next / 60 * 10) / 10} ساعة.` : 'لا أخبار عالية التأثير مسجلة قادمة.' };
}

const ALERTS = [
    { d: '25 نوفمبر 14:06', t: 'تنبيه XAUT هبوط 0.74 بالمئة', x: 'من 3517.71 إلى 3491.73.' },
    { d: '25 نوفمبر 09:53', t: 'تنبيه ETH هبوط 2.562 بالمئة', x: 'من 1683.46 إلى 1640.35.' },
    { d: '25 نوفمبر 08:17', t: 'تنبيه XAUT هبوط 0.556 بالمئة', x: 'من 3537.16 إلى 3517.71، تحت أول دعم 3527.5 (أدنى 30 يوم).' },
    { d: '25 نوفمبر 02:21', t: 'تنبيه XAUT هبوط 0.566 بالمئة', x: 'من المرجع 3557.28 إلى 3537.16 خلال فترة المراقبة. التنبيه أرسل عبر واتساب.' },
];

type Q = { id: string; mag: number; place: string; time: number };
type D = { id: string; type: string; name: string; level: string; date: string };
const TYPE: Record<string, string> = { EQ: 'زلزال', TC: 'إعصار', FL: 'فيضان', VO: 'بركان', DR: 'جفاف', WF: 'حرائق' };

export function Radar() {
    const [now] = useState(() => Date.now());
    const [q, setQ] = useState<Q[] | null>(null);
    const [d, setD] = useState<D[] | null>(null);
    const [err, setErr] = useState('');
    useEffect(() => {
        fetch('https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson').then(r => r.json())
            .then(j => setQ(j.features.filter((f: any) => f.properties.mag >= 5.5).map((f: any) => ({ id: f.id, mag: f.properties.mag, place: f.properties.place || 'موقع غير محدد', time: f.properties.time }))))
            .catch(() => setErr('تعذر جلب الزلازل'));
        const from = new Date(Date.now() - 10 * 864e5).toISOString().slice(0, 10), to = new Date().toISOString().slice(0, 10);
        fetch(`https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?alertlevel=Orange;Red&eventlist=EQ;TC;FL;VO&fromdate=${from}&todate=${to}`).then(r => r.text()).then(t => (t ? JSON.parse(t) : { features: [] }))
            .then(j => setD(j.features.map((f: any) => ({ id: String(f.properties.eventid) + f.properties.eventtype, type: f.properties.eventtype, name: f.properties.name, level: f.properties.alertlevel, date: f.properties.fromdate || '' }))))
            .catch(() => setErr('تعذر جلب الكوارث'));
    }, []);
    const c = caution(now);
    const sorted = [...EVENTS].sort((a, b) => +new Date(a.at) - +new Date(b.at));
    return <>
        <Header title="الأخبار والتقويم" intro="الأحداث القادمة والسابقة وتأثيرها الوصفي على الذهب وBNB وETH وSOL. بحث وتوثيق فقط، وليس توقعا ولا نصيحة تداول." />
        <Callout title={`حالة الحذر: ${c.t}`} tone={c.tone}>{c.x} هذه علامة بحثية فقط. نافذتها: {BEFORE} دقيقة قبل الخبر العالي و{AFTER} دقيقة بعده. القرار قرارك.</Callout>
        <Group label="التقويم الاقتصادي الأمريكي، 25 نوفمبر (بتوقيت القاهرة)" heading>
            <Rows>{sorted.map((e, i) => { const st = status(e, now); return <Row key={e.name} number={i + 1} name={`${e.name} (${e.imp})`} detail={`${st.s}، ${fmt(e.at)}. المتوقع ${e.fc}، السابق ${e.prev}${e.act ? `، الفعلي ${e.act}` : ''}. ${e.note}`} />; })}</Rows>
            <Caption>الحالة تحسب من ساعة جهازك عند فتح الصفحة. القيم الفعلية تضاف مع التحديث اليومي أو عند طلبها.</Caption>
        </Group>
        <Group label="الجيوسياسة والكوارث (حي من مصادر عامة)" heading>
            {err && <Callout title="تنبيه" tone="note">{err}</Callout>}
            <Rows>{(d || []).slice(0, 8).map((e, i) => <Row key={e.id} number={i + 1} name={`${TYPE[e.type] || e.type}، مستوى ${e.level === 'Red' ? 'أحمر' : 'برتقالي'}`} detail={`${e.name}. ${e.date.slice(0, 10)}. مصدر GDACS.`} />)}</Rows>
            <Rows>{(q || []).slice(0, 6).map((e, i) => <Row key={e.id} number={i + 1} name={`زلزال ${e.mag}`} detail={`${e.place}. ${new Date(e.time).toLocaleString('ar-EG', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Africa/Cairo' })}. مصدر USGS.`} />)}</Rows>
            {d && q && !d.length && !q.length && <Caption>لا كوارث كبرى في المصدرين خلال الفترة.</Caption>}
            <Callout title="التأثير على العملات" tone="note">الكوارث الطبيعية نادرا ما تحرك الذهب أو العملات الرقمية إلا إذا ضربت منطقة اقتصادية كبرى. الحروب والانقلابات والعقوبات تؤثر عادة عبر الملاذ الآمن، فيدعم الذهب أحيانا، ويتذبذب الكريبتو، لكن الأثر غير مضمون ويتغير من حدث لآخر.</Callout>
            <Callout title="ما لا أستطيع جلبه تلقائيا" tone="note">لا يوجد مصدر مجاني بلا مفاتيح يسمح لصفحة اللوحة بجلب أخبار الحروب والانقلابات مباشرة (المصادر المجانية تحدد عدد الطلبات). هذه تضاف يدويا من البحث اليومي، ولا توجد أحداث منها مسجلة الآن.</Callout>
        </Group>
        <Group label="سجل التنبيهات" heading>
            <Rows>{ALERTS.map((e, i) => <Row key={e.d} number={i + 1} name={e.t} detail={`${e.d}. ${e.x}`} />)}</Rows>
            <Caption>التنبيهات تصل إليك على واتساب. هنا تسجيل لها يتجدد مع كل نسخة من اللوحة، وليس لحظيا.</Caption>
        </Group>
        <Group label="مصادر الأخبار" heading>
            <Facts items={[
                { label: 'التقويم الاقتصادي', value: 'helious.io/calendar (الأوقات تحول إلى القاهرة)' },
                { label: 'الزلازل', value: 'USGS، الزلازل المهمة في آخر أسبوع، حي' },
                { label: 'الكوارث', value: 'GDACS (الأمم المتحدة والمفوضية الأوروبية)، مستويات برتقالي وأحمر، حي' },
                { label: 'الأسعار', value: 'بينانس سبوت العامة' },
                { label: 'قراءات التحليل', value: 'TradingView عبر قراءتك المرسلة' },
            ]} />
        </Group>
    </>;
}
