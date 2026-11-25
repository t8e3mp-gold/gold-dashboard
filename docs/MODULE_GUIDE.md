# Adding a module

1. Copy `modules/hello/` to `modules/<new-id>/`.
2. Edit `manifest.json`: id (same as folder), names, version, kind, inputs (data ids it reads), outputs (data id + schema file), label, source, max_age_hours, schedule, run, and optional view.
3. Edit `run.py`. It reads files from `$DATA_DIR`, writes each output to `$OUT_DIR/<output-id>.json` as `{"meta": {...}, "records": [envelope records]}`.
4. Write the output schema in `schema/` and a fixture test in `tests/`.
5. Add the id to `modules/registry.json`.
6. Push. CI loads every manifest, runs all tests and the whole pipeline.

External data source: make a `source` module. Fetch from a public URL, map fields to the envelope, put the real URL and fetch time in each record. For a cross-check, add a second source module for the same quantity and set `checked_against`.

Limits: modules cannot read secrets; they get only PATH, DATA_DIR, OUT_DIR. Output outside the declared outputs is ignored.

## History files (append-only)
Add `"history": ["<output-id>"]` to the manifest for an output that must keep past records (trade logs, snapshots). The runner rejects a new output that drops or changes any earlier record (matched by id and fetched_at) and keeps the old file. Append new records; never rewrite old ones.

## Schema keywords
Output schemas may use only: type, required, properties, items, enum, pattern, minimum, minItems (plus description, title). Any other keyword fails the run, so a schema cannot silently do nothing.

## Repo checks (CI)
Unit tests, module tests, a secret and personal-data scan (`python tools/scan.py .`), a pipeline run on scratch data, and a mobile UI test (`tests/ui/ui.test.mjs`).

## Fallback source (Plan B)
If your module reads an outside source, say in `README.md` of the module which second source replaces it when the first is down or blocked. Show the fallback's own source and label. Never blend two sources into one number.
