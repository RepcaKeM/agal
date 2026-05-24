# Where should this state live?

```
Is this data from the server?
├── YES → server-state library (TanStack Query, SWR, RTK Query, Apollo)
│        Provides cache, dedup, refetch, optimistic update.
│        DO NOT mirror into Redux/Zustand.
│
└── NO (it's UI state)
    │
    Is it used by exactly one component?
    ├── YES → useState in that component
    │
    Is it shared by 2-3 components in a small subtree?
    ├── YES → lift to nearest common ancestor; pass via props
    │
    Is it shared widely AND changes rarely (theme, current user, locale)?
    ├── YES → React Context (split: state context + setter context)
    │
    Is it shared widely AND changes often?
    └── YES → external store (Zustand for small/medium, Redux Toolkit for large)
              Selectors must be narrow to avoid re-rendering all consumers.
```

## Smells
- `useState` in a parent passed 6 levels deep → lift to context or store.
- Context value that changes every render → memoize, or split into stable + dynamic contexts.
- `useEffect` mirroring props to state → you almost never need this. Compute on render or use `useMemo`.
- Multiple components calling the same API independently → cache miss → use server-state lib.
