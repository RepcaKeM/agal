# Launch readiness checklist

## 2 weeks before
- [ ] PRD signed off
- [ ] Engineering has a deploy plan with rollback path
- [ ] Success + guardrail dashboards live and validated against historical data
- [ ] Pricing / packaging decision recorded (if applicable)
- [ ] Customer comms drafted (email + in-product + help center article)

## 1 week before
- [ ] Internal demo for sales / support / CS
- [ ] Support knows the top 3 anticipated questions and answers
- [ ] Feature flag wired; rollout plan written (e.g., 10% → 50% → 100%)
- [ ] Beta customers contacted; explicit "you can opt out" written

## Launch day
- [ ] Enabled per the rollout plan; not at 100%
- [ ] On-call paging on the guardrail dashboards
- [ ] Comms sent at the agreed time, not in a rush
- [ ] Twitter / changelog post matches the in-product message

## 1 week after
- [ ] Primary metric tracking against target
- [ ] Guardrails all green; investigate any drift > 1σ
- [ ] Top 3 user complaints triaged
- [ ] Post-launch review scheduled (within 30 days)
