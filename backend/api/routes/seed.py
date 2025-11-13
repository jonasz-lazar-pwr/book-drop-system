# === api/routes/seed.py ===

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db
from core.security import hash_password
from models import Locker, LockerBox, User
from models.enums import UserRole
from services.books_importer import import_books

router = APIRouter(tags=["Seed"])


@router.post(
    "/run",
    summary="Populate database with initial data",
    description="""
Creates test data for BookDrop system:
- 6 sample users (readers, librarians, couriers)
- 3 lockers, each with 10 boxes
""",
)
async def seed_database(db: AsyncSession = Depends(get_db)):
    users = [
        ("anna.kowalska@example.com", "reader123", UserRole.READER, "Anna", "Kowalska"),
        ("piotr.nowak@example.com", "reader123", UserRole.READER, "Piotr", "Nowak"),
        (
            "katarzyna.wisniewska@example.com",
            "librarian123",
            UserRole.LIBRARIAN,
            "Katarzyna",
            "Wiśniewska",
        ),
        (
            "tomasz.lewandowski@example.com",
            "librarian123",
            UserRole.LIBRARIAN,
            "Tomasz",
            "Lewandowski",
        ),
        ("adam.zielinski@example.com", "courier123", UserRole.COURIER, "Adam", "Zieliński"),
        ("magda.wrobel@example.com", "courier123", UserRole.COURIER, "Magdalena", "Wróbel"),
    ]

    for email, plain_pw, role, first, last in users:
        existing = await db.execute(select(User).where(User.email == email))
        if not existing.scalar():
            db.add(
                User(
                    email=email,
                    password=hash_password(plain_pw),
                    role=role,
                    first_name=first,
                    last_name=last,
                )
            )
    await db.commit()

    lockers_data = [
        (
            "WRO-PWR",
            "Wybrzeże Stanisława Wyspiańskiego 27",
            "Wrocław",
            "50-370",
            "SRID=4326;POINT(17.0615 51.1079)",
        ),
        ("WRO-RYN", "Rynek 1", "Wrocław", "50-438", "SRID=4326;POINT(17.0326 51.1101)"),
        (
            "WRO-DWR",
            "Józefa Piłsudskiego 105",
            "Wrocław",
            "50-046",
            "SRID=4326;POINT(17.0386 51.0980)",
        ),
    ]

    existing_lockers = (await db.execute(select(Locker))).scalars().all()
    if not existing_lockers:
        for code, street, city, postal, geo in lockers_data:
            db.add(
                Locker(
                    locker_code=code,
                    street=street,
                    city=city,
                    postal_code=postal,
                    location=geo,
                )
            )
        await db.flush()

        lockers = (await db.execute(select(Locker))).scalars().all()
        for locker in lockers:
            for i in range(1, 11):
                db.add(LockerBox(locker_id=locker.id, number=i, is_available=True))
        await db.commit()

    # Import books from Google Books
    topics = ["literatura", "nauka", "historia", "fantastyka", "biografia", "technologia"]
    count = await import_books(db, topics, limit_per_topic=40)

    return {
        "detail": "Database seeded successfully",
        "users_added": len(users),
        "lockers_created": 3,
        "boxes_per_locker": 10,
        "books_imported": count,
    }
