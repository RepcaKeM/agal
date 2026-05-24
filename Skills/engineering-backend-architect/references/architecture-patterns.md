# Architecture patterns — when to pick what

## Modular monolith
- **Use when**: small team (<10 devs), unclear domain boundaries, early-stage product.
- **Avoid when**: independent scaling per module is a hard requirement, or teams need fully independent deploy.
- **Trap**: ignoring module boundaries inside the monolith — it becomes a distributed monolith without the benefits.

## Microservices
- **Use when**: clear bounded contexts, team-per-service ownership is realistic, independent scaling matters.
- **Avoid when**: <5 services, no platform team, team can't run own DB.
- **Trap**: distributed transactions. If two services need the same atomic write, you split wrong.

## Event-driven (pub/sub or event log)
- **Use when**: producers and consumers evolve independently, async tolerable, fan-out is real.
- **Avoid when**: caller needs the result immediately, ordering across topics matters.
- **Trap**: lost or duplicated messages — design for at-least-once and idempotent consumers.

## CQRS / read models
- **Use when**: write model and read model diverge significantly (e.g. analytics views, search indices).
- **Avoid when**: CRUD app with simple queries — you're adding two systems to replace one.
- **Trap**: eventual consistency surfaces to the user; budget for "your change might take a few seconds to appear."

## API style
- **REST**: external consumers, cacheability, broad tooling. Default unless you have a reason.
- **GraphQL**: many client variants with different needs, federation across services. High infra cost.
- **gRPC**: internal service-to-service, strict typing, streaming. Avoid for browser clients without proxy.
- **Server-Sent Events / WebSocket**: server-push to one client. Plan for reconnection and message replay.
