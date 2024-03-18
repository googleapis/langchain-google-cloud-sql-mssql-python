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
import os
import uuid
from typing import Generator

import pytest
import sqlalchemy
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage

from langchain_google_cloud_sql_mssql import MSSQLChatMessageHistory, MSSQLEngine

project_id = os.environ["PROJECT_ID"]
region = os.environ["REGION"]
instance_id = os.environ["INSTANCE_ID"]
db_name = os.environ["DB_NAME"]
db_user = os.environ["DB_USER"]
db_password = os.environ["DB_PASSWORD"]
table_name = "message_store" + str(uuid.uuid4()).replace("-", "_")
malformed_table = "malformed_table" + str(uuid.uuid4()).replace("-", "_")


@pytest.fixture(name="memory_engine")
def setup() -> Generator:
    engine = MSSQLEngine.from_instance(
        project_id=project_id,
        region=region,
        instance=instance_id,
        database=db_name,
        user=db_user,
        password=db_password,
    )

    # create table with malformed schema (missing 'type')
    query = f"""CREATE TABLE {malformed_table} (
        id INT IDENTITY(1,1) PRIMARY KEY,
        session_id NVARCHAR(MAX) NOT NULL,
        data NVARCHAR(MAX) NOT NULL,
    );"""
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text(query))
        conn.commit()
    yield engine
    # cleanup tables
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text(f"DROP TABLE IF EXISTS {table_name}"))
        conn.execute(sqlalchemy.text(f"DROP TABLE IF EXISTS {malformed_table}"))
        conn.commit()


def test_chat_message_history(memory_engine: MSSQLEngine) -> None:
    memory_engine.init_chat_history_table(table_name)
    history = MSSQLChatMessageHistory(
        engine=memory_engine, session_id="test", table_name=table_name
    )
    history.add_user_message("hi!")
    history.add_ai_message("whats up?")
    messages = history.messages

    # verify messages are correct
    assert messages[0].content == "hi!"
    assert type(messages[0]) is HumanMessage
    assert messages[1].content == "whats up?"
    assert type(messages[1]) is AIMessage

    # verify clear() clears message history
    history.clear()
    assert len(history.messages) == 0


def test_chat_message_history_table_does_not_exist(
    memory_engine: MSSQLEngine,
) -> None:
    """Test that MSSQLChatMessageHistory fails if table does not exist."""
    with pytest.raises(AttributeError) as exc_info:
        MSSQLChatMessageHistory(
            engine=memory_engine, session_id="test", table_name="missing_table"
        )
        # assert custom error message for missing table
        assert (
            exc_info.value.args[0]
            == f"Table 'missing_table' does not exist. Please create it before initializing MSSQLChatMessageHistory. See MSSQLEngine.init_chat_history_table() for a helper method."
        )


def test_chat_message_history_table_malformed_schema(
    memory_engine: MSSQLEngine,
) -> None:
    """Test that MSSQLChatMessageHistory fails if schema is malformed."""
    with pytest.raises(IndexError):
        MSSQLChatMessageHistory(
            engine=memory_engine,
            session_id="test",
            table_name=malformed_table,
        )
