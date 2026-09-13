"""
FastAPI dependency injection — auth, DB session, role checks
"""
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database.session import get_db_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Decode JWT and return the currently authenticated user.
    Raises HTTP 401 if token is missing, invalid, or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: Optional[str] = payload.get("sub")
        token_type: Optional[str] = payload.get("type")

        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Import here to avoid circular imports
    from app.models.user import User
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )
    return user


async def get_current_active_user(current_user=Depends(get_current_user)):
    """Alias that ensures user is active (already checked in get_current_user)."""
    return current_user


def require_roles(*roles: str):
    """
    Factory function returning a dependency that enforces role-based access.

    Usage:
        @router.post("/", dependencies=[Depends(require_roles("ADMIN", "INSPECTOR"))])
    """
    async def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of: {', '.join(roles)}",
            )
        return current_user
    return role_checker


# Convenience role dependencies
require_admin = require_roles("ADMIN")
require_inspector_or_above = require_roles("ADMIN", "INSPECTOR")
require_any_role = require_roles("ADMIN", "INSPECTOR", "VIEWER")
