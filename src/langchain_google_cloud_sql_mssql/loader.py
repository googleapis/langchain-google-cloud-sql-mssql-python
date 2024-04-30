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
from typing import Any, Dict, Iterable, Iterator, List, Optional

import sqlalchemy
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document

from .engine import MSSQLEngine

DEFAULT_CONTENT_COL = "page_content"
DEFAULT_METADATA_COL = "langchain_metadata"


def _parse_doc_from_row(
    content_columns: Iterable[str],
    metadata_columns: Iterable[str],
    row: Dict,
    metadata_json_column: str = DEFAULT_METADATA_COL,
) -> Document:
    page_content = " ".join(
        str(row[column]) for column in content_columns if column in row
    )
    metadata: Dict[str, Any] = {}
    # unnest metadata from langchain_metadata column
    if row.get(metadata_json_column):
        for k, v in row[metadata_json_column].items():
            metadata[k] = v
    # load metadata from other columns
    for column in metadata_columns:
        if column in row and column != metadata_json_column:
            metadata[column] = row[column]
    return Document(page_content=page_content, metadata=metadata)


def _parse_row_from_doc(
    column_names: Iterable[str],
    doc: Document,
    content_column: str = DEFAULT_CONTENT_COL,
    metadata_json_column: str = DEFAULT_METADATA_COL,
) -> Dict:
    doc_metadata = doc.metadata.copy()
    row: Dict[str, Any] = {content_column: doc.page_content}
    for entry in doc.metadata:
        if entry in column_names:
            row[entry] = doc_metadata[entry]
            del doc_metadata[entry]
    # store extra metadata in langchain_metadata column in json format
    if metadata_json_column in column_names and len(doc_metadata) > 0:
        row[metadata_json_column] = doc_metadata
    return row


class MSSQLLoader(BaseLoader):
    """A class for loading langchain documents from a Cloud SQL MSSQL database."""

    def __init__(
        self,
        engine: MSSQLEngine,
        table_name: str = "",
        query: str = "",
        content_columns: Optional[List[str]] = None,
        metadata_columns: Optional[List[str]] = None,
        metadata_json_column: Optional[str] = None,
    ):
        """
        Document page content defaults to the first column present in the query or table and
        metadata defaults to all other columns. Use with content_columns to overwrite the column
        used for page content. Use metadata_columns to select specific metadata columns rather
        than using all remaining columns.

        If multiple content columns are specified, page_content’s string format will default to
        space-separated string concatenation.

        Args:
            engine (MSSQLEngine): MSSQLEngine object to connect to the MSSQL database.
            table_name (str): The MSSQL database table name. (OneOf: table_name, query).
            query (str): The query to execute in MSSQL format.  (OneOf: table_name, query).
            content_columns (List[str]): The columns to write into the `page_content`
                of the document. Optional.
            metadata_columns (List[str]): The columns to write into the `metadata` of the document.
                Optional.
            metadata_json_column (str): The name of the JSON column to use as the metadata’s base
                dictionary. Default: `langchain_metadata`. Optional.
        """
        self.engine = engine
        self.table_name = table_name
        self.query = query
        self.content_columns = content_columns
        self.metadata_columns = metadata_columns
        self.metadata_json_column = metadata_json_column
        if not self.table_name and not self.query:
            raise ValueError("One of 'table_name' or 'query' must be specified.")
        if self.table_name and self.query:
            raise ValueError(
                "Cannot specify both 'table_name' and 'query'. Specify 'table_name' to load "
                "entire table or 'query' to load a specific query."
            )

    def load(self) -> List[Document]:
        """
        Load langchain documents from a Cloud SQL MSSQL database.

        Returns:
            (List[langchain_core.documents.Document]): a list of Documents with metadata from
                specific columns.
        """
        return list(self.lazy_load())

    def lazy_load(self) -> Iterator[Document]:
        """
        Lazy Load langchain documents from a Cloud SQL MSSQL database. Use lazy load to avoid
        caching all documents in memory at once.

        Returns:
            (Iterator[langchain_core.documents.Document]): a list of Documents with metadata from
                specific columns.
        """
        if self.query:
            stmt = sqlalchemy.text(self.query)
        else:
            stmt = sqlalchemy.text(f'select * from "{self.table_name}";')
        with self.engine.connect() as connection:
            result_proxy = connection.execute(stmt)
            column_names = list(result_proxy.keys())
            content_columns = self.content_columns or [column_names[0]]
            metadata_columns = self.metadata_columns or [
                col for col in column_names if col not in content_columns
            ]
            # check validity of metadata json column
            if (
                self.metadata_json_column
                and self.metadata_json_column not in column_names
            ):
                raise ValueError(
                    f"Column {self.metadata_json_column} not found in query result {column_names}."
                )
            # check validity of other column
            all_names = content_columns + metadata_columns
            for name in all_names:
                if name not in column_names:
                    raise ValueError(
                        f"Column {name} not found in query result {column_names}."
                    )
            # use default metadata json column if not specified
            metadata_json_column = self.metadata_json_column or DEFAULT_METADATA_COL

            # load document one by one
            while True:
                row = result_proxy.fetchone()
                if not row:
                    break
                # Handle default metadata field
                row_data = {}
                for column in column_names:
                    value = getattr(row, column)
                    if column == metadata_json_column:
                        row_data[column] = json.loads(value)
                    else:
                        row_data[column] = value
                yield _parse_doc_from_row(
                    content_columns,
                    metadata_columns,
                    row_data,
                    metadata_json_column,
                )


