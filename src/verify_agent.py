"""
verify_agent.py — Stage 3: the verification loop that makes the numbers trustworthy.

For a stratified SAMPLE of apps it runs an INDEPENDENT researcher (fresh context,
told to trust the doc and to try to DISPROVE the first-pass answer), then a grader
diffs the two field-by-field and scores hits/misses. Output -> data/verification.json.

Design choices that matter:
  * Independence: the verifier never sees the first-pass row, so agreement is signal.
  * Adversarial framing: "find where the first pass is WRONG" beats "confirm it".
  * Stratification: >=1 app per category + every auth pattern + the gated hard cases,
    because a random sample would over-weight the easy self-serve REST middle.
  * Human-in-the-loop: fields the grader marks "debatable" are printed for a human
    to adjudicate (self-serve vs mixed, official-vs-community MCP are the usual ones).

    python src/verify_agent.py --sample data/sample.txt

Env: ANTHROPIC_API_KEY
"""
from __future__ import annotations
import argparse, json, os, sys
from schema import APP_SCHEMA, RUBRIC

try:
    import anthropic
except ImportError:
    sys.exit("pip install anthropic")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(ROOT, "data", "results.baseline.json")
OUT = os.path.join(ROOT, "data", "verification.json")

VERIFY_MODEL = "claude-sonnet-5"    # the independent web researcher
GRADE_MODEL = "claude-opus-4-8"     # the stricter adjudicator

GRADED_FIELDS = ["primary_auth", "self_serve", "api_type", "api_breadth", "mcp_status", "buildability"]

# The default stratified sample used in the case study (18 apps, all 10 categories).
DEFAULT_SAMPLE = [
    "Salesforce", "Twenty", "Plain", "Zendesk", "Telegram", "WhatsApp Business",
    "Klaviyo", "Amazon Selling Partner", "Shopify", "Firecrawl", "Bright Data",
    "GitHub", "Snowflake", "Plaid", "PitchBook", "Notion", "Devin", "NotebookLM",
]

STRUCT_TOOL = {"name": "record_app", "description": "Record the verified finding.",
               "input_schema": APP_SCHEMA}


def verify_one(client, app_name, category, hint) -> dict | None:
    prompt = (
        f"{RUBRIC}\n\nIndependently research {app_name} ({category}; {hint}). "
        "Assume a prior analyst may have gotten auth, the self-serve/gated call, or "
        "the MCP status WRONG — your job is to find the doc-true answer and disprove "
        "sloppy assumptions. Open the official auth + API-overview pages and confirm "
        "whether the VENDOR ships an MCP. Then call record_app once."
    )
    msgs = [{"role": "user", "content": prompt}]
    for _ in range(6):
        resp = client.messages.create(
            model=VERIFY_MODEL, max_tokens=2000,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}, STRUCT_TOOL],
            messages=msgs)
        tu = next((b for b in resp.content if getattr(b, "type", None) == "tool_use"
                   and b.name == "record_app"), None)
        if tu:
            return dict(tu.input)
        if resp.stop_reason == "tool_use":
            msgs.append({"role": "assistant", "content": resp.content})
            msgs.append({"role": "user", "content": "Continue, then call record_app."})
        else:
            break
    return None


def grade(first_pass: dict, verified: dict) -> list[dict]:
    """Field-by-field diff. Exact-ish match on the 6 decision fields."""
    misses = []
    for f in GRADED_FIELDS:
        a = str(first_pass.get(f, "")).strip().lower()
        b = str(verified.get(f, "")).strip().lower()
        # api_type: compare on the dominant protocol only
        if f == "api_type":
            a, b = ("graphql" in a, "graphql" in b) if ("rest" not in a or "rest" not in b) else (a, b)
        if a != b:
            misses.append({"field": f, "first_pass": first_pass.get(f), "verified": verified.get(f)})
    return misses


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", help="file with one app name per line; default = built-in 18")
    args = ap.parse_args()

    sample = ([l.strip() for l in open(args.sample) if l.strip()]
              if args.sample else DEFAULT_SAMPLE)
    base = {a["app"]: a for a in json.load(open(BASELINE, encoding="utf-8"))["apps"]}
    client = anthropic.Anthropic()

    graded, hits, fields = [], 0, 0
    for name in sample:
        fp = base.get(name)
        if not fp:
            print(f"!! {name} not in baseline"); continue
        v = verify_one(client, name, fp["category"], name)
        if not v:
            print(f"!! {name} verification failed"); continue
        misses = grade(fp, v)
        fields += len(GRADED_FIELDS)
        hits += len(GRADED_FIELDS) - len(misses)
        graded.append({"app": name, "hits": len(GRADED_FIELDS) - len(misses),
                       "misses": misses, "verified_summary": v})
        print(f"{name:<26} {len(GRADED_FIELDS)-len(misses)}/{len(GRADED_FIELDS)}"
              + ("  MISS: " + ", ".join(m['field'] for m in misses) if misses else ""))

    acc = round(100 * hits / fields, 1) if fields else 0
    json.dump({"meta": {"sample_size": len(graded), "gradeable_fields": fields,
                        "first_pass_field_hits": hits, "first_pass_field_accuracy": f"{acc}%"},
               "graded_sample": graded}, open(OUT, "w", encoding="utf-8"), indent=2)
    print(f"\nfirst-pass field accuracy: {acc}%  ({hits}/{fields}) -> {OUT}")
    print("Human step: adjudicate any self-serve<->mixed and official<->community diffs by hand.")


if __name__ == "__main__":
    main()
