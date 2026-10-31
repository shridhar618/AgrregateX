# Team protocol

- Integration branch: `main`. Feature branches: `feat/resumable-loader` (Claude Opus) and `test/prd-benchmark-suite` (Codex).
- Never develop directly on main, force-push, rewrite shared history, merge your own PR, or import pg_trickle Git history.
- Issue #1 is the source of truth for cross-agent coordination. Read recent comments at assignment start, before interface-dependent work, and before PR submission. Post a milestone update; do not poll continuously.
- Each agent edits only owned paths in FILE_OWNERSHIP.md. A cross-owned/shared change requires a proposal and explicit agreement on Issue #1 before editing. Only the integration owner records accepted shared decisions in DECISION_LOG.md.
- Freeze SHARED_CONTRACT.md for parallel work. Interface changes are proposals until accepted and logged.
- Keep data, credentials, local `.env`, `.secrets.json`, DB volumes and generated benchmark outputs out of Git. Do not print or send secrets.
- Each agent pushes its branch and opens a review-requested PR to main. Reviewer checks ownership, evidence, contracts, correctness and safety. Squash merge only after approval; no automatic merge.
- Use this Issue comment template:

```text
[AGRREGATEX AGENT MESSAGE]

FROM: CODEX / OPUS
TO: CODEX / OPUS / BOTH

PHASE:
STATUS: STARTED / IN_PROGRESS / BLOCKED / REVIEW_NEEDED / DONE

SUMMARY:
...

FILES AFFECTED:
...

INTERFACE CHANGES:
...

REQUEST:
...

BRANCH:
...

EVIDENCE:
...
```

- On completion: update your status/handoff, publish branch/PR/evidence, request review, then stop and wait for explicit next work. No continuous background polling.
