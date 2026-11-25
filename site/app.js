"use strict";
const APP_VERSION = 10; // bump when the page code changes; data files carry the version they expect
// All data is rendered with textContent only. No HTML from data files is ever injected.
const LABELS = {measured:"مقاس", simulated:"محاكاة", live:"حي", hypothesis:"فرضية", ai:"ذكاء اصطناعي"};
const $ = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };
// Time: never trust the phone clock. Offset = server time (HTTP Date + Age headers) minus phone time.
let offsetMs = Number(localStorage.getItem("gd-offset") || 0), offline = false, bust = String(Math.floor(Date.now() / 6e4));
const nowMs = () => Date.now() + offsetMs;
const ageH = ts => (nowMs() - Date.parse(ts)) / 36e5;

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
  w.append($("div", "src", "أخضر = المشترون المبادرون أكثر، أحمر = البائعون المبادرون أكثر (آخر " + bars.length + " شمعة). بيانات Binance فقط، وهي ليست نية المتداول."));
  return w;
}

function profileView(rec) {
  const rows = rec.value, st = rec.stats, w = $("div"), NS = "http://www.w3.org/2000/svg", H = 150, rh = H / rows.length;
  const mx = Math.max(...rows.map(r => r[2])) || 1, svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 300 " + H); svg.setAttribute("class", "spark vprofile"); svg.setAttribute("role", "img"); svg.style.height = "160px";
  rows.slice().reverse().forEach((r, i) => { const inVA = r[1] > st.val && r[0] < st.vah, isPoc = st.poc > r[0] && st.poc <= r[1] + 1e-9, bw = r[2] / mx * 290, rc = document.createElementNS(NS, "rect");
    rc.setAttribute("x", 0); rc.setAttribute("y", (i * rh).toFixed(2)); rc.setAttribute("width", bw.toFixed(1)); rc.setAttribute("height", (rh - 0.4).toFixed(2));
    rc.setAttribute("fill", isPoc ? "#D4AF37" : inVA ? "#8a7424" : "#3a3a3a"); svg.append(rc); });
  w.append($("div", "val", "POC (أكثر سعر تداولا): " + Number(st.poc.toPrecision(7))));
  w.append(svg);
  w.append($("div", "src", "منطقة القيمة 70%: من " + Number(st.val.toPrecision(7)) + " إلى " + Number(st.vah.toPrecision(7)) + " | النطاق " + Number(st.price_low.toPrecision(7)) + " - " + Number(st.price_high.toPrecision(7)) + " | الشموع: " + st.bars_used + " (" + st.bar_size + ")" + (st.coverage_pct != null ? " | تغطية " + st.coverage_pct + "%" : " | تحذير: شموع ساعة فقط، تقريب خشن")));
  w.append($("div", "src", "تقدير: حجم كل شمعة موزّع بالتساوي على مدى سعرها، وليس صفقات فعلية. ذهبي = POC، بني = منطقة القيمة."));
  return w;
}

