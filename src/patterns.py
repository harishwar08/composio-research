"""
patterns.py — cluster the 100-app results and print the cross-app patterns.

Reads data/results.json (the reconciled final dataset) and emits:
  - distributions for self_serve, buildability, primary auth family, mcp_status, api_type
  - per-category cross-tabs (self-serve vs gated, buildability)
  - "easy wins" (self-serve + ready) and "needs outreach" (gated/blocked) lists
  - the most common blocker theme
Also writes data/patterns.json for the HTML page to consume.

Usage:  python src/patterns.py
"""
import json, os, re
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "data", "results.json")
OUT = os.path.join(ROOT, "data", "patterns.json")


def auth_family(primary: str) -> str:
    p = (primary or "").lower()
    if "oauth" in p:
        return "OAuth2"
    if "hmac" in p or "signature" in p:
        return "API key + signature"
    if "api key" in p or "consumer key" in p:
        return "API key"
    if "key-pair" in p or "keypair" in p:
        return "Key-pair (JWT)"
    if "bot token" in p:
        return "Bot token"
    if "basic" in p:
        return "Basic"
    if any(t in p for t in ["pat", "token", "access token", "auth token"]):
        return "Token / PAT"
    if "none" in p:
        return "None (OSS/CLI)"
    return "Unknown / other"


def main():
    data = json.load(open(RESULTS, encoding="utf-8"))
    apps = data["apps"]
    n = len(apps)

    self_serve = Counter(a["self_serve"] for a in apps)
    build = Counter(a["buildability"] for a in apps)
    mcp = Counter(a["mcp_status"] for a in apps)
    auth = Counter(auth_family(a["primary_auth"]) for a in apps)
    api = Counter(("GraphQL" if "graphql" in a["api_type"].lower() and "rest" not in a["api_type"].lower()
                   else "REST+GraphQL" if "graphql" in a["api_type"].lower()
                   else "REST" if "rest" in a["api_type"].lower()
                   else "None/CLI" if a["api_breadth"] == "none"
                   else "Other") for a in apps)

    by_cat = defaultdict(lambda: Counter())
    build_by_cat = defaultdict(lambda: Counter())
    for a in apps:
        by_cat[a["category"]][a["self_serve"]] += 1
        build_by_cat[a["category"]][a["buildability"]] += 1

    easy_wins = [a["app"] for a in apps if a["self_serve"] == "self-serve" and a["buildability"] == "ready"]
    needs_outreach = [a["app"] for a in apps if a["self_serve"] == "gated" or a["buildability"] == "blocked"]
    official_mcp = [a["app"] for a in apps if a["mcp_status"] == "official"]

    # blocker themes
    themes = Counter()
    for a in apps:
        b = (a.get("blocker") or "").lower()
        if not b:
            continue
        if any(k in b for k in ["review", "approval", "verification", "registration", "developer token"]):
            themes["app review / approval / verification"] += 1
        elif any(k in b for k in ["paid", "plan", "customer account", "metered", "credits", "contract", "cap"]):
            themes["paid plan / customer account required"] += 1
        elif any(k in b for k in ["enterprise", "partner", "sales", "instance", "admin"]):
            themes["enterprise / partnership gate"] += 1
        elif any(k in b for k in ["no public", "no self-serve", "no hosted", "sparse", "no documented", "wrap the cli"]):
            themes["no public/self-serve API (or CLI-only)"] += 1
        else:
            themes["other"] += 1

    out = {
        "n": n,
        "self_serve": dict(self_serve),
        "buildability": dict(build),
        "mcp_status": dict(mcp),
        "auth_family": dict(auth.most_common()),
        "api_type": dict(api.most_common()),
        "self_serve_by_category": {k: dict(v) for k, v in by_cat.items()},
        "buildability_by_category": {k: dict(v) for k, v in build_by_cat.items()},
        "easy_wins": easy_wins,
        "easy_wins_count": len(easy_wins),
        "needs_outreach": needs_outreach,
        "needs_outreach_count": len(needs_outreach),
        "official_mcp": official_mcp,
        "official_mcp_count": len(official_mcp),
        "blocker_themes": dict(themes.most_common()),
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), indent=2)

    def bar(c):
        items = c.items() if hasattr(c, "items") else c
        return "  ".join(f"{k}={v}" for k, v in items)

    print(f"N = {n}\n")
    print("SELF-SERVE:      ", bar(self_serve))
    print("BUILDABILITY:    ", bar(build))
    print("MCP STATUS:      ", bar(mcp))
    print("AUTH FAMILY:     ", bar(auth.most_common()))
    print("API TYPE:        ", bar(api.most_common()))
    print(f"\nEASY WINS (self-serve + ready): {len(easy_wins)}")
    print(f"NEEDS OUTREACH (gated or blocked): {len(needs_outreach)} -> {needs_outreach}")
    print(f"OFFICIAL MCP: {len(official_mcp)}")
    print("\nBLOCKER THEMES:  ", bar(themes.most_common()))
    print("\nSELF-SERVE BY CATEGORY:")
    for k, v in by_cat.items():
        print(f"  {k:42s} {dict(v)}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
