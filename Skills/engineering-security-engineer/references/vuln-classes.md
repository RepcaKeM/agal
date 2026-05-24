# Fix patterns per OWASP class

## Injection (SQL / NoSQL / cmd / template / LDAP)
**Fix**: parameterized queries / prepared statements. Never string-format SQL.
```python
# ❌ cur.execute(f"SELECT * FROM users WHERE email = '{email}'")
# ✅
cur.execute("SELECT * FROM users WHERE email = %s", (email,))
```
For shell: use `subprocess.run([...], shell=False)` with a list. Never `shell=True` with user input.

## Broken authentication
**Fix (JWT)**: pin algorithm, verify issuer + audience + expiry, rotate signing keys.
```python
jwt.decode(token, key=PUB_KEY, algorithms=["RS256"],
           audience=AUD, issuer=ISS)   # rejects alg=none, HS256, expired
```
Add rate limit + account lockout on login + password reset + MFA.

## Broken access control (IDOR / BOLA)
**Fix**: every record fetch checks ownership server-side.
```python
record = db.get(record_id)
if record.owner_id != current_user.id and not current_user.is_admin:
    raise HTTPException(403)
```
Do not trust `?user_id=` from the client.

## XSS
**Fix**: output-encode by default (framework template auto-escape on). For raw HTML, use a sanitizer (DOMPurify / bleach). Set `Content-Security-Policy` with nonces.

## CSRF
**Fix**: SameSite=Lax (default for state-changing same-origin), CSRF token for cross-origin POST flows. Idempotent endpoints don't need CSRF.

## SSRF
**Fix**: allowlist hostnames the server may fetch; block RFC1918, link-local, and metadata IPs (169.254.169.254). Resolve hostname once and pass the IP to the HTTP client to prevent DNS rebinding.

## Mass assignment
**Fix**: explicit allow-list of fields per endpoint (Pydantic schema, DTO). Never `Object.assign(user, req.body)`.

## Secrets management
**Fix**: vault (HashiCorp Vault / AWS Secrets Manager / SOPS-encrypted file). Short-lived creds when possible. Rotation policy with deadline.

## Security headers (sane defaults)
```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-<RANDOM>'; object-src 'none'; base-uri 'self'
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

## File upload
- check magic bytes, not just extension
- size cap (server-side)
- store off-host (S3) with private ACL; serve via signed URL
- never serve back with original filename / mime
