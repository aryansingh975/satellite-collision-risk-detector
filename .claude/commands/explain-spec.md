---
description: Explain what was done, how and why after a verified spec
argument-hint: spec-id (e.g., S3.2, S5.4)
allowed-tools: Read, Glob
---

After verifying spec $ARGUMENTS, read the spec and explain clearly:

## Step 1: Load Spec
1. Find spec folder: `specs/spec-$ARGUMENTS*/`
2. Read `spec.md` — load Tangible Outcomes, Functional Requirements
3. Read `checklist.md` — note what was checked off
4. Read `roadmap.md` row for this spec

## Step 2: Explain WHAT was done
- List every file that was created or modified
- List every Tangible Outcome that was implemented
- Show the final verdict (PASS/FAIL) from verification

## Step 3: Explain HOW it was implemented
- What was the technical approach?
- What key functions/classes were created?
- What tests were written and what do they verify?
- How does it connect to other parts of the system?

## Step 4: Explain WHY those choices were made
- Why this architecture/structure?
- Why these specific technical decisions?
- Any tradeoffs that were made?

## Step 5: Plain English Summary
Write a simple 5-10 line summary that even a non-technical
person could understand:
- What does this spec do for the satellite tracking system?
- What can the system now do that it couldn't before?
- How does this spec connect to the next one?
## Step 6: Just tell that am i ready to go on the next spec
write in one line that i can start with next spec or not