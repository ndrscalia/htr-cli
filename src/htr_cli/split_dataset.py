import typer
import pandas as pd
from pathlib import Path
from typing import Annotated, Optional
from sklearn.model_selection import train_test_split
from rich import print

from . import paths
from . import utils

app = typer.Typer(rich_markup_mode="rich")


def _read_page_set(path: Path) -> set[str]:
    # Split on "_reg-" so we accept both bare page names and full line ids
    # (the latter is what this command writes to {train,val,test}_ids.txt).
    with open(path) as f:
        return {line.strip().split("_reg-")[0] for line in f if line.strip()}


def _subset(df: pd.DataFrame, pages) -> pd.DataFrame:
    return (
        df[df["page"].isin(pages)]
        .sort_values(["page", "region_order", "reading_order"], kind="stable")
    )


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
            ] = 0,
        custom_train: Annotated[
            Optional[Path],
            typer.Option(
                "--custom-train",
                help="Path to a file listing pages for the train split (one id per line; accepts page names or full line ids). When set, --val-size and --test-size are ignored."
                )
            ] = None,
        custom_val: Annotated[
            Optional[Path],
            typer.Option(
                "--custom-val",
                help="Path to a file listing pages for the val split. Required when --custom-train is set."
                )
            ] = None,
        custom_test: Annotated[
            Optional[Path],
            typer.Option(
                "--custom-test",
                help="Path to a file listing pages for the test split. Optional even when other custom files are set."
                )
            ] = None,
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
        segments_df = segments_df[~segments_df["unclear_tag"]]

    if custom_train or custom_val or custom_test:
        if not (custom_train and custom_val):
            raise typer.BadParameter("--custom-train and --custom-val must both be provided when using custom splits.")

        train_pages = _read_page_set(custom_train)
        val_pages = _read_page_set(custom_val)
        test_pages = _read_page_set(custom_test) if custom_test else None

        overlaps = []
        if train_pages & val_pages:
            overlaps.append(f"train ∩ val: {sorted(train_pages & val_pages)[:3]}")
        if test_pages is not None:
            if train_pages & test_pages:
                overlaps.append(f"train ∩ test: {sorted(train_pages & test_pages)[:3]}")
            if val_pages & test_pages:
                overlaps.append(f"val ∩ test: {sorted(val_pages & test_pages)[:3]}")
        if overlaps:
            raise typer.BadParameter("Custom splits overlap: " + "; ".join(overlaps))

        all_custom = train_pages | val_pages | (test_pages or set())
        missing = all_custom - set(segments_df["page"].unique())
        if missing:
            sample = sorted(missing)[:5]
            print(f"[yellow]warning: {len(missing)} page(s) from custom files not present in lines.csv (likely filtered by --omit-unclear or missing reading_order). Sample: {sample}[/yellow]")
    else:
        page_ids = segments_df["page"].unique()
        if test_size == 0:
            train_pages, val_pages = train_test_split(page_ids, test_size=val_size / 100, random_state=42)
            test_pages = None
        else:
            train_pages, holdout = train_test_split(page_ids, test_size=(val_size + test_size) / 100, random_state=42)
            val_pages, test_pages = train_test_split(holdout, test_size=test_size / (val_size + test_size), random_state=42)

    train_df = _subset(segments_df, train_pages)
    val_df = _subset(segments_df, val_pages)
    test_df = _subset(segments_df, test_pages) if test_pages is not None else None


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

