"""PreToolUse hook: keep agents from sweeping, rewriting, or switching things in the shared working tree.

All agents of a feature share ONE working tree, ONE index, and ONE branch. This hook blocks:

  git add . | -A | --all | -u | --update | * | :/        (or `git add` with no path)    -> stage explicit files
  git commit -a | --all | -am ...                                                       -> never auto-stage
  git commit --amend                                                                    -> never rewrite history
  git commit without an explicit path list after `--`, or with a repo-wide one (. * :/) -> commit only your own files
  git push | pull | rebase | merge | stash | reset | clean | checkout | switch          -> user-only operations
  git restore (without --staged) | git branch <name> / -d / -m | git tag <name>         -> user-only operations

Correct pattern:   git add <my files>   then   git commit -m "<type>: <description>" -m "subagent: <name>" -- <my files>

The user creates the feature branch and does push / merge / pull etc. outside Claude. Reading commands
(status, log, diff, show, branch --show-current, branch --list, fetch, restore --staged) stay allowed.

Exit 0 = allow, exit 2 = block (stderr is shown to Claude). Commands that cannot be parsed are allowed through.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gitparse import git_calls  # noqa: E402

BROAD_PATHSPECS = {".", "./", ".\\", "*", "**", ":/", ":/*", ":/.", ":(top)", "..", "../", "..\\", "-A", "--all", "-u", "--update"}
ADD_BROAD_FLAGS = {"-A", "--all", "-u", "--update", "--no-ignore-removal"}
COMMIT_ARG_FLAGS = {"-m", "-F", "-C", "-c", "-t", "--message", "--file", "--reuse-message", "--reedit-message",
                    "--template", "--author", "--date", "--cleanup", "--trailer", "--fixup", "--squash"}
SHORT_ARG_LETTERS = set("mFCct")

USER_ONLY = {
    "push": "agents never push",
    "pull": "agents never pull",
    "rebase": "agents never rewrite history",
    "merge": "agents never merge",
    "stash": "stashing would hide other agents' work in the shared working tree",
    "reset": "resetting would discard or unstage other agents' work",
    "clean": "cleaning would delete other agents' untracked files",
    "checkout": "agents never switch branches or discard files — the user creates the feature branch",
    "switch": "agents never switch or create branches — the user creates the feature branch",
}
BRANCH_READ_FLAGS = {"--show-current", "-l", "--list", "-a", "--all", "-r", "--remotes", "-v", "-vv", "--verbose",
                     "--contains", "--no-contains", "--merged", "--no-merged", "--points-at", "--format"}
BRANCH_WRITE_FLAGS = {"-d", "-D", "--delete", "-m", "-M", "--move", "-c", "-C", "--copy", "-f", "--force",
                      "-u", "--set-upstream-to", "--unset-upstream"}


def is_broad(path: str) -> bool:
    return path in BROAD_PATHSPECS or path.endswith("/.") or path.endswith("\\.")


def check_add(args):
    flags = [a for a in args if a.startswith("-") and a != "--"]
    paths = args[args.index("--") + 1:] if "--" in args else [a for a in args if not a.startswith("-")]
    if any(f in ADD_BROAD_FLAGS for f in flags):
        return "git add with -A/--all/-u/--update stages every changed file, including other agents' files"
    if not paths and not any(f.startswith("--pathspec-from-file") for f in flags):
        return "git add without an explicit path"
    for p in paths:
        if is_broad(p):
            return f"git add {p} stages every changed file under that path, including other agents' files"
    return None


def check_commit(args):
    i, short_flags, long_flags, paths = 0, set(), set(), []
    while i < len(args):
        t = args[i]
        if t == "--":
            paths = [a for a in args[i + 1:] if a]
            break
        if t.startswith("--"):
            name = t.split("=", 1)[0]
            long_flags.add(name)
            if name in COMMIT_ARG_FLAGS and "=" not in t:
                i += 1
        elif t.startswith("-") and len(t) > 1:
            letters = t[1:]
            short_flags.update(letters)
            if letters[-1] in SHORT_ARG_LETTERS:
                i += 1  # an option that takes a value, also as the end of a cluster such as -am "msg"
        i += 1
    if "a" in short_flags or "--all" in long_flags:
        return "git commit -a/--all stages every modified file, including other agents' files"
    if "--amend" in long_flags:
        return "git commit --amend rewrites a commit that another agent may have built on; make a new commit instead"
    if "--allow-empty" in long_flags and not paths:
        return None
    if not paths:
        return "git commit without an explicit path list also takes files another agent has staged"
    for p in paths:
        if is_broad(p):
            return f"git commit -- {p} commits every changed file, including other agents' files"
    return None


def check_branch(args):
    flags = {a for a in args if a.startswith("-")}
    positional = [a for a in args if not a.startswith("-")]
    if flags & BRANCH_WRITE_FLAGS:
        return "git branch with -d/-m/-c/-f/-u changes branches — the user manages branches"
    if positional and not (flags & BRANCH_READ_FLAGS):
        return "git branch <name> creates a branch — the user creates the feature branch"
    return None


def check_tag(args):
    flags = {a for a in args if a.startswith("-")}
    positional = [a for a in args if not a.startswith("-")]
    if flags & {"-d", "--delete", "-f", "--force"}:
        return "git tag -d/-f changes tags — the user manages tags"
    if positional and not (flags & {"-l", "--list", "--contains", "--merged", "--points-at"}):
        return "git tag <name> creates a tag — agents never tag"
    return None


def check_restore(args):
    if not ({"--staged", "-S"} & set(args)):
        return "git restore without --staged discards changes in the shared working tree"
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    command = (payload.get("tool_input") or {}).get("command", "")
    if "git" not in command.lower():
        return 0

    problem = None
    for sub, args in git_calls(command):
        if sub == "add":
            problem = check_add(args)
        elif sub == "commit":
            problem = check_commit(args)
        elif sub in USER_ONLY:
            problem = f"git {sub}: {USER_ONLY[sub]}"
        elif sub == "branch":
            problem = check_branch(args)
        elif sub == "tag":
            problem = check_tag(args)
        elif sub == "restore":
            problem = check_restore(args)
        if problem:
            break
    if problem:
        sys.stderr.write(
            f"Blocked: {problem}.\n"
            "All agents of a feature share one working tree and one branch. Stage only your own files by explicit path "
            "(`git add <path> ...`) and commit with the same list: "
            "`git commit -m \"<type>: <description>\" -m \"subagent: <name>\" -- <path> ...`. "
            "Branch creation/switching, push, pull, merge, rebase, stash, reset, and clean are done by the user outside Claude. "
            "If `.git/index.lock` exists, wait a few seconds and retry (up to 5 times).\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
