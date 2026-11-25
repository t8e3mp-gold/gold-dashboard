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
const cards = await p.$$eval(".card", cs => cs.map(c => c.innerText));
ok(cards.length > 0, "cards rendered (" + cards.length + ")");
ok(cards.every(t => t.includes("المصدر") && t.includes("الوقت") && t.includes("العمر") && /مقاس|محاكاة|حي|فرضية|ذكاء اصطناعي/.test(t) && /محدّثة|قديمة/.test(t)), "every card has source, time, age, label and status");
ok(await p.$eval("body", e => e.scrollWidth <= window.innerWidth), "no horizontal overflow at 390px");
ok(await p.$$eval(".src bdi", bs => bs.every(x => x.getClientRects().length === 1)), "timestamps do not wrap");
ok(await p.$eval("#banner", e => e.hidden), "no banner when data is fresh");
await p.waitForTimeout(1500);
const pc = (await p.$$eval(".card", cs => cs.map(c => c.innerText))).filter(t => t.includes("سعر "));
ok(pc.length === 4 && pc.every(t => t.includes("مطابقة") || t.includes("مصدر واحد")), "4 price cards, each shows a cross-check or a single-source warning");
const kc = (await p.$$eval(".card", cs => cs.map(c => c.innerText))).filter(t => t.includes("شموع"));
ok(kc.length === 8 && kc.every(t => t.includes("آخر إغلاق") && t.includes("الفرق الوسيط")), "8 candle cards, each with last close and cross-check");
ok(await p.$$eval(".spark", e => e.length === 8 && e.every(x => x.querySelector("polyline").getAttribute("points").length > 100)), "8 sparklines drawn");
await p.screenshot({ path: "/tmp/ui-fresh.png" });
// 2. forced stale data: banner and stale badge appear
p = await load(j => { j.generated_at = "2026-01-01T00:00:00Z"; });
ok(await p.$eval("#banner", e => !e.hidden && e.innerText.includes("قديمة")), "banner shows when data is older than 26h");
// 3. forced failed module: banner and warning on card
p = await load(j => { for (const m of Object.values(j.modules)) { m.status = "failed"; m.detail = "test"; } });
ok(await p.$eval("#banner", e => !e.hidden && e.innerText.includes("مشكلة")), "banner shows when a module failed");
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
await b.close(); srv.close(); process.exit(fails ? 1 : 0);
