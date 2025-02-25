import os
from tests.pipeline.utils import assert_load_info


def start_snippet() -> None:

    # @@@DLT_SNIPPET_START start
    import dlt

    data = [
        {'id': 1, 'name': 'Alice'},
        {'id': 2, 'name': 'Bob'}
    ]

    pipeline = dlt.pipeline(
        pipeline_name='quick_start',
        destination='duckdb',
        dataset_name='mydata'
    )
    load_info = pipeline.run(data, table_name="users")

    print(load_info)
    # @@@DLT_SNIPPET_END start

    assert_load_info(load_info)


def json_snippet() -> None:

    # @@@DLT_SNIPPET_START json
    import dlt

    from dlt.common import json

    with open("./assets/json_file.json", 'rb') as file:
        data = json.load(file)

    pipeline = dlt.pipeline(
        pipeline_name='from_json',
        destination='duckdb',
        dataset_name='mydata',
    )

    # NOTE: test data that we load is just a dictionary so we enclose it in a list
    # if your JSON contains a list of objects you do not need to do that
    load_info = pipeline.run([data], table_name="json_data")

    print(load_info)
    # @@@DLT_SNIPPET_END json

    assert_load_info(load_info)


def csv_snippet() -> None:

    # @@@DLT_SNIPPET_START csv
    import dlt
    import pandas as pd

    owid_disasters_csv = "https://raw.githubusercontent.com/owid/owid-datasets/master/datasets/Natural%20disasters%20from%201900%20to%202019%20-%20EMDAT%20(2020)/Natural%20disasters%20from%201900%20to%202019%20-%20EMDAT%20(2020).csv"
    df = pd.read_csv(owid_disasters_csv)
    data = df.to_dict(orient='records')

    pipeline = dlt.pipeline(
        pipeline_name='from_csv',
        destination='duckdb',
        dataset_name='mydata',
    )
    load_info = pipeline.run(data, table_name="natural_disasters")

    print(load_info)
    # @@@DLT_SNIPPET_END csv

    assert_load_info(load_info)


def api_snippet() -> None:

    # @@@DLT_SNIPPET_START api
    import dlt
    from dlt.sources.helpers import requests

    # url to request dlt-hub/dlt issues
    url = "https://api.github.com/repos/dlt-hub/dlt/issues"
    # make the request and check if succeeded
    response = requests.get(url)
    response.raise_for_status()

    pipeline = dlt.pipeline(
        pipeline_name='from_api',
        destination='duckdb',
        dataset_name='github_data',
    )
    # the response contains a list of issues
    load_info = pipeline.run(response.json(), table_name="issues")

    print(load_info)
    # @@@DLT_SNIPPET_END api

    assert_load_info(load_info)


def db_snippet() -> None:

    # @@@DLT_SNIPPET_START db
    import dlt
    from sqlalchemy import create_engine

    # use any sql database supported by SQLAlchemy, below we use a public mysql instance to get data
    # NOTE: you'll need to install pymysql with "pip install pymysql"
    # NOTE: loading data from public mysql instance may take several seconds
    engine = create_engine("mysql+pymysql://rfamro@mysql-rfam-public.ebi.ac.uk:4497/Rfam")
    with engine.connect() as conn:
        # select genome table, stream data in batches of 100 elements
        rows = conn.execution_options(yield_per=100).exec_driver_sql("SELECT * FROM genome LIMIT 1000")

        pipeline = dlt.pipeline(
            pipeline_name='from_database',
            destination='duckdb',
            dataset_name='genome_data',
        )

        # here we convert the rows into dictionaries on the fly with a map function
        load_info = pipeline.run(
            map(lambda row: dict(row._mapping), rows),
            table_name="genome"
        )

    print(load_info)
    # @@@DLT_SNIPPET_END db

    assert_load_info(load_info)


def replace_snippet() -> None:

    # @@@DLT_SNIPPET_START replace
    import dlt

    data = [
        {'id': 1, 'name': 'Alice'},
        {'id': 2, 'name': 'Bob'}
    ]

    pipeline = dlt.pipeline(
        pipeline_name='replace_data',
        destination='duckdb',
        dataset_name='mydata',
    )
    load_info = pipeline.run(data, table_name="users", write_disposition="replace")

    print(load_info)
    # @@@DLT_SNIPPET_END replace

    assert_load_info(load_info)


def incremental_snippet() -> None:

    # @@@DLT_SNIPPET_START incremental
    import dlt
    from dlt.sources.helpers import requests

    @dlt.resource(table_name="issues", write_disposition="append")
    def get_issues(
        created_at=dlt.sources.incremental("created_at", initial_value="1970-01-01T00:00:00Z")
    ):
        # NOTE: we read only open issues to minimize number of calls to the API. There's a limit of ~50 calls for not authenticated Github users
        url = "https://api.github.com/repos/dlt-hub/dlt/issues?per_page=100&sort=created&directions=desc&state=open"

        while True:
            response = requests.get(url)
            response.raise_for_status()
            yield response.json()

            # stop requesting pages if the last element was already older than initial value
            # note: incremental will skip those items anyway, we just do not want to use the api limits
            if created_at.start_out_of_range:
                break

            # get next page
            if "next" not in response.links:
                break
            url = response.links["next"]["url"]


    pipeline = dlt.pipeline(
        pipeline_name='github_issues_incremental',
        destination='duckdb',
        dataset_name='github_data_append',
    )
    load_info = pipeline.run(get_issues)
    row_counts = pipeline.last_trace.last_normalize_info

    print(row_counts)
    print("------")
    print(load_info)
    # @@@DLT_SNIPPET_END incremental

    assert_load_info(load_info)


