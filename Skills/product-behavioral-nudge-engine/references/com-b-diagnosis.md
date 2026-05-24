# COM-B diagnosis — for any target behavior

## Decision tree

```
Target behavior: <e.g. "user completes profile after signup">

Are the users who DON'T do it:
├── Unable to do it (Capability)?
│       - psychological: don't know how
│       - physical:      need a tool / data / device they lack
│   → FIX: instruction, example, worked walkthrough, reduce complexity
│
├── Unable to do it in their context (Opportunity)?
│       - physical:  no time, no environment, no required input
│       - social:    norm against it, no peer model
│   → FIX: reduce required inputs, move the ask to a better moment, prefill,
│          show peer behavior ("12 of your team have completed this")
│
└── Capable + has opportunity but don't want to (Motivation)?
        - reflective: don't see the value (conscious)
        - automatic:  habit not formed (subconscious)
    → FIX: clarify value, social proof, loss frame (carefully),
           identity framing ("you're the kind of person who…"),
           reduce friction so the automatic path becomes the desired behavior
```

## Evidence to collect per blocker

| Blocker | What to look at |
|---|---|
| Capability (psych) | Time spent on the step; help-doc searches; support tickets |
| Capability (phys) | Errors during the step; device / browser / region patterns |
| Opportunity (phys) | Time of day, day of week, abandonment after starting |
| Opportunity (social) | Cohort effects: do users with active peers complete more? |
| Motivation (refl) | Survey: "did you see the value of completing this?" |
| Motivation (auto) | Patterns of "started, didn't finish, came back, finished" — habit forming |

## Common mistake
Skipping diagnosis and treating every gap as motivation. If you send "complete your profile!" emails to people who don't have the required document on hand, the email feels like nagging because it IS nagging — they can't comply.
