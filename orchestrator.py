import logging
import os
import sys
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from typing import List, Optional

from common.models import SystemConfiguration
from common.postgres_connector import PostgresDatabase
from common.utils import (end_execution, fetch_system_configurations,
                          log_step_detail, start_execution)
from connectors.yardi_connector import YardiConnector
from destinations.rds_destination import RDSDestination
from destinations.s3_destination import S3Destination
from parsers.yardi_parser import YardiParser

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(
        self,
        schedule: Optional[str] = None,
        system: Optional[str] = None,
        partner_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ):
        # self.configurations: List[SystemConfiguration] = fetch_system_configurations()
        self.db = PostgresDatabase(
            database=os.getenv("RDS_DB_NAME"),
            endpoint=os.getenv("RDS_DB_HOST"),
            port=os.getenv("RDS_DB_PORT"),  # Default port is 5432 for PostgreSQL
            user=os.getenv("RDS_DB_USER"),
            password=os.getenv("RDS_DB_PASSWORD"),
        )
        self.execution_id = str(uuid.uuid4())
        self.run_id = None
        self.successful_configs = 0
        self.failed_configs = 0
        self.schedule = schedule
        self.system = system
        self.partner_id = partner_id
        self.from_date = from_date
        self.to_date = to_date
        logger.info(
            f"Orchestrator initialized with schedule={schedule}, system={system}, partner_id={partner_id}, from_date={from_date}, to_date={to_date}"
        )

    def get_configurations(self, db: PostgresDatabase) -> List[SystemConfiguration]:
        """
        Fetch system configurations with applied filters.

        :return: List of filtered SystemConfiguration objects.
        """
        return fetch_system_configurations(
            db=self.db,
            schedule=self.schedule,
            system=self.system,
            partner_id=self.partner_id,
        )

    def start_execution(self, configurations):
        """Initialize a new execution record."""
        start_time = datetime.now()
        self.run_id = start_execution(
            db=self.db,
            execution_id=self.execution_id,
            total_configs_executed=len(configurations),
            start_time=start_time,
        )

    def end_execution(self, success_count, failure_count, error_message=None):
        """Complete the execution record with summary data."""
        end_time = datetime.now()
        status = "success" if failure_count == 0 else "failure"
        end_execution(
            db=self.db,
            run_id=self.run_id,
            successful_configs=success_count,
            failed_configs=failure_count,
            status=status,
            end_time=end_time,
            error_message=error_message,
        )

    def get_connector(self, config: SystemConfiguration):
        if config.system_name == "Yardi":
            return YardiConnector(config.config, config.feature_flags)
        else:
            raise Exception(f"Unsupported system: {config.system_name}")

    def get_parser(self, config: str, execution_id):
        if config.system_name == "Yardi":
            return YardiParser(config.system_config_id, execution_id)
        else:
            raise Exception(f"Unsupported system: {config.system_name}")

    def get_destinations(self, config: SystemConfiguration):
        s3 = S3Destination(config.s3_bucket_name)
        rds = RDSDestination(self.db, "provider_integration.status_update_queue")
        return [s3, rds]

    def process_configuration(self, config):
        """Process each configuration and log each step's outcome."""
        current_step = "initialization"  # Initialize to a default step
        error_message = None  # Initialize error_message
        try:
            connector = self.get_connector(config)
            parser = self.get_parser(config, self.execution_id)
            destinations = self.get_destinations(config)
            feature_flags = config.feature_flags
            steps = feature_flags.get('steps')

            # Step 1: Fetch data
            if steps.get('fetch_data'):
                current_step = "fetch_data"
                fetch_start_time = datetime.now()
                raw_data = connector.fetch_raw_data(
                    from_date=self.from_date, to_date=self.to_date
                )
                logger.info(f"Data type for {current_step}: {type(raw_data)}")
                log_step_detail(
                    db=self.db,
                    run_id=self.run_id,
                    execution_id=self.execution_id,
                    system_config_id=config.system_config_id,
                    system_name=config.system_name,
                    partner_name=config.partner_name,
                    step=current_step,
                    status="success",
                    records_fetched=len(raw_data),
                    start_time=fetch_start_time,
                    end_time=datetime.now(),
                )
            else:
                logger.info(f"Skipping fetch_data step for {config.partner_name}")

            # Step 2: Insert raw data to S3 before parsing
            if steps.get('store_raw_data_s3'):
                current_step = "store_raw_data_s3"
                for destination in destinations:
                    if isinstance(destination, S3Destination):
                        s3_start_time = datetime.now()
                        destination.send(
                            raw_data,
                            provider=config.system_name,
                            partner_id=config.partner_id,
                            file_type=config.file_type,
                        )
                        log_step_detail(
                            db=self.db,
                            run_id=self.run_id,
                            execution_id=self.execution_id,
                            system_config_id=config.system_config_id,
                            system_name=config.system_name,
                            partner_name=config.partner_name,
                            step=current_step,
                            status="success",
                            records_fetched=len(raw_data),
                            start_time=s3_start_time,
                            end_time=datetime.now(),
                        )
            else:
                logger.info(f"Skipping store_raw_data_s3 step for {config.partner_name}")
                

            # Step 3: Parse data
            if steps.get("parse_data"):
                current_step = "parse_data"
                parse_start_time = datetime.now()
                logger.info(f"Creating parser with execution_id: {self.execution_id}")
                parsed_data = parser.parse(raw_data)
                log_step_detail(
                    db=self.db,
                    run_id=self.run_id,
                    execution_id=self.execution_id,
                    system_config_id=config.system_config_id,
                    system_name=config.system_name,
                    partner_name=config.partner_name,
                    step=current_step,
                    status="success",
                    records_fetched=len(parsed_data),
                    start_time=parse_start_time,
                    end_time=datetime.now(),
                )
            else:
                logger.info(f"Skipping parse_data step for {config.partner_name}")

            # Step 4: Send parsed data to RDS
            if steps.get("send_data_to_rds"):
                current_step = "send_data_to_rds"
                send_start_time = datetime.now()
                for destination in destinations:
                    if isinstance(destination, RDSDestination):
                        destination.send(parsed_data)
                        log_step_detail(
                            db=self.db,
                            run_id=self.run_id,
                            execution_id=self.execution_id,
                            system_config_id=config.system_config_id,
                            system_name=config.system_name,
                            partner_name=config.partner_name,
                            step=current_step,
                            status="success",
                            records_success=len(parsed_data),
                            start_time=send_start_time,
                            end_time=datetime.now(),
                        )
            else:
                logger.info(f"Skipping send_data_to_rds step for {config.partner_name}")
            
        except Exception as e:
            error_message = str(e)
            logger.error(
                f"Error processing config {config.system_name}-{config.partner_name}: {error_message}",
                exc_info=True,
            )
            log_step_detail(
                db=self.db,
                run_id=self.run_id,
                execution_id=self.execution_id,
                system_config_id=config.system_config_id,
                system_name=config.system_name,
                partner_name=config.partner_name,
                step=current_step,
                status="failure",
                error_message=error_message,
                start_time=locals().get(f"{current_step}_start_time", datetime.now()),
                end_time=datetime.now(),
            )
            return False  # Indicate failure for this configuration
        return True  # Indicate success for this configuration

    def run(self):
        """Run the orchestrator, processing each configuration and logging results."""
        configurations = []  # Default initialization
        try:
            logger.info(
                f"Starting the execution with execution_id: {self.execution_id}"
            )
            configurations = self.get_configurations(self.db)
            self.start_execution(configurations)

            success_count = 0
            failure_count = 0
            error_messages = []  # To collect errors and summarize them at the end

            for config in configurations:
                try:
                    logger.info(
                        f"Processing configuration: {config.system_name}-{config.partner_name}"
                    )

                    # Attempt to process the configuration
                    if self.process_configuration(config):
                        success_count += 1
                    else:
                        failure_count += 1
                        error_messages.append(
                            f"Failed configuration: {config.system_name}-{config.partner_name}"
                        )

                except Exception as e:
                    # Log and track any unexpected exceptions for the configuration
                    error_message = str(e)
                    logger.error(
                        f"Unexpected error for configuration {config.system_name}-{config.partner_name}: {error_message}"
                    )
                    failure_count += 1
                    error_messages.append(
                        f"{config.system_name}-{config.partner_name} error: {error_message}"
                    )
                    # Log the error in the error log
                    # self.log_error(config, error_message)

            # End execution with accumulated metrics and errors
            status = "success" if failure_count == 0 else "failure"
            error_summary = "; ".join(error_messages) if error_messages else None
            self.end_execution(
                success_count, failure_count, error_message=error_summary
            )
            logger.info("Execution completed.")

        except Exception as e:
            # Global catch-all for the run method to log any top-level errors
            error_summary = f"Critical error during orchestrator run: {str(e)}"
            logger.critical(error_summary)
            self.end_execution(
                success_count=0,
                failure_count=len(configurations),
                error_message=error_summary,
            )


if __name__ == "__main__":
    # configurations = fetch_system_configurations()
    # for config in configurations:
    #     print(config)
    orchestrator = Orchestrator()
    orchestrator.run()