def incremental_merge_snippet() -> None:

    # @@@DLT_SNIPPET_START incremental_merge
    import dlt
    from dlt.sources.helpers import requests

    @dlt.resource(
        table_name="issues",
        write_disposition="merge",
        primary_key="id",
    )
    def get_issues(
        updated_at = dlt.sources.incremental("updated_at", initial_value="1970-01-01T00:00:00Z")
    ):
        # NOTE: we read only open issues to minimize number of calls to the API. There's a limit of ~50 calls for not authenticated Github users
        url = f"https://api.github.com/repos/dlt-hub/dlt/issues?since={updated_at.last_value}&per_page=100&sort=updated&directions=desc&state=open"

        while True:
            response = requests.get(url)
            response.raise_for_status()
            yield response.json()

            # get next page
            if "next" not in response.links:
                break
            url = response.links["next"]["url"]

    pipeline = dlt.pipeline(
        pipeline_name='github_issues_merge',
        destination='duckdb',
        dataset_name='github_data_merge',
    )
    load_info = pipeline.run(get_issues)
    row_counts = pipeline.last_trace.last_normalize_info

    print(row_counts)
    print("------")
    print(load_info)
    # @@@DLT_SNIPPET_END incremental_merge

    assert_load_info(load_info)


def table_dispatch_snippet() -> None:

    # @@@DLT_SNIPPET_START table_dispatch
    import dlt
    from dlt.sources.helpers import requests

    @dlt.resource(primary_key="id", table_name=lambda i: i["type"], write_disposition="append")  # type: ignore
    def repo_events(
        last_created_at = dlt.sources.incremental("created_at")
    ):
        url = "https://api.github.com/repos/dlt-hub/dlt/events?per_page=100"

        while True:
            response = requests.get(url)
            response.raise_for_status()
            yield response.json()

            # stop requesting pages if the last element was already older than initial value
            # note: incremental will skip those items anyway, we just do not want to use the api limits
            if last_created_at.start_out_of_range:
                break

            # get next page
            if "next" not in response.links:
                break
            url = response.links["next"]["url"]

    pipeline = dlt.pipeline(
        pipeline_name='github_events',
        destination='duckdb',
        dataset_name='github_events_data',
    )
    load_info = pipeline.run(repo_events)
    row_counts = pipeline.last_trace.last_normalize_info

    print(row_counts)
    print("------")
    print(load_info)
    # @@@DLT_SNIPPET_END table_dispatch

    assert_load_info(load_info)

def pdf_to_weaviate_snippet() -> None:
    # @@@DLT_SNIPPET_START pdf_to_weaviate
    import os

    import dlt
    from dlt.destinations.weaviate import weaviate_adapter
    from PyPDF2 import PdfReader


    @dlt.resource(selected=False)
    def list_files(folder_path: str):
        folder_path = os.path.abspath(folder_path)
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            yield {
                "file_name": filename,
                "file_path": file_path,
                "mtime": os.path.getmtime(file_path)
            }


    @dlt.transformer(primary_key="page_id", write_disposition="merge")
    def pdf_to_text(file_item, separate_pages: bool = False):
        if not separate_pages:
            raise NotImplementedError()
        # extract data from PDF page by page
        reader = PdfReader(file_item["file_path"])
        for page_no in range(len(reader.pages)):
            # add page content to file item
            page_item = dict(file_item)
            page_item["text"] = reader.pages[page_no].extract_text()
            page_item["page_id"] = file_item["file_name"] + "_" + str(page_no)
            yield page_item

    pipeline = dlt.pipeline(
        pipeline_name='pdf_to_text',
        destination='weaviate'
    )

    # this constructs a simple pipeline that: (1) reads files from "invoices" folder (2) filters only those ending with ".pdf"
    # (3) sends them to pdf_to_text transformer with pipe (|) operator
    pdf_pipeline = list_files("assets/invoices").add_filter(
        lambda item: item["file_name"].endswith(".pdf")
    ) | pdf_to_text(separate_pages=True)

    # set the name of the destination table to receive pages
    # NOTE: Weaviate, dlt's tables are mapped to classes
    pdf_pipeline.table_name = "InvoiceText"

    # use weaviate_adapter to tell destination to vectorize "text" column
    load_info = pipeline.run(
        weaviate_adapter(pdf_pipeline, vectorize="text")
    )
    row_counts = pipeline.last_trace.last_normalize_info
    print(row_counts)
    print("------")
    print(load_info)
    # @@@DLT_SNIPPET_END pdf_to_weaviate

    assert_load_info(load_info)

    # @@@DLT_SNIPPET_START pdf_to_weaviate_read
    import weaviate

    client = weaviate.Client("http://localhost:8080")
    # get text of all the invoices in InvoiceText class we just created above
    print(client.query.get("InvoiceText", ["text", "file_name", "mtime", "page_id"]).do())
    # @@@DLT_SNIPPET_END pdf_to_weaviate_read

