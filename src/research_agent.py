"""
research_agent.py — Stage 2 of the pipeline: research each of the 100 apps into
the strict schema, backed by live web search + official-doc reading.

This is the standalone, runnable reproduction of what the case study actually did
with Claude Code subagents. It uses the Claude Messages API with Anthropic's
server-side web_search tool, forces structured output via a tool, and writes
data/results.raw.json.

    python src/research_agent.py --limit 10        # smoke test on 10 apps
    python src/research_agent.py                    # all 100

Env:
    ANTHROPIC_API_KEY   required

--- Where Composio fits (the "in the spirit of the role" part) ---
Two integration points are marked COMPOSIO below:
  1. Tool discovery: instead of free web search, ask Composio which apps it already
     has a toolkit/auth-scheme for (composio.toolkits.get / list) to ground the
     auth + surface answers in Composio's own registry.
  2. Live probe: for a "does a dev-tier key actually work" check, use the Composio
     SDK to attempt an auth-config + a no-op action and record the real result.
Both are optional and gated on COMPOSIO_API_KEY; the script runs without them.
"""
from __future__ import annotations
import argparse, json, os, sys, time
from schema import APP_SCHEMA, RUBRIC

try:
    import anthropic
except ImportError:
    sys.exit("pip install anthropic")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "data", "apps.seed.json")
OUT = os.path.join(ROOT, "data", "results.raw.json")

RESEARCH_MODEL = "claude-sonnet-5"          # fast, cheap enough for 100 fan-out workers
STRUCT_TOOL = {
    "name": "record_app",
    "description": "Record the structured research finding for one app.",
    "input_schema": APP_SCHEMA,
}


def research_one(client: "anthropic.Anthropic", app: dict) -> dict | None:
    """One app -> one validated schema object, grounded in live web search."""
    prompt = (
        f"{RUBRIC}\n\n"
        f"Research this app: {app['app']} (category: {app['category']}; "
        f"hint: {app['hint']}).\n"
        "Use web_search to find the OFFICIAL developer docs, open the auth page and "
        "the API overview, and confirm whether the VENDOR ships an MCP server. "
        "Then call record_app exactly once with your finding."
    )
    # COMPOSIO (1): ground in Composio's registry before/instead of web search:
    #   tk = composio.toolkits.get(slug=app['app'])   # auth_schemes, has_actions, ...
    #   prompt += f"\nComposio already models auth as: {tk.auth_config_details}"

    msgs = [{"role": "user", "content": prompt}]
    for _ in range(6):  # allow a few web_search round-trips
        resp = client.messages.create(
            model=RESEARCH_MODEL,
            max_tokens=2000,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}, STRUCT_TOOL],
            messages=msgs,
        )
        tool_use = next((b for b in resp.content if getattr(b, "type", None) == "tool_use"
                         and b.name == "record_app"), None)
        if tool_use:
            rec = dict(tool_use.input)
            rec["_model"] = RESEARCH_MODEL
            return rec
        if resp.stop_reason == "tool_use":
            # web_search executed server-side; feed the result back and continue
            msgs.append({"role": "assistant", "content": resp.content})
            msgs.append({"role": "user", "content": "Continue, then call record_app."})
        else:
            break
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="research only the first N apps")
    args = ap.parse_args()

    apps = json.load(open(SEED, encoding="utf-8"))["apps"]
    if args.limit:
        apps = apps[: args.limit]
    client = anthropic.Anthropic()

    out = []
    for i, app in enumerate(apps, 1):
        try:
            rec = research_one(client, app)
            status = "ok" if rec else "FAILED"
        except Exception as e:                       # keep the batch alive
            rec, status = None, f"error: {e}"
        if rec:
            rec["id"] = app["id"]
            out.append(rec)
        print(f"[{i:>3}/{len(apps)}] {app['app']:<26} {status}")
        time.sleep(0.3)                              # gentle on rate limits

    json.dump({"meta": {"source": "research_agent", "model": RESEARCH_MODEL},
               "apps": out}, open(OUT, "w", encoding="utf-8"), indent=2)
    print(f"\nwrote {OUT}  ({len(out)}/{len(apps)} apps)")


if __name__ == "__main__":
    main()
