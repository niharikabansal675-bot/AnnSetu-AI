"""Run the bounded Food Rescue coordination cycle on a polling schedule.

Use one worker process only. For the prototype, run alongside Uvicorn:
    python agent_worker.py --interval 30
Or run once for screenshots: python agent_worker.py --once

The worker invokes existing backend-enforced eligibility and writes the audit log.
"""
import argparse
import time
from sqlalchemy import select
from main import SessionLocal, User, run_coordinator


def cycle():
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.role == 'admin'))
        if admin is None:
            print('No admin yet; run create_admin.py before starting the coordinator.', flush=True)
            return
        result = run_coordinator(user=admin, db=db)
        print('Coordinator:', result, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--interval', type=int, default=30)
    args = parser.parse_args()
    while True:
        try:
            cycle()
        except Exception as exc:
            print(f'Coordinator error: {type(exc).__name__}: {exc}', flush=True)
        if args.once:
            break
        time.sleep(max(10, args.interval))
