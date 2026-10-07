# CrewAI agent team for weekly competitor research reports

**Budget:** Fixed price, $1,800 · **Experience:** Expert

We are a B2B SaaS company in logistics software. Every Monday our product marketer
spends half a day checking eight competitors: pricing pages, changelogs, blog posts,
job ads and G2 reviews. The result is a two-page summary for leadership.

We want a Python solution built on CrewAI (or LangGraph if you can justify it): one
agent collects sources, one extracts what changed since last week, one writes the
summary in our template. Output goes to a Google Doc and a Slack message. It must cite
the source URL for every claim, and it should run on a schedule on our own server
(Docker is fine).

**Screening questions**
1. Have you built a multi-agent system before? What framework and what did it do?
2. How do you make sure the summary does not contain invented facts?
