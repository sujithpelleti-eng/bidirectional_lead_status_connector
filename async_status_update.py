import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import requests

from common.models import StatusUpdateQueue
from common.postgres_connector import PostgresDatabase
from common.utils import fetch_query_results, update_status_update_record

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StatusUpdatePoster:
    def __init__(self, db: PostgresDatabase, post_threshold: int = 10):
        """
        Initialize the StatusUpdatePoster.

        :param db: Database connection instance.
        :param config: Dictionary containing API configuration.
        :param post_threshold: Maximum number of attempts before marking a record as failed.
        """
        self.db = db
        self.post_threshold = post_threshold
        self.api_url = os.getenv("API_URL")
        self.headers = {
            "Caring-Partner": os.getenv("API_TOKEN")
        }  # Use token from env variables

        if not self.api_url or not self.headers.get("Caring-Partner"):
            raise ValueError(
                "API URL and API token must be provided in the configuration."
            )

    def fetch_records(self) -> List[StatusUpdateQueue]:
        """
        Fetch the latest records for each lead, avoiding duplicate deliveries of the same status.
        - Excludes records if the status and sub_status match the most recently delivered record.

        :return: List of StatusUpdateQueue records.
        """
        query = """
            WITH latest_delivered_status AS (
                SELECT lead_id, status, sub_status, MAX(updated_at) AS last_delivered_at
                FROM provider_integration.status_update_queue
                WHERE is_delivered = TRUE
                GROUP BY lead_id, status, sub_status
            ),
            ranked_records AS (
                SELECT suq.*, 
                    ROW_NUMBER() OVER (
                        PARTITION BY suq.lead_id
                        ORDER BY suq.updated_at DESC, suq.last_attempt DESC
                    ) AS rank
                FROM provider_integration.status_update_queue suq
                LEFT JOIN latest_delivered_status lds
                ON suq.lead_id = lds.lead_id 
                AND suq.status = lds.status
                AND suq.sub_status = lds.sub_status
                WHERE suq.is_delivered = FALSE 
                AND suq.attempts < %s 
                AND (lds.last_delivered_at IS NULL OR suq.updated_at > lds.last_delivered_at)
            )
            SELECT 
                status_update_id, execution_id, system_config_id, lead_id, 
                status, sub_status, notes, lead_json, community_code,
                attempts, last_attempt, is_delivered, updated_at 
            FROM ranked_records
            WHERE rank = 1;
        """
        # Fetch records from the database
        raw_records = fetch_query_results(self.db, query, (self.post_threshold,))

        # Convert raw records to StatusUpdateQueue objects
        return [StatusUpdateQueue(**record) for record in raw_records]

    def post_status_update(self, record: StatusUpdateQueue) -> Dict[str, Any]:
        """
        Post a status update to the API.

        :param record: StatusUpdateQueue record to post.
        :return: Dictionary containing the success status and an error message if any.
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
                return {"success": True, "error_message": None}
            else:
                error_message = response_data.get("error", "Unknown error from API")
                logger.error(f"Failed to post record {record.lead_id}: {error_message}")
                return {"success": False, "error_message": error_message}
        except Exception as e:
            logger.error(f"Error posting record {record.lead_id}: {e}")
            return {"success": False, "error_message": str(e)}

    # def update_record(
    #     self, record: StatusUpdateQueue, success: bool, error_message: str = None
    # ):
    #     """
    #     Update the database record after an attempt.

    #     :param record: StatusUpdateQueue record.
    #     :param success: Whether the post was successful.
    #     :param error_message: Error message in case of failure.
    #     """
    #     query = """
    #         UPDATE provider_integration.status_update_queue
    #         SET attempts = %s, last_attempt = %s, is_delivered = %s, updated_at = %s, notes = COALESCE(%s, notes)
    #         WHERE status_update_id = %s
    #     """
    #     self.db.execute(
    #         query,
    #         (
    #             record.attempts + 1,
    #             datetime.now(),
    #             success,
    #             datetime.now(),
    #             error_message,
    #             record.status_update_id,
    #         ),
    #     )

    def process_updates(self):
        """
        Process and post status updates.
        """
        records = self.fetch_records()
        if not records:
            logger.info("No records to process.")
            return

        logger.info(f"Fetched {len(records)} records to post.")

        for record in records:
            logger.info(f"Processing record {record.lead_id} at {datetime.now()}")
            result = self.post_status_update(record)
            success = result["success"]
            error_message = result["error_message"]
            print(result, success, error_message)
            update_status_update_record(
                db=self.db,  # Pass the database connection
                record=record,
                success=success,
                error_message=error_message,
            )
