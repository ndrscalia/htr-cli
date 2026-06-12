import cv2
import json
import typer
import numpy as np
from typing import Annotated
from rich.progress import track

from ._vendor.deslant_img import deslant_img
from . import utils
from . import paths

app = typer.Typer(rich_markup_mode="rich")

@app.command(rich_help_panel="Pre-processing")
def process_images(
        norm_height: Annotated[
            int,
            typer.Argument(help="Height normalization value in pixels.")
            ] = 64,
        contrast_stretch: Annotated[
            bool,
            typer.Option(
                "--contrast-stretch/--no-contrast-stretch",
                help="Disable contrast stretch with `--no-contrast-stretch`.",
                show_default=True
                )
            ] = True,
        enhance_sauvola: Annotated[
            bool,
            typer.Option(
                "--enhance-sauvola/--no-enhance-sauvola",
                help="Disable enhance Sauvola with `--no-enhance-sauvola`.",
                show_default=True
                )
            ] = True,
        deslope: Annotated[
            bool,
            typer.Option(
                "--deslope/--no-deslope",
                help="Disable deslope with `--no-deslope`.",
                show_default=True
                )
            ] = True,
        deslant: Annotated[
            bool,
            typer.Option(
                "--deslant/--no-deslant",
                help="Disable deslant with `--no-deslant`.",
                show_default=True
                )
            ] = True,
        moment_normalize: Annotated[
            bool,
            typer.Option(
                "--moment-normalize/--no-moment-normalize",
                help="Disable moment normalize with `--no-moment-normalize`.",
                show_default=True
                )
            ] = True,
        light_pipeline: Annotated[
            bool,
            typer.Option(
                "--light-pipeline",
                help="Use a pipeline that only consists of deslope, deslant, and enhance.",
                show_default=False
                )
            ] = False,
        full_pipeline: Annotated[
                bool,
                typer.Option(
                "--full-pipeline/--no-full-pipeline",
                show_default=True
                )
            ] = True,
        ):
    """
    Extract line images and apply preprocessing to each one.
    """

    for dir in [paths.IMAGES_DIR, paths.TRAIN_IMAGES, paths.VAL_IMAGES]:
        dir.mkdir(parents=True, exist_ok=True)

    with open(paths.POLYGONS_JSON, "r") as f:
        content = json.load(f)

    with open(paths.VAL_IDS, "r") as f:
        val_ids = {s.strip().split("/")[-1] for s in f.readlines()}

    with open(paths.TRAIN_IDS, "r") as f:
        train_ids = {s.strip().split("/")[-1] for s in f.readlines()}

    test_ids: set[str] = set()
    if paths.TEST_IDS.exists():
        with open(paths.TEST_IDS, "r") as f:
            test_ids = {s.strip().split("/")[-1] for s in f.readlines()}
        paths.TEST_IMAGES.mkdir(parents=True, exist_ok=True)

    seen_lines: set[str] = set()
    if paths.CHECKPOINT.exists():
        with open(paths.CHECKPOINT, "r") as f:
            seen_lines = {s.strip() for s in f.readlines()}

    for line in track(content, description="Extracting lines", total=len(content)):
        region_key = utils.normalize_region(line["region_id"])
        region_order = int(line["region_order"])
        ro = int(line["reading_order"])
        full_name = f"{line['page']}_reg-{region_order:04d}-{region_key}_ro{ro:04d}_{line['line_id']}"

        if full_name in seen_lines:
            continue

        if full_name in train_ids:
            output_path = paths.TRAIN_IMAGES
        elif full_name in val_ids:
            output_path = paths.VAL_IMAGES
        elif full_name in test_ids:
            output_path = paths.TEST_IMAGES
        else:
            continue # skip images that where filtered out because of the unclear_tag in split_dataset.py

        img_path = utils.find_extension(paths.IMAGES_DIR, line["page"])
        if img_path is None:
            continue
        img = cv2.imread(img_path)

        pts = []

        for coord in line["coords"].split():
            pts.append([int(n) for n in coord.split(",")])

        pts_arr = np.array(pts)

        mask = np.zeros(img.shape[:2], dtype=np.uint8) # transparency layer
        cv2.fillPoly(mask, [pts_arr], 255) # fill poly with white

        result = np.full_like(img, 255) # white background instead of black
        result[mask == 255] = img[mask == 255] # copy only polygon pixels

        x, y, w, h = cv2.boundingRect(pts_arr)
        cropped_img = result[y:y+h, x:x+w] # keep the smallest rectangle that contains the poly
        cropped_img = cv2.cvtColor(cropped_img, cv2.COLOR_BGR2GRAY)

        if light_pipeline:
            if deslope:
                cropped_img = utils.deslope(cropped_img)
            if deslant:
                cropped_img = deslant_img(cropped_img).img
            if enhance_sauvola:
                cropped_img = utils.enhance_sauvola(cropped_img)

        if full_pipeline:
            if contrast_stretch:
                cropped_img = utils.contrast_stretch(cropped_img)
            if enhance_sauvola:
                cropped_img = utils.enhance_sauvola(cropped_img, slope=0.5)
            if deslope:
                cropped_img = utils.deslope(cropped_img)
            if deslant:
                cropped_img, _ = utils.deslant(cropped_img) # not working properly if before enhance_sauvola
            if moment_normalize:
                cropped_img = utils.moment_normalize(cropped_img)

        # resize image while keeping aspect ratio
        target_h = norm_height
        h_orig, w_orig = cropped_img.shape[:2]
        scale = target_h / h_orig
        cropped_img = cv2.resize(cropped_img, (int(w_orig * scale), target_h))


        cropped_img = cv2.copyMakeBorder(cropped_img, 0, 0, 10, 10, cv2.BORDER_CONSTANT, value=255)

        cv2.imwrite(
                f"{output_path}/{full_name}.jpg",
                cropped_img
                )

        with open(paths.CHECKPOINT, "a") as f:
            f.write(f"{full_name}\n")

        seen_lines.add(full_name)
