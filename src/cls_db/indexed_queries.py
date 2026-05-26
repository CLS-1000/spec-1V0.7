"""Indexed query helpers for cls_db.

Provides a thin, composable query layer on top of :class:`cls_db.repository.Repository`
that always enforces ``LIMIT`` so callers can't accidentally run unbounded scans
against large SQLite tables.

Typical usage::

    from cls_db.database import Database
    from cls_db.migrate import ensure_schema
    from cls_db.repository import Repository
    from cls_db.indexed_queries import IndexedQueryLayer

    db = Database("spec1.db")
    ensure_schema(db)
    repo = Repository(db, "leads", pk_field="lead_id")
    q = IndexedQueryLayer(repo)

    recent = q.latest(20)
    high   = q.by_field("priority", "HIGH", limit=50)
    page   = q.page(limit=25, offset=50)
"""

from __future__ import annotations

import re
from typing import Any, Optional

from cls_db.repository import Repository


_DEFAULT_LIMIT = 100

# Strict identifier pattern: letters, digits, and underscores only; must start
# with a letter or underscore.  Used to prevent SQL injection when column names
# or sort columns are interpolated into raw SQL.
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_VALID_DIRECTIONS = frozenset({"ASC", "DESC"})


class IndexedQueryLayer:
    """Composable, limit-enforced query layer over a :class:`Repository`.

    All methods accept an explicit ``limit`` argument and default to
    :data:`_DEFAULT_LIMIT` when none is provided.  This prevents unbounded
    table scans and keeps latency predictable.

    Parameters
    ----------
    repo:
        The underlying repository to query.
    default_limit:
        Cap applied when callers omit ``limit``.  Defaults to 100.
    """

    def __init__(self, repo: Repository, default_limit: int = _DEFAULT_LIMIT) -> None:
        self.repo = repo
        self.default_limit = default_limit

    # ------------------------------------------------------------------
    # Core queries
    # ------------------------------------------------------------------

    def latest(self, limit: Optional[int] = None) -> list[dict]:
        """Return the most recently inserted records (by rowid)."""
        n = limit if limit is not None else self.default_limit
        return self.repo.latest(n)

    def by_field(
        self,
        field: str,
        value: Any,
        limit: Optional[int] = None,
    ) -> list[dict]:
        """Return records where ``field = value``, up to ``limit`` rows."""
        n = limit if limit is not None else self.default_limit
        return self.repo.filter(field, value, limit=n)

    def page(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> list[dict]:
        """Return a page of records ordered by insertion order (rowid).

        Parameters
        ----------
        limit:
            Page size.  Defaults to ``self.default_limit``.
        offset:
            Number of records to skip before returning results.
        """
        n = limit if limit is not None else self.default_limit
        return self.repo.all(limit=n, offset=offset)

    def get(self, pk_value: str) -> Optional[dict]:
        """Fetch a single record by primary key; returns ``None`` on miss."""
        return self.repo.get(pk_value)

    def count(self) -> int:
        """Return the total number of records in the table."""
        return self.repo.count()

    # ------------------------------------------------------------------
    # Multi-field helpers
    # ------------------------------------------------------------------

    def by_fields(
        self,
        filters: dict[str, Any],
        limit: Optional[int] = None,
        order_by: str = "rowid",
        order_dir: str = "ASC",
    ) -> list[dict]:
        """Filter by multiple ``field = value`` pairs (AND-combined).

        This builds a parameterised query from *filters* and delegates
        directly to the underlying :class:`~cls_db.database.Database`.
        The result is always capped at ``limit`` rows.

        Parameters
        ----------
        filters:
            Mapping of column name → expected value.
        limit:
            Maximum rows to return.
        order_by:
            Column to sort by.  Defaults to ``rowid`` (insertion order).
            Must match ``^[A-Za-z_][A-Za-z0-9_]*$`` to prevent SQL injection.
        order_dir:
            ``"ASC"`` or ``"DESC"``.

        Raises
        ------
        ValueError
            If any column name in *filters* or *order_by* contains invalid
            characters, or if *order_dir* is not ``"ASC"`` or ``"DESC"``.
        """
        # Validate order_dir before any SQL is built.
        order_dir_upper = order_dir.upper()
        if order_dir_upper not in _VALID_DIRECTIONS:
            raise ValueError(
                f"order_dir must be 'ASC' or 'DESC', got {order_dir!r}"
            )

        # Validate order_by column identifier.
        if not _IDENT_RE.match(order_by):
            raise ValueError(
                f"order_by contains invalid identifier: {order_by!r}"
            )

        if not filters:
            return self.page(limit=limit)

        # Validate every filter column name.
        for col in filters:
            if not _IDENT_RE.match(col):
                raise ValueError(
                    f"Filter column contains invalid identifier: {col!r}"
                )

        n = limit if limit is not None else self.default_limit
        where_clauses = [f"{col} = ?" for col in filters]
        params: list[Any] = list(filters.values())
        sql = (
            f"SELECT * FROM {self.repo.table}"
            f" WHERE {' AND '.join(where_clauses)}"
            f" ORDER BY {order_by} {order_dir_upper}"
            f" LIMIT ?"
        )
        params.append(n)
        rows = self.repo.db.fetchall(sql, tuple(params))
        # Re-use Repository's deserialisation helper
        from cls_db.repository import _row_to_dict
        return [_row_to_dict(r) for r in rows]
