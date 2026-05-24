# API reference — one entry per endpoint / function

```
## <method> <path>      OR      ## <fn name>

<One-sentence description of what it does.>

### Parameters

| Name | Type | In | Required | Description |
|---|---|---|---|---|
| user_id | string (UUID) | path | yes | Target user |
| include | string | query | no | Comma-separated list of expansions: `profile,settings` |

### Request example

​```bash
curl -X GET https://api.example.com/v1/users/123 \
  -H "Authorization: Bearer $TOKEN" \
  -d 'include=profile'
​```

### Response (200)

​```json
{
  "id": "123",
  "email": "ada@example.com",
  "profile": { "display_name": "Ada" }
}
​```

### Errors

| Code | Meaning | Recovery |
|---|---|---|
| 401 | Missing / invalid token | Re-auth |
| 404 | User not found | Verify the user_id |
| 429 | Rate-limited | Backoff per `Retry-After` header |

### Notes

Anything non-obvious about caching, idempotency, side effects, timing.
```

## Rules
- One minimal real example per endpoint. Don't show every parameter combination.
- Document EVERY error code the endpoint can return.
- Generate from source where possible (OpenAPI → reference page). Hand-written drifts.
- Version every page (or pin version in code blocks if single-version).
