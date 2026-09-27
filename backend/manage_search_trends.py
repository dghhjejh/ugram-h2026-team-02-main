"""Search trend worker management.

Processes queued search events into daily aggregates.
"""

import argparse
import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from src.adapters.outbound.persistence.database import SessionLocal, engine
from src.adapters.outbound.persistence.sqlalchemy_image_repository import SQLAlchemyImageRepository
from src.adapters.outbound.time_provider import SystemTimeProvider
from src.domain.images.services import ImageService

logger = logging.getLogger(__name__)
WORKER_LOCK_KEY = 2_026_032_201


@contextmanager
def advisory_worker_lock() -> Iterator[bool]:
    """Ensure only one trend worker stays active per Postgres database."""
    if engine.dialect.name != "postgresql":
        logger.info("Running search trend worker without advisory lock for dialect=%s", engine.dialect.name)
        yield True
        return

    connection = engine.connect()
    acquired = bool(connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": WORKER_LOCK_KEY}).scalar())
    if not acquired:
        connection.close()
        yield False
        return

    try:
        logger.info("Acquired search trend worker advisory lock")
        yield True
    finally:
        connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": WORKER_LOCK_KEY})
        connection.close()


def process_once(batch_size: int) -> int:
    """Process one batch of pending search events."""
    with SessionLocal() as session:
        service = ImageService(SQLAlchemyImageRepository(session), SystemTimeProvider())
        processed = service.process_pending_search_events(batch_size=batch_size)
        session.commit()
        return processed


def run_worker(batch_size: int, poll_interval: float) -> None:
    """Continuously process queued search events."""
    with advisory_worker_lock() as acquired:
        if not acquired:
            logger.warning("Another search trend worker is already running; exiting.")
            return

        logger.info("Starting search trend worker with batch_size=%s poll_interval=%ss", batch_size, poll_interval)
        while True:
            processed = process_once(batch_size=batch_size)
            if processed:
                logger.info("Processed %s search events", processed)
                continue
            time.sleep(poll_interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process queued search events into daily trend aggregates.")
    parser.add_argument("command", choices=["process-once", "worker"])
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--poll-interval", type=float, default=2.0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    if args.command == "process-once":
        processed = process_once(batch_size=args.batch_size)
        logger.info("Processed %s search events", processed)
        return

    run_worker(batch_size=args.batch_size, poll_interval=args.poll_interval)


if __name__ == "__main__":
    main()
