from typing import Annotated

from rich.progress import track
import typer
import cv2
import numpy as np
import json

from . import paths
from . import utils

app = typer.Typer(rich_markup_mode="rich")

@app.command(rich_help_panel="Pre-processing")
def process_images_tfe(
        norm_height: Annotated[
            int,
            typer.Option(help="Height normalization value in pixels.")
            ] = 64,
        norm_x_height: Annotated[
            int,
            typer.Option(help="x-height normalization value (0 disables; alternative to --norm-height).")
            ] = 0,
        padding: Annotated[
            int,
            typer.Option(help="Horizontal padding (px) added to each side of the output line.")
            ] = 10,
        maxwidth: Annotated[
            int,
            typer.Option(help="Maximum width (px) of the output line.")
            ] = 6000,
        enh_win: Annotated[
            int,
            typer.Option(help="Window size for the Sauvola-style enhancement.")
            ] = 30,
        enh_prm: Annotated[
            float,
            typer.Option(help="k parameter for the Sauvola-style enhancement.")
            ] = 0.1,
        enh3_prm0: Annotated[
            int,
            typer.Option(help="Reserved enhancement parameter 0 (advanced; see TFE docs).")
            ] = 0,
        enh3_prm2: Annotated[
            int,
            typer.Option(help="Reserved enhancement parameter 2 (advanced; see TFE docs).")
            ] = 0,
        stretch: Annotated[
            bool,
            typer.Option(
                "--stretch/--no-stretch",
                help="Disable contrast stretch with `--no-stretch`.",
                show_default=False
                )
            ] = True,
        enh: Annotated[
            bool,
            typer.Option(
                "--enh/--no-enh",
                help="Disable Sauvola-style enhancement with `--no-enh`.",
                show_default=False
                )
            ] = True,
        deslope: Annotated[
            bool,
            typer.Option(
                "--deslope/--no-deslope",
                help="Disable deslope with `--no-deslope`.",
                show_default=False
                )
            ] = True,
        deslant: Annotated[
            bool,
            typer.Option(
                "--deslant/--no-deslant",
                help="Disable deslant with `--no-deslant`.",
                show_default=False
                )
            ] = True,
        momentnorm: Annotated[
            bool,
            typer.Option(
                "--momentnorm/--no-momentnorm",
                help="Disable moment normalization with `--no-momentnorm`.",
                show_default=False
                )
            ] = True,
        fcontour_dilate: Annotated[
            int,
            typer.Option(help="Dilation amount (px) applied to the feature contour (0 disables).")
            ] = 0,
        ):
    """
    Extract line images and apply preprocessing to each one using `TextFeatExtractor`. Only runs on Linux. Check the docs for a working docker image.
    """
    try:
        from textfeat import TextFeatExtractor
        import pagexml
    except ImportError as e:
        raise typer.BadParameter(
                f"process-images-tfe requires `textfeat` and `pagexml`, which are Linux/Docker-only."
                f"Use `process-images` instead. ({e})"
                )

    tfe = TextFeatExtractor(
      #type="raw",
      #format="img",
      stretch=stretch,
      enh=enh,
      enh_win=enh_win,
      enh_prm=enh_prm,
      #enh_prm_rand =[0.05, 0.3],
      enh3_prm0=enh3_prm0,
      enh3_prm2=enh3_prm2,
      deslope=deslope,
      deslant=deslant,
      normxheight=norm_x_height,
      normheight=norm_height,
      momentnorm=momentnorm,
      #fpgram=True,
      #fcontour=True,
      fcontour_dilate=fcontour_dilate,
      padding=padding,
      maxwidth=maxwidth
    )

    tfe.printConf()

    for dir in [paths.IMAGES_DIR, paths.TRAIN_IMAGES, paths.VAL_IMAGES, paths.TEST_IMAGES]:
        dir.mkdir(parents=True, exist_ok=True)

    with open(paths.VAL_IDS, "r") as f:
        val_ids = {s.strip().split("/")[-1] for s in f.readlines()}

    with open(paths.TRAIN_IDS, "r") as f:
        train_ids = {s.strip().split("/")[-1] for s in f.readlines()}

    test_ids: set[str] = set()
    if paths.TEST_IDS.exists():
        with open(paths.TEST_IDS, "r") as f:
            test_ids = {s.strip().split("/")[-1] for s in f.readlines()}

    # load polygons and find a line from this page
    with open(paths.POLYGONS_JSON) as f:
      content = json.load(f)

    seen_lines: set[str] = set()
    if paths.CHECKPOINT.exists():
        with open(paths.CHECKPOINT, "r") as f:
            seen_lines = {s.strip() for s in f.readlines()}

    for line in track(content, description="Extracting lines", total=len(content)):

        # load and crop
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
        pts = np.array([[int(n) for n in c.split(",")] for c in line["coords"].split()])
        mask = np.zeros(img.shape[:2], dtype=np.uint8)
        cv2.fillPoly(mask, [pts], 255)
        result = np.full_like(img, 255)
        result[mask == 255] = img[mask == 255]
        x, y, w, h = cv2.boundingRect(pts)
        crop = result[y:y+h, x:x+w]

        # run TextFeatExtractor preprocess
        h, w, c = crop.shape
        crop_cont = np.ascontiguousarray(crop)
        mat = pagexml.Mat(h, w, cv2.CV_8UC3, crop_cont.ctypes.data)
        result = tfe.extract(mat)
        processed = np.array(result)


        cv2.imwrite(
            f"{output_path}/{full_name}.jpg",
            processed
        )

        with open(paths.CHECKPOINT, "a") as f:
            f.write(f"{full_name}\n")

        seen_lines.add(full_name)
