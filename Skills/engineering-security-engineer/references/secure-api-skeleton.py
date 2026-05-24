"""FastAPI skeleton with the boring-but-required security primitives.

What this enforces:
- Bearer auth via dependency (fails before handler runs)
- Strict input validation via Pydantic
- Rate limit per IP
- JWT decoded with pinned alg + iss + aud
- No /docs in prod
- Audit log on the server, never to the client
"""

import re
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
import jwt
import logging


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
bearer = HTTPBearer()
limiter = Limiter(key_func=get_remote_address)
audit = logging.getLogger("audit")


class UserInput(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email:    str = Field(..., max_length=254)

    @field_validator("username")
    @classmethod
    def _u(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username contains invalid characters")
        return v


def verify_token(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        return jwt.decode(
            creds.credentials,
            key=settings.JWT_PUBLIC_KEY,
            algorithms=["RS256"],          # pinned — rejects alg=none, HS256
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",   # generic; do not say why
        )


@app.post("/api/users", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_user(
    request: Request,
    user: UserInput,
    auth: dict = Depends(verify_token),
):
    audit.info("user_created actor=%s target=%s", auth["sub"], user.username)
    return {"status": "created", "username": user.username}
