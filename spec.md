# Spec SX.Y — <Feature>

| Field | Value |
|-------|-------|
| **Spec** | SX.Y |
| **Phase** | <Phase name> |
| **Owner** | S1 / S2 / Both |
| **Location** | `<file path the code lives in>` |
| **Depends On** | S?.? (all must be `done`) |
| **Status** | pending → spec → impl → done |

## Objective
*One paragraph: the single observable outcome this spec delivers.*

## Scope
**In:** …
**Out:** … *(keep the spec atomic — one function / file / artifact)*

## Interface / Contract
*Exact public surface dependents rely on — function signature(s), endpoint path + request/response schema, or data shape.*

```
# signature / endpoint / schema
```

## Dependencies & Assumptions
- Upstream specs: …
- Libraries / data: …
- Thresholds / formulas / constants (record decisions): …

## Acceptance Criteria → Test List  *(becomes the TDD tests, written RED-first)*

| # | Test (given / when / then) | Type |
|---|----------------------------|------|
| 1 | … | unit |
| 2 | … | integration |
| 3 | … | oracle / e2e / manual-acceptance |

## Notes / Risks
*Limitations, tradeoffs, anything the next person needs to know.*
