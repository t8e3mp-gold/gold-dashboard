// Mobile UI test. Set DATA=<dir> to test freshly generated data (CI does). Needs: npm i playwright-core@1.65.1 and a Chrome install (CI has google-chrome).
import http from "node:http"; import fs from "node:fs"; import path from "node:path"; import { chromium } from "playwright-core";
const ROOT = path.resolve(process.argv[2] || "."); const DATA = path.resolve(process.env.DATA || path.join(ROOT, "data")); let fails = 0;
const ok = (c, m) => { console.log((c ? "PASS " : "FAIL ") + m); if (!c) fails++; };
const types = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json"};
const srv = http.createServer((q, r) => {
  const u = decodeURIComponent(q.url.split("?")[0]); const f = u.startsWith("/data/") ? path.join(DATA, u.slice(6)) : path.join(ROOT, "site", u === "/" ? "index.html" : u);
  if (!fs.existsSync(f)) { r.writeHead(404); return r.end(); } r.writeHead(200, { "content-type": types[path.extname(f)] || "text/plain" }); r.end(fs.readFileSync(f));
}).listen(0); const base = "http://127.0.0.1:" + srv.address().port + "/";
const b = await chromium.launch({ executablePath: process.env.CHROME || "/usr/bin/google-chrome", args: ["--no-sandbox"] });
async function load(mutate) {
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, deviceScaleFactor: 2 }); const p = await ctx.newPage();
  if (mutate) await p.route("**/data/meta.json*", async rt => { const j = JSON.parse(fs.readFileSync(path.join(DATA, "meta.json"), "utf8")); mutate(j); rt.fulfill({ contentType: "application/json", body: JSON.stringify(j) }); });
  await p.goto(base); await p.waitForSelector(".card"); return p;
}
// 1. fresh data: every card shows source, time, label, status; no overflow; timestamp not wrapped
let p = await load(null);
// open every section of every tab and collect what is on screen
async function collect(p) {
  const cards = [], x = { spark: 0, flowbars: 0, vprofile: 0, wrap: true, overflow: false, flowRects: [], profRects: [], sparkOk: true, secs: {}, heads: [] };
  for (const t of ["XAUT", "ETH", "SOL", "BNB", "system"]) {
    await p.click('nav button[data-t="' + t + '"]'); await p.waitForTimeout(150);
    await p.$$eval("details.sec", ds => ds.forEach(d => { d.open = true; }));
    cards.push(...await p.$$eval(".card", cs => cs.map(c => c.innerText)));
    x.spark += await p.$$eval(".spark:not(.flowbars):not(.vprofile)", e => e.length);
    x.sparkOk = x.sparkOk && await p.$$eval(".spark:not(.flowbars):not(.vprofile)", e => e.every(s => s.querySelector("polyline").getAttribute("points").length > 100));
    x.flowbars += await p.$$eval(".flowbars", e => e.length); x.vprofile += await p.$$eval(".vprofile", e => e.length);
    x.flowRects.push(...await p.$$eval(".flowbars", e => e.map(s => s.querySelectorAll("rect").length))); x.profRects.push(...await p.$$eval(".vprofile", e => e.map(s => s.querySelectorAll("rect").length)));
    x.wrap = x.wrap && await p.$$eval(".src bdi", bs => bs.every(b => b.getClientRects().length === 1));
    x.overflow = x.overflow || !(await p.$eval("body", e => e.scrollWidth <= window.innerWidth));
    x.secs[t] = await p.$$eval("details.sec > summary", e => e.map(s => s.innerText)); x.heads.push(await p.$$eval(".head", e => e.map(h => h.innerText)));
  }
  return { cards, x };
}
const { cards, x: X } = await collect(p);
ok(cards.length > 0, "cards rendered (" + cards.length + ")");
ok(cards.every(t => t.includes("المصدر") && t.includes("الوقت") && t.includes("العمر") && /مقاس|محاكاة|حي|فرضية|ذكاء اصطناعي/.test(t) && /محدّثة|قديمة/.test(t)), "every card has source, time, age, label and status");
ok(!X.overflow, "no horizontal overflow at 390px in any tab (all sections open)");
ok(X.wrap, "timestamps do not wrap");
ok(await p.$eval("#banner", e => e.hidden), "no banner when data is fresh");
ok(cards.length >= 39, "all 39 cards are reachable through the tabs (" + cards.length + ")");
ok(await p.$$eval("nav button", bs => bs.map(b => b.innerText).join(",") === "XAUT,ETH,SOL,BNB,النظام"), "tab row: XAUT, ETH, SOL, BNB, then system");
const pc = cards.filter(t => t.startsWith("سعر "));
ok(pc.length === 4 && pc.every(t => t.includes("مطابقة") || t.includes("مصدر واحد")), "4 price cards, each shows a cross-check or a single-source warning");
const kc = cards.filter(t => t.startsWith("شموع"));
ok(kc.length === 8 && kc.every(t => t.includes("آخر إغلاق") && t.includes("الفرق الوسيط")), "8 candle cards, each with last close and cross-check");
ok(X.spark === 8 && X.sparkOk, "8 sparklines drawn");
const fc = cards.filter(t => t.startsWith("تدفق"));
ok(fc.length === 8 && fc.every(t => t.includes("الصافي") && t.includes("نسبة الشراء") && (t.includes("الفرق") || t.includes("بلا مطابقة"))), "8 flow cards: net delta, buy share, and a check or a no-check warning");
ok(X.flowbars === 8 && X.flowRects.every(n => n === 48), "8 delta bar charts of 48 bars");
const vc = cards.filter(t => t.startsWith("بروفايل الحجم"));
ok(vc.length === 8 && vc.every(t => t.includes("أكثر سعر تداولا") && t.includes("منطقة القيمة") && t.includes("تقدير")), "8 volume-profile cards: POC, value area, estimate disclaimer");
ok(X.vprofile === 8 && X.profRects.every(n => n === 60), "8 profile charts of 60 bins");
ok(pc.every(t => t.includes("لقطة محفوظة وليست حية")), "price cards are labelled as saved snapshots, not live");
ok(fc.every(t => t.includes("الساعة الجارية غير محسوبة")), "flow cards say the open hour is not counted");
ok(["XAUT", "ETH", "SOL", "BNB"].every(c => ["لقطة السعر", "الشموع", "التدفق", "بروفايل الحجم", "مؤشرات النية", "التوصية", "الاختبارات"].every(k => X.secs[c].some(s => s.includes(k)))), "each coin tab has price, candles, flow, profile, intent, recommendation and tests sections");
ok(X.heads[0].some(h => h.includes("XAUT") && h.includes("انتظر") && h.includes("السعر الحي")), "XAUT header shows price slot and stance (wait)");
ok(X.heads[4].some(h => h.includes("حالة النظام")) && cards.some(t => t.includes("سجل")), "system tab shows status and the cross-check log");
{ const all = cards.join(" ").split("\n").filter(l => l.includes("المصدر")).join(" ").replace(/XAUT|BNB|ETH|SOL|USDT|UTC|\d|https?:\S+/g, ""); const m = all.match(/[A-Za-z]{3,}/g); ok(!m, "no Latin words left in card source lines" + (m ? ": " + [...new Set(m)].slice(0, 8).join(",") : "")); }
await p.click('nav button[data-t="XAUT"]'); await p.waitForTimeout(300);
await p.screenshot({ path: "/tmp/ui-fresh.png" });
// 2. forced stale data: banner and stale badge appear
p = await load(j => { j.generated_at = "2026-01-01T00:00:00Z"; });
ok(await p.$eval("#banner", e => !e.hidden && e.innerText.includes("قديمة")), "banner shows when data is older than 26h");
// 3. forced failed module: banner and warning on card
p = await load(j => { for (const m of Object.values(j.modules)) { m.status = "failed"; m.detail = "test"; } });
ok(await p.$eval("#banner", e => !e.hidden && e.innerText.includes("مشكلة")), "banner shows when a module failed");
await p.$$eval("details.sec", ds => ds.forEach(d => { d.open = true; }));
ok((await p.$$eval(".card", cs => cs.map(c => c.innerText))).every(t => t.includes("تحذير")), "failed module warning on card");
await p.screenshot({ path: "/tmp/ui-failed.png" });
// 3b. data built for a newer page than the one loaded: tell the user to reload
p = await load(j => { j.app_version = 999; });
ok(await p.$eval("#banner", e => !e.hidden && e.innerText.includes("نسخة أحدث")), "banner shows when data expects a newer page version");
p = await load(null);
ok(await p.$eval("#banner", e => e.hidden), "no new-version banner when versions match");
// 4. phone clock 5 days wrong: ages must still be right (server time is used)
{ const ctx = await b.newContext({ viewport: { width: 390, height: 844 } });
  await ctx.addInitScript(() => { const o = Date.now; Date.now = () => o() - 5 * 864e5; });
  const q = await ctx.newPage(); await q.goto(base); await q.waitForSelector(".card");
  const txt = (await q.$$eval(".card", cs => cs.map(c => c.innerText))).join(" ");
  const age = Number((txt.match(/العمر: (-?[\d.]+)/) || [])[1]);
  ok(age >= 0 && age < 2, "age correct with a phone clock 5 days behind (age " + age + "h)");
  ok(await q.$eval("#banner", e => e.hidden), "no false stale banner with a wrong phone clock"); }
