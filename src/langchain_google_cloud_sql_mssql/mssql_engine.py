# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# TODO: Remove below import when minimum supported Python version is 3.10
from __future__ import annotations

from typing import Optional

import sqlalchemy
from google.cloud.sql.connector import Connector


class MSSQLEngine:
    """A class for managing connections to a Cloud SQL for MSSQL database."""

    _connector: Optional[Connector] = None

    def __init__(
        self,
        engine: sqlalchemy.engine.Engine,
    ) -> None:
        self.engine = engine

    @classmethod
    def from_instance(
        cls,
        project_id: str,
        region: str,
        instance: str,
        database: str,
        user: str,
        password: str,
    ) -> MSSQLEngine:
        """Create an instance of MSSQLEngine from Cloud SQL instance
        details.

        This method uses the Cloud SQL Python Connector to connect to Cloud SQL
        MSSQL instance using the given database credentials.

        More details can be found at
        https://github.com/GoogleCloudPlatform/cloud-sql-python-connector#credentials

        Args:
            project_id (str): Project ID of the Google Cloud Project where
                the Cloud SQL instance is located.
            region (str): Region where the Cloud SQL instance is located.
            instance (str): The name of the Cloud SQL instance.
            database (str): The name of the database to connect to on the
                Cloud SQL instance.
            db_user (str): The username to use for authentication.
            db_password (str): The password to use for authentication.

        Returns:
            (MSSQLEngine): The engine configured to connect to a
                Cloud SQL instance database.
        """
        engine = cls._create_connector_engine(
            instance_connection_name=f"{project_id}:{region}:{instance}",
            database=database,
            user=user,
            password=password,
        )
        return cls(engine=engine)

    @classmethod
    def _create_connector_engine(
        cls, instance_connection_name: str, database: str, user: str, password: str
    ) -> sqlalchemy.engine.Engine:
        """Create a SQLAlchemy engine using the Cloud SQL Python Connector.

        Args:
            instance_connection_name (str): The instance connection
                name of the Cloud SQL instance to establish a connection to.
                (ex. "project-id:instance-region:instance-name")
            database (str): The name of the database to connect to on the
                Cloud SQL instance.
            user (str): The username to use for authentication.
            password (str): The password to use for authentication.
        Returns:
            (sqlalchemy.engine.Engine): Engine configured using the Cloud SQL
                Python Connector.
        """
        if cls._connector is None:
            cls._connector = Connector()

        # anonymous function to be used for SQLAlchemy 'creator' argument
        def getconn():
            conn = cls._connector.connect(  # type: ignore
                instance_connection_name,
                "pytds",
                user=user,
                password=password,
                db=database,
            )
            return conn

        return sqlalchemy.create_engine(
            "mssql+pytds://",
            creator=getconn,
        )

    def connect(self) -> sqlalchemy.engine.Connection:
        """Create a connection from SQLAlchemy connection pool.

        Returns:
            (sqlalchemy.engine.Connection): a single DBAPI connection checked
                out from the connection pool.
        """
        return self.engine.connect()
