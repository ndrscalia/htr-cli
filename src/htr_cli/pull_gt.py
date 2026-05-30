import typer
import requests
from rich.progress import track
from pathlib import Path, PosixPath
from typing import Annotated
from transkribus import TranskribusAPI
from transkribus.models import Collection

from enum import Enum

from . import paths
from . import config

app = typer.Typer(rich_markup_mode="rich")

class PageStatus(str, Enum):
    ground_truth = "GT"
    in_progress = "IN_PROGRESS"
    done = "DONE"
    new = "NEW"

@app.command(rich_help_panel="Fetch data")
def pull_transkribus(
        page_status: Annotated[
            PageStatus,
            typer.Option(help="Filter by page status.")
            ] = PageStatus.ground_truth,
        output_dir: Annotated[
            Path,
            typer.Option(help="Choose destination directory for downloaded files and images.")
            ] = paths.DATA_DIR
        ):
    """
    Download xml and jpg files from Transkribus based on page status.
    """
    tr_password = config.get_password()
    tr_username = config.get_email()

    api = TranskribusAPI()
    api.login(tr_username, tr_password)

    if output_dir != paths.DATA_DIR:
        paths.XML_DIR = Path(output_dir / "xml_texts")
        paths.IMAGES_DIR = Path(output_dir / "images")
        output_dir.mkdir(parents=True, exist_ok=True)
        paths.XML_DIR.mkdir(parents=True, exist_ok=True)
        paths.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        
    for collection_data in track(api.list_collections(), description="Fetching data.."):
        for document in Collection(collection_data["colId"]).get_documents(api):
            for page in document.get_pages(api):
                if page.data["ctStatus"] == page_status:
                    collection_name = collection_data["colName"]
                    doc_id = page.data["docId"]
                    page_id = page.data["pageId"]
                    img_id = page.data["imageId"]
                    file_name = page.data["imgFileName"].split(".")[0]
                    full_name = f"{collection_name}_{doc_id}_{page_id}_{img_id}_{file_name}"

                    # Download image
                    img_dir = paths.IMAGES_DIR
                    img_url = page.data["url"]
                    img_path = img_dir / f"{full_name}.jpg"

                    img_response = requests.get(img_url, stream=True)
                    with open(img_path, "wb") as f:
                        for chunk in img_response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    # Download XML transcript
                    xml_dir = paths.XML_DIR
                    transcript = page.get_transcript()
                    xml_url = transcript.data["url"]
                    xml_path = xml_dir / f"{full_name}.xml"

                    xml_response = requests.get(xml_url)
                    with open(xml_path, "wb") as f:
                        f.write(xml_response.content)
