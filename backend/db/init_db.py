# === db/init_db.py ===

# """
# Database initialization script.
#
# This script creates all database tables based on the SQLAlchemy ORM models.
# It connects to the database using the async engine and runs the schema creation
# within an async context.
#
# Usage:
#     Run the script directly to initialize the database schema:
#
#     $ python api/db/init_db.py
# """
#
# import asyncio
# from api.db.session import engine
# from api.models.base import Base
# from api.models.user import User
# from api.models.chat import Chat
# from api.models import user, chat, message
#
# async def init_db():
#     """
#     Initializes the database schema.
#
#     This function connects to the database and creates all tables
#     defined in the SQLAlchemy models (Base metadata).
#     """
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#
# if __name__ == "__main__":
#     # Run the async init function using asyncio
#     asyncio.run(init_db())