// 5. offline: service worker serves last data and says so
{ const ctx = await b.newContext({ viewport: { width: 390, height: 844 } }); const q = await ctx.newPage();
  await q.goto(base); await q.waitForSelector(".card"); await q.evaluate(() => navigator.serviceWorker.ready);
  await q.reload(); await q.waitForSelector(".card"); await q.waitForTimeout(500);
  await ctx.setOffline(true); await q.reload(); await q.waitForSelector(".card", { timeout: 8000 });
  ok(await q.$eval("#banner", e => !e.hidden && e.innerText.includes("غير متصل")), "offline: cards still shown with an offline banner");
  await q.screenshot({ path: "/tmp/ui-offline.png" }); }
async function tabsText(q, sel) { const out = []; for (const t of ["XAUT", "ETH", "SOL", "BNB"]) { await q.click('nav button[data-t="' + t + '"]'); await q.waitForTimeout(200); out.push(await q.$eval(sel, e => e.innerText)); } return out.join("\n"); }
// 6. live prices (browser-side): mocked exchanges
const BASE = { XAUT: 4000, BNB: 600, ETH: 3000, SOL: 150 };
async function liveCase(o) {
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, deviceScaleFactor: 2 }); const q = await ctx.newPage(); const hits = { binance: 0 };
  await q.route("**/data-api.binance.vision/**", r => { hits.binance++; if (o.binance === "451") return r.fulfill({ status: 451, body: "blocked" });
    r.fulfill({ contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify(Object.entries(BASE).map(([k, v]) => ({ symbol: k + "USDT", price: String(o.binance === "zero" ? 0 : v) }))) }); });
  await q.route("**/www.okx.com/**", r => { if (o.okx === "fail") return r.fulfill({ status: 500, body: "x" }); const id = new URL(r.request().url()).searchParams.get("instId").split("-")[0];
    r.fulfill({ contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify({ data: [{ last: String(BASE[id] * (o.okxMul && o.okxMul[id] || 1)) }] }) }); });
  await q.route("**/api.gateio.ws/**", r => { if (o.gate === "fail") return r.fulfill({ status: 500, body: "x" }); const id = new URL(r.request().url()).searchParams.get("currency_pair").split("_")[0];
    r.fulfill({ contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify([{ last: String(BASE[id]) }]) }); });
  await q.goto(base); await q.waitForSelector(".card"); await q.waitForTimeout(1500);
  return { q, hits, txt: await tabsText(q, "#live") };
}
{ const { q, hits, txt } = await liveCase({ okxMul: { XAUT: 1.001 } });
  ok(/XAUT\s*4000/.test(txt) && /ETH\s*3000/.test(txt) && txt.includes("حي") && txt.includes("متطابق") && txt.includes("باينانس"), "live: 4 prices shown, label live, source, cross-check matched");
  ok(await q.$eval("body", e => e.scrollWidth <= window.innerWidth), "live: no horizontal overflow");
  await q.screenshot({ path: "/tmp/ui-live.png" });
  await q.waitForTimeout(10500); ok(hits.binance >= 2, "live: polls again after about 10 s (requests: " + hits.binance + ")"); }
{ const { txt } = await liveCase({ okxMul: { XAUT: 1.02 } }); ok(txt.includes("تحذير فرق"), "live: a 2% source difference raises the warning"); }
{ const { txt } = await liveCase({}); ok(!/Binance|OKX|Gate/.test(txt) && txt.includes("بتوقيت القاهرة") && /UTC \d\d:\d\d:\d\d/.test(txt), "live: Arabic source names, Cairo time with UTC second"); }
{ const { txt } = await liveCase({ binance: "451" }); ok(/XAUT\s*4000/.test(txt) && txt.includes("أو كي إكس") && txt.includes("بديل"), "live: falls back to OKX when Binance answers 451"); }
{ const { txt } = await liveCase({ binance: "zero" }); ok(txt.includes("أو كي إكس") && !/XAUT\s*0\b/.test(txt), "live: a zero price from Binance is rejected"); }
{ const { txt } = await liveCase({ binance: "451", okx: "fail" }); ok(txt.includes("جيت") && /XAUT\s*4000/.test(txt), "live: falls back to Gate.io when Binance and OKX fail"); }
{ const { txt } = await liveCase({ binance: "451", okx: "fail", gate: "fail" }); ok(txt.includes("تعذّر جلب"), "live: all sources down shows a clear warning and no price"); }
// 7. order book (browser only): mocked depth
function book(mid, depth, bidMul, askMul) { const bids = [], asks = []; for (let i = 0; i < 100; i++) { bids.push([String((mid * (1 - 0.00002 * (i + 1))).toFixed(4)), String(depth * bidMul)]); asks.push([String((mid * (1 + 0.00002 * (i + 1))).toFixed(4)), String(depth * askMul)]); } return { bids, asks }; }
async function obCase(o) {
  const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, deviceScaleFactor: 2 }); const q = await ctx.newPage(); const mids = { XAUT: 4000, BNB: 600, ETH: 3000, SOL: 150 };
  const sym = u => (u.searchParams.get("symbol") || u.searchParams.get("instId") || u.searchParams.get("currency_pair")).split(/[-_]/)[0].replace("USDT", "");
  await q.route("**/data-api.binance.vision/api/v3/depth*", r => { if (o.binance === "451") return r.fulfill({ status: 451, body: "x" }); const u = new URL(r.request().url()); const s = sym(u);
    r.fulfill({ contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify(o.crossed ? { bids: [["101", "1"]], asks: [["100", "1"]] } : book(mids[s], 1, s === "XAUT" ? 3 : 1, 1)) }); });
  await q.route("**/data-api.binance.vision/api/v3/ticker/**", r => r.fulfill({ status: 500, body: "x" }));
  await q.route("**/www.okx.com/api/v5/market/books*", r => { if (o.okx === "fail") return r.fulfill({ status: 500, body: "x" }); const u = new URL(r.request().url()); const s = sym(u);
    r.fulfill({ contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify({ data: [book(mids[s], 1, 1, 1)] }) }); });
  await q.route("**/api.gateio.ws/api/v4/spot/order_book*", r => { if (o.gate === "fail") return r.fulfill({ status: 500, body: "x" }); const u = new URL(r.request().url()); r.fulfill({ contentType: "application/json", headers: { "access-control-allow-origin": "*" }, body: JSON.stringify(book(mids[sym(u)], 1, 1, 1)) }); });
  await q.goto(base); await q.waitForSelector(".card"); await q.waitForTimeout(1500);
  return { q, txt: await tabsText(q, "#obook") };
}
{ const { q, txt } = await obCase({});
  ok(txt.includes("حي") && txt.includes("باينانس") && /XAUT/.test(txt) && txt.includes("نطاق"), "order book: 4 rows, label live, source, band shown");
  ok(/XAUT[\s\S]*?\+50%/.test(txt) && /BNB[\s\S]*?\+0%/.test(txt), "order book: imbalance computed (XAUT bids 3x asks = +50%, BNB equal = 0%)");
  ok(await q.$eval("body", e => e.scrollWidth <= window.innerWidth), "order book: no horizontal overflow");
  ok(txt.includes("اختلال الشراء/البيع") && txt.includes("فارق السعر بين أفضل شراء وأفضل بيع") && txt.includes("لا تقارن الأشرطة بين العملات"), "order book: imbalance, spread and per-coin band wording present");
  ok(!/Binance|OKX|Gate|UTC\s*\d{4}/.test(txt) && txt.includes("بتوقيت القاهرة") && /UTC \d\d:\d\d:\d\d/.test(txt), "order book: Arabic source names, Cairo time with UTC second");
  await q.screenshot({ path: "/tmp/ui-ob.png" }); }
{ const { txt } = await obCase({ binance: "451" }); ok(txt.includes("أو كي إكس") && txt.includes("بديل"), "order book: falls back to OKX"); }
{ const { txt } = await obCase({ binance: "451", okx: "fail" }); ok(txt.includes("جيت"), "order book: falls back to Gate.io"); }
{ const { txt } = await obCase({ crossed: true, okx: "fail", gate: "fail" }); ok(txt.includes("تعذّر جلب"), "order book: crossed or failed books are rejected with a clear warning"); }
await b.close(); srv.close(); process.exit(fails ? 1 : 0);
