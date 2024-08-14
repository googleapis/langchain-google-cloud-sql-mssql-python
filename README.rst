Cloud SQL for SQL Server for LangChain
======================================

|preview| |pypi| |versions|

- `Client Library Documentation`_
- `Product Documentation`_

.. |preview| image:: https://img.shields.io/badge/support-preview-orange.svg
   :target: https://cloud.google.com/products#product-launch-stages
.. |pypi| image:: https://img.shields.io/pypi/v/langchain-google-cloud-sql-mssql.svg
   :target: https://pypi.org/project/langchain-google-cloud-sql-mssql/
.. |versions| image:: https://img.shields.io/pypi/pyversions/langchain-google-cloud-sql-mssql.svg
   :target: https://pypi.org/project/langchain-google-cloud-sql-mssql/
.. _Client Library Documentation: https://cloud.google.com/python/docs/reference/langchain-google-cloud-sql-mssql/latest
.. _Product Documentation: https://cloud.google.com/sql/sqlserver

Quick Start
-----------

In order to use this library, you first need to go through the following
steps:

1. `Select or create a Cloud Platform project.`_
2. `Enable billing for your project.`_
3. `Enable the Google Cloud SQL Admin API.`_
4. `Setup Authentication.`_

.. _Select or create a Cloud Platform project.: https://console.cloud.google.com/project
.. _Enable billing for your project.: https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project
.. _Enable the Google Cloud SQL Admin API.: https://console.cloud.google.com/flows/enableapi?apiid=sqladmin.googleapis.com
.. _Setup Authentication.: https://googleapis.dev/python/google-api-core/latest/auth.html

Installation
~~~~~~~~~~~~

Install this library in a `virtualenv`_ using pip. `virtualenv`_ is a tool to create isolated Python environments. The basic problem it addresses is
one of dependencies and versions, and indirectly permissions.

With `virtualenv`_, it’s possible to install this library without needing system install permissions, and without clashing with the installed system dependencies.

.. _`virtualenv`: https://virtualenv.pypa.io/en/latest/

Supported Python Versions
^^^^^^^^^^^^^^^^^^^^^^^^^

Python >= 3.8

Mac/Linux
^^^^^^^^^

.. code-block:: console

   pip install virtualenv
   virtualenv <your-env>
   source <your-env>/bin/activate
   <your-env>/bin/pip install langchain-google-cloud-sql-mssql

Windows
^^^^^^^

.. code-block:: console

   pip install virtualenv
   virtualenv <your-env>
   <your-env>\Scripts\activate
   <your-env>\Scripts\pip.exe install langchain-google-cloud-sql-mssql


Document Loader Usage
~~~~~~~~~~~~~~~~~~~~~

Use a document loader to load data as LangChain ``Document``\ s.

.. code-block:: python

    from langchain_google_cloud_sql_mssql import MSSQLEngine, MSSQLLoader

    engine = MSSQLEngine.from_instance("project-id", "region", "my-instance", "my-database", "db_user", "db_pass")
    loader = MSSQLLoader(
        engine,
        table_name="my-table-name"
    )
    docs = loader.lazy_load()

See the full `Document Loader`_ tutorial.

.. _`Document Loader`: https://github.com/googleapis/langchain-google-cloud-sql-mssql-python/blob/main/docs/document_loader.ipynb

Chat Message History Usage
~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``ChatMessageHistory`` to store messages and provide conversation
history to LLMs.

.. code:: python

    from langchain_google_cloud_sql_mssql import MSSQLChatMessageHistory, MSSQLEngine

    engine = MSSQLEngine.from_instance("project-id", "region", "my-instance", "my-database", "db_user", "db_pass")
    history = MSSQLChatMessageHistory(
        engine,
        table_name="my-message-store",
        session_id="my-session_id"
    )

See the full `Chat Message History`_ tutorial.

.. _`Chat Message History`: https://github.com/googleapis/langchain-google-cloud-sql-mssql-python/blob/main/docs/chat_message_history.ipynb

Contributions
~~~~~~~~~~~~~

Contributions to this library are always welcome and highly encouraged.

See `CONTRIBUTING`_ for more information how to get started.

Please note that this project is released with a Contributor Code of Conduct. By participating in
this project you agree to abide by its terms. See `Code of Conduct`_ for more
information.

.. _`CONTRIBUTING`: https://github.com/googleapis/langchain-google-cloud-sql-mssql-python/blob/main/CONTRIBUTING.md
.. _`Code of Conduct`: https://github.com/googleapis/langchain-google-cloud-sql-mssql-python/blob/main/CODE_OF_CONDUCT.md


License
-------

Apache 2.0 - See
`LICENSE <https://github.com/googleapis/langchain-google-cloud-sql-mssql-python/blob/main/LICENSE>`_
for more information.

Disclaimer
----------

This is not an officially supported Google product.

