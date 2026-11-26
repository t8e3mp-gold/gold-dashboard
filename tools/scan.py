"""Public-repo safety scan. Fails on emails, key-like strings, private keys and password assignments.
Usage: python tools/scan.py [root]. Allowed: noreply addresses and example domains."""
import os, re, sys

PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "github-token": re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "aws-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private-key": re.compile("-----BEGIN [A-Z ]*PRIVATE" + " KEY-----"),
    "long-secret": re.compile(r"\b[A-Fa-f0-9]{40,}\b|\b[A-Za-z0-9+/]{48,}={0,2}\b"),
    "password-assign": re.compile(r"(?i)\b(pass(word|wd)?|secret|api[_-]?key|token)\b\s*[:=]\s*[\"'][^\"']{4,}[\"']"),
    "phone": re.compile(r"(?<![\d.])\+?\d{1,3}[ -]?\(?\d{2,4}\)?[ -]?\d{3,4}[ -]?\d{3,4}(?![\d.])"),
}
ALLOW_EMAIL = re.compile(r"(@users\.noreply\.github\.com|@example\.(com|org)|@t8e3mp-gold)$|^git@")
ACTION_PIN = re.compile(r"^\s*(-\s*)?uses:\s*[\w.-]+/[\w./-]+@[0-9a-f]{40}(\s+#.*)?\s*$")
SKIP_DIRS = {".git", "node_modules", "__pycache__"}
SKIP_FILES = {"scan.py", "test_scan.py", "package-lock.json"}
TEXT = (".py", ".js", ".mjs", ".json", ".md", ".yml", ".yaml", ".html", ".css", ".txt", ".sh", ".tsx", ".ts")

def scan_text(name, text):
    out = []
    for kind, rx in PATTERNS.items():
        for m in rx.finditer(text):
            s = m.group(0)
            if kind == "email" and ALLOW_EMAIL.search(s):
                continue
            if kind == "long-secret" and len(s) == 40 and ACTION_PIN.search(text[text.rfind("\n", 0, m.start()) + 1:text.find("\n", m.end()) if text.find("\n", m.end()) != -1 else len(text)]):
                continue  # a commit SHA pinning a GitHub Action is public, not a secret
            if kind == "phone":
                digits = re.sub(r"\D", "", s)
                if len(digits) < 10 or re.fullmatch(r"20\d{2}[-\d ]*", s.strip()) or not (s.startswith("+") or " " in s or "-" in s):
                    continue
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", s.strip()):
                    continue
            line = text.count("\n", 0, m.start()) + 1
            out.append(f"{name}:{line}: {kind}")
    return out

def scan(root):
    hits = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            if f in SKIP_FILES or not f.endswith(TEXT):
                continue
            p = os.path.join(d, f)
            try:
                text = open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                hits.append(f"{p}: unreadable text file"); continue
            hits += scan_text(os.path.relpath(p, root), text)
    return hits

if __name__ == "__main__":
    h = scan(sys.argv[1] if len(sys.argv) > 1 else ".")
    print("\n".join(h) if h else "scan clean")
    sys.exit(1 if h else 0)
