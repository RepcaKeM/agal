# Ethics checklist — run on any nudge / mechanic / cadence

## Alignment of interest
- [ ] Does this nudge advance the user's stated goal, OR our metric at their expense?
- [ ] Would the user agree this is helpful if you explained the mechanism to them?

## Transparency
- [ ] Is the user aware this nudge exists?
- [ ] Could they opt out without losing core functionality?
- [ ] Does the UI make the consequence of the action clear, or obscure it?

## Vulnerability
- [ ] Who's the worst-case user? (anxious / lonely / addicted / cognitively impaired / minor)
- [ ] What harm could this cause to that user?
- [ ] Is there a safer default / alternative for them?

## Dark-pattern check (any of these is a red flag)
- [ ] Forced action ("you must opt in to continue")
- [ ] Misdirection (CTA styled to push one option; quiet "no thanks")
- [ ] Confirmshaming ("No, I don't want to save money")
- [ ] Hidden costs (revealed after commitment)
- [ ] Sneak into basket / auto-renewal without prominent disclosure
- [ ] Privacy zuckering (defaults set to maximum sharing)
- [ ] Roach motel (easy to get in, hard to get out)

## Variable-reward / addictive mechanics
- [ ] Does this feature use variable-ratio reinforcement (slot-machine pattern)?
- [ ] If so: is it appropriate to the product purpose (vs. attention extraction)?
- [ ] Can the user disable it?

## Research ethics (if A/B testing on users)
- [ ] Is the experiment within "normal product variation" or does it warrant explicit consent?
- [ ] If risky (e.g. nudging financial / health behavior), is there IRB-equivalent review?
- [ ] Will harms be detectable within the experiment? Stopping rule defined?

## After
If any answer is concerning, the nudge needs redesign — not just a footnote in the spec.
