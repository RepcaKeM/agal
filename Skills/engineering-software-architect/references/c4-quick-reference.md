# C4 — pick the level for the audience

## Level 1 — System Context
**For**: execs, new joiners, external stakeholders.
**Shows**: your system as one box, its users, and the external systems it talks to.
**Don't**: include internals.

## Level 2 — Containers
**For**: engineers across teams; onboarding.
**Shows**: web app, API, worker, DB, cache, queue. One box per deployable unit.
**Don't**: name classes or fields.

## Level 3 — Components
**For**: engineers within the team owning a container.
**Shows**: logical groupings inside one container (controllers, services, repositories).
**Don't**: draw if it duplicates the directory structure — read the code.

## Level 4 — Code
**For**: rarely. Sequence/class diagrams of a tricky algorithm or protocol.
**Don't**: generate from code "for completeness." It rots immediately.

## Rule
Always start at Level 1 for a new audience. Drop one level only when you've answered the question at the higher level and a new question demands more detail.
