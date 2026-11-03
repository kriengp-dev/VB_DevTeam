---
name: config-update
description: Updates the one machine-specific path declared in .claude/rules/PATH.md (GIT_REPO = the root of the single git repository that holds the Claude area (.claude\) and the customer area (the rest of the repository)) after moving to another computer or folder, validates the new location, checks that the needed tools exist on the machine, and reports any old path still written elsewhere. Dry run by default; writes only the GIT_REPO row after the user confirms. After a successful apply it also runs /codeanalyze on the repository so the new machine starts with fresh analysis reports (skip with --no-analyze). Use when setting up on a new PC, when the repository folder moved, or when GIT_REPO is wrong.
---

## When to Use

- You moved or cloned this repository to another computer, drive, or folder
- `GIT_REPO` no longer exists, still holds a placeholder (for example `C:\`), or points to the wrong folder
- `/vb-development-workflow`, `/codeanalyze`, or an agent stopped with "GIT_REPO is empty / a drive root / missing"
- First-time setup on a machine (the skill finishes by analyzing the program with `/codeanalyze`)

**Arguments:** `--git-repo "<folder>"` (explicit folder), `--no-analyze` (skip the final analysis step).

**Not for:** changing how paths are derived (edit `PATH.md` by hand), or editing other settings (stack, SQL instance, models).

---

## Hard Rules

1. **Only one value is ever written**: the `GIT_REPO` row of the *Declared Paths* table in `.claude/rules/PATH.md`. Every other path is derived from it, from `${CLAUDE_PROJECT_DIR}` (hooks), or from a script's own location — none of it needs editing.
2. **Dry run first.** Show the user the result, get explicit confirmation of the path, and only then run with `--apply`.
3. **Never accept a bad path.** The script refuses a missing folder, a drive root, a folder without `.claude\rules\PATH.md`, and a folder that is not the git root. Do not work around a refusal; ask the user for the right folder.
4. **Do not scan drives or guess.** The script detects the repository from its own location; if that is wrong, ask the user — never search the machine for it.
5. **No other file is edited** by this skill (the analysis step in Step 6 is delegated to `/codeanalyze`, whose agents write only their own report files in `<DOC_DIR>`). If the report lists an old path written somewhere else, tell the user which file and line; fix it only if they ask (the fix is to replace it with the variable name).
6. **Read-only toward git.** The skill itself reads the branch and remote; it does not change, fetch, commit, or push anything. It writes only the one `PATH.md` row after confirmation. Commits made during the analysis step are the analysis agents' own (`analyze:` reports, explicit paths) and never include `PATH.md`.
7. **Analysis runs only after a clean, applied, verified change** — never on a dry run, never when the checks reported PROBLEMS, never with `--no-analyze`, and never against a repository without a program (say so instead).

---

## Steps

1. **Show the current state** (dry run, no arguments):

   ```bash
   python -I "<SKILLS_DIR>/config-update/config_update.py"
   ```

   `<SKILLS_DIR>` is declared in `.claude/rules/PATH.md`; the script detects the repository root from its own location, so it is correct on any machine. Use absolute, quoted paths.

2. **Compare:** if the table shows `same`, nothing needs changing — go to step 5. If it shows `CHANGE`, the detected root on this machine differs from the value in `PATH.md` (the normal case after moving). Confirm with the user that the detected folder is the repository they opened. If they want a different folder, use `--git-repo "<folder>"`.

3. **Dry run with an explicit path** (only if needed):

   ```bash
   python -I "<SKILLS_DIR>/config-update/config_update.py" --git-repo "<folder>"
   ```

   Read the whole report. It covers:
   - **Change table:** the current value in `PATH.md` vs the new one
   - **Repository checks:** `.claude\` found (Claude area); git root; current branch (protected-branch note); remote; customer area — `.sln`/`.vbproj` found (only a note when the program is not added yet), `doc\` present (default `CUSTOMER_DOC_DIR`)
   - **Tools:** git, python, nuget, sqlcmd, MSBuild and `vstest.console.exe` (via Visual Studio's vswhere), and whether the `VB_TEST_DB` environment variable is set
   - **Old path still written elsewhere:** any file that still contains the previous `GIT_REPO` value

   If it reports **PROBLEMS**, explain them and go back to step 2. Do not apply.

4. **Confirm and apply** — show the change table and ask the user to confirm; then:

   ```bash
   python -I "<SKILLS_DIR>/config-update/config_update.py" [--git-repo "<folder>"] --apply
   ```

5. **Verify:** re-run the dry run without arguments; `GIT_REPO` must show `same`, with no problems. Then list `<PLANS_DIR>` to confirm the plans are still found.

6. **Analyze** (after Step 5 verified `same` with no problems, unless `--no-analyze`):
   - Check the repository has a program: `.sln` / `.vbproj` outside `.claude\`, `bin\`, `obj\`, `packages\` (the repository checks in the report already list them). None → skip and say "no program yet — run `/codeanalyze` after it is added".
   - Check the branch from the report. On a protected branch (`main` / `master` / `production` / `prod` / `release*`) or a detached HEAD, do not start: tell the user to create a branch (for example `docs/code-analysis`) and run `/codeanalyze` afterwards. The `PATH.md` change is already applied and stays.
   - Otherwise invoke `Skill: codeanalyze` (pass the solution name if the user gave one). It follows its own rules: analysis-only agents, one report per aspect in `<DOC_DIR>`, `analyze:` commits by the agents, and it asks the user whether to refresh or keep reports that already exist (typical after moving a repository that already carries reports).
   - Do not stage or commit `PATH.md` as part of this; the agents commit only their own report files by explicit path.

7. **Report to the user:**
   - What changed (old → new), and the verification result
   - The analysis result from Step 6 (scorecard and top risks from `/codeanalyze`), or why it was skipped
   - Tools that are **NOT FOUND** or env vars **NOT SET**, and what each affects:
     - MSBuild / vstest missing → install Visual Studio 2026 with the required workloads (build and test cannot run)
     - `nuget` missing → restore packages from Visual Studio, or install the CLI
     - `sqlcmd` missing → `db-developer` cannot run scripts from the command line (SSMS still works)
     - `VB_TEST_DB` not set → integration tests will be `Inconclusive`
     - `python` missing → the commit-guard hooks fail; commits will be blocked until it is installed
   - Things to check by hand on a new machine (the skill cannot): the SQL Server instance name (default assumed `.\SQLEXPRESS`), `git config user.name/user.email`, git credentials for the remote, the customer's documents folder (`CUSTOMER_DOC_DIR`), and that the Claude Code project is opened from the repository folder (restart Claude Code if the folder changed, so `${CLAUDE_PROJECT_DIR}` and the hooks follow it)
   - Existing plans (`<PLANS_DIR>`) whose *Git repo* line holds a literal old path (listed in the "old path" section)
   - **Do not commit the machine-specific change:** the `GIT_REPO` row holds an absolute path of this computer and `PATH.md` is tracked in the shared repository. Leave the change uncommitted (or use `git update-index --skip-worktree` locally); commit `PATH.md` only when the layout itself changes

---

## What Stays Valid Without Editing

- All `<VARIABLE>` references in agents, rules, skills, templates (resolved from `PATH.md`)
- Hooks in `settings.local.json` (`${CLAUDE_PROJECT_DIR}`) and the hook scripts (they find the repo from the command and their own location)
- `config-update` and `savememo` scripts (take their location from the file path)

---

## Key Principles

1. **One source of truth** — the path lives in `PATH.md`; this skill changes that file and nothing else
2. **Validate before write** — a wrong path breaks every agent, so refuse and ask rather than guess
3. **Confirm before apply** — the user sees old → new and agrees
4. **Analyze once the machine is ready** — a new setup ends with fresh reports, but never before the path is verified
5. **Report, don't fix silently** — leftover old paths and missing tools are listed for the user
