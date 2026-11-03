# doc/ — Analyses and Traceability Reports

`DOC_DIR` (declared in `.claude/rules/PATH.md`). Holds the documents the agents produce about the application, kept in the Claude area (`.claude\doc`) — not among the customer's program files:

```text
doc/
├── README.md                              (this file)
├── analysis_<solution-name>.md            codebase analysis written by vb-analyzer
├── KNOWHOW.md                             shared memo of know-how, tips, issues and solutions (user + all agents, via /savememo)
├── analysis_<solution-name>_<aspect>.md   per-aspect reports written by /codeanalyze (database, quality, backend-tests, frontend-tests, requirements, summary)
└── requirements_trace_<feature-name>.md   requirement-to-code traceability report written by vb-requirement-analysis
```

Plans are not here — they live in `../plans/` (`PLANS_DIR`).

## Rules

- **`vb-analyzer`** writes `analysis_<solution-name>.md` (read-only analysis of the customer's program in `<GIT_REPO>`; it never changes application source).
- **`vb-requirement-analysis`** writes `requirements_trace_<feature-name>.md` for a feature, using that feature's plan in `PLANS_DIR`.
- **`/codeanalyze`** runs the agents in read-only analysis mode; each writes only its own `analysis_<solution-name>_<aspect>.md` (`db-developer` → `database`, `vb-reviewer` → `quality`, `vb-backend-tester` → `backend-tests`, `vb-frontend-tester` → `frontend-tests`, `vb-requirement-analysis` → `requirements`, `vb-analyzer` → `summary`), committed as `analyze:` with that agent's `subagent:` line.
- **`KNOWHOW.md`** is written by the user and by every agent, only through `/savememo` (`savememo.py`: locked, secret-checked, numbered `KH-NNN`); search it before debugging, add an entry after solving; entries are never deleted, only marked `outdated`; committed as `docs:`.
- Other agents read these files; they do not edit them (except `KNOWHOW.md` through `/savememo`).
- `<feature-name>` is the same slug as the plan (`plans/plan_<feature-name>.md`) .
- Record the date, the target repo path, and the commit or state analyzed, so a stale report can be recognised.
- Do not store secrets, passwords, or real connection strings in these documents (redact them).
- Commit documents with the feature: analyses as `analyze:` (by `vb-analyzer`), trace reports as `review2:` (by `vb-requirement-analysis`).
