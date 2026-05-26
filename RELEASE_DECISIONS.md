# Release Decisions

Decision lineage for release-time work on `master`. Continues the harness
decision numbering (path_c D1–D19, path_d D20–D47); release decisions begin at
D48. Append new entries; do not renumber.

---

## D48 — Pragmatic-key decision + credential-hygiene forward rule

**Filed:** 2026-05-26 (v0.1.0 release prep, Phase C kickoff).

Proceeded with API key `CJR278Q6KK` and the `.p12` password despite brief
chat-channel exposure during the portal walkthrough. Risk accepted:
Developer-role minimum scope, revocable at any time; chat history is on
Anthropic systems but not subject to training per policy.

**Forward rule:** credentials are NEVER uploaded or pasted into chat
interfaces; they go directly to local install via Claude Code's filesystem
tools, with interactive prompting for any password input.

**Post-release rotation recommended (architect TODO):** revoke + regenerate
the App Store Connect API key, re-export the `.p12` with a new password.
