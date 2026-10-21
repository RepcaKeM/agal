# LinkedIn MCP: tool map

Read from the source of `mcp-server-linkedin` 4.26.2 (github.com/stickerdaniel/linkedin-mcp-server).
Tool names as Claude Code exposes them: `mcp__linkedin__<tool>`. The server drives a
Chromium browser on the user's own LinkedIn session; calls run one at a time and can
take up to 180 s each.

| Use | Tool | Notes |
|---|---|---|
| search | `search_jobs` | `keywords` (required), `location` (free text, e.g. `Poland`, `Kraków`), `work_type` (`remote`, `hybrid`, `on_site`, comma-separated), `date_posted` (`past_hour`, `past_24_hours`, `past_week`, `past_month`), `job_type` (`full_time`, `contract`, `part_time`, …), `experience_level`, `easy_apply`, `sort_by` (`date`, `relevance`), `max_pages` 1–10 (default 3). Returns `job_ids`, raw text in `sections`, `total`. No matches → empty `job_ids` + `section_errors` `no_matching_jobs` |
| details | `get_job_details` | `job_id`. Returns `url` (`https://www.linkedin.com/jobs/view/<id>/`), raw text in `sections.job_posting` — parse it yourself. `apply: {type: applied \| closed}` only when the posting shows it; no `apply` key does not prove it is open |

## Errors worth knowing

- `section_errors.job_posting.error_type` `description_missing` — the text lacks the
  English "About the job" heading (the server expects the English LinkedIn UI). Text is
  kept but may be incomplete; one retry may return more.
- a rate-limited section error → stop the run (see SKILL.md Safety).
- setup/auth in progress → the server asks to retry in about 30 s.

## Write tools — never call

`send_message`, `connect_with_person`. They are also denied in the workspace's
`.claude/settings.json`.
