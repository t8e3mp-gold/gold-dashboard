"""Module runner. Reads modules/registry.json, orders modules by data dependencies,
runs each in isolation, validates output, publishes only valid output.
A failing module never stops the others and never overwrites its last good output."""
import json, os, re, subprocess, sys, tempfile, shutil
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(__file__))
import validate as V

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def p(*a): return os.path.join(ROOT, *a)

def shell_version(root):
    """Version of the page code (APP_VERSION in site/app.js) that this data was built together with."""
    try:
        m = re.search(r"const APP_VERSION = (\d+);", open(os.path.join(root, "site", "app.js"), encoding="utf-8").read())
        return int(m.group(1)) if m else 0
    except OSError:
        return 0


def load_manifests(root=ROOT):
    reg = V.load(os.path.join(root, "modules", "registry.json"))
    extra = [x for x in os.environ.get("EXTRA_MODULES", "").split(",") if x]
    reg = {"enabled": list(reg["enabled"]) + [x for x in extra if x not in reg["enabled"]]}
    schema = V.load(os.path.join(root, "schemas", "manifest.schema.json"))
    mans, errs = {}, []
    for mid in reg["enabled"]:
        mp = os.path.join(root, "modules", mid, "manifest.json")
        try:
            m = V.load(mp)
        except Exception as e:
            errs.append(f"{mid}: cannot read manifest ({e})"); continue
        e = V.check_schema(m, schema)
        if m.get("id") != mid:
            e.append("manifest id must equal folder name")
        if e:
            errs += [f"{mid}: {x}" for x in e]; continue
        mans[mid] = m
    return mans, errs

def lint_manifests(mans, root=ROOT, data_dir=None):
    """CI checks: inputs must be produced by an enabled module or exist as a data file;
    output schemas must use only supported keywords; schema files must exist."""
    data_dir = data_dir or os.path.join(root, "data")
    produced = {o["id"] for m in mans.values() for o in m["outputs"]}
    errs = []
    for mid, m in mans.items():
        for i in m["inputs"]:
            if i not in produced and not os.path.exists(os.path.join(data_dir, i + ".json")):
                errs.append(f"{mid}: input '{i}' is produced by no enabled module and no data file exists")
        for h in m.get("history", []):
            if h not in {o["id"] for o in m["outputs"]}:
                errs.append(f"{mid}: history id '{h}' is not an output")
        for o in m["outputs"]:
            sp = os.path.join(root, "modules", mid, o["schema"])
            if not os.path.exists(sp):
                errs.append(f"{mid}: schema file missing: {o['schema']}"); continue
            errs += [f"{mid}/{o['schema']}: {e}" for e in V.lint_schema(V.load(sp))]
    return errs

def check_history(old_doc, new_doc):
    """Append-only contract: every old record (id, fetched_at) must still be in the new file."""
    new = {(r["id"], r["fetched_at"]) for r in new_doc["records"]}
    lost = [k for k in ((r["id"], r["fetched_at"]) for r in old_doc["records"]) if k not in new]
    return [f"history record dropped or changed: {k[0]} @ {k[1]}" for k in lost[:5]]

def order(mans):
    """Topological order. Raises on cycles. Inputs that no module produces must exist as data files."""
    producers = {o["id"]: mid for mid, m in mans.items() for o in m["outputs"]}
    deps = {mid: {producers[i] for i in m["inputs"] if i in producers and producers[i] != mid}
            for mid, m in mans.items()}
    out, done = [], set()
    while len(out) < len(mans):
        ready = sorted(m for m in mans if m not in done and deps[m] <= done)
        if not ready:
            raise ValueError("dependency cycle among: " + ", ".join(sorted(set(mans) - done)))
        for m in ready:
            out.append(m); done.add(m)
    return out

def sandbox_prefix(network):
    """Command prefix that removes network access for modules that did not declare it.
    Fails closed: if no isolation mechanism works, a no-network module is not run."""
    if network:
        return []
    probes = [["unshare", "-rn"],
              ["sudo", "-n", "unshare", "-n", "setpriv", f"--reuid={os.getuid()}", f"--regid={os.getgid()}", "--clear-groups"]]
    for pre in probes:
        try:
            if subprocess.run(pre + ["true"], capture_output=True, timeout=10).returncode == 0:
                return pre
        except (OSError, subprocess.TimeoutExpired):
            pass
    return None

def _limits(timeout):
    import resource
    def f():
        resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
        resource.setrlimit(resource.RLIMIT_FSIZE, (50 << 20, 50 << 20))
        resource.setrlimit(resource.RLIMIT_CPU, (int(timeout) + 5, int(timeout) + 5))
    return f

