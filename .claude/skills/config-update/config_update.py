"""Update the machine-specific path declared in PATH.md (use after moving to another computer or folder).

There is ONE git repository holding the Claude area (.claude\\ and CLAUDE.md) and the customer area (the rest of
the repository root). The only machine-specific value is GIT_REPO, the root of that repository; every other
path is derived from it.

Usage:
  python -I config_update.py                         # dry run: show current value, detect this machine's repo root
  python -I config_update.py --git-repo "D:\\work\\App"          # dry run for another folder
  python -I config_update.py --apply                 # write the detected (or given) GIT_REPO to PATH.md
  python -I config_update.py --path-file <file>      # operate on another copy of PATH.md (testing)

Only the GIT_REPO row of the "Declared Paths" table is ever written.
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
DEFAULT_GIT_REPO = HERE.parents[3]          # <repo>/.claude/skills/config-update/<this file>
DEFAULT_PATH_FILE = DEFAULT_GIT_REPO / ".claude" / "rules" / "PATH.md"
ROW = re.compile(r"^(\|\s*`GIT_REPO`\s*\|\s*`)([^`]*)(`\s*\|.*)$")
LEGACY_ROW = re.compile(r"^\|\s*`(TARGET_REPO|CLAUDE_REPO)`\s*\|\s*`([^`]*)`")
TEXT_EXT = {".md", ".py", ".json", ".txt", ".sql", ".cfg", ".ini", ".yml", ".yaml"}
SKIP_DIRS = {".git", ".claude", ".vs", "bin", "obj", "packages", "node_modules", "$RECYCLE.BIN", "System Volume Information"}
PROTECTED = {"main", "master", "production", "prod", "release"}


def run(cmd, cwd=None):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)
        return r.returncode, r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def norm(p):
    return os.path.normcase(os.path.normpath(str(p))).replace("\\", "/").rstrip("/")


def is_drive_root(p):
    p = Path(p)
    return p.parent == p or str(p) == p.anchor


def find_files(root, suffix, max_depth=5, limit=5):
    """Bounded search: stops after `limit` hits, never deeper than `max_depth`, skips .claude and build folders."""
    found = []
    root = str(root)
    base_depth = root.rstrip("\\/").count(os.sep)
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        if dirpath.rstrip("\\/").count(os.sep) - base_depth >= max_depth:
            dirnames[:] = []
        for f in filenames:
            if f.lower().endswith(suffix):
                found.append(os.path.join(dirpath, f))
                if len(found) >= limit:
                    return found
    return found


def check_git_repo(path):
    """Return (problems, info_lines) for a candidate GIT_REPO."""
    problems, info = [], []
    p = Path(path)
    if not p.exists() or not p.is_dir():
        return [f"GIT_REPO does not exist or is not a folder: {path}"], info
    if is_drive_root(p):
        return ["GIT_REPO is a drive root — set the repository folder instead (not scanned)"], info
    if not (p / ".claude" / "rules" / "PATH.md").exists():
        problems.append(f"GIT_REPO does not contain .claude\\rules\\PATH.md — this is not the Claude project's repository: {path}")
        return problems, info

    info.append("Claude area: .claude\\ found")
    code, top = run(["git", "-C", str(p), "rev-parse", "--show-toplevel"])
    if code != 0:
        info.append("note: not a git repository yet — run `git init` here; the single repository holds the program, SQL, and plans")
    else:
        if norm(top) != norm(p):
            problems.append(f"GIT_REPO must be the git root of the repository (the git root is {top})")
        _, branch = run(["git", "-C", str(p), "branch", "--show-current"])
        info.append(f"git branch: {branch or '(detached)'}")
        if branch.lower() in PROTECTED or branch.lower().startswith(("release/", "release-")):
            info.append("note: on a protected branch — the user must create a feature branch before agents can commit")
        _, remote = run(["git", "-C", str(p), "remote", "-v"])
        info.append("remote: " + (remote.splitlines()[0] if remote else "(none)"))

    slns = find_files(p, ".sln")
    vbs = find_files(p, ".vbproj")
    info.append(f"customer area: .sln found: {len(slns)}{'+' if len(slns) == 5 else ''}, .vbproj found: {len(vbs)}{'+' if len(vbs) == 5 else ''}")
    if not slns and not vbs:
        info.append("note: no .sln or .vbproj yet — add the customer's program to the repository")
    if (p / "doc").is_dir():
        info.append("customer documents: doc\\ found (CUSTOMER_DOC_DIR default)")
    else:
        info.append("customer documents: doc\\ NOT found — if they live elsewhere, edit CUSTOMER_DOC_DIR in PATH.md")
    return problems, info


def tools():
    out = []
    for name in ("git", "python", "nuget", "sqlcmd"):
        w = shutil.which(name) or (sys.executable if name == "python" else None)
        out.append((name, w or "NOT FOUND"))
    vswhere = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
    if vswhere.exists():
        _, msb = run([str(vswhere), "-latest", "-requires", "Microsoft.Component.MSBuild", "-find", r"MSBuild\**\Bin\MSBuild.exe"])
        _, vst = run([str(vswhere), "-latest", "-find", r"Common7\IDE\CommonExtensions\Microsoft\TestWindow\vstest.console.exe"])
        out.append(("MSBuild (Visual Studio)", msb.splitlines()[0] if msb else "NOT FOUND"))
        out.append(("vstest.console.exe", vst.splitlines()[0] if vst else "NOT FOUND"))
    else:
        out.append(("vswhere / Visual Studio", "NOT FOUND (install Visual Studio 2026 or locate MSBuild manually)"))
    out.append(("VB_TEST_DB env var", "set" if os.environ.get("VB_TEST_DB") else "NOT SET (integration tests need the test-database connection string)"))
    return out


def find_old_refs(repo, old_values, skip):
    hits = []
    skip_n = {norm(s) for s in skip}
    roots = [Path(repo) / "CLAUDE.md", Path(repo) / ".claude"]
    files = []
    for r in roots:
        if r.is_file():
            files.append(r)
        elif r.is_dir():
            for f in r.rglob("*"):
                if f.is_file() and f.suffix.lower() in TEXT_EXT and ".git" not in f.parts and "logs" not in f.parts:
                    files.append(f)
    needles = [(o, norm(o)) for o in old_values if o and not is_drive_root(o)]
    for f in files:
        if norm(f) in skip_n:
            continue
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            ln = line.replace("\\", "/").lower()
            for orig, n in needles:
                if n and n in ln:
                    hits.append((f, i, orig))
                    break
    return hits


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--git-repo", help="new GIT_REPO, the root of the single git repository (default: detected from this script's location)")
    ap.add_argument("--apply", action="store_true", help="write the new value to PATH.md (default: dry run)")
    ap.add_argument("--path-file", help="PATH.md to read/write (default: this project's)")
    a = ap.parse_args()

    path_file = Path(a.path_file) if a.path_file else DEFAULT_PATH_FILE
    if not path_file.exists():
        print(f"PATH.md not found: {path_file}")
        return 2
    lines = path_file.read_text(encoding="utf-8").splitlines(keepends=True)
    cur = None
    for line in lines:
        m = ROW.match(line.rstrip("\r\n"))
        if m:
            cur = m.group(2)
            break
    if cur is None:
        legacy = [LEGACY_ROW.match(l) for l in lines]
        if any(legacy):
            print("PATH.md still uses the old two-row format (TARGET_REPO / CLAUDE_REPO). Replace it with a single `GIT_REPO` row in the Declared Paths table, then run this again.")
        else:
            print(f"Could not find the `GIT_REPO` row in the Declared Paths table of {path_file}")
        return 2

    detected = str(DEFAULT_GIT_REPO)
    new = a.git_repo or detected

    print("# Config update — machine path\n")
    print(f"PATH.md: {path_file}\n")
    print("| Variable | Current (PATH.md) | New | Change |")
    print("|----------|-------------------|-----|--------|")
    print(f"| GIT_REPO | `{cur}` | `{new}` | {'same' if norm(cur) == norm(new) else 'CHANGE'} |")
    print(f"\nDetected repository root on this machine (from the script location): `{detected}`\n")

    problems, info = check_git_repo(new)
    print("## Repository checks (Claude area + customer area)")
    for i in info:
        print(f"- {i}")
    for x in problems:
        print(f"- PROBLEM: {x}")
    if not problems:
        print("- OK")

    print("\n## Tools on this machine")
    for name, where in tools():
        print(f"- {name}: {where}")

    print("\n## Old path still written elsewhere")
    old_vals = [cur] if norm(cur) != norm(new) else []
    if not old_vals:
        print("- (the path is not changing)")
    else:
        hits = find_old_refs(new if Path(new).exists() else detected, old_vals, [path_file])
        if not hits:
            print("- none — everything else is derived from PATH.md, `${CLAUDE_PROJECT_DIR}`, or the script location")
        else:
            for f, i, o in hits[:30]:
                print(f"- {f}:{i} still contains `{o}` — replace it with the variable name")
            if len(hits) > 30:
                print(f"- … and {len(hits) - 30} more")

    if problems:
        print("\nResult: PROBLEMS found — fix them (or choose another folder) before applying.")
        if a.apply:
            print("Not applied.")
        return 1

    if not a.apply:
        print("\nResult: dry run OK — nothing written. Re-run with --apply to update PATH.md.")
        return 0

    out, done = [], False
    for line in lines:
        m = ROW.match(line.rstrip("\r\n"))
        if m and not done:
            eol = line[len(line.rstrip("\r\n")):]
            line = m.group(1) + new + m.group(3) + eol
            done = True
        out.append(line)
    path_file.write_text("".join(out), encoding="utf-8", newline="")
    print(f"\nApplied: updated GIT_REPO in {path_file}")
    print("Reminder: this row holds an absolute path of THIS machine. Do not commit a change to it that only reflects your machine (it would break other computers); commit PATH.md only when the layout itself changes.")
    print("Next: restart Claude Code if the folder changed (`${CLAUDE_PROJECT_DIR}` follows the folder you open), then run `/vb-development-workflow` or `/codeanalyze`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
