import typer

from .initialize import app as config_app
from .pull_gt import app as fetch_data_app
from .data_extraction import app as data_extraction_app
from .split_dataset import app as split_dataset_app
from .image_processing import app as image_processing_app
from .image_processing_tfe import app as image_processing_tfe_app

app = typer.Typer()

app.add_typer(config_app)
app.add_typer(fetch_data_app)
app.add_typer(data_extraction_app)
app.add_typer(split_dataset_app)
app.add_typer(image_processing_app)
app.add_typer(image_processing_tfe_app)

if __name__ == "__main__":
    app()
