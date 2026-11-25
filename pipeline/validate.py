"""Validation gate. Schema checks use the standard `jsonschema` library (Draft 2020-12).
Freshness and the record envelope are checked here on top of it."""
import json
from datetime import datetime, timezone
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

LABELS = ["measured", "simulated", "live", "hypothesis", "ai"]

def lint_schema(s):
    """Return [] if `s` is itself a valid Draft 2020-12 schema, else error strings."""
    try:
        Draft202012Validator.check_schema(s)
        return []
    except SchemaError as e:
        return [f"invalid schema: {e.message}"]

def check_schema(v, s, path="$"):
    bad = lint_schema(s)
    if bad:
        return bad
    errs = []
    for e in sorted(Draft202012Validator(s).iter_errors(v), key=lambda e: list(map(str, e.path))):
        where = path + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in e.path)
        errs.append(f"{where}: {e.message[:120]}")
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
