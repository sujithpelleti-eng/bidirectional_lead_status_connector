import argparse
import os
import sys
import logging
from datetime import datetime, timedelta
from orchestrator import Orchestrator
from async_status_update import StatusUpdatePoster
from common.postgres_connector import PostgresDatabase
from common.utils import fetch_api_config

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    """
    Main function to control the flow based on command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Run the Orchestrator or Status Update Poster.")
    parser.add_argument(
        "--action",
        type=str,
        required=True,
        choices=["orchestrator", "post_status_updates"],
        help="Action to perform: orchestrator or post_status_updates",
    )
    parser.add_argument("--schedule", type=str, help="Schedule filter for configurations.")
    parser.add_argument("--system", type=str, help="System filter for configurations.")
    parser.add_argument("--partner_id", type=str, help="Partner_id filter for configurations.")
    # parser.add_argument("--post_threshold", type=int, default=10, help="Max retry attempts for posting status updates.")
    parser.add_argument("--from-date", type=str, help="Start date for data fetch (YYYY-MM-DD).")
    parser.add_argument("--to-date", type=str, help="End date for data fetch (YYYY-MM-DD).")
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Fetch data for the last year if no dates are provided.",
    )


    args = parser.parse_args()

    # Calculate dates if not provided
    from_date, to_date = None, None
    if args.full_refresh:
        from_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%dT00:00:00")
        to_date = datetime.now().strftime("%Y-%m-%dT00:00:00")
        logger.info(f"Full refresh selected: Fetching data from {from_date} to {to_date}")
    elif args.from_date and args.to_date:
        from_date = args.from_date
        to_date = args.to_date
        logger.info(f"Custom date range: Fetching data from {from_date} to {to_date}")
    else:
        from_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
        to_date = datetime.now().strftime("%Y-%m-%dT00:00:00")
        logger.info(f"Incremental fetch: Fetching data from {from_date} to {to_date}")


    # Initialize the database connection
    db = PostgresDatabase(
        database=os.getenv("RDS_DB_NAME"),
        endpoint=os.getenv("RDS_DB_HOST"),
        port=os.getenv("RDS_DB_PORT"),
        user=os.getenv("RDS_DB_USER"),
        password=os.getenv("RDS_DB_PASSWORD"),
    )

    if args.action == "orchestrator":
        # Run the Orchestrator
        orchestrator = Orchestrator(
            schedule=args.schedule,
            system=args.system,
            partner_id=args.partner_id,
            from_date=from_date,
            to_date=to_date,
        )
        orchestrator.run()
    elif args.action == "post_status_updates":
        # Fetch the API configuration dynamically
        api_config = fetch_api_config(db, system=args.system, partner=args.partner)
        if not api_config:
            logger.error("No API configuration found for the specified parameters.")
            sys.exit(1)

        # Run the Status Update Poster
        poster = StatusUpdatePoster(db, config=api_config, post_threshold=args.post_threshold)
        poster.process_updates()


if __name__ == "__main__":
    main()
