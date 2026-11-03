# Paths

Single place where every reference path is declared. Agents, rules, skills, slash commands, and hook scripts use the **variable names** below (written `<NAME>` in prose); change a value here and everything follows. This file is the only place a literal path is written.

---

## One Git Repository, Two Areas

There is **one git repository** (`GIT_REPO`): one history, one set of branches. It holds two areas:

| Area | Where | What it is | Agents may |
|------|-------|------------|------------|
| **Customer area** | `<GIT_REPO>` (the repository root, everything outside `.claude\` and `CLAUDE.md`) | The customer's program (source code), its production code/config, and the customer's own documents. This is what the developers **implement** in | Read everything; **write application code** (developer agents only; the testers write nothing here); never write plans, analyses, or SQL scripts here; never deploy |
| **Claude area** | `<CLAUDE_DIR>` = `<GIT_REPO>\.claude\` (and `CLAUDE.md`) | Agents, rules, skills, hooks, plans (with their embedded research), analyses, trace reports, SQL scripts, **test code**, and the know-how memo | Write plans, docs, and SQL scripts here (by the owning agent); never write application code here |

Because the history is shared, **every change of a feature — code, tests, SQL, plan, documents — lives on the same feature branch**, committed in separate commits by area and by author agent (see "Branches and commits").

---

## Declared Paths (edit this)

| Name | Value | Meaning |
|------|-------|---------|
| `GIT_REPO` | `E:\Work\Hirate\github\VB_DevTeam` | Root of the single git repository (contains `.claude\`, `CLAUDE.md`, and the customer's program) |

This is the only machine-specific value. Everything else is derived from it.

---

## Derived Paths (do not edit separately)

**Customer area (under `GIT_REPO`)**

| Name | Value | Purpose |
|------|-------|---------|
| `CUSTOMER_DOC_DIR` | `<GIT_REPO>\doc` | The customer's own documents (specifications, requirements, manuals). **Read-only reference** for `vb-analyzer`, `vb-planner`, and `vb-requirement-analysis`; agents never create or edit files here unless the user explicitly asks. The folder name `doc` is an assumption — change it here if the customer's documents live elsewhere. It is not `DOC_DIR` (our documents under `.claude\doc`) |

The application's own files (`.sln`, `.vbproj`, `.vb`, config) are located by searching `GIT_REPO` — always skip `.claude\`, `bin\`, `obj\`, `packages\`. Our tests are in `<TEST_DIR>`. Production code and configuration are part of the customer area.

**Claude area (under `GIT_REPO`)**

| Name | Value | Purpose |
|------|-------|---------|
| `CLAUDE_DIR` | `<GIT_REPO>\.claude` | Root of the Claude area |
| `AGENTS_DIR` | `<CLAUDE_DIR>\agents` | Agent definitions |
| `RULES_DIR` | `<CLAUDE_DIR>\rules` | Rules (this file, `AGENT.md`, `WORKFLOWS.md`, `ENVIRONMENT.md`, `PERFORMANCE.md`) |
| `DOC_DIR` | `<CLAUDE_DIR>\doc` | Our analyses (`analysis_<solution>.md`, `analysis_<solution>_<aspect>.md`), requirement traceability reports (`requirements_trace_<feature>.md`), and the know-how memo (`KNOWHOW.md`) — not the customer's documents |
| `PLANS_DIR` | `<CLAUDE_DIR>\plans` | Plan files written by `vb-planner` (`plan_<feature-name>.md`): PRD, architecture, Work Plan (steps, agents, waves, in-scope files), Requirement Traceability |
| `TEST_DIR` | `<CLAUDE_DIR>\test` | Test projects and test code written by the testers (`vb-backend-tester`, `vb-frontend-tester`); they reference the customer's projects, but nothing of them is written into the customer area |
| `DB_DIR` | `<CLAUDE_DIR>\db` | `.sql` scripts written by `db-developer` |
| `MIGRATIONS_DIR` | `<DB_DIR>\migrations` | Ordered `V<NNN>__<name>.sql` scripts (+ reverse scripts) |
| `PROCS_DIR` | `<DB_DIR>\procs` | Stored procedures (`usp_*.sql`) |
| `VIEWS_DIR` | `<DB_DIR>\views` | Views (`vw_*.sql`) |
| `QUERIES_DIR` | `<DB_DIR>\queries` | Ad-hoc and report queries |
| `SKILLS_DIR` | `<CLAUDE_DIR>\skills` | Skills (`vb-development-workflow`, `codeanalyze`, `savememo`, `config-update`, `git-commit`) |
| `HOOKS_DIR` | `<CLAUDE_DIR>\hooks` | Hook scripts (`guard_main_branch.py`, `guard_staging.py`, `validate_commit_msg.py`, and the shared parser `_gitparse.py`) |

**File patterns**

| Name | Value |
|------|-------|
| `PLAN_FILE` | `<PLANS_DIR>\plan_<feature-name>.md` |
| `ANALYSIS_FILE` | `<DOC_DIR>\analysis_<solution-name>.md` |
| `KNOWHOW_FILE` | `<DOC_DIR>\KNOWHOW.md` (shared memo of know-how, tips, issues and solved problems; written only through `/savememo`) |
| `ANALYSIS_PART_FILE` | `<DOC_DIR>\analysis_<solution-name>_<aspect>.md` (written by `/codeanalyze`; aspect = `database`, `quality`, `backend-tests`, `frontend-tests`, `requirements`, `summary`) |
| `TRACE_FILE` | `<DOC_DIR>\requirements_trace_<feature-name>.md` |
| `ENVIRONMENT_FILE` | `<RULES_DIR>\ENVIRONMENT.md` |

---

## Usage Rules

**Who must use these variables:** every agent, skill, slash command, rule, and hook script that mentions a path. Refer to the variable name (for example `<PLANS_DIR>/plan_foo.md`), never a literal drive path or a guessed location. Prose may write the separator as `/`; tools receive the resolved Windows path.

**Resolving a variable:** look up its value in this file, substitute the `<...>` parts, and use the absolute result in tool calls. Quote paths that contain spaces.

**Adding a path:** declare it here first (as a declared or derived path), then reference it by name. Do not introduce a new literal path in another file.

**Overrides**
- `GIT_REPO`: agents use the value above and do not ask for it again, unless the user names a different folder in the request (the user's request wins for that run), the orchestrator's prompt or the plan's *Git repo* line names one (that one wins for that run), or the value is empty/invalid.
- Hook scripts run by Claude Code resolve the repository through `${CLAUDE_PROJECT_DIR}`, which is the same folder as `GIT_REPO`; keep the two consistent.

**Placement — which area owns which file**

| File | Area |
|------|------|
| Application source, project files, config (`.vb`, `.vbproj`, `.xaml`, `App.config`/`Web.config`) — written by the developers | Customer area |
| The customer's documents (`CUSTOMER_DOC_DIR`) | Customer area (read-only for agents) |
| **Tests** (`TEST_DIR`), plans, analyses, trace reports, SQL scripts, agents, rules, skills, hooks, `CLAUDE.md` | Claude area (`.claude\` and `CLAUDE.md`) |

Never write Claude-area files into the customer area, and never write application files under `.claude\` — test code under `.claude\test\` is the one kind of code that belongs to the Claude area, so that test content never reaches the customer area.

**Branches and commits — one repository**
- One **feature branch per feature** (`<type>/<name>`) holds everything: code, tests, SQL scripts, plan, documents. Never work or commit directly on `main`, `master`, `production`, `prod`, or `release*` (the `guard_main_branch.py` hook blocks it). **The user creates the feature branch**: an agent that finds the repository on a protected branch (or a detached HEAD) does not commit and does not create or switch branches — it stops and asks the user to create the branch (`Skill: git-commit`).
- The orchestrator's prompt names that branch; all agents of a feature use the same branch.
- Each agent commits **its own work in its own commit(s)**, never someone else's files. Keep customer-area changes and Claude-area changes in separate commits. Commit types: `feat` / `fix` / `refactor` (program code), `test` (test code in `.claude\test\`), `analyze` (analysis), `plans` (the plan file), `review1` (changes made by the reviewer), `review2` (requirement-analysis trace report and traceability comments), `docs` / `chore` (other documents, memo entries, housekeeping).
- Commit messages follow `<type>: <description>` plus the `subagent:` line.
- **Parallel agents share one working tree and one index.** Stage and commit only your own files by explicit path: `git add <path> …`, then `git commit -m "<type>: <description>" -m "subagent: <name>" -- <path> …` (the path list limits the commit to those files even if another agent has staged others). Never `git add .` / `-A` / `-u`, `git commit -a`, or `--amend`, and never `git stash`, `git reset`, `git clean`, `git pull`, `rebase`, `merge`, or switch branches while other agents may be working. If `.git/index.lock` exists, wait a few seconds and retry (up to 5 times). The `guard_staging.py` hook blocks the sweeping forms, repo-wide path lists (`.` `*` `:/`), and the user-only commands (`push`, `pull`, `rebase`, `merge`, `stash`, `reset`, `clean`, `checkout`, `switch`, creating branches or tags, `restore` without `--staged`); `validate_commit_msg.py` requires `-m`, a valid type, a subject of at most 72 characters, and `subagent:` on its own line naming a known agent.
- Work Plan steps that run in parallel have **disjoint *In scope* file lists**; a shared file (for example a legacy `.vbproj`) is owned by one step and the others depend on it.
- The repository contains **production** code and configuration: agents never deploy, publish, push, merge, or change production settings. Production changes reach production only through the customer's own process after the user merges.

**Safety:** never commit secrets found under any of these paths.

---

## Notes

- Moving to another computer or folder: run `/config-update` — it validates the new location and rewrites the one declared row above. Because that row holds an absolute path of one machine and this file is committed, do not commit a change to it that only reflects your machine (see the `/config-update` skill).
- `CUSTOMER_DOC_DIR` (`<GIT_REPO>\doc`) is an assumed location for the customer's documents.
- Searches over `<GIT_REPO>` (`glob`, `grep`, MSBuild) cover the Claude area too; skip `.claude\` when looking for the application's files.
