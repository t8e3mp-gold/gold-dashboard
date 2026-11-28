"use strict";
const APP_VERSION = 18; // bump when the page code changes; data files carry the version they expect
// All data is rendered with textContent only. No HTML from data files is ever injected.
const LABELS = {measured:"مقاس", simulated:"محاكاة", live:"حي", hypothesis:"فرضية", ai:"ذكاء اصطناعي"};
const $ = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };
// Time: never trust the phone clock. Offset = server time (HTTP Date + Age headers) minus phone time.
let offsetMs = Number(localStorage.getItem("gd-offset") || 0), offline = false, bust = String(Math.floor(Date.now() / 6e4));
const nowMs = () => Date.now() + offsetMs;
const ageH = ts => (nowMs() - Date.parse(ts)) / 36e5;

// Cairo time first, UTC second (display only). Source names in Arabic for the Arabic UI.
const cairoFmt = new Intl.DateTimeFormat("en-GB", {timeZone: "Africa/Cairo", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"});
function cairoStr(ms) { const o = {}; cairoFmt.formatToParts(new Date(ms)).forEach(x => { o[x.type] = x.value; }); return o.year + "-" + o.month + "-" + o.day + " " + o.hour + ":" + o.minute + ":" + o.second; }
function timeEl(ms) { const f = document.createDocumentFragment(), x = $("bdi", null, cairoStr(ms)), u = $("bdi", null, "UTC " + new Date(ms).toISOString().slice(11, 19)); x.dir = "ltr"; u.dir = "ltr"; f.append(x, " بتوقيت القاهرة (", u, ")"); return f; }
const arSrc = t => String(t).replace(/klines module \(Binance public data\), daily candles closed at 00:00 UTC/g, "وحدة الشموع (بيانات باينانس العامة)، شموع يومية تُقفل 00:00 UTC").replace(/1h candles, last hour of the same day/g, "شموع الساعة، آخر ساعة في نفس اليوم").replace(/recommendation and klines modules \(Binance public data\), scored on real later candles/g, "وحدتا التوصية والشموع (بيانات باينانس العامة)، وتُقيَّم بشموع حقيقية لاحقة").replace(/Al Jazeera RSS, Federal Reserve press RSS, ECB press RSS, Fed FOMC calendar, BEA release schedule/g, "خلاصات الجزيرة، بيانات الاحتياطي الفيدرالي والبنك المركزي الأوروبي، تقويم الفيدرالي، جدول مكتب التحليل الاقتصادي").replace(/levels, news and backtest modules \(computed rules, no AI\)/g, "وحدات المستويات والأخبار والاختبار الرجعي (قواعد محسوبة بدون ذكاء اصطناعي)").replace(/Binance public klines history \(downloaded earlier\); backtest results saved in this repo, not fetched live/g, "تاريخ شموع باينانس العامة (اتحمّل قبل كده)، ونتائج الاختبار الرجعي محفوظة في المستودع وما بتتجابش لحظيا").replace(/klines and volume-profile modules \(Binance public data\)/g, "وحدتا الشموع وبروفايل الحجم (بيانات باينانس العامة)").replace(/Cross-check results of the other modules/g, "نتائج الفحص المتبادل للوحدات الأخرى").replace(/Runner system clock \(UTC\)/g, "ساعة جهاز التشغيل (UTC)").replace(/klines module 1h volume over the same whole hours/g, "حجم الساعة من وحدة الشموع على نفس الساعات الكاملة").replace(/klines and flow modules \(Binance\)/g, "وحدتا الشموع والتدفق (باينانس)").replace(/OKX spot candles/g, "شموع أو كي إكس الفورية").replace(/OKX spot tickers/g, "أسعار أو كي إكس الفورية").replace(/, 1m candles/g, "، شموع الدقيقة").replace(/\(taker buy volume\)/g, "(حجم الشراء المبادر)").replace(/Binance aggTrades summed for the last closed hour/g, "مجموع الصفقات المجمعة من باينانس لآخر ساعة مغلقة").replace(/klines module volume \(same exchange\)/g, "حجم وحدة الشموع (نفس المنصة)").replace(/taker buy volume/g, "حجم الشراء المبادر").replace(/aggTrades/g, "الصفقات المجمعة").replace(/Binance public data mirror/g, "مرآة بيانات باينانس العامة").replace(/Binance/g, "باينانس").replace(/OKX/g, "أو كي إكس").replace(/Gate\.io/g, "جيت").replace(/\bbinance\b/g, "باينانس").replace(/\bokx\b/g, "أو كي إكس").replace(/\bgate\b/g, "جيت").replace(/klines/g, "الشموع").replace(/flow/g, "التدفق");

async function getJSON(p, track) {
  const r = await fetch(p + "?v=" + bust, {cache: "no-store"});
  if (!r.ok) throw new Error(p + " " + r.status);
  if (r.headers.get("x-sw-cache")) offline = true;
  else if (track && r.headers.get("date")) {
    const srv = Date.parse(r.headers.get("date")) + 1000 * Number(r.headers.get("age") || 0);
    if (!isNaN(srv)) { offsetMs = srv - Date.now(); localStorage.setItem("gd-offset", String(offsetMs)); }
  }
  return r.json();
}

function badge(mod, rec) {
  const wrap = $("span");
  wrap.append($("span", "pill p-lbl", LABELS[rec.label] || rec.label));
  const a = ageH(rec.fetched_at);
  const stale = a > rec.max_age_hours || mod.status !== "ok";
  wrap.append($("span", "pill " + (stale ? "p-bad" : "p-ok"), stale ? "قديمة" : "محدّثة"));
  return {wrap, a};
}

function candleView(cs) {
  const w = $("div"), last = cs[cs.length - 1], day = t => new Date(t).toISOString().slice(0, 10);
  w.append($("div", "val", "آخر إغلاق " + last[4] + " USDT"));
  const closes = cs.map(r => r[4]), lo = Math.min(...closes), hi = Math.max(...closes);
  const NS = "http://www.w3.org/2000/svg", svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 300 60"); svg.setAttribute("class", "spark"); svg.setAttribute("role", "img");
  const pl = document.createElementNS(NS, "polyline");
  pl.setAttribute("points", closes.map((v, i) => (i * 299 / (closes.length - 1)).toFixed(1) + "," + (58 - (v - lo) / ((hi - lo) || 1) * 56).toFixed(1)).join(" "));
  pl.setAttribute("fill", "none"); pl.setAttribute("stroke", "#D4AF37"); pl.setAttribute("stroke-width", "1.5");
  svg.append(pl); w.append(svg);
  const d = $("div", "src", "عدد الشموع المغلقة: " + cs.length + " | من "); const a = $("bdi", null, day(cs[0][0])); a.dir = "ltr";
  const b = $("bdi", null, day(last[0])); b.dir = "ltr"; d.append(a, " إلى ", b, " | أدنى إغلاق " + lo + " | أعلى إغلاق " + hi);
  w.append(d); return w;
}

function flowView(cs) {
  const w = $("div"), l = cs[cs.length - 1], fx = n => Number(n.toPrecision(6)).toString();
  const pct = l[1] ? l[2] / l[1] * 100 : 0;
  w.append($("div", "val", "الصافي (شراء - بيع): " + fx(l[4])));
  w.append($("div", "src", "آخر شمعة مغلقة: شراء " + fx(l[2]) + " | بيع " + fx(l[3]) + " | نسبة الشراء " + pct.toFixed(1) + "% | التراكمي (من بداية النافذة) " + fx(l[5])));
  const bars = cs.slice(-48), mx = Math.max(...bars.map(r => Math.abs(r[4]))) || 1;
  const NS = "http://www.w3.org/2000/svg", svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 300 60"); svg.setAttribute("class", "spark flowbars"); svg.setAttribute("role", "img");
  const z = document.createElementNS(NS, "line"); z.setAttribute("x1", 0); z.setAttribute("x2", 300); z.setAttribute("y1", 30); z.setAttribute("y2", 30); z.setAttribute("stroke", "#555"); svg.append(z);
  bars.forEach((r, i) => { const h = Math.abs(r[4]) / mx * 28, rc = document.createElementNS(NS, "rect"), bw = 300 / bars.length;
    rc.setAttribute("x", (i * bw + 0.5).toFixed(1)); rc.setAttribute("width", (bw - 1).toFixed(1)); rc.setAttribute("height", Math.max(h, 0.5).toFixed(1));
    rc.setAttribute("y", (r[4] >= 0 ? 30 - h : 30).toFixed(1)); rc.setAttribute("fill", r[4] >= 0 ? "#1f9d55" : "#d64545"); svg.append(rc); });
  w.append(svg);
  w.append($("div", "src", "أخضر = المشترون المبادرون أكثر، أحمر = البائعون المبادرون أكثر (آخر " + bars.length + " شمعة). بيانات باينانس فقط، وهي ليست نية المتداول. الشموع المغلقة فقط: الساعة الجارية غير محسوبة، لذلك قد يظهر البيع في ساعة أغلقت بينما السعر يصعد الآن."));
  return w;
}

function profileView(rec) {
  const rows = rec.value, st = rec.stats, w = $("div"), NS = "http://www.w3.org/2000/svg", H = 150, rh = H / rows.length;
  const mx = Math.max(...rows.map(r => r[2])) || 1, svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 300 " + H); svg.setAttribute("class", "spark vprofile"); svg.setAttribute("role", "img"); svg.style.height = "160px";
  rows.slice().reverse().forEach((r, i) => { const inVA = r[1] > st.val && r[0] < st.vah, isPoc = st.poc > r[0] && st.poc <= r[1] + 1e-9, bw = r[2] / mx * 290, rc = document.createElementNS(NS, "rect");
    rc.setAttribute("x", 0); rc.setAttribute("y", (i * rh).toFixed(2)); rc.setAttribute("width", bw.toFixed(1)); rc.setAttribute("height", (rh - 0.4).toFixed(2));
    rc.setAttribute("fill", isPoc ? "#D4AF37" : inVA ? "#8a7424" : "#3a3a3a"); svg.append(rc); });
  w.append($("div", "val", "أكثر سعر تداولا: " + Number(st.poc.toPrecision(7))));
  w.append(svg);
  w.append($("div", "src", "منطقة القيمة 70%: من " + Number(st.val.toPrecision(7)) + " إلى " + Number(st.vah.toPrecision(7)) + " | النطاق " + Number(st.price_low.toPrecision(7)) + " - " + Number(st.price_high.toPrecision(7)) + " | الشموع: " + st.bars_used + " (" + st.bar_size + ")" + (st.coverage_pct != null ? " | تغطية " + st.coverage_pct + "%" : " | تحذير: شموع ساعة فقط، تقريب خشن")));
  w.append($("div", "src", "تقدير: حجم كل شمعة موزّع بالتساوي على مدى سعرها، وليس صفقات فعلية. ذهبي = أكثر سعر تداولا، بني = منطقة القيمة."));
  return w;
}

function intentSizeView(rec) {
  const st = rec.stats, w = $("div"), f = x => Number(Number(x).toPrecision(5));
  w.append($("div", "val", "حصة الصفقات الكبيرة من الحجم: " + st.large_volume_share_pct + "%"));
  w.append($("div", "src", "الصفقات الكبيرة: " + st.large_trades + " من " + st.sample_trades + " صفقة (آخر " + st.window_hours + " ساعات) | صافي شراء الكبيرة: " + f(st.large_net_buy) + " | نسبة الشراء بين الكبيرة: " + st.large_buy_share_pct + "%"));
  w.append($("div", "src", "حجم الصفقة: الوسيط " + f(st.p50) + " | 90% " + f(st.p90) + " | حد الكبيرة (99%) " + f(st.p99_threshold) + " | المتوسط " + f(st.mean_size)));
  w.append($("div", "src", "فرضية وليست نية: الصفقة الكبيرة قد تكون أمرا مقسما أو روبوتا، والحد 99% اختياري. لا تعتمد عليها قبل اختبار خارج العينة."));
  return w;
}
function intentDivView(rec) {
  const v = rec.value, h = rec.stats, w = $("div"), AR = {"no divergence": "لا يوجد تباعد", "price up while net taker flow is selling": "السعر صاعد بينما صافي المشترين الفعليين سالب (بيع)", "price down while net taker flow is buying": "السعر هابط بينما صافي المشترين الفعليين موجب (شراء)"};
  w.append($("div", "val", AR[v.state] || v.state));
  w.append($("div", "src", "آخر " + v.window_hours + " ساعات: تغير السعر " + v.price_change_pct + "% | صافي الدلتا " + v.net_delta_pct_of_volume + "% من الحجم"));
  w.append($("div", "src", "التاريخ (" + h.history_hours + " ساعة): " + h.past_events + " حالة سابقة" + (h.past_events ? "، تبعت الدلتا في " + h.next_window_followed_delta_direction + " (" + h.hit_rate_pct + "%، مجال 95%: " + h.ci95_low_pct + "-" + h.ci95_high_pct + "%) مقابل 50% للعملة" : "") + " | " + (h.reading === "no evidence" ? "لا دليل" : "المجال يستبعد 50% لكن غير مثبت")));
  w.append($("div", "src", "فرضية: عينة صغيرة وغير مختبرة خارج العينة."));
  return w;
}

function xcheckView(rec) {
  const st = rec.stats, w = $("div"), G = {price: "الأسعار", kline: "الشموع", flow: "التدفق", profile: "بروفايل الحجم", other: "أخرى"};
  w.append($("div", "val", "فحوصات مسجلة: " + st.checks_total + " | إنذارات: " + st.flagged_total));
  w.append($("div", "src", "عدد مرات التحديث المسجلة: " + st.runs + " (نحتفظ بآخر " + st.kept + ")"));
  Object.entries(st.groups).forEach(([k, g]) => w.append($("div", "src", (G[k] || k) + ": " + g.checks + " فحص | أكبر فرق حقيقي " + g.max_diff_pct + "% | متوسط " + g.mean_diff_pct + "% | إنذارات " + g.flagged)));
  w.append($("div", "src", "الغرض: التفريق بين فحص هادئ (فروق صغيرة دائما) وفحص ميت (لا يسجل شيئا). الإنذار يظهر عندما يتجاوز الفرق حد الفحص."));
  return w;
}

const LV = {
  res: {c: "#e5534b", w: 2, d: "", n: "مقاومة"}, resS: {c: "#e5534b", w: 5, d: "", n: "مقاومة أقوى"},
  sup: {c: "#2ea043", w: 2, d: "", n: "دعم"}, supS: {c: "#2ea043", w: 5, d: "", n: "دعم قوي"},
  watch: {c: "#D4AF37", w: 3, d: "7 4", n: "رقم المراقبة"}, bounce: {c: "#1fb6c9", w: 2, d: "2 3", n: "منطقة ارتداد"},
  form: {c: "#a371f7", w: 3, d: "9 3 2 3", n: "ارتداد يتشكل"}, wall: {c: "#f0883e", w: 2, d: "1 3", n: "جدار أوامر حي"}, px: {c: "#ffffff", w: 1.5, d: "", n: "السعر"}};
const NSv = "http://www.w3.org/2000/svg", svgEl = (t, a) => { const e = document.createElementNS(NSv, t); Object.entries(a).forEach(([k, v]) => e.setAttribute(k, v)); return e; };
function lvSample(k) { const sv = svgEl("svg", {viewBox: "0 0 34 10", width: 34, height: 10, class: "lvs"}); sv.append(svgEl("line", {x1: 1, x2: 33, y1: 5, y2: 5, stroke: LV[k].c, "stroke-width": Math.min(LV[k].w, 5), "stroke-dasharray": LV[k].d})); return sv; }
function legendView() { const g = $("div", "legend"); ["res", "resS", "sup", "supS", "watch", "bounce", "form", "wall", "px"].forEach(k => { const i = $("span", "lgi"); i.append(lvSample(k), LV[k].n); g.append(i); }); return g; }
function ladder(items, price, f) {
  // items: [{k, lo, hi}] ; draws horizontal lines on a price axis (display only). Labels are nudged apart so they never overlap.
  const all = items.concat([{k: "px", lo: price, hi: price}]), mn = Math.min(...all.map(x => x.lo)), mx = Math.max(...all.map(x => x.hi)), pad = (mx - mn) * 0.06 || 1;
  const H = 210, y = v => 10 + (1 - (v - (mn - pad)) / ((mx + pad) - (mn - pad))) * (H - 20), sv = svgEl("svg", {viewBox: "0 0 300 " + H, class: "ladder", role: "img", direction: "ltr"});
  const rows = all.slice().sort((a, b) => b.hi - a.hi).map(it => ({it, yy: y((it.lo + it.hi) / 2)}));
  let prev = -99; rows.forEach(r => { r.ly = Math.max(r.yy - 3, prev + 11); prev = r.ly; });
  rows.forEach(({it, yy, ly}) => { const st = LV[it.k];
    if (it.k === "bounce" || it.lo !== it.hi) sv.append(svgEl("rect", {x: 0, y: y(it.hi), width: 300, height: Math.max(y(it.lo) - y(it.hi), 3), fill: st.c, opacity: 0.18}));
    sv.append(svgEl("line", {x1: 0, x2: 300, y1: yy, y2: yy, stroke: st.c, "stroke-width": st.w, "stroke-dasharray": st.d}));
    const tx = svgEl("text", {x: 4, y: ly + 1, fill: st.c, "font-size": 9.5, "font-weight": "bold"}); tx.textContent = f(it.k === "px" ? price : (it.lo + it.hi) / 2) + "  " + st.n; sv.append(tx); });
  return sv;
}

// Pure function (tested): choose what to show from the zones relative to a price. Display only, no new numbers are invented.
function levelPick(zones, price) {
  const above = zones.filter(z => z.mid > price).sort((x, y) => x.mid - y.mid), below = zones.filter(z => z.mid < price).sort((x, y) => y.mid - x.mid);
  const near = (z) => Math.abs(z.mid - price) / price * 100 <= 5;
  const best = (arr, cmp) => arr.filter(near).sort(cmp)[0] || null;
  const res1 = above[0] || null, sup1 = below[0] || null;
  const resStrong = best(above, (x, y) => y.strength - x.strength || x.mid - y.mid), supStrong = best(below, (x, y) => y.strength - x.strength || y.mid - x.mid);
  const ratio = z => z.bounces / z.episodes;
  const bounce = best(below.filter(z => z.episodes >= 3), (x, y) => ratio(y) - ratio(x) || y.episodes - x.episodes);
  const all = zones.slice().sort((x, y) => Math.abs(x.mid - price) - Math.abs(y.mid - price));
  return {res1, resStrong, sup1, supStrong, bounce, watch: all[0] || null};
}
function levelsView(rec, sym) {
  const w = $("div"); w.dataset.levels = "1";
  const draw = () => {
    const v = rec.value, lp = live.ok && live.ok.prices[sym], price = lp || v.price_ref, pk = levelPick(v.zones, price), f = n => Number(Number(n).toPrecision(7));
    const dist = z => ((z.mid - price) / price * 100);
    const line = (title, z, k) => { const d = $("div", "lvl"); d.style.borderInlineStartColor = LV[k].c; d.style.borderInlineStartWidth = Math.min(LV[k].w, 5) + "px"; d.style.borderInlineStartStyle = LV[k].d ? (LV[k].d.length > 3 ? "dashed" : "dotted") : "solid"; d.append($("b", null, title + ": ")); d.firstChild.style.color = LV[k].c;
      if (!z) { d.append("لا يوجد قريب ضمن 5%"); return d; }
      const rg = z.lo === z.hi ? String(f(z.mid)) : f(z.lo) + " - " + f(z.hi), b = $("bdi", "val2", rg); b.dir = "ltr"; d.append(b);
      d.append(" (" + (dist(z) >= 0 ? "+" : "") + dist(z).toFixed(2) + "%)");
      d.append($("div", "src", "عينة: " + z.episodes + " لمسة سابقة، ارتد منها " + z.bounces + " | مصادر: " + z.why.slice(0, 3).join("، "))); return d; };
    w.replaceChildren();
    w.append($("div", "src", "السعر المرجعي: " + (lp ? "الحي " : "آخر شمعة ساعة ") + f(price)));
    const its = []; const add = (k, z) => { if (z) its.push({k, lo: z.lo, hi: z.hi}); };
    add("watch", pk.watch); add("res", pk.res1); add("resS", pk.resStrong); add("sup", pk.sup1); add("supS", pk.supStrong); add("bounce", pk.bounce);
    if (v.forming) its.push({k: "form", lo: v.forming.zone_mid, hi: v.forming.zone_mid});
    const ob0 = ob.ok && ob.ok.m[sym]; if (ob0) { if (ob0.bidWall) its.push({k: "wall", lo: ob0.bidWall.p, hi: ob0.bidWall.p}); if (ob0.askWall) its.push({k: "wall", lo: ob0.askWall.p, hi: ob0.askWall.p}); }
    w.append(ladder(its, price, f), legendView());
    if (pk.watch) w.append(line("رقم المراقبة (الأقرب للسعر)", pk.watch, "watch"));
    w.append(line("أقرب مقاومة", pk.res1, "res")); if (pk.resStrong && pk.resStrong !== pk.res1) w.append(line("مقاومة أقوى (ضمن 5%)", pk.resStrong, "resS"));
    w.append(line("أقرب دعم", pk.sup1, "sup")); if (pk.supStrong && pk.supStrong !== pk.sup1) w.append(line("دعم قوي (ضمن 5%)", pk.supStrong, "supS"));
    w.append(line("منطقة ارتداد محتملة (أفضل نسبة ارتداد سابقة، 3 لمسات فأكثر)", pk.bounce, "bounce"));
    const fm = v.forming; const fd = $("div", "lvl"); fd.style.borderInlineStartColor = LV.form.c; fd.style.borderInlineStartWidth = "3px"; fd.style.borderInlineStartStyle = "dashed"; fd.style.color = LV.form.c; fd.textContent = (fm ? "ارتداد يتشكل: " + (fm.side === "support" ? "السعر لمس منطقة دعم قرب " : "السعر لمس منطقة مقاومة قرب ") + f(fm.zone_mid) + " وأغلق بعيدا عنها في آخر 3 شموع ساعة (وصف لما حدث، ليس توقعا)" : "ارتداد يتشكل: لا يوجد الآن"); w.append(fd);
    const o = ob.ok && ob.ok.m[sym];
    if (o && (o.bidWall || o.askWall)) { const wl = (t, x) => x ? t + " " + f(x.p) + " (" + x.dist.toFixed(2) + "% بعيدا، " + x.x.toFixed(1) + " ضعف المعتاد)" : ""; w.append($("div", "src", "جدران أوامر حية (حي، قد تُلغى في أي لحظة): " + [wl("شراء", o.bidWall), wl("بيع", o.askWall)].filter(Boolean).join(" | "))); }
    w.append($("div", "src", "فرضيات من الماضي: مستويات من بروفايل الحجم والقمم والقيعان، عدد اللمسات والارتداد عينات صغيرة، ولم تُختبر خارج العينة. ليست توقعا ولا نصيحة."));
  };
  draw(); const key = () => (live.ok ? live.ok.prices[sym] : "") + "|" + (ob.ok ? ob.ok.at : "");
  let last = key(); const t = setInterval(() => { if (!w.isConnected) { clearInterval(t); return; } const k = key(); if (k !== last) { last = k; draw(); } }, 2000);
  return w;
}
window.__levelPick = levelPick;

function backtestView(rec) {
  const w = $("div"), v = rec.value, st = rec.stats, pc = x => (x * 100).toFixed(1) + "%", sg = x => (x > 0 ? "+" : "") + x.toFixed(2) + "%";
  w.append($("div", "src", "محاكاة على بيانات الماضي (شراء فقط، سبوت، رسوم وانزلاق " + (st.fee_per_side * 100 + st.slippage_per_side * 100).toFixed(2) + "% لكل جانب). الاختيار على أول " + Math.round(st.split * 100) + "% من الوقت والقياس على الباقي (خارج العينة). فرضية وليست توصية."));
  w.append($("div", "src", "عدد الشموع: " + st.candles + " (ساعة) من " + cairoStr(st.from) + " إلى " + cairoStr(st.to) + " بتوقيت القاهرة."));
  let any = false;
  Object.entries(v.strategies).forEach(([k, r]) => {
    const o = r.out_of_sample, b = r.baseline_oos_same_exits, d = $("div", "lvl"); d.append($("b", null, (v.names[k] || k) + ": "));
    if (!o || !o.trades) { d.append("لا صفقات كافية للاختيار"); w.append(d); return; }
    const pos = o.avg_net_per_trade_pct > 0; any = any || pos;
    d.style.borderInlineStartColor = pos ? "#2ea043" : "#e5534b"; d.style.borderInlineStartWidth = "4px";
    d.append("صفقات " + o.trades + " | نسبة النجاح " + pc(o.win_rate) + " (نطاق 95%: " + pc(o.win_rate_ci95[0]) + " إلى " + pc(o.win_rate_ci95[1]) + ") | صافي الصفقة بعد الرسوم " + sg(o.avg_net_per_trade_pct) + " | أقصى سحب " + o.max_drawdown_pct + "% | بدون مستويات (نفس الخروج) " + sg(b.avg_net_per_trade_pct));
    const e = $("div", "src", "خروج مختار: هدف " + (r.chosen.tp * 100) + "%، وقف " + (r.chosen.sl * 100) + "%" + (r.chosen.tranche ? "، شريحتان" : "") + " | صافي داخل العينة " + sg(r.chosen.in_sample.avg_net_per_trade_pct) + " على " + r.chosen.in_sample.trades + " صفقة");
    d.append(e); w.append(d);
  });
  const mx = Math.max(...Object.values(v.strategies).map(r => r.out_of_sample ? r.out_of_sample.trades : 0));
  w.append($("div", "src", any ? "بعض القواعد موجبة خارج العينة: لا تُعتبر مثبتة قبل عينة أكبر." : "لا قاعدة موجبة بعد الرسوم خارج العينة. نسبة نجاح عالية مع صافٍ سالب تعني أن الخسائر أكبر من الأرباح. شرطك (98% على 1000+ صفقة وسحب أقل من 20% وصافٍ موجب) غير متحقق؛ أكبر عينة هنا " + mx + " صفقة."));
  return w;
}
const FEEDAR = {"aljazeera-en": "الجزيرة (إنجليزي)", "aljazeera-ar": "الجزيرة (عربي)", fed: "الاحتياطي الفيدرالي (رسمي)", ecb: "البنك المركزي الأوروبي (رسمي)", fomc: "تقويم الفيدرالي", calendar: "تقويم رسمي مكتوب يدويا", bea: "جدول مكتب التحليل الاقتصادي الأمريكي"};
const EVSRC = src => /^official calendar/.test(src) ? "تقويم رسمي (مراجعة يدوية " + (src.match(/\d{4}-\d{2}-\d{2}/) || [""])[0] + ")" : src === "BEA" ? "مكتب التحليل الاقتصادي" : src === "FOMC calendar" ? "تقويم الفيدرالي" : src;
function newsView(rec) {
  const w = $("div"), v = rec.value, sx = v.stance, nowMs = Date.now(), fm = n => Number(Number(n).toPrecision(4)).toString();
  const mk = (t, k) => $("span", "pill " + k, t);
  const top = $("div", "lvl"); top.append($("b", null, "موقف الأخبار: "), mk(sx.wait ? "انتظر" : "لا حدث مجدول قريب", sx.wait ? "p-warn" : "p-ok"));
  if (sx.leak_trap) top.append(" ", mk("احتمال تسريب أو فخ", "p-bad"));
  top.append($("div", "src", sx.wait ? "قاعدة: انتظار من ساعتين قبل حدث مجدول إلى ساعة بعده. الإصدار الرسمي تأكيد وليس أول إشارة." : "قاعدة: انتظار من ساعتين قبل حدث مجدول إلى ساعة بعده، ولا حدث ضمنها الآن. الإصدار الرسمي تأكيد وليس أول إشارة."));
  top.append($("div", "src", "حركة آخر ساعتين: " + fm(sx.move_2h_pct) + "% (" + fm(sx.move_in_atr) + " ضعف متوسط المدى الساعي " + fm(sx.atr_1h_pct) + "%). تُرفع علامة التسريب فقط إذا كان الحدث خلال ساعتين والحركة ضعفين فأكثر."));
  w.append(top);
  const ne = sx.next_event;
  if (ne) { const d = $("div", "src"); d.append("أقرب حدث مجدول: " + ne.title + " | "); d.append(timeEl(Date.parse(ne.start))); if (ne.time_assumed) d.append(" (الساعة افتراضية 14:00 نيويورك وليست من الصفحة)"); d.append(" | " + EVSRC(ne.source)); w.append(d); }
  else w.append($("div", "src", "لا حدث مجدول قادم ضمن 7 أيام في المصادر المتاحة (لا تغطي هذه المصادر مؤشر الأسعار والوظائف الأمريكية)."));
  v.events.slice(0, 6).forEach(e => { const d = $("div", "src"); d.append("• " + e.title + " | "); d.append(timeEl(Date.parse(e.start))); w.append(d); });
  const h = $("div", "lvl"); h.append($("b", null, "آخر العناوين (كما نُشرت، بدون تقييم):")); w.append(h);
  v.headlines.slice(0, 8).forEach(x => { const d = $("div", "src"); d.append(mk(x.kind === "official" ? "رسمي" : "إعلام", x.kind === "official" ? "p-ok" : "p-lbl"), " " + (FEEDAR[x.feed] || x.feed) + " | "); d.append(timeEl(Date.parse(x.published))); d.append(" | ");
    const a = $("a", null, x.title); a.href = x.link; a.rel = "noopener"; a.dir = "auto"; d.append(a); w.append(d); });
  const bad = Object.entries(rec.stats.feeds).filter(([k, f]) => !f.ok);
  w.append($("div", "src", bad.length ? "تحذير: مصادر لم تعمل في آخر تحديث: " + bad.map(([k]) => FEEDAR[k] || k).join("، ") : "كل المصادر عملت في آخر تحديث."));
  return w;
}
const RULEAR = {support_bounce: "ارتداد من دعم", strict_support: "دعم مشدد", rsi_oversold: "RSI", bollinger_reclaim: "بولينجر"}, STANCEAR = {wait: "انتظر", buy_watch: "مراقبة شراء", sell_watch: "مراقبة بيع"};
function recView(rec) {
  const w = $("div"), v = rec.value, f = n => Number(Number(n).toPrecision(7)).toString(), sg = x => (x > 0 ? "+" : "") + x, st = v.stance, ed = v.edge;
  const top = $("div", "lvl"); top.append($("b", null, "الموقف: "), $("span", "pill " + (st === "wait" ? "p-warn" : "p-ok"), STANCEAR[st]), " ", $("span", "pill p-lbl", "فرضية"), " ", $("span", "pill p-bad", ed.proven ? "ميزة مثبتة" : "لا ميزة مثبتة"));
  top.append($("div", "src", "عرض فقط، لا أوامر. سبوت، شراء على الهبوط وبيع على الصعود بشرائح، بدون رافعة.")); w.append(top);
  const R = {
    no_edge: r => "لا ميزة مثبتة بعد الاختبار الرجعي: أفضل قاعدة (" + (r.best ? RULEAR[r.best.rule] || r.best.rule : "-") + ") خارج العينة " + (r.best ? sg(r.best.avg_net_pct) + "% للصفقة بعد الرسوم على " + r.best.trades + " صفقة" : "بلا صفقات") + "؛ " + r.positive + " من " + r.tested + " قواعد موجبة. الشرط للخروج من الانتظار: " + ed.min_trades + " صفقة فأكثر وصافٍ موجب.",
    news_wait: () => "نافذة حدث مجدول (من ساعتين قبله إلى ساعة بعده): الانتظار هو الافتراضي.",
    leak_trap: () => "احتمال تسريب أو فخ: حركة حادة قبل إصدار مجدول، لا تُلاحَق.",
    near_support: () => "السعر قريب من أقرب دعم (ضمن متوسط مدى ساعي واحد).", near_resistance: () => "السعر قريب من أقرب مقاومة (ضمن متوسط مدى ساعي واحد).", forming_bounce: () => "ارتداد يتشكل عند منطقة (وصف لما حدث وليس توقعا)."};
  const rs = $("div", "lvl"); rs.append($("b", null, "الأسباب (بالترتيب):"));
  if (!v.reasons.length) rs.append($("div", "src", "لا أسباب للانتظار ولا إشارة قريبة."));
  v.reasons.forEach((r, i) => rs.append($("div", "src", (i + 1) + ". " + R[r.code](r)))); w.append(rs);
  const bp = v.buy_plan;
  if (bp) { const d = $("div", "lvl"); d.style.borderInlineStartColor = LV.sup.c; d.append($("b", null, "خطة شراء مشروطة (ليست توصية): "));
    d.append("إذا وصل السعر لمنطقة " + f(bp.zone_lo) + " - " + f(bp.zone_hi) + " (تبعد " + f(bp.dist_pct) + "% تحت السعر) وأغلقت شمعة ساعة فوقها فهي منطقة دخول للمراقبة. إبطال الفكرة: تحت " + f(bp.invalidation) + " (خسارة محتملة " + f(bp.risk_pct) + "% من الدخول)." +
      (bp.target ? " هدف أول " + f(bp.target) + " (+" + f(bp.reward_pct) + "%)، العائد إلى المخاطرة بعد الرسوم " + f(bp.rr_after_fees) + "." : "") + " عينة المنطقة: " + bp.samples + " لمسة، ارتد منها " + bp.bounces + "."); w.append(d); }
  const sp = v.sell_plan;
  if (sp) { const d = $("div", "lvl"); d.style.borderInlineStartColor = LV.res.c; d.append($("b", null, "خطة بيع بشرائح لو عندك الأصل (ليست توصية): "));
    d.append(sp.tranches.map(t => "شريحة عند " + f(t.lo) + " - " + f(t.hi) + " (" + sg(f(t.dist_pct)) + "%، " + t.samples + " لمسة وارتد " + t.bounces + ")").join("؛ ") + ". احتفظ بالباقي إذا أغلق السعر فوق " + f(sp.hold_rest_above) + "."); w.append(d); }
  const abc = $("div", "lvl"); abc.append($("b", null, "الخطط: "));
  abc.append($("div", "src", "أ: انتظر لمس الدعم ثم إغلاق ساعة فوقه قبل أي فكرة شراء."), $("div", "src", "ب: إذا أغلقت شمعة ساعة تحت مستوى الإبطال فالفكرة ملغاة، ارجع لقسم المستويات."), $("div", "src", "ج: عند حدث مجدول أو علامة تسريب: لا إجراء حتى ساعة بعد الإصدار الرسمي."));
  w.append(abc);
  if (v.news.next_event) { const e = $("div", "src"); e.append("أقرب حدث مجدول: " + v.news.next_event.title + " | "); e.append(timeEl(Date.parse(v.news.next_event.start))); w.append(e); }
  const t = v.inputs_time, a = $("div", "src"); a.append("أعمار المدخلات: المستويات "); a.append(timeEl(Date.parse(t.levels))); a.append("، الأخبار "); a.append(timeEl(Date.parse(t.news))); a.append("، الاختبار الرجعي "); a.append(timeEl(Date.parse(t.backtest))); w.append(a);
  return w;
}
function fwdView(rec) {
  const w = $("div"), v = rec.value, pc = x => x == null ? "-" : (Math.round(x * 1000) / 10) + "%", sg = x => x == null ? "-" : (x > 0 ? "+" : "") + x;
  const d = $("div", "lvl"); d.append($("b", null, "السجل الأمامي (قياس حقيقي)"), " ", $("span", "pill p-lbl", "مقاس"));
  d.append($("div", "src", "كل ساعة تقريبا تُسجَّل التوصية كما قالتها، وبعد 24 ساعة تُقارَن بالشموع الحقيقية اللاحقة بعد رسوم 0.3%. لا تعديل لما سُجِّل ولا نظر للمستقبل."));
  w.append(d);
  const s = $("div", "lvl"); s.append($("div", "src", "سُجّل: " + v.logged + " مرة | حُسب نتيجته: " + v.scored + " | أيام مستقلة: " + v.independent_days + " (السجلات المتجاورة تتداخل، فالعدد الفعلي أقل)."));
  s.append($("div", "src", "بخطة شراء: " + v.with_plan + " | لمس المنطقة: " + v.touched + " | رابحة: " + v.wins + " | نسبة النجاح: " + pc(v.win_rate) + " | متوسط الصافي: " + sg(v.avg_net_pct) + "% | هدف أولا: " + v.target_first + " | إبطال أولا: " + v.invalid_first));
  s.append($("div", "src", "الهدف المطلوب: نجاح " + pc(v.target.win_rate) + " على " + v.target.trades + " صفقة فأكثر. العينة الآن صغيرة جدا ولا تثبت شيئا." + (v.first_logged ? "" : " لم يبدأ التسجيل بعد."))); w.append(s);
  if (v.first_logged) { const e = $("div", "src"); e.append("بدأ التسجيل: "); e.append(timeEl(Date.parse(v.first_logged))); w.append(e); }
  return w;
}
function watchView(rec) {
  const v = rec.value, w = $("div"), f = n => Number(Number(n).toPrecision(7)), st = {above: "فوق المستوى الأعلى", below: "تحت المستوى الأدنى", between: "بين المستويين"}[v.state];
  const d = $("div", "lvl"); const cb = $("bdi", "val", String(f(v.last_close.close))); cb.dir = "ltr";
  d.append($("b", null, "آخر إغلاق يومي (00:00 UTC): "), cb, " ", $("span", "pill " + (v.state === "between" ? "p-warn" : "p-ok"), st), " ", $("span", "pill p-lbl", "مقاس"));
  w.append(d);
  const l = $("div", "lvl"); l.append($("span", "pill p-lbl", "فرضية"), " مستويات حددها المستخدم (مش محسوبة ومش توقع): أعلى " + f(v.levels.upper) + " | أدنى " + f(v.levels.lower));
  l.append($("div", "src", "أيام متتالية إغلاقها فوق الأعلى: " + v.streak_above + " | تحت الأدنى: " + v.streak_below + ". الشمعة اليومية الجارية لا تُحسب أبدا، فقط الشموع المقفولة."));
  const t = $("div", "src", "آخر " + v.closes.length + " إغلاقات (الأحدث أولا):");
  v.closes.slice().reverse().forEach(c => { const r = $("div"), b = $("bdi", null, new Date(c[0]).toISOString().slice(0, 10) + "  " + f(c[1])); b.dir = "ltr"; r.append(b); t.append(r); });
  l.append(t); w.append(l);
  w.append($("div", "src", "للعرض فقط. لا إشارة ولا نصيحة، والبوابة 98% لم تتغير."));
  return w;
}
function recCard(mod, rec, sym) {
  const c = $("div", "card");
  const ttl = rec.title_ar || (mod.view ? mod.view.title : rec.id);
  c.append($("h2", null, rec.id.indexOf("price.") === 0 ? ttl + " (لقطة محفوظة وليست حية)" : ttl));
  if (rec.id.indexOf("price.") === 0) c.append($("div", "src", "هذه لقطة من آخر تحديث للبيانات وقد تختلف عن السعر الحي في أعلى الصفحة."));
  if (Array.isArray(rec.value) && /^candles/.test(rec.unit)) c.append(candleView(rec.value));
  else if (Array.isArray(rec.value) && /^flow/.test(rec.unit)) c.append(flowView(rec.value));
  else if (Array.isArray(rec.value) && /^profile/.test(rec.unit) && rec.stats) c.append(profileView(rec));
  else if (/^intent-size/.test(rec.unit) && rec.stats) c.append(intentSizeView(rec));
  else if (rec.unit === "levels" && rec.value) c.append(levelsView(rec, sym));
  else if (rec.unit === "watch" && rec.value) c.append(watchView(rec));
  else if (rec.unit === "backtest" && rec.value) c.append(backtestView(rec));
  else if (rec.unit === "news" && rec.value) c.append(newsView(rec));
  else if (rec.unit === "recommendation" && rec.value) c.append(recView(rec));
  else if (rec.unit === "forward-summary" && rec.value) c.append(fwdView(rec));
  else if (/^xcheck/.test(rec.unit) && rec.stats) c.append(xcheckView(rec));
  else if (rec.unit === "divergence" && rec.stats) c.append(intentDivView(rec));
  else c.append($("div", "val", typeof rec.value === "object" ? JSON.stringify(rec.value) : String(rec.value) + (rec.unit ? " " + rec.unit : "")));
  const s = $("div", "src");
  const b = badge(mod, rec);
  s.append("المصدر: ");
  if (/^https?:\/\//.test(rec.source.url)) { const l = $("a", null, arSrc(rec.source.name)); l.href = rec.source.url; l.rel = "noopener"; s.append(l); } else s.append(arSrc(rec.source.name));
  s.append(" | الوقت: "); s.append(timeEl(Date.parse(rec.fetched_at)));
  s.append(" | العمر: " + b.a.toFixed(1) + " ساعة ");
  s.append(b.wrap);
  if (mod.status !== "ok") s.append($("div", "src", "تحذير: آخر تشغيل للوحدة " + (mod.status === "failed" ? "فشل" : "قديم") + (mod.detail ? " (" + mod.detail + ")" : "")));
  const ck = rec.checked_against;
  if (ck) {
    const x = $("div", "src", "مطابقة مع " + arSrc(ck.source) + (ck.value != null ? ": " : ""));
    if (ck.value != null) { const v = $("bdi", null, String(ck.value)); v.dir = "ltr"; x.append(v); }
    x.append(ck.trades != null ? " | الفرق " + ck.diff_pct + "% (" + ck.trades + " صفقة)" : ck.median_diff_pct != null ? " | الفرق الوسيط " + ck.median_diff_pct + "% (الأقصى " + ck.max_diff_pct + "% على " + ck.candles_compared + " شمعة) " : " | الفرق " + ck.diff_pct + "% ");
    x.append($("span", "pill " + (ck.ok ? "p-ok" : "p-bad"), ck.ok ? "متطابق" : "تحذير: فرق كبير بين المصدرين (الحد " + ck.limit_pct + "%)"));
    s.append(x);
  } else if (rec.id.indexOf("price.") === 0 || rec.id.indexOf("flow.") === 0 || rec.id.indexOf("profile.") === 0) s.append($("div", "src", "تحذير: بلا مطابقة مستقلة"));
  c.append(s);
  return c;
}


// ---- Live prices (B1b): fetched by this page from public exchange APIs, never from our data files. Label: live.
const LIVE = {syms: ["XAUT", "BNB", "ETH", "SOL"], pollMs: 10000, checkEvery: 3, maxDiff: 0.5, staleSec: 35};
const LSRC = {
  binance: {name: "مرآة بيانات باينانس العامة", url: "https://data-api.binance.vision/api/v3/ticker/price",
    get: async () => { const r = await fetch("https://data-api.binance.vision/api/v3/ticker/price?symbols=" + encodeURIComponent(JSON.stringify(LIVE.syms.map(x => x + "USDT"))), {cache: "no-store"}); if (!r.ok) throw new Error("binance " + r.status);
      const o = {}; for (const t of await r.json()) o[t.symbol.slice(0, -4)] = Number(t.price); return o; }},
  okx: {name: "أو كي إكس", url: "https://www.okx.com/api/v5/market/ticker",
    get: async () => { const o = {}; await Promise.all(LIVE.syms.map(async s => { const r = await fetch("https://www.okx.com/api/v5/market/ticker?instId=" + s + "-USDT", {cache: "no-store"}); if (!r.ok) throw new Error("okx " + r.status); o[s] = Number((await r.json()).data[0].last); })); return o; }},
  gate: {name: "جيت", url: "https://api.gateio.ws/api/v4/spot/tickers",
    get: async () => { const o = {}; await Promise.all(LIVE.syms.map(async s => { const r = await fetch("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=" + s + "_USDT", {cache: "no-store"}); if (!r.ok) throw new Error("gate " + r.status); o[s] = Number((await r.json())[0].last); })); return o; }},
};
// P9: a source that just failed (429 or any error) is skipped for COOL_MS so we do not hammer a rate-limited API every 10 s; if every source is cooling the poll is skipped (the old data keeps its age and turns stale by itself).
const COOL_MS = 30000, cool = {};
const coolFail = (grp, k) => { cool[grp + k] = performance.now() + COOL_MS; };
const order = (grp, ks) => ks.filter(k => !(cool[grp + k] > performance.now()));
const validPrices = o => LIVE.syms.every(s => Number.isFinite(o[s]) && o[s] > 0);
const live = {n: 0, ok: null, errs: {}};
let LIVEBOX = null, OBBOX = null, curSym = null;
const symsShown = () => LIVE.syms.filter(x => !curSym || x === curSym);
async function livePoll() {
  const srcs = order("L", ["binance", "okx", "gate"]); if (!srcs.length) { renderLive(); return; }
  live.n++;
  let prim = null, name = null; live.errs = {};
  for (const k of srcs) {
    try { const o = await LSRC[k].get(); if (!validPrices(o)) throw new Error("bad data"); prim = o; name = k; break; }
    catch (e) { live.errs[k] = String(e.message || e).slice(0, 40); coolFail("L", k); }
  }
  if (prim) {
    let chk = live.ok && live.ok.chk && live.n % LIVE.checkEvery ? live.ok.chk : null;
    if (!chk || live.n % LIVE.checkEvery === 1 || live.n === 1) {
      for (const k of order("L", ["okx", "gate", "binance"]).filter(x => x !== name)) {
        try { const o = await LSRC[k].get(); if (validPrices(o)) { chk = {k, o}; break; } } catch (e) { coolFail("L", k); /* the check is optional */ }
      }
    }
    live.ok = {name, prices: prim, chk, at: nowMs(), t0: performance.now()};
  }
  renderLive();
}
function updateHead() { if (window.__updateHead) window.__updateHead(); }
function renderLive() {
  const box = LIVEBOX; if (!box) return; updateHead();
  box.replaceChildren(); box.append($("h2", null, "الأسعار الحية (من المتصفح مباشرة)"));
  const l = live.ok, age = l ? (performance.now() - l.t0) / 1000 : null, stale = !l || age > LIVE.staleSec;
  if (!l) { box.append($("div", "src", "تحذير: تعذّر جلب الأسعار الحية من كل المصادر: " + Object.entries(live.errs).map(([k, v]) => arSrc(k) + " " + arSrc(v)).join("، "))); return; }
  for (const s of symsShown()) {
    const row = $("div", "lrow"); row.append($("span", "lsym", s));
    const v = $("bdi", "val", String(l.prices[s])); v.dir = "ltr"; row.append(v);
    if (l.chk) { const d = Math.abs(l.prices[s] - l.chk.o[s]) / l.chk.o[s] * 100, okc = d <= LIVE.maxDiff;
      row.append($("span", "pill " + (okc ? "p-ok" : "p-bad"), okc ? "متطابق " + d.toFixed(3) + "%" : "تحذير فرق " + d.toFixed(2) + "%")); }
    box.append(row);
  }
  const f = $("div", "src"); f.append($("span", "pill p-lbl", LABELS.live), $("span", "pill " + (stale ? "p-bad" : "p-ok"), stale ? "قديمة" : "محدّثة"));
  f.append(" المصدر: "); const a = $("a", null, LSRC[l.name].name); a.href = LSRC[l.name].url; a.rel = "noopener"; f.append(a);
  if (l.name !== "binance") f.append(" (بديل: " + Object.keys(live.errs).map(arSrc).join("، ") + " تعذّر)");
  if (l.chk) f.append(" | المطابقة: " + LSRC[l.chk.k].name);
  else f.append(" | تحذير: بلا مطابقة");
  f.append(" | الوقت: "); f.append(timeEl(l.at));
  f.append(" | العمر: " + Math.round(age) + " ث");
  box.append(f);
}
function startLive(main) {
  const box = $("section", "live"); box.id = "live"; LIVEBOX = box;
  renderLive();
  let timer = null;
  const tick = async () => { if (document.hidden || !navigator.onLine) { renderLive(); return; } try { await livePoll(); } catch (e) { /* shown as stale */ } };
  const loop = () => { clearInterval(timer); tick(); timer = setInterval(() => { tick(); }, LIVE.pollMs); };
  document.addEventListener("visibilitychange", () => { if (!document.hidden) loop(); });
  window.addEventListener("online", loop);
  setInterval(renderLive, 1000);
  loop();
}

// ---- Live order book view: browser only, labelled live, nothing stored, never used in a backtest (no free history exists).
const OB = {maxBand: 0.25, pollMs: 10000, staleSec: 35};
const OBSRC = {
  binance: {name: "مرآة بيانات باينانس العامة", url: "https://data-api.binance.vision/api/v3/depth",
    get: async s => { const r = await fetch("https://data-api.binance.vision/api/v3/depth?symbol=" + s + "USDT&limit=100", {cache: "no-store"}); if (!r.ok) throw new Error("binance " + r.status); const d = await r.json(); return {bids: d.bids, asks: d.asks}; }},
  okx: {name: "أو كي إكس", url: "https://www.okx.com/api/v5/market/books",
    get: async s => { const r = await fetch("https://www.okx.com/api/v5/market/books?instId=" + s + "-USDT&sz=100", {cache: "no-store"}); if (!r.ok) throw new Error("okx " + r.status); const d = (await r.json()).data[0]; return {bids: d.bids, asks: d.asks}; }},
  gate: {name: "جيت", url: "https://api.gateio.ws/api/v4/spot/order_book",
    get: async s => { const r = await fetch("https://api.gateio.ws/api/v4/spot/order_book?currency_pair=" + s + "_USDT&limit=100", {cache: "no-store"}); if (!r.ok) throw new Error("gate " + r.status); const d = await r.json(); return {bids: d.bids, asks: d.asks}; }},
};
// Pure function (tested): imbalance inside a price band around the mid. band = smaller of OB.maxBand and what both sides of the 100 levels really cover.
function obMetrics(raw) {
  const b = raw.bids.map(x => [Number(x[0]), Number(x[1])]), a = raw.asks.map(x => [Number(x[0]), Number(x[1])]);
  if (!b.length || !a.length || [...b, ...a].some(x => !(x[0] > 0) || !(x[1] >= 0))) throw new Error("bad book");
  if (b[0][0] >= a[0][0]) throw new Error("crossed book");
  const mid = (b[0][0] + a[0][0]) / 2, reach = Math.min((mid - b[b.length - 1][0]) / mid * 100, (a[a.length - 1][0] - mid) / mid * 100);
  const band = Math.max(Math.min(OB.maxBand, reach), 0);
  const bv = b.filter(x => x[0] >= mid * (1 - band / 100)).reduce((t, x) => t + x[1], 0);
  const av = a.filter(x => x[0] <= mid * (1 + band / 100)).reduce((t, x) => t + x[1], 0);
  const wallOf = (side, sgn) => { const q = side.map(x => x[1]).sort((x, y) => x - y), med = q[Math.floor(q.length / 2)] || 0; let best = null;
    side.forEach(x => { const d = Math.abs(x[0] - mid) / mid * 100; if (d <= 1 && med > 0 && x[1] >= 4 * med && (!best || x[1] > best.q)) best = {p: x[0], q: x[1], dist: d, x: x[1] / med}; }); return best; };
  return {mid, spreadPct: (a[0][0] - b[0][0]) / mid * 100, band, bv, av, imb: bv + av > 0 ? (bv - av) / (bv + av) : 0, bidWall: wallOf(b), askWall: wallOf(a)};
}
const ob = {ok: null, errs: {}};
async function obPoll() {
  const srcs = order("O", ["binance", "okx", "gate"]); if (!srcs.length) { renderOb(); return; }
  ob.errs = {};
  for (const k of srcs) {
    try {
      const out = {};
      await Promise.all(LIVE.syms.map(async s => { out[s] = obMetrics(await OBSRC[k].get(s)); }));
      ob.ok = {name: k, m: out, at: nowMs(), t0: performance.now()}; renderOb(); return;
    } catch (e) { ob.errs[k] = String(e.message || e).slice(0, 40); coolFail("O", k); }
  }
  renderOb();
}
function renderOb() {
  const box = OBBOX; if (!box) return;
  box.replaceChildren(); box.append($("h2", null, "دفتر الأوامر الحي (من المتصفح مباشرة)"));
  const o = ob.ok, age = o ? (performance.now() - o.t0) / 1000 : null, stale = !o || age > OB.staleSec;
  if (!o) { box.append($("div", "src", "تحذير: تعذّر جلب دفتر الأوامر من كل المصادر: " + Object.entries(ob.errs).map(([k, v]) => arSrc(k) + " " + arSrc(v)).join("، "))); return; }
  for (const s of symsShown()) {
    const m = o.m[s], row = $("div", "lrow"); row.append($("span", "lsym", s));
    const pct = Math.round((m.imb + 1) / 2 * 100), bar = $("span", "obbar"), g = $("i", "obg"), r = $("i", "obr");
    g.style.width = pct + "%"; r.style.width = (100 - pct) + "%"; bar.append(g, r); row.append(bar);
    const t = $("bdi", "src", (m.imb >= 0 ? "+" : "") + (m.imb * 100).toFixed(0) + "%"); t.dir = "ltr"; row.append(t);
    box.append(row);
    const d = $("div", "src", "اختلال الشراء/البيع (الشراء ناقص البيع على مجموعهما) داخل نطاق ±" + m.band.toFixed(3) + "% | شراء " + Number(m.bv.toPrecision(5)) + " | بيع " + Number(m.av.toPrecision(5)) + " | فارق السعر بين أفضل شراء وأفضل بيع " + m.spreadPct.toFixed(4) + "%");
    box.append(d);
  }
  const f = $("div", "src"); f.append($("span", "pill p-lbl", LABELS.live), $("span", "pill " + (stale ? "p-bad" : "p-ok"), stale ? "قديمة" : "محدّثة"));
  f.append(" المصدر: "); const a = $("a", null, OBSRC[o.name].name); a.href = OBSRC[o.name].url; a.rel = "noopener"; f.append(a);
  if (o.name !== "binance") f.append(" (بديل: " + Object.keys(ob.errs).map(arSrc).join("، ") + " تعذّر)");
  f.append(" | الوقت: "); f.append(timeEl(o.at));
  f.append(" | العمر: " + Math.round(age) + " ث"); box.append(f);
  box.append($("div", "src", "النسبة المئوية بجوار الشريط هي اختلال الشراء/البيع. عرض النطاق يختلف من عملة لأخرى (مثلا ETH أضيق بكثير)، فلا تقارن الأشرطة بين العملات. لقطة لحظية لأول 100 مستوى فقط، أخضر = أوامر شراء واقفة أكثر، أحمر = أوامر بيع أكثر. الأوامر الواقفة قد تُلغى أو تكون وهمية، ولا تدل على نية. لا يُحفظ لها تاريخ ولا تدخل في أي اختبار رجعي."));
}
function startOb(anchor) {
  const box = $("section", "live"); box.id = "obook"; OBBOX = box; renderOb();
  let timer = null; const tick = async () => { if (document.hidden || !navigator.onLine) { renderOb(); return; } try { await obPoll(); } catch (e) { /* shown as stale */ } };
  const loop = () => { clearInterval(timer); tick(); timer = setInterval(tick, OB.pollMs); };
  document.addEventListener("visibilitychange", () => { if (!document.hidden) loop(); }); window.addEventListener("online", loop);
  setInterval(renderOb, 1000); loop();
}

async function main() {
  const meta = await getJSON("data/meta.json", true);
  bust = meta.generated_at;
  const g = ageH(meta.generated_at);
  document.getElementById("gen").textContent = "آخر تحديث للبيانات: \u2066" + cairoStr(Date.parse(meta.generated_at)) + " بتوقيت القاهرة (UTC " + meta.generated_at.slice(11, 19) + ")\u2069 (قبل " + g.toFixed(1) + " ساعة)" + (g > 26 ? " تحذير: البيانات قديمة" : "");
  const bad = Object.entries(meta.modules).filter(([, m]) => m.status !== "ok").map(([id]) => id);
  const msgs = [];
  if (g > 26) msgs.push("البيانات قديمة: آخر تحديث قبل " + g.toFixed(0) + " ساعة (الحد 26 ساعة)");
  if (bad.length) msgs.push("وحدات بها مشكلة: " + bad.join("، "));
  if (meta.manifest_errors.length) msgs.push("أخطاء في تعريف الوحدات");
  if (Number(meta.app_version || 0) > APP_VERSION) msgs.push("نسخة أحدث من الصفحة متاحة: أعد تحميل الصفحة (قد تكون نسخة قديمة محفوظة مؤقتا)");
  const bn = document.getElementById("banner");
  if (offline) msgs.unshift("غير متصل: عرض آخر نسخة محفوظة، والأعمار تقريبية");
  if (msgs.length) { bn.textContent = msgs.join(" | "); bn.hidden = false; }
  const nav = document.getElementById("tabs"), main = document.getElementById("main");
  startLive(main);
  startOb(null);
  // Load every output once, then group the records by coin (display only; no values are changed).
  const all = [];
  const HEAVY = ["forward-log", "forward-score", "forward-archive"];   // growing history files: the page only needs the summary
  for (const [id, m] of Object.entries(meta.modules)) {
    for (const o of m.outputs) {
      if (HEAVY.includes(o)) continue;
      try { const d = await getJSON("data/" + o + ".json"); d.records.forEach(r => all.push({m, r})); }
      catch (e) { all.push({m, err: o}); }
    }
  }
  const coinOf = r => { const x = /(xaut|bnb|eth|sol)usdt/.exec(r.id); return x ? x[1].toUpperCase() : null; };
  const SECS = [
    ["levels", "المستويات المراقَبة (فرضيات)", r => /^levels\./.test(r.id)],
    ["watch", "متابعة الإغلاق اليومي (مستويات المستخدم)", r => /^watch\./.test(r.id)],
    ["news", "الأخبار والأحداث المجدولة", r => /^news\./.test(r.id)],
    ["rec", "التوصية والمنطقة وإبطال الفكرة (فرضية)", r => /^recommendation\./.test(r.id)],
    ["fwd", "السجل الأمامي: ماذا حدث بعد التوصية", r => /^forwardsummary\./.test(r.id)],
    ["price", "لقطة السعر والفحص", r => /^(price|change24h)\./.test(r.id)],
    ["kline", "الشموع", r => /^kline\./.test(r.id)],
    ["flow", "التدفق (دلتا المشترين والبائعين)", r => /^flow\./.test(r.id)],
    ["profile", "بروفايل الحجم", r => /^profile\./.test(r.id)],
    ["intent", "مؤشرات النية (فرضيات)", r => /^intent\./.test(r.id)],
    ["tests", "الاختبارات الرجعية (محاكاة)", r => /^backtest\./.test(r.id)],
  ];
  const find = (c, f) => all.filter(x => x.r && coinOf(x.r) === c && f(x.r));
  const fx = n => Number(Number(n).toPrecision(6)).toString();
  function oneLine(key, c) {
    const L = {rec: () => { const x = find(c, r => /^recommendation\./.test(r.id))[0]; if (!x) return ""; return STANCEAR[x.r.value.stance] + " | " + (x.r.value.edge.proven ? "ميزة مثبتة" : "لا ميزة مثبتة"); },
      watch: () => { const x = find(c, r => /^watch\./.test(r.id))[0]; if (!x) return ""; const v = x.r.value; return "آخر إغلاق " + fx(v.last_close.close) + " | " + ({above: "فوق", below: "تحت", between: "بين المستويين"}[v.state]); },
      fwd: () => { const x = find(c, r => /^forwardsummary\./.test(r.id))[0]; if (!x) return ""; return "سُجّل " + x.r.value.logged + " | حُسب " + x.r.value.scored + " | لمس المنطقة " + x.r.value.touched; },
      news: () => { const x = find(c, r => /^news\./.test(r.id))[0]; if (!x) return ""; const sx = x.r.value.stance; return (sx.wait ? "انتظر (حدث مجدول)" : "لا حدث مجدول قريب") + (sx.leak_trap ? " | احتمال تسريب أو فخ" : ""); },
      tests: () => { const x = find(c, r => /^backtest\./.test(r.id))[0]; if (!x) return ""; const p = Object.values(x.r.value.strategies).filter(r => r.out_of_sample && r.out_of_sample.trades); const pos = p.filter(r => r.out_of_sample.avg_net_per_trade_pct > 0).length; return pos + " من " + p.length + " قواعد موجبة خارج العينة"; },
      levels: () => { const x = find(c, r => /^levels\./.test(r.id))[0]; if (!x) return ""; const pk = levelPick(x.r.value.zones, x.r.value.price_ref), f = n => Number(Number(n).toPrecision(7)); return "أقرب دعم " + (pk.sup1 ? f(pk.sup1.mid) : "-") + " | أقرب مقاومة " + (pk.res1 ? f(pk.res1.mid) : "-"); },
      kline: () => { const x = find(c, r => /^kline\..*\.1h$/.test(r.id))[0]; return x ? "آخر إغلاق ساعة: " + fx(x.r.value[x.r.value.length - 1][4]) : ""; },
      flow: () => { const x = find(c, r => /^flow\..*\.1h$/.test(r.id))[0]; return x ? "صافي آخر ساعة مغلقة: " + fx(x.r.value[x.r.value.length - 1][4]) : ""; },
      profile: () => { const x = find(c, r => /^profile\..*\.24h$/.test(r.id))[0]; return x ? "أكثر سعر تداولا 24 ساعة: " + fx(x.r.stats.poc) : ""; },
      intent: () => { const x = find(c, r => r.unit === "divergence")[0]; return x ? "تباعد السعر والدلتا: " + ({"no divergence": "لا يوجد", "price up while net taker flow is selling": "سعر صاعد وبيع صافٍ", "price down while net taker flow is buying": "سعر هابط وشراء صافٍ"}[x.r.value.state] || "") : ""; },
      price: () => { const x = find(c, r => /^price\./.test(r.id))[0]; return x ? "آخر لقطة: " + fx(x.r.value) : ""; }};
    return L[key] ? L[key]() : "";
  }
  function section(title, line, body, open) { const d = $("details", "sec"); if (open) d.open = true; const sm = $("summary", null, title); if (line) sm.append($("span", "sline", " | " + line)); d.append(sm); body.forEach(x => d.append(x)); return d; }
  const placeholder = (t, m) => { const d = $("div", "head"); d.append($("div", "src", m)); return section(t, "لم يُبنَ بعد", [d], false); };
  const coins = ["XAUT", "ETH", "SOL", "BNB"], modOk = Object.values(meta.modules).filter(m => m.status === "ok").length, modAll = Object.keys(meta.modules).length;
  function headFor(c) {
    const h = $("div", "head"); h.append($("h2", null, c + " / USDT"));
    const hp = $("div"); hp.append("السعر الحي: "); const v = $("bdi", "val", "..."); v.id = "headprice"; v.dir = "ltr"; hp.append(v); h.append(hp);
    const rx = find(c, r => /^recommendation\./.test(r.id))[0], sv = rx ? rx.r.value : null, st = $("div"); st.append("التوصية: ", $("span", "pill " + (sv && sv.stance !== "wait" ? "p-ok" : "p-warn"), sv ? STANCEAR[sv.stance] : "انتظر"), $("span", "pill p-lbl", "فرضية"));
    if (sv && !sv.edge.proven) st.append($("span", "pill p-bad", "لا ميزة مثبتة")); h.append(st);
    h.append($("div", "src", sv ? "الافتراضي هو الانتظار حتى تثبت قاعدة ميزتها خارج العينة بعد الرسوم. التفاصيل والأسباب في قسم التوصية." : "لا توصية متاحة الآن."));
    h.append($("div", "src", "حالة النظام: " + modOk + " من " + modAll + " وحدات سليمة | عمر البيانات المحفوظة " + ageH(meta.generated_at).toFixed(1) + " ساعة"));
    return h;
  }
  function updateHeadImpl() { const v = document.getElementById("headprice"); if (!v) return; const l = live.ok; v.textContent = l && curSym && l.prices[curSym] != null ? String(l.prices[curSym]) : "..."; }
  window.__updateHead = updateHeadImpl;
  async function show(t) {
    [...nav.children].forEach(b => b.classList.toggle("on", b.dataset.t === t));
    main.replaceChildren(); curSym = coins.includes(t) ? t : null;
    if (meta.manifest_errors.length) main.append($("div", "card", "أخطاء في تعريف الوحدات: " + meta.manifest_errors.join("؛ ")));
    if (curSym) {
      main.append(headFor(t));
      for (const [key, title, f] of SECS) {
        const items = find(t, f); if (!items.length) continue;
        if (key === "price") { main.append(LIVEBOX, OBBOX); renderLive(); renderOb(); }
        main.append(section(title, oneLine(key, t), items.map(x => recCard(x.m, x.r, t)), key === "levels" || key === "price"));
      }
    } else {
      const h = $("div", "head"); h.append($("h2", null, "حالة النظام"));
      h.append($("div", "src", "آخر تحديث للبيانات: ")); h.lastChild.append(timeEl(Date.parse(meta.generated_at)));
      h.append($("div", "src", "الوحدات السليمة: " + modOk + " من " + modAll + " | عمر البيانات: " + ageH(meta.generated_at).toFixed(1) + " ساعة"));
      for (const [id, m] of Object.entries(meta.modules)) { const r = $("div", "src"); r.append(m.name_ar + ": "); r.append($("span", "pill " + (m.status === "ok" ? "p-ok" : "p-bad"), m.status === "ok" ? "سليمة" : m.status === "stale" ? "قديمة" : "فشلت")); if (m.last_ok) { r.append(" آخر نجاح: "); r.append(timeEl(Date.parse(m.last_ok))); } h.append(r); }
      main.append(h);
      all.filter(x => !x.r || !coinOf(x.r)).forEach(x => main.append(x.r ? recCard(x.m, x.r) : $("div", "card", "تعذّر تحميل " + x.err)));
    }
  }
  [...coins, "system"].forEach(t => { const b = $("button", null, t === "system" ? "النظام" : t); b.dataset.t = t; b.onclick = () => show(t); nav.append(b); });
  show("XAUT");
}
main().catch(e => { document.getElementById("gen").textContent = "تعذّر تحميل البيانات: " + e.message; });

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