function recCard(mod, rec) {
  const c = $("div", "card");
  c.append($("h2", null, rec.title_ar || (mod.view ? mod.view.title : rec.id)));
  if (Array.isArray(rec.value) && /^candles/.test(rec.unit)) c.append(candleView(rec.value));
  else if (Array.isArray(rec.value) && /^flow/.test(rec.unit)) c.append(flowView(rec.value));
  else if (Array.isArray(rec.value) && /^profile/.test(rec.unit) && rec.stats) c.append(profileView(rec));
  else c.append($("div", "val", typeof rec.value === "object" ? JSON.stringify(rec.value) : String(rec.value) + (rec.unit ? " " + rec.unit : "")));
  const s = $("div", "src");
  const b = badge(mod, rec);
  s.append("المصدر: ");
  if (/^https?:\/\//.test(rec.source.url)) { const l = $("a", null, rec.source.name); l.href = rec.source.url; l.rel = "noopener"; s.append(l); } else s.append(rec.source.name);
  s.append(" | الوقت: "); const tm = $("bdi", null, rec.fetched_at); tm.dir = "ltr"; s.append(tm);
  s.append(" | العمر: " + b.a.toFixed(1) + " ساعة ");
  s.append(b.wrap);
  if (mod.status !== "ok") s.append($("div", "src", "تحذير: آخر تشغيل للوحدة " + (mod.status === "failed" ? "فشل" : "قديم") + (mod.detail ? " (" + mod.detail + ")" : "")));
  const ck = rec.checked_against;
  if (ck) {
    const x = $("div", "src", "مطابقة مع " + ck.source + (ck.value != null ? ": " : ""));
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
  binance: {name: "Binance public data mirror", url: "https://data-api.binance.vision/api/v3/ticker/price",
    get: async () => { const r = await fetch("https://data-api.binance.vision/api/v3/ticker/price?symbols=" + encodeURIComponent(JSON.stringify(LIVE.syms.map(x => x + "USDT"))), {cache: "no-store"}); if (!r.ok) throw new Error("binance " + r.status);
      const o = {}; for (const t of await r.json()) o[t.symbol.slice(0, -4)] = Number(t.price); return o; }},
  okx: {name: "OKX", url: "https://www.okx.com/api/v5/market/ticker",
    get: async () => { const o = {}; await Promise.all(LIVE.syms.map(async s => { const r = await fetch("https://www.okx.com/api/v5/market/ticker?instId=" + s + "-USDT", {cache: "no-store"}); if (!r.ok) throw new Error("okx " + r.status); o[s] = Number((await r.json()).data[0].last); })); return o; }},
  gate: {name: "Gate.io", url: "https://api.gateio.ws/api/v4/spot/tickers",
    get: async () => { const o = {}; await Promise.all(LIVE.syms.map(async s => { const r = await fetch("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=" + s + "_USDT", {cache: "no-store"}); if (!r.ok) throw new Error("gate " + r.status); o[s] = Number((await r.json())[0].last); })); return o; }},
};
const validPrices = o => LIVE.syms.every(s => Number.isFinite(o[s]) && o[s] > 0);
const live = {n: 0, ok: null, errs: {}};
async function livePoll() {
  live.n++;
  let prim = null, name = null; live.errs = {};
  for (const k of ["binance", "okx", "gate"]) {
    try { const o = await LSRC[k].get(); if (!validPrices(o)) throw new Error("bad data"); prim = o; name = k; break; }
    catch (e) { live.errs[k] = String(e.message || e).slice(0, 40); }
  }
  if (prim) {
    let chk = live.ok && live.ok.chk && live.n % LIVE.checkEvery ? live.ok.chk : null;
    if (!chk || live.n % LIVE.checkEvery === 1 || live.n === 1) {
      for (const k of ["okx", "gate", "binance"].filter(x => x !== name)) {
        try { const o = await LSRC[k].get(); if (validPrices(o)) { chk = {k, o}; break; } } catch (e) { /* the check is optional */ }
      }
    }
    live.ok = {name, prices: prim, chk, at: nowMs(), t0: performance.now()};
  }
  renderLive();
}
function renderLive() {
  const box = document.getElementById("live"); if (!box) return;
  box.replaceChildren(); box.append($("h2", null, "الأسعار الحية (من المتصفح مباشرة)"));
  const l = live.ok, age = l ? (performance.now() - l.t0) / 1000 : null, stale = !l || age > LIVE.staleSec;
  if (!l) { box.append($("div", "src", "تحذير: تعذّر جلب الأسعار الحية من كل المصادر: " + Object.entries(live.errs).map(([k, v]) => k + " " + v).join("، "))); return; }
  for (const s of LIVE.syms) {
    const row = $("div", "lrow"); row.append($("span", "lsym", s));
    const v = $("bdi", "val", String(l.prices[s])); v.dir = "ltr"; row.append(v);
    if (l.chk) { const d = Math.abs(l.prices[s] - l.chk.o[s]) / l.chk.o[s] * 100, okc = d <= LIVE.maxDiff;
      row.append($("span", "pill " + (okc ? "p-ok" : "p-bad"), okc ? "متطابق " + d.toFixed(3) + "%" : "تحذير فرق " + d.toFixed(2) + "%")); }
    box.append(row);
  }
  const f = $("div", "src"); f.append($("span", "pill p-lbl", LABELS.live), $("span", "pill " + (stale ? "p-bad" : "p-ok"), stale ? "قديمة" : "محدّثة"));
  f.append(" المصدر: "); const a = $("a", null, LSRC[l.name].name); a.href = LSRC[l.name].url; a.rel = "noopener"; f.append(a);
  if (l.name !== "binance") f.append(" (بديل: " + Object.keys(live.errs).join("، ") + " تعذّر)");
  if (l.chk) f.append(" | المطابقة: " + LSRC[l.chk.k].name);
  else f.append(" | تحذير: بلا مطابقة");
  f.append(" | الوقت: "); const tm = $("bdi", null, new Date(l.at).toISOString().slice(0, 19) + "Z"); tm.dir = "ltr"; f.append(tm);
  f.append(" | العمر: " + Math.round(age) + " ث");
  box.append(f);
}
function startLive(main) {
  const box = $("section", "live"); box.id = "live"; main.parentNode.insertBefore(box, main);
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
  binance: {name: "Binance public data mirror", url: "https://data-api.binance.vision/api/v3/depth",
    get: async s => { const r = await fetch("https://data-api.binance.vision/api/v3/depth?symbol=" + s + "USDT&limit=100", {cache: "no-store"}); if (!r.ok) throw new Error("binance " + r.status); const d = await r.json(); return {bids: d.bids, asks: d.asks}; }},
  okx: {name: "OKX", url: "https://www.okx.com/api/v5/market/books",
    get: async s => { const r = await fetch("https://www.okx.com/api/v5/market/books?instId=" + s + "-USDT&sz=100", {cache: "no-store"}); if (!r.ok) throw new Error("okx " + r.status); const d = (await r.json()).data[0]; return {bids: d.bids, asks: d.asks}; }},
  gate: {name: "Gate.io", url: "https://api.gateio.ws/api/v4/spot/order_book",
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
  return {mid, spreadPct: (a[0][0] - b[0][0]) / mid * 100, band, bv, av, imb: bv + av > 0 ? (bv - av) / (bv + av) : 0};
}
const ob = {ok: null, errs: {}};
async function obPoll() {
  ob.errs = {};
  for (const k of ["binance", "okx", "gate"]) {
    try {
      const out = {};
      await Promise.all(LIVE.syms.map(async s => { out[s] = obMetrics(await OBSRC[k].get(s)); }));
      ob.ok = {name: k, m: out, at: nowMs(), t0: performance.now()}; renderOb(); return;
    } catch (e) { ob.errs[k] = String(e.message || e).slice(0, 40); }
  }
  renderOb();
}
function renderOb() {
  const box = document.getElementById("obook"); if (!box) return;
  box.replaceChildren(); box.append($("h2", null, "دفتر الأوامر الحي (من المتصفح مباشرة)"));
  const o = ob.ok, age = o ? (performance.now() - o.t0) / 1000 : null, stale = !o || age > OB.staleSec;
  if (!o) { box.append($("div", "src", "تحذير: تعذّر جلب دفتر الأوامر من كل المصادر: " + Object.entries(ob.errs).map(([k, v]) => k + " " + v).join("، "))); return; }
  for (const s of LIVE.syms) {
    const m = o.m[s], row = $("div", "lrow"); row.append($("span", "lsym", s));
    const pct = Math.round((m.imb + 1) / 2 * 100), bar = $("span", "obbar"), g = $("i", "obg"), r = $("i", "obr");
    g.style.width = pct + "%"; r.style.width = (100 - pct) + "%"; bar.append(g, r); row.append(bar);
    const t = $("bdi", "src", (m.imb >= 0 ? "+" : "") + (m.imb * 100).toFixed(0) + "%"); t.dir = "ltr"; row.append(t);
    box.append(row);
    const d = $("div", "src", "نطاق ±" + m.band.toFixed(3) + "% | شراء " + Number(m.bv.toPrecision(5)) + " | بيع " + Number(m.av.toPrecision(5)) + " | الفارق " + m.spreadPct.toFixed(4) + "%");
    box.append(d);
  }
  const f = $("div", "src"); f.append($("span", "pill p-lbl", LABELS.live), $("span", "pill " + (stale ? "p-bad" : "p-ok"), stale ? "قديمة" : "محدّثة"));
  f.append(" المصدر: "); const a = $("a", null, OBSRC[o.name].name); a.href = OBSRC[o.name].url; a.rel = "noopener"; f.append(a);
  if (o.name !== "binance") f.append(" (بديل: " + Object.keys(ob.errs).join("، ") + " تعذّر)");
  f.append(" | الوقت: "); const tm = $("bdi", null, new Date(o.at).toISOString().slice(0, 19) + "Z"); tm.dir = "ltr"; f.append(tm);
  f.append(" | العمر: " + Math.round(age) + " ث"); box.append(f);
  box.append($("div", "src", "لقطة لحظية لأول 100 مستوى فقط، أخضر = أوامر شراء واقفة أكثر، أحمر = أوامر بيع أكثر. الأوامر الواقفة قد تُلغى أو تكون وهمية، ولا تدل على نية. لا يُحفظ لها تاريخ ولا تدخل في أي اختبار رجعي."));
}
function startOb(anchor) {
  const box = $("section", "live"); box.id = "obook"; anchor.after(box); renderOb();
  let timer = null; const tick = async () => { if (document.hidden || !navigator.onLine) { renderOb(); return; } try { await obPoll(); } catch (e) { /* shown as stale */ } };
  const loop = () => { clearInterval(timer); tick(); timer = setInterval(tick, OB.pollMs); };
  document.addEventListener("visibilitychange", () => { if (!document.hidden) loop(); }); window.addEventListener("online", loop);
  setInterval(renderOb, 1000); loop();
}

async function main() {
  const meta = await getJSON("data/meta.json", true);
  bust = meta.generated_at;
  const g = ageH(meta.generated_at);
  document.getElementById("gen").textContent = "آخر تحديث للبيانات: \u2066" + meta.generated_at + "\u2069 (قبل " + g.toFixed(1) + " ساعة)" + (g > 26 ? " تحذير: البيانات قديمة" : "");
  const bad = Object.entries(meta.modules).filter(([, m]) => m.status !== "ok").map(([id]) => id);
  const msgs = [];
  if (g > 26) msgs.push("البيانات قديمة: آخر تحديث قبل " + g.toFixed(0) + " ساعة (الحد 26 ساعة)");
  if (bad.length) msgs.push("وحدات بها مشكلة: " + bad.join("، "));
  if (meta.manifest_errors.length) msgs.push("أخطاء في تعريف الوحدات");
  if (Number(meta.app_version || 0) > APP_VERSION) msgs.push("نسخة أحدث من الصفحة متاحة: أعد تحميل الصفحة (قد تكون نسخة قديمة محفوظة مؤقتا)");
  const bn = document.getElementById("banner");
  if (offline) msgs.unshift("غير متصل: عرض آخر نسخة محفوظة، والأعمار تقريبية");
  if (msgs.length) { bn.textContent = msgs.join(" | "); bn.hidden = false; }
  const tabs = {};
  for (const [id, m] of Object.entries(meta.modules)) { const t = (m.view && m.view.tab) || "modules"; (tabs[t] = tabs[t] || []).push([id, m]); }
  const nav = document.getElementById("tabs"), main = document.getElementById("main");
  startLive(main);
  startOb(document.getElementById("live"));
  const names = {modules: "الوحدات"};
  async function show(t) {
    [...nav.children].forEach(b => b.classList.toggle("on", b.dataset.t === t));
    main.replaceChildren();
    if (meta.manifest_errors.length) main.append($("div", "card", "أخطاء في تعريف الوحدات: " + meta.manifest_errors.join("؛ ")));
    for (const [id, m] of tabs[t]) {
      for (const o of m.outputs) {
        try { const d = await getJSON("data/" + o + ".json"); d.records.forEach(r => main.append(recCard(m, r))); }
        catch (e) { main.append($("div", "card", "تعذّر تحميل " + o)); }
      }
    }
  }
  Object.keys(tabs).forEach(t => { const b = $("button", null, names[t] || t); b.dataset.t = t; b.onclick = () => show(t); nav.append(b); });
  show(Object.keys(tabs)[0]);
}
main().catch(e => { document.getElementById("gen").textContent = "تعذّر تحميل البيانات: " + e.message; });

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
