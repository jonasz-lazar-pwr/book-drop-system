# === core/verify_models.py ===

import asyncio
import logging

from typing import Any

from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from core.session import engine
from models import Base

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bookdrop.dbcheck")


def _normalize_type(type_str: str) -> str:
    """Normalize SQL type names for reliable comparison."""
    return (
        type_str.replace("timestamp with time zone", "timestamptz")
        .replace("character varying", "varchar")
        .lower()
    )


def _check_columns(inspector, table_name: str, orm_table) -> None:
    """Compare ORM and database columns for a given table."""
    db_columns = {col["name"]: col for col in inspector.get_columns(table_name, schema="public")}

    for col_name, orm_col in orm_table.columns.items():
        if col_name not in db_columns:
            logger.error("%sColumn %s missing in DB.%s", RED, col_name, RESET)
            continue

        db_col = db_columns[col_name]
        orm_type = _normalize_type(str(orm_col.type))
        db_type = _normalize_type(str(db_col["type"]))

        if orm_type != db_type:
            logger.warning(
                "%sType mismatch:%s %s ORM=%s DB=%s", YELLOW, RESET, col_name, orm_type, db_type
            )

        if orm_col.nullable != db_col["nullable"]:
            logger.warning(
                "%sNullability differs:%s %s ORM.nullable=%s DB.nullable=%s",
                YELLOW,
                RESET,
                col_name,
                orm_col.nullable,
                db_col["nullable"],
            )

    extra_cols = set(db_columns.keys()) - set(orm_table.columns.keys())
    if extra_cols:
        logger.warning("%sExtra columns in DB:%s %s", YELLOW, RESET, extra_cols)
    else:
        logger.info("%s✔ Columns match.%s", GREEN, RESET)


def _check_constraints(inspector, table_name: str, orm_table) -> None:
    """Validate primary keys, indexes, and foreign keys."""
    pk_db = inspector.get_pk_constraint(table_name)["constrained_columns"]
    pk_orm = [c.name for c in orm_table.primary_key.columns]
    if set(pk_db) != set(pk_orm):
        logger.warning("%sPK mismatch:%s ORM=%s DB=%s", YELLOW, RESET, pk_orm, pk_db)
    else:
        logger.info("%s✔ Primary key consistent.%s", GREEN, RESET)

    db_indexes = {idx["name"]: idx for idx in inspector.get_indexes(table_name)}
    orm_indexes = {idx.name for idx in orm_table.indexes if idx.name}
    missing_indexes = orm_indexes - set(db_indexes.keys())
    if missing_indexes:
        logger.warning("%sIndexes missing in DB:%s %s", YELLOW, RESET, missing_indexes)
    else:
        logger.info("%s✔ All ORM indexes exist.%s", GREEN, RESET)

    db_fks = inspector.get_foreign_keys(table_name)
    logger.info("%s✔ Found %d FK(s).%s", GREEN, len(db_fks), RESET)


async def verify_orm_vs_db() -> None:
    """Run full verification of ORM models against the database schema."""
    try:
        async with engine.begin() as conn:
            logger.info("Connected to database. Starting schema verification...")

            def sync_check(sync_conn: Any):
                inspector = inspect(sync_conn)
                db_tables = set(inspector.get_table_names(schema="public"))
                orm_tables = set(Base.metadata.tables.keys())

                logger.info("%s[1] Checking table sets...%s", YELLOW, RESET)

                missing_in_db = orm_tables - db_tables
                missing_in_orm = db_tables - orm_tables

                if missing_in_db:
                    logger.warning("%sMissing in DB:%s %s", RED, RESET, sorted(missing_in_db))
                else:
                    logger.info("%s✔ All ORM tables exist.%s", GREEN, RESET)

                if missing_in_orm:
                    logger.warning(
                        "%sExtra tables in DB:%s %s", YELLOW, RESET, sorted(missing_in_orm)
                    )
                else:
                    logger.info("%s✔ No extra DB tables.%s", GREEN, RESET)

                for table_name in sorted(orm_tables & db_tables):
                    orm_table = Base.metadata.tables[table_name]
                    logger.info("\n--- Inspecting table: %s ---", table_name)
                    _check_columns(inspector, table_name, orm_table)
                    _check_constraints(inspector, table_name, orm_table)

                logger.info("%s✅ Verification completed.%s", GREEN, RESET)

            await conn.run_sync(sync_check)

    except SQLAlchemyError as e:
        logger.error("%sDatabase verification failed:%s %s", RED, RESET, e)


if __name__ == "__main__":
    asyncio.run(verify_orm_vs_db())
