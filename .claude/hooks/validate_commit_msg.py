"""PreToolUse hook: validate the commit message of every `git commit`.

Required subject: `<type>: <description>` (one space after the colon, at most 72 characters).
Valid types: feat, fix, perf, refactor, test, docs, chore, analyze, plans, review1, review2

Also enforced:
  * the message must be given with -m / --message (no editor, no -F file) so it can be validated
  * `subagent: <agent>` must be on its own line, never inside the subject, and name a known agent/skill

Works for `git commit`, `git -C <path> commit`, and `cd <path> && git commit`.

Exit 0 = allow, exit 2 = block (stderr is shown to Claude).
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gitparse import git_calls  # noqa: E402

TYPES = "feat|fix|perf|refactor|test|docs|chore|analyze|plans|review1|review2"
SUBJECT_RE = re.compile(rf"^(?:{TYPES}): \S.*$")
MAX_SUBJECT = 72
SUBAGENTS = {
    "vb-analyzer", "vb-planner", "vb-backend-developer", "vb-frontend-developer", "db-developer",
    "vb-backend-tester", "vb-frontend-tester", "vb-reviewer", "vb-requirement-analysis",
    "vb-researcher", "savememo",
}

# -m "msg" / -m 'msg' / --message="msg" / heredoc: -m "$(cat <<'EOF' ... EOF )"
HEREDOC_RE = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?\s*\n(.*?)\n\s*\1\b", re.DOTALL)
MSG_RE = re.compile(r"""(?:-m|--message)[=\s]*(?:"((?:[^"\\]|\\.)*)"|'([^']*)')""", re.DOTALL)
SUBAGENT_LINE = re.compile(r"^\s*subagent:\s*(\S+)\s*$", re.I | re.M)


def messages(command: str):
    """All -m / --message values (heredoc bodies included), in order."""
    out = []
    for h in HEREDOC_RE.finditer(command):
        out.append(h.group(2))
    for m in MSG_RE.finditer(command):
        text = m.group(1) if m.group(1) is not None else m.group(2)
        if text is not None and "$(cat <<" not in text:
            out.append(text)
    return out


def first_line(text: str):
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    command = (payload.get("tool_input") or {}).get("command", "")
    commit_args = [args for sub, args in git_calls(command) if sub == "commit"]
    if not commit_args:
        return 0

    msgs = messages(command)
    if not msgs:
        sys.stderr.write(
            "Blocked: give the commit message with -m (`git commit -m \"<type>: <description>\" -m \"subagent: <name>\" -- <paths>`); "
            "an editor, -F file, or --amend/--no-edit message cannot be validated.\n"
        )
        return 2

    subject = first_line(msgs[0])
    if subject is None or not SUBJECT_RE.match(subject):
        sys.stderr.write(
            f"Blocked: commit subject '{subject}' does not match '<type>: <description>'.\n"
            f"Valid types: {TYPES.replace('|', ', ')}.\n"
        )
        return 2
    if len(subject) > MAX_SUBJECT:
        sys.stderr.write(f"Blocked: commit subject is {len(subject)} characters; keep it at most {MAX_SUBJECT}.\n")
        return 2
    if "subagent:" in subject.lower():
        sys.stderr.write("Blocked: `subagent: <agent>` must be on its own line (a second -m), not inside the subject.\n")
        return 2
    for text in msgs:
        for name in SUBAGENT_LINE.findall(text):
            if name not in SUBAGENTS:
                sys.stderr.write(f"Blocked: unknown subagent '{name}'. Known: {', '.join(sorted(SUBAGENTS))}.\n")
                return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
