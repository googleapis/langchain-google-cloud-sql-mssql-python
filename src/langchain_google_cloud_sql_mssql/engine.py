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

from typing import List, Optional

import sqlalchemy
from google.cloud.sql.connector import Connector, RefreshStrategy

from .version import __version__

USER_AGENT = "langchain-google-cloud-sql-mssql-python/" + __version__


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
            cls._connector = Connector(
                user_agent=USER_AGENT, refresh_strategy=RefreshStrategy.LAZY
            )

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

    def init_chat_history_table(self, table_name: str) -> None:
        """Create table with schema required for MSSQLChatMessageHistory class.

        Required schema is as follows:

        ::

            CREATE TABLE {table_name} (
                id INT IDENTITY(1,1) PRIMARY KEY,
                session_id NVARCHAR(MAX) NOT NULL,
                data NVARCHAR(MAX) NOT NULL,
                type NVARCHAR(MAX) NOT NULL
            )

        Args:
            table_name (str): Name of database table to create for storing chat
                message history.
        """
        create_table_query = f"""IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = '{table_name}')
        BEGIN
        CREATE TABLE {table_name} (
            id INT IDENTITY(1,1) PRIMARY KEY,
            session_id NVARCHAR(MAX) NOT NULL,
            data NVARCHAR(MAX) NOT NULL,
            type NVARCHAR(MAX) NOT NULL
        )
        END;"""
        with self.engine.connect() as conn:
            conn.execute(sqlalchemy.text(create_table_query))
            conn.commit()

    def init_document_table(
        self,
        table_name: str,
        metadata_columns: List[sqlalchemy.Column] = [],
        content_column: str = "page_content",
        metadata_json_column: Optional[str] = "langchain_metadata",
        overwrite_existing: bool = False,
    ) -> None:
        """
        Create a table for saving of langchain documents.

        Args:
            table_name (str): The MSSQL database table name.
            metadata_columns (List[sqlalchemy.Column]): A list of SQLAlchemy Columns
                to create for custom metadata. Optional.
            content_column (str): The column to store document content.
                Deafult: `page_content`.
            metadata_json_column (Optional[str]): The column to store extra metadata in JSON format.
                Default: `langchain_metadata`. Optional.
            overwrite_existing (bool): Whether to drop existing table. Default: False.
        """
        if overwrite_existing:
            with self.engine.connect() as conn:
                conn.execute(sqlalchemy.text(f'DROP TABLE IF EXISTS "{table_name}";'))
                conn.commit()

        columns = [
            sqlalchemy.Column(
                content_column,
                sqlalchemy.UnicodeText,
                primary_key=False,
                nullable=False,
            )
        ]
        columns += metadata_columns
        if metadata_json_column:
            columns.append(
                sqlalchemy.Column(
                    metadata_json_column,
                    sqlalchemy.JSON,
                    primary_key=False,
                    nullable=True,
                )
            )
        sqlalchemy.Table(table_name, sqlalchemy.MetaData(), *columns).create(
            self.engine
        )

    def _load_document_table(self, table_name: str) -> sqlalchemy.Table:
        """
        Load table schema from existing table in MSSQL database.

        Args:
            table_name (str): The MSSQL database table name.

        Returns:
            (sqlalchemy.Table): The loaded table.
        """
        metadata = sqlalchemy.MetaData()
        sqlalchemy.MetaData.reflect(metadata, bind=self.engine, only=[table_name])
        return metadata.tables[table_name]
