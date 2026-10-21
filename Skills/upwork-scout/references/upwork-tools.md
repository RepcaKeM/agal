# Upwork MCP: tool map

Verified 2026-10-07 against the official Upwork MCP (`https://mcp.upwork.com/mcp`).
Tool names as Claude Code exposes them: `mcp__upwork__upwork__<tool>`. Every call
takes `org_uid` — get it once per run from `list_accounts` (the account with
`role: TALENT`).

| Spec action | Tool + action | Notes |
|---|---|---|
| account / org_uid | `list_accounts` | no params |
| invitations | `list_freelancer_proposals` `invitations` | `id` = invitation_uid; `jobPosting.id` → `find_jobs get` |
| matched jobs | `find_jobs` `smart_search` | `mode: best_match` or `most_recent` (+ `days_posted`); no query; returns `connect_price`, `applied` |
| keyword search | `find_jobs` `search` | `query` (whole posting) or `title` (1–3 words, ANDed); `verified_payment_only`, `job_type`, `rate_min`, `budget_min` (fixed only); `limit` ≤ 10, `cursor` |
| job details | `find_jobs` `get` | `id` = numeric id, `~02…` or URL. Returns `connects_cost`, `connects_balance`, `can_apply`, `applied`, `client_record` (hires, spend, feedback, `hire_rate_percent`), `activityStat.jobActivity` (hired/offered), `preferred_qualifications`, `url` |
| my proposals + status | `list_freelancer_proposals` `list` / `get` | `status`: Accepted = **submitted**, Pending = processing, Offered, Hired, Declined, Withdrawn, Archived, Activated = invitation accepted |
| Connects balance | `get_freelancer_dashboard` `check` (also in `find_jobs get` and the create preview) | dashboard also lists invitations, offers, matching jobs |
| prepare proposal | `manage_proposals` `create` | params `job_reference` (numeric id), `cover_letter` (≤ 5000 chars), `charged_amount` (number), `answers` [{question, answer}], optional `boost_connects`, `attachments`, `portfolio_project_ids`, `certificate_ids`. Returns a **server-side preview** (`preview_id`) with `connects_cost`, `connects_balance`, screening questions, boost info. **Not submitted.** |
| reply to an invitation | `manage_proposals` `accept_invitation` | `invitation_uid`, `cover_letter`, `bid`, `answers`. Use instead of `create` when an invitation exists (`create` fails with VJ-JA-10) |
| submit | `confirm_preview` `type: proposal` (or `proposal_accept_invitation`), `preview_id` | **spends Connects**; only after explicit user approval in the chat |
| read a pending preview | `get_preview` `type`, `id` | does not consume it |

## Rules the Upwork server imposes

- Before `create`: check `list_freelancer_proposals invitations` and `list` for this job.
- Before submitting: ask the user about file attachments and about attaching portfolio
  projects / certificates (`get_profile list_highlights`). Always state `connects_cost`
  and `connects_balance`. Offer boost only when `boost.available` and the recommendation
  is not `skip`; never invent bid numbers.
- After submitting, status is `Pending`, then `Accepted` (= submitted).

## What does not exist

- **No draft on upwork.com.** A preview lives only on the MCP server; the user cannot
  open or submit it on upwork.com. It has no URL and expires 15 minutes after creation
  (`expires_at`, `ttl_seconds: 899` observed 2026-10-07). Submitting happens only through
  `confirm_preview`.
- **No more than one live preview at a time.** Each `manage_proposals` create replaces
  the previous preview (`supersedes_previous_preview: true`); the older `preview_id`
  then returns "Invalid or expired preview_id" (observed 2026-10-07). To send several
  approved proposals: for each one, rebuild its preview with the approved text and
  rate, then `confirm_preview` it before building the next.
- **Proposal counts in search lag.** `find_jobs search` showed 17 proposals; after
  submitting, `list_freelancer_proposals get` insights showed 68 for the same job.
