# === repositories/auth_repository.py ===

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password, verify_password
from models import User
from models.enums import UserRole


class AuthRepository:
    """Encapsulates user registration and authentication operations."""

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        """Return user by email if exists."""
        result = await db.execute(select(User).where(User.email == email.lower().strip()))
        return result.scalar_one_or_none()

    @staticmethod
    async def register_user(
        db: AsyncSession, email: str, password: str, first_name: str, last_name: str
    ) -> User:
        """Create a new user account."""
        existing = await AuthRepository.get_by_email(db, email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user = User(
            email=email.lower().strip(),
            password=hash_password(password),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            role=UserRole.READER,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
        """Validate user credentials and return user if valid."""
        user = await AuthRepository.get_by_email(db, email)
        if not user or not verify_password(password, str(user.password)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        return user
