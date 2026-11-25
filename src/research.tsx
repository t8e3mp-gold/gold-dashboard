import { Callout, Caption, Facts, Group, Header, Row, Rows } from '@instinct/files';
import R from './data/research.json';
import scalp from './data/scalp.json';
const d: any = R;
export function Research() {
    const T: any[] = (scalp as any).trades || [];
    const closed = T.filter(t => t.exit != null);
    const w = closed.filter(t => t.pct > 0).length;
    return <>
        <Header title="المخزن والمصنع" fact="لا ميزة حتى الآن" intro="مرجع كل ما قسناه وجربناه في التداول القصير على XAUT. كل بند موسوم: مقاس (من بيانات حقيقية) أو فرضية (لم تُختبر). أموال وهمية، سبوت فقط، ولا شيء على GitHub." />
        <Group label="نتائج الاختبار التاريخي حسب الإطار الزمني" heading>
            <Rows>{d.backtests.map((b: any, j: number) => <Row key={j} number={j + 1} name={b.tf} detail={b.status} />)}</Rows>
            <Callout title="ملاحظة" tone="note">الاستراتيجيات: RSI مع بولينجر، حجم مع EMA، وشراء الهبوط وبيع الصعود. تُملأ الأرقام التفصيلية لكل إطار فور وصولها. الفراغ يعني لم تصل، وليس صفرا.</Callout>
        </Group>
        <Group label="الاستكشاف من الأساس (مقاس)" heading>
            <Rows>{d.findings.map((x: any, j: number) => <Row key={j} number={j + 1} name={`${x[0]} [${x[2]}]`} detail={x[1]} />)}</Rows>
        </Group>
        <Group label="محاكاة 1000 صفقة (مقاس بالمحاكاة)" heading>
            <Rows>{d.sim.map((x: any, j: number) => <Row key={j} number={j + 1} name={x[0]} detail={x[1]} />)}</Rows>
        </Group>
        <Group label="التذبذب حسب الجلسة بتوقيت القاهرة (مقاس، 208 يوما، شموع ساعة)" heading>
            <Rows>{d.sessions.map((x: any, j: number) => <Row key={j} number={j + 1} name={x[0]} detail={x[1]} />)}</Rows>
            <Caption>الحدود قد تنزاح ساعة بسبب التوقيت الصيفي المصري في جزء من العينة. الذهب يتداول 24 ساعة لكن السيولة تتبع لندن ونيويورك. الأخبار وقت الإصدار تكبر الشمعة نحو 50 بالمئة بلا اتجاه ثابت (قياس أولي).</Caption>
        </Group>
        <Group label="قواعد الأخبار والمخاطرة (قواعد معتمدة)" heading>
            <Rows>{d.rules.map((x: any, j: number) => <Row key={j} number={j + 1} name={x[0]} detail={x[1]} />)}</Rows>
        </Group>
        <Group label="مسجل عمق دفتر الأوامر" heading>
            <Facts items={[{ label: 'الحالة', value: d.depth.status }]} />
            <Callout title="التفاصيل" tone="note">{d.depth.detail} الفرضية: اختلال الدفتر قد يتنبأ بحركة 1 إلى 5 دقائق، وهي لم تُختبر بعد.</Callout>
        </Group>
        <Group label="الصفقات الحية في الديمو" heading>
            <Facts items={[
                { label: 'مغلقة', value: String(closed.length) },
                { label: 'رابحة', value: String(w) },
                { label: 'خاسرة', value: String(closed.length - w) },
                { label: 'نسبة النجاح', value: closed.length ? Math.round(100 * w / closed.length) + ' بالمئة' : 'لا صفقات بعد' },
            ]} />
            <Caption>التفاصيل والأسباب في تبويب التداول. آخر تحديث لهذه الصفحة: {d.updated}.</Caption>
        </Group>
    </>;
}
