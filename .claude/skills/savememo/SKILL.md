---
name: savememo
description: Shared memo of know-how, tips and tricks, issues, and solved problems for the user and every agent, kept in one file (<DOC_DIR>/KNOWHOW.md). Search it when a problem appears (so a known fix is reused instead of re-debugged), and save an entry after solving or learning something non-obvious (error text, cause, fix, evidence). Entries are added, searched, listed, shown, and marked outdated through a helper script that locks the file, refuses secrets, and catches duplicates. Use at the first sign of an error or surprise, and again once it is understood or solved; the user can also run /savememo add|search|list|show|status.
---

## When to Use

**Search first** (`search`) — at the first error, failing build/test, odd behavior, or "how did we do this before?", *before* debugging or asking the user. A known fix saves the whole investigation.

**Save** (`add`) — after any of these, as soon as it is understood:
- A problem was **solved** and the cause or fix was not obvious (`problem-solve`)
- A problem was seen but the cause or fix is **not known yet** (`issue`, status `open`) — so the next person does not start from zero
- A **trick or shortcut** that saves time (`tip`)
- A fact about how this project / stack must be done that is not written elsewhere (`knowhow`)

**Do not save:** what the code or an existing doc already says clearly, workflow status (that is the plan and git history), plans (that is `plans/`), one-off typos, anything secret.

The user can call it directly: `/savememo add …`, `/savememo search <keywords>`, `/savememo list`, `/savememo show KH-012`, `/savememo status KH-012 outdated`.

---

## Hard Rules

1. **One file:** `<KNOWHOW_FILE>` = `<DOC_DIR>/KNOWHOW.md` (Claude area). Always go through the helper script — never hand-edit entries, never create another memo file. The script locks the file (parallel agents are safe), numbers entries `KH-NNN`, and keeps the format searchable.
2. **No secrets.** No passwords, tokens, keys, or real connection strings; redact (`Password=***`). The script refuses obvious ones — redact and retry, never bypass.
3. **One entry per problem, self-contained.** Someone who reads only the entry must understand the symptom, the cause, and what to do. Put the **exact error text** in *Problem / Context* so a search on the message finds it.
4. **Evidence, not opinion.** *References* cite `file:line`, the command and its output, a link, a plan step (`S2`), or a commit.
5. **Never delete an entry.** A fix that no longer applies is marked `outdated` with a note saying what replaced it. A search result marked `outdated` is verified before use.
6. **Check for a duplicate before adding.** The script stops on a similar title; if the entry exists, update its status or add a note — add a new one only with `--force` when it is really a different problem.
7. **Diagrams are Mermaid** (fenced `mermaid` block), as everywhere in this project.
8. **Paths come from `PATH.md`** (`<SKILLS_DIR>`, `<DOC_DIR>`, `<KNOWHOW_FILE>`).
9. **This skill is not a license to skip the rules:** a recalled tip never overrides `.claude/rules/` — if they conflict, follow the rules and flag the entry to the user.

---

## Commands

All via `python -I "<SKILLS_DIR>/savememo/savememo.py" <command> …` (quote text in single quotes so the shell does not expand `$`, backticks, or `!`).

| Command | Purpose |
|---------|---------|
| `search <keywords…> [--type T] [--area A] [--status S] [--limit N] [--full N]` | Ranked matches; the top `--full` (default 3) are printed in full. Use 2–4 distinctive words: the error code / message fragment, the tool name, the area |
| `list [--type T] [--area A] [--status S]` | One line per entry |
| `show KH-012` | One entry in full |
| `add --type T --title '…' --problem '…' [--cause '…'] [--solution '…'] [--refs '…'] [--area A] [--tags a,b] [--status S] --author <name> [--force]` | Save an entry |
| `status KH-012 open\|solved\|outdated [--note '…'] --author <name>` | Change status and append a dated update line |

Types: `knowhow`, `tip`, `issue`, `problem-solve` (needs `--cause` and `--solution`; status defaults to `solved`). Areas: `db`, `backend`, `frontend`, `build`, `test`, `git`, `hooks`, `env`, `docs`, `other`. `--author` is `user` or the agent's name.

Write **title** as the symptom a person would type into a search ("sqlcmd fails with certificate error"), and **tags** as the words they might use (error codes, tool names, Thai terms if the user searches in Thai).

---

## Workflow for an Agent

1. **On a problem:** `search` with the key words of the error. Found a matching `solved` entry → apply it, verify with real output, mention `KH-NNN` in your final report. Found `outdated` → treat as a hint only. Nothing found → debug normally.
2. **Solved something non-obvious:** `add` a `problem-solve` entry (title = symptom, problem = exact error + when it happens, cause, solution = steps/commands, refs = evidence). Cannot solve it → `add` an `issue` (status `open`) with what you tried, and report it under **Issues** in your final report as usual (a question for the user follows your Work Assignment protocol).
3. **A recalled fix turned out wrong or stale:** `status KH-NNN outdated --note '…'`, then add the correct entry.
4. **Commit the memo** (`Skill: git-commit` first): `git add "<KNOWHOW_FILE>"`, then `git commit -m "docs: add KH-NNN <short title>" -m "subagent: <your agent name>" -- "<KNOWHOW_FILE>"`. If another agent's new entry is in the file, it goes into your commit too — harmless. On a protected branch (or detached HEAD) do not commit: leave the file changed and tell the user to create the branch.
5. Saving is a side task: it never changes your scope or *In scope* list; the memo is the one file every agent may edit through this script.

## Workflow for the User / Main Session

- `/savememo search …` → run `search`, show the top entries, and say whether a `solved` entry applies.
- `/savememo add …` → collect the fields from what the user said and the conversation (symptom with exact error text, cause, fix, evidence, area). Ask **one** short question only if the problem or the solution is genuinely missing; otherwise save. Use `--author user`. Confirm the saved `KH-NNN` and where.
- Commit the same way (commit subject `docs: add KH-NNN …`, `subagent: savememo` when the main session saves for the user). On a protected branch leave it uncommitted and say so.
- When the user describes a fresh problem (not asking to save), run `search` first — the answer may already be in the memo.

---

## Entry Format (written by the script)

```
## KH-012 · [problem-solve] sqlcmd fails with certificate error
| Field | Value |  → ID, Type, Status, Area, Tags, Added (date by author), Updated
**Problem / Context**   exact error text, when it happens
**Cause**               root cause
**Solution / Steps**    commands / steps that worked
**References**          file:line, output, link, plan step (S2), commit
**Update <date> (<author>):** …   (appended by `status`)
```

---

## Key Principles

1. **Search before you debug, save after you solve** — the memo only pays off if both halves happen
2. **Exact error text and evidence** make an entry findable and trustworthy
3. **Mark outdated, never delete** — history stays, stale advice stops being followed
4. **No secrets, ever**
5. **One shared file, written only through the script** — safe for parallel agents, searchable by user and agents alike
