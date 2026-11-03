# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository is a Claude Code project for developing **VB.NET** applications for a customer, and it also holds the customer's program. It is **one git repository** (`GIT_REPO`, declared in `.claude/rules/PATH.md`) with two areas:

| Area | Where | Contents | Used for |
|------|-------|----------|----------|
| Customer area | `GIT_REPO` (the repository root, outside `.claude\` and this file) | The customer's program, its production code/config, and the customer's documents | Developers **implement** here (never deployed by an agent); the testers write nothing here |
| Claude area | `.claude\` (`CLAUDE_DIR`) and this file | Agents, rules, skills, hooks, plans (with their embedded research), analyses, trace reports, SQL scripts, **test code**, the know-how memo | Planning, research, documentation, SQL, tests |

There is **one history and one feature branch per feature**: code, tests, SQL, plan, and documents of a feature all live on the same branch. Each agent commits its own work in its own commit(s); customer-area and Claude-area changes go in separate commits. Build/lint/test commands for the program are in `ENVIRONMENT_FILE` (once the program is added, re-run `/init`). The only machine-specific setting is `GIT_REPO` in `PATH.md` (the repository root); every other path is derived from it, so `/config-update` is all a new computer needs.

## Standing Orders (always)

1. **Always follow the rules in `.claude/rules/`** (`PATH.md`, `AGENT.md`, `WORKFLOWS.md`, `ENVIRONMENT.md`, `PERFORMANCE.md`). They apply to every request, in the main session and in every subagent. Read the rule before acting; when a request conflicts with a rule, say so and ask the user instead of silently bending the rule. Paths come from the variables in `PATH.md`, never from a guess.
2. **Always delegate work to the suitable subagent — never do it yourself.** The main session is the orchestrator: it picks the agent per `AGENT.md` (research → `vb-researcher`; analysis → `vb-analyzer`; plan → `vb-planner`; backend → `vb-backend-developer`; UI → `vb-frontend-developer`; SQL → `db-developer`; tests → `vb-backend-tester` / `vb-frontend-tester`; review → `vb-reviewer` + `vb-requirement-analysis`), launches it with a precise prompt (the plan and its step), independent agents in parallel, and verifies the result from files and git. The main session does not write application code, tests, SQL, plans, or analyses inline, even for a small change; the only things it edits itself are what a skill explicitly assigns to the orchestrator (the `GIT_REPO` row via `/config-update`, memo entries via `/savememo`) and answering questions. If no agent fits, tell the user instead of doing the work inline.
3. **Search the memo, save the lesson.** At the first error or surprise run `/savememo search` (`.claude/doc/KNOWHOW.md`) before debugging; after solving something non-obvious run `/savememo add`. Agents do the same (`Skill: savememo`).
4. **Diagrams are always Mermaid.** Every diagram, flow, sequence, ER model, state machine, or dependency graph you put in a Markdown document is written as a fenced ```mermaid block (flowchart, sequenceDiagram, erDiagram, stateDiagram-v2, classDiagram) — never ASCII art, never an image, and never a diagram without the `mermaid` language tag. Keep a one-line caption above it saying what it shows; explain it in text too, because not every viewer renders Mermaid. Tables stay tables. Applies to every document any agent writes (plans, analyses, trace reports, READMEs).

---

## How work flows

Commands: `/vb-development-workflow <feature>` (Plan → Implement → Test → Review; `--resume <feature-name>` after an interruption), `/codeanalyze [solution]` (read-only analysis of the customer's program by all relevant agents → reports in `.claude/doc`), `/savememo` (shared know-how / issue / solution memo `.claude/doc/KNOWHOW.md`: search it when a problem appears, save after solving), `/config-update` (new computer / moved folder). Full rules: `.claude/rules/WORKFLOWS.md` and `.claude/rules/AGENT.md`.

There are **no task files**. The approved, committed plan is the contract; the orchestrator tracks progress with a todo list and git history.

1. **Plan (Phase 1) — one file** — `vb-researcher` (sourced research + reuse decision) and `vb-analyzer` (report-only mode, only if the structure is unknown) run in parallel; when the **customer's documents or written requirements exist** (REQ-in-scope), `vb-requirement-analysis` also produces a requirement-grounding brief. None of them writes a file: each returns its report, which the orchestrator pastes into `vb-planner`'s prompt. `vb-planner` drafts the single file `plans/plan_<feature>.md` — the reports embedded as *Research*, *Existing Solution* and *Requirement Grounding*, then PRD with numbered requirements, architecture, API contract / screen spec, SQL schema, a **Work Plan** (steps `S1…Sn`: agent, wave, depends on, requirement IDs, in-scope files, acceptance criteria) and a **Requirement Traceability** table — **without committing**. When REQ-in-scope, `vb-requirement-analysis` scope-checks the draft (scope creep, gaps) and the planner revises. Then the orchestrator **stops and asks the user to approve the plan**; only after approval is the plan committed (one `plans:` commit). Never skipped.
2. **Implement (Phase 2)** — each Work Plan step is routed to its agent by layer: `.sql` / procedures / views / queries → `db-developer`; services, repositories, Web API, class libraries → `vb-backend-developer`; WinForms / WPF / MVC / WebForms → `vb-frontend-developer`. Independent steps with disjoint *In scope* files run in parallel; a `db-developer` Query Contract finishes first and is handed to the backend step. Each agent applies its own gate and commits its own work; the orchestrator confirms from the final report and `git log` (commits touch only *In scope* files). Gate: all committed and the MSBuild build passes.
3. **Test (Phase 3)** — `vb-backend-tester` and `vb-frontend-tester` run in parallel on the committed files and write only under `.claude/test/`. A testability gap or a product defect goes back to the developer that owns the file (surgical fix), then the tester re-runs. "Nothing testable" is a valid result.
4. **Review (Phase 4)** — `vb-reviewer` (and, when REQ-in-scope, `vb-requirement-analysis` walking the plan's Requirement Traceability table) review in parallel. Findings are grouped by the agent that owns the file and fixed surgically, affected testers re-run, and **new** reviewer instances re-review (an agent never verifies its own fix); at most 3 review passes, then the user decides.
5. **Questions go through the orchestrator.** Agents cannot talk to the user: an agent that needs a decision ends its final report with `QUESTION FOR USER: …`; the orchestrator relays it and relaunches the agent with the answer. A subagent never writes to a prod database — `db-developer` delivers the script and blocks; the orchestrator runs it only after the user's explicit same-turn approval. An incomplete agent is relaunched at most twice, then the user is asked.
6. **Defects are fixed, not tracked.** The finder reports the defect (file:line or test, expected vs actual, requirement ID, severity); the orchestrator maps the file to its owning agent, which fixes only that. A wrong or incomplete plan is a *plan change*: only while no agent is running, by `vb-planner`, shown to the user again and committed as `plans:`.
7. **Parallel agents share one working tree.** Steps of the same wave have disjoint *In scope* files (a legacy `.vbproj` is owned by one step); every agent stages and commits only its own files by explicit path (`git add <path>`, then `git commit -m "<type>: …" -m "subagent: <name>" -- <path>`), never `git add .` / `-A` / `-u`, `commit -a`, `--amend`, `stash`, `reset`, or branch switching.
8. **Interrupted runs resume** from the plan and git: `/vb-development-workflow --resume <feature-name>` rebuilds the status from the committed plan, `git log --grep "subagent:"`, and `git status`, shows it to the user, and continues where they agree.
9. **Branch and finish** — **the user creates the feature branch**; on `main` / `master` / `production` / `prod` / `release*` (or a detached HEAD) an agent never commits and never creates or switches branches: it stops and asks the user (`Skill: git-commit`). Finish = merge checklist and a final report listing the commits on the feature branch. Agents never push, merge, deploy, or touch a production branch.

## Target environment

| Item | Value |
|------|-------|
| Language | Visual Basic .NET (`.vbproj`) |
| Framework | .NET Framework 4.8 |
| IDE | Visual Studio 2026 Community |
| Database | SQL Server 2025 Express edition |
| DB management | SQL Server Management Studio (SSMS) |

Full details, VB.NET conventions, and build/test commands (MSBuild and VSTest): `ENVIRONMENT_FILE` (declared in `.claude/rules/PATH.md`).

## Layout of `.claude/`

- `agents/` — subagents: `vb-researcher`, `vb-analyzer`, `vb-planner`, `vb-backend-developer`, `vb-frontend-developer`, `db-developer`, `vb-backend-tester`, `vb-frontend-tester`, `vb-reviewer`, `vb-requirement-analysis`
- `rules/` — `PATH.md` (declares the repository's two areas and every path as a variable; agents, skills, and scripts reference the variables instead of literal paths), `AGENT.md` (when to use which agent), `WORKFLOWS.md` (agent chains), `ENVIRONMENT.md` (target stack), `PERFORMANCE.md` (model/context strategy)
- `skills/` — `vb-development-workflow` (`/vb-development-workflow`: Phases 1–4 and finish, orchestrating the agents above with the plan as the contract), `codeanalyze` (`/codeanalyze`: runs `vb-analyzer`, `db-developer`, `vb-reviewer`, both testers and, when documents exist, `vb-requirement-analysis` in read-only analysis mode and writes `analysis_<solution>_<aspect>.md` plus a summary), `savememo` (`/savememo`: add / search / list / show / status entries in `doc/KNOWHOW.md`; user and every agent), `git-commit` (invoked by agents before every commit: branch rule — the user creates the feature branch, message format, explicit-path staging), and `config-update` (`/config-update`: updates `GIT_REPO` in `PATH.md` after moving to another computer, then runs `/codeanalyze` unless `--no-analyze`)
- `doc/` — our analyses (`analysis_<solution>.md`, from `vb-analyzer`; `analysis_<solution>_<aspect>.md`, from `/codeanalyze`), requirement traceability reports (`requirements_trace_<feature>.md`, from `vb-requirement-analysis`), and the know-how memo (`KNOWHOW.md`); the customer's own documents are in `GIT_REPO` (`CUSTOMER_DOC_DIR`, read-only)
- `test/` — test projects written by `vb-backend-tester` / `vb-frontend-tester` (`Backend\`, `Frontend\`); they reference the customer's projects by relative path, so no test content enters the customer area
- `db/` — `.sql` scripts written by `db-developer` (`migrations/`, `procs/`, `views/`, `queries/`)
- `plans/` — one plan per feature (`plan_<feature-name>.md`) written by `vb-planner`: research, existing-solution analysis, requirements, architecture, Work Plan, Requirement Traceability
- `hooks/` — commit guards, registered in `settings.local.json` (registered on every Bash/PowerShell call and acting only on git commands; `guard_main_branch.py`: no commit on `main` / `master` / `production` / `prod` / `release*` or a detached HEAD; `guard_staging.py`: no `git add .` / `-A` / `-u`, no `git commit -a` / `--amend`, every commit lists its own (not repo-wide) paths after `--` because parallel agents share one working tree, and the user-only commands `push` / `pull` / `rebase` / `merge` / `stash` / `reset` / `clean` / `checkout` / `switch` / creating branches or tags are blocked; `validate_commit_msg.py`: message given with `-m`, `<type>: <description>` subject of at most 72 characters, `subagent:` on its own line naming a known agent; types `feat` / `fix` / `perf` / `refactor` / `test` / `docs` / `chore` plus `analyze` (analysis), `plans` (the plan), `review1` (reviewer's changes), `review2` (requirement-analysis report and comments); memo entries are `docs`). Commits also carry a `subagent: <agent-name>` line.
