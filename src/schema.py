"""
schema.py — the strict per-app research schema.

Every research/verify agent is forced to return an object matching APP_SCHEMA.
Validation happens at the tool-call boundary so the model retries on a mismatch
instead of us parsing free text. This is what keeps 100 rows comparable.
"""

APP_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "app", "category", "one_liner", "auth_methods", "primary_auth",
        "self_serve", "self_serve_reason", "api_type", "api_breadth",
        "mcp_status", "buildability", "blocker", "evidence", "confidence",
    ],
    "properties": {
        "app": {"type": "string"},
        "category": {"type": "string"},
        "one_liner": {"type": "string", "maxLength": 160},
        "auth_methods": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "primary_auth": {"type": "string"},
        # the decision-driving fields — constrained enums so they cluster cleanly
        "self_serve": {"enum": ["self-serve", "mixed", "gated"]},
        "self_serve_reason": {"type": "string"},
        "api_type": {"type": "string"},           # e.g. "REST", "GraphQL", "REST + GraphQL", "none (CLI)"
        "api_breadth": {"enum": ["broad", "moderate", "narrow", "none"]},
        "mcp_status": {"enum": ["official", "community", "none"]},
        "buildability": {"enum": ["ready", "ready-with-caveats", "blocked"]},
        "blocker": {"type": ["string", "null"]},
        "evidence": {"type": "array", "items": {"type": "string", "format": "uri"}, "minItems": 1},
        "confidence": {"enum": ["high", "medium", "low"]},
        "mcp_by": {"type": ["string", "null"]},
        "notes": {"type": "string"},
    },
}

# The instruction block shared by the research and verify agents. Kept in one
# place so "what we asked the model" is auditable and identical across runs.
RUBRIC = """\
You research a SaaS/dev app so an AI-agent platform (Composio) can decide whether
to build an agent toolkit for it. Fill every field. Rules:

- self_serve: "self-serve" = a developer can get WORKING credentials free/trial
  themselves; "mixed" = self-serve to build/test but production needs approval,
  a paid plan, or review; "gated" = needs a paid contract, admin/enterprise
  provisioning, partnership, or contact-sales before you can call the API.
- mcp_status: "official" ONLY if the vendor themselves ship an MCP server;
  "community" if only third parties do; "none" otherwise. Do not guess "official".
- buildability: "ready" (build today), "ready-with-caveats" (buildable but a real
  friction: paid plan, review, wrap-a-CLI), "blocked" (no self-serve API today).
- evidence: cite the official doc URL you actually read. No doc, no claim.
- Trust the doc over any prior assumption. Note anything surprising in notes.
"""
