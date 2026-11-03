"""PreToolUse hook: block `git commit` while the target repo is on a protected branch or a detached HEAD.

Acts ONLY on commands that contain a `git commit` (any other Bash/PowerShell command passes untouched), so it can be
registered on every Bash/PowerShell call.

Works for the single repository (and still for a nested repo): the repo is taken from the command itself
(`git -C <path> commit ...`, or `cd <path> && git commit ...`, or PowerShell `Set-Location <path>`),
falling back to the session's working directory.

Exit 0 = allow, exit 2 = block (stderr is shown to Claude).
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gitparse import has_git_call  # noqa: E402

PROTECTED = {"main", "master", "production", "prod", "release"}
PROTECTED_PREFIXES = ("release/", "release-")

ARG = r'("[^"]+"|\'[^\']+\'|[^\s;&|]+)'
GIT_C = re.compile(r"git\s+(?:-c\s+\S+\s+)*-C\s+" + ARG, re.IGNORECASE)
CD = re.compile(r"(?:^|[;&|\n]\s*)(?:cd|chdir|set-location|sl|pushd)\s+(?:/d\s+)?(?:-path\s+)?" + ARG, re.IGNORECASE)


def unquote(s: str) -> str:
    return s[1:-1] if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'" else s


def target_dir(command: str, cwd: str) -> str:
    """Directory the commit will run in."""
    before = command
    m_commit = re.search(r"git\b[^\n;&|]*\bcommit\b", command, re.IGNORECASE)
    if m_commit:
        before = command[: m_commit.end()]
    directory = cwd or os.getcwd()

    cds = list(CD.finditer(before))
    if cds:
        d = unquote(cds[-1].group(1))
        directory = d if os.path.isabs(d) else os.path.join(directory, d)

    gc = list(GIT_C.finditer(before))
    if gc:
        d = unquote(gc[-1].group(1))
        directory = d if os.path.isabs(d) else os.path.join(directory, d)
    return directory


def is_protected(branch: str) -> bool:
    b = branch.lower()
    return b in PROTECTED or b.startswith(PROTECTED_PREFIXES)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    command = (payload.get("tool_input") or {}).get("command", "")
    if not has_git_call(command, "commit"):
        return 0  # not a commit: nothing to guard
    directory = target_dir(command, payload.get("cwd") or "")
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=directory, capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, NotADirectoryError, OSError):
        return 0  # not a git repo / git missing / bad path: do not block

    if not branch:
        # empty output = detached HEAD (a failed rev-parse means "not a repository": do not block)
        try:
            head = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=directory,
                                  capture_output=True, text=True, check=True).stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError, NotADirectoryError, OSError):
            return 0
        if head == "HEAD":
            sys.stderr.write(
                f"Blocked: HEAD is detached in {directory}; commits there are easily lost. "
                "Do not commit and do not create or switch branches yourself: stop and ask the USER to check out a feature branch, "
                "then continue after they confirm.\n"
            )
            return 2
        return 0

    if is_protected(branch):
        sys.stderr.write(
            f"Blocked: committing directly to '{branch}' in {directory} is not allowed. "
            "Do not commit here and do not create or switch branches yourself: stop and ask the USER to create a feature branch "
            "(git checkout -b <type>/<name>), then continue after they confirm.\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
