import json
import os

import pandas as pd
import psycopg2
from sqlalchemy import create_engine


class PostgresDatabase:
    def __init__(self, database, endpoint, port, user, password):
        """
        Initialize the PostgreSQL database connection.
        """
        self.database = database
        self.endpoint = endpoint
        self.port = int(port)  # Default to port 5432 for PostgreSQL
        self.user = user
        self.password = password
        self._engine = self.create_postgres_engine()

    def create_postgres_engine(self):
        """
        Create a SQLAlchemy engine for PostgreSQL.
        """
        # connection_url = f"postgresql+psycopg2://{self.user}:{self.password}@{self.endpoint}:{self.port}/{self.database}"
        connection_url = (
            f"postgresql+psycopg2://{self.user}:{self.password}@{self.endpoint}:{self.port}/{self.database}"
            "?sslmode=disable&client_encoding=utf8"
        )

        print(f"Connecting to: {connection_url}")

        return create_engine(connection_url, client_encoding="utf8")

    def run_query(self, query):
        """
        Execute a SQL query and return the result as JSON.
        """
        try:
            with self._engine.connect() as connection:

                connection.execute("SET client_encoding = 'UTF8';")
                result_df = pd.read_sql(query, connection)
                return result_df.to_json(orient="records")
        except Exception as e:
            print(f"Error running query: {e}")
            return None


if __name__ == "__main__":
    # Initialize PostgreSQL connection using environment variables
    postgres = PostgresDatabase(
        database=os.getenv("RDS_DB_NAME"),
        endpoint=os.getenv("RDS_DB_HOST"),
        port=os.getenv("RDS_DB_PORT"),  # Default port is 5432 for PostgreSQL
        user=os.getenv("RDS_DB_USER"),
        password=os.getenv("RDS_DB_PASSWORD"),
    )

    # Run a query and get the result as JSON
    query = (
        "SELECT * FROM provider_integration.system_configuration where is_Active=true"
    )
    result = postgres.run_query(query)
    print(result)
