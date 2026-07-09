"""
build_site.py — Stage 5: render the self-contained case-study page.

Reads the three data files, adds two derived fields the page needs, and injects
one JSON blob into site/template.html -> site/index.html. The page is fully
self-contained (data inlined) so it works as a static file or an Artifact.

    python src/build_site.py
"""
import json, os, datetime
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
TEMPLATE = os.path.join(ROOT, "site", "template.html")
OUT = os.path.join(ROOT, "site", "index.html")


def load(name):
    return json.load(open(os.path.join(D, name), encoding="utf-8"))


def de_dash(obj):
    """Strip em/en dashes from every string in the data (design choice: no '—' on the page).
    Spaced dashes become ', '; any stray dash becomes '-'."""
    if isinstance(obj, str):
        return (obj.replace(" — ", ", ").replace(" – ", ", ")
                   .replace("—", "-").replace("–", "-"))
    if isinstance(obj, list):
        return [de_dash(x) for x in obj]
    if isinstance(obj, dict):
        return {k: de_dash(v) for k, v in obj.items()}
    return obj


def main():
    results = load("results.json")
    patterns = load("patterns.json")
    verification = load("verification.json")
    seed = load("apps.seed.json")
    apps = results["apps"]

    # derived fields the page consumes
    patterns["categories_order"] = seed["meta"]["categories"]
    patterns["rest_speaking"] = sum(1 for a in apps if "rest" in a["api_type"].lower())
    mcp_by_cat = {}
    for a in apps:
        mcp_by_cat.setdefault(a["category"], Counter())[a["mcp_status"]] += 1
    patterns["mcp_by_category"] = {k: dict(v) for k, v in mcp_by_cat.items()}

    data = de_dash({
        "apps": apps,
        "patterns": patterns,
        "verification": verification,
        "generated": datetime.date.today().isoformat(),
    })

    html = open(TEMPLATE, encoding="utf-8").read()
    html = html.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    open(OUT, "w", encoding="utf-8").write(html)
    print(f"wrote {OUT}  ({len(apps)} apps, {len(html):,} bytes)")


if __name__ == "__main__":
    main()
