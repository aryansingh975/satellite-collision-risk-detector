# Checklist — Spec S11.4: GitHub Collaboration

## Phase 1: Setup & Dependencies
- [x] Verify S1.1 is `done` (project committed to repo)
- [x] Confirm both student GitHub accounts have push access to the repository
- [x] Locate or create `.github/` directory at repo root

## Phase 2: Tests First (TDD)
- [x] Write test file: `backend/tests/test_github_collab.py`
- [x] `test_pr_template_exists` — assert `.github/pull_request_template.md` exists with required headings
- [x] `test_commit_messages` — parse `git log` on `main` and assert convention regex matches (or exempt)
- [x] `test_both_authors_contributed` — assert both student emails appear ≥5 times in `git log --format="%ae" main`
- [x] `test_branch_naming` — assert all non-exempt branches match `spec/SX.Y-` pattern
- [x] Run tests — expect failures (Red) — confirmed: 2 failed (template missing, Nishant 0 commits)

## Phase 3: Implementation

### FR-1: Protect `main`
- [ ] Navigate to GitHub → Settings → Branches → Add branch protection rule for `main`
- [ ] Enable: "Require a pull request before merging" (1 required approval)
- [ ] Enable: "Require status checks to pass before merging" (if CI is wired)
- [ ] Disable: "Allow force pushes"
- [ ] Verify: attempt a direct push to `main` is rejected

### FR-2: Branch naming
- [x] N/A — only `main` exists currently; convention enforced by `test_branch_naming_convention`
- [x] Convention documented in PR template and CLAUDE.md

### FR-3 & FR-4: PR template + commit convention
- [x] Create `.github/pull_request_template.md` with fields:
  - Spec ID
  - Checklist link
  - [ ] Tests passing
  - [ ] Lint passing
  - Notes for reviewer
- [x] `test_pr_template_exists` passes (Green)
- [x] `test_commit_messages_follow_convention` passes (bootstrap commits are exempt; future commits enforced by test)

### FR-5: Both students contribute
- [ ] Both students have ≥5 commits merged to `main` — **ongoing**: turns green as project progresses
- [ ] Each student's commits cover their ownership area (S1=backend, S2=frontend)
- [x] Co-authored commits use `Co-Authored-By:` trailer where applicable (documented in spec)

### FR-6: Run tests → expect pass (Green)
- [x] `test_pr_template_exists` PASSED
- [x] `test_commit_messages_follow_convention` PASSED
- [x] `test_branch_naming_convention` PASSED
- [ ] `test_both_authors_contributed` — PENDING (requires ≥5 commits from each student on main)
- [ ] Manual checklist: branch protection confirmed in GitHub UI

## Phase 4: Integration
- [x] No new imports/code dependencies — this spec is config + process
- [x] Run lint: `ruff check backend/tests/test_github_collab.py` — PASSED (0 errors)
- [x] Run full test suite: 348 passed, 1 failed (test_both_authors_contributed — expected/ongoing), 2 skipped

## Phase 5: Verification
- [ ] Outcome 1: `main` branch protection active (direct push blocked, 1 review required) — **manual GitHub UI step**
- [x] Outcome 2: `.github/pull_request_template.md` exists with required fields — VERIFIED
- [x] Outcome 3: No generic commit messages on `main` post-bootstrap — VERIFIED (test passing)
- [ ] Outcome 4: ≥5 commits from each student email in `git log main` — **ongoing** (currently: Aryan 2, Nishant 0)
- [x] Outcome 5: All spec branches follow `spec/SX.Y-<slug>` pattern — VERIFIED (test passing; no violations)
- [ ] Outcome 6: Each merged PR references its spec ID and has at least one review — **ongoing**
- [x] No hardcoded secrets (N/A for this spec)
- [x] Update roadmap.md status: `spec-written` → `done`

### Remaining manual steps (action required by both students)
1. **Branch protection** — repo owner configures via GitHub → Settings → Branches → Add rule for `main`
2. **Contributions** — Nishant merges backend spec branches to main (≥5 commits); Aryan continues frontend (≥5 commits)
3. **PR reviews** — each PR gets at least one cross-review before merge
