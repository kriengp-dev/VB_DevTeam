#!/usr/bin/env python3
"""savememo - keep and recall know-how, tips, issues and solutions in <DOC_DIR>/KNOWHOW.md.

Commands (see SKILL.md):
  add     save a new entry (refuses secrets and likely duplicates)
  search  find entries by keywords (title, tags, area, problem, cause, solution, references)
  list    one line per entry, optionally filtered
  show    print one entry in full
  status  change the status of an entry (open / solved / outdated) and append an update note

The file is found from this script's own location (.claude/skills/savememo -> .claude/doc/KNOWHOW.md),
so it is correct on any machine. Writes take a lock file, so parallel agents do not corrupt it.
It never commits; the SKILL.md says how to commit (explicit path, git-commit skill).
"""
import argparse
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

TYPES = ("knowhow", "tip", "issue", "problem-solve")
STATUSES = ("open", "solved", "outdated")
DEFAULT_FILE = Path(__file__).resolve().parents[2] / "doc" / "KNOWHOW.md"

HEADER = """# KNOWHOW — know-how, tips, issues and solutions

Shared memo of the user and all agents (`/savememo`). **Search here before debugging** (`/savememo search <keywords>`), and **save here after solving** something non-obvious.

| Type | Use for |
|------|---------|
| `knowhow` | How something works or must be done in this project / stack |
| `tip` | A trick or shortcut that saves time |
| `issue` | A problem seen, cause unknown or fix pending (`open`) |
| `problem-solve` | A problem with its cause and the fix that worked (`solved`) |

Rules: one entry per problem; no secrets, passwords, or real connection strings (redact them); cite `file:line`, command, or error text as evidence; mark an entry `outdated` instead of deleting it; diagrams are Mermaid blocks.

---
"""

