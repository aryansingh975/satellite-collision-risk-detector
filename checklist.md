# Checklist SX.Y — <Feature>

Status: `pending` → `spec` → `impl` → `done`
A spec is **done** only when Phase 4 passes. Do not start Phase 1 until every **Depends On** spec is `done`.

## Phase 1 · Create Spec
- [ ] All upstream deps are `done`
- [ ] `spec.md` complete — objective, scope, interface, deps, acceptance criteria, test list (no TBDs)
- [ ] Interface/contract is precise and unambiguous
→ Status becomes `spec` after Phase 2.

## Phase 2 · Verify Spec
- [ ] Reviewed by the other student
- [ ] Dependencies confirmed correct and `done`
- [ ] Every acceptance criterion is concrete and testable
- [ ] Test list agreed → **spec frozen**

## Phase 3 · Implement Spec (TDD)  → status `impl`
- [ ] Test 1 written RED → GREEN → refactor
- [ ] Test 2 written RED → GREEN → refactor
- [ ] Test 3 written RED → GREEN → refactor
- [ ] (…all tests from the list…)
- [ ] No skipped / xfail tests

## Phase 4 · Verify Implement  → status `done`
- [ ] Full suite green in CI
- [ ] Coverage target met; lint/format clean
- [ ] Acceptance criteria demonstrably met (manual items checked)
- [ ] Integrates with dependents without breaking them
- [ ] Merged to `main` via reviewed PR (commit: `SX.Y(impl): …`)
→ **DONE.** Downstream specs unlock.
