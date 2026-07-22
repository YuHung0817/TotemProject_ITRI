import argparse
import json

from app.db.session import SessionLocal
from app.services.cleanup_service import cleanup_expired_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete expired Totem data and image files")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete expired data; without this flag the command is a dry run",
    )
    args = parser.parse_args()
    with SessionLocal() as db:
        report = cleanup_expired_data(db, dry_run=not args.execute)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
