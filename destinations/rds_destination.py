import os
import json
import logging
from dataclasses import asdict, is_dataclass
from typing import List, Dict, Any
from datetime import datetime

from common.models import StatusUpdateQueue
from common.postgres_connector import PostgresDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class RDSDestination:
    """
    Class to handle data insertion into an RDS PostgreSQL database table.
    """

    def __init__(self, db: PostgresDatabase, table_name: str):
        """
        Initialize RDSDestination with a PostgreSQL database connection and target table.
        :param db: Instance of PostgresDatabase for database connection
        :param table_name: Name of the target database table
        """
        self._db = db
        self._table_name = table_name

    def _convert_data_for_insert(self, data: List[StatusUpdateQueue]) -> List[Dict[str, Any]]:
        """
        Convert a list of StatusUpdateQueue dataclass instances to a list of dictionaries.
        :param data: List of StatusUpdateQueue instances
        :return: List of dictionaries ready for insertion
        """
        data_dicts = []
        for item in data:
            if is_dataclass(item):
                item_dict = asdict(item)
                # Ensure datetime fields are serialized as strings
                if isinstance(item_dict.get("last_attempt"), datetime):
                    item_dict["last_attempt"] = item_dict["last_attempt"].isoformat()
                data_dicts.append(item_dict)
            else:
                data_dicts.append(item)  # Already a dictionary
        return data_dicts

    def send(self, data: List[Dict[str, Any]]) -> None:
        """
        Public method to insert data into the target table. Delegates to send_bulk for batch insertion.
        :param data: List of data dictionaries to insert
        """
        if not data:
            logger.warning("No data provided to insert.")
            return
        
        # Filter out records with null 'lead_id'
        filtered_data = [item for item in data if item.lead_id not in [None, ""]]

        if not filtered_data:
            logger.warning("No data to insert after filtering out records with null 'lead_id'.")
            return

        # Convert dataclass instances to dictionaries if needed
        data_dicts = self._convert_data_for_insert(data)
        logger.info("Preparing to insert data into RDS.")
        self._send_bulk(data_dicts)

    def _send_bulk(self, data: List[Dict[str, Any]]) -> None:
        """
        Private method to perform bulk insert into the database table.
        Uses a transaction to ensure atomicity.
        :param data: List of data dictionaries to insert
        """
        if not data:
            logger.warning("No data to insert in bulk.")
            return
        
        # Serialize the 'lead_json' field to JSON string if it exists
        for record in data:
            if 'lead_json' in record:
                record['lead_json'] = json.dumps(record['lead_json'])  # Convert dict to JSON string

        # SQL for bulk insert
        insert_query = f"""
            INSERT INTO {self._table_name} 
            (execution_id, system_config_id, lead_id, status, sub_status, notes, lead_json, attempts, last_attempt, is_delivered)
            VALUES (%(execution_id)s, %(system_config_id)s, %(lead_id)s, %(status)s, %(sub_status)s, %(notes)s, %(lead_json)s, %(attempts)s, %(last_attempt)s, %(is_delivered)s)
        """
        
        try:
            with self._db._engine.begin() as connection:
                logger.info(f"Inserting {len(data)} records into {self._table_name}.")
                connection.execute(insert_query, data)
            logger.info("Bulk insert completed successfully.")
        except Exception as e:
            logger.error(f"Error during bulk insert: {e}")
            raise


if __name__ == "__main__":
    # Example data structure matching the schema, to test insertion functionality
    sample_data = [
        StatusUpdateQueue(
            system_config_id=1,
            lead_id="1234",
            status="valid_lead",
            sub_status="timeframe_30",
            notes="Customer may move within 30 days.",
            lead_json={'lead_id': '28955', 'status': 'tour_completed', 'sub_status': '', 'notes': 'Tour completed on 10/21/2024 12:00:00 AM'},
            attempts=0,
            last_attempt=datetime.now(),
            is_delivered=False
        ),
        # Add more records as needed
    ]

    # Initialize PostgreSQL connection
    db = PostgresDatabase(
        database=os.getenv("RDS_DB_NAME"),
        endpoint=os.getenv("RDS_DB_HOST"),
        port=os.getenv("RDS_DB_PORT"),  # Default port is 5432 for PostgreSQL
        user=os.getenv("RDS_DB_USER"),
        password=os.getenv("RDS_DB_PASSWORD"),
    )

    # Initialize RDSDestination with target table and PostgresDatabase instance
    rds_destination = RDSDestination(db, "provider_integration.status_update_queue")

    # Insert data into the table
    rds_destination.send(sample_data)
