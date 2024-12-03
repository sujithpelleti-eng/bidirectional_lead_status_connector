import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import boto3

from common.models import SystemConfiguration
from common.postgres_connector import PostgresDatabase


def execute_query(db: PostgresDatabase, query: str, params: Tuple = ()):
    """Executes a query that does not return a result, like an UPDATE or INSERT."""
    try:
        with db._engine.connect() as connection:
            connection.execute(query, params)
    except Exception as e:
        raise e


def execute_query_returning_id(
    db: PostgresDatabase, query: str, params: Tuple = ()
) -> int:
    """Executes an INSERT query and returns the generated primary key."""
    try:
        with db._engine.connect() as connection:
            result = connection.execute(query, params)
            return result.fetchone()[0]
    except Exception as e:
        raise e


def get_secret(secret_id: str) -> Dict[str, Any]:
    client = boto3.client("secretsmanager")
    try:
        response = client.get_secret_value(SecretId=secret_id)
        return json.loads(response["SecretString"])
    except Exception as e:
        raise Exception(f"Error retrieving secret {secret_id}: {e}")


# Execution-level tracking functions
def start_execution(
    db: PostgresDatabase,
    execution_id: str,
    total_configs_executed: int,
    start_time: datetime,
) -> int:
    """Inserts a new record into `run_history` with an initial status and returns the generated `run_id`."""
    query = """
    INSERT INTO provider_integration.run_history (execution_id, total_configs_executed, status, start_time)
    VALUES (%s, %s, %s, %s) RETURNING run_id;
    """
    initial_status = "in_progress"  # Setting the initial status for the run
    return execute_query_returning_id(
        db, query, (execution_id, total_configs_executed, initial_status, start_time)
    )


def end_execution(
    db: PostgresDatabase,
    run_id: int,
    successful_configs: int,
    failed_configs: int,
    status: str,
    end_time: datetime,
    error_message: Optional[str] = None,
):
    """Updates the summary record in `run_history`."""
    query = """
    UPDATE provider_integration.run_history SET successful_configs = %s, failed_configs = %s, status = %s,
    end_time = %s, error_message = %s WHERE run_id = %s;
    """
    execute_query(
        db,
        query,
        (successful_configs, failed_configs, status, end_time, error_message, run_id),
    )


def log_step_detail(
    db: PostgresDatabase,
    run_id: int,
    execution_id: str,
    system_config_id: int,
    system_name: str,
    partner_name: str,
    step: str,
    status: str,
    records_fetched: int = 0,
    records_success: int = 0,
    records_error: int = 0,
    error_message: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
):
    """Inserts a new record into `run_history_detail` for step-level tracking."""
    query = """
    INSERT INTO provider_integration.run_history_detail (
        run_id, execution_id, system_config_id, system_name, partner_name, step, status,
        records_fetched, records_success, records_error, error_message, start_time, end_time
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    execute_query(
        db,
        query,
        (
            run_id,
            execution_id,
            system_config_id,
            system_name,
            partner_name,
            step,
            status,
            records_fetched,
            records_success,
            records_error,
            error_message,
            start_time,
            end_time,
        ),
    )


def fetch_system_configurations(
    db: PostgresDatabase,
    schedule: Optional[str] = None,
    system: Optional[str] = None,
    partner_id: Optional[str] = None,
) -> List[SystemConfiguration]:
    """
    Fetch system configurations with optional filters for schedule, system, and partner.

    :param db: Database connection instance.
    :param schedule: Optional schedule filter.
    :param system: Optional system name filter.
    :param partner_id: Optional partner_id filter.
    :return: List of SystemConfiguration objects.
    """
    query = """
        SELECT * 
        FROM provider_integration.system_configuration
        WHERE is_active = TRUE
    """

    # Build WHERE clause dynamically based on filters
    filters = []
    if schedule:
        filters.append(f"schedule = '{schedule}'")
    if system:
        filters.append(f"system_name = '{system}'")
    if partner_id:
        filters.append(f"partner_id = '{partner_id}'")

    # Append filters to query
    if filters:
        query += " AND " + " AND ".join(filters)

    # Run the query and parse the result
    raw_rows = db.run_query(query)
    try:
        rows = json.loads(raw_rows)  # Parse the JSON string into Python objects
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse database query result as JSON: {e}")

    # Convert rows to SystemConfiguration objects
    configs = [
        SystemConfiguration(
            system_config_id=row.get("system_config_id"),
            system_name=row.get("system_name"),
            partner_name=row.get("partner_name"),
            partner_id=row.get("partner_id"),
            file_type=row.get("file_type"),
            system_type=row.get("system_type"),
            config=row.get("config")
            if isinstance(row.get("config"), dict)
            else json.loads(row.get("config")),
            s3_bucket_name=row.get("s3_bucket_name"),
            credentials_secret_id=row.get("credentials_secret_id"),
            schedule=row.get("schedule"),
            is_active=row.get("is_active"),
        )
        for row in rows
    ]
    return configs


def fetch_api_config():
    pass


if __name__ == "__main__":
    # Initialize PostgreSQL connection using environment variables
    db = PostgresDatabase(
        database=os.getenv("RDS_DB_NAME"),
        endpoint=os.getenv("RDS_DB_HOST"),
        port=os.getenv("RDS_DB_PORT"),
        user=os.getenv("RDS_DB_USER"),
        password=os.getenv("RDS_DB_PASSWORD"),
    )

    # Fetch system configurations using the existing `db` connection
    config = fetch_system_configurations(db)
    print(config)
