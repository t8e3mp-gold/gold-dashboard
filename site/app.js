"use strict";
// All data is rendered with textContent only. No HTML from data files is ever injected.
const LABELS = {measured:"مقاس", simulated:"محاكاة", live:"حي", hypothesis:"فرضية", ai:"ذكاء اصطناعي"};
const $ = (t, c, x) => { const e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; };
const ageH = ts => (Date.now() - Date.parse(ts)) / 36e5;

async function getJSON(p) { const r = await fetch(p, {cache: "no-store"}); if (!r.ok) throw new Error(p + " " + r.status); return r.json(); }

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
  const meta = await getJSON("data/meta.json");
  const g = ageH(meta.generated_at);
  document.getElementById("gen").textContent = "آخر تحديث للبيانات: \u2066" + meta.generated_at + "\u2069 (قبل " + g.toFixed(1) + " ساعة)" + (g > 26 ? " تحذير: البيانات قديمة" : "");
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
