# === repositories/catalog_repository.py ===

from sqlalchemy import Integer, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, BookItem
from schemas.catalog import CatalogFilters


class CatalogRepository:
    """Encapsulates database operations for the book catalog."""

    @staticmethod
    def _apply_filters(stmt, filters: CatalogFilters):
        """Apply search and filter conditions to the query."""
        conditions = []

        if filters.search:
            search_term = f"%{filters.search.lower()}%"
            conditions.append(
                or_(
                    func.lower(Book.title).ilike(search_term),
                    func.lower(Book.authors).ilike(search_term),
                    func.lower(Book.isbn).ilike(search_term),
                )
            )

        if filters.publisher:
            conditions.append(Book.publisher == filters.publisher)
        if filters.available_only:
            conditions.append(BookItem.is_available.is_(True))
        if filters.year_from is not None:
            conditions.append(
                func.cast(func.substr(Book.published_date, 1, 4), Integer).isnot(None)
            )
            conditions.append(func.substr(Book.published_date, 1, 4).regexp_match("^[0-9]{4}$"))
            conditions.append(
                func.cast(func.substr(Book.published_date, 1, 4), Integer) >= filters.year_from
            )
        if filters.year_to is not None:
            conditions.append(
                func.cast(func.substr(Book.published_date, 1, 4), Integer).isnot(None)
            )
            conditions.append(func.substr(Book.published_date, 1, 4).regexp_match("^[0-9]{4}$"))
            conditions.append(
                func.cast(func.substr(Book.published_date, 1, 4), Integer) <= filters.year_to
            )
        if conditions:
            stmt = stmt.where(and_(*conditions))

        return stmt

    @staticmethod
    def _apply_sorting(stmt, sort: str | None):
        """Apply sorting rules to the query."""
        order_expr = {
            "title_asc": Book.title.asc(),
            "title_desc": Book.title.desc(),
            "author_asc": Book.authors.asc(),
            "date_newest": Book.published_date.desc().nullslast(),
            "date_oldest": Book.published_date.asc().nullslast(),
            "available_first": func.count(BookItem.id)
            .filter(BookItem.is_available.is_(True))
            .desc(),
        }.get(sort, Book.title.asc())

        return stmt.order_by(order_expr)

    @staticmethod
    async def list_books(
        db: AsyncSession,
        page: int = 1,
        limit: int = 15,
        filters: CatalogFilters | None = None,
    ):
        """Return paginated book list with filters and sorting."""
        stmt = (
            select(
                Book.isbn,
                Book.title,
                Book.authors,
                Book.publisher,
                Book.published_date,
                Book.thumbnail,
                func.count(BookItem.id)
                .filter(BookItem.is_available.is_(True))
                .label("available_count"),
            )
            .join(BookItem, Book.isbn == BookItem.isbn, isouter=True)
            .group_by(Book.isbn)
        )

        if filters:
            stmt = CatalogRepository._apply_filters(stmt, filters)
            stmt = CatalogRepository._apply_sorting(stmt, filters.sort)

        total_query = select(func.count(func.distinct(Book.isbn)))
        if filters:
            total_query = CatalogRepository._apply_filters(total_query, filters)
        total_result = await db.execute(total_query)
        total = total_result.scalar_one() or 0

        stmt = stmt.offset((page - 1) * limit).limit(limit)

        result = await db.execute(stmt)
        rows = result.mappings().all()

        return rows, total

    @staticmethod
    async def get_book(db: AsyncSession, isbn: str):
        """Return a single book with availability count."""
        stmt = (
            select(
                Book,
                func.count(BookItem.id)
                .filter(BookItem.is_available.is_(True))
                .label("available_count"),
            )
            .join(BookItem, Book.isbn == BookItem.isbn, isouter=True)
            .where(Book.isbn == isbn)
            .group_by(Book.isbn)
        )
        result = await db.execute(stmt)
        return result.mappings().first()

    @staticmethod
    async def list_publishers(db: AsyncSession):
        """Return a list of unique publishers."""
        stmt = (
            select(func.distinct(Book.publisher))
            .where(Book.publisher.isnot(None))
            .order_by(Book.publisher.asc())
        )
        result = await db.execute(stmt)
        return [row[0] for row in result.fetchall()]
