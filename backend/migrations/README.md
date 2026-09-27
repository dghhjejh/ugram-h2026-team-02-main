# Database Migrations (Simple)

This project uses Alembic to manage database schema changes.

## Most Used Commands

```bash
task migrate                       # Apply all pending migrations
task migrate:create "message"      # Create a migration from model changes
task migrate:status                # Show current revision
task migrate:history               # Show migration history
task migrate:rollback              # Rollback one migration
```

## Daily Workflow

1. Update SQLAlchemy models.
2. Create migration:

```bash
task migrate:create "describe change"
```

3. Review generated file in `backend/migrations/versions/`.
4. Apply migration locally:

```bash
task migrate
```

5. Run tests, then commit model + migration file together.

## Team Rule

- Commit migration files to Git.
- Do not share local database files.
- After `git pull`, run:

```bash
task migrate
```

## Production

Before starting the backend in production:

```bash
cd backend
uv run alembic upgrade head
```

## Common Issues

- `Can't locate revision`: run `git pull` then `task migrate`.
- `Target database is not up to date`: run `task migrate`.
- `Multiple head revisions`: create a merge migration with Alembic.

## Notes

- Do not modify a migration that was already pushed and applied by teammates.
- If a pushed migration is wrong, create a new migration to fix it.
- Quick cheatsheet: see `backend/migrations/QUICKSTART.md`.
