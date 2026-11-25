"use strict";
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

function recCard(mod, rec) {
  const c = $("div", "card");
  c.append($("h2", null, mod.view ? mod.view.title : rec.id));
  c.append($("div", "val", typeof rec.value === "object" ? JSON.stringify(rec.value) : String(rec.value) + (rec.unit ? " " + rec.unit : "")));
  const s = $("div", "src");
  const b = badge(mod, rec);
  s.append("المصدر: ");
  if (/^https?:\/\//.test(rec.source.url)) { const l = $("a", null, rec.source.name); l.href = rec.source.url; l.rel = "noopener"; s.append(l); } else s.append(rec.source.name);
  s.append(" | الوقت: "); const tm = $("bdi", null, rec.fetched_at); tm.dir = "ltr"; s.append(tm);
  s.append(" | العمر: " + b.a.toFixed(1) + " ساعة ");
  s.append(b.wrap);
  if (mod.status !== "ok") s.append($("div", "src", "تحذير: آخر تشغيل للوحدة " + (mod.status === "failed" ? "فشل" : "قديم") + (mod.detail ? " (" + mod.detail + ")" : "")));
  c.append(s);
  return c;
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
  const bn = document.getElementById("banner");
  if (offline) msgs.unshift("غير متصل: عرض آخر نسخة محفوظة، والأعمار تقريبية");
  if (msgs.length) { bn.textContent = msgs.join(" | "); bn.hidden = false; }
  const tabs = {};
  for (const [id, m] of Object.entries(meta.modules)) { const t = (m.view && m.view.tab) || "modules"; (tabs[t] = tabs[t] || []).push([id, m]); }
  const nav = document.getElementById("tabs"), main = document.getElementById("main");
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
