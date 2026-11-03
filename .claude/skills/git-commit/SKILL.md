---
name: git-commit
description: Rules every agent follows when committing in this repository — never commit on main/master/production/prod/release*; the USER creates the feature branch (agents stop and ask, they never create or switch branches); commit message format with the subagent line; explicit-path staging and commits so parallel agents do not collide; separate commits by area and type; no push/merge unless asked. Invoke before any git commit or when opening a pull request.
---

## When to Use

- Before **every** `git add` / `git commit` (agents invoke this from their commit step)
- When an agent has finished its work and must commit it (work is not done until it is committed)
- When unsure which branch is allowed, how to word the message, or which files a commit may contain
- When the user asks for a pull request

---

## Step 0 — Find the Repository (mandatory first step)

There is **one** git repository (`GIT_REPO` in `PATH.md`): the Claude area (`.claude\`) and the customer area share it.

```bash
git -C "<GIT_REPO or the folder of the changed files>" rev-parse --show-toplevel
```

- Use the printed path for every later git command (not the shell's working directory by guess).
- If the command fails → **STOP** and tell the user which folder is not a git repository. Never guess another repository.
- **Never run `git init`** unless the user explicitly asks for it in the current message.

---

## Step 1 — Branch Check (mandatory, before staging anything)

```bash
git -C "<repo>" branch --show-current
```

**Protected branches:** `main`, `master`, `production`, `prod`, anything starting `release/` or `release-`, and a detached HEAD (empty result).

### If the current branch is protected → STOP. The user creates the branch.

You must **not** commit, **not** create a branch (`git checkout -b`, `git switch -c`, `git branch`), and **not** switch branches. Instead:

1. Leave your work as it is, uncommitted. **Do not report your step as `done`**: report `Status: blocked` with the pending commit — or, if you were only asked to commit, report that nothing was committed.
2. Tell the user, in one short message:

   ```
   I'm on `<branch>` (protected), so I did not commit.
   Please create a feature branch, then tell me to continue:
       git checkout -b <type>/<short-description>
   Suggested: <type>/<feature-name>   (e.g. feat/foo-create-endpoint)
   Uncommitted work: <list of your files>
   ```

3. Stop. When the user says the branch exists, re-run Step 1 and continue.

The `guard_main_branch.py` hook blocks the commit anyway; do not try to work around it (no `--no-verify`, no editing hooks, no committing from another clone).

### If the current branch is NOT protected

Commit on it. All agents of the feature use this one branch (the orchestrator's prompt names it). Branch prefix suggestions for the user: `feat/`, `fix/`, `refactor/`, `docs/`, `test/`, `chore/`, `perf/`, or `<type>/<feature-name>`.

---

## Step 2 — Stage and Commit Only Your Own Files

All agents of a feature share one working tree and one index, so stage **only your own files, by explicit path**, and commit with the same list:

```bash
git -C "<repo>" add <path-1> <path-2> …
git -C "<repo>" commit -m "<type>: <description>" -m "subagent: <agent>" -- <path-1> <path-2> …
```

- Your files = the files of your step's *In scope* list (from the plan's Work Plan or the orchestrator's prompt) — nothing else.
- **Never** `git add .` / `-A` / `--all` / `-u`, `git commit -a` / `--all`, or `--amend`; never `git stash`, `reset`, `clean`, `pull`, `rebase`, `merge`, or branch switching while other agents may be running. (`guard_staging.py` blocks the sweeping forms and repo-wide path lists such as `-- .` / `-- *` / `-- :/`.)
- Always list the paths after `--`: that limits the commit to those files even if another agent has staged others.
- If `.git/index.lock` exists, wait a few seconds and retry (up to 5 times); do not delete the lock.
- Before committing, run `git -C "<repo>" diff --cached --stat` after your `git add` and confirm only your files are staged. Never commit secrets, passwords, real connection strings, logs, or exports.

---

## Commit Message Format

```
<type>: <description>
subagent: <agent>

<optional body>
```

`subagent:` goes on its **own line** after the subject (with `-m "<subject>" -m "subagent: <agent>"` it is its own paragraph — that is accepted). The subject is `<type>: <description>` with a space after the colon, at most 72 characters (the hook rejects longer), imperative mood. The message **must** be given with `-m` (no editor, no `-F` file), `subagent:` must never be inside the subject, and its value must be a known agent or skill.

### Types (the `validate_commit_msg.py` hook rejects any other)

| Type | Use for | Typical author |
|------|---------|----------------|
| `feat` | New behavior in the program | `vb-backend-developer`, `vb-frontend-developer`, `db-developer` |
| `fix` | Bug fix | developers, `db-developer` |
| `perf` | Performance change | developers, `db-developer` |
| `refactor` | Restructuring without behavior change | developers |
| `test` | Test code under `.claude\test\` (Claude area) | `vb-backend-tester`, `vb-frontend-tester` |
| `docs` | Other documentation, memo entries (`KNOWHOW.md`) | any |
| `chore` | Tooling, config, housekeeping | any |
| `analyze` | Codebase analysis report | `vb-analyzer` |
| `plans` | The plan file (`plans/plan_<feature>.md`) and approved plan changes | `vb-planner` |
| `review1` | Changes made by the reviewer | `vb-reviewer` |
| `review2` | Requirement-analysis report and traceability comments | `vb-requirement-analysis` |

### `subagent:` values

`vb-analyzer`, `vb-planner`, `vb-backend-developer`, `vb-frontend-developer`, `db-developer`, `vb-backend-tester`, `vb-frontend-tester`, `vb-reviewer`, `vb-requirement-analysis`, `vb-researcher`, and for the memo skill run by the main session: `savememo`. A commit made by a person has no `subagent:` line.

### Examples

```bash
git -C "<repo>" commit -m "feat: add foo creation endpoint" -m "subagent: vb-backend-developer" -- src/FooController.vb
git -C "<repo>" commit -m "test: cover foo creation validation" -m "subagent: vb-backend-tester" -- .claude/test/Backend/FooTests.vb
git -C "<repo>" commit -m "plans: add implementation plan for foo" -m "subagent: vb-planner" -- .claude/plans/plan_foo.md
git -C "<repo>" commit -m "docs: add KH-001 sqlcmd certificate error" -m "subagent: db-developer" -- .claude/doc/KNOWHOW.md
```

---

## Separate Commits by Area and Type

- **Customer area** (program, project files) and **Claude area** (`.claude\`: tests, plans, SQL, analyses, trace reports) go in **separate commits**.
- Within an area, keep code, tests, and documents in separate commits; an agent commits only its own files.
- Order inside a feature, for example: `plans:` (plan, with its research and analysis) → `feat:` / `feat:` (developers) → `test:` (testers) → `review1:` / `review2:` (reviewers). A fix to reviewed code is its own `fix:` commit by the owning agent.

---

## Commands That Belong to the User

The `guard_staging.py` hook blocks these for agents: `git push`, `pull`, `rebase`, `merge`, `stash`, `reset`, `clean`, `checkout`, `switch`, `cherry-pick`-style history changes via `--amend`, creating or deleting branches (`git branch <name>`, `-d`, `-m`) or tags, and `git restore` without `--staged`. The user creates the feature branch, pushes, merges, and cleans up outside Claude. Reading commands stay allowed: `status`, `log`, `diff`, `show`, `branch --show-current`, `branch --list`, `fetch`, `restore --staged <path>`.

---

## Push, Merge, Pull Request

Agents **never push, merge, rebase, tag, or open a pull request** unless the user asks in the current message. When asked for a PR:

1. Review the whole branch, not just the last commit: `git diff <base>...HEAD`
2. Draft a title (≤ 70 characters) and a body with a summary, the steps completed, build/test results from real runs, and the manual checks still open
3. Push only when the user asked: `git push -u origin <branch>`
4. Open the PR targeting `main`; never merge it yourself

---

## Commit Checklist

- [ ] Step 0: the repository root was resolved (no `git init`)
- [ ] Step 1: the current branch is **not** protected — otherwise you stopped and asked the user to create the branch
- [ ] Only your own files are staged, by explicit path; `git diff --cached --stat` shows nothing else
- [ ] The commit lists the same paths after `--`
- [ ] Subject is `<type>: <description>` with a valid type; `subagent:` is on its own line
- [ ] Customer-area and Claude-area changes are in separate commits
- [ ] No secrets, connection strings, logs, or exports are staged
- [ ] Build and tests that your step requires passed before committing implementation code
