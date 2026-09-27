"""Database migration management script.

This script provides convenient commands for managing Alembic database migrations.
Run this instead of calling alembic directly for better integration with application settings.
"""

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config


def get_alembic_config() -> Config:
    """Get Alembic configuration."""
    # Alembic config file is in backend directory
    backend_dir = Path(__file__).parent
    alembic_ini = backend_dir / "alembic.ini"

    config = Config(str(alembic_ini))
    # Set the script location relative to backend directory
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    return config


def upgrade(revision: str = "head") -> None:
    """Apply migrations up to the specified revision."""
    config = get_alembic_config()
    command.upgrade(config, revision)


def current() -> None:
    """Show current database revision."""
    config = get_alembic_config()
    command.current(config, verbose=True)


def history() -> None:
    """Show migration history."""
    config = get_alembic_config()
    command.history(config, verbose=True)


def create(message: str, autogenerate: bool = True) -> None:
    """Create a new migration."""
    config = get_alembic_config()
    command.revision(config, message=message, autogenerate=autogenerate)


def main() -> None:
    """Main entry point for migration management."""
    if len(sys.argv) < 2:
        print("Usage: python manage_migrations.py [command] [args]")
        print("\nCommands:")
        print("  create <message>   - Create a new migration from model changes")
        print("  upgrade            - Apply migrations to head")
        print("  current            - Show current revision")
        print("  history            - Show migration history")
        sys.exit(1)

    command_name = sys.argv[1]

    try:
        if command_name == "upgrade":
            upgrade()
        elif command_name == "current":
            current()
        elif command_name == "history":
            history()
        elif command_name == "create":
            if len(sys.argv) < 3:
                print("Error: Migration message required")
                sys.exit(1)
            message = sys.argv[2]
            create(message)
        else:
            print(f"Unknown command: {command_name}")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
