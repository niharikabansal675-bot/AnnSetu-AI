from __future__ import annotations

import argparse
import os
import time
from sqlalchemy import select, text

from app.database import SessionLocal, engine
from app.models import User
from app.routers.coordinator import run_coordinator
from app.agents.T3.scheduler import cycle_demo_donations

LOCK_KEY = 714231904  # scoped to this application in the configured PostgreSQL database


def configured_mode() -> str:
    mode = os.getenv('T3_COORDINATOR_MODE', 'legacy').strip().lower()
    if mode not in {'legacy', 'preview', 'demo'}:
        raise RuntimeError('T3_COORDINATOR_MODE must be legacy, preview or demo')
    if mode == 'demo' and os.getenv('T3_DEMO_EXECUTION_ENABLED', 'false').lower() != 'true':
        raise RuntimeError('Demo execution is disabled; refusing to create offers')
    return mode


def cycle(mode: str) -> dict:
    if mode == 'legacy':
        with SessionLocal() as db:
            admin = db.scalar(select(User).where(User.role == 'admin'))
            if admin is None:
                return {'status': 'skipped', 'reason': 'No admin account'}
            return run_coordinator(user=admin, db=db)
    with SessionLocal() as db:
        return cycle_demo_donations(db, write=(mode == 'demo'), limit=25)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--interval', type=int, default=30)
    args = parser.parse_args()
    mode = configured_mode()
    if engine.dialect.name != 'postgresql':
        raise RuntimeError('Automated worker requires PostgreSQL advisory locking')

    # Hold the advisory lock on a dedicated connection across all polling cycles.
    # This lock is session-scoped and released in finally even on failure.
    with engine.connect() as connection:
        got_lock = connection.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key': LOCK_KEY})
        connection.commit()
        if not got_lock:
            raise RuntimeError('Another AnnSetu coordinator worker is running; stop it first')
        try:
            print(f'AnnSetu coordinator mode: {mode}', flush=True)
            while True:
                try:
                    print('Coordinator cycle:', cycle(mode), flush=True)
                except Exception as exc:
                    print(f'Coordinator error: {type(exc).__name__}: {exc}', flush=True)
                if args.once:
                    break
                time.sleep(max(10, args.interval))
        finally:
            connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': LOCK_KEY})
            connection.commit()


if __name__ == '__main__':
    main()
