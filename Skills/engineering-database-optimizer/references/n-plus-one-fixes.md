# Fixing N+1 — patterns in order of preference

## 1. JOIN with aggregation (single round-trip)

```sql
SELECT
    u.id,
    u.email,
    COALESCE(
        json_agg(
            json_build_object('id', p.id, 'title', p.title)
        ) FILTER (WHERE p.id IS NOT NULL),
        '[]'
    ) AS posts
FROM users u
LEFT JOIN posts p ON p.user_id = u.id
WHERE u.created_at > NOW() - INTERVAL '7 days'
GROUP BY u.id;
```

Pros: one query. Cons: payload can be big; not great if "posts per user" is unbounded.

## 2. Two queries + in-memory zip (DataLoader pattern)

```ts
const users = await db.query("SELECT * FROM users WHERE created_at > $1", [d]);
const userIds = users.map(u => u.id);
const posts = await db.query(
  "SELECT * FROM posts WHERE user_id = ANY($1::int[])", [userIds]
);
const postsByUser = groupBy(posts, p => p.user_id);
users.forEach(u => (u.posts = postsByUser[u.id] ?? []));
```

Pros: bounded per-row payload, works for unrelated sub-queries. Cons: two round-trips.

## 3. ORM eager-load

- Prisma: `include: { posts: true }`
- SQLAlchemy: `.options(selectinload(User.posts))`
- Active Record: `.includes(:posts)`

Verify it produces ONE query (or N=constant), not N=rows. Check the log.

## How to detect N+1 in dev

Log every SQL statement per HTTP request, then assert per-route:
- Static count (1, 2, 3) regardless of result size = good
- Count scales with rows = N+1

Tools: `pg_stat_statements`, `rack-mini-profiler`, Prisma's `log: ['query']`.
