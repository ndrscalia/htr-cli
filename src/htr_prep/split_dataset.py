import typer
import pandas as pd
from typing import Annotated
from sklearn.model_selection import train_test_split
from rich import print

from . import paths
from . import utils

app = typer.Typer(rich_markup_mode="rich")

@app.command(rich_help_panel="Pre-processing")
def split_dataset(
        omit_unclear: Annotated[
            bool,
            typer.Option(
                "--omit-unclear",
                "-u",
                help="Omit lines where an 'unclear' tag appears."
                )
            ] = True,
        val_size: Annotated[
            float,
            typer.Option(
                "--val-size",
                help="Choose validation set size. If you only want train and val split, leave `--test-size` to the default value."
                )
            ] = 10,
        test_size: Annotated[
            float,
            typer.Option(
                "--test-size",
                help="Choose test set size."
                )
            ] = 0
        ):
    """
    Extract tokenized and non-tokenized text lines, split for training, test, and validation, and generate corresponding ids files.
    """

    segments_df = pd.read_csv(paths.LINES_CSV, index_col=False)
    segments_df["collection"] = segments_df["page"].apply(lambda x: x.split("_")[0])
    segments_df["region_key"] = segments_df["region_id"].apply(utils.normalize_region)

    # drop lines with missing reading order and store them
    # for inspection in a csv file (see EOF)
    dropped_df = segments_df[segments_df["reading_order"].isna()]
    segments_df = segments_df.dropna(subset=["reading_order"])

    segments_df["full_id"] = (
            segments_df["page"]
            + "_reg-" + segments_df["region_order"].astype(int).map(lambda n: f"{n:04d}")
            + "-" + segments_df["region_key"]
            + "_ro" + segments_df["reading_order"].astype(int).map(lambda n: f"{n:04d}")
            + "_" + segments_df["line_id"]
        )
    segments_df["line_text"] = segments_df["line_text"].str.replace("\u00a0", " ", regex=False)
    segments_df["tok_line_text"] = segments_df["line_text"].apply(lambda x: " ".join(char if char != " " else "<space>" for char in x))

    if omit_unclear:
        segments_df = segments_df[segments_df["unclear_tag"] == False]

    test_pages = None
    test_df = None
    page_ids = segments_df["page"].unique()

    if test_size == 0:
        first_split = val_size / 100

        train_pages, val_pages = train_test_split(page_ids, test_size=first_split, random_state=42)

        train_df = segments_df[segments_df["page"].isin(train_pages)]
        train_df = train_df.sort_values(["page", "region_order", "reading_order"], kind="stable")

        val_df = segments_df[segments_df["page"].isin(val_pages)]
        val_df = val_df.sort_values(["page", "region_order", "reading_order"], kind="stable")
    if test_size != 0:
        first_split = (val_size + test_size) / 100

        train_pages, val_pages = train_test_split(page_ids, test_size=first_split, random_state=42)

        train_df = segments_df[segments_df["page"].isin(train_pages)]
        train_df = train_df.sort_values(["page", "region_order", "reading_order"], kind="stable")

        second_split = test_size / (val_size + test_size)

        val_pages, test_pages = train_test_split(val_pages, test_size=second_split, random_state=42)

        val_df = segments_df[segments_df["page"].isin(val_pages)]
        val_df = val_df.sort_values(["page", "region_order", "reading_order"], kind="stable")

        test_df = segments_df[segments_df["page"].isin(test_pages)]
        test_df = test_df.sort_values(["page", "region_order", "reading_order"], kind="stable")


    with open(paths.CORPUS_CHAR, "w") as f:
        for _, row in segments_df.iterrows():
            f.write(f"{row['tok_line_text']}\n")

    with open(paths.TRAIN_TEXT, "w") as f:
        for _, row in train_df.iterrows():
            f.write(f"train/{row['full_id']} {row['line_text']}\n")

    with open(paths.VAL_TEXT, "w") as f:
        for _, row in val_df.iterrows():
            f.write(f"val/{row['full_id']} {row['line_text']}\n")

    with open(paths.TRAIN_TOK_TEXT, "w") as f:
        for _, row in train_df.iterrows():
            f.write(f"train/{row['full_id']} {row['tok_line_text']}\n")

    with open(paths.VAL_TOK_TEXT, "w") as f:
        for _, row in val_df.iterrows():
            f.write(f"val/{row['full_id']} {row['tok_line_text']}\n")

    with open(paths.TRAIN_IDS, "w") as f:
        for _, row in train_df.iterrows():
            f.write(f"train/{row['full_id']}\n")

    with open(paths.VAL_IDS, "w") as f:
        for _, row in val_df.iterrows():
            f.write(f"val/{row['full_id']}\n")

    if test_df is not None:
        with open(paths.TEST_TEXT, "w") as f:
            for _, row in test_df.iterrows():
                f.write(f"test/{row['full_id']} {row['line_text']}\n")

        with open(paths.TEST_TOK_TEXT, "w") as f:
            for _, row in test_df.iterrows():
                f.write(f"test/{row['full_id']} {row['tok_line_text']}\n")

        with open(paths.TEST_IDS, "w") as f:
            for _, row in test_df.iterrows():
                f.write(f"test/{row['full_id']}\n")

    print(
          "\nThe following files have been [bold bright_green]written[/bold bright_green]:\n"
          f"    {paths.TRAIN_TEXT}\n"
          f"    {paths.VAL_TEXT}\n"
          f"    {paths.TRAIN_TOK_TEXT}\n"
          f"    {paths.VAL_TOK_TEXT}\n"
          f"    {paths.TRAIN_IDS}\n"
          f"    {paths.VAL_IDS}\n"
          f"    {paths.CORPUS_CHAR}\n"
    )

    if test_df is not None:
        print(
        f"      {paths.TEST_TEXT}\n"
        f"      {paths.TEST_TOK_TEXT}\n"
        f"      {paths.TEST_IDS}\n"
                )

    if not dropped_df.empty:
        print(
                "The following lines have been [bold red]dropped[/bold red] because of missing reading order:\n"
                )
        print(dropped_df)
        dropped_df.to_csv("missing_reading_order.csv")
        print(
                "csv file saved to: missing_reading_order.csv"
                )