SECRET_PATTERNS = [
    (re.compile(r"(?i)\b(password|passwd|pwd|secret|api[_-]?key|access[_-]?key|token)\s*[=:]\s*(?!\*{3}|<|\[|redacted|xxx|\.\.\.)[^\s;,'\"]{3,}"), "a password / secret / token value"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]{20,}"), "a bearer token"),
    (re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{40,}={0,2}(?![A-Za-z0-9+/])"), "a long key-like string (40+ base64 characters)"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
]

ENTRY_RE = re.compile(r"^## (KH-\d+) · \[([^\]]+)\] (.*)$")
FIELD_RE = re.compile(r"^\|\s*([A-Za-z ]+?)\s*\|\s*(.*?)\s*\|\s*$")
SECTIONS = ("Problem / Context", "Cause", "Solution / Steps", "References")


# ----------------------------------------------------------------------------- file access
class Lock:
    def __init__(self, path):
        self.lock = Path(str(path) + ".lock")

    def __enter__(self):
        deadline = time.time() + 15
        while True:
            try:
                fd = os.open(str(self.lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
                return self
            except FileExistsError:
                try:
                    if time.time() - self.lock.stat().st_mtime > 30:  # stale lock of a crashed run
                        self.lock.unlink()
                        continue
                except OSError:
                    pass
                if time.time() > deadline:
                    raise SystemExit(f"Could not lock {self.lock} (another run is writing). Retry in a few seconds.")
                time.sleep(0.2)

    def __exit__(self, *exc):
        try:
            self.lock.unlink()
        except OSError:
            pass


def read_text(path):
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def parse(text):
    """Return (header, entries). An entry is a dict with its raw block under 'raw'."""
    lines = text.split("\n")
    starts = [i for i, l in enumerate(lines) if ENTRY_RE.match(l)]
    header = "\n".join(lines[: starts[0]]) if starts else text
    entries = []
    for n, s in enumerate(starts):
        e = starts[n + 1] if n + 1 < len(starts) else len(lines)
        block = lines[s:e]
        while block and block[-1].strip() in ("", "---"):
            block.pop()
        m = ENTRY_RE.match(block[0])
        fields = {}
        for l in block[1:]:
            fm = FIELD_RE.match(l)
            if fm and fm.group(1) not in ("Field",):
                fields[fm.group(1).lower()] = fm.group(2)
        entries.append({"id": m.group(1), "type": m.group(2), "title": m.group(3), "fields": fields, "raw": "\n".join(block)})
    return header, entries


def render(header, entries):
    out = header.rstrip("\n") + "\n\n"
    out += "\n\n---\n\n".join(e["raw"] for e in entries)
    return out + ("\n" if entries else "")


def next_id(entries):
    nums = [int(e["id"][3:]) for e in entries]
    return f"KH-{(max(nums) + 1) if nums else 1:03d}"


def check_secrets(*values):
    for v in values:
        for rx, what in SECRET_PATTERNS:
            if v and rx.search(v):
                return what
    return None


def tokens(s):
    return [t for t in re.split(r"[^\w]+", s.lower()) if len(t) >= 2]


# ----------------------------------------------------------------------------- commands
def build_entry(eid, a, today):
    body = [
        f"## {eid} · [{a.type}] {a.title.strip()}",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| ID | {eid} |",
        f"| Type | {a.type} |",
        f"| Status | {a.status} |",
        f"| Area | {a.area} |",
        f"| Tags | {', '.join(t.strip() for t in a.tags.split(',') if t.strip())} |",
        f"| Added | {today} by {a.author} |",
        f"| Updated | {today} |",
        "",
        "**Problem / Context**",
        a.problem.strip(),
        "",
    ]
    if a.cause:
        body += ["**Cause**", a.cause.strip(), ""]
    if a.solution:
        body += ["**Solution / Steps**", a.solution.strip(), ""]
    if a.refs:
        body += ["**References**", a.refs.strip(), ""]
    return "\n".join(body).rstrip("\n")


def cmd_add(a, path):
    if a.type not in TYPES:
        print(f"--type must be one of: {', '.join(TYPES)}")
        return 2
    if a.type == "problem-solve" and not (a.solution and a.cause):
        print("A `problem-solve` entry needs --cause and --solution (use --type issue when the fix is not known yet).")
        return 2
    if a.type == "problem-solve" and a.status == "open":
        a.status = "solved"
    if a.status not in STATUSES:
        print(f"--status must be one of: {', '.join(STATUSES)}")
        return 2
    what = check_secrets(a.title, a.problem, a.cause, a.solution, a.refs, a.tags)
    if what:
        print(f"Refused: the text looks like it contains {what}. Redact it (for example `Password=***`) and run again.")
        return 3
    with Lock(path):
        text = read_text(path)
        header, entries = parse(text) if text else (HEADER, [])
        if not a.force:
            qt = set(tokens(a.title))
            for e in entries:
                et = set(tokens(e["title"]))
                if qt and et and len(qt & et) / len(qt | et) >= 0.6 and e["fields"].get("status") != "outdated":
                    print(f"Possible duplicate of {e['id']} ({e['title']}). Review it with `show {e['id']}`; update it with `status`, or re-run with --force to add anyway.")
                    return 4
        eid = next_id(entries)
        entries.append({"id": eid, "type": a.type, "title": a.title.strip(), "fields": {}, "raw": build_entry(eid, a, str(date.today()))})
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(header, entries), encoding="utf-8", newline="\n")
    print(f"Saved {eid} [{a.type}/{a.status}] {a.title.strip()}")
    print(f"File: {path}")
    print(f"Commit (explicit path): git add {path} ; git commit -m \"docs: add {eid} {a.title.strip()[:40]}\" -m \"subagent: <your agent name>\" -- {path}")
    return 0


def matches(e, a):
    f = e["fields"]
    if a.type and e["type"] != a.type:
        return False
    if a.area and f.get("area", "").lower() != a.area.lower():
        return False
    if a.status and f.get("status", "") != a.status:
        return False
    return True


def score(e, toks):
    f = e["fields"]
    title, tags, area = e["title"].lower(), f.get("tags", "").lower(), f.get("area", "").lower()
    body = e["raw"].lower()
    s, hit = 0, 0
    for t in toks:
        c = 0
        if t in title:
            c += 5
        if t in tags:
            c += 4
        if t in area:
            c += 2
        n = body.count(t)
        if n:
            c += min(n, 3)
        if c:
            hit += 1
        s += c
    if toks and hit == len(toks):
        s += 10
    if f.get("status") == "outdated":
        s -= 3
    return s if hit else 0


def one_line(e):
    f = e["fields"]
    tail = f" — {f.get('area', '')}" + (f" — {f['tags']}" if f.get("tags") else "")
    return f"{e['id']}  [{e['type']}/{f.get('status', '?')}]  {e['title']}{tail}"


def cmd_search(a, path):
    text = read_text(path)
    if not text:
        print("KNOWHOW.md does not exist yet - nothing saved. (Add the first entry with `add`.)")
        return 0
    _, entries = parse(text)
    toks = tokens(" ".join(a.keywords))
    if not toks:
        print("Give at least one keyword (2+ characters).")
        return 2
    ranked = sorted(((score(e, toks), e) for e in entries if matches(e, a)), key=lambda x: -x[0])
    ranked = [(s, e) for s, e in ranked if s > 0][: a.limit]
    if not ranked:
        print(f"No entry matches: {' '.join(a.keywords)}  ({len(entries)} entries searched). After you solve it, save it with `add`.")
        return 0
    print(f"{len(ranked)} match(es) for: {' '.join(a.keywords)}\n")
    for n, (s, e) in enumerate(ranked):
        if n < a.full:
            note = "  (OUTDATED - verify before using)" if e["fields"].get("status") == "outdated" else ""
            print(e["raw"] + (note and f"\n{note}") + "\n\n" + "-" * 60 + "\n")
        else:
            print(one_line(e))
    return 0


def cmd_list(a, path):
    text = read_text(path)
    if not text:
        print("KNOWHOW.md does not exist yet - nothing saved.")
        return 0
    _, entries = parse(text)
    sel = [e for e in entries if matches(e, a)]
    print(f"{len(sel)} of {len(entries)} entries\n")
    for e in sel:
        print(one_line(e))
    return 0


def find(entries, eid):
    eid = eid.upper() if eid.upper().startswith("KH-") else f"KH-{int(eid):03d}"
    return next((e for e in entries if e["id"] == eid), None)


def cmd_show(a, path):
    text = read_text(path)
    if not text:
        print("KNOWHOW.md does not exist yet.")
        return 1
    _, entries = parse(text)
    e = find(entries, a.id)
    if not e:
        print(f"{a.id} not found")
        return 1
    print(e["raw"])
    return 0


def cmd_status(a, path):
    what = check_secrets(a.note)
    if what:
        print(f"Refused: the note looks like it contains {what}. Redact it.")
        return 3
    with Lock(path):
        text = read_text(path)
        if not text:
            print("KNOWHOW.md does not exist yet.")
            return 1
        header, entries = parse(text)
        e = find(entries, a.id)
        if not e:
            print(f"{a.id} not found")
            return 1
        today = str(date.today())
        raw = re.sub(r"(?m)^\| Status \|.*\|$", f"| Status | {a.new_status} |", e["raw"], count=1)
        raw = re.sub(r"(?m)^\| Updated \|.*\|$", f"| Updated | {today} |", raw, count=1)
        raw += f"\n\n**Update {today} ({a.author}):** status → {a.new_status}" + (f". {a.note.strip()}" if a.note else "")
        e["raw"] = raw
        path.write_text(render(header, entries), encoding="utf-8", newline="\n")
    print(f"{e['id']} status -> {a.new_status}")
    print(f"Commit (explicit path): git add {path} ; git commit -m \"docs: update {e['id']} to {a.new_status}\" -m \"subagent: <your agent name>\" -- {path}")
    return 0


# ----------------------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description="Keep and recall know-how, tips, issues and solutions (KNOWHOW.md).")
    ap.add_argument("--file", help="memo file (default: <DOC_DIR>/KNOWHOW.md next to this skill)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add", help="save a new entry")
    p.add_argument("--type", required=True, choices=TYPES)
    p.add_argument("--title", required=True, help="short, searchable title (the symptom or the topic)")
    p.add_argument("--problem", required=True, help="problem or context: what happened / when it matters, incl. exact error text")
    p.add_argument("--cause", default="", help="root cause (needed for problem-solve)")
    p.add_argument("--solution", default="", help="solution or steps (needed for problem-solve)")
    p.add_argument("--refs", default="", help="evidence: file:line, command, link, plan step (S2), commit")
    p.add_argument("--area", default="other", help="db | backend | frontend | build | test | git | hooks | env | docs | other")
    p.add_argument("--tags", default="", help="comma-separated keywords people would search for")
    p.add_argument("--status", default="open", help="open | solved | outdated (problem-solve defaults to solved)")
    p.add_argument("--author", required=True, help="'user' or the agent name")
    p.add_argument("--force", action="store_true", help="add even when a similar title exists")
    p.set_defaults(fn=cmd_add)

    p = sub.add_parser("search", help="find entries by keywords")
    p.add_argument("keywords", nargs="+")
    p.add_argument("--type", choices=TYPES)
    p.add_argument("--area")
    p.add_argument("--status", choices=STATUSES)
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--full", type=int, default=3, help="print the top N entries in full (default 3)")
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser("list", help="one line per entry")
    p.add_argument("--type", choices=TYPES)
    p.add_argument("--area")
    p.add_argument("--status", choices=STATUSES)
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("show", help="print one entry")
    p.add_argument("id", help="KH-012 or 12")
    p.set_defaults(fn=cmd_show)

    p = sub.add_parser("status", help="change an entry's status")
    p.add_argument("id")
    p.add_argument("new_status", choices=STATUSES)
    p.add_argument("--note", default="", help="why (what changed, what replaced it)")
    p.add_argument("--author", required=True)
    p.set_defaults(fn=cmd_status)

    a = ap.parse_args()
    path = Path(a.file) if a.file else DEFAULT_FILE
    return a.fn(a, path)


if __name__ == "__main__":
    sys.exit(main())
