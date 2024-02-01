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
import json
import os
from typing import Generator

import pytest
import sqlalchemy
from langchain_core.documents import Document

from langchain_google_cloud_sql_mssql import MSSQLEngine, MSSQLLoader

project_id = os.environ["PROJECT_ID"]
region = os.environ["REGION"]
instance_id = os.environ["INSTANCE_ID"]
table_name = os.environ["TABLE_NAME"]
db_name = os.environ["DB_NAME"]
db_user = os.environ["DB_USER"]
db_password = os.environ["DB_PASSWORD"]


@pytest.fixture(name="engine")
def setup() -> Generator:
    engine = MSSQLEngine.from_instance(
        project_id=project_id,
        region=region,
        instance=instance_id,
        database=db_name,
        db_user=db_user,
        db_password=db_password,
    )
    yield engine

    with engine.connect() as conn:
        conn.execute(sqlalchemy.text(f'DROP TABLE IF EXISTS "{table_name}"'))
        conn.commit()


@pytest.fixture
def default_setup(engine):
    with engine.connect() as conn:
        conn.execute(
            sqlalchemy.text(
                f"""
                IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[{table_name}]') AND type in (N'U'))
                BEGIN
                    CREATE TABLE [dbo].[{table_name}](
                        fruit_id INT IDENTITY(1,1) PRIMARY KEY,
                        fruit_name VARCHAR(100) NOT NULL,
                        variety VARCHAR(50),  
                        quantity_in_stock INT NOT NULL,
                        price_per_unit DECIMAL(6,2) NOT NULL,
                        organic BIT NOT NULL
                    )
                END
                """
            )
        )
        conn.commit()
    yield engine

    with engine.connect() as conn:
        conn.execute(sqlalchemy.text(f'DROP TABLE IF EXISTS "{table_name}"'))
        conn.commit()


def test_load_from_query_default(default_setup):
    with default_setup.connect() as conn:
        conn.execute(
            sqlalchemy.text(
                f"""
                INSERT INTO [dbo].[{table_name}] (fruit_name, variety, quantity_in_stock, price_per_unit, organic)
                VALUES
                    ('Apple', 'Granny Smith', 150, 1.00, 1);
                """
            )
        )
        conn.commit()
    query = f'SELECT * FROM "{table_name}";'
    loader = MSSQLLoader(
        engine=default_setup,
        query=query,
    )

    documents = loader.load()
    assert documents == [
        Document(
            page_content="1",
            metadata={
                "fruit_name": "Apple",
                "variety": "Granny Smith",
                "quantity_in_stock": 150,
                "price_per_unit": 1,
                "organic": True,
            },
        )
    ]


def test_load_from_query_customized_content_customized_metadata(default_setup):
    with default_setup.connect() as conn:
        conn.execute(
            sqlalchemy.text(
                f"""
                INSERT INTO "{table_name}" (fruit_name, variety, quantity_in_stock, price_per_unit, organic)
                VALUES
                    ('Apple', 'Granny Smith', 150, 0.99, 1),
                    ('Banana', 'Cavendish', 200, 0.59, 0),
                    ('Orange', 'Navel', 80, 1.29, 1);
                """
            )
        )
        conn.commit()
    query = f'SELECT * FROM "{table_name}";'
    loader = MSSQLLoader(
        engine=default_setup,
        query=query,
        content_columns=[
            "fruit_name",
            "variety",
            "quantity_in_stock",
            "price_per_unit",
            "organic",
        ],
        metadata_columns=["fruit_id"],
    )

    documents = loader.load()

    assert documents == [
        Document(
            page_content="Apple Granny Smith 150 0.99 True",
            metadata={"fruit_id": 1},
        ),
        Document(
            page_content="Banana Cavendish 200 0.59 False",
            metadata={"fruit_id": 2},
        ),
        Document(
            page_content="Orange Navel 80 1.29 True",
            metadata={"fruit_id": 3},
        ),
    ]


def test_load_from_query_customized_content_default_metadata(default_setup):
    with default_setup.connect() as conn:
        conn.execute(
            sqlalchemy.text(
                f"""
                INSERT INTO "{table_name}" (fruit_name, variety, quantity_in_stock, price_per_unit, organic)
                VALUES
                    ('Apple', 'Granny Smith', 150, 0.99, 1);
                """
            )
        )
        conn.commit()
    query = f'SELECT * FROM "{table_name}";'
    loader = MSSQLLoader(
        engine=default_setup,
        query=query,
        content_columns=[
            "variety",
            "quantity_in_stock",
            "price_per_unit",
        ],
    )

    documents = loader.load()
    assert documents == [
        Document(
            page_content="Granny Smith 150 0.99",
            metadata={
                "fruit_id": 1,
                "fruit_name": "Apple",
                "organic": True,
            },
        )
    ]


def test_load_from_query_default_content_customized_metadata(default_setup):
    with default_setup.connect() as conn:
        conn.execute(
            sqlalchemy.text(
                f"""
                INSERT INTO "{table_name}" (fruit_name, variety, quantity_in_stock, price_per_unit, organic)
                VALUES
                    ('Apple', 'Granny Smith', 150, 1, 1);
                """
            )
        )
        conn.commit()

    query = f'SELECT * FROM "{table_name}";'
    loader = MSSQLLoader(
        engine=default_setup,
        query=query,
        metadata_columns=[
            "fruit_name",
            "organic",
        ],
    )

    documents = loader.load()
    assert documents == [
        Document(
            page_content="1",
            metadata={
                "fruit_name": "Apple",
                "organic": True,
            },
        )
    ]


def test_load_from_query_with_langchain_metadata(engine):
    with engine.connect() as conn:
        conn.execute(
            sqlalchemy.text(
                f"""
                IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[{table_name}]') AND type in (N'U'))
                BEGIN
                    CREATE TABLE [dbo].[{table_name}](
                        fruit_id INT IDENTITY(1,1) PRIMARY KEY,
                        fruit_name VARCHAR(100) NOT NULL,
                        variety VARCHAR(50),  
                        quantity_in_stock INT NOT NULL,
                        price_per_unit DECIMAL(6,2) NOT NULL,
                        langchain_metadata NVARCHAR(MAX)
                    )
                END
                """
            )
        )
        metadata = json.dumps({"organic": 1})
        conn.execute(
            sqlalchemy.text(
                f"""
                INSERT INTO "{table_name}" (fruit_name, variety, quantity_in_stock, price_per_unit, langchain_metadata)
                VALUES
                    ('Apple', 'Granny Smith', 150, 1, '{metadata}');
                """
            )
        )
        conn.commit()
    query = f'SELECT * FROM "{table_name}";'
    loader = MSSQLLoader(
        engine=engine,
        query=query,
        metadata_columns=[
            "fruit_name",
            "langchain_metadata",
        ],
    )

    documents = loader.load()
    assert documents == [
        Document(
            page_content="1",
            metadata={
                "fruit_name": "Apple",
                "organic": True,
            },
        )
    ]