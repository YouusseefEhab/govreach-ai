"""Check Git candidates for excluded artifacts and obvious credentials.

This is a focused repository guard, not a complete secret-scanning product.
"""

from pathlib import Path
import re
import subprocess

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {"node_modules", ".venv", ".venv-ci", "__pycache__", ".pytest_cache", "dist", ".git"}
TOKEN_PATTERNS = [
    re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),
    re.compile(rb"ghp_[0-9A-Za-z]{30,}"),
    re.compile(rb"github_pat_[0-9A-Za-z_]{40,}"),
    re.compile(rb"sk-proj-[0-9A-Za-z_-]{20,}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


def main():
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, capture_output=True, check=True,
    )
    paths = sorted(set(result.stdout.decode("utf-8").split("\0")) - {""})
    local_values = dotenv_values(ROOT / ".env") if (ROOT / ".env").exists() else {}
    secrets = [
        value.encode("utf-8") for name, value in local_values.items()
        if name in {"GEMINI_API_KEY", "OPENAI_API_KEY", "JWT_SECRET", "CLOUDFLARE_API_TOKEN"} and value and len(value) >= 12
    ]
    findings = []
    for name in paths:
        path = Path(name)
        if path.parts[:2] == ("data", "media") or set(path.parts) & EXCLUDED_PARTS or (path.name.startswith(".env") and path.name != ".env.example"):
            findings.append((name, "excluded local file"))
            continue
        absolute = ROOT / path
        if not absolute.is_file():
            continue
        data = absolute.read_bytes()
        if any(pattern.search(data) for pattern in TOKEN_PATTERNS) or any(secret in data for secret in secrets):
            findings.append((name, "possible credential; value suppressed"))
    if findings:
        for name, reason in findings:
            print(f"{name}: {reason}")
        return 1
    print(f"Repository guard passed for {len(paths)} Git candidates. Credential values were not printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
