import React, { useEffect, useState } from 'react';
import { Callout, Caption, Facts, Group, Header, Row, Rows } from '@instinct/files';
import prog from './data/progress.json';
import hist from './data/history.json';
import lab from './data/lab.json';
import research from './data/research.json';
import scalp from './data/scalp.json';

const B = 'https://data-api.binance.vision/api/v3';
const COINS = ['XAUTUSDT', 'BNBUSDT', 'ETHUSDT', 'SOLUSDT'];
const hhmm = (d: Date) => d.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

export function Src({ s, t, kind }: { s: string; t?: string; kind: 'مقاس' | 'فرضية' | 'محاكاة' | 'ذكاء اصطناعي' | 'حي' }) {
    return <Caption>[{kind}] المصدر: {s}{t ? ` | الوقت: ${t}` : ''}</Caption>;
}

function Cross() {
    const [rows, setRows] = useState<any[]>([]); const [at, setAt] = useState<Date | null>(null); const [err, setErr] = useState('');
    const run = () => {
        Promise.all(COINS.map(async s => {
            const [a, b, c] = await Promise.all([fetch(`${B}/ticker/price?symbol=${s}`).then(r => r.json()), fetch(`${B}/ticker/bookTicker?symbol=${s}`).then(r => r.json()), fetch(`${B}/avgPrice?symbol=${s}`).then(r => r.json())]);
            const p = +a.price, mid = (+b.bidPrice + +b.askPrice) / 2, avg = +c.price;
            return { s, p, mid, avg, d1: (mid / p - 1) * 100, d2: (avg / p - 1) * 100 };
        })).then(r => { setRows(r); setAt(new Date()); setErr(''); }).catch(() => setErr('تعذر الجلب الآن'));
    };
    useEffect(() => { run(); const i = setInterval(run, 60000); return () => clearInterval(i); }, []);
    const age = at ? (Date.now() - at.getTime()) / 1000 : 1e9;
    return <Group label="مقارنة السعر عبر ثلاث نقاط من Binance (حي)" heading>
        {err && <Callout title="خطأ" tone="warning">{err}</Callout>}
        {rows.length > 0 && <Rows>{rows.map((r, j) => {
            const bad = Math.abs(r.d1) > 0.3;
            return <Row key={r.s} number={j + 1} name={`${r.s.replace('USDT', '')} ${bad ? '(تباين)' : '(متطابق)'}`} detail={`آخر سعر ${r.p} | منتصف الدفتر ${r.mid.toFixed(2)} (${r.d1 >= 0 ? '+' : ''}${r.d1.toFixed(3)}%) | متوسط 5 دقائق ${r.avg.toFixed(2)} (${r.d2 >= 0 ? '+' : ''}${r.d2.toFixed(3)}%)`} />;
        })}</Rows>}
        {at && <Src s="data-api.binance.vision: ticker/price و bookTicker و avgPrice" t={hhmm(at)} kind="مقاس" />}
        {at && age > 120 && <Callout title="بيانات قديمة" tone="warning">آخر تحديث منذ أكثر من دقيقتين.</Callout>}
        <Callout title="حدود المقارنة" tone="note">النقاط الثلاث من نفس البورصة، فهي تكشف خللا في الجلب أو اتساعا غير عادي للفارق، لكنها ليست مصدرا مستقلا. مصدر خارجي مستقل يحتاج إضافته وفحص أنه يعمل من المتصفح. التباين المعتمد: 0.3 بالمئة بين آخر سعر ومنتصف الدفتر. متوسط الخمس دقائق يختلف طبيعيا عن اللحظي.</Callout>
    </Group>;
}

function ageH(iso?: string | number | null) { if (!iso) return null; const t = typeof iso === 'number' ? iso : new Date(iso).getTime(); return isNaN(t) ? null : (Date.now() - t) / 3600000; }

function Freshness() {
    const items: [string, string | number | null | undefined, number, string][] = [
        ['التاريخ اليومي (history)', (hist as any)._saved, 26, 'السكربت اليومي 08:30'],
        ['معمل الاستراتيجيات (lab)', (lab as any).generated, 26, 'السكربت اليومي 08:30'],
        ['ملاحظات الأبحاث', (research as any).updated?.replace(' ', 'T') + ':00+02:00', 72, 'ما يرسله فريق البحث، يُنشر مع كل تحديث'],
        ['سجل الديمو الحي', (scalp as any).updated, 24, 'قناة التداول التجريبي، يُنشر مع كل تحديث'],
    ];
    return <Group label="عمر البيانات المخزنة" heading>
        <Rows>{items.map(([n, t, lim, how], j) => { const a = ageH(t as any); const st = a == null ? 'غير متاح (لم يبدأ)' : a > lim ? `قديمة: ${a.toFixed(0)} ساعة (الحد ${lim})` : `حديثة: ${a.toFixed(1)} ساعة`; return <Row key={n} number={j + 1} name={n} detail={`${st} | يصل عبر: ${how}`} />; })}</Rows>
        <Caption>يقاس العمر عند فتح الصفحة، وهذه الكتل لا تتحدث إلا عند إعادة النشر.</Caption>
    </Group>;
}

