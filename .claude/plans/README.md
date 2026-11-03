# plans/ — Plan Files

`PLANS_DIR` (declared in `.claude/rules/PATH.md`). Holds one plan per feature, written by `vb-planner`:

```text
plans/
├── README.md                    (this file)
└── plan_<feature-name>.md       one file per feature
```

## What a plan contains

PRD with numbered requirements (FR / NFR / SC / API / DB), architecture, API contract or screen spec, SQL schema, a **Work Plan** (steps `S1…Sn`: agent, wave, depends on, requirement IDs, in-scope files, acceptance criteria), a **Requirement Traceability** table (the rubric of Phase 4), open questions, and a Plan Change Log.

## Rules

- **Only `vb-planner` writes plans.** Other agents read the sections their step cites; they do not edit plans.
- The plan is the **contract and source of truth**: there are no task files. Agents are launched with a prompt that names the plan and their step(s) in the **Work Plan**; when a plan section changes (a *plan change*, only while no agent is running), `vb-planner` updates the affected Work Plan rows and Requirement Traceability rows and logs it in the Plan Change Log.
- `<feature-name>` is the feature slug used by `/vb-development-workflow` (and by `doc/requirements_trace_<feature-name>.md`).
- Requirement IDs (FR-n, NFR-n, SC-n, API-n, DB-n) are stable — never renumber an existing ID.
- Do not store secrets or real connection strings in a plan.
- Created by `/vb-development-workflow` (Phase 1) and committed only after the user approved it; kept as the record of what was planned and which steps implemented it.
