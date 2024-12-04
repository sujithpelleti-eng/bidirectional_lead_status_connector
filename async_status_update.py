import logging
from datetime import datetime
from typing import Dict, List

import requests

from common.models import StatusUpdateQueue
from common.postgres_connector import PostgresDatabase

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StatusUpdatePoster:
    def __init__(
        self, db: PostgresDatabase, config: Dict[str, str], post_threshold: int = 10
    ):
        """
        Initialize the StatusUpdatePoster.

        :param db: Database connection instance.
        :param config: Dictionary containing API configuration.
        :param post_threshold: Maximum number of attempts before marking a record as failed.
        """
        self.db = db
        self.post_threshold = post_threshold
        self.api_config = config
        self.api_url = config.get("api_url")
        self.headers = {
            "Caring-Partner": config.get("api_token")
        }  # Use token from config

        if not self.api_url or not self.headers.get("Caring-Partner"):
            raise ValueError(
                "API URL and API token must be provided in the configuration."
            )

    def fetch_records(self) -> List[StatusUpdateQueue]:
        """
        Fetch records from the status_update_queue table that need to be posted.

        :return: List of StatusUpdateQueue records.
        """
        query = """
            SELECT * FROM provider_integration.status_update_queue
            WHERE attempts < %s AND is_delivered = FALSE AND attempts < {self.post_threshold}
        """
        records = self.db.query(query, (self.post_threshold,))
        return [StatusUpdateQueue(**record) for record in records]

    def post_status_update(self, record: StatusUpdateQueue) -> bool:
        """
        Post a status update to the API.

        :param record: StatusUpdateQueue record to post.
        :return: True if the post was successful, False otherwise.
        """
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={
                    "lead_id": record.lead_id,
                    "status": record.status,
                    "sub_status": record.sub_status,
                    "notes": record.notes,
                },
            )
            response_data = response.json()
            if response.status_code == 200:
                logger.info(
                    f"Successfully posted record {record.lead_id}: {response_data}"
                )
                return True
            else:
                logger.error(f"Failed to post record {record.lead_id}: {response_data}")
                return False
        except Exception as e:
            logger.error(f"Error posting record {record.lead_id}: {e}")
            return False

    def update_record(
        self, record: StatusUpdateQueue, success: bool, error_message: str = None
    ):
        """
        Update the database record after an attempt.

        :param record: StatusUpdateQueue record.
        :param success: Whether the post was successful.
        :param error_message: Error message in case of failure.
        """
        query = """
            UPDATE provider_integration.status_update_queue
            SET attempts = %s, last_attempt = %s, is_delivered = %s, updated_at = %s, notes = COALESCE(%s, notes)
            WHERE status_update_id = %s
        """
        self.db.execute(
            query,
            (
                record.attempts + 1,
                datetime.now(),
                success,
                datetime.now(),
                error_message,
                record.status_update_id,
            ),
        )

    def process_updates(self):
        """
        Process and post status updates.
        """
        records = self.fetch_records()
        logger.info(f"Fetched {len(records)} records to post.")

        for record in records:
            success = self.post_status_update(record)
            error_message = None if success else "Failed to post after maximum retries."
            self.update_record(record, success, error_message)