function Progress() {
    const P: any = prog;
    const mark = (ok: boolean | null) => ok === null ? 'لم يُقس' : ok ? 'تحقق' : 'لم يتحقق';
    return <Group label={`تقدم الاستراتيجيات نحو هدف ${P.target} بالمئة`} heading>
        <Callout title="شروط العرض كتوصية" tone="warning">نجاح {P.target} بالمئة أو أكثر على {P.minTrades} صفقة فأكثر، وصافي موجب بعد الرسوم، وتراجع محدود، والتحقق خارج العينة. لا تعرض أي استراتيجية كمحققة للهدف قبل قياس كل الشروط.</Callout>
        <Rows>{P.rows.map((r: any, j: number) => {
            const c1 = r.trades >= P.minTrades, c2 = r.win == null ? null : r.win >= P.target, c3 = r.net == null ? null : r.net > 0, c4 = r.dd == null ? null : r.dd > -20, c5 = null;
            const all = c1 && c2 === true && c3 === true && c4 === true;
            return <Row key={j} number={j + 1} name={`${r.name} [${r.kind}] ${all ? '' : '(لم تحقق الهدف)'}`} detail={`الصفقات ${r.trades} من ${P.minTrades} (${mark(c1)}) | النجاح ${r.win == null ? 'لم يُقس' : r.win + '% من ' + P.target + '% (' + mark(c2) + ')'} | الصافي بعد الرسوم ${r.net == null ? 'لم يُقس' : r.net + '% (' + mark(c3) + ')'} | أقصى تراجع ${r.dd == null ? 'لم يُقس' : r.dd + '%'} | خارج العينة: ${r.oos} | المصدر: ${r.src}`} />;
        })}</Rows>
        <Src s="research.json و progress.json (قناة البحث والمعمل)" t={P.updated} kind="مقاس" />
        <Caption>حد التراجع المحدود المستخدم هنا مؤقتا: أقل من 20 بالمئة، وهو افتراض للمراجعة وليس قاعدة معتمدة.</Caption>
    </Group>;
}

function Registry() {
    const S = [
        ['الأسعار والشموع والدفتر', 'Binance العامة (data-api.binance.vision)', 'جلب مباشر من المتصفح كل 60 ثانية'],
        ['التاريخ اليومي والمعمل', 'شموع Binance، سكربت يومي', 'إعادة النشر 08:30'],
        ['الزلازل والكوارث', 'USGS و GDACS', 'جلب مباشر من المتصفح'],
        ['التقويم والإصدارات', 'BEA و DOL ومصادر التقويم الاقتصادي', 'عبر وكيل التقويم ثم إعادة النشر'],
        ['الأبحاث والمحاكاة وسجل الديمو', 'قناة السكالبنج على حساب Binance التجريبي', 'عبر الوكيل ثم إعادة النشر'],
        ['المحلل التفاعلي', 'شموع Binance الحية، يحسب في المتصفح', 'مباشر'],
        ['التعليق بالذكاء الاصطناعي', 'غير مفعل بعد', 'يُضاف لاحقا، وسيُوسم، ولن يعرض رقما غير موجود في البيانات المحسوبة'],
    ];
    return <Group label="مصادر البيانات وكيف تصل" heading>
        <Rows>{S.map(([a, b, c], j) => <Row key={a} number={j + 1} name={a} detail={`${b} | ${c}`} />)}</Rows>
        <Callout title="معنى الوسوم" tone="note">مقاس: محسوب من بيانات حقيقية. محاكاة: نتيجة اختبار على بيانات تاريخية، وليست صفقات حية. حي: من الحساب التجريبي. فرضية: لم تُختبر. ذكاء اصطناعي: نص مولد، يُقبل فقط لو كل رقم فيه موجود في بيانات محسوبة.</Callout>
    </Group>;
}

export function Trust() {
    return <>
        <Header title="التحقق والمصادر" fact="لا استراتيجية حققت الهدف" intro="كل رقم في اللوحة يجب أن يُنسب لمصدر ووقت ووسم. هنا مقارنات السعر الحية وعمر البيانات المخزنة وتقدم كل استراتيجية نحو هدف النجاح." />
        <Cross />
        <Freshness />
        <Progress />
        <Registry />
    </>;
}
