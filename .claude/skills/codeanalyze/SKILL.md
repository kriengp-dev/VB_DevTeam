---
name: codeanalyze
description: Analyzes the structure and health of the customer's software project (the program in GIT_REPO) by running every relevant read-only agent and writing one report file per aspect into DOC_DIR — project/architecture map (vb-analyzer), database and SQL layer (db-developer), code quality and risks (vb-reviewer), backend and frontend testability and coverage (vb-backend-tester, vb-frontend-tester), and requirement conformance against the customer's documents (vb-requirement-analysis, only when documents exist) — then a consolidated summary. Changes no application code, creates no plan. Use on an unfamiliar or inherited codebase, before /vb-development-workflow, or to refresh stale analyses.
---

## When to Use

- First contact with the customer's program, or an inherited / undocumented solution
- Before `/vb-development-workflow` when `<DOC_DIR>` has no (or only stale) `analysis_*.md`
- The user says "analyze the code", "วิเคราะห์โครงสร้าง", or invokes `/codeanalyze [solution-name] [--only a,b] [--no-build]`

**Skip when:** the change is small and the structure is known, or the repository has no program yet (stop and say so).

**Next step after this skill:** `/vb-development-workflow <feature>` — the planner reads the summary's "Before You Start" and "Potential Issues".

---

## Hard Rules

