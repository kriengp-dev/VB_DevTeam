"""Shared command parsing for the git hooks (not a hook itself).

The hooks run on every Bash / PowerShell tool call, so they must decide quickly whether the command contains a
`git <subcommand>` and with which arguments. Quoted strings (commit messages, heredocs) are blanked out first so
their text can never be mistaken for options or sub-commands.
"""
import re
import shlex

DQ = re.compile(r'"(?:[^"\\]|\\.)*"', re.S)
SQ = re.compile(r"'[^']*'", re.S)
SEGMENT_SPLIT = re.compile(r"&&|\|\||;|\||\n")
GLOBAL_ARG_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def sanitize(command: str) -> str:
    """Blank out quoted strings so their content cannot confuse the parser."""
    return SQ.sub("'Q'", DQ.sub('"Q"', command))


def _unquote(tok: str) -> str:
    return tok.strip().strip("\"'")


def git_calls(command: str):
    """Yield (subcommand, args) for every segment of the command that is `git [global options] <sub> <args…>`."""
    for seg in SEGMENT_SPLIT.split(sanitize(command)):
        seg = seg.strip()
        if seg.startswith("&"):          # PowerShell call operator
            seg = seg[1:].strip()
        try:
            toks = shlex.split(seg, posix=False)
        except ValueError:
            toks = seg.split()
        toks = [_unquote(t) for t in toks]
        if not toks or toks[0].lower() not in ("git", "git.exe"):
            continue
        i, sub = 1, None
        while i < len(toks):
            t = toks[i]
            if t in GLOBAL_ARG_OPTS:
                i += 2
                continue
            if t.startswith("-"):
                i += 1
                continue
            sub = t
            break
        if sub:
            yield sub, toks[i + 1:]


def has_git_call(command: str, subcommand: str) -> bool:
    return any(s == subcommand for s, _ in git_calls(command))
