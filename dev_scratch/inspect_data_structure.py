"""
Run this script in a REPL and then use something like `pprint(page_data[i])`
to inspect how the data is strctured.
"""
import os
from transkribus import TranskribusAPI
from transkribus.models import Collection

api = TranskribusAPI()
api.login()

initial_cwd = os.getcwd()

document_data = []
page_data = []

for collection_data in api.list_collections():
    for document in Collection(collection_data["colId"]).get_documents(api):
        content = document.data
        document_data.append(content)
        for page in document.get_pages(api):
            content = page.data
            page_data.append(content)