def run_module(m, data_dir, root=ROOT, now=None):
    """Returns (status, detail). Runs in a throwaway copy of the module with only its declared inputs.
    Network is off unless permissions.network is true. Publishes outputs only if all validate."""
    env_schema = V.load(os.path.join(root, "schemas", "envelope.schema.json"))
    mdir = os.path.join(root, "modules", m["id"])
    box = tempfile.mkdtemp(prefix="mod-")
    tmp = os.path.join(box, "out"); os.makedirs(tmp)
    try:
        sdata = os.path.join(box, "data"); os.makedirs(sdata)
        for i in m["inputs"]:
            src = os.path.join(data_dir, i + ".json")
            if not os.path.exists(src):
                if i in {o["id"] for o in m["outputs"]}:
                    continue          # a module may read its own previous output (first run has none)
                return "failed", f"missing input '{i}'"
            shutil.copy(src, os.path.join(sdata, i + ".json"))
        sdir = os.path.join(box, "module"); shutil.copytree(mdir, sdir)
        net = bool(m.get("permissions", {}).get("network", False))
        pre = sandbox_prefix(net)
        if pre is None:
            return "failed", "no network isolation available on this machine; refusing to run a no-network module unsandboxed"
        envp = {"PATH": os.environ.get("PATH", ""), "DATA_DIR": sdata, "OUT_DIR": tmp,
                "PYTHONPATH": os.path.join(root, "pipeline")}
        # env is passed as arguments because sudo resets the environment of the command it starts
        cmd = pre + ["env", "-i"] + [f"{k}={v}" for k, v in envp.items()] + [sys.executable if c == "python" else c for c in m["run"]]
        tmo = m.get("timeout_s", 120)
        r = subprocess.run(cmd, cwd=sdir, capture_output=True, text=True, timeout=tmo, preexec_fn=_limits(tmo),
                           env=envp)
        if r.returncode != 0:
            return "failed", "exit %d: %s" % (r.returncode, r.stderr.strip()[-300:])
        stale_all = []
        for o in m["outputs"]:
            fp = os.path.join(tmp, o["id"] + ".json")
            if not os.path.exists(fp):
                return "failed", f"output '{o['id']}' not written"
            doc = V.load(fp)
            sch = V.load(os.path.join(mdir, o["schema"]))
            errs, stale = V.validate_output(doc, sch, env_schema, now)
            if o["id"] in m.get("history", []):
                oldp = os.path.join(data_dir, o["id"] + ".json")
                if os.path.exists(oldp):
                    errs += check_history(V.load(oldp), doc)
            if errs:
                return "failed", "validation: " + "; ".join(errs[:5])
            stale_all += stale
        for o in m["outputs"]:
            shutil.move(os.path.join(tmp, o["id"] + ".json"), os.path.join(data_dir, o["id"] + ".json"))
        return ("stale" if stale_all else "ok"), ("stale: " + ", ".join(stale_all) if stale_all else "")
    except subprocess.TimeoutExpired:
        return "failed", "timeout"
    finally:
        shutil.rmtree(box, ignore_errors=True)

def main(root=ROOT, data_dir=None):
    data_dir = data_dir or os.path.join(root, "data")
    os.makedirs(data_dir, exist_ok=True)
    mans, errs = load_manifests(root)
    mp = os.path.join(data_dir, "meta.json")
    prev = V.load(mp) if os.path.exists(mp) else {"modules": {}}
    meta = {"schema_version": 1, "app_version": shell_version(root), "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "manifest_errors": errs, "modules": {}}
    for mid in order(mans):
        m = mans[mid]
        status, detail = run_module(m, data_dir, root)
        last_ok = meta["generated_at"] if status in ("ok", "stale") else prev["modules"].get(mid, {}).get("last_ok")
        meta["modules"][mid] = {"name_ar": m["name_ar"], "name_en": m["name_en"], "version": m["version"],
                                "kind": m["kind"], "label": m["label"], "source": m["source"],
                                "max_age_hours": m["max_age_hours"], "status": status, "detail": detail,
                                "last_ok": last_ok, "outputs": [o["id"] for o in m["outputs"]],
                                "view": m.get("view")}
        print(f"{mid}: {status} {detail}")
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1, sort_keys=True)
    bad = [k for k, v in meta["modules"].items() if v["status"] == "failed"]
    return 1 if (bad or errs) else 0

if __name__ == "__main__":
    sys.exit(main())
