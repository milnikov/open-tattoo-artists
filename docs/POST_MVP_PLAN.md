# Post-MVP Plan

Planned updates after the MVP is stable. Not yet scheduled; order may change.

---

## 1. Artist ranking by “followed by other artists”

### Goal

- Obtain **followers** and **following** lists for each artist in the directory (e.g. from Instagram, within policy and technical limits).
- Rank artists by **how many other artists from our list follow them**: artists who are followed by more directory artists appear higher.
- In the web app, let the user **switch between**:
  - **Alphabetical** view (current default), and
  - **“Most followed by artists”** (or similar) view — this special ordering.

### Intended behaviour

- Data: For each artist we need at least “count of directory artists who follow this artist” (and optionally the full graph for future features).
- List view: A toggle or sort option to choose “A–Z” vs “By influence” (or “Most followed by artists”).
- Ranking can be stored in an index (e.g. `data/indexes/` or a new field) and refreshed periodically; the directory remains the source of truth for who is in the list.

### Considerations

- **Data source**: Instagram API or other means must comply with platform ToS and rate limits. Alternatives (e.g. self-reported, manual, or other social links) can be considered.
- **Privacy / storage**: Prefer storing only what’s needed for ranking (e.g. counts or internal IDs), not full follower lists, unless required for the product.
- **Updates**: Define how often the “followed by artists” data is refreshed and how that is run (cron, manual, etc.).

---

## 2. OpenClaw bot — automatic GitHub issue processing

### Goal

- Set up **openClaw** so it can **automatically process requests/issues** in the project’s GitHub repo (e.g. add-artist and report-problem issues).
- Reduce manual triage and speed up handling of suggestions and reports.

### Intended setup (to be detailed)

- **Scope**: Which issues the bot handles (new “add artist”, “report problem”, or both), and which repos.
- **Permissions**: GitHub token or app with access to read issues, add comments, change labels, close/reopen, and optionally create branches/PRs if the bot will propose data changes.
- **Behaviour**: Document desired flows, e.g.:
  - Triage (label, assign, or comment with next steps).
  - Validation (e.g. check required fields, duplicate artist).
  - Auto-close when criteria are met or link to a merged PR.
- **Deployment**: Where openClaw runs (e.g. GitHub Actions, separate server, serverless), how it is triggered (webhook, cron), and where configuration and secrets live.
- **Docs**: Once the setup is fixed, add a short “OpenClaw setup” section or doc (e.g. in `docs/`) with steps to install, configure, and run the bot.

### Outcome

- A clear setup so openClaw can run continuously and process GitHub issues according to the agreed rules; this doc (or a dedicated `OPENCLAW_SETUP.md`) will be updated with the final steps.
