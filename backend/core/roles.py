# === core/role.py ===

from fastapi import Depends, HTTPException

from core.deps import get_current_user
from models import User


def require_role(required: str):
    async def checker(user: User = Depends(get_current_user)):
        if user.role != required:
            raise HTTPException(
                status_code=403, detail=f"Only {required}s can access this endpoint."
            )
        return user

    return checker
