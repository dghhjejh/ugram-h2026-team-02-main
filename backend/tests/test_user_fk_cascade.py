"""Schema guard tests for user foreign key delete behavior."""

from src.adapters.outbound.persistence.models import Base


def _iter_foreign_keys_to_users_id() -> list[tuple[str, str, str | None]]:
    """Collect all FKs that reference users.id from SQLAlchemy metadata."""
    results: list[tuple[str, str, str | None]] = []
    for table in Base.metadata.tables.values():
        for fk in table.foreign_keys:
            if fk.column.table.name == "users" and fk.column.name == "id":
                results.append((table.name, fk.parent.name, fk.ondelete))
    return results


def test_all_foreign_keys_to_users_id_use_ondelete_cascade() -> None:
    """Every FK targeting users.id must enforce ON DELETE CASCADE."""
    fk_refs = _iter_foreign_keys_to_users_id()
    assert fk_refs, "Expected at least one FK referencing users.id"

    missing_cascade = [
        f"{table_name}.{column_name}"
        for table_name, column_name, ondelete in fk_refs
        if (ondelete or "").upper() != "CASCADE"
    ]

    assert not missing_cascade, "Found FK(s) to users.id without ON DELETE CASCADE: " + ", ".join(
        sorted(missing_cascade)
    )
