"""Validation gate. Stdlib only. Every module output must pass before it is published."""
import json, re
from datetime import datetime, timezone

LABELS = ["measured", "simulated", "live", "hypothesis", "ai"]

def _type_ok(v, t):
    return {"object": isinstance(v, dict), "array": isinstance(v, list),
            "string": isinstance(v, str), "boolean": isinstance(v, bool),
            "number": isinstance(v, (int, float)) and not isinstance(v, bool),
            "integer": isinstance(v, int) and not isinstance(v, bool),
            "null": v is None}[t]

def check_schema(v, s, path="$"):
    """Small JSON Schema subset: type, required, properties, items, enum, pattern, minimum, minItems."""
    errs = []
    t = s.get("type")
    if t:
        ts = t if isinstance(t, list) else [t]
        if not any(_type_ok(v, x) for x in ts):
            return [f"{path}: expected {t}"]
    if "enum" in s and v not in s["enum"]:
        errs.append(f"{path}: not in {s['enum']}")
    if "pattern" in s and isinstance(v, str) and not re.search(s["pattern"], v):
        errs.append(f"{path}: pattern mismatch")
    if "minimum" in s and isinstance(v, (int, float)) and v < s["minimum"]:
        errs.append(f"{path}: below minimum")
    if isinstance(v, dict):
        for k in s.get("required", []):
            if k not in v:
                errs.append(f"{path}: missing '{k}'")
        for k, sub in s.get("properties", {}).items():
            if k in v:
                errs += check_schema(v[k], sub, f"{path}.{k}")
    if isinstance(v, list):
        if "minItems" in s and len(v) < s["minItems"]:
            errs.append(f"{path}: fewer than {s['minItems']} items")
        if "items" in s:
            for i, x in enumerate(v):
                errs += check_schema(x, s["items"], f"{path}[{i}]")
    return errs

def parse_ts(x):
    return datetime.fromisoformat(x.replace("Z", "+00:00"))

def age_hours(ts, now=None):
    now = now or datetime.now(timezone.utc)
    return (now - parse_ts(ts)).total_seconds() / 3600

def check_envelope(doc, envelope_schema, now=None):
    """Every record needs value, unit, source, fetched_at, label, max_age_hours.
    Returns (errors, stale_ids)."""
    errs, stale = [], []
    if not isinstance(doc, dict) or "records" not in doc or "meta" not in doc:
        return ["output must be an object with 'meta' and 'records'"], stale
    for i, r in enumerate(doc["records"]):
        e = check_schema(r, envelope_schema, f"records[{i}]")
        errs += e
        if not e:
            try:
                a = age_hours(r["fetched_at"], now)
            except ValueError:
                errs.append(f"records[{i}].fetched_at: not an ISO time")
                continue
            if a < -0.1:
                errs.append(f"records[{i}].fetched_at: in the future")
            elif a > r["max_age_hours"]:
                stale.append(r["id"])
    return errs, stale

def validate_output(doc, out_schema, envelope_schema, now=None):
    errs = check_schema(doc, out_schema)
    e2, stale = check_envelope(doc, envelope_schema, now)
    return errs + e2, stale

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)
