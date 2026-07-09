# Composio — 100-App Buildability Research (agentic pipeline + case study)

Research **100 apps** for whether Composio can turn each into an agent-callable toolkit:
auth method, self-serve vs gated, API surface, existing MCP, and a buildability verdict —
then **find the patterns** across all 100 and **prove the answers are accurate** with a
verification loop.

**The deliverable is [`index.html`](index.html)** — a single, self-explanatory
case-study page (open it in a browser). Everything below is the pipeline that produced it.

> **▶ Live case study:** **https://composio-100-research.vercel.app**
> &nbsp;•&nbsp; **Reproduce every number with no API key:** `python src/patterns.py`

---

## TL;DR of the findings

- **Auth is rarely the blocker.** OAuth2 (43) + API key (34) = **77%** of primary auth; **91/100 speak REST**.
- **69/100 are self-serve; 64 are "easy wins"** (self-serve **and** buildable today).
- **The gate is concentrated:** Ads, enterprise commerce/CRM, and the newest AI/research tools.
  Dev/Infra and Productivity are **10/10 self-serve**; Marketing (4/10) and Fintech (3/10) are the gated corners.
- **Most common blocker is process, not tech:** app-review/verification and "no public API / CLI-only" tie at 9 each.
- **38/100 already ship an official MCP** — dense in dev/infra/productivity (overlap risk), sparse in the support/comms/ecommerce long tail (green field for Composio).

Full accuracy report is on the page; headline: **first-pass field accuracy 86.1% → ~100%** after the verification loop, with the biggest miss category being **MCP status** (parametric knowledge under-counts newly-shipped official MCPs).

---

## How it works (the pipeline)

```
data/apps.seed.json            the 100 apps + hints
        │
        ▼  ① research_agent.py   LLM + live web_search → strict schema per app
data/results.raw.json          (first pass)
        │
        ▼  ② verify_agent.py     independent, adversarial web re-research on a
data/verification.json           stratified 18-app sample, graded field-by-field
        │                        + a HUMAN adjudicates debatable calls
        ▼  ③ reconcile           apply doc-true corrections
data/results.json              (final, 100 rows; `verified`/`corrected` flags)
        │
        ▼  ④ patterns.py         cluster → distributions + headline
data/patterns.json
        │
        ▼  ⑤ index.html     the case study (data inlined; open in a browser)
```

| File | Role |
|---|---|
| `src/schema.py` | The strict per-app JSON schema + the shared research rubric (auditable "what we asked"). |
| `src/research_agent.py` | Stage ①. Claude Messages API + server-side `web_search`, structured output forced via a tool. |
| `src/verify_agent.py` | Stage ②. Independent verifier + stricter grader; prints the human-adjudication queue. |
| `src/patterns.py` | Stage ④. Reads `results.json`, writes `patterns.json`, prints every distribution. |
| `src/build_site.py` | Stage ⑤. Injects the 3 JSON files into `site/template.html` → self-contained `index.html`. |
| `data/results.baseline.json` | The **before** snapshot (knowledge-only first pass) — kept so the accuracy delta is real. |
| `data/results.json` | The **after** dataset (100 apps, reconciled). |
| `data/verification.json` | The 18-app hits/misses grading + the honest "what we got wrong". |

## Run it

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...

python src/research_agent.py --limit 10     # smoke test on 10 apps
python src/research_agent.py                 # research all 100  -> data/results.raw.json
python src/verify_agent.py                   # verify the sample -> data/verification.json
python src/patterns.py                       # cluster + headline -> data/patterns.json
```

`patterns.py` needs no API key — it just reads the committed `data/results.json`, so you can
reproduce every number on the page immediately:

```bash
python src/patterns.py
```

## How reviewers can test this

**In ~2 minutes (no setup):** open the live case study link. Patterns are up top, the 100-row matrix
is filterable/sortable, and the accuracy proof (86.1% → ~100%, with every hit and miss) is near the end.

**Reproduce the numbers (no API key):**
```bash
git clone <this-repo> && cd composio-100-research
python src/patterns.py          # prints every distribution shown on the page
python src/build_site.py        # regenerates index.html from the JSON
```

**Re-run the agent end-to-end (needs a key):**
```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python src/research_agent.py    # live-web research across the 100
python src/verify_agent.py      # independent adversarial re-check on the sample
```

**Inspect the raw data** (human- and machine-readable): `data/results.json` (final),
`data/results.baseline.json` (before), `data/verification.json` (hits/misses).

## Deploy (Vercel / any static host)

The page is one self-contained static file, so there is no build step.

- **Live now on Vercel:** https://composio-100-research.vercel.app
- **Redeploy / other hosts:** import the repo on Vercel or Netlify (framework "Other", no build
  step), or use GitHub Pages — `index.html` at the repo root is served at `/` automatically, no config.

Deployed on a normal host (no strict CSP), the *General Sans* font loads from its CDN and the page
renders pixel-perfect.

## Where Composio's own SDK/MCP plugs in

Marked `COMPOSIO` in `research_agent.py`. Two spots, both optional and gated on `COMPOSIO_API_KEY`:
1. **Ground in the registry** — `composio.toolkits.get(slug=...)` to read Composio's own
   auth-scheme + action model for an app instead of (or before) web search.
2. **Live probe** — use the SDK to create an auth-config and attempt a no-op action, turning
   "docs say a dev key works" into "a dev key actually worked."

## Where a human was needed (honest)

1. **Adjudicating `self-serve` vs `mixed`** — "free sandbox, paid/approved production" (Plaid, Devin, WhatsApp) is a judgment call the agent tends to over-round to "gated."
2. **`official` vs `community` MCP** — the agent under-counts brand-new first-party MCPs; a human confirmed Plain/Plaid/Amazon.
3. **The long-tail unknowns** — `fanbasis`, `Paygent`, `iPayX`, `Waterfall.io`, `Consensus`, `higgsfield` have thin/no public docs; the honest output is "blocked / needs human check," which a human labelled rather than the agent inventing an answer.
4. **Stale facts** — a human caught Amazon SP-API's removed AWS SigV4 requirement.

## Honesty notes / limitations

- Verification was measured on an **18-app stratified sample** (18%), not all 100. The other 82 carry a `confidence` field; `mcp_status` is the lowest-confidence dimension there (see the caveat in `data/results.json`).
- `data/results.json` is the single source of truth; `index.html` inlines a copy of it so the page is self-contained (Artifacts/static hosting can't fetch local files).
- **Design/fonts:** the page uses a warm editorial theme and loads the *General Sans* typeface from the Fontshare CDN with an `Inter`/system fallback — if that CDN is blocked (offline, or a strict-CSP host), it degrades to a clean system-sans and everything else still works. The page was render-verified headless (Puppeteer) with zero JS errors.
