from datetime import UTC, datetime


def utcnow() -> datetime:
    """Python-side default/onupdate for timestamp columns.

    A server-side onupdate=func.now() requires re-fetching the generated value
    from the DB after flush, which the async driver can't do implicitly — this
    callable makes the new value available on the ORM object immediately.
    """
    return datetime.now(UTC)
