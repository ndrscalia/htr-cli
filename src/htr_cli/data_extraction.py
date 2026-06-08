import json
import unicodedata
import re
from typing import Annotated, Optional
import typer
import pandas as pd
from lxml import etree
from pathlib import Path
from rich.progress import track

from . import utils
from . import paths

app = typer.Typer(rich_markup_mode="rich")

@app.command(rich_help_panel="Pre-processing")
def data_extraction(
        regions_list: Annotated[
            Optional[list[str]],
            typer.Argument(help="Choose the region/regions you want to extract. If `None`, extracts every region. If regions are not defined in your XML data, leave to `None`.")
            ] = None,
        unclear_name: Annotated[
            str,
            typer.Option(help="Choose the exact name of the tag that skips a line.")
            ] = "unclear"

        ):
    """
    This command extracts text for every line (lines.csv), build syms.txt, and creates polygons_coordinates.json for segments extraction from images.
    """
    segments_df = pd.DataFrame(
            columns=[
                "page",
                "region_id",
                "region_order",
                "reading_order",
                "line_id","line_text"
                ]
            )
    full_text = []
    polygons_coordinates = []

    files_path = Path("data/xml_texts/")

    for current_file in track(files_path.iterdir(), description="Extracting data"):
        if current_file.is_file:

            tree = etree.parse(current_file)
            elem = tree.getroot()

            ns_uri = etree.QName(elem.tag).namespace
            ns = {"page": ns_uri} if ns_uri else {}

            regions = elem.findall(".//page:TextRegion", namespaces=ns)

            for region in regions:
                region_type = utils.get_custom_field(region.get("custom"), "structure", "type")
                if not regions_list or region_type in regions_list:
                    region_id = region.get("id")
                    region_order = utils.parse_reading_order(region.get("custom"))
                    if region_order is None:
                        continue
                    lines = region.findall("page:TextLine", namespaces=ns)
                    for line in lines:

                        unclear_tag = utils.get_custom_field(line.get("custom"), unclear_name, "offset")

                        if unclear_tag:
                            unclear_tag = True
                        else:
                            unclear_tag = False

                        reading_order = utils.parse_reading_order(line.get("custom"))
                        if reading_order is None:
                            continue

                        coordinates = {}

                        coords = line.find("page:Coords", namespaces=ns)
                        points = coords.get("points")

                        text_elem = line.find("page:TextEquiv/page:Unicode", namespaces=ns)
                        text = text_elem.text if text_elem is not None and text_elem.text is not None else ""
                        if not text.strip():
                            continue
                        full_text.append(text)

                        page_name = current_file.stem
                        line_id = line.get("id")
                        new_row = pd.DataFrame(
                                [
                                    {
                                        "page": page_name,
                                        "region_id": region_id,
                                        "region_order": region_order,
                                        "reading_order": reading_order,
                                        "line_id": line_id,
                                        "line_text": text,
                                        "unclear_tag": unclear_tag
                                        }
                                    ]
                                )
                        segments_df = pd.concat([segments_df, new_row], ignore_index=True)

                        coordinates["page"] = current_file.stem
                        coordinates["region_id"] = region_id
                        coordinates["region_order"] = region_order
                        coordinates["reading_order"] = reading_order
                        coordinates["line_id"] = line.get("id")
                        coordinates["coords"] = points

                        polygons_coordinates.append(coordinates)

    with open("polygons_coordinates.json", "w") as f:
        f.write(json.dumps(polygons_coordinates, indent=4, separators=(",", ": ")))

    segments_df.to_csv("lines.csv", index=False)

    with open(paths.SYMS_TXT, "w") as f:
        chars = []
        for string in full_text:
            for char in string:
                chars.append(" " if unicodedata.category(char) == "Zs" or char == "\t" else char) # every space sep and tab is treated as space

        f.write("<ctc> 0\n")

        global_index = 1

        for index, char in enumerate(set(chars), start=1):
            if char == " ":
                f.write(f"<space> {index}\n")
            else:
                f.write(f"{char} {index}\n")

            global_index += 1

        f.write(f"<unk> {global_index}")

    # build a list of tokens for prediction with LM
    with open(paths.TOK_TXT, "w") as f:
        chars = []
        for string in full_text:
            for char in string:
                chars.append(" " if unicodedata.category(char) == "Zs" or char == "\t" else char) # every space sep and tab is treated as space

        f.write("<ctc>\n")


        for char in set(chars):
            if char == " ":
                f.write("<space>\n")
            else:
                f.write(f"{char}\n")

        f.write("<unk>")

    # build a lexicon of tokens for prediction with LM (only suited for char level LM)
    with open(paths.LEX_TXT, "w") as f:
        chars = []
        for string in full_text:
            for char in string:
                chars.append(" " if unicodedata.category(char) == "Zs" or char == "\t" else char) # every space sep and tab is treated as space

        f.write("<ctc> <ctc>\n")


        for char in set(chars):
            if char == " ":
                f.write("<space> <space>\n")
            else:
                f.write(f"{char} {char}\n")

        f.write("<unk> <unk>")

    # build a dictionary of words to find orthographic differencs
    with open(paths.DICTIONARY, "w") as f:
        words = []
        full_text = " ".join(full_text) # remove punctuation
        full_text = re.sub(r"[^\w\s]", "", full_text)

        for word in full_text.split():
            words.append(word) # with split space is filtered out and there's no need to worry about nbsp

        for word in set(words):
            f.write(f"{word}\n")