1. **Read-only on the program.** No agent changes anything in the customer area (`<GIT_REPO>` outside `.claude\`). The only files written are the report files listed below, in `<DOC_DIR>` (Claude area). The testers write **no test files** in this mode and the reviewers do **no refactoring and no traceability comments** — this overrides their usual write scope for this run.
2. **This skill creates no plan and writes no files itself** — it launches agents, verifies their reports, and reports. Plans are written only by `vb-planner`.
3. **Paths come from `PATH.md`** (`<GIT_REPO>`, `<DOC_DIR>`, `<CUSTOMER_DOC_DIR>`, `<TEST_DIR>`, `<DB_DIR>`). Never guess a path; skip `.claude\`, `bin\`, `obj\`, `packages\` when searching the program.
4. **No secrets in reports** — connection strings are reported as server/database names only; passwords, tokens, and keys are redacted.
5. **No database access.** `db-developer` analyzes scripts, code, and config only; it does not connect to any server in this mode.
6. **Evidence-based.** Every finding cites `file:line`, a command output, or a customer document section.
7. **Diagrams are Mermaid.** Every diagram in a report (architecture, project dependencies, ER model, flows) is a fenced ```mermaid block with a one-line caption, never ASCII art or an image; tell each agent this in its prompt. The summary's "System in one page" contains at least one Mermaid architecture diagram and the database report an `erDiagram` when tables are known. Gate 2 checks that no report holds a diagram outside a `mermaid` block.
8. **Commits:** each agent commits its own report by explicit path (`analyze: …` + its own `subagent:` line) on the feature branch, via `Skill: git-commit`. This skill never commits, pushes, or switches branches.

---

## Report Files (all in `<DOC_DIR>`, `<solution>` = the `.sln` name in kebab-case)

| Aspect | Agent | File | Always? |
|--------|-------|------|---------|
| structure | `vb-analyzer` | `analysis_<solution>.md` (format in the agent) | yes |
| database | `db-developer` | `analysis_<solution>_database.md` | when SQL / data access exists |
| quality | `vb-reviewer` | `analysis_<solution>_quality.md` | yes |
| backend-tests | `vb-backend-tester` | `analysis_<solution>_backend-tests.md` | when backend code exists |
| frontend-tests | `vb-frontend-tester` | `analysis_<solution>_frontend-tests.md` | when UI code exists |
| requirements | `vb-requirement-analysis` | `analysis_<solution>_requirements.md` | only when `<CUSTOMER_DOC_DIR>` or a plan holds written requirements |
| summary | `vb-analyzer` (second pass) | `analysis_<solution>_summary.md` | yes — last |

Each report starts with: date, target path, git branch and `git rev-parse --short HEAD` analyzed, analyst agent. Section outlines are in each step below.

---

## Pre-flight

1. Read `.claude/rules/PATH.md`. If `<GIT_REPO>` is empty, a drive root, missing, or not a git repository, **stop and ask the user** (run `/config-update`).
2. Check the branch (`git branch --show-current`). If it is `main` / `master` / `production` / `prod` / `release*` (or detached), **stop and ask the user to create a branch** (for example `docs/code-analysis`) — agents commit their reports, the hooks block commits there, and you never create or switch branches yourself.
3. Find the solutions: Glob `<GIT_REPO>/**/*.sln` and `**/*.vbproj`, ignoring `.claude\`, `bin\`, `obj\`, `packages\`. None found → stop: "no program in the repository yet". More than one `.sln` → analyze each (reports named per solution) unless `$ARGUMENTS` names one. No `.sln` but `.vbproj` files → name the report after the repository folder.
4. Parse `$ARGUMENTS`: an optional solution name, `--only <aspects>` (comma list of: structure, database, quality, backend-tests, frontend-tests, requirements; `structure` always runs and `summary` runs last), `--no-build` (agents must not build or run tests).
5. Decide which optional aspects apply:
   - database: any `.sql`, `SqlConnection`, `DbContext`, or `connectionString` in the program, or SQL in `<DB_DIR>`
   - backend-tests: backend code (Library / Web API / WCF / service classes) exists
   - frontend-tests: WinForms / WPF / MVC / WebForms UI exists
   - requirements: files in `<CUSTOMER_DOC_DIR>` or a `<PLANS_DIR>/plan_*.md`; otherwise skip and say so in the report
6. Existing reports for the solution: if `analysis_<solution>*.md` exist, ask the user once: **refresh** (agents overwrite their own file; git keeps the history) or **keep** (skip aspects that already have a report newer than the last commit touching the program). Never delete reports.
7. Snapshot the program's state: `git status --porcelain -- . ":(exclude).claude" ":(exclude)CLAUDE.md"` and `git rev-parse --short HEAD` — used in the verification step.
8. Create a todo list for the phases below.

---

## Phase 1 — Structure (`vb-analyzer`)

Launch **`vb-analyzer`** alone, first, because the other agents read its project map.

Prompt: *Analyze solution `<solution>` in `<GIT_REPO>` following your steps and report format; write `<DOC_DIR>/analysis_<solution>.md`; follow `$ARGUMENTS` (`--no-build` = skip Step 6 and say so). No plan or step — skip the plan-specific items of your Work Assignment section. Commit as `analyze:` per your Commit section.*

Gate 1: the file exists, has its 9 sections, and lists every project found in pre-flight. Otherwise relaunch once with the missing items.

---

## Phase 2 — Specialists (launch together, one message, one Agent call each)

Each prompt contains: the solution name, `<GIT_REPO>`, the path of `analysis_<solution>.md` to read first, the exact output file, the read-only rule (Hard Rules 1, 4, 5, 6, 7), "No plan or step — skip the plan-specific items of your Work Assignment section", `--no-build` if set, and the commit line (`analyze: add <aspect> analysis for <solution>`, `subagent: <agent>`, explicit path, `Skill: git-commit`). Output files are disjoint, so they run in parallel safely.

### database — `db-developer`  → `analysis_<solution>_database.md`
Static analysis only. Sections: 1 Data-access approach and connection names (redacted); 2 Tables/entities, keys, relationships (from scripts, EF mappings, or SQL in code); 3 Stored procedures, views, functions called and where; 4 Raw / concatenated SQL (injection risk, `file:line`); 5 Query hot-spots (SELECT *, missing paging, N+1, scans, implicit conversions) with a suggested index or rewrite; 6 Migration / script organization and whether they run unchanged in SSMS; 7 SQL Server 2025 Express fit (database size cap, no SQL Server Agent, compatibility level assumptions); 8 Open questions for the user.

### quality — `vb-reviewer`  → `analysis_<solution>_quality.md`
Review the whole code base, risk-first (data access, startup, auth, async, disposal, then UI), using your severity scale — **Section 1 only**; do not run Section 2 (refactor), do not edit any file. Sections: 1 Summary table (CRITICAL / HIGH / MEDIUM / LOW counts); 2 Findings per severity (`file:line`, problem, why it matters, suggested fix, effort S/M/L); 3 `Option Strict` / `Option Explicit` / `TreatWarningsAsErrors` per project; 4 Async and resource-handling patterns; 5 Layering violations (SQL or business rules in forms/code-behind); 6 Dead code and duplication candidates; 7 Recommended order of fixes.

### backend-tests — `vb-backend-tester`  → `analysis_<solution>_backend-tests.md`
Assess only; write **no test files**, change no code. Sections: 1 Existing tests (projects, framework, count, where; ours in `<TEST_DIR>`); 2 Run result if the toolchain exists and `--no-build` is not set (real counts, otherwise "not run: reason"); 3 Testability map per backend class (seams, static state, `New` inside methods, direct `SqlConnection`) rated easy / needs seam / hard; 4 Coverage gaps ranked by risk; 5 Proposed test plan (what to test first, unit vs SQL Express integration, needed seams) as text — no plan created; 6 Test-environment needs (test database, connection-string variable).

### frontend-tests — `vb-frontend-tester`  → `analysis_<solution>_frontend-tests.md`
Same rules. Sections: 1 UI surface (forms / windows / views / pages count by kind); 2 Existing UI tests; 3 Testability map (presenters / view models vs logic in code-behind, event-handler weight, missing selectors / `AutomationId`); 4 Gaps ranked by risk; 5 Proposed test plan as text; 6 Feasibility of UI automation (FlaUI / Selenium) for the critical flows.

### requirements — `vb-requirement-analysis`  → `analysis_<solution>_requirements.md`
Only if requirements exist. **Audit mode: no refactoring, no traceability comments, no code or test changes.** Take requirements from `<CUSTOMER_DOC_DIR>` and any `<PLANS_DIR>/plan_*.md`; give each a stable ID (`CD-<n>` for customer-document items, with document and section). Sections: 1 Sources read; 2 Traceability matrix (requirement → code `file:line` / not found / partial); 3 Behavioral non-conformance and gaps; 4 Undocumented behavior found in code; 5 Ambiguities to put to the user. No plan steps, no traceability-table outcomes.

Wait for all agents; then:

Gate 2 — for each launched agent: its file exists, has every section above (empty sections say "none found" with what was checked), carries the header (date, branch, commit), contains no secret-looking strings (`password=`, `pwd=`, `secret`, `Bearer `, long base64) except redacted ones, and the agent's commit exists (`git log -1 --grep "subagent: <agent>" -- <file>`). A gap → relaunch that agent **once** with the exact list; still failing → record it as "incomplete" in the summary.

---

## Phase 3 — Summary (`vb-analyzer`, second pass)

Launch **`vb-analyzer`** again with the paths of all reports. It reads them (no new code scan beyond spot checks) and writes `<DOC_DIR>/analysis_<solution>_summary.md`:

1. Scorecard — one line per aspect: status (done / skipped + reason / incomplete), headline number (projects, tables, CRITICAL+HIGH findings, tests present, requirements covered), link to the file
2. System in one page — stack, architecture, application surface, data layer (from the structure and database reports)
3. Top risks — the 10 most important findings across all reports, each with severity, `file:line`, report link
4. Conflicts between reports (for example the analyzer says Layered, the reviewer found SQL in forms) and which is right, with evidence
5. Recommended next features / work packages — ordered, each tagged with the requirement or finding behind it (text only; **no plan, no steps**)
6. Before You Start (prerequisites for planning: environment, access, decisions the user must make)
7. Open questions for the user (collected from all reports)

Commit: `analyze: add summary for <solution>`, `subagent: vb-analyzer`.

---

## Verification (before reporting)

1. `git status --porcelain` outside `.claude\`/`CLAUDE.md` is identical to the pre-flight snapshot — **the customer area is untouched**. If not, report the changed files to the user and stop; do not revert anything yourself.
2. Only files named in the table above changed under `.claude\`.
3. Every report has a commit with the right `subagent:` line (`git log --grep "subagent:" `) and no uncommitted report file remains. If an agent could not commit (protected branch, index lock), say so.
4. Read the summary and confirm every report is linked and counted.

---

## Report to the User

Reply with:

- Solutions analyzed and the commit analyzed
- The scorecard (aspect | agent | file | status)
- Top 5 risks, with `file:line`
- Skipped or incomplete aspects and why
- Questions only the user can answer
- Next step: **`/vb-development-workflow <feature>`** (the planner will use the summary), or ask to fix specific findings through the normal workflow — fixes are never made by this skill

---

## Key Principles

1. **Analysis, not change** — the program and the tests are never modified; only reports are written
2. **One report per aspect, one owner per report** — disjoint files let the agents run in parallel without collisions
3. **Structure first, specialists in parallel, summary last** — each phase consumes the previous output
4. **Verify from files and git, not from replies**
5. **Stop on a bad target** — no program, protected branch, or unconfirmed repo means ask, not guess