class MSSQLDocumentSaver:
    """A class for saving langchain documents into a Cloud SQL MSSQL database table."""

    def __init__(
        self,
        engine: MSSQLEngine,
        table_name: str,
        content_column: Optional[str] = None,
        metadata_json_column: Optional[str] = None,
    ):
        """
        MSSQLDocumentSaver allows for saving of langchain documents in a database. If the table
        doesn't exists, a table with default schema will be created. The default schema:
        - page_content (type: text)
        - langchain_metadata (type: JSON)

        Args:
          engine: MSSQLEngine object to connect to the MSSQL database.
          table_name: The name of table for saving documents.
          content_column (str): The column to store document content.
            Deafult: `page_content`. Optional.
          metadata_json_column (str): The name of the JSON column to use as the metadata’s base
            dictionary. Default: `langchain_metadata`. Optional.
        """
        self.engine = engine
        self.table_name = table_name
        self._table = self.engine._load_document_table(table_name)
        self.content_column = content_column or DEFAULT_CONTENT_COL
        if self.content_column not in self._table.columns.keys():
            raise ValueError(
                f"Missing '{self.content_column}' field in table {table_name}."
            )
        # check metadata_json_column existence if it's provided.
        if (
            metadata_json_column
            and metadata_json_column not in self._table.columns.keys()
        ):
            raise ValueError(
                f"Cannot find '{metadata_json_column}' column in table {table_name}."
            )
        self.metadata_json_column = metadata_json_column or DEFAULT_METADATA_COL

    def add_documents(self, docs: List[Document]) -> None:
        """
        Save documents in the DocumentSaver table. Document’s metadata is added to columns if found or
        stored in langchain_metadata JSON column.

        Args:
            docs (List[langchain_core.documents.Document]): a list of documents to be saved.
        """
        with self.engine.connect() as conn:
            for doc in docs:
                row = _parse_row_from_doc(
                    self._table.columns.keys(),
                    doc,
                    self.content_column,
                    self.metadata_json_column,
                )
                if self.metadata_json_column in row:
                    row[self.metadata_json_column] = json.dumps(
                        row[self.metadata_json_column]
                    )
                conn.execute(sqlalchemy.insert(self._table).values(row))
            conn.commit()

    def delete(self, docs: List[Document]) -> None:
        """
        Delete all instances of a document from the DocumentSaver table by matching the entire Document
        object.

        Args:
            docs (List[langchain_core.documents.Document]): a list of documents to be deleted.
        """
        with self.engine.connect() as conn:
            for doc in docs:
                row = _parse_row_from_doc(
                    self._table.columns.keys(),
                    doc,
                    self.content_column,
                    self.metadata_json_column,
                )
                if self.metadata_json_column in row:
                    row[self.metadata_json_column] = json.dumps(
                        row[self.metadata_json_column]
                    )
                # delete by matching all fields of document
                where_conditions = []
                for col in self._table.columns:
                    where_conditions.append(col == row[col.name])
                conn.execute(
                    sqlalchemy.delete(self._table).where(
                        sqlalchemy.and_(*where_conditions)
                    )
                )
            conn.commit()
