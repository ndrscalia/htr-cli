import typer
from rich import print
from typing import Annotated

from . import paths
from . import utils
from . import config

app = typer.Typer(rich_markup_mode="rich")

@app.command(rich_help_panel="Config")
def init(
        transkribus: Annotated[
            bool,
            typer.Option(prompt=True)
            ]
        ):
    """
    Set different configuration options interactively.
    """
    if transkribus:
        email = typer.prompt("Email")
        password = typer.prompt("Password", hide_input=True)
        config.set_email(email)
        config.set_password(password)
        print("We are [bold green]done[/bold green]!")
    else:
        print("We are [bold green]done[/bold green]!")


@app.command(rich_help_panel="Config")
def scaffold():
    """
    Command to scaffold the directory tree.
    """

    try:
        for d in paths.DIRS:
            d.mkdir(parents=True, exist_ok=True)
        print("[bold bright_blue]All directories have been successfully created![/bold bright_blue]")
        print(utils.build_tree(paths.DIRS))
        
    except PermissionError:
        print("[red]Permission denied while trying to create directories![/red]")

