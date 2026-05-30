from rich.progress import track
import typer
import cv2
import numpy as np
import json

from . import paths
from . import utils

app = typer.Typer(rich_markup_mode="rich")

@app.command(rich_help_panel="Pre-processing")
def process_images_tfe():
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
      stretch=True,
      enh=True,
      enh_win=30,
      enh_prm=0.1,
      #enh_prm_rand =[0.05, 0.3],
      enh3_prm0 = 0,
      enh3_prm2 = 0,
      deslope=True,
      deslant=True,
      normxheight=0,
      normheight=64,
      momentnorm=True,
      #fpgram=True,
      #fcontour=True,
      fcontour_dilate=0,
      padding=10,
      maxwidth=6000
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

        img = cv2.imread(f"{paths.IMAGES_DIR}/{line['page']}.jpg")
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
