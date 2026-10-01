"""
Validate PBIR JSON files against the JSON schema each file declares in "$schema".

Remote schema references are downloaded once and cached in tools/schema_cache/.

Usage (from the repo root):
    pip install jsonschema
    python tools/validate_pbir.py $(find B2B_Sales_Analytics.Report/definition -name "*.json")
"""
import json, sys, urllib.request, pathlib, hashlib
from jsonschema import Draft7Validator
from referencing import Registry, Resource

CACHE = pathlib.Path(__file__).parent / "schema_cache"
CACHE.mkdir(exist_ok=True)


def fetch(uri):
    f = CACHE / (hashlib.md5(uri.encode()).hexdigest() + ".json")
    if not f.exists():
        with urllib.request.urlopen(uri) as r:
            f.write_bytes(r.read())
    return json.loads(f.read_text(encoding="utf-8"))


def retrieve(uri):
    return Resource.from_contents(fetch(uri))


registry = Registry(retrieve=retrieve)
bad = 0
for path in sys.argv[1:]:
    doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8-sig"))
    schema = fetch(doc["$schema"])
    errs = sorted(Draft7Validator(schema, registry=registry).iter_errors(doc), key=lambda e: list(e.path))
    if errs:
        bad += 1
        print(f"FAIL {path}")
        for e in errs[:8]:
            print("   ", "/".join(map(str, e.path)), "->", e.message[:300])
    else:
        print(f"ok   {path}")
sys.exit(1 if bad else 0)
