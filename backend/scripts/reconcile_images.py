"""Inspect local media; optional offline orphan cleanup/interrupted-state recovery."""

import argparse
import json

from app.core.database import SessionLocal
from app.services.image_library import get_image_storage
from app.services.image_maintenance import reconcile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Delete old unreferenced image files")
    parser.add_argument("--offline", action="store_true", help="Confirm all API and image diagnostics are stopped")
    parser.add_argument("--min-age-hours", type=float, default=24)
    parser.add_argument("--mark-unknown", type=int, help="Mark one old generating request outcome_unknown; never retry")
    args = parser.parse_args()
    try:
        with SessionLocal() as db:
            report = reconcile(db, get_image_storage(), apply=args.apply, offline=args.offline,
                               min_age_hours=args.min_age_hours, mark_unknown_id=args.mark_unknown)
        print(json.dumps(report, indent=2))
        return 0
    except ValueError as exc:
        print(str(exc))
        return 1
    except Exception:
        print("Image maintenance stopped; check database/storage availability. No provider calls were made.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
