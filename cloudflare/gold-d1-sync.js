// Cloudflare Worker "gold-d1-sync" v2: pulls public JSON from the GitHub repo and upserts it into D1. No token, no secret.
// GitHub stays the source of truth. D1 is a mirror. Free plan: 10 ms CPU, 50 subrequests per run.
// v2 changes: per-file try/catch, record validation, last_error stored in D1, no public /sync-now (a public write trigger could burn the daily write quota).
const BASE = "https://raw.githubusercontent.com/t8e3mp-gold/gold-dashboard/main/data/";
const FILES = ["forward-log", "forward-score", "forward-summary", "forward-archive"];
const KEEP = 300;

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
  async scheduled(event, env, ctx) { ctx.waitUntil(sync(env).catch(e => console.log("sync failed " + e))); },
  async fetch(request, env) {
    const c = await env.DB.prepare("SELECT source, count(*) AS n, max(synced_at) AS last_sync FROM records GROUP BY source").all();
    const s = await env.DB.prepare("SELECT v, at FROM sync_status WHERE k = 'last_error'").all().catch(() => ({ results: [] }));
    return Response.json({ mirror: "gold-dashboard D1", tables: c.results, last_error: s.results[0] || null });
  },
};
