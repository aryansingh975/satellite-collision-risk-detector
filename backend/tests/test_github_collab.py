"""
S11.4 — GitHub collaboration hygiene tests.

Checks run against the live repository and filesystem; no HTTP mocks needed.

  test_pr_template_exists     — FR-6: .github/pull_request_template.md exists
  test_commit_messages        — FR-4: non-exempt commits follow SX.Y(<type>): convention
  test_developer_contributed  — FR-5: developer email has ≥2 commits on main
  test_branch_naming_convention — FR-2: all branches follow spec/SX.Y-<slug> or exempt pattern
"""

import re
import subprocess
from pathlib import Path

# Project root: satellite-collision-risk-detector/ (3 levels up from backend/tests/)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Developer email address
DEVELOPER_EMAIL = "0309.aryansingh@gmail.com"

# Commit subjects that are exempt from the convention (initial bootstrapping
# and pre-spec-workflow commits made before the convention was enforced).
BOOTSTRAP_SUBJECTS = frozenset(
    {
        "Initial commit",
        "Add README and update gitignore",
        "Add full app implementation: backend API, frontend globe, Docker, docs",
        "Update screenshots and README to match current UI",
    }
)

# SX.Y(<type>): <description>   e.g.  S5.4(impl): TCA refinement & miss distance
CONVENTION_RE = re.compile(r"^S\d+\.\d+\([a-z]+\): .+")

# GitHub-generated merge commits are exempt
MERGE_COMMIT_RE = re.compile(r"^Merge pull request #\d+")


def _git(*args: str) -> list[str]:
    """Run a git command from the repo root; return non-empty output lines."""
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# FR-6: PR template
# ---------------------------------------------------------------------------


class TestPRTemplate:
    def test_pr_template_exists(self):
        """FR-6: .github/pull_request_template.md must exist with required fields."""
        template = REPO_ROOT / ".github" / "pull_request_template.md"
        assert template.exists(), (
            "Missing: .github/pull_request_template.md — "
            "create it with Spec ID, Checklist, Tests passing, Lint passing fields."
        )
        content = template.read_text(encoding="utf-8")
        required_fields = ("Spec ID", "Checklist", "Tests passing", "Lint passing")
        for field in required_fields:
            assert field in content, (
                f"PR template is missing required field: {field!r}"
            )


# ---------------------------------------------------------------------------
# FR-4: Commit message convention
# ---------------------------------------------------------------------------


class TestCommitMessages:
    def test_commit_messages_follow_convention(self):
        """FR-4: Post-bootstrap commits on main must follow SX.Y(<type>): convention."""
        log = _git("log", "--format=%s", "main")
        violations = []
        for subject in log:
            if subject in BOOTSTRAP_SUBJECTS:
                continue
            if MERGE_COMMIT_RE.match(subject):
                continue
            if not CONVENTION_RE.match(subject):
                violations.append(f"  {subject!r}")
        assert not violations, (
            "Commits on main violate the message convention:\n"
            + "\n".join(violations)
            + "\nRequired format: SX.Y(<type>): <description>"
            "\nExample: S5.4(impl): TCA refinement & miss distance"
            "\nAllowed types: spec, impl, fix, test, docs, refactor"
        )


# ---------------------------------------------------------------------------
# FR-5: Developer has committed
# ---------------------------------------------------------------------------


class TestContributions:
    MIN_COMMITS = 2

    def test_developer_contributed(self):
        """FR-5: Developer email must appear ≥2 times in git log main."""
        emails = _git("log", "--format=%ae", "main")
        count = emails.count(DEVELOPER_EMAIL)
        assert count >= self.MIN_COMMITS, (
            f"Developer ({DEVELOPER_EMAIL}) has {count} commit(s) on main; "
            f"need ≥{self.MIN_COMMITS}."
        )


# ---------------------------------------------------------------------------
# FR-2: Branch naming convention
# ---------------------------------------------------------------------------


class TestBranchNaming:
    # Patterns exempt from the spec/SX.Y-<slug> requirement
    EXEMPT_PATTERNS = [
        re.compile(r"^main$"),
        re.compile(r"^HEAD$"),
        re.compile(r"^origin$"),
        re.compile(r"^origin/main$"),
        re.compile(r"^origin/HEAD$"),
        re.compile(r"^feature/satcollision-"),
        re.compile(r"^origin/feature/satcollision-"),
        re.compile(r"^hotfix/"),
        re.compile(r"^docs/"),
        # Common shorthand conventions used alongside the spec workflow
        re.compile(r"^fix/"),
        re.compile(r"^feat/"),
        re.compile(r"^origin/fix/"),
        re.compile(r"^origin/feat/"),
    ]
    # The required pattern for all other branches
    SPEC_BRANCH_RE = re.compile(r"^(origin/)?spec/S\d+\.\d+-")

    def test_branch_naming_convention(self):
        """FR-2: All branches must follow spec/SX.Y-<slug> or an exempt pattern."""
        branches = _git("branch", "-a", "--format=%(refname:short)")
        violations = []
        for branch in branches:
            if any(pat.match(branch) for pat in self.EXEMPT_PATTERNS):
                continue
            if self.SPEC_BRANCH_RE.match(branch):
                continue
            violations.append(f"  {branch!r}")
        assert not violations, (
            "Branches violate the naming convention:\n"
            + "\n".join(violations)
            + "\nAllowed: spec/SX.Y-<slug>, feature/satcollision-*, hotfix/*, docs/*"
        )
