// Cloudflare Worker "gold-d1-sync" v2: pulls public JSON from the GitHub repo and upserts it into D1. No token, no secret.
// GitHub stays the source of truth. D1 is a mirror. Free plan: 10 ms CPU, 50 subrequests per run.
// v3: also keeps the dashboard data fresh: hourly it checks data/meta.json and dispatches the Refresh workflow when it is older than 100 min (GitHub token stored only as the encrypted Worker secret GH_TOKEN, scope Actions read/write on this one repo).
// v2 changes: per-file try/catch, record validation, last_error stored in D1, no public /sync-now (a public write trigger could burn the daily write quota).
const BASE = "https://raw.githubusercontent.com/t8e3mp-gold/gold-dashboard/main/data/";
const FILES = ["forward-log", "forward-score", "forward-summary", "forward-archive"];
const KEEP = 300;
const REPO = "t8e3mp-gold/gold-dashboard", STALE_MIN = 100;

async function keeper(env) {
  const now = new Date().toISOString(); let v;
  try {
    const m = await fetch(BASE + "meta.json", { cf: { cacheTtl: 0 } });
    if (!m.ok) throw new Error("meta http " + m.status);
    const gen = Date.parse((await m.json()).generated_at); if (!gen) throw new Error("meta has no generated_at");
    const age = Math.round((Date.now() - gen) / 60000);
    if (age < STALE_MIN) v = "fresh age=" + age + "min, no dispatch";
    else if (!env.GH_TOKEN) v = "ERROR no GH_TOKEN";
    else {
      const d = await fetch("https://api.github.com/repos/" + REPO + "/actions/workflows/refresh.yml/dispatches", { method: "POST", headers: { Authorization: "Bearer " + env.GH_TOKEN, Accept: "application/vnd.github+json", "User-Agent": "gold-d1-sync", "X-GitHub-Api-Version": "2022-11-28" }, body: JSON.stringify({ ref: "main" }) });
      v = (d.status === 204 ? "dispatched" : "ERROR dispatch http " + d.status) + " age=" + age + "min";
    }
  } catch (e) { v = "ERROR " + String(e).slice(0, 80); }
  await env.DB.prepare("CREATE TABLE IF NOT EXISTS sync_status (k TEXT PRIMARY KEY, v TEXT, at TEXT)").run();
  await env.DB.prepare("INSERT INTO sync_status (k, v, at) VALUES ('last_keeper', ?1, ?2) ON CONFLICT(k) DO UPDATE SET v = excluded.v, at = excluded.at").bind(v, now).run();
  return v;
}

async function sync(env) {
  const now = new Date().toISOString(), stmts = [], seen = {}, errors = [];
  await env.DB.prepare("CREATE TABLE IF NOT EXISTS records (source TEXT NOT NULL, id TEXT NOT NULL, fetched_at TEXT, json TEXT NOT NULL, synced_at TEXT NOT NULL, PRIMARY KEY (source, id))").run();
  await env.DB.prepare("CREATE TABLE IF NOT EXISTS sync_status (k TEXT PRIMARY KEY, v TEXT, at TEXT)").run();
  for (const f of FILES) {
    try {
      const r = await fetch(BASE + f + ".json", { cf: { cacheTtl: 0 } });
      if (!r.ok) { seen[f] = "skip " + r.status; if (r.status !== 404) errors.push(f + " http " + r.status); continue; }
      const recs = ((await r.json()).records || []).slice(-KEEP);
      let ok = 0, bad = 0;
      for (const x of recs) {
        if (!x || typeof x.id !== "string" || !x.id) { bad++; continue; }
        stmts.push(env.DB.prepare("INSERT INTO records (source, id, fetched_at, json, synced_at) VALUES (?1, ?2, ?3, ?4, ?5) ON CONFLICT(source, id) DO UPDATE SET fetched_at = excluded.fetched_at, json = excluded.json, synced_at = excluded.synced_at").bind(f, x.id, x.fetched_at || null, JSON.stringify(x), now));
        ok++;
      }
      seen[f] = ok;
      if (bad) errors.push(f + ": " + bad + " invalid records skipped");
    } catch (e) { errors.push(f + ": " + String(e).slice(0, 80)); }
  }
  try { if (stmts.length) await env.DB.batch(stmts); } catch (e) { errors.push("write: " + String(e).slice(0, 80)); }
  await env.DB.prepare("INSERT INTO sync_status (k, v, at) VALUES ('last_error', ?1, ?2) ON CONFLICT(k) DO UPDATE SET v = excluded.v, at = excluded.at").bind(errors.join(" | ") || "none", now).run();
  return { synced_at: now, files: seen, rows_written: stmts.length, errors };
}
export default {
  async scheduled(event, env, ctx) {
    if (event.cron === "40 */3 * * *") ctx.waitUntil(sync(env).catch(e => console.log("sync failed " + e)));
    ctx.waitUntil(keeper(env).catch(e => console.log("keeper failed " + e)));
  },
  async fetch(request, env) {
    const c = await env.DB.prepare("SELECT source, count(*) AS n, max(synced_at) AS last_sync FROM records GROUP BY source").all();
    const s = await env.DB.prepare("SELECT k, v, at FROM sync_status").all().catch(() => ({ results: [] }));
    const g = (k) => { const r = s.results.find(x => x.k === k); return r ? { v: r.v, at: r.at } : null; };
    return Response.json({ mirror: "gold-dashboard D1", tables: c.results, last_error: g("last_error"), last_keeper: g("last_keeper") });
  },
};
